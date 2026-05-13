import json
import sys

from app.classifier.constants import GOLDEN_EXPECTED_PATH, GOLDEN_IMAGES_DIR
from app.classifier.predict import predict_image_path

_EXPECTED_COUNT = 50
_CONF_TOLERANCE = 1e-6


def run_golden_replay() -> int:
    entries = json.loads(GOLDEN_EXPECTED_PATH.read_text())

    if len(entries) != _EXPECTED_COUNT:
        print(
            f"FAIL: golden_expected.json has {len(entries)} entries; "
            f"expected exactly {_EXPECTED_COUNT}."
        )
        return 1

    mismatches: list[str] = []

    for entry in entries:
        filename = entry["filename"]
        path = GOLDEN_IMAGES_DIR / filename

        pred = predict_image_path(path, device="cpu")

        lines: list[str] = []

        if pred.label_name != entry["expected_label"]:
            lines.append(
                f"  expected_label={entry['expected_label']}  got={pred.label_name}"
            )

        conf_diff = abs(pred.top1_confidence - entry["expected_top1_confidence"])
        if conf_diff > _CONF_TOLERANCE:
            lines.append(
                f"  expected_top1={entry['expected_top1_confidence']:.7f}"
                f"  got={pred.top1_confidence:.7f}"
                f"  diff={conf_diff:.2e}"
            )

        got_top5 = [t.label_name for t in pred.top5]
        if got_top5 != entry["expected_top5_labels"]:
            lines.append(f"  expected_top5={entry['expected_top5_labels']}")
            lines.append(f"  got_top5     ={got_top5}")

        if lines:
            mismatches.append(f"MISMATCH {filename}\n" + "\n".join(lines))

    if not mismatches:
        print(
            f"PASS: {_EXPECTED_COUNT}/{_EXPECTED_COUNT} golden images replayed "
            "identically (label, top1 within 1e-6, top5)"
        )
        return 0

    for block in mismatches:
        print(block)
    print(f"FAIL: {len(mismatches)}/{_EXPECTED_COUNT} mismatches.")
    return 1


if __name__ == "__main__":
    sys.exit(run_golden_replay())
