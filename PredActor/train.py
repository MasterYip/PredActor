import sys
# use line-buffering for both stdout and stderr
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', buffering=1)

import torch
torch.set_float32_matmul_precision('medium')
torch.backends.cuda.matmul.allow_tf32 = True

import hydra
from omegaconf import OmegaConf
import pathlib, os
import time

from diffusion_policy import DIFFUSION_POLICY_ROOT
from diffusion_policy.trainer.base_trainer import BaseTrainer
from diffusion_policy.utils.config_loader import load_config

OmegaConf.register_new_resolver("eval", eval, replace=True)

import argparse

parser = argparse.ArgumentParser(description='Process some integers.')

# diffusion policy arguments
parser.add_argument("--cfg", required=True, help="Name of the config file")
parser.add_argument("--exp_name", required=False, default='default_exp', help="exp name")
parser.add_argument("--gpu", type=int, default=None, help="GPU device ID (sets CUDA_VISIBLE_DEVICES + torch.cuda.set_device)")
parser.add_argument("--resume-output-dir", default=None, help="Existing DAgger output directory to resume")
parser.add_argument('overrides', nargs='*', default=[], help='OmegaConf dot-path overrides (e.g. logging.mode=offline policy.actor.backbone.cross_attn_window=0)')

# parse the arguments
args_cli = parser.parse_args()

# ── GPU device selection ────────────────────────────────────────────
if args_cli.gpu is not None:
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args_cli.gpu)
    torch.cuda.set_device(0)  # device 0 after CUDA_VISIBLE_DEVICES remapping
    print(f"[train.py] GPU set to device {args_cli.gpu} (CUDA_VISIBLE_DEVICES={args_cli.gpu})")

def main():
    # resolve immediately so all the ${now:} resolvers
    # will use the same time.
    cfg: OmegaConf = load_config(os.path.join(DIFFUSION_POLICY_ROOT, './config_files', args_cli.cfg))
    # Apply CLI overrides (key=value pairs)
    for override in args_cli.overrides:
        key, _, value = override.partition("=")
        if not value:
            continue
        # Convert string values to appropriate types
        if value == "null":
            value = None
        elif value == "true":
            value = True
        elif value == "false":
            value = False
        else:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
        OmegaConf.update(cfg, key, value, merge=False)
        print(f"[train.py] Override: {key}={value}")
    OmegaConf.resolve(cfg)

    # Derive the stem from the basename so `--cfg` works with either a bare
    # config name (g1prdp_diffuse.yaml) or an absolute path to a recorded
    # experiment config.yaml.  This keeps output_dir names sane.
    cfg_stem = os.path.splitext(os.path.basename(args_cli.cfg))[0]
    cfg.exp_name = cfg_stem + "-" + args_cli.exp_name
    if args_cli.resume_output_dir:
        output = pathlib.Path(args_cli.resume_output_dir).resolve()
        checkpoint = OmegaConf.select(cfg, "dagger.resume_checkpoint")
        if not checkpoint or not output.is_dir() or not pathlib.Path(checkpoint).is_file():
            raise ValueError("resume output requires an existing directory and DAgger checkpoint")
        if not (output / "resolved_config.yaml").is_file():
            raise ValueError("resume output lacks its original resolved config")
        cfg.output_dir = str(output)
    else:
        cfg.output_dir = os.path.join(cfg.output_dir, time.strftime("%B-%d-%H-%M-%S", time.localtime()) + "-" + cfg.exp_name)
    os.makedirs(cfg.output_dir, exist_ok=True)

    # Save the fully-resolved config (with all defaults composed and CLI
    # overrides baked in) for reproducible evaluation.  This file can be
    # passed directly to cond_eval.py --config.
    if not args_cli.resume_output_dir:
        OmegaConf.save(cfg, os.path.join(cfg.output_dir, "resolved_config.yaml"))
    print(f"[train.py] Resolved config saved to {cfg.output_dir}/resolved_config.yaml")

    # ── Force-disable ALL guidance during training ──────────────────────
    try:
        actor = cfg.policy.actor
        if hasattr(actor, 'enable_root_pos_guide'):
            actor.enable_root_pos_guide = False
        stack = [(actor, 'policy.actor')]
        while stack:
            node, path = stack.pop()
            try:
                items = node.items()
            except Exception:
                continue
            for k, v in items:
                if k == 'enabled' and isinstance(v, bool) and v:
                    node[k] = False
                    print(f"[train.py] Forced {path}.enabled=false for training.")
                elif k != 'enabled':
                    try:
                        _ = v.items
                        stack.append((v, f"{path}.{k}"))
                    except Exception:
                        pass
    except Exception:
        pass

    cls = hydra.utils.get_class(cfg._target_)
    trainer: BaseTrainer = cls(cfg)
    
    trainer.train(args_cli)

if __name__ == "__main__":
    main()
