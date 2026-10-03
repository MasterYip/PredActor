"""
G1 Robot Forward Kinematics using pytorch-kinematics.

Drop-in replacement for G1ForwardKinematics (pinocchio) with additional
batch operation support: joint_pos can be [29] (single) or [B, 29] (batch).

Install:
    pip install pytorch-kinematics
"""

import numpy as np
from .g1fk_pinocchio import G1ForwardKinematics
import torch
from typing import Optional, Dict, List, Union

from .g1_reindex import (
    ISAACLAB_BODY_NAMES,
    ISAACLAB_DOF_NAMES,
    MUJOCO_DOF_NAMES,
    create_isaaclab_to_mujoco_mapping,
)


class G1TorchForwardKinematics:
    """
    Forward kinematics calculator for G1 robot using pytorch-kinematics.

    Supports both single-sample and batch FK computation.

    Input (single):
        joint_pos  [29]              – joint positions in MUJOCO (SDK) order
        joint_vel  [29]              – joint velocities in MUJOCO order
        imu_pose   [3] (RPY) or [4] (wxyz quaternion)
        imu_gyro   [3]              – angular velocity in world frame

    Input (batch):
        joint_pos  [B, 29]
        joint_vel  [B, 29]
        imu_pose   [B, 3] or [B, 4]
        imu_gyro   [B, 3]

    Output (single) → numpy arrays (same as G1ForwardKinematics/pinocchio):
        'body_pos'    [30, 3]
        'body_lin_vel'[30, 3]
        'root_pos'    [3]
        'root_rot'    [4]   (wxyz quaternion)
        'root_lin_vel'[3]
        'root_ang_vel'[3]
        'state'       [192]

    Output (batch) → torch tensors:
        'body_pos'    [B, 30, 3]
        'body_lin_vel'[B, 30, 3]
        'root_pos'    [B, 3]
        'root_rot'    [B, 4]
        'root_lin_vel'[B, 3]
        'root_ang_vel'[B, 3]
        'state'       [B, 192]
    """

    def __init__(
        self,
        urdf_path: str,
        device: str = "cpu",
        dtype: torch.dtype = torch.float32,
    ):
        """
        Args:
            urdf_path: Path to G1 URDF file.
            device:    Torch device ('cpu' or 'cuda').
            dtype:     Torch dtype (float32 recommended for speed).
        """
        try:
            import pytorch_kinematics as pk
        except ImportError as e:
            raise ImportError(
                "pytorch-kinematics is required for G1TorchForwardKinematics. "
                "Install it with: pip install pytorch-kinematics"
            ) from e

        self.device = device
        self.dtype = dtype
        self.urdf_path = urdf_path
        self.n_bodies = len(ISAACLAB_BODY_NAMES)

        # ------------------------------------------------------------------
        # Build full tree chain
        # ------------------------------------------------------------------
        with open(urdf_path, mode="rb") as f:
            urdf_content = f.read()

        full_chain = pk.build_chain_from_urdf(urdf_content)
        # NOTE: pk chain .to() is in-place, so we must build all SerialChains
        # while the full_chain is still on CPU, then move everything to device.

        # Joint names in URDF/chain order (may differ from SDK/MUJOCO order)
        self._chain_joint_names: List[str] = full_chain.get_joint_parameter_names()

        # ------------------------------------------------------------------
        # joint_remapping (from g1_reindex.create_isaaclab_to_mujoco_mapping):
        #   joint_remapping[chain_idx] = isaaclab_idx
        # Meaning: q_in_chain_order = q_in_isaaclab_order[:, joint_remapping]
        # This is the pinocchio-compatible interface used by apply_action_transform.
        # ------------------------------------------------------------------
        self.joint_remapping = create_isaaclab_to_mujoco_mapping(self._chain_joint_names)

        # _chain_to_mujoco_idx[chain_idx] = mujoco_idx
        # → q_in_chain_order = q_in_mujoco_order[:, _chain_to_mujoco_idx]
        # For the G1 robot the URDF chain order equals MUJOCO_DOF_NAMES order,
        # so this is the identity, but computed explicitly for correctness.
        self._chain_to_mujoco_idx: List[int] = []
        for name in self._chain_joint_names:
            if name in MUJOCO_DOF_NAMES:
                self._chain_to_mujoco_idx.append(MUJOCO_DOF_NAMES.index(name))
            else:
                raise ValueError(
                    f"Chain joint '{name}' not found in MUJOCO_DOF_NAMES. "
                    f"Check that MUJOCO_DOF_NAMES covers all URDF actuated joints."
                )

        # ------------------------------------------------------------------
        # Build one SerialChain per body for Jacobian / velocity computation.
        # All SerialChains are constructed while full_chain is still on CPU,
        # then everything is moved to device in one pass at the end.
        # ------------------------------------------------------------------
        self._body_serial_chains: List = []
        self._body_mujoco_indices: List[List[int]] = []

        for body_name in ISAACLAB_BODY_NAMES:
            sc = pk.SerialChain(full_chain, body_name)
            sc_joints = sc.get_joint_parameter_names()
            indices = []
            for jname in sc_joints:
                if jname in MUJOCO_DOF_NAMES:
                    indices.append(MUJOCO_DOF_NAMES.index(jname))
            self._body_serial_chains.append(sc)
            self._body_mujoco_indices.append(indices)

        # Move everything to target device/dtype now that all chains are built.
        self._full_chain = full_chain.to(device=device, dtype=dtype)
        self._body_serial_chains = [
            sc.to(device=device, dtype=dtype) for sc in self._body_serial_chains
        ]

        print(f"[G1TorchFK] Loaded URDF from {urdf_path}")
        print(f"  Chain joints  : {len(self._chain_joint_names)}")
        print(f"  Body links    : {self.n_bodies}")
        print(f"  Device / dtype: {device} / {dtype}")

    # ------------------------------------------------------------------
    # Public interface (mirrors G1ForwardKinematics / pinocchio)
    # ------------------------------------------------------------------

    def compute_fk(
        self,
        joint_pos: Union[np.ndarray, torch.Tensor],
        joint_vel: Union[np.ndarray, torch.Tensor],
        imu_pose: Optional[Union[np.ndarray, torch.Tensor]] = None,
        imu_gyro: Optional[Union[np.ndarray, torch.Tensor]] = None,
        base_lin_vel: Optional[Union[np.ndarray, torch.Tensor]] = None,
        base_pos: Optional[Union[np.ndarray, torch.Tensor]] = None,
        isaaclab_q_order: bool = False,
        # backward-compat alias
        imu_rpy: Optional[Union[np.ndarray, torch.Tensor]] = None,
    ) -> Dict[str, Union[np.ndarray, torch.Tensor]]:
        """
        Compute forward kinematics.

        Args:
            joint_pos      : [29] or [B, 29]  – in MUJOCO order (default) or IsaacLab order
            joint_vel      : [29] or [B, 29]
            imu_pose       : [3] RPY or [4] wxyz quat, or [B, 3] / [B, 4] for batch
            imu_gyro       : [3] or [B, 3]    – angular velocity in world frame
            base_lin_vel   : [3] or [B, 3]    – base linear velocity (zeros if None)
            base_pos       : [3] or [B, 3]    – base position (zeros if None)
            isaaclab_q_order: if True, joint_pos/vel are in IsaacLab DOF order
            imu_rpy        : deprecated alias for imu_pose (RPY only)

        Returns:
            For single input → dict of numpy arrays
            For batch input  → dict of torch tensors with leading B dimension
        """
        # ---- resolve imu_pose alias ----
        if imu_pose is None and imu_rpy is None:
            raise ValueError("imu_pose (or deprecated imu_rpy) must be provided")
        if imu_pose is None:
            imu_pose = imu_rpy  # backward compat

        # ---- detect batch ----
        is_batch = (
            (isinstance(joint_pos, np.ndarray) and joint_pos.ndim == 2)
            or (isinstance(joint_pos, torch.Tensor) and joint_pos.ndim == 2)
        )

        if is_batch:
            return self._compute_fk_batch(
                joint_pos, joint_vel, imu_pose, imu_gyro,
                base_lin_vel, base_pos, isaaclab_q_order
            )
        else:
            return self._compute_fk_single(
                joint_pos, joint_vel, imu_pose, imu_gyro,
                base_lin_vel, base_pos, isaaclab_q_order
            )

    # ------------------------------------------------------------------
    # Single-sample FK (returns numpy – backward compatible)
    # ------------------------------------------------------------------

    def _compute_fk_single(
        self,
        joint_pos, joint_vel, imu_pose, imu_gyro,
        base_lin_vel, base_pos, isaaclab_q_order,
    ) -> Dict[str, np.ndarray]:

        # Expand to batch=1 and call batch path
        def _to_np(x):
            if x is None:
                return None
            if isinstance(x, torch.Tensor):
                return x.cpu().numpy()
            return np.asarray(x, dtype=np.float32)

        joint_pos = _to_np(joint_pos)[np.newaxis]   # [1, 29]
        joint_vel = _to_np(joint_vel)[np.newaxis]
        imu_pose  = _to_np(imu_pose)[np.newaxis]
        imu_gyro  = _to_np(imu_gyro)[np.newaxis] if imu_gyro is not None else None
        base_lin_vel = _to_np(base_lin_vel)[np.newaxis] if base_lin_vel is not None else None
        base_pos     = _to_np(base_pos)[np.newaxis]     if base_pos     is not None else None

        batch_result = self._compute_fk_batch(
            joint_pos, joint_vel, imu_pose, imu_gyro,
            base_lin_vel, base_pos, isaaclab_q_order
        )

        # Squeeze batch dim and convert to numpy
        out = {}
        for k, v in batch_result.items():
            arr = v.squeeze(0).cpu().numpy()  # remove B=1 dim
            out[k] = arr.astype(np.float32)
        return out

    # ------------------------------------------------------------------
    # Batch FK (returns torch tensors)
    # ------------------------------------------------------------------

    def _compute_fk_batch(
        self,
        joint_pos, joint_vel, imu_pose, imu_gyro,
        base_lin_vel, base_pos, isaaclab_q_order,
    ) -> Dict[str, torch.Tensor]:

        dev = self.device
        dt  = self.dtype

        def _t(x, shape_hint=None):
            """Convert to torch tensor on device."""
            if x is None:
                return None
            if isinstance(x, torch.Tensor):
                return x.to(device=dev, dtype=dt)
            return torch.tensor(np.asarray(x, dtype=np.float32), device=dev, dtype=dt)

        q   = _t(joint_pos)   # [B, 29]
        dq  = _t(joint_vel)   # [B, 29]
        gyro = _t(imu_gyro)    # [B, 3] or None
        bv   = _t(base_lin_vel)
        bp   = _t(base_pos)

        B = q.shape[0]

        # ---- IMU pose → quaternion wxyz [B, 4] and RPY [B, 3] ----
        imu_t = _t(imu_pose)
        if imu_t.shape[-1] == 4:
            imu_quat_wxyz = imu_t                          # [B, 4]
            imu_rpy  = self._quat_wxyz_to_rpy_batch(imu_t) # [B, 3]
        else:
            imu_rpy = imu_t                               # [B, 3]
            imu_quat_wxyz = self._rpy_to_quat_wxyz_batch(imu_t)  # [B, 4]

        # Rotation matrix base → world  [B, 3, 3]
        R = self._rpy_to_rotmat_batch(imu_rpy)  # [B, 3, 3]

        # ---- Build joint-value tensor in chain order ----
        # joint_remapping[chain_idx] = isaaclab_idx  (from g1_reindex)
        # _chain_to_mujoco_idx[chain_idx] = mujoco_idx
        if isaaclab_q_order:
            # q is in isaaclab order → reindex to chain order
            jremap = torch.tensor(self.joint_remapping, device=dev, dtype=torch.long)
            q_chain = q[:, jremap]   # [B, 29]
        else:
            # q is in mujoco order → reindex to chain order
            jremap = torch.tensor(self._chain_to_mujoco_idx, device=dev, dtype=torch.long)
            q_chain = q[:, jremap]   # [B, 29]

        q_dict = {
            name: q_chain[:, i]                  # [B]  (pytorch_kinematics expects scalar-per-batch, not [B,1])
            for i, name in enumerate(self._chain_joint_names)
        }

        # ---- Body positions via full-chain FK (one pass, all links) ----
        with torch.no_grad():
            ret = self._full_chain.forward_kinematics(q_dict)

        body_pos_base = torch.zeros(B, self.n_bodies, 3, device=dev, dtype=dt)
        for bdy_idx, body_name in enumerate(ISAACLAB_BODY_NAMES):
            tg = ret[body_name]                # Transform object [B, 4, 4] or similar
            m  = tg.get_matrix()               # [B, 4, 4]
            body_pos_base[:, bdy_idx, :] = m[:, :3, 3]

        # ---- Base position ----
        base_position = bp if bp is not None else torch.zeros(B, 3, device=dev, dtype=dt)  # [B, 3]

        # ---- Body positions in world frame ----
        # p_world = R @ p_base + base_pos   [B, 30, 3]
        body_pos = torch.bmm(body_pos_base, R.transpose(1, 2)) + base_position.unsqueeze(1)
        # (equivalent: (R @ p_base.T).T = p_base @ R.T)

        # ---- Body linear velocities ----
        base_lin_vel_val = bv if bv is not None else torch.zeros(B, 3, device=dev, dtype=dt)
        angular_vel = gyro if gyro is not None else torch.zeros(B, 3, device=dev, dtype=dt)

        body_lin_vel = torch.zeros(B, self.n_bodies, 3, device=dev, dtype=dt)

        for bdy_idx, (sc, mujoco_indices) in enumerate(
            zip(self._body_serial_chains, self._body_mujoco_indices)
        ):
            if len(mujoco_indices) == 0:
                # Root body (pelvis) – no joints, velocity = base linear velocity
                body_lin_vel[:, bdy_idx, :] = base_lin_vel_val
                # + ω × r_body (but r_body = 0 for pelvis so this is 0)
                continue

            # Joint values for this serial chain [B, n_sc_joints]
            # mujoco_indices are indices into MUJOCO_DOF_NAMES (= chain order for G1)
            if isaaclab_q_order:
                # joint_remapping[mujoco_idx] = isaaclab_idx  (g1_reindex)
                isaaclab_indices = [self.joint_remapping[mi] for mi in mujoco_indices]
                q_sc  = q[:,  isaaclab_indices]   # [B, n_sc_joints]
                dq_sc = dq[:, isaaclab_indices]
            else:
                q_sc  = q[:,  mujoco_indices]     # [B, n_sc_joints]
                dq_sc = dq[:, mujoco_indices]

            # Jacobian [B, 6, n_sc_joints]
            with torch.no_grad():
                J = sc.jacobian(q_sc)

            # Linear velocity in base frame: v = J[:3, :] @ dq  [B, 3]
            vel_base = torch.bmm(J[:, :3, :], dq_sc.unsqueeze(-1)).squeeze(-1)

            # Transform to world frame: v_world = R @ v_base  [B, 3]
            vel_world = torch.bmm(vel_base.unsqueeze(1), R.transpose(1, 2)).squeeze(1)

            # Add root linear velocity and ω × r_body
            r_body = body_pos[:, bdy_idx, :] - base_position  # [B, 3]
            ang_contribution = torch.cross(angular_vel, r_body, dim=-1)  # [B, 3]

            body_lin_vel[:, bdy_idx, :] = vel_world + base_lin_vel_val + ang_contribution

        # ---- Root state ----
        if bp is not None:
            root_pos = base_position                     # [B, 3]
        else:
            root_pos = body_pos[:, 0, :]                 # pelvis position

        root_rot     = imu_quat_wxyz                     # [B, 4]  wxyz
        root_lin_vel = base_lin_vel_val                  # [B, 3]
        root_ang_vel = angular_vel                        # [B, 3]

        # ---- Concatenate 192-dim state ----
        state = torch.cat([
            body_pos.reshape(B, -1),       # [B, 90]
            body_lin_vel.reshape(B, -1),   # [B, 90]
            root_pos,                       # [B, 3]
            root_rot,                       # [B, 4]
            root_lin_vel,                   # [B, 3]
            root_ang_vel,                   # [B, 3]
        ], dim=-1)                          # [B, 193] – matches pinocchio (90+90+3+4+3+3=193)
        # NOTE: pinocchio outputs root_rot as 4-dim quaternion wxyz (see pinocchio.py lines 168-172)

        return {
            "body_pos":     body_pos,       # [B, 30, 3]
            "body_lin_vel": body_lin_vel,   # [B, 30, 3]
            "root_pos":     root_pos,       # [B, 3]
            "root_rot":     root_rot,       # [B, 4]  wxyz
            "root_lin_vel": root_lin_vel,   # [B, 3]
            "root_ang_vel": root_ang_vel,   # [B, 3]
            "state":        state,          # [B, 193]
        }

    # ------------------------------------------------------------------
    # Rotation utilities (batch)
    # ------------------------------------------------------------------

    @staticmethod
    def _rpy_to_rotmat_batch(rpy: torch.Tensor) -> torch.Tensor:
        """[B, 3] RPY → [B, 3, 3] rotation matrix (ZYX convention)."""
        roll  = rpy[:, 0]
        pitch = rpy[:, 1]
        yaw   = rpy[:, 2]

        cr, sr = torch.cos(roll),  torch.sin(roll)
        cp, sp = torch.cos(pitch), torch.sin(pitch)
        cy, sy = torch.cos(yaw),   torch.sin(yaw)

        # R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
        B = rpy.shape[0]
        R = torch.stack([
            torch.stack([cy*cp,  cy*sp*sr - sy*cr,  cy*sp*cr + sy*sr], dim=1),
            torch.stack([sy*cp,  sy*sp*sr + cy*cr,  sy*sp*cr - cy*sr], dim=1),
            torch.stack([-sp,    cp*sr,              cp*cr            ], dim=1),
        ], dim=1)  # [B, 3, 3]
        return R

    @staticmethod
    def _rpy_to_quat_wxyz_batch(rpy: torch.Tensor) -> torch.Tensor:
        """[B, 3] RPY → [B, 4] quaternion wxyz."""
        roll  = rpy[:, 0] * 0.5
        pitch = rpy[:, 1] * 0.5
        yaw   = rpy[:, 2] * 0.5

        cr, sr = torch.cos(roll),  torch.sin(roll)
        cp, sp = torch.cos(pitch), torch.sin(pitch)
        cy, sy = torch.cos(yaw),   torch.sin(yaw)

        qw = cr * cp * cy + sr * sp * sy
        qx = sr * cp * cy - cr * sp * sy
        qy = cr * sp * cy + sr * cp * sy
        qz = cr * cp * sy - sr * sp * cy

        return torch.stack([qw, qx, qy, qz], dim=1)  # [B, 4] wxyz

    @staticmethod
    def _quat_wxyz_to_rpy_batch(q: torch.Tensor) -> torch.Tensor:
        """[B, 4] quaternion wxyz → [B, 3] RPY."""
        qw, qx, qy, qz = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
        roll  = torch.atan2(2*(qw*qx + qy*qz), 1 - 2*(qx*qx + qy*qy))
        sinp  = 2*(qw*qy - qz*qx)
        pitch = torch.asin(torch.clamp(sinp, -1.0, 1.0))
        yaw   = torch.atan2(2*(qw*qz + qx*qy), 1 - 2*(qy*qy + qz*qz))
        return torch.stack([roll, pitch, yaw], dim=1)  # [B, 3]


# ---------------------------------------------------------------------------
# Factory function used by unitree_env.py / mujoco_env.py / runners
# ---------------------------------------------------------------------------

def build_fk_calculator(
    fk_type: str,
    urdf_path: str,
    device: str = "cpu",
    dtype: torch.dtype = torch.float32,
):
    """
    Factory for FK calculators.

    Args:
        fk_type  : 'torch' → G1TorchForwardKinematics
                   'pinocchio' → G1ForwardKinematics
        urdf_path: Path to G1 URDF.
        device   : Torch device (only used for 'torch' backend).
        dtype    : Torch dtype  (only used for 'torch' backend).

    Returns:
        An FK calculator with a `compute_fk(...)` method and a
        `joint_remapping` attribute.
    """
    fk_type = fk_type.lower()

    if fk_type == "torch":
        return G1TorchForwardKinematics(urdf_path=urdf_path, device=device, dtype=dtype)
    elif fk_type == "pinocchio":
        return G1ForwardKinematics(urdf_path=urdf_path)
    else:
        raise ValueError(
            f"Unknown fk_calculator_type '{fk_type}'. "
            "Choose 'torch' or 'pinocchio'."
        )
