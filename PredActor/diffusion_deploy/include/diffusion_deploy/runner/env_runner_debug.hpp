/**
 * env_runner_debug.hpp
 *
 * EnvRunnerDebug — standalone debug runner with detailed per-step logging and
 * optional real-time visualization via the Python cloc_fdb_debugger.
 *
 * Robot state streaming to the Python visualizer uses a compact UDP protocol:
 *
 *   Wire format (little-endian):
 *     4 bytes   magic = 0xDBD10001
 *     4 bytes   frame index (uint32)
 *     4 bytes   n_fields (uint32)
 *     per-field:
 *       64 bytes  field name (null-padded)
 *       4 bytes   n_floats (uint32)
 *       n_floats * 4 bytes  float32 values
 *
 * The companion Python receiver (tools/cloc_fdb_udp_receiver.py) unpacks this
 * and forwards the reconstructed dict to CLoCFdbDebugger.update().
 *
 * CLIP conditioning can be injected from a running Python clip_cond_sender.py
 * via UDP (tools/clip_cond_sender.py).
 */
#pragma once

#include "diffusion_deploy/runner/env_runner.hpp"
#include "diffusion_deploy/obs/obs_terms.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

// POSIX UDP
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

namespace diffusion_deploy {

// ---- Debug UDP wire-format constants ----
static constexpr uint32_t DEBUG_UDP_MAGIC    = 0xDBD10001u;
static constexpr int      DEBUG_FIELD_NAME_LEN = 64;

// ---- Configuration ----

struct EnvRunnerDebugConfig {
    // Inherit all EnvRunnerConfig fields via composition
    EnvRunnerConfig base;

    // ---- Logging ----
    bool print_obs      = true;   ///< Print obs terms each step
    bool print_action   = true;   ///< Print raw action each step
    bool print_timing   = true;   ///< Print per-step wall-clock time
    int  print_interval = 1;      ///< Print every N steps (1 = every step)

    // ---- Debug UDP (robot state to Python visualizer) ----
    bool        enable_debug_udp   = false;
    std::string debug_udp_host     = "127.0.0.1";
    int         debug_udp_port     = 9878;   ///< Different from cond UDP (9877)
    int         debug_udp_interval = 1;      ///< Send every N steps

    // ---- Fields to send (subset of ObsTerms) ----
    // All enabled by default; disable individually if bandwidth is tight.
    bool send_joint_pos         = true;
    bool send_joint_vel         = true;
    bool send_projected_gravity = true;
    bool send_base_lin_vel      = true;
    bool send_base_ang_vel      = true;
    bool send_root_pos          = true;
    bool send_root_rot          = true;
    bool send_last_actions      = true;
    bool send_body_pos          = true;
    bool send_body_lin_vel      = true;
};

// ---- EnvRunnerDebug ----

/**
 * Standalone debug control loop with per-step logging and robot-state UDP
 * streaming.  Re-implements the full loop rather than subclassing EnvRunner
 * (EnvRunner::run_step is private), but shares the same env/agent/composer.
 */
class EnvRunnerDebug {
public:
    EnvRunnerDebug(std::unique_ptr<BaseEnv>         env,
                   std::unique_ptr<ObsComposer>     obs_composer,
                   std::unique_ptr<DiffusionAgent>  agent,
                   const EnvRunnerDebugConfig&      config);

    ~EnvRunnerDebug();

    /** Run the debug control loop (blocking). */
    RunStats run();

    /** Signal the loop to stop from another thread or signal handler. */
    void request_stop() { stop_requested_.store(true); }

private:
    std::unique_ptr<BaseEnv>         env_;
    std::unique_ptr<ObsComposer>     obs_composer_;
    std::unique_ptr<DiffusionAgent>  agent_;
    EnvRunnerDebugConfig             cfg_;
    int action_lower_index_{0};
    int action_upper_index_{0};
    double action_alpha_{0.0};

    ObsHistory        obs_history_;
    torch::Tensor     last_actions_;
    std::atomic<bool> stop_requested_{false};

    // Episode tracking
    struct EpStats {
        torch::Tensor current_rewards;
        torch::Tensor current_lengths;
        std::vector<float> episode_rewards;
        std::vector<float> episode_lengths;
    } ep_stats_;

    // Async cond UDP (CLIP conditioning from Python sender)
    std::mutex        cond_mutex_;
    torch::Tensor     latest_cond_;
    std::thread       cond_recv_thread_;
    std::atomic<bool> cond_recv_running_{false};

    // Debug UDP socket (robot state → Python visualizer)
    int         debug_sock_ = -1;
    sockaddr_in debug_addr_{};
    uint32_t    frame_idx_  = 0;

    // Timing
    std::chrono::steady_clock::time_point loop_start_;

    // ---- private helpers ----
    void prime_history();
    bool run_step(int step_idx);
    void enforce_rate(std::chrono::steady_clock::time_point step_start);

    void start_cond_receiver();
    void stop_cond_receiver();

    void init_debug_udp();
    void close_debug_udp();

    void send_debug_udp(const ObsTerms& obs, const torch::Tensor& action);

    static void print_obs_terms(int step, const ObsTerms& obs,
                                const torch::Tensor& action,
                                double step_ms,
                                bool print_action, bool print_timing);
};

}  // namespace diffusion_deploy
