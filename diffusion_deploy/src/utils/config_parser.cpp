#include "diffusion_deploy/utils/config_parser.hpp"
#include "diffusion_deploy/utils/action_selection.hpp"
#include <yaml-cpp/yaml.h>
#include <torch/version.h>
#include <cmath>
#include <filesystem>
#include <stdexcept>
#include <iostream>

namespace diffusion_deploy {

static std::string resolve_config_path(const std::string& yaml_path,
                                       const std::string& value) {
    if (value.empty()) return {};
    const std::filesystem::path path(value);
    if (path.is_absolute()) return path.lexically_normal().string();
    const auto config_dir = std::filesystem::absolute(yaml_path).parent_path();
    return (config_dir / path).lexically_normal().string();
}

// ---- Helper: load float vector from YAML node ----
static std::vector<float> load_float_vec(const YAML::Node& node,
                                          const std::string& key) {
    if (!node[key]) return {};
    std::vector<float> v;
    for (const auto& x : node[key]) v.push_back(x.as<float>());
    return v;
}

static std::vector<int> load_int_vec(const YAML::Node& node,
                                     const std::string& key) {
    if (!node[key]) return {};
    std::vector<int> v;
    for (const auto& x : node[key]) v.push_back(x.as<int>());
    return v;
}

static AxisGuidanceConfig load_axis_guidance(const YAML::Node& node) {
    AxisGuidanceConfig out;
    if (!node) return out;
    out.enabled = node["enabled"] ? node["enabled"].as<bool>() : false;
    out.command = node["command"] ? node["command"].as<float>() : 0.0f;
    out.kp = node["kp"] ? node["kp"].as<float>() : 1.0f;
    out.body_indices = load_int_vec(node, "body_indices");
    if (out.body_indices.empty()) out.body_indices = {0, 9};
    return out;
}

// ---- Helper: load single normalizer ----
static std::shared_ptr<Normalizer> load_single_normalizer(const YAML::Node& node) {
    if (!node) return nullptr;
    std::string mode = node["mode"] ? node["mode"].as<std::string>() : "linear";

    if (mode == "scale_offset") {
        auto scale  = load_float_vec(node, "scale");
        auto offset = load_float_vec(node, "offset");
        if (scale.empty() || offset.empty()) return nullptr;
        return Normalizer::from_scale_offset(scale, offset);
    }
    if (mode == "linear" || mode == "limits") {
        auto mn = load_float_vec(node, "min");
        auto mx = load_float_vec(node, "max");
        if (mn.empty() || mx.empty()) return nullptr;
        return Normalizer::from_min_max(mn, mx);
    }
    if (mode == "standard" || mode == "gaussian") {
        auto mean = load_float_vec(node, "mean");
        auto std  = load_float_vec(node, "std");
        if (mean.empty() || std.empty()) return nullptr;
        return Normalizer::from_mean_std(mean, std);
    }
    throw std::runtime_error("config_parser: unknown normalizer mode: " + mode);
}

// ---- load_config() ----

DeployConfig load_config(
        const std::string& yaml_path,
        const DeployConfigOverrides& overrides) {
    YAML::Node root;
    try {
        root = YAML::LoadFile(yaml_path);
    } catch (const YAML::Exception& e) {
        throw std::runtime_error("config_parser: failed to load '" +
                                  yaml_path + "': " + e.what());
    }

    DeployConfig cfg;
    // BUG: The config is not loaded correctly (e.g. cond_dim)
    // ---- model ----
    if (root["model"]) {
        const auto& m = root["model"];
        cfg.model_backend = m["backend"]      ? m["backend"].as<std::string>()       : "torch";
        cfg.actor_type    = m["actor_type"]   ? m["actor_type"].as<std::string>()    : "torch";
        cfg.model_path    = m["path"]         ? m["path"].as<std::string>()          : "";
        cfg.schedule_path = m["schedule_path"]? m["schedule_path"].as<std::string>() : "";
        cfg.export_torch_version = m["export_torch_version"]
            ? m["export_torch_version"].as<std::string>() : "";
        cfg.model_precision = m["precision"]
            ? m["precision"].as<std::string>() : "fp32";
        if (cfg.model_precision != "fp32" && cfg.model_precision != "fp16")
            throw std::runtime_error(
                "config_parser: model.precision must be fp32 or fp16");

        // Legacy ActorConfig (for TorchActor / OnnxActor fallback)
        cfg.actor.obs_dim         = m["obs_dim"]         ? m["obs_dim"].as<int>()         : 192;
        cfg.actor.action_dim      = m["action_dim"]      ? m["action_dim"].as<int>()      : 29;
        cfg.actor.cond_dim        = m["cond_dim"]        ? m["cond_dim"].as<int>()        : 512;
        cfg.actor.n_obs_steps     = m["n_obs_steps"]     ? m["n_obs_steps"].as<int>()     : 4;
        cfg.actor.n_future_steps  = m["n_future_steps"]  ? m["n_future_steps"].as<int>()  : 16;
        cfg.actor.denoising_steps = m["denoising_steps"] ? m["denoising_steps"].as<int>() : 100;

        // DiffusionActorConfig
        auto& da = cfg.diffusion_actor;
        da.obs_dim           = cfg.actor.obs_dim;
        da.action_dim        = cfg.actor.action_dim;
        da.n_obs_steps       = cfg.actor.n_obs_steps;
        da.n_future_steps    = cfg.actor.n_future_steps;
        da.denoising_steps   = cfg.actor.denoising_steps;
        da.predict_epsilon   = m["predict_epsilon"]  ? m["predict_epsilon"].as<bool>()   : false;
        da.denoised_clip     = m["denoised_clip"]    ? m["denoised_clip"].as<float>()    : 1.0f;
        da.has_motion_cond   = m["has_motion_cond"]  ? m["has_motion_cond"].as<bool>()   : true;
        da.motion_dim        = m["motion_dim"]       ? m["motion_dim"].as<int>()         : 512;
        da.backbone_cond_dim = m["backbone_cond_dim"]? m["backbone_cond_dim"].as<int>()  : da.obs_dim;
        da.ddim_steps        = m["ddim_steps"]       ? m["ddim_steps"].as<int>()         : 0;
        da.ddim_eta          = m["ddim_eta"]         ? m["ddim_eta"].as<float>()         : 0.0f;

        // JointDiffusionActorConfig (inherits from DiffusionActorConfig fields)
        auto& ja = cfg.joint_actor;
        ja.precision                = cfg.model_precision;
        ja.obs_dim                  = da.obs_dim;
        ja.action_dim               = da.action_dim;
        ja.n_obs_steps              = da.n_obs_steps;
        ja.n_future_steps           = da.n_future_steps;
        ja.denoising_steps          = da.denoising_steps;
        ja.predict_epsilon          = da.predict_epsilon;
        ja.denoised_clip            = da.denoised_clip;
        ja.has_motion_cond          = da.has_motion_cond;
        ja.motion_dim               = da.motion_dim;
        ja.backbone_cond_dim        = da.backbone_cond_dim;
        ja.n_cond_steps             = m["n_cond_steps"] ? m["n_cond_steps"].as<int>() : 1;
        ja.no_state_override        = m["no_state_override"] ? m["no_state_override"].as<bool>() : false;
        ja.state_pred_epsilon       = m["state_pred_epsilon"]   ? m["state_pred_epsilon"].as<bool>()   : da.predict_epsilon;
        ja.action_pred_epsilon      = m["action_pred_epsilon"]  ? m["action_pred_epsilon"].as<bool>()  : da.predict_epsilon;
        ja.action_denoising_steps   = m["action_denoising_steps"]? m["action_denoising_steps"].as<int>(): da.denoising_steps;
        ja.state_denoising_steps    = m["state_denoising_steps"] ? m["state_denoising_steps"].as<int>() : da.denoising_steps;
        ja.ddim_steps               = da.ddim_steps;
        ja.ddim_eta                 = da.ddim_eta;
        ja.attention_projection_packing = m["attention_projection_packing"]
            ? m["attention_projection_packing"].as<std::string>() : "none";
        ja.condition_embedding_reuse = m["condition_embedding_reuse"]
            ? m["condition_embedding_reuse"].as<bool>() : false;
        ja.ddim_precompute = m["ddim_precompute"]
            ? m["ddim_precompute"].as<bool>() : false;
        ja.defer_finite_checks = m["defer_finite_checks"]
            ? m["defer_finite_checks"].as<bool>() : false;
        ja.inference_mode = m["inference_mode"]
            ? m["inference_mode"].as<bool>() : false;
        if (ja.condition_embedding_reuse && !ja.has_motion_cond)
            throw std::runtime_error(
                "config_parser: condition_embedding_reuse requires a conditioned model");
        if (ja.ddim_precompute && (ja.ddim_steps <= 0 || ja.ddim_eta != 0.0f))
            throw std::runtime_error(
                "config_parser: ddim_precompute requires deterministic DDIM "
                "(ddim_steps>0, ddim_eta=0)");

        // ---- Python-aligned `backbone:` block + actor provenance fields ----
        // The deploy YAML mirrors the Python config names: a nested
        // model.backbone block (x_input_dim / x_output_dim / cond_dim /
        // n_cond_steps / cross_attn_window / cross_attn_mode) plus top-level
        // model.clean_past_state and model.data_profile.  Parse them onto the
        // joint_actor struct and cross-check against the flat legacy names
        // (state_dim / backbone_cond_dim / n_cond_steps) so a drifted export
        // fails loudly instead of silently mis-running.
        if (m["state_dim"]) {
            // Flat legacy name for the emphasis-space state dim (Python
            // backbone.x_output_dim).  C++ derives the runtime dim from the
            // emphasis matrix, so this is recorded for the cross-check.
            ja.x_output_dim = m["state_dim"].as<int>();
        }
        if (m["backbone"] && m["backbone"].IsMap()) {
            const auto& bb = m["backbone"];
            if (bb["x_input_dim"])   ja.x_input_dim  = bb["x_input_dim"].as<int>();
            if (bb["x_output_dim"])  ja.x_output_dim = bb["x_output_dim"].as<int>();
            if (bb["cond_dim"]) {
                const int cond_dim_py = bb["cond_dim"].as<int>();
                if (m["backbone_cond_dim"]
                    && m["backbone_cond_dim"].as<int>() != cond_dim_py) {
                    throw std::runtime_error(
                        "config_parser: model.backbone.cond_dim (" +
                        std::to_string(cond_dim_py) + ") != "
                        "model.backbone_cond_dim (" +
                        std::to_string(m["backbone_cond_dim"].as<int>()) + ")");
                }
                ja.backbone_cond_dim = cond_dim_py;
            }
            if (bb["n_cond_steps"]) {
                const int ncs = bb["n_cond_steps"].as<int>();
                if (m["n_cond_steps"] && m["n_cond_steps"].as<int>() != ncs) {
                    throw std::runtime_error(
                        "config_parser: model.backbone.n_cond_steps (" +
                        std::to_string(ncs) + ") != model.n_cond_steps (" +
                        std::to_string(m["n_cond_steps"].as<int>()) + ")");
                }
                ja.n_cond_steps = ncs;
            }
            if (bb["cross_attn_window"] && !bb["cross_attn_window"].IsNull())
                ja.cross_attn_window = bb["cross_attn_window"].as<int>();
            if (bb["cross_attn_mode"])
                ja.cross_attn_mode = bb["cross_attn_mode"].as<std::string>();
        }
        if (m["clean_past_state"]) ja.clean_past_state = m["clean_past_state"].as<bool>();
        if (m["data_profile"])     ja.data_profile     = m["data_profile"].as<std::string>();

        // DiffuseCLoCActorConfig
        auto& ca = cfg.cloc_actor;
        static_cast<JointDiffusionActorConfig&>(ca) = ja;
        ca.action_schedule = m["action_schedule"] ? m["action_schedule"].as<std::string>() : "from_xT_decreasing";
        ca.state_schedule  = m["state_schedule"]  ? m["state_schedule"].as<std::string>()  : "from_xT_step";
        ca.state_emphasis  = m["state_emphasis"]  ? m["state_emphasis"].as<std::string>()  : "same";
        ca.sampler_mode    = m["sampler_mode"]    ? m["sampler_mode"].as<std::string>()    : "rolling_ddpm";
        ca.use_ns_ddim = m["use_ns_ddim"] ? m["use_ns_ddim"].as<bool>() : false;
        ca.randomize_noise_schedule =
            m["randomize_noise_schedule"] ? m["randomize_noise_schedule"].as<bool>() : true;
        ca.classifier_guidance_impl = m["classifier_guidance_impl"]
            ? m["classifier_guidance_impl"].as<std::string>()
            : "reuse_x0";
        ca.emphasis_path   = m["emphasis_path"]   ? m["emphasis_path"].as<std::string>()   : "";
        if (m["whole_body_guidance"]) {
            const auto& w = m["whole_body_guidance"];
            ca.guidance.enabled = w["enabled"] ? w["enabled"].as<bool>() : false;
            ca.guidance.mode = w["mode"] ? w["mode"].as<std::string>() : "classifier";
            ca.guidance.trajectory_mode = w["trajectory_mode"]
                ? w["trajectory_mode"].as<std::string>() : "simple";
            ca.guidance.dt = w["dt"] ? w["dt"].as<float>() : 0.02f;
            ca.guidance.enable_zeta_comp = w["enable_zeta_comp"]
                ? w["enable_zeta_comp"].as<bool>() : true;
            ca.guidance.enable_damping_comp = w["enable_damping_comp"]
                ? w["enable_damping_comp"].as<bool>() : true;
            ca.guidance.axis_gradient_impl = w["axis_gradient_impl"]
                ? w["axis_gradient_impl"].as<std::string>() : "sequential";
            ca.guidance.n_past_steps = ja.n_obs_steps;
            ca.guidance.horizon = ja.horizon();
            ca.guidance.denoising_steps = ja.denoising_steps;
            ca.guidance.vx = load_axis_guidance(w["vx"]);
            ca.guidance.vy = load_axis_guidance(w["vy"]);
            ca.guidance.wz = load_axis_guidance(w["wz"]);
        }

        if (m["obs_profile"]) {
            cfg.obs_profile = obs_profile_from_string(m["obs_profile"].as<std::string>());
        }

        // ---- Cross-check Python-aligned vs flat legacy names ----
        // The nested `backbone:` block and the flat model fields must agree.
        // Fail loudly on any mismatch so a drifted export cannot silently run
        // with wrong dimensions.  The runtime state dim is derived from the
        // emphasis matrix, so x_input_dim/x_output_dim are cross-checked for
        // self-consistency (they are 384 for the G1 PRDP) but not assumed to
        // equal the pre-emphasis obs_dim.
        if (ja.x_input_dim != 0 && ja.x_output_dim != 0
            && ja.x_input_dim != ja.x_output_dim) {
            throw std::runtime_error(
                "config_parser: model.backbone.x_input_dim (" +
                std::to_string(ja.x_input_dim) + ") != "
                "model.backbone.x_output_dim (" +
                std::to_string(ja.x_output_dim) + ")");
        }
        if (ja.cross_attn_window < 0) {
            throw std::runtime_error(
                "config_parser: model.backbone.cross_attn_window must be >= 0 "
                "(null/unset), got " + std::to_string(ja.cross_attn_window));
        }
        const std::string& cam = ja.cross_attn_mode;
        if (cam != "full" && cam != "state" && cam != "action" && cam != "no_attn") {
            throw std::runtime_error(
                "config_parser: model.backbone.cross_attn_mode '" + cam +
                "' not in {full,state,action,no_attn}");
        }
    }

    // ---- env ----
    if (root["env"]) {
        const auto& e = root["env"];
        cfg.env.execution_mode = parse_execution_mode(
            e["execution_mode"] ? e["execution_mode"].as<std::string>() : "offline");
        cfg.env.network_interface = e["network_interface"] ?
            e["network_interface"].as<std::string>() : "";
        cfg.env.control_dt  = e["control_dt"]  ? e["control_dt"].as<double>()  : 0.02;
        cfg.env.state_timeout_s = e["state_timeout_s"] ?
            e["state_timeout_s"].as<double>() : 0.10;
        cfg.env.num_dof     = e["num_dof"]     ? e["num_dof"].as<int>()        : 29;
        cfg.env.use_pr_mode = e["use_pr_mode"] ? e["use_pr_mode"].as<bool>()   : true;
        cfg.env.enable_safety_checks = e["enable_safety_checks"] ?
            e["enable_safety_checks"].as<bool>() : true;
        cfg.env.release_mode_before_control = e["release_mode_before_control"] ?
            e["release_mode_before_control"].as<bool>() : true;
        cfg.env.mode_machine = e["mode_machine"] ?
            static_cast<uint8_t>(e["mode_machine"].as<int>()) : static_cast<uint8_t>(0);
        cfg.env.use_fk    = e["use_fk"]    ? e["use_fk"].as<bool>()          : false;
        cfg.env.urdf_path = e["urdf_path"] ? e["urdf_path"].as<std::string>() : "";

        auto kp = load_float_vec(e, "Kp");
        auto kd = load_float_vec(e, "Kd");
        if (!kp.empty()) cfg.env.Kp = kp;
        if (!kd.empty()) cfg.env.Kd = kd;
    }

    // ---- portable resource contract (optional for legacy configs) ----
    if (root["resources"]) {
        const auto& resources = root["resources"];
        cfg.resource_schema_version = resources["schema_version"]
            ? resources["schema_version"].as<int>() : 0;
        cfg.resource_manifest_path = resources["manifest"]
            ? resources["manifest"].as<std::string>() : "";
        cfg.resource_checksum_path = resources["checksum_file"]
            ? resources["checksum_file"].as<std::string>() : "";
        cfg.conditioning_mode = resources["conditioning_mode"]
            ? resources["conditioning_mode"].as<std::string>() : "";
        if (cfg.resource_schema_version != 1)
            throw std::runtime_error(
                "config_parser: resources.schema_version must be 1");
        if (cfg.resource_manifest_path.empty() || cfg.resource_checksum_path.empty())
            throw std::runtime_error(
                "config_parser: resources.manifest and checksum_file are required");
        const auto require_relative = [](const std::string& label,
                                         const std::string& path) {
            if (!path.empty() && std::filesystem::path(path).is_absolute())
                throw std::runtime_error(
                    "config_parser: portable resources require relative " +
                    label + ": " + path);
        };
        require_relative("model.path", cfg.model_path);
        require_relative("model.schedule_path", cfg.schedule_path);
        require_relative("model.emphasis_path", cfg.cloc_actor.emphasis_path);
        require_relative("env.urdf_path", cfg.env.urdf_path);
        require_relative("resources.manifest", cfg.resource_manifest_path);
        require_relative("resources.checksum_file", cfg.resource_checksum_path);
        if (cfg.conditioning_mode != "none"
            && cfg.conditioning_mode != "external_udp"
            && cfg.conditioning_mode != "cached_in_process")
            throw std::runtime_error(
                "config_parser: resources.conditioning_mode must be none, "
                "external_udp, or cached_in_process");
    }

    // Artifact paths in deploy YAML are relative to the YAML file, not the
    // process working directory. This makes an installed bundle movable.
    cfg.model_path = resolve_config_path(yaml_path, cfg.model_path);
    cfg.schedule_path = resolve_config_path(yaml_path, cfg.schedule_path);
    cfg.cloc_actor.emphasis_path =
        resolve_config_path(yaml_path, cfg.cloc_actor.emphasis_path);
    cfg.env.urdf_path = resolve_config_path(yaml_path, cfg.env.urdf_path);
    cfg.resource_manifest_path =
        resolve_config_path(yaml_path, cfg.resource_manifest_path);
    cfg.resource_checksum_path =
        resolve_config_path(yaml_path, cfg.resource_checksum_path);

    // ---- runner ----
    cfg.runner.n_obs_steps = cfg.actor.n_obs_steps;
    cfg.runner.target_dt = cfg.env.control_dt;
    if (root["runner"]) {
        const auto& r = root["runner"];
        cfg.runner.max_steps     = r["max_steps"]     ? r["max_steps"].as<int>()       : 1000;
        cfg.runner.delay_action_step = r["delay_action_step"]
            ? r["delay_action_step"].as<double>() : 0.0;
        cfg.runner.realtime_mode = r["realtime_mode"] ? r["realtime_mode"].as<bool>()  : true;
        cfg.runner.reset_height  = r["reset_height"]  ? r["reset_height"].as<float>()  : 0.3f;
        if (r["csv_record_path"]) {
            cfg.runner.csv_record.path = r["csv_record_path"].as<std::string>();
            cfg.runner.csv_record.enabled = !cfg.runner.csv_record.path.empty();
        }

        // Cond UDP
        if (r["enable_cond_udp"]) {
            cfg.runner.enable_cond_udp = r["enable_cond_udp"].as<bool>();
        }
        if (r["cond_udp_port"]) {
            cfg.runner.cond_udp_port = r["cond_udp_port"].as<int>();
        }
        cfg.runner.cond_dim = cfg.actor.cond_dim;
        cfg.runner.condition_profile = r["condition_profile"]
            ? r["condition_profile"].as<std::string>() : "external";
        cfg.runner.n_cond_steps = r["n_cond_steps"]
            ? r["n_cond_steps"].as<int>() : cfg.joint_actor.n_cond_steps;
        cfg.runner.rlobs_cond_dim = r["rlobs_cond_dim"]
            ? r["rlobs_cond_dim"].as<int>() : 0;
        cfg.runner.text_cond_dim = r["text_cond_dim"]
            ? r["text_cond_dim"].as<int>() : 0;
        cfg.runner.cond_startup_timeout_s = r["cond_startup_timeout_s"]
            ? r["cond_startup_timeout_s"].as<double>() : 30.0;
        if (cfg.runner.condition_profile == "prdp_rlobs"
            || cfg.runner.condition_profile == "g1_prdp_standard2")
            cfg.runner.cond_dim = cfg.runner.text_cond_dim;

        // WBG UDP (interactive whole-body guidance commands)
        if (r["enable_wbg_udp"]) {
            cfg.runner.enable_wbg_udp = r["enable_wbg_udp"].as<bool>();
        }
        if (r["wbg_udp_host"]) {
            cfg.runner.wbg_udp_host = r["wbg_udp_host"].as<std::string>();
        }
        if (r["wbg_udp_port"]) {
            cfg.runner.wbg_udp_port = r["wbg_udp_port"].as<int>();
        }

        // Unified C++ joystick command source (opt-in; old UDP senders remain
        // the default). Relative latent paths follow deploy-config semantics.
        if (r["unified_command"]) {
            const auto& u = r["unified_command"];
            auto& out = cfg.runner.unified_command;
            out.enabled = u["enabled"] ? u["enabled"].as<bool>() : false;
            out.source = parse_unified_command_source(
                u["source"] ? u["source"].as<std::string>() : "auto");
            out.joystick_device = u["joystick_device"]
                ? u["joystick_device"].as<std::string>()
                : (out.source == UnifiedCommandSource::UnitreeLowState
                       ? "" : "/dev/input/js0");
            out.joystick_mapping = u["joystick_mapping"]
                ? u["joystick_mapping"].as<std::string>() : "xbox";
            out.source_timeout_s = u["source_timeout_s"]
                ? u["source_timeout_s"].as<double>() : 0.10;
            out.deadzone = u["deadzone"] ? u["deadzone"].as<float>() : 0.10f;
            out.dpad_debounce_ms = u["dpad_debounce_ms"]
                ? u["dpad_debounce_ms"].as<int>() : 150;
            if (u["wbg"]) {
                const auto& w = u["wbg"];
                out.wbg_enabled = w["enabled"] ? w["enabled"].as<bool>() : true;
                out.max_vx = w["max_vx"] ? w["max_vx"].as<float>() : 5.0f;
                out.max_vy = w["max_vy"] ? w["max_vy"].as<float>() : 5.0f;
                out.max_wz = w["max_wz"] ? w["max_wz"].as<float>() : 5.0f;
                out.wbg_kp = w["kp"] ? w["kp"].as<float>() : 1.0f;
                if (w["controls"]) {
                    const auto& c = w["controls"];
                    out.wbg_controls.l2_kp_enabled = c["l2_kp_enabled"]
                        ? c["l2_kp_enabled"].as<bool>() : false;
                    out.wbg_controls.kp_axis = c["kp_axis"]
                        ? c["kp_axis"].as<std::string>() : "l2";
                    out.wbg_controls.kp_unpressed = c["kp_unpressed"]
                        ? c["kp_unpressed"].as<float>() : 1.0f;
                    out.wbg_controls.kp_pressed = c["kp_pressed"]
                        ? c["kp_pressed"].as<float>() : 0.0f;
                    out.wbg_controls.lb_toggle_enabled = c["lb_toggle_enabled"]
                        ? c["lb_toggle_enabled"].as<bool>() : false;
                    out.wbg_controls.toggle_button = c["toggle_button"]
                        ? c["toggle_button"].as<std::string>() : "LB";
                    out.wbg_controls.toggle_debounce_ms = c["toggle_debounce_ms"]
                        ? c["toggle_debounce_ms"].as<int>() : 150;
                }
            }
            if (u["motions"]) {
                if (!u["motions"].IsSequence())
                    throw std::runtime_error("config_parser: runner.unified_command.motions must be a sequence");
                for (const auto& item : u["motions"]) {
                    MotionLatentConfig motion;
                    motion.name = item["name"] ? item["name"].as<std::string>() : "";
                    motion.dpad = item["dpad"] ? item["dpad"].as<std::string>() : "";
                    motion.path = item["path"] ? resolve_config_path(
                        yaml_path, item["path"].as<std::string>()) : "";
                    motion.hash = item["hash"] ? item["hash"].as<std::string>() : "";
                    motion.dim = item["dim"] ? item["dim"].as<int>() : 512;
                    out.motions.push_back(std::move(motion));
                }
            }
            if (u["compatibility_udp"]) {
                const auto& p = u["compatibility_udp"];
                out.compatibility_udp.enabled = p["enabled"]
                    ? p["enabled"].as<bool>() : false;
                out.compatibility_udp.host = p["host"]
                    ? p["host"].as<std::string>() : "127.0.0.1";
                out.compatibility_udp.condition_port = p["condition_port"]
                    ? p["condition_port"].as<int>() : 9877;
                out.compatibility_udp.wbg_port = p["wbg_port"]
                    ? p["wbg_port"].as<int>() : 9879;
            }
            if (u["telemetry"]) {
                const auto& t = u["telemetry"];
                out.telemetry.enabled = t["enabled"] ? t["enabled"].as<bool>() : false;
                out.telemetry.host = t["host"]
                    ? t["host"].as<std::string>() : "127.0.0.1";
                out.telemetry.port = t["port"] ? t["port"].as<int>() : 9880;
            }
        }
    }

    if (overrides.enable_unified_command)
        cfg.runner.unified_command.enabled = true;
    if (!overrides.unified_command_source.empty()) {
        cfg.runner.unified_command.source = parse_unified_command_source(
            overrides.unified_command_source);
        if (overrides.unified_command_device.empty()
            && cfg.runner.unified_command.source
                == UnifiedCommandSource::UnitreeLowState) {
            cfg.runner.unified_command.joystick_device.clear();
        } else if (overrides.unified_command_device.empty()
                   && cfg.runner.unified_command.source
                       == UnifiedCommandSource::Joydev
                   && (cfg.runner.unified_command.joystick_device.empty()
                       || cfg.runner.unified_command.joystick_device == "null")) {
            cfg.runner.unified_command.joystick_device = "/dev/input/js0";
        }
    }
    if (!overrides.unified_command_device.empty())
        cfg.runner.unified_command.joystick_device =
            overrides.unified_command_device;
    if (!overrides.unified_command_mapping.empty())
        cfg.runner.unified_command.joystick_mapping =
            overrides.unified_command_mapping;
    if (cfg.runner.unified_command.enabled && cfg.runner.enable_cond_udp)
        throw std::runtime_error(
            "config_parser: unified_command and enable_cond_udp are mutually exclusive");
    if (cfg.runner.unified_command.enabled && cfg.runner.enable_wbg_udp)
        throw std::runtime_error(
            "config_parser: unified_command and enable_wbg_udp are mutually exclusive");
    if (cfg.runner.unified_command.enabled && cfg.runner.text_cond_dim <= 0)
        throw std::runtime_error(
            "config_parser: unified_command requires runner.text_cond_dim > 0");
    if (cfg.runner.unified_command.enabled) {
        const auto source = resolve_unified_command_source(
            cfg.runner.unified_command);
        const bool has_device = !cfg.runner.unified_command.joystick_device.empty()
            && cfg.runner.unified_command.joystick_device != "null";
        if ((source == UnifiedCommandSource::Joydev && !has_device)
            || (source == UnifiedCommandSource::UnitreeLowState && has_device))
            throw std::runtime_error(
                "config_parser: unified command source/device conflict");
        if (!std::isfinite(cfg.runner.unified_command.source_timeout_s)
            || cfg.runner.unified_command.source_timeout_s <= 0.0)
            throw std::runtime_error(
                "config_parser: unified source_timeout_s must be finite and positive");
        if (!std::isfinite(cfg.runner.unified_command.max_vx)
            || !std::isfinite(cfg.runner.unified_command.max_vy)
            || !std::isfinite(cfg.runner.unified_command.max_wz)
            || cfg.runner.unified_command.max_vx < 0.0f
            || cfg.runner.unified_command.max_vy < 0.0f
            || cfg.runner.unified_command.max_wz < 0.0f)
            throw std::runtime_error(
                "config_parser: unified WBG max_vx/max_vy/max_wz must be finite and non-negative");
        const auto& controls = cfg.runner.unified_command.wbg_controls;
        if (controls.l2_kp_enabled && controls.kp_axis != "l2")
            throw std::runtime_error(
                "config_parser: unified WBG controls.kp_axis must be l2");
        if (controls.lb_toggle_enabled && controls.toggle_button != "LB")
            throw std::runtime_error(
                "config_parser: unified WBG controls.toggle_button must be LB");
        if (controls.toggle_debounce_ms < 0
            || !std::isfinite(controls.kp_unpressed)
            || !std::isfinite(controls.kp_pressed)
            || controls.kp_unpressed < 0.0f || controls.kp_pressed < 0.0f
            || controls.kp_unpressed > 1.0f || controls.kp_pressed > 1.0f
            || controls.kp_pressed > controls.kp_unpressed)
            throw std::runtime_error(
                "config_parser: invalid unified WBG trigger/toggle controls");
    }

    try {
        (void)runner_action_selection(
            cfg.actor.n_obs_steps, cfg.runner.delay_action_step,
            cfg.actor.horizon(),
            std::vector<int>(static_cast<size_t>(cfg.actor.horizon()), 0));
    } catch (const std::exception& e) {
        throw std::runtime_error(
            std::string("config_parser: invalid runner.delay_action_step: ") + e.what());
    }

    if (cfg.resource_schema_version != 0) {
        if (!std::filesystem::is_regular_file(cfg.resource_manifest_path))
            throw std::runtime_error(
                "config_parser: resource manifest not found: " +
                cfg.resource_manifest_path);
        if (!std::filesystem::is_regular_file(cfg.resource_checksum_path))
            throw std::runtime_error(
                "config_parser: resource checksum file not found: " +
                cfg.resource_checksum_path);
        if (cfg.conditioning_mode == "external_udp") {
            if (cfg.runner.text_cond_dim <= 0
                || !cfg.runner.enable_cond_udp
                || cfg.runner.unified_command.enabled)
                throw std::runtime_error(
                    "config_parser: external_udp resources require text_cond_dim > 0 "
                    "and runner.enable_cond_udp=true with unified_command disabled");
        } else if (cfg.conditioning_mode == "cached_in_process") {
            if (cfg.runner.text_cond_dim <= 0
                || !cfg.runner.unified_command.enabled
                || cfg.runner.enable_cond_udp)
                throw std::runtime_error(
                    "config_parser: cached_in_process resources require "
                    "text_cond_dim > 0 and runner.unified_command.enabled=true "
                    "with enable_cond_udp=false");
        } else if (cfg.runner.text_cond_dim != 0) {
            throw std::runtime_error(
                "config_parser: conditioning_mode=none requires text_cond_dim=0");
        }
    }

    // ---- normalization ----
    cfg.normalizer = std::make_shared<MultiNormalizer>();
    if (root["normalization"]) {
        const auto& n = root["normalization"];

        auto obs_norm = load_single_normalizer(n["obs"]);
        if (obs_norm) {
            cfg.normalizer->add("obs", obs_norm);
            if (cfg.cloc_actor.guidance.enabled) {
                cfg.cloc_actor.guidance.obs_scale = load_float_vec(n["obs"], "scale");
                cfg.cloc_actor.guidance.obs_offset = load_float_vec(n["obs"], "offset");
            }
        } else {
            std::cerr << "[config_parser] Warning: no obs normalizer found, using identity.\n";
            cfg.normalizer->add("obs",
                Normalizer::create_identity(cfg.actor.obs_dim));
        }

        auto act_norm = load_single_normalizer(n["action"]);
        if (act_norm) {
            cfg.normalizer->add("action", act_norm);
        } else {
            std::cerr << "[config_parser] Warning: no action normalizer found, using identity.\n";
            cfg.normalizer->add("action",
                Normalizer::create_identity(cfg.actor.action_dim));
        }

        if (n["cond"] && cfg.actor.cond_dim > 0) {
            auto cond_norm = load_single_normalizer(n["cond"]);
            if (cond_norm) cfg.normalizer->add("cond", cond_norm);
        }
    } else {
        // Fallback: identity normalizers
        cfg.normalizer->add("obs",
            Normalizer::create_identity(cfg.actor.obs_dim));
        cfg.normalizer->add("action",
            Normalizer::create_identity(cfg.actor.action_dim));
    }

    if (cfg.actor_type == "prdp") {
        if (!cfg.export_torch_version.empty()) {
            const std::string runtime = TORCH_VERSION;
            auto major_minor = [](const std::string& version) {
                const auto first = version.find('.');
                const auto second = first == std::string::npos
                    ? std::string::npos : version.find('.', first + 1);
                return second == std::string::npos ? version : version.substr(0, second);
            };
            if (major_minor(cfg.export_torch_version) != major_minor(runtime)) {
                std::cerr
                    << "[config_parser] Warning: PRDP export/runtime PyTorch mismatch: export="
                    << cfg.export_torch_version << " runtime=" << runtime
                    << ". Continuing; validate numerical parity before deployment.\n";
            }
        }
        if (cfg.obs_profile != ObsProfile::G1 || cfg.actor.obs_dim != 192)
            throw std::runtime_error("config_parser: PRDP requires obs_profile=G1 and obs_dim=192");
        const std::string& dp = cfg.joint_actor.data_profile;
        const bool standard2 = dp == "g1_prdp_standard2";
        const std::string expected_profile = standard2
            ? "g1_prdp_standard2" : "prdp_rlobs";
        const int expected_robot_dim = standard2 ? 93 : 96;
        if (cfg.runner.condition_profile != expected_profile
            || cfg.runner.rlobs_cond_dim != expected_robot_dim
            || cfg.joint_actor.n_cond_steps != 4)
            throw std::runtime_error(
                "config_parser: PRDP condition profile/dimension mismatch for data_profile='" +
                dp + "'");
        const int expected = expected_robot_dim + cfg.runner.text_cond_dim;
        if (cfg.joint_actor.backbone_cond_dim != expected)
            throw std::runtime_error("config_parser: PRDP backbone condition dimension mismatch");
        if (cfg.normalizer->has("cond")
            && cfg.normalizer->get("cond")->dim() != expected)
            throw std::runtime_error(
                "config_parser: PRDP condition normalizer dimension mismatch");
        if (cfg.runner.text_cond_dim != 0 && cfg.runner.text_cond_dim != 512)
            throw std::runtime_error("config_parser: PRDP text condition must be 0 or 512 dimensions");
        // data_profile ↔ condition-dimension cross-check (provenance, not
        // ignored): g1_prdp_standard = 96-D RL obs only; g1_prdp_standard_cond
        // = 96-D RL obs + 512-D text = 608-D backbone cond.  Some training
        // configs label a 608-D checkpoint with the 'g1_prdp_standard' string,
        // so a mismatch is a loud WARNING (surfaced, not silently ignored) but
        // not a hard error — the authoritative cond dim is backbone_cond_dim.
        {
            auto warn = [&](const std::string& msg) {
                std::cerr << "[config_parser] Warning: " << msg << "\n";
            };
            if (dp == "g1_prdp_standard"
                && (cfg.runner.text_cond_dim != 0
                    || cfg.joint_actor.backbone_cond_dim != 96)) {
                warn("data_profile='g1_prdp_standard' but text_cond_dim=" +
                     std::to_string(cfg.runner.text_cond_dim) + ", cond_dim=" +
                     std::to_string(cfg.joint_actor.backbone_cond_dim) +
                     "; authoritative cond dim is backbone_cond_dim");
            }
            if (dp == "g1_prdp_standard_cond"
                && (cfg.runner.text_cond_dim != 512
                    || cfg.joint_actor.backbone_cond_dim != 608)) {
                warn("data_profile='g1_prdp_standard_cond' but text_cond_dim=" +
                     std::to_string(cfg.runner.text_cond_dim) + ", cond_dim=" +
                     std::to_string(cfg.joint_actor.backbone_cond_dim) +
                     "; authoritative cond dim is backbone_cond_dim");
            }
            if (dp == "g1_prdp_standard2"
                && (cfg.runner.condition_profile != "g1_prdp_standard2"
                    || cfg.runner.rlobs_cond_dim != 93
                    || cfg.runner.text_cond_dim != 512
                    || cfg.joint_actor.backbone_cond_dim != 605)) {
                throw std::runtime_error(
                    "config_parser: g1_prdp_standard2 requires condition_profile="
                    "g1_prdp_standard2, robot_cond_dim=93, text_cond_dim=512, "
                    "and backbone cond_dim=605");
            }
        }
        const std::string& sm = cfg.cloc_actor.sampler_mode;
        const bool valid_mode =
            sm == "rolling_ddpm" || sm == "scalar_ddim" || sm == "ns_ddim"
            || sm == "rolling_ddim";
        if (!valid_mode)
            throw std::runtime_error(
                "config_parser: unsupported PRDP sampler_mode '" + sm +
                "'; use rolling_ddpm, scalar_ddim, ns_ddim, or rolling_ddim");
        if (cfg.cloc_actor.classifier_guidance_impl != "duplicate_backbone"
            && cfg.cloc_actor.classifier_guidance_impl != "reuse_x0")
            throw std::runtime_error(
                "config_parser: model.classifier_guidance_impl must be "
                "duplicate_backbone or reuse_x0");
        if ((sm == "rolling_ddpm") != (cfg.cloc_actor.ddim_steps == 0)) {
            throw std::runtime_error(
                "config_parser: PRDP sampler_mode/ddim_steps mismatch: "
                "use sampler_mode=rolling_ddpm with ddim_steps=0, or "
                "sampler_mode=scalar_ddim|ns_ddim|rolling_ddim with ddim_steps>0");
        }
        if (cfg.cloc_actor.ddim_precompute && sm != "scalar_ddim" && sm != "ns_ddim")
            throw std::runtime_error(
                "config_parser: ddim_precompute currently requires "
                "sampler_mode=scalar_ddim or ns_ddim");
        if (sm == "ns_ddim" && !cfg.cloc_actor.use_ns_ddim)
            throw std::runtime_error(
                "config_parser: sampler_mode=ns_ddim requires use_ns_ddim: true");
        if (sm == "rolling_ddim" && !cfg.cloc_actor.randomize_noise_schedule)
            throw std::runtime_error(
                "config_parser: sampler_mode=rolling_ddim requires "
                "randomize_noise_schedule: true");
        if (cfg.cloc_actor.guidance.enabled) {
            if (cfg.cloc_actor.guidance.axis_gradient_impl != "sequential"
                && cfg.cloc_actor.guidance.axis_gradient_impl != "stacked")
                throw std::runtime_error(
                    "config_parser: whole_body_guidance.axis_gradient_impl "
                    "must be sequential or stacked");
            // Whole-body guidance is supported on every sampler mode. The
            // gradient path is sampler-independent: it needs only the 192-D FK
            // profile and per-step state timesteps (zeta is integrated across
            // each DDIM jump in the DDIM paths).
            //
            // The FK requirement is an observation-*quality* concern only:
            // WholeBodyGuidance consumes the g1_standard obs layout directly
            // (kBodyPos=0, kBodyVel=90, kRootPos=180, ...) and never calls FK.
            // G1ForwardKinematics merely upgrades the env's cheap
            // build_body_pos/build_body_lin_vel approximations.  With
            // no_state_override=true (the documented FK-free deploy path) the
            // state stream is denoised from the condition without nobs
            // inpainting, so no privilege state is needed and FK is not
            // required.  Only the FK path (no_state_override=false) must
            // require env.use_fk + a URDF.
            if (!cfg.cloc_actor.no_state_override
                && (!cfg.env.use_fk || cfg.env.urdf_path.empty()))
                throw std::runtime_error(
                    "config_parser: PRDP whole-body guidance requires "
                    "env.use_fk=true and a non-empty env.urdf_path when "
                    "model.no_state_override=false");
            if (std::fabs(cfg.cloc_actor.guidance.dt
                          - static_cast<float>(cfg.env.control_dt)) > 1e-5f)
                throw std::runtime_error(
                    "config_parser: PRDP whole-body guidance dt must equal "
                    "env.control_dt");
        }
    }

    return cfg;
}

}  // namespace diffusion_deploy
