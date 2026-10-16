/**
 * torch_actor.hpp
 *
 * LibTorch TorchScript actor.
 *
 * Supports two export modes:
 *
 * 1. Full loop export (recommended):
 *    The entire denoising loop is inside the TorchScript graph.
 *    act() calls model.forward(nobs, cond) once and returns action_traj.
 *    Export from Python:
 *      traced = torch.jit.trace(full_loop_fn, example_inputs)
 *      traced.save("policy_full_loop.pt")
 *
 * 2. Backbone only (step-by-step):
 *    The TorchScript backbone predicts x0 from noisy trajectory.
 *    act() implements the DDPM reverse loop in C++:
 *      for t in reversed(schedule):
 *          x0_pred = model(noisy, t, nobs, cond)
 *          noisy = ddpm_step(noisy, x0_pred, t)
 *    Export from Python:
 *      scripted = torch.jit.script(actor.backbone)
 *      scripted.save("policy_backbone.pt")
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include <torch/script.h>
#include <string>
#include <vector>

namespace diffusion_deploy {

enum class TorchExportMode {
    FULL_LOOP,  ///< Single forward() call returns complete action trajectory
    BACKBONE,   ///< Backbone predicts x0; C++ implements DDPM loop
};

class TorchActor : public BaseActor {
public:
    /**
     * Load a TorchScript model.
     *
     * @param model_path  Path to .pt TorchScript file.
     * @param config      Actor hyperparameters.
     * @param export_mode Whether model is full-loop or backbone-only.
     * @param device      Inference device (e.g. "cuda:0" or "cpu").
     */
    TorchActor(const std::string& model_path,
               const ActorConfig& config,
               TorchExportMode export_mode = TorchExportMode::FULL_LOOP,
               torch::Device device = torch::kCPU);

    torch::Tensor act(const torch::Tensor& nobs_norm,
                       const torch::Tensor& cond_norm = {}) override;

    int n_obs_steps()    const override { return config_.n_obs_steps; }
    int n_future_steps() const override { return config_.n_future_steps; }
    int horizon()        const override { return config_.horizon(); }
    int action_dim()     const override { return config_.action_dim; }
    int obs_dim()        const override { return config_.obs_dim; }

    torch::Device device() const override { return device_; }
    void to(torch::Device device) override;

private:
    torch::jit::script::Module model_;
    ActorConfig config_;
    TorchExportMode export_mode_;
    torch::Device device_;

    // DDPM noise schedule (pre-computed for backbone mode)
    torch::Tensor betas_;           // [T]
    torch::Tensor alphas_cumprod_;  // [T]
    torch::Tensor sqrt_alpha_cumprod_;     // [T]
    torch::Tensor sqrt_one_minus_alpha_cumprod_; // [T]

    /** Compute and cache DDPM schedule (linear beta schedule). */
    void init_noise_schedule(float beta_start = 0.0001f, float beta_end = 0.02f);

    /** C++ DDPM denoising loop (backbone export mode). */
    torch::Tensor denoise_backbone(const torch::Tensor& nobs_norm,
                                    const torch::Tensor& cond_norm);

    /** Single DDPM reverse step: x_{t-1} from x_t and x0_pred. */
    torch::Tensor ddpm_step(const torch::Tensor& x_t,
                             const torch::Tensor& x0_pred,
                             int t, int t_prev);
};

}  // namespace diffusion_deploy
