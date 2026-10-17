/**
 * run_g1_robot.cpp
 *
 * Main executable for deploying a trained diffusion policy on the Unitree G1.
 *
 * Usage:
 *   ./run_g1_robot --config /path/to/g1_deploy_config.yaml \
 *                  --model  /path/to/policy.pt \
 *                  --device cuda:0
 *
 * The executable:
 *   1. Loads YAML configuration.
 *   2. Dispatches actor_type → DiffusionActor / JointDiffusionActor /
 *      DiffuseCLoCActor / TorchActor (legacy full-loop fallback).
 *   3. Instantiates UnitreeEnv and ObsComposer.
 *   4. Runs EnvRunner control loop.
 */
#include "diffusion_deploy/utils/config_parser.hpp"
#include "diffusion_deploy/actor/torch_actor.hpp"
#include "diffusion_deploy/actor/diffusion_actor.hpp"
#include "diffusion_deploy/actor/joint_diffusion_actor.hpp"
#include "diffusion_deploy/actor/diffuse_cloc_actor.hpp"
#include "diffusion_deploy/agent/diffusion_agent.hpp"
#include "diffusion_deploy/env/unitree_env.hpp"
#include "diffusion_deploy/obs/obs_composer.hpp"
#include "diffusion_deploy/runner/env_runner.hpp"
#include "diffusion_deploy/safety/deploy_fsm.hpp"

#include <yaml-cpp/yaml.h>

#include <iostream>
#include <string>
#include <csignal>
#include <ctime>
#include <filesystem>
#include <memory>

// ---- Global runner pointer for signal handler ----
static diffusion_deploy::EnvRunner* g_runner = nullptr;

static void signal_handler(int /*sig*/) {
    // Track first interrupt time; force-quit on repeated interrupts within 5 seconds.
    static std::atomic<time_t> s_first_interrupt{0};
    time_t now = std::time(nullptr);
    time_t first = s_first_interrupt.load();

    if (first == 0 || (now - first) > 5) {
        // First interrupt (or previous was >5s ago) — request graceful stop.
        s_first_interrupt.store(now);
        std::cout << "\n[run_g1_robot] Interrupt received, stopping gracefully...\n"
                  << "[run_g1_robot] Press Ctrl+C again within 5s to force quit.\n";
        if (g_runner) g_runner->request_stop();
    } else {
        // Repeated interrupt within the 5-second window — force quit.
        std::cout << "\n[run_g1_robot] Second interrupt within 5s, forcing quit.\n";
        std::_Exit(1);
    }
}

// ---- Simple argument parser ----
static std::string get_arg(int argc, char* argv[],
                            const std::string& flag,
                            const std::string& default_val = "") {
    for (int i = 1; i < argc - 1; ++i) {
        if (std::string(argv[i]) == flag) return argv[i + 1];
    }
    return default_val;
}

static bool has_flag(int argc, char* argv[], const std::string& flag) {
    for (int i = 1; i < argc; ++i)
        if (std::string(argv[i]) == flag) return true;
    return false;
}

// ---- main() ----

int main(int argc, char* argv[]) {
    if (has_flag(argc, argv, "--help") || has_flag(argc, argv, "-h")) {
        std::cout
            << "Usage: run_g1_robot [OPTIONS]\n"
            << "  --config PATH     Path to deploy config YAML  (required)\n"
            << "  --model  PATH     Override model path from config (optional)\n"
            << "  --device DEV      Torch device: cpu | cuda:0   (default: cpu)\n"
            << "  --mode MODE       offline | receive-only | no-publish | control\n"
            << "  --max-steps N     Override bounded runner steps (positive integer)\n"
            << "  --record-csv PATH Write per-step obs/action/command CSV (opt-in)\n"
            << "  --fsm-config PATH Optional FSM configuration YAML\n"
            << "  --fsm-device PATH Joystick device; omit for Unitree DDS remote\n"
            << "  --fsm-joy-mapping NAME  Controller mapping: xbox | ps5 (default: xbox)\n"
            << "  --no-fsm          Disable safety FSM entirely\n"
            << "  --wbg-udp         Enable interactive WBG commands over UDP\n"
            << "  --wbg-host IP     UDP host for WBG receiver (default: 127.0.0.1)\n"
            << "  --wbg-port PORT   UDP port for WBG receiver (default: 9879)\n";
    std::cout << "  --unified-command Enable configured in-process C++ joystick commands\n"
              << "  --command-source NAME auto | unitree_lowstate | joydev\n"
              << "  --command-device PATH  Override unified joystick device\n"
              << "  --command-mapping NAME Override unified mapping (xbox/xbox_new/...)\n"
              << "  --validate-config Parse config/CLI contract and exit before env/DDS startup\n";
        return 0;
    }

    const std::string config_path = get_arg(argc, argv, "--config");
    if (config_path.empty()) {
        std::cerr << "[run_g1_robot] Error: --config is required.\n";
        return 1;
    }

    const std::string model_override = get_arg(argc, argv, "--model");
    const std::string device_str     = get_arg(argc, argv, "--device", "cpu");

    // ---- 1. Load config ----
    std::cout << "[run_g1_robot] Loading config: " << config_path << "\n";
    diffusion_deploy::DeployConfig cfg;
    try {
        diffusion_deploy::DeployConfigOverrides config_overrides;
        config_overrides.enable_unified_command =
            has_flag(argc, argv, "--unified-command");
        config_overrides.unified_command_source =
            get_arg(argc, argv, "--command-source", "");
        config_overrides.unified_command_device =
            get_arg(argc, argv, "--command-device", "");
        config_overrides.unified_command_mapping =
            get_arg(argc, argv, "--command-mapping", "");
        cfg = diffusion_deploy::load_config(config_path, config_overrides);
    } catch (const std::exception& e) {
        std::cerr << "[run_g1_robot] Config error: " << e.what() << "\n";
        return 1;
    }

    try {
        cfg.env.execution_mode = diffusion_deploy::parse_execution_mode(
            get_arg(argc, argv, "--mode",
                    diffusion_deploy::execution_mode_name(cfg.env.execution_mode)));
    } catch (const std::exception& e) {
        std::cerr << "[run_g1_robot] Mode error: " << e.what() << "\n";
        return 1;
    }
    std::cout << "[run_g1_robot] Execution mode: "
              << diffusion_deploy::execution_mode_name(cfg.env.execution_mode)
#ifdef ENABLE_UNITREE_COMMAND_PUBLISH
              << "; command publishing compiled in\n";
#else
              << "; command publishing unavailable\n";
#endif

    const std::string fsm_yaml = get_arg(argc, argv, "--fsm-config");
    if (cfg.env.execution_mode == diffusion_deploy::ExecutionMode::Control) {
        if (has_flag(argc, argv, "--no-fsm")) {
            std::cerr << "[run_g1_robot] Error: control mode cannot be combined with --no-fsm.\n";
            return 1;
        }
        if (fsm_yaml.empty()) {
            std::cerr << "[run_g1_robot] Error: control mode requires --fsm-config PATH.\n";
            return 1;
        }
    }

    // Load the FSM document once. record_csv is a top-level sibling of FSM so
    // recording and safety settings travel together in each deployment bundle.
    YAML::Node fsm_root;
    if (!fsm_yaml.empty()) {
        try {
            fsm_root = YAML::LoadFile(fsm_yaml);
            if (fsm_root["record_csv"]) {
                const auto record_node = fsm_root["record_csv"];
                cfg.runner.csv_record =
                    diffusion_deploy::parse_csv_record_config(
                        record_node, cfg.runner.csv_record);
                if (record_node["path"] && !cfg.runner.csv_record.path.empty()) {
                    std::filesystem::path output_path(cfg.runner.csv_record.path);
                    if (output_path.is_relative()) {
                        const auto fsm_dir =
                            std::filesystem::absolute(fsm_yaml).parent_path();
                        cfg.runner.csv_record.path =
                            (fsm_dir / output_path).lexically_normal().string();
                    }
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "[run_g1_robot] FSM config error: " << e.what() << "\n";
            return 1;
        }
    }

    const std::string max_steps_override = get_arg(argc, argv, "--max-steps");
    if (!max_steps_override.empty()) {
        try {
            std::size_t parsed = 0;
            const long value = std::stol(max_steps_override, &parsed);
            if (parsed != max_steps_override.size() || value <= 0) {
                throw std::invalid_argument("not a positive integer");
            }
            cfg.runner.max_steps = static_cast<int>(value);
        } catch (const std::exception&) {
            std::cerr << "[run_g1_robot] Error: --max-steps must be a positive integer.\n";
            return 1;
        }
    }

    const std::string record_csv = get_arg(argc, argv, "--record-csv");
    if (!record_csv.empty()) {
        cfg.runner.csv_record.enabled = true;
        cfg.runner.csv_record.path = record_csv;
    }
    try {
        diffusion_deploy::validate_csv_record_config(cfg.runner.csv_record);
    } catch (const std::exception& e) {
        std::cerr << "[run_g1_robot] CSV record config error: " << e.what() << "\n";
        return 1;
    }

    if (has_flag(argc, argv, "--validate-config")) {
        std::cout
            << "[run_g1_robot] Config validation PASS: conditioning_mode="
            << cfg.conditioning_mode
            << " condition_profile=" << cfg.runner.condition_profile
            << " text_cond_dim=" << cfg.runner.text_cond_dim
            << " backbone_cond_dim=" << cfg.joint_actor.backbone_cond_dim
            << " unified_command="
            << (cfg.runner.unified_command.enabled ? "enabled" : "disabled")
            << " command_source="
            << diffusion_deploy::unified_command_source_name(
                   diffusion_deploy::resolve_unified_command_source(
                       cfg.runner.unified_command))
            << " motions=" << cfg.runner.unified_command.motions.size()
            << " max_vx=" << cfg.runner.unified_command.max_vx
            << " max_vy=" << cfg.runner.unified_command.max_vy
            << " max_wz=" << cfg.runner.unified_command.max_wz
            << " classifier_guidance_impl="
            << cfg.cloc_actor.classifier_guidance_impl
            << " record_csv="
            << (cfg.runner.csv_record.enabled ? "enabled" : "disabled");
        if (cfg.runner.csv_record.enabled) {
            std::cout << " record_csv_path=" << cfg.runner.csv_record.path
                      << " record_csv_fields="
                      << diffusion_deploy::csv_record_fields_summary(
                             cfg.runner.csv_record.fields);
        }
        std::cout
            << "\n[run_g1_robot] Validation only; environment and DDS were not initialized.\n";
        return 0;
    }

    if (cfg.env.execution_mode == diffusion_deploy::ExecutionMode::ReceiveOnly) {
        try {
            diffusion_deploy::UnitreeEnv env(cfg.env);
            env.initialize();
            const auto obs = env.get_obs_terms();
            const auto counters = diffusion_deploy::UnitreeEnv::safety_counters();
            if (!obs.joint_pos.defined() || counters.publisher_constructions != 0 ||
                counters.shutdown_calls != 0 || counters.publish_calls != 0) {
                throw std::runtime_error("receive-only safety invariant failed");
            }
            std::cout << "[run_g1_robot] Receive-only snapshot valid; "
                      << "publisher_constructions=0 shutdown_calls=0 publish_calls=0\n";
            env.close();
            return 0;
        } catch (const std::exception& e) {
            std::cerr << "[run_g1_robot] Receive-only diagnostic failed: "
                      << e.what() << "\n";
            return 1;
        }
    }

    if (!model_override.empty()) cfg.model_path = model_override;
    if (cfg.model_path.empty()) {
        std::cerr << "[run_g1_robot] Error: model path not specified in config or --model.\n";
        return 1;
    }

    // ---- 2. Torch device ----
    torch::Device device(device_str);
    std::cout << "[run_g1_robot] Using device: " << device << "\n";

    // ---- 3. Build actor (dispatch on actor_type) ----
    std::shared_ptr<diffusion_deploy::BaseActor> actor;
    const std::string& atype = cfg.actor_type;

    try {
        if (atype == "diffusion") {
            std::cout << "[run_g1_robot] actor_type=diffusion → DiffusionActor\n";
            if (cfg.schedule_path.empty())
                throw std::runtime_error("actor_type=diffusion requires schedule_path in config");
            actor = std::make_shared<diffusion_deploy::DiffusionActor>(
                cfg.model_path, cfg.schedule_path, cfg.diffusion_actor, device);

        } else if (atype == "joint_diffusion") {
            std::cout << "[run_g1_robot] actor_type=joint_diffusion → JointDiffusionActor\n";
            if (cfg.schedule_path.empty())
                throw std::runtime_error("actor_type=joint_diffusion requires schedule_path in config");
            actor = std::make_shared<diffusion_deploy::JointDiffusionActor>(
                cfg.model_path, cfg.schedule_path, cfg.joint_actor, device);

        } else if (atype == "diffuse_cloc" || atype == "prdp") {
            std::cout << "[run_g1_robot] actor_type=" << atype
                      << " → DiffuseCLoCActor\n";
            if (cfg.schedule_path.empty())
                throw std::runtime_error("actor_type=" + atype + " requires schedule_path in config");
            if (cfg.cloc_actor.emphasis_path.empty())
                throw std::runtime_error("actor_type=" + atype + " requires emphasis_path in config");
            actor = std::make_shared<diffusion_deploy::DiffuseCLoCActor>(
                cfg.model_path, cfg.schedule_path, cfg.cloc_actor.emphasis_path,
                cfg.cloc_actor, device);

        } else {
            // Legacy: full-loop TorchScript (actor_type="torch" or unrecognised)
            std::cout << "[run_g1_robot] actor_type=" << atype
                      << " → TorchActor (full-loop)\n";
            actor = std::make_shared<diffusion_deploy::TorchActor>(
                cfg.model_path, cfg.actor, diffusion_deploy::TorchExportMode::FULL_LOOP, device);
        }
    } catch (const std::exception& e) {
        std::cerr << "[run_g1_robot] Failed to load model: " << e.what() << "\n";
        return 1;
    }

    // ---- 4. Build agent ----
    auto& norm = *cfg.normalizer;

    auto obs_norm    = norm.has("obs")    ? norm.get("obs")    : diffusion_deploy::Normalizer::create_identity(cfg.actor.obs_dim);
    auto action_norm = norm.has("action") ? norm.get("action") : diffusion_deploy::Normalizer::create_identity(cfg.actor.action_dim);
    std::shared_ptr<diffusion_deploy::Normalizer> cond_norm = nullptr;
    if (norm.has("cond")) cond_norm = norm.get("cond");

    obs_norm->to(device);
    action_norm->to(device);
    if (cond_norm) cond_norm->to(device);

    auto agent = std::make_unique<diffusion_deploy::DiffusionAgent>(
        actor, obs_norm, action_norm, cond_norm);

    std::cout << "[run_g1_robot] Agent ready. obs_dim=" << cfg.actor.obs_dim
              << " action_dim=" << cfg.actor.action_dim
              << " n_obs_steps=" << cfg.actor.n_obs_steps
              << " horizon=" << cfg.actor.horizon() << "\n";

    // ---- 4b. WBG UDP overrides (CLI takes priority over config) ----
    if (has_flag(argc, argv, "--wbg-udp")) cfg.runner.enable_wbg_udp = true;

    if (has_flag(argc, argv, "--unified-command"))
        cfg.runner.unified_command.enabled = true;
    const auto command_source = get_arg(argc, argv, "--command-source", "");
    if (!command_source.empty())
        cfg.runner.unified_command.source =
            diffusion_deploy::parse_unified_command_source(command_source);
    const auto command_device = get_arg(argc, argv, "--command-device", "");
    if (!command_device.empty())
        cfg.runner.unified_command.joystick_device = command_device;
    const auto command_mapping = get_arg(argc, argv, "--command-mapping", "");
    if (!command_mapping.empty())
        cfg.runner.unified_command.joystick_mapping = command_mapping;
    if (cfg.runner.unified_command.enabled
        && (cfg.runner.enable_cond_udp || cfg.runner.enable_wbg_udp)) {
        throw std::runtime_error(
            "--unified-command cannot be combined with legacy cond/WBG receivers");
    }
    const std::string wbg_host = get_arg(argc, argv, "--wbg-host");
    if (!wbg_host.empty()) cfg.runner.wbg_udp_host = wbg_host;
    const std::string wbg_port = get_arg(argc, argv, "--wbg-port");
    if (!wbg_port.empty()) {
        try {
            cfg.runner.wbg_udp_port = std::stoi(wbg_port);
        } catch (const std::exception&) {
            std::cerr << "[run_g1_robot] Error: invalid --wbg-port '" << wbg_port << "'\n";
            return 1;
        }
    }
    if (cfg.runner.enable_wbg_udp) {
        std::cout << "[run_g1_robot] WBG UDP enabled: "
                  << cfg.runner.wbg_udp_host << ":" << cfg.runner.wbg_udp_port << "\n";
    }

    // ---- 5. Build environment ----
    // Apply FSM env overrides first (network_interface, PR mode, etc.)
    const bool use_fsm = !has_flag(argc, argv, "--no-fsm");
    if (use_fsm && !fsm_yaml.empty()) {
        try {
            if (fsm_root["FSM"] && fsm_root["FSM"]["env"]) {
                auto n = fsm_root["FSM"]["env"];
                if (n["network_interface"])
                    cfg.env.network_interface = n["network_interface"].as<std::string>();
                if (n["use_pr_mode"])
                    cfg.env.use_pr_mode = n["use_pr_mode"].as<bool>();
                if (n["enable_safety_checks"])
                    cfg.env.enable_safety_checks = n["enable_safety_checks"].as<bool>();
                if (n["release_mode_before_control"])
                    cfg.env.release_mode_before_control =
                        n["release_mode_before_control"].as<bool>();
                if (n["state_timeout_s"])
                    cfg.env.state_timeout_s = n["state_timeout_s"].as<double>();
                std::cout << "[run_g1_robot] FSM env overrides applied.\n";
            }
        } catch (const std::exception& e) {
            std::cerr << "[run_g1_robot] FSM env config error: "
                      << e.what() << "\n";
            return 1;
        }
    }
    auto env = std::make_unique<diffusion_deploy::UnitreeEnv>(cfg.env);

    // ---- 6. Build obs composer ----
    auto composer = std::make_unique<diffusion_deploy::ObsComposer>(
        cfg.obs_profile, cfg.actor.n_obs_steps);

    std::cout << "[run_g1_robot] ObsComposer profile=" << cfg.actor.obs_dim
              << "-dim, n_obs_steps=" << cfg.actor.n_obs_steps << "\n";

    // ---- 7. (Optional) Safety FSM —— MUST be created BEFORE EnvRunner ----
    // The EnvRunner constructor *copies* EnvRunnerConfig, so the
    // safety_fsm pointer must be set in cfg.runner before construction.
    std::unique_ptr<diffusion_deploy::safety::DeployFSM> fsm;

    if (use_fsm) {
        // Load FSM definition from YAML (or use built-in defaults below)
        diffusion_deploy::safety::FSMDefinition fsm_def;
        if (!fsm_yaml.empty()) {
            try {
                if (fsm_root["FSM"]) {
                    fsm_def = diffusion_deploy::safety::load_fsm_definition(
                        fsm_root["FSM"]);
                } else {
                    std::cerr << "[run_g1_robot] Warning: --fsm-config YAML has no 'FSM:' key.\n";
                }
            } catch (const std::exception& e) {
                std::cerr << "[run_g1_robot] FSM definition error: "
                          << e.what() << "\n";
                return 1;
            }
        }

        // If no YAML FSM loaded, build a default 3-state FSM
        if (fsm_def.states.empty()) {
            std::cout << "[run_g1_robot] No FSM config provided. Using built-in defaults.\n";
            // Build defaults programmatically matching the old behaviour:
            // Passive (safe, kp=0) → Ready (stand pose) → Running (policy)
            diffusion_deploy::safety::FSMStateDef passive;
            passive.name = "Passive";
            passive.id   = 1;
            passive.kd   = {  // low damping for passive mode (29 DOF, MuJoCo order)
                3.f,3.f,3.f,3.f,3.f,3.f, 3.f,3.f,3.f,3.f,3.f,3.f, 3.f,3.f,3.f,
                3.f,3.f,3.f,3.f,3.f,3.f,3.f, 3.f,3.f,3.f,3.f,3.f,3.f,3.f,
            };
            passive.transitions.push_back({"Ready", diffusion_deploy::safety::parse_trigger("RB.on_pressed")});
            fsm_def.state_index["Passive"] = 0;
            fsm_def.states.push_back(passive);

            diffusion_deploy::safety::FSMStateDef ready;
            ready.name = "Ready";
            ready.id   = 2;
            ready.kp   = {  // stand stiffness (MuJoCo order)
                100,100,100,150,40,40, 100,100,100,150,40,40,
                200,200,200, 40,40,40,40,40,40,40, 40,40,40,40,40,40,40,
            };
            ready.kd   = {
                2,2,2,4,2,2, 2,2,2,4,2,2, 5,5,5,
                10,10,10,10,10,10,10, 10,10,10,10,10,10,10,
            };
            ready.has_interpolation = true;
            ready.interp_ts = {0.0f, 2.0f};  // 2-second smooth stand-up
            ready.interp_qs = {{}, diffusion_deploy::safety::reindex_mujoco_to_isaaclab({
                // MuJoCo (SDK) order — matches fsm_config.yaml convention
                // left leg: hip_pitch, hip_roll, hip_yaw, knee, ankle_pitch, ankle_roll
                -0.312f, 0.0f, 0.0f, 0.669f, -0.363f, 0.0f,
                // right leg: hip_pitch, hip_roll, hip_yaw, knee, ankle_pitch, ankle_roll
                -0.312f, 0.0f, 0.0f, 0.669f, -0.363f, 0.0f,
                // waist: yaw, roll, pitch
                0.0f, 0.0f, 0.0f,
                // left arm: shoulder_pitch, shoulder_roll, shoulder_yaw, elbow, wrist_roll, wrist_pitch, wrist_yaw
                0.2f, 0.2f, 0.0f, 0.6f, 0.0f, 0.0f, 0.0f,
                // right arm: shoulder_pitch, shoulder_roll, shoulder_yaw, elbow, wrist_roll, wrist_pitch, wrist_yaw
                0.2f, -0.2f, 0.0f, 0.6f, 0.0f, 0.0f, 0.0f,
            })};
            ready.transitions.push_back({"Passive", diffusion_deploy::safety::parse_trigger("B.on_pressed")});
            ready.transitions.push_back({"Running", diffusion_deploy::safety::parse_trigger("START.on_pressed")});
            fsm_def.state_index["Ready"] = 1;
            fsm_def.states.push_back(ready);

            diffusion_deploy::safety::FSMStateDef running;
            running.name = "Running";
            running.id   = 3;
            running.type = "policy";
            running.transitions.push_back({"Passive", diffusion_deploy::safety::parse_trigger("B.on_pressed")});
            fsm_def.state_index["Running"] = 2;
            fsm_def.states.push_back(running);

            // Passive (first state with no kp) is the fallback
            fsm_def.initial_idx    = 0;
            fsm_def.fallback_state = "Passive";
            fsm_def.has_fallback   = true;
        }

        std::string js_dev  = get_arg(argc, argv, "--fsm-device");
        // "null" → empty string → external mode (Unitree joystick from DDS)
        if (js_dev == "null") js_dev.clear();
        std::string js_map  = get_arg(argc, argv, "--fsm-joy-mapping", "xbox");

        // Load runtime overrides from YAML BEFORE constructing DeployFSM
        // (joystick_mapping must be set before JoystickReader opens the device).
        float  yaml_fall_limit    = 0.0f;
        bool   has_yaml_fall      = false;
        if (!fsm_yaml.empty()) {
            try {
                YAML::Node root = YAML::LoadFile(fsm_yaml);
                if (root["FSM"]) {
                    auto n = root["FSM"];
                    if (n["joystick_device"]) {
                        js_dev = n["joystick_device"].as<std::string>();
                        if (js_dev == "null") js_dev.clear();
                    }
                    if (n["joystick_mapping"])
                        js_map = n["joystick_mapping"].as<std::string>();
                    if (n["bad_orientation_limit_deg"]) {
                        yaml_fall_limit = n["bad_orientation_limit_deg"].as<float>();
                        has_yaml_fall = true;
                    }
                }
            } catch (...) {}
        }

        // When enabled, unified_command is the single joystick config truth
        // for FSM buttons, WBG axes and D-pad text selection.
        if (cfg.runner.unified_command.enabled) {
            const auto source = diffusion_deploy::resolve_unified_command_source(
                cfg.runner.unified_command);
            js_dev = source == diffusion_deploy::UnifiedCommandSource::UnitreeLowState
                ? "" : cfg.runner.unified_command.joystick_device;
            js_map = cfg.runner.unified_command.joystick_mapping;
        }

        fsm = std::make_unique<diffusion_deploy::safety::DeployFSM>(
            fsm_def,
            js_dev,   // empty → external mode (Unitree DDS joystick)
            js_map);

        // Apply runtime config (CLI overrides take priority over YAML)
        std::string limit_str = get_arg(argc, argv, "--fsm-fall-limit");
        if (!limit_str.empty())
            fsm->config_.bad_orientation_limit_deg = std::stof(limit_str);
        else if (has_yaml_fall)
            fsm->config_.bad_orientation_limit_deg = yaml_fall_limit;

        // Load remaining runtime overrides from YAML
        if (!fsm_yaml.empty()) {
            try {
                YAML::Node root = YAML::LoadFile(fsm_yaml);
                if (root["FSM"]) {
                    auto n = root["FSM"];
                    if (n["auto_passive_on_fall"])
                        fsm->config_.auto_passive_on_fall = n["auto_passive_on_fall"].as<bool>();
                    if (n["torque_limits"] && n["torque_limits"].IsSequence())
                        fsm->config_.torque_limits = n["torque_limits"].as<std::vector<float>>();
                }
            } catch (...) {}
        }

        cfg.runner.safety_fsm = fsm.get();
    } else {
        std::cout << "[run_g1_robot] FSM disabled (--no-fsm). No safety supervision.\n";
    }

    // ---- 8. Build runner ----
    cfg.runner.n_obs_steps = cfg.actor.n_obs_steps;
    cfg.runner.target_dt   = cfg.env.control_dt;

    auto runner = std::make_unique<diffusion_deploy::EnvRunner>(
        std::move(env), std::move(composer), std::move(agent), cfg.runner);

    g_runner = runner.get();

    // ---- 9. Install signal handler ----
    std::signal(SIGINT,  signal_handler);
    std::signal(SIGTERM, signal_handler);

    // ---- 10. Run ----
    std::cout << "[run_g1_robot] Starting control loop. Press Ctrl+C to stop.\n";
    auto stats = runner->run();

    // ---- 11. Print results ----
    std::cout << "\n[run_g1_robot] Results:\n"
              << "  Total steps:       " << stats.total_steps    << "\n"
              << "  Elapsed (s):       " << stats.elapsed_s      << "\n"
              << "  Avg step (ms):     " << stats.avg_step_ms    << "\n"
              << "  Num episodes:      " << stats.num_episodes    << "\n"
              << "  Mean reward:       " << stats.mean_episode_reward << "\n"
              << "  Mean length:       " << stats.mean_episode_length << "\n"
              << "  Policy steps:      " << stats.policy_steps << "\n"
              << "  Finite actions:    " << stats.finite_action_steps << "/"
              << stats.policy_steps << "\n"
              << "  Max |action|:      " << stats.max_abs_action << "\n"
              << "  Action RMS:        " << stats.action_rms << "\n"
              << "  Action delta RMS:  " << stats.action_delta_rms << "\n"
              << "  Max |action delta|:" << stats.max_abs_action_delta << "\n"
              << "  Action jerk RMS:   " << stats.action_jerk_rms << "\n"
              << "  Max |action jerk|: " << stats.max_abs_action_jerk << "\n"
              << "  Saturation rate:   " << stats.action_saturation_rate << "\n"
              << "  Max joint motion:  " << stats.max_joint_displacement << " rad\n"
              << "  Avg inference (ms):" << stats.avg_inference_ms << "\n"
              << "  Loop overruns:     " << stats.overrun_count << "\n"
              << "  Max step (ms):     " << stats.max_step_ms << "\n";

    g_runner = nullptr;
    return 0;
}
