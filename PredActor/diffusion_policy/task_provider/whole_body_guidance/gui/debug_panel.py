"""DebugPanel — per-guidance body intensity heatmap, group sliders, term toggles.

Embedded inside the Activation Manager panel.  Tracks a **selected guidance
index**; ALL controls (heatmap, group sliders, term toggles, click handler,
toolbar actions) operate on that guidance's :class:`GuidanceActivationSet`
only.  Selecting a different guidance row instantly redraws everything.
"""

from __future__ import annotations

try:
    import customtkinter as ctk
    import tkinter as tk
    _CTK_AVAILABLE = True
except ImportError:
    _CTK_AVAILABLE = False

from ..body_groups import G1_BODY_GROUPS, _BODY_ABBR
from ..guidance_activation_manager import GuidanceActivationManager
from ..term_resolver import TermResolver


class DebugPanel:
    """Per-guidance debug heatmap + group sliders + term toggles.

    Call ``set_selected_guidance(idx)`` to switch which guidance's activation
    set drives all controls.  Every mutation touches **only** the selected
    guidance — other guidances are left unchanged.
    """

    def __init__(
        self,
        manager: GuidanceActivationManager,
        term_resolver: TermResolver,
    ):
        self._manager = manager
        self._term_resolver = term_resolver
        self._selected_idx: int | None = None
        self._canvas = None
        self._heatmap_label = None
        self._frame = None
        self._built = False
        self._root_tk = None
        self._group_vars: dict[str, tk.DoubleVar] = {}
        self._term_vars: dict[str, tk.BooleanVar] = {}
        self._debug_override_active = False

    # ── Selected guidance activation shorthand ────────────────────────────

    @property
    def _activation(self):
        """The :class:`GuidanceActivationSet` of the currently selected guidance, or None."""
        if self._selected_idx is None:
            return None
        try:
            return self._manager.guidances[self._selected_idx].activation
        except (IndexError, AttributeError):
            return None

    # ── Selection ────────────────────────────────────────────────────────

    def set_selected_guidance(self, idx: int) -> None:
        """Switch all controls to operate on guidance *idx*."""
        if idx == self._selected_idx:
            return
        self._selected_idx = idx
        self._debug_override_active = False
        activation = self._activation
        if activation is None or not self._built:
            return

        # ── Refresh group sliders from selected guidance ──────────────────
        for g, var in self._group_vars.items():
            val = activation.group_intensities.get(g, 0.0)
            var.set(val)

        # ── Refresh term checkboxes from selected guidance ────────────────
        guided_terms = set(activation.guided_terms)
        disabled = activation.disabled_terms
        for t, var in self._term_vars.items():
            in_g = t in guided_terms
            var.set(in_g and t not in disabled)

        self._draw_heatmap()

    # ── Build ────────────────────────────────────────────────────────────

    def build(self, parent, root_tk):
        """Create all widgets and return the root ``CTkFrame``.

        The entire body is inside a try/except so that a single widget-creation
        failure never takes down the GUI.  On error we return a fallback frame
        with the traceback rendered as a label.
        """
        import traceback as _tb

        if not _CTK_AVAILABLE:
            try:
                return ctk.CTkFrame(parent)
            except Exception:
                # Last resort: return a bare tk Frame so .pack() won't crash.
                return tk.Frame(parent, bg='#2b2b2b')

        try:
            return self._build_impl(parent, root_tk)
        except Exception as _exc:
            err_msg = _tb.format_exc()
            print(f"[DebugPanel] build failed:\n{err_msg}", flush=True)
            # Return a fallback frame so the caller's .pack() doesn't crash.
            try:
                fb = ctk.CTkFrame(parent)
                ctk.CTkLabel(
                    fb, text=f"Heatmap build error:\n{_exc}",
                    font=ctk.CTkFont(size=11, family="Arial"),
                    text_color="#f44",
                ).pack(padx=8, pady=8)
                return fb
            except Exception:
                return tk.Frame(parent, bg='#2b2b2b')

    def _build_impl(self, parent, root_tk):
        """Actual widget construction — extracted so exceptions are caught."""

        cols = 6
        cell_w, cell_h = 176, 28
        gap_x, gap_y = 8, 6
        abbr_gap = 16
        margin_x, margin_y = 16, 12
        rows = 5
        canvas_w = margin_x * 2 + cols * (cell_w + gap_x) - gap_x
        canvas_h = margin_y * 2 + rows * (cell_h + gap_y + abbr_gap) + 38

        self._root_tk = root_tk
        self._heatmap_geom = (cell_w, cell_h, gap_x, gap_y, abbr_gap, margin_x, margin_y)
        self._heatmap_cols = cols

        frame = ctk.CTkFrame(parent)
        self._frame = frame

        # ── Toolbar row ──
        toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        toolbar.pack(fill="x", padx=4, pady=(2, 2))

        ctk.CTkButton(
            toolbar, text="Toggle All", width=70, height=22,
            fg_color="#555", hover_color="#777",
            command=self._toggle_all_groups,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            toolbar, text="Reset Bodies", width=80, height=22,
            fg_color="#555", hover_color="#777",
            command=self._reset_overrides,
        ).pack(side="left", padx=2)

        ctk.CTkLabel(
            toolbar, text="Click cell → toggle override",
            font=ctk.CTkFont(size=11, family="Arial"), text_color="#888",
        ).pack(side="left", padx=6)

        # ── Group intensity sliders ──
        groups = sorted(G1_BODY_GROUPS.keys())
        self._group_vars.clear()
        if groups:
            grp_bar = ctk.CTkFrame(frame, fg_color="transparent")
            grp_bar.pack(fill="x", padx=4, pady=(0, 2))
            ctk.CTkLabel(
                grp_bar, text="Groups:", font=ctk.CTkFont(size=11, family="Arial"),
                text_color="#888",
            ).pack(side="left")

            for g in groups:
                frm = ctk.CTkFrame(grp_bar, fg_color="transparent")
                frm.pack(side="left", padx=2, pady=1)

                var = tk.DoubleVar(master=root_tk, value=0.0)
                self._group_vars[g] = var

                def _on_grp_change(v, _g=g, _var=var):
                    """Write group intensity ONLY to the selected guidance."""
                    activation = self._activation
                    if activation is not None:
                        activation.group_intensities[_g] = _var.get()
                    self._debug_override_active = True
                    self._draw_heatmap()

                ctk.CTkLabel(
                    frm, text=g, font=ctk.CTkFont(size=11, family="Arial"),
                    text_color="#aaa",
                ).pack()

                ctk.CTkSlider(
                    frm, from_=0.0, to=1.0, variable=var,
                    width=60, command=_on_grp_change,
                ).pack(side="left")

                val_lbl = ctk.CTkLabel(
                    frm, text="0.0", font=ctk.CTkFont(size=11, family="Arial"),
                    text_color="#888", width=20,
                )
                val_lbl.pack(side="left")
                var.trace_add('write', lambda *a, _l=val_lbl, _v=var: _l.configure(
                    text=f"{_v.get():.1f}"))

        # ── Term toggle checkboxes ──
        profile_terms = self._term_resolver.terms if self._term_resolver else []

        self._term_vars.clear()
        if profile_terms:
            term_bar = ctk.CTkFrame(frame, fg_color="transparent")
            term_bar.pack(fill="x", padx=4, pady=(0, 2))
            ctk.CTkLabel(
                term_bar, text="Terms:", font=ctk.CTkFont(size=11, family="Arial"),
                text_color="#888",
            ).pack(side="left")

            for t in profile_terms:
                var = tk.BooleanVar(master=root_tk, value=False)
                self._term_vars[t] = var

                def _on_term_toggle(_t=t, _v=var):
                    """Enable/disable term ONLY on the selected guidance."""
                    activation = self._activation
                    if activation is None:
                        return
                    if _v.get():
                        activation.disabled_terms.discard(_t)
                    else:
                        activation.disabled_terms.add(_t)
                    self._draw_heatmap()

                ctk.CTkCheckBox(
                    term_bar, text=t, variable=var,
                    command=_on_term_toggle,
                    font=ctk.CTkFont(size=11, family="Arial"),
                    checkbox_width=14, checkbox_height=14,
                ).pack(side="left", padx=1, pady=1)

        # ── Heatmap canvas ──
        self._canvas = tk.Canvas(
            frame, width=canvas_w, height=canvas_h,
            bg='#2b2b2b', highlightthickness=0,
        )
        self._canvas.pack(fill="x", padx=2, pady=2)

        # ── Stats label ──
        self._heatmap_label = ctk.CTkLabel(
            frame, text="", anchor="w",
            font=ctk.CTkFont(size=11, family="Arial"),
        )
        self._heatmap_label.pack(fill="x", padx=4, pady=(0, 2))

        self._built = True
        # If selection was set before build, replay it now
        if self._selected_idx is not None:
            self.set_selected_guidance(self._selected_idx)
        return frame

    # ═════════════════════════════════════════════════════════════════════
    # Heatmap rendering — reads ONLY the selected guidance
    # ═════════════════════════════════════════════════════════════════════

    def _draw_heatmap(self) -> None:
        canvas = self._canvas
        if canvas is None:
            return
        canvas.delete('all')

        activation = self._activation
        if activation is None:
            if self._heatmap_label:
                self._heatmap_label.configure(text="(select a guidance above)")
            return

        cols = self._heatmap_cols
        cell_w, cell_h, gap_x, gap_y, abbr_gap, margin_x, margin_y = self._heatmap_geom
        bi = activation.build_body_intensity(G1_BODY_GROUPS)

        def _lerp_hex(a_hex, b_hex, t):
            def _h2rgb(h):
                return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))
            ar, ag, a_b = _h2rgb(a_hex)
            br, bg, b_b = _h2rgb(b_hex)
            return f'#{(int(ar + (br - ar) * t)):02x}{(int(ag + (bg - ag) * t)):02x}{(int(a_b + (b_b - a_b) * t)):02x}'

        grey = '#666666'
        green = '#4CAF50'

        for i in range(30):
            row = i // cols
            col = i % cols
            x = margin_x + col * (cell_w + gap_x)
            y = margin_y + row * (cell_h + gap_y + abbr_gap)

            w = bi[i]
            fill = _lerp_hex(grey, green, w)
            text_fg = '#333' if w < 0.5 else '#E8F5E9'

            tag = f'cell_{i}'
            has_override = i in activation.body_intensity_overrides
            outline = '#FF9800' if has_override else '#555'
            outline_w = 2 if has_override else 1

            canvas.create_rectangle(
                x, y, x + cell_w, y + cell_h,
                fill=fill, outline=outline, width=outline_w, tags=tag)

            star = '*' if has_override else ' '
            label = f"{star}{i:2d} {_BODY_ABBR[i]}"
            canvas.create_text(x + cell_w / 2, y + cell_h / 2,
                               text=label, font=('TkDefaultFont', 7, 'bold'),
                               fill=text_fg, tags=tag)

            ovr_tag = ' [ovr]' if has_override else ''
            canvas.create_text(x + cell_w / 2, y + cell_h + 4,
                               text=f"w={w:.1f}{ovr_tag}", font=('TkDefaultFont', 6),
                               fill='#aaa', anchor='n', tags=tag)

            canvas.tag_bind(tag, '<Button-1>',
                            lambda _e, idx=i: self._on_heatmap_click(idx))

        # ── Legend ──
        ly = margin_y + 5 * (cell_h + gap_y + abbr_gap) + 6
        for j, t in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
            bx = margin_x + j * 22
            c = _lerp_hex(grey, green, t)
            canvas.create_rectangle(bx, ly, bx + 20, ly + 12, fill=c, outline='')
        canvas.create_text(margin_x + 115, ly + 6,
                           text='Grey=off → Green=full', anchor='w',
                           font=('TkDefaultFont', 7), fill='#aaa')

        n_active = sum(1 for w in bi if w > 0.0)
        canvas.create_text(margin_x + 280, ly + 6,
                           text=f"Active: {n_active}/30",
                           anchor='w', font=('TkDefaultFont', 8, 'bold'), fill='#ccc')

        # ── Stats label ──
        group_parts = []
        for g in sorted(activation.group_intensities.keys()):
            wi = activation.group_intensities[g]
            group_parts.append(f"{g}={wi:.1f}")
        group_str = ', '.join(group_parts)
        disabled = activation.disabled_terms
        term_parts = []
        for t in activation.guided_terms:
            if t in disabled:
                term_parts.append(f"~~{t}~~")
            else:
                term_parts.append(t)
        term_str = ', '.join(term_parts)
        ovr = " [OVERRIDE]" if self._debug_override_active else ""
        nm = self._manager.guidances[self._selected_idx].guidance_name
        self._heatmap_label.configure(
            text=f"[{nm}]  Intensity:{ovr} {group_str}  |  Terms: {term_str}")

    # ═════════════════════════════════════════════════════════════════════
    # Click handler — modifies ONLY the selected guidance
    # ═════════════════════════════════════════════════════════════════════

    def _on_heatmap_click(self, body_idx: int) -> None:
        activation = self._activation
        if activation is None:
            return
        self._debug_override_active = True

        # Compute what groups give this body
        group_val = 0.0
        for gname, indices in G1_BODY_GROUPS.items():
            if body_idx in indices:
                w = activation.group_intensities.get(gname, 0.0)
                if w > group_val:
                    group_val = w

        current = activation.body_intensity_overrides.get(body_idx, group_val)
        new_val = 0.0 if current > 0.0 else 1.0

        if abs(new_val - group_val) < 0.001:
            activation.body_intensity_overrides.pop(body_idx, None)
        else:
            activation.body_intensity_overrides[body_idx] = new_val

        self._draw_heatmap()

    # ═════════════════════════════════════════════════════════════════════
    # Toolbar actions — modify ONLY the selected guidance
    # ═════════════════════════════════════════════════════════════════════

    def _toggle_all_groups(self) -> None:
        activation = self._activation
        if activation is None:
            return
        any_active = any(w > 0.0 for w in activation.group_intensities.values())
        new_val = 0.0 if any_active else 1.0
        for g in activation.group_intensities:
            activation.group_intensities[g] = new_val
            if g in self._group_vars:
                self._group_vars[g].set(new_val)
        self._debug_override_active = True
        self._draw_heatmap()

    def _reset_overrides(self) -> None:
        activation = self._activation
        if activation is None:
            return
        # Restore group intensities from config defaults
        for g in G1_BODY_GROUPS:
            is_guided = g in activation.guided_body_groups
            activation.group_intensities[g] = 1.0 if is_guided else 0.0
            if g in self._group_vars:
                self._group_vars[g].set(activation.group_intensities[g])
        activation.reset_overrides()
        self._debug_override_active = False

        # Reset term checkboxes for this guidance
        guided_terms = set(activation.guided_terms)
        for t, v in self._term_vars.items():
            v.set(t in guided_terms)

        self._draw_heatmap()

    # ── Public API ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Redraw the heatmap (called from GUI tick loop)."""
        if self._built and self._selected_idx is not None:
            self._draw_heatmap()
