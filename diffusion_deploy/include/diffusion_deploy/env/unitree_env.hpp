/**
 * unitree_env.hpp
 *
 * Unitree G1 robot environment.
 * Mirrors diffusion_policy/env/unitree_env.py UnitreeG1Env.
 *
 * Communicates with Unitree MuJoCo or a G1 through unitree_sdk2 DDS. Command
 * publishing is compiled only when ENABLE_UNITREE_COMMAND_PUBLISH is enabled.
 *
 * Key responsibilities:
 *  - Initialize no DDS (offline), state-only DDS, or an explicit control path.
 *  - Read joint positions/velocities and IMU state from LowState_.
 *  - Compute projected gravity and body-frame velocities.
 *  - Optionally invoke forward kinematics to produce body_pos / body_lin_vel.
 *  - Validate, transform, and optionally publish LowCmd actions.
 */
#pragma once

#include "diffusion_deploy/env/base_env.hpp"
#include "diffusion_deploy/utils/math_utils.hpp"

#ifdef USE_FK
#include "diffusion_deploy/utils/g1_fk.hpp"
#include <memory>
#endif

#include <atomic>
#include <chrono>
#include <mutex>
#include <string>
#include <vector>
#include <memory>
#include <functional>

// Forward-declare SDK types so the header compiles without the SDK present.
// When HAVE_UNITREE_SDK2 is defined the .cpp includes the real headers.
#ifndef HAVE_UNITREE_SDK2
struct LowState_Stub {};
struct LowCmd_Stub {};
struct SportModeState_Stub {};
#endif

namespace diffusion_deploy {

// ---- Joint order mappings (MuJoCo SDK order <-> IsaacLab training order) ----

/**
 * Joint index order used by unitree_sdk2 LowState / LowCmd
 * (matches physical motor numbering in the G1 robot).
 */
// Reindex: for IsaacLab joint index i, MUJOCO_TO_ISAACLAB_REINDEX[i] gives the MuJoCo index.
// i.e. isaaclab_joints[i] = mujoco_joints[MUJOCO_TO_ISAACLAB_REINDEX[i]]
static const std::vector<int> MUJOCO_TO_ISAACLAB_REINDEX = {
    0, 6, 12, 1, 7, 13, 2, 8, 14,
    3, 9, 15, 22, 4, 10, 16, 23, 5, 11, 17, 24,
    18, 25, 19, 26, 20, 27, 21, 28
};

// Inverse: for MuJoCo joint index j, ISAACLAB_TO_MUJOCO_REINDEX[j] gives the IsaacLab index.
// i.e. mujoco_joints[j] = isaaclab_joints[ISAACLAB_TO_MUJOCO_REINDEX[j]]
static const std::vector<int> ISAACLAB_TO_MUJOCO_REINDEX = []() {
    std::vector<int> inv(29);
    for (int i = 0; i < 29; ++i) inv[MUJOCO_TO_ISAACLAB_REINDEX[i]] = i;
    return inv;
}();

// ---- Action transform constants (IsaacLab order, 29 joints) ----
// Mirrors g1_reindex.py ISAACLAB_DEFAULT_JOINT_POS and ISAACLAB_ACTION_SCALE.

static const std::vector<float> ISAACLAB_DEFAULT_JOINT_POS = {
    -0.312f,  // left_hip_pitch_joint
    -0.312f,  // right_hip_pitch_joint
     0.0f,    // waist_yaw_joint
     0.0f,    // left_hip_roll_joint
     0.0f,    // right_hip_roll_joint
     0.0f,    // waist_roll_joint
     0.0f,    // left_hip_yaw_joint
     0.0f,    // right_hip_yaw_joint
     0.0f,    // waist_pitch_joint
     0.669f,  // left_knee_joint
     0.669f,  // right_knee_joint
     0.2f,    // left_shoulder_pitch_joint
     0.2f,    // right_shoulder_pitch_joint
    -0.363f,  // left_ankle_pitch_joint
    -0.363f,  // right_ankle_pitch_joint
     0.2f,    // left_shoulder_roll_joint
    -0.2f,    // right_shoulder_roll_joint
     0.0f,    // left_ankle_roll_joint
     0.0f,    // right_ankle_roll_joint
     0.0f,    // left_shoulder_yaw_joint
     0.0f,    // right_shoulder_yaw_joint
     0.6f,    // left_elbow_joint
     0.6f,    // right_elbow_joint
     0.0f,    // left_wrist_roll_joint
     0.0f,    // right_wrist_roll_joint
     0.0f,    // left_wrist_pitch_joint
     0.0f,    // right_wrist_pitch_joint
     0.0f,    // left_wrist_yaw_joint
     0.0f,    // right_wrist_yaw_joint
};

static const std::vector<float> ISAACLAB_ACTION_SCALE = {
    0.5475464652142303f,   // left_hip_pitch_joint
    0.5475464652142303f,   // right_hip_pitch_joint
    0.5475464652142303f,   // waist_yaw_joint
    0.3506614663788243f,   // left_hip_roll_joint
    0.3506614663788243f,   // right_hip_roll_joint
    0.43857731392336724f,  // waist_roll_joint
    0.5475464652142303f,   // left_hip_yaw_joint
    0.5475464652142303f,   // right_hip_yaw_joint
    0.43857731392336724f,  // waist_pitch_joint
    0.3506614663788243f,   // left_knee_joint
    0.3506614663788243f,   // right_knee_joint
    0.43857731392336724f,  // left_shoulder_pitch_joint
    0.43857731392336724f,  // right_shoulder_pitch_joint
    0.43857731392336724f,  // left_ankle_pitch_joint
    0.43857731392336724f,  // right_ankle_pitch_joint
    0.43857731392336724f,  // left_shoulder_roll_joint
    0.43857731392336724f,  // right_shoulder_roll_joint
    0.43857731392336724f,  // left_ankle_roll_joint
    0.43857731392336724f,  // right_ankle_roll_joint
    0.43857731392336724f,  // left_shoulder_yaw_joint
    0.43857731392336724f,  // right_shoulder_yaw_joint
    0.43857731392336724f,  // left_elbow_joint
    0.43857731392336724f,  // right_elbow_joint
    0.43857731392336724f,  // left_wrist_roll_joint
    0.43857731392336724f,  // right_wrist_roll_joint
    0.07450087032950714f,  // left_wrist_pitch_joint
    0.07450087032950714f,  // right_wrist_pitch_joint
    0.07450087032950714f,  // left_wrist_yaw_joint
    0.07450087032950714f,  // right_wrist_yaw_joint
};

static const std::vector<float> DEFAULT_KP = {
    60, 60, 60, 100, 40, 40,     // left leg
    60, 60, 60, 100, 40, 40,     // right leg
    60, 40, 40,                  // waist
    40, 40, 40, 40, 40, 40, 40,  // left arm
    40, 40, 40, 40, 40, 40, 40   // right arm
};

static const std::vector<float> DEFAULT_KD = {
    1, 1, 1, 2, 1, 1,
    1, 1, 1, 2, 1, 1,
    1, 1, 1,
    1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1
};

// ---- Configuration ----

enum class ExecutionMode {
    Offline,
    ReceiveOnly,
    NoPublish,
    Control,
};

const char* execution_mode_name(ExecutionMode mode);
ExecutionMode parse_execution_mode(const std::string& value);

struct UnitreeEnvConfig {
    ExecutionMode execution_mode = ExecutionMode::Offline;
    std::string network_interface = "";  // empty = use default interface
    double      control_dt        = 0.02; // 50 Hz
    double      state_timeout_s   = 0.10; // refuse control from stale LowState
    int         num_dof           = 29;
    std::vector<float> Kp         = DEFAULT_KP;
    std::vector<float> Kd         = DEFAULT_KD;
    bool        enable_safety_checks = true;
    bool        release_mode_before_control = true;
    bool        use_pr_mode          = true;  // PR mode (ankle PD) vs AB mode
    uint8_t     mode_machine         = 0;     // 0=auto-detect, 5=G1-29dof

    // Forward kinematics (compiled only when USE_FK=ON)
    bool        use_fk    = false;            // Enable Pinocchio FK
    std::string urdf_path = "";               // Path to G1 URDF file
};

// ---- Robot state snapshot (all accessed under state_mutex) ----

struct RobotState {
    // Joint positions/velocities/torques in MuJoCo SDK order [num_dof]
    std::vector<float> joint_pos;
    std::vector<float> joint_vel;
    std::vector<float> joint_torque;  // estimated motor torque [N·m]
    // IMU
    std::array<float, 4> imu_quat = {1, 0, 0, 0}; // w, x, y, z
    std::array<float, 3> imu_gyro = {0, 0, 0};     // body-frame angular vel
    std::array<float, 3> imu_rpy  = {0, 0, 0};     // roll, pitch, yaw
    // SportModeState (high-level, optional)
    std::array<float, 3> base_lin_vel = {0, 0, 0};  // world-frame
    std::array<float, 3> base_pos     = {0, 0, 0};  // world-frame
    bool high_state_valid = false;
    // Mode
    uint8_t mode_machine = 0;
    bool    valid        = false;

    // Unitree wireless remote (40-byte raw packet, parsed into UnitreeJoystick)
    std::array<uint8_t, 40> wireless_remote = {};
};

/** Monotonic receive/fetch boundaries for an observation snapshot.
 *
 * The subscriber is asynchronous. lowstate_receive_ns is the local callback
 * completion time associated with the copied state, not sensor acquisition
 * time, so consumers must label it as a packet-age proxy.
 */
struct ObservationFetchTiming {
    int64_t fetch_start_ns = 0;
    int64_t lowstate_receive_ns = 0;
    int64_t highstate_receive_ns = 0;
    bool highstate_valid = false;
    int64_t snapshot_complete_ns = 0;
    int64_t pre_fk_complete_ns = 0;
    int64_t fk_complete_ns = 0;
    int64_t obs_terms_complete_ns = 0;
};

// ---- UnitreeEnv ----

class UnitreeEnv : public BaseEnv {
public:
    explicit UnitreeEnv(const UnitreeEnvConfig& config = {});
    ~UnitreeEnv() override;

    void initialize() override;
    void close() override;
    void reset() override;

    /**
     * Execute one control step.
     * action: joint position targets in IsaacLab order [num_dof].
     *         Internally remapped to MuJoCo SDK order and published only in
     *         Control mode from a command-publishing build.
     */
    StepResult step(const torch::Tensor& action) override;

    /**
     * Build ObsTerms from current robot state.
     * Returned tensors have shape [1, 1, ...] (B=1, T=1).
     *
     * last_actions: [num_dof] in IsaacLab order, used for last_actions term.
     *               Pass undefined tensor to use zeros.
     */
    ObsTerms get_obs_terms(const torch::Tensor& last_actions = {}) override;

    /** Same observation path with local monotonic receive/fetch boundaries. */
    ObsTerms get_obs_terms_timed(ObservationFetchTiming& timing,
                                 const torch::Tensor& last_actions = {});

    bool is_running() const override { return initialized_.load(); }
    std::optional<double> get_step_dt() const override { return config_.control_dt; }

    const UnitreeEnvConfig& config() const { return config_; }

    struct SafetyCounters {
        uint64_t publisher_constructions = 0;
        uint64_t shutdown_calls = 0;
        uint64_t publish_calls = 0;
    };

    static SafetyCounters safety_counters();
    static void reset_safety_counters_for_test();

    // ---- Safety / FSM interface ----

    /** Thread-safe snapshot of latest IMU quaternion [w, x, y, z]. */
    std::array<float, 4> get_imu_quat() const {
        std::lock_guard<std::mutex> lk(state_mutex_);
        return state_.imu_quat;
    }

    /** Thread-safe snapshot of latest joint torques (MuJoCo order, N·m). */
    std::vector<float> get_joint_torques() const {
        std::lock_guard<std::mutex> lk(state_mutex_);
        return state_.joint_torque;
    }

    /** Thread-safe snapshot of latest wireless remote data (40-byte raw packet). */
    std::array<uint8_t, 40> get_wireless_remote() const {
        std::lock_guard<std::mutex> lk(state_mutex_);
        return state_.wireless_remote;
    }

    struct WirelessRemoteSnapshot {
        std::array<uint8_t, 40> data{};
        bool lowstate_received = false;
        double lowstate_age_s = 0.0;
    };

    /** Wireless bytes and age from the existing LowState subscriber. */
    WirelessRemoteSnapshot get_wireless_remote_snapshot() const;

    /**
     * Set safety / FSM gain overrides.
     *
     * When passive=true, subsequent step() calls send kp=0 and use
     * the provided kd_override (or config Kd if nullptr).
     * When passive=false, kp_override/kd_override replace config
     * Kp/Kd for per-state stiffness (e.g. Ready stand gains).
     * Pass nullptr to revert to config defaults.
     *
     * Thread-safe: called from the same thread as step(), but
     * uses an atomic flag for visibility.
     */
    void set_safety_mode(bool passive,
                         const std::vector<float>* kd_override = nullptr,
                         const std::vector<float>* kp_override = nullptr) {
        safety_passive_.store(passive, std::memory_order_release);
        std::lock_guard<std::mutex> lk(safety_mutex_);
        // Always apply overrides when provided (both passive and active states)
        if (kd_override && !kd_override->empty()) {
            safety_kd_override_ = *kd_override;
        } else if (!passive && kd_override && kd_override->empty()) {
            safety_kd_override_.clear();  // explicit empty → revert to config
        }
        if (kp_override && !kp_override->empty()) {
            safety_kp_override_ = *kp_override;
        } else if (passive) {
            safety_kp_override_.clear();  // passive → kp=0 via the passive flag
        }
    }

private:
    UnitreeEnvConfig config_;
    std::atomic<bool> initialized_{false};

    // Shared robot state (updated by DDS callbacks)
    mutable std::mutex state_mutex_;
    RobotState state_;
    std::atomic<int64_t> last_lowstate_ns_{0};
    std::atomic<int64_t> last_highstate_ns_{0};

    // Safety mode (FSM-controlled)
    std::atomic<bool>      safety_passive_{false};
    mutable std::mutex     safety_mutex_;
    std::vector<float>     safety_kd_override_;
    std::vector<float>     safety_kp_override_;

    // Forward-kinematics accumulator for body_pos / body_lin_vel
    // Updated incrementally from joint + IMU data.
    // Simple version: we propagate only root pose + joint positions.
    // A full FK pipeline (Pinocchio) can be added via USE_FK flag.
    struct FKState {
        std::array<float, 3> root_pos = {0, 0, 0};
        float root_height_estimate    = 0.76f;  // rough G1 pelvis height
    } fk_state_;

#ifdef USE_FK
    // Pinocchio FK — only allocated when config_.use_fk == true.
    std::unique_ptr<G1ForwardKinematics> fk_;
#endif

    // ---- DDS handles (pimpl to avoid SDK headers in public interface) ----
    struct DdsHandles;
    std::unique_ptr<DdsHandles> dds_;

    // ---- Private helpers ----

    /** Build ObsTerms from a locked robot state snapshot. */
    ObsTerms build_obs_terms(const RobotState& s,
                             const torch::Tensor& last_actions,
                             ObservationFetchTiming* timing = nullptr) const;

    /** Reindex joint array from MuJoCo SDK order to IsaacLab order. */
    static torch::Tensor reindex_to_isaaclab(const std::vector<float>& mujoco_joints,
                                             torch::Dtype dtype = torch::kFloat64);

    /** Compute gravity projection: g rotated into body frame by quat (w,x,y,z). */
    static std::array<float, 3> compute_projected_gravity(
        const std::array<float, 4>& quat_wxyz);

    /** Rotate 3-vector by quaternion (w,x,y,z).  Body→world. */
    static std::array<float, 3> quat_rotate(
        const std::array<float, 4>& quat_wxyz,
        const std::array<float, 3>& vec);

    /** Rotate 3-vector by *conjugate* of quaternion (w,x,y,z).  World→body.
     *  Matches Python _quat_rotate (uses  vec - qw*t + cross(q_xyz,t)). */
    static std::array<float, 3> quat_rotate_inverse(
        const std::array<float, 4>& quat_wxyz,
        const std::array<float, 3>& vec);

    /** Build simple body_pos tensor (30 bodies × 3).
     *  For profiles that do NOT need full FK, only root body[0] is set. */
    torch::Tensor build_body_pos(const RobotState& s) const;

    /** Build body_lin_vel tensor (30 bodies × 3). Only root body used. */
    torch::Tensor build_body_lin_vel(const RobotState& s) const;

    /** Estimate root rotation quaternion (w,x,y,z) from IMU. */
    static std::array<float, 4> root_rot_from_imu(
        const std::array<float, 4>& imu_quat_wxyz);
};

}  // namespace diffusion_deploy
