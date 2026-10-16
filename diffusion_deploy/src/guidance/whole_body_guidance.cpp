#include "diffusion_deploy/guidance/whole_body_guidance.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace diffusion_deploy {

namespace {

torch::Tensor right_project(const torch::Tensor& values,
                            const torch::Tensor& matrix) {
#if defined(__aarch64__)
    if (values.device().is_cpu()) {
        TORCH_CHECK(values.dim() == 3 && matrix.dim() == 2,
                    "right_project expects [B,H,D] x [D,O]");
        return (values.unsqueeze(-1) * matrix.unsqueeze(0).unsqueeze(0)).sum(-2);
    }
#endif
    return torch::matmul(values, matrix);
}

}  // namespace
namespace {
constexpr int kObsDim = 192;
constexpr int kBodyPos = 0;
constexpr int kBodyVel = 90;
constexpr int kRootPos = 180;
constexpr int kRootRot = 183;
constexpr int kRootLinVel = 186;
constexpr int kRootAngVel = 189;

constexpr float kMaxKp     = 100.0f;

constexpr std::array<at::ScalarType, 4> kCachedDtypes{{
    at::ScalarType::Float,
    at::ScalarType::Double,
    at::ScalarType::Half,
    at::ScalarType::BFloat16,
}};

bool sanitize_live_value(float bound, float enabled_f, float command, float kp,
                         bool& enabled_out, float& command_out, float& kp_out) {
    if (!std::isfinite(enabled_f) || !std::isfinite(command)
        || !std::isfinite(kp)) return false;
    enabled_out = enabled_f > 0.5f;
    command_out = std::isfinite(bound)
        ? std::clamp(command, -bound, bound) : command;
    kp_out = std::clamp(kp, 0.0f, kMaxKp);
    return true;
}
}

bool LiveGuidanceSnapshot::any_active() const {
    for (int axis = 0; axis < 3; ++axis) {
        if (enabled[axis] && kp[axis] != 0.0f) return true;
    }
    return false;
}

bool parse_wbg_udp_frame(const void* bytes, std::size_t n, WbgUdpFrame& out) {
    if (bytes == nullptr || n != 9 * sizeof(float)) return false;
    float vals[9];
    std::memcpy(vals, bytes, sizeof(vals));  // unaligned-safe copy
    for (int i = 0; i < 9; ++i) {
        if (!std::isfinite(vals[i])) return false;
    }
    out = WbgUdpFrame{vals[0], vals[1], vals[2],
                      vals[3], vals[4], vals[5],
                      vals[6], vals[7], vals[8]};
    return true;
}

void WholeBodyGuidance::validate_axis(const AxisGuidanceConfig& cfg,
                                      const std::string& name) {
    if (cfg.kp < 0.0f)
        throw std::invalid_argument("WholeBodyGuidance: " + name + ".kp must be non-negative");
    for (int body : cfg.body_indices) {
        if (body < 0 || body >= 30)
            throw std::invalid_argument("WholeBodyGuidance: " + name + " body index out of [0,29]");
    }
}

WholeBodyGuidance::WholeBodyGuidance(const WholeBodyGuidanceConfig& config,
                                     torch::Device device)
    : cfg_(config), device_(device)
    , live_vx_(config.vx), live_vy_(config.vy), live_wz_(config.wz) {
    if (!cfg_.enabled) return;
    if (cfg_.mode != "classifier")
        throw std::invalid_argument(
            "WholeBodyGuidance: C++ supports classifier mode only; refusing a PD substitution");
    if (cfg_.trajectory_mode != "simple")
        throw std::invalid_argument("WholeBodyGuidance: only trajectory_mode=simple is supported");
    if (cfg_.axis_gradient_impl != "sequential"
        && cfg_.axis_gradient_impl != "stacked")
        throw std::invalid_argument(
            "WholeBodyGuidance: axis_gradient_impl must be sequential or stacked");
    if (cfg_.horizon <= cfg_.n_past_steps || cfg_.n_past_steps <= 0
        || cfg_.denoising_steps <= 0 || cfg_.dt <= 0.0f)
        throw std::invalid_argument("WholeBodyGuidance: invalid timing/horizon schema");
    validate_axis(cfg_.vx, "vx");
    validate_axis(cfg_.vy, "vy");
    validate_axis(cfg_.wz, "wz");
    if (cfg_.obs_scale.size() != kObsDim || cfg_.obs_offset.size() != kObsDim)
        throw std::invalid_argument("WholeBodyGuidance: g1_standard requires 192-D obs scale/offset");

    rebuild_static_caches();
}

void WholeBodyGuidance::to(torch::Device device) {
    device_ = device;
    if (cfg_.enabled) rebuild_static_caches();
}

void WholeBodyGuidance::apply_live_udp(const WbgUdpFrame& frame) {
    const std::array<float, 3> enabled_in{{
        frame.vx_enabled, frame.vy_enabled, frame.wz_enabled}};
    const std::array<float, 3> command_in{{
        frame.vx_command, frame.vy_command, frame.wz_command}};
    const std::array<float, 3> kp_in{{frame.vx_kp, frame.vy_kp, frame.wz_kp}};
    std::array<bool, 3> enabled;
    std::array<float, 3> command;
    std::array<float, 3> kp;
    std::lock_guard<std::mutex> lk(live_mutex_);
    for (int axis = 0; axis < 3; ++axis) {
        if (!sanitize_live_value(live_command_bounds_[axis], enabled_in[axis], command_in[axis],
                                 kp_in[axis], enabled[axis], command[axis],
                                 kp[axis])) return;
    }
    std::array<AxisGuidanceConfig*, 3> dst{{&live_vx_, &live_vy_, &live_wz_}};
    bool changed = false;
    for (int axis = 0; axis < 3; ++axis) {
        changed = changed || dst[axis]->enabled != enabled[axis]
            || dst[axis]->command != command[axis]
            || dst[axis]->kp != kp[axis];
        dst[axis]->enabled = enabled[axis];
        dst[axis]->command = command[axis];
        dst[axis]->kp = kp[axis];
    }
    if (changed) ++live_generation_;
}

void WholeBodyGuidance::set_live_command_bounds(float max_vx, float max_vy,
                                                float max_wz) {
    const std::array<float, 3> bounds{{max_vx, max_vy, max_wz}};
    for (float bound : bounds) {
        if (!std::isfinite(bound) || bound < 0.0f)
            throw std::invalid_argument(
                "WholeBodyGuidance: live command bounds must be finite and non-negative");
    }
    std::lock_guard<std::mutex> lk(live_mutex_);
    live_command_bounds_ = bounds;
}

void WholeBodyGuidance::set_live_axis(int axis, float enabled_f,
                                      float command, float kp) {
    if (axis < 0 || axis > 2)
        throw std::invalid_argument("WholeBodyGuidance: live axis must be 0,1,2");
    std::lock_guard<std::mutex> lk(live_mutex_);
    bool enabled = false;
    if (!sanitize_live_value(live_command_bounds_[axis], enabled_f, command, kp,
                             enabled, command, kp)) return;

    AxisGuidanceConfig* dst = (axis == 0) ? &live_vx_
                             : (axis == 1) ? &live_vy_ : &live_wz_;
    const bool changed = dst->enabled != enabled || dst->command != command
        || dst->kp != kp;
    dst->enabled = enabled;
    dst->command = command;
    dst->kp = kp;
    if (changed) ++live_generation_;
}

AxisGuidanceConfig WholeBodyGuidance::live_axis(int axis) const {
    if (axis < 0 || axis > 2)
        throw std::invalid_argument("WholeBodyGuidance: live axis must be 0,1,2");
    std::lock_guard<std::mutex> lk(live_mutex_);
    return (axis == 0) ? live_vx_ : (axis == 1) ? live_vy_ : live_wz_;
}

void WholeBodyGuidance::rebuild_static_caches() {
    auto base_opts = torch::TensorOptions().dtype(torch::kFloat32).device(device_);
    scale_ = torch::tensor(cfg_.obs_scale, base_opts);
    offset_ = torch::tensor(cfg_.obs_offset, base_opts);
    horizon_weight_ = torch::ones({cfg_.horizon}, base_opts);
    horizon_weight_.narrow(0, 0, cfg_.n_past_steps).zero_();
    steps_ = (torch::arange(cfg_.horizon, base_opts)
              - (cfg_.n_past_steps - 1)).clamp_min(0);
    const int ramp = std::min(4, cfg_.horizon - cfg_.n_past_steps);
    for (int i = 0; i < ramp; ++i)
        horizon_weight_[cfg_.n_past_steps + i] =
            static_cast<float>(i + 1) / ramp;

    std::vector<float> masks(30 * 3, 0.0f);
    for (int axis = 0; axis < 3; ++axis) {
        const auto& src = axis == 0 ? cfg_.vx : (axis == 1 ? cfg_.vy : cfg_.wz);
        for (int body : src.body_indices) masks[body * 3 + axis] = 1.0f;
    }
    auto body_mask_matrix = torch::tensor(masks, base_opts).view({30, 3});
    for (int axis = 0; axis < 3; ++axis)
        body_masks_[axis] = body_mask_matrix.select(1, axis);

    for (std::size_t i = 0; i < kCachedDtypes.size(); ++i) {
        const auto dtype = kCachedDtypes[i];
        auto& cache = static_caches_[i];
        cache.dtype = dtype;
        cache.scale = scale_.to(dtype);
        cache.offset = offset_.to(dtype);
        cache.horizon_weight = horizon_weight_.to(dtype);
        cache.steps = steps_.to(dtype);
        cache.body_mask_matrix = body_mask_matrix.to(dtype);
    }
    auto index_opts = torch::TensorOptions().dtype(torch::kLong).device(device_);
    root_position_indices_ = torch::tensor({180, 181, 185}, index_opts);
    root_velocity_indices_ = torch::tensor({186, 187, 191}, index_opts);

    std::lock_guard<std::mutex> lk(live_mutex_);
    for (auto& cache : live_tensor_caches_) {
        cache = LiveTensorCache{};
    }
}

const WholeBodyGuidance::StaticTensorCache& WholeBodyGuidance::static_cache(
    at::ScalarType dtype) const {
    for (const auto& cache : static_caches_) {
        if (cache.dtype == dtype) return cache;
    }
    throw std::invalid_argument(
        "WholeBodyGuidance: unsupported floating dtype for cached constants");
}

LiveGuidanceSnapshot WholeBodyGuidance::live_snapshot_unlocked() const {
    LiveGuidanceSnapshot result;
    const std::array<const AxisGuidanceConfig*, 3> src{{
        &live_vx_, &live_vy_, &live_wz_}};
    for (int axis = 0; axis < 3; ++axis) {
        result.enabled[axis] = src[axis]->enabled;
        result.command[axis] = src[axis]->command;
        result.kp[axis] = src[axis]->kp;
    }
    result.generation = live_generation_;
    return result;
}

LiveGuidanceSnapshot WholeBodyGuidance::live_snapshot() const {
    std::lock_guard<std::mutex> lk(live_mutex_);
    return live_snapshot_unlocked();
}

WholeBodyGuidance::PreparedLive WholeBodyGuidance::prepare_live(
    at::ScalarType dtype) const {
    std::lock_guard<std::mutex> lk(live_mutex_);
    PreparedLive result;
    result.snapshot = live_snapshot_unlocked();
    LiveTensorCache* selected = nullptr;
    for (auto& cache : live_tensor_caches_) {
        if (cache.dtype == dtype) {
            selected = &cache;
            break;
        }
        if (selected == nullptr && cache.dtype == at::ScalarType::Undefined)
            selected = &cache;
    }
    if (selected == nullptr)
        throw std::runtime_error("WholeBodyGuidance: no live tensor cache slot");
    if (selected->dtype != dtype
        || selected->generation != result.snapshot.generation) {
        auto options = torch::TensorOptions().dtype(dtype).device(device_);
        std::vector<float> packed(15, 0.0f);
        for (int axis = 0; axis < 3; ++axis) {
            packed[axis] = result.snapshot.command[axis];
            packed[3 + axis] = packed[axis] * cfg_.dt;
            packed[6 + axis] = result.snapshot.enabled[axis]
                ? -2.0f * result.snapshot.kp[axis] : 0.0f;
            packed[9 + axis] = axis == 2 ? 0.0f : packed[axis];
            packed[12 + axis] = axis == 2 ? 0.0f : packed[3 + axis];
        }
        selected->dtype = dtype;
        selected->generation = result.snapshot.generation;
        selected->packed = torch::tensor(packed, options).view({5, 3});
        selected->command = selected->packed.select(0, 0).view({1, 1, 3});
        selected->command_dt = selected->packed.select(0, 1).view({1, 1, 3});
        selected->gain = selected->packed.select(0, 2).view({1, 1, 3});
        selected->body_command =
            selected->packed.select(0, 3).view({1, 1, 1, 3});
        selected->body_command_dt =
            selected->packed.select(0, 4).view({1, 1, 1, 3});
    }
    result.command = selected->command;
    result.command_dt = selected->command_dt;
    result.gain = selected->gain;
    result.body_command = selected->body_command;
    result.body_command_dt = selected->body_command_dt;
    return result;
}

void WholeBodyGuidance::accumulate_axis_gradient_reference(
    torch::Tensor& grad, const torch::Tensor& state,
    const LiveGuidanceSnapshot& snapshot, const StaticTensorCache& cache,
    int axis, bool yaw) const {
    if (!snapshot.enabled[axis] || snapshot.kp[axis] == 0.0f) return;
    const int H = static_cast<int>(state.size(1));
    const int now = cfg_.n_past_steps - 1;
    auto steps = cache.steps;
    auto w = cache.horizon_weight.view({1, H, 1});
    auto w2 = w.squeeze(-1);
    const float command = snapshot.command[axis];
    const float gain = -2.0f * snapshot.kp[axis];
    const int pos_slice = yaw ? kRootRot : kRootPos;
    const int vel_slice = yaw ? kRootAngVel : kRootLinVel;

    auto root_now = state.index(
        {torch::indexing::Slice(), now, pos_slice + axis}).unsqueeze(1);
    auto root_current = state.index(
        {torch::indexing::Slice(), torch::indexing::Slice(), pos_slice + axis});
    auto root_delta = (root_now + command * cfg_.dt * steps.unsqueeze(0)
        - root_current) * w2;
    grad.index({torch::indexing::Slice(), torch::indexing::Slice(),
        pos_slice + axis}).copy_(gain * root_delta);

    auto vel_current = state.index(
        {torch::indexing::Slice(), torch::indexing::Slice(), vel_slice + axis});
    grad.index({torch::indexing::Slice(), torch::indexing::Slice(),
        vel_slice + axis}).copy_(gain * (command - vel_current) * w2);

    auto body_mask = cache.body_mask_matrix.select(1, axis)
        .view({1, 1, 30});
    auto body_now = state.index({torch::indexing::Slice(), now,
        torch::indexing::Slice(kBodyPos + axis, kBodyPos + 90, 3)}).unsqueeze(1);
    auto body_current = state.index({torch::indexing::Slice(), torch::indexing::Slice(),
        torch::indexing::Slice(kBodyPos + axis, kBodyPos + 90, 3)});
    const float body_command = yaw ? 0.0f : command;
    auto body_delta = (body_now + body_command * cfg_.dt * steps.view({1, H, 1})
        - body_current) * body_mask * w;
    grad.index({torch::indexing::Slice(), torch::indexing::Slice(),
        torch::indexing::Slice(kBodyPos + axis, kBodyPos + 90, 3)})
        .copy_(gain * body_delta);

    auto body_vel_current = state.index({torch::indexing::Slice(), torch::indexing::Slice(),
        torch::indexing::Slice(kBodyVel + axis, kBodyVel + 90, 3)});
    grad.index({torch::indexing::Slice(), torch::indexing::Slice(),
        torch::indexing::Slice(kBodyVel + axis, kBodyVel + 90, 3)})
        .copy_(gain * (body_command * body_mask - body_vel_current) * w);
}

void WholeBodyGuidance::accumulate_stacked_gradient(
    torch::Tensor& grad, const torch::Tensor& state,
    const PreparedLive& live, const StaticTensorCache& cache) const {
    const auto B = state.size(0);
    const auto H = state.size(1);
    const int now = cfg_.n_past_steps - 1;
    auto w = cache.horizon_weight.view({1, H, 1});
    auto steps = cache.steps.view({1, H, 1});

    auto root_position = state.index_select(2, root_position_indices_);
    auto root_now = root_position.select(1, now).unsqueeze(1);
    auto root_delta = (root_now + live.command_dt * steps
                       - root_position) * w;
    grad.index_copy_(2, root_position_indices_, live.gain * root_delta);

    auto root_velocity = state.index_select(2, root_velocity_indices_);
    grad.index_copy_(2, root_velocity_indices_,
                     live.gain * (live.command - root_velocity) * w);

    auto body_mask = cache.body_mask_matrix.view({1, 1, 30, 3});
    auto body_gain = live.gain.view({1, 1, 1, 3});
    auto body_position = state.narrow(2, kBodyPos, 90).view({B, H, 30, 3});
    auto body_now = body_position.select(1, now).unsqueeze(1);
    auto body_delta = (body_now + live.body_command_dt
                       * steps.unsqueeze(2) - body_position) * body_mask
                      * w.unsqueeze(2);
    grad.narrow(2, kBodyPos, 90).copy_(
        (body_gain * body_delta).reshape({B, H, 90}));

    auto body_velocity = state.narrow(2, kBodyVel, 90).view({B, H, 30, 3});
    grad.narrow(2, kBodyVel, 90).copy_(
        (body_gain * (live.body_command * body_mask - body_velocity)
         * w.unsqueeze(2)).reshape({B, H, 90}));
}

torch::Tensor WholeBodyGuidance::gradient_impl(
    const torch::Tensor& state_x0_projected, const torch::Tensor& emphasis_inv,
    const torch::Tensor& state_t_b, const torch::Tensor& state_t_prev_b,
    bool stacked) const {
    if (!cfg_.enabled) return torch::zeros_like(state_x0_projected);
    if (state_x0_projected.dim() != 3 || state_x0_projected.size(1) != cfg_.horizon
        || emphasis_inv.dim() != 2 || emphasis_inv.size(1) != kObsDim
        || emphasis_inv.size(0) != state_x0_projected.size(2))
        throw std::invalid_argument(
            "WholeBodyGuidance: expected state[B,H,Dproj] and emphasis_inv[Dproj,192]");

    const auto dtype = state_x0_projected.scalar_type();
    // Reordering fused elementwise expressions changes FP16/BF16 rounding.
    // Preserve reference semantics for low precision; production FP32 remains fused.
    const bool use_stacked = stacked && dtype != at::ScalarType::Half
        && dtype != at::ScalarType::BFloat16;

    LiveGuidanceSnapshot snapshot;
    PreparedLive prepared;
    if (use_stacked) {
        prepared = prepare_live(dtype);
        snapshot = prepared.snapshot;
    } else {
        snapshot = live_snapshot();
    }
    if (!snapshot.any_active()) return torch::zeros_like(state_x0_projected);

    const auto& cache = static_cache(dtype);
    auto state_norm = right_project(state_x0_projected, emphasis_inv);
    auto state = (state_norm - cache.offset) / cache.scale;
    auto grad_physical = torch::zeros_like(state);

    if (use_stacked) {
        accumulate_stacked_gradient(grad_physical, state, prepared, cache);
    } else {
        accumulate_axis_gradient_reference(
            grad_physical, state, snapshot, cache, 0, false);
        accumulate_axis_gradient_reference(
            grad_physical, state, snapshot, cache, 1, false);
        accumulate_axis_gradient_reference(
            grad_physical, state, snapshot, cache, 2, true);
    }

    if (cfg_.enable_damping_comp) {
        auto damping = emphasis_inv.square().sum(0).clamp_min(1e-6f);
        grad_physical.div_(damping.view({1, 1, kObsDim}));
    }
    auto grad_projected = torch::matmul(
        grad_physical * cache.scale, emphasis_inv.transpose(0, 1));

    auto current = state_t_b.to(grad_projected.scalar_type());
    torch::Tensor zeta;
    if (cfg_.enable_zeta_comp && state_t_prev_b.defined()) {
        auto previous = state_t_prev_b.to(grad_projected.scalar_type());
        zeta = (current * (current + 1.0f) - previous * (previous + 1.0f))
            .mul_(0.5f).clamp_min_(0.0f);
    } else {
        zeta = current;
    }
    zeta.div_(static_cast<float>(std::max(cfg_.denoising_steps - 1, 1)));
    return grad_projected * zeta.unsqueeze(-1);
}

torch::Tensor WholeBodyGuidance::gradient(
    const torch::Tensor& state_x0_projected, const torch::Tensor& emphasis_inv,
    const torch::Tensor& state_t_b, const torch::Tensor& state_t_prev_b) const {
    return gradient_impl(state_x0_projected, emphasis_inv, state_t_b,
                         state_t_prev_b,
                         cfg_.axis_gradient_impl == "stacked");
}

torch::Tensor WholeBodyGuidance::gradient_sequential_reference(
    const torch::Tensor& state_x0_projected, const torch::Tensor& emphasis_inv,
    const torch::Tensor& state_t_b, const torch::Tensor& state_t_prev_b) const {
    return gradient_impl(state_x0_projected, emphasis_inv, state_t_b,
                         state_t_prev_b, false);
}

torch::Tensor WholeBodyGuidance::gradient_stacked(
    const torch::Tensor& state_x0_projected, const torch::Tensor& emphasis_inv,
    const torch::Tensor& state_t_b, const torch::Tensor& state_t_prev_b) const {
    return gradient_impl(state_x0_projected, emphasis_inv, state_t_b,
                         state_t_prev_b, true);
}

}  // namespace diffusion_deploy
