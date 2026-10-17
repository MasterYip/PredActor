/**
 * base_agent.hpp
 *
 * Abstract agent interface.
 * Mirrors diffusion_policy/agent/base_agent.py BaseAgent.
 *
 * An agent wraps an actor and a normalizer.
 * DiffusionAgent is the concrete implementation used for deployment.
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include "diffusion_deploy/utils/normalizer.hpp"
#include <torch/torch.h>
#include <memory>

namespace diffusion_deploy {

class BaseAgent {
public:
    virtual ~BaseAgent() = default;

    /**
     * Run inference.
     * @param obs   Raw (unnormalized) observations [B, n_obs_steps, obs_dim].
     * @param cond  Optional conditioning [B, 1, cond_dim].
     * @return      Unnormalized action trajectory [B, horizon, action_dim].
     */
    virtual torch::Tensor act(const torch::Tensor& obs,
                              const torch::Tensor& cond = {}) = 0;

    virtual int  n_obs_steps()    const = 0;
    virtual int  horizon()        const = 0;
    virtual int  action_dim()     const = 0;
    virtual torch::Device device() const = 0;

    virtual void to(torch::Device device) = 0;
};

}  // namespace diffusion_deploy
