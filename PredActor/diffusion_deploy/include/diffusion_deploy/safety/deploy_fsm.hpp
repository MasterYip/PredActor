/**
 * deploy_fsm.hpp
 *
 * YAML-driven Finite State Machine for safe robot deployment.
 *
 * Configuration follows the reference style from temp/deploy:
 *
 *   FSM:
 *     _:                    # enabled states (first = initial)
 *       Passive:  {id: 1}
 *       Ready:    {id: 2}
 *       Running:  {id: 3, type: policy}
 *
 *     Passive:
 *       transitions:
 *         Ready: RB.on_pressed
 *       kd: [3, 3, ...]     # 29 values, MuJoCo order
 *
 *     Ready:
 *       transitions:
 *         Passive: B.on_pressed
 *         Running: START.on_pressed
 *       kp: [100, 100, ...]
 *       kd: [2, 2, ...]
 *       ts: [0, 2.0]        # interpolation time stamps [s]
 *       qs:                  # written in MuJoCo (SDK) order, auto-converted to IsaacLab at load
 *         - []               # empty = capture current joint pos at entry
 *         - [-0.1, ...]      # target stand pose (MuJoCo order, 29 DOF)
 *
 *     Running:
 *       transitions:
 *         Passive: B.on_pressed
 *       # no kp/kd → inherits from deploy config
 *
 * State types:
 *   (empty)  — normal: uses state's kp/kd + target pose (with interpolation)
 *   "policy" — diffusion policy runs; should_run_policy() == true
 *
 * Passive detection: a state with no 'kp' (or all zeros) triggers kp=0
 * in the motor commands → robot is limp.
 *
 * Dependencies: joystick_reader.hpp, safety_validator.hpp, yaml-cpp.
 */
#pragma once

#include "diffusion_deploy/safety/joystick_reader.hpp"
#include "diffusion_deploy/safety/safety_validator.hpp"

#include <yaml-cpp/yaml.h>

#include <array>
#include <vector>
#include <string>
#include <map>
#include <chrono>
#include <iostream>
#include <cmath>
#include <cassert>

namespace diffusion_deploy {
namespace safety {

// =====================================================================
//  Button trigger
// =====================================================================

enum class TriggerType {
    OnPressed,   // rising edge (just pressed this cycle)
    Pressed,     // level (currently held)
    OnReleased,  // falling edge (just released this cycle)
};

struct ButtonTrigger {
    JoystickButton button;
    TriggerType    type = TriggerType::OnPressed;
};

/** Parse a trigger string, e.g. "RB.on_pressed", "START.pressed". */
inline ButtonTrigger parse_trigger(const std::string& s) {
    ButtonTrigger result;

    // split on '.'
    auto dot = s.find('.');
    std::string btn_name = (dot != std::string::npos) ? s.substr(0, dot) : s;
    std::string evt_name = (dot != std::string::npos) ? s.substr(dot + 1) : "on_pressed";

    result.button = button_from_name(btn_name);

    if (evt_name == "pressed")       result.type = TriggerType::Pressed;
    else if (evt_name == "on_released") result.type = TriggerType::OnReleased;
    else                             result.type = TriggerType::OnPressed;  // default

    return result;
}

/** Evaluate a ButtonTrigger against current joystick state. */
inline bool evaluate_trigger(const ButtonTrigger& t, const JoystickReader& js) {
    switch (t.type) {
        case TriggerType::OnPressed:  return js.just_pressed(t.button);
        case TriggerType::Pressed:    return js.is_pressed(t.button);
        case TriggerType::OnReleased: return js.just_released(t.button);
    }
    return false;
}

// =====================================================================
//  FSM state definition (parsed from YAML)
// =====================================================================

struct FSMStateDef {
    std::string name;
    int         id   = 0;
    std::string type;  // "" = normal, "policy" = runs diffusion

    // Gains (MuJoCo SDK joint order).  Empty kp → passive (kp=0).
    std::vector<float> kp;
    std::vector<float> kd;

    // Transitions: list of (target_state, trigger) pairs
    std::vector<std::pair<std::string, ButtonTrigger>> transitions;

    // Interpolation into this state (matches reference ts/qs format)
    bool has_interpolation = false;
    std::vector<float>              interp_ts;
    std::vector<std::vector<float>> interp_qs;  // empty first element = capture current
};

// =====================================================================
//  Complete FSM definition (set of states)
// =====================================================================

struct FSMDefinition {
    std::vector<FSMStateDef>         states;
    std::map<std::string, int>       state_index;  // name → index in states[]
    int                              initial_idx = 0;
    std::string                      fallback_state;  // safety fallback target
    bool                             has_fallback = false;
};

// =====================================================================
//  Joint order conversion
// =====================================================================

/**
 * Reindex a 29-DOF joint position vector from MuJoCo (SDK) order
 * to IsaacLab (training) order.
 *
 * MuJoCo order (matches physical motor numbering / LowState):
 *   left_leg[6], right_leg[6], waist[3], left_arm[7], right_arm[7]
 *
 * IsaacLab order (alphabetical by joint name):
 *   interleaved left/right, mixed body parts
 *
 * Identity passthrough if size != 29 (graceful degradation).
 */
inline std::vector<float> reindex_mujoco_to_isaaclab(const std::vector<float>& mujoco_qs) {
    if (mujoco_qs.size() != 29) return mujoco_qs;

    // MUJOCO_TO_ISAACLAB_REINDEX[i] = MuJoCo index for IsaacLab position i
    // i.e.  isaaclab[i] = mujoco[MUJOCO_TO_ISAACLAB_REINDEX[i]]
    static const std::vector<int> m2i = {
        0, 6, 12, 1, 7, 13, 2, 8, 14,
        3, 9, 15, 22, 4, 10, 16, 23, 5, 11, 17, 24,
        18, 25, 19, 26, 20, 27, 21, 28
    };

    std::vector<float> isaaclab_qs(29);
    for (int i = 0; i < 29; ++i) {
        isaaclab_qs[i] = mujoco_qs[m2i[i]];
    }
    return isaaclab_qs;
}

// =====================================================================
//  YAML loading
// =====================================================================

/**
 * Parse an FSM definition from a YAML node at the "FSM:" key.
 *
 * The node must contain:
 *   _:  <map of enabled states: name → {id, [type]}>
 *   <StateName>:  {transitions, [kp], [kd], [ts], [qs]}
 *
 * The first state under "_" is the initial state.
 * The first state whose kp is empty/absent is used as the fallback target.
 *
 * Convention:
 *   - kp / kd: stored in MuJoCo (SDK) order (matches hardware motor numbering)
 *   - qs:     written in MuJoCo (SDK) order in YAML, automatically converted
 *             to IsaacLab order at load time for internal use.
 */
inline FSMDefinition load_fsm_definition(const YAML::Node& fsm_root) {
    FSMDefinition def;

    if (!fsm_root["_"]) {
        throw std::runtime_error("FSM YAML: missing '_' key for enabled states");
    }

    // ---- Parse enabled states (order preserved by YAML map iteration) ----
    auto enabled = fsm_root["_"];
    std::vector<std::string> state_order;
    for (auto it = enabled.begin(); it != enabled.end(); ++it) {
        std::string name = it->first.as<std::string>();
        auto       info  = it->second;

        FSMStateDef sd;
        sd.name = name;
        sd.id   = info["id"] ? info["id"].as<int>() : 0;
        if (info["type"]) sd.type = info["type"].as<std::string>();

        def.state_index[name] = static_cast<int>(def.states.size());
        def.states.push_back(sd);
        state_order.push_back(name);
    }

    if (def.states.empty()) {
        throw std::runtime_error("FSM YAML: no enabled states under '_'");
    }
    def.initial_idx = 0;  // first listed state

    // ---- Parse per-state sections ----
    for (auto& sd : def.states) {
        if (!fsm_root[sd.name]) continue;  // no extra config
        auto sn = fsm_root[sd.name];

        // Transitions
        if (sn["transitions"]) {
            for (auto tr = sn["transitions"].begin(); tr != sn["transitions"].end(); ++tr) {
                std::string target = tr->first.as<std::string>();
                std::string expr   = tr->second.as<std::string>();
                sd.transitions.push_back({target, parse_trigger(expr)});
            }
        }

        // Gains (kp / kd)
        if (sn["kp"]) {
            sd.kp = sn["kp"].as<std::vector<float>>();
        }
        if (sn["kd"]) {
            sd.kd = sn["kd"].as<std::vector<float>>();
        }

        // Interpolation (ts / qs)
        // qs in YAML is written in MuJoCo (SDK) order; convert to IsaacLab
        // order here so that all downstream code (get_target_action, etc.)
        // works with IsaacLab-order positions consistently.
        if (sn["ts"] && sn["qs"]) {
            sd.has_interpolation = true;
            sd.interp_ts = sn["ts"].as<std::vector<float>>();
            for (auto qnode : sn["qs"]) {
                if (qnode.IsSequence() && qnode.size() > 0) {
                    sd.interp_qs.push_back(
                        reindex_mujoco_to_isaaclab(qnode.as<std::vector<float>>()));
                } else {
                    sd.interp_qs.push_back({});  // empty = capture current
                }
            }
        }
    }

    // ---- Identify fallback state (first state with no kp) ----
    for (auto& sd : def.states) {
        if (sd.kp.empty() || std::all_of(sd.kp.begin(), sd.kp.end(),
                                          [](float v) { return v == 0.0f; })) {
            def.fallback_state = sd.name;
            def.has_fallback   = true;
            break;
        }
    }

    // ---- Validate transitions reference real states ----
    for (auto& sd : def.states) {
        for (auto& [target, _] : sd.transitions) {
            if (!def.state_index.count(target)) {
                std::cerr << "[FSM] Warning: state '" << sd.name
                          << "' has transition to unknown state '" << target << "'\n";
            }
        }
    }

    return def;
}

// =====================================================================
//  Linear interpolator (matches temp/deploy/include/LinearInterpolator.h)
// =====================================================================

/**
 * Piecewise-linear interpolation across waypoints in time.
 *
 * Usage:
 *   LinearInterpolator interp(ts, qs, current_joint_pos);
 *   // ... each tick:
 *   auto target = interp.step(elapsed_seconds);
 *   bool done   = interp.is_done(elapsed_seconds);
 */
class LinearInterpolator {
public:
    /**
     * @param ts  Time stamps [s].  Must be monotonically increasing.
     * @param qs  Joint position waypoints (same length as ts).
     * @param current_q  Initial joint positions.  Used to fill any
     *                   empty waypoint (qs[i].empty() == true).
     */
    LinearInterpolator(const std::vector<float>& ts,
                       std::vector<std::vector<float>> qs,
                       const std::vector<float>& current_q)
        : ts_(ts), qs_(std::move(qs))
    {
        assert(ts_.size() == qs_.size() && ts_.size() >= 2);

        // Fill empty waypoints with current positions
        for (auto& q : qs_) {
            if (q.empty()) q = current_q;
        }
    }

    /** Get interpolated position at elapsed time `t` (seconds since entry). */
    std::vector<float> step(float t) const {
        if (t <= ts_[0]) return qs_[0];
        if (t >= ts_.back()) return qs_.back();

        // Find segment
        for (size_t i = 0; i < ts_.size() - 1; ++i) {
            if (t >= ts_[i] && t <= ts_[i + 1]) {
                float alpha = (t - ts_[i]) / (ts_[i + 1] - ts_[i]);
                size_t n = qs_[i].size();
                std::vector<float> result(n);
                for (size_t j = 0; j < n; ++j) {
                    result[j] = qs_[i][j] * (1.0f - alpha) + qs_[i + 1][j] * alpha;
                }
                return result;
            }
        }
        return qs_.back();  // unreachable
    }

    /** True when elapsed >= final time stamp. */
    bool is_done(float t) const { return t >= ts_.back(); }

    /** Final target position. */
    const std::vector<float>& target() const { return qs_.back(); }

private:
    std::vector<float>              ts_;
    std::vector<std::vector<float>> qs_;
};

// =====================================================================
//  State-change notification
// =====================================================================

struct StateChange {
    bool        changed = false;
    std::string from;
    std::string to;
};

// =====================================================================
//  DeployFSM
// =====================================================================

class DeployFSM {
public:
    /**
     * @param def              Parsed FSM definition.
     * @param joystick_device  Path to joystick device, e.g. "/dev/input/js0".
     * @param joystick_mapping Controller mapping: "xbox" (default) or "ps5".
     */
    DeployFSM(const FSMDefinition& def,
              const std::string& joystick_device  = "/dev/input/js0",
              const std::string& joystick_mapping = "xbox")
        : def_(def)
        , joystick_(joystick_device, joystick_mapping)
    {
        state_idx_ = def_.initial_idx;

        std::cout << "[DeployFSM] Initialised.  states=" << def_.states.size()
                  << "  initial=" << current_def().name
                  << "  fallback=" << (def_.has_fallback ? def_.fallback_state : "(none)")
                  << "  joystick=" << (joystick_.is_connected() ? "connected" : "NOT FOUND")
                  << "  limit=" << config_.bad_orientation_limit_deg << "°\n";

        std::cout << "[DeployFSM] States:";
        for (auto& sd : def_.states) {
            std::cout << " " << sd.name;
            if (!sd.type.empty()) std::cout << "(type=" << sd.type << ")";
        }
        std::cout << "\n";
    }

    // ---- Main update ----

    /**
     * Call once per control tick.
     *
     * @param imu_quat       Latest IMU quaternion [w,x,y,z] for fall detection.
     * @param dt             Timestep [s] since last call, for interpolation.
     * @param joint_torques  Joint torque estimates [N·m] in MuJoCo order (empty = skip check).
     */
    void update(const std::array<float, 4>& imu_quat, double dt,
                const std::vector<float>& joint_torques = {}) {
        last_change_.changed = false;
        dt_ = static_cast<float>(dt);

        // 1. Poll joystick
        joystick_.poll();

        // 2. Safety: gravity-based fall detection
        if (config_.auto_passive_on_fall && def_.has_fallback) {
            auto proj_g = projected_gravity(imu_quat);
            float limit_rad = config_.bad_orientation_limit_deg
                              * (static_cast<float>(M_PI) / 180.0f);
            if (bad_orientation(proj_g[2], limit_rad)) {
                if (current_def().name != def_.fallback_state) {
                    std::cerr << "[DeployFSM] SAFETY: bad orientation → "
                              << def_.fallback_state << "\n";
                    transition_to(def_.fallback_state);
                }
                return;
            }
        }

        // 3. Safety: torque protection (per-joint limits)
        if (!config_.torque_limits.empty() && !joint_torques.empty() && def_.has_fallback) {
            size_t n = std::min(joint_torques.size(), config_.torque_limits.size());
            for (size_t i = 0; i < n; ++i) {
                float limit = config_.torque_limits[i];
                if (limit > 0.0f && std::fabs(joint_torques[i]) > limit) {
                    if (current_def().name != def_.fallback_state) {
                        std::cerr << "[DeployFSM] SAFETY: joint " << i
                                  << " torque " << joint_torques[i]
                                  << " N·m > limit " << limit
                                  << " → " << def_.fallback_state << "\n";
                        transition_to(def_.fallback_state);
                    }
                    return;
                }
            }
        }

        // 4. Evaluate state transitions
        for (auto& [target_name, trigger] : current_def().transitions) {
            if (evaluate_trigger(trigger, joystick_)) {
                if (target_name != current_def().name) {
                    std::cout << "[DeployFSM] joystick trigger: → " << target_name << "\n";
                    transition_to(target_name);
                }
                break;  // only one transition per tick
            }
        }
    }

    // ---- Accessors ----

    /** Current state name (e.g. "Passive", "Ready", "Running"). */
    const std::string& state_name() const { return current_def().name; }

    /** True when the current state runs the diffusion policy. */
    bool should_run_policy() const { return current_def().type == "policy"; }

    /**
     * True when the current state should send kp=0 in motor commands.
     *
     * A state is passive when:
     *   - It is NOT a policy state (policy states inherit config gains), AND
     *   - Its kp is empty or all zeros (explicitly configured as passive).
     */
    bool is_passive() const {
        if (current_def().type == "policy") return false;
        const auto& kp = current_def().kp;
        return kp.empty() || std::all_of(kp.begin(), kp.end(),
                                         [](float v) { return v == 0.0f; });
    }

    const StateChange& last_change() const { return last_change_; }

    JoystickReader& joystick() { return joystick_; }
    const JoystickReader& joystick() const { return joystick_; }

    // ---- Action & gain queries (for EnvRunner integration) ----

    /**
     * Target joint positions for the current state (IsaacLab order).
     *
     * Behaviour depends on state type:
     *   - Passive (no kp): track current joint positions
     *   - With interpolation:  interpolate toward target
     *   - No interpolation:    return final qs waypoint (or current pos if none)
     *
     * @param current_joint_pos  Latest joint positions (IsaacLab order).
     * @param dt                 Timestep [s] since last call.
     */
    std::vector<float> get_target_action(const std::vector<float>& current_joint_pos, double dt) {
        // Passive: track current position
        if (is_passive()) {
            return current_joint_pos;
        }

        // Interpolation active
        if (interp_) {
            interp_elapsed_ += static_cast<float>(dt);
            return interp_->step(interp_elapsed_);
        }

        // Static target (stand pose)
        if (!current_def().interp_qs.empty()) {
            // Return the final waypoint
            const auto& last = current_def().interp_qs.back();
            if (!last.empty()) return last;
        }

        // Fallback: hold current position
        return current_joint_pos;
    }

    /** Current state's Kp gains (MuJoCo order). Empty → passive. */
    const std::vector<float>& current_kp() const { return current_def().kp; }

    /** Current state's Kd gains (MuJoCo order). */
    const std::vector<float>& current_kd() const { return current_def().kd; }

    // ---- Configuration exposed for CLI overrides ----
    struct RuntimeConfig {
        float bad_orientation_limit_deg = 57.3f;
        bool  auto_passive_on_fall      = true;
        /// Per-joint torque limits [N·m] (MuJoCo order).  Empty = disabled.
        std::vector<float> torque_limits;
    };
    RuntimeConfig config_;

private:
    FSMDefinition           def_;
    JoystickReader          joystick_;
    int                     state_idx_ = 0;
    StateChange             last_change_;
    float                   dt_ = 0.02f;

    // Interpolation state (created on state entry, destroyed on exit)
    std::unique_ptr<LinearInterpolator> interp_;
    float                               interp_elapsed_ = 0.0f;

    const FSMStateDef& current_def() const { return def_.states[state_idx_]; }

    void transition_to(const std::string& target_name) {
        auto it = def_.state_index.find(target_name);
        if (it == def_.state_index.end()) {
            std::cerr << "[DeployFSM] Unknown target state: " << target_name << "\n";
            return;
        }

        int new_idx = it->second;
        if (new_idx == state_idx_) return;

        // Exit current state
        interp_.reset();
        interp_elapsed_ = 0.0f;

        last_change_.changed = true;
        last_change_.from    = current_def().name;
        last_change_.to      = target_name;

        state_idx_ = new_idx;
        std::cout << "[DeployFSM] " << last_change_.from
                  << " → " << last_change_.to << "\n";

        // Print available transitions from the new state
        const auto& sd = current_def();
        if (!sd.transitions.empty()) {
            std::cout << "[DeployFSM] " << sd.name << " actions:";
            for (auto& [tgt, trig] : sd.transitions) {
                // Build a human-readable trigger string
                std::string desc;
                switch (trig.type) {
                    case TriggerType::OnPressed:  desc = "press"; break;
                    case TriggerType::Pressed:    desc = "hold";  break;
                    case TriggerType::OnReleased: desc = "release"; break;
                }
                // Map button enum back to name
                const char* btn_name = "?";
                switch (trig.button) {
                    case JoystickButton::A:     btn_name = "A"; break;
                    case JoystickButton::B:     btn_name = "B"; break;
                    case JoystickButton::X:     btn_name = "X"; break;
                    case JoystickButton::Y:     btn_name = "Y"; break;
                    case JoystickButton::LB:    btn_name = "LB"; break;
                    case JoystickButton::RB:    btn_name = "RB"; break;
                    case JoystickButton::BACK:  btn_name = "BACK"; break;
                    case JoystickButton::START: btn_name = "START"; break;
                    case JoystickButton::GUIDE: btn_name = "GUIDE"; break;
                    case JoystickButton::LS:    btn_name = "LS"; break;
                    case JoystickButton::RS:    btn_name = "RS"; break;
                }
                std::cout << " [" << desc << " " << btn_name << " → " << tgt << "]";
            }
            std::cout << "\n";
        }

        // Enter new state — create interpolator if configured
        if (sd.has_interpolation && !sd.interp_qs.empty()) {
            // We don't have current joint pos here — caller provides that
            // via get_target_action().  Defer creation to first call.
            // For now, mark that interpolation should be created lazily.
            interp_needs_current_ = true;
        }
    }

    // Lazy interpolation init flag
    bool interp_needs_current_ = false;

    /** Create the interpolator using current joint positions.
     *  Called internally by get_target_action() on first use after state entry. */
    void ensure_interp(const std::vector<float>& current_q) {
        if (!interp_needs_current_) return;
        interp_needs_current_ = false;
        interp_elapsed_       = 0.0f;

        const auto& sd = current_def();
        if (sd.has_interpolation && sd.interp_ts.size() >= 2
            && sd.interp_qs.size() == sd.interp_ts.size()) {
            interp_ = std::make_unique<LinearInterpolator>(
                sd.interp_ts, sd.interp_qs, current_q);
        }
    }

public:
    /** Allow EnvRunner to trigger lazy interpolator creation. */
    void init_interpolation(const std::vector<float>& current_q) {
        ensure_interp(current_q);
    }
};

}  // namespace safety
}  // namespace diffusion_deploy
