#include "diffusion_deploy/actor/torch_actor.hpp"
#include <stdexcept>
#include <iostream>
#include <cmath>

namespace diffusion_deploy {

TorchActor::TorchActor(const std::string& model_path,
                       const ActorConfig& config,
                       TorchExportMode export_mode,
                       torch::Device device)
    : config_(config), export_mode_(export_mode), device_(device)
{
    try {
        model_ = torch::jit::load(model_path, device);
        model_.eval();
    } catch (const c10::Error& e) {
        throw std::runtime_error(
            "[TorchActor] Failed to load model from: " + model_path +
            "\n  error: " + e.what());
    }

    if (export_mode_ == TorchExportMode::BACKBONE) {
        init_noise_schedule();
    }

    std::cout << "[TorchActor] Loaded model: " << model_path
              << " (mode=" << (export_mode_ == TorchExportMode::FULL_LOOP ? "full_loop" : "backbone")
              << ", device=" << device << ")\n";
}

void TorchActor::to(torch::Device device) {
    device_ = device;
    model_.to(device);
    if (betas_.defined())              betas_              = betas_.to(device);
    if (alphas_cumprod_.defined())     alphas_cumprod_     = alphas_cumprod_.to(device);
    if (sqrt_alpha_cumprod_.defined()) sqrt_alpha_cumprod_ = sqrt_alpha_cumprod_.to(device);
    if (sqrt_one_minus_alpha_cumprod_.defined())
        sqrt_one_minus_alpha_cumprod_ = sqrt_one_minus_alpha_cumprod_.to(device);
}

void TorchActor::init_noise_schedule(float beta_start, float beta_end) {
    int T = config_.denoising_steps;
    // Linear beta schedule matching Python diffusion_policy
    betas_ = torch::linspace(beta_start, beta_end, T, device_);
    auto alphas = 1.0f - betas_;
    alphas_cumprod_ = torch::cumprod(alphas, /*dim=*/0);
    sqrt_alpha_cumprod_          = torch::sqrt(alphas_cumprod_);
    sqrt_one_minus_alpha_cumprod_= torch::sqrt(1.0f - alphas_cumprod_);
}

// ---- act() ----

torch::Tensor TorchActor::act(const torch::Tensor& nobs_norm,
                               const torch::Tensor& cond_norm) {
    torch::NoGradGuard ng;

    auto obs = nobs_norm.to(device_).to(torch::kFloat32);

    if (export_mode_ == TorchExportMode::FULL_LOOP) {
        // Single forward pass returns action trajectory directly
        std::vector<torch::jit::IValue> inputs = {obs};
        if (cond_norm.defined() && cond_norm.numel() > 0) {
            inputs.push_back(cond_norm.to(device_).to(torch::kFloat32));
        }
        auto output = model_.forward(inputs);
        // Output may be Tensor or Tuple — extract first element
        if (output.isTensor()) {
            return output.toTensor();
        }
        return output.toTuple()->elements()[0].toTensor();
    }

    // Backbone mode: C++ DDPM denoising loop
    return denoise_backbone(obs,
        cond_norm.defined() ? cond_norm.to(device_).to(torch::kFloat32) : torch::Tensor{});
}

// ---- denoise_backbone() ----

torch::Tensor TorchActor::denoise_backbone(const torch::Tensor& nobs_norm,
                                            const torch::Tensor& cond_norm) {
    const int B = static_cast<int>(nobs_norm.size(0));
    const int H = config_.horizon();
    const int Da = config_.action_dim;
    const int T  = config_.denoising_steps;

    // Initialise with Gaussian noise
    auto action_traj = torch::randn({B, H, Da}, torch::TensorOptions()
                                    .dtype(torch::kFloat32).device(device_));

    // Reverse diffusion: from T-1 down to 0
    for (int t = T - 1; t >= 0; --t) {
        int t_prev = t - 1;  // -1 means x0 directly

        // Timestep tensor [B]
        auto t_tensor = torch::full({B}, t,
            torch::TensorOptions().dtype(torch::kLong).device(device_));

        // Backbone forward: predict x0
        std::vector<torch::jit::IValue> inputs = {action_traj, t_tensor, nobs_norm};
        if (cond_norm.defined() && cond_norm.numel() > 0) {
            inputs.push_back(cond_norm);
        }
        auto out    = model_.forward(inputs);
        torch::Tensor x0_pred;
        if (out.isTensor()) {
            x0_pred = out.toTensor();
        } else {
            x0_pred = out.toTuple()->elements()[0].toTensor();
        }

        action_traj = ddpm_step(action_traj, x0_pred, t, t_prev);
    }

    return action_traj;
}

// ---- ddpm_step() ----

torch::Tensor TorchActor::ddpm_step(const torch::Tensor& x_t,
                                     const torch::Tensor& x0_pred,
                                     int t, int t_prev) {
    // DDPM posterior mean:
    //   x_{t-1} = sqrt(alpha_bar_{t-1}) * x0_pred
    //           + sqrt(1 - alpha_bar_{t-1} - sigma^2) * (x_t - sqrt(alpha_bar_t)*x0_pred)
    //               / sqrt(1 - alpha_bar_t)
    //           + sigma * noise
    //
    // Here we use the simplified "DDIM deterministic" variant (sigma=0) which
    // works well for the denoising steps used in DiffuseCLoC:
    //   x_{t-1} = sqrt(alpha_bar_{t-1}) * x0_pred
    //           + sqrt(1 - alpha_bar_{t-1}) * eps_pred
    // where eps_pred = (x_t - sqrt(alpha_bar_t)*x0_pred) / sqrt(1 - alpha_bar_t)

    if (t_prev < 0) {
        // Last step: return x0 directly
        return x0_pred;
    }

    float sqrt_abar_t      = sqrt_alpha_cumprod_[t].item<float>();
    float sqrt_1m_abar_t   = sqrt_one_minus_alpha_cumprod_[t].item<float>();
    float sqrt_abar_tprev  = sqrt_alpha_cumprod_[t_prev].item<float>();
    float sqrt_1m_abar_tprev = sqrt_one_minus_alpha_cumprod_[t_prev].item<float>();

    // Predicted noise
    auto eps_pred = (x_t - sqrt_abar_t * x0_pred) / (sqrt_1m_abar_t + 1e-8f);

    // Deterministic DDIM step
    return sqrt_abar_tprev * x0_pred + sqrt_1m_abar_tprev * eps_pred;
}

}  // namespace diffusion_deploy
