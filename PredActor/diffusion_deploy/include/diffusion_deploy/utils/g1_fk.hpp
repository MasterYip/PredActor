/**
 * g1_fk.hpp
 *
 * G1 Robot Forward Kinematics using Pinocchio.
 * Mirrors diffusion_policy/utils/g1fk_pinocchio.py.
 *
 * Only compiled when -DUSE_FK=ON (pinocchio::pinocchio linked).
 *
 * Usage:
 *   G1ForwardKinematics fk("/path/to/g1.urdf");
 *   FKResult res = fk.compute(joint_pos_il, joint_vel_il, imu_quat, imu_gyro,
 *                              base_lin_vel, base_pos, isaaclab_order=true);
 *   // res.body_pos[i]     : world-frame position of body i  (30 × 3)
 *   // res.body_lin_vel[i] : world-frame linear velocity     (30 × 3)
 *   // res.root_pos        : base position [3]
 *   // res.root_rot        : quaternion wxyz [4]
 *   // res.root_lin_vel    : world-frame base linear velocity [3]
 *   // res.root_ang_vel    : body-frame angular velocity (IMU gyro) [3]
 */
#pragma once

#ifdef USE_FK

#include <array>
#include <string>
#include <vector>

#include <pinocchio/multibody/model.hpp>
#include <pinocchio/multibody/data.hpp>

namespace diffusion_deploy {

// ---------------------------------------------------------------------------
// FKResult — output of one FK call
// ---------------------------------------------------------------------------

struct FKResult {
    // World-frame positions for each of the 30 G1 bodies (IsaacLab body order).
    std::vector<std::array<float, 3>> body_pos;      // [30][3]
    std::vector<std::array<float, 3>> body_lin_vel;  // [30][3]

    std::array<float, 3> root_pos     = {0, 0, 0};
    std::array<float, 4> root_rot     = {1, 0, 0, 0};  // wxyz
    std::array<float, 3> root_lin_vel = {0, 0, 0};
    std::array<float, 3> root_ang_vel = {0, 0, 0};
};

// ---------------------------------------------------------------------------
// G1ForwardKinematics
// ---------------------------------------------------------------------------

class G1ForwardKinematics {
public:
    /**
     * Load URDF and build Pinocchio model.
     * Throws std::runtime_error if a required body/joint is missing.
     */
    explicit G1ForwardKinematics(const std::string& urdf_path);

    /**
     * Compute forward kinematics.
     *
     * @param joint_pos    29 joint positions. When isaaclab_order=true these are
     *                     in IsaacLab (alphabetical) order; otherwise Pinocchio
     *                     URDF-tree order.
     * @param joint_vel    29 joint velocities (same order as joint_pos).
     * @param imu_quat     IMU quaternion (w, x, y, z) — world-frame orientation.
     * @param imu_gyro     IMU angular velocity (body frame) [3].
     * @param base_lin_vel Base linear velocity in world frame [3].
     *                     Pass {0,0,0} if not available.
     * @param base_pos     Base position in world frame [3].
     *                     Pass {0,0,0} if not available.
     * @param isaaclab_order  When true joint_pos/vel are in IsaacLab order and
     *                        will be remapped before calling Pinocchio.
     */
    FKResult compute(
        const std::vector<float>& joint_pos,
        const std::vector<float>& joint_vel,
        const std::array<float, 4>& imu_quat,    // wxyz
        const std::array<float, 3>& imu_gyro,
        const std::array<float, 3>& base_lin_vel,
        const std::array<float, 3>& base_pos,
        bool isaaclab_order = true
    ) const;

private:
    pinocchio::Model model_;
    mutable pinocchio::Data data_;   // mutable: algorithms write here (const iface)

    // Frame IDs for the 30 G1 bodies (in ISAACLAB_BODY_NAMES order).
    std::vector<pinocchio::FrameIndex> body_frame_ids_;

    // joint_remapping_[pinocchio_idx] = isaaclab_idx
    // Reorders IsaacLab joint array to Pinocchio URDF-tree order.
    std::vector<int> joint_remapping_;  // length 29

    // ---- helpers ----

    /** Build 3×3 rotation matrix from roll-pitch-yaw (ZYX convention). */
    static void rpy_to_rot_matrix(
        const std::array<float, 3>& rpy,
        float R[3][3]);

    /** Convert quaternion wxyz to roll-pitch-yaw. */
    static std::array<float, 3> quat_wxyz_to_rpy(
        const std::array<float, 4>& q);

    /** Cross product a × b. */
    static std::array<float, 3> cross3(
        const std::array<float, 3>& a,
        const std::array<float, 3>& b);

    /** Rotate v by 3×3 matrix R: result = R * v. */
    static std::array<float, 3> mat3_mul_vec3(
        const float R[3][3],
        const std::array<float, 3>& v);
};

}  // namespace diffusion_deploy

#endif  // USE_FK
