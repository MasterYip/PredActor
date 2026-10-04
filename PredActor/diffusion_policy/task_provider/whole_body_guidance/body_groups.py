"""G1 robot body names, group definitions, and abbreviation labels.

These are shared by :class:`BodyGroupSelector`, the guidance debug heatmap,
and any guidance type that needs to map group names to body indices.
"""

from __future__ import annotations

# 30 G1 bodies in body_pos_local order
_G1_BODY_NAMES = [
    "pelvis",                    # 0
    "left_hip_pitch_link",       # 1
    "right_hip_pitch_link",      # 2
    "waist_yaw_link",            # 3
    "left_hip_roll_link",        # 4
    "right_hip_roll_link",       # 5
    "waist_roll_link",           # 6
    "left_hip_yaw_link",         # 7
    "right_hip_yaw_link",        # 8
    "torso_link",                # 9
    "left_knee_link",            # 10
    "right_knee_link",           # 11
    "left_shoulder_pitch_link",  # 12
    "right_shoulder_pitch_link", # 13
    "left_ankle_pitch_link",     # 14
    "right_ankle_pitch_link",    # 15
    "left_shoulder_roll_link",   # 16
    "right_shoulder_roll_link",  # 17
    "left_ankle_roll_link",      # 18
    "right_ankle_roll_link",     # 19
    "left_shoulder_yaw_link",    # 20
    "right_shoulder_yaw_link",   # 21
    "left_elbow_link",           # 22
    "right_elbow_link",          # 23
    "left_wrist_roll_link",      # 24
    "right_wrist_roll_link",     # 25
    "left_wrist_pitch_link",     # 26
    "right_wrist_pitch_link",    # 27
    "left_wrist_yaw_link",       # 28
    "right_wrist_yaw_link",      # 29
]

G1_BODY_GROUPS: dict[str, list[int]] = {
    # ── Fine-grained groups ──
    "pelvis":    [0],
    "hip_pitch": [1, 2],
    "waist":     [3, 6, 9],        # waist_yaw, waist_roll, torso_link
    "hip_roll":  [4, 5],
    "hip_yaw":   [7, 8],
    "knee":      [10, 11],
    "shoulder":  [12, 13, 16, 17, 20, 21],
    "elbow":     [22, 23],
    "wrist":     [24, 25, 26, 27, 28, 29],
    "ankle":     [14, 15, 18, 19],
    # ── Aggregate groups (backward-compatible) ──
    "torso":     [0, 3, 4, 5, 6, 7, 8, 9],
    "pelvis_torso": [0, 9],          # pelvis + torso_link only (default vx activation)
    "hip":       [1, 2],
    "leg":       [10, 11],
    "foot":      [14, 15, 18, 19],
    "arm":       [12, 13, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
}

# Global debug flag — set ``True`` to enable body guidance heatmap.
# When enabled the tkinter GUI shows a Canvas-based heatmap of which of the
# 30 G1 bodies are currently guided (green) vs not guided (red).  Falls
# back to a console text summary when tkinter is unavailable.
DEBUG: bool = True

# Short labels for each body index, used in the debug heatmap cells.
# Format: ``<joint>_<side>`` so you can read them without decoding.
_BODY_ABBR: list[str] = [
    "pelvis",  "hp_pch_L","hp_pch_R","wst_yaw", "hp_rol_L","hp_rol_R",
    "wst_rol", "hp_yaw_L","hp_yaw_R","torso",   "knee_L",  "knee_R",
    "sh_pch_L","sh_pch_R","ank_p_L", "ank_p_R", "sh_rol_L","sh_rol_R",
    "ank_r_L", "ank_r_R", "sh_yaw_L","sh_yaw_R","elbow_L", "elbow_R",
    "wr_rol_L","wr_rol_R","wr_pch_L","wr_pch_R","wr_yaw_L","wr_yaw_R",
]
