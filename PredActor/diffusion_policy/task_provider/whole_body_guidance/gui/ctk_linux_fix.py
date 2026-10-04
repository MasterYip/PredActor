"""Monkey-patch CustomTkinter with Linux rendering fixes from PR #2646.

This applies the unmerged upstream patch:
  https://github.com/TomSchimansky/CustomTkinter/pull/2646

Import this module once before any CTk widgets are created.  Patches are
idempotent and only activate on Linux.

Fixes applied
-------------
*draw_engine.py*
  - ``__init__`` → default to ``circle_shapes`` drawing method (antialiases
    correctly on X11/Wayland; ``polygon_shapes`` renders jagged on many
    Linux configurations).
  - ``__calc_optimal_corner_radius`` → finer 0.25-step rounding on Linux
    (vs upstream 0.5) for ``circle_shapes``; ``round(r*1.25)/1.25`` for
    ``polygon_shapes`` to compensate for coordinate snapping.
  - ``__draw_rounded_rect_with_border_circle_shapes`` → tweak
    ``corner_radius`` and ``border_width`` by −0.5 / −0.2 px to prevent
    1px border bleed-through on Linux.

*font_manager.py*
  - ``linux_font_paths`` → list with ``~/.local/share/fonts/`` fallback.
  - ``load_font`` → avoid redundant copies + call ``fc-cache`` on copy.
  - ``refresh_font_cache`` → new ``fc-cache -fv`` helper.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

# ── Sentinel ────────────────────────────────────────────────────────────────
_PATCHED = False


def _apply() -> None:
    """Apply PR #2646 fixes to the running CustomTkinter installation."""
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    if not sys.platform.startswith("linux"):
        return

    try:
        import customtkinter.windows.widgets.core_rendering.draw_engine as _de_mod
        import customtkinter.windows.widgets.font.font_manager as _fm_mod
    except ImportError as exc:
        print(f"[ctk_linux_fix] customtkinter not importable — skipping ({exc})", flush=True)
        return

    # ── DrawEngine ──────────────────────────────────────────────────────
    _patch_draw_engine(_de_mod.DrawEngine)

    # ── FontManager ─────────────────────────────────────────────────────
    _patch_font_manager(_fm_mod.FontManager)

    print("[ctk_linux_fix] PR #2646 Linux rendering patches applied", flush=True)


# ═════════════════════════════════════════════════════════════════════════════
# DrawEngine
# ═════════════════════════════════════════════════════════════════════════════

def _patch_draw_engine(DrawEngine) -> None:
    # --- __init__: default to circle_shapes on Linux ------------------------
    _orig_de_init = DrawEngine.__init__

    def _patched_init(self, canvas):
        _orig_de_init(self, canvas)
        if sys.platform.startswith("linux"):
            self.preferred_drawing_method = "circle_shapes"

    DrawEngine.__init__ = _patched_init

    # --- __calc_optimal_corner_radius: full replacement ---------------------
    DrawEngine._DrawEngine__calc_optimal_corner_radius = _calc_optimal_corner_radius

    # --- __draw_rounded_rect_with_border_circle_shapes: wrap -----------------
    _orig_circle = DrawEngine._DrawEngine__draw_rounded_rect_with_border_circle_shapes

    def _patched_circle(self, width, height, corner_radius, border_width, inner_corner_radius):
        if sys.platform.startswith("linux"):
            corner_radius = max(corner_radius - 0.5, 0)
            border_width = max(border_width - 0.2, 0)
        return _orig_circle(self, width, height, corner_radius, border_width, inner_corner_radius)

    DrawEngine._DrawEngine__draw_rounded_rect_with_border_circle_shapes = _patched_circle


def _calc_optimal_corner_radius(self, user_corner_radius):
    """Optimize corner radius based on the preferred drawing method and platform."""
    # Optimize for polygon shapes
    if self.preferred_drawing_method == "polygon_shapes":
        if sys.platform == "darwin":
            return user_corner_radius
        elif sys.platform.startswith("linux"):
            return round(user_corner_radius * 1.25) / 1.25
        else:
            return round(user_corner_radius)

    # Optimize for antialiased font shapes
    elif self.preferred_drawing_method == "font_shapes":
        return round(user_corner_radius)

    # Optimize for circles and rects
    elif self.preferred_drawing_method == "circle_shapes":
        if sys.platform.startswith("linux"):
            user_corner_radius = 0.25 * round(user_corner_radius / 0.25)
        else:
            user_corner_radius = 0.5 * round(user_corner_radius / 0.5)

        if user_corner_radius == 0:
            return 0
        elif user_corner_radius % 1 == 0:
            return user_corner_radius + 0.5
        else:
            return user_corner_radius


# ═════════════════════════════════════════════════════════════════════════════
# FontManager
# ═════════════════════════════════════════════════════════════════════════════

def _patch_font_manager(FontManager) -> None:
    # Replace class attribute (original is "~/.fonts/" string)
    FontManager.linux_font_paths = [
        os.path.expanduser("~/.fonts/"),
        os.path.expanduser("~/.local/share/fonts/"),
    ]

    FontManager.init_font_manager = classmethod(_init_font_manager)
    FontManager.load_font = classmethod(_load_font)
    FontManager.refresh_font_cache = staticmethod(_refresh_font_cache)


def _init_font_manager(cls):
    """Initialize font manager by ensuring the required font directories exist."""
    if sys.platform.startswith("linux"):
        try:
            for path in cls.linux_font_paths:
                if not os.path.isdir(path):
                    os.makedirs(path, exist_ok=True)
            return True
        except Exception as err:
            sys.stderr.write(f"FontManager error (init): {err}\n")
            return False
    return True


def _load_font(cls, font_path: str) -> bool:
    """Load a font into the system for different platforms."""
    if not os.path.isfile(font_path):
        sys.stderr.write(f"FontManager error: Font file '{font_path}' does not exist.\n")
        return False

    if sys.platform.startswith("win"):
        return cls.windows_load_font(font_path, private=True, enumerable=False)

    elif sys.platform.startswith("linux"):
        for path in cls.linux_font_paths:
            try:
                dest = os.path.join(path, os.path.basename(font_path))
                if not os.path.isfile(dest):
                    shutil.copy(font_path, dest)
                    cls.refresh_font_cache(path)
                return True
            except Exception as err:
                sys.stderr.write(f"FontManager error (Linux): {err}\n")
        return False

    else:
        sys.stderr.write("FontManager warning: Font loading is not supported on this platform.\n")
        return False


def _refresh_font_cache(directory: str) -> None:
    """Refresh the font cache on Linux using fc-cache."""
    try:
        subprocess.run(
            ["fc-cache", "-fv", directory],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except Exception as err:
        sys.stderr.write(f"FontManager error (fc-cache): {err}\n")


# ── Apply on import ─────────────────────────────────────────────────────────
_apply()
