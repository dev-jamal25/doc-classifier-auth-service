# public prediction API used by worker/golden.py

"""Inference orchestration for the document classifier.

Composes model.py and transforms.py into the two public entry points
the inference worker uses:

  * predict_pil_image(image, device=...)
  * predict_image_path(path, device=...)

Both return a Prediction dataclass containing the top-1 label, top-1
confidence, the top-5 list, a needs_review flag, and the model SHA-256.

This module does not touch the database, the queue, blob storage, or
HTTP. It is a pure inference library.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .runtime import configure_inference_runtime

configure_inference_runtime()

import torch

from .constants import DEFAULT_DEVICE, ID_TO_LABEL, REVIEW_THRESHOLD
from .model import ClassifierError, get_model
from .transforms import prepare_image

# Number of top predictions returned. The top-1 is duplicated in
# label_id/label_name/top1_confidence for convenience.
_TOPK: int = 5


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class PredictionError(ClassifierError):
    """Base class for inference-time errors."""


class InvalidImageError(PredictionError):
    """The image file could not be opened or decoded by PIL."""


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TopKEntry:
    """One entry in the top-k prediction list."""

    label_id: int
    label_name: str
    confidence: float


@dataclass(frozen=True)
class Prediction:
    """A single document-classification result.

    Attributes:
        label_id: Integer class id of the top-1 prediction (0..NUM_CLASSES-1).
        label_name: Human-readable class name corresponding to label_id.
        top1_confidence: Softmax probability of the top-1 class, in [0, 1].
        top5: Tuple of the top-5 entries sorted by descending confidence.
            top5[0] always matches label_id / label_name / top1_confidence.
        needs_review: True when top1_confidence < REVIEW_THRESHOLD; consumed
            by the reviewer-permission logic in the API.
        model_sha256: SHA-256 of the classifier.pt that produced this
            prediction. Lets downstream systems track which model version
            wrote any given row.
    """

    label_id: int
    label_name: str
    top1_confidence: float
    top5: tuple[TopKEntry, ...]
    needs_review: bool
    model_sha256: str


# ---------------------------------------------------------------------------
# Public inference functions
# ---------------------------------------------------------------------------
def predict_pil_image(
    image: Image.Image,
    device: str = DEFAULT_DEVICE,
) -> Prediction:
    """Run inference on an already-opened PIL image.

    Args:
        image: A PIL image in any mode. RGB conversion is handled inside
            the transforms pipeline.
        device: Torch device string. Defaults to "cpu".

    Returns:
        A Prediction with top-1, top-5, and needs_review populated.
    """
    model, card = get_model(device)
    tensor = prepare_image(image).to(device)

    with torch.inference_mode():
        logits = model(tensor)
        # Explicit float32 keeps softmax deterministic even if anyone later
        # wraps the model in autocast or quantization.
        probs = torch.softmax(logits.float(), dim=1)
        top_probs, top_ids = torch.topk(probs, k=_TOPK, dim=1)

    # Drop the batch dim and move to Python primitives
    top_probs_list = top_probs.squeeze(0).cpu().tolist()
    top_ids_list = top_ids.squeeze(0).cpu().tolist()

    top5 = tuple(
        TopKEntry(
            label_id=int(label_id),
            label_name=ID_TO_LABEL[int(label_id)],
            confidence=float(prob),
        )
        for label_id, prob in zip(top_ids_list, top_probs_list, strict=True)
    )
    top1 = top5[0]

    return Prediction(
        label_id=top1.label_id,
        label_name=top1.label_name,
        top1_confidence=top1.confidence,
        top5=top5,
        needs_review=top1.confidence < REVIEW_THRESHOLD,
        model_sha256=card["checkpoint"]["sha256"],
    )


def predict_image_path(
    path: str | Path,
    device: str = DEFAULT_DEVICE,
) -> Prediction:
    """Open an image file from disk and run inference.

    The file is opened lazily by PIL and forced to load via the RGB
    conversion in prepare_image. Multi-page TIFFs use the first frame.

    Args:
        path: Filesystem path to a PIL-readable image (TIFF, PNG, JPEG, etc.).
        device: Torch device string. Defaults to "cpu".

    Raises:
        InvalidImageError: PIL could not open or decode the file.
    """
    path = Path(path)
    try:
        with Image.open(path) as image:
            return predict_pil_image(image, device=device)
    except FileNotFoundError as e:
        raise InvalidImageError(f"image file not found: {path}") from e
    except UnidentifiedImageError as e:
        raise InvalidImageError(f"PIL could not decode {path}: {e}") from e
    except OSError as e:
        # PIL raises plain OSError for truncated files, zero-byte files, etc.
        raise InvalidImageError(f"could not read image {path}: {e}") from e
