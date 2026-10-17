/**
 * joystick_reader.hpp
 *
 * Gamepad reader wrapping joystick_parser.hpp with edge detection.
 *
 * Opens /dev/input/js0 (configurable) via joystick::JoystickParser.
 * Adds on_pressed / on_released edge detection and press-time tracking
 * on top of the parser's raw button state.
 *
 * Supports both raw button indices (A=0, B=1, ...) and logical names
 * (south, east, west, north, l1, r1, select, start, ...).
 *
 * Configurable per controller type: "xbox" (default) or "ps5".
 */
#pragma once

#include "diffusion_deploy/utils/joystick_parser.hpp"

#include <chrono>
#include <array>
#include <cstdint>
#include <string>
#include <iostream>

namespace diffusion_deploy {
namespace safety {

// ---- Button index constants (raw Linux gamepad numbering) ----
enum class JoystickButton : int {
    A      = 0,
    B      = 1,
    X      = 2,
    Y      = 3,
    LB     = 4,
    RB     = 5,
    BACK   = 6,
    START  = 7,
    GUIDE  = 8,
    LS     = 9,
    RS     = 10,
};

// ---- Logical-name-to-button-index mapping (Xbox controller) ----
// Matches joystick_parser.hpp xbox_mapping() button names.
inline JoystickButton button_from_logical(const std::string& name) {
    if (name == "south")  return JoystickButton::A;
    if (name == "east")   return JoystickButton::B;
    if (name == "west")   return JoystickButton::X;
    if (name == "north")  return JoystickButton::Y;
    if (name == "l1")     return JoystickButton::LB;
    if (name == "r1")     return JoystickButton::RB;
    if (name == "select") return JoystickButton::BACK;
    if (name == "start")  return JoystickButton::START;
    if (name == "mode")   return JoystickButton::GUIDE;
    if (name == "l3")     return JoystickButton::LS;
    if (name == "r3")     return JoystickButton::RS;
    return JoystickButton::A; // fallback
}

// Recognisable button names for config parsing.
// Accepts both raw names (A/B/X/Y) and logical names (south/east/west/north).
inline JoystickButton button_from_name(const std::string& name) {
    // Raw names (backward compatible)
    if (name == "A" || name == "a")           return JoystickButton::A;
    if (name == "B" || name == "b")           return JoystickButton::B;
    if (name == "X" || name == "x")           return JoystickButton::X;
    if (name == "Y" || name == "y")           return JoystickButton::Y;
    if (name == "LB" || name == "lb")         return JoystickButton::LB;
    if (name == "RB" || name == "rb")         return JoystickButton::RB;
    if (name == "BACK" || name == "back")     return JoystickButton::BACK;
    if (name == "START" || name == "start")   return JoystickButton::START;
    if (name == "GUIDE" || name == "guide")   return JoystickButton::GUIDE;
    if (name == "LS" || name == "ls")         return JoystickButton::LS;
    if (name == "RS" || name == "rs")         return JoystickButton::RS;
    // Logical names
    return button_from_logical(name);
}

// ---- Button state with edge detection ----
struct ButtonState {
    bool  pressed      = false;
    bool  on_pressed   = false;  // rising edge this poll cycle
    bool  on_released  = false;  // falling edge this poll cycle
    float pressed_time = 0.0f;   // seconds (accumulated while held)
};

// ---- External joystick state (fed from Unitree DDS or other source) ----
// Caller populates this from UnitreeJoystick or equivalent, then
// calls JoystickReader::apply_external_state().
struct RawJoystickState {
    // Button pressed flags (index = JoystickButton enum value)
    bool  buttons[16]{};
    // Raw edge flags already computed by source (UnitreeJoystick has these)
    bool  on_pressed[16]{};
    bool  on_released[16]{};
    float pressed_time[16]{};
    // Axes
    float lx = 0, ly = 0, rx = 0, ry = 0, lt = 0, rt = 0;
    int   dpad_x = 0, dpad_y = 0;
    bool  valid = false;
};

/** Decode one Unitree LowState wireless_remote packet into canonical axes. */
RawJoystickState decode_unitree_wireless_remote(
    const std::array<uint8_t, 40>& packet);

// ---- Logical-name → raw-index lookup for axes ----
inline const char* logical_for_axis(int idx) {
    switch (idx) {
        case 0: return "left_x";
        case 1: return "left_y";
        case 2: return "l2";
        case 3: return "right_x";
        case 4: return "right_y";
        case 5: return "r2";
        case 6: return "dpad_x";
        case 7: return "dpad_y";
        default: return nullptr;
    }
}

// ---- JoystickReader (wraps joystick::JoystickParser) ----
class JoystickReader {
public:
    /**
     * @param device_path  e.g. "/dev/input/js0"
     * @param mapping_name Controller mapping: "xbox" (default) or "ps5"
     */
    explicit JoystickReader(const std::string& device_path = "/dev/input/js0",
                            const std::string& mapping_name = "xbox")
        : mapping_(&joystick::get_mapping(mapping_name))
        , parser_(device_path, mapping_)
        , external_mode_(device_path.empty() || device_path == "null")
    {
        if (external_mode_) {
            std::cout << "[JoystickReader] External mode — using Unitree joystick from DDS.\n";
        } else if (parser_.is_connected()) {
            std::cout << "[JoystickReader] Opened " << device_path
                      << "  mapping=" << mapping_->name << "\n";
        }
    }

    /** True when joydev is open or the latest external packet is valid. */
    bool is_connected() const {
        return external_mode_ ? external_connected_ : parser_.is_connected();
    }

    /** True when using external (Unitree DDS) joystick instead of local gamepad. */
    bool is_external_mode() const { return external_mode_; }

    /**
     * Feed joystick state from an external source (e.g. Unitree DDS).
     * Call this before poll() when is_external_mode() is true.
     * The RawJoystickState should be populated from UnitreeJoystick.
     */
    void apply_external_state(const RawJoystickState& ext) {
        if (!external_mode_) return;
        ext_state_      = ext;
        ext_received_   = true;
    }

    /**
     * Read all pending events and update edge-detection state.
     * Must be called once per control cycle.
     */
    void poll() {
        // Handle external mode separately (Unitree joystick from DDS)
        if (external_mode_) {
            // Clear edge flags from previous cycle
            for (auto& bs : button_state_) {
                bs.on_pressed  = false;
                bs.on_released = false;
            }
            if (!ext_received_) return;  // no new packet this cycle

            bool prev_state[kMaxButtons] = {};
            for (int i = 0; i < kMaxButtons; ++i)
                prev_state[i] = button_state_[i].pressed;

            external_connected_ = ext_state_.valid;
            if (!ext_state_.valid) {
                ext_state_ = RawJoystickState{};
            }

            // Compute edges here from the canonical current state. Unitree's
            // helper edge flags are stateful, but LowState packets are decoded
            // independently and must not retrigger while a button is held.
            for (int i = 0; i < kMaxButtons; ++i) {
                button_state_[i].pressed      = ext_state_.buttons[i];
                button_state_[i].on_pressed   = ext_state_.buttons[i] && !prev_state[i];
                button_state_[i].on_released  = !ext_state_.buttons[i] && prev_state[i];
                button_state_[i].pressed_time = ext_state_.pressed_time[i];
            }
            axes_[0] = ext_state_.lx;
            axes_[1] = ext_state_.ly;
            axes_[2] = ext_state_.lt;
            axes_[3] = ext_state_.rx;
            axes_[4] = ext_state_.ry;
            axes_[5] = ext_state_.rt;
            dpad_x_  = ext_state_.dpad_x;
            dpad_y_  = ext_state_.dpad_y;

            ext_received_ = false;  // will be re-fed next cycle
            return;
        }

        // Local gamepad mode
        if (!parser_.is_connected()) return;

        // Clear edge flags from previous cycle
        for (auto& bs : button_state_) {
            bs.on_pressed  = false;
            bs.on_released = false;
        }

        // Compute dt for press-time accumulation
        auto now = std::chrono::steady_clock::now();
        float dt = 0.0f;
        if (last_poll_valid_) {
            dt = std::chrono::duration<float>(now - last_poll_).count();
        }
        last_poll_ = now;
        last_poll_valid_ = true;

        // Read raw state before poll for edge detection
        bool prev_state[kMaxButtons] = {};
        for (int i = 0; i < kMaxButtons; ++i) prev_state[i] = button_state_[i].pressed;

        // Poll the underlying parser
        parser_.poll();

        // Update semantic button slots from the selected mapping. Do not copy
        // physical indices directly: xbox_new exposes START/L3/R3 at different
        // numbers than classic Xbox, while the FSM consumes semantic slots.
        static const char* logical_button_names[] = {
            "south", "east", "west", "north", "l1", "r1",
            "select", "start", "mode", "l3", "r3"
        };
        for (int i = 0; i < kMaxButtons; ++i) {
            const bool raw = i < 11
                ? parser_.get_button(logical_button_names[i]) : false;

            bool was_pressed = prev_state[i];
            button_state_[i].pressed = raw;

            if (raw && !was_pressed) {
                button_state_[i].on_pressed   = true;
                button_state_[i].on_released  = false;
                button_state_[i].pressed_time = 0.0f;
            } else if (!raw && was_pressed) {
                button_state_[i].on_pressed   = false;
                button_state_[i].on_released  = true;
            }

            // Accumulate press time
            if (raw && dt > 0.0f) {
                button_state_[i].pressed_time += dt;
            }
        }

        // Update axes from parser using logical names
        auto read_axis = [&](const char* name) -> float {
            return parser_.get_axis_normalized(name);
        };
        axes_[0] = read_axis("left_x");
        axes_[1] = read_axis("left_y");
        axes_[2] = read_axis("l2");
        axes_[3] = read_axis("right_x");
        axes_[4] = read_axis("right_y");
        axes_[5] = read_axis("r2");
        // D-pad
        dpad_x_ = static_cast<int>(parser_.get_axis_normalized("dpad_x"));
        dpad_y_ = static_cast<int>(parser_.get_axis_normalized("dpad_y"));
    }

    // ---- Button accessors ----

    const ButtonState& button(JoystickButton btn) const {
        return button_state_[static_cast<int>(btn)];
    }
    bool is_pressed(JoystickButton btn) const {
        return button_state_[static_cast<int>(btn)].pressed;
    }
    bool just_pressed(JoystickButton btn) const {
        return button_state_[static_cast<int>(btn)].on_pressed;
    }
    bool just_released(JoystickButton btn) const {
        return button_state_[static_cast<int>(btn)].on_released;
    }
    float pressed_time(JoystickButton btn) const {
        return button_state_[static_cast<int>(btn)].pressed_time;
    }

    // ---- D-pad convenience ----
    bool dpad_up()    const { return dpad_y_ < 0; }
    bool dpad_down()  const { return dpad_y_ > 0; }
    bool dpad_left()  const { return dpad_x_ < 0; }
    bool dpad_right() const { return dpad_x_ > 0; }

    // ---- Analog axes ([-1,1] for sticks, [0,1] for triggers) ----
    float axis_lx() const { return axes_[0]; }
    float axis_ly() const { return axes_[1]; }
    float axis_rx() const { return axes_[3]; }
    float axis_ry() const { return axes_[4]; }
    float axis_lt() const { return axes_[2]; }
    float axis_rt() const { return axes_[5]; }

private:
    static constexpr int kMaxButtons = 16;

    const joystick::JoystickMappingConfig* mapping_;
    joystick::JoystickParser              parser_;

    // Per-button state with edge detection
    std::array<ButtonState, kMaxButtons> button_state_{};
    // Normalised axes: LX, LY, LT, RX, RY, RT
    std::array<float, 6> axes_{};
    int dpad_x_ = 0;
    int dpad_y_ = 0;

    std::chrono::steady_clock::time_point last_poll_;
    bool last_poll_valid_ = false;

    // External mode (Unitree joystick from DDS)
    bool            external_mode_  = false;
    bool            external_connected_ = false;
    RawJoystickState ext_state_;
    bool            ext_received_   = false;
};

}  // namespace safety
}  // namespace diffusion_deploy
