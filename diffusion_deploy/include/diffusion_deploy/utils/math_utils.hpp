/**
 * math_utils.hpp
 *
 * Quaternion and rotation utilities used by UnitreeEnv and ObsComposer.
 * All quaternions use (w, x, y, z) convention matching Python traj_utils.
 */
#pragma once

#include <array>
#include <cmath>

namespace diffusion_deploy {
namespace math {

// Rotate vector by quaternion q: v' = q * v * q_conj
inline std::array<float, 3> quat_rotate(
    const std::array<float, 4>& q_wxyz,
    const std::array<float, 3>& v)
{
    float qw = q_wxyz[0], qx = q_wxyz[1], qy = q_wxyz[2], qz = q_wxyz[3];
    float tx = 2.f * (qy * v[2] - qz * v[1]);
    float ty = 2.f * (qz * v[0] - qx * v[2]);
    float tz = 2.f * (qx * v[1] - qy * v[0]);
    return {
        v[0] + qw * tx + qy * tz - qz * ty,
        v[1] + qw * ty + qz * tx - qx * tz,
        v[2] + qw * tz + qx * ty - qy * tx
    };
}

// Rotate vector by inverse (conjugate) of quaternion
inline std::array<float, 3> quat_rotate_inverse(
    const std::array<float, 4>& q_wxyz,
    const std::array<float, 3>& v)
{
    // conjugate = [w, -x, -y, -z]
    std::array<float, 4> qc = {q_wxyz[0], -q_wxyz[1], -q_wxyz[2], -q_wxyz[3]};
    return quat_rotate(qc, v);
}

// Extract yaw angle from quaternion (w,x,y,z)
inline float quat_to_yaw(const std::array<float, 4>& q_wxyz) {
    float qw = q_wxyz[0], qx = q_wxyz[1], qy = q_wxyz[2], qz = q_wxyz[3];
    float siny = 2.f * (qw * qz + qx * qy);
    float cosy = 1.f - 2.f * (qy * qy + qz * qz);
    return std::atan2(siny, cosy);
}

// Build yaw-only quaternion from yaw angle
inline std::array<float, 4> yaw_to_quat(float yaw) {
    float half = yaw * 0.5f;
    return {std::cos(half), 0.f, 0.f, std::sin(half)};
}

// Projected gravity in body frame
// Returns gravity vector rotated into body frame via quat (w,x,y,z)
inline std::array<float, 3> projected_gravity(const std::array<float, 4>& q_wxyz) {
    float qw = q_wxyz[0], qx = q_wxyz[1], qy = q_wxyz[2], qz = q_wxyz[3];
    return {
         2.f * (-qz * qx + qw * qy),
        -2.f * ( qz * qy + qw * qx),
         1.f - 2.f * (qw * qw + qz * qz)
    };
}

// Quaternion multiply: q1 * q2  (both w,x,y,z)
inline std::array<float, 4> quat_mul(
    const std::array<float, 4>& q1,
    const std::array<float, 4>& q2)
{
    float w1=q1[0], x1=q1[1], y1=q1[2], z1=q1[3];
    float w2=q2[0], x2=q2[1], y2=q2[2], z2=q2[3];
    return {
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    };
}

// Normalise quaternion
inline std::array<float, 4> quat_normalize(const std::array<float, 4>& q) {
    float n = std::sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
    if (n < 1e-8f) return {1.f, 0.f, 0.f, 0.f};
    return {q[0]/n, q[1]/n, q[2]/n, q[3]/n};
}

}  // namespace math
}  // namespace diffusion_deploy
