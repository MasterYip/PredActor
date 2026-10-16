/**
 * joint_diffusion_actor.hpp
 *
 * C++ reimplementation of JointDiffusionActor (joint_diffusion.py).
 *
 * Architecture
 * ------------
 * - Joint-distribution diffusion over state AND action trajectories.
 * - Backbone: TorchScript JointSeqBackbone (transformer_codiffuse.py)
 *     forward(x_input[B,Hx,Dx], y_input[B,Hy,Dy],
 *             x_timesteps[B,Hx], y_timesteps[B,Hy],
 *             cond) -> (x_out[B,Hx,Dx], y_out[B,Hy,Dy])
 *   where x = state, y = action.
 * - Inpainting: past states are replaced by nobs and their timesteps set to 0.
 * - Separate DDPM loops for state and action (same schedule by default).
 *
 * Export
 * ------
 * Run export_policy.py --mode backbone to produce:
 *   models/g1_policy_backbone.pt   — TorchScript JointSeqBackbone
 *   models/ddpm_schedule.pt        — DDPM schedule tensors
 *   models/<deploy_config>.yaml    — C++ deploy config (actor hyper-parameters
 *                                    live in the model: block)
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include <torch/script.h>
#include <cstdint>
#include <functional>
#include <utility>
#include <string>
#include <vector>
#include <array>

namespace diffusion_deploy {

/**
 * Config for JointDiffusionActor.
 * Loaded from the deploy config's model: block (config_parser).
 */
struct JointDiffusionActorConfig {
    std::string precision        = "fp32"; ///< Learned backbone precision: fp32|fp16
    int  obs_dim              = 96;    ///< State / obs dimension (x_output_dim)
    int  action_dim           = 29;    ///< Action dimension (y_output_dim)
    int  n_obs_steps          = 4;     ///< Past steps inpainted as clean state
    int  n_future_steps       = 16;    ///< Future steps to predict
    int  denoising_steps      = 10;    ///< DDPM reverse steps
    bool predict_epsilon      = true;  ///< Backbone predicts ε or x0
    bool state_pred_epsilon   = true;  ///< State branch pred mode
    bool action_pred_epsilon  = true;  ///< Action branch pred mode
    float denoised_clip       = 1.0f;  ///< Clip x0 predictions
    int  action_denoising_steps = 0;   ///< 0 → use denoising_steps
    int  state_denoising_steps  = 0;   ///< 0 → use denoising_steps

    // Optional motion conditioning
    bool has_motion_cond      = false;
    int  motion_dim           = 0;
    int  backbone_cond_dim    = 0;   ///< Actual cond input dim to backbone (motion_dim for CLoC, obs_dim+motion_dim for DP)
    int  n_cond_steps         = 1;   ///< Exact temporal condition tokens expected by backbone
    bool no_state_override    = false; ///< PRDP: denoise state from condition instead of inpainting nobs

    // Python-aligned backbone/actor fields (config-schema alignment).  These
    // mirror the Python config's nested `backbone:` block and actor fields and
    // are parsed for provenance + cross-checking; the C++ runtime derives the
    // effective state dim from the emphasis matrix and the cond dim from
    // backbone_cond_dim.
    int         x_input_dim       = 0;    ///< Python backbone.x_input_dim (0 = unset)
    int         x_output_dim      = 0;    ///< Python backbone.x_output_dim (0 = unset)
    int         cross_attn_window = 0;    ///< Python backbone.cross_attn_window (0 = null/unset)
    std::string cross_attn_mode   = "full"; ///< Python backbone.cross_attn_mode (full|state|action|no_attn)
    bool        clean_past_state  = false; ///< Python actor.clean_past_state (training-only provenance)
    std::string data_profile;             ///< Python actor.data_profile (e.g. g1_prdp_standard2)
    std::string attention_projection_packing = "none"; ///< Artifact provenance: none|self|cross|all

    // Exact-semantics inference optimizations.  Every switch is opt-in so
    // existing artifacts/configs retain the legacy execution path.
    bool condition_embedding_reuse = false; ///< Encode condition once per policy call
    bool ddim_precompute = false;             ///< Reuse fixed B=1 timestep tensors/scalars
    bool defer_finite_checks = false;         ///< One input/output check instead of per NFE
    bool inference_mode = false;              ///< c10::InferenceMode instead of NoGrad alone

    // DDIM acceleration (0 = disabled, use full DDPM)
    int   ddim_steps = 0;     ///< Sub-sampled denoising steps (0 → full DDPM)
    float ddim_eta   = 0.0f;  ///< 0.0 = deterministic DDIM; 1.0 ≈ DDPM

    int horizon() const { return n_obs_steps + n_future_steps; }
    int eff_action_steps() const {
        return action_denoising_steps > 0 ? action_denoising_steps : denoising_steps;
    }
    int eff_state_steps() const {
        return state_denoising_steps > 0 ? state_denoising_steps : denoising_steps;
    }
};

/**
 * JointDiffusionActor — joint state+action DDPM for trajectory generation.
 *
 * Mirrors Python JointDiffusionActor.act() / diffuse_step().
 */
class JointDiffusionActor : public BaseActor {
public:
    using TimelineHook = std::function<void(const std::string&)>;
    /**
     * @param backbone_path  Path to TorchScript JointSeqBackbone (.pt).
     * @param schedule_path  Path to DDPM schedule tensors.
     * @param config         Actor hyper-parameters.
     * @param device         Inference device.
     */
    JointDiffusionActor(const std::string& backbone_path,
                         const std::string& schedule_path,
                         const JointDiffusionActorConfig& config,
                         torch::Device device = torch::kCPU);

    /**
     * Run joint DDPM inference.
     *
     * @param nobs_norm  Normalised obs [B, n_obs_steps, obs_dim].
     * @param cond_norm  Optional motion cond [B, 1, motion_dim].
     * @return           Normalised action trajectory [B, horizon, action_dim].
     *                   (State trajectory is discarded; DiffuseCLoCActor returns it.)
     */
    torch::Tensor act(const torch::Tensor& nobs_norm,
                      const torch::Tensor& cond_norm = {}) override;

    /**
     * Full act() returning both trajectories.
     *
     * @return pair<action_traj[B,H,Da], state_traj[B,H,Do]>
     */
    virtual std::pair<torch::Tensor, torch::Tensor>
    act_joint(const torch::Tensor& nobs_norm,
              const torch::Tensor& cond_norm = {});

    int n_obs_steps()    const override { return cfg_.n_obs_steps; }
    int n_future_steps() const override { return cfg_.n_future_steps; }
    int horizon()        const override { return cfg_.horizon(); }
    int action_dim()     const override { return cfg_.action_dim; }
    int obs_dim()        const override { return cfg_.obs_dim; }
    torch::Device device() const override { return device_; }
    void to(torch::Device device) override;

    /** Number of actual TorchScript backbone invocations since the last reset. */
    std::uint64_t backbone_forward_count() const { return backbone_forward_count_; }
    void reset_backbone_forward_count() { backbone_forward_count_ = 0; }
    void set_timeline_hook(TimelineHook hook) { timeline_hook_ = std::move(hook); }

    /** Exact scalar-DDIM plan used by act(); exposed for provenance tests. */
    std::vector<int> scalar_ddim_timesteps() const {
        return build_ddim_timesteps(cfg_.denoising_steps, cfg_.ddim_steps);
    }

protected:
    struct DdimStepPlan {
        int t_cur = 0;
        int t_prev = -1;
        float sqrt_acp_t = 1.0f;
        float sqrt_acp_prev = 1.0f;
        float sqrt_one_minus_t = 0.0f;
        float sqrt_one_minus_prev = 0.0f;
        torch::Tensor action_t;
        torch::Tensor state_t;
        torch::Tensor state_t_prev;
        torch::Tensor state_t_denoise;
        torch::Tensor state_t_prev_denoise;
    };

    torch::jit::script::Module backbone_;
    JointDiffusionActorConfig cfg_;
    torch::Device device_;
    torch::ScalarType model_dtype_ = torch::kFloat32;

    // DDPM schedule tensors (from ddpm_schedule.pt)
    torch::Tensor alphas_cumprod_;               // [K] — needed for DDIM
    torch::Tensor sqrt_recip_alphas_cumprod_;
    torch::Tensor sqrt_recipm1_alphas_cumprod_;
    torch::Tensor ddpm_mu_coef1_;
    torch::Tensor ddpm_mu_coef2_;
    torch::Tensor ddpm_logvar_clipped_;
    std::vector<DdimStepPlan> ddim_plan_;
    bool optimized_methods_verified_ = false;
    std::uint64_t backbone_forward_count_ = 0;
    TimelineHook timeline_hook_;
    std::uint64_t timeline_backbone_index_ = 0;

    void timeline_mark(const std::string& name) {
        if (timeline_hook_) timeline_hook_(name);
    }
    void reset_timeline_backbone_index() { timeline_backbone_index_ = 0; }

    void load_schedule(const std::string& path);
    void build_ddim_plan();
    torch::Tensor build_condition_embeddings(const torch::Tensor& condition);

    /**
     * Extract schedule value at t_bh and broadcast.
     * @param a    [K] schedule tensor
     * @param t_bh [B, H] long index tensor
     * @return     [B, H, 1]
     */
    static torch::Tensor extract(const torch::Tensor& a, const torch::Tensor& t_bh);

    /** Predict x0 from epsilon prediction. */
    torch::Tensor predict_x0_from_epsilon(const torch::Tensor& x_t,
                                           const torch::Tensor& t_bh,
                                           const torch::Tensor& eps) const;

    /**
     * Call dual-stream backbone.
     *
     * @param state_traj  [B, H, Do]
     * @param action_traj [B, H, Da]
     * @param state_t_b   [B, H] long
     * @param action_t_b  [B, H] long
     * @param cond        [B, T_c, cond_dim] or undefined
     * @return (state_pred[B,H,Do], action_pred[B,H,Da])
     */
    std::pair<torch::Tensor, torch::Tensor>
    backbone_forward(const torch::Tensor& state_traj,
                     const torch::Tensor& action_traj,
                     const torch::Tensor& state_t_b,
                     const torch::Tensor& action_t_b,
                     const torch::Tensor& cond,
                     const torch::Tensor& condition_embeddings = {});

    /**
     * Single joint reverse diffusion step.
     * Inpaints past states: state_traj[:, :n_past] = nobs; state_t[:n_past] = 0.
     *
     * @param nobs        [B, n_past, Do] clean observations
     * @param action_traj [B, H, Da]  current noisy actions
     * @param state_traj  [B, H, Do]  current noisy states
     * @param action_t    [H] action timesteps (long, on device)
     * @param state_t     [H] state timesteps (long, on device)
     * @param cond        [B, T_c, cond_dim] or undefined
     * @return (action_traj', state_traj')
     */
    virtual std::pair<torch::Tensor, torch::Tensor>
    diffuse_step(const torch::Tensor& nobs,
                 torch::Tensor action_traj,
                 torch::Tensor state_traj,
                 const torch::Tensor& action_t,
                 const torch::Tensor& state_t,
                 const torch::Tensor& cond);

    /** Apply one DDPM update using an already computed x0 prediction. */
    std::pair<torch::Tensor, torch::Tensor>
    diffuse_step_from_predictions(
        torch::Tensor action_traj,
        torch::Tensor state_traj,
        const torch::Tensor& action_t_b,
        const torch::Tensor& state_t_b,
        const torch::Tensor& action_pred,
        const torch::Tensor& state_pred);

    /**
     * Build sub-sampled DDIM timestep sequence [t_{N-1}, ..., t_0] descending.
     * Mirrors Python linspace approach. See DiffusionActor for details.
     */
    static std::vector<int> build_ddim_timesteps(int K, int ddim_steps);

    /**
     * Predict clean (action_x0, state_x0) from noisy trajectories via one
     * backbone forward pass.  Handles predict_epsilon for each stream.
     * Clips x0 by default; classifier WBG requests raw x0 and the subsequent
     * DDIM update clips the guided prediction, matching Python's ordering.
     */
    std::pair<torch::Tensor, torch::Tensor>
    predict_x0(const torch::Tensor& action_traj,
               const torch::Tensor& state_traj,
               const torch::Tensor& action_t_b,
               const torch::Tensor& state_t_b,
               const torch::Tensor& cond,
               const torch::Tensor& condition_embeddings = {},
               bool clip_predictions = true);

    /** Deprecated two-forward classifier-guidance hook for historical replay. */
    virtual torch::Tensor pre_denoise_guidance(
        const torch::Tensor& action_traj,
        const torch::Tensor& state_traj,
        const torch::Tensor& action_t_b,
        const torch::Tensor& state_t_b,
        const torch::Tensor& state_t_prev_b,
        const torch::Tensor& cond);

    /**
     * Single DDIM reverse step for both action and state streams.
     * Inpaints past states ([:n_obs_steps]) from nobs before the backbone call
     * and restores them afterwards.
     *
     * @param action_traj  [B, H, Da]
     * @param state_traj   [B, H, Do]
     * @param nobs         [B, n_obs_steps, Do] clean observations (inpaint anchor)
     * @param t_cur        current timestep index into alphas_cumprod_
     * @param t_prev       next  timestep index (-1 = final step → clean)
     * @param eta          stochasticity (0 = deterministic)
     * @param cond         [B, T_c, cond_dim]
     * @return (new_action_traj, new_state_traj)
     */
    std::pair<torch::Tensor, torch::Tensor>
    joint_ddim_step(torch::Tensor action_traj,
                    torch::Tensor state_traj,
                    const torch::Tensor& nobs,
                    int t_cur,
                    int t_prev,
                    float eta,
                    const torch::Tensor& cond,
                    const torch::Tensor& condition_embeddings = {},
                    const DdimStepPlan* plan = nullptr);

    /** Apply one scalar DDIM update using already computed x0 predictions. */
    std::pair<torch::Tensor, torch::Tensor>
    joint_ddim_step_from_predictions(
        torch::Tensor action_traj,
        torch::Tensor state_traj,
        const torch::Tensor& nobs,
        int t_cur,
        int t_prev,
        float eta,
        const torch::Tensor& action_pred,
        const torch::Tensor& state_pred,
        const DdimStepPlan* plan = nullptr);

public:
    /**
     * Per-position DDIM reverse step (mirrors NoiseScheduler.ddim_step).
     * t_cur / t_prev are [H] long vectors; -1 in t_prev means "clean" (acp=1).
     * Static and schedule-parameterised so the unit test can validate the
     * numerics directly against Python without loading a backbone.
     */
    static torch::Tensor per_position_ddim_step(
        const torch::Tensor& x_t,
        const torch::Tensor& x0_pred,
        const torch::Tensor& t_cur,
        const torch::Tensor& t_prev,
        float eta,
        const torch::Tensor& alphas_cumprod,
        int64_t denoising_steps);

protected:
    /**
     * Per-position DDIM reverse step (NS DDIM), mirroring Python
     * JointDiffusionActor.joint_ns_ddim_step + NoiseScheduler.ddim_step.
     *
     * Each horizon position may have its own noise level. Inpaints past states
     * from nobs before the backbone call and restores them afterwards.
     *
     * @param action_traj  [B, H, Da]
     * @param state_traj   [B, H, Do]
     * @param nobs         [B, n_obs_steps, Do] clean observations (inpaint anchor)
     * @param a_t_cur      [H] action noise level per position before this step
     * @param a_t_prev     [H] action noise level per position after this step (-1 = clean)
     * @param s_t_cur      [H] state  noise level per position before this step
     * @param s_t_prev     [H] state  noise level per position after this step (-1 = clean)
     * @param eta          stochasticity (0 = deterministic)
     * @param cond         [B, T_c, cond_dim]
     * @return (new_action_traj, new_state_traj)
     */
    std::pair<torch::Tensor, torch::Tensor>
    joint_ns_ddim_step(torch::Tensor action_traj,
                       torch::Tensor state_traj,
                       const torch::Tensor& nobs,
                       const torch::Tensor& a_t_cur,
                       const torch::Tensor& a_t_prev,
                       const torch::Tensor& s_t_cur,
                       const torch::Tensor& s_t_prev,
                       float eta,
                       const torch::Tensor& cond);

    /** Apply one per-position NS-DDIM update using predictions from one NFE. */
    std::pair<torch::Tensor, torch::Tensor>
    joint_ns_ddim_step_from_predictions(
        torch::Tensor action_traj,
        torch::Tensor state_traj,
        const torch::Tensor& nobs,
        const torch::Tensor& a_t_cur,
        const torch::Tensor& a_t_prev,
        const torch::Tensor& s_t_cur,
        const torch::Tensor& s_t_prev,
        float eta,
        const torch::Tensor& action_pred,
        const torch::Tensor& state_pred);

private:
    /**
     * DDPM posterior mean+var from x0 prediction.
     * Returns (mu, logvar) each [B,H,D].
     */
    std::pair<torch::Tensor, torch::Tensor>
    mean_var_from_x0(const torch::Tensor& x_t,
                     const torch::Tensor& t_bh,
                     const torch::Tensor& x0_pred) const;
};

}  // namespace diffusion_deploy
