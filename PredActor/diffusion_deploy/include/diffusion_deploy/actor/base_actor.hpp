/**
 * base_actor.hpp
 *
 * Abstract actor interface.
 * Mirrors the Python BaseActor / JointDiffusionActor interface.
 *
 * An actor owns the neural network model and implements the denoising loop.
 * It operates entirely in *normalized* space — the DiffusionAgent wrapper
 * handles normalization/unnormalization of inputs and outputs.
 */
#pragma once

#include <torch/torch.h>
#include <vector>
#include <memory>
#include <string>

namespace diffusion_deploy {

/**
 * Configuration shared by all actor backends.
 * Loaded from YAML config["model"].
 */
struct ActorConfig {
    int obs_dim        = 192;  ///< Policy obs input dimension
    int action_dim     = 29;   ///< Action output dimension
    int cond_dim       = 0;    ///< Conditioning dimension (0 = unconditional)
    int n_obs_steps    = 4;    ///< n_past_steps fed to policy (= n_past_steps in Python)
    int n_future_steps = 16;   ///< Predicted future steps
    int denoising_steps= 100;  ///< Number of DDPM reverse steps

    /** horizon = n_obs_steps + n_future_steps */
    int horizon() const { return n_obs_steps + n_future_steps; }
};

class BaseActor {
public:
    virtual ~BaseActor() = default;

    /**
     * Run inference.
     *
     * @param nobs_norm  Normalised observations [B, n_obs_steps, obs_dim].
     * @param cond_norm  Optional conditioning tensor [B, 1, cond_dim].
     *                   Pass undefined tensor for unconditional inference.
     * @return           Normalised action trajectory [B, horizon, action_dim].
     */
    virtual torch::Tensor act(const torch::Tensor& nobs_norm,
                               const torch::Tensor& cond_norm = {}) = 0;

    virtual int n_obs_steps()     const = 0;
    virtual int n_future_steps()  const = 0;
    virtual int horizon()         const = 0;
    virtual int action_dim()      const = 0;
    virtual int obs_dim()         const = 0;

    virtual torch::Device device() const = 0;

    /** Terminal per-position action noise levels for the active schedule. */
    virtual std::vector<int> terminal_action_noise_levels() const {
        return std::vector<int>(static_cast<size_t>(horizon()), 0);
    }

    /** Configure endpoint-specific terminal denoising for action selection. */
    virtual void configure_action_selection(double /*delay_action_step*/) {}

    /** Move model to device. */
    virtual void to(torch::Device device) = 0;

    /** Reset episode-local state such as rolling diffusion buffers. */
    virtual void reset() {}
};

}  // namespace diffusion_deploy
