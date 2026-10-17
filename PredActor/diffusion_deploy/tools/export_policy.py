"""
export_policy.py
================
Export a trained Python checkpoint to files consumable by the C++ library.

Produces a SINGLE runtime config (the C++ deploy YAML) plus the model artifacts:

  models/g1_policy_backbone.pt       — TorchScript backbone network
  models/g1_policy_full_loop.pt      — TorchScript full-loop model (lazy, may fail)
  models/ddpm_schedule.pt            — DDPM schedule tensors for C++ actors
  models/deploy_config.yaml          — the ONE C++ runtime config (model+env+runner+normalization)

The C++ runtime reads ONLY the deploy YAML (run_g1_robot --config <deploy.yaml>);
the ``model:`` block is a superset of the actor hyper-parameters, and the
``normalization:`` block carries the exact normalizer stats the runtime needs.
For debugging, ``--write-actor-config`` additionally dumps ``actor_config.yaml``
(root key ``actor:``) and ``--write-normalizer-stats`` dumps
``normalizer_stats.yaml`` — neither is read at runtime.

Export modes
------------
backbone    Reliable: traces *only* the backbone network.
            C++ actors (DiffusionActor / JointDiffusionActor / DiffuseCLoCActor)
            implement the full DDPM loop in native C++. Recommended.

full_loop   Lazy: attempts torch.jit.trace / script of the entire Python loop.
            May fail for DiffuseCLoC / JointDiffusionActor due to abstract-type
            annotations and dynamic Python attributes. Kept as a fallback.

Usage
-----
  # Minimal PRDP export (defaults --config checkpoint; derives obs_profile /
  # use_fk / urdf_path from the embedded cfg and normalizer dims):
  python export_policy.py --checkpoint outputs/latest.ckpt --output models/prdp

  # Reliable backbone export with an explicit (mutable) training YAML override:
  python export_policy.py --checkpoint outputs/latest.ckpt \\
                          --config g1rlobs_cond_dp.yaml \\
                          --output models/ --mode backbone

  # Lazy full-loop export
  python export_policy.py --checkpoint outputs/latest.ckpt \\
                          --config g1_cond_diffuse.yaml \\
                          --output models/ --mode full_loop

  # Dry-run: just print normalizer stats
  python export_policy.py --checkpoint outputs/latest.ckpt \\
                          --config g1_cond_diffuse.yaml \\
                          --output models/ --stats-only

  # PRDP exports DEFAULT to WBG-enabled: when the checkpoint's embedded cfg has
  # no enabled whole_body_guidance_config (absent, or all guides disabled — the
  # default training state) and --wbg-config is not given, the exporter injects
  # the validated classifier vx=0.3 WBG block so the generated deploy config
  # carries model.whole_body_guidance and --wbg-udp takes effect. --wbg-config
  # still overrides with a custom config:
  python export_policy.py --checkpoint outputs/latest.ckpt \\
                          --output models/prdp \\
                          --wbg-config /path/to/wbg_config.yaml

  # Interactive config editor (--gui, headless is the default): pre-loads the
  # editor from the GIVEN Python config, GUI edits override the extracted
  # defaults, then exports normally. Requires a display (customtkinter).
  python export_policy.py --checkpoint outputs/latest.ckpt \\
                          --config g1prdp_cond_diffuse.yaml \\
                          --output models/prdp --mode backbone --gui \\
                          --write-wbg-config models/edited_wbg.yaml
"""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)

import contextlib
import hashlib
import math
import os
import pathlib
import click
import torch
import yaml
import numpy as np
from omegaconf import OmegaConf

from diffusion_policy import DIFFUSION_POLICY_ROOT
from diffusion_policy.trainer.base_trainer import BaseTrainer
from diffusion_policy.utils.config_loader import load_config

# Ensure the PDPlanner repo root is on sys.path so `diffusion_deploy.*`
# resolves when this file is run directly (`python tools/export_policy.py`).
# `_DEPLOY_ROOT` is defined below; the bootstrap runs before it.
_DEPLOY_ROOT_BOOTSTRAP = pathlib.Path(__file__).resolve().parent.parent
_REPO_ROOT = _DEPLOY_ROOT_BOOTSTRAP.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from diffusion_deploy.tools.deploy_config_schema import (
    EditorDefaults,
    coerce_field,
    derive_sampler_mode,
    extract_actor_defaults,
    extract_wbg_defaults,
    merge_actor_override,
    merge_wbg_override,
    to_plain,
    validate_actor_overrides,
    wbg_to_deploy_block,
)
from diffusion_deploy.tools.export_resource_bundle import (
    CHECKSUM_NAME,
    MANIFEST_NAME,
    SCHEMA_VERSION,
    copy_runtime_resource,
    write_resource_manifest,
)
from diffusion_deploy.tools.torch21_compat import (
    TARGET as JETSON_JP5_TARGET,
    Torch21ConditionEmbeddingBackbone,
    assert_torch21_operators,
    lower_multihead_attention,
    parity_tolerances,
    write_compatibility_manifest,
)


# ---- Normalizer helpers ----

def _normalizer_stats_to_dict(normalizer, key):
    """Export scale/offset directly from a SingleFieldLinearNormalizer.

    Exporting the raw input_stats (min/max or mean/std) and re-deriving scale/offset
    in C++ is fragile because the Python normalizer may use either 'limits' or 'gaussian'
    mode, and the mode flag is not stored explicitly in a reliable way.  Instead we
    export the final scale and offset tensors that the normalizer actually uses, so the
    C++ side can apply  y = x * scale + offset  /  x = (y - offset) / scale  directly
    without any re-derivation.
    """
    params = normalizer.params_dict
    try:
        scale  = params["scale"].detach().cpu().tolist()
        offset = params["offset"].detach().cpu().tolist()
    except Exception as e:
        print(f"  [warn] Could not extract scale/offset for '{key}': {e}")
        return {"mode": "scale_offset", "scale": [], "offset": []}
    return {"mode": "scale_offset", "scale": scale, "offset": offset}


def _load_export_config(payload, config):
    """Load a training config from a YAML path/name or the checkpoint payload."""
    if config == "checkpoint":
        checkpoint_cfg = payload.get("cfg")
        if checkpoint_cfg is None:
            raise click.ClickException(
                "--config checkpoint requested, but the checkpoint has no 'cfg' payload")
        # Copy the DictConfig so resolution and trainer construction cannot mutate
        # the object retained in the loaded checkpoint payload.
        cfg = OmegaConf.create(OmegaConf.to_container(checkpoint_cfg, resolve=False))
        _migrate_legacy_profile(cfg)
        print("Config source: checkpoint payload")
        return cfg

    config_path = pathlib.Path(config)
    if not config_path.is_absolute():
        config_path = pathlib.Path(DIFFUSION_POLICY_ROOT) / "config_files" / config_path
    print(f"Config source: {config_path}")
    return load_config(config_path)


def _migrate_legacy_profile(cfg):
    """Relocate the task-030 no-text profile after its semantics-preserving rename."""
    legacy = "g1_prdp_standard_notext"
    current = "g1_prdp_standard"
    actor_profile = OmegaConf.select(cfg, "policy.actor.data_profile")
    dataset_profile = OmegaConf.select(cfg, "dataset.data_profile")
    if actor_profile != legacy and dataset_profile != legacy:
        return None

    profile_path = (pathlib.Path(DIFFUSION_POLICY_ROOT) / "config_files" / "defaults"
                    / "dataset" / f"{current}.yaml")
    with profile_path.open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)["data_profile"]
    expected_observation = [
        "body_pos_local", "body_lin_vel_local", "root_pos_local",
        "root_rot_local", "root_lin_vel_local", "root_ang_vel_local",
    ]
    expected_condition = [
        "joint_pos", "joint_vel", "projected_gravity", "base_lin_vel",
        "base_ang_vel", "last_actions",
    ]
    if (profile["observation"]["terms"] != expected_observation
            or profile["task_condition"]["terms"] != expected_condition
            or profile["action_term"] != "act"):
        raise click.ClickException(
            "refusing legacy profile migration: current g1_prdp_standard semantics changed")
    if actor_profile == legacy:
        OmegaConf.update(cfg, "policy.actor.data_profile", current)
    if dataset_profile == legacy:
        OmegaConf.update(cfg, "dataset.data_profile", current)
    print("Migrated legacy profile g1_prdp_standard_notext -> g1_prdp_standard "
          "(validated identical observation/task term grammar)")
    resolution = {
        "decision": "user-approved export-time migration; no filesystem alias",
        "original_actor_profile": actor_profile,
        "original_dataset_profile": dataset_profile,
        "original_resolved_path": str(
            pathlib.Path(DIFFUSION_POLICY_ROOT) / "config_files" / "defaults"
            / "dataset" / f"{legacy}.yaml"),
        "replacement_profile": current,
        "replacement_path": str(profile_path.resolve()),
        "replacement_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
    }
    OmegaConf.update(cfg, "_deploy_export.profile_resolution", resolution, force_add=True)
    return resolution


# ---- Derive deploy args from the checkpoint (Part 3: arg reduction) ----

# diffusion_deploy/ root (parent of examples/), used to resolve repo-relative paths.
_DEPLOY_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _default_urdf_path():
    """Return an absolute path to a G1 URDF in the merged PegasusMoDye repo, or "".

    PDPlanner is a submodule of PegasusMoDye; the G1 URDF ships in RLTracker.
    We walk up from diffusion_deploy/ looking for a sibling ``RLTracker``
    (``../../RLTracker/...`` in the merged repo, ``../../../RLTracker/...`` in a
    worktree under PegasusMoDye/worktrees/).  When no such repo layout is found
    (standalone PDPlanner clone) we return "" so FK exports still require an
    explicit --urdf-path.
    """
    rel = (pathlib.Path("RLTracker") / "source" / "rl_tracker" / "rl_tracker"
           / "assets" / "unitree_description" / "urdf" / "g1" / "main.urdf")
    cur = _DEPLOY_ROOT.parent  # e.g. <repo>/PDPlanner  or <worktree-root>
    for _ in range(5):
        cand = cur / rel
        if cand.is_file():
            return str(cand)
        cur = cur.parent
    return ""


def _derive_deploy_args(actor_type, obs_dim, obs_profile, use_fk, urdf_path):
    """Resolve obs_profile / use_fk / urdf_path when the user did not pass them.

    Derivation rules (documented in the README):
      * actor_type == "prdp"      → obs_profile "G1", use_fk true (192-D body + FK)
      * obs_dim == 96             → "G1_RLObs", no FK
      * obs_dim == 192            → "G1", FK
      * anything else             → genuinely ambiguous → require --obs-profile
    urdf_path defaults to the repo-relative RLTracker G1 URDF when found.
    """
    if obs_profile is None:
        if actor_type == "prdp":
            obs_profile = "G1"
        elif obs_dim == 96:
            obs_profile = "G1_RLObs"
        elif obs_dim == 192:
            obs_profile = "G1"
        else:
            raise click.ClickException(
                f"Cannot derive obs_profile from actor_type={actor_type!r} "
                f"obs_dim={obs_dim}. Pass --obs-profile explicitly "
                "(G1_RLObs | G1 | G1_Q | G1WQ).")
        print(f"Derived obs_profile={obs_profile} (actor_type={actor_type}, "
              f"obs_dim={obs_dim})")

    if use_fk is None:
        if actor_type == "prdp":
            use_fk = True
        elif obs_profile == "G1":
            use_fk = True
        elif obs_profile == "G1_RLObs":
            use_fk = False
        else:
            raise click.ClickException(
                f"Cannot derive use_fk for obs_profile={obs_profile}. "
                "Pass --use-fk explicitly.")
        print(f"Derived use_fk={use_fk} (obs_profile={obs_profile})")

    if not urdf_path:
        urdf_path = _default_urdf_path()
        if urdf_path:
            print(f"Defaulted urdf_path to: {urdf_path}")
        elif use_fk:
            print("[warn] No default G1 URDF found; pass --urdf-path when "
                  "use_fk=true (FK requires a URDF at runtime).")
    return obs_profile, use_fk, urdf_path


# ---- Interactive config editor (DEPLOY-WORKFLOW-GUI-017) ----

def _launch_gui_editor(cfg, obs_profile, use_fk, urdf_path, output, deploy_config,
                       device, mode, write_actor_config, write_normalizer_stats):
    """Launch the customtkinter config editor pre-loaded from the given config.

    The editor is imported LAZILY so the headless export path never touches
    customtkinter.  Returns ``(result, advanced_tuple)`` where ``result`` is the
    :class:`EditorResult` (``None`` = user cancelled → the exporter exits) and
    ``advanced_tuple`` carries the post-GUI advanced values.

    Defaults come from the GIVEN config YAML (``cfg.policy.actor``), never from
    hardcoded values.
    """
    from diffusion_deploy.tools.export_config_editor import run_deploy_config_editor

    actor_plain = to_plain(cfg.get("policy", {}).get("actor", {}))
    defaults = EditorDefaults(
        actor=extract_actor_defaults(actor_plain, cfg.get("env_runner", {})),
        wbg=extract_wbg_defaults(actor_plain),
        advanced={
            "obs_profile": obs_profile or "",
            "use_fk": bool(use_fk),
            "urdf_path": urdf_path or "",
            "output": output,
            "deploy_config": deploy_config,
            "device": device,
            "mode": mode,
            "write_actor_config": bool(write_actor_config),
            "write_normalizer_stats": bool(write_normalizer_stats),
        },
    )

    result = run_deploy_config_editor(defaults)
    if result is None:
        print("Export cancelled by user.")
        sys.exit(0)

    adv = result.advanced or {}
    if adv.get("obs_profile"):
        obs_profile = adv["obs_profile"]
    if "use_fk" in adv:
        use_fk = bool(adv["use_fk"])
    if adv.get("urdf_path"):
        urdf_path = adv["urdf_path"]
    if adv.get("output"):
        output = adv["output"]
    if adv.get("deploy_config"):
        deploy_config = adv["deploy_config"]
    if adv.get("device"):
        device = adv["device"]
    if adv.get("mode"):
        mode = adv["mode"]
    write_actor_config = bool(adv.get("write_actor_config", write_actor_config))
    write_normalizer_stats = bool(adv.get("write_normalizer_stats",
                                          write_normalizer_stats))

    return result, (obs_profile, use_fk, urdf_path, output, deploy_config,
                    device, mode, write_actor_config, write_normalizer_stats)


def _merge_gui_result(actor_cfg, result, write_wbg_config):
    """Merge an EditorResult into the extracted ``actor_cfg`` (GUI wins).

    * Actor fields are coerced + validated, then merged via
      :func:`merge_actor_override` (recomputes sampler_mode / cond-derived
      fields so the deploy YAML and the C++ cross-checks stay coherent).
    * WBG is merged via :func:`merge_wbg_override` (an explicit GUI disable pops
      the injected PRDP default block).
    * ``--write-wbg-config`` dumps the edited ``whole_body_guidance_config``.
    """
    gui_actor = coerce_field(result.actor or {})
    errors = validate_actor_overrides(gui_actor)
    if errors:
        raise click.ClickException(
            "Invalid actor settings from the GUI:\n  - " + "\n  - ".join(errors))

    merged = merge_actor_override(actor_cfg, gui_actor)
    merged = merge_wbg_override(merged, result.wbg)

    if write_wbg_config:
        with open(write_wbg_config, "w") as f:
            yaml.dump(result.wbg or {}, f, default_flow_style=None, sort_keys=False)
        print(f"WBG config saved to: {write_wbg_config}")

    return merged


# ---- DDPM cosine schedule (mirrors diffusion_model.py) ----

def cosine_beta_schedule(timesteps, s=0.008):
    steps = timesteps + 1
    x = np.linspace(0, steps, steps)
    alphas_cumprod = np.cos(((x / steps) + s) / (1 + s) * np.pi * 0.5) ** 2
    alphas_cumprod = alphas_cumprod / alphas_cumprod[0]
    betas = 1 - (alphas_cumprod[1:] / alphas_cumprod[:-1])
    return np.clip(betas, 0, 0.999).astype(np.float32)


def compute_ddpm_schedule(denoising_steps):
    """Return DDPM schedule tensors as a TorchScript module.

    Saved via torch.jit.save so C++ can load with torch::jit::load and
    read each tensor via module.attr("key").
    """
    betas = torch.tensor(cosine_beta_schedule(denoising_steps))
    alphas = 1.0 - betas
    alphas_cumprod = torch.cumprod(alphas, dim=0)
    alphas_cumprod_prev = torch.cat([torch.ones(1), alphas_cumprod[:-1]])

    sqrt_recip_alphas_cumprod    = torch.sqrt(1.0 / alphas_cumprod)
    sqrt_recipm1_alphas_cumprod  = torch.sqrt(1.0 / alphas_cumprod - 1)

    ddpm_var = betas * (1.0 - alphas_cumprod_prev) / (1.0 - alphas_cumprod)
    ddpm_logvar_clipped = torch.log(torch.clamp(ddpm_var, min=1e-20))
    ddpm_mu_coef1 = betas * torch.sqrt(alphas_cumprod_prev) / (1.0 - alphas_cumprod)
    ddpm_mu_coef2 = (1.0 - alphas_cumprod_prev) * torch.sqrt(alphas) / (1.0 - alphas_cumprod)

    # Pack into a scripted module so torch::jit::load works on the C++ side
    class DDPMSchedule(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.register_buffer("alphas_cumprod",               alphas_cumprod)
            self.register_buffer("sqrt_recip_alphas_cumprod",   sqrt_recip_alphas_cumprod)
            self.register_buffer("sqrt_recipm1_alphas_cumprod", sqrt_recipm1_alphas_cumprod)
            self.register_buffer("ddpm_mu_coef1",               ddpm_mu_coef1)
            self.register_buffer("ddpm_mu_coef2",               ddpm_mu_coef2)
            self.register_buffer("ddpm_logvar_clipped",         ddpm_logvar_clipped)

        def forward(self) -> torch.Tensor:
            return self.sqrt_recip_alphas_cumprod  # dummy; tensors accessed via attr

    return torch.jit.script(DDPMSchedule())


def _enable_scalar_ddim(actor_cfg):
    """Return a deterministic scalar-DDIM export override.

    Task082's condition-embedding and fixed-plan reuse require scalar DDIM.
    The override is explicit so old exporter invocations continue to preserve
    the checkpoint sampler unchanged.
    """
    if actor_cfg.get("actor_type") not in ("diffuse_cloc", "prdp"):
        raise click.ClickException(
            "--scalar-ddim requires a DiffuseCLoC/PRDP actor")
    if int(actor_cfg.get("ddim_steps") or 0) <= 0:
        raise click.ClickException("--scalar-ddim requires ddim_steps > 0")
    if float(actor_cfg.get("ddim_eta", 0.0)) != 0.0:
        raise click.ClickException("--scalar-ddim requires deterministic ddim_eta=0")
    updated = dict(actor_cfg)
    updated["use_ns_ddim"] = False
    updated["randomize_noise_schedule"] = False
    updated["sampler_mode"] = "scalar_ddim"
    return updated


def _apply_ddim_steps_override(cfg, ddim_steps):
    """Apply a bounded DDIM-step override without changing sampler semantics."""
    if ddim_steps is None:
        return
    if ddim_steps < 1:
        raise click.ClickException("--ddim-steps must be at least 1")
    denoising_steps = OmegaConf.select(cfg, "policy.actor.denoising_steps")
    if denoising_steps is None:
        raise click.ClickException(
            "--ddim-steps requires policy.actor.denoising_steps in the export config")
    if ddim_steps > int(denoising_steps):
        raise click.ClickException(
            f"--ddim-steps ({ddim_steps}) exceeds denoising_steps ({denoising_steps})")
    OmegaConf.update(cfg, "policy.actor.ddim_steps", ddim_steps)


# ---- Actor type detection ----

def _actor_type_name(actor):
    # Walk the MRO to identify the most specific known actor class
    from diffusion_policy.modules.policy_diffusion import DiffusionActor
    from diffusion_policy.modules.joint_diffusion import JointDiffusionActor
    try:
        from diffusion_policy.modules.diffuse_prdp import DiffusePRDP
        if isinstance(actor, DiffusePRDP):
            return "prdp"
    except ImportError:
        pass
    try:
        from diffusion_policy.modules.diffuse_cprdp import DiffuseCPRDP
        if isinstance(actor, DiffuseCPRDP):
            return "prdp"
    except ImportError:
        pass
    try:
        from diffusion_policy.modules.diffuse_cloc import DiffuseCLoC
        if isinstance(actor, DiffuseCLoC):
            if getattr(actor, "data_profile", None) in (
                    "g1_prdp_standard", "g1_prdp_standard2"):
                return "prdp"
            return "diffuse_cloc"
    except ImportError:
        pass
    if isinstance(actor, JointDiffusionActor):
        return "joint_diffusion"
    if isinstance(actor, DiffusionActor):
        return "diffusion"
    return type(actor).__name__


# ---- Backbone tracing helpers ----

def _single_stream_inputs(backbone, n_past, horizon, action_dim):
    cond_dim = backbone.cond_dim
    return (
        torch.randn(1, horizon, action_dim),
        torch.zeros(1, horizon, dtype=torch.long),
        torch.randn(1, n_past, cond_dim),
    )


def _trace_single_stream_backbone(backbone, n_past, obs_dim, horizon, action_dim,
                                  trace_inputs=None):
    """Trace a ConditionalSeqBackbone (transformer.py).

    backbone.forward(sample[B,H,Da], timesteps[B,H], cond)
    cond: plain tensor [B, n_past, cond_dim]  OR
          dict {'obs': [B,n_past,obs_dim], 'motion': [B,1,motion_dim]}
    We always trace with the *concatenated* cond tensor [B, n_past, cond_dim]
    because dict-conditioning goes through reshape(B,-1,cond_dim) before
    reaching the transformer layers.
    """
    cond_dim = backbone.cond_dim
    if trace_inputs is None:
        trace_inputs = _single_stream_inputs(backbone, n_past, horizon, action_dim)
    example_sample, example_t, example_cond = trace_inputs

    print(f"  Tracing backbone: sample[1,{horizon},{action_dim}] "
          f"t[1,{horizon}] cond[1,{n_past},{cond_dim}]")
    return torch.jit.trace(backbone, (example_sample, example_t, example_cond),
                           check_trace=False)


def _joint_stream_inputs(backbone, n_cond_steps, state_dim, action_dim, horizon):
    x_horizon = getattr(backbone, 'x_horizon', horizon)
    y_horizon = getattr(backbone, 'y_horizon', horizon)
    cond_dim = getattr(backbone, 'cond_dim', 0)
    values = (
        torch.randn(1, x_horizon, state_dim),
        torch.randn(1, y_horizon, action_dim),
        torch.zeros(1, x_horizon, dtype=torch.long),
        torch.zeros(1, y_horizon, dtype=torch.long),
    )
    if cond_dim > 0:
        values += (torch.randn(1, n_cond_steps, cond_dim),)
    return values


def _trace_joint_stream_backbone(backbone, n_cond_steps, state_dim, action_dim, horizon,
                                 trace_inputs=None):
    """Trace a JointSeqBackbone (transformer_codiffuse.py).

    backbone.forward(x_input[B,Hx,Dx], y_input[B,Hy,Dy],
                     x_timesteps[B,Hx], y_timesteps[B,Hy],
                     cond)
    Returns (x_out[B,Hx,Dx], y_out[B,Hy,Dy]).
    """
    x_horizon = getattr(backbone, 'x_horizon', horizon)
    y_horizon = getattr(backbone, 'y_horizon', horizon)

    # cond_dim is 0 or set on backbone; use zeros if no conditioning
    cond_dim = getattr(backbone, 'cond_dim', 0)
    if trace_inputs is None:
        trace_inputs = _joint_stream_inputs(
            backbone, n_cond_steps, state_dim, action_dim, horizon)
    example_x, example_y, example_xt, example_yt = trace_inputs[:4]

    if cond_dim > 0:
        example_cond = trace_inputs[4]
        print(f"  Tracing joint backbone: x[1,{x_horizon},{state_dim}] "
              f"y[1,{y_horizon},{action_dim}] xt[1,{x_horizon}] yt[1,{y_horizon}] "
              f"cond[1,{n_cond_steps},{cond_dim}]")
    else:
        print(f"  Tracing joint backbone (no cond): x[1,{x_horizon},{state_dim}] "
              f"y[1,{y_horizon},{action_dim}]")

    return torch.jit.trace(backbone, trace_inputs, check_trace=False)


def _trace_condition_embedding_backbone(backbone, trace_inputs):
    """Trace legacy forward plus the exact per-policy-call condition API."""
    if len(trace_inputs) != 5:
        raise click.ClickException(
            "condition embedding reuse requires a conditioned joint backbone")
    wrapper = Torch21ConditionEmbeddingBackbone(backbone).eval()
    condition_embeddings = wrapper.build_condition_embeddings(trace_inputs[4])
    return torch.jit.trace_module(
        wrapper,
        {
            "forward": trace_inputs,
            "build_condition_embeddings": (trace_inputs[4],),
            "forward_encoded_condition": trace_inputs[:4] + (condition_embeddings,),
        },
        check_trace=False,
    )


def _parity_error(actual, expected):
    actual_values = actual if isinstance(actual, (tuple, list)) else (actual,)
    expected_values = expected if isinstance(expected, (tuple, list)) else (expected,)
    if len(actual_values) != len(expected_values):
        raise click.ClickException("Torch 2.1 lowering changed backbone output arity")
    maximum = 0.0
    for actual_value, expected_value in zip(actual_values, expected_values):
        is_half = actual_value.dtype == torch.float16 or expected_value.dtype == torch.float16
        atol, rtol = parity_tolerances("fp16" if is_half else "fp32")
        torch.testing.assert_close(actual_value, expected_value, atol=atol, rtol=rtol)
        maximum = max(maximum, float((actual_value - expected_value).abs().max().item()))
    return maximum


def _input_schema(trace_inputs):
    return [{"shape": list(value.shape), "dtype": str(value.dtype)}
            for value in trace_inputs]


def _validate_prdp_export_contract(actor, norm_stats):
    backbone = actor.backbone
    data_profile = getattr(actor, "data_profile", "")
    checks = {
        "actor_obs_dim": int(actor.obs_dim),
        "actor_action_dim": int(actor.action_dim),
        "backbone_x_input_dim": int(backbone.x_input_dim),
        "backbone_x_output_dim": int(backbone.x_output_dim),
        "backbone_y_input_dim": int(backbone.y_input_dim),
        "backbone_y_output_dim": int(backbone.y_output_dim),
        "backbone_cond_dim": int(backbone.cond_dim),
        "backbone_n_cond_steps": int(backbone.n_cond_steps),
        "normalizer_obs_dim": len(norm_stats.get("obs", {}).get("scale", [])),
        "normalizer_action_dim": len(norm_stats.get("action", {}).get("scale", [])),
        "normalizer_cond_dim": len(norm_stats.get("cond", {}).get("scale", [])),
        "emphasis_input_dim": int(actor.emphasis_mat.shape[0]),
        "emphasis_output_dim": int(actor.emphasis_mat.shape[1]),
    }
    expected = {
        "actor_obs_dim": 384,
        "actor_action_dim": 29,
        "backbone_x_input_dim": 384,
        "backbone_x_output_dim": 384,
        "backbone_y_input_dim": 29,
        "backbone_y_output_dim": 29,
        "backbone_n_cond_steps": 4,
        "normalizer_obs_dim": 192,
        "normalizer_action_dim": 29,
        "emphasis_input_dim": 192,
        "emphasis_output_dim": 384,
    }
    incompatible = {key: {"actual": checks[key], "expected": value}
                    for key, value in expected.items() if checks[key] != value}

    # PRDP always consumes the 96-D deployable RL observation. Conditional
    # checkpoints append one 512-D MotionCLIP embedding, while no-text
    # checkpoints use the RL observation alone. Keep this aligned with the
    # C++ config parser instead of imposing one experiment's 96-D contract on
    # every PRDP export.
    cond_dim = checks["backbone_cond_dim"]
    allowed_cond_dims = (605,) if data_profile == "g1_prdp_standard2" else (96, 608)
    if cond_dim not in allowed_cond_dims:
        incompatible["backbone_cond_dim"] = {
            "actual": cond_dim,
            "expected": ("605 (93 robot + 512 text)"
                         if data_profile == "g1_prdp_standard2"
                         else "96 (no text) or 608 (96 RLObs + 512 text)"),
        }
    if checks["normalizer_cond_dim"] != cond_dim:
        incompatible["normalizer_cond_dim"] = {
            "actual": checks["normalizer_cond_dim"],
            "expected": cond_dim,
        }
    if incompatible:
        raise click.ClickException(
            "PRDP export contract mismatch for data_profile=" +
            repr(data_profile) + ": " + str(incompatible))
    robot_cond_dim = 93 if data_profile == "g1_prdp_standard2" else 96
    checks["rlobs_cond_dim"] = robot_cond_dim
    checks["text_cond_dim"] = cond_dim - robot_cond_dim
    checks["condition_variant"] = "text" if cond_dim > robot_cond_dim else "no_text"
    checks["status"] = "pass"
    return checks


# ---- Actor config extraction ----

# Default whole_body_guidance_config applied to PRDP exports when neither the
# checkpoint's embedded cfg nor --wbg-config provides an enabled WBG config.
# Mirrors config/prdp_wbg_actor_config.yaml and the validated classifier
# vx=0.3 example (config/prdp_wbg_ddim_example.yaml). Only vx is enabled by
# default; set whole_body_guidance.enabled: false in the deploy config to
# disable guidance entirely, or pass --wbg-config to override this block.
_PRDP_DEFAULT_WBG_CONFIG = {
    "enabled": True,
    "guidance_mode": "classifier",
    "mode": "simple",
    "enable_zeta_comp": True,
    "enable_damping_comp": True,
    "guidances": {
        "vx_guide": {"enabled": True, "kp": 0.1, "command": 0.3,
                     "body_indices": [0, 9]},
        "vy_guide": {"enabled": False, "kp": 0.1},
        "wz_guide": {"enabled": False, "kp": 0.1},
    },
}


# Canonical WBG→C++ translation lives in tools/deploy_config_schema.py so the
# GUI merge and the headless export always agree (DEPLOY-WORKFLOW-GUI-017).
_wbg_deploy_block = wbg_to_deploy_block


def _extract_actor_config(actor, actor_type, obs_dim, wbg_config=None,
                          delay_action_step=0,
                          delay_action_step_source="compatibility_default"):
    """Build actor_config dict for the C++ actor constructor."""
    cfg = {
        "actor_type":      actor_type,
        "export_torch_version": str(torch.__version__),
        "action_dim":      int(actor.action_dim),
        "obs_dim":         int(obs_dim),
        "n_obs_steps":     int(actor.n_past_steps),
        "delay_action_step": float(delay_action_step),
        "delay_action_step_source": str(delay_action_step_source),
        "horizon":         int(actor.horizon),
        "denoising_steps": int(actor.denoising_steps),
        "predict_epsilon": bool(actor.predict_epsilon),
        "denoised_clip_value": float(actor.denoised_clip_value)
                                if actor.denoised_clip_value is not None else 1.0,
    }

    # Motion conditioning
    if hasattr(actor, 'backbone') and hasattr(actor.backbone, 'cond_dim'):
        backbone_cond_dim = int(actor.backbone.cond_dim)
        cfg["backbone_cond_dim"] = backbone_cond_dim
        # For DP/TorchActor: backbone cond = [obs, motion_latent] → motion_dim = backbone_cond_dim - obs_dim
        # For CLoC/JointDiffusion: backbone cond = motion_latent only → motion_dim = backbone_cond_dim
        if actor_type in ("joint_diffusion", "diffuse_cloc", "prdp"):
            has_motion_cond = backbone_cond_dim > 0
            motion_dim = backbone_cond_dim
        else:
            has_motion_cond = backbone_cond_dim > obs_dim
            motion_dim = backbone_cond_dim - obs_dim if has_motion_cond else 0
        cfg["has_motion_cond"] = has_motion_cond
        cfg["motion_dim"]      = motion_dim

    # DDIM acceleration params (Python None → C++ 0 to mean "disabled").
    # Extracted BEFORE sampler-mode derivation so derive_sampler_mode reads the
    # RAW ddim_steps (None = no DDIM acceleration) and matches the actor.
    ddim_steps_py = getattr(actor, 'ddim_steps', None)
    cfg["ddim_steps"] = int(ddim_steps_py) if ddim_steps_py is not None else 0
    cfg["ddim_eta"]   = float(getattr(actor, 'ddim_eta', 0.0))

    # JointDiffusionActor / DiffuseCLoC extras
    if actor_type in ("joint_diffusion", "diffuse_cloc", "prdp"):
        cfg["state_dim"]              = int(actor.obs_dim)
        cfg["state_pred_epsilon"]     = bool(getattr(actor, 'state_pred_epsilon', actor.predict_epsilon))
        cfg["action_pred_epsilon"]    = bool(getattr(actor, 'action_pred_epsilon', actor.predict_epsilon))
        cfg["action_denoising_steps"] = int(getattr(actor, 'action_denoising_steps', actor.denoising_steps))
        cfg["state_denoising_steps"]  = int(getattr(actor, 'state_denoising_steps', actor.denoising_steps))

    # DiffuseCLoC extras
    if actor_type in ("diffuse_cloc", "prdp"):
        cfg["state_emphasis"]  = str(getattr(actor, 'state_emphasis', 'same'))
        cfg["action_schedule"] = str(getattr(actor, 'action_schedule', 'from_xT_decreasing'))
        cfg["state_schedule"]  = str(getattr(actor, 'state_schedule', 'from_xT_step'))
        cfg["n_cond_steps"] = int(getattr(actor.backbone, "n_cond_steps", actor.n_past_steps))
        cfg["no_state_override"] = bool(getattr(actor, "no_state_override", False))
        cfg["randomize_noise_schedule"] = bool(getattr(actor, "randomize_noise_schedule", False))
        cfg["use_ns_ddim"] = bool(getattr(actor, "use_ns_ddim", False))
        # Old checkpoints may carry the former constructor default as a
        # serialized attribute. Production exports correct that bug unless the
        # CLI explicitly requests duplicate_backbone for historical replay.
        cfg["classifier_guidance_impl"] = "reuse_x0"
        cfg["sampler_mode"] = derive_sampler_mode({
            "use_ns_ddim": cfg["use_ns_ddim"],
            "ddim_steps": ddim_steps_py,
            "randomize_noise_schedule": cfg["randomize_noise_schedule"],
        })
        wbg_src = (wbg_config if wbg_config is not None
                   else getattr(actor, "whole_body_guidance_config", None))
        if wbg_config is None and wbg_src is not None \
                and not bool(wbg_src.get("enabled", False)):
            # Embedded config exists but explicitly disables WBG (training
            # configs default all guides off, e.g. the July-31 g1prdp_diffuse
            # checkpoint). With no --wbg-config override, fall through to the
            # PRDP default so exports stay WBG-enabled.
            wbg_src = None
        if wbg_src is None and actor_type == "prdp":
            # PRDP exports default to WBG-enabled: inject the validated
            # classifier vx=0.3 block so the generated deploy config carries
            # model.whole_body_guidance and --wbg-udp takes effect. Override
            # with --wbg-config (or an embedded enabled whole_body_guidance_
            # config) to customize; pass --wbg-config with enabled: false to
            # disable guidance entirely.
            wbg_src = _PRDP_DEFAULT_WBG_CONFIG
            print("WBG: PRDP default injected (classifier vx=0.3); pass "
                  "--wbg-config to override, or --wbg-config enabled=false "
                  "to disable guidance.")
        wbg = _wbg_deploy_block(wbg_src)
        if wbg is not None:
            cfg["whole_body_guidance"] = wbg

        # Export emphasis matrices (needed by C++ DiffuseCLoCActor)
        emph     = actor.emphasis_mat.cpu().float()
        emph_inv = actor.emphasis_mat_inv.cpu().float()
        cfg["emphasis_mat_shape"]     = list(emph.shape)
        cfg["emphasis_mat_inv_shape"] = list(emph_inv.shape)

    # ---- Python-aligned backbone / actor fields (follow-up: config-schema
    # alignment).  The deploy YAML now carries a nested ``backbone:`` block with
    # the Python names (x_input_dim/x_output_dim/cond_dim/n_cond_steps/
    # cross_attn_window/cross_attn_mode) plus top-level clean_past_state and
    # data_profile.  The flat legacy names (state_dim/backbone_cond_dim/
    # motion_dim) stay for back-compat.
    if hasattr(actor, 'backbone'):
        bb = actor.backbone
        if hasattr(bb, 'x_input_dim'):
            cfg["x_input_dim"] = int(bb.x_input_dim)
        if hasattr(bb, 'x_output_dim'):
            cfg["x_output_dim"] = int(bb.x_output_dim)
        _w = getattr(bb, 'cross_attn_window', None)
        cfg["cross_attn_window"] = int(_w) if _w is not None else 0  # 0 = null
        cfg["cross_attn_mode"] = str(getattr(bb, 'cross_attn_mode', 'full'))
    cfg["clean_past_state"] = bool(getattr(actor, 'clean_past_state', False))
    _dp = getattr(actor, 'data_profile', '')
    cfg["data_profile"] = str(_dp) if isinstance(_dp, str) else ''

    return cfg


# ---- Deploy config generation ----

def _resolve_prdp_condition_contract(actor_cfg):
    """Resolve deploy-time PRDP packing without profile aliases.

    g1_prdp_standard2 is an explicit wire/runtime contract: the 93-D robot
    prefix omits base_lin_vel and is followed by the 512-D text embedding.
    Any checkpoint/profile dimension drift is rejected before artifacts are
    written.
    """
    if actor_cfg["actor_type"] != "prdp":
        return {
            "condition_profile": "external",
            "robot_cond_dim": 0,
            "text_cond_dim": (actor_cfg.get("motion_dim", 0)
                              if actor_cfg.get("has_motion_cond", False) else 0),
            "terms": [],
        }

    data_profile = actor_cfg.get("data_profile", "")
    backbone_cond_dim = int(actor_cfg.get("backbone_cond_dim", 0))
    if data_profile == "g1_prdp_standard2":
        if backbone_cond_dim != 605:
            raise click.ClickException(
                "g1_prdp_standard2 requires backbone cond_dim=605 "
                f"(93 robot + 512 text), got {backbone_cond_dim}")
        return {
            "condition_profile": "g1_prdp_standard2",
            "robot_cond_dim": 93,
            "text_cond_dim": 512,
            "terms": [
                "joint_pos", "joint_vel", "projected_gravity",
                "base_ang_vel", "last_actions", "text_cond",
            ],
        }

    return {
        "condition_profile": "prdp_rlobs",
        "robot_cond_dim": 96,
        "text_cond_dim": max(0, backbone_cond_dim - 96),
        "terms": [
            "joint_pos", "joint_vel", "projected_gravity", "base_lin_vel",
            "base_ang_vel", "last_actions",
        ] + (["text_cond"] if backbone_cond_dim > 96 else []),
    }

def _write_deploy_config(output_dir, actor_cfg, norm_stats, backbone_path, schedule_path,
                          obs_profile="G1_RLObs", config_name=None,
                          urdf_path="", use_fk=False, compatibility_path=None,
                          target_profile="native", precision="fp32"):
    """Write a ready-to-use C++ deploy config YAML next to the exported model files.

    The generated file mirrors g1_deploy_config.yaml in structure and is fully
    populated with the normalizer statistics extracted from the checkpoint, so
    no manual editing is needed after export.

    Kp/Kd are no longer written as active config keys; they have moved to
    fsm_config.yaml → Running state.  Reference values are appended as YAML
    comments for documentation.
    """
    output_path = pathlib.Path(output_dir).resolve()

    def _resource_path(path):
        """Return a POSIX path relative to the exported resource directory."""
        try:
            return pathlib.Path(path).resolve().relative_to(output_path).as_posix()
        except ValueError as exc:
            raise click.ClickException(
                f"runtime artifact must be inside --output: {path}"
            ) from exc

    fsm_path = copy_runtime_resource(
        _DEPLOY_ROOT / "config" / "fsm_unitree_remote.yaml",
        output_path,
        "fsm_config.yaml",
    )
    exported_urdf = ""
    if use_fk:
        if not urdf_path:
            raise click.ClickException(
                "env.use_fk=true requires --urdf-path so the URDF can be bundled"
            )
        try:
            exported_urdf = copy_runtime_resource(
                urdf_path, output_path, "assets/g1.urdf")
        except (FileNotFoundError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    n_future = actor_cfg.get("horizon", actor_cfg["n_obs_steps"] + 16) - actor_cfg["n_obs_steps"]

    # Reference Kp/Kd values for fsm_config.yaml Running state (MuJoCo SDK order).
    _ref_kp = [
        40.17923847137318, 99.09842777666113, 40.17923847137318, 99.09842777666113,
        28.50124619574858, 28.50124619574858, 40.17923847137318, 99.09842777666113,
        40.17923847137318, 99.09842777666113, 28.50124619574858, 28.50124619574858,
        40.17923847137318, 28.50124619574858, 28.50124619574858, 14.25062309787429,
        14.25062309787429, 14.25062309787429, 14.25062309787429, 14.25062309787429,
        16.77832748089279, 16.77832748089279, 14.25062309787429, 14.25062309787429,
        14.25062309787429, 14.25062309787429, 14.25062309787429, 16.77832748089279,
        16.77832748089279,
    ]
    _ref_kd = [
        2.5578897650279457, 6.3088018534966395, 2.5578897650279457, 6.3088018534966395,
        1.814445686584846, 1.814445686584846, 2.5578897650279457, 6.3088018534966395,
        2.5578897650279457, 6.3088018534966395, 1.814445686584846, 1.814445686584846,
        2.5578897650279457, 1.814445686584846, 1.814445686584846, 0.907222843292423,
        0.907222843292423, 0.907222843292423, 0.907222843292423, 0.907222843292423,
        1.06814150219, 1.06814150219, 0.907222843292423, 0.907222843292423,
        0.907222843292423, 0.907222843292423, 0.907222843292423, 1.06814150219,
        1.06814150219,
    ]

    condition_contract = _resolve_prdp_condition_contract(actor_cfg)
    prdp_text_dim = condition_contract["text_cond_dim"]
    deploy = {
        "model": {
            "backend":          "torch",
            "actor_type":       actor_cfg["actor_type"],
            "path":             _resource_path(backbone_path),
            "schedule_path":    _resource_path(schedule_path),
            "export_torch_version": actor_cfg.get("export_torch_version", ""),
            "target_profile": target_profile,
            "precision": precision,
            "obs_dim":          actor_cfg["obs_dim"],
            "action_dim":       actor_cfg["action_dim"],
            "n_obs_steps":      actor_cfg["n_obs_steps"],
            "n_future_steps":   n_future,
            "denoising_steps":  actor_cfg["denoising_steps"],
            "predict_epsilon":  actor_cfg["predict_epsilon"],
            "denoised_clip":    actor_cfg.get("denoised_clip_value", 1.0),
            "has_motion_cond":  actor_cfg.get("has_motion_cond", False),
            "motion_dim":       actor_cfg.get("motion_dim", 0),
            "backbone_cond_dim": actor_cfg.get("backbone_cond_dim", actor_cfg["obs_dim"]),
            "obs_profile":      obs_profile,
            "n_cond_steps":     actor_cfg.get("n_cond_steps", 1),
            "no_state_override": actor_cfg.get("no_state_override", False),
            # Python-aligned actor provenance fields (config-schema alignment).
            "clean_past_state": actor_cfg.get("clean_past_state", False),
            "data_profile":     actor_cfg.get("data_profile", ""),
            # Python-aligned `backbone:` block.  Names now match the Python
            # config (x_input_dim/x_output_dim/cond_dim/n_cond_steps/
            # cross_attn_window/cross_attn_mode); the flat legacy names
            # (state_dim/backbone_cond_dim/n_cond_steps/motion_dim) are kept
            # below so existing YAMLs keep loading.
            "backbone": {
                "x_input_dim":      actor_cfg.get("x_input_dim", actor_cfg.get("state_dim", actor_cfg["obs_dim"])),
                "x_output_dim":     actor_cfg.get("x_output_dim", actor_cfg.get("state_dim", actor_cfg["obs_dim"])),
                "cond_dim":         actor_cfg.get("backbone_cond_dim", actor_cfg["obs_dim"]),
                "n_cond_steps":     actor_cfg.get("n_cond_steps", 1),
                "cross_attn_window": (actor_cfg.get("cross_attn_window")
                                      if actor_cfg.get("cross_attn_window") else None),
                "cross_attn_mode":  actor_cfg.get("cross_attn_mode", "full"),
            },
        },
        "env": {
            "execution_mode":      "offline",
            "network_interface":   "lo",
            "control_dt":          0.02,
            "num_dof":             actor_cfg["action_dim"],
            "use_pr_mode":         False,
            "enable_safety_checks": True,
            "use_fk":              use_fk,
            "urdf_path":           exported_urdf,
        },
        "runner": {
            "max_steps":       200000,
            "delay_action_step": actor_cfg.get("delay_action_step", 0),
            "realtime_mode":   True,
            "reset_height":    0.3,
            "enable_cond_udp": prdp_text_dim > 0 if actor_cfg["actor_type"] == "prdp" else actor_cfg.get("has_motion_cond", False),
            "cond_udp_host":   "127.0.0.1",
            "cond_udp_port":   9877,
            "condition_profile": condition_contract["condition_profile"],
            "n_cond_steps": actor_cfg.get("n_cond_steps", 1),
            "rlobs_cond_dim": condition_contract["robot_cond_dim"],
            "text_cond_dim": prdp_text_dim,
        },
        "normalization": {
            k: v for k, v in norm_stats.items() if k in ("obs", "action", "cond")
        },
        "resources": {
            "schema_version": SCHEMA_VERSION,
            "manifest": MANIFEST_NAME,
            "checksum_file": CHECKSUM_NAME,
            "conditioning_mode": "external_udp" if prdp_text_dim > 0 else "none",
        },
    }

    compatibility_relative = None
    if compatibility_path:
        compatibility_relative = _resource_path(compatibility_path)
        deploy["model"]["compatibility_manifest"] = compatibility_relative

    # Drop cond block when there is no motion conditioning
    if not actor_cfg.get("has_motion_cond", False):
        deploy["normalization"].pop("cond", None)

    # DDIM acceleration
    deploy["model"]["ddim_steps"] = actor_cfg.get("ddim_steps", 0)
    deploy["model"]["ddim_eta"]   = actor_cfg.get("ddim_eta", 0.0)

    # DiffuseCLoC / JointDiffusion extras
    if actor_cfg["actor_type"] in ("joint_diffusion", "diffuse_cloc", "prdp"):
        deploy["model"]["state_dim"]              = actor_cfg.get("state_dim", actor_cfg["obs_dim"])
        deploy["model"]["state_pred_epsilon"]     = actor_cfg.get("state_pred_epsilon", actor_cfg["predict_epsilon"])
        deploy["model"]["action_pred_epsilon"]    = actor_cfg.get("action_pred_epsilon", actor_cfg["predict_epsilon"])
        deploy["model"]["action_denoising_steps"] = actor_cfg.get("action_denoising_steps", actor_cfg["denoising_steps"])
        deploy["model"]["state_denoising_steps"]  = actor_cfg.get("state_denoising_steps",  actor_cfg["denoising_steps"])
        deploy["model"]["attention_projection_packing"] = actor_cfg.get(
            "attention_projection_packing", "none")
        deploy["model"]["condition_embedding_reuse"] = actor_cfg.get(
            "condition_embedding_reuse", False)
        deploy["model"]["ddim_precompute"] = actor_cfg.get("ddim_precompute", False)
        deploy["model"]["defer_finite_checks"] = actor_cfg.get(
            "defer_finite_checks", False)
        deploy["model"]["inference_mode"] = actor_cfg.get("inference_mode", False)
    if actor_cfg["actor_type"] in ("diffuse_cloc", "prdp"):
        deploy["model"]["emphasis_path"]   = _resource_path(actor_cfg["emphasis_path"])
        deploy["model"]["state_emphasis"]  = actor_cfg.get("state_emphasis", "same")
        deploy["model"]["action_schedule"] = actor_cfg.get("action_schedule", "from_xT_decreasing")
        deploy["model"]["state_schedule"]  = actor_cfg.get("state_schedule",  "from_xT_step")
        deploy["model"]["sampler_mode"]    = actor_cfg.get("sampler_mode", "rolling_ddpm")
        # Sampler-mode predicates consumed by the C++ config_parser validation
        # (ns_ddim requires use_ns_ddim; rolling_ddim requires
        # randomize_noise_schedule).
        deploy["model"]["use_ns_ddim"]             = actor_cfg.get("use_ns_ddim", False)
        deploy["model"]["randomize_noise_schedule"] = actor_cfg.get("randomize_noise_schedule", True)
        deploy["model"]["classifier_guidance_impl"] = actor_cfg.get(
            "classifier_guidance_impl", "reuse_x0")
        if actor_cfg.get("whole_body_guidance"):
            deploy["model"]["whole_body_guidance"] = actor_cfg["whole_body_guidance"]

    if config_name is None:
        config_name = "deploy_config.yaml"
    cfg_path = str(output_path / config_name)
    _resource_path(cfg_path)
    with open(cfg_path, "w") as f:
        yaml.dump(deploy, f, default_flow_style=None, sort_keys=False)
        # Append reference Kp/Kd as comments (these now live in fsm_config.yaml Running state)
        f.write("\n# =====================================================================\n")
        f.write("# Reference Kp / Kd (MuJoCo SDK joint order, 29 DOF).\n")
        f.write("# These have moved to fsm_config.yaml → Running state.\n")
        f.write("# Copy the values below into the Running.kp / Running.kd sections.\n")
        f.write("#\n")
        f.write("# Kp: " + str(_ref_kp) + "\n")
        f.write("# Kd: " + str(_ref_kd) + "\n")
    artifacts = [
        {"role": "policy_backbone", "path": _resource_path(backbone_path)},
        {"role": "diffusion_schedule", "path": _resource_path(schedule_path)},
        {"role": "deploy_config", "path": _resource_path(cfg_path)},
        {"role": "fsm_config", "path": fsm_path},
    ]
    if compatibility_relative:
        artifacts.append({
            "role": "actor_compatibility",
            "path": compatibility_relative,
        })
    if actor_cfg["actor_type"] in ("diffuse_cloc", "prdp"):
        artifacts.append({
            "role": "emphasis_matrices",
            "path": _resource_path(actor_cfg["emphasis_path"]),
        })
    if exported_urdf:
        artifacts.append({"role": "g1_urdf", "path": exported_urdf})
    manifest_path = write_resource_manifest(
        output_path, cfg_path, output_path / fsm_path, artifacts, prdp_text_dim,
        data_profile=actor_cfg.get("data_profile", ""),
        condition_profile=condition_contract["condition_profile"],
        robot_cond_dim=condition_contract["robot_cond_dim"],
        condition_terms=condition_contract["terms"],
        precision=precision,
        delay_action_step=actor_cfg.get("delay_action_step", 0),
        delay_action_step_source=actor_cfg.get(
            "delay_action_step_source", "compatibility_default"))
    print(f"Resource manifest saved to: {manifest_path}")
    return cfg_path


# ---- Main ----

@click.command()
@click.option("-c", "--checkpoint", required=True)
@click.option("--config", default="checkpoint", show_default=True,
              help="Config YAML name/path, or 'checkpoint' (default) to use the "
                   "immutable cfg embedded in the checkpoint")
@click.option("-o", "--output", default="models/", help="Output directory")
@click.option("--mode", default="backbone",
              type=click.Choice(["backbone", "full_loop"]),
              help="Export mode: backbone (reliable, C++ loop) or full_loop (lazy JIT)")
@click.option("--device", default="cpu")
@click.option("--precision", type=click.Choice(["fp32", "fp16"]), default=None,
              help="Export precision. Default: training.precision from checkpoint/config, else fp32.")
@click.option("--target", default="native", show_default=True,
              type=click.Choice(["native", "jetson-jp5-torch21"]),
              help="Export operator profile; the JP5 target lowers fused SDPA to Torch 2.1 primitives")
@click.option("--attention-projection-packing", default="none", show_default=True,
              type=click.Choice(["none", "self", "cross", "all"]),
              help="Jetson opt-in: pack decoder self QKV and/or cross KV projections")
@click.option("--condition-embedding-reuse/--no-condition-embedding-reuse", default=False,
              help="Export stateless methods that encode condition once per policy call")
@click.option("--ddim-precompute/--no-ddim-precompute", default=False,
              help="Precompute fixed B=1 deterministic DDIM timestep tensors/scalars")
@click.option("--defer-finite-checks/--no-defer-finite-checks", default=False,
              help="Move per-NFE finite synchronization to policy input/output boundaries")
@click.option("--inference-mode/--no-inference-mode", default=False,
              help="Run the C++ actor under c10::InferenceMode in addition to no-grad")
@click.option("--scalar-ddim", is_flag=True, default=False,
              help="Explicitly export deterministic scalar DDIM instead of the "
                   "checkpoint's ns/rolling schedule; required by Task082 "
                   "condition-reuse and DDIM-plan optimizations")
@click.option("--ddim-steps", type=click.IntRange(min=1), default=None,
              help="Override policy.actor.ddim_steps before reconstructing the "
                   "checkpoint actor. The checkpoint's sampler family is preserved.")
@click.option("--delay-action-step", type=float, default=None,
              help="Override env_runner.delay_action_step before export.")
@click.option("--stats-only", is_flag=True, default=False)
@click.option("--obs-profile", default=None, show_default=False,
              help="obs_profile written into the deploy config. Default: derived "
                   "(prdp→G1, obs_dim 96→G1_RLObs, 192→G1); pass explicitly when "
                   "ambiguous.")
@click.option("--deploy-config", default="deploy_config.yaml", show_default=True,
              help="Filename for the generated C++ deploy config (inside --output)")
@click.option("--urdf-path", default=None, show_default=False,
              help="Path to G1 URDF for Pinocchio FK (written into env.urdf_path). "
                   "Default: repo-relative RLTracker G1 URDF when found, else empty.")
@click.option("--use-fk/--no-use-fk", default=None,
              help="Enable or disable FK in the generated deploy config. Default: "
                   "derived (G1/prdp→true, G1_RLObs→false).")
@click.option("--write-actor-config", is_flag=True, default=False,
              help="Debug: also dump actor_config.yaml (root key `actor:`). The C++ "
                   "runtime does NOT read this file; the deploy config is the single "
                   "runtime source of truth.")
@click.option("--write-normalizer-stats", is_flag=True, default=False,
              help="Debug: also dump normalizer_stats.yaml (normalization: block). "
                   "The C++ runtime reads only the deploy config's normalization: "
                   "block; this file is NOT read at runtime (parity fixtures use "
                   "it). Implied by --stats-only.")
@click.option("--wbg-config", default=None, show_default=True,
              help="YAML file with a whole_body_guidance_config dict (enabled, "
                   "guidance_mode, mode, guidances.{vx,vy,wz}_guide[.enabled/.kp/"
                   ".command/.body_indices]) to serialize into the deploy config. "
                   "Overrides the embedded whole_body_guidance_config or the PRDP "
                   "default block (classifier vx=0.3) that is injected when the "
                   "checkpoint has none.")
@click.option("--classifier-guidance-impl", default=None,
              type=click.Choice(["duplicate_backbone", "reuse_x0"]),
              help="Override the checkpoint's classifier-guidance implementation. "
                   "reuse_x0 is the production default; duplicate_backbone is "
                   "deprecated and retained only for historical replay.")
@click.option("--gui", is_flag=True, default=False,
              help="Open the interactive config editor (customtkinter) pre-loaded "
                   "from the given config (--config YAML or checkpoint payload) "
                   "before exporting.  GUI edits override the extracted defaults. "
                   "Headless export is the default when --gui is NOT passed.")
@click.option("--write-wbg-config", default=None, show_default=True,
              help="Also dump the edited whole_body_guidance_config as YAML to "
                   "this path (round-trips into a later --wbg-config).  Only "
                   "meaningful with --gui.")
def main(checkpoint, config, output, mode, device, precision, target,
         attention_projection_packing, condition_embedding_reuse,
         ddim_precompute, defer_finite_checks, inference_mode, scalar_ddim, ddim_steps,
         delay_action_step,
         stats_only, obs_profile, deploy_config,
         urdf_path, use_fk, write_actor_config, write_normalizer_stats, wbg_config,
         classifier_guidance_impl, gui, write_wbg_config):
    if gui and stats_only:
        raise click.ClickException("--gui and --stats-only are mutually exclusive")
    if gui and mode == "full_loop":
        print("[warn] --gui with --mode full_loop: the editor edits the actor "
              "config that only --mode backbone exports; continuing.")
    if attention_projection_packing != "none" and target != JETSON_JP5_TARGET:
        raise click.ClickException(
            "--attention-projection-packing requires --target jetson-jp5-torch21")
    if condition_embedding_reuse and target != JETSON_JP5_TARGET:
        raise click.ClickException(
            "--condition-embedding-reuse requires --target jetson-jp5-torch21")
    pathlib.Path(output).mkdir(parents=True, exist_ok=True)

    print(f"Loading checkpoint: {checkpoint}")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)

    cfg = _load_export_config(payload, config)
    OmegaConf.resolve(cfg)
    if ddim_steps is not None:
        _apply_ddim_steps_override(cfg, ddim_steps)
        print(f"Sampler step override: ddim_steps={ddim_steps}; sampler family preserved")
    if delay_action_step is not None:
        if not math.isfinite(delay_action_step):
            raise click.ClickException("--delay-action-step must be finite")
        OmegaConf.update(cfg, "env_runner.delay_action_step", delay_action_step, force_add=True)
        print(f"Action selection override: delay_action_step={delay_action_step}")
    from diffusion_policy.utils.precision import normalize_precision, validate_precision_device
    precision = normalize_precision(
        precision if precision is not None
        else OmegaConf.select(cfg, "training.precision", default="fp32"))
    export_device = validate_precision_device(precision, device)
    if precision == "fp16" and export_device.type != "cuda":
        raise click.ClickException("fp16 export requires --device cuda:N")
    OmegaConf.update(cfg, "training.precision", precision, force_add=True)

    cls = __import__("hydra.utils", fromlist=["get_class"]).get_class(cfg._target_)
    trainer: BaseTrainer = cls(cfg, init_wandb=False)
    trainer.load_payload(payload, exclude_keys=None, include_keys=None)

    use_ema = bool(cfg.training.get("use_ema", False))
    if use_ema:
        if not hasattr(trainer, "ema_agent") or trainer.ema_agent is None:
            raise click.ClickException(
                "checkpoint/config requires EMA export, but ema_agent could not be reconstructed")
        agent = trainer.ema_agent
        print("Export weight source: ema_agent")
    else:
        agent = trainer.agent
        print("Export weight source: agent")
    agent.to(device)
    agent.eval()

    # ---- Export normalizer stats ----
    print("\nExporting normalizer stats...")
    norm_stats = {}
    norm_keys = list(agent.normalizer.params_dict.keys())
    for key in norm_keys:
        try:
            single = agent.normalizer[key]
            norm_stats[key] = _normalizer_stats_to_dict(single, key)
            dim = len(norm_stats[key].get("scale", norm_stats[key].get("min", norm_stats[key].get("mean", []))))
            print(f"  {key}: mode={norm_stats[key]['mode']}  dim={dim}")
        except Exception as e:
            print(f"  [skip] {key}: {e}")

    # normalizer_stats.yaml is NOT a runtime artifact: the deploy config's
    # normalization: block carries the identical stats (from the same
    # norm_stats dict) and is the single runtime source.  Only dump the file
    # for the parity fixtures (--write-normalizer-stats) or the stats-only
    # dry-run (--stats-only implies it).
    stats_path = os.path.join(output, "normalizer_stats.yaml")
    if write_normalizer_stats or stats_only:
        with open(stats_path, "w") as f:
            yaml.dump({"normalization": norm_stats}, f, default_flow_style=None)
        print(f"Normalizer stats saved to: {stats_path}")
    else:
        print(f"[skip] normalizer_stats.yaml not written (debug flag "
              "--write-normalizer-stats off); deploy config normalization: "
              "block is the single runtime source.")

    if stats_only:
        return

    # ---- Identify actor ----
    actor = agent.actor
    actor_type = _actor_type_name(actor)
    print(f"\nActor type: {type(actor).__name__}  →  actor_type={actor_type!r}")

    obs_dim = agent.normalizer["obs"].params_dict["scale"].shape[0]
    print(f"obs_dim={obs_dim}  action_dim={actor.action_dim}  "
          f"n_past={actor.n_past_steps}  horizon={actor.horizon}  "
          f"denoising_steps={actor.denoising_steps}")
    contract = (_validate_prdp_export_contract(actor, norm_stats)
                if actor_type == "prdp" else {})
    if contract:
        print("PRDP checkpoint/model/profile contract: PASS")
    profile_resolution = OmegaConf.select(cfg, "_deploy_export.profile_resolution")
    if profile_resolution is None:
        profile_resolution = {}
    elif OmegaConf.is_config(profile_resolution):
        profile_resolution = OmegaConf.to_container(profile_resolution, resolve=True)
    else:
        profile_resolution = dict(profile_resolution)

    # ---- Derive obs_profile / use_fk / urdf_path (seeds the GUI advanced tab) ----
    if mode == "backbone" or gui:
        obs_profile, use_fk, urdf_path = _derive_deploy_args(
            actor_type, obs_dim, obs_profile, use_fk, urdf_path)

    # ---- Interactive config editor (--gui) ----
    _gui_result = None
    if gui:
        print("\n[gui] Launching the config editor (customtkinter)...")
        (_gui_result,
         (obs_profile, use_fk, urdf_path, output, deploy_config, device, mode,
          write_actor_config, write_normalizer_stats)) = _launch_gui_editor(
            cfg, obs_profile, use_fk, urdf_path, output, deploy_config, device,
            mode, write_actor_config, write_normalizer_stats)
        agent.to(device)  # idempotent re-apply if the GUI changed --device
        pathlib.Path(output).mkdir(parents=True, exist_ok=True)
        if mode != "backbone":
            print(f"[gui] mode overridden to {mode!r} by the editor.")

    # ---- Backbone export (reliable) ----
    if mode == "backbone":
        backbone = actor.backbone
        backbone.eval()
        if precision == "fp16":
            backbone.half()

        is_joint = actor_type in ("joint_diffusion", "diffuse_cloc", "prdp")

        # PRDP C++ fidelity gate. The C++ DiffuseCLoCActor implements every
        # sampler mode derive_sampler_mode can produce EXCEPT "full_ddpm"
        # (non-rolling full DDPM: fresh noise + full K-step DDPM every tick,
        # no warm-start rolling buffer). per-position NS-DDIM ("ns_ddim") and
        # per-position rolling DDIM ("rolling_ddim") ARE implemented in C++
        # (commit 5cf3649 "feat(deploy): WBG on DDIM paths + per-position
        # NS-DDIM and rolling-DDIM"); the old blanket gate that blocked
        # use_ns_ddim was stale. DiffusePRDP is still rejected by type because
        # its act() uses a distinct sampling path (per-position schedule modes
        # from_xt_*) that DiffuseCLoCActor does not mirror.
        sampler_mode = derive_sampler_mode({
            "use_ns_ddim": bool(getattr(actor, "use_ns_ddim", False)),
            "ddim_steps": getattr(actor, "ddim_steps", None),
            "randomize_noise_schedule": bool(getattr(actor, "randomize_noise_schedule", False)),
        })
        if actor_type == "prdp" and (
            type(actor).__name__ == "DiffusePRDP"
            or sampler_mode == "full_ddpm"
        ):
            if sampler_mode == "full_ddpm":
                raise click.ClickException(
                    "PRDP non-rolling full DDPM is not implemented in C++; "
                    "export scalar-DDIM, ns-DDIM, rolling-DDIM, or rolling-DDPM "
                    "inference semantics instead")
            raise click.ClickException(
                "DiffusePRDP uses per-position from_xt_ schedule semantics not "
                "implemented in C++; export a DiffuseCLoC/DiffuseCPRDP actor "
                "(scalar-DDIM / ns-DDIM / rolling-DDIM / rolling-DDPM) instead")

        print("\n[backbone mode] Tracing backbone network...")
        backbone.eval()
        torch.manual_seed(20260817)
        if is_joint:
            n_cond_steps = getattr(backbone, "n_cond_steps", actor.n_past_steps)
            trace_inputs = _joint_stream_inputs(
                backbone, n_cond_steps, actor.obs_dim, actor.action_dim, actor.horizon)
        else:
            trace_inputs = _single_stream_inputs(
                backbone, actor.n_past_steps, actor.horizon, actor.action_dim)
        trace_inputs = tuple(
            value.to(export_device, dtype=torch.float16)
            if value.is_floating_point() and precision == "fp16"
            else value.to(export_device)
            for value in trace_inputs
        )
        with torch.no_grad():
            reference_output = backbone(*trace_inputs)
        lowering = (lower_multihead_attention(backbone, attention_projection_packing)
                    if target == JETSON_JP5_TARGET else contextlib.nullcontext(0))
        with torch.no_grad(), lowering as lowered_count:
            lowered_output = backbone(*trace_inputs)
            lowered_error = _parity_error(lowered_output, reference_output)
            if is_joint:
                state_dim  = actor.obs_dim
                action_dim = actor.action_dim
                if condition_embedding_reuse:
                    scripted = _trace_condition_embedding_backbone(
                        backbone, trace_inputs)
                else:
                    scripted = _trace_joint_stream_backbone(
                        backbone, getattr(backbone, "n_cond_steps", actor.n_past_steps),
                        state_dim, action_dim, actor.horizon, trace_inputs=trace_inputs)
            else:
                action_dim = actor.action_dim
                scripted = _trace_single_stream_backbone(
                    backbone, actor.n_past_steps, obs_dim, actor.horizon, action_dim,
                    trace_inputs=trace_inputs)
            scripted_error = _parity_error(scripted(*trace_inputs), reference_output)

        if target == JETSON_JP5_TARGET:
            if lowered_count == 0:
                raise click.ClickException(
                    "jetson-jp5-torch21 export found no MultiheadAttention modules")
            assert_torch21_operators(scripted)
            print(f"  Lowered {lowered_count} MultiheadAttention modules to Torch 2.1 primitives")
            print(f"  Parity max_abs: lowered={lowered_error:.3e}, scripted={scripted_error:.3e}")

        out_path = os.path.join(output, "g1_policy_backbone.pt")
        scripted.save(out_path)
        print(f"Backbone saved to: {out_path}")

        compatibility_path = None
        if target == JETSON_JP5_TARGET:
            compatibility_path = os.path.join(output, "actor_compatibility.json")
            parity_atol, parity_rtol = parity_tolerances(precision)
            write_compatibility_manifest(
                scripted, out_path, compatibility_path, "jetson-jp5",
                parity={
                    "atol": parity_atol,
                    "rtol": parity_rtol,
                    "lowered_max_abs": lowered_error,
                    "scripted_max_abs": scripted_error,
                },
                input_schema=_input_schema(trace_inputs),
                profile_resolution=profile_resolution,
                contract=contract)
            print(f"Compatibility manifest saved to: {compatibility_path}")

        # ---- DDPM schedule tensors ----
        print("\nExporting DDPM schedule tensors...")
        schedule = compute_ddpm_schedule(actor.denoising_steps)
        schedule_path = os.path.join(output, "ddpm_schedule.pt")
        torch.jit.save(schedule, schedule_path)
        print(f"DDPM schedule saved to: {schedule_path}")
        K = actor.denoising_steps
        print(f"  denoising_steps={K}")

        # ---- DiffuseCLoC: emphasis matrices ----
        if actor_type in ("diffuse_cloc", "prdp"):
            print("\nExporting emphasis matrices...")
            emph_path = os.path.join(output, "emphasis_matrices.pt")
            _emph     = actor.emphasis_mat.detach().cpu().float().contiguous()
            _emph_inv = actor.emphasis_mat_inv.detach().cpu().float().contiguous()

            class EmphasisMatrices(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.register_buffer("emphasis_mat",     _emph)
                    self.register_buffer("emphasis_mat_inv", _emph_inv)

                def forward(self) -> torch.Tensor:
                    return self.emphasis_mat  # dummy

            torch.jit.save(torch.jit.script(EmphasisMatrices()), emph_path)
            print(f"Emphasis matrices saved to: {emph_path}")
            print(f"  emphasis_mat:     {list(actor.emphasis_mat.shape)}")
            print(f"  emphasis_mat_inv: {list(actor.emphasis_mat_inv.shape)}")

        # ---- Actor config YAML ----
        # Only the explicit --wbg-config CLI override is forwarded; the
        # checkpoint's embedded whole_body_guidance_config is read off the actor
        # inside _extract_actor_config, so the PRDP default applies when it is
        # absent or explicitly disabled (the common training state).
        _wbg_cfg = None
        if wbg_config is not None:
            with open(wbg_config, "r") as f:
                _wbg_cfg = yaml.safe_load(f) or {}
            print(f"WBG: --wbg-config override loaded from {wbg_config} "
                  f"(enabled={_wbg_cfg.get('enabled', False)})")
        configured_delay = OmegaConf.select(cfg, "env_runner.delay_action_step")
        delay_source = ("config" if configured_delay is not None
                        else "compatibility_default")
        delay_action_step = 0 if configured_delay is None else configured_delay
        from diffusion_policy.utils.action_selection import (
            action_selection, configure_actor_action_selection,
            terminal_action_noise_levels)
        try:
            configure_actor_action_selection(
                actor, int(actor.n_past_steps), delay_action_step)
            action_selection(
                int(actor.n_past_steps) - 1, delay_action_step,
                int(actor.horizon), terminal_action_noise_levels(actor))
        except (TypeError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        actor_cfg = _extract_actor_config(
            actor, actor_type, obs_dim, wbg_config=_wbg_cfg,
            delay_action_step=delay_action_step,
            delay_action_step_source=delay_source)
        if scalar_ddim:
            actor_cfg = _enable_scalar_ddim(actor_cfg)
            print("Sampler override: deterministic scalar_ddim")
        if condition_embedding_reuse and not is_joint:
            raise click.ClickException(
                "--condition-embedding-reuse requires a joint conditioned backbone")
        if ddim_precompute and (actor_cfg.get("ddim_steps", 0) <= 0
                                or actor_cfg.get("ddim_eta", 0.0) != 0.0):
            raise click.ClickException(
                "--ddim-precompute requires deterministic DDIM (steps>0, eta=0)")
        actor_cfg["attention_projection_packing"] = attention_projection_packing
        actor_cfg["condition_embedding_reuse"] = bool(condition_embedding_reuse)
        actor_cfg["ddim_precompute"] = bool(ddim_precompute)
        actor_cfg["defer_finite_checks"] = bool(defer_finite_checks)
        actor_cfg["inference_mode"] = bool(inference_mode)
        if actor_type == "prdp":
            cond_stats_dim = len(norm_stats.get("cond", {}).get("scale", []))
            if cond_stats_dim != actor_cfg["backbone_cond_dim"]:
                raise click.ClickException(
                    "PRDP condition normalizer/backbone mismatch: "
                    f"normalizer={cond_stats_dim}, backbone={actor_cfg['backbone_cond_dim']}. "
                    "Use the resolved checkpoint profile; do not alias incompatible current YAML.")
        actor_cfg["backbone_path"]  = os.path.abspath(out_path)
        actor_cfg["schedule_path"]  = os.path.abspath(schedule_path)
        if actor_type in ("diffuse_cloc", "prdp"):
            actor_cfg["emphasis_path"] = os.path.abspath(emph_path)

        # ---- Merge GUI edits into the actor config (--gui; GUI wins) ----
        if gui and _gui_result is not None:
            actor_cfg = _merge_gui_result(actor_cfg, _gui_result, write_wbg_config)
            try:
                configure_actor_action_selection(
                    actor, actor_cfg["n_obs_steps"],
                    actor_cfg.get("delay_action_step", 0))
                action_selection(
                    actor_cfg["n_obs_steps"] - 1,
                    actor_cfg.get("delay_action_step", 0), actor_cfg["horizon"],
                    terminal_action_noise_levels(actor))
            except (TypeError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
            actor_cfg["delay_action_step_source"] = "gui"
            if actor_type == "prdp":
                cond_stats_dim = len(norm_stats.get("cond", {}).get("scale", []))
                if cond_stats_dim != actor_cfg.get("backbone_cond_dim"):
                    raise click.ClickException(
                        "PRDP condition normalizer/backbone mismatch after GUI "
                        "edit: normalizer=" + str(cond_stats_dim) +
                        ", backbone=" + str(actor_cfg.get("backbone_cond_dim")) +
                        ". Use the resolved checkpoint profile; do not alias "
                        "incompatible current YAML.")

        if classifier_guidance_impl is not None:
            if actor_type not in ("diffuse_cloc", "prdp"):
                raise click.ClickException(
                    "--classifier-guidance-impl requires a DiffuseCLoC/PRDP actor")
            actor_cfg["classifier_guidance_impl"] = classifier_guidance_impl
            print("Classifier guidance implementation override: "
                  + classifier_guidance_impl)

        # ---- Optional debug actor config (NOT read by the C++ runtime) ----
        # The deploy config's model: block is a superset of actor_cfg and is the
        # single runtime source of truth. actor_config.yaml is only dumped when
        # --write-actor-config is passed (debugging / back-compat).
        actor_cfg_path = None
        if write_actor_config:
            actor_cfg_path = os.path.join(output, "actor_config.yaml")
            with open(actor_cfg_path, "w") as f:
                yaml.dump({"actor": actor_cfg}, f, default_flow_style=None)
            print(f"\nActor config saved to: {actor_cfg_path}  (debug only)")
        else:
            print("\n[skip] actor_config.yaml not written (debug flag "
                  "--write-actor-config off); deploy config is the single "
                  "runtime config.")

        # ---- Deploy config ----
        deploy_cfg_path = _write_deploy_config(
            output, actor_cfg, norm_stats, out_path, schedule_path,
            obs_profile=obs_profile, config_name=deploy_config,
            urdf_path=urdf_path, use_fk=use_fk,
            compatibility_path=compatibility_path,
            target_profile=("jetson-jp5" if target == JETSON_JP5_TARGET else "native"),
            precision=precision)
        print(f"Deploy config saved to: {deploy_cfg_path}")

        print("\n[backbone export done]")
        print(f"  backbone:    {out_path}")
        print(f"  schedule:    {schedule_path}")
        if write_normalizer_stats or stats_only:
            print(f"  normalizer:  {stats_path}  (debug only)")
        if actor_cfg_path:
            print(f"  actor_cfg:   {actor_cfg_path}  (debug only)")
        print(f"  deploy_cfg:  {deploy_cfg_path}  (single runtime config)")
        return

    # ---- Full-loop lazy export (may fail for DiffuseCLoC / JointDiffusion) ----
    print("\n[full_loop mode] Attempting lazy JIT capture of entire Python loop...")
    print("NOTE: This may fail for DiffuseCLoC / JointDiffusionActor due to")
    print("      abstract-type annotations and dynamic Python attributes.")
    print("      Use --mode backbone for a reliable export.")

    n_past      = actor.n_past_steps
    backbone_cond_dim = getattr(getattr(actor, 'backbone', None), 'cond_dim', obs_dim)
    has_motion_cond = backbone_cond_dim > obs_dim
    motion_dim = backbone_cond_dim - obs_dim if has_motion_cond else 0

    if has_motion_cond:
        print(f"  Detected motion conditioning: obs_dim={obs_dim}, "
              f"motion_dim={motion_dim}, backbone cond_dim={backbone_cond_dim}")

        class FullLoopWrapper(torch.nn.Module):
            def __init__(self, actor_):
                super().__init__()
                self.actor = actor_

            def forward(self, nobs_norm, motion_cond_norm):
                result = self.actor.act(nobs_norm, cond=motion_cond_norm)
                if isinstance(result, tuple):
                    return result[0]
                return result

        wrapper = FullLoopWrapper(actor).eval()
        example_obs  = torch.randn(1, n_past, obs_dim)
        example_cond = torch.randn(1, 1, motion_dim)
        trace_inputs = (example_obs, example_cond)
    else:
        class FullLoopWrapperUncond(torch.nn.Module):
            def __init__(self, actor_):
                super().__init__()
                self.actor = actor_

            def forward(self, nobs_norm):
                result = self.actor.act(nobs_norm)
                if isinstance(result, tuple):
                    return result[0]
                return result

        wrapper = FullLoopWrapperUncond(actor).eval()
        example_obs  = torch.randn(1, n_past, obs_dim)
        trace_inputs = (example_obs,)

    try:
        scripted = torch.jit.trace(wrapper, trace_inputs)
    except Exception as e:
        print(f"  trace() failed: {e}")
        print("  Falling back to script()...")
        scripted = torch.jit.script(wrapper)

    out_path = os.path.join(output, "g1_policy_full_loop.pt")
    scripted.save(out_path)
    print(f"Full-loop model saved to: {out_path}")
    if has_motion_cond:
        print(f"  NOTE: model takes TWO inputs: nobs[B,{n_past},{obs_dim}] "
              f"and motion_cond[B,1,{motion_dim}]")

    print("\nDone. Update config/g1_deploy_config.yaml with:")
    print(f"  model.path: {out_path}")
    print(f"  [paste normalizer stats from {stats_path}]")


if __name__ == "__main__":
    main()
