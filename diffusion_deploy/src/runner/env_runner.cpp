#include "diffusion_deploy/runner/env_runner.hpp"
#include "diffusion_deploy/utils/action_selection.hpp"
#include "diffusion_deploy/env/unitree_env.hpp"
#include "diffusion_deploy/actor/diffuse_cloc_actor.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <thread>

// For async UDP cond receiver
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

namespace diffusion_deploy {

// ---- Construction / Destruction ----

EnvRunner::EnvRunner(std::unique_ptr<BaseEnv>         env,
                     std::unique_ptr<ObsComposer>     obs_composer,
                     std::unique_ptr<DiffusionAgent>  agent,
                     const EnvRunnerConfig&           config)
    : env_(std::move(env))
    , obs_composer_(std::move(obs_composer))
    , agent_(std::move(agent))
    , config_(config)
    , obs_history_(config.n_obs_steps)
    , step_count_(0)
    , acc_obs_s_(0.0), acc_infer_s_(0.0), acc_env_step_s_(0.0)
    , acc_total_s_(0.0), max_step_s_(0.0)
{
    if (!env_)          throw std::invalid_argument("EnvRunner: env is null");
    if (!obs_composer_) throw std::invalid_argument("EnvRunner: obs_composer is null");
    if (!agent_)        throw std::invalid_argument("EnvRunner: agent is null");
    agent_->actor()->configure_action_selection(config_.delay_action_step);
    const auto selection = runner_action_selection(
        config_.n_obs_steps, config_.delay_action_step, agent_->horizon(),
        agent_->actor()->terminal_action_noise_levels());
    action_lower_index_ = selection.lower_index;
    action_upper_index_ = selection.upper_index;
    action_alpha_ = selection.alpha;
    std::cout << "[EnvRunner] action_selection lower=" << selection.lower_index
              << " noise=" << selection.lower_noise_level
              << " upper=" << selection.upper_index
              << " noise=" << selection.upper_noise_level
              << " alpha=" << selection.alpha << "\n";
    if (config_.condition_profile == "prdp_rlobs") {
        if (config_.rlobs_cond_dim != 96 || config_.n_cond_steps <= 0
            || config_.n_cond_steps > config_.n_obs_steps) {
            throw std::invalid_argument("EnvRunner: invalid PRDP RL-observation condition schema");
        }
        condition_composer_ = std::make_unique<ObsComposer>(
            ObsProfile::G1_RLObs, config_.n_obs_steps);
    } else if (config_.condition_profile == "g1_prdp_standard2") {
        if (config_.rlobs_cond_dim != 93 || config_.text_cond_dim != 512
            || config_.n_cond_steps <= 0
            || config_.n_cond_steps > config_.n_obs_steps) {
            throw std::invalid_argument(
                "EnvRunner: invalid g1_prdp_standard2 condition schema");
        }
        condition_composer_ = std::make_unique<ObsComposer>(
            ObsProfile::G1_PRDPStandard2Cond, config_.n_obs_steps);
    } else if (config_.condition_profile != "external") {
        throw std::invalid_argument("EnvRunner: unknown condition_profile");
    }
    if (config_.unified_command.enabled) {
        safety::JoystickReader* shared = config_.safety_fsm
            ? &config_.safety_fsm->joystick() : nullptr;
        unified_command_ = std::make_unique<UnifiedCommandInterface>(
            config_.unified_command, shared);
        if (unified_command_->state().latent.size()
            != static_cast<std::size_t>(config_.text_cond_dim))
            throw std::invalid_argument(
                "EnvRunner: unified command latent dimension != text_cond_dim");
        auto cloc = std::dynamic_pointer_cast<DiffuseCLoCActor>(agent_->actor());
        if (!cloc)
            throw std::invalid_argument(
                "EnvRunner: unified command requires a DiffuseCLoCActor for WBG guidance");
        cloc->set_live_wbg_command_bounds(
            config_.unified_command.max_vx,
            config_.unified_command.max_vy,
            config_.unified_command.max_wz);
        std::cout << "[EnvRunner] Unified C++ command interface enabled: motion="
                  << unified_command_->state().motion_name
                  << " transport=in-process"
                  << " max_vx=" << config_.unified_command.max_vx
                  << " max_vy=" << config_.unified_command.max_vy
                  << " max_wz=" << config_.unified_command.max_wz
                  << (config_.unified_command.compatibility_udp.enabled
                      ? "+compatibility-udp" : "") << "\n";
    }

    if (config_.csv_record.enabled) {
        validate_csv_record_config(config_.csv_record);
        int condition_dim = config_.text_cond_dim > 0
            ? config_.text_cond_dim : config_.cond_dim;
        if (condition_dim <= 0 && unified_command_)
            condition_dim = static_cast<int>(unified_command_->state().latent.size());
        std::string command_source = "none";
        if (unified_command_) {
            command_source = unified_command_source_name(
                unified_command_->resolved_source());
        } else if (config_.enable_cond_udp && config_.enable_wbg_udp) {
            command_source = "cond_udp+wbg_udp";
        } else if (config_.enable_cond_udp) {
            command_source = "cond_udp";
        } else if (config_.enable_wbg_udp) {
            command_source = "wbg_udp";
        }
        csv_recorder_ = std::make_unique<CsvRecorder>(
            config_.csv_record.path,
            config_.n_obs_steps,
            obs_composer_->obs_dim(),
            agent_->action_dim(),
            condition_dim,
            std::move(command_source),
            config_.csv_record.fields);
        std::cout << "[EnvRunner] CSV recording enabled: "
                  << csv_recorder_->path() << " fields="
                  << csv_record_fields_summary(config_.csv_record.fields) << "\n";
    }
}

EnvRunner::~EnvRunner() {
    stop_cond_receiver();
    stop_wbg_receiver();
    if (csv_recorder_) {
        try {
            csv_recorder_->close();
        } catch (const std::exception& e) {
            std::cerr << "[EnvRunner] CSV recorder close failed: "
                      << e.what() << "\n";
        }
    }
    if (env_) env_->close();
}

// ---- run() ----

RunStats EnvRunner::run() {
    // 1. Initialize env
    env_->initialize();

    // Override target_dt from env if available
    auto env_dt = env_->get_step_dt();
    if (env_dt.has_value()) config_.target_dt = *env_dt;

    // 2. Start optional cond / WBG receivers
    if (config_.enable_cond_udp) {
        start_cond_receiver();
        wait_for_initial_condition();
    }
    if (config_.enable_wbg_udp) {
        start_wbg_receiver();
    }

    // 3. Move agent to env device (agent may already be on correct device)
    //    (no-op if already there)

    // 4. Prime observation history
    env_->reset();
    prime_history();

    // 5. Initialize episode trackers
    int n_envs = 1;  // single-robot deployment
    ep_stats_.current_rewards = torch::zeros({n_envs});
    ep_stats_.current_lengths = torch::zeros({n_envs}, torch::kLong);
    ep_stats_.episode_rewards.clear();
    ep_stats_.episode_lengths.clear();

    // 6. Main loop
    stop_requested_.store(false);
    step_count_      = 0;
    acc_obs_s_       = 0.0;
    acc_infer_s_     = 0.0;
    acc_env_step_s_  = 0.0;
    acc_total_s_     = 0.0;
    max_step_s_      = 0.0;
    policy_step_count_ = 0;
    finite_action_step_count_ = 0;
    action_value_count_ = 0;
    action_sq_sum_ = 0.0;
    max_abs_action_ = 0.0;
    max_joint_displacement_ = 0.0;
    first_policy_joint_pos_ = torch::Tensor();
    looper_.reset();

    auto start_wall = std::chrono::steady_clock::now();

    for (int step = 0; step < config_.max_steps && !stop_requested_.load(); ++step) {
        auto step_start = RealtimeLooper::now();

        bool keep_running = run_step(step);

        // record() measures work time, warns on overrun, sleeps remaining budget,
        // and logs rate/rtf periodically — mirrors Python realtime_loop decorator.
        bool enforce = config_.realtime_mode && config_.target_dt > 0.0;
        double loop_dt = looper_.record(step_start, config_.target_dt, enforce);

        acc_total_s_ += loop_dt;
        if (loop_dt > max_step_s_) max_step_s_ = loop_dt;

        ++step_count_;
        if (!keep_running) break;
    }

    auto elapsed = std::chrono::steady_clock::now() - start_wall;
    double elapsed_s = std::chrono::duration<double>(elapsed).count();

    // 7. Flush unfinished episodes
    int n = static_cast<int>(ep_stats_.current_lengths.size(0));
    for (int i = 0; i < n; ++i) {
        if (ep_stats_.current_lengths[i].item<int64_t>() > 0) {
            ep_stats_.episode_rewards.push_back(
                ep_stats_.current_rewards[i].item<float>());
            ep_stats_.episode_lengths.push_back(
                static_cast<float>(ep_stats_.current_lengths[i].item<int64_t>()));
        }
    }

    // 8. Stop helpers
    stop_cond_receiver();
    stop_wbg_receiver();
    if (csv_recorder_) {
        csv_recorder_->close();
        std::cout << "[EnvRunner] CSV recording saved: "
                  << csv_recorder_->path()
                  << " (rows=" << csv_recorder_->row_count() << ")\n";
    }

    // 9. Build stats
    RunStats stats;
    stats.total_steps  = step_count_;
    stats.elapsed_s    = elapsed_s;
    stats.avg_step_ms  = step_count_ > 0 ? (acc_total_s_ / step_count_) * 1000.0 : 0.0;
    stats.num_episodes = static_cast<int>(ep_stats_.episode_rewards.size());

    // Per-phase timing
    stats.avg_obs_ms       = step_count_ > 0 ? (acc_obs_s_      / step_count_) * 1000.0 : 0.0;
    stats.avg_inference_ms = step_count_ > 0 ? (acc_infer_s_    / step_count_) * 1000.0 : 0.0;
    stats.avg_env_step_ms  = step_count_ > 0 ? (acc_env_step_s_ / step_count_) * 1000.0 : 0.0;
    stats.overrun_count    = looper_.overrun_count();
    stats.max_step_ms      = max_step_s_ * 1000.0;
    stats.policy_steps = policy_step_count_;
    stats.finite_action_steps = finite_action_step_count_;
    stats.max_abs_action = max_abs_action_;
    stats.action_rms = action_value_count_ > 0
        ? std::sqrt(action_sq_sum_ / static_cast<double>(action_value_count_)) : 0.0;
    stats.action_delta_rms = action_delta_value_count_ > 0
        ? std::sqrt(action_delta_sq_sum_ / static_cast<double>(action_delta_value_count_)) : 0.0;
    stats.max_abs_action_delta = max_abs_action_delta_;
    stats.action_jerk_rms = action_jerk_value_count_ > 0
        ? std::sqrt(action_jerk_sq_sum_ / static_cast<double>(action_jerk_value_count_)) : 0.0;
    stats.max_abs_action_jerk = max_abs_action_jerk_;
    stats.action_saturation_rate = action_normalized_value_count_ > 0
        ? static_cast<double>(action_saturation_count_) /
          static_cast<double>(action_normalized_value_count_) : 0.0;
    stats.max_joint_displacement = max_joint_displacement_;

    if (!ep_stats_.episode_rewards.empty()) {
        float sum = std::accumulate(ep_stats_.episode_rewards.begin(),
                                    ep_stats_.episode_rewards.end(), 0.f);
        stats.mean_episode_reward = sum / stats.num_episodes;

        float sum_l = std::accumulate(ep_stats_.episode_lengths.begin(),
                                      ep_stats_.episode_lengths.end(), 0.f);
        stats.mean_episode_length = sum_l / stats.num_episodes;

        float var = 0.f;
        for (float r : ep_stats_.episode_rewards) {
            float d = r - stats.mean_episode_reward;
            var += d * d;
        }
        stats.std_episode_reward = std::sqrt(var / stats.num_episodes);
    }

    std::cout << "[EnvRunner] Done."
              << "  steps="    << stats.total_steps
              << "  episodes=" << stats.num_episodes
              << "  mean_reward=" << stats.mean_episode_reward
              << "  elapsed="  << elapsed_s << "s\n"
              << "[EnvRunner] Timing (mean per step):"
              << "  obs="      << stats.avg_obs_ms       << " ms"
              << "  infer="    << stats.avg_inference_ms << " ms"
              << "  env_step=" << stats.avg_env_step_ms  << " ms"
              << "  total="    << stats.avg_step_ms      << " ms"
              << "  max="      << stats.max_step_ms      << " ms"
              << "  overruns=" << stats.overrun_count    << "\n";
    return stats;
}

// ---- prime_history() ----

void EnvRunner::prime_history() {
    agent_->reset();
    int num_dof = agent_->action_dim();
    last_actions_ = torch::zeros({num_dof}, torch::kFloat64);

    auto init_terms = env_->get_obs_terms(last_actions_);
    auto map = obs_terms_to_map(init_terms);
    obs_history_.init(map);
}

// ---- run_step() ----

bool EnvRunner::run_step(int /*step_idx*/) {
    using Clock = std::chrono::steady_clock;

    // ---- Phase 1: obs ----
    auto t0 = Clock::now();

    // 1. Get latest obs terms (T=1 snapshot)
    auto terms = env_->get_obs_terms(last_actions_);
    auto terms_map = obs_terms_to_map(terms);

    // 2. Shift history and append
    obs_history_.shift_append(terms_map);

    // 3. Compose normalized obs [1, n_obs_steps, obs_dim]
    auto nobs = obs_composer_->compose(obs_history_.get());  // [1, H, D]
    auto finite_obs = torch::isfinite(nobs);
    if (!finite_obs.all().item<bool>()) {
        auto first_bad = torch::nonzero(torch::logical_not(finite_obs))[0]
                             .to(torch::kCPU);
        throw std::runtime_error(
            "EnvRunner: nonfinite composed observation at [" +
            std::to_string(first_bad[0].item<int64_t>()) + "," +
            std::to_string(first_bad[1].item<int64_t>()) + "," +
            std::to_string(first_bad[2].item<int64_t>()) + "]");
    }

    auto t1 = Clock::now();
    acc_obs_s_ += std::chrono::duration<double>(t1 - t0).count();

    // ---- FSM Safety Gate ----
    if (config_.safety_fsm) {
        auto* uenv = dynamic_cast<UnitreeEnv*>(env_.get());
        bool unified_source_fresh = true;
        if (uenv) {
            // Feed Unitree joystick when FSM is in external mode
            auto& js = config_.safety_fsm->joystick();
            if (js.is_external_mode()) {
                const auto snapshot = uenv->get_wireless_remote_snapshot();
                const double timeout_s = unified_command_
                    && unified_command_->resolved_source()
                        == UnifiedCommandSource::UnitreeLowState
                    ? unified_command_->config().source_timeout_s
                    : uenv->config().state_timeout_s;
                const bool lowstate_fresh = snapshot.lowstate_received
                    && snapshot.lowstate_age_s <= timeout_s;
                auto ext = lowstate_fresh
                    ? safety::decode_unitree_wireless_remote(snapshot.data)
                    : safety::RawJoystickState{};
                js.apply_external_state(ext);
                if (unified_command_ && unified_command_->resolved_source()
                    == UnifiedCommandSource::UnitreeLowState) {
                    unified_source_fresh = lowstate_fresh && ext.valid;
                }
            }

            // Update FSM with latest IMU quaternion, torques, and control dt
            auto imu_q = uenv->get_imu_quat();
            auto torques = uenv->get_joint_torques();  // MuJoCo order, N·m
            double step_dt = config_.target_dt > 0.0 ? config_.target_dt : 0.02;
            config_.safety_fsm->update(imu_q, step_dt, torques);

            // Sync gain profile (on state change AND on first step)
            static bool fsm_first_step = true;
            const auto& chg = config_.safety_fsm->last_change();
            if (chg.changed || fsm_first_step) {
                fsm_first_step = false;
                bool passive = config_.safety_fsm->is_passive();
                const auto& kp = config_.safety_fsm->current_kp();
                const auto& kd = config_.safety_fsm->current_kd();
                const auto* kp_ptr = (!passive && !kp.empty()) ? &kp : nullptr;
                const auto* kd_ptr = kd.empty() ? nullptr : &kd;
                uenv->set_safety_mode(passive, kd_ptr, kp_ptr);
                std::cout << "[EnvRunner] FSM gain sync: passive=" << (passive ? "yes" : "no")
                          << "  state=" << config_.safety_fsm->state_name()
                          << "  kp_override=" << (kp_ptr ? "yes" : "no")
                          << "  kd_override=" << (kd_ptr ? "yes" : "no")
                          << "\n";
            }
        }

        // DeployFSM::update polls its JoystickReader for the production
        // Unitree path. A non-Unitree host fixture has no FSM poll, so the
        // command interface owns that poll for deterministic tests.
        update_unified_command(/*shared_reader_already_polled=*/uenv != nullptr,
                               unified_source_fresh);

        // If not Running, execute safe behaviour and skip inference
        if (!config_.safety_fsm->should_run_policy()) {
            double step_dt = config_.target_dt > 0.0 ? config_.target_dt : 0.02;
            return execute_safe_step(step_dt, terms, nobs);
        }
    } else {
        update_unified_command(/*shared_reader_already_polled=*/false, true);
    }

    // ---- Phase 2: inference ----
    // 4. Compose the profile-selected rolling robot condition; text is
    // concatenated per token. g1_prdp_standard2 deliberately omits base_lin_vel.
    torch::Tensor cond;
    torch::Tensor external_cond;
    if (config_.enable_cond_udp || unified_command_) {
        std::lock_guard<std::mutex> lk(cond_mutex_);
        if (latest_cond_.defined()) external_cond = latest_cond_;
    }
    if (condition_composer_) {
        auto rlobs = condition_composer_->compose(obs_history_.get());
        rlobs = rlobs.narrow(1, config_.n_obs_steps - config_.n_cond_steps,
                            config_.n_cond_steps);
        if (config_.text_cond_dim > 0) {
            if (!external_cond.defined() || external_cond.size(2) != config_.text_cond_dim)
                throw std::runtime_error("EnvRunner: conditional PRDP text condition missing/wrong shape");
            auto text = external_cond.expand(
                {rlobs.size(0), config_.n_cond_steps, config_.text_cond_dim});
            cond = torch::cat({rlobs, text}, 2);
        } else {
            cond = rlobs;
        }
        const int expected_dim = config_.rlobs_cond_dim + config_.text_cond_dim;
        if (cond.size(2) != expected_dim)
            throw std::runtime_error("EnvRunner: packed PRDP condition dimension mismatch");
    } else {
        cond = external_cond;
    }

    // // Debug: print first 8 values of received cond
    // if (cond.defined() && cond.numel() >= 8) {
    //     auto ca = cond.to(torch::kFloat64).flatten();
    //     std::cout << "[EnvRunner] cond[:8] = ["
    //               << ca[0].item<double>() << ", "
    //               << ca[1].item<double>() << ", "
    //               << ca[2].item<double>() << ", "
    //               << ca[3].item<double>() << ", "
    //               << ca[4].item<double>() << ", "
    //               << ca[5].item<double>() << ", "
    //               << ca[6].item<double>() << ", "
    //               << ca[7].item<double>() << "]"
    //               << "  |cond|=" << torch::linalg_norm(cond.to(torch::kFloat64)).item<double>()
    //               << "  dim=" << cond.numel()
    //               << "\n";
    // } else if (config_.enable_cond_udp) {
    //     std::cout << "[EnvRunner] cond: not yet received\n";
    // }
    // 5. Agent inference -> unnormalized action trajectory
    auto action_traj = agent_->act(nobs, cond);  // [1, horizon, action_dim]

    auto t2 = Clock::now();
    acc_infer_s_ += std::chrono::duration<double>(t2 - t1).count();

    // ---- Phase 3: env step ----
    // 6. Extract the configured zero-based action slot.
    auto action = action_traj.index(
        {0, action_lower_index_, torch::indexing::Slice()});
    if (action_alpha_ != 0.0) {
        auto upper = action_traj.index(
            {0, action_upper_index_, torch::indexing::Slice()});
        action = torch::lerp(action, upper, action_alpha_);
    }

    if (!torch::isfinite(action).all().item<bool>())
        throw std::runtime_error("EnvRunner: nonfinite selected policy action");

    ++policy_step_count_;
    ++finite_action_step_count_;
    auto action64 = action.detach().to(torch::kCPU, torch::kFloat64);
    action_value_count_ += action64.numel();
    action_sq_sum_ += action64.square().sum().item<double>();
    max_abs_action_ = std::max(
        max_abs_action_, action64.abs().max().item<double>());

    if (previous_policy_action_.defined()) {
        auto delta = action64 - previous_policy_action_;
        action_delta_value_count_ += delta.numel();
        action_delta_sq_sum_ += delta.square().sum().item<double>();
        max_abs_action_delta_ = std::max(
            max_abs_action_delta_, delta.abs().max().item<double>());
        if (previous_action_delta_.defined()) {
            auto jerk = delta - previous_action_delta_;
            action_jerk_value_count_ += jerk.numel();
            action_jerk_sq_sum_ += jerk.square().sum().item<double>();
            max_abs_action_jerk_ = std::max(
                max_abs_action_jerk_, jerk.abs().max().item<double>());
        }
        previous_action_delta_ = delta;
    }
    previous_policy_action_ = action64.clone();

    auto normalized_action = agent_->action_normalizer()->normalize(action64);
    action_normalized_value_count_ += normalized_action.numel();
    action_saturation_count_ += (normalized_action.abs() >= 0.999).sum().item<int64_t>();

    auto current_joint_pos = terms.joint_pos.detach().flatten().to(
        torch::kCPU, torch::kFloat64);
    if (!first_policy_joint_pos_.defined()) {
        first_policy_joint_pos_ = current_joint_pos.clone();
    } else {
        max_joint_displacement_ = std::max(
            max_joint_displacement_,
            (current_joint_pos - first_policy_joint_pos_).abs().max().item<double>());
    }

    // 7. Update last_actions for next step
    last_actions_ = action.detach()
                        .to(torch::kCPU, torch::kFloat64)
                        .contiguous();

    // 8. Step environment
    auto result = env_->step(action);

    auto t3 = Clock::now();
    acc_env_step_s_ += std::chrono::duration<double>(t3 - t2).count();

    if (csv_recorder_)
        record_step(/*policy_active=*/true, terms, nobs, action, external_cond);

    // 9. Track episode stats
    ep_stats_.current_rewards[0] += result.reward;
    ep_stats_.current_lengths[0] += 1;

    if (result.done) {
        ep_stats_.episode_rewards.push_back(
            ep_stats_.current_rewards[0].item<float>());
        ep_stats_.episode_lengths.push_back(
            static_cast<float>(ep_stats_.current_lengths[0].item<int64_t>()));
        ep_stats_.current_rewards[0] = 0.f;
        ep_stats_.current_lengths[0] = 0;

        // Re-prime history after episode reset
        env_->reset();
        prime_history();
    }

    return env_->is_running();
}

void EnvRunner::update_unified_command(bool shared_reader_already_polled,
                                       bool source_fresh) {
    if (!unified_command_) return;
    const auto& command = unified_command_->poll(
        shared_reader_already_polled, 0, source_fresh);
    {
        std::lock_guard<std::mutex> lk(cond_mutex_);
        latest_cond_ = torch::from_blob(
            const_cast<float*>(command.latent.data()),
            {1, 1, static_cast<int64_t>(command.latent.size())},
            torch::TensorOptions().dtype(torch::kFloat32)).clone();
    }
    auto* cloc = dynamic_cast<DiffuseCLoCActor*>(agent_->actor().get());
    if (!cloc) {
        throw std::runtime_error(
            "EnvRunner: unified command WBG requires DiffuseCLoCActor");
    }
    cloc->apply_live_wbg(make_live_wbg_frame(command.wbg));
}

void EnvRunner::record_step(bool policy_active,
                            const ObsTerms& terms,
                            const torch::Tensor& policy_obs,
                            const torch::Tensor& action,
                            const torch::Tensor& condition) {
    // With no --record-csv path, no recorder exists and this helper is not
    // called; no tensor is copied/formatted on the normal control path.
    if (!csv_recorder_) return;

    torch::Tensor condition_to_record;
    if (csv_recorder_->records_condition()) condition_to_record = condition;
    if (csv_recorder_->records_condition() && !condition_to_record.defined()
        && (config_.enable_cond_udp || unified_command_)) {
        std::lock_guard<std::mutex> lk(cond_mutex_);
        if (latest_cond_.defined()) condition_to_record = latest_cond_;
    }

    WbgUdpFrame wbg_udp;
    bool has_wbg_udp = false;
    if (csv_recorder_->records_command() && config_.enable_wbg_udp) {
        std::lock_guard<std::mutex> lk(wbg_command_mutex_);
        if (latest_wbg_command_defined_) {
            wbg_udp = latest_wbg_command_;
            has_wbg_udp = true;
        }
    }

    const std::string fsm_state = config_.safety_fsm
        ? config_.safety_fsm->state_name() : "";
    csv_recorder_->append(
        step_count_,
        config_.target_dt > 0.0
            ? static_cast<double>(step_count_) * config_.target_dt : 0.0,
        policy_active,
        fsm_state,
        terms,
        policy_obs,
        action,
        condition_to_record,
        unified_command_ ? &unified_command_->state() : nullptr,
        has_wbg_udp ? &wbg_udp : nullptr);
}

// ---- execute_safe_step() ----

bool EnvRunner::execute_safe_step(double dt,
                                  const ObsTerms& terms,
                                  const torch::Tensor& policy_obs) {
    auto* fsm   = config_.safety_fsm;
    auto* uenv  = dynamic_cast<UnitreeEnv*>(env_.get());

    if (!fsm || !uenv) return env_->is_running();

    // Use the same observation snapshot already composed at the start of this
    // control tick.  This also makes the optional recording row line up with
    // the observation that was actually observed before the safe action.
    auto joint_pos = terms.joint_pos;  // [1, 1, 29] float64

    int num_dof = static_cast<int>(joint_pos.size(2));
    std::vector<float> current_pos(num_dof);
    auto acc = joint_pos.accessor<double, 3>();
    for (int i = 0; i < num_dof; ++i) {
        current_pos[i] = static_cast<float>(acc[0][0][i]);
    }

    // Lazy init interpolation on first call after state entry
    fsm->init_interpolation(current_pos);

    // Get target positions from FSM (handles passive track / interpolation / static target)
    std::vector<float> target_abs = fsm->get_target_action(current_pos, dt);

    // Convert absolute positions to residual form for step().
    // step() applies:  action_abs = action * SCALE + DEFAULT_POS
    // So we send:     action = (target_abs - DEFAULT_POS) / SCALE
    std::vector<float> action_residual(num_dof, 0.f);
    for (int i = 0; i < num_dof; ++i) {
        float scale = (i < (int)ISAACLAB_ACTION_SCALE.size())
                      ? ISAACLAB_ACTION_SCALE[i] : 1.0f;
        float def_pos = (i < (int)ISAACLAB_DEFAULT_JOINT_POS.size())
                        ? ISAACLAB_DEFAULT_JOINT_POS[i] : 0.0f;
        float target = (i < (int)target_abs.size()) ? target_abs[i] : def_pos;
        // Avoid divide-by-zero: if scale is near zero, clamp to 1.0
        if (std::fabs(scale) < 1e-6f) scale = 1.0f;
        action_residual[i] = (target - def_pos) / scale;
    }

    auto action_t = torch::tensor(action_residual, torch::kFloat64);

    // // Diagnostic (first 3 steps + every 1000, or on state change)
    // static int safe_step_count = 0;
    // static std::string last_safe_state;
    // bool state_changed = (fsm->state_name() != last_safe_state);
    // if (safe_step_count < 3 || safe_step_count % 1000 == 0 || state_changed) {
    //     last_safe_state = fsm->state_name();
    //     std::cout << "[EnvRunner] safe_step " << safe_step_count
    //               << "  state=" << fsm->state_name()
    //               << "  target[0..2]=" << target_abs[0]
    //               << " " << target_abs[1]
    //               << " " << target_abs[2]
    //               << "  residual[0..2]=" << action_residual[0]
    //               << " " << action_residual[1]
    //               << " " << action_residual[2]
    //               << "\n";
    // }
    // ++safe_step_count;

    // Update last_actions for history consistency
    last_actions_ = action_t.detach()
                        .to(torch::kCPU, torch::kFloat64)
                        .contiguous();

    // Step environment (kp=0 in passive mode comes from set_safety_mode)
    auto result = env_->step(action_t);

    if (csv_recorder_)
        record_step(/*policy_active=*/false, terms, policy_obs, action_t, {});

    // Track episode stats (same as run_step)
    ep_stats_.current_rewards[0] += result.reward;
    ep_stats_.current_lengths[0] += 1;

    if (result.done) {
        ep_stats_.episode_rewards.push_back(
            ep_stats_.current_rewards[0].item<float>());
        ep_stats_.episode_lengths.push_back(
            static_cast<float>(ep_stats_.current_lengths[0].item<int64_t>()));
        ep_stats_.current_rewards[0] = 0.f;
        ep_stats_.current_lengths[0] = 0;
        env_->reset();
        prime_history();
    }

    return env_->is_running();
}

void EnvRunner::start_cond_receiver() {
    cond_recv_running_.store(true);
    cond_recv_thread_ = std::thread([this]() {
        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) {
            std::cerr << "[EnvRunner] UDP socket creation failed.\n";
            return;
        }

        sockaddr_in addr{};
        addr.sin_family      = AF_INET;
        addr.sin_port        = htons(static_cast<uint16_t>(config_.cond_udp_port));
        addr.sin_addr.s_addr = inet_addr(config_.cond_udp_host.c_str());

        if (bind(sock, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
            std::cerr << "[EnvRunner] UDP bind failed on port "
                      << config_.cond_udp_port << "\n";
            close(sock);
            return;
        }

        // Set receive timeout so we can check stop flag
        struct timeval tv{0, 100000};  // 100ms
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        const int expected_bytes = config_.cond_dim * sizeof(float);
        std::vector<float> buf(config_.cond_dim, 0.f);

        std::cout << "[EnvRunner] UDP cond receiver listening on port "
                  << config_.cond_udp_port << " (cond_dim=" << config_.cond_dim << ")\n";

        while (cond_recv_running_.load()) {
            ssize_t n = recv(sock, buf.data(),
                             static_cast<size_t>(expected_bytes), 0);
            if (n == expected_bytes) {
                auto t = torch::tensor(buf, torch::kFloat32)
                         .reshape({1, 1, config_.cond_dim});
                std::lock_guard<std::mutex> lk(cond_mutex_);
                latest_cond_ = t;
            }
        }
        close(sock);
    });
}

void EnvRunner::wait_for_initial_condition() {
    if (!condition_composer_ || config_.text_cond_dim <= 0) return;

    std::cout << "[EnvRunner] Waiting up to " << config_.cond_startup_timeout_s
              << "s for initial text condition...\n";
    const auto deadline = std::chrono::steady_clock::now()
        + std::chrono::duration<double>(config_.cond_startup_timeout_s);
    while (std::chrono::steady_clock::now() < deadline) {
        {
            std::lock_guard<std::mutex> lk(cond_mutex_);
            if (latest_cond_.defined() && latest_cond_.dim() == 3
                && latest_cond_.size(2) == config_.text_cond_dim) {
                std::cout << "[EnvRunner] Initial text condition received.\n";
                return;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    throw std::runtime_error(
        "EnvRunner: timed out waiting for initial conditional PRDP text UDP payload");
}

void EnvRunner::stop_cond_receiver() {
    cond_recv_running_.store(false);
    if (cond_recv_thread_.joinable()) {
        cond_recv_thread_.join();
    }
}

void EnvRunner::start_wbg_receiver() {
    wbg_recv_running_.store(true);
    wbg_recv_thread_ = std::thread([this]() {
        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) {
            std::cerr << "[EnvRunner] WBG UDP socket creation failed.\n";
            return;
        }

        sockaddr_in addr{};
        addr.sin_family      = AF_INET;
        addr.sin_port        = htons(static_cast<uint16_t>(config_.wbg_udp_port));
        addr.sin_addr.s_addr = inet_addr(config_.wbg_udp_host.c_str());

        if (bind(sock, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
            std::cerr << "[EnvRunner] WBG UDP bind failed on port "
                      << config_.wbg_udp_port << "\n";
            close(sock);
            return;
        }

        // Set receive timeout so we can check the stop flag.
        struct timeval tv{0, 100000};  // 100ms
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        constexpr size_t kBytes = 9 * sizeof(float);
        float buf[9] = {0.f, 0.f, 0.f, 0.f, 0.f, 0.f, 0.f, 0.f, 0.f};

        std::cout << "[EnvRunner] WBG UDP receiver listening on port "
                  << config_.wbg_udp_port << " (9 x float32 datagrams)\n";

        auto* cloc = dynamic_cast<DiffuseCLoCActor*>(agent_->actor().get());
        if (!cloc) {
            std::cerr << "[EnvRunner] WBG UDP: actor is not DiffuseCLoCActor; "
                         "interactive WBG disabled.\n";
            close(sock);
            return;
        }
        if (!cloc->wbg_enabled()) {
            std::cout << "[EnvRunner] WBG UDP: whole_body_guidance.enabled=false "
                         "in config; UDP can only adjust enabled/command/kp of a "
                         "configured WBG.\n";
        }

        long accepted = 0;
        long rejected = 0;
        while (wbg_recv_running_.load()) {
            ssize_t n = recv(sock, buf, kBytes, 0);
            if (n != static_cast<ssize_t>(kBytes)) continue;

            WbgUdpFrame frame;
            if (!parse_wbg_udp_frame(buf, kBytes, frame)) {
                if (++rejected == 1) {
                    std::cerr << "[EnvRunner] WBG UDP: rejected non-finite "
                                 "datagram (no update applied).\n";
                }
                continue;
            }
            ++accepted;
            if (csv_recorder_) {
                std::lock_guard<std::mutex> lk(wbg_command_mutex_);
                latest_wbg_command_ = frame;
                latest_wbg_command_defined_ = true;
            }
            cloc->apply_live_wbg_udp(frame);
        }
        if (accepted > 0) {
            std::cout << "[EnvRunner] WBG UDP receiver closing. accepted="
                      << accepted << " rejected=" << rejected << "\n";
        }
        close(sock);
    });
}

void EnvRunner::stop_wbg_receiver() {
    wbg_recv_running_.store(false);
    if (wbg_recv_thread_.joinable()) {
        wbg_recv_thread_.join();
    }
}

}  // namespace diffusion_deploy
