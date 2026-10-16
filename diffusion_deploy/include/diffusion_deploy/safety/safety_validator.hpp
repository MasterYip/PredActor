/**
 * safety_validator.hpp
 *
 * Stateless safety checks for the humanoid robot.
 *
 *   - projected_gravity()   : compute gravity direction in body frame from IMU
 *                             quaternion. Identical to the formula in
 *                             UnitreeEnv::compute_projected_gravity().
 *   - bad_orientation()     : true when the robot has tilted past the safe
 *                             threshold (default 1.0 rad ~ 57 deg).
 *
 * Mirrors the reference isaaclab::mdp::bad_orientation() in
 *   temp/deploy/include/isaaclab/envs/mdp/terminations.h
 */
#pragma once

#include <array>
#include <cmath>

namespace diffusion_deploy {
namespace safety {

/**
 * Compute projected gravity in the robot's body frame.
 *
 * @param quat_wxyz  IMU quaternion [w, x, y, z] (Hamilton convention,
 *                   same as Unitree SDK and IsaacLab).
 * @return           Gravity vector in body frame [gx, gy, gz].
 *                   Upright → approx {0, 0, -1}.
 */
inline std::array<float, 3> projected_gravity(const std::array<float, 4>& quat_wxyz) {
    float qw = quat_wxyz[0], qx = quat_wxyz[1],
          qy = quat_wxyz[2], qz = quat_wxyz[3];
    return {
         2.f * (-qz * qx + qw * qy),
        -2.f * ( qz * qy + qw * qx),
         1.f - 2.f * (qw * qw + qz * qz)
    };
}

/**
 * Check whether the robot has tilted too far from upright.
 *
 * Uses the body-frame z-component of projected gravity:
 *   tilt_angle = |acos(-projected_gravity_z)|
 *
 * @param projected_gravity_z  Body-frame z component of projected gravity.
 *                             Upright = -1.0, upside-down = +1.0.
 * @param limit_angle_rad      Maximum allowed tilt in radians (default 1.0 ≈ 57°).
 * @return true if the robot is tilted beyond the limit (fall detected).
 */
inline bool bad_orientation(float projected_gravity_z, float limit_angle_rad = 1.0f) {
    // Clamp to [-1, 1] to avoid NaN from numerical noise
    float clamped = std::fmax(-1.0f, std::fmin(1.0f, -projected_gravity_z));
    return std::fabs(std::acos(clamped)) > limit_angle_rad;
}

/**
 * Check orientation from the full projected gravity vector.
 * Convenience overload that computes the angle internally.
 */
inline bool bad_orientation(const std::array<float, 3>& projected_g,
                            float limit_angle_rad = 1.0f) {
    return bad_orientation(projected_g[2], limit_angle_rad);
}

}  // namespace safety
}  // namespace diffusion_deploy
