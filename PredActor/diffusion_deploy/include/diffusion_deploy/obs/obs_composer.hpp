/**
 * obs_composer.hpp
 *
 * Converts raw ObsTerms history into the normalized policy input tensor.
 * Mirrors diffusion_policy/dataset/obs_composer.py ObsComposer.
 *
 * The heavy normalization logic (state_normalize) is implemented per-profile,
 * matching the Python dataset classes:
 *   G1        -> G1_Dataset.state_normalize()      (192-dim)
 *   G1_EE     -> G1_Dataset_EE.state_normalize()   (198-dim)
 *   G1_Q      -> G1_Dataset_Q.state_normalize()    (70-dim)
 *   G1_RLObs  -> G1_Dataset_RLObs.state_normalize() (96-dim)
 *   G1_PRDPStandard2Cond -> g1_prdp_standard2 task condition (93-dim)
 */
#pragma once

#include "diffusion_deploy/obs/obs_terms.hpp"
#include <torch/torch.h>
#include <string>

namespace diffusion_deploy {

enum class ObsProfile {
    G1,       ///< 192-dim body-space (G1_Dataset)
    G1_EE,    ///< 198-dim body + end-effectors (G1_Dataset_EE)
    G1_Q,     ///< 70-dim joint-space (G1_Dataset_Q)
    G1_RLObs, ///< 96-dim RL-style obs (G1_Dataset_RLObs)
    G1_PRDPStandard2Cond, ///< 93-dim PRDP condition without base_lin_vel
};

/** Convert string name to ObsProfile enum. Throws on unknown name. */
ObsProfile obs_profile_from_string(const std::string& name);

/** Returns the expected obs dimension for a given profile. */
int obs_dim_for_profile(ObsProfile profile);

/** Returns true if the profile requires RL-specific terms
 *  (projected_gravity, base_lin_vel, base_ang_vel, last_actions). */
bool profile_requires_rl_terms(ObsProfile profile);

// G1 end-effector body indices (left/right wrist)
// Mirrors G1_Dataset.ee_idxs()
static constexpr int G1_EE_IDXS[2] = {20, 27};  // left_wrist, right_wrist

class ObsComposer {
public:
    /**
     * @param profile      Which obs profile to use.
     * @param n_obs_steps  Number of history steps fed to policy (n_past_steps).
     */
    ObsComposer(ObsProfile profile, int n_obs_steps);

    /**
     * Compose and normalize raw history into policy input tensor.
     * Mirrors ObsComposer.compose() in Python.
     *
     * @param history  ObsTensorMap where each tensor has shape [B, n_obs_steps, ...].
     * @return         Tensor of shape [B, n_obs_steps, obs_dim].
     */
    torch::Tensor compose(const ObsTensorMap& history) const;

    ObsProfile profile()    const { return profile_; }
    int        n_obs_steps() const { return n_obs_steps_; }
    int        nominal_frame_idx() const { return nominal_frame_idx_; }
    int        obs_dim() const { return obs_dim_for_profile(profile_); }

private:
    ObsProfile profile_;
    int n_obs_steps_;
    int nominal_frame_idx_;  // = n_obs_steps - 1

    // ---- Per-profile normalization ----

    /**
     * G1 / G1_EE body-space normalization.
     * Mirrors G1DatasetBase.state_normalize() (192 or 198 dims).
     */
    torch::Tensor normalize_g1(const ObsTensorMap& payload, bool with_ee) const;

    /**
     * G1_Q joint-space normalization (70 dims).
     * Mirrors G1_Dataset_Q.state_normalize().
     */
    torch::Tensor normalize_g1_q(const ObsTensorMap& payload) const;

    /**
     * G1_RLObs normalization (96 dims).
     * [joint_pos(29), joint_vel(29), projected_gravity(3),
     *  base_lin_vel(3), base_ang_vel(3), last_actions(29)]
     */
    torch::Tensor normalize_g1_rlobs(const ObsTensorMap& payload) const;

    /** g1_prdp_standard2 condition normalization (93 dims).
     * [joint_pos(29), joint_vel(29), projected_gravity(3),
     *  base_ang_vel(3), last_actions(29)]
     */
    torch::Tensor normalize_g1_prdp_standard2_cond(
        const ObsTensorMap& payload) const;

    // ---- Shared geometry helpers ----

    /** Extract yaw-only quaternion from root rotation quaternion. */
    static torch::Tensor compute_yaw_quat(const torch::Tensor& root_rot_BHC4);

    /** Rotate 3-vectors by inverse of quaternion (for each B,H,J). */
    static torch::Tensor quat_rotate_inverse(const torch::Tensor& quat_N4,
                                              const torch::Tensor& vec_N3);

    /** box_minus: relative rotation vector between two quaternions. */
    static torch::Tensor box_minus(const torch::Tensor& q1_N4,
                                    const torch::Tensor& q2_N4);
};

}  // namespace diffusion_deploy
