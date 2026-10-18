/**
 * realtime_looper.hpp
 *
 * Tracks loop timing and optionally enforces a target period.
 *
 * Mirrors diffusion_policy/utils/realtime_looper.py::RealtimeLooper.
 *
 * Features:
 *   - Sliding window of recent loop durations (configurable size).
 *   - Periodic status log: rate [Hz], realtime factor, min/max factor.
 *   - Overrun warning printed to stderr + cumulative overrun counter.
 *   - Optional sleep to enforce target_dt.
 *   - Header-only; no LibTorch dependency.
 *
 * Usage:
 *   RealtimeLooper looper("env_runner_loop", 50, 2.0);
 *
 *   for (int step = 0; ...; ++step) {
 *       auto t0 = RealtimeLooper::now();
 *       do_work();
 *       looper.record(t0, target_dt, enforce=true);
 *   }
 */
#pragma once

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <deque>
#include <functional>
#include <iostream>
#include <numeric>
#include <string>
#include <thread>

namespace diffusion_deploy {

class RealtimeLooper {
public:
    using Clock     = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;
    using Logger    = std::function<void(const std::string&)>;

    /**
     * @param name           Label printed in log lines.
     * @param window_size    Number of recent steps kept for statistics.
     * @param print_interval Minimum wall-clock seconds between status prints
     *                       (0 = never print).
     * @param logger         Sink for status messages (default: stdout).
     */
    explicit RealtimeLooper(
        std::string name           = "loop",
        int         window_size    = 50,
        double      print_interval = 2.0,
        Logger      logger         = nullptr)
        : name_(std::move(name))
        , window_size_(std::max(1, window_size))
        , print_interval_(std::max(0.0, print_interval))
        , logger_(logger ? std::move(logger)
                         : [](const std::string& s){ std::cout << s << "\n"; })
        , last_log_time_(Clock::now())
    {}

    // ---- Static helper ----

    /** Capture current time — call immediately before the loop body. */
    static TimePoint now() { return Clock::now(); }

    // ---- Core method ----

    /**
     * Record one loop iteration; optionally sleep to meet target_dt.
     *
     * Measures elapsed work time before sleeping, warns to stderr on overrun
     * (increments overrun_count()), then sleeps the remaining budget if
     * enforce=true.  Stores the full loop duration (work + sleep) in the
     * sliding window for rate/rtf statistics.
     *
     * @param step_start  Time captured immediately before the loop body.
     * @param target_dt   Desired loop period [s].  0 = no sleep / no enforce.
     * @param enforce     If true, sleep remaining time to hit target_dt.
     * @return            Actual wall-clock duration of this step [s].
     */
    double record(TimePoint step_start, double target_dt, bool enforce = true) {
        target_dt_ = target_dt;
        enforce_   = enforce;

        // Measure work time before any sleep
        double work_s = to_sec(Clock::now() - step_start);

        // Overrun: work alone already exceeds the budget
        if (target_dt > 0.0 && work_s > target_dt) {
            ++overrun_count_;
            char buf[128];
            std::snprintf(buf, sizeof(buf),
                "[%s] loop overrun: %.2f ms > target %.2f ms",
                name_.c_str(), work_s * 1000.0, target_dt * 1000.0);
            std::cerr << buf << "\n";
        }

        // Optional rate-enforcement sleep
        if (enforce && target_dt > 0.0) {
            double remaining = target_dt - work_s;
            if (remaining > 0.0)
                std::this_thread::sleep_for(std::chrono::duration<double>(remaining));
        }

        // Record full loop duration (work + sleep)
        double loop_dt = to_sec(Clock::now() - step_start);
        if (static_cast<int>(dts_.size()) >= window_size_)
            dts_.pop_front();
        dts_.push_back(loop_dt);

        maybe_log();
        return loop_dt;
    }

    // ---- Properties ----

    /** Mean loop rate over the sliding window [Hz]. */
    double current_hz() const {
        double m = mean_dt();
        return m > 0.0 ? 1.0 / m : 0.0;
    }

    /**
     * Realtime factor: target_dt / mean_actual_dt.
     * 1.0 = exactly on time; <1.0 = slower than real time.
     */
    double realtime_factor() const {
        if (dts_.empty() || target_dt_ <= 0.0) return 0.0;
        double m = mean_dt();
        return m > 0.0 ? target_dt_ / m : 0.0;
    }

    /** Total overruns since construction or last reset(). */
    int overrun_count() const { return overrun_count_; }

    // ---- Snapshot ----

    struct Snapshot {
        double target_dt       = 0.0;
        bool   enforcing       = false;
        double hz              = 0.0;
        double realtime_factor = 0.0;
        double min_factor      = 0.0;  ///< factor of fastest step in window
        double max_factor      = 0.0;  ///< factor of slowest step in window
        int    overrun_count   = 0;
    };

    Snapshot snapshot() const {
        Snapshot s;
        s.target_dt       = target_dt_;
        s.enforcing       = enforce_;
        s.hz              = current_hz();
        s.realtime_factor = realtime_factor();
        s.overrun_count   = overrun_count_;
        if (!dts_.empty() && target_dt_ > 0.0) {
            double worst = *std::max_element(dts_.begin(), dts_.end());
            double best  = *std::min_element(dts_.begin(), dts_.end());
            s.min_factor = worst > 0.0 ? target_dt_ / worst : 0.0;
            s.max_factor = best  > 0.0 ? target_dt_ / best  : 0.0;
        }
        return s;
    }

    // ---- Reset ----

    /** Clear all accumulated statistics and overrun counter. */
    void reset() {
        dts_.clear();
        overrun_count_  = 0;
        last_log_time_  = Clock::now();
    }

private:
    std::string name_;
    int         window_size_;
    double      print_interval_;
    Logger      logger_;

    std::deque<double> dts_;
    TimePoint          last_log_time_;
    double             target_dt_    = 0.0;
    bool               enforce_      = true;
    int                overrun_count_ = 0;

    // ---- Helpers ----

    static double to_sec(Clock::duration d) {
        return std::chrono::duration<double>(d).count();
    }

    double mean_dt() const {
        if (dts_.empty()) return 0.0;
        return std::accumulate(dts_.begin(), dts_.end(), 0.0)
               / static_cast<double>(dts_.size());
    }

    void maybe_log() {
        if (print_interval_ <= 0.0) return;
        if (to_sec(Clock::now() - last_log_time_) < print_interval_) return;
        if (dts_.empty()) return;

        auto s = snapshot();
        char buf[256];
        std::snprintf(buf, sizeof(buf),
            "[%s] rate: %.2f Hz | rtf: %.2fx (min: %.2fx, max: %.2fx)",
            name_.c_str(), s.hz, s.realtime_factor, s.min_factor, s.max_factor);
        logger_(buf);
        last_log_time_ = Clock::now();
    }
};

}  // namespace diffusion_deploy
