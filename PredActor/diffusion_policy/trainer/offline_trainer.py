import os
import hydra
import torch
from omegaconf import OmegaConf
import pathlib
from torch.utils.data import DataLoader
import copy
import random
import wandb
import tqdm
import numpy as np
import shutil

import zarr
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.widgets import Slider
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Slider, RadioButtons # Import RadioButtons


from diffusion_policy.utils.pytorch_util import dict_apply, optimizer_to
from diffusion_policy.trainer.base_trainer import BaseTrainer
from diffusion_policy.agent.base_agent import BaseAgent
from diffusion_policy.dataset.offline_dataset import OfflineDataset
from diffusion_policy.trainer.lr_scheduler import get_scheduler
from diffusers.training_utils import EMAModel
from diffusion_policy.trainer.normalizer import LinearNormalizer
from diffusion_policy.trainer.normalizer_sampling import fit_training_normalizer
from diffusion_policy.trainer.bc_training_step import run_bc_training_step
from diffusion_policy.dataset.g1_dataset import TermComposer
from diffusion_policy.utils.precision import (
    make_grad_scaler,
    normalize_precision,
    validate_precision_device,
)

OmegaConf.register_new_resolver("eval", eval, replace=True)

# ===================================================================
# 1. DEFINE YOUR NAMES and GENERATE LABELS
# ===================================================================
BODY_NAMES = [
    "pelvis", "left_hip_pitch_link", "right_hip_pitch_link", "waist_yaw_link",
    "left_hip_roll_link", "right_hip_roll_link", "waist_roll_link", "left_hip_yaw_link",
    "right_hip_yaw_link", "torso_link", "left_knee_link", "right_knee_link",
    "left_shoulder_pitch_link", "right_shoulder_pitch_link", "left_ankle_pitch_link",
    "right_ankle_pitch_link", "left_shoulder_roll_link", "right_shoulder_roll_link",
    "left_ankle_roll_link", "right_ankle_roll_link", "left_shoulder_yaw_link",
    "right_shoulder_yaw_link", "left_elbow_link", "right_elbow_link",
    "left_wrist_roll_link", "right_wrist_roll_link", "left_wrist_pitch_link",
    "right_wrist_pitch_link", "left_wrist_yaw_link", "right_wrist_yaw_link",
]
JOINT_NAMES = [
    "left_hip_pitch_joint", "right_hip_pitch_joint", "waist_yaw_joint", "left_hip_roll_joint",
    "right_hip_roll_joint", "waist_roll_joint", "left_hip_yaw_joint", "right_hip_yaw_joint",
    "waist_pitch_joint", "left_knee_joint", "right_knee_joint", "left_shoulder_pitch_joint",
    "right_shoulder_pitch_joint", "left_ankle_pitch_joint", "right_ankle_pitch_joint",
    "left_shoulder_roll_joint", "right_shoulder_roll_joint", "left_ankle_roll_joint",
    "right_ankle_roll_joint", "left_shoulder_yaw_joint", "right_shoulder_yaw_joint",
    "left_elbow_joint", "right_elbow_joint", "left_wrist_roll_joint",
    "right_wrist_roll_joint", "left_wrist_pitch_joint", "right_wrist_pitch_joint",
    "left_wrist_yaw_joint", "right_wrist_yaw_joint",
]

# --- Place the function definition here ---

def generate_correct_obs_labels(body_names):
    """
    Generates observation labels based ONLY on the body/root features.
    """
    obs_labels = []
    
    # Order based on your provided feature list:
    # 1. body_pos_local
    for body_name in body_names:
        for dim in ['pos_x', 'pos_y', 'pos_z']:
            obs_labels.append(f"{body_name}_{dim}")
            
    # 2. body_lin_vel_local
    for body_name in body_names:
        for dim in ['vel_x', 'vel_y', 'vel_z']:
            obs_labels.append(f"{body_name}_{dim}")

    # 3. root_pos_local
    for dim in ['x', 'y', 'z']:
        obs_labels.append(f"root_pos_{dim}")

    # 4. root_rot_local
    for dim in ['rx', 'ry', 'rz']:
        obs_labels.append(f"root_rot_{dim}")

    # 5. root_lin_vel_local
    for dim in ['vx', 'vy', 'vz']:
        obs_labels.append(f"root_vel_{dim}")

    # 6. root_ang_vel_local
    for dim in ['wx', 'wy', 'wz']:
        obs_labels.append(f"root_ang_vel_{dim}")
        
    return obs_labels
    
class OfflineTrainer(BaseTrainer):
    include_keys = ['global_step', 'epoch']

    def __init__(self, cfg: OmegaConf, output_dir=None,init_wandb=True):
        super().__init__(cfg, output_dir=output_dir,init_wandb=init_wandb)
        # set seed
        seed = cfg.training.seed
        torch.manual_seed(seed)
        np.random.seed(seed)
        random.seed(seed)

        # configure model
        self.agent: BaseAgent
        self.agent = hydra.utils.instantiate(cfg.policy)

        self.ema_agent = None
        if cfg.training.use_ema:
            try:
                self.ema_agent = copy.deepcopy(self.agent)
            except Exception as e:
                print(f"Warning: Failed to create EMA agent: {e}")

        # configure training state
        self.optimizer = self.agent.get_optimizer(**cfg.optimizer)

        self.precision = normalize_precision(cfg.training.get('precision', 'fp32'))
        precision_device = validate_precision_device(self.precision, cfg.training.device)
        self.grad_scaler = make_grad_scaler(self.precision, precision_device)

        self.global_step = 0
        self.epoch = 0
        self.obs_composer = None

    def _run_training_batch(
        self,
        batch,
        local_epoch_idx,
        lr_scheduler,
        device,
        *,
        capture_audit=False,
    ):
        return run_bc_training_step(
            agent=self.agent,
            optimizers=self.optimizer,
            schedulers=lr_scheduler,
            batch=batch,
            local_epoch_idx=local_epoch_idx,
            global_step=self.global_step,
            gradient_accumulate_every=self.cfg.training.gradient_accumulate_every,
            precision=self.precision,
            device=device,
            grad_scaler=self.grad_scaler,
            capture_audit=capture_audit,
        )

    def load_payload(self, payload, exclude_keys=None, include_keys=None, **kwargs):
        super().load_payload(
            payload,
            exclude_keys=exclude_keys,
            include_keys=include_keys,
            **kwargs,
        )
        for key in self.include_keys:
            if key in payload.get("pickles", {}):
                import dill
                setattr(self, key, dill.loads(payload["pickles"][key]))


    def plot_saliency_map(self, target_T, target_D, jacobian_data, obs_labels, act_labels):
        """
        Plots the saliency map for a specific target action component.
        """
        # Select the pre-computed gradient data
        gradient_map = jacobian_data[target_T, target_D]
        
        plt.figure(figsize=(12, 8))
        ax = sns.heatmap(
            gradient_map, 
            cmap='RdBu_r', # Red-Blue diverging colormap
            center=0,     # Center the color map at zero
            xticklabels=obs_labels,
            yticklabels=[f"t-{i}" for i in range(jacobian_data.shape[2]-1, -1, -1)]
        )
        
        ax.set_title(f"Influence on Action '{act_labels[target_D]}' at Timestep t+{target_T}")
        ax.set_xlabel("Observation Features (Input State)")
        ax.set_ylabel("Input History")
        plt.show()

    def load_for_eval(self, dataset_path=None):
        """
        Load dataset and set normalizer for evaluation.
        This should be called after loading checkpoint to properly initialize normalizer.
        Only loads from dataset if normalizer wasn't already loaded from checkpoint.
        
        Args:
            dataset_path: Optional path to dataset. If None, uses cfg.dataset_dir + cfg.dataset.zarr_path
        """
        # Check if normalizer was already loaded from checkpoint
        if hasattr(self.agent, 'normalizer') and self.agent.normalizer is not None:
            print("Normalizer already loaded from checkpoint, skipping dataset load")
            return self.agent.normalizer
        
        print("Normalizer not found in checkpoint, loading from dataset...")
        cfg = copy.deepcopy(self.cfg)
        
        # Configure dataset
        cfg.dataset.horizon = self.agent.horizon
        cfg.dataset.n_past_steps = self.agent.n_past_steps
        
        if dataset_path is not None:
            cfg.dataset.zarr_path = dataset_path
        else:
            cfg.dataset.zarr_path = os.path.join(cfg.dataset_dir, cfg.dataset.zarr_path)
        
        # Load dataset
        dataset: OfflineDataset = hydra.utils.instantiate(cfg.dataset)
        assert isinstance(dataset, OfflineDataset)
        
        # Get and set normalizer with configured sample rate
        normalizer = fit_training_normalizer(dataset, cfg.dataset)
        self.agent.set_normalizer(normalizer)
        self.agent.set_dataset_class(dataset.__class__)
        if hasattr(dataset, 'term_composer'):
            self.obs_composer = dataset.term_composer
            for _agent in [self.agent, self.ema_agent if cfg.training.use_ema else None]:
                if _agent is not None and hasattr(_agent, 'set_task_mask_from_profile'):
                    _agent.set_task_mask_from_profile(dataset.data_profile.task_condition)
                if _agent is not None and hasattr(_agent, 'set_dropout_from_profile'):
                    _agent.set_dropout_from_profile(dataset.data_profile.task_condition)
                # Boundaries must be wired last so both task_mask_gen and
                # per_term_dropout (created above) receive them in one call.
                if _agent is not None and hasattr(_agent, 'set_task_mask_boundaries'):
                    _agent.set_task_mask_boundaries(dataset.term_composer.cond_term_boundaries)
        else:
            self.obs_composer = None
        
        if cfg.training.use_ema and self.ema_agent is not None:
            self.ema_agent.set_normalizer(normalizer)
            self.ema_agent.set_dataset_class(dataset.__class__)
        
        print(f"Loaded normalizer from dataset: {cfg.dataset.zarr_path}")
        print(f"Normalizer type: {type(normalizer).__name__}")
        
        return normalizer

    def train(self, args_cli):
        cfg = copy.deepcopy(self.cfg)

        # configure dataset
        dataset: OfflineDataset
        # FIXME: param override occur here.
        cfg.dataset.horizon = self.agent.horizon
        cfg.dataset.n_obs_steps = self.agent.n_past_steps

        cfg.dataset.zarr_path = os.path.join(cfg.dataset_dir, cfg.dataset.zarr_path)
        dataset = hydra.utils.instantiate(cfg.dataset)
        assert isinstance(dataset, OfflineDataset)
        dl_kwargs = dict(cfg.dataloader)
        if (
            'worker_init_fn' not in dl_kwargs
            and hasattr(dataset, 'worker_init_fn')
            and not getattr(dataset, '_load_to_memory', False)
        ):
            dl_kwargs['worker_init_fn'] = dataset.worker_init_fn
        train_dataloader = DataLoader(dataset, collate_fn=dataset.collate_fn, **dl_kwargs)
        
        # Get normalizer with configured sample rate to reduce RAM usage
        normalizer = fit_training_normalizer(dataset, cfg.dataset)
        self.agent.set_normalizer(normalizer)
        self.agent.set_dataset_class(dataset.__class__)
        if cfg.training.use_ema and self.ema_agent is not None:
            self.ema_agent.set_normalizer(normalizer)
            self.ema_agent.set_dataset_class(dataset.__class__)

        # Wire task mask term boundaries from the dataset's TermComposer
        if hasattr(dataset, 'term_composer'):
            for _agent in [self.agent, self.ema_agent]:
                if _agent is not None and hasattr(_agent, 'set_task_mask_from_profile'):
                    _agent.set_task_mask_from_profile(dataset.data_profile.task_condition)
                if _agent is not None and hasattr(_agent, 'set_dropout_from_profile'):
                    _agent.set_dropout_from_profile(dataset.data_profile.task_condition)
                # Boundaries must be wired last so both task_mask_gen and
                # per_term_dropout (created above) receive them in one call.
                if _agent is not None and hasattr(_agent, 'set_task_mask_boundaries'):
                    _agent.set_task_mask_boundaries(dataset.term_composer.cond_term_boundaries)


        # resume training
        if cfg.training.resume:
            # lastest_ckpt_path = pathlib.Path(cfg.training.resume_path).joinpath('checkpoints', 'latest.ckpt')

            payload = self.load_wandb_checkpoint(cfg.training.resume_path)
            # import ipdb;ipdb.set_trace()
            self.load_payload(payload)

        # configure validation dataset
        val_dataset = dataset.get_validation_dataset()
        val_dataloader = DataLoader(val_dataset, **cfg.val_dataloader)

        # configure lr scheduler
        lr_scheduler = {}
        for key in self.optimizer.keys():
        
            lr_scheduler[key] = get_scheduler(
                cfg.training.lr_scheduler,
                optimizer=self.optimizer[key],
                num_warmup_steps=cfg.training.lr_warmup_steps,
                num_training_steps=(
                    len(train_dataloader) * cfg.training.num_epochs) \
                        // cfg.training.gradient_accumulate_every,
                # pytorch assumes stepping LRScheduler every epoch
                # however huggingface diffusers steps it every batch
                last_epoch=-1
            )

        # configure ema
        ema: EMAModel = None
        if cfg.training.use_ema:
            ema = hydra.utils.instantiate(
                cfg.ema,
                model=self.ema_agent)


        # device transfer
        device = torch.device(cfg.training.device)
        validate_precision_device(self.precision, device)
        self.agent.to(device)
        if self.ema_agent is not None:
            self.ema_agent.to(device)
        for optim in self.optimizer.values():
            optimizer_to(optim, device)

        # save batch for sampling
        train_sampling_batch = None

        if cfg.training.debug:
            cfg.training.num_epochs = 2
            cfg.training.max_train_steps = 3
            cfg.training.max_val_steps = 3
            cfg.training.rollout_every = 1
            cfg.training.checkpoint_every = 1
            cfg.training.val_every = 1
            cfg.training.sample_every = 1

        # training loop
        log_path = os.path.join(self.output_dir, 'logs.json.txt')
        for local_epoch_idx in range(cfg.training.num_epochs):
            step_log = dict()
            # ========= train for this epoch ==========
            with tqdm.tqdm(train_dataloader, desc=f"Training epoch {self.epoch}", 
                    leave=False, mininterval=cfg.training.tqdm_interval_sec) as tepoch:
                for batch_idx, batch in enumerate(tepoch):
                    # device transfer
                    batch = dict_apply(batch, lambda x: x.to(device, non_blocking=True))
                    if train_sampling_batch is None:
                        train_sampling_batch = batch

                    step_log = {
                        'global_step': self.global_step,       
                        'epoch': self.epoch,
                    }



                    transaction = self._run_training_batch(
                        batch, local_epoch_idx, lr_scheduler, device
                    )
                    step_log.update(transaction["step_log"])
                    tepoch.set_postfix(
                        loss=transaction["last_raw_loss"], refresh=False
                    )
                    
                    # ============================================ANALYSIS ==========================
                    """
                                        
                    full_jacobian_data = np.zeros( ( self.agent.horizon, self.agent.actor.action_dim,self.agent.horizon, int(self.agent.actor.obs_dim/2)) )
                    for target_T in tqdm.tqdm(range(self.agent.horizon), desc="Analyzing Action Horizon"):
                        for target_D in range(cfg.policy.actor.backbone.y_input_dim):
                            # --- Run the gradient calculation for this specific action component ---

                            # 1. Prepare the input, must be done fresh for each backward pass
                            state_input = batch['obs'].clone().detach().requires_grad_(True)
                            analysis_batch = {'obs': state_input, 'action': batch['action']}

                            # 2. Forward pass (no need to re-run if action_pred is already computed)
                            # Assuming `action_pred` of shape (batch, horizon, act_dim) is already available
                            # If not, recompute it here.
                            self.agent.zero_grad()
                            # Note: In a real scenario, you'd get action_pred once and reuse it.
                            for loss_dict in self.agent.compute_loss(analysis_batch, local_epoch_idx):
                                action_pred = loss_dict['grad_analysis']['action_pred']

                            # 3. Isolate the single scalar output value, averaged over the batch
                            scalar_output = action_pred[:, target_T, target_D].mean()
                            
                            # 4. Backward pass to get gradients w.r.t. state_input
                            scalar_output.backward()
                            
                            # 5. Extract and store the result (averaged over the batch dim)
                            input_gradients = state_input.grad.abs().mean(dim=0).cpu().numpy()
                            # import ipdb; ipdb.set_trace() 
                            full_jacobian_data[target_T, target_D, :, :] = input_gradients

                    global_vmin = full_jacobian_data.min()
                    global_vmax = full_jacobian_data.max()

                    obs_feature_labels = [f"obs_{i}" for i in range(int(self.agent.actor.obs_dim/2))]
                    action_feature_labels = [f"act_{i}" for i in range(self.agent.actor.action_dim)]
                    # import ipdb; ipdb.set_trace() 
                    # Simulate the interactive "GUI" by calling the function
                    # "I want to see what affects action dimension 0 at future step 4"
                    # self.plot_saliency_map(target_T=4, target_D=0, jacobian_data=full_jacobian_data, 
                    #                 obs_labels=obs_feature_labels, act_labels=action_feature_labels)
                        
                    # # "Now I want to see what affects action dimension 1 at future step 0 (the immediate action)"
                    # self.plot_saliency_map(target_T=19, target_D=1, jacobian_data=full_jacobian_data, 
                    #                 obs_labels=obs_feature_labels, act_labels=action_feature_labels)


                    # ===================================================================
                    # 2. CREATE THE INTERACTIVE MATPLOTLIB PLOT
                    # ===================================================================
                    obs_feature_labels = generate_correct_obs_labels(BODY_NAMES)
                    action_feature_labels = [f"{name}_target" for name in JOINT_NAMES]

                    # --- Create the main figure and axis for the heatmap ---
                    # `fig` is the entire window, `ax` is the main plotting area
                    fig, ax = plt.subplots(figsize=(18, 16))
                    plt.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.35)

                    # --- Define the axes for the two sliders ---
                    # The format is [left, bottom, width, height] in figure coordinates
                    ax_slider_T = plt.axes([0.25, 0.1, 0.65, 0.03])
                    ax_slider_D = plt.axes([0.25, 0.05, 0.65, 0.03])
                    ax_radio = fig.add_axes([0.05, 0.05, 0.12, 0.12])

                    # --- Create the Slider widgets ---
                    slider_T = Slider(
                        ax=ax_slider_T,
                        label='Target Future Step (T)',
                        valmin=0,
                        valmax=19,
                        valinit=0,
                        valstep=1  # Make it an integer slider
                    )

                    slider_D = Slider(
                        ax=ax_slider_D,
                        label='Target Action Dim (D)',
                        valmin=0,
                        valmax=28,
                        valinit=0,
                        valstep=1  # Make it an integer slider
                    )

                    radio_buttons = RadioButtons(ax_radio, ('Global Norm', 'Local Norm'))

                    def update(val):
                        target_T = int(slider_T.val)
                        target_D = int(slider_D.val)
                        norm_mode = radio_buttons.value_selected

                        gradient_map = full_jacobian_data[target_T, target_D]
                        flipped_gradient_map = np.flipud(gradient_map)
                        
                        # Clear only the main heatmap axis. The colorbar axis is untouched.
                        ax.cla()
                        
                        # Redraw the heatmap with the new fixed settings
                         # --- NEW: Conditional logic for normalization ---
                        if norm_mode == 'Global Norm':
                            # Use the pre-calculated global min/max
                            sns.heatmap(
                                data=flipped_gradient_map, cmap='viridis', ax=ax, cbar=False,
                                vmin=global_vmin, vmax=global_vmax,
                                xticklabels=obs_feature_labels
                            )
                        else: # 'Local Norm'
                            # Let Seaborn determine the scale automatically from the local data
                            sns.heatmap(
                                data=flipped_gradient_map, cmap='viridis', ax=ax, cbar=False,
                                xticklabels=obs_feature_labels
                            )
                                            
                        # Redraw labels and title on the main axis
                        ax.set_title(f"Influence on Action: '{action_feature_labels[target_D]}', at Timestep t: {target_T}")
                        ax.set_xlabel("Observation Features")
                        ax.set_ylabel("Input History")
                        
                        # Set y-tick labels correctly
                        num_history_steps = full_jacobian_data.shape[2]
                        y_labels = [f"t-{i}" for i in range(num_history_steps - 1, -1, -1)]
                        y_labels[-1] = "t (current)"
                        ax.set_yticklabels(y_labels, rotation=0)
                        fig.canvas.draw_idle()

                        # No need to call fig.canvas.draw_idle() inside the update function
                        # when using interactive backends like the one in Jupyter or modern Matplotlib.

                    # --- Register the update function and draw the initial plot ---
                    slider_T.on_changed(update)
                    slider_D.on_changed(update)
                    radio_buttons.on_clicked(update) # Use on_clicked for radio buttons

                    update(None) # Initial call to draw the first plot
                    """

                    plt.show()
                    # update ema
                    if cfg.training.use_ema:
                        ema.step(self.agent)

                    is_last_batch = (batch_idx == (len(train_dataloader)-1))
                    if not is_last_batch:
                        # log of last step is combined with validation and rollout
                        self.wandb_run.log(step_log, step=self.global_step)
                        self.global_step += 1

                    if (cfg.training.max_train_steps is not None) \
                        and batch_idx >= (cfg.training.max_train_steps-1):
                        break
            
            # ========= eval for this epoch ==========
            policy = self.agent
            if cfg.training.use_ema:
                policy = self.ema_agent
            policy.eval()

            if (self.epoch in [50, 100, 200, 300, 400, 800, 1000]):
                self.save_checkpoint(save_wandb=cfg.checkpoint.get('upload_to_wandb', False), tag=self.epoch)

            # checkpoint
            if (self.epoch % cfg.training.checkpoint_every) == 0:
                # checkpointing
                if cfg.checkpoint.save_last_ckpt:
                    self.save_checkpoint(save_wandb=cfg.checkpoint.get('upload_to_wandb', False), tag='latest')   
            
                # sanitize metric names
                metric_dict = dict()
                for key, value in step_log.items():
                    new_key = key.replace('/', '_')
                    metric_dict[new_key] = value

            # ========= eval end for this epoch ==========
            policy.train()

            # end of epoch
            # log of last step is combined with validation and rollout
            self.wandb_run.log(step_log, step=self.global_step)
            self.global_step += 1
            self.epoch += 1

        if cfg.training.get('save_terminal_checkpoint', False):
            # Periodic saves happen before the epoch counter is advanced, so a
            # 50-epoch run otherwise retains epoch 40 as ``latest.ckpt``. Join
            # any cadence save, then synchronously persist the completed state.
            if self._saving_thread is not None:
                self._saving_thread.join()
            terminal_path = self.save_checkpoint(
                save_wandb=cfg.checkpoint.get('upload_to_wandb', False),
                tag='latest',
                use_thread=False,
            )
            print(
                f"[OfflineTrainer] Terminal checkpoint saved: {terminal_path} "
                f"(completed_epochs={self.epoch}, global_step={self.global_step})"
            )
