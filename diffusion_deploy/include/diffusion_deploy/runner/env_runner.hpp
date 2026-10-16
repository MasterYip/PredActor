/**
 * env_runner.hpp
 *
 * Top-level control loop orchestrator.
 * Mirrors diffusion_policy/env_runner/env_runner.py EnvRunner.
 *
 * Responsibilities:
 *   - Initialize env, prime obs history.
 *   - Each tick: get_obs_terms → shift_append → compose → act → unnormalize → step.
 *   - Rate enforcement via realtime_looper (optional).
 *   - Async UDP/ZMQ conditioning receiver for CLIP latents (optional).
 *
 * Usage:
 *   EnvRunnerConfig cfg;
 *   cfg.max_steps = 2000;
 *   EnvRunner runner(std::move(env), std::move(composer),
 *                    std::move(agent), cfg);
 *   runner.run();
 */
#pragma once

#include "diffusion_deploy/env/base_env.hpp"
#include "diffusion_deploy/obs/obs_composer.hpp"
#include "diffusion_deploy/agent/diffusion_agent.hpp"
#include "diffusion_deploy/utils/obs_history.hpp"
#include "diffusion_deploy/utils/realtime_looper.hpp"
#include "diffusion_deploy/safety/deploy_fsm.hpp"
#include "diffusion_deploy/command/unified_command_interface.hpp"
#include "diffusion_deploy/runner/csv_recorder.hpp"

#include <atomic>
#include <memory>
#include <mutex>
#include <optional>
#include <thread>
#include <functional>

namespace diffusion_deploy {

// ---- Configuration ----

struct EnvRunnerConfig {
    int    max_steps     = 1000;
    int    n_obs_steps   = 4;
    double delay_action_step = 0.0; ///< Signed fractional offset from n_obs_steps-1.
    double target_dt     = 0.02;    ///< Control period [s]. 0 = no rate enforcement.
    bool   realtime_mode = true;    ///< Enforce control rate.
    float  reset_height  = 0.3f;    ///< Auto-reset root_z threshold (MuJoCo-only).

    // Async conditioning via UDP (CLIP latent from Python)
    bool        enable_cond_udp = false;
    std::string cond_udp_host   = "127.0.0.1";
    int         cond_udp_port   = 9877;
    int         cond_dim        = 512;
    std::string condition_profile = "external"; ///< external | prdp_rlobs | g1_prdp_standard2
    int         n_cond_steps      = 1;
    int         rlobs_cond_dim    = 0;
    int         text_cond_dim     = 0;
    double      cond_startup_timeout_s = 30.0; ///< Wait for first required UDP text condition.

    // Async interactive WBG commands via UDP (Python wbg_guidance_sender.py).
    // Each datagram is 9 x float32 LE:
    //   [vx_enabled, vx_command, vx_kp, vy_enabled, vy_command, vy_kp,
    //    wz_enabled, wz_command, wz_kp]
    // Only per-axis enabled/command/kp are applied to the live guidance config.
    bool        enable_wbg_udp = false;
    std::string wbg_udp_host   = "127.0.0.1";
    int         wbg_udp_port   = 9879;

    // New opt-in in-process joystick command source. Disabled by default and
    // independent from the legacy CLIP/WBG UDP sender processes.
    UnifiedCommandConfig unified_command;

    // Disabled by default. The FSM YAML may enable it and select column groups;
    // when enabled, one row is written per tick and finalized on shutdown.
    CsvRecordConfig csv_record;

    // Safety FSM (optional). When set, EnvRunner gates each step through the
    // FSM.  Passive/Ready states skip inference and use safe joint targets.
    diffusion_deploy::safety::DeployFSM* safety_fsm = nullptr;
};

// ---- Statistics ----

struct RunStats {
    int   total_steps          = 0;
    double elapsed_s           = 0.0;
    double avg_step_ms         = 0.0;
    int   num_episodes         = 0;
    float mean_episode_reward  = 0.f;
    float std_episode_reward   = 0.f;
    float mean_episode_length  = 0.f;

    // Per-phase timing (mean over all steps, ms)
    double avg_obs_ms        = 0.0;   ///< get_obs_terms + shift_append + compose
    double avg_inference_ms  = 0.0;   ///< agent.act
    double avg_env_step_ms   = 0.0;   ///< env.step
    // Overrun stats
    int    overrun_count     = 0;     ///< steps where step_dt > target_dt
    double max_step_ms       = 0.0;   ///< worst single step [ms]

    // Policy-output and observed-motion evidence.
    int    policy_steps           = 0;
    int    finite_action_steps    = 0;
    double max_abs_action         = 0.0;
    double action_rms             = 0.0;
    double action_delta_rms       = 0.0;
    double max_abs_action_delta   = 0.0;
    double action_jerk_rms        = 0.0;
    double max_abs_action_jerk    = 0.0;
    double action_saturation_rate = 0.0;
    double max_joint_displacement = 0.0;
};

// ---- EnvRunner ----

class EnvRunner {
public:
    EnvRunner(std::unique_ptr<BaseEnv>         env,
              std::unique_ptr<ObsComposer>     obs_composer,
              std::unique_ptr<DiffusionAgent>  agent,
              const EnvRunnerConfig&           config = {});

    ~EnvRunner();

    /**
     * Run the blocking control loop.
     * Returns after max_steps or when env.is_running() returns false.
     */
    RunStats run();

    /** Signal the loop to stop gracefully (thread-safe). */
    void request_stop() { stop_requested_.store(true); }

    // ---- Accessors ----
    BaseEnv&        env()     { return *env_; }
    DiffusionAgent& agent()   { return *agent_; }
    ObsComposer&    composer(){ return *obs_composer_; }
    const EnvRunnerConfig& config() const { return config_; }

private:
    std::unique_ptr<BaseEnv>         env_;
    std::unique_ptr<ObsComposer>     obs_composer_;
    std::unique_ptr<ObsComposer>     condition_composer_;
    std::unique_ptr<DiffusionAgent>  agent_;
    EnvRunnerConfig                  config_;
    int action_lower_index_{0};
    int action_upper_index_{0};
    double action_alpha_{0.0};

    // Episode tracking
    struct EpStats {
        torch::Tensor current_rewards;
        torch::Tensor current_lengths;
        std::vector<float> episode_rewards;
        std::vector<float> episode_lengths;
    } ep_stats_;

    // Loop state
    ObsHistory       obs_history_;
    torch::Tensor    last_actions_;   ///< [num_dof] IsaacLab order
    std::atomic<bool> stop_requested_{false};
    int              step_count_{0};  ///< actual steps executed
    int              policy_step_count_{0};
    int              finite_action_step_count_{0};
    int64_t          action_value_count_{0};
    double           action_sq_sum_{0.0};
    double           max_abs_action_{0.0};
    int64_t          action_delta_value_count_{0};
    double           action_delta_sq_sum_{0.0};
    double           max_abs_action_delta_{0.0};
    int64_t          action_jerk_value_count_{0};
    double           action_jerk_sq_sum_{0.0};
    double           max_abs_action_jerk_{0.0};
    int64_t          action_saturation_count_{0};
    int64_t          action_normalized_value_count_{0};
    torch::Tensor    previous_policy_action_;
    torch::Tensor    previous_action_delta_;
    double           max_joint_displacement_{0.0};
    torch::Tensor    first_policy_joint_pos_;

    // Realtime loop tracker (mirrors Python RealtimeLooper)
    RealtimeLooper   looper_{"EnvRunnerLoop", /*window=*/50, /*print_interval=*/10.0};

    // Per-step timing accumulators (seconds)
    double acc_obs_s_       = 0.0;
    double acc_infer_s_     = 0.0;
    double acc_env_step_s_  = 0.0;
    double acc_total_s_     = 0.0;
    double max_step_s_      = 0.0;

    // Async conditioning
    std::mutex          cond_mutex_;
    torch::Tensor       latest_cond_;        ///< [1, 1, cond_dim]
    std::thread         cond_recv_thread_;
    std::atomic<bool>   cond_recv_running_{false};

    // Async WBG command receiver
    std::thread         wbg_recv_thread_;
    std::atomic<bool>   wbg_recv_running_{false};

    // One joystick source drives both live WBG and cached text conditions.
    std::unique_ptr<UnifiedCommandInterface> unified_command_;

    // Optional per-step diagnostic recording.  Null when disabled; the
    // control loop only performs a pointer check in that default path.
    std::unique_ptr<CsvRecorder> csv_recorder_;

    // Last accepted legacy WBG UDP frame, used only by the optional recorder.
    std::mutex wbg_command_mutex_;
    WbgUdpFrame latest_wbg_command_;
    bool latest_wbg_command_defined_ = false;

    // ---- Private methods ----

    /** Execute one control tick. Returns false when loop should stop. */
    bool run_step(int step_idx);

    /** Prime observation history from initial env state. */
    void prime_history();

    /**
     * Execute one safe step (Passive or Ready state).
     * Sends a safe joint-position target (track-current or interpolated stand-pose)
     * without running policy inference.
     *
     * @param dt  Timestep [s] since last call, forwarded to FSM interpolator.
     * @return true if the environment is still running.
     */
    bool execute_safe_step(double dt,
                           const ObsTerms& terms,
                           const torch::Tensor& policy_obs);

    /** Start async UDP listener for CLIP conditioning. */
    void start_cond_receiver();

    /** Wait for the first required external text condition at startup. */
    void wait_for_initial_condition();

    /** Stop and join cond receiver thread. */
    void stop_cond_receiver();

    /** Start async UDP listener for interactive WBG commands. */
    void start_wbg_receiver();

    /** Stop and join WBG receiver thread. */
    void stop_wbg_receiver();

    /** Poll and apply the opt-in in-process joystick command source. */
    void update_unified_command(bool shared_reader_already_polled,
                                bool source_fresh = true);

    /** Append one completed control tick when CSV recording is enabled. */
    void record_step(bool policy_active,
                     const ObsTerms& terms,
                     const torch::Tensor& policy_obs,
                     const torch::Tensor& action,
                     const torch::Tensor& condition);
};

}  // namespace diffusion_deploy
