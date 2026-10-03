from __future__ import annotations
import copy
from typing import Optional, Tuple, Union, Dict

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time 

from diffusion_policy.modules import *
# from diffusion_policy.utils.sdf import * 

from diffusion_policy.agent.base_agent import BaseAgent
from diffusion_policy.utils.module_dict import ModuleDict
from diffusion_policy.utils.traj_utils import quat_from_euler_xyz, get_euler_xyz, quat_mul, quat_rotate, box_minus, quat_rotate_inverse, box_plus, quat_conjugate
from diffusion_policy.trainer.cond_dropout import AdaptiveConditionDropout, PerTermConditionDropout

try:
    from diffusion_policy.utils.live_visualizer_pyg import LivePlotVisualizerPygame
except:
    print("Plot Visualizer NOT INSTALLED")


class BCAgent(BaseAgent):
    def __init__(
        self,
        actor: BaseActor,
        condition_dropout_config: Dict = None,
        task_mask_config: Dict = None,
        cond_compressor: Dict = None,
        **kwargs,
    ):
        """
        Initialize BCAgent with optional Adaptive Condition Dropout, Task Mask,
        and Condition Compressor.

        Args:
            actor: The actor model (e.g., DiffuseCLoC)
            condition_dropout_config: Configuration dict for AdaptiveConditionDropout
                (semantic robustness — corrupts the full condition for classifier-free guidance)
                Keys: 'enable', 'initial_prob', 'final_prob', 'warmup_steps',
                       'dropout_type', 'noise_std'
            task_mask_config: Configuration dict for TaskMaskGenerator
                (task controllability — per-term binary mask fed to the policy network)
                Keys: 'enable', 'terms': {term_name: {enabled, initial_prob, final_prob, warmup_steps}}
            cond_compressor: Configuration dict for CondCompressor
                (trainable MLP to compress condition before dropout/mask)
                Keys: 'enable', 'input_dim', 'output_dim', 'hidden_dim',
                       'num_layers', 'activation', 'dropout'
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(
            actor=actor,
        )

        # Initialize condition compressor if enabled (applied BEFORE dropout/mask)
        self.cond_compressor = None
        if cond_compressor is not None and cond_compressor.get('enable', False):
            from diffusion_policy.modules.cond_compressor import CondCompressor
            cc = cond_compressor
            self.cond_compressor = CondCompressor(
                input_dim=cc.get('input_dim'),
                output_dim=cc.get('output_dim'),
                hidden_dim=cc.get('hidden_dim'),
                num_layers=cc.get('num_layers', 2),
                activation=cc.get('activation', 'mish'),
                dropout=cc.get('dropout', 0.0),
            )
            print(f"[BCAgent] Condition Compressor Enabled: {cond_compressor}")

        # Initialize condition dropout if enabled
        self.condition_dropout = None
        if condition_dropout_config is not None and condition_dropout_config.get('enable', False):
            self.condition_dropout = AdaptiveConditionDropout(
                initial_prob=condition_dropout_config.get('initial_prob', 0.1),
                final_prob=condition_dropout_config.get('final_prob', 0.3),
                warmup_steps=condition_dropout_config.get('warmup_steps', 50000),
                dropout_type=condition_dropout_config.get('dropout_type', 'null'),
                noise_std=condition_dropout_config.get('noise_std', 0.1),
                seed=condition_dropout_config.get('seed', 0),
                clip_latent_dim=condition_dropout_config.get('clip_latent_dim', 0),
            )
            print(f"[BCAgent] Condition Dropout Enabled: {condition_dropout_config}")

        # Initialize task mask generator if enabled.
        # If task_mask_config has no mask_config_train/mask_config_infer keys (i.e. just
        # `enable: true`), the generator is created now with empty term configs and the
        # trainer will call set_task_mask_from_profile() after the dataset is loaded to
        # populate schedules from the dataset's DataProfile — avoiding duplication.
        self.task_mask_gen = None
        self._task_mask_enable = (
            task_mask_config is not None and task_mask_config.get('enable', False)
        )
        if self._task_mask_enable:
            from diffusion_policy.trainer.task_mask import TaskMaskGenerator
            self.task_mask_gen = TaskMaskGenerator.from_config(task_mask_config)
            print(f"[BCAgent] Task Mask Enabled: {task_mask_config}")

        # Per-term condition dropout (applied before task mask).
        # Populated via set_dropout_from_profile() after the dataset is loaded.
        self.per_term_dropout: Optional[PerTermConditionDropout] = None
        self._pending_per_term_dropout_state = None

    def test_mode(self):
        pass

    def train_mode(self):
        pass

    def set_task_mask_boundaries(self, term_boundaries) -> None:
        """Wire TermComposer's cond_term_boundaries into the TaskMaskGenerator.

        Called by the trainer after the dataset is created.
        """
        if self.task_mask_gen is not None:
            self.task_mask_gen.set_term_boundaries(term_boundaries)
        if self.per_term_dropout is not None:
            self.per_term_dropout.set_term_boundaries(term_boundaries)

    def set_task_mask_from_profile(self, task_condition) -> None:
        """Populate task mask schedules from the dataset's DataProfile.task_condition.

        Called by the trainer when the experiment YAML only specifies
        ``task_mask_config: enable: true`` without repeating mask_config_train /
        mask_config_infer (those live in the dataset profile YAML instead).

        Args:
            task_condition: ``DataProfile.task_condition`` (a TermGroupConfig).
        """
        if self.task_mask_gen is None or not self._task_mask_enable:
            return
        # Only fill in if the generator was created with empty term configs
        if self.task_mask_gen.term_configs:
            return  # explicit per-term config in the policy YAML takes precedence

        from diffusion_policy.trainer.task_mask import TermMaskEntry
        for term_name, entry in task_condition.mask_config_train.items():
            self.task_mask_gen.term_configs[term_name] = TermMaskEntry(
                enabled=entry.enabled,
                initial_prob=entry.initial_prob,
                final_prob=entry.final_prob,
                warmup_steps=entry.warmup_steps,
                mask_mode=getattr(entry, "mask_mode", "full_term"),
            )
        # Always refresh from the profile so edits to mask_config_infer in the
        # dataset YAML take effect at eval time regardless of what was in the checkpoint.
        self.task_mask_gen._default_infer_active = dict(task_condition.mask_config_infer)
        print("[BCAgent] Task mask schedules loaded from dataset profile.")

    def set_dropout_from_profile(self, task_condition) -> None:
        """Create and wire PerTermConditionDropout from the dataset profile.

        Called by the trainer after the dataset is created, alongside
        set_task_mask_from_profile().  A non-empty dropout_config_train in
        the profile is sufficient to enable per-term dropout; no extra flag
        is needed.

        Args:
            task_condition: DataProfile.task_condition (a TermGroupConfig).
        """
        if not task_condition.dropout_config_train:
            return
        from diffusion_policy.trainer.cond_dropout import TermDropoutEntry
        self.per_term_dropout = PerTermConditionDropout(
            term_configs={
                name: TermDropoutEntry(
                    enabled=entry.enabled,
                    initial_prob=entry.initial_prob,
                    final_prob=entry.final_prob,
                    warmup_steps=entry.warmup_steps,
                    dropout_type=entry.dropout_type,
                    noise_std=entry.noise_std,
                )
                for name, entry in task_condition.dropout_config_train.items()
            },
            term_boundaries=[],  # boundaries wired via set_task_mask_boundaries()
        )
        if self._pending_per_term_dropout_state is not None:
            self.per_term_dropout.load_state_dict(
                self._pending_per_term_dropout_state
            )
            self._pending_per_term_dropout_state = None
        print("[BCAgent] Per-term condition dropout loaded from dataset profile.")

    def _apply_task_mask(self, ncond: torch.Tensor, batch_size: int, training: bool):
        """Apply task mask and concatenate mask vector onto ncond.

        Returns the augmented condition [B, T, 2*cond_dim] if task mask is
        enabled, otherwise returns ncond unchanged.
        """
        if self.task_mask_gen is None or not self.task_mask_gen.term_boundaries:
            return ncond

        if training:
            mask = self.task_mask_gen.sample_mask(batch_size, ncond.device)  # [B, cond_dim]
        else:
            # Inference: caller may pass active_terms via obs_dict; handled in act()
            return ncond  # placeholder; act() handles inference masking directly

        ncond = self.task_mask_gen.apply(ncond, mask)
        T_cond = ncond.shape[1]
        mask_exp = mask.unsqueeze(1).expand(-1, T_cond, -1)  # [B, T_cond, cond_dim]
        return torch.cat([ncond, mask_exp], dim=-1)  # [B, T_cond, 2*cond_dim]
    
    @torch.no_grad()
    def act(self, obs_dict):

        from diffusion_policy.utils.precision import autocast_context

        # Normalization and returned control/state values stay FP32. Only the
        # learned actor forward is eligible for CUDA autocast.
        obs = self.normalizer['obs'].normalize(obs_dict['obs'].float())

        # Extract optional conditioning
        cond = obs_dict.get('cond', None)
        if cond is not None:
            cond = self.normalizer['cond'].normalize(cond.float())

            # Apply condition compressor (trainable dimensionality reduction).
            # Applied BEFORE task mask so the mask operates on compressed dims.
            if self.cond_compressor is not None:
                cond = self.cond_compressor(cond)

            # Apply task mask at inference time
            if self.task_mask_gen is not None and self.task_mask_gen.term_boundaries:
                active_terms = obs_dict.get('active_terms', None)
                mask = self.task_mask_gen.inference_mask(active_terms, cond.device)  # [cond_dim]
                mask = mask.unsqueeze(0)  # [1, cond_dim]
                cond = self.task_mask_gen.apply(cond, mask)
                T_cond = cond.shape[1]
                mask_exp = mask.unsqueeze(1).expand(cond.shape[0], T_cond, -1)
                cond = torch.cat([cond, mask_exp], dim=-1)  # [B, T_cond, 2*cond_dim]
                print("mask:", mask_exp[0, 0, :6])
                print("cond:", cond[0, 0, :6])

        with autocast_context(self.inference_precision, obs.device):
            output = self.actor.act(obs, cond=cond)

        if isinstance(self.actor, JointDiffusionActor):
            naction_pred, nstate_pred = output
        
            action_pred = self.normalizer['action'].unnormalize(naction_pred.float())
            state_pred = self.normalizer['obs'].unnormalize(nstate_pred.float())
            # global_body_pos, root_rot_global = self.dataset_class.state_unnormalize(state_pred.clone(), obs_dict['global_root'], return_rot=True)
            # body_pos = self.dataset_class.state_unnormalize(state_pred.clone(), return_rot=False)
            
            return action_pred, state_pred, None #global_body_pos, body_pos #, #state_pred #body_pos
        
        elif isinstance(self.actor, DiffusionActor):
            naction_pred = output
            action_pred = self.normalizer['action'].unnormalize(naction_pred.float())

            return action_pred
    
        elif isinstance(self.actor, TransActor):
            naction_pred = output
            action_pred = self.normalizer['action'].unnormalize(naction_pred.float())
            return action_pred
        else:
            raise NotImplementedError

    def get_optimizer(
            self, **kwargs
        ) -> Dict[str, torch.optim.Optimizer]:

        optimizer = dict()

        if isinstance(self.actor, (DiffusionActor, JointDiffusionActor, TransActor)):
            opt = self.actor.get_optimizer(**kwargs)
            if self.cond_compressor is not None:
                wd = kwargs.get('weight_decay', 1e-3)
                opt.add_param_group({
                    'params': self.cond_compressor.parameters(),
                    'weight_decay': wd,
                })
            optimizer.update({'diffusion': opt})

        return ModuleDict(optimizer)

    def compute_loss(self, batch, local_epoch_idx, return_loss_components=False):
        B = batch['obs'].shape[0]

        nbatch = self.normalizer.normalize(batch)

        nobs = nbatch['obs']
        naction = nbatch['action']
        
        # Extract optional conditioning
        ncond = nbatch.get('cond', None)

        # 0. Apply condition compressor (trainable dimensionality reduction).
        #    Applied BEFORE dropout/mask so the compressor sees clean normalized values.
        if ncond is not None and self.cond_compressor is not None:
            ncond = self.cond_compressor(ncond)

        # 1. Apply per-term condition dropout (semantic robustness per term).
        #    Applied before the task mask so noise/null is injected into raw values.
        if ncond is not None and self.per_term_dropout is not None:
            ncond = self.per_term_dropout(ncond, training=True)

        # 2. (legacy) Apply legacy full-condition Adaptive Condition Dropout if still configured.
        if ncond is not None and self.condition_dropout is not None:
            ncond = self.condition_dropout(ncond, training=True)

        # 3. Apply task mask (controllability) — zeroes inactive terms and appends mask vector.
        #    Applied after dropout so the mask always reflects intent, not noise.
        if ncond is not None and self.task_mask_gen is not None:
            ncond = self._apply_task_mask(ncond, B, training=True)
            self.task_mask_gen.step()
        if ncond is not None and self.per_term_dropout is not None:
            self.per_term_dropout.step()

        loss_dict = {}

        B = nobs.shape[0]
        device = nobs.device

        if isinstance(self.actor, JointDiffusionActor):
            loss_result = self.actor.p_losses(
                action_traj=naction,
                state_traj=nobs,
                cond=ncond,
                return_loss_components=return_loss_components,
            )
            loss, action_loss, state_loss, action_pred, state_pred = loss_result[:5]

            dropout_log = {}
            if self.condition_dropout is not None:
                dropout_log['cond_dropout_prob'] = np.float32(self.condition_dropout.get_dropout_prob())
                dropout_log['cond_dropout_step'] = np.float32(self.condition_dropout.current_step)

            loss_dict.update(
                {
                    'diffusion': loss.mean(),
                    "grad_analysis": {
                        "action_pred": action_pred,
                        "state_pred": state_pred,
                    },
                    "log": {
                        "action_loss": np.sqrt(action_loss.detach().cpu()),
                        "state_loss": np.sqrt(state_loss.detach().cpu()),
                        **dropout_log,
                    }
                }
            )
            if return_loss_components:
                loss_dict["loss_components"] = loss_result[5]
            yield loss_dict

        elif isinstance(self.actor, CondCoDiffuseActor):
            loss, action_loss, state_loss, action_pred, state_pred = self.actor.p_losses(
                action_traj=naction, state_traj=nobs, cond=ncond)

            dropout_log = {}
            if self.condition_dropout is not None:
                dropout_log['cond_dropout_prob'] = np.float32(self.condition_dropout.get_dropout_prob())
                dropout_log['cond_dropout_step'] = np.float32(self.condition_dropout.current_step)

            loss_dict.update(
                {
                    'diffusion': loss.mean(),
                    "grad_analysis": {
                        "action_pred": action_pred,
                        "state_pred": state_pred,
                    },
                    "log": {
                        "action_loss": np.sqrt(action_loss.detach().cpu()),
                        "state_loss": np.sqrt(state_loss.detach().cpu()),
                        **dropout_log,
                    }
                }
            )
            yield loss_dict

        elif isinstance(self.actor, DiffusionActor):
            # For DiffusionActor, only pass n_past_steps observations
            nobs_past = nobs[:, :self.actor.n_past_steps]
            loss = self.actor.p_losses(trajectory=naction, cond=nobs_past, motion_cond=ncond)

            # Log dropout progress if enabled
            dropout_log = {}
            if self.condition_dropout is not None:
                dropout_log['cond_dropout_prob'] = np.float32(self.condition_dropout.get_dropout_prob())
                dropout_log['cond_dropout_step'] = np.float32(self.condition_dropout.current_step)

            loss_dict.update(
                {
                    'diffusion': loss.mean(),
                    "log": dropout_log
                }
            )
            yield loss_dict

        elif isinstance(self.actor, TransActor):
            # For TransActor, slice obs to n_past_steps and call p_losses directly
            nobs_past = nobs[:, :self.actor.n_past_steps]
            loss = self.actor.p_losses(trajectory=naction, cond=nobs_past, motion_cond=ncond)

            dropout_log = {}
            if self.condition_dropout is not None:
                dropout_log['cond_dropout_prob'] = np.float32(self.condition_dropout.get_dropout_prob())
                dropout_log['cond_dropout_step'] = np.float32(self.condition_dropout.current_step)

            loss_dict.update(
                {
                    'diffusion': loss.mean(),
                    "log": dropout_log
                }
            )
            yield loss_dict
    
    def state_dict(self) -> Dict:
        """Get agent state for checkpointing."""
        state = super().state_dict() if hasattr(super(), 'state_dict') else {}
        if self.condition_dropout is not None:
            state['condition_dropout'] = self.condition_dropout.state_dict()
        if self.task_mask_gen is not None:
            state['task_mask_gen'] = self.task_mask_gen.state_dict()
        if self.per_term_dropout is not None:
            state['per_term_dropout'] = self.per_term_dropout.state_dict()
        elif self._pending_per_term_dropout_state is not None:
            state['per_term_dropout'] = copy.deepcopy(
                self._pending_per_term_dropout_state
            )
        return state

    def load_state_dict(self, state: Dict, strict: bool = False) -> None:
        """Load agent state from checkpoint.

        Checkpoints in this repo evolve over time as actor buffers and optional
        conditioning modules are added or removed.  Default to non-strict loading
        so older checkpoints remain usable for evaluation.
        """
        state = dict(state)

        if 'condition_dropout' in state:
            if self.condition_dropout is not None:
                self.condition_dropout.load_state_dict(state['condition_dropout'])
            state.pop('condition_dropout', None)
        if 'task_mask_gen' in state:
            if self.task_mask_gen is not None:
                self.task_mask_gen.load_state_dict(state['task_mask_gen'])
            state.pop('task_mask_gen', None)
        if 'per_term_dropout' in state:
            if self.per_term_dropout is not None:
                self.per_term_dropout.load_state_dict(state['per_term_dropout'])
            else:
                self._pending_per_term_dropout_state = copy.deepcopy(
                    state['per_term_dropout']
                )
            state.pop('per_term_dropout', None)

        if hasattr(super(), 'load_state_dict'):
            incompatible = super().load_state_dict(state, strict=strict)
            if (incompatible.missing_keys or incompatible.unexpected_keys) and not strict:
                print(
                    "[BCAgent] Non-strict checkpoint load: "
                    f"missing={incompatible.missing_keys[:8]} "
                    f"unexpected={incompatible.unexpected_keys[:8]}"
                )
