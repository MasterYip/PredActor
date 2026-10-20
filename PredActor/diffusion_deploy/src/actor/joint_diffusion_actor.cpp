/**
 * joint_diffusion_actor.cpp
 *
 * C++ implementation of JointDiffusionActor.
 * Mirrors Python JointDiffusionActor (joint_diffusion.py).
 */
#include "diffusion_deploy/actor/joint_diffusion_actor.hpp"
#include <ATen/record_function.h>
#include <stdexcept>
#include <iostream>
#include <cmath>
#include <optional>
#include <set>
#include <c10/core/InferenceMode.h>

namespace diffusion_deploy {

// ---- Construction ----

JointDiffusionActor::JointDiffusionActor(const std::string& backbone_path,
                                          const std::string& schedule_path,
                                          const JointDiffusionActorConfig& config,
                                          torch::Device device)
    : cfg_(config), device_(device)
{
    if (cfg_.precision != "fp32" && cfg_.precision != "fp16")
        throw std::invalid_argument("[JointDiffusionActor] precision must be fp32 or fp16");
    if (cfg_.precision == "fp16" && !device_.is_cuda())
        throw std::invalid_argument("[JointDiffusionActor] fp16 requires a CUDA device");
    if (cfg_.attention_projection_packing != "none"
        && cfg_.attention_projection_packing != "self"
        && cfg_.attention_projection_packing != "cross"
        && cfg_.attention_projection_packing != "all")
        throw std::invalid_argument(
            "attention_projection_packing must be none, self, cross, or all");
    model_dtype_ = cfg_.precision == "fp16" ? torch::kFloat16 : torch::kFloat32;
    try {
        backbone_ = torch::jit::load(backbone_path, device_);
        backbone_.eval();
        // Jetson's Torch 2.1 loader can leave top-level traced tensor
        // attributes on CPU even when map_location is CUDA. Move the known
        // Transformer inference attributes explicitly; nested parameters are
        // still handled by Module::to().
        backbone_.to(device_, model_dtype_);
        for (const char* name : {"pos_emb", "cond_pos_emb", "mask",
                                 "encoder_mask", "cross_attn_mask"}) {
            if (!backbone_.hasattr(name)) continue;
            auto value = backbone_.attr(name);
            if (!value.isTensor()) continue;
            auto tensor = value.toTensor().to(device_);
            if (tensor.is_floating_point()) tensor = tensor.to(model_dtype_);
            backbone_.setattr(name, tensor);
            if (tensor.device() != device_) {
                throw std::runtime_error(
                    std::string("backbone attribute device migration failed: ") + name);
            }
        }
        if (cfg_.condition_embedding_reuse) {
            try {
                (void)backbone_.get_method("build_condition_embeddings");
                (void)backbone_.get_method("forward_encoded_condition");
                optimized_methods_verified_ = true;
            } catch (const c10::Error&) {
                throw std::runtime_error(
                    "condition_embedding_reuse=true requires a compatible artifact "
                    "with build_condition_embeddings and forward_encoded_condition methods");
            }
        }
    } catch (const c10::Error& e) {
        throw std::runtime_error(
            "[JointDiffusionActor] Failed to load backbone: " + backbone_path +
            "\n  " + e.what());
    }

    load_schedule(schedule_path);
    if (cfg_.ddim_precompute) build_ddim_plan();

    // Cross-attention mask/window consistency: the Python backbone registers
    // `cross_attn_mask` as a buffer whenever cross_attn_window is set or
    // cross_attn_mode != "full" (transformer_codiffuse.py).  It is baked into
    // the exported TorchScript module, so C++ only needs to confirm it is
    // present when the config declares windowed/masked attention — fail loudly
    // if the export lost the mask (silent drift would produce wrong attention).
    const bool expects_mask = (cfg_.cross_attn_window != 0
                               || cfg_.cross_attn_mode != "full");
    bool has_mask = false;
    if (expects_mask) {
        try {
            (void)backbone_.attr("cross_attn_mask");
            has_mask = true;
        } catch (const c10::Error&) {
            has_mask = false;
        }
        if (!has_mask) {
            throw std::runtime_error(
                "[JointDiffusionActor] config declares cross_attn_window/mode "
                "but the exported backbone has no 'cross_attn_mask' buffer; "
                "re-export with --config checkpoint (mask is baked at trace time)");
        }
        const auto mask = backbone_.attr("cross_attn_mask").toTensor();
        std::cout << "[JointDiffusionActor] cross_attn_mask=" << mask.sizes()
                  << " window=" << cfg_.cross_attn_window
                  << " mode=" << cfg_.cross_attn_mode << "\n";
    }

    std::cout << "[JointDiffusionActor] backbone=" << backbone_path
              << "  obs_dim=" << cfg_.obs_dim
              << "  action_dim=" << cfg_.action_dim
              << "  K=" << cfg_.denoising_steps
              << "  precision=" << cfg_.precision
              << "  attention_projection_packing=" << cfg_.attention_projection_packing
              << "  condition_embedding_reuse=" << cfg_.condition_embedding_reuse
              << "  ddim_precompute=" << cfg_.ddim_precompute
              << "  defer_finite_checks=" << cfg_.defer_finite_checks
              << "  inference_mode=" << cfg_.inference_mode
              << "  accel=" << (cfg_.ddim_steps > 0
                  ? "DDIM(steps=" + std::to_string(cfg_.ddim_steps)
                    + ",eta=" + std::to_string(cfg_.ddim_eta) + ")"
                  : "DDPM(full,K=" + std::to_string(cfg_.denoising_steps) + ")")
              << "\n";
}

void JointDiffusionActor::build_ddim_plan() {
    if (cfg_.ddim_steps <= 0)
        throw std::invalid_argument("ddim_precompute requires ddim_steps > 0");
    if (cfg_.ddim_eta != 0.0f)
        throw std::invalid_argument("ddim_precompute currently requires deterministic ddim_eta=0");
    const auto timesteps = build_ddim_timesteps(cfg_.denoising_steps, cfg_.ddim_steps);
    auto acp_cpu = alphas_cumprod_.to(torch::kCPU).contiguous();
    ddim_plan_.clear();
    ddim_plan_.reserve(timesteps.size());
    const int H = cfg_.horizon();
    for (std::size_t i = 0; i < timesteps.size(); ++i) {
        DdimStepPlan plan;
        plan.t_cur = timesteps[i];
        plan.t_prev = (i + 1 < timesteps.size()) ? timesteps[i + 1] : -1;
        const float acp_t = acp_cpu[plan.t_cur].item<float>();
        const float acp_p = plan.t_prev < 0 ? 1.0f : acp_cpu[plan.t_prev].item<float>();
        plan.sqrt_acp_t = std::sqrt(acp_t);
        plan.sqrt_acp_prev = std::sqrt(acp_p);
        plan.sqrt_one_minus_t = std::sqrt(std::max(1.0f - acp_t, 1e-8f));
        plan.sqrt_one_minus_prev = std::sqrt(std::max(1.0f - acp_p, 0.0f));
        auto options = torch::TensorOptions().dtype(torch::kLong).device(device_);
        plan.action_t = torch::full({1, H}, plan.t_cur, options);
        plan.state_t = torch::full({1, H}, plan.t_cur, options);
        plan.state_t_prev = torch::full({1, H}, plan.t_prev, options);
        plan.state_t_denoise = plan.state_t.clone();
        plan.state_t_prev_denoise = plan.state_t_prev.clone();
        // Python JointDiffusionActor.joint_ddim_step always gives the observed
        // prefix clean-time embeddings, including no_state_override=true where
        // the prefix values themselves remain denoised.  This distinction was
        // previously hidden by the NS-DDIM production path and is observable
        // for the scalar-DDIM export.
        plan.state_t_denoise.narrow(1, 0, cfg_.n_obs_steps).fill_(0);
        if (!cfg_.no_state_override) {
            plan.state_t_prev_denoise.narrow(1, 0, cfg_.n_obs_steps).fill_(0);
        }
        ddim_plan_.push_back(std::move(plan));
    }
}

torch::Tensor JointDiffusionActor::build_condition_embeddings(
    const torch::Tensor& condition) {
    RECORD_FUNCTION("task142::condition_encoding", std::vector<c10::IValue>());
    if (!optimized_methods_verified_)
        throw std::runtime_error("Condition methods were not verified");
    timeline_mark("actor/condition_embedding_start");
    auto result = backbone_.get_method("build_condition_embeddings")({condition});
    timeline_mark("actor/condition_embedding_end");
    if (!result.isTensor())
        throw std::runtime_error("build_condition_embeddings must return a Tensor");
    return result.toTensor();
}

void JointDiffusionActor::load_schedule(const std::string& path) {
    try {
        auto mod = torch::jit::load(path, device_);
        auto get = [&](const char* k) -> torch::Tensor {
            return mod.attr(k).toTensor().to(torch::kFloat32).to(device_);
        };
        alphas_cumprod_              = get("alphas_cumprod");
        sqrt_recip_alphas_cumprod_   = get("sqrt_recip_alphas_cumprod");
        sqrt_recipm1_alphas_cumprod_ = get("sqrt_recipm1_alphas_cumprod");
        ddpm_mu_coef1_               = get("ddpm_mu_coef1");
        ddpm_mu_coef2_               = get("ddpm_mu_coef2");
        ddpm_logvar_clipped_         = get("ddpm_logvar_clipped");
        std::cout << "[JointDiffusionActor] Schedule loaded from: " << path << "\n";
    } catch (const std::exception& e) {
        throw std::runtime_error(
            "[JointDiffusionActor] Failed to load DDPM schedule: " + path +
            "\n  " + e.what());
    }
}

void JointDiffusionActor::to(torch::Device device) {
    if (cfg_.precision == "fp16" && !device.is_cuda())
        throw std::invalid_argument("[JointDiffusionActor] fp16 requires a CUDA device");
    device_ = device;
    backbone_.to(device_, model_dtype_);
    auto mv = [&](torch::Tensor& t) { if (t.defined()) t = t.to(device_); };
    mv(alphas_cumprod_);
    mv(sqrt_recip_alphas_cumprod_);
    mv(sqrt_recipm1_alphas_cumprod_);
    mv(ddpm_mu_coef1_);
    mv(ddpm_mu_coef2_);
    mv(ddpm_logvar_clipped_);
    if (cfg_.ddim_precompute) build_ddim_plan();
}

// ---- Static helpers ----

torch::Tensor JointDiffusionActor::extract(const torch::Tensor& a,
                                             const torch::Tensor& t_bh) {
    return a.index({t_bh}).unsqueeze(2);  // [B, H, 1]
}

torch::Tensor JointDiffusionActor::predict_x0_from_epsilon(
    const torch::Tensor& x_t,
    const torch::Tensor& t_bh,
    const torch::Tensor& eps) const
{
    return extract(sqrt_recip_alphas_cumprod_,  t_bh) * x_t
         - extract(sqrt_recipm1_alphas_cumprod_, t_bh) * eps;
}

// ---- backbone_forward() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::backbone_forward(const torch::Tensor& state_traj,
                                       const torch::Tensor& action_traj,
                                       const torch::Tensor& state_t_b,
                                       const torch::Tensor& action_t_b,
                                       const torch::Tensor& cond,
                                       const torch::Tensor& condition_embeddings)
{
    // JointSeqBackbone.forward(x_input, y_input, x_timesteps, y_timesteps, cond)
    // → (x_out, y_out)  where x=state, y=action
    // Condition shape is part of the exported deployment contract. PRDP must
    // never silently replace missing proprioceptive conditioning with zeros.
    torch::Tensor cond_in;
    if (cond.defined() && cond.numel() > 0) {
        cond_in = cond;
        if (cond_in.dim() != 3 || cond_in.size(0) != state_traj.size(0)
            || cond_in.size(1) != cfg_.n_cond_steps
            || cond_in.size(2) != cfg_.backbone_cond_dim) {
            throw std::invalid_argument(
                "[JointDiffusionActor] condition schema mismatch: expected [B," +
                std::to_string(cfg_.n_cond_steps) + "," +
                std::to_string(cfg_.backbone_cond_dim) + "]");
        }
    } else if (cfg_.has_motion_cond && cfg_.backbone_cond_dim > 0) {
        if (cfg_.no_state_override) {
            throw std::invalid_argument(
                "[JointDiffusionActor] PRDP no_state_override requires explicit condition");
        }
        const int B = static_cast<int>(state_traj.size(0));
        cond_in = torch::zeros({B, cfg_.n_cond_steps, cfg_.backbone_cond_dim},
            torch::TensorOptions().dtype(torch::kFloat32).device(device_));
    } else {
        // Model was traced without cond; passing None as IValue
        cond_in = torch::Tensor();  // undefined → not pushed below
    }
    std::vector<torch::jit::IValue> inputs = {
        state_traj.to(model_dtype_), action_traj.to(model_dtype_), state_t_b, action_t_b
    };
    if (cond_in.defined()) {
        inputs.push_back(cond_in.to(model_dtype_));
    }
    RECORD_FUNCTION("task142::backbone", std::vector<c10::IValue>());
    torch::jit::IValue out;
    ++backbone_forward_count_;
    const auto backbone_index = timeline_backbone_index_++;
    timeline_mark("actor/backbone_" + std::to_string(backbone_index) + "_start");
    if (condition_embeddings.defined()) {
        std::vector<torch::jit::IValue> encoded_inputs(inputs.begin(), inputs.begin() + 4);
        encoded_inputs.push_back(condition_embeddings);
        out = backbone_.get_method("forward_encoded_condition")(encoded_inputs);
    } else {
        out = backbone_.forward(inputs);
    }
    timeline_mark("actor/backbone_" + std::to_string(backbone_index) + "_end");

    torch::Tensor state_out, action_out;
    if (out.isTuple()) {
        auto elems = out.toTuple()->elements();
        // Diffusion schedules, WBG/FK and the control boundary remain FP32.
        state_out  = elems[0].toTensor().to(torch::kFloat32);
        action_out = elems[1].toTensor().to(torch::kFloat32);
    } else {
        throw std::runtime_error(
            "[JointDiffusionActor] backbone must return a tuple (state_out, action_out)");
    }
    return {state_out, action_out};
}

torch::Tensor JointDiffusionActor::pre_denoise_guidance(
    const torch::Tensor&, const torch::Tensor& state_traj,
    const torch::Tensor&, const torch::Tensor&, const torch::Tensor&, const torch::Tensor&) {
    return state_traj;
}

// ---- predict_x0() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::predict_x0(const torch::Tensor& action_traj,
                                  const torch::Tensor& state_traj,
                                  const torch::Tensor& action_t_b,
                                  const torch::Tensor& state_t_b,
                                  const torch::Tensor& cond,
                                  const torch::Tensor& condition_embeddings,
                                  bool clip_predictions)
{
    auto [state_out, action_out] = backbone_forward(
        state_traj, action_traj, state_t_b, action_t_b, cond,
        condition_embeddings);
    if (!cfg_.defer_finite_checks
        && (!torch::isfinite(state_out).all().item<bool>()
            || !torch::isfinite(action_out).all().item<bool>()))
        throw std::runtime_error("[JointDiffusionActor] nonfinite backbone output");

    torch::Tensor action_pred = cfg_.action_pred_epsilon
        ? predict_x0_from_epsilon(action_traj, action_t_b, action_out) : action_out;
    torch::Tensor state_pred  = cfg_.state_pred_epsilon
        ? predict_x0_from_epsilon(state_traj,  state_t_b,  state_out)  : state_out;

    if (clip_predictions) {
        action_pred.clamp_(-cfg_.denoised_clip, cfg_.denoised_clip);
        state_pred.clamp_(-cfg_.denoised_clip, cfg_.denoised_clip);
    }
    return {action_pred, state_pred};
}

// ---- build_ddim_timesteps() ----

std::vector<int> JointDiffusionActor::build_ddim_timesteps(int K, int ddim_steps) {
    std::vector<int> ts;
    if (K <= 0 || ddim_steps <= 0) return ts;
    if (ddim_steps == 1) return {K - 1};
    if (ddim_steps >= K) {
        for (int t = K - 1; t >= 0; --t) ts.push_back(t);
        return ts;
    }
    std::set<int> seen;
    for (int i = 0; i < ddim_steps; ++i) {
        double frac = static_cast<double>(i) / (ddim_steps - 1);
        int t = static_cast<int>(std::round(frac * (K - 1)));
        seen.insert(t);
    }
    for (auto it = seen.rbegin(); it != seen.rend(); ++it) ts.push_back(*it);
    return ts;
}

// ---- joint_ddim_step() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::joint_ddim_step(torch::Tensor action_traj,
                                       torch::Tensor state_traj,
                                       const torch::Tensor& nobs,
                                       int t_cur,
                                       int t_prev,
                                       float eta,
                                       const torch::Tensor& cond,
                                       const torch::Tensor& condition_embeddings,
                                       const DdimStepPlan* plan)
{
    const int B      = static_cast<int>(action_traj.size(0));
    const int H      = static_cast<int>(action_traj.size(1));
    const int n_past = cfg_.n_obs_steps;

    // Build [B, H] timestep tensors (full levels for the guidance hook; the
    // past positions are zeroed only for the DDIM step itself, not for the
    // guidance hook — Python DiffuseCLoC._apply_classifier_guidance runs on
    // the non-inpainted trajectory with the raw (H,) schedule).
    auto a_t_b = plan ? plan->action_t : torch::full({B, H}, t_cur,
        torch::TensorOptions().dtype(torch::kLong).device(device_));
    auto s_t_b = plan ? plan->state_t : torch::full({B, H}, t_cur,
        torch::TensorOptions().dtype(torch::kLong).device(device_)).clone();
    auto s_t_prev_b = plan ? plan->state_t_prev : torch::full({B, H}, t_prev,
        torch::TensorOptions().dtype(torch::kLong).device(device_));

    // Classifier guidance on the current (non-inpainted) trajectory.
    state_traj = state_traj.clone();
    state_traj = pre_denoise_guidance(
        action_traj, state_traj, a_t_b, s_t_b, s_t_prev_b, cond);

    // Match Python scalar DDIM: prefix timestep embeddings are clean even when
    // no_state_override leaves the corresponding state values denoised.
    if (plan) {
        s_t_b = plan->state_t_denoise;
    } else {
        s_t_b.narrow(1, 0, n_past).fill_(0);
    }

    // Inpaint prefix values only when state override is active.
    if (!cfg_.no_state_override) {
        state_traj.narrow(1, 0, n_past).copy_(nobs);
        if (plan) {
            s_t_prev_b = plan->state_t_prev_denoise;
        } else {
            s_t_prev_b.narrow(1, 0, n_past).fill_(0);
        }
    }

    // Predict x0 for both streams
    auto [action_pred, state_pred] = predict_x0(
        action_traj, state_traj, a_t_b, s_t_b, cond, condition_embeddings);

    return joint_ddim_step_from_predictions(
        action_traj, state_traj, nobs, t_cur, t_prev, eta,
        action_pred, state_pred, plan);
}

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::joint_ddim_step_from_predictions(
    torch::Tensor action_traj,
    torch::Tensor state_traj,
    const torch::Tensor& nobs,
    int t_cur,
    int t_prev,
    float eta,
    const torch::Tensor& action_pred,
    const torch::Tensor& state_pred,
    const DdimStepPlan* plan)
{
    timeline_mark("actor/scheduler_start");
    const int n_past = cfg_.n_obs_steps;
    if (!cfg_.defer_finite_checks
        && (!torch::isfinite(action_pred).all().item<bool>()
            || !torch::isfinite(state_pred).all().item<bool>()))
        throw std::runtime_error(
            "[JointDiffusionActor] nonfinite supplied x0 prediction");

    // DDIM formula (scalar schedule)
    float acp_t = plan ? 0.0f : alphas_cumprod_[t_cur].item<float>();
    float acp_p = plan ? 0.0f : ((t_prev < 0) ? 1.0f : alphas_cumprod_[t_prev].item<float>());
    float sqrt_acp_t = plan ? plan->sqrt_acp_t : std::sqrt(acp_t);
    float sqrt_acp_p = plan ? plan->sqrt_acp_prev : std::sqrt(acp_p);
    float sqrt_1m_t  = plan ? plan->sqrt_one_minus_t : std::sqrt(std::max(1.0f - acp_t, 1e-8f));
    float sqrt_1m_p  = plan ? plan->sqrt_one_minus_prev : std::sqrt(1.0f - acp_p);

    auto eps_a = (action_traj - sqrt_acp_t * action_pred) / sqrt_1m_t;
    auto eps_s = (state_traj  - sqrt_acp_t * state_pred)  / sqrt_1m_t;

    torch::Tensor new_action, new_state;
    if (eta == 0.0f) {
        new_action = sqrt_acp_p * action_pred + sqrt_1m_p * eps_a;
        new_state  = sqrt_acp_p * state_pred  + sqrt_1m_p * eps_s;
    } else {
        float sigma_sq = eta * eta
                       * (1.0f - acp_p) / std::max(1.0f - acp_t, 1e-8f)
                       * std::max(1.0f - acp_t / std::max(acp_p, 1e-8f), 0.0f);
        float sigma    = std::sqrt(sigma_sq);
        float dir_coef = std::sqrt(std::max(1.0f - acp_p - sigma_sq, 0.0f));
        auto noise_a = (t_cur == 0) ? torch::zeros_like(action_traj) : torch::randn_like(action_traj);
        auto noise_s = (t_cur == 0) ? torch::zeros_like(state_traj)  : torch::randn_like(state_traj);
        new_action = sqrt_acp_p * action_pred + dir_coef * eps_a + sigma * noise_a;
        new_state  = sqrt_acp_p * state_pred  + dir_coef * eps_s + sigma * noise_s;
    }

    if (!cfg_.no_state_override)
        new_state.narrow(1, 0, n_past).copy_(nobs);
    timeline_mark("actor/scheduler_end");
    return {new_action, new_state};
}

// ---- per_position_ddim_step() ----

torch::Tensor JointDiffusionActor::per_position_ddim_step(
    const torch::Tensor& x_t,
    const torch::Tensor& x0_pred,
    const torch::Tensor& t_cur,
    const torch::Tensor& t_prev,
    float eta,
    const torch::Tensor& alphas_cumprod,
    int64_t denoising_steps)
{
    const int64_t B = x_t.size(0);
    const int64_t H = x_t.size(1);
    const int64_t D = x_t.size(2);
    const int64_t K = denoising_steps;

    auto t_cur_clamped  = t_cur.clamp(0, K - 1);
    auto t_prev_clamped = t_prev.clamp(0, K - 1);
    auto is_final       = (t_prev < 0);  // [H] bool

    auto acp_t    = alphas_cumprod.index({t_cur_clamped}).view({1, H, 1});
    auto acp_prev = alphas_cumprod.index({t_prev_clamped}).view({1, H, 1});
    if (is_final.any().item<bool>()) {
        acp_prev = acp_prev.clone();
        acp_prev[0].narrow(1, 0, 1).masked_fill_(is_final.unsqueeze(1), 1.0);
    }

    auto sqrt_acp_t   = acp_t.sqrt();
    auto sqrt_acp_prev = acp_prev.sqrt();
    auto sqrt_1m_t    = (1.0 - acp_t).sqrt();
    auto sqrt_1m_p    = (1.0 - acp_prev).sqrt();
    auto eps_hat      = (x_t - sqrt_acp_t * x0_pred) / sqrt_1m_t.clamp_min(1e-8);

    if (eta == 0.0f) {
        return sqrt_acp_prev * x0_pred + sqrt_1m_p * eps_hat;
    }
    auto ratio     = (1.0 - acp_t / acp_prev.clamp_min(1e-8)).clamp_min(0.0);
    auto sigma_sq  = eta * eta * (1.0 - acp_prev)
                   / (1.0 - acp_t).clamp_min(1e-8) * ratio;
    auto sigma     = sigma_sq.sqrt();
    auto dir_coef  = (1.0 - acp_prev - sigma_sq).clamp_min(0.0).sqrt();
    auto noise     = torch::randn_like(x_t);
    auto zero_mask = (t_cur == 0).view({1, H, 1}).expand({B, H, D});
    noise.masked_fill_(zero_mask, 0.0f);
    return sqrt_acp_prev * x0_pred + dir_coef * eps_hat + sigma * noise;
}

// ---- joint_ns_ddim_step() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::joint_ns_ddim_step(torch::Tensor action_traj,
                                         torch::Tensor state_traj,
                                         const torch::Tensor& nobs,
                                         const torch::Tensor& a_t_cur,
                                         const torch::Tensor& a_t_prev,
                                         const torch::Tensor& s_t_cur,
                                         const torch::Tensor& s_t_prev,
                                         float eta,
                                         const torch::Tensor& cond)
{
    const int B      = static_cast<int>(action_traj.size(0));
    const int H      = static_cast<int>(action_traj.size(1));
    const int n_past = cfg_.n_obs_steps;

    // Mirror Python JointDiffusionActor.joint_ns_ddim_step: inpaint past
    // states, build [B,H] timesteps from the per-position (H,) vectors, run
    // the per-position NoiseScheduler DDIM step, then restore inpainting.
    state_traj = state_traj.clone();
    if (!cfg_.no_state_override)
        state_traj.narrow(1, 0, n_past).copy_(nobs);

    auto a_t_b = a_t_cur.unsqueeze(0).expand({B, H}).to(device_);
    auto s_t_b = s_t_cur.unsqueeze(0).expand({B, H}).to(device_);

    auto [action_pred, state_pred] = predict_x0(
        action_traj, state_traj, a_t_b, s_t_b, cond);
    return joint_ns_ddim_step_from_predictions(
        action_traj, state_traj, nobs,
        a_t_cur, a_t_prev, s_t_cur, s_t_prev, eta,
        action_pred, state_pred);
}

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::joint_ns_ddim_step_from_predictions(
    torch::Tensor action_traj,
    torch::Tensor state_traj,
    const torch::Tensor& nobs,
    const torch::Tensor& a_t_cur,
    const torch::Tensor& a_t_prev,
    const torch::Tensor& s_t_cur,
    const torch::Tensor& s_t_prev,
    float eta,
    const torch::Tensor& action_pred_in,
    const torch::Tensor& state_pred_in)
{
    RECORD_FUNCTION("task142::scheduler_update", std::vector<c10::IValue>());
    timeline_mark("actor/scheduler_start");
    const int n_past = cfg_.n_obs_steps;
    auto action_pred = action_pred_in.clamp(
        -cfg_.denoised_clip, cfg_.denoised_clip);
    auto state_pred = state_pred_in.clamp(
        -cfg_.denoised_clip, cfg_.denoised_clip);

    auto new_action = per_position_ddim_step(
        action_traj, action_pred, a_t_cur, a_t_prev, eta,
        alphas_cumprod_, cfg_.denoising_steps);
    auto new_state = per_position_ddim_step(
        state_traj, state_pred, s_t_cur, s_t_prev, eta,
        alphas_cumprod_, cfg_.denoising_steps);

    if (!cfg_.no_state_override)
        new_state.narrow(1, 0, n_past).copy_(nobs);
    timeline_mark("actor/scheduler_end");
    return {new_action, new_state};
}

// ---- mean_var_from_x0() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::mean_var_from_x0(const torch::Tensor& x_t,
                                        const torch::Tensor& t_bh,
                                        const torch::Tensor& x0_pred) const
{
    auto mu     = extract(ddpm_mu_coef1_, t_bh) * x0_pred
                + extract(ddpm_mu_coef2_, t_bh) * x_t;
    auto logvar = extract(ddpm_logvar_clipped_, t_bh);
    return {mu, logvar};
}

// ---- diffuse_step() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::diffuse_step(const torch::Tensor& nobs,
                                    torch::Tensor action_traj,
                                    torch::Tensor state_traj,
                                    const torch::Tensor& action_t,
                                    const torch::Tensor& state_t,
                                    const torch::Tensor& cond)
{
    const int B      = static_cast<int>(action_traj.size(0));
    const int H      = static_cast<int>(action_traj.size(1));
    const int n_past = cfg_.n_obs_steps;

    // Build batch timestep tensors [B, H] (full levels for the guidance hook).
    auto action_t_b = action_t.unsqueeze(0).expand({B, H}).to(device_);
    auto state_t_b  = state_t .unsqueeze(0).expand({B, H}).to(device_);

    // Classifier guidance on the current (non-inpainted) trajectory — matches
    // Python DiffuseCLoC.diffuse_step which applies guidance before inpainting.
    state_traj = pre_denoise_guidance(
        action_traj, state_traj, action_t_b, state_t_b, {}, cond);
    if (!torch::isfinite(state_traj).all().item<bool>()
        || !torch::isfinite(action_traj).all().item<bool>()
        || !torch::isfinite(cond).all().item<bool>())
        throw std::runtime_error("[JointDiffusionActor] nonfinite backbone input");

    // --- Inpainting: replace past state with clean nobs ---
    // state_traj[:, :n_past] = nobs; zero those timesteps for the DDPM step.
    if (!cfg_.no_state_override) {
        state_traj.narrow(1, 0, n_past).copy_(nobs);
        state_t_b = state_t_b.clone();
        state_t_b.narrow(1, 0, n_past).fill_(0);
    }

    // --- Backbone predict_x0 ---
    auto [state_out, action_out] = backbone_forward(
        state_traj, action_traj, state_t_b, action_t_b, cond);
    if (!torch::isfinite(state_out).all().item<bool>()
        || !torch::isfinite(action_out).all().item<bool>())
        throw std::runtime_error("[JointDiffusionActor] nonfinite DDPM backbone output");

    // Convert epsilon → x0 if needed
    torch::Tensor state_pred, action_pred;
    if (cfg_.state_pred_epsilon) {
        state_pred  = predict_x0_from_epsilon(state_traj,  state_t_b,  state_out);
    } else {
        state_pred  = state_out;
    }
    if (cfg_.action_pred_epsilon) {
        action_pred = predict_x0_from_epsilon(action_traj, action_t_b, action_out);
    } else {
        action_pred = action_out;
    }

    return diffuse_step_from_predictions(
        action_traj, state_traj, action_t_b, state_t_b,
        action_pred, state_pred);
}

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::diffuse_step_from_predictions(
    torch::Tensor action_traj,
    torch::Tensor state_traj,
    const torch::Tensor& action_t_b,
    const torch::Tensor& state_t_b,
    const torch::Tensor& action_pred_in,
    const torch::Tensor& state_pred_in)
{
    auto action_pred = action_pred_in.clamp(
        -cfg_.denoised_clip, cfg_.denoised_clip);
    auto state_pred = state_pred_in.clamp(
        -cfg_.denoised_clip, cfg_.denoised_clip);
    if (!torch::isfinite(state_pred).all().item<bool>()
        || !torch::isfinite(action_pred).all().item<bool>())
        throw std::runtime_error(
            "[JointDiffusionActor] nonfinite clipped prediction clip="
            + std::to_string(cfg_.denoised_clip));

    // --- DDPM posterior mean + logvar ---
    auto [action_mu, action_logvar] = mean_var_from_x0(action_traj, action_t_b, action_pred);
    auto [state_mu,  state_logvar]  = mean_var_from_x0(state_traj,  state_t_b,  state_pred);
    const bool action_mu_finite = torch::isfinite(action_mu).all().item<bool>();
    const bool state_mu_finite = torch::isfinite(state_mu).all().item<bool>();
    if (!action_mu_finite || !state_mu_finite)
        throw std::runtime_error(
            "[JointDiffusionActor] nonfinite posterior mean action="
            + std::to_string(action_mu_finite) + " state="
            + std::to_string(state_mu_finite));

    // --- Stochastic sample: no noise at t=0 ---
    auto action_noise = torch::randn_like(action_traj);
    action_noise.masked_fill_((action_t_b == 0).unsqueeze(2).expand_as(action_noise), 0.0f);

    auto state_noise  = torch::randn_like(state_traj);
    state_noise.masked_fill_((state_t_b == 0).unsqueeze(2).expand_as(state_noise), 0.0f);

    auto new_action = action_mu + (0.5f * action_logvar).exp() * action_noise;
    auto new_state  = state_mu  + (0.5f * state_logvar ).exp() * state_noise;

    return {new_action, new_state};
}

// ---- act() / act_joint() ----

std::pair<torch::Tensor, torch::Tensor>
JointDiffusionActor::act_joint(const torch::Tensor& nobs_norm,
                                 const torch::Tensor& cond_norm)
{
    torch::NoGradGuard ng;
    std::optional<c10::InferenceMode> inference_guard;
    if (cfg_.inference_mode && !c10::InferenceMode::is_enabled())
        inference_guard.emplace(true);

    auto nobs = nobs_norm.to(device_).to(torch::kFloat32);
    if (nobs.dim() != 3 || nobs.size(1) < cfg_.n_obs_steps
        || nobs.size(2) != cfg_.obs_dim) {
        throw std::invalid_argument(
            "[JointDiffusionActor] observation schema mismatch: expected [B,>=n_obs_steps,obs_dim]");
    }
    nobs = nobs.narrow(1, 0, cfg_.n_obs_steps);

    torch::Tensor cond;
    if (cond_norm.defined() && cond_norm.numel() > 0) {
        cond = cond_norm.to(device_).to(torch::kFloat32);
    }

    if (cfg_.defer_finite_checks) {
        auto finite = torch::isfinite(nobs).all();
        if (cond.defined()) finite = torch::logical_and(finite, torch::isfinite(cond).all());
        if (!finite.item<bool>())
            throw std::invalid_argument("[JointDiffusionActor] nonfinite optimized input");
    }

    const int B  = static_cast<int>(nobs.size(0));
    const int H  = cfg_.horizon();
    const int Do = cfg_.obs_dim;
    const int Da = cfg_.action_dim;
    const int K  = cfg_.denoising_steps;
    if (cfg_.ddim_precompute && B != 1)
        throw std::invalid_argument("ddim_precompute requires static batch size B=1");

    torch::Tensor condition_embeddings;
    if (cfg_.condition_embedding_reuse) {
        if (!cond.defined())
            throw std::invalid_argument("condition_embedding_reuse requires condition input");
        condition_embeddings = build_condition_embeddings(cond.to(model_dtype_));
    }

    auto action_traj = torch::randn({B, H, Da},
        torch::TensorOptions().dtype(torch::kFloat32).device(device_));
    auto state_traj  = torch::randn({B, H, Do},
        torch::TensorOptions().dtype(torch::kFloat32).device(device_));

    // ---- DDIM path ----
    if (cfg_.ddim_steps > 0) {
        auto ts = build_ddim_timesteps(K, cfg_.ddim_steps);
        for (int i = 0; i < static_cast<int>(ts.size()); ++i) {
            int t_cur  = ts[i];
            int t_prev = (i + 1 < static_cast<int>(ts.size())) ? ts[i + 1] : -1;
            const DdimStepPlan* plan = cfg_.ddim_precompute ? &ddim_plan_.at(i) : nullptr;
            auto [new_action, new_state] = joint_ddim_step(
                action_traj, state_traj, nobs, t_cur, t_prev, cfg_.ddim_eta, cond,
                condition_embeddings, plan);
            action_traj = new_action;
            state_traj  = new_state;
        }
        if (cfg_.defer_finite_checks
            && !torch::logical_and(torch::isfinite(action_traj).all(),
                                   torch::isfinite(state_traj).all()).item<bool>())
            throw std::runtime_error("[JointDiffusionActor] nonfinite optimized output");
        return {action_traj, state_traj};
    }

    // ---- DDPM path (default) ----
    // t_all[i] shape [H]: all positions share the same global timestep t = K-1-i
    for (int i = 0; i < K; ++i) {
        int t_val = K - 1 - i;
        auto action_t = torch::full({H}, t_val,
            torch::TensorOptions().dtype(torch::kLong).device(device_));
        auto state_t  = torch::full({H}, t_val,
            torch::TensorOptions().dtype(torch::kLong).device(device_));

        auto [new_action, new_state] = diffuse_step(
            nobs, action_traj, state_traj, action_t, state_t, cond);
        action_traj = new_action;
        state_traj  = new_state;
    }

    return {action_traj, state_traj};
}

torch::Tensor JointDiffusionActor::act(const torch::Tensor& nobs_norm,
                                         const torch::Tensor& cond_norm) {
    return act_joint(nobs_norm, cond_norm).first;
}

}  // namespace diffusion_deploy
