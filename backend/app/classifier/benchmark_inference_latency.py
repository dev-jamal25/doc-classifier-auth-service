from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

IMAGE_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}

DEVICE = "cpu"
P95_BUDGET_MS = 1000.0


def log(message: str) -> None:
    print(message, flush=True)


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = math.ceil((p / 100) * len(values)) - 1
    index = max(0, min(index, len(values) - 1))
    return values[index]


def format_ms(value: float) -> str:
    return f"{value:.2f}ms"


def main() -> None:
    log("=== Starting classifier latency benchmark ===")

    # Import heavy libraries after first log so we can see where it waits.
    log("Importing torch and classifier modules...")

    import torch

    from app.classifier.constants import GOLDEN_IMAGES_DIR
    from app.classifier.model import get_model
    from app.classifier.predict import predict_image_path

    warmup_runs = int(os.getenv("BENCHMARK_WARMUP_RUNS", "5"))
    repeats_per_image = int(os.getenv("BENCHMARK_REPEATS_PER_IMAGE", "1"))
    progress_every = int(os.getenv("BENCHMARK_PROGRESS_EVERY", "1"))

    torch.set_grad_enabled(False)

    log(f"Device: {DEVICE}")
    log(f"Torch version: {torch.__version__}")
    log(f"Torch CPU threads: {torch.get_num_threads()}")
    log(f"Warmup runs: {warmup_runs}")
    log(f"Repeats per image: {repeats_per_image}")
    log(f"Progress every: {progress_every}")
    log(f"Golden image dir: {GOLDEN_IMAGES_DIR}")

    image_paths = sorted(
        path
        for path in Path(GOLDEN_IMAGES_DIR).iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    log(f"Found {len(image_paths)} benchmark images")

    if not image_paths:
        raise RuntimeError(f"No golden images found in {GOLDEN_IMAGES_DIR}")

    log("First few images:")
    for path in image_paths[:5]:
        log(f"  - {path.name}")

    log("Loading model...")
    model_load_start = time.perf_counter()
    model, card = get_model(device=DEVICE)
    model.eval()
    model_load_ms = (time.perf_counter() - model_load_start) * 1000

    log(f"Loaded model SHA: {card['checkpoint']['sha256'][:12]}...")
    log(f"Model load time: {format_ms(model_load_ms)}")
    log("Model load is NOT counted in p95 inference latency.")

    warmup_images = image_paths[: min(warmup_runs, len(image_paths))]

    log(f"Starting warmup: {len(warmup_images)} prediction(s), not counted")

    for idx, image_path in enumerate(warmup_images, start=1):
        start = time.perf_counter()
        pred = predict_image_path(image_path, device=DEVICE)
        elapsed_ms = (time.perf_counter() - start) * 1000

        log(
            f"[warmup {idx}/{len(warmup_images)}] "
            f"{image_path.name} -> {pred.label_name} "
            f"conf={pred.top1_confidence:.4f} "
            f"latency={format_ms(elapsed_ms)}"
        )

    total_runs = repeats_per_image * len(image_paths)

    log(
        f"Starting timed benchmark: "
        f"{len(image_paths)} images × {repeats_per_image} repeat(s) "
        f"= {total_runs} timed prediction(s)"
    )

    latencies_ms: list[float] = []
    completed = 0
    benchmark_start = time.perf_counter()

    for repeat_idx in range(1, repeats_per_image + 1):
        log(f"--- Repeat {repeat_idx}/{repeats_per_image} ---")

        for image_path in image_paths:
            start = time.perf_counter()
            pred = predict_image_path(image_path, device=DEVICE)
            elapsed_ms = (time.perf_counter() - start) * 1000

            latencies_ms.append(elapsed_ms)
            completed += 1

            if completed <= 5 or completed % progress_every == 0 or completed == total_runs:
                running_mean = sum(latencies_ms) / len(latencies_ms)
                running_p95 = percentile(latencies_ms, 95)

                log(
                    f"[{completed}/{total_runs}] "
                    f"{image_path.name} -> {pred.label_name} "
                    f"conf={pred.top1_confidence:.4f} "
                    f"latency={format_ms(elapsed_ms)} "
                    f"running_mean={format_ms(running_mean)} "
                    f"running_p95={format_ms(running_p95)}"
                )

    total_benchmark_seconds = time.perf_counter() - benchmark_start

    mean_latency = sum(latencies_ms) / len(latencies_ms)
    p50 = percentile(latencies_ms, 50)
    p95 = percentile(latencies_ms, 95)
    max_latency = max(latencies_ms)

    result = {
        "device": DEVICE,
        "torch_version": torch.__version__,
        "torch_num_threads": torch.get_num_threads(),
        "num_images": len(image_paths),
        "warmup_runs_not_counted": len(warmup_images),
        "repeats_per_image": repeats_per_image,
        "num_timed_runs": len(latencies_ms),
        "total_benchmark_seconds": round(total_benchmark_seconds, 2),
        "mean_ms": round(mean_latency, 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "max_ms": round(max_latency, 2),
        "budget_ms": P95_BUDGET_MS,
        "pass": p95 < P95_BUDGET_MS,
    }

    log("=== Final benchmark result ===")
    print(json.dumps(result, indent=2), flush=True)

    if p95 >= P95_BUDGET_MS:
        raise SystemExit(
            f"Inference latency budget failed: "
            f"p95={p95:.2f}ms >= {P95_BUDGET_MS:.2f}ms"
        )

    log(f"PASS: inference p95={p95:.2f}ms is under {P95_BUDGET_MS:.2f}ms")


if __name__ == "__main__":
    main()