/**
 * base_env.hpp
 *
 * Abstract environment interface.
 * Mirrors diffusion_policy/env/base_env.py BaseEnv class.
 */
#pragma once

#include "diffusion_deploy/obs/obs_terms.hpp"
#include <torch/torch.h>
#include <optional>
#include <tuple>
#include <unordered_map>

namespace diffusion_deploy {

/**
 * Return type of step(): (obs, reward, done, info_dict).
 * obs is nullptr when the env does not return observation on step
 * (e.g. UnitreeEnv — call get_obs_terms() separately).
 */
struct StepResult {
    ObsTerms obs;               // may be empty if env returns obs separately
    float    reward  = 0.0f;
    bool     done    = false;
    std::unordered_map<std::string, float> info;
};

class BaseEnv {
public:
    virtual ~BaseEnv() = default;

    /** Initialize hardware/simulation connections. Must be called before step(). */
    virtual void initialize() = 0;

    /** Release all resources. */
    virtual void close() = 0;

    /** Reset environment to initial state. */
    virtual void reset() = 0;

    /**
     * Execute one control step.
     *
     * @param action   Joint position targets [num_dof], assumed IsaacLab order.
     */
    virtual StepResult step(const torch::Tensor& action) = 0;

    /**
     * Return current raw observation terms (T=1 snapshot).
     *
     * @param last_actions  Last executed actions [num_dof] passed back as a
     *                      term so G1_RLObs profiles can include them.
     *                      Pass an undefined tensor to use zeros.
     */
    virtual ObsTerms get_obs_terms(const torch::Tensor& last_actions = {}) = 0;

    /** True while the environment is in a runnable state. */
    virtual bool is_running() const { return true; }

    /** Control timestep in seconds (nullptr-equivalent = not enforced). */
    virtual std::optional<double> get_step_dt() const { return std::nullopt; }
};

}  // namespace diffusion_deploy
