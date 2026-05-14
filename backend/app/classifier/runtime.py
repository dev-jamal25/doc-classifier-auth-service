"""Runtime controls for classifier inference.

This module is intentionally tiny and has no app-layer dependencies.
It should be called before importing model.py or transforms.py, because
those modules import torch / torchvision.
"""

from __future__ import annotations

import os

_CONFIGURED = False


def _default_thread_count() -> int:
    """Pick a safe default CPU thread count for local inference.

    We avoid using every CPU core because that can make the laptop unstable
    during Docker/demo runs. The value can still be overridden with:
    CLASSIFIER_TORCH_NUM_THREADS=...
    """
    cpu_count = os.cpu_count() or 1
    return max(1, min(4, cpu_count))


def _read_positive_int_env(name: str, default: int) -> int:
    """Read a positive integer env var with a safe fallback."""
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return max(1, value)


def configure_inference_runtime() -> None:
    """Configure PyTorch CPU inference runtime once.

    Defaults:
      - CLASSIFIER_TORCH_NUM_THREADS: min(4, os.cpu_count())
      - CLASSIFIER_TORCH_INTEROP_THREADS: 1
      - CLASSIFIER_ENABLE_MKLDNN: 1

    Env overrides allow benchmarking different CPU settings without code edits.
    """

    global _CONFIGURED

    if _CONFIGURED:
        return

    torch_num_threads = _read_positive_int_env(
        "CLASSIFIER_TORCH_NUM_THREADS",
        _default_thread_count(),
    )
    torch_interop_threads = _read_positive_int_env(
        "CLASSIFIER_TORCH_INTEROP_THREADS",
        1,
    )

    # Best effort: these matter most when set before torch is imported.
    os.environ.setdefault("OMP_NUM_THREADS", str(torch_num_threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(torch_num_threads))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(torch_num_threads))
    os.environ.setdefault("NUMEXPR_NUM_THREADS", str(torch_num_threads))

    import torch

    torch.set_num_threads(torch_num_threads)

    try:
        torch.set_num_interop_threads(torch_interop_threads)
    except RuntimeError:
        # PyTorch only allows this before inter-op parallel work starts.
        # In a fresh worker/CI process this should succeed; this fallback
        # keeps local interactive sessions from crashing.
        pass

    # MKLDNN / oneDNN usually makes ConvNeXt CPU inference much faster.
    # Keep it enabled by default for latency, but allow disabling it if
    # golden replay ever shows unacceptable numeric drift.
    enable_mkldnn = os.getenv("CLASSIFIER_ENABLE_MKLDNN", "1") == "1"

    if hasattr(torch.backends, "mkldnn"):
        torch.backends.mkldnn.enabled = enable_mkldnn

    # Keep operations deterministic where PyTorch supports it.
    torch.use_deterministic_algorithms(True, warn_only=True)

    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    _CONFIGURED = True
