from __future__ import annotations

import json

from app.classifier.constants import GOLDEN_EXPECTED_PATH, GOLDEN_IMAGES_DIR
from app.classifier.predict import predict_image_path


def main() -> None:
    entries = json.loads(GOLDEN_EXPECTED_PATH.read_text(encoding="utf-8"))

    if len(entries) != 50:
        raise RuntimeError(f"Expected 50 golden entries, found {len(entries)}")

    updated_entries = []

    for entry in entries:
        filename = entry["filename"]
        image_path = GOLDEN_IMAGES_DIR / filename

        if not image_path.is_file():
            raise FileNotFoundError(f"Missing golden image: {image_path}")

        pred = predict_image_path(image_path, device="cpu")

        updated = dict(entry)

        # Runtime-dependent expected prediction fields.
        updated["expected_label_id"] = pred.label_id
        updated["expected_label"] = pred.label_name
        updated["expected_top1_confidence"] = pred.top1_confidence
        updated["expected_top5_label_ids"] = [item.label_id for item in pred.top5]
        updated["expected_top5_labels"] = [item.label_name for item in pred.top5]
        updated["expected_top5_confidences"] = [item.confidence for item in pred.top5]

        # Preserve the Colab selection metadata, but refresh correctness
        # against the true label if that field exists.
        if "true_label" in updated:
            updated["correct"] = pred.label_name == updated["true_label"]

        updated_entries.append(updated)

    GOLDEN_EXPECTED_PATH.write_text(
        json.dumps(updated_entries, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Regenerated expected outputs for {len(updated_entries)} golden images.")
    print(f"Updated: {GOLDEN_EXPECTED_PATH}")


if __name__ == "__main__":
    main()
