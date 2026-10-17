/**
 * diffusion_agent.hpp
 *
 * BCAgent equivalent for C++ deployment.
 * Mirrors diffusion_policy/agent/bc_agent.py BCAgent.
 *
 * Responsibilities (matching BCAgent.act()):
 *   1. Normalize obs:  nobs_norm = obs_normalizer.normalize(obs)
 *   2. Normalize cond: cond_norm = cond_normalizer.normalize(cond)   [optional]
 *   3. Forward to actor: action_traj_norm = actor.act(nobs_norm, cond_norm)
 *   4. Unnormalize:    action_traj = action_normalizer.unnormalize(action_traj_norm)
 *
 * The DiffusionAgent does NOT own env or obs_composer — those are managed
 * by EnvRunner.
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include "diffusion_deploy/utils/normalizer.hpp"
#include <memory>
#include <optional>
#include <functional>
#include <utility>

namespace diffusion_deploy {

class DiffusionAgent {
public:
    using TimelineHook = std::function<void(const std::string&)>;
    /**
     * @param actor              Neural network actor (TorchActor or OnnxActor).
     * @param obs_normalizer     Normalizer for raw obs -> [-1,1].
     * @param action_normalizer  Normalizer for normalized action -> raw joints.
     * @param cond_normalizer    Optional normalizer for CLIP conditioning vector.
     */
    DiffusionAgent(std::shared_ptr<BaseActor>    actor,
                   std::shared_ptr<Normalizer>   obs_normalizer,
                   std::shared_ptr<Normalizer>   action_normalizer,
                   std::shared_ptr<Normalizer>   cond_normalizer = nullptr);

    /**
     * Run full inference pipeline: normalize → actor → unnormalize.
     *
     * @param obs   Raw (unnormalized) obs [B, n_obs_steps, obs_dim].
     * @param cond  Optional conditioning [B, 1, cond_dim].
     *              Pass undefined tensor when running unconditionally.
     * @return      Unnormalized action trajectory [B, horizon, action_dim].
     */
    torch::Tensor act(const torch::Tensor& obs,
                      const torch::Tensor& cond = {});

    // Delegation to actor for shape info
    int  n_obs_steps()    const { return actor_->n_obs_steps(); }
    int  n_future_steps() const { return actor_->n_future_steps(); }
    int  horizon()        const { return actor_->horizon(); }
    int  action_dim()     const { return actor_->action_dim(); }
    int  obs_dim()        const { return actor_->obs_dim(); }

    torch::Device device()    const { return actor_->device(); }

    /** Move actor and normalizers to device. */
    void to(torch::Device device);

    /** Reset actor episode-local state (notably PRDP rolling buffers). */
    void reset();

    const std::shared_ptr<BaseActor>&   actor()             const { return actor_; }
    const std::shared_ptr<Normalizer>&  obs_normalizer()    const { return obs_normalizer_; }
    const std::shared_ptr<Normalizer>&  action_normalizer() const { return action_normalizer_; }
    const std::shared_ptr<Normalizer>&  cond_normalizer()   const { return cond_normalizer_; }
    void set_timeline_hook(TimelineHook hook) { timeline_hook_ = std::move(hook); }

private:
    std::shared_ptr<BaseActor>  actor_;
    std::shared_ptr<Normalizer> obs_normalizer_;
    std::shared_ptr<Normalizer> action_normalizer_;
    std::shared_ptr<Normalizer> cond_normalizer_;  // may be nullptr
    TimelineHook timeline_hook_;

    void timeline_mark(const char* name) {
        if (timeline_hook_) timeline_hook_(name);
    }
};

}  // namespace diffusion_deploy
