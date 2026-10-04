"""Shared zero-based action-trajectory selection contract."""

from __future__ import annotations

import math
import operator
from typing import NamedTuple, Sequence

import torch


def _integer(name: str, value: int) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not bool")
    try:
        return operator.index(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}") from exc


class ActionSelection(NamedTuple):
    lower_index: int
    upper_index: int
    alpha: float
    lower_noise_level: int
    upper_noise_level: int


def validate_delay_action_step(delay_action_step: float) -> float:
    """Return a finite real delay without rounding or truncation."""
    if isinstance(delay_action_step, bool) or not isinstance(
        delay_action_step, (int, float)
    ):
        raise TypeError(
            "delay_action_step must be a real number, got "
            f"{type(delay_action_step).__name__}")
    delay = float(delay_action_step)
    if not math.isfinite(delay):
        raise ValueError(f"delay_action_step must be finite, got {delay}")
    return delay


def action_selection(
    past_step: int,
    delay_action_step: float,
    horizon: int,
    terminal_noise_levels: Sequence[int] | None = None,
) -> ActionSelection:
    """Build a schedule-aware adjacent-index interpolation plan."""
    past_step = _integer("past_step", past_step)
    delay = validate_delay_action_step(delay_action_step)
    horizon = _integer("horizon", horizon)
    if past_step < 0:
        raise ValueError(f"past_step must be >= 0, got {past_step}")
    if horizon <= 1:
        raise ValueError(f"horizon must be > 1, got {horizon}")
    coordinate = past_step + delay
    lower = math.floor(coordinate)
    upper = math.ceil(coordinate)
    if lower < 0 or upper >= horizon - 1:
        raise ValueError(
            "action interpolation endpoints are outside executable slots: "
            f"coordinate={coordinate}, lower={lower}, upper={upper}, "
            f"executable=[0, {horizon - 2}], horizon={horizon}")
    fractional = lower != upper
    if terminal_noise_levels is None:
        if fractional:
            raise ValueError(
                "fractional delay_action_step requires terminal action-noise levels")
        lower_noise = upper_noise = 0
    else:
        if len(terminal_noise_levels) != horizon:
            raise ValueError(
                "terminal action-noise level count must equal horizon: "
                f"{len(terminal_noise_levels)} != {horizon}")
        lower_noise = int(terminal_noise_levels[lower])
        upper_noise = int(terminal_noise_levels[upper])
        if lower_noise != 0 or upper_noise != 0:
            raise ValueError(
                "delay_action_step requires terminally clean selected "
                f"endpoints; lower={lower} noise={lower_noise}, "
                f"upper={upper} noise={upper_noise}")
    return ActionSelection(
        lower, upper, coordinate - lower, lower_noise, upper_noise)


def configure_actor_action_selection(
    actor, n_obs_steps: int, delay_action_step: float
) -> tuple[int, int]:
    """Configure the actor's endpoint-specific final clean transition."""
    delay = validate_delay_action_step(delay_action_step)
    coordinate = (_integer("n_obs_steps", n_obs_steps) - 1) + delay
    lower, upper = math.floor(coordinate), math.ceil(coordinate)
    horizon = int(actor.horizon)
    if lower < 0 or upper >= horizon - 1:
        raise ValueError(
            "action selection endpoints are outside executable slots: "
            f"lower={lower}, upper={upper}, executable=[0, {horizon - 2}]")
    actor._action_selection_clean_endpoints = (lower, upper)
    return lower, upper


def terminal_action_noise_levels(actor) -> tuple[int, ...]:
    """Derive terminal per-position noise from the actor's action schedule."""
    horizon = int(actor.horizon)
    schedule_name = str(getattr(actor, "action_schedule", "full"))
    rolling = (
        bool(getattr(actor, "randomize_noise_schedule", False))
        and not bool(getattr(actor, "use_ns_ddim", False))
    )
    levels = (0,) * horizon
    if rolling:
        scheduler = getattr(actor, "action_noise_scheduler", None)
        if scheduler is None:
            scheduler = getattr(actor, "noise_scheduler", None)
        if scheduler is None:
            raise ValueError(
                "rolling actor does not expose its configured action noise scheduler")
        matrix = scheduler.get_denoising_matrix(schedule_name, is_state=False)
        raw = [int(v) for v in matrix[-1].detach().cpu().tolist()]
        if not getattr(actor, "ddim_steps", None):
            raw = [max(v - 1, 0) for v in raw]
        for index in getattr(actor, "_action_selection_clean_endpoints", ()):
            raw[index] = 0
        levels = tuple(raw)
    return levels


def format_action_selection(selection: ActionSelection) -> str:
    return (
        f"lower={selection.lower_index} noise={selection.lower_noise_level}, "
        f"upper={selection.upper_index} noise={selection.upper_noise_level}, "
        f"alpha={selection.alpha:.6g}")


def select_action_for_agent(
    action_trajectory: torch.Tensor,
    bc_agent,
    n_obs_steps: int,
    delay_action_step: float = 0,
) -> torch.Tensor:
    """Schedule-aware selection with one clear runtime contract log."""
    actor = bc_agent.actor
    if action_trajectory.dim() != 3:
        return select_action(
            action_trajectory, n_obs_steps, delay_action_step)
    levels = terminal_action_noise_levels(actor)
    selection = action_selection(
        n_obs_steps - 1, delay_action_step, action_trajectory.shape[1], levels)
    log_key = (float(delay_action_step), selection)
    if getattr(actor, "_action_selection_log_key", None) != log_key:
        print(f"[ActionSelection] {format_action_selection(selection)}")
        actor._action_selection_log_key = log_key
    return select_action(
        action_trajectory, n_obs_steps, delay_action_step, levels)


def selected_action_index(past_step: int, delay_action_step: float, horizon: int) -> int:
    """Return ``past_step + delay_action_step`` after fail-closed validation.

    All values are zero-based tensor coordinates. Runners preserve their legacy
    behavior by passing ``past_step=n_obs_steps - 1``.
    """
    selection = action_selection(past_step, delay_action_step, horizon)
    if selection.lower_index != selection.upper_index:
        raise ValueError(
            "selected_action_index requires an integral selected coordinate")
    return selection.lower_index


def select_action(
    action_trajectory: torch.Tensor,
    n_obs_steps: int,
    delay_action_step: float = 0,
    terminal_noise_levels: Sequence[int] | None = None,
) -> torch.Tensor:
    """Select one action from ``[batch, horizon, action_dim]``.

    Two-dimensional policy outputs already contain a selected action and only
    accept delay zero; a delay cannot be applied without a trajectory.
    """
    delay_action_step = validate_delay_action_step(delay_action_step)
    if action_trajectory.dim() == 2:
        if delay_action_step != 0:
            raise ValueError(
                "delay_action_step requires a 3-D action trajectory; "
                f"got shape {tuple(action_trajectory.shape)}")
        return action_trajectory
    if action_trajectory.dim() != 3:
        raise ValueError(
            "action trajectory must have shape [batch, horizon, action_dim] "
            f"or [batch, action_dim], got {tuple(action_trajectory.shape)}")
    n_obs_steps = _integer("n_obs_steps", n_obs_steps)
    if n_obs_steps <= 0:
        raise ValueError(f"n_obs_steps must be > 0, got {n_obs_steps}")
    selection = action_selection(
        n_obs_steps - 1, delay_action_step, action_trajectory.shape[1],
        terminal_noise_levels)
    lower = action_trajectory[:, selection.lower_index, :]
    if selection.alpha == 0.0:
        return lower
    upper = action_trajectory[:, selection.upper_index, :]
    return torch.lerp(lower, upper, selection.alpha)
