/**
 * diffusion_actor.hpp
 *
 * C++ reimplementation of DiffusionActor (policy_diffusion.py).
 *
 * Architecture
 * ------------
 * - Single-stream diffusion over action trajectories.
 * - Backbone: TorchScript ConditionalSeqBackbone (transformer.py)
 *     forward(sample[B,H,Da], timesteps[B,H], cond[B,T_cond,cond_dim]) -> [B,H,Da]
 * - DDPM reverse loop (cosine schedule) implemented entirely in C++.
 * - Optional motion conditioning: cond tensor [B,1,motion_dim] is concatenated
 *   with nobs [B,n_past,obs_dim] along the feature dim before being passed to the
 *   backbone as a flat [B, n_past, backbone_cond_dim] tensor.
 *
 * Export
 * ------
 * Run export_policy.py --mode backbone to produce:
 *   models/g1_policy_backbone.pt   — TorchScript backbone
 *   models/ddpm_schedule.pt        — DDPM schedule tensors
 *   models/<deploy_config>.yaml    — C++ deploy config (actor hyper-parameters
 *                                    live in the model: block)
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include <torch/script.h>
#include <string>
#include <vector>

namespace diffusion_deploy {

/**
 * Config specific to DiffusionActor.
 * Loaded from the deploy config's model: block (config_parser).
 */
struct DiffusionActorConfig {
    int  obs_dim           = 96;    ///< Backbone obs input dim (per step)
    int  action_dim        = 29;    ///< Action output dimension
    int  n_obs_steps       = 4;     ///< History steps fed as conditioning
    int  n_future_steps    = 16;    ///< Future steps predicted
    int  denoising_steps   = 10;    ///< Number of DDPM reverse steps
    bool predict_epsilon   = true;  ///< true: backbone predicts ε; false: predicts x0
    float denoised_clip    = 1.0f;  ///< Clip x0 predictions to [-clip, clip]

    // Motion conditioning (cond tensor from CLIP etc.)
    bool has_motion_cond   = false;
    int  motion_dim        = 0;     ///< Dimension of motion latent (0 if none)
    int  backbone_cond_dim = 0;     ///< obs_dim + motion_dim (auto-set if 0)

    // DDIM acceleration (0 = disabled, use full DDPM)
    int   ddim_steps = 0;     ///< Sub-sampled denoising steps (0 → full DDPM)
    float ddim_eta   = 0.0f;  ///< 0.0 = deterministic DDIM; 1.0 ≈ DDPM

    int horizon() const { return n_obs_steps + n_future_steps; }
};

/**
 * DiffusionActor — single-stream conditional DDPM for action generation.
 *
 * Mirrors Python DiffusionActor.act():
 *   trajectory = randn(B, H, Da)
 *   for i, t in enumerate(reversed(range(K))):
 *       trajectory = diffuse_step(trajectory, t_vec, i, cond)
 */
class DiffusionActor : public BaseActor {
public:
    /**
     * @param backbone_path  Path to TorchScript backbone (.pt).
     * @param schedule_path  Path to DDPM schedule tensors saved by export_policy.py.
     * @param config         Actor hyper-parameters.
     * @param device         Inference device.
     */
    DiffusionActor(const std::string& backbone_path,
                   const std::string& schedule_path,
                   const DiffusionActorConfig& config,
                   torch::Device device = torch::kCPU);

    /**
     * Run DDPM inference.
     *
     * @param nobs_norm  Normalised observations [B, n_obs_steps, obs_dim].
     * @param cond_norm  Optional motion conditioning [B, 1, motion_dim].
     *                   Pass undefined / empty tensor if has_motion_cond=false.
     * @return           Normalised action trajectory [B, horizon, action_dim].
     */
    torch::Tensor act(const torch::Tensor& nobs_norm,
                       const torch::Tensor& cond_norm = {}) override;

    /**
     * Run DDPM inference with pre-supplied noise tensors (for parity testing).
     *
     * @param nobs_norm   Normalised observations [B, n_obs_steps, obs_dim].
     * @param cond_norm   Optional motion conditioning [B, 1, motion_dim].
     * @param noise_list  Pre-generated noise tensors in call order:
     *                      noise_list[0]   : initial trajectory [B, H, Da]
     *                      noise_list[1..K]: per-step noise     [B, H, Da]
     *                    Tensors are moved to device_ internally.
     * @return            Normalised action trajectory [B, horizon, action_dim].
     */
    torch::Tensor act_with_noise(const torch::Tensor& nobs_norm,
                                  const torch::Tensor& cond_norm,
                                  const std::vector<torch::Tensor>& noise_list);

    int n_obs_steps()    const override { return cfg_.n_obs_steps; }
    int n_future_steps() const override { return cfg_.n_future_steps; }
    int horizon()        const override { return cfg_.horizon(); }
    int action_dim()     const override { return cfg_.action_dim; }
    int obs_dim()        const override { return cfg_.obs_dim; }
    torch::Device device() const override { return device_; }
    void to(torch::Device device) override;

private:
    torch::jit::script::Module backbone_;
    DiffusionActorConfig cfg_;
    torch::Device device_;

    // DDPM cosine schedule tensors (loaded from ddpm_schedule.pt)
    torch::Tensor alphas_cumprod_;               // [K]  — needed for DDIM
    torch::Tensor sqrt_recip_alphas_cumprod_;    // [K]
    torch::Tensor sqrt_recipm1_alphas_cumprod_;  // [K]
    torch::Tensor ddpm_mu_coef1_;                // [K]
    torch::Tensor ddpm_mu_coef2_;                // [K]
    torch::Tensor ddpm_logvar_clipped_;          // [K]

    void load_schedule(const std::string& schedule_path);

    /**
     * Build conditioning tensor for the backbone.
     *
     * If has_motion_cond=false: returns nobs_norm reshaped to [B, n_past, obs_dim].
     * If has_motion_cond=true:  concatenates nobs and motion along feature dim
     *   producing [B, n_past, obs_dim + motion_dim] (= [B, n_past, backbone_cond_dim]).
     *   (Mirrors transformer.py lines that handle dict cond {'obs':..,'motion':..})
     */
    torch::Tensor build_cond(const torch::Tensor& nobs_norm,
                              const torch::Tensor& cond_norm) const;

    /**
     * Call backbone: predict epsilon (or x0) from noisy trajectory.
     *
     * @param x_t    [B, H, Da] noisy trajectory
     * @param t_bh   [B, H]    timestep indices (long)
     * @param cond   [B, T_c, cond_dim]
     * @return       [B, H, Da] prediction
     */
    torch::Tensor backbone_forward(const torch::Tensor& x_t,
                                    const torch::Tensor& t_bh,
                                    const torch::Tensor& cond);

    /**
     * Extract schedule value at timestep t and broadcast to x_shape.
     * Mirrors Python extract(a, t, x_shape).
     *
     * @param a    [K]        schedule tensor
     * @param t_bh [B, H]     long index tensor
     * @return     [B, H, 1]  broadcast-ready
     */
    static torch::Tensor extract(const torch::Tensor& a,
                                  const torch::Tensor& t_bh);

    /** Predict x0 from epsilon prediction (mirrors predict_x0_from_epsilon). */
    torch::Tensor predict_x0_from_epsilon(const torch::Tensor& x_t,
                                           const torch::Tensor& t_bh,
                                           const torch::Tensor& eps) const;

    /**
     * Predict clean x0 from noisy x_t via one backbone forward pass.
     * Handles both predict_epsilon=true (ε→x0 conversion) and false (direct x0).
     * Clips result to [-denoised_clip, denoised_clip].
     */
    torch::Tensor predict_x0(const torch::Tensor& x_t,
                              const torch::Tensor& t_b,
                              const torch::Tensor& cond);

    /**
     * Build sub-sampled DDIM timestep sequence [t_{N-1}, ..., t_0] in descending
     * order, mirroring the Python linspace approach.
     *
     * @param K          Total denoising steps (full schedule length).
     * @param ddim_steps Number of steps to keep.
     * @return           Descending vector of unique int timestep indices.
     *                   Length = min(ddim_steps, K).
     */
    static std::vector<int> build_ddim_timesteps(int K, int ddim_steps);

    /**
     * Single DDIM reverse step: x_t -> x_{t_prev}.
     * t_prev = -1 signals the final step: acp_prev = 1.0 → returns exactly x0_pred.
     *
     * @param x_t      [B, H, Da] current noisy trajectory
     * @param x0_pred  [B, H, Da] predicted clean trajectory
     * @param t_cur    int — current timestep index into alphas_cumprod_
     * @param t_prev   int — target timestep index (-1 = clean)
     * @param eta      float — stochasticity (0 = deterministic)
     * @return         [B, H, Da]
     */
    torch::Tensor ddim_step(const torch::Tensor& x_t,
                             const torch::Tensor& x0_pred,
                             int t_cur,
                             int t_prev,
                             float eta) const;

    /**
     * Single stochastic DDPM reverse step: x_t -> x_{t-1}.
     * Mirrors SequentialDiffusionModel.diffuse_step().
     *
     * @param x_t    [B, H, Da] noisy input
     * @param t_vec  [H]        per-position timestep (long, on CPU)
     * @param i      iteration index (used to form t_b)
     * @param cond   [B, T_c, cond_dim]
     * @return       [B, H, Da] less noisy output
     */
    torch::Tensor diffuse_step(const torch::Tensor& x_t,
                                const torch::Tensor& t_vec,
                                int i,
                                const torch::Tensor& cond);

    /**
     * Same as diffuse_step but uses a pre-supplied noise tensor instead of
     * calling torch::randn_like.  Used by act_with_noise() for deterministic
     * parity testing.
     */
    torch::Tensor diffuse_step_with_noise(const torch::Tensor& x_t,
                                           const torch::Tensor& t_vec,
                                           const torch::Tensor& noise,
                                           const torch::Tensor& cond);
};

}  // namespace diffusion_deploy
