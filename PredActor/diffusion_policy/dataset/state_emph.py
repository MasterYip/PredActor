"""Emphasis (projection) matrix generation for diffusion guidance.

Public API
----------
EmphMatGen             — build emphasis matrices from a DataProfile
build_legacy_emphasis  — reconstruct emphasis matrices from old string mode names
                         (backward compat for existing YAML configs)

The matrix amplifies certain observation dimensions before the score network
processes them, making the denoising more sensitive to task-relevant features.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import torch


def build_profile_emphasis_projection(
    profile,
    device: torch.device,
    obs_reflect_op: Optional[torch.Tensor] = None,
    seed: Optional[int] = None,
) -> torch.Tensor:
    """Build the profile projection, optionally without consuming global RNG.

    An explicit seed is useful for paired architecture ablations: both actors
    receive the exact same fixed random projection while their trainable weight
    initialization continues to follow the ordinary training seed.
    """
    device = torch.device(device)
    if seed is None:
        return EmphMatGen.build(profile, device, obs_reflect_op)

    cuda_devices = []
    if device.type == "cuda":
        cuda_devices = [
            device.index if device.index is not None else torch.cuda.current_device()
        ]
    with torch.random.fork_rng(devices=cuda_devices):
        torch.manual_seed(int(seed))
        if cuda_devices:
            torch.cuda.manual_seed_all(int(seed))
        return EmphMatGen.build(profile, device, obs_reflect_op)


# ---------------------------------------------------------------------------
# EmphMatGen — profile-driven emphasis matrix builder
# ---------------------------------------------------------------------------

class EmphMatGen:
    """Generate emphasis projection matrices for diffusion guidance.

    All construction is based on the profile's per-term weight declarations.
    """

    @staticmethod
    def build(
        profile,
        device: torch.device,
        obs_reflect_op: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Build the emphasis matrix from profile weights.

        For type="same":        diagonal weight matrix  (obs_dim × obs_dim)
        For type="random":      random projection scaled by weights  (obs_dim × obs_dim)
        For type="random_symm": symmetric random + identity copy  (obs_dim × 2*obs_dim)
        For type="random_double": non-symmetric doubling  (obs_dim × 2*obs_dim)

        Args:
            profile:        DataProfile with observation.state_emph filled in.
            device:         Target torch device.
            obs_reflect_op: Left-right reflection operator (required for random_symm).

        Returns:
            Tensor of shape (base_dim, out_dim).
        """
        from diffusion_policy.dataset.term_compose import TERM_DIMS

        emph = profile.observation.state_emph
        term_dims = []
        weights_list = []
        for term in profile.observation.terms:
            try:
                d = EmphMatGen._term_dim(term)
            except ValueError:
                d = 3  # fallback for unknown variable-dim terms
            w = emph.weights.get(term, 1.0)
            term_dims.append(d)
            weights_list.extend([w] * d)

        obs_dim = sum(term_dims)
        w_vec = torch.tensor(weights_list, dtype=torch.float32, device=device)

        mode = emph.type

        if mode == "same":
            return torch.diag(w_vec)

        elif mode == "random":
            A = torch.randn((obs_dim, obs_dim), device=device) / np.sqrt(obs_dim)
            return torch.diag(w_vec) @ A

        elif mode in ("random_symm", "random_double"):
            if obs_reflect_op is None:
                from diffusion_policy.dataset.state_normalize import build_g1_reflect_ops
                from diffusion_policy.dataset.g1_dataset import DEFAULT_EE_IDXS
                obs_reflect_op, _ = build_g1_reflect_ops(
                    profile.observation.terms, DEFAULT_EE_IDXS
                )
                obs_reflect_op = obs_reflect_op.to(device)
            if mode == "random_symm":
                return EmphMatGen._build_random_symm(w_vec, obs_reflect_op.to(device))
            else:
                return EmphMatGen._build_random_double(w_vec, obs_reflect_op.to(device))

        else:
            raise ValueError(f"Unknown state_emph type: '{mode}'")

    @staticmethod
    def _term_dim(term: str) -> int:
        from diffusion_policy.dataset.term_compose import TERM_DIMS, _init_term_dims
        if TERM_DIMS.get("joint_pos") is None:
            _init_term_dims()
        d = TERM_DIMS.get(term)
        if d is not None:
            return d
        raise ValueError(f"Cannot statically determine dimension for term '{term}'")

    @staticmethod
    def _build_random_symm(w_vec: torch.Tensor, obs_r: torch.Tensor) -> torch.Tensor:
        """Symmetric random projection that doubles the state space.

        Output shape: (base, 2*base) where base = obs_dim.
        Columns 0..base-1 : B @ A  (emphasis-aware symmetric random projection)
        Columns base..2*base-1: I  (lossless identity copy)
        """
        base = w_vec.shape[0]
        device = w_vec.device
        mask = obs_r.sum(dim=0) < 0  # antisymmetric dims

        A = torch.zeros((base, base), device=device)
        A[mask, : base // 2] = A[mask, : base // 2].normal_()
        A[~mask, base // 2:] = A[~mask, base // 2:].normal_()
        A = (A + obs_r.abs().to(A.dtype) @ A) / 2
        n_anti = int(mask.sum())
        n_sym = base - n_anti
        if n_anti > 0:
            A[mask, : base // 2] /= np.sqrt(n_anti)
        if n_sym > 0:
            A[~mask, base // 2:] /= np.sqrt(n_sym)

        B_mat = torch.diag(w_vec)
        B_nom = torch.eye(base, device=device)
        return torch.cat((B_mat @ A, B_nom), dim=1)

    @staticmethod
    def _build_random_double(w_vec: torch.Tensor, obs_r: torch.Tensor) -> torch.Tensor:
        """Non-symmetric doubling: random projection + identity. Shape (base, 2*base)."""
        base = w_vec.shape[0]
        device = w_vec.device
        A = torch.randn((base, base), device=device) / np.sqrt(base)
        B_mat = torch.diag(w_vec)
        B_nom = torch.eye(base, device=device)
        return torch.cat((B_mat @ A, B_nom), dim=1)

    # ------------------------------------------------------------------
    # Legacy string-mode support (for existing YAML configs that still use
    # old emphasis names like "random_emph_symm", "g1q_emph", etc.)
    # ------------------------------------------------------------------

    @staticmethod
    def build_from_mode(
        mode: str,
        state_dim: int,
        device: torch.device,
    ) -> torch.Tensor:
        """Build emphasis matrix from legacy string mode name.

        This method is provided solely for backward compatibility with
        existing experiment configs that specify `state_emphasis` as a
        string (e.g. "random_emph_symm", "g1q_emph").  New code should
        use `EmphMatGen.build()` with a DataProfile instead.
        """
        return build_legacy_emphasis(mode, state_dim, device)


# ---------------------------------------------------------------------------
# Legacy emphasis matrix builder (previously emph_mat_legacy.py)
# ---------------------------------------------------------------------------

def build_legacy_emphasis(mode: str, state_dim: int, device: torch.device) -> torch.Tensor:
    """Reconstruct the emphasis matrix that ObsComposer.build_emphasis_matrix() used to return."""

    if mode == "rand":
        return torch.randn((state_dim, state_dim), device=device) / np.sqrt(state_dim)

    elif mode == "same":
        return torch.eye(state_dim, device=device)

    elif mode == "emph_global":
        m = torch.eye(state_dim, device=device)
        m[torch.arange(144, 150), torch.arange(144, 150)] = 3
        m[torch.arange(162, 165), torch.arange(162, 165)] = 3
        return m

    elif mode == "random_emph":
        A = torch.randn((state_dim, state_dim), device=device)
        B = torch.eye(state_dim, device=device)
        B[torch.arange(144, 150), torch.arange(144, 150)] = 5
        B[torch.arange(162, 165), torch.arange(162, 165)] = 5
        return (B @ A) / np.sqrt(state_dim - 9 + 9 * 5 ** 2)

    elif mode == "random_emph_double":
        base = state_dim // 2
        A = torch.randn((base, base), device=device)
        B = torch.eye(base, device=device)
        B_nom = torch.eye(base, device=device)
        start = base - 12
        B[torch.arange(start, start + 6), torch.arange(start, start + 6)] = 4
        B[torch.arange(start + 6, start + 12), torch.arange(start + 6, start + 12)] = 4
        m = B @ A / np.sqrt(base - 9 / 2 + 9 * 4 ** 2 / 2)
        return torch.cat((m, B_nom), dim=1)

    elif mode == "random_emph_symm":
        base = state_dim // 2
        obs_r, _ = _get_standard_reflect_ops()
        return _symm_double(obs_r.to(device), base, start=base - 12, amp=4)

    elif mode == "g1q_emph":
        m = torch.eye(state_dim, device=device)
        m[torch.arange(0, 6), torch.arange(0, 6)] = 3
        m[torch.arange(6, 12), torch.arange(6, 12)] = 2
        m[torch.arange(41, 70), torch.arange(41, 70)] = 0.7
        return m

    elif mode == "g1rlobs_emph":
        if state_dim != 96:
            raise ValueError(f"g1rlobs_emph expects state_dim=96, got {state_dim}.")
        m = torch.eye(state_dim, device=device)
        m[torch.arange(0, 29), torch.arange(0, 29)] = 1.2
        m[torch.arange(29, 58), torch.arange(29, 58)] = 0.9
        m[torch.arange(58, 61), torch.arange(58, 61)] = 3.0
        m[torch.arange(61, 64), torch.arange(61, 64)] = 2.0
        m[torch.arange(64, 67), torch.arange(64, 67)] = 2.5
        m[torch.arange(67, 96), torch.arange(67, 96)] = 0.85
        return m

    elif mode == "g1rlpos_emph":
        if state_dim != 102:
            raise ValueError(f"g1rlpos_emph expects state_dim=102, got {state_dim}.")
        m = torch.eye(state_dim, device=device)
        m[torch.arange(0, 29), torch.arange(0, 29)] = 1.2
        m[torch.arange(29, 58), torch.arange(29, 58)] = 0.9
        m[torch.arange(58, 61), torch.arange(58, 61)] = 2.0
        m[torch.arange(61, 64), torch.arange(61, 64)] = 1.2
        m[torch.arange(64, 67), torch.arange(64, 67)] = 1.2
        m[torch.arange(67, 96), torch.arange(67, 96)] = 0.65
        m[torch.arange(96, 99), torch.arange(96, 99)] = 2.0
        m[torch.arange(99, 102), torch.arange(99, 102)] = 2.0
        return m

    elif mode == "g1novel_emph":
        if state_dim != 320:
            raise ValueError(f"g1novel_emph expects state_dim=320, got {state_dim}.")
        base = state_dim // 2
        from diffusion_policy.utils.symm_utils import get_reflect_reps, get_reflect_op
        from diffusion_policy.dataset.g1_dataset import BODY_NAMES, JOINT_NAMES
        Q, Rd, Rd_pseudo, Q_Rd, Q_Rd_pseudo, _ = get_reflect_reps(BODY_NAMES, JOINT_NAMES)
        obs_reps = [Q_Rd, Rd, Rd_pseudo, Rd, Rd_pseudo, Q, Q]
        obs_r = get_reflect_op(obs_reps).to(device)
        m = _symm_double_custom(obs_r, base,
                                amp_ranges=[(90, 96, 4.0), (99, 102, 3.0)])
        return m

    elif mode == "g1prdp_emph":
        if state_dim != 64:
            raise ValueError(f"g1prdp_emph expects state_dim=64, got {state_dim}.")
        m = torch.eye(state_dim, device=device)
        m[torch.arange(0, 29), torch.arange(0, 29)] = 1.2
        m[torch.arange(29, 58), torch.arange(29, 58)] = 0.9
        m[torch.arange(58, 61), torch.arange(58, 61)] = 2.5
        m[torch.arange(61, 64), torch.arange(61, 64)] = 2.0
        return m

    elif mode == "g1prdp_emph_symm":
        if state_dim != 128:
            raise ValueError(f"g1prdp_emph_symm expects state_dim=128, got {state_dim}.")
        base = state_dim // 2
        from diffusion_policy.utils.symm_utils import get_reflect_reps, get_reflect_op
        from diffusion_policy.dataset.g1_dataset import BODY_NAMES, JOINT_NAMES
        Q, Rd, Rd_pseudo, _, _, _ = get_reflect_reps(BODY_NAMES, JOINT_NAMES)
        obs_reps = [Q, Q, Rd, Rd_pseudo]
        obs_r = get_reflect_op(obs_reps).to(device)
        m = _symm_double_custom(obs_r, base, amp_ranges=[(58, 64, 4.0)])
        return m

    elif mode == "g1wq_emph_symm":
        if state_dim != 500:
            raise ValueError(f"g1wq_emph_symm expects state_dim=500, got {state_dim}.")
        base = state_dim // 2
        from diffusion_policy.utils.symm_utils import get_reflect_reps, get_reflect_op
        from diffusion_policy.dataset.g1_dataset import BODY_NAMES, JOINT_NAMES
        Q, Rd, Rd_pseudo, Q_Rd, Q_Rd_pseudo, _ = get_reflect_reps(BODY_NAMES, JOINT_NAMES)
        obs_reps = [Q_Rd, Q_Rd, Rd, Rd_pseudo, Rd, Rd_pseudo, Q, Q]
        obs_r = get_reflect_op(obs_reps).to(device)
        m = _symm_double_custom(obs_r, base,
                                amp_ranges=[(180, 186, 4.0), (189, 192, 4.0)])
        return m

    elif mode == "elair_emph":
        m = torch.eye(state_dim, device=device)
        m[torch.arange(0, 6), torch.arange(0, 6)] = 2
        m[torch.arange(9, 12), torch.arange(9, 12)] = 2
        m[torch.arange(12, 30), torch.arange(12, 30)] = 1.5
        return m

    elif mode == "copy":
        base = state_dim - 9 * 10
        mat = torch.eye(base, device=device)
        m = torch.zeros((base, base + 9 * 10), device=device)
        m[:144, :144] = mat[:144, :144]
        for i in range(10):
            m[144:150, 144 + i * 6: 144 + (i + 1) * 6] = mat[144:150, 144:150]
        m[150:162, 210:222] = mat[150:162, 150:162]
        for i in range(10):
            m[162:165, 222 + i * 3: 222 + (i + 1) * 3] = mat[162:165, 162:165]
        return m

    else:
        raise ValueError(f"Unknown legacy state_emphasis mode: '{mode}'")


def _get_standard_reflect_ops():
    """Build reflect ops for the standard 192-dim G1 observation."""
    from diffusion_policy.utils.symm_utils import get_reflect_reps, get_reflect_op
    from diffusion_policy.dataset.g1_dataset import BODY_NAMES, JOINT_NAMES
    Q, Rd, Rd_pseudo, Q_Rd, Q_Rd_pseudo, _ = get_reflect_reps(BODY_NAMES, JOINT_NAMES)
    obs_reps = [Q_Rd, Q_Rd, Rd, Rd_pseudo, Rd, Rd_pseudo]
    obs_r = get_reflect_op(obs_reps)
    act_r = get_reflect_op([Q])
    return obs_r, act_r


def _symm_double(obs_r: torch.Tensor, base: int, start: int, amp: float) -> torch.Tensor:
    """Standard symmetric-double used by random_emph_symm."""
    device = obs_r.device
    mask = obs_r.sum(dim=0) < 0
    A = torch.zeros((base, base), device=device)
    A[mask, : base // 2] = A[mask, : base // 2].normal_()
    A[~mask, base // 2:] = A[~mask, base // 2:].normal_()
    A = (A + obs_r.abs().to(A.dtype) @ A) / 2
    n_anti = int(mask.sum())
    n_sym = base - n_anti
    if n_anti > 0:
        A[mask, : base // 2] /= np.sqrt(n_anti)
    if n_sym > 0:
        A[~mask, base // 2:] /= np.sqrt(n_sym)
    B = torch.eye(base, device=device)
    B_nom = torch.eye(base, device=device)
    B[torch.arange(start, start + 6), torch.arange(start, start + 6)] = amp
    B[torch.arange(start + 9, start + 12), torch.arange(start + 9, start + 12)] = amp
    return torch.cat((B @ A, B_nom), dim=1)


def _symm_double_custom(
    obs_r: torch.Tensor, base: int, amp_ranges: list
) -> torch.Tensor:
    """Symmetric-double with arbitrary amplification ranges.

    amp_ranges: list of (start, end, amplitude) tuples.
    """
    device = obs_r.device
    mask = obs_r.sum(dim=0) < 0
    A = torch.zeros((base, base), device=device)
    A[mask, : base // 2] = A[mask, : base // 2].normal_()
    A[~mask, base // 2:] = A[~mask, base // 2:].normal_()
    A = (A + obs_r.abs().to(A.dtype) @ A) / 2
    n_anti = int(mask.sum())
    n_sym = base - n_anti
    if n_anti > 0:
        A[mask, : base // 2] /= np.sqrt(n_anti)
    if n_sym > 0:
        A[~mask, base // 2:] /= np.sqrt(n_sym)
    B = torch.eye(base, device=device)
    B_nom = torch.eye(base, device=device)
    for (s, e, amp) in amp_ranges:
        B[torch.arange(s, e), torch.arange(s, e)] = amp
    return torch.cat((B @ A, B_nom), dim=1)
