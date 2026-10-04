"""Unified environment runner for all low-dim observation agents.

Runner responsibility is intentionally narrow:
- query observation terms from env
- compose/normalize observations through TermComposer
- run agent action inference
- step env and enforce loop rate when requested
"""

from __future__ import annotations

import time
import multiprocessing as mp
from pathlib import Path
from typing import Dict, Optional

import traceback
import numpy as np
import torch
from tqdm import tqdm

from diffusion_policy.dataset.g1_dataset import TermComposer
from diffusion_policy.env.base_env import BaseEnv
from diffusion_policy.env.mujoco_env import MuJoCoG1Env, MuJoCoEnvConfig
from diffusion_policy.env_runner.base_lowdim_runner import BaseLowdimRunner
from diffusion_policy.task_provider.base import (
    TaskCondProvider,
    ClipCondProvider,
    CompositeCondProvider,
)
from diffusion_policy.utils.realtime_looper import realtime_loop
from diffusion_policy.utils.action_selection import (
    configure_actor_action_selection, select_action_for_agent,
    validate_delay_action_step)
from diffusion_policy.task_provider.whole_body_guidance.destination_follow import (
    map_target_between_root_frames,
)


# ---------------------------------------------------------------------------
# EnvRunner
# ---------------------------------------------------------------------------

class EnvRunner(BaseLowdimRunner):
    def __init__(
        self,
        output_dir: str,
        max_steps: int = 1000,
        n_obs_steps: int = 4,
        device: Optional[str] = None,
        tqdm_interval_sec: float = 5.0,
        realtime_mode: bool = False,
        dataset_class: Optional[str] = None,
        # Optional nested env object/config. If absent, we infer from legacy flat args.
        env: Optional[BaseEnv] = None,
        # Task condition provider.  Pass a TaskCondProvider directly, or use the
        # legacy clip_teleop / clip_interp kwargs (auto-wrapped in ClipCondProvider).
        task_cond_provider: Optional[TaskCondProvider] = None,
        # Legacy flat kwargs — kept for backward compatibility.
        # Prefer passing a pre-built provider via task_cond_provider.
        clip_teleop: Optional[object] = None,
        clip_interp: Optional[object] = None,
        moref_teleop: Optional[object] = None,
        # task_cond_providers dict is consumed by cond_eval.py before instantiation;
        # listed here only so Hydra does not fail on unexpected keys.
        task_cond_providers: Optional[dict] = None,
        # Optional debugger
        enable_debugger: bool = False,
        debugger_config: Optional[dict] = None,
        # Optional metrics collector (injected by benchmark / eval scripts).
        # When set, per-step timing and trajectory data are fed to the
        # collector automatically inside _run_interval_core.
        metrics_collector=None,
        runtime_observer=None,
        delay_action_step: float = 0,
        # Legacy/compatibility kwargs used to build env internally.
        **kwargs,
    ):
        super().__init__(output_dir)
        self.max_steps = max_steps
        self.n_obs_steps = n_obs_steps
        self.delay_action_step = validate_delay_action_step(delay_action_step)
        self.device = device
        self.tqdm_interval_sec = tqdm_interval_sec
        self.realtime_mode = realtime_mode
        self.target_dt = kwargs.get("control_dt", None)
        self.dataset_class_name = dataset_class

        # Task condition provider — prefer explicit, fall back to legacy CLIP wrappers.
        # Multiple providers are combined into a CompositeCondProvider.
        providers = []
        if task_cond_provider is not None:
            providers.append(task_cond_provider)
        if clip_teleop is not None or clip_interp is not None:
            if clip_teleop is not None and clip_interp is not None:
                raise ValueError("Cannot use both clip_teleop and clip_interp simultaneously")
            providers.append(ClipCondProvider(clip_teleop or clip_interp))
        if moref_teleop is not None:
            providers.append(moref_teleop)

        if len(providers) == 0:
            self.task_cond_provider: Optional[TaskCondProvider] = None
        elif len(providers) == 1:
            self.task_cond_provider: Optional[TaskCondProvider] = providers[0]
        else:
            self.task_cond_provider: Optional[TaskCondProvider] = CompositeCondProvider(providers)

        self.enable_debugger = enable_debugger
        self.debugger_config = debugger_config or {}
        self.debugger_process = None
        self.debugger_queue = None

        self.env: BaseEnv = env if env is not None else self._build_env_from_kwargs(kwargs)
        self.obs_composer: Optional[TermComposer] = None
        self.metrics_collector = metrics_collector
        self.runtime_observer = runtime_observer

    def _has_task_condition_provider(self) -> bool:
        provider = self.task_cond_provider
        return provider is not None and bool(getattr(provider, "provides_task_condition", True))

    def _build_env_from_kwargs(self, kwargs) -> BaseEnv:
        # Priority 1: explicit env type
        env_type = kwargs.get("env_type", None)

        # Priority 2: infer from familiar legacy runner args
        if env_type is None:
            if "task_name" in kwargs or "headless" in kwargs or "n_envs" in kwargs:
                env_type = "isaac_lab"
            elif kwargs.get("use_mujoco_loop_sync", False):
                env_type = "mujoco"
            else:
                env_type = "unitree"

        if env_type == "isaac_lab":
            from diffusion_policy.env.isaaclab_env import IsaacLabEnv, IsaacLabEnvConfig

            cfg = IsaacLabEnvConfig(
                task_name=kwargs.get("task_name", "Isaac-PegasusMoDye-Diffusion-G1-v0"),
                n_envs=kwargs.get("n_envs", 1),
                headless=kwargs.get("headless", True),
                use_fk=kwargs.get("use_fk", False),
                urdf_path=kwargs.get("urdf_path", None),
                fk_calculator_type=kwargs.get("fk_calculator_type", "pinocchio"),
                fk_device=kwargs.get("fk_device", "cpu"),
                debug_fk=kwargs.get("debug_fk", False),
                debug_fk_interval=kwargs.get("debug_fk_interval", 50),
            )
            return IsaacLabEnv(config=cfg)

        if env_type == "mujoco":
            cfg = MuJoCoEnvConfig(
                control_dt=kwargs.get("control_dt", 0.02),
                simulation_dt=kwargs.get("mujoco_simulation_dt", 0.002),
                num_dof=kwargs.get("num_dof", 29),
                xml_path=kwargs.get("mujoco_xml_path", None),
                Kp=np.array(kwargs["Kp"], dtype=np.float32) if kwargs.get("Kp") is not None else None,
                Kd=np.array(kwargs["Kd"], dtype=np.float32) if kwargs.get("Kd") is not None else None,
                enable_viewer=kwargs.get("mujoco_enable_viewer", False),
                urdf_path=kwargs.get("urdf_path", None),
                use_fk=kwargs.get("use_fk", True),
                fk_calculator_type=kwargs.get("fk_calculator_type", "pinocchio"),
                fk_device=kwargs.get("fk_device", "cpu"),
            )
            return MuJoCoG1Env(config=cfg)

        # Default: Unitree SDK path.
        from diffusion_policy.env.unitree_env import UnitreeEnvConfig, UnitreeG1Env

        cfg = UnitreeEnvConfig(
            control_dt=kwargs.get("control_dt", 0.02),
            num_dof=kwargs.get("num_dof", 29),
            use_pr_mode=kwargs.get("use_pr_mode", True),
            network_interface=kwargs.get("network_interface", None),
            Kp=kwargs.get("Kp", None),
            Kd=kwargs.get("Kd", None),
            enable_safety_checks=kwargs.get("safety_checks", True),
            use_fk=kwargs.get("use_fk", True),
            urdf_path=kwargs.get("urdf_path", None),
            fk_calculator_type=kwargs.get("fk_calculator_type", "pinocchio"),
            fk_device=kwargs.get("fk_device", "cpu"),
        )
        return UnitreeG1Env(config=cfg)

    def _cleanup_debugger_process(self):
        if self.debugger_process and self.debugger_process.is_alive():
            try:
                self.debugger_queue.put(None, timeout=1.0)
                self.debugger_process.join(timeout=5.0)
                if self.debugger_process.is_alive():
                    self.debugger_process.terminate()
                    self.debugger_process.join(timeout=2.0)
            except Exception:
                pass
        self.debugger_process = None
        self.debugger_queue = None

    def _build_term_composer(self, cfg) -> TermComposer:
        """Build a TermComposer from cfg.dataset (always available at inference)."""
        from diffusion_policy.dataset.g1_dataset import DataProfile
        ds_cfg = cfg.dataset
        profile = DataProfile.from_yaml(ds_cfg.get("data_profile") or "g1_standard")
        # When no CLIP provider is active, strip text_cond from the
        # task_condition so the composed cond_dim matches the backbone.
        if not self._has_task_condition_provider() and hasattr(profile, 'task_condition'):
            tc = profile.task_condition
            if hasattr(tc, 'terms') and 'text_cond' in tc.terms:
                tc.terms = [t for t in tc.terms if t != 'text_cond']
                print("[EnvRunner] No CLIP provider active — removed text_cond from task_condition")
        n_task_steps = int(ds_cfg.get("n_task_steps") or 1)
        return TermComposer(profile, self.n_obs_steps, n_task_steps=n_task_steps)

    def run(self, bc_agent, cfg) -> Optional[Dict]:
        try:
            return self._run_internal(bc_agent, cfg)
        except Exception as e:
            print("\033[31m", traceback.format_exc(), "\033[0m")
        finally:
            if self.runtime_observer is not None:
                self.runtime_observer.stop()
            self._cleanup_debugger_process()
            if self.task_cond_provider is not None:
                self.task_cond_provider.stop()
            if self.env is not None:
                self.env.close()

    def _run_internal(self, bc_agent, cfg=None) -> Dict:
        self.env.initialize()
        if self.runtime_observer is not None:
            self.runtime_observer.start(self.env, bc_agent)
        step_dt = self.env.get_step_dt()
        if step_dt is not None:
            self.target_dt = step_dt

        if self.task_cond_provider is not None:
            self.task_cond_provider.start()
            # Wire JoyTextWBG's WholeBodyGuidance into the diffusion module
            # so that guidance values set by the joystick are actually applied
            # during denoising.
            if hasattr(self.task_cond_provider, 'wbg') and hasattr(bc_agent, 'actor'):
                actor = bc_agent.actor
                actor.whole_body_guidance = self.task_cond_provider.wbg
                # Forward normalizer if already set on the actor
                norm = getattr(actor, 'normalizer', None)
                if norm is not None:
                    self.task_cond_provider.wbg.set_normalizer(norm)
                print("[EnvRunner] Wired JoyTextWBG.wbg → DiffuseCLoC.whole_body_guidance")

        device = bc_agent.device if self.device is None else torch.device(self.device)
        self.obs_composer = self._build_term_composer(cfg)
        assert self.obs_composer is not None

        # Wire cond_term_boundaries into the agent's task mask generator so
        # inference masking (term_boundaries check in act()) works correctly.
        if hasattr(bc_agent, "set_task_mask_from_profile") or hasattr(bc_agent, "set_dropout_from_profile"):
            from diffusion_policy.dataset.g1_dataset import DataProfile
            profile = DataProfile.from_yaml(cfg.dataset.get("data_profile") or "g1_standard")
            if not self._has_task_condition_provider() and hasattr(profile, "task_condition"):
                tc = profile.task_condition
                if hasattr(tc, "terms") and "text_cond" in tc.terms:
                    tc.terms = [term for term in tc.terms if term != "text_cond"]
            if hasattr(bc_agent, "set_task_mask_from_profile"):
                bc_agent.set_task_mask_from_profile(profile.task_condition)
            if hasattr(bc_agent, "set_dropout_from_profile"):
                bc_agent.set_dropout_from_profile(profile.task_condition)
        # Boundaries must be wired last so both task_mask_gen and
        # per_term_dropout (created above) receive them in one call.
        if hasattr(bc_agent, "set_task_mask_boundaries"):
            bc_agent.set_task_mask_boundaries(self.obs_composer.cond_term_boundaries)

        # Prime env state
        on_reset = getattr(self.runtime_observer, "on_reset", None)
        if callable(on_reset):
            on_reset(reason="initial")
        self.env.reset()
        action_dim = self._infer_action_dim()
        zero_action = np.zeros(action_dim, dtype=np.float64)
        init_terms = self.env.get_obs_terms(last_actions=zero_action)
        # Inject any externally-sourced task condition keys before building history.
        n_envs_init = next(iter(init_terms.values())).shape[0]
        self._attach_task_condition(init_terms, n_envs_init)
        raw_history = TermComposer.init_history(init_terms, n_obs_steps=self.n_obs_steps)

        if self.enable_debugger:
            from diffusion_policy.utils.cloc_fdb_debugger import debugger_worker_process

            self.debugger_queue = mp.Queue(maxsize=1)
            debugger_output_dir = Path(self.output_dir) / "debugger_vis" / "env_runner"
            self.debugger_process = mp.Process(
                target=debugger_worker_process,
                args=(self.debugger_queue, self.debugger_config, str(debugger_output_dir), "EnvRunner"),
            )
            self.debugger_process.daemon = True
            self.debugger_process.start()

        self.loop_ctx = {
            "raw_history": raw_history,
            "step_count": 0,
            "pbar": tqdm(total=self.max_steps, desc="Env Eval", mininterval=self.tqdm_interval_sec),
            "episode_rewards": [],
            "episode_lengths": [],
            "current_rewards": None,
            "current_lengths": None,
        }

        # Setup episode trackers after first env step shape is known.
        n_envs = int(raw_history["joint_pos"].shape[0])
        self.loop_ctx["current_rewards"] = torch.zeros(n_envs, device=device)
        self.loop_ctx["current_lengths"] = torch.zeros(n_envs, device=device, dtype=torch.long)

        start_time = time.time()
        try:
            for step_idx in range(self.max_steps):
                keep_running = self._run_interval_realtime(step_idx, bc_agent, device)
                if keep_running is False:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.loop_ctx["pbar"].close()

        elapsed_time = time.time() - start_time
        step_count = self.loop_ctx["step_count"]
        avg_step_time = elapsed_time / step_count if step_count > 0 else 0.0

        # Flush unfinished episodes
        current_rewards = self.loop_ctx["current_rewards"]
        current_lengths = self.loop_ctx["current_lengths"]
        episode_rewards = self.loop_ctx["episode_rewards"]
        episode_lengths = self.loop_ctx["episode_lengths"]
        for i in range(current_lengths.shape[0]):
            if current_lengths[i] > 0:
                episode_rewards.append(float(current_rewards[i].item()))
                episode_lengths.append(int(current_lengths[i].item()))

        results = {
            "total_steps": step_count,
            "elapsed_time": elapsed_time,
            "avg_step_time": avg_step_time,
            "target_dt": self.target_dt,
            "num_episodes": len(episode_rewards),
            "mean_episode_reward": float(np.mean(episode_rewards)) if episode_rewards else 0.0,
            "std_episode_reward": float(np.std(episode_rewards)) if episode_rewards else 0.0,
            "mean_episode_length": float(np.mean(episode_lengths)) if episode_lengths else 0.0,
        }

        # Merge metrics results if collector is active
        if self.metrics_collector:
            metrics_output = self.metrics_collector.finalize()
            results["metrics"] = {
                "results": [r.to_dict() for r in metrics_output["metric_results"]],
                "wandb": metrics_output["wandb"],
                "table": metrics_output["table"],
            }

        return results

    def _infer_action_dim(self) -> int:
        # Prefer explicit env config data where available.
        for attr in ("config",):
            cfg = getattr(self.env, attr, None)
            if cfg is not None and hasattr(cfg, "num_dof"):
                return int(cfg.num_dof)
        # Fall back to 29 for G1.
        return 29

    def _send_debug(self, terms):
        if not self.enable_debugger or self.debugger_queue is None:
            return
        try:
            debug_data = {
                "body_pos": terms["body_pos"][0, -1].cpu().numpy(),
                "body_lin_vel": terms["body_lin_vel"][0, -1].cpu().numpy(),
                "root_pos": terms["root_pos"][0, -1].cpu().numpy(),
                "root_rot": terms["root_rot"][0, -1].cpu().numpy(),
                "root_ang_vel": terms["body_ang_vel"][0, -1, 0].cpu().numpy(),
                "projected_gravity": terms["projected_gravity"][0, -1].cpu().numpy(),
                "base_lin_vel": terms["base_lin_vel"][0, -1].cpu().numpy(),
                "base_ang_vel": terms["base_ang_vel"][0, -1].cpu().numpy(),
                "last_actions": terms["last_actions"][0, -1].cpu().numpy(),
            }
            self.debugger_queue.put(debug_data, block=False)
        except Exception:
            pass

    def _attach_task_condition(
        self,
        next_terms: dict,
        batch_size: int,
    ) -> None:
        """Inject externally-sourced task condition keys into *next_terms* in-place.

        ``next_terms`` is the single-step dict ``[B, 1, ...]`` returned by
        ``env.get_obs_terms()``.  Any task_condition terms not already present
        (i.e. not produced by the env) are filled here from the provider.

        Currently the only externally-sourced term is ``text_cond`` (CLIP /
        MotionCLIP embedding), which is stored under the ``"motion_latent"``
        key to match the zarr layout seen during training.

        Injected tensors are stored on CPU to stay consistent with the rest of
        raw_history (env tensors are always CPU).  The composed cond is moved
        to device by the caller after compose_cond().
        """
        if self.task_cond_provider is None:
            return
        assert self.obs_composer is not None, "_attach_task_condition called before obs_composer was built"

        # Each provider writes its key(s) directly into next_terms via inject_raw_keys.
        # - ClipCondProvider  → next_terms["motion_latent"]      [B, 1, D]
        # - MoRefTeleop       → next_terms["motion_ref_root_pos"] [B, 1, 3]
        # - CompositeCondProvider fans out to all sub-providers.
        self.task_cond_provider.inject_raw_keys(next_terms, batch_size)

    def _feed_point_reach_guidance(self, bc_agent, next_terms: dict) -> None:
        """Feed world-frame body positions to WholeBodyGuidance for point-reach.

        The controller and policy deliberately share ``next_terms`` so the
        controller cannot silently consume privileged simulator state.  Point
        following therefore requires a live FK observation mode; zero-filled
        proprioceptive-only pose placeholders are not a valid controller input.

        Extracts pelvis (index 0), left wrist (24), right wrist (25) from the
        selected control-state terms and passes them to
        ``WholeBodyGuidance.set_world_body_pos()``.  Also syncs the debug sphere
        position and the MuJoCo viewer marker.
        """
        import logging as _log
        try:
            wbg = getattr(getattr(bc_agent, 'actor', None), 'whole_body_guidance', None)
            if wbg is None or not (
                    getattr(wbg, '_has_point_reach', False)
                    or getattr(wbg, '_has_destination_follow', False)):
                return

            body_pos = next_terms.get('body_pos')  # [1, 1, 30, 3] world-frame
            root_pos = next_terms.get('root_pos')  # [1, 1, 3] world-frame
            root_rot = next_terms.get('root_rot')  # [1, 1, 4] quat (w,x,y,z)

            # Destination-follow only needs root position/yaw. Legacy
            # point-reach wrist/pelvis overlays additionally consume body_pos.
            if root_pos is None or root_rot is None:
                return

            # Extract key body positions
            bp = body_pos[0, 0] if body_pos is not None else None  # [30, 3]
            rp = root_pos[0, 0]  # [3]
            pelvis = (float(bp[0, 0]), float(bp[0, 1]), float(bp[0, 2])) if bp is not None else None
            lwrist = ((float(bp[24, 0]), float(bp[24, 1]), float(bp[24, 2]))
                      if bp is not None and bp.shape[0] > 24 else None)
            rwrist = ((float(bp[25, 0]), float(bp[25, 1]), float(bp[25, 2]))
                      if bp is not None and bp.shape[0] > 25 else None)
            root_p = (float(rp[0]), float(rp[1]), float(rp[2]))

            # Compute yaw from root quaternion
            yaw = 0.0
            if root_rot is not None:
                rr = root_rot[0, 0]  # [4] quat
                w, x, y, z = float(rr[0]), float(rr[1]), float(rr[2]), float(rr[3])
                yaw = float(np.arctan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))

            wbg.set_world_body_pos(
                pelvis_pos=pelvis, left_wrist_pos=lwrist,
                right_wrist_pos=rwrist, root_pos=root_p, root_yaw=yaw,
            )

            # Update MuJoCo debug markers at either legacy point-reach or the
            # destination-follow target. Destination mode may run with an
            # RL-only profile where body_pos is intentionally absent.
            destination = getattr(wbg, 'destination_follow_snapshot', lambda: {})()
            target = None
            if destination.get('enabled') and destination.get('target') is not None:
                # Destination follow owns vx/vy/wz while enabled, so its target
                # must also own the marker. A policy may retain live legacy
                # PointReach data whose unrelated target would otherwise win.
                target = destination['target']
                inputs = destination.get('inputs', {})
                controller_root = inputs.get('root_pos')
                controller_yaw = inputs.get('root_yaw')
                qpos = getattr(getattr(self.env, 'data', None), 'qpos', None)
                if controller_root is not None and controller_yaw is not None and qpos is not None:
                    try:
                        qw, qx, qy, qz = (float(value) for value in qpos[3:7])
                        render_yaw = float(np.arctan2(
                            2.0 * (qw * qz + qx * qy),
                            1.0 - 2.0 * (qy * qy + qz * qz),
                        ))
                        target = map_target_between_root_frames(
                            target,
                            controller_root,
                            controller_yaw,
                            qpos[0:3],
                            render_yaw,
                        )
                    except (IndexError, TypeError, ValueError):
                        pass
            else:
                pt = wbg.get_point_target()
                if pt.get('has_world_data'):
                    target = (pt['x'], pt['y'], pt['z'])
            if target is not None:
                x, y, z = (float(value) for value in target)
                if hasattr(self.env, 'set_debug_sphere'):
                    self.env.set_debug_sphere((x, y, z), radius=0.06,
                                              rgba=(1.0, 0.2, 0.2, 0.85))
                # Crosshair: three axis-aligned box bars so the centre is visible
                # from any camera angle.
                if hasattr(self.env, 'add_debug_marker'):
                    import mujoco as _mj
                    bar_s = 0.08  # half-length of each bar
                    bar_t = 0.012  # half-thickness
                    for axis, color in [
                        (0, (1.0, 0.3, 0.3, 0.7)),  # X = red
                        (1, (0.3, 1.0, 0.3, 0.7)),  # Y = green
                        (2, (0.3, 0.3, 1.0, 0.7)),  # Z = blue
                    ]:
                        size = [bar_t, bar_t, bar_t]
                        size[axis] = bar_s
                        self.env.add_debug_marker(
                            _mj.mjtGeom.mjGEOM_BOX, tuple(size), (x, y, z),
                            rgba=color, label=f"_wbg_cross_{axis}",
                        )
            else:
                # Remove a stale target after cancel/arrival/reset. Keep this
                # scoped to WBG labels so unrelated simulator markers survive.
                remove_marker = getattr(self.env, 'remove_debug_marker', None)
                if callable(remove_marker):
                    remove_marker('_wbg_sphere')
                    for axis in range(3):
                        remove_marker(f'_wbg_cross_{axis}')
        except Exception as e:
            import traceback
            _log.warning(f"[PointReach] Failed to feed guidance: {e}")
            traceback.print_exc()  # one-time trace so we can diagnose

    def _run_interval_core(self, step_idx, bc_agent, device):
        assert self.obs_composer is not None
        ctx = self.loop_ctx
        raw_history = ctx["raw_history"]
        if self.runtime_observer is not None:
            # Reset requests originate on the web-server thread. Consume and
            # execute them here so MuJoCo state is only mutated by this loop.
            while self.runtime_observer.before_step(step_idx):
                raw_history = self._reset_environment_history(
                    raw_history, reason="manual")
                after_reset = getattr(self.runtime_observer, "after_reset", None)
                if callable(after_reset):
                    after_reset(step_idx, self.env)
        self._send_debug(raw_history)

        # Observation composition
        t_loop_start = time.perf_counter() if self.metrics_collector else 0
        obs_normalized = self.obs_composer.compose(raw_history)
        t_obs = (time.perf_counter() - t_loop_start) * 1000.0 if self.metrics_collector else 0
        obs_dict_policy = {"obs": obs_normalized.to(device)}
        if self.obs_composer.use_task_interface:
            obs_dict_policy["cond"] = self.obs_composer.compose_cond(raw_history).to(device)
        elif self.task_cond_provider is not None:
            # Legacy CLIP-only path (no task_condition profile): provider supplies cond directly.
            n_task_steps = self.obs_composer.n_task_steps
            obs_dict_policy["cond"] = self.task_cond_provider.get_task_cond(
                raw_history, obs_normalized.shape[0], n_task_steps, device
            )

        # Agent Inference
        t_inf_start = time.perf_counter() if self.metrics_collector else 0
        with torch.no_grad():
            configure_actor_action_selection(
                bc_agent.actor, self.n_obs_steps, self.delay_action_step)
            result = bc_agent.act(obs_dict_policy)
            if isinstance(result, tuple) and len(result) >= 1:
                action_traj = result[0]
            else:
                action_traj = result
            actions = select_action_for_agent(
                action_traj, bc_agent, self.n_obs_steps, self.delay_action_step)
        t_inf = (time.perf_counter() - t_inf_start) * 1000.0 if self.metrics_collector else 0

        # Step env.
        env_actions = actions
        if actions.shape[0] == 1:
            env_actions = actions.squeeze(0).detach().cpu().numpy()
        before_env_step = getattr(self.runtime_observer, "before_env_step", None)
        if callable(before_env_step):
            before_env_step()
        obs_dict, rewards, done, infos = self.env.step(env_actions, action_is_isaaclab_order=True)
        if self.runtime_observer is not None:
            self.runtime_observer.after_step(step_idx, self.env, bc_agent)

        # Collect next terms, using latest policy actions as last_actions.
        last_actions_for_obs = actions.detach()
        if last_actions_for_obs.shape[0] == 1:
            last_actions_for_obs = last_actions_for_obs.squeeze(0).detach().cpu().numpy()
        next_terms = self.env.get_obs_terms(last_actions=last_actions_for_obs)

        # Inject externally-sourced task condition keys (e.g. motion_latent from provider).
        self._attach_task_condition(next_terms, obs_normalized.shape[0])

        # ── Point-reach guidance world-state feed ────────────────────────
        # Pass world-frame body positions from the simulator to
        # WholeBodyGuidance so point_reach_guide can compute the
        # world→local delta.  Also update the MuJoCo debug sphere.
        self._feed_point_reach_guidance(bc_agent, next_terms)

        # Per-env termination check — each env implements its own criterion.
        if self.env.check_terminate() and self._auto_reset_enabled():
            raw_history = self._reset_environment_history(
                raw_history, reason="automatic")
            next_terms = {key: value[:, -1:] for key, value in raw_history.items()}
            after_reset = getattr(self.runtime_observer, "after_reset", None)
            if callable(after_reset):
                after_reset(step_idx + 1, self.env)

        raw_history = TermComposer.shift_append(raw_history, next_terms)

        reward_t = torch.as_tensor(rewards, device=device, dtype=torch.float32).flatten()
        done_t = torch.as_tensor(done, device=device, dtype=torch.bool).flatten()

        if reward_t.numel() == 1 and ctx["current_rewards"].numel() > 1:
            reward_t = reward_t.repeat(ctx["current_rewards"].numel())
            done_t = done_t.repeat(ctx["current_rewards"].numel())

        ctx["current_rewards"] += reward_t
        ctx["current_lengths"] += 1

        # --- Metrics collection ---
        if self.metrics_collector:
            step_ms = (time.perf_counter() - t_loop_start) * 1000.0
            step_data = self.metrics_collector.collect_step_data(
                raw_history=raw_history,
                actions=actions,
                inference_time_ms=t_inf,
                obs_time_ms=t_obs,
                step_time_ms=step_ms,
                reward=rewards,
                done=bool(done_t.any()),
            )
            self.metrics_collector.step(step_data)

        if done_t.any():
            done_idxs = torch.where(done_t)[0]
            for env_idx in done_idxs:
                ctx["episode_rewards"].append(float(ctx["current_rewards"][env_idx].item()))
                ctx["episode_lengths"].append(int(ctx["current_lengths"][env_idx].item()))
                ctx["current_rewards"][env_idx] = 0.0
                ctx["current_lengths"][env_idx] = 0

            # Flush metrics for this episode
            if self.metrics_collector:
                self.metrics_collector.flush_episode()

        ctx["raw_history"] = raw_history
        ctx["step_count"] += 1
        ctx["pbar"].update(1)

        if not self.env.is_running():
            return False
        return True

    def _auto_reset_enabled(self) -> bool:
        getter = getattr(self.runtime_observer, "auto_reset_enabled", None)
        return True if not callable(getter) else bool(getter())

    def _reset_environment_history(self, raw_history, *, reason: str):
        on_reset = getattr(self.runtime_observer, "on_reset", None)
        if callable(on_reset):
            on_reset(reason=reason)
        self.env.reset()
        zero_action = np.zeros(self._infer_action_dim(), dtype=np.float64)
        reset_terms = self.env.get_obs_terms(last_actions=zero_action)
        batch_size = next(iter(raw_history.values())).shape[0]
        self._attach_task_condition(reset_terms, batch_size)
        reset_history = TermComposer.init_history(
            reset_terms, n_obs_steps=self.n_obs_steps)
        current_rewards = self.loop_ctx.get("current_rewards")
        current_lengths = self.loop_ctx.get("current_lengths")
        if current_rewards is not None:
            current_rewards.zero_()
        if current_lengths is not None:
            current_lengths.zero_()
        return reset_history

    @realtime_loop(expected_dt="target_dt", enable_attr="realtime_mode", name="env_runner_loop")
    def _run_interval_realtime(self, step_idx, bc_agent, device):
        return self._run_interval_core(step_idx, bc_agent, device)
