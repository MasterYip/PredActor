#include "diffusion_deploy/safety/joystick_reader.hpp"
#include "diffusion_deploy/vendor/unitree_joystick.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace diffusion_deploy::safety {

RawJoystickState decode_unitree_wireless_remote(
    const std::array<uint8_t, 40>& packet) {
    RawJoystickState out;
    unitree::common::REMOTE_DATA_RX remote{};
    static_assert(sizeof(remote.buff) == 40, "Unitree remote packet size drift");
    std::memcpy(remote.buff, packet.data(), packet.size());
    const auto& button = remote.RF_RX.btn.components;
    out.buttons[static_cast<int>(JoystickButton::A)] = button.A;
    out.buttons[static_cast<int>(JoystickButton::B)] = button.B;
    out.buttons[static_cast<int>(JoystickButton::X)] = button.X;
    out.buttons[static_cast<int>(JoystickButton::Y)] = button.Y;
    out.buttons[static_cast<int>(JoystickButton::LB)] = button.L1;
    out.buttons[static_cast<int>(JoystickButton::RB)] = button.R1;
    out.buttons[static_cast<int>(JoystickButton::BACK)] = button.Select;
    out.buttons[static_cast<int>(JoystickButton::START)] = button.Start;
    // The Unitree 16-bit wireless ABI exposes its two extra buttons as f1/f2.
    // Use them as the LowState aliases for the L3/R3 semantic slots that Linux
    // joydev supplies directly.
    out.buttons[static_cast<int>(JoystickButton::LS)] = button.f1;
    out.buttons[static_cast<int>(JoystickButton::RS)] = button.f2;

    const auto finite_axis = [](float value) {
        return std::isfinite(value) && value >= -1.25f && value <= 1.25f;
    };
    if (!finite_axis(remote.RF_RX.lx) || !finite_axis(remote.RF_RX.ly)
        || !finite_axis(remote.RF_RX.rx) || !finite_axis(remote.RF_RX.ry)) {
        return RawJoystickState{};
    }
    out.lx = std::clamp(remote.RF_RX.lx, -1.0f, 1.0f);
    out.ly = std::clamp(remote.RF_RX.ly, -1.0f, 1.0f);
    out.rx = std::clamp(remote.RF_RX.rx, -1.0f, 1.0f);
    out.ry = std::clamp(remote.RF_RX.ry, -1.0f, 1.0f);
    // The stock G1 remote exposes triggers as digital button bits.
    out.lt = button.L2 ? 1.0f : 0.0f;
    out.rt = button.R2 ? 1.0f : 0.0f;
    out.dpad_x = (button.right ? 1 : 0) - (button.left ? 1 : 0);
    // Match Linux joydev semantics consumed by JoystickReader: up is negative.
    out.dpad_y = (button.down ? 1 : 0) - (button.up ? 1 : 0);
    out.valid = true;
    return out;
}

}  // namespace diffusion_deploy::safety
