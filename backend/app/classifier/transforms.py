# exact preprocessing only

"""Deterministic inference preprocessing for the document classifier.

This is the only place in the codebase where inference preprocessing is
defined. All callers — predict.py, golden.py, and the inference worker —
must route through prepare_image. Duplicating these steps elsewhere is
the most common source of golden-set drift.

Pipeline:
    PIL.Image -> convert to RGB -> resize 224x224 -> ToTensor -> ImageNet normalize

No random augmentations. No OCR. No data-dependent branches.
"""

from __future__ import annotations

import torch
from PIL import Image
from torchvision import transforms

from .constants import IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD

# Built once at module import. Constructing a Compose per call would be
# wasteful and is also a footgun if anything in the pipeline ever becomes
# stateful (e.g. a Normalize with running statistics).
_INFERENCE_TRANSFORM: transforms.Compose = transforms.Compose(
    [
        transforms.Resize(IMAGE_SIZE, antialias=True),
        transforms.ToTensor(),
        transforms.Normalize(mean=list(IMAGENET_MEAN), std=list(IMAGENET_STD)),
    ]
)


def prepare_image(image: Image.Image) -> torch.Tensor:
    """Apply the inference preprocessing pipeline to a PIL image.

    The RGB conversion is performed inside this function (not as a
    transform step or in the caller) so it is structurally impossible
    for a caller to forget it. RVL-CDIP TIFFs are grayscale, but
    ConvNeXt expects 3-channel input.

    Args:
        image: A PIL image in any mode (L, RGB, RGBA, etc.). Multi-page
            TIFFs are handled as PIL handles them: only the current frame
            is used.

    Returns:
        A float32 tensor on CPU with shape (1, 3, 224, 224), ready to be
        moved to the inference device by the caller. The leading
        dimension is the batch dimension.
    """
    rgb_image = image.convert("RGB")
    tensor = _INFERENCE_TRANSFORM(rgb_image)
    return tensor.unsqueeze(0)
