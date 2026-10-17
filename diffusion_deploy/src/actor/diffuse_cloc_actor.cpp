/**
 * diffuse_cloc_actor.cpp
 *
 * C++ implementation of DiffuseCLoCActor.
 * Mirrors Python DiffuseCLoC (diffuse_cloc.py).
 */
#include "diffusion_deploy/actor/diffuse_cloc_actor.hpp"
#include "diffusion_deploy/utils/action_selection.hpp"
#include <ATen/record_function.h>
#include <stdexcept>
#include <iostream>
#include <algorithm>
#include <optional>

namespace diffusion_deploy {

namespace {

torch::Tensor right_project(const torch::Tensor& values,
                            const torch::Tensor& matrix) {
#if defined(__aarch64__)
    // NVIDIA's JP5 Torch 2.1 CPU build returns nonfinite values for this
    // finite 3-D x 2-D matmul. Keep CUDA on its fast GEMM path; only avoid
    // the defective ARM CPU backend.
    if (values.device().is_cpu()) {
        TORCH_CHECK(values.dim() == 3 && matrix.dim() == 2,
                    "right_project expects [B,H,D] x [D,O]");
        return (values.unsqueeze(-1) * matrix.unsqueeze(0).unsqueeze(0)).sum(-2);
    }
#endif
    return torch::matmul(values, matrix);
}

}  // namespace

// ---- Construction ----

DiffuseCLoCActor::DiffuseCLoCActor(const std::string& backbone_path,
                                    const std::string& schedule_path,
                                    const std::string& emphasis_path,
                                    const DiffuseCLoCActorConfig& config,
                                    torch::Device device)
    : JointDiffusionActor(backbone_path, schedule_path, config, device)
    , cloc_cfg_(config)
{
    if (cloc_cfg_.classifier_guidance_impl != "duplicate_backbone"
        && cloc_cfg_.classifier_guidance_impl != "reuse_x0")
        throw std::invalid_argument(
            "[DiffuseCLoCActor] classifier_guidance_impl must be "
            "duplicate_backbone or reuse_x0");
    load_emphasis(emphasis_path);
    if (cfg_.ddim_precompute && cloc_cfg_.sampler_mode == "ns_ddim")
        build_ns_ddim_plan();
    if (cloc_cfg_.guidance.enabled) {
        guidance_ = std::make_unique<WholeBodyGuidance>(cloc_cfg_.guidance, device_);
        const auto& g = cloc_cfg_.guidance;
        std::cout << "[DiffuseCLoCActor] WBG enabled"
                  << " mode=" << g.mode
                  << " trajectory=" << g.trajectory_mode
                  << " dt=" << g.dt
                  << " zeta_comp=" << g.enable_zeta_comp
                  << " damping_comp=" << g.enable_damping_comp
                  << " vx=" << (g.vx.enabled ? g.vx.command : 0.0f)
                  << " vy=" << (g.vy.enabled ? g.vy.command : 0.0f)
                  << " wz=" << (g.wz.enabled ? g.wz.command : 0.0f) << "\n";
    }

    std::cout << "[DiffuseCLoCActor] emphasis_mat=[" << emphasis_mat_.size(0)
              << "," << emphasis_mat_.size(1) << "]"
              << "  action_schedule=" << cloc_cfg_.action_schedule
              << "  state_schedule="  << cloc_cfg_.state_schedule
              << "  accel=" << (cfg_.ddim_steps > 0
                  ? "DDIM(steps=" + std::to_string(cfg_.ddim_steps)
                    + ",eta=" + std::to_string(cfg_.ddim_eta) + ")"
                  : "DDPM(full,K=" + std::to_string(cfg_.denoising_steps) + ")")
              << "  classifier_guidance_impl="
              << cloc_cfg_.classifier_guidance_impl
              << "\n";
}

void DiffuseCLoCActor::load_emphasis(const std::string& path) {
    try {
        auto mod = torch::jit::load(path, device_);
        emphasis_mat_ = mod.attr("emphasis_mat").toTensor()
                            .to(device_, torch::kFloat32).clone().contiguous();
        emphasis_mat_inv_ = mod.attr("emphasis_mat_inv").toTensor()
                                .to(device_, torch::kFloat32).clone().contiguous();
        if (!torch::isfinite(emphasis_mat_).all().item<bool>() ||
            !torch::isfinite(emphasis_mat_inv_).all().item<bool>()) {
            throw std::runtime_error("emphasis matrices contain nonfinite values");
        }
        std::cout << "[DiffuseCLoCActor] Emphasis matrices loaded from: " << path << "\n";
    } catch (const std::exception& e) {
        throw std::runtime_error(
            "[DiffuseCLoCActor] Failed to load emphasis matrices: " + path +
            "\n  " + e.what());
    }
}

void DiffuseCLoCActor::to(torch::Device device) {
    JointDiffusionActor::to(device);
    if (emphasis_mat_.defined())     emphasis_mat_     = emphasis_mat_.to(device);
    if (emphasis_mat_inv_.defined()) emphasis_mat_inv_ = emphasis_mat_inv_.to(device);
    if (action_rolling_traj_.defined()) action_rolling_traj_ = action_rolling_traj_.to(device);
    if (state_rolling_traj_.defined())  state_rolling_traj_  = state_rolling_traj_.to(device);
    if (guidance_) guidance_->to(device);
    if (cfg_.ddim_precompute && cloc_cfg_.sampler_mode == "ns_ddim")
        build_ns_ddim_plan();
}

void DiffuseCLoCActor::build_ns_ddim_plan() {
    const int T = cfg_.denoising_steps;
    const int H = cfg_.horizon();
    const int n_past = cfg_.n_obs_steps;
    const auto opts = torch::TensorOptions().dtype(torch::kLong).device(device_);
    std::vector<NSDdimStepPlan> full;
    full.reserve(T);
    for (int t = T - 1; t >= 0; --t) {
        auto action_cur = torch::full({H}, t, opts);
        auto action_prev = torch::full({H}, t - 1, opts);
        auto state_cur = action_cur.clone();
        auto state_prev = action_prev.clone();
        if (!cfg_.no_state_override) {
            state_cur.narrow(0, 0, n_past).fill_(0);
            state_prev.narrow(0, 0, n_past).fill_(0);
        }
        full.push_back({action_cur, action_prev, state_cur, state_prev});
    }
    ns_ddim_plan_.clear();
    for (int index : uniform_indices(T, cfg_.ddim_steps))
        ns_ddim_plan_.push_back(full.at(index));
    for (std::size_t i = 0; i + 1 < ns_ddim_plan_.size(); ++i) {
        ns_ddim_plan_[i].action_prev = ns_ddim_plan_[i + 1].action_cur;
        ns_ddim_plan_[i].state_prev = ns_ddim_plan_[i + 1].state_cur;
    }
}

void DiffuseCLoCActor::reset_rolling() {
    has_rolling_         = false;
    action_rolling_traj_ = torch::Tensor();
    state_rolling_traj_  = torch::Tensor();
}

void DiffuseCLoCActor::apply_live_wbg(const WbgUdpFrame& frame) {
    if (guidance_) guidance_->apply_live_udp(frame);
}

void DiffuseCLoCActor::set_live_wbg_command_bounds(float max_vx, float max_vy,
                                                   float max_wz) {
    if (guidance_) guidance_->set_live_command_bounds(max_vx, max_vy, max_wz);
}

torch::Tensor DiffuseCLoCActor::pre_denoise_guidance(
    const torch::Tensor& action_traj,
    const torch::Tensor& state_traj,
    const torch::Tensor& action_t_b,
    const torch::Tensor& state_t_b,
    const torch::Tensor& state_t_prev_b,
    const torch::Tensor& cond) {
    if (!guidance_ || !guidance_->enabled()) return state_traj;
    auto predictions = predict_x0(
        action_traj, state_traj, action_t_b, state_t_b, cond);
    RECORD_FUNCTION("task142::wbg_fk_gradient", std::vector<c10::IValue>());
    timeline_mark("actor/wbg_start");
    auto guided = state_traj - guidance_->gradient(
        predictions.second, emphasis_mat_inv_, state_t_b, state_t_prev_b);
    timeline_mark("actor/wbg_end");
    return guided;
}

// ---- generate_denoising_matrix() ----

std::pair<torch::Tensor, int>
DiffuseCLoCActor::decreasing_matrix(int start_value, bool is_state, int step_size) const {
    const int K = cfg_.denoising_steps;
    const int H = cfg_.horizon();
    const int Nf = cfg_.n_future_steps;

    int end;
    if (step_size == 1) {
        end = is_state ? start_value + Nf : start_value + Nf + 1;
    } else {
        end = K + step_size;
    }

    // first_row = arange(start_value, end, step_size)
    int n_cols = static_cast<int>(std::ceil((double)(end - start_value) / step_size));
    auto first_row = torch::arange(start_value, end, step_size,
                                    torch::TensorOptions().dtype(torch::kLong));

    int m = start_value + 1;
    // decrement_column = -arange(m) shape [m, 1]
    auto decrement = -torch::arange(m, torch::TensorOptions().dtype(torch::kLong))
                      .view({m, 1});

    // broadcast: [m, n_cols]
    auto matrix = first_row.unsqueeze(0).expand({m, n_cols}) + decrement;
    matrix = torch::clamp(matrix, 0, K - 1);

    int n_pad = H - static_cast<int>(matrix.size(1));
    return {matrix.to(device_), n_pad};
}

torch::Tensor DiffuseCLoCActor::generate_denoising_matrix(const std::string& schedule,
                                                            bool is_state) const {
    const int K = cfg_.denoising_steps;
    const int H = cfg_.horizon();
    const int Nf = cfg_.n_future_steps;
    const int n_past = cfg_.n_obs_steps;

    if (schedule == "full") {
        // [K, H]: row i all equal to K-1-i (Python does not zero past here;
        // past timesteps are zeroed inside the denoising step instead).
        auto t = torch::flip(torch::arange(K, torch::TensorOptions().dtype(torch::kLong)),
                              {0});
        return t.unsqueeze(1).repeat({1, H}).to(device_);

    } else if (schedule == "full_decreasing") {
        auto [mat, n] = decreasing_matrix(K - 1, is_state, 1);
        auto pad_col = mat.narrow(1, 0, 1).repeat({1, n});
        auto out = torch::cat({pad_col, mat}, /*dim=*/1);
        // Mirror Python _build_noise_matrix: past positions are clean (t=0).
        out.narrow(1, 0, n_past).fill_(0);
        return out.to(device_);

    } else if (schedule.find("from_xT_decreasing") != std::string::npos
               || schedule.find("from_xt_decreasing") != std::string::npos) {
        int start;
        if (is_state) {
            start = std::max(K - Nf, 0);
        } else {
            start = std::max(K - 8 - 1, 0);
        }
        auto [mat, n] = decreasing_matrix(start, is_state, 1);
        auto pad_col = mat.narrow(1, 0, 1).repeat({1, n});
        auto out = torch::cat({pad_col, mat}, /*dim=*/1);
        out.narrow(1, 0, n_past).fill_(0);
        return out.to(device_);

    } else if (schedule.find("from_xT_step") != std::string::npos
               || schedule.find("from_xt_step") != std::string::npos) {
        int start     = 14;
        int step_size = 10;
        auto [mat, n] = decreasing_matrix(start, is_state, step_size);
        auto pad_col = mat.narrow(1, 0, 1).repeat({1, n});
        auto out = torch::cat({pad_col, mat}, /*dim=*/1);
        out.narrow(1, 0, n_past).fill_(0);
        return out.to(device_);

    } else {
        throw std::invalid_argument(
            "[DiffuseCLoCActor] Unknown schedule: " + schedule);
    }
}

std::vector<int> DiffuseCLoCActor::terminal_action_noise_levels() const {
    const int H = cfg_.horizon();
    if (cloc_cfg_.sampler_mode != "rolling_ddim"
        && cloc_cfg_.sampler_mode != "rolling_ddpm")
        return std::vector<int>(static_cast<size_t>(H), 0);
    auto terminal = generate_denoising_matrix(
        cloc_cfg_.action_schedule, false).index({-1}).to(torch::kCPU);
    std::vector<int> levels(static_cast<size_t>(H));
    for (int i = 0; i < H; ++i) {
        int level = terminal[i].item<int>();
        if (cloc_cfg_.sampler_mode == "rolling_ddpm")
            level = std::max(level - 1, 0);
        levels[static_cast<size_t>(i)] = level;
    }
    for (int endpoint : action_selection_clean_endpoints_)
        levels[static_cast<size_t>(endpoint)] = 0;
    return levels;
}

void DiffuseCLoCActor::configure_action_selection(double delay_action_step) {
    const auto selection = action_selection(
        cfg_.n_obs_steps - 1, delay_action_step, cfg_.horizon(),
        std::vector<int>(static_cast<size_t>(cfg_.horizon()), 0));
    action_selection_clean_endpoints_ = {selection.lower_index};
    if (selection.upper_index != selection.lower_index)
        action_selection_clean_endpoints_.push_back(selection.upper_index);
}

std::vector<int> DiffuseCLoCActor::uniform_indices(int total, int n) {
    if (n >= total) {
        std::vector<int> all(total);
        for (int i = 0; i < total; ++i) all[i] = i;
        return all;
    }
    if (n == 1) return {0};
    std::vector<int> out;
    out.reserve(n);
    const double step = static_cast<double>(total - 1) / (n - 1);
    for (int i = 0; i < n; ++i)
        out.push_back(static_cast<int>(std::lround(i * step)));
    return out;
}

// ---- get_rolling_traj() ----

torch::Tensor DiffuseCLoCActor::get_rolling_traj(
    const std::vector<std::pair<torch::Tensor, torch::Tensor>>& chain,
    const torch::Tensor& t_all) const
{
    // Mirrors Python exactly:
    //   traj = stack([c[0] for c in chain], dim=1)[:,:,1:,:]  # [B, K, H-1, D]
    //   idx  = stack([c[1] for c in chain])[:,1:]              # [K, H-1]
    //   needed_idx = t_all[0, :-1] + 1                         # [H-1]
    //   mask = idx == needed_idx                               # [K, H-1]  (broadcast)
    //   mask = logical_xor(mask, (mask.roll(-1,0)==mask) & mask)
    //   traj = traj[:,mask]                                    # [B, H-1, D]
    //         (2D bool mask on dims [1,2] of a 4D tensor → selects K*(H-1) entries
    //          with exactly H-1 True, giving [B, H-1, D])

    if (chain.empty())
        throw std::runtime_error("[DiffuseCLoCActor] get_rolling_traj: empty chain");

    // --- stack traj and t ---
    std::vector<torch::Tensor> traj_list, t_list;
    for (const auto& [tr, tv] : chain) {
        traj_list.push_back(tr.unsqueeze(1));  // [B, 1, H, D]
        t_list   .push_back(tv.unsqueeze(0));  // [1, H]
    }
    auto traj_stacked = torch::cat(traj_list, 1);  // [B, K, H, D]
    auto t_stacked    = torch::cat(t_list,    0);  // [K, H]

    const int64_t B   = traj_stacked.size(0);
    const int64_t K   = traj_stacked.size(1);
    const int64_t H   = traj_stacked.size(2);
    const int64_t D   = traj_stacked.size(3);
    const int64_t Hm1 = H - 1;

    // Slice positions [1..H-1]
    auto traj_slice = traj_stacked.narrow(2, 1, Hm1);  // [B, K, H-1, D]
    auto t_slice    = t_stacked   .narrow(1, 1, Hm1);  // [K, H-1]

    // needed_idx = t_all[0, :-1] + 1   [H-1]
    auto needed = t_all.index({0, torch::indexing::Slice(0, -1)}) + 1;  // [H-1]

    // mask[k, h] = (t_slice[k,h] == needed[h])   [K, H-1]
    auto mask = (t_slice == needed.unsqueeze(0)).to(torch::kBool);

    // XOR to keep first occurrence per column
    auto rolled   = torch::roll(mask, -1, 0);
    auto mask_xor = torch::logical_xor(mask, torch::logical_and(rolled == mask, mask));
    // mask_xor: [K, H-1]  — exactly one True per column (H-1 position)

    // Python: traj[:,mask]  where traj=[B,K,H-1,D], mask=[K,H-1]
    // Flatten the K*(H-1) dims, apply 1D mask, then reshape.
    //   traj_flat = traj_slice.permute(0,2,1,3).reshape(B, H-1*K, D)  -- NO
    //   Python collapses dims 1&2 together: need [B, K*(H-1), D]
    auto traj_flat   = traj_slice.reshape({B, K * Hm1, D});  // [B, K*H-1, D]
    auto mask_flat   = mask_xor.reshape({K * Hm1});           // [K*H-1]

    // Select the H-1 True positions for each batch entry
    // traj_flat[:, mask_flat, :]  → [B, H-1, D]
    auto indices  = torch::where(mask_flat)[0];                // [H-1] long indices
    auto result   = traj_flat.index_select(1, indices);        // [B, H-1, D]
    return result;
}

// ---- act() ----

torch::Tensor DiffuseCLoCActor::act(const torch::Tensor& nobs_norm,
                                     const torch::Tensor& cond_norm)
{
    RECORD_FUNCTION("task142::actor_total", std::vector<c10::IValue>());
    torch::NoGradGuard ng;
    std::optional<c10::InferenceMode> inference_guard;
    if (cfg_.inference_mode && !c10::InferenceMode::is_enabled())
        inference_guard.emplace(true);
    reset_timeline_backbone_index();
    timeline_mark("actor/start");

    auto nobs = nobs_norm.to(device_).to(torch::kFloat32);
    if (nobs.dim() != 3 || nobs.size(1) < cfg_.n_obs_steps
        || nobs.size(2) != emphasis_mat_.size(0)) {
        throw std::invalid_argument(
            "[DiffuseCLoCActor] observation schema mismatch with emphasis matrix");
    }
    nobs = nobs.narrow(1, 0, cfg_.n_obs_steps);

    torch::Tensor cond;
    if (cond_norm.defined() && cond_norm.numel() > 0) {
        cond = cond_norm.to(device_).to(torch::kFloat32);
    }
    timeline_mark("actor/input_ready");
    if (cfg_.defer_finite_checks) {
        auto finite = torch::isfinite(nobs).all();
        if (cond.defined())
            finite = torch::logical_and(finite, torch::isfinite(cond).all());
        if (!finite.item<bool>())
            throw std::invalid_argument("[DiffuseCLoCActor] nonfinite optimized input");
    }

    const int B       = static_cast<int>(nobs.size(0));
    const int H       = cfg_.horizon();
    const int Da      = cfg_.action_dim;
    // State dimension in emphasis space (may differ from cfg_.obs_dim when
    // emphasis_mat is non-square, e.g. [192, 384] maps 192-dim obs → 384-dim).
    const int Do_emph = static_cast<int>(emphasis_mat_.size(1));

    // ---- Initial trajectories ----
    timeline_mark("actor/noise_start");
    auto action_traj = torch::randn({B, H, Da},
        torch::TensorOptions().dtype(torch::kFloat32).device(device_));
    // Allocate state_traj in the emphasized space so that inpainting
    // (state_traj[:, :n_past] = nobs_emph) works without a shape mismatch.
    auto state_traj  = torch::randn({B, H, Do_emph},
        torch::TensorOptions().dtype(torch::kFloat32).device(device_));
    timeline_mark("actor/noise_end");

    // ---- Apply emphasis to nobs ----
    // nobs_emph = nobs @ emphasis_mat   [B, n_past, Do_emph]
    // emphasis_mat shape: [Do, Do] or [Do, Do_emph]
    timeline_mark("actor/emphasis_start");
    auto nobs_emph = right_project(nobs, emphasis_mat_);  // [B, n_past, Do_emph]
    if (!cfg_.defer_finite_checks
        && !torch::isfinite(nobs_emph).all().item<bool>()) {
        const auto flat_idx = torch::argmax(torch::abs(nobs)).to(torch::kCPU).item<int64_t>();
        const auto obs_dim = nobs.size(2);
        const auto time_dim = nobs.size(1);
        const auto d = flat_idx % obs_dim;
        const auto t = (flat_idx / obs_dim) % time_dim;
        const auto b = flat_idx / (obs_dim * time_dim);
        const auto value = nobs.index({b, t, d}).to(torch::kCPU).item<double>();
        const auto matrix_max = torch::amax(torch::abs(emphasis_mat_))
                                    .to(torch::kCPU).item<double>();
        throw std::runtime_error(
            "[DiffuseCLoCActor] nonfinite emphasis projection; max_abs_nobs at [" +
            std::to_string(b) + "," + std::to_string(t) + "," +
            std::to_string(d) + "]=" + std::to_string(value) +
            ", max_abs_emphasis=" + std::to_string(matrix_max));
    }
    timeline_mark("actor/emphasis_end");

    // ---- DDIM paths (three scheduling options, mirroring Python
    // DiffuseCLoC.act() when ddim_steps > 0) ----
    //   (a) ns_ddim       : per-position NS DDIM via joint_ns_ddim_step
    //   (b) rolling_ddim  : per-position rolling DDIM (warm-start buffer)
    //   (c) scalar_ddim   : uniform-t scalar DDIM via joint_ddim_step
    // Production classifier guidance modifies the step's single x0 prediction;
    // duplicate_backbone retains the former pre-denoise path for replay only.
    if (cfg_.ddim_steps > 0) {
        const int T      = cfg_.denoising_steps;
        const int n_past = cfg_.n_obs_steps;
        const std::string& sm = cloc_cfg_.sampler_mode;
        auto expand_h = [&](const torch::Tensor& h_vec) {
            return h_vec.unsqueeze(0).expand({B, H});
        };

        if (cfg_.ddim_precompute && B != 1)
            throw std::invalid_argument("ddim_precompute requires static batch size B=1");

        torch::Tensor condition_embeddings;
        if (cfg_.condition_embedding_reuse) {
            if (!cond.defined())
                throw std::invalid_argument(
                    "condition_embedding_reuse requires condition input");
            condition_embeddings = build_condition_embeddings(cond.to(model_dtype_));
        }

        if (sm == "ns_ddim") {
            // ---- Option (a): per-position NS DDIM ----
            timeline_mark("actor/schedule_start");
            std::vector<NSDdimStepPlan> dynamic_plan;
            const std::vector<NSDdimStepPlan>* plan = &ns_ddim_plan_;
            if (!cfg_.ddim_precompute) {
                auto opts = torch::TensorOptions().dtype(torch::kLong).device(device_);
                std::vector<NSDdimStepPlan> full;
                full.reserve(T);
                for (int t = T - 1; t >= 0; --t) {
                    auto action_cur = torch::full({H}, t, opts);
                    auto action_prev = torch::full({H}, t - 1, opts);
                    auto state_cur = action_cur.clone();
                    auto state_prev = action_prev.clone();
                    if (!cfg_.no_state_override) {
                        state_cur.narrow(0, 0, n_past).fill_(0);
                        state_prev.narrow(0, 0, n_past).fill_(0);
                    }
                    full.push_back({action_cur, action_prev, state_cur, state_prev});
                }
                for (int index : uniform_indices(T, cfg_.ddim_steps))
                    dynamic_plan.push_back(full.at(index));
                for (std::size_t i = 0; i + 1 < dynamic_plan.size(); ++i) {
                    dynamic_plan[i].action_prev = dynamic_plan[i + 1].action_cur.clone();
                    dynamic_plan[i].state_prev = dynamic_plan[i + 1].state_cur.clone();
                }
                plan = &dynamic_plan;
            }
            timeline_mark("actor/schedule_end");

            for (const auto& st : *plan) {
                torch::Tensor na, ns;
                if (guidance_ && guidance_->enabled()
                    && cloc_cfg_.classifier_guidance_impl == "reuse_x0") {
                    const auto a_t = expand_h(st.action_cur);
                    const auto s_t = expand_h(st.state_cur);
                    const auto s_prev = expand_h(st.state_prev);
                    auto state_input = state_traj.clone();
                    if (!cfg_.no_state_override)
                        state_input.narrow(1, 0, n_past).copy_(nobs_emph);
                    auto predictions = predict_x0(
                        action_traj, state_input, a_t, s_t, cond,
                        condition_embeddings, false);
                    torch::Tensor guided_state_pred;
                    {
                        RECORD_FUNCTION("task142::wbg_fk_gradient", std::vector<c10::IValue>());
                        timeline_mark("actor/wbg_start");
                        guided_state_pred = predictions.second - guidance_->gradient(
                            predictions.second, emphasis_mat_inv_, s_t, s_prev);
                        timeline_mark("actor/wbg_end");
                    }
                    std::tie(na, ns) = joint_ns_ddim_step_from_predictions(
                        action_traj, state_input, nobs_emph,
                        st.action_cur, st.action_prev,
                        st.state_cur, st.state_prev, cfg_.ddim_eta,
                        predictions.first, guided_state_pred);
                } else {
                    state_traj = pre_denoise_guidance(
                        action_traj, state_traj, expand_h(st.action_cur),
                        expand_h(st.state_cur), expand_h(st.state_prev), cond);
                    std::tie(na, ns) = joint_ns_ddim_step(
                        action_traj, state_traj, nobs_emph,
                        st.action_cur, st.action_prev,
                        st.state_cur, st.state_prev, cfg_.ddim_eta, cond);
                }
                action_traj = na;
                state_traj = ns;
            }
        } else if (sm == "rolling_ddim") {
            // ---- Option (b): rolling per-position DDIM ----
            std::vector<std::pair<torch::Tensor, torch::Tensor>> action_chain,
                state_chain;
            torch::Tensor action_t_all, state_t_all;
            // Always use configured schedules for chain building so that rolling
            // buffer extraction (which also uses configured schedules) can match.
            action_t_all = generate_denoising_matrix(cloc_cfg_.action_schedule, false);
            state_t_all  = generate_denoising_matrix(cloc_cfg_.state_schedule,  true);
            if (has_rolling_) {
                action_traj.narrow(1, 0, H - 1).copy_(action_rolling_traj_);
                state_traj.narrow(1, 0, H - 1).copy_(state_rolling_traj_);
            }
            const int full_len  = static_cast<int>(action_t_all.size(0));
            const int state_len = static_cast<int>(state_t_all.size(0));
            // Iterate max(action,state) rows so the rolling buffer stays
            // full-length (H-1). Python's literal `range(full_len)` (action
            // length) leaves the STATE buffer one short on warm-start, which
            // breaks the next `copy_`; the DDPM path uses max() for the same
            // reason.
            const int total_steps = std::max(full_len, state_len);
            std::vector<int> ddim_idx;
            if (cfg_.ddim_steps < T) {
                ddim_idx = uniform_indices(total_steps, cfg_.ddim_steps);
            } else {
                for (int i = 0; i < total_steps; ++i) ddim_idx.push_back(i);
            }

            auto prev_action_t = action_t_all[0].clone() + 1;
            auto prev_state_t  = state_t_all[0].clone() + 1;

            for (size_t step_i = 0; step_i < ddim_idx.size(); ++step_i) {
                const int full_i = ddim_idx[step_i];
                torch::Tensor action_t = action_t_all[std::min(full_i, full_len - 1)];
                torch::Tensor state_t;
                if (full_i > state_len - 1) {
                    state_t = prev_state_t.clone();
                    auto zero_pos = torch::nonzero(state_t == 0);
                    if (zero_pos.size(0) > 0) {
                        int last_zero =
                            static_cast<int>(zero_pos[-1][0].item<int64_t>());
                        if (last_zero + 1 < H)
                            state_t.narrow(0, last_zero + 1,
                                           H - last_zero - 1) -= 1;
                    }
                } else {
                    state_t = state_t_all[full_i];
                }

                action_chain.push_back({action_traj.clone(), prev_action_t});
                state_chain .push_back({state_traj.clone(), prev_state_t});
                prev_action_t = action_t.clone();
                prev_state_t  = state_t.clone();

                auto a_t_prev =
                    action_t_all[std::min(full_i + 1, full_len - 1)];
                if (step_i + 1 == ddim_idx.size()) {
                    a_t_prev = a_t_prev.clone();
                    for (int endpoint : action_selection_clean_endpoints_)
                        a_t_prev.index_put_({endpoint}, -1);
                }
                auto s_t_prev =
                    state_t_all[std::min(full_i + 1, state_len - 1)];

                torch::Tensor na, ns;
                if (guidance_ && guidance_->enabled()
                    && cloc_cfg_.classifier_guidance_impl == "reuse_x0") {
                    const auto a_t_b = expand_h(action_t);
                    const auto s_t_b = expand_h(state_t);
                    const auto s_t_prev_b = expand_h(s_t_prev);
                    auto state_input = state_traj.clone();
                    if (!cfg_.no_state_override)
                        state_input.narrow(1, 0, n_past).copy_(nobs_emph);
                    auto predictions = predict_x0(
                        action_traj, state_input, a_t_b, s_t_b, cond,
                        condition_embeddings, false);
                    auto guided_state_pred = predictions.second
                        - guidance_->gradient(
                            predictions.second, emphasis_mat_inv_, s_t_b,
                            s_t_prev_b);
                    std::tie(na, ns) = joint_ns_ddim_step_from_predictions(
                        action_traj, state_input, nobs_emph, action_t,
                        a_t_prev, state_t, s_t_prev, cfg_.ddim_eta,
                        predictions.first, guided_state_pred);
                } else {
                    state_traj = pre_denoise_guidance(
                        action_traj, state_traj, expand_h(action_t),
                        expand_h(state_t), expand_h(s_t_prev), cond);
                    std::tie(na, ns) = joint_ns_ddim_step(
                        action_traj, state_traj, nobs_emph, action_t,
                        a_t_prev, state_t, s_t_prev, cfg_.ddim_eta, cond);
                }
                action_traj = na;
                state_traj = ns;
            }

            const int last_i = ddim_idx.back();
            action_chain.push_back(
                {action_traj.clone(), action_t_all[std::min(last_i, full_len - 1)].clone()});
            state_chain.push_back(
                {state_traj.clone(), state_t_all[std::min(last_i, state_len - 1)].clone()});
            action_rolling_traj_ = get_rolling_traj(
                action_chain, generate_denoising_matrix(cloc_cfg_.action_schedule, false));
            state_rolling_traj_ = get_rolling_traj(
                state_chain, generate_denoising_matrix(cloc_cfg_.state_schedule, true));
            if (action_rolling_traj_.size(1) != H - 1 || state_rolling_traj_.size(1) != H - 1) {
                std::cerr << "[DiffuseCLoCActor] rolling_ddim buffer size mismatch ("
                          << "action=" << action_rolling_traj_.size(1)
                          << ", state=" << state_rolling_traj_.size(1)
                          << ", expected=" << (H - 1) << "), discarding warm-start\n";
                reset_rolling();
            } else {
                has_rolling_ = true;
            }
        } else {
            // ---- Option (c): uniform-t scalar DDIM ----
            auto ts = build_ddim_timesteps(T, cfg_.ddim_steps);
            for (int i = 0; i < static_cast<int>(ts.size()); ++i) {
                int t_cur  = ts[i];
                int t_prev = (i + 1 < static_cast<int>(ts.size())) ? ts[i + 1] : -1;
                const DdimStepPlan* plan =
                    cfg_.ddim_precompute ? &ddim_plan_.at(i) : nullptr;
                torch::Tensor na, ns;
                if (guidance_ && guidance_->enabled()
                    && cloc_cfg_.classifier_guidance_impl == "reuse_x0") {
                    auto opts = torch::TensorOptions().dtype(torch::kLong).device(device_);
                    auto a_t = plan ? plan->action_t
                                    : torch::full({B, H}, t_cur, opts);
                    auto s_t = plan ? plan->state_t_denoise
                                    : torch::full({B, H}, t_cur, opts);
                    auto s_prev = plan ? plan->state_t_prev_denoise
                                       : torch::full({B, H}, t_prev, opts);
                    if (!plan)
                        s_t.narrow(1, 0, n_past).fill_(0);
                    auto state_input = state_traj.clone();
                    if (!cfg_.no_state_override)
                        state_input.narrow(1, 0, n_past).copy_(nobs_emph);
                    auto predictions = predict_x0(
                        action_traj, state_input, a_t, s_t, cond,
                        condition_embeddings, false);
                    auto guided_state_pred = predictions.second
                        - guidance_->gradient(
                            predictions.second, emphasis_mat_inv_, s_t, s_prev);
                    std::tie(na, ns) = joint_ddim_step_from_predictions(
                        action_traj, state_input, nobs_emph, t_cur, t_prev,
                        cfg_.ddim_eta, predictions.first, guided_state_pred, plan);
                } else {
                    std::tie(na, ns) = joint_ddim_step(
                        action_traj, state_traj, nobs_emph, t_cur, t_prev,
                        cfg_.ddim_eta, cond, condition_embeddings, plan);
                }
                action_traj = na;
                state_traj = ns;
            }
        }
        // Undo emphasis on state (not returned, but useful for callers who
        // inspect it). Only action_traj is returned by act().
        state_traj = right_project(state_traj, emphasis_mat_inv_);
        if (cfg_.defer_finite_checks
            && !torch::logical_and(torch::isfinite(action_traj).all(),
                                   torch::isfinite(state_traj).all()).item<bool>())
            throw std::runtime_error("[DiffuseCLoCActor] nonfinite optimized output");
        timeline_mark("actor/end");
        return action_traj;
    }

    // ---- Noise schedule matrices ----
    torch::Tensor action_t_all, state_t_all;

    // Always use configured schedules for chain building so that rolling
    // buffer extraction (which also uses configured schedules) can match
    // the columns it expects.
    action_t_all = generate_denoising_matrix(cloc_cfg_.action_schedule, false);
    state_t_all  = generate_denoising_matrix(cloc_cfg_.state_schedule,  true);

    if (has_rolling_) {
        // Warm-start from cached partially-denoised trajectories
        // action_traj[:, :-1] = action_rolling_traj_
        action_traj.narrow(1, 0, H - 1).copy_(action_rolling_traj_);
        // state_traj[:, :-1] = state_rolling_traj_
        state_traj.narrow(1, 0, H - 1).copy_(state_rolling_traj_);
    }

    const int K_action = static_cast<int>(action_t_all.size(0));
    const int K_state  = static_cast<int>(state_t_all.size(0));
    const int K_max    = std::max(K_action, K_state);

    // Denoising chains for rolling buffer
    std::vector<std::pair<torch::Tensor, torch::Tensor>> action_chain, state_chain;

    // prev_t (for filling state_t beyond schedule length)
    auto prev_action_t = action_t_all[0].clone() + 1;
    auto prev_state_t  = state_t_all[0].clone() + 1;

    // ---- Denoising loop ----
    for (int i = 0; i < K_max; ++i) {
        torch::Tensor action_t = action_t_all[std::min(i, K_action - 1)];
        if (i + 1 == K_max) {
            action_t = action_t.clone();
            for (int endpoint : action_selection_clean_endpoints_)
                action_t.index_put_({endpoint}, 0);
        }

        torch::Tensor state_t;
        if (i >= K_state) {
            // Beyond schedule length: manually shift one past step
            state_t = prev_state_t.clone();
            // Python: state_t[torch.nonzero(state_t==0)[-1,-1]+1:] -= 1
            // Find last zero position
            auto zero_pos = torch::nonzero(state_t == 0);
            if (zero_pos.size(0) > 0) {
                int last_zero = static_cast<int>(zero_pos[-1][0].item<int64_t>());
                if (last_zero + 1 < H) {
                    state_t.narrow(0, last_zero + 1, H - last_zero - 1) -= 1;
                }
            }
        } else {
            state_t = state_t_all[i];
        }

        // Collect chain entries (before the step)
        action_chain.push_back({action_traj.clone(), prev_action_t.clone()});
        state_chain .push_back({state_traj .clone(), prev_state_t .clone()});

        prev_action_t = action_t.clone();
        prev_state_t  = state_t.clone();

        torch::Tensor new_action, new_state;
        if (guidance_ && guidance_->enabled()
            && cloc_cfg_.classifier_guidance_impl == "reuse_x0") {
            auto action_t_b = action_t.unsqueeze(0).expand({B, H}).to(device_);
            auto state_t_b = state_t.unsqueeze(0).expand({B, H}).to(device_);
            auto state_input = state_traj.clone();
            if (!cfg_.no_state_override) {
                state_input.narrow(1, 0, cfg_.n_obs_steps).copy_(nobs_emph);
                state_t_b = state_t_b.clone();
                state_t_b.narrow(1, 0, cfg_.n_obs_steps).fill_(0);
            }
            auto predictions = predict_x0(
                action_traj, state_input, action_t_b, state_t_b, cond,
                {}, false);
            auto guided_state_pred = predictions.second
                - guidance_->gradient(
                    predictions.second, emphasis_mat_inv_, state_t_b, {});
            std::tie(new_action, new_state) = diffuse_step_from_predictions(
                action_traj, state_input, action_t_b, state_t_b,
                predictions.first, guided_state_pred);
        } else {
            // Explicit historical replay path with two backbone executions.
            std::tie(new_action, new_state) = diffuse_step(
                nobs_emph, action_traj, state_traj, action_t, state_t, cond);
        }
        if (!torch::isfinite(new_action).all().item<bool>()
            || !torch::isfinite(new_state).all().item<bool>()) {
            throw std::runtime_error(
                "[DiffuseCLoCActor] nonfinite DDPM output at denoise step "
                + std::to_string(i));
        }
        action_traj = new_action;
        state_traj  = new_state;
    }

    // Final chain entries
    action_chain.push_back({action_traj.clone(), prev_action_t});
    state_chain .push_back({state_traj .clone(), prev_state_t });

    // ---- Update rolling buffer ----
    auto act_sched_next  = generate_denoising_matrix(cloc_cfg_.action_schedule, false);
    auto stat_sched_next = generate_denoising_matrix(cloc_cfg_.state_schedule,  true);

    action_rolling_traj_ = get_rolling_traj(action_chain, act_sched_next);
    state_rolling_traj_  = get_rolling_traj(state_chain,  stat_sched_next);

    // Defensive: discard warm-start if the extraction produced an
    // unexpected buffer size (guard against future schedule mismatches).
    if (action_rolling_traj_.size(1) != H - 1 || state_rolling_traj_.size(1) != H - 1) {
        std::cerr << "[DiffuseCLoCActor] rolling buffer size mismatch ("
                  << "action=" << action_rolling_traj_.size(1)
                  << ", state=" << state_rolling_traj_.size(1)
                  << ", expected=" << (H - 1) << "), discarding warm-start\n";
        reset_rolling();
    } else {
        has_rolling_ = true;
    }

    // ---- Apply inverse emphasis to state output ----
    // state_traj = state_traj @ emphasis_mat_inv
    // (discarded — only action_traj is returned by act())
    // state_traj = torch::matmul(state_traj, emphasis_mat_inv_);

    return action_traj;
}

}  // namespace diffusion_deploy
