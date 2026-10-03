"""Kinematic target builders for whole-body guidance.

Two strategies are provided:

* ``_build_simple_target`` — fast O(1): same position delta + velocity for
  all frames.  Suitable when ``wz≈0`` or when speed matters more than
  curved-path accuracy.
* ``_build_target_trajectory`` — accurate O(H×N): step-wise rigid-body
  integration with world-frame velocity rotation and body-offset kinematics.
"""

from __future__ import annotations

import math

import torch

from .term_resolver import TermResolver


def _build_simple_target(
    state_unnorm: torch.Tensor,
    term_index: TermResolver,
    vx: float, vy: float, vz: float, wz: float,
    dt: float,
    n_past_steps: int,
    body_intensity: list[float] | None = None,
) -> dict[str, torch.Tensor]:
    """Fast non-integration guidance: same position delta + velocity for all frames.

    Uses present-frame body-frame velocity [vx,vy] directly (no world-frame rotation).
    All bodies get the same Δpos and the same vel. O(1) per call — no step loop.

    Suitable when wz≈0 or when speed matters more than curved-path accuracy.
    """
    B, H, _D = state_unnorm.shape
    device = state_unnorm.device
    dtype = state_unnorm.dtype
    now = n_past_steps - 1

    def batch_value(value, name: str) -> torch.Tensor:
        result = torch.as_tensor(value, dtype=dtype, device=device)
        if result.ndim == 0:
            return result.expand(B)
        if result.ndim != 1 or result.shape[0] != B:
            raise ValueError(f"{name} must be scalar or have shape [{B}], got {tuple(result.shape)}")
        return result

    vx_batch = batch_value(vx, "vx")
    vy_batch = batch_value(vy, "vy")
    vz_batch = batch_value(vz, "vz")
    wz_batch = batch_value(wz, "wz")

    root_pos_now = term_index.get(state_unnorm[:, now, :], "root_pos_local")
    root_rot_now = term_index.get(state_unnorm[:, now, :], "root_rot_local")
    body_pos_now = term_index.get(state_unnorm[:, now, :], "body_pos_local")

    # ── Single delta for all future frames ───────────────────────────────
    # Position ramp: current + velocity * dt * steps_since_present
    steps = torch.arange(H, dtype=dtype, device=device) - now
    steps = steps.clamp(min=0)                                           # [H]
    delta_x = vx_batch[:, None] * dt * steps[None, :]                    # [B,H]
    delta_y = vy_batch[:, None] * dt * steps[None, :]                    # [B,H]
    delta_z = vz_batch[:, None] * dt * steps[None, :]                    # [B,H]

    target_root_pos = torch.zeros(B, H, 3, device=device, dtype=dtype)
    target_root_pos[:, :, 0] = root_pos_now[:, 0:1] + delta_x
    target_root_pos[:, :, 1] = root_pos_now[:, 1:2] + delta_y
    target_root_pos[:, :, 2] = root_pos_now[:, 2:3] + delta_z

    target_root_rot = root_rot_now.unsqueeze(1).expand(B, H, 3).clone()
    target_root_rot[:, :, 2] = root_rot_now[:, 2:3] + wz_batch[:, None] * dt * steps[None, :]

    target_root_lin_vel = torch.zeros(B, H, 3, device=device, dtype=dtype)
    target_root_lin_vel[:, :, 0] = vx_batch[:, None]
    target_root_lin_vel[:, :, 1] = vy_batch[:, None]
    target_root_lin_vel[:, :, 2] = vz_batch[:, None]

    target_root_ang_vel = torch.zeros(B, H, 3, device=device, dtype=dtype)
    target_root_ang_vel[:, :, 2] = wz_batch[:, None]

    # ── Body parts: delta scaled by per-body intensity ────────────────────
    # Start from full current state → non-guided bodies keep zero PD error
    target_body_pos = term_index.get(state_unnorm, "body_pos_local").clone()
    target_body_lin_vel = torch.zeros(B, H, 90, device=device, dtype=dtype)

    have_intensity = body_intensity is not None
    for body_n in range(30):
        w = body_intensity[body_n] if have_intensity else 1.0
        if w > 0.0:
            bp = body_pos_now[:, body_n * 3:body_n * 3 + 3]
            target_body_pos[:, :, body_n * 3 + 0] = bp[:, 0:1] + delta_x * w
            target_body_pos[:, :, body_n * 3 + 1] = bp[:, 1:2] + delta_y * w
            target_body_pos[:, :, body_n * 3 + 2] = bp[:, 2:3] + delta_z * w
            target_body_lin_vel[:, :, body_n * 3 + 0] = vx_batch[:, None] * w
            target_body_lin_vel[:, :, body_n * 3 + 1] = vy_batch[:, None] * w
            target_body_lin_vel[:, :, body_n * 3 + 2] = vz_batch[:, None] * w

    # Copy past frames unchanged (root only — body already clone of state above)
    target_root_pos[:, :n_past_steps] = term_index.get(
        state_unnorm[:, :n_past_steps, :], "root_pos_local")
    target_root_rot[:, :n_past_steps] = term_index.get(
        state_unnorm[:, :n_past_steps, :], "root_rot_local")

    return {
        "root_pos_local": target_root_pos,
        "root_rot_local": target_root_rot,
        "root_lin_vel_local": target_root_lin_vel,
        "root_ang_vel_local": target_root_ang_vel,
        "body_pos_local": target_body_pos,
        "body_lin_vel_local": target_body_lin_vel,
    }


def _build_target_trajectory(
    state_unnorm: torch.Tensor,   # [B, H, D]
    term_index: TermResolver,
    vx: float, vy: float, vz: float, wz: float,
    dt: float,
    n_past_steps: int,
    body_intensity: list[float] | None = None,
) -> dict[str, torch.Tensor]:
    """Build target values for all kinematic terms by step-wise integration.

    Returns a dict ``{term_name: target_tensor [B, H, term_dim]}`` with
    the same keys as the guiding guidance's ``guided_terms``.
    """
    B, H, _D = state_unnorm.shape
    device = state_unnorm.device
    now = n_past_steps - 1  # index of "present" frame

    # ── Extract current state ──────────────────────────────────────────
    root_pos_now = term_index.get(state_unnorm[:, now, :], "root_pos_local")      # [B, 3]
    root_rot_now = term_index.get(state_unnorm[:, now, :], "root_rot_local")      # [B, 3]
    body_pos_now = term_index.get(state_unnorm[:, now, :], "body_pos_local")      # [B, 90]

    # ── Allocate targets ────────────────────────────────────────────────
    target_root_pos = torch.zeros(B, H, 3, device=device)
    target_root_rot = torch.zeros(B, H, 3, device=device)
    target_root_lin_vel = torch.zeros(B, H, 3, device=device)
    target_root_ang_vel = torch.zeros(B, H, 3, device=device)
    # Body targets: clone from state so non-guided bodies keep zero PD error
    target_body_pos = term_index.get(state_unnorm, "body_pos_local").clone()
    target_body_lin_vel = torch.zeros(B, H, 90, device=device)

    # Copy past+present frames unchanged
    target_root_pos[:, :n_past_steps] = term_index.get(
        state_unnorm[:, :n_past_steps, :], "root_pos_local")
    target_root_rot[:, :n_past_steps] = term_index.get(
        state_unnorm[:, :n_past_steps, :], "root_rot_local")

    # ── Body offsets from root (body-frame, constant across horizon) ────
    body_offsets = body_pos_now.reshape(B, 30, 3) - root_pos_now.unsqueeze(1)  # [B, 30, 3]

    # ── Step-wise integration for future frames ─────────────────────────
    for t in range(n_past_steps, H):
        rel_t = t - now
        theta = wz * dt * rel_t                                              # accumulated yaw
        cos_t, sin_t = math.cos(theta), math.sin(theta)

        # World-frame root velocity (rotated from body-frame [vx, vy])
        world_vx = cos_t * vx - sin_t * vy
        world_vy = sin_t * vx + cos_t * vy

        if t == n_past_steps:
            # First future step: integrate from present position
            target_root_pos[:, t, 0] = root_pos_now[:, 0] + world_vx * dt
            target_root_pos[:, t, 1] = root_pos_now[:, 1] + world_vy * dt
        else:
            target_root_pos[:, t, 0] = target_root_pos[:, t - 1, 0] + world_vx * dt
            target_root_pos[:, t, 1] = target_root_pos[:, t - 1, 1] + world_vy * dt
        target_root_pos[:, t, 2] = root_pos_now[:, 2] + vz * dt * rel_t     # height ramp

        target_root_rot[:, t, 0] = root_rot_now[:, 0]
        target_root_rot[:, t, 1] = root_rot_now[:, 1]
        target_root_rot[:, t, 2] = root_rot_now[:, 2] + theta                 # yaw accumulation

        target_root_lin_vel[:, t, 0] = world_vx
        target_root_lin_vel[:, t, 1] = world_vy
        target_root_lin_vel[:, t, 2] = vz

        target_root_ang_vel[:, t, 0] = 0.0
        target_root_ang_vel[:, t, 1] = 0.0
        target_root_ang_vel[:, t, 2] = wz

        # Body parts: rigid body kinematics v_body = v_root + ω × r
        have_intensity = body_intensity is not None
        for body_n in range(30):
            w = body_intensity[body_n] if have_intensity else 1.0
            if w == 0.0:
                continue
            rx = body_offsets[:, body_n, 0]   # [B]
            ry = body_offsets[:, body_n, 1]   # [B]
            # Rotate offset by accumulated yaw
            rx_rot = cos_t * rx - sin_t * ry
            ry_rot = sin_t * rx + cos_t * ry

            # Position: interpolate between original and commanded by w
            orig_px = target_body_pos[:, t, body_n * 3 + 0]
            orig_py = target_body_pos[:, t, body_n * 3 + 1]
            orig_pz = target_body_pos[:, t, body_n * 3 + 2]
            cmd_px = target_root_pos[:, t, 0] + rx_rot
            cmd_py = target_root_pos[:, t, 1] + ry_rot
            cmd_pz = body_pos_now[:, body_n * 3 + 2] + vz * dt * rel_t
            target_body_pos[:, t, body_n * 3 + 0] = orig_px + w * (cmd_px - orig_px)
            target_body_pos[:, t, body_n * 3 + 1] = orig_py + w * (cmd_py - orig_py)
            target_body_pos[:, t, body_n * 3 + 2] = orig_pz + w * (cmd_pz - orig_pz)

            # Velocity: v_root + ω × r  (tangential component from rotation)
            orig_vx = target_body_lin_vel[:, t, body_n * 3 + 0]
            orig_vy = target_body_lin_vel[:, t, body_n * 3 + 1]
            orig_vz = target_body_lin_vel[:, t, body_n * 3 + 2]
            cmd_vx = world_vx - wz * ry_rot
            cmd_vy = world_vy + wz * rx_rot
            cmd_vz = vz
            target_body_lin_vel[:, t, body_n * 3 + 0] = orig_vx + w * (cmd_vx - orig_vx)
            target_body_lin_vel[:, t, body_n * 3 + 1] = orig_vy + w * (cmd_vy - orig_vy)
            target_body_lin_vel[:, t, body_n * 3 + 2] = orig_vz + w * (cmd_vz - orig_vz)

    return {
        "root_pos_local": target_root_pos,
        "root_rot_local": target_root_rot,
        "root_lin_vel_local": target_root_lin_vel,
        "root_ang_vel_local": target_root_ang_vel,
        "body_pos_local": target_body_pos,
        "body_lin_vel_local": target_body_lin_vel,
    }
