"""CLIP semantic interpolation for conditional motion control.

A tkinter GUI presents one slider per text pair.  The final conditioning
embedding is the weighted sum of difference vectors ``(emb2 - emb1) * w``.
Optional unit-norm normalisation is applied after the sum.
"""

import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Any, List, Optional, Tuple

import clip
import torch

from diffusion_policy.task_provider.base import TaskCondProvider
from diffusion_policy.task_provider.clip_proposition import (
    describe_interpolation_terms,
    encode_and_compose,
    interpolation_weight_bounds,
    matched_weight_defaults,
    terms_from_pairs,
    validate_interpolation_terms,
)


class CLIPInterp(TaskCondProvider):
    """GUI slider-based semantic interpolation between CLIP text embeddings.

    Each slider controls how much of a *difference direction* is added to the
    base embedding.  For a pair ``(text1, text2)`` with weight ``w``:

        contribution = (encode(text2) - encode(text1)) * w

    ``None`` entries are treated as zero vectors.

    Args:
        text_pairs: List of ``(text_a, text_b)`` pairs.  ``None`` = zero vec.
        device: PyTorch device for the CLIP model.
        cond_dim: Conditioning dimension (512 for ViT-B/32).
        clip_model_name: CLIP variant to load.
        clip_training: ``''`` = frozen, ``'text'`` = fine-tune text encoder.
        clip_layers: Number of transformer layers.
        checkpoint_path: Optional MotionCLIP checkpoint for CLIP weights.
        normalize: Normalise the summed embedding to unit norm.
        scale: GUI scale factor for hi-res screens (fonts, window size, padding).
    """

    def __init__(
        self,
        text_pairs: List[Tuple[Optional[str], Optional[str]]],
        device: str = "cuda:0",
        cond_dim: int = 512,
        clip_model_name: str = "ViT-B/32",
        clip_training: str = "",
        clip_layers: int = 12,
        checkpoint_path: Optional[str] = None,
        normalize: bool = True,
        scale: float = 2.0,
        gui_enabled: bool = True,
    ):
        self.device = device
        self.cond_dim = cond_dim
        self.text_pairs = list(text_pairs)
        self.normalize = normalize
        self.scale = float(scale)
        self.gui_enabled = bool(gui_enabled)

        print(f"Loading CLIP model: {clip_model_name} on {device}")
        self.clip_model, _ = clip.load(clip_model_name, device=device, jit=False)
        clip.model.convert_weights(self.clip_model)

        for domain in clip_training.split("_"):
            if domain == "text":
                self.clip_model.initialize_parameters()
                self.clip_model.transformer.resblocks = self.clip_model.transformer.resblocks[:clip_layers]
            if domain == "image":
                self.clip_model.initialize_parameters()
                self.clip_model.visual.transformer = self.clip_model.transformer.resblocks[:clip_layers]

        if checkpoint_path is not None:
            self._load_clip_from_checkpoint(checkpoint_path)

        if clip_training == "":
            self.clip_model.eval()
            for p in self.clip_model.parameters():
                p.requires_grad = False

        self._embedding_lock = threading.RLock()
        self._update_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._embedding_cache: dict[str, torch.Tensor] = {}
        self.pair_embeddings: List[Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]] = []
        self._current_embedding: Optional[torch.Tensor] = None
        self._interp_weights: List[float] = []
        self._interpolation_default_terms: list[dict[str, Any]] = []

        self._gui_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._root: Optional[tk.Tk] = None

        self.set_interpolation_terms(terms_from_pairs(self.text_pairs))

        print(f"CLIPInterp ready — {len(text_pairs)} text pairs:")
        for i, (t1, t2) in enumerate(text_pairs):
            print(f"  [{i}] '{t1 or 'ZERO'}' ↔ '{t2 or 'ZERO'}'")

    # ------------------------------------------------------------------
    # TaskCondProvider interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the GUI in a background daemon thread."""
        if not self.gui_enabled:
            return
        if self._gui_thread is not None and self._gui_thread.is_alive():
            print("[CLIPInterp] GUI already running")
            return
        self._stop_event.clear()
        self._gui_thread = threading.Thread(target=self._gui_worker, daemon=True)
        self._gui_thread.start()
        print("[CLIPInterp] GUI thread started")

    def stop(self) -> None:
        """Close the GUI and stop the background thread."""
        if self._gui_thread is None:
            return
        print("\n[CLIPInterp] Stopping GUI…")
        self._stop_event.set()
        if self._root is not None:
            try:
                self._root.quit()
            except Exception:
                pass
        self._gui_thread.join(timeout=2.0)
        if self._gui_thread.is_alive():
            print("[CLIPInterp] Warning: GUI thread did not stop cleanly")
        else:
            print("[CLIPInterp] GUI stopped")

    def inject_raw_keys(self, next_terms: dict, batch_size: int) -> None:
        """Write ``motion_latent`` (shape ``[B, 1, D]``) into *next_terms*."""
        emb = self.get_embedding(batch_size=batch_size, n_cond_steps=1)
        if next_terms:
            emb = emb.to(next(iter(next_terms.values())).device)
        next_terms["motion_latent"] = emb

    def get_task_cond(self, raw_history, batch_size, n_task_steps, device=None):
        """Legacy path: return ``[B, n_task_steps, cond_dim]`` directly."""
        emb = self.get_embedding(batch_size=batch_size, n_cond_steps=n_task_steps)
        if device is not None:
            emb = emb.to(device)
        return emb

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def get_embedding(self, batch_size: int = 1, n_cond_steps: int = 1) -> torch.Tensor:
        """Return ``[batch_size, n_cond_steps, cond_dim]`` on the model's device."""
        with self._embedding_lock:
            if self._current_embedding is None:
                return torch.zeros(batch_size, n_cond_steps, self.cond_dim, device=self.device)
            emb = self._current_embedding.unsqueeze(1)  # [1, 1, D]
            return emb.expand(batch_size, n_cond_steps, -1)

    def set_weights(self, weights: List[float]) -> None:
        """Programmatically set interpolation weights (one per pair)."""
        with self._embedding_lock:
            pairs = list(self.text_pairs)
        self.set_interpolation_terms(terms_from_pairs(pairs, weights))

    def set_interpolation(self, text_a: str, text_b: str, weight: float) -> None:
        """Legacy one-axis adapter using the proposition direction contract."""
        self.set_interpolation_terms([{
            "text_a": text_a,
            "text_b": text_b,
            "weight": max(0.0, min(1.0, float(weight))),
        }])

    def set_interpolation_terms(self, terms: list[dict[str, Any]]) -> dict[str, Any]:
        """Atomically replace all proposition terms after complete encoding."""
        clean = validate_interpolation_terms(terms)
        with self._update_lock:
            pairs, final = encode_and_compose(
                clean,
                self._cached_encode_text,
                cond_dim=self.cond_dim,
                device=self.device,
                normalize=self.normalize,
            )
            with self._embedding_lock:
                if not self._interpolation_default_terms:
                    default_pairs = [(term["text_a"], term["text_b"]) for term in clean]
                    self._interpolation_default_terms = terms_from_pairs(default_pairs)
                self.text_pairs = [(term["text_a"], term["text_b"]) for term in clean]
                self._interp_weights = [term["weight"] for term in clean]
                self.pair_embeddings = pairs
                self._current_embedding = final
        return self.get_interpolation_snapshot()

    def get_interpolation_snapshot(self) -> dict[str, Any]:
        """Return the provider-accepted proposition state for Web UI hydration."""
        with self._embedding_lock:
            terms = [{"text_a": pair[0], "text_b": pair[1], "weight": weight}
                     for pair, weight in zip(self.text_pairs, self._interp_weights)]
            weight_defaults = matched_weight_defaults(terms, self._interpolation_default_terms)
            return {
                "available": True,
                "normalize": self.normalize,
                "terms": describe_interpolation_terms(terms, weight_defaults=weight_defaults),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _encode_text(self, text: str) -> torch.Tensor:
        tokens = clip.tokenize([text]).to(self.device)
        emb = self.clip_model.encode_text(tokens).float()
        return emb / emb.norm(dim=-1, keepdim=True)

    def _cached_encode_text(self, text: str) -> torch.Tensor:
        with self._cache_lock:
            embedding = self._embedding_cache.get(text)
            if embedding is None:
                embedding = self._encode_text(text)
                self._embedding_cache[text] = embedding
            return embedding

    def _update_embedding(self) -> None:
        with self._embedding_lock:
            terms = [{"text_a": pair[0], "text_b": pair[1], "weight": weight}
                     for pair, weight in zip(self.text_pairs, self._interp_weights)]
        self.set_interpolation_terms(terms)

    def _load_clip_from_checkpoint(self, checkpoint_path: str) -> None:
        print(f"[CLIPInterp] Loading CLIP weights from: {checkpoint_path}")
        try:
            state_dict = torch.load(checkpoint_path, map_location=self.device)
            model_state = state_dict.get("model", state_dict)
            clip_state = {
                k.replace("clip_model.", ""): v
                for k, v in model_state.items()
                if k.startswith("clip_model.")
            }
            if not clip_state:
                print("[CLIPInterp] Warning: no CLIP keys in checkpoint — using defaults")
                return
            missing, unexpected = self.clip_model.load_state_dict(clip_state, strict=False)
            if missing:
                print(f"[CLIPInterp] Missing keys: {len(missing)}")
            if unexpected:
                print(f"[CLIPInterp] Unexpected keys: {len(unexpected)}")
            print("[CLIPInterp] Checkpoint CLIP weights loaded")
        except Exception as exc:
            print(f"[CLIPInterp] Checkpoint load error: {exc} — using defaults")

    def _on_slider_change(self, pair_idx: int, value: float) -> None:
        with self._embedding_lock:
            weights = list(self._interp_weights)
            lower, upper = interpolation_weight_bounds(*self.text_pairs[pair_idx])
        weights[pair_idx] = max(lower, min(upper, value))
        self.set_weights(weights)

    def _on_normalize_toggle(self) -> None:
        self.normalize = self._normalize_var.get()
        self._update_embedding()
        print(f"[CLIPInterp] Normalisation: {'ON' if self.normalize else 'OFF'}")

    def _gui_worker(self) -> None:
        s = self.scale

        self._root = tk.Tk()
        self._root.title("CLIP Semantic Interpolation")
        self._root.geometry(f"{int(600 * s)}x{int(400 * s)}")

        # Scale pixel-per-point so point-based dimensions (and point-sized
        # fonts) multiply by `s`.  Pixel-sized fonts are NOT affected by
        # `tk scaling`, so the style font below is re-pointed to a scaled
        # pixel size when the platform default font is pixel-based, or kept at
        # its point size when point-based (tk scaling then renders it ×s).
        self._root.tk.call("tk", "scaling", s)

        # Scale the default font for all ttk widgets (elements + font grow
        # together; `tk scaling` alone does not scale pixel-sized fonts).
        style = ttk.Style()
        default_font = tkfont.nametofont("TkDefaultFont")
        _size = default_font.cget("size")
        if isinstance(_size, int) and _size < 0:
            # Negative size = pixels → scale the pixel size manually.
            style.configure(".", font=(default_font.cget("family"), int(_size * s)))
        else:
            # Positive size = points → tk scaling renders it at size*s px.
            style.configure(".", font=(default_font.cget("family"), _size))

        main_frame = ttk.Frame(self._root, padding=str(int(10 * s)))
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Point-based font tuple; `tk scaling` scales it to size*s px.
        title_font = ("Arial", 14, "bold")
        ttk.Label(main_frame, text="CLIP Semantic Interpolation",
                  font=title_font).grid(row=0, column=0, columnspan=3, pady=int(10 * s))

        self._normalize_var = tk.BooleanVar(value=self.normalize)
        ttk.Checkbutton(
            main_frame,
            text="Normalise final embedding to unit norm",
            variable=self._normalize_var,
            command=self._on_normalize_toggle,
        ).grid(row=1, column=0, columnspan=3, pady=int(5 * s))

        ttk.Separator(main_frame, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=int(10 * s)
        )

        self._sliders: List[tk.DoubleVar] = []
        for i, (t1, t2) in enumerate(self.text_pairs):
            lower, upper = interpolation_weight_bounds(t1, t2)
            control_name = "Direction" if lower < 0 else "Weight"
            row_base = 3 + i * 3
            lbl_text = f"Pair {i}: '{t1 or 'ZERO'}' ↔ '{t2 or 'ZERO'}'"
            ttk.Label(main_frame, text=lbl_text).grid(
                row=row_base, column=0, columnspan=2, sticky=tk.W,
                pady=(int(10 * s), int(2 * s)),
            )
            weight_lbl = ttk.Label(main_frame, text=f"{control_name}: {self._interp_weights[i]:.2f}")
            weight_lbl.grid(row=row_base, column=2, sticky=tk.E, padx=int(5 * s))

            var = tk.DoubleVar(value=self._interp_weights[i])
            ttk.Scale(
                main_frame,
                from_=lower,
                to=upper,
                orient=tk.HORIZONTAL,
                variable=var,
                command=lambda v, idx=i: self._on_slider_change(idx, float(v)),
            ).grid(row=row_base + 1, column=0, columnspan=3, sticky=(tk.W, tk.E),
                   pady=(int(2 * s), int(5 * s)))
            var.trace_add("write", lambda *_, idx=i, lbl=weight_lbl, name=control_name:
                          lbl.config(text=f"{name}: {self._interp_weights[idx]:.2f}"))
            self._sliders.append(var)

        main_frame.columnconfigure(0, weight=1)
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        print(f"[CLIPInterp] GUI started  (scale={s:.1f})")
        try:
            while not self._stop_event.is_set():
                self._root.update()
                self._root.update_idletasks()
        except tk.TclError:
            pass
        except Exception as exc:
            print(f"[CLIPInterp] GUI error: {exc}")
        try:
            self._root.destroy()
        except Exception:
            pass
        print("[CLIPInterp] GUI exiting")

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
