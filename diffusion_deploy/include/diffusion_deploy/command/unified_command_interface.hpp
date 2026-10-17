/**
 * Unified joystick command source for deployment.
 *
 * One JoystickReader drives both fast WBG values and edge-triggered selection
 * of pre-exported text-condition latents.  Control is in-process by default;
 * UDP output is an explicit compatibility/debug option.
 */
#pragma once

#include "diffusion_deploy/safety/joystick_reader.hpp"
#include "diffusion_deploy/guidance/whole_body_guidance.hpp"

#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace diffusion_deploy {

enum class UnifiedCommandSource {
    Auto,
    Joydev,
    UnitreeLowState,
};

UnifiedCommandSource parse_unified_command_source(const std::string& value);
const char* unified_command_source_name(UnifiedCommandSource source);

struct MotionLatentConfig {
    std::string name;
    std::string dpad;       ///< up | right | down | left
    std::string path;       ///< raw little-endian float32, exactly dim entries
    std::string hash;       ///< required fnv1a64:<16 lower-case hex digits>
    int dim = 512;
};

struct UnifiedCommandUdpConfig {
    bool enabled = false;
    std::string host = "127.0.0.1";
    int condition_port = 9877;
    int wbg_port = 9879;
};

struct UnifiedCommandTelemetryConfig {
    bool enabled = false;
    std::string host = "127.0.0.1";
    int port = 9880;
};

struct UnifiedWbgControlConfig {
    // Disabled preserves the legacy fixed wbg.kp behavior.
    bool l2_kp_enabled = false;
    std::string kp_axis = "l2";
    float kp_unpressed = 1.0f;
    float kp_pressed = 0.0f;
    bool lb_toggle_enabled = false;
    std::string toggle_button = "LB";
    int toggle_debounce_ms = 150;
};

struct UnifiedCommandConfig {
    bool enabled = false;
    // Auto preserves the legacy device-based behavior: an empty/null device
    // selects the FSM's external Unitree state, otherwise Linux joydev.
    UnifiedCommandSource source = UnifiedCommandSource::Auto;
    std::string joystick_device = "/dev/input/js0";
    std::string joystick_mapping = "xbox";
    double source_timeout_s = 0.10;
    float deadzone = 0.10f;
    int dpad_debounce_ms = 150;
    float max_vx = 5.0f;
    float max_vy = 5.0f;
    float max_wz = 5.0f;
    float wbg_kp = 1.0f;
    bool wbg_enabled = true;
    UnifiedWbgControlConfig wbg_controls;
    std::vector<MotionLatentConfig> motions;
    UnifiedCommandUdpConfig compatibility_udp;
    UnifiedCommandTelemetryConfig telemetry;
};

UnifiedCommandSource resolve_unified_command_source(
    const UnifiedCommandConfig& config);

struct UnifiedWbgCommand {
    float vx = 0.0f;
    float vy = 0.0f;
    float wz = 0.0f;
    float kp = 1.0f;
    bool enabled = true;
    bool linear_enabled = true;  ///< L3 toggles vx and vy together.
    bool yaw_enabled = true;     ///< R3 toggles wz independently.
};

struct UnifiedCommandState {
    uint64_t sequence = 0;
    uint64_t monotonic_ms = 0;
    bool joystick_connected = false;
    std::string motion_name;
    std::string motion_hash;
    std::vector<float> latent;
    UnifiedWbgCommand wbg;
};

/** Pure deterministic D-pad edge/debounce state machine. */
class DpadSelector {
public:
    explicit DpadSelector(int debounce_ms = 150);
    /** Returns -1 for no change, otherwise up=0/right=1/down=2/left=3. */
    int update(int x, int y, uint64_t monotonic_ms);

private:
    int debounce_ms_;
    int previous_ = -1;
    uint64_t last_change_ms_ = 0;
    bool has_change_ = false;
};

/** Pure rising-edge/debounce toggle used by the LB, L3, and R3 controls. */
class RisingEdgeToggle {
public:
    RisingEdgeToggle(bool initial_state, int debounce_ms = 150);
    /** Updates the input and returns true only when the output toggles. */
    bool update(bool pressed, uint64_t monotonic_ms);
    bool state() const { return state_; }

private:
    bool state_;
    bool previous_pressed_ = false;
    int debounce_ms_;
    uint64_t last_toggle_ms_ = 0;
    bool has_toggled_ = false;
};

float apply_joystick_deadzone(float value, float deadzone);
float l2_pressure_to_kp(float pressure, float kp_unpressed = 1.0f,
                        float kp_pressed = 0.0f);
uint64_t fnv1a64(const void* data, std::size_t size);
std::string fnv1a64_string(const void* data, std::size_t size);
std::array<float, 9> make_legacy_wbg_packet(const UnifiedWbgCommand& command);
WbgUdpFrame make_live_wbg_frame(const UnifiedWbgCommand& command);

class UnifiedCommandInterface {
public:
    /**
     * shared_reader is used when the safety FSM already owns the joystick.
     * If null, this class owns the only reader.  Call poll(true) only after a
     * shared reader has already been polled in that control cycle.
     */
    explicit UnifiedCommandInterface(
        UnifiedCommandConfig config,
        safety::JoystickReader* shared_reader = nullptr);
    ~UnifiedCommandInterface();

    UnifiedCommandInterface(const UnifiedCommandInterface&) = delete;
    UnifiedCommandInterface& operator=(const UnifiedCommandInterface&) = delete;

    const UnifiedCommandState& poll(bool shared_reader_already_polled = false,
                                    uint64_t monotonic_ms = 0,
                                    bool source_fresh = true);
    const UnifiedCommandState& state() const { return state_; }
    const UnifiedCommandConfig& config() const { return config_; }
    UnifiedCommandSource resolved_source() const { return resolved_source_; }
    safety::JoystickReader& joystick() { return *reader_; }

private:
    struct LoadedMotion {
        MotionLatentConfig config;
        std::vector<float> values;
    };

    UnifiedCommandConfig config_;
    UnifiedCommandSource resolved_source_ = UnifiedCommandSource::Joydev;
    std::unique_ptr<safety::JoystickReader> owned_reader_;
    safety::JoystickReader* reader_ = nullptr;
    DpadSelector selector_;
    RisingEdgeToggle wbg_toggle_;
    RisingEdgeToggle linear_guidance_toggle_;
    RisingEdgeToggle yaw_guidance_toggle_;
    std::array<LoadedMotion, 4> motions_;
    UnifiedCommandState state_;
    int compatibility_socket_ = -1;
    int telemetry_socket_ = -1;

    void validate_and_load_motions();
    void select_motion(int index);
    void send_optional_udp();
};

}  // namespace diffusion_deploy
