#include "diffusion_deploy/utils/config_parser.hpp"
#include "diffusion_deploy/safety/deploy_fsm.hpp"

#include <yaml-cpp/yaml.h>

#include <torch/torch.h>
#include <torch/version.h>

#include <filesystem>
#include <iostream>
#include <net/if.h>
#include <utility>
#include <vector>
#include <string>
#include <sys/utsname.h>

namespace fs = std::filesystem;

namespace {

std::string arg_value(int argc, char** argv, const std::string& flag) {
    for (int i = 1; i + 1 < argc; ++i) {
        if (argv[i] == flag) return argv[i + 1];
    }
    return {};
}

bool has_flag(int argc, char** argv, const std::string& flag) {
    for (int i = 1; i < argc; ++i) {
        if (argv[i] == flag) return true;
    }
    return false;
}

bool check_file(const std::string& label, const std::string& path, bool required) {
    if (path.empty()) {
        std::cerr << (required ? "[FAIL] " : "[WARN] ")
                  << label << " path is empty\n";
        return false;
    }
    const bool ok = fs::is_regular_file(path);
    std::cout << (ok ? "[PASS] " : (required ? "[FAIL] " : "[WARN] "))
              << label << ": " << path << "\n";
    return ok;
}

}  // namespace

int main(int argc, char** argv) {
    if (has_flag(argc, argv, "--help") || has_flag(argc, argv, "-h")) {
        std::cout
            << "Read-only deployment preflight. It never initializes DDS or publishes LowCmd.\n"
            << "Usage: inspect_edge_deploy --config PATH [--fsm-config PATH] [--target host|jetson] "
               "[--network-interface NAME] [--allow-missing-assets] [--offline]\n";
        return 0;
    }

    const std::string config_path = arg_value(argc, argv, "--config");
    const std::string fsm_config_path = arg_value(argc, argv, "--fsm-config");
    const std::string target = arg_value(argc, argv, "--target").empty()
        ? "host" : arg_value(argc, argv, "--target");
    const std::string interface_override = arg_value(argc, argv, "--network-interface");
    const bool allow_missing_assets = has_flag(argc, argv, "--allow-missing-assets");
    const bool offline = has_flag(argc, argv, "--offline");

    if (config_path.empty() || (target != "host" && target != "jetson")) {
        std::cerr << "[FAIL] --config is required and --target must be host or jetson\n";
        return 2;
    }

    int failures = 0;
    struct utsname sys_info {};
    if (uname(&sys_info) != 0) {
        std::cerr << "[FAIL] uname failed\n";
        ++failures;
    } else {
        std::cout << "[INFO] host=" << sys_info.sysname << " " << sys_info.machine << "\n";
        if (target == "jetson" && std::string(sys_info.machine) != "aarch64") {
            std::cerr << "[FAIL] Jetson target requires an aarch64 runtime host; this host is "
                      << sys_info.machine << "\n";
            ++failures;
        }
    }

    diffusion_deploy::DeployConfig cfg;
    try {
        cfg = diffusion_deploy::load_config(config_path);
        std::cout << "[PASS] config parsed: " << fs::absolute(config_path).lexically_normal() << "\n";
    } catch (const std::exception& e) {
        std::cerr << "[FAIL] config parse: " << e.what() << "\n";
        return 1;
    }

    std::string fsm_network_interface;
    if (fsm_config_path.empty()) {
        std::cout << "[WARN] no FSM config supplied; external Unitree remote path was not checked\n";
        if (target == "jetson") ++failures;
    } else {
        try {
            const YAML::Node fsm_root = YAML::LoadFile(fsm_config_path)["FSM"];
            if (!fsm_root) throw std::runtime_error("missing FSM root");
            const auto definition = diffusion_deploy::safety::load_fsm_definition(fsm_root);
            if (fsm_root["env"] && fsm_root["env"]["network_interface"]) {
                fsm_network_interface =
                    fsm_root["env"]["network_interface"].as<std::string>();
            }
            const auto joystick = fsm_root["joystick_device"];
            if (joystick && !joystick.IsNull() && !joystick.as<std::string>().empty()) {
                std::cerr << "[FAIL] FSM joystick_device must be null/empty for Unitree DDS remote\n";
                ++failures;
            } else if (!definition.state_index.count("Passive")
                       || !definition.state_index.count("Ready")
                       || !definition.state_index.count("Running")
                       || !definition.has_fallback
                       || definition.fallback_state != "Passive") {
                std::cerr << "[FAIL] FSM must include Passive/Ready/Running and a passive fallback\n";
                ++failures;
            } else {
                std::cout << "[PASS] external Unitree remote FSM parsed with passive fallback\n";
            }
        } catch (const std::exception& e) {
            std::cerr << "[FAIL] FSM config parse: " << e.what() << "\n";
            ++failures;
        }
    }

    if (target == "jetson" && offline) {
        std::cerr << "[FAIL] --offline is for host fixtures only, not Jetson readiness\n";
        ++failures;
    }

    const std::string network_interface = interface_override.empty()
        ? cfg.env.network_interface : interface_override;
    if (network_interface.empty() || network_interface == "lo"
        || network_interface.find("REQUIRED_") == 0) {
        std::cerr << "[FAIL] explicit non-loopback G1 network interface is required; got '"
                  << network_interface << "'\n";
        ++failures;
    } else if (!offline && if_nametoindex(network_interface.c_str()) == 0) {
        std::cerr << "[FAIL] network interface does not exist on this host: "
                  << network_interface << "\n";
        ++failures;
    } else {
        std::cout << "[PASS] explicit network interface: " << network_interface
                  << (offline ? " (offline name check)" : "") << "\n";
    }

    if (!fsm_network_interface.empty()
        && fsm_network_interface != network_interface) {
        std::cerr << "[FAIL] deploy and FSM network interfaces differ: "
                  << network_interface << " vs " << fsm_network_interface << "\n";
        ++failures;
    }

    try {
        const YAML::Node raw = YAML::LoadFile(config_path);
        for (const auto& item : std::vector<std::pair<std::string, int>>{
                 {"obs", cfg.actor.obs_dim}, {"action", cfg.actor.action_dim}}) {
            const auto n = raw["normalization"][item.first];
            const std::string mode = n && n["mode"]
                ? n["mode"].as<std::string>() : "linear";
            std::string first = "min";
            std::string second = "max";
            if (mode == "scale_offset") {
                first = "scale";
                second = "offset";
            } else if (mode == "standard" || mode == "gaussian") {
                first = "mean";
                second = "std";
            }
            const bool populated = n && n[first] && n[second]
                && n[first].IsSequence() && n[second].IsSequence()
                && static_cast<int>(n[first].size()) == item.second
                && n[first].size() == n[second].size();
            if (!populated) {
                std::cerr << "[FAIL] normalization." << item.first << " mode="
                          << mode << " must contain exported " << item.second
                          << "-element " << first << "/" << second << " vectors\n";
                ++failures;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[FAIL] normalization inspection: " << e.what() << "\n";
        ++failures;
    }

    if (cfg.env.use_fk) {
        std::cerr << "[FAIL] edge-minimal config must set env.use_fk=false\n";
        ++failures;
    } else {
        std::cout << "[PASS] FK disabled\n";
    }
    if (cfg.runner.enable_cond_udp || cfg.runner.enable_wbg_udp) {
        std::cerr << "[FAIL] edge-minimal config must disable condition and WBG UDP\n";
        ++failures;
    } else {
        std::cout << "[PASS] external condition/WBG UDP disabled\n";
    }

    bool assets_ok = true;
    assets_ok &= check_file("model", cfg.model_path, !allow_missing_assets);
    const bool diffusion_actor = cfg.actor_type == "diffusion"
        || cfg.actor_type == "joint_diffusion" || cfg.actor_type == "diffuse_cloc"
        || cfg.actor_type == "prdp";
    if (diffusion_actor) assets_ok &= check_file("schedule", cfg.schedule_path, !allow_missing_assets);
    if (cfg.actor_type == "diffuse_cloc" || cfg.actor_type == "prdp") {
        assets_ok &= check_file("emphasis", cfg.cloc_actor.emphasis_path, !allow_missing_assets);
    }
    if (!assets_ok && !allow_missing_assets) ++failures;
    if (!assets_ok && allow_missing_assets) {
        std::cout << "[WARN] missing assets allowed for template-only inspection\n";
    }

    std::cout << "[INFO] torch=" << TORCH_VERSION
              << " cuda_available=" << (torch::cuda::is_available() ? "true" : "false")
#ifdef _GLIBCXX_USE_CXX11_ABI
              << " cxx11_abi=" << _GLIBCXX_USE_CXX11_ABI
#endif
              << "\n";
#ifdef HAVE_UNITREE_SDK2
    std::cout << "[PASS] built with Unitree SDK2\n";
#else
    std::cout << "[WARN] built without Unitree SDK2; robot executable is not hardware-ready\n";
    if (target == "jetson") ++failures;
#endif
#ifdef USE_FK
    std::cout << "[INFO] binary includes optional FK support (config keeps it disabled)\n";
#endif

    if (target == "jetson" && !torch::cuda::is_available()) {
        std::cerr << "[FAIL] Jetson target requires a working CUDA Torch runtime\n";
        ++failures;
    }

    std::cout << "[INFO] no DDS channel was initialized; no command was published\n";
    if (failures != 0) {
        std::cerr << "[RESULT] BLOCKED: " << failures << " preflight gate(s) failed\n";
        return 1;
    }
    std::cout << "[RESULT] PASS: static/read-only preflight gates passed\n";
    return 0;
}
