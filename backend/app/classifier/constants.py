# static paths, class names, model-card fields

# """Frozen configuration for the RVL-CDIP document classifier.

# This module is the single source of truth for class names, preprocessing
# parameters, artifact paths, and quality-gate thresholds. It has no
# runtime dependencies beyond the Python standard library so that it can
# be imported safely from any layer, including startup code that runs
# before torch is loaded.

# Nothing in this module imports torch, torchvision, FastAPI, SQLAlchemy,
# Redis, MinIO, or any other application-layer dependency.
# """

from __future__ import annotations

from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Class taxonomy
# ---------------------------------------------------------------------------
# The order of CLASS_NAMES is the label-id mapping used by the trained model.
# Do not sort, reorder, or regenerate from a set. It must match the order
# committed in model_card.json under dataset.classes.
CLASS_NAMES: Final[tuple[str, ...]] = (
    "letter",
    "form",
    "email",
    "handwritten",
    "advertisement",
    "scientific_report",
    "scientific_publication",
    "specification",
    "file_folder",
    "news_article",
    "budget",
    "invoice",
    "presentation",
    "questionnaire",
    "resume",
    "memo",
)

NUM_CLASSES: Final[int] = len(CLASS_NAMES)

LABEL_TO_ID: Final[dict[str, int]] = {name: i for i, name in enumerate(CLASS_NAMES)}
ID_TO_LABEL: Final[dict[int, str]] = {i: name for i, name in enumerate(CLASS_NAMES)}


# ---------------------------------------------------------------------------
# Preprocessing contract (mirrors model_card.json input_contract)
# ---------------------------------------------------------------------------
IMAGE_SIZE: Final[tuple[int, int]] = (224, 224)
IMAGENET_MEAN: Final[tuple[float, float, float]] = (0.485, 0.456, 0.406)
IMAGENET_STD: Final[tuple[float, float, float]] = (0.229, 0.224, 0.225)


# ---------------------------------------------------------------------------
# Inference policy
# ---------------------------------------------------------------------------
# Predictions with top-1 confidence below this threshold are flagged for
# human review. This value MUST match the reviewer permission rule in the
# Casbin policy ("reviewer may relabel where top-1 < 0.7"). If you change
# one, change both together.
REVIEW_THRESHOLD: Final[float] = 0.70

# Production target is CPU per the latency budget in the project brief.
DEFAULT_DEVICE: Final[str] = "cpu"


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------
# api and worker refuse to boot if model_card.json reports a full-test top-1
# below this threshold. Must match the value committed in the repo README.
MIN_TEST_TOP1: Final[float] = 0.70


# ---------------------------------------------------------------------------
# Artifact paths
# ---------------------------------------------------------------------------
# Paths are resolved relative to this file so the package is portable
# across Colab, local dev, and Docker. Never hardcode absolute paths.
CLASSIFIER_DIR: Final[Path] = Path(__file__).resolve().parent
MODELS_DIR: Final[Path] = CLASSIFIER_DIR / "models"
EVAL_DIR: Final[Path] = CLASSIFIER_DIR / "eval"

MODEL_CARD_PATH: Final[Path] = MODELS_DIR / "model_card.json"
CHECKPOINT_PATH: Final[Path] = MODELS_DIR / "classifier.pt"

GOLDEN_EXPECTED_PATH: Final[Path] = EVAL_DIR / "golden_expected.json"
GOLDEN_IMAGES_DIR: Final[Path] = EVAL_DIR / "golden_images"
