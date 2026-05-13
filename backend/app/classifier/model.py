# build/load/validate model + SHA check
"""Artifact validation and ConvNeXt-Tiny model loading.

This module owns:
  * SHA-256 verification of the trained weights against the model card.
  * Model-card schema validation and quality-gate enforcement.
  * Constructing torchvision's ConvNeXt-Tiny with a 16-class head WITHOUT
    downloading pretrained weights (weights=None).
  * Robust state_dict loading that handles bare state_dicts, wrapped
    checkpoints, DataParallel prefixes, and torch.compile prefixes.
  * Thread-safe lazy caching of the loaded model, keyed by device.

The module exposes three public entry points:
  * verify_artifacts(): cheap startup check used by the FastAPI app.
  * get_model(device): full load used by the inference worker.
  * get_model_sha256(): returns the cached SHA for prediction results.

Nothing in this module touches the database, queue, blob storage, or
network. It only reads two files: model_card.json and classifier.pt.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torchvision.models import convnext_tiny

from .constants import (
    CHECKPOINT_PATH,
    CLASS_NAMES,
    DEFAULT_DEVICE,
    MIN_TEST_TOP1,
    MODEL_CARD_PATH,
    NUM_CLASSES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ClassifierError(Exception):
    """Base class for all classifier-package errors."""


class ArtifactError(ClassifierError):
    """An artifact file is missing, malformed, or contractually invalid."""


class ChecksumMismatchError(ArtifactError):
    """The computed SHA-256 of the checkpoint does not match the model card."""


class QualityGateError(ArtifactError):
    """The model card reports test top-1 below the configured threshold."""


class ModelLoadError(ClassifierError):
    """The state_dict could not be loaded into the network."""


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------
_SHA256_CHUNK_SIZE: int = 1 << 20  # 1 MiB


def _compute_sha256(path: Path) -> str:
    """Stream a file through SHA-256, chunked to keep memory bounded."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_SHA256_CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Model card
# ---------------------------------------------------------------------------
def _load_model_card() -> dict[str, Any]:
    """Read and JSON-parse model_card.json, with clear errors on failure."""
    if not MODEL_CARD_PATH.is_file():
        raise ArtifactError(f"model card not found at {MODEL_CARD_PATH}")
    try:
        with MODEL_CARD_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ArtifactError(f"model card is not valid JSON: {e}") from e
    except OSError as e:
        raise ArtifactError(f"could not read model card: {e}") from e


def _validate_card_schema(card: dict[str, Any]) -> None:
    """Confirm the card contains the keys we depend on, with sane values."""
    try:
        checkpoint_sha = card["checkpoint"]["sha256"]
        dataset_classes = card["dataset"]["classes"]
        arch_num_classes = card["architecture"]["num_classes"]
        test_top1 = card["metrics"]["full_test"]["top1"]
    except KeyError as e:
        raise ArtifactError(f"model card missing required key: {e}") from e

    if not isinstance(checkpoint_sha, str) or len(checkpoint_sha) != 64:
        raise ArtifactError("model card sha256 is not a 64-char hex string")
    if tuple(dataset_classes) != CLASS_NAMES:
        raise ArtifactError(
            "model card class list does not match constants.CLASS_NAMES; "
            "either the card or the constants is out of date"
        )
    if arch_num_classes != NUM_CLASSES:
        raise ArtifactError(
            f"model card num_classes={arch_num_classes} != constants.NUM_CLASSES={NUM_CLASSES}"
        )
    if not isinstance(test_top1, (int, float)):
        raise ArtifactError("model card metrics.full_test.top1 is not numeric")


def verify_artifacts() -> dict[str, Any]:
    """Validate that artifacts exist, match the card, and clear the quality gate.

    This is the boot-time check used by the FastAPI app. It does NOT load
    the model into memory, so it is cheap enough to run on every process
    start. The worker also calls this via get_model().

    Returns:
        The parsed and validated model card dict.

    Raises:
        ArtifactError: artifact missing or model card malformed.
        ChecksumMismatchError: computed SHA does not match the card.
        QualityGateError: card's reported test top-1 is below MIN_TEST_TOP1.
    """
    card = _load_model_card()
    _validate_card_schema(card)

    if not CHECKPOINT_PATH.is_file():
        raise ArtifactError(f"checkpoint not found at {CHECKPOINT_PATH}")

    expected_sha = card["checkpoint"]["sha256"]
    actual_sha = _compute_sha256(CHECKPOINT_PATH)
    if actual_sha != expected_sha:
        raise ChecksumMismatchError(
            f"checkpoint SHA-256 mismatch: card={expected_sha} actual={actual_sha}"
        )

    test_top1 = float(card["metrics"]["full_test"]["top1"])
    if test_top1 < MIN_TEST_TOP1:
        raise QualityGateError(
            f"model card test top-1 {test_top1:.4f} is below quality gate "
            f"{MIN_TEST_TOP1:.4f}; refusing to load"
        )

    logger.info(
        "classifier artifacts verified: sha256=%s test_top1=%.4f",
        actual_sha[:12],
        test_top1,
    )
    return card


# ---------------------------------------------------------------------------
# Model construction and state_dict loading
# ---------------------------------------------------------------------------
def _build_convnext_tiny(num_classes: int = NUM_CLASSES) -> nn.Module:
    """Build a ConvNeXt-Tiny with a fresh num_classes head.

    weights=None is critical: we never download pretrained weights at
    runtime. The trained weights come from the local checkpoint file.
    """
    model = convnext_tiny(weights=None)
    # ConvNeXt-Tiny's classifier is Sequential(LayerNorm2d, Flatten, Linear).
    # We replace only the final Linear, preserving the existing in_features (768).
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, num_classes)
    return model


# Common prefixes that get prepended by training wrappers and need stripping
# before a strict load_state_dict will accept the keys.
_STATE_DICT_PREFIXES: tuple[str, ...] = ("module.", "_orig_mod.")


def _unwrap_checkpoint(raw: Any) -> dict[str, torch.Tensor]:
    """Extract the actual state_dict from various save formats."""
    if isinstance(raw, dict):
        # Wrapped formats commonly produced by training loops
        for key in ("state_dict", "model_state_dict", "model"):
            if key in raw and isinstance(raw[key], dict):
                return raw[key]
        # Otherwise assume the dict itself is the state_dict.
        return raw
    raise ModelLoadError(
        f"checkpoint is not a dict (got {type(raw).__name__}); "
        "cannot extract a state_dict"
    )


def _strip_prefixes(state_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Remove training-wrapper prefixes from state_dict keys."""
    cleaned: dict[str, torch.Tensor] = {}
    for key, value in state_dict.items():
        new_key = key
        for prefix in _STATE_DICT_PREFIXES:
            if new_key.startswith(prefix):
                new_key = new_key[len(prefix):]
        cleaned[new_key] = value
    return cleaned


def _load_state_dict_robust(model: nn.Module, ckpt_path: Path, device: str) -> None:
    """Load weights into model, tolerating common training-time wrapping.

    Uses weights_only=True so torch will reject checkpoints that try to
    unpickle arbitrary Python objects. If your checkpoint was saved with
    custom classes, re-save a plain state_dict on Colab — do not flip
    weights_only to False.
    """
    try:
        raw = torch.load(ckpt_path, map_location=device, weights_only=True)
    except Exception as e:
        raise ModelLoadError(f"torch.load failed for {ckpt_path}: {e}") from e

    state_dict = _strip_prefixes(_unwrap_checkpoint(raw))

    try:
        model.load_state_dict(state_dict, strict=True)
    except RuntimeError as e:
        raise ModelLoadError(
            f"strict load_state_dict failed; the checkpoint architecture "
            f"does not match ConvNeXt-Tiny with a {NUM_CLASSES}-class head. "
            f"Underlying error: {e}"
        ) from e


# ---------------------------------------------------------------------------
# Cached model accessor
# ---------------------------------------------------------------------------
_cache_lock = threading.Lock()
_model_cache: dict[str, tuple[nn.Module, dict[str, Any]]] = {}


def get_model(device: str = DEFAULT_DEVICE) -> tuple[nn.Module, dict[str, Any]]:
    """Return the cached (model, model_card) pair for the given device.

    On the first call for a device, this:
      1. Calls verify_artifacts() — raises if anything is wrong.
      2. Builds a ConvNeXt-Tiny with weights=None.
      3. Loads the local checkpoint robustly.
      4. Moves the model to device, sets eval mode, freezes parameters.
      5. Caches (model, card) keyed by device.

    Subsequent calls for the same device return the cached pair without
    reloading. The cache is thread-safe.

    The inference worker should call this once at startup to surface
    artifact errors before processing any jobs.
    """
    with _cache_lock:
        if device in _model_cache:
            return _model_cache[device]

        card = verify_artifacts()
        model = _build_convnext_tiny()
        _load_state_dict_robust(model, CHECKPOINT_PATH, device)
        model.to(device)
        model.eval()
        for param in model.parameters():
            param.requires_grad_(False)

        _model_cache[device] = (model, card)
        logger.info("classifier model loaded onto device=%s", device)
        return model, card


def get_model_sha256() -> str:
    """Return the cached model's SHA-256.

    If no model is cached yet, loads on DEFAULT_DEVICE to populate the
    cache. Cheap after the first call.
    """
    with _cache_lock:
        if _model_cache:
            # Any cached entry has the same SHA — they all point at the
            # same on-disk checkpoint.
            _, card = next(iter(_model_cache.values()))
            return card["checkpoint"]["sha256"]
    # Cache empty: load on default device. get_model takes its own lock.
    _, card = get_model()
    return card["checkpoint"]["sha256"]