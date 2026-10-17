/**
 * unitree_env.cpp
 *
 * Implementation of UnitreeEnv.
 * Communicates with the G1 robot via unitree_sdk2 DDS channels.
 *
 * When compiled with HAVE_UNITREE_SDK2 the real SDK headers and libraries
 * are used.  Without them the DDS calls are stubbed out so the rest of the
 * library can still be built and unit-tested.
 */
#include "diffusion_deploy/env/unitree_env.hpp"
#include <cmath>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <chrono>

#ifdef USE_FK
#include "diffusion_deploy/utils/g1_fk.hpp"
#endif

#ifdef HAVE_UNITREE_SDK2
#ifdef ENABLE_UNITREE_COMMAND_PUBLISH
#include <unitree/robot/channel/channel_publisher.hpp>
#include <unitree/idl/hg/LowCmd_.hpp>
#include <unitree/dds_wrapper/common/crc.h>
#include <unitree/dds_wrapper/robots/g1/g1.h>
#include <unitree/dds_wrapper/robots/go2/go2.h>
#include <unitree/robot/b2/motion_switcher/motion_switcher_client.hpp>
#endif
#include <unitree/robot/channel/channel_subscriber.hpp>
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/idl/hg/LowState_.hpp>
#include <unitree/idl/go2/SportModeState_.hpp>
using LowState_t       = unitree_hg::msg::dds_::LowState_;
using SportModeState_t = unitree_go::msg::dds_::SportModeState_;
#ifdef ENABLE_UNITREE_COMMAND_PUBLISH
using LowCmd_t         = unitree_hg::msg::dds_::LowCmd_;
#endif
#endif

namespace diffusion_deploy {

// ---- DDS pimpl ----

struct UnitreeEnv::DdsHandles {
#ifdef HAVE_UNITREE_SDK2
#ifdef ENABLE_UNITREE_COMMAND_PUBLISH
    unitree::robot::ChannelPublisherPtr<LowCmd_t> lowcmd_pub;
    std::shared_ptr<unitree::robot::b2::MotionSwitcherClient> motion_switcher;
#endif
    unitree::robot::ChannelSubscriberPtr<LowState_t>       lowstate_sub;
    unitree::robot::ChannelSubscriberPtr<SportModeState_t> highstate_sub;
#endif
};

namespace {
std::atomic<uint64_t> g_publisher_constructions{0};
std::atomic<uint64_t> g_shutdown_calls{0};
std::atomic<uint64_t> g_publish_calls{0};
}

const char* execution_mode_name(ExecutionMode mode) {
    switch (mode) {
        case ExecutionMode::Offline: return "offline";
        case ExecutionMode::ReceiveOnly: return "receive-only";
        case ExecutionMode::NoPublish: return "no-publish";
        case ExecutionMode::Control: return "control";
    }
    return "unknown";
}

ExecutionMode parse_execution_mode(const std::string& value) {
    if (value == "offline") return ExecutionMode::Offline;
    if (value == "receive-only") return ExecutionMode::ReceiveOnly;
    if (value == "no-publish") return ExecutionMode::NoPublish;
    if (value == "control") return ExecutionMode::Control;
    throw std::invalid_argument(
        "unknown execution mode '" + value +
        "'; expected offline, receive-only, no-publish, or control");
}

UnitreeEnv::SafetyCounters UnitreeEnv::safety_counters() {
    return {g_publisher_constructions.load(), g_shutdown_calls.load(),
            g_publish_calls.load()};
}

void UnitreeEnv::reset_safety_counters_for_test() {
    g_publisher_constructions.store(0);
    g_shutdown_calls.store(0);
    g_publish_calls.store(0);
}

// ---- Construction / Destruction ----

UnitreeEnv::UnitreeEnv(const UnitreeEnvConfig& config)
    : config_(config), dds_(std::make_unique<DdsHandles>()) {
    // Pre-size state arrays
    state_.joint_pos.resize(config_.num_dof, 0.f);
    state_.joint_vel.resize(config_.num_dof, 0.f);
    state_.joint_torque.resize(config_.num_dof, 0.f);

#ifdef USE_FK
    if (config_.use_fk) {
        if (config_.urdf_path.empty()) {
            throw std::runtime_error(
                "[UnitreeEnv] use_fk=true but urdf_path is empty. "
                "Set env.urdf_path in g1_deploy_config.yaml.");
        }
        fk_ = std::make_unique<G1ForwardKinematics>(config_.urdf_path);
    }
#endif
}

UnitreeEnv::~UnitreeEnv() {
    close();
}

// ---- Lifecycle ----

void UnitreeEnv::initialize() {
    if (initialized_.load()) {
        std::cout << "[UnitreeEnv] Already initialized.\n";
        return;
    }

#ifdef HAVE_UNITREE_SDK2
    if (config_.execution_mode != ExecutionMode::Offline) {
        const auto initialize_dds = [this]() {
            if (config_.network_interface.empty()) {
                unitree::robot::ChannelFactory::Instance()->Init(0);
            } else {
                unitree::robot::ChannelFactory::Instance()->Init(
                    0, config_.network_interface);
            }
        };
        initialize_dds();

        if (config_.execution_mode == ExecutionMode::Control) {
#ifdef ENABLE_UNITREE_COMMAND_PUBLISH
            // Unitree MuJoCo uses loopback DDS and does not expose the physical
            // robot's MotionSwitcher service. All other interfaces retain the
            // high-level-mode release gate before low-level command ownership.
            if (config_.release_mode_before_control &&
                config_.network_interface != "lo") {
                // Preserve the Unitree reference startup handoff: detect a
                // pre-existing low-level command stream and stop the default
                // controller before constructing our publisher.
                auto lowcmd_check =
                    std::make_shared<unitree::robot::g1::subscription::LowCmd>();
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
                if (!lowcmd_check->isTimeout()) {
                    std::cout
                        << "[UnitreeEnv] Existing rt/lowcmd stream detected; "
                           "shutting down the active controller before takeover.\n";
                    unitree::robot::go2::shutdown();
                    g_shutdown_calls.fetch_add(1);

                    lowcmd_check.reset();
                    unitree::robot::ChannelFactory::Instance()->Release();
                    std::this_thread::sleep_for(std::chrono::milliseconds(300));
                    initialize_dds();

                    auto verify_lowcmd =
                        std::make_shared<unitree::robot::g1::subscription::LowCmd>();
                    std::this_thread::sleep_for(std::chrono::milliseconds(200));
                    if (!verify_lowcmd->isTimeout()) {
                        throw std::runtime_error(
                            "[UnitreeEnv] rt/lowcmd remains active after controller "
                            "shutdown; refusing to create a second publisher");
                    }
                }

                dds_->motion_switcher =
                    std::make_shared<unitree::robot::b2::MotionSwitcherClient>();
                dds_->motion_switcher->SetTimeout(5.0f);
                dds_->motion_switcher->Init();

                std::string form;
                std::string name;
                const int32_t check_status = dds_->motion_switcher->CheckMode(form, name);
                if (check_status != 0) {
                    throw std::runtime_error(
                        "[UnitreeEnv] MotionSwitcher CheckMode failed: " +
                        std::to_string(check_status));
                }
                if (!name.empty()) {
                    std::cout << "[UnitreeEnv] Releasing active high-level mode: "
                              << name << "\n";
                    const int32_t release_status = dds_->motion_switcher->ReleaseMode();
                    g_shutdown_calls.fetch_add(1);
                    if (release_status != 0) {
                        throw std::runtime_error(
                            "[UnitreeEnv] MotionSwitcher ReleaseMode failed: " +
                            std::to_string(release_status));
                    }
                    std::this_thread::sleep_for(std::chrono::seconds(1));

                    form.clear();
                    name.clear();
                    const int32_t verify_status =
                        dds_->motion_switcher->CheckMode(form, name);
                    if (verify_status != 0 || !name.empty()) {
                        throw std::runtime_error(
                            "[UnitreeEnv] high-level mode remained active after ReleaseMode");
                    }
                }
            }

            dds_->lowcmd_pub.reset(
                new unitree::robot::ChannelPublisher<LowCmd_t>("rt/lowcmd"));
            dds_->lowcmd_pub->InitChannel();
            g_publisher_constructions.fetch_add(1);
#else
            throw std::runtime_error(
                "[UnitreeEnv] control mode requires a command-publishing build");
#endif
        }

        dds_->lowstate_sub.reset(
            new unitree::robot::ChannelSubscriber<LowState_t>("rt/lowstate"));
        dds_->lowstate_sub->InitChannel([this](const void* msg) {
            const auto* s = reinterpret_cast<const LowState_t*>(msg);
            std::lock_guard<std::mutex> lk(state_mutex_);
            for (int i = 0; i < config_.num_dof && i < 35; ++i) {
                state_.joint_pos[i]    = s->motor_state()[i].q();
                state_.joint_vel[i]    = s->motor_state()[i].dq();
                state_.joint_torque[i] = s->motor_state()[i].tau_est();
            }
            const auto& imu = s->imu_state();
            state_.imu_quat = {imu.quaternion()[0], imu.quaternion()[1],
                               imu.quaternion()[2], imu.quaternion()[3]};
            state_.imu_gyro = {imu.gyroscope()[0], imu.gyroscope()[1],
                               imu.gyroscope()[2]};
            state_.imu_rpy = {imu.rpy()[0], imu.rpy()[1], imu.rpy()[2]};
            state_.mode_machine = s->mode_machine();
            const auto& wr = s->wireless_remote();
            std::copy(wr.begin(), wr.end(), state_.wireless_remote.begin());
            state_.valid = true;
            last_lowstate_ns_.store(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count(),
                std::memory_order_release);
        }, 1);

        dds_->highstate_sub.reset(
            new unitree::robot::ChannelSubscriber<SportModeState_t>("rt/sportmodestate"));
        dds_->highstate_sub->InitChannel([this](const void* msg) {
            const auto* s = reinterpret_cast<const SportModeState_t*>(msg);
            std::lock_guard<std::mutex> lk(state_mutex_);
            state_.base_lin_vel = {(float)s->velocity()[0],
                                   (float)s->velocity()[1],
                                   (float)s->velocity()[2]};
            state_.base_pos = {(float)s->position()[0],
                               (float)s->position()[1],
                               (float)s->position()[2]};
            state_.high_state_valid = true;
            last_highstate_ns_.store(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count(),
                std::memory_order_release);
        }, 1);

        const auto start = std::chrono::steady_clock::now();
        while (true) {
            {
                std::lock_guard<std::mutex> lk(state_mutex_);
                if (state_.valid) break;
            }
            if (std::chrono::duration<double>(
                    std::chrono::steady_clock::now() - start).count() > 5.0) {
                throw std::runtime_error(
                    "[UnitreeEnv] Timeout waiting for robot state");
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    } else {
        state_.imu_quat = {1, 0, 0, 0};
        state_.valid = true;
    }
#else
    if (config_.execution_mode == ExecutionMode::Control) {
        throw std::runtime_error(
            "[UnitreeEnv] control mode requires Unitree SDK2");
    }
    state_.imu_quat = {1, 0, 0, 0};
    state_.valid    = true;
#endif

    std::cout << "[UnitreeEnv] Initialized mode="
              << execution_mode_name(config_.execution_mode)
#ifdef ENABLE_UNITREE_COMMAND_PUBLISH
              << "; command publishing compiled in\n";
#else
              << "; command publishing unavailable in this build\n";
#endif
    initialized_.store(true);
}

void UnitreeEnv::close() {
    initialized_.store(false);
#ifdef HAVE_UNITREE_SDK2
    dds_ = std::make_unique<DdsHandles>();
#endif
    std::cout << "[UnitreeEnv] Closed.\n";
}

void UnitreeEnv::reset() {
    // On the real robot reset is handled externally (stand-up routine).
    // Here we just zero the FK accumulator.
    std::lock_guard<std::mutex> lk(state_mutex_);
    fk_state_ = FKState{};
}

UnitreeEnv::WirelessRemoteSnapshot
UnitreeEnv::get_wireless_remote_snapshot() const {
    WirelessRemoteSnapshot snapshot;
    {
        std::lock_guard<std::mutex> lk(state_mutex_);
        snapshot.data = state_.wireless_remote;
    }
    const int64_t last_ns = last_lowstate_ns_.load(std::memory_order_acquire);
    snapshot.lowstate_received = last_ns > 0;
    if (snapshot.lowstate_received) {
        const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        snapshot.lowstate_age_s = std::max(
            0.0, static_cast<double>(now_ns - last_ns) * 1e-9);
    }
    return snapshot;
}

// ---- step() ----

StepResult UnitreeEnv::step(const torch::Tensor& action) {
    if (!initialized_.load())
        throw std::runtime_error("[UnitreeEnv] step() called before initialize().");

    if (config_.execution_mode == ExecutionMode::ReceiveOnly) {
        throw std::runtime_error(
            "[UnitreeEnv] step() is disabled in receive-only mode");
    }
    if (config_.execution_mode == ExecutionMode::Control) {
#if !defined(HAVE_UNITREE_SDK2) || !defined(ENABLE_UNITREE_COMMAND_PUBLISH)
        throw std::runtime_error(
            "[UnitreeEnv] control mode requires SDK2 and command publishing");
#endif
        if (config_.state_timeout_s <= 0.0) {
            throw std::runtime_error(
                "[UnitreeEnv] control mode requires env.state_timeout_s > 0");
        }
        const int64_t last_ns = last_lowstate_ns_.load(std::memory_order_acquire);
        const int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        const double age_s = static_cast<double>(now_ns - last_ns) * 1e-9;
        if (last_ns <= 0 || age_s > config_.state_timeout_s) {
            throw std::runtime_error(
                "[UnitreeEnv] refusing command: LowState is stale (age=" +
                std::to_string(age_s) + " s, limit=" +
                std::to_string(config_.state_timeout_s) + " s)");
        }
    }

    // action: [num_dof] in IsaacLab order (policy output, normalised residuals)
    // Host-side action transforms and SDK buffers must never dereference
    // device storage. CUDA policy outputs therefore cross this boundary as an
    // owned, contiguous CPU tensor before validation or accessor use.
    auto action_1d = action.detach().flatten()
                         .to(torch::kCPU, torch::kFloat32)
                         .contiguous();
    if (action_1d.size(0) != config_.num_dof) {
        throw std::invalid_argument(
            "[UnitreeEnv] step(): action dim mismatch. Expected " +
            std::to_string(config_.num_dof) + " got " +
            std::to_string(action_1d.size(0)));
    }
    if (!torch::isfinite(action_1d).all().item<bool>())
        throw std::runtime_error("[UnitreeEnv] refusing nonfinite action");

    // Apply action transform (mirrors g1_reindex.py apply_action_transform):
    //   1. scale:   action * ISAACLAB_ACTION_SCALE
    //   2. offset:  action_scaled + ISAACLAB_DEFAULT_JOINT_POS
    //   3. reindex: remap IsaacLab -> MuJoCo SDK joint order
    auto acc = action_1d.accessor<float, 1>();
    std::vector<float> action_abs(config_.num_dof);
    for (int i = 0; i < config_.num_dof; ++i) {
        action_abs[i] = acc[i] * ISAACLAB_ACTION_SCALE[i] + ISAACLAB_DEFAULT_JOINT_POS[i];
    }

    // Remap IsaacLab -> MuJoCo SDK joint order
    // ISAACLAB_TO_MUJOCO_REINDEX[mj] = il  =>  mujoco[mj] = action_abs[il]
    int n_mj = static_cast<int>(ISAACLAB_TO_MUJOCO_REINDEX.size());
    std::vector<float> action_mujoco(n_mj, 0.f);
    for (int mj = 0; mj < n_mj; ++mj) {
        int il = ISAACLAB_TO_MUJOCO_REINDEX[mj];
        action_mujoco[mj] = (il < config_.num_dof) ? action_abs[il] : 0.f;
    }

#if defined(HAVE_UNITREE_SDK2) && defined(ENABLE_UNITREE_COMMAND_PUBLISH)
    if (config_.execution_mode == ExecutionMode::Control) {
        LowCmd_t cmd{};
        cmd.mode_pr() = config_.use_pr_mode ? 0x01 : 0x00;
        {
            std::lock_guard<std::mutex> lk(state_mutex_);
            cmd.mode_machine() = config_.mode_machine
                ? config_.mode_machine : state_.mode_machine;
        }

        bool passive = safety_passive_.load(std::memory_order_acquire);
        std::vector<float> override_kd;
        std::vector<float> override_kp;
        {
            std::lock_guard<std::mutex> lk(safety_mutex_);
            override_kd = safety_kd_override_;
            override_kp = safety_kp_override_;
        }
        if (config_.Kp.size() < static_cast<size_t>(config_.num_dof) ||
            config_.Kd.size() < static_cast<size_t>(config_.num_dof)) {
            throw std::runtime_error("[UnitreeEnv] Kp/Kd length is smaller than num_dof");
        }

        for (int i = 0; i < config_.num_dof; ++i) {
            cmd.motor_cmd()[i].q() = action_mujoco[i];
            cmd.motor_cmd()[i].dq() = 0.0f;
            cmd.motor_cmd()[i].tau() = 0.0f;
            cmd.motor_cmd()[i].mode() = 0x01;
            if (passive) {
                cmd.motor_cmd()[i].kp() = 0.0f;
                cmd.motor_cmd()[i].kd() = i < static_cast<int>(override_kd.size())
                    ? override_kd[i] : config_.Kd[i];
            } else {
                cmd.motor_cmd()[i].kp() = i < static_cast<int>(override_kp.size())
                    ? override_kp[i] : config_.Kp[i];
                cmd.motor_cmd()[i].kd() = i < static_cast<int>(override_kd.size())
                    ? override_kd[i] : config_.Kd[i];
            }
        }
        cmd.crc() = crc32_core(reinterpret_cast<uint32_t*>(&cmd),
                               (sizeof(cmd) >> 2) - 1);
        dds_->lowcmd_pub->Write(cmd);
        g_publish_calls.fetch_add(1);
    }
#else
    (void)action_mujoco;
#endif

    StepResult res;
    res.reward = 0.f;
    res.done   = false;
    return res;
}

// ---- get_obs_terms() ----

ObsTerms UnitreeEnv::get_obs_terms(const torch::Tensor& last_actions) {
    ObservationFetchTiming ignored;
    return get_obs_terms_timed(ignored, last_actions);
}

ObsTerms UnitreeEnv::get_obs_terms_timed(ObservationFetchTiming& timing,
                                         const torch::Tensor& last_actions) {
    const auto monotonic_ns = []() {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    };
    timing = {};
    timing.fetch_start_ns = monotonic_ns();
    RobotState snapshot;
    {
        std::lock_guard<std::mutex> lk(state_mutex_);
        snapshot = state_;
        timing.lowstate_receive_ns =
            last_lowstate_ns_.load(std::memory_order_acquire);
        timing.highstate_receive_ns =
            last_highstate_ns_.load(std::memory_order_acquire);
        timing.highstate_valid = snapshot.high_state_valid;
    }
    timing.snapshot_complete_ns = monotonic_ns();
    return build_obs_terms(snapshot, last_actions, &timing);
}

// ---- Private helpers ----

ObsTerms UnitreeEnv::build_obs_terms(const RobotState& s,
                                     const torch::Tensor& last_actions,
                                     ObservationFetchTiming* timing) const {
    const auto monotonic_ns = []() {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    };
    ObsTerms terms;
    const auto dtype = torch::kFloat64;
    // B=1, T=1
    auto unsq = [](torch::Tensor t) { return t.unsqueeze(0).unsqueeze(0); };

    // Joint positions / velocities (IsaacLab order)
    auto q_il  = reindex_to_isaaclab(s.joint_pos, dtype);
    auto dq_il = reindex_to_isaaclab(s.joint_vel, dtype);
    terms.joint_pos = unsq(q_il);   // [1,1,29]
    terms.joint_vel = unsq(dq_il);  // [1,1,29]

    // Root rotation from IMU quaternion (w,x,y,z)
    auto root_quat_arr = root_rot_from_imu(s.imu_quat);
    auto root_rot_t = torch::tensor(
        {(double)root_quat_arr[0], (double)root_quat_arr[1],
         (double)root_quat_arr[2], (double)root_quat_arr[3]},
        torch::TensorOptions().dtype(dtype));
    terms.root_rot = unsq(root_rot_t); // [1,1,4]

    // Root position — use base_pos from high state if available, else zeros
    auto root_pos_t = torch::zeros({3}, dtype);
    if (s.high_state_valid) {
        root_pos_t[0] = s.base_pos[0];
        root_pos_t[1] = s.base_pos[1];
        root_pos_t[2] = s.base_pos[2];
    } else {
        root_pos_t[2] = fk_state_.root_height_estimate;
    }
    terms.root_pos = unsq(root_pos_t); // [1,1,3]
    if (timing) timing->pre_fk_complete_ns = monotonic_ns();

    // Body positions (30 bodies × 3) and body linear velocities
#ifdef USE_FK
    if (config_.use_fk && fk_) {
        // Joints in MuJoCo SDK order — reindex to IsaacLab order for FK
        auto joint_pos_il = reindex_to_isaaclab(s.joint_pos, torch::kFloat32)
                                .to(torch::kFloat32);
        auto joint_vel_il = reindex_to_isaaclab(s.joint_vel, torch::kFloat32)
                                .to(torch::kFloat32);

        std::vector<float> qpos(joint_pos_il.data_ptr<float>(),
                                joint_pos_il.data_ptr<float>() + config_.num_dof);
        std::vector<float> qvel(joint_vel_il.data_ptr<float>(),
                                joint_vel_il.data_ptr<float>() + config_.num_dof);

        auto base_lin_vel_w = s.high_state_valid
            ? std::array<float, 3>{s.base_lin_vel[0], s.base_lin_vel[1], s.base_lin_vel[2]}
            : std::array<float, 3>{0.f, 0.f, 0.f};
        auto base_pos_w = s.high_state_valid
            ? std::array<float, 3>{s.base_pos[0], s.base_pos[1], s.base_pos[2]}
            : std::array<float, 3>{0.f, 0.f, fk_state_.root_height_estimate};

        FKResult fk_res = fk_->compute(
            qpos, qvel,
            s.imu_quat, s.imu_gyro,
            base_lin_vel_w, base_pos_w,
            /* isaaclab_order= */ true);

        auto body_pos_t     = torch::zeros({30, 3}, dtype);
        auto body_lin_vel_t = torch::zeros({30, 3}, dtype);
        for (int b = 0; b < 30; ++b) {
            for (int k = 0; k < 3; ++k) {
                body_pos_t[b][k]     = (double)fk_res.body_pos[b][k];
                body_lin_vel_t[b][k] = (double)fk_res.body_lin_vel[b][k];
            }
        }
        terms.body_pos     = unsq(body_pos_t);
        terms.body_lin_vel = unsq(body_lin_vel_t);
    } else {
        terms.body_pos     = unsq(build_body_pos(s));
        terms.body_lin_vel = unsq(build_body_lin_vel(s));
    }
#else
    // Full FK placeholder
    terms.body_pos     = unsq(build_body_pos(s));       // [1,1,30,3]
    terms.body_lin_vel = unsq(build_body_lin_vel(s));   // [1,1,30,3]
#endif
    if (timing) timing->fk_complete_ns = monotonic_ns();

    // body_rot, body_ang_vel: zeros (only root/IMU used in G1 profiles)
    terms.body_rot     = unsq(torch::zeros({30, 4}, dtype));  // [1,1,30,4]
    terms.body_ang_vel = unsq(torch::zeros({30, 3}, dtype));  // [1,1,30,3]
    // Fill root angular velocity from IMU gyro
    terms.body_ang_vel.index_put_(
        {0, 0, 0, torch::indexing::Slice()},
        torch::tensor({(double)s.imu_gyro[0],
                       (double)s.imu_gyro[1],
                       (double)s.imu_gyro[2]}, dtype));

    // Projected gravity (body frame)
    auto pg = compute_projected_gravity(s.imu_quat);
    terms.projected_gravity = unsq(
        torch::tensor({(double)pg[0], (double)pg[1], (double)pg[2]}, dtype)); // [1,1,3]

    // Base linear velocity in body frame
    // SportModeState velocity[] is in world frame; rotate to body frame with quat inverse.
    auto blv_world = s.high_state_valid
        ? std::array<float,3>{s.base_lin_vel[0], s.base_lin_vel[1], s.base_lin_vel[2]}
        : std::array<float,3>{0.f, 0.f, 0.f};
    auto blv_body  = quat_rotate_inverse(s.imu_quat, blv_world);
    terms.base_lin_vel = unsq(
        torch::tensor({(double)blv_body[0], (double)blv_body[1], (double)blv_body[2]}, dtype));

    // Base angular velocity in body frame.
    // IMU gyroscope is measured in body frame directly — no rotation needed.
    terms.base_ang_vel = unsq(
        torch::tensor({(double)s.imu_gyro[0], (double)s.imu_gyro[1], (double)s.imu_gyro[2]}, dtype));

    // Last actions
    if (last_actions.defined() && last_actions.numel() > 0) {
        terms.last_actions = unsq(last_actions.flatten().to(dtype)); // [1,1,29]
    } else {
        terms.last_actions = unsq(torch::zeros({config_.num_dof}, dtype));
    }

    if (timing) timing->obs_terms_complete_ns = monotonic_ns();
    return terms;
}

torch::Tensor UnitreeEnv::reindex_to_isaaclab(const std::vector<float>& mujoco_joints,
                                               torch::Dtype dtype) {
    // MUJOCO_TO_ISAACLAB_REINDEX[il_idx] = mujoco_idx
    // so: isaaclab[il_idx] = mujoco[MUJOCO_TO_ISAACLAB_REINDEX[il_idx]]
    int n = static_cast<int>(MUJOCO_TO_ISAACLAB_REINDEX.size());
    auto t = torch::zeros(n, dtype);
    for (int il = 0; il < n; ++il) {
        int mj = MUJOCO_TO_ISAACLAB_REINDEX[il];
        t[il]  = (mj < (int)mujoco_joints.size()) ? (double)mujoco_joints[mj] : 0.0;
    }
    return t;
}


std::array<float, 3> UnitreeEnv::compute_projected_gravity(
    const std::array<float, 4>& quat_wxyz)
{
    float qw = quat_wxyz[0], qx = quat_wxyz[1],
          qy = quat_wxyz[2], qz = quat_wxyz[3];
    // Matches Python: _get_projected_gravity(quat_wxyz)
    return {
        2.f * (-qz * qx + qw * qy),
       -2.f * ( qz * qy + qw * qx),
        1.f - 2.f * (qw * qw + qz * qz)
    };
}

std::array<float, 3> UnitreeEnv::quat_rotate(const std::array<float, 4>& quat_wxyz,
                                              const std::array<float, 3>& vec)
{
    float qw = quat_wxyz[0], qx = quat_wxyz[1],
          qy = quat_wxyz[2], qz = quat_wxyz[3];
    // t = 2 * cross(q_xyz, vec)
    float tx = 2.f * (qy * vec[2] - qz * vec[1]);
    float ty = 2.f * (qz * vec[0] - qx * vec[2]);
    float tz = 2.f * (qx * vec[1] - qy * vec[0]);
    // result = vec + qw * t + cross(q_xyz, t)   [body→world]
    return {
        vec[0] + qw * tx + qy * tz - qz * ty,
        vec[1] + qw * ty + qz * tx - qx * tz,
        vec[2] + qw * tz + qx * ty - qy * tx
    };
}

// Rotate vec by the *conjugate* of quat (world→body frame).
// Matches Python _quat_rotate which uses  vec - qw*t + cross(q_xyz,t).
std::array<float, 3> UnitreeEnv::quat_rotate_inverse(const std::array<float, 4>& quat_wxyz,
                                                      const std::array<float, 3>& vec)
{
    float qw = quat_wxyz[0], qx = quat_wxyz[1],
          qy = quat_wxyz[2], qz = quat_wxyz[3];
    float tx = 2.f * (qy * vec[2] - qz * vec[1]);
    float ty = 2.f * (qz * vec[0] - qx * vec[2]);
    float tz = 2.f * (qx * vec[1] - qy * vec[0]);
    // result = vec - qw * t + cross(q_xyz, t)
    return {
        vec[0] - qw * tx + qy * tz - qz * ty,
        vec[1] - qw * ty + qz * tx - qx * tz,
        vec[2] - qw * tz + qx * ty - qy * tx
    };
}

std::array<float, 4> UnitreeEnv::root_rot_from_imu(
    const std::array<float, 4>& imu_quat_wxyz)
{
    // The IMU quaternion directly gives us the root orientation.
    return imu_quat_wxyz;
}

torch::Tensor UnitreeEnv::build_body_pos(const RobotState& s) const {
    // 30 bodies × 3 — full FK would require a Pinocchio/urdf model.
    // Placeholder: zero all bodies except root (body[0]) which gets base_pos.
    auto body_pos = torch::zeros({30, 3}, torch::kFloat64);
    if (s.high_state_valid) {
        body_pos[0][0] = s.base_pos[0];
        body_pos[0][1] = s.base_pos[1];
        body_pos[0][2] = s.base_pos[2];
    } else {
        body_pos[0][2] = fk_state_.root_height_estimate;
    }
    return body_pos; // [30, 3]
}

torch::Tensor UnitreeEnv::build_body_lin_vel(const RobotState& s) const {
    auto body_vel = torch::zeros({30, 3}, torch::kFloat64);
    if (s.high_state_valid) {
        // Rotate world-frame velocity to body frame (matches Python FK body_lin_vel[0])
        auto blv = quat_rotate_inverse(s.imu_quat,
            {s.base_lin_vel[0], s.base_lin_vel[1], s.base_lin_vel[2]});
        body_vel[0][0] = blv[0];
        body_vel[0][1] = blv[1];
        body_vel[0][2] = blv[2];
    }
    return body_vel; // [30, 3]
}

}  // namespace diffusion_deploy
