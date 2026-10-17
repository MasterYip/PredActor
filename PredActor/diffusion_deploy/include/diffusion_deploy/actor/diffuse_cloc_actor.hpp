/**
 * diffuse_cloc_actor.hpp
 *
 * C++ reimplementation of DiffuseCLoC (diffuse_cloc.py).
 * Extends JointDiffusionActor with:
 *
 *   1. State emphasis projection
 *      nobs_emph = nobs @ emphasis_mat
 *      state_traj_emph = state_traj @ emphasis_mat
 *      output state_traj = state_traj_emph @ emphasis_mat_inv
 *
 *   2. Custom noise schedules (generate_denoising_matrix)
 *      - "full"                 : K steps, each position gets the same global t
 *      - "full_decreasing"      : K+n_future steps, decreasing triangle pattern
 *      - "from_xT_decreasing"   : shorter warm-start version
 *      - "from_xT_step"         : coarse stepping (start=14, step_size=10)
 *
 *   3. Rolling inference buffer (FIFO)
 *      Between calls, partially-denoised trajectories are cached and
 *      re-used as warm starts for the next step.
 *
 * Export
 * ------
 * Run export_policy.py --mode backbone to produce:
 *   models/g1_policy_backbone.pt     — TorchScript JointSeqBackbone
 *   models/ddpm_schedule.pt          — DDPM schedule tensors
 *   models/emphasis_matrices.pt      — emphasis_mat + emphasis_mat_inv
 *   models/<deploy_config>.yaml      — C++ deploy config (actor hyper-parameters
 *                                      live in the model: block)
 */
#pragma once

#include "diffusion_deploy/actor/joint_diffusion_actor.hpp"
#include "diffusion_deploy/guidance/whole_body_guidance.hpp"
#include <string>
#include <vector>

namespace diffusion_deploy {

/**
 * Config for DiffuseCLoCActor (superset of JointDiffusionActorConfig).
 */
struct DiffuseCLoCActorConfig : public JointDiffusionActorConfig {
    // Noise-schedule names (match Python attribute names)
    std::string action_schedule = "from_xT_decreasing";
    std::string state_schedule  = "from_xT_step";
    std::string state_emphasis  = "same";
    // sampler_mode selects the denoising loop:
    //   "rolling_ddpm"  -> rolling DDPM (ddim_steps == 0)
    //   "scalar_ddim"   -> uniform-t scalar DDIM (ddim_steps > 0, option c)
    //   "ns_ddim"       -> per-position NS DDIM (ddim_steps > 0, option a)
    //   "rolling_ddim"  -> per-position rolling DDIM (ddim_steps > 0, option b)
    std::string sampler_mode    = "rolling_ddpm";

    // Python-faithful flags (parsed for provenance/consistency; the dispatch is
    // sampler_mode-driven in act()).
    bool use_ns_ddim = false;             ///< option (a) per-position NS DDIM
    bool randomize_noise_schedule = true; ///< option (b) rolling per-position DDIM
    // One x0 prediction is the production classifier-guidance contract.
    // duplicate_backbone remains only for explicit historical replay.
    std::string classifier_guidance_impl = "reuse_x0";

    // Path to emphasis_matrices.pt (saved by export_policy.py)
    std::string emphasis_path;
    WholeBodyGuidanceConfig guidance;
};

/**
 * DiffuseCLoCActor — rolling-inference joint diffusion with state emphasis.
 *
 * Mirrors Python DiffuseCLoC.act().
 *
 * Thread-safety: NOT thread-safe (rolling buffer is mutated in act()).
 */
class DiffuseCLoCActor : public JointDiffusionActor {
public:
    /**
     * @param backbone_path   Path to TorchScript backbone (.pt).
     * @param schedule_path   Path to DDPM schedule tensors.
     * @param emphasis_path   Path to emphasis_matrices.pt.
     * @param config          Actor hyper-parameters.
     * @param device          Inference device.
     */
    DiffuseCLoCActor(const std::string& backbone_path,
                     const std::string& schedule_path,
                     const std::string& emphasis_path,
                     const DiffuseCLoCActorConfig& config,
                     torch::Device device = torch::kCPU);

    /**
     * Run rolling DDPM inference with state emphasis.
     *
     * @param nobs_norm  Normalised obs [B, n_obs_steps, obs_dim].
     * @param cond_norm  Optional motion cond [B, 1, motion_dim].
     * @return           Normalised action trajectory [B, horizon, action_dim].
     */
    torch::Tensor act(const torch::Tensor& nobs_norm,
                       const torch::Tensor& cond_norm = {}) override;

    /**
     * Reset the rolling inference buffer.
     * Call between episodes / resets.
     */
    void reset_rolling();
    void reset() override { reset_rolling(); }

    std::vector<int> terminal_action_noise_levels() const override;
    void configure_action_selection(double delay_action_step) override;

    /** Return the exact native timestep matrix for replay/provenance tests. */
    torch::Tensor denoising_schedule(const std::string& schedule,
                                     bool is_state = false) const {
        return generate_denoising_matrix(schedule, is_state);
    }

    /**
     * Apply a live WBG UDP frame (interactive whole-body guidance).
     * Overrides only per-axis enabled/command/kp; no-op if WBG is not
     * configured (guidance_ is null).
     */
    /** Apply a live WBG command directly in process. */
    void apply_live_wbg(const WbgUdpFrame& frame);

    /** Set unified-command WBG limits; legacy UDP keeps no implicit limit. */
    void set_live_wbg_command_bounds(float max_vx, float max_vy, float max_wz);

    /** Backward-compatible UDP-named wrapper. */
    void apply_live_wbg_udp(const WbgUdpFrame& frame) { apply_live_wbg(frame); }

    /** True if this actor carries a WBG instance (WBG enabled at load). */
    bool wbg_enabled() const {
        return guidance_ != nullptr && guidance_->enabled();
    }

    void to(torch::Device device) override;

protected:
    DiffuseCLoCActorConfig cloc_cfg_;

    // Emphasis matrices (registered as buffers in Python)
    torch::Tensor emphasis_mat_;      // [Do, Do] or [Do, 2*Do]
    torch::Tensor emphasis_mat_inv_;  // pseudo-inverse

    // Rolling buffer (None until first call)
    bool has_rolling_ = false;
    torch::Tensor action_rolling_traj_;  // [B, H-1, Da]
    torch::Tensor state_rolling_traj_;   // [B, H-1, Do_emph]

    std::unique_ptr<WholeBodyGuidance> guidance_;
    std::vector<int> action_selection_clean_endpoints_;

    torch::Tensor pre_denoise_guidance(
        const torch::Tensor& action_traj,
        const torch::Tensor& state_traj,
        const torch::Tensor& action_t_b,
        const torch::Tensor& state_t_b,
        const torch::Tensor& state_t_prev_b,
        const torch::Tensor& cond) override;

private:
    struct NSDdimStepPlan {
        torch::Tensor action_cur;
        torch::Tensor action_prev;
        torch::Tensor state_cur;
        torch::Tensor state_prev;
    };

    std::vector<NSDdimStepPlan> ns_ddim_plan_;

    void load_emphasis(const std::string& path);
    void build_ns_ddim_plan();

    /**
     * Generate noise schedule matrix.
     * Mirrors Python DiffuseCLoC.generate_denoising_matrix().
     *
     * @param schedule  "full" | "full_decreasing" | "from_xT_decreasing" | "from_xT_step"
     * @param is_state  Affects n used in decreasing_matrix
     * @return          [K, H] long tensor (on device_)
     */
    torch::Tensor generate_denoising_matrix(const std::string& schedule,
                                             bool is_state = false) const;

    /**
     * Internal helper used by generate_denoising_matrix.
     * Mirrors Python decreasing_matrix(start_value, is_state, step_size).
     *
     * @return (matrix[m, cols], n_pad)
     */
    std::pair<torch::Tensor, int>
    decreasing_matrix(int start_value, bool is_state, int step_size = 1) const;

    /**
     * Extract rolling trajectory from the denoising chain.
     * Mirrors Python DiffuseCLoC.get_rolling_traj().
     *
     * @param chain  Vector of (traj[B,H,D], t[H]) pairs
     * @param t_all  [K, H] target noise schedule
     * @return       [B, H-1, D]
     */
    torch::Tensor get_rolling_traj(
        const std::vector<std::pair<torch::Tensor, torch::Tensor>>& chain,
        const torch::Tensor& t_all) const;

    /**
     * Evenly spaced indices from [0, total), always including first and last.
     * Mirrors NoiseScheduler._uniform_indices().
     */
    static std::vector<int> uniform_indices(int total, int n);
};

}  // namespace diffusion_deploy
