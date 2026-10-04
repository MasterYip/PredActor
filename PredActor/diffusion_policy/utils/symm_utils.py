import torch


def get_joint_permutation_matrix(joint_names):
    """Build a joint-index permutation vector that swaps left↔right joints.

    For each left joint (e.g. "left_hip_pitch_joint") the corresponding right
    joint ("right_hip_pitch_joint") is found and their indices are swapped.
    The result is an integer tensor `p` such that `p[i]` is the index of joint
    `i`'s mirror partner (or `i` itself for bilateral joints like waist).

    Used to construct the joint reflection matrix Q via:
        Q[i, p[i]] = jref[i]   (permute + sign flip)

    Args:
        joint_names: list[str] — ordered joint name list (length N_joints).

    Returns:
        matrix: (N_joints,) LongTensor — permutation indices.
    """
    left_names = [name for name in joint_names if name.startswith('left')]
    right_names = [name for name in joint_names if name.startswith('right')]

    if len(left_names) != len(right_names):
        raise ValueError("The number of left and right body parts must be equal for permutation.")

    matrix = torch.arange(len(joint_names))

    for i, left_name in enumerate(left_names):
        left_index = joint_names.index(left_name)
        right_name = 'right' + left_name.split('left')[1]

        if right_name in joint_names:
            right_index = joint_names.index(right_name)
            matrix[left_index] = right_index
            matrix[right_index] = left_index
    return matrix


def get_joint_reflection_matrix(joint_names):
    """Build a per-joint sign vector for left-right reflection.

    Under a left-right body reflection, most joints keep the same sign
    (pitch, knee flex, etc.), but **roll** and **yaw** joints negate because
    they rotate around axes that flip direction under the reflection.

    Returns:
        matrix: (N_joints,) FloatTensor — +1 or -1 per joint.
    """
    matrix = torch.ones(len(joint_names))

    for i, name in enumerate(joint_names):
        if 'roll' in name or 'yaw' in name:
            matrix[i] = -1
    return matrix


def get_body_permutation_matrix(body_names):
    """Build a body-index permutation vector that swaps left↔right bodies.

    Identical in structure to get_joint_permutation_matrix but operates on
    the rigid-body list (30 bodies for G1) rather than the joint list.

    Used to build Q_Rd and Q_Rd_pseudo (see get_reflect_reps).

    Args:
        body_names: list[str] — ordered body name list (length N_bodies).

    Returns:
        matrix: (N_bodies,) LongTensor — permutation indices.
    """
    left_names = [name for name in body_names if name.startswith('left')]
    right_names = [name for name in body_names if name.startswith('right')]

    if len(left_names) != len(right_names):
        raise ValueError("The number of left and right body parts must be equal for permutation.")

    matrix = torch.arange(len(body_names))

    for i, left_name in enumerate(left_names):
        left_index = body_names.index(left_name)
        right_name = 'right' + left_name.split('left')[1]

        if right_name in body_names:
            right_index = body_names.index(right_name)
            matrix[left_index] = right_index
            matrix[right_index] = left_index
    return matrix


def get_reflect_op(reps):
    """Assemble a block-diagonal reflection operator from a list of square blocks.

    Each entry in `reps` is the reflection matrix for one group of state dims
    (e.g. body positions, root rotation, joint velocities). The final operator
    is their direct sum (block-diagonal concatenation):

        reflect_op = block_diag(reps[0], reps[1], ..., reps[k])

    Applying this matrix to a concatenated state vector reflects all groups
    simultaneously.

    Args:
        reps: list[Tensor] — square matrices, one per state group.

    Returns:
        reflect_op: (sum(shapes), sum(shapes)) FloatTensor.
    """
    reps_shape = []
    for i in range(len(reps)):
        assert reps[i].shape[1] == reps[i].shape[0]
        reps_shape.append(reps[i].shape[0])

    reflect_op = torch.zeros((sum(reps_shape), sum(reps_shape)))

    for i in range(len(reps)):
        idx0 = sum(reps_shape[:i])
        idx1 = sum(reps_shape[:i + 1])
        reflect_op[idx0:idx1, idx0:idx1] = reps[i]

    return reflect_op


def get_reflect_reps(body_names, joint_names):
    """Build all primitive left-right reflection matrices for the G1 robot.

    Returns five matrices that cover every type of quantity in the state vector:

    Coordinate reflection primitives
    ---------------------------------
    Rd  (3×3)
        Flips the Y-axis: diag(1, -1, 1).
        Applied to **positions** and **linear velocities** — the lateral (Y)
        component negates under a sagittal-plane reflection.

    Rd_pseudo  (3×3)
        Flips X and Z axes: diag(-1, 1, -1).
        Applied to **rotation vectors** and **angular velocities** — these are
        axial (pseudo-vector) quantities and flip on the transverse axes instead.

    Per-joint matrix
    -----------------
    Q  (N_joints × N_joints)
        Simultaneously permutes left↔right joints AND negates roll/yaw joints:
            Q[i, jperm[i]] = jref[i]
        A reflected robot has its left and right joints swapped, and roll/yaw
        angles negate because their rotation axes flip direction.

    Per-body matrices
    ------------------
    Q_Rd  (3*N_bodies × 3*N_bodies)
        Combined body-permutation + Rd rotation. For each body i:
            Q_Rd[3i:3i+3, 3*bperm[i]:3*bperm[i]+3] = Rd
        Flattened from a 4D (N_bodies, 3, N_bodies, 3) tensor via permute+reshape.
        Applied to body positions and body linear velocities (vectors → flip Y).

    Q_Rd_pseudo  (3*N_bodies × 3*N_bodies)
        Same as Q_Rd but using Rd_pseudo instead of Rd.
        Applied to body angular velocities (pseudo-vectors → flip X,Z).

    Usage in G1_Dataset.get_reflection_ops()
    -----------------------------------------
    For the standard 192-dim state the full obs reflection operator is:
        block_diag(Q_Rd, Q_Rd, Rd, Rd_pseudo, Rd, Rd_pseudo)
         body_pos  body_vel  rpos  rrot       rlv  rav

    For joint-space states (e.g. G1_Dataset_Q):
        block_diag(Rd, Rd_pseudo, Rd, Rd_pseudo, Q, Q)
         root_pos  root_rot   rlv   rav        jpos jvel

    Args:
        body_names:  list[str] — ordered body name list (N_bodies entries).
        joint_names: list[str] — ordered joint name list (N_joints entries).

    Returns:
        Q            (N_joints, N_joints)
        Rd           (3, 3)
        Rd_pseudo    (3, 3)
        Q_Rd         (3*N_bodies, 3*N_bodies)
        Q_Rd_pseudo  (3*N_bodies, 3*N_bodies)
        num_bodies   int
    """
    # --- Coordinate reflection primitives ---
    Rd = torch.eye(3)
    Rd[1, 1] = -1           # flip Y  (lateral axis)

    Rd_pseudo = torch.eye(3)
    Rd_pseudo[[0, 2], [0, 2]] = -1   # flip X, Z  (transverse axes for pseudo-vectors)

    # --- Joint matrix Q: permute left↔right + sign flip for roll/yaw ---
    jperm = get_joint_permutation_matrix(joint_names)
    jref  = get_joint_reflection_matrix(joint_names)
    Q = torch.zeros((len(jperm), len(jperm)))
    Q[torch.arange(len(jperm)), jperm] = jref

    # --- Body matrices Q_Rd and Q_Rd_pseudo: permute bodies + rotate 3D coords ---
    # Build as 4D block tensors (N_bodies, 3, N_bodies, 3), then flatten.
    # Q_Rd[i, bperm[i]] = Rd  means: body i's coordinates map to body bperm[i]
    # with a coordinate rotation by Rd applied.
    bperm = get_body_permutation_matrix(body_names)

    Q_Rd = torch.zeros((len(bperm), len(bperm), 3, 3))
    Q_Rd[torch.arange(len(bperm)), bperm] = Rd[None, :, :].repeat(len(bperm), 1, 1)
    Q_Rd = Q_Rd.permute(0, 2, 1, 3).reshape(len(bperm) * 3, len(bperm) * 3)

    Q_Rd_pseudo = torch.zeros((len(bperm), len(bperm), 3, 3))
    Q_Rd_pseudo[torch.arange(len(bperm)), bperm] = Rd_pseudo[None, :, :].repeat(len(bperm), 1, 1)
    Q_Rd_pseudo = Q_Rd_pseudo.permute(0, 2, 1, 3).reshape(len(bperm) * 3, len(bperm) * 3)

    return Q, Rd, Rd_pseudo, Q_Rd, Q_Rd_pseudo, len(bperm)
