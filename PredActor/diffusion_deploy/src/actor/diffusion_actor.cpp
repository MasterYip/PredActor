/**
 * diffusion_actor.cpp
 *
 * C++ implementation of DiffusionActor.
 * Mirrors Python DiffusionActor (policy_diffusion.py) +
 *   SequentialDiffusionModel (diffusion_model.py).
 */
#include "diffusion_deploy/actor/diffusion_actor.hpp"
#include <stdexcept>
#include <iostream>
#include <cmath>
#include <set>

namespace diffusion_deploy {

// ---- Construction ----

DiffusionActor::DiffusionActor(const std::string& backbone_path,
                                const std::string& schedule_path,
                                const DiffusionActorConfig& config,
                                torch::Device device)
    : cfg_(config), device_(device)
{
    // Fix up backbone_cond_dim if caller left it 0
    if (cfg_.backbone_cond_dim <= 0) {
        cfg_.backbone_cond_dim = cfg_.obs_dim + cfg_.motion_dim;
    }

    try {
        backbone_ = torch::jit::load(backbone_path, device_);
        backbone_.eval();
    } catch (const c10::Error& e) {
        throw std::runtime_error(
            "[DiffusionActor] Failed to load backbone from: " + backbone_path +
            "\n  " + e.what());
    }

    load_schedule(schedule_path);

    std::cout << "[DiffusionActor] backbone=" << backbone_path
              << "  obs_dim=" << cfg_.obs_dim
              << "  action_dim=" << cfg_.action_dim
              << "  K=" << cfg_.denoising_steps
              << "  motion_cond=" << (cfg_.has_motion_cond ? "yes" : "no")
              << "  accel=" << (cfg_.ddim_steps > 0
                  ? "DDIM(steps=" + std::to_string(cfg_.ddim_steps)
                    + ",eta=" + std::to_string(cfg_.ddim_eta) + ")"
                  : "DDPM(full,K=" + std::to_string(cfg_.denoising_steps) + ")")
              << "\n";
}

void DiffusionActor::load_schedule(const std::string& schedule_path) {
    // ddpm_schedule.pt is saved via torch.jit.save(scripted_module, path).
    // Read tensors via module.attr("name").
    try {
        auto mod = torch::jit::load(schedule_path, device_);
        auto get = [&](const char* k) -> torch::Tensor {
            return mod.attr(k).toTensor().to(torch::kFloat32).to(device_);
        };
        alphas_cumprod_              = get("alphas_cumprod");
        sqrt_recip_alphas_cumprod_   = get("sqrt_recip_alphas_cumprod");
        sqrt_recipm1_alphas_cumprod_ = get("sqrt_recipm1_alphas_cumprod");
        ddpm_mu_coef1_               = get("ddpm_mu_coef1");
        ddpm_mu_coef2_               = get("ddpm_mu_coef2");
        ddpm_logvar_clipped_         = get("ddpm_logvar_clipped");
        std::cout << "[DiffusionActor] Schedule loaded from: " << schedule_path
                  << "  K=" << sqrt_recip_alphas_cumprod_.size(0) << "\n";
    } catch (const std::exception& e) {
        throw std::runtime_error(
            "[DiffusionActor] Failed to load DDPM schedule from: " + schedule_path +
            "\n  " + e.what());
    }
}

void DiffusionActor::to(torch::Device device) {
    device_ = device;
    backbone_.to(device_);
    auto mv = [&](torch::Tensor& t) { if (t.defined()) t = t.to(device_); };
    mv(alphas_cumprod_);
    mv(sqrt_recip_alphas_cumprod_);
    mv(sqrt_recipm1_alphas_cumprod_);
    mv(ddpm_mu_coef1_);
    mv(ddpm_mu_coef2_);
    mv(ddpm_logvar_clipped_);
}

// ---- act() ----

torch::Tensor DiffusionActor::act(const torch::Tensor& nobs_norm,
                                    const torch::Tensor& cond_norm) {
    torch::NoGradGuard ng;

    auto obs = nobs_norm.to(device_).to(torch::kFloat32);
    // Clip to n_obs_steps
    obs = obs.narrow(1, 0, cfg_.n_obs_steps);

    const int B = static_cast<int>(obs.size(0));
    const int H = cfg_.horizon();
    const int Da = cfg_.action_dim;
    const int K  = cfg_.denoising_steps;

    // Build conditioning tensor once
    torch::Tensor cond_input;
    if (cond_norm.defined() && cond_norm.numel() > 0) {
        cond_input = build_cond(obs, cond_norm.to(device_).to(torch::kFloat32));
    } else {
        cond_input = build_cond(obs, {});
    }

    // Sample initial noise trajectory
    auto trajectory = torch::randn({B, H, Da},
                        torch::TensorOptions().dtype(torch::kFloat32).device(device_));

    // ---- DDIM path ----
    if (cfg_.ddim_steps > 0) {
        auto ts = build_ddim_timesteps(K, cfg_.ddim_steps);
        for (int i = 0; i < static_cast<int>(ts.size()); ++i) {
            int t_cur  = ts[i];
            int t_prev = (i + 1 < static_cast<int>(ts.size())) ? ts[i + 1] : -1;
            auto t_b = torch::full({B, H}, t_cur,
                torch::TensorOptions().dtype(torch::kLong).device(device_));
            auto x0 = predict_x0(trajectory, t_b, cond_input);
            trajectory = ddim_step(trajectory, x0, t_cur, t_prev, cfg_.ddim_eta);
        }
        return trajectory;
    }

    // ---- DDPM path (default) ----
    // Reverse diffusion: t = K-1 down to 0, all horizon positions share the same t
    for (int i = 0; i < K; ++i) {
        int t_val = K - 1 - i;
        // t_vec: [H] all equal to t_val
        auto t_vec = torch::full({H}, t_val,
            torch::TensorOptions().dtype(torch::kLong).device(device_));
        trajectory = diffuse_step(trajectory, t_vec, i, cond_input);
    }

    return trajectory;
}

// ---- act_with_noise() ----

torch::Tensor DiffusionActor::act_with_noise(const torch::Tensor& nobs_norm,
                                               const torch::Tensor& cond_norm,
                                               const std::vector<torch::Tensor>& noise_list) {
    torch::NoGradGuard ng;

    const int K = cfg_.denoising_steps;
    // Expect K+1 noise tensors: [0]=initial trajectory noise, [1..K]=per-step
    if (static_cast<int>(noise_list.size()) < K + 1) {
        throw std::runtime_error(
            "[DiffusionActor::act_with_noise] Expected " + std::to_string(K + 1) +
            " noise tensors, got " + std::to_string(noise_list.size()));
    }

    auto obs = nobs_norm.to(device_).to(torch::kFloat32);
    obs = obs.narrow(1, 0, cfg_.n_obs_steps);

    const int H = cfg_.horizon();

    torch::Tensor cond_input;
    if (cond_norm.defined() && cond_norm.numel() > 0) {
        cond_input = build_cond(obs, cond_norm.to(device_).to(torch::kFloat32));
    } else {
        cond_input = build_cond(obs, {});
    }

    // Use pre-supplied initial noise instead of torch::randn
    auto trajectory = noise_list[0].to(device_).to(torch::kFloat32);

    for (int i = 0; i < K; ++i) {
        int t_val = K - 1 - i;
        auto t_vec = torch::full({H}, t_val,
            torch::TensorOptions().dtype(torch::kLong).device(device_));
        auto step_noise = noise_list[i + 1].to(device_).to(torch::kFloat32);
        trajectory = diffuse_step_with_noise(trajectory, t_vec, step_noise, cond_input);
    }

    return trajectory;
}



torch::Tensor DiffusionActor::build_cond(const torch::Tensor& nobs,
                                           const torch::Tensor& motion_cond) const {
    if (!cfg_.has_motion_cond) {
        // Plain obs conditioning: [B, n_past, obs_dim]
        return nobs;
    }

    // If obs already fills the backbone cond capacity (obs_per_step * n_past == backbone_cond_dim),
    // there is no room for motion latent — return obs directly without concatenation.
    // This handles the case where the model was exported with cond=[B, n_past, backbone_cond_dim/n_past]
    // rather than obs=[B,n_past,obs_dim] + motion=[B,n_past,motion_dim].
    const int obs_feat_dim = static_cast<int>(nobs.size(2));
    if (obs_feat_dim * cfg_.n_obs_steps == cfg_.backbone_cond_dim) {
        return nobs;
    }
    // Motion conditioning: concatenate obs and motion along feature dim.
    // nobs:        [B, n_past, obs_dim]
    // motion_cond: [B, 1,      motion_dim]  → expand to [B, n_past, motion_dim]
    // If no motion signal is available, zero-fill the motion portion so the
    // backbone always receives cond[B, n_past, backbone_cond_dim].
    const int B      = static_cast<int>(nobs.size(0));
    const int n_past = cfg_.n_obs_steps;

    torch::Tensor mc;
    if (motion_cond.defined() && motion_cond.numel() > 0) {
        mc = motion_cond.expand({B, n_past, motion_cond.size(2)});
    } else {
        mc = torch::zeros({B, n_past, cfg_.motion_dim},
                torch::TensorOptions().dtype(torch::kFloat32).device(device_));
    }
    return torch::cat({nobs, mc}, /*dim=*/2);
}

// ---- predict_x0() ----

torch::Tensor DiffusionActor::predict_x0(const torch::Tensor& x_t,
                                           const torch::Tensor& t_b,
                                           const torch::Tensor& cond) {
    auto pred = backbone_forward(x_t, t_b, cond);
    torch::Tensor x0;
    if (cfg_.predict_epsilon) {
        x0 = predict_x0_from_epsilon(x_t, t_b, pred);
    } else {
        x0 = pred;
    }
    x0.clamp_(-cfg_.denoised_clip, cfg_.denoised_clip);
    return x0;
}

// ---- build_ddim_timesteps() ----

std::vector<int> DiffusionActor::build_ddim_timesteps(int K, int ddim_steps) {
    // Mirror Python: linspace(0, K-1, ddim_steps).round().long() + dedup + sort desc
    std::vector<int> ts;
    if (K <= 0 || ddim_steps <= 0) return ts;
    if (ddim_steps == 1) return {K - 1};
    if (ddim_steps >= K) {
        for (int t = K - 1; t >= 0; --t) ts.push_back(t);
        return ts;
    }
    // Compute linspace and round
    std::set<int> seen;
    for (int i = 0; i < ddim_steps; ++i) {
        double frac = static_cast<double>(i) / (ddim_steps - 1);
        int t = static_cast<int>(std::round(frac * (K - 1)));
        seen.insert(t);
    }
    // Convert set to vector in descending order
    for (auto it = seen.rbegin(); it != seen.rend(); ++it) ts.push_back(*it);
    return ts;
}

// ---- ddim_step() ----

torch::Tensor DiffusionActor::ddim_step(const torch::Tensor& x_t,
                                          const torch::Tensor& x0_pred,
                                          int t_cur,
                                          int t_prev,
                                          float eta) const {
    // acp_t: scalar alpha-cumprod at current step
    float acp_t = alphas_cumprod_[t_cur].item<float>();
    // acp_prev: 1.0 if final step (t_prev=-1), else alphas_cumprod_[t_prev]
    float acp_p = (t_prev < 0) ? 1.0f : alphas_cumprod_[t_prev].item<float>();

    float sqrt_acp_t = std::sqrt(acp_t);
    float sqrt_acp_p = std::sqrt(acp_p);
    float sqrt_1m_t  = std::sqrt(std::max(1.0f - acp_t, 1e-8f));
    float sqrt_1m_p  = std::sqrt(1.0f - acp_p);

    // ε̂ = (x_t - √ᾱ_t * x0) / √(1 - ᾱ_t)
    auto eps_hat = (x_t - sqrt_acp_t * x0_pred) / sqrt_1m_t;

    if (eta == 0.0f) {
        // Deterministic DDIM: x_{t_prev} = √ᾱ_prev * x0 + √(1-ᾱ_prev) * ε̂
        return sqrt_acp_p * x0_pred + sqrt_1m_p * eps_hat;
    }
    // Stochastic DDIM (η > 0)
    float sigma_sq = eta * eta
                   * (1.0f - acp_p) / std::max(1.0f - acp_t, 1e-8f)
                   * std::max(1.0f - acp_t / std::max(acp_p, 1e-8f), 0.0f);
    float sigma    = std::sqrt(sigma_sq);
    float dir_coef = std::sqrt(std::max(1.0f - acp_p - sigma_sq, 0.0f));
    auto  noise    = (t_cur == 0) ? torch::zeros_like(x_t) : torch::randn_like(x_t);
    return sqrt_acp_p * x0_pred + dir_coef * eps_hat + sigma * noise;
}

// ---- backbone_forward() ----

torch::Tensor DiffusionActor::backbone_forward(const torch::Tensor& x_t,
                                                 const torch::Tensor& t_bh,
                                                 const torch::Tensor& cond) {
    // backbone(sample[B,H,Da], timesteps[B,H], cond[B,T_cond,cond_dim]) -> [B,H,Da]
    std::vector<torch::jit::IValue> inputs = {x_t, t_bh, cond};
    auto out = backbone_.forward(inputs);
    if (out.isTensor()) return out.toTensor();
    return out.toTuple()->elements()[0].toTensor();
}

// ---- extract() ----

torch::Tensor DiffusionActor::extract(const torch::Tensor& a,
                                        const torch::Tensor& t_bh) {
    // a: [K], t_bh: [B, H]  →  out: [B, H, 1]
    return a.index({t_bh}).unsqueeze(2);  // gather, then broadcast dim
}

// ---- predict_x0_from_epsilon() ----

torch::Tensor DiffusionActor::predict_x0_from_epsilon(const torch::Tensor& x_t,
                                                        const torch::Tensor& t_bh,
                                                        const torch::Tensor& eps) const {
    // x0 = sqrt(1/abar_t) * x_t - sqrt(1/abar_t - 1) * eps
    return extract(sqrt_recip_alphas_cumprod_,  t_bh) * x_t
         - extract(sqrt_recipm1_alphas_cumprod_, t_bh) * eps;
}

// ---- diffuse_step() ----

torch::Tensor DiffusionActor::diffuse_step(const torch::Tensor& x_t,
                                             const torch::Tensor& t_vec,
                                             int /*i*/,
                                             const torch::Tensor& cond) {
    const int B = static_cast<int>(x_t.size(0));
    const int H = static_cast<int>(x_t.size(1));

    // t_b: [B, H] — broadcast t_vec over batch
    auto t_b = t_vec.unsqueeze(0).expand({B, H}).to(device_);

    // Backbone prediction: epsilon or x0
    auto pred = backbone_forward(x_t, t_b, cond);

    // Predict x0
    torch::Tensor x0_pred;
    if (cfg_.predict_epsilon) {
        x0_pred = predict_x0_from_epsilon(x_t, t_b, pred);
    } else {
        x0_pred = pred;
    }

    // Clip
    x0_pred.clamp_(-cfg_.denoised_clip, cfg_.denoised_clip);

    // DDPM posterior mean: mu = coef1 * x0 + coef2 * x_t
    auto mu = extract(ddpm_mu_coef1_, t_b) * x0_pred
            + extract(ddpm_mu_coef2_, t_b) * x_t;

    // DDPM log-variance
    auto logvar = extract(ddpm_logvar_clipped_, t_b);

    // Stochastic step: no noise at t=0
    auto noise = torch::randn_like(x_t);
    // Zero noise where t == 0 (any element of t_b)
    auto zero_mask = (t_b == 0).unsqueeze(2).expand_as(noise);
    noise.masked_fill_(zero_mask, 0.0f);

    return mu + (0.5f * logvar).exp() * noise;
}

// ---- diffuse_step_with_noise() ----

torch::Tensor DiffusionActor::diffuse_step_with_noise(const torch::Tensor& x_t,
                                                        const torch::Tensor& t_vec,
                                                        const torch::Tensor& noise,
                                                        const torch::Tensor& cond) {
    const int B = static_cast<int>(x_t.size(0));
    const int H = static_cast<int>(x_t.size(1));

    auto t_b = t_vec.unsqueeze(0).expand({B, H}).to(device_);

    auto pred = backbone_forward(x_t, t_b, cond);

    torch::Tensor x0_pred;
    if (cfg_.predict_epsilon) {
        x0_pred = predict_x0_from_epsilon(x_t, t_b, pred);
    } else {
        x0_pred = pred;
    }
    x0_pred.clamp_(-cfg_.denoised_clip, cfg_.denoised_clip);

    auto mu = extract(ddpm_mu_coef1_, t_b) * x0_pred
            + extract(ddpm_mu_coef2_, t_b) * x_t;
    auto logvar = extract(ddpm_logvar_clipped_, t_b);

    // Use supplied noise; zero it where t == 0
    auto n = noise.to(device_).to(torch::kFloat32);
    auto zero_mask = (t_b == 0).unsqueeze(2).expand_as(n);
    n.masked_fill_(zero_mask, 0.0f);

    return mu + (0.5f * logvar).exp() * n;
}

}  // namespace diffusion_deploy
