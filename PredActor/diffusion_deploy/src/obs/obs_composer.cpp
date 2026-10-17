/**
 * obs_composer.cpp
 *
 * Observation composition and normalization matching Python G1DatasetBase.
 *
 * Key normalization steps for G1 / G1_EE (body-space):
 *   1. Compute yaw quaternion at nominal_frame_idx from root_rot.
 *   2. Normalise body_pos: subtract root XY, rotate to yaw frame.
 *   3. Normalise body_lin_vel: subtract root lin vel, rotate to yaw frame.
 *   4. Normalise root_pos: subtract initial XY, rotate to yaw frame.
 *   5. Normalise root_rot: box_minus from nominal yaw quat.
 *   6. Normalise root_lin_vel, root_ang_vel: rotate to nominal yaw frame.
 *   7. Concatenate everything into [B, H, D].
 *
 * For G1_Q: direct concat [root_pos(3), root_rot(3), root_lin_vel(3),
 *            root_ang_vel(3), joint_pos(29), joint_vel(29)] = 70 dims.
 *
 * For G1_RLObs: direct concat [joint_pos(29), joint_vel(29),
 *            projected_gravity(3), base_lin_vel(3), base_ang_vel(3),
 *            last_actions(29)] = 96 dims.
 *
 * For G1_PRDPStandard2Cond: direct concat [joint_pos(29), joint_vel(29),
 *            projected_gravity(3), base_ang_vel(3), last_actions(29)] = 93 dims.
 */
#include "diffusion_deploy/obs/obs_composer.hpp"
#include <stdexcept>
#include <cmath>
#include <sstream>

namespace diffusion_deploy {

// ---- Free functions ----

ObsProfile obs_profile_from_string(const std::string& name) {
    if (name == "G1")       return ObsProfile::G1;
    if (name == "G1_EE")    return ObsProfile::G1_EE;
    if (name == "G1_Q")     return ObsProfile::G1_Q;
    if (name == "G1_RLObs") return ObsProfile::G1_RLObs;
    if (name == "G1_PRDPStandard2Cond") return ObsProfile::G1_PRDPStandard2Cond;
    throw std::invalid_argument("Unknown ObsProfile: " + name);
}

int obs_dim_for_profile(ObsProfile p) {
    switch (p) {
        case ObsProfile::G1:       return 192;
        case ObsProfile::G1_EE:    return 198;
        case ObsProfile::G1_Q:     return 70;
        case ObsProfile::G1_RLObs: return 96;
        case ObsProfile::G1_PRDPStandard2Cond: return 93;
    }
    return 192;
}

bool profile_requires_rl_terms(ObsProfile p) {
    return p == ObsProfile::G1_RLObs || p == ObsProfile::G1_PRDPStandard2Cond;
}

// ---- Constructor ----

ObsComposer::ObsComposer(ObsProfile profile, int n_obs_steps)
    : profile_(profile)
    , n_obs_steps_(n_obs_steps)
    , nominal_frame_idx_(n_obs_steps - 1)
{}

// ---- compose() ----

torch::Tensor ObsComposer::compose(const ObsTensorMap& history) const {
    // Clone to avoid accidental in-place changes (mirrors Python)
    ObsTensorMap payload;
    for (const auto& [k, v] : history) payload[k] = v.clone();

    switch (profile_) {
        case ObsProfile::G1:
            return normalize_g1(payload, /*with_ee=*/false);
        case ObsProfile::G1_EE:
            return normalize_g1(payload, /*with_ee=*/true);
        case ObsProfile::G1_Q:
            return normalize_g1_q(payload);
        case ObsProfile::G1_RLObs: {
            // Validate RL terms are present
            for (const auto& key : {"projected_gravity", "base_lin_vel",
                                    "base_ang_vel", "last_actions"}) {
                if (!payload.count(key)) {
                    throw std::runtime_error(
                        std::string("ObsComposer(G1_RLObs): missing RL term: ") + key);
                }
            }
            return normalize_g1_rlobs(payload);
        }
        case ObsProfile::G1_PRDPStandard2Cond: {
            for (const auto& key : {"projected_gravity", "base_ang_vel",
                                    "last_actions"}) {
                if (!payload.count(key)) {
                    throw std::runtime_error(
                        std::string("ObsComposer(G1_PRDPStandard2Cond): missing term: ") + key);
                }
            }
            return normalize_g1_prdp_standard2_cond(payload);
        }
    }
    throw std::runtime_error("ObsComposer::compose: unknown profile");
}

// ---- Shared geometry helpers ----

/**
 * Compute yaw-only quaternion from root_rot.
 *
 * root_rot_BHC4: [B, H, 4]  quaternion (w, x, y, z)
 * Returns:       [B, H, 4]  yaw quaternion
 *
 * Mirrors G1DatasetBase._compute_yaw_frame().
 */
torch::Tensor ObsComposer::compute_yaw_quat(const torch::Tensor& root_rot_BHC4) {
    // Flatten to [N, 4]
    auto N = root_rot_BHC4.size(0) * root_rot_BHC4.size(1);
    auto q = root_rot_BHC4.reshape({N, 4}).to(torch::kFloat64);

    auto qw = q.select(1, 0);
    auto qx = q.select(1, 1);
    auto qy = q.select(1, 2);
    auto qz = q.select(1, 3);

    // Extract yaw from quaternion
    // yaw = atan2(2*(qw*qz + qx*qy), 1 - 2*(qy*qy + qz*qz))
    auto siny = 2.0 * (qw * qz + qx * qy);
    auto cosy = 1.0 - 2.0 * (qy * qy + qz * qz);
    auto yaw  = torch::atan2(siny, cosy);  // [N]

    // Build yaw-only quat: q = [cos(yaw/2), 0, 0, sin(yaw/2)]
    auto half_yaw = yaw / 2.0;
    auto yaw_quat = torch::stack({
        torch::cos(half_yaw),    // w
        torch::zeros_like(half_yaw),  // x
        torch::zeros_like(half_yaw),  // y
        torch::sin(half_yaw)     // z
    }, /*dim=*/1);  // [N, 4]

    return yaw_quat.reshape(root_rot_BHC4.sizes());
}

/**
 * Rotate 3-vectors by the inverse (conjugate) of quaternion.
 *
 * quat_N4: [N, 4]  (w, x, y, z)
 * vec_N3:  [N, 3]
 * returns: [N, 3]
 *
 * Formula: v_rot = v - 2*w*(q×v) + 2*(q×(q×v))
 * (Hamilton product with q_conj = [w, -x, -y, -z])
 */
torch::Tensor ObsComposer::quat_rotate_inverse(const torch::Tensor& quat_N4,
                                                const torch::Tensor& vec_N3) {
    auto qw = quat_N4.select(1, 0).unsqueeze(1);  // [N,1]
    auto qx = quat_N4.select(1, 1);
    auto qy = quat_N4.select(1, 2);
    auto qz = quat_N4.select(1, 3);
    // conjugate
    auto q_xyz = torch::stack({-qx, -qy, -qz}, 1);  // [N,3]

    auto t = 2.0 * at::linalg_cross(q_xyz, vec_N3, /*dim=*/1);  // [N,3]
    return vec_N3 + qw * t + at::linalg_cross(q_xyz, t, /*dim=*/1);
}

/**
 * box_minus: rotation vector q1 "relative to" q2.
 *
 * Returns a 3-dim rotation vector (axis * angle) such that
 * q2 * exp(result/2) ≈ q1.
 *
 * Mirrors traj_utils.box_minus() in Python.
 * Simplified: result = log(q2_conj * q1) * 2
 */
torch::Tensor ObsComposer::box_minus(const torch::Tensor& q1_N4,
                                      const torch::Tensor& q2_N4) {
    // q_rel = q2_conj * q1
    auto qw2 =  q2_N4.select(1, 0);
    auto qx2 = -q2_N4.select(1, 1);
    auto qy2 = -q2_N4.select(1, 2);
    auto qz2 = -q2_N4.select(1, 3);

    auto qw1 = q1_N4.select(1, 0);
    auto qx1 = q1_N4.select(1, 1);
    auto qy1 = q1_N4.select(1, 2);
    auto qz1 = q1_N4.select(1, 3);

    // Hamilton product q2_conj * q1
    auto rw = qw2*qw1 - qx2*qx1 - qy2*qy1 - qz2*qz1;
    auto rx = qw2*qx1 + qx2*qw1 + qy2*qz1 - qz2*qy1;
    auto ry = qw2*qy1 - qx2*qz1 + qy2*qw1 + qz2*qx1;
    auto rz = qw2*qz1 + qx2*qy1 - qy2*qx1 + qz2*qw1;

    // Normalise rw to [-1,1] for acos
    rw = rw.clamp(-1.0, 1.0);
    auto angle = 2.0 * torch::acos(rw.abs());  // [N]
    auto sin_half = torch::sqrt(torch::clamp(1.0 - rw * rw, 0.0));
    auto eps = 1e-8;
    auto safe_sin = sin_half.clamp(eps);

    auto axis_x = rx / safe_sin;
    auto axis_y = ry / safe_sin;
    auto axis_z = rz / safe_sin;

    return torch::stack({axis_x * angle, axis_y * angle, axis_z * angle}, 1); // [N,3]
}

// ---- normalize_g1() ----

torch::Tensor ObsComposer::normalize_g1(const ObsTensorMap& p, bool with_ee) const {
    // All tensors cast to float64 for arithmetic precision (matches Python double)
    auto dtype = torch::kFloat64;

    auto root_pos_frame = p.at("root_pos").to(dtype);        // [B,H,3]
    auto root_rot_frame = p.at("root_rot").to(dtype);        // [B,H,4]
    auto body_pos       = p.at("body_pos").to(dtype);        // [B,H,30,3]
    auto body_lin_vel   = p.at("body_lin_vel").to(dtype);    // [B,H,30,3]
    auto joint_pos      = p.at("joint_pos").to(dtype);       // [B,H,29]

    int64_t B = root_pos_frame.size(0);
    int64_t H = root_pos_frame.size(1);
    int64_t J = body_pos.size(2);  // 30

    // 1. Yaw quaternion [B, H, 4]
    auto yaw_quat = compute_yaw_quat(root_rot_frame);  // [B,H,4]

    // 2. Normalise body positions
    //    body_pos[:,:,:,:2] -= root_pos_frame[:,:,None,:2]
    auto body_pos_n = body_pos.clone();
    body_pos_n.index_put_(
        {torch::indexing::Slice(), torch::indexing::Slice(),
         torch::indexing::Slice(), torch::indexing::Slice(0,2)},
        body_pos.index({torch::indexing::Slice(), torch::indexing::Slice(),
                        torch::indexing::Slice(), torch::indexing::Slice(0,2)})
        - root_pos_frame.index({torch::indexing::Slice(), torch::indexing::Slice(),
                                torch::indexing::None, torch::indexing::Slice(0,2)})
    );
    // Rotate to yaw frame
    auto yq_expanded = yaw_quat.unsqueeze(2).expand({B,H,J,4}).reshape({B*H*J, 4});
    auto bp_flat     = body_pos_n.reshape({B*H*J, 3});
    auto body_pos_local = quat_rotate_inverse(yq_expanded, bp_flat).reshape({B,H,J,3});

    // 3. Normalise body linear velocities
    auto root_lin_vel = body_lin_vel.index(
        {torch::indexing::Slice(), torch::indexing::Slice(), 0,
         torch::indexing::Slice()});  // [B,H,3]
    auto body_vel_n   = body_lin_vel - root_lin_vel.unsqueeze(2);  // [B,H,J,3]
    auto bv_flat      = body_vel_n.reshape({B*H*J, 3});
    auto body_vel_local = quat_rotate_inverse(yq_expanded, bv_flat).reshape({B,H,J,3});

    // Root lin vel in nominal yaw frame
    auto yq_nominal_rep = yaw_quat.index(
        {torch::indexing::Slice(),
         torch::indexing::Slice(nominal_frame_idx_, nominal_frame_idx_+1),
         torch::indexing::Slice()})
        .expand({B,H,4}).reshape({B*H, 4});
    auto rlv_flat = root_lin_vel.reshape({B*H, 3});
    auto root_lin_vel_local = quat_rotate_inverse(yq_nominal_rep, rlv_flat).reshape({B,H,3});

    // Root ang vel in nominal yaw frame
    auto body_ang_vel = p.at("body_ang_vel").to(dtype);  // [B,H,30,3]
    auto root_ang_vel = body_ang_vel.index(
        {torch::indexing::Slice(), torch::indexing::Slice(), 0,
         torch::indexing::Slice()});  // [B,H,3]
    auto rav_flat = root_ang_vel.reshape({B*H, 3});
    auto root_ang_vel_local = quat_rotate_inverse(yq_nominal_rep, rav_flat).reshape({B,H,3});

    // 4. Normalise root position
    auto root_pos_init = root_pos_frame.index(
        {torch::indexing::Slice(), nominal_frame_idx_, torch::indexing::Slice()})
        .unsqueeze(1);  // [B,1,3]
    auto root_pos_n = root_pos_frame.clone();
    root_pos_n.index_put_(
        {torch::indexing::Slice(), torch::indexing::Slice(), torch::indexing::Slice(0,2)},
        root_pos_frame.index({torch::indexing::Slice(), torch::indexing::Slice(),
                              torch::indexing::Slice(0,2)})
        - root_pos_init.index({torch::indexing::Slice(), torch::indexing::Slice(),
                               torch::indexing::Slice(0,2)}));
    auto rp_flat        = root_pos_n.reshape({B*H, 3});
    auto root_pos_local = quat_rotate_inverse(yq_nominal_rep, rp_flat).reshape({B,H,3});

    // 5. Normalise root rotation (box_minus)
    auto yq_nom_rep_BH = yaw_quat.index(
        {torch::indexing::Slice(),
         torch::indexing::Slice(nominal_frame_idx_, nominal_frame_idx_+1),
         torch::indexing::Slice()})
        .expand({B,H,4}).reshape({B*H, 4});
    auto rr_flat        = root_rot_frame.reshape({B*H, 4});
    auto root_rot_local = box_minus(rr_flat, yq_nom_rep_BH).reshape({B,H,3});

    // 6. Concatenate body_pos_local [B,H,90], body_vel_local [B,H,90],
    //    root_pos_local [B,H,3], root_rot_local [B,H,3],
    //    root_lin_vel_local [B,H,3], root_ang_vel_local [B,H,3]  -> 192 dims
    auto bp_out  = body_pos_local.reshape({B, H, J*3});   // [B,H,90]
    auto bv_out  = body_vel_local.reshape({B, H, J*3});   // [B,H,90]

    std::vector<torch::Tensor> parts = {
        bp_out,           // [B,H,90]
        bv_out,           // [B,H,90]
        root_pos_local,   // [B,H,3]
        root_rot_local,   // [B,H,3]
        root_lin_vel_local, // [B,H,3]
        root_ang_vel_local  // [B,H,3]
    };

    if (with_ee) {
        // G1_EE: append 2 ee body rotations (6 dims from quaternion components)
        // Use body_rot if available, else zeros
        torch::Tensor body_rot;
        auto it = p.find("body_rot");
        if (it != p.end() && it->second.defined()) {
            body_rot = it->second.to(dtype);
        } else {
            body_rot = torch::zeros({B,H,J,4}, dtype);
        }
        // Take indices [20, 27] (left/right wrist), use first 3 components (xyz of quat)
        auto ee_rot_0 = body_rot.index(
            {torch::indexing::Slice(), torch::indexing::Slice(),
             G1_EE_IDXS[0], torch::indexing::Slice(1,4)});  // [B,H,3]
        auto ee_rot_1 = body_rot.index(
            {torch::indexing::Slice(), torch::indexing::Slice(),
             G1_EE_IDXS[1], torch::indexing::Slice(1,4)});  // [B,H,3]
        parts.push_back(ee_rot_0);
        parts.push_back(ee_rot_1);
    }

    return torch::cat(parts, /*dim=*/2).to(torch::kFloat32);
}

// ---- normalize_g1_q() ----

torch::Tensor ObsComposer::normalize_g1_q(const ObsTensorMap& p) const {
    auto dtype = torch::kFloat64;

    auto root_pos  = p.at("root_pos").to(dtype);   // [B,H,3]
    auto root_rot  = p.at("root_rot").to(dtype);   // [B,H,4]
    auto joint_pos = p.at("joint_pos").to(dtype);  // [B,H,29]

    int64_t B = root_pos.size(0);
    int64_t H = root_pos.size(1);

    // Compute root linear / angular velocity from body terms if available
    torch::Tensor root_lin_vel, root_ang_vel;
    auto blv_it = p.find("base_lin_vel");
    auto bav_it = p.find("base_ang_vel");
    if (blv_it != p.end() && blv_it->second.defined()) {
        root_lin_vel = blv_it->second.to(dtype);  // [B,H,3]
    } else {
        root_lin_vel = torch::zeros({B,H,3}, dtype);
    }
    if (bav_it != p.end() && bav_it->second.defined()) {
        root_ang_vel = bav_it->second.to(dtype);  // [B,H,3]
    } else {
        root_ang_vel = torch::zeros({B,H,3}, dtype);
    }

    // Yaw frame normalization for root pose
    auto yaw_quat   = compute_yaw_quat(root_rot);  // [B,H,4]
    auto yq_nom_rep = yaw_quat.index(
        {torch::indexing::Slice(),
         torch::indexing::Slice(nominal_frame_idx_, nominal_frame_idx_+1),
         torch::indexing::Slice()})
        .expand({B,H,4}).reshape({B*H, 4});

    // root_pos local
    auto root_pos_init = root_pos.index(
        {torch::indexing::Slice(), nominal_frame_idx_, torch::indexing::Slice()})
        .unsqueeze(1);
    auto root_pos_n = root_pos.clone();
    root_pos_n.index_put_(
        {torch::indexing::Slice(), torch::indexing::Slice(), torch::indexing::Slice(0,2)},
        root_pos.index({torch::indexing::Slice(), torch::indexing::Slice(),
                       torch::indexing::Slice(0,2)})
        - root_pos_init.index({torch::indexing::Slice(), torch::indexing::Slice(),
                               torch::indexing::Slice(0,2)}));
    auto root_pos_local = quat_rotate_inverse(yq_nom_rep, root_pos_n.reshape({B*H,3}))
                          .reshape({B,H,3});

    // root_rot local (box_minus)
    auto yq_nom_rep_BH = yq_nom_rep;
    auto root_rot_local = box_minus(root_rot.reshape({B*H,4}), yq_nom_rep_BH).reshape({B,H,3});

    // velocities in nominal yaw frame
    auto rlinv_local = quat_rotate_inverse(yq_nom_rep, root_lin_vel.reshape({B*H,3}))
                       .reshape({B,H,3});
    auto rangv_local = quat_rotate_inverse(yq_nom_rep, root_ang_vel.reshape({B*H,3}))
                       .reshape({B,H,3});

    // joint_vel (optional)
    torch::Tensor joint_vel;
    auto jv_it = p.find("joint_vel");
    if (jv_it != p.end() && jv_it->second.defined()) {
        joint_vel = jv_it->second.to(dtype);
    } else {
        joint_vel = torch::zeros({B,H,29}, dtype);
    }

    // Concatenate: [root_pos(3), root_rot(3), root_lin_vel(3), root_ang_vel(3),
    //               joint_pos(29), joint_vel(29)] = 70
    return torch::cat({root_pos_local, root_rot_local, rlinv_local, rangv_local,
                       joint_pos, joint_vel}, /*dim=*/2)
           .to(torch::kFloat32);
}

// ---- normalize_g1_rlobs() ----

torch::Tensor ObsComposer::normalize_g1_rlobs(const ObsTensorMap& p) const {
    auto dtype = torch::kFloat64;

    auto joint_pos        = p.at("joint_pos").to(dtype);        // [B,H,29]
    auto joint_vel        = p.at("joint_vel").to(dtype);        // [B,H,29]
    auto projected_gravity= p.at("projected_gravity").to(dtype);// [B,H,3]
    auto base_lin_vel     = p.at("base_lin_vel").to(dtype);     // [B,H,3]
    auto base_ang_vel     = p.at("base_ang_vel").to(dtype);     // [B,H,3]
    auto last_actions     = p.at("last_actions").to(dtype);     // [B,H,29]

    // Direct concatenation — no yaw-frame transformation needed for RLObs.
    // [joint_pos(29), joint_vel(29), projected_gravity(3),
    //  base_lin_vel(3), base_ang_vel(3), last_actions(29)] = 96
    return torch::cat({joint_pos, joint_vel, projected_gravity,
                       base_lin_vel, base_ang_vel, last_actions}, /*dim=*/2)
           .to(torch::kFloat32);
}

torch::Tensor ObsComposer::normalize_g1_prdp_standard2_cond(
    const ObsTensorMap& p) const {
    auto dtype = torch::kFloat64;
    auto joint_pos         = p.at("joint_pos").to(dtype);
    auto joint_vel         = p.at("joint_vel").to(dtype);
    auto projected_gravity = p.at("projected_gravity").to(dtype);
    auto base_ang_vel      = p.at("base_ang_vel").to(dtype);
    auto last_actions      = p.at("last_actions").to(dtype);

    return torch::cat({joint_pos, joint_vel, projected_gravity,
                       base_ang_vel, last_actions}, /*dim=*/2)
           .to(torch::kFloat32);
}

}  // namespace diffusion_deploy
