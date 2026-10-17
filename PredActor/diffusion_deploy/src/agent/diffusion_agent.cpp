#include "diffusion_deploy/agent/diffusion_agent.hpp"
#include <ATen/record_function.h>
#include <stdexcept>

namespace diffusion_deploy {

DiffusionAgent::DiffusionAgent(std::shared_ptr<BaseActor>  actor,
                               std::shared_ptr<Normalizer> obs_normalizer,
                               std::shared_ptr<Normalizer> action_normalizer,
                               std::shared_ptr<Normalizer> cond_normalizer)
    : actor_(std::move(actor))
    , obs_normalizer_(std::move(obs_normalizer))
    , action_normalizer_(std::move(action_normalizer))
    , cond_normalizer_(std::move(cond_normalizer))
{
    if (!actor_)             throw std::invalid_argument("DiffusionAgent: actor is null");
    if (!obs_normalizer_)    throw std::invalid_argument("DiffusionAgent: obs_normalizer is null");
    if (!action_normalizer_) throw std::invalid_argument("DiffusionAgent: action_normalizer is null");
}

torch::Tensor DiffusionAgent::act(const torch::Tensor& obs,
                                   const torch::Tensor& cond) {
    RECORD_FUNCTION("task142::agent_total", std::vector<c10::IValue>());
    timeline_mark("agent/start");
    // 1. Normalize obs: [B, n_obs_steps, obs_dim] -> normalized
    torch::Tensor nobs;
    {
        RECORD_FUNCTION("task142::obs_normalize", std::vector<c10::IValue>());
        nobs = obs_normalizer_->normalize(obs);
    }
    auto finite_nobs = torch::isfinite(nobs);
    if (!finite_nobs.all().item<bool>()) {
        auto first_bad = torch::nonzero(torch::logical_not(finite_nobs))[0]
                             .to(torch::kCPU);
        const auto b = first_bad[0].item<int64_t>();
        const auto t = first_bad[1].item<int64_t>();
        const auto d = first_bad[2].item<int64_t>();
        const auto raw = obs.index({b, t, d}).to(torch::kCPU).item<double>();
        const auto scale = obs_normalizer_->scale().index({d}).to(torch::kCPU).item<double>();
        const auto offset = obs_normalizer_->offset().index({d}).to(torch::kCPU).item<double>();
        throw std::runtime_error(
            "DiffusionAgent: nonfinite normalized observation at [" +
            std::to_string(b) + "," + std::to_string(t) + "," +
            std::to_string(d) + "] (raw=" + std::to_string(raw) +
            ", scale=" + std::to_string(scale) +
            ", offset=" + std::to_string(offset) + ")");
    }
    timeline_mark("agent/obs_normalized");

    // 2. Normalize cond (optional)
    torch::Tensor ncond;
    if (cond.defined() && cond.numel() > 0 && cond_normalizer_ != nullptr) {
        RECORD_FUNCTION("task142::condition_normalize", std::vector<c10::IValue>());
        ncond = cond_normalizer_->normalize(cond);
    } else if (cond.defined() && cond.numel() > 0) {
        ncond = cond;  // pass through if no normalizer
    }
    timeline_mark("agent/condition_normalized");

    // 3. Actor inference
    timeline_mark("agent/actor_start");
    auto action_norm = actor_->act(nobs, ncond);
    timeline_mark("agent/actor_end");

    // 4. Unnormalize: normalized action -> raw joint targets
    torch::Tensor action;
    {
        RECORD_FUNCTION("task142::action_unnormalize", std::vector<c10::IValue>());
        action = action_normalizer_->unnormalize(action_norm);
    }
    timeline_mark("agent/end");
    return action;
}

void DiffusionAgent::to(torch::Device device) {
    actor_->to(device);
    obs_normalizer_->to(device);
    action_normalizer_->to(device);
    if (cond_normalizer_) cond_normalizer_->to(device);
}

void DiffusionAgent::reset() {
    actor_->reset();
}

}  // namespace diffusion_deploy
