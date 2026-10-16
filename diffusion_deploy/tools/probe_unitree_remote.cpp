/** Receive-only probe for the G1 wireless controller carried in LowState. */
#include "diffusion_deploy/env/unitree_env.hpp"
#include "diffusion_deploy/safety/joystick_reader.hpp"

#include <chrono>
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

namespace {

std::string arg(int argc, char** argv, const std::string& name,
                const std::string& fallback = "") {
    for (int i = 1; i + 1 < argc; ++i)
        if (argv[i] == name) return argv[i + 1];
    return fallback;
}

void require_no_publish() {
    const auto counters = diffusion_deploy::UnitreeEnv::safety_counters();
    if (counters.publisher_constructions != 0 || counters.shutdown_calls != 0
        || counters.publish_calls != 0) {
        throw std::runtime_error("receive-only probe observed a publish surface");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto interface = arg(argc, argv, "--network-interface");
        if (interface.empty() || interface == "lo")
            throw std::invalid_argument(
                "--network-interface must name the G1 non-loopback interface");
        const int samples = std::stoi(arg(argc, argv, "--samples", "100"));
        const int interval_ms = std::stoi(arg(argc, argv, "--interval-ms", "20"));
        const double timeout_s = std::stod(arg(argc, argv, "--timeout-s", "0.10"));
        if (samples <= 0 || interval_ms <= 0 || timeout_s <= 0.0)
            throw std::invalid_argument("sample/interval/timeout values must be positive");

        diffusion_deploy::UnitreeEnvConfig config;
        config.execution_mode = diffusion_deploy::ExecutionMode::ReceiveOnly;
        config.network_interface = interface;
        diffusion_deploy::UnitreeEnv::reset_safety_counters_for_test();
        diffusion_deploy::UnitreeEnv env(config);
        env.initialize();
        require_no_publish();

        int fresh_count = 0;
        int valid_remote_count = 0;
        int active_packet_count = 0;
        diffusion_deploy::safety::RawJoystickState latest;
        for (int i = 0; i < samples; ++i) {
            const auto snapshot = env.get_wireless_remote_snapshot();
            if (snapshot.lowstate_received && snapshot.lowstate_age_s <= timeout_s) {
                ++fresh_count;
                const auto decoded =
                    diffusion_deploy::safety::decode_unitree_wireless_remote(
                        snapshot.data);
                if (decoded.valid) {
                    ++valid_remote_count;
                    latest = decoded;
                }
                if (std::any_of(snapshot.data.begin(), snapshot.data.end(),
                                [](uint8_t value) { return value != 0; })) {
                    ++active_packet_count;
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
        }
        env.close();
        require_no_publish();
        std::cout << "[probe_unitree_remote] fresh_lowstate=" << fresh_count
                  << "/" << samples
                  << " valid_wireless=" << valid_remote_count
                  << " active_packets=" << active_packet_count
                  << " lx=" << latest.lx << " ly=" << latest.ly
                  << " rx=" << latest.rx << " l2=" << latest.lt
                  << " dpad_x=" << latest.dpad_x
                  << " dpad_y=" << latest.dpad_y
                  << " publisher_constructions=0 shutdown_calls=0 publish_calls=0\n";
        if (fresh_count != samples || valid_remote_count == 0) {
            std::cerr << "[probe_unitree_remote] FAIL: LowState/wireless source is missing or stale\n";
            return 2;
        }
        std::cout << "[probe_unitree_remote] PASS: receive-only Unitree source ready\n";
        if (active_packet_count == 0)
            std::cout << "[probe_unitree_remote] NOTE: controller stayed centered; "
                         "presence requires an operator input check\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "[probe_unitree_remote] ERROR: " << error.what() << "\n";
        return 1;
    }
}
