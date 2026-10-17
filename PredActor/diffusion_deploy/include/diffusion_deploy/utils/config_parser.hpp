/**
 * config_parser.hpp
 *
 * YAML configuration parser for g1_deploy_config.yaml.
 * Produces ActorConfig, UnitreeEnvConfig, EnvRunnerConfig, and
 * MultiNormalizer from a single YAML file.
 */
#pragma once

#include "diffusion_deploy/actor/base_actor.hpp"
#include "diffusion_deploy/actor/diffusion_actor.hpp"
#include "diffusion_deploy/actor/joint_diffusion_actor.hpp"
#include "diffusion_deploy/actor/diffuse_cloc_actor.hpp"
#include "diffusion_deploy/env/unitree_env.hpp"
#include "diffusion_deploy/obs/obs_composer.hpp"
#include "diffusion_deploy/runner/env_runner.hpp"
#include "diffusion_deploy/utils/normalizer.hpp"

#include <memory>
#include <string>

namespace diffusion_deploy {

/**
 * Parsed configuration from YAML file.
 */
struct DeployConfig {
    // model section
    std::string     model_backend   = "torch";  // "torch" or "onnx"
    std::string     actor_type      = "torch";  // "torch"|"diffusion"|"joint_diffusion"|"diffuse_cloc"
    std::string     model_path;                 // backbone .pt path
    std::string     schedule_path;              // ddpm_schedule.pt path
    std::string     export_torch_version;       // producer PyTorch version
    std::string     model_precision = "fp32";  // fp32|fp16 learned backbone

    // resources section (portable export contract)
    int             resource_schema_version = 0;
    std::string     resource_manifest_path;
    std::string     resource_checksum_path;
    std::string     conditioning_mode = "legacy";
    ActorConfig     actor;
    DiffusionActorConfig    diffusion_actor;
    JointDiffusionActorConfig joint_actor;
    DiffuseCLoCActorConfig  cloc_actor;
    ObsProfile      obs_profile     = ObsProfile::G1;

    // env section
    UnitreeEnvConfig env;

    // runner section
    EnvRunnerConfig runner;

    // normalizer section
    std::shared_ptr<MultiNormalizer> normalizer;
};

struct DeployConfigOverrides {
    // Applied before cross-field/resource validation so CLI opt-in has the
    // same typed contract as runner.unified_command.enabled in YAML.
    bool enable_unified_command = false;
    std::string unified_command_source;
    std::string unified_command_device;
    std::string unified_command_mapping;
};

/**
 * Load DeployConfig from a YAML file.
 * Throws std::runtime_error on missing required fields.
 *
 * Expected YAML structure:
 *   model:
 *     backend: "torch"
 *     path: "models/g1_policy.pt"
 *     obs_dim: 192
 *     action_dim: 29
 *     cond_dim: 0
 *     n_obs_steps: 4
 *     n_future_steps: 16
 *     denoising_steps: 100
 *     obs_profile: "G1"
 *   env:
 *     network_interface: "eth0"
 *     control_dt: 0.02
 *     num_dof: 29
 *     Kp: [...]
 *     Kd: [...]
   *   runner:
   *     max_steps: 2000
 *     delay_action_step: 0
   *     realtime_mode: true
 *     reset_height: 0.3
 *   normalization:
 *     obs:
 *       mode: "linear"
 *       min: [...]
 *       max: [...]
 *     action:
 *       mode: "linear"
 *       min: [...]
 *       max: [...]
 *     cond:          # optional
 *       mode: "standard"
 *       mean: [...]
 *       std: [...]
 */
DeployConfig load_config(
    const std::string& yaml_path,
    const DeployConfigOverrides& overrides = {});

}  // namespace diffusion_deploy
