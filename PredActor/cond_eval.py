"""
Conditional DiffuseCLoC evaluation script with Hydra-based unified EnvRunner configuration.

This script uses a single `env_runner` section in config files (e.g., g1_cond_diffuse.yaml),
with one runner implementation orchestrating env/composer/agent interaction.
Different environments are selected by changing the nested `env` target in `env_runner`.

Usage:
    # Launch the public release with its default artifacts and Web UI
    predactor-eval

    # Use an absolute path (e.g. a wandb config.yaml or a saved checkpoint config)
    python cond_eval.py --checkpoint checkpoints/20260130_run/latest.ckpt \\
        --config /abs/path/to/config.yaml -o eval_output

    # Evaluate with specific device
    python cond_eval.py --checkpoint outputs/latest.ckpt --config g1_cond_diffuse.yaml -o eval_output \\
        --device cuda:0 --headless

    # Evaluate a DAgger checkpoint with the canonical evaluation profile.
    # The profile controls runtime behavior; checkpoint weights and fitted
    # normalizers are restored strictly through the embedded DAgger loader.
    python cond_eval.py --checkpoint outputs/dagger_run/checkpoints/latest.ckpt \\
        --config g1prdp_diffuse.yaml -o eval_output/dagger \\
        --device cuda:0

    # Open the local Web UI, then enter a world-frame destination under
    # Whole-body guidance -> Destination follow.
    python cond_eval.py --checkpoint outputs/dagger_run/checkpoints/latest.ckpt \\
        --config g1prdp_cond_diffuse.yaml -o eval_output/destination --web-ui

    # Native CustomTkinter WBG UI (includes the Destination Follow tab).
    # Keep --no-headless when running on a workstation with a display.
    python cond_eval.py --checkpoint outputs/dagger_run/checkpoints/latest.ckpt \\
        --config g1prdp_cond_diffuse.yaml -o eval_output/destination --no-headless
"""

import sys

# Keep CLI output line-buffered without replacing/closing pytest or notebook
# capture streams.  Re-opening their file descriptors breaks test capture and
# can make a clean config load look like an interrupted parse.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(line_buffering=True)
    except (AttributeError, OSError):
        pass

import os
import pathlib
from pathlib import Path
import click
import torch
import json
from omegaconf import OmegaConf
import hydra

from diffusion_policy import DIFFUSION_POLICY_ROOT
from diffusion_policy.trainer.base_trainer import BaseTrainer
from diffusion_policy.utils.config_loader import (
    load_config,
    is_wandb_config,
    unwrap_wandb_config,
)
from diffusion_policy.task_provider import (
    TaskCondProvider,
    ClipCondProvider,
    CompositeCondProvider,
)
from diffusion_policy.task_provider.clip_proposition import terms_from_pairs


EVALUATOR_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = EVALUATOR_ROOT.parent
DEFAULT_ARTIFACTS_ROOT = REPOSITORY_ROOT / 'Artifacts'
DEFAULT_CHECKPOINT = DEFAULT_ARTIFACTS_ROOT / 'checkpoints' / 'predactor' / 'pdp051' / 'latest.ckpt'
DEFAULT_TEXT_CHECKPOINT = (
    DEFAULT_ARTIFACTS_ROOT / 'checkpoints' / 'motionclip' / 'g1-model-xyz-clip' / 'checkpoint_0100.pth.tar')
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / 'eval_output' / 'web'
DEFAULT_CONFIG = 'g1prdp_cond_diffuse.yaml'
DEFAULT_DEVICE = 'cuda:0' if torch.cuda.is_available() else 'cpu'


def _is_dagger_checkpoint(payload):
    checkpoint_cfg = payload.get('cfg')
    if checkpoint_cfg is None:
        return False
    target = OmegaConf.select(checkpoint_cfg, '_target_', default='')
    # Match the DaggerTrainer family, including the dual-variant subclass
    # (``DualVariantDaggerTrainer`` does not end with the dotted form).
    return str(target).endswith('DaggerTrainer')


def _load_eval_agent(checkpoint, payload, cfg, device, checkpoint_replica='agent'):
    """Load standard checkpoints normally and DAgger checkpoints strictly."""
    if _is_dagger_checkpoint(payload):
        if checkpoint_replica != 'agent':
            raise ValueError('DAgger evaluation supports only the primary agent replica')
        checkpoint_cfg = payload['cfg']
        checkpoint_actor = OmegaConf.select(
            checkpoint_cfg, 'policy.actor._target_', default=None)
        eval_actor = OmegaConf.select(cfg, 'policy.actor._target_', default=None)
        if checkpoint_actor != eval_actor:
            raise ValueError(
                'DAgger checkpoint/config actor mismatch: '
                f'{checkpoint_actor!r} != {eval_actor!r}')

        print(
            'Detected DAgger checkpoint; using evaluation actor config with '
            'strict checkpoint state loading')
        from dagger.rollout import load_student_agent
        return load_student_agent(checkpoint, device, actor_config=cfg.policy.actor)

    if checkpoint_replica not in {'agent', 'ema_agent'}:
        raise ValueError(f'Unsupported checkpoint replica: {checkpoint_replica}')
    if checkpoint_replica not in payload.get('state_dicts', {}):
        raise ValueError(f'Checkpoint has no {checkpoint_replica!r} replica')
    # Load either replica into one actor, avoiding deepcopy of GUI-bearing WBG.
    payload = dict(payload)
    payload['state_dicts'] = dict(payload['state_dicts'])
    payload['state_dicts']['agent'] = payload['state_dicts'][checkpoint_replica]
    trainer_cfg = OmegaConf.create(OmegaConf.to_container(cfg, resolve=True))
    trainer_cfg.training.use_ema = False
    cls = hydra.utils.get_class(trainer_cfg._target_)
    trainer: BaseTrainer = cls(trainer_cfg, init_wandb=False)
    exclude_keys = tuple(
        key for key in payload.get('state_dicts', {})
        if getattr(trainer, key, None) is None
    )
    if exclude_keys:
        print(
            f'cond_eval evaluates {checkpoint_replica}; skipping unused '
            f'checkpoint replicas: {list(exclude_keys)}.')
    trainer.load_payload(
        payload, exclude_keys=exclude_keys, include_keys=None)
    bc_agent = trainer.agent
    bc_agent.to(device)
    bc_agent.eval()
    return bc_agent


def _sampler_runtime_summary(agent):
    """Describe the sampler that the loaded actor will execute."""
    actor = getattr(agent, 'actor', None)
    if actor is None:
        return None
    schedule_steps = int(getattr(actor, 'denoising_steps', 0) or 0)
    ddim_steps = getattr(actor, 'ddim_steps', None)
    if ddim_steps is None:
        family = 'DDPM'
        executed_steps = schedule_steps
    else:
        family = 'NS-DDIM' if bool(getattr(actor, 'use_ns_ddim', False)) else 'DDIM'
        executed_steps = int(ddim_steps)
    return {
        'family': family,
        'executed_steps': executed_steps,
        'schedule_steps': schedule_steps,
        'eta': float(getattr(actor, 'ddim_eta', 0.0) or 0.0),
        'randomize_noise_schedule': bool(getattr(actor, 'randomize_noise_schedule', False)),
    }


def _web_interpolation_terms(providers_cfg):
    """Resolve the Web UI proposition defaults from the configured CLIPInterp block."""
    interp_cfg = (providers_cfg or {}).get('clip_interp', {})
    pairs = interp_cfg.get('text_pairs') or []
    return terms_from_pairs(pairs)


def _configure_web_interpolation(provider, terms):
    """Install configured proposition terms on whichever CLIP provider is active."""
    if not terms or provider is None:
        return False
    sources = getattr(provider, '_providers', [provider])
    for source in sources:
        source = getattr(source, '_clip_source', source)
        configure = getattr(source, 'set_interpolation_terms', None)
        if callable(configure):
            configure(terms)
            return True
    return False


def _apply_runtime_overrides(cfg, runner_cfg, device=None, headless=None, fk_device=None):
    """Apply CLI runtime overrides to every component that consumes them.

    ``--device`` historically changed only ``env_runner.device``.  That left
    IsaacLab and CLIP providers on the YAML defaults (usually ``cuda:0``),
    which made a CPU invocation look as if the config had not been parsed and
    could fail later during environment/provider construction.  Keep the
    checkpoint/model config intact, but make the copied runtime config
    internally consistent before it is printed or instantiated.
    """
    if device:
        runner_cfg.device = device
        if OmegaConf.select(cfg, 'training.device', default=None) is not None:
            OmegaConf.update(cfg, 'training.device', device)

        env_cfg = OmegaConf.select(runner_cfg, 'env.config', default=None)
        if env_cfg is not None:
            for key in ('device', 'fk_device'):
                if OmegaConf.select(env_cfg, key, default=None) is not None:
                    OmegaConf.update(env_cfg, key, device)

        providers_cfg = OmegaConf.select(runner_cfg, 'task_cond_providers', default=None)
        if providers_cfg is not None:
            for provider_cfg in providers_cfg.values():
                if OmegaConf.select(provider_cfg, 'device', default=None) is not None:
                    OmegaConf.update(provider_cfg, 'device', device)

    if fk_device is not None:
        env_cfg = OmegaConf.select(runner_cfg, 'env.config', default=None)
        if env_cfg is None or OmegaConf.select(env_cfg, 'fk_device', default=None) is None:
            raise ValueError('--fk-device requires an environment with an FK device setting')
        OmegaConf.update(env_cfg, 'fk_device', fk_device)

    if headless is not None:
        env_cfg = OmegaConf.select(runner_cfg, 'env.config', default=None)
        if env_cfg is not None and OmegaConf.select(env_cfg, 'headless', default=None) is not None:
            OmegaConf.update(env_cfg, 'headless', bool(headless))

        if headless:
            # These components may start GUI threads during policy/provider
            # construction, so disable them before _load_eval_agent().
            wbg_gui_path = 'policy.actor.whole_body_guidance_config.gui.enabled'
            if OmegaConf.select(cfg, wbg_gui_path, default=None) is not None:
                OmegaConf.update(cfg, wbg_gui_path, False)

            providers_cfg = OmegaConf.select(runner_cfg, 'task_cond_providers', default=None)
            if providers_cfg is not None:
                for provider_cfg in providers_cfg.values():
                    target = str(OmegaConf.select(provider_cfg, '_target_', default=''))
                    if target.endswith(('CLIPInterp', 'MoRefTeleop', 'JoyTextWBG')):
                        OmegaConf.update(provider_cfg, 'gui_enabled', False, force_add=True)
                    if target.endswith('CLIPTeleop'):
                        OmegaConf.update(provider_cfg, 'interactive_input', False, force_add=True)


@click.command()
@click.option('-c', '--checkpoint', default=str(DEFAULT_CHECKPOINT), show_default=True,
              help='Path to checkpoint file')
@click.option(
    '--config', default=DEFAULT_CONFIG, show_default=True,
    help=(
        'Evaluation/runtime config with env_runner configuration '
        '(e.g., g1prdp_diffuse.yaml). DAgger weights and normalizers still '
        'come from the checkpoint.'
    ),
)
@click.option('-o', '--output_dir', default=str(DEFAULT_OUTPUT_DIR), show_default=True,
              help='Output directory for results')
@click.option('-d', '--device', default=DEFAULT_DEVICE, show_default=True,
              help='Device for inference')
@click.option(
    '--fk-device', default=None,
    help='Optional FK-only device override; policy inference remains on --device.',
)
@click.option('--checkpoint-replica', type=click.Choice(['agent', 'ema_agent']),
              default='agent', show_default=True, help='Checkpoint weights used for inference.')
@click.option(
    '--headless/--no-headless', default=None,
    help=(
        'Override the environment viewer and interactive guidance GUIs. '
        'Use --headless for CPU/server evaluation.'
    ),
)
@click.option('--precision', type=click.Choice(['fp32', 'fp16']), default=None,
              help='Inference precision. Default: training.precision from config, else fp32.')
@click.option('--web-ui/--no-web-ui', default=True, show_default=True,
              help='Serve the responsive local MuJoCo evaluation interface.')
@click.option('--web-host', default='127.0.0.1', show_default=True, help='Web UI bind host.')
@click.option('--web-port', default=8765, type=click.IntRange(1024, 65535), show_default=True, help='Web UI port.')
@click.option('--web-no-browser', is_flag=True, help='Do not open the web UI automatically.')
@click.option('--web-joystick-device', default='auto', show_default=True, help='Linux joystick device or auto.')
@click.option('--web-joystick-type', default='xbox_new', show_default=True, help='Canonical joystick mapping.')
@click.option('--web-perturb/--no-web-perturb', default=False, show_default=True,
              help='Enable local MuJoCo body perturbation in the web viewport.')
@click.option('--web-perturb-max-force', default=120.0, type=click.FloatRange(min=1e-6), show_default=True)
@click.option('--web-perturb-max-torque', default=30.0, type=click.FloatRange(min=1e-6), show_default=True)
@click.option('--camera-follow/--no-camera-follow', default=None,
              help='Override MuJoCo pelvis/body camera tracking.')
@click.option('--camera-follow-body', default=None, help='MuJoCo body name to follow (G1: pelvis).')
@click.option('--camera-follow-yaw/--camera-world-heading', default=None,
              help='Follow body yaw or retain a world-fixed camera heading.')
@click.option('--camera-smoothing-tau', type=click.FloatRange(min=0.0), default=None,
              help='Camera damping time constant in seconds; 0 disables damping.')
@click.option('--camera-lookat-offset', type=(float, float, float), default=None,
              help='Camera look-at offset X Y Z relative to the followed body.')
def main(checkpoint, config, output_dir, device, fk_device, checkpoint_replica, headless, precision, web_ui, web_host, web_port,
         web_no_browser, web_joystick_device, web_joystick_type, web_perturb,
         web_perturb_max_force, web_perturb_max_torque, camera_follow, camera_follow_body,
         camera_follow_yaw, camera_smoothing_tau, camera_lookat_offset):
    """
    Evaluate a trained conditional DiffuseCLoC policy with Hydra-configured runner.
    
    This script uses the env_runner configuration section from the config file.
    The section instantiates the unified EnvRunner with a nested environment target.
    - CLIP teleop for interactive text conditioning
    - CLIP interp for semantic interpolation conditioning
    - Easy configuration of evaluation settings via config file
    """
    
    # Release-relative defaults remove environment setup from the public CLI.
    # Explicit environment values still win for development and custom layouts.
    os.environ.setdefault('PREDACTOR_ROOT', str(EVALUATOR_ROOT))
    os.environ.setdefault('PREDACTOR_TEXT_CHECKPOINT', str(DEFAULT_TEXT_CHECKPOINT))

    # Create output directory
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load checkpoint
    print(f"Loading checkpoint: {checkpoint}")
    payload = torch.load(checkpoint, map_location='cpu', weights_only=False)

    # Load configuration from file
    print(f"Loading configuration from file: {config}")

    # If config has no directory component, look it up in config_files/
    config_path = Path(config)
    if config_path.parent == Path('.'):
        config_path = Path(DIFFUSION_POLICY_ROOT) / 'config_files' / config
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw_cfg = OmegaConf.load(config_path)
    if is_wandb_config(raw_cfg):
        # Wandb config.yaml: value-wrapped, fully resolved — unwrap directly.
        print("  (detected wandb config format — unwrapping values)")
        cfg = unwrap_wandb_config(raw_cfg)
        OmegaConf.resolve(cfg)
    else:
        # Normal config file: may use Hydra-style defaults composition.
        print("  (detected standard config format — composing defaults)")
        cfg = load_config(config_path)
        OmegaConf.resolve(cfg)

    # Web mode owns every interactive source. Disable legacy windows before
    # constructing the policy/provider so no Tk, stdin or MuJoCo viewer races it.
    if web_ui:
        if OmegaConf.select(cfg, 'policy.actor.whole_body_guidance_config.gui') is not None:
            cfg.policy.actor.whole_body_guidance_config.gui.enabled = False
        if OmegaConf.select(cfg, 'env_runner.env.config.enable_viewer') is not None:
            cfg.env_runner.env.config.enable_viewer = False

    camera_overrides = {
        'camera_follow': camera_follow,
        'camera_follow_body': camera_follow_body,
        'camera_follow_yaw': camera_follow_yaw,
        'camera_smoothing_tau': camera_smoothing_tau,
        'camera_lookat_offset': list(camera_lookat_offset) if camera_lookat_offset is not None else None,
    }
    for key, value in camera_overrides.items():
        if value is not None:
            OmegaConf.update(cfg, f'env_runner.env.config.{key}', value, force_add=True)
    
    # Select env_runner configuration
    runner = 'env_runner'
    if runner not in cfg:
        raise ValueError(
            f"Config file {config} does not contain '{runner}' section. "
            f"Available sections: {list(cfg.keys())}"
        )
    
    # Work on a runtime copy.  Apply overrides before printing and before
    # constructing the policy/provider so all nested devices and GUI sources
    # agree with the CLI invocation.
    runner_cfg = OmegaConf.create(cfg[runner])
    _apply_runtime_overrides(
        cfg, runner_cfg, device=device, headless=headless, fk_device=fk_device)
    print(f"\nUsing runner configuration: {runner}")
    print(OmegaConf.to_yaml(runner_cfg))

    print("\nInitializing checkpoint-compatible policy...")
    bc_agent = _load_eval_agent(checkpoint, payload, cfg, device, checkpoint_replica)
    from diffusion_policy.utils.precision import normalize_precision, validate_precision_device
    if precision is None:
        precision = OmegaConf.select(cfg, 'training.precision', default='fp32')
    precision = normalize_precision(precision)
    validate_precision_device(precision, device)
    bc_agent.set_inference_precision(precision)
    if 'training' not in cfg:
        cfg.training = OmegaConf.create({})
    cfg.training.precision = precision
    
    print(f"BCAgent loaded and moved to {device} (precision={precision})")
    print(f"Policy type: {type(bc_agent.actor).__name__}")
    sampler = _sampler_runtime_summary(bc_agent)
    if sampler is not None:
        print(
            'Sampler runtime: '
            f"{sampler['family']}-{sampler['executed_steps']} "
            f"(executed denoising iterations={sampler['executed_steps']}; "
            f"training noise schedule levels={sampler['schedule_steps']}; "
            f"eta={sampler['eta']}; "
            f"randomize_noise_schedule={sampler['randomize_noise_schedule']})")

    # Instantiate eval_runner from config using Hydra
    print("\nInstantiating evaluation runner from config...")
    
    # Override output directory on the already-resolved runtime copy.
    runner_cfg.output_dir = output_dir

    # Instantiate task condition providers from task_cond_providers dict.
    # Each entry with enabled=true is instantiated and combined.
    task_cond_provider = None
    web_interp_terms = []
    if 'task_cond_providers' in runner_cfg:
        providers_cfg = OmegaConf.to_container(runner_cfg.task_cond_providers, resolve=True)
        if web_ui:
            web_interp_terms = _web_interpolation_terms(providers_cfg)
        active_providers = []
        for name, pcfg in providers_cfg.items():
            if not pcfg.get('enabled', False):
                continue
            pcfg = {k: v for k, v in pcfg.items() if k != 'enabled'}
            target = str(pcfg.get('_target_', ''))
            if web_ui and target.endswith('.CLIPTeleop'):
                pcfg['interactive_input'] = False
                precache = list(pcfg.get('precache_texts') or ())
                for text in ('stand', 'walk', 'jog', 'squat down'):
                    if text not in precache:
                        precache.append(text)
                pcfg['precache_texts'] = precache
            if web_ui and target.endswith('.CLIPInterp'):
                pcfg['gui_enabled'] = False
            print(f"  Instantiating task cond provider: {name}  (_target_={pcfg.get('_target_', '?')})")
            instance = hydra.utils.instantiate(OmegaConf.create(pcfg))
            # TaskCondProvider subclasses (e.g. MoRefTeleop) are used directly;
            # raw CLIP objects (CLIPTeleop, CLIPInterp) need a ClipCondProvider wrapper.
            if isinstance(instance, TaskCondProvider):
                active_providers.append(instance)
            else:
                active_providers.append(ClipCondProvider(instance))
        if len(active_providers) == 1:
            task_cond_provider = active_providers[0]
        elif len(active_providers) > 1:
            task_cond_provider = CompositeCondProvider(active_providers)
        if web_ui:
            _configure_web_interpolation(task_cond_provider, web_interp_terms)
        runner_cfg = OmegaConf.masked_copy(
            runner_cfg,
            [k for k in runner_cfg if k != 'task_cond_providers']
        )

    # Remove legacy cond_type key if still present in older configs
    if 'cond_type' in runner_cfg:
        runner_cfg = OmegaConf.masked_copy(
            runner_cfg, [k for k in runner_cfg if k != 'cond_type']
        )
    # Remove legacy flat clip_teleop / clip_interp / moref_teleop keys if present
    legacy_keys = ['clip_teleop', 'clip_interp', 'moref_teleop']
    present_legacy = [k for k in legacy_keys if k in runner_cfg]
    if present_legacy:
        runner_cfg = OmegaConf.masked_copy(
            runner_cfg, [k for k in runner_cfg if k not in legacy_keys]
        )

    runtime_observer = None
    if web_ui:
        from diffusion_policy.utils.joystick_parser import VelocityJoystick
        from diffusion_policy.web_ui import EvaluationWebSession, WebCameraConfig
        joystick = VelocityJoystick(device=web_joystick_device, joystick_type=web_joystick_type)
        lookat_offset = list(OmegaConf.select(
            runner_cfg, 'env.config.camera_lookat_offset', default=[0.0, 0.0, 0.0]))
        lookat_offset[2] += float(OmegaConf.select(
            runner_cfg, 'env.config.camera_lookat_height_offset', default=0.04))
        web_camera_config = WebCameraConfig(
            enabled=OmegaConf.select(runner_cfg, 'env.config.camera_follow', default=True),
            body_name=OmegaConf.select(runner_cfg, 'env.config.camera_follow_body', default='pelvis'),
            follow_yaw=OmegaConf.select(runner_cfg, 'env.config.camera_follow_yaw', default=False),
            lookat_offset=tuple(lookat_offset),
            smoothing_tau=OmegaConf.select(runner_cfg, 'env.config.camera_smoothing_tau', default=0.15),
        )
        runtime_observer = EvaluationWebSession(
            provider=task_cond_provider, host=web_host, port=web_port,
            open_browser=not web_no_browser, joystick=joystick,
            perturb_enabled=web_perturb, perturb_max_force=web_perturb_max_force,
            perturb_max_torque=web_perturb_max_torque, camera_config=web_camera_config)
        runtime_observer.launch()

    # Instantiate runner using Hydra
    env_runner = hydra.utils.instantiate(
        runner_cfg, task_cond_provider=task_cond_provider,
        runtime_observer=runtime_observer)
    
    print(f"Runner type: {type(env_runner).__name__}")

    # Report active task condition providers
    tcp = env_runner.task_cond_provider
    if tcp is None:
        print("Task Cond Provider: NONE (unconditional)")
    elif isinstance(tcp, CompositeCondProvider):
        print(f"Task Cond Provider: CompositeCondProvider ({len(tcp._providers)} providers)")
        for p in tcp._providers:
            print(f"  - {type(p).__name__}")
    else:
        print(f"Task Cond Provider: {type(tcp).__name__}")

    # Run evaluation with BCAgent
    print(f"\nStarting evaluation...")
    
    # Print runner-specific info (handle different runner types)
    if hasattr(env_runner, 'task_name'):
        print(f"  Task: {env_runner.task_name}")
    if hasattr(env_runner, 'n_envs'):
        print(f"  Num envs: {env_runner.n_envs}")
    print(f"  Max steps: {env_runner.max_steps}")
    if hasattr(env_runner, 'headless'):
        print(f"  Headless: {env_runner.headless}")
    print(f"  Normalization: {'Enabled' if hasattr(bc_agent, 'normalizer') else 'Disabled'}")

    results = env_runner.run(bc_agent, cfg)
    if results is None:
        print("Evaluation did not produce results (error occurred). Exiting.")
        sys.exit(1)

    # Save results to JSON
    output_file = os.path.join(output_dir, 'eval_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, sort_keys=True)
    
    print(f"\nResults saved to: {output_file}")

    # Save configuration used for evaluation
    config_output_file = os.path.join(output_dir, 'eval_config.yaml')
    with open(config_output_file, 'w') as f:
        OmegaConf.save(cfg, f)
    print(f"Config saved to: {config_output_file}")

    # Save summary
    summary_file = os.path.join(output_dir, 'eval_summary.txt')
    with open(summary_file, 'w') as f:
        f.write(f"Conditional DiffuseCLoC Evaluation Summary\n")
        f.write(f"=========================================\n\n")
        f.write(f"Checkpoint: {checkpoint}\n")
        f.write(f"Config: {config}\n")
        f.write(f"Precision: {precision}\n")
        f.write(f"Runner: {type(env_runner).__name__}\n")
        
        # Write runner-specific info (handle different runner types)
        if hasattr(env_runner, 'task_name'):
            f.write(f"Task: {env_runner.task_name}\n")
        if hasattr(env_runner, 'n_envs'):
            f.write(f"Num Envs: {env_runner.n_envs}\n")
        f.write(f"Max Steps: {env_runner.max_steps}\n")
        
        tcp = env_runner.task_cond_provider
        if tcp is None:
            f.write(f"Task Cond Provider: NONE\n")
        elif isinstance(tcp, CompositeCondProvider):
            f.write(f"Task Cond Provider: CompositeCondProvider\n")
            for p in tcp._providers:
                f.write(f"  - {type(p).__name__}\n")
        else:
            f.write(f"Task Cond Provider: {type(tcp).__name__}\n")
        
        f.write(f"\nResults:\n")
        # Handle different result formats from different runners
        if 'num_episodes' in results:
            f.write(f"  Episodes: {results['num_episodes']}\n")
            f.write(f"  Mean Reward: {results['mean_episode_reward']:.2f} ± {results['std_episode_reward']:.2f}\n")
            f.write(f"  Mean Length: {results['mean_episode_length']:.1f}\n")
        else:
            # Unitree runner or other format
            for key, value in results.items():
                f.write(f"  {key}: {value}\n")
    
    print(f"Summary saved to: {summary_file}")


if __name__ == '__main__':
    main()
