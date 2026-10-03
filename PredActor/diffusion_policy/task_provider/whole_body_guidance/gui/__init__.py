"""GUI layer for WholeBodyGuidance v2 — CustomTkinter panels."""

# ── Single source of truth for UI scale ─────────────────────────────────────
# All widgets, fonts, and window geometry derive from this value.
# Increase for HiDPI (1.25, 1.5, 2.0), decrease for low-res (1.0).
# 2.0 = ×2 HiDPI UI (DEPLOY-WORKFLOW-GUI-017).
SCALE: float = 1.0
# Min font size — nothing goes below this (px before scaling)
MIN_FONT: int = 11
