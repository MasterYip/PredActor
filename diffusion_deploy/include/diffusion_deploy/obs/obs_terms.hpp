/**
 * obs_terms.hpp
 *
 * Container for raw observation terms produced by UnitreeEnv::get_obs_terms().
 * Mirrors the Python ObsTerms = Dict[str, torch.Tensor] used throughout
 * the diffusion_policy package.
 *
 * All tensors have shape [B, T, ...] where:
 *   B = batch size (1 for single-robot deployment)
 *   T = time steps (T=1 when freshly returned from get_obs_terms();
 *       temporal stacking is handled by ObsHistory)
 */
#pragma once

#include <string>
#include <unordered_map>
#include <torch/torch.h>

namespace diffusion_deploy {

/**
 * Raw observation terms from the environment.
 *
 * Layout matches what Python UnitreeG1Env.get_fk_observation() returns.
 * All tensors use torch::kFloat64 to match Python double tensors.
 *
 * When returned from get_obs_terms(), every tensor has T=1 (single timestep).
 * ObsHistory accumulates them into shape [B, n_obs_steps, ...].
 */
struct ObsTerms {
    // [B, T, 30, 3]  body positions in character frame
    torch::Tensor body_pos;
    // [B, T, 30, 4]  body rotations (quaternion w,x,y,z) in character frame
    torch::Tensor body_rot;
    // [B, T, 30, 3]  body linear velocities
    torch::Tensor body_lin_vel;
    // [B, T, 30, 3]  body angular velocities (root at index 0)
    torch::Tensor body_ang_vel;
    // [B, T, 3]      root position in nominal frame
    torch::Tensor root_pos;
    // [B, T, 4]      root rotation quaternion (w,x,y,z) in nominal frame
    torch::Tensor root_rot;
    // [B, T, 29]     joint positions (IsaacLab joint order)
    torch::Tensor joint_pos;
    // [B, T, 29]     joint velocities (IsaacLab joint order)
    torch::Tensor joint_vel;

    // RL-specific terms (required for G1_RLObs obs profile)
    // [B, T, 3]  gravity vector projected into body frame
    torch::Tensor projected_gravity;
    // [B, T, 3]  base linear velocity in body frame
    torch::Tensor base_lin_vel;
    // [B, T, 3]  base angular velocity in body frame
    torch::Tensor base_ang_vel;
    // [B, T, 29] last executed actions
    torch::Tensor last_actions;
};

/**
 * Convert an ObsTerms struct to an unordered_map<string, Tensor>.
 * The map keys match those expected by ObsComposer::compose().
 *
 * Only populated (non-undefined) tensors are included.
 */
using ObsTensorMap = std::unordered_map<std::string, torch::Tensor>;

ObsTensorMap obs_terms_to_map(const ObsTerms& terms);

/**
 * Reconstruct an ObsTerms struct from a map.
 * Missing keys result in undefined tensors (ObsTerms fields default to
 * torch::Tensor{} which evaluates to false with .defined()).
 */
ObsTerms obs_terms_from_map(const ObsTensorMap& map);

}  // namespace diffusion_deploy
