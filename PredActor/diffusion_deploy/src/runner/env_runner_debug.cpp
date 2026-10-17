/**
 * env_runner_debug.cpp
 *
 * Implementation of EnvRunnerDebug.
 */
#include "diffusion_deploy/runner/env_runner_debug.hpp"
#include "diffusion_deploy/utils/action_selection.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <thread>

// POSIX networking
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

namespace diffusion_deploy {

// ---- Construction / Destruction ----

EnvRunnerDebug::EnvRunnerDebug(std::unique_ptr<BaseEnv>         env,
                                std::unique_ptr<ObsComposer>     obs_composer,
                                std::unique_ptr<DiffusionAgent>  agent,
                                const EnvRunnerDebugConfig&      config)
    : env_(std::move(env))
    , obs_composer_(std::move(obs_composer))
    , agent_(std::move(agent))
    , cfg_(config)
    , obs_history_(config.base.n_obs_steps)
{
    if (!env_)          throw std::invalid_argument("EnvRunnerDebug: env is null");
    if (!obs_composer_) throw std::invalid_argument("EnvRunnerDebug: obs_composer is null");
    if (!agent_)        throw std::invalid_argument("EnvRunnerDebug: agent is null");
    agent_->actor()->configure_action_selection(cfg_.base.delay_action_step);
    const auto selection = runner_action_selection(
        cfg_.base.n_obs_steps, cfg_.base.delay_action_step, agent_->horizon(),
        agent_->actor()->terminal_action_noise_levels());
    action_lower_index_ = selection.lower_index;
    action_upper_index_ = selection.upper_index;
    action_alpha_ = selection.alpha;
    std::cout << "[EnvRunnerDebug] action_selection lower=" << selection.lower_index
              << " noise=" << selection.lower_noise_level
              << " upper=" << selection.upper_index
              << " noise=" << selection.upper_noise_level
              << " alpha=" << selection.alpha << "\n";
}

EnvRunnerDebug::~EnvRunnerDebug() {
    stop_cond_receiver();
    close_debug_udp();
    if (env_) env_->close();
}

// ---- run() ----

RunStats EnvRunnerDebug::run() {
    env_->initialize();

    auto env_dt = env_->get_step_dt();
    if (env_dt.has_value()) cfg_.base.target_dt = *env_dt;

    if (cfg_.base.enable_cond_udp) start_cond_receiver();
    if (cfg_.enable_debug_udp)     init_debug_udp();

    env_->reset();
    prime_history();

    const int n_envs = 1;
    ep_stats_.current_rewards = torch::zeros({n_envs});
    ep_stats_.current_lengths = torch::zeros({n_envs}, torch::kLong);
    ep_stats_.episode_rewards.clear();
    ep_stats_.episode_lengths.clear();

    stop_requested_.store(false);
    loop_start_ = std::chrono::steady_clock::now();

    std::cout << "[EnvRunnerDebug] Starting debug loop. max_steps="
              << cfg_.base.max_steps << "\n";

    for (int step = 0; step < cfg_.base.max_steps && !stop_requested_.load(); ++step) {
        auto step_start = std::chrono::steady_clock::now();

        bool keep_running = run_step(step);

        if (cfg_.base.realtime_mode && cfg_.base.target_dt > 0.0)
            enforce_rate(step_start);

        if (!keep_running) break;
    }

    stop_cond_receiver();
    close_debug_udp();

    // Flush unfinished episodes
    for (int i = 0; i < (int)ep_stats_.current_lengths.size(0); ++i) {
        if (ep_stats_.current_lengths[i].item<int64_t>() > 0) {
            ep_stats_.episode_rewards.push_back(ep_stats_.current_rewards[i].item<float>());
            ep_stats_.episode_lengths.push_back((float)ep_stats_.current_lengths[i].item<int64_t>());
        }
    }

    double elapsed_s = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - loop_start_).count();

    RunStats stats;
    stats.total_steps  = cfg_.base.max_steps;
    stats.elapsed_s    = elapsed_s;
    stats.avg_step_ms  = elapsed_s / std::max(1, stats.total_steps) * 1000.0;
    stats.num_episodes = (int)ep_stats_.episode_rewards.size();

    if (!ep_stats_.episode_rewards.empty()) {
        float sum = std::accumulate(ep_stats_.episode_rewards.begin(),
                                    ep_stats_.episode_rewards.end(), 0.f);
        stats.mean_episode_reward = sum / stats.num_episodes;

        float sum_l = std::accumulate(ep_stats_.episode_lengths.begin(),
                                      ep_stats_.episode_lengths.end(), 0.f);
        stats.mean_episode_length = sum_l / stats.num_episodes;
    }

    std::cout << "[EnvRunnerDebug] Done. episodes=" << stats.num_episodes
              << " mean_reward=" << stats.mean_episode_reward
              << " elapsed=" << elapsed_s << "s\n";
    return stats;
}

// ---- prime_history() ----

void EnvRunnerDebug::prime_history() {
    last_actions_ = torch::zeros({agent_->action_dim()}, torch::kFloat64);
    auto init_terms = env_->get_obs_terms(last_actions_);
    auto map = obs_terms_to_map(init_terms);
    obs_history_.init(map);
}

// ---- run_step() ----

bool EnvRunnerDebug::run_step(int step_idx) {
    auto step_start = std::chrono::steady_clock::now();

    // 1. Observe
    auto terms     = env_->get_obs_terms(last_actions_);
    auto terms_map = obs_terms_to_map(terms);
    obs_history_.shift_append(terms_map);

    // 2. Compose normalised obs [1, n_obs_steps, obs_dim]
    auto nobs = obs_composer_->compose(obs_history_.get());

    // 3. Get optional CLIP conditioning
    torch::Tensor cond;
    if (cfg_.base.enable_cond_udp) {
        std::lock_guard<std::mutex> lk(cond_mutex_);
        if (latest_cond_.defined()) cond = latest_cond_;
    }

    // 4. Inference
    auto action_traj = agent_->act(nobs, cond);  // [1, horizon, action_dim]

    // 5. Extract current-step action
    auto action = action_traj.index(
        {0, action_lower_index_, torch::indexing::Slice()});
    if (action_alpha_ != 0.0) {
        auto upper = action_traj.index(
            {0, action_upper_index_, torch::indexing::Slice()});
        action = torch::lerp(action, upper, action_alpha_);
    }

    // 6. Timing
    double step_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - step_start).count();

    // 7. Debug output
    bool do_print = cfg_.print_obs && (step_idx % cfg_.print_interval == 0);
    if (do_print) {
        print_obs_terms(step_idx, terms, action, step_ms,
                        cfg_.print_action, cfg_.print_timing);
    }

    // 8. Debug UDP
    if (cfg_.enable_debug_udp && debug_sock_ >= 0 &&
        (step_idx % cfg_.debug_udp_interval == 0)) {
        send_debug_udp(terms, action);
    }

    // 9. Step env
    last_actions_ = action.detach()
                        .to(torch::kCPU, torch::kFloat64)
                        .contiguous();
    auto result   = env_->step(action);

    // 10. Episode tracking
    ep_stats_.current_rewards[0] += result.reward;
    ep_stats_.current_lengths[0] += 1;

    if (result.done) {
        ep_stats_.episode_rewards.push_back(ep_stats_.current_rewards[0].item<float>());
        ep_stats_.episode_lengths.push_back((float)ep_stats_.current_lengths[0].item<int64_t>());
        ep_stats_.current_rewards[0] = 0.f;
        ep_stats_.current_lengths[0] = 0;
        env_->reset();
        prime_history();
        std::cout << "[EnvRunnerDebug] Episode reset at step " << step_idx << "\n";
    }

    return env_->is_running();
}

// ---- print_obs_terms() ----

void EnvRunnerDebug::print_obs_terms(int step,
                                      const ObsTerms& obs,
                                      const torch::Tensor& action,
                                      double step_ms,
                                      bool print_action,
                                      bool print_timing) {
    auto fmt_vec = [](const torch::Tensor& t, int max_elems = 8) -> std::string {
        if (!t.defined()) return "<undef>";
        auto flat = t.reshape(-1).to(torch::kFloat32).contiguous();
        std::ostringstream ss;
        ss << std::fixed << std::setprecision(4);
        int n = (int)std::min((int64_t)max_elems, flat.size(0));
        ss << "[";
        for (int i = 0; i < n; ++i) {
            ss << flat[i].item<float>();
            if (i + 1 < flat.size(0)) ss << ", ";
        }
        if (flat.size(0) > max_elems) ss << "...";
        ss << "]";
        return ss.str();
    };

    std::cout << "\n--- step " << step;
    if (print_timing) std::cout << "  (" << std::fixed << std::setprecision(2) << step_ms << " ms)";
    std::cout << " ---\n";

    if (obs.joint_pos.defined())
        std::cout << "  joint_pos[29]:         " << fmt_vec(obs.joint_pos, 10) << "\n";
    if (obs.joint_vel.defined())
        std::cout << "  joint_vel[29]:         " << fmt_vec(obs.joint_vel, 10) << "\n";
    if (obs.projected_gravity.defined())
        std::cout << "  projected_gravity[3]:  " << fmt_vec(obs.projected_gravity, 3) << "\n";
    if (obs.base_lin_vel.defined())
        std::cout << "  base_lin_vel[3]:       " << fmt_vec(obs.base_lin_vel, 3) << "\n";
    if (obs.base_ang_vel.defined())
        std::cout << "  base_ang_vel[3]:       " << fmt_vec(obs.base_ang_vel, 3) << "\n";
    if (obs.root_pos.defined())
        std::cout << "  root_pos[3]:           " << fmt_vec(obs.root_pos, 3) << "\n";
    if (obs.root_rot.defined())
        std::cout << "  root_rot[4] (wxyz):    " << fmt_vec(obs.root_rot, 4) << "\n";
    if (obs.last_actions.defined())
        std::cout << "  last_actions[29]:      " << fmt_vec(obs.last_actions, 8) << "\n";
    if (obs.body_pos.defined()) {
        auto bp = obs.body_pos.reshape({-1, 3})[0].to(torch::kFloat32);
        std::cout << "  body_pos[0] (root):    ["
                  << bp[0].item<float>() << ", "
                  << bp[1].item<float>() << ", "
                  << bp[2].item<float>() << "]\n";
    }
    if (print_action && action.defined())
        std::cout << "  action[29]:            " << fmt_vec(action, 10) << "\n";
}

// ---- enforce_rate() ----

void EnvRunnerDebug::enforce_rate(std::chrono::steady_clock::time_point step_start) {
    auto target  = std::chrono::duration<double>(cfg_.base.target_dt);
    auto elapsed = std::chrono::steady_clock::now() - step_start;
    if (elapsed < target)
        std::this_thread::sleep_for(target - elapsed);
}

// ---- Cond UDP receiver (CLIP conditioning from Python sender) ----

void EnvRunnerDebug::start_cond_receiver() {
    cond_recv_running_.store(true);
    cond_recv_thread_ = std::thread([this]() {
        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock < 0) {
            std::cerr << "[EnvRunnerDebug] cond UDP socket creation failed.\n";
            return;
        }

        sockaddr_in addr{};
        addr.sin_family      = AF_INET;
        addr.sin_port        = htons((uint16_t)cfg_.base.cond_udp_port);
        addr.sin_addr.s_addr = INADDR_ANY;

        if (bind(sock, (sockaddr*)&addr, sizeof(addr)) < 0) {
            std::cerr << "[EnvRunnerDebug] cond UDP bind failed on port "
                      << cfg_.base.cond_udp_port << "\n";
            close(sock);
            return;
        }

        struct timeval tv{0, 100000};  // 100ms timeout
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        const int n_floats       = cfg_.base.cond_dim;
        const int expected_bytes = n_floats * sizeof(float);
        std::vector<float> buf(n_floats, 0.f);

        std::cout << "[EnvRunnerDebug] Cond UDP receiver listening on port "
                  << cfg_.base.cond_udp_port
                  << " (cond_dim=" << n_floats << ")\n";

        while (cond_recv_running_.load()) {
            ssize_t n = recv(sock, buf.data(), expected_bytes, 0);
            if (n == expected_bytes) {
                auto t = torch::tensor(buf, torch::kFloat32)
                         .reshape({1, 1, n_floats});
                std::lock_guard<std::mutex> lk(cond_mutex_);
                latest_cond_ = t;
            }
        }
        close(sock);
    });
}

void EnvRunnerDebug::stop_cond_receiver() {
    cond_recv_running_.store(false);
    if (cond_recv_thread_.joinable()) cond_recv_thread_.join();
}

// ---- Debug UDP (robot state → Python visualizer) ----

void EnvRunnerDebug::init_debug_udp() {
    debug_sock_ = socket(AF_INET, SOCK_DGRAM, 0);
    if (debug_sock_ < 0) {
        std::cerr << "[EnvRunnerDebug] Failed to create debug UDP socket.\n";
        debug_sock_ = -1;
        return;
    }

    std::memset(&debug_addr_, 0, sizeof(debug_addr_));
    debug_addr_.sin_family = AF_INET;
    debug_addr_.sin_port   = htons((uint16_t)cfg_.debug_udp_port);
    inet_pton(AF_INET, cfg_.debug_udp_host.c_str(), &debug_addr_.sin_addr);

    std::cout << "[EnvRunnerDebug] Debug UDP will send to "
              << cfg_.debug_udp_host << ":" << cfg_.debug_udp_port << "\n";
}

void EnvRunnerDebug::close_debug_udp() {
    if (debug_sock_ >= 0) {
        close(debug_sock_);
        debug_sock_ = -1;
    }
}

// ---- send_debug_udp() ----
//
// Wire format:
//   [4B magic][4B frame_idx][4B n_fields]
//   per field:
//     [64B name][4B n_floats][n_floats * 4B float32]
//
void EnvRunnerDebug::send_debug_udp(const ObsTerms& obs,
                                     const torch::Tensor& action) {
    if (debug_sock_ < 0) return;

    struct Field { const char* name; torch::Tensor tensor; bool enabled; };
    std::vector<Field> fields = {
        {"joint_pos",         obs.joint_pos,         cfg_.send_joint_pos},
        {"joint_vel",         obs.joint_vel,         cfg_.send_joint_vel},
        {"projected_gravity", obs.projected_gravity, cfg_.send_projected_gravity},
        {"base_lin_vel",      obs.base_lin_vel,      cfg_.send_base_lin_vel},
        {"base_ang_vel",      obs.base_ang_vel,      cfg_.send_base_ang_vel},
        {"root_pos",          obs.root_pos,          cfg_.send_root_pos},
        {"root_rot",          obs.root_rot,          cfg_.send_root_rot},
        {"last_actions",      obs.last_actions,      cfg_.send_last_actions},
        {"body_pos",          obs.body_pos,          cfg_.send_body_pos},
        {"body_lin_vel",      obs.body_lin_vel,      cfg_.send_body_lin_vel},
        {"action",            action,                cfg_.send_last_actions},
    };

    std::vector<uint8_t> buf;
    buf.reserve(64 * 1024);

    auto write_u32 = [&](uint32_t v) {
        buf.push_back(v & 0xFF);
        buf.push_back((v >> 8) & 0xFF);
        buf.push_back((v >> 16) & 0xFF);
        buf.push_back((v >> 24) & 0xFF);
    };

    uint32_t n_fields = 0;
    for (auto& f : fields)
        if (f.enabled && f.tensor.defined() && f.tensor.numel() > 0) ++n_fields;

    write_u32(DEBUG_UDP_MAGIC);
    write_u32(frame_idx_++);
    write_u32(n_fields);

    for (auto& f : fields) {
        if (!f.enabled || !f.tensor.defined() || f.tensor.numel() == 0) continue;

        char name_buf[DEBUG_FIELD_NAME_LEN] = {};
        std::strncpy(name_buf, f.name, DEBUG_FIELD_NAME_LEN - 1);
        buf.insert(buf.end(), (uint8_t*)name_buf,
                   (uint8_t*)name_buf + DEBUG_FIELD_NAME_LEN);

        auto flat = f.tensor.reshape(-1).to(torch::kFloat32).contiguous();
        uint32_t n_floats = (uint32_t)flat.numel();
        write_u32(n_floats);

        const float* data_ptr = flat.data_ptr<float>();
        buf.insert(buf.end(), (uint8_t*)data_ptr,
                   (uint8_t*)(data_ptr + n_floats));
    }

    if (buf.size() > 65507) {
        std::cerr << "[EnvRunnerDebug] Warning: debug UDP payload too large ("
                  << buf.size() << " bytes), truncating.\n";
        buf.resize(65507);
    }

    sendto(debug_sock_, buf.data(), buf.size(), 0,
           (sockaddr*)&debug_addr_, sizeof(debug_addr_));
}

}  // namespace diffusion_deploy
