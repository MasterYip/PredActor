"""Interactive CLIP text teleoperator for conditional motion control.

Runs a background stdin-reader thread that accepts free-form text commands
and updates the conditioning embedding in real time.
"""

import queue
import threading
import time
from typing import Any, Callable, Iterable, Optional

import clip
import torch

from diffusion_policy.task_provider.base import TaskCondProvider
from diffusion_policy.task_provider.clip_proposition import (
    describe_interpolation_terms,
    encode_and_compose,
    matched_weight_defaults,
    terms_from_pairs,
    validate_interpolation_terms,
)


class CLIPTeleop(TaskCondProvider):
    """Interactive text-to-motion embedding provider using CLIP.

    The user types text commands in the terminal while evaluation is running.
    Each command is encoded into a CLIP embedding which is then supplied as
    the ``motion_latent`` task conditioning key every policy step.

    Args:
        device: PyTorch device string for the CLIP model.
        cond_dim: Conditioning dimension (must match policy; 512 for ViT-B/32).
        default_text: Initial text prompt used before the first user input.
        clip_model_name: CLIP variant to load when ``checkpoint_path`` is not
            provided (e.g. ``"ViT-B/32"``).
        clip_training: ``''`` = frozen, ``'text'`` = train text encoder.
        clip_layers: Number of transformer layers to use.
        checkpoint_path: Optional path to a MotionCLIP checkpoint containing
            the complete ``clip_model.*`` state. When provided, the model is
            constructed directly from these weights.
    """

    def __init__(
        self,
        device: str = "cuda:0",
        cond_dim: int = 512,
        default_text: str = "walking forward",
        clip_model_name: str = "ViT-B/32",
        clip_training: str = "",
        clip_layers: int = 12,
        checkpoint_path: Optional[str] = None,
        precache_texts: Optional[Iterable[str]] = None,
        on_embedding_update: Optional[Callable] = None,
        interactive_input: bool = True,
    ):
        self.device = device
        self.cond_dim = cond_dim
        self.default_text = default_text
        self._on_embedding_update = on_embedding_update
        self.interactive_input = bool(interactive_input)

        if checkpoint_path is not None:
            self.clip_model = self._load_clip_from_checkpoint(checkpoint_path)
        else:
            print(f"Loading CLIP model: {clip_model_name} on {device}")
            self.clip_model, _ = clip.load(clip_model_name, device=device, jit=False)
            clip.model.convert_weights(self.clip_model)

        for domain in clip_training.split("_"):
            if domain == "text":
                if checkpoint_path is None:
                    self.clip_model.initialize_parameters()
                self.clip_model.transformer.resblocks = self.clip_model.transformer.resblocks[:clip_layers]
            if domain == "image":
                if checkpoint_path is None:
                    self.clip_model.initialize_parameters()
                self.clip_model.visual.transformer = self.clip_model.transformer.resblocks[:clip_layers]

        if clip_training == "":
            self.clip_model.eval()
            for p in self.clip_model.parameters():
                p.requires_grad = False

        self._embedding_lock = threading.RLock()
        self._update_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._current_embedding: Optional[torch.Tensor] = None
        self._current_text: Optional[str] = None
        self._embedding_cache = {}
        self._interpolation_terms: list[dict[str, Any]] = []
        self._interpolation_default_terms: list[dict[str, Any]] = []

        self._input_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._text_queue: queue.Queue = queue.Queue()

        self._update_embedding(default_text)
        for text in precache_texts or ():
            if text:
                self._cached_encode_embedding(text)
        print(f"CLIPTeleop ready — default text: '{default_text}'")

    # ------------------------------------------------------------------
    # TaskCondProvider interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background stdin-reader thread."""
        if not self.interactive_input:
            return
        if self._input_thread is not None and self._input_thread.is_alive():
            print("[CLIPTeleop] Input thread already running")
            return
        self._stop_event.clear()
        self._input_thread = threading.Thread(target=self._input_worker, daemon=True)
        self._input_thread.start()
        print("[CLIPTeleop] Input thread started")

    def stop(self) -> None:
        """Stop the stdin-reader thread."""
        if self._input_thread is None:
            return
        print("\n[CLIPTeleop] Stopping input thread…")
        self._stop_event.set()
        self._input_thread.join(timeout=2.0)
        if self._input_thread.is_alive():
            print("[CLIPTeleop] Warning: input thread did not stop cleanly")
        else:
            print("[CLIPTeleop] Input thread stopped")

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

    def set_text(self, text: str) -> None:
        """Programmatically update the text prompt (useful in scripted eval)."""
        self._update_embedding(text)

    def set_interpolation(self, text_a: str, text_b: str, weight: float) -> None:
        """Set a semantic interpolation without creating a second CLIP model."""
        weight = max(0.0, min(1.0, float(weight)))
        with self._update_lock:
            embeddings = [self._cached_encode_embedding(text) for text in (text_a, text_b)]
            mixed = (1.0 - weight) * embeddings[0] + weight * embeddings[1]
            mixed = mixed / mixed.norm(dim=-1, keepdim=True).clamp_min(1e-8)
            with self._embedding_lock:
                self._current_embedding = mixed
                self._current_text = f"{text_a} -> {text_b} ({weight:.2f})"

    def set_interpolation_terms(self, terms: list[dict[str, Any]]) -> dict[str, Any]:
        """Publish one normalized additive proposition vector atomically."""
        clean = validate_interpolation_terms(terms)
        with self._update_lock:
            _, final = encode_and_compose(
                clean,
                self._cached_encode_embedding,
                cond_dim=self.cond_dim,
                device=self.device,
                normalize=True,
            )
            with self._embedding_lock:
                if not self._interpolation_default_terms:
                    default_pairs = [(term["text_a"], term["text_b"]) for term in clean]
                    self._interpolation_default_terms = terms_from_pairs(default_pairs)
                self._current_embedding = final
                self._interpolation_terms = clean
                self._current_text = self._interpolation_label(clean)
        return self.get_interpolation_snapshot()

    def get_interpolation_snapshot(self) -> dict[str, Any]:
        """Return the provider-accepted proposition terms for the Web UI."""
        with self._embedding_lock:
            weight_defaults = matched_weight_defaults(
                self._interpolation_terms, self._interpolation_default_terms)
            return {
                "available": bool(self._interpolation_terms),
                "normalize": True,
                "terms": describe_interpolation_terms(
                    self._interpolation_terms, weight_defaults=weight_defaults),
            }

    def get_current_text(self) -> Optional[str]:
        """Return the text command that produced the current embedding."""
        with self._embedding_lock:
            return self._current_text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _encode_embedding(self, text: str) -> torch.Tensor:
        with torch.no_grad():
            tokens = clip.tokenize([text]).to(self.device)
            emb = self.clip_model.encode_text(tokens).float()  # [1, D]
            emb = emb / emb.norm(dim=-1, keepdim=True)
        return emb

    def _cached_encode_embedding(self, text: str) -> torch.Tensor:
        with self._cache_lock:
            embedding = self._embedding_cache.get(text)
            if embedding is None:
                embedding = self._encode_embedding(text)
                self._embedding_cache[text] = embedding
            return embedding

    @staticmethod
    def _interpolation_label(terms: list[dict[str, Any]]) -> str:
        active = [term for term in terms if term["weight"] != 0]
        if len(active) == 1:
            term = active[0]
            return f"{term['text_a'] or 'ZERO'} -> {term['text_b'] or 'ZERO'} ({term['weight']:.2f})"
        return f"{len(active)} active semantic terms"

    def _update_embedding(self, text: str, input_done_ns: Optional[int] = None) -> None:
        start_ns = time.monotonic_ns()
        with self._update_lock:
            with self._cache_lock:
                cache_hit = text in self._embedding_cache
            emb = self._cached_encode_embedding(text)
            encode_done_ns = time.monotonic_ns()
            with self._embedding_lock:
                self._current_embedding = emb
                self._current_text = text
        if self._on_embedding_update is not None:
            self._on_embedding_update(text, emb, {
                "cache_hit": cache_hit,
                "input_done_ns": input_done_ns or start_ns,
                "encode_done_ns": encode_done_ns,
            })
        print(f"[CLIPTeleop] Embedding updated: '{text}'")

    def _load_clip_from_checkpoint(self, checkpoint_path: str) -> torch.nn.Module:
        print(f"[CLIPTeleop] Building CLIP model from: {checkpoint_path}")
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model_state = state_dict.get("model", state_dict)
        clip_state = {
            k.removeprefix("clip_model."): v
            for k, v in model_state.items()
            if k.startswith("clip_model.")
        }
        if not clip_state:
            raise ValueError(
                f"MotionCLIP checkpoint contains no clip_model.* weights: {checkpoint_path}")

        model = clip.model.build_model(clip_state)
        if torch.device(self.device).type == "cpu":
            model.float()
            model.load_state_dict(clip_state)
        model.to(self.device)
        print("[CLIPTeleop] CLIP model built from checkpoint")
        return model

    def _input_worker(self) -> None:
        print("\n" + "=" * 70)
        print("CLIP TELEOP — Interactive Text Input")
        print("=" * 70)
        print("Type text commands to control robot motion (e.g. 'run', 'walk').")
        print("Press Enter to keep the current command.  Ctrl+C to stop eval.")
        print("=" * 70 + "\n")

        while not self._stop_event.is_set():
            try:
                print(f"\nCurrent: '{self._current_text}'")
                print("New command (Enter = keep): ", end="", flush=True)
                text = input().strip()
                input_done_ns = time.monotonic_ns()
                if self._stop_event.is_set():
                    break
                if text:
                    self._update_embedding(text, input_done_ns=input_done_ns)
                else:
                    print(f"[CLIPTeleop] Keeping: '{self._current_text}'")
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n[CLIPTeleop] Keyboard interrupt — stopping")
                break
            except Exception as exc:
                print(f"[CLIPTeleop] Input error: {exc}")
                break

        print("[CLIPTeleop] Input thread exiting")

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
