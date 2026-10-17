#include "diffusion_deploy/command/unified_command_interface.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

namespace diffusion_deploy {
namespace {

uint64_t now_ms() {
    return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
}

int direction_index(int x, int y) {
    if (y < 0 && x == 0) return 0;  // up
    if (x > 0 && y == 0) return 1;  // right
    if (y > 0 && x == 0) return 2;  // down
    if (x < 0 && y == 0) return 3;  // left
    return -1;                       // neutral and diagonals
}

int configured_direction(const std::string& value) {
    if (value == "up") return 0;
    if (value == "right") return 1;
    if (value == "down") return 2;
    if (value == "left") return 3;
    throw std::runtime_error("unified_command: dpad must be up/right/down/left");
}

sockaddr_in endpoint(const std::string& host, int port) {
    if (port < 1 || port > 65535)
        throw std::runtime_error("unified_command: UDP port outside 1..65535");
    sockaddr_in out{};
    out.sin_family = AF_INET;
    out.sin_port = htons(static_cast<uint16_t>(port));
    if (inet_pton(AF_INET, host.c_str(), &out.sin_addr) != 1)
        throw std::runtime_error("unified_command: UDP host must be a numeric IPv4 address");
    return out;
}

void send_bytes(int socket_fd, const sockaddr_in& target, const void* data, std::size_t size) {
    const auto sent = sendto(socket_fd, data, size, 0,
                             reinterpret_cast<const sockaddr*>(&target), sizeof(target));
    if (sent != static_cast<ssize_t>(size))
        throw std::runtime_error("unified_command: UDP sendto failed");
}

}  // namespace

UnifiedCommandSource parse_unified_command_source(const std::string& value) {
    if (value == "auto") return UnifiedCommandSource::Auto;
    if (value == "joydev") return UnifiedCommandSource::Joydev;
    if (value == "unitree_lowstate") return UnifiedCommandSource::UnitreeLowState;
    throw std::invalid_argument(
        "unified_command: source must be auto, joydev, or unitree_lowstate");
}

const char* unified_command_source_name(UnifiedCommandSource source) {
    switch (source) {
        case UnifiedCommandSource::Auto: return "auto";
        case UnifiedCommandSource::Joydev: return "joydev";
        case UnifiedCommandSource::UnitreeLowState: return "unitree_lowstate";
    }
    return "unknown";
}

UnifiedCommandSource resolve_unified_command_source(
    const UnifiedCommandConfig& config) {
    if (config.source != UnifiedCommandSource::Auto) return config.source;
    return config.joystick_device.empty() || config.joystick_device == "null"
        ? UnifiedCommandSource::UnitreeLowState : UnifiedCommandSource::Joydev;
}

DpadSelector::DpadSelector(int debounce_ms) : debounce_ms_(debounce_ms) {
    if (debounce_ms < 0) throw std::invalid_argument("D-pad debounce must be non-negative");
}

int DpadSelector::update(int x, int y, uint64_t monotonic_ms) {
    const int current = direction_index(x, y);
    if (current == previous_) return -1;
    previous_ = current;
    if (current < 0) return -1;
    if (has_change_ && monotonic_ms < last_change_ms_ + static_cast<uint64_t>(debounce_ms_))
        return -1;
    last_change_ms_ = monotonic_ms;
    has_change_ = true;
    return current;
}

RisingEdgeToggle::RisingEdgeToggle(bool initial_state, int debounce_ms)
    : state_(initial_state), debounce_ms_(debounce_ms) {
    if (debounce_ms < 0) throw std::invalid_argument("toggle debounce must be non-negative");
}

bool RisingEdgeToggle::update(bool pressed, uint64_t monotonic_ms) {
    const bool rising = pressed && !previous_pressed_;
    previous_pressed_ = pressed;
    if (!rising) return false;
    if (has_toggled_
        && monotonic_ms < last_toggle_ms_ + static_cast<uint64_t>(debounce_ms_))
        return false;
    state_ = !state_;
    last_toggle_ms_ = monotonic_ms;
    has_toggled_ = true;
    return true;
}

float apply_joystick_deadzone(float value, float deadzone) {
    if (!std::isfinite(value) || !std::isfinite(deadzone) || deadzone < 0.0f || deadzone >= 1.0f)
        throw std::invalid_argument("unified_command: invalid joystick value/deadzone");
    if (std::abs(value) <= deadzone) return 0.0f;
    const float magnitude = (std::abs(value) - deadzone) / (1.0f - deadzone);
    return std::copysign(std::min(magnitude, 1.0f), value);
}

float l2_pressure_to_kp(float pressure, float kp_unpressed, float kp_pressed) {
    if (!std::isfinite(pressure) || !std::isfinite(kp_unpressed)
        || !std::isfinite(kp_pressed) || kp_unpressed < 0.0f
        || kp_pressed < 0.0f || kp_unpressed > 1.0f || kp_pressed > 1.0f
        || kp_pressed > kp_unpressed) {
        throw std::invalid_argument("unified_command: invalid L2 Kp mapping");
    }
    pressure = std::clamp(pressure, 0.0f, 1.0f);
    return kp_unpressed + pressure * (kp_pressed - kp_unpressed);
}

uint64_t fnv1a64(const void* data, std::size_t size) {
    const auto* bytes = static_cast<const uint8_t*>(data);
    uint64_t value = UINT64_C(14695981039346656037);
    for (std::size_t i = 0; i < size; ++i) {
        value ^= bytes[i];
        value *= UINT64_C(1099511628211);
    }
    return value;
}

std::string fnv1a64_string(const void* data, std::size_t size) {
    std::ostringstream out;
    out << "fnv1a64:" << std::hex << std::setfill('0') << std::setw(16)
        << fnv1a64(data, size);
    return out.str();
}

std::array<float, 9> make_legacy_wbg_packet(const UnifiedWbgCommand& command) {
    const float linear_enabled =
        command.enabled && command.linear_enabled ? 1.0f : 0.0f;
    const float yaw_enabled =
        command.enabled && command.yaw_enabled ? 1.0f : 0.0f;
    return {{
        linear_enabled, command.vx, command.kp,
        linear_enabled, command.vy, command.kp,
        yaw_enabled, command.wz, command.kp,
    }};
}

WbgUdpFrame make_live_wbg_frame(const UnifiedWbgCommand& command) {
    const float linear_enabled =
        command.enabled && command.linear_enabled ? 1.0f : 0.0f;
    const float yaw_enabled =
        command.enabled && command.yaw_enabled ? 1.0f : 0.0f;
    return WbgUdpFrame{
        linear_enabled, command.vx, command.kp,
        linear_enabled, command.vy, command.kp,
        yaw_enabled, command.wz, command.kp,
    };
}

UnifiedCommandInterface::UnifiedCommandInterface(
    UnifiedCommandConfig config, safety::JoystickReader* shared_reader)
    : config_(std::move(config)), selector_(config_.dpad_debounce_ms),
      wbg_toggle_(config_.wbg_enabled, config_.wbg_controls.toggle_debounce_ms),
      linear_guidance_toggle_(true, config_.wbg_controls.toggle_debounce_ms),
      yaw_guidance_toggle_(true, config_.wbg_controls.toggle_debounce_ms) {
    if (!config_.enabled) throw std::invalid_argument("unified_command: constructed while disabled");
    if (config_.deadzone < 0.0f || config_.deadzone >= 1.0f)
        throw std::invalid_argument("unified_command: deadzone must be in [0,1)");
    for (float value : {config_.max_vx, config_.max_vy, config_.max_wz, config_.wbg_kp})
        if (!std::isfinite(value) || value < 0.0f)
            throw std::invalid_argument("unified_command: WBG ranges/gain must be finite and non-negative");
    const auto& controls = config_.wbg_controls;
    if (controls.l2_kp_enabled && controls.kp_axis != "l2")
        throw std::invalid_argument("unified_command: WBG kp_axis must be l2");
    if (controls.lb_toggle_enabled && controls.toggle_button != "LB")
        throw std::invalid_argument("unified_command: WBG toggle_button must be LB");
    if (controls.toggle_debounce_ms < 0)
        throw std::invalid_argument("unified_command: WBG toggle_debounce_ms must be non-negative");
    (void)l2_pressure_to_kp(0.0f, controls.kp_unpressed, controls.kp_pressed);

    resolved_source_ = resolve_unified_command_source(config_);
    if (config_.source_timeout_s <= 0.0 || !std::isfinite(config_.source_timeout_s))
        throw std::invalid_argument(
            "unified_command: source_timeout_s must be finite and positive");

    if (shared_reader) {
        reader_ = shared_reader;
        const bool expect_external =
            resolved_source_ == UnifiedCommandSource::UnitreeLowState;
        if (reader_->is_external_mode() != expect_external)
            throw std::invalid_argument(
                "unified_command: configured source conflicts with shared FSM joystick");
    } else {
        if (resolved_source_ == UnifiedCommandSource::UnitreeLowState)
            throw std::invalid_argument(
                "unified_command: unitree_lowstate requires the shared FSM reader");
        if (config_.joystick_device.empty() || config_.joystick_device == "null")
            throw std::invalid_argument(
                "unified_command: local C++ joystick_device is required without a shared FSM reader");
        owned_reader_ = std::make_unique<safety::JoystickReader>(
            config_.joystick_device, config_.joystick_mapping);
        reader_ = owned_reader_.get();
    }
    validate_and_load_motions();
    select_motion(0);  // deterministic startup = stand
    state_.wbg.enabled = config_.wbg_enabled;
    state_.wbg.kp = state_.wbg.enabled
        ? (controls.l2_kp_enabled ? controls.kp_unpressed : config_.wbg_kp)
        : 0.0f;
    std::cout << "[UnifiedCommand] WBG "
              << (state_.wbg.enabled ? "enabled" : "disabled")
              << "; kp=" << (controls.l2_kp_enabled ? "L2 linear" : "fixed")
              << "; LB toggle=" << (controls.lb_toggle_enabled ? "enabled" : "disabled")
              << "; L3=vx/vy toggle; R3=wz toggle"
              << "; max_vx=" << config_.max_vx
              << " max_vy=" << config_.max_vy
              << " max_wz=" << config_.max_wz
              << "; source=" << unified_command_source_name(resolved_source_)
              << "\n";

    if (config_.compatibility_udp.enabled) {
        (void)endpoint(config_.compatibility_udp.host, config_.compatibility_udp.condition_port);
        (void)endpoint(config_.compatibility_udp.host, config_.compatibility_udp.wbg_port);
        compatibility_socket_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (compatibility_socket_ < 0)
            throw std::runtime_error("unified_command: compatibility UDP socket creation failed");
    }
    if (config_.telemetry.enabled) {
        (void)endpoint(config_.telemetry.host, config_.telemetry.port);
        telemetry_socket_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (telemetry_socket_ < 0)
            throw std::runtime_error("unified_command: telemetry UDP socket creation failed");
    }
}

UnifiedCommandInterface::~UnifiedCommandInterface() {
    if (compatibility_socket_ >= 0) close(compatibility_socket_);
    if (telemetry_socket_ >= 0) close(telemetry_socket_);
}

void UnifiedCommandInterface::validate_and_load_motions() {
    if (config_.motions.size() != 4)
        throw std::runtime_error("unified_command: exactly four motion caches are required");
    const std::array<std::string, 4> names{{"stand", "walk", "jog", "squat down"}};
    std::array<bool, 4> seen{{false, false, false, false}};
    for (const auto& entry : config_.motions) {
        const int direction = configured_direction(entry.dpad);
        if (seen[direction]) throw std::runtime_error("unified_command: duplicate D-pad direction");
        if (entry.name != names[direction])
            throw std::runtime_error(
                "unified_command: fixed mapping is up=stand,right=walk,down=jog,left=squat down");
        if (entry.dim <= 0) throw std::runtime_error("unified_command: latent dim must be positive");
        if (entry.hash.rfind("fnv1a64:", 0) != 0 || entry.hash.size() != 24)
            throw std::runtime_error("unified_command: required hash format is fnv1a64:<16 hex>");
        std::ifstream input(entry.path, std::ios::binary | std::ios::ate);
        if (!input) throw std::runtime_error("unified_command: missing latent cache: " + entry.path);
        const auto size = input.tellg();
        const auto expected = static_cast<std::streamoff>(entry.dim * sizeof(float));
        if (size != expected)
            throw std::runtime_error("unified_command: latent byte count mismatch: " + entry.path);
        input.seekg(0);
        LoadedMotion loaded;
        loaded.config = entry;
        loaded.values.resize(static_cast<std::size_t>(entry.dim));
        input.read(reinterpret_cast<char*>(loaded.values.data()), expected);
        if (!input) throw std::runtime_error("unified_command: latent read failed: " + entry.path);
        for (float value : loaded.values)
            if (!std::isfinite(value))
                throw std::runtime_error("unified_command: latent contains non-finite value: " + entry.path);
        const auto actual = fnv1a64_string(loaded.values.data(), loaded.values.size() * sizeof(float));
        if (actual != entry.hash)
            throw std::runtime_error("unified_command: latent hash mismatch: " + entry.path);
        motions_[direction] = std::move(loaded);
        seen[direction] = true;
    }
}

void UnifiedCommandInterface::select_motion(int index) {
    if (index < 0 || index >= static_cast<int>(motions_.size()))
        throw std::out_of_range("unified_command: invalid motion selection");
    state_.motion_name = motions_[index].config.name;
    state_.motion_hash = motions_[index].config.hash;
    state_.latent = motions_[index].values;
}

const UnifiedCommandState& UnifiedCommandInterface::poll(
    bool shared_reader_already_polled, uint64_t monotonic_ms,
    bool source_fresh) {
    if (!shared_reader_already_polled) reader_->poll();
    if (monotonic_ms == 0) monotonic_ms = now_ms();
    state_.monotonic_ms = monotonic_ms;
    state_.joystick_connected = source_fresh && reader_->is_connected();
    if (!state_.joystick_connected) {
        select_motion(0);
        state_.wbg = UnifiedWbgCommand{};
        state_.wbg.kp = 0.0f;
        state_.wbg.enabled = false;
        ++state_.sequence;
        send_optional_udp();
        return state_;
    }
    const float forward_axis = resolved_source_ == UnifiedCommandSource::UnitreeLowState
        ? reader_->axis_ly() : -reader_->axis_ly();
    state_.wbg.vx = apply_joystick_deadzone(forward_axis, config_.deadzone) * config_.max_vx;
    state_.wbg.vy = apply_joystick_deadzone(-reader_->axis_lx(), config_.deadzone) * config_.max_vy;
    state_.wbg.wz = apply_joystick_deadzone(-reader_->axis_rx(), config_.deadzone) * config_.max_wz;
    if (config_.wbg_controls.lb_toggle_enabled
        && wbg_toggle_.update(
            reader_->is_pressed(safety::JoystickButton::LB), monotonic_ms)) {
        std::cout << "[UnifiedCommand] LB: WBG "
                  << (wbg_toggle_.state() ? "enabled" : "disabled") << "\n";
    }
    if (linear_guidance_toggle_.update(
            reader_->is_pressed(safety::JoystickButton::LS), monotonic_ms)) {
        std::cout << "[UnifiedCommand] L3: vx/vy guidance "
                  << (linear_guidance_toggle_.state() ? "enabled" : "disabled")
                  << "\n";
    }
    if (yaw_guidance_toggle_.update(
            reader_->is_pressed(safety::JoystickButton::RS), monotonic_ms)) {
        std::cout << "[UnifiedCommand] R3: wz guidance "
                  << (yaw_guidance_toggle_.state() ? "enabled" : "disabled")
                  << "\n";
    }
    state_.wbg.enabled = config_.wbg_controls.lb_toggle_enabled
        ? wbg_toggle_.state() : config_.wbg_enabled;
    state_.wbg.linear_enabled = linear_guidance_toggle_.state();
    state_.wbg.yaw_enabled = yaw_guidance_toggle_.state();
    const float requested_kp = config_.wbg_controls.l2_kp_enabled
        ? l2_pressure_to_kp(reader_->axis_lt(),
                            config_.wbg_controls.kp_unpressed,
                            config_.wbg_controls.kp_pressed)
        : config_.wbg_kp;
    // This is the effective gain exposed in telemetry and sent to the actor.
    // Disabled guidance still tracks all live inputs, but contributes exactly zero.
    state_.wbg.kp = state_.wbg.enabled ? requested_kp : 0.0f;
    const int selected = selector_.update(
        reader_->dpad_left() ? -1 : (reader_->dpad_right() ? 1 : 0),
        reader_->dpad_up() ? -1 : (reader_->dpad_down() ? 1 : 0), monotonic_ms);
    if (selected >= 0) select_motion(selected);
    ++state_.sequence;
    send_optional_udp();
    return state_;
}

void UnifiedCommandInterface::send_optional_udp() {
    if (compatibility_socket_ >= 0) {
        const auto cond_target = endpoint(config_.compatibility_udp.host,
                                          config_.compatibility_udp.condition_port);
        send_bytes(compatibility_socket_, cond_target, state_.latent.data(),
                   state_.latent.size() * sizeof(float));
        const auto wbg = make_legacy_wbg_packet(state_.wbg);
        const auto wbg_target = endpoint(config_.compatibility_udp.host,
                                         config_.compatibility_udp.wbg_port);
        send_bytes(compatibility_socket_, wbg_target, wbg.data(),
                   wbg.size() * sizeof(float));
    }
    if (telemetry_socket_ >= 0) {
        std::ostringstream json;
        json << "{\"schema\":1,\"sequence\":" << state_.sequence
             << ",\"monotonic_ms\":" << state_.monotonic_ms
             << ",\"joystick_connected\":" << (state_.joystick_connected ? "true" : "false")
             << ",\"motion\":\"" << state_.motion_name
             << "\",\"motion_hash\":\"" << state_.motion_hash
             << "\",\"wbg\":{\"vx\":" << state_.wbg.vx
             << ",\"vy\":" << state_.wbg.vy << ",\"wz\":" << state_.wbg.wz
             << ",\"kp\":" << state_.wbg.kp
             << ",\"vx_enabled\":"
             << (state_.wbg.enabled && state_.wbg.linear_enabled ? "true" : "false")
             << ",\"vy_enabled\":"
             << (state_.wbg.enabled && state_.wbg.linear_enabled ? "true" : "false")
             << ",\"wz_enabled\":"
             << (state_.wbg.enabled && state_.wbg.yaw_enabled ? "true" : "false")
             << ",\"enabled\":" << (state_.wbg.enabled ? "true" : "false") << "}}";
        const auto payload = json.str();
        const auto target = endpoint(config_.telemetry.host, config_.telemetry.port);
        send_bytes(telemetry_socket_, target, payload.data(), payload.size());
    }
}

}  // namespace diffusion_deploy
