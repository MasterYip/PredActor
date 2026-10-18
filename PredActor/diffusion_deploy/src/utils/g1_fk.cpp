/**
 * g1_fk.cpp
 *
 * G1 Robot Forward Kinematics using Pinocchio.
 * Mirrors diffusion_policy/utils/g1fk_pinocchio.py.
 */
#ifdef USE_FK

#include "diffusion_deploy/utils/g1_fk.hpp"

#include <cmath>
#include <stdexcept>
#include <iostream>
#include <unordered_map>

#include <pinocchio/parsers/urdf.hpp>
#include <pinocchio/algorithm/kinematics.hpp>
#include <pinocchio/algorithm/frames.hpp>

namespace diffusion_deploy {

// ---------------------------------------------------------------------------
// Body names — must match ISAACLAB_BODY_NAMES in g1_reindex.py (30 bodies)
// ---------------------------------------------------------------------------
static const char* const ISAACLAB_BODY_NAMES[30] = {
    "pelvis",
    "left_hip_pitch_link",
    "right_hip_pitch_link",
    "waist_yaw_link",
    "left_hip_roll_link",
    "right_hip_roll_link",
    "waist_roll_link",
    "left_hip_yaw_link",
    "right_hip_yaw_link",
    "torso_link",
    "left_knee_link",
    "right_knee_link",
    "left_shoulder_pitch_link",
    "right_shoulder_pitch_link",
    "left_ankle_pitch_link",
    "right_ankle_pitch_link",
    "left_shoulder_roll_link",
    "right_shoulder_roll_link",
    "left_ankle_roll_link",
    "right_ankle_roll_link",
    "left_shoulder_yaw_link",
    "right_shoulder_yaw_link",
    "left_elbow_link",
    "right_elbow_link",
    "left_wrist_roll_link",
    "right_wrist_roll_link",
    "left_wrist_pitch_link",
    "right_wrist_pitch_link",
    "left_wrist_yaw_link",
    "right_wrist_yaw_link",
};

// Joint names in IsaacLab (alphabetical) order — 29 actuated joints.
// Must match ISAACLAB_DOF_NAMES in g1_reindex.py.
static const char* const ISAACLAB_DOF_NAMES[29] = {
    "left_hip_pitch_joint",
    "right_hip_pitch_joint",
    "waist_yaw_joint",
    "left_hip_roll_joint",
    "right_hip_roll_joint",
    "waist_roll_joint",
    "left_hip_yaw_joint",
    "right_hip_yaw_joint",
    "waist_pitch_joint",
    "left_knee_joint",
    "right_knee_joint",
    "left_shoulder_pitch_joint",
    "right_shoulder_pitch_joint",
    "left_ankle_pitch_joint",
    "right_ankle_pitch_joint",
    "left_shoulder_roll_joint",
    "right_shoulder_roll_joint",
    "left_ankle_roll_joint",
    "right_ankle_roll_joint",
    "left_shoulder_yaw_joint",
    "right_shoulder_yaw_joint",
    "left_elbow_joint",
    "right_elbow_joint",
    "left_wrist_roll_joint",
    "right_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "right_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_wrist_yaw_joint",
};

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

G1ForwardKinematics::G1ForwardKinematics(const std::string& urdf_path)
    : data_(pinocchio::Model{})
{
    // Build fixed-base model (no floating base — we handle world transform manually,
    // matching g1fk_pinocchio.py which uses pinocchio.buildModelFromUrdf default).
    pinocchio::urdf::buildModel(urdf_path, model_);
    data_ = pinocchio::Data(model_);

    std::cout << "[G1FK] Loaded URDF from " << urdf_path << "\n";
    std::cout << "[G1FK]   njoints=" << model_.njoints
              << "  nv=" << model_.nv << "\n";

    // ---- Resolve body frame IDs ----
    body_frame_ids_.resize(30);
    for (int b = 0; b < 30; ++b) {
        std::string name = ISAACLAB_BODY_NAMES[b];
        if (!model_.existFrame(name)) {
            throw std::runtime_error(
                "[G1FK] Body frame '" + name + "' not found in URDF model.\n"
                "  Check that the URDF matches ISAACLAB_BODY_NAMES.");
        }
        body_frame_ids_[b] = model_.getFrameId(name);
    }

    // ---- Build joint remapping: Pinocchio order → IsaacLab order ----
    // Pinocchio names joints starting at index 1 (index 0 = universe).
    // We find each IsaacLab joint in Pinocchio's list and record where it lands.
    // joint_remapping_[pin_idx] = isaaclab_idx
    // so that q_pin[pin_idx] = q_il[joint_remapping_[pin_idx]]
    int njoints_act = model_.nv;  // == 29 for a fixed-base 29-DOF model
    joint_remapping_.resize(njoints_act, -1);

    // Map joint name → IsaacLab index
    std::unordered_map<std::string, int> il_idx_map;
    for (int i = 0; i < 29; ++i) {
        il_idx_map[ISAACLAB_DOF_NAMES[i]] = i;
    }

    // Walk Pinocchio joints (skip universe at index 0)
    int q_offset = 0;
    for (int j = 1; j < model_.njoints; ++j) {
        const std::string& jname = model_.names[j];
        auto it = il_idx_map.find(jname);
        if (it != il_idx_map.end()) {
            // Pinocchio q-index for this joint:
            int nq_j = model_.joints[j].nq();
            for (int k = 0; k < nq_j && q_offset + k < njoints_act; ++k) {
                joint_remapping_[q_offset + k] = it->second + k;
            }
        }
        q_offset += model_.joints[j].nq();
    }

    // Check all entries were filled
    for (int i = 0; i < njoints_act; ++i) {
        if (joint_remapping_[i] < 0) {
            throw std::runtime_error(
                "[G1FK] Could not map Pinocchio q[" + std::to_string(i) +
                "] to any IsaacLab joint.");
        }
    }

    std::cout << "[G1FK] Joint remapping built ("
              << njoints_act << " DOFs).\n";
}

// ---------------------------------------------------------------------------
// compute()
// ---------------------------------------------------------------------------

FKResult G1ForwardKinematics::compute(
    const std::vector<float>& joint_pos,
    const std::vector<float>& joint_vel,
    const std::array<float, 4>& imu_quat,
    const std::array<float, 3>& imu_gyro,
    const std::array<float, 3>& base_lin_vel,
    const std::array<float, 3>& base_pos,
    bool isaaclab_order) const
{
    int nv = model_.nv;

    // ---- Build Pinocchio q / v vectors ----
    Eigen::VectorXd q = Eigen::VectorXd::Zero(model_.nq);
    Eigen::VectorXd v = Eigen::VectorXd::Zero(model_.nv);

    if (isaaclab_order) {
        // Remap: q_pin[i] = q_il[ joint_remapping_[i] ]
        for (int i = 0; i < nv; ++i) {
            int il = joint_remapping_[i];
            q[i] = (il < (int)joint_pos.size()) ? joint_pos[il] : 0.0;
            v[i] = (il < (int)joint_vel.size()) ? joint_vel[il] : 0.0;
        }
    } else {
        for (int i = 0; i < nv; ++i) {
            q[i] = (i < (int)joint_pos.size()) ? joint_pos[i] : 0.0;
            v[i] = (i < (int)joint_vel.size()) ? joint_vel[i] : 0.0;
        }
    }

    // ---- Pinocchio FK in base frame ----
    pinocchio::forwardKinematics(model_, data_, q, v);
    pinocchio::updateFramePlacements(model_, data_);

    // ---- World-frame transform ----
    // Convert IMU quaternion (wxyz) → RPY → rotation matrix
    auto imu_rpy = quat_wxyz_to_rpy(imu_quat);
    float R[3][3];
    rpy_to_rot_matrix(imu_rpy, R);

    // ---- Extract body positions and velocities ----
    FKResult res;
    res.body_pos.resize(30);
    res.body_lin_vel.resize(30);

    for (int b = 0; b < 30; ++b) {
        pinocchio::FrameIndex fid = body_frame_ids_[b];

        // Position in base frame
        const auto& t_base = data_.oMf[fid].translation();
        std::array<float, 3> p_base = {
            (float)t_base[0], (float)t_base[1], (float)t_base[2]};

        // Velocity in base frame (LOCAL_WORLD_ALIGNED reference)
        auto v_frame = pinocchio::getFrameVelocity(
            model_, data_, fid, pinocchio::LOCAL_WORLD_ALIGNED);
        std::array<float, 3> v_base = {
            (float)v_frame.linear()[0],
            (float)v_frame.linear()[1],
            (float)v_frame.linear()[2]};

        // Transform position to world frame: p_w = R * p_b + base_pos
        auto p_w = mat3_mul_vec3(R, p_base);
        res.body_pos[b] = {
            p_w[0] + base_pos[0],
            p_w[1] + base_pos[1],
            p_w[2] + base_pos[2]};

        // Transform velocity to world frame:
        // v_w = R * v_b + base_lin_vel + imu_gyro × r
        // where r = body_pos_world - base_pos
        auto v_w = mat3_mul_vec3(R, v_base);
        std::array<float, 3> r = {
            res.body_pos[b][0] - base_pos[0],
            res.body_pos[b][1] - base_pos[1],
            res.body_pos[b][2] - base_pos[2]};
        auto ang_contrib = cross3(imu_gyro, r);

        res.body_lin_vel[b] = {
            v_w[0] + base_lin_vel[0] + ang_contrib[0],
            v_w[1] + base_lin_vel[1] + ang_contrib[1],
            v_w[2] + base_lin_vel[2] + ang_contrib[2]};
    }

    // ---- Root state ----
    res.root_pos     = base_pos;
    res.root_rot     = imu_quat;       // wxyz
    res.root_lin_vel = base_lin_vel;
    res.root_ang_vel = imu_gyro;

    return res;
}

// ---------------------------------------------------------------------------
// Static helpers
// ---------------------------------------------------------------------------

void G1ForwardKinematics::rpy_to_rot_matrix(
    const std::array<float, 3>& rpy,
    float R[3][3])
{
    float roll = rpy[0], pitch = rpy[1], yaw = rpy[2];
    float cr = std::cos(roll),  sr = std::sin(roll);
    float cp = std::cos(pitch), sp = std::sin(pitch);
    float cy = std::cos(yaw),   sy = std::sin(yaw);

    // R = Rz(yaw) * Ry(pitch) * Rx(roll)
    R[0][0] = cy * cp;
    R[0][1] = cy * sp * sr - sy * cr;
    R[0][2] = cy * sp * cr + sy * sr;
    R[1][0] = sy * cp;
    R[1][1] = sy * sp * sr + cy * cr;
    R[1][2] = sy * sp * cr - cy * sr;
    R[2][0] = -sp;
    R[2][1] = cp * sr;
    R[2][2] = cp * cr;
}

std::array<float, 3> G1ForwardKinematics::quat_wxyz_to_rpy(
    const std::array<float, 4>& q)
{
    float qw = q[0], qx = q[1], qy = q[2], qz = q[3];
    float roll  = std::atan2(2.f * (qw * qx + qy * qz),
                             1.f - 2.f * (qx * qx + qy * qy));
    float sinp  = 2.f * (qw * qy - qz * qx);
    sinp        = sinp >  1.f ?  1.f : (sinp < -1.f ? -1.f : sinp);
    float pitch = std::asin(sinp);
    float yaw   = std::atan2(2.f * (qw * qz + qx * qy),
                             1.f - 2.f * (qy * qy + qz * qz));
    return {roll, pitch, yaw};
}

std::array<float, 3> G1ForwardKinematics::cross3(
    const std::array<float, 3>& a,
    const std::array<float, 3>& b)
{
    return {
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]};
}

std::array<float, 3> G1ForwardKinematics::mat3_mul_vec3(
    const float R[3][3],
    const std::array<float, 3>& v)
{
    return {
        R[0][0]*v[0] + R[0][1]*v[1] + R[0][2]*v[2],
        R[1][0]*v[0] + R[1][1]*v[1] + R[1][2]*v[2],
        R[2][0]*v[0] + R[2][1]*v[1] + R[2][2]*v[2]};
}

}  // namespace diffusion_deploy

#endif  // USE_FK
