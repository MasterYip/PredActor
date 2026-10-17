#pragma once

#include <torch/torch.h>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <mutex>
#include <string>
#include <vector>

namespace diffusion_deploy {

struct AxisGuidanceConfig {
    bool enabled = false;
    float command = 0.0f;
    float kp = 1.0f;
    std::vector<int> body_indices;
};

struct WholeBodyGuidanceConfig {
    bool enabled = false;
    std::string mode = "classifier";
    std::string trajectory_mode = "simple";
    float dt = 0.02f;
    int n_past_steps = 4;
    int horizon = 20;
    int denoising_steps = 20;
    bool enable_zeta_comp = true;
    bool enable_damping_comp = true;
    // Kept sequential by default until target profiling accepts the exact
    // stacked implementation.
    std::string axis_gradient_impl = "sequential";
    AxisGuidanceConfig vx;
    AxisGuidanceConfig vy;
    AxisGuidanceConfig wz;
    std::vector<float> obs_scale;
    std::vector<float> obs_offset;
};

/**
 * Interactive WBG UDP frame (wire format).
 *
 * One datagram is 9 x float32 LE in this fixed order:
 *   [vx_enabled, vx_command, vx_kp,
 *    vy_enabled, vy_command, vy_kp,
 *    wz_enabled, wz_command, wz_kp]
 *
 *   enabled: 0.0 (disabled) or 1.0 (enabled)
 *   command: m/s for vx/vy, rad/s for wz   (clamped by the receiver)
 *   kp:      guidance gain                  (clamped by the receiver)
 *
 * Only these per-axis fields are mutable over UDP. Body indices, masks,
 * scale/offset, mode, and trajectory_mode are NOT changeable over UDP.
 */
struct WbgUdpFrame {
    float vx_enabled = 0.0f;  float vx_command = 0.0f;  float vx_kp = 1.0f;
    float vy_enabled = 0.0f;  float vy_command = 0.0f;  float vy_kp = 1.0f;
    float wz_enabled = 0.0f;  float wz_command = 0.0f;  float wz_kp = 1.0f;
};

/** One coherent generation of all live WBG axis controls. */
struct LiveGuidanceSnapshot {
    std::array<bool, 3> enabled{{false, false, false}};
    std::array<float, 3> command{{0.0f, 0.0f, 0.0f}};
    std::array<float, 3> kp{{0.0f, 0.0f, 0.0f}};
    std::uint64_t generation = 0;

    bool any_active() const;
};

/**
 * Parse a 36-byte WBG UDP datagram (9 x float32 LE) into a WbgUdpFrame.
 *
 * @return false if bytes is null, n != 36, or any field is non-finite.
 */
bool parse_wbg_udp_frame(const void* bytes, std::size_t n, WbgUdpFrame& out);

/** Headless classifier WBG for the operational G1 192-D kinematic profile. */
class WholeBodyGuidance {
public:
    explicit WholeBodyGuidance(const WholeBodyGuidanceConfig& config,
                               torch::Device device = torch::kCPU);

    torch::Tensor gradient(const torch::Tensor& state_x0_projected,
                           const torch::Tensor& emphasis_inv,
                           const torch::Tensor& state_t_b,
                           const torch::Tensor& state_t_prev_b = {}) const;

    // Correctness/benchmark surfaces. Production callers should use gradient().
    torch::Tensor gradient_sequential_reference(
        const torch::Tensor& state_x0_projected,
        const torch::Tensor& emphasis_inv,
        const torch::Tensor& state_t_b,
        const torch::Tensor& state_t_prev_b = {}) const;
    torch::Tensor gradient_stacked(
        const torch::Tensor& state_x0_projected,
        const torch::Tensor& emphasis_inv,
        const torch::Tensor& state_t_b,
        const torch::Tensor& state_t_prev_b = {}) const;
    void to(torch::Device device);
    bool enabled() const { return cfg_.enabled; }

    /**
     * Apply a live WBG UDP frame. Overrides only each axis's
     * enabled/command/kp; all other config is fixed at construction.
     * Commands are bounded only when explicit limits are configured; non-finite
     * values are rejected.
     */
    void apply_live_udp(const WbgUdpFrame& frame);

    /** Set finite, non-negative per-axis limits for unified-command WBG. */
    void set_live_command_bounds(float max_vx, float max_vy, float max_wz);

    /**
     * Update one axis live: axis 0=vx, 1=vy, 2=wz.
     * enabled_f is 0.0/1.0. command follows the configured bound and kp is
     * clamped to its finite gain range.
     */
    void set_live_axis(int axis, float enabled_f, float command, float kp);

    /** Snapshot of a live axis config (enabled/command/kp). Thread-safe. */
    AxisGuidanceConfig live_axis(int axis) const;

    /** Snapshot all axes under one lock; no mixed frame can be observed. */
    LiveGuidanceSnapshot live_snapshot() const;

private:
    WholeBodyGuidanceConfig cfg_;
    torch::Device device_;
    torch::Tensor scale_;
    torch::Tensor offset_;
    torch::Tensor horizon_weight_;
    torch::Tensor steps_;
    std::array<torch::Tensor, 3> body_masks_;

    struct StaticTensorCache {
        at::ScalarType dtype = at::ScalarType::Undefined;
        torch::Tensor scale;
        torch::Tensor offset;
        torch::Tensor horizon_weight;
        torch::Tensor steps;
        torch::Tensor body_mask_matrix;
    };
    std::array<StaticTensorCache, 4> static_caches_;
    torch::Tensor root_position_indices_;
    torch::Tensor root_velocity_indices_;

    struct LiveTensorCache {
        at::ScalarType dtype = at::ScalarType::Undefined;
        std::uint64_t generation = static_cast<std::uint64_t>(-1);
        torch::Tensor packed;
        torch::Tensor command;
        torch::Tensor command_dt;
        torch::Tensor gain;
        torch::Tensor body_command;
        torch::Tensor body_command_dt;
    };
    struct PreparedLive {
        LiveGuidanceSnapshot snapshot;
        torch::Tensor command;
        torch::Tensor command_dt;
        torch::Tensor gain;
        torch::Tensor body_command;
        torch::Tensor body_command_dt;
    };

    // Live-updatable per-axis commands (UDP). Read under live_mutex_.
    mutable std::mutex live_mutex_;
    AxisGuidanceConfig live_vx_;
    AxisGuidanceConfig live_vy_;
    AxisGuidanceConfig live_wz_;
    // Legacy UDP has no configured command limits. Unified command sets
    // these explicitly from runner.unified_command.max_*.
    std::array<float, 3> live_command_bounds_{{
        std::numeric_limits<float>::infinity(),
        std::numeric_limits<float>::infinity(),
        std::numeric_limits<float>::infinity()}};
    std::uint64_t live_generation_ = 0;
    mutable std::array<LiveTensorCache, 4> live_tensor_caches_;

    void rebuild_static_caches();
    const StaticTensorCache& static_cache(at::ScalarType dtype) const;
    LiveGuidanceSnapshot live_snapshot_unlocked() const;
    PreparedLive prepare_live(at::ScalarType dtype) const;
    torch::Tensor gradient_impl(
        const torch::Tensor& state_x0_projected,
        const torch::Tensor& emphasis_inv,
        const torch::Tensor& state_t_b,
        const torch::Tensor& state_t_prev_b,
        bool stacked) const;
    void accumulate_axis_gradient_reference(
        torch::Tensor& grad,
        const torch::Tensor& state,
        const LiveGuidanceSnapshot& snapshot,
        const StaticTensorCache& cache,
        int axis,
        bool yaw) const;
    void accumulate_stacked_gradient(
        torch::Tensor& grad,
        const torch::Tensor& state,
        const PreparedLive& live,
        const StaticTensorCache& cache) const;
    static void validate_axis(const AxisGuidanceConfig& cfg,
                              const std::string& name);
};

}  // namespace diffusion_deploy
