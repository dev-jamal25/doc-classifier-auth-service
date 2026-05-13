"""Runtime controls for deterministic classifier inference.

This module is intentionally tiny and has no app-layer dependencies.
It should be called before importing model.py or transforms.py, because
those modules import torch / torchvision.
"""

from __future__ import annotations

import os

_CONFIGURED = False


def configure_inference_runtime() -> None:
    """Configure PyTorch CPU inference for reproducible golden replay."""

    global _CONFIGURED

    if _CONFIGURED:
        return

    # Best effort: these matter most when set before torch is imported.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

    import torch

    torch.set_num_threads(1)

    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # PyTorch only allows this before inter-op parallel work starts.
        # In a fresh worker/CI process this should succeed; this fallback
        # keeps local interactive sessions from crashing.
        pass

    # Avoid tiny CPU-kernel differences from MKLDNN / oneDNN.
    if hasattr(torch.backends, "mkldnn"):
        torch.backends.mkldnn.enabled = False

    # Keep operations deterministic where PyTorch supports it.
    torch.use_deterministic_algorithms(True, warn_only=True)

    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    _CONFIGURED = True