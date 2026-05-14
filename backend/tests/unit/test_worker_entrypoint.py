from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image

from app.classifier.predict import InvalidImageError
from app.domain.queue import ClassificationJob
from app.entrypoints.worker import (
    InferenceResult,
    predict_document_bytes,
    process_classification_job,
    render_overlay_png,
)


class _FakeBlobClient:
    def __init__(self, *, payload: bytes, steps: list[str]) -> None:
        self._payload = payload
        self._steps = steps
        self.uploads: list[tuple[str, str, bytes, str]] = []

    def download_file(self, bucket: str, key: str) -> bytes:
        self._steps.append("download")
        assert bucket == "documents-raw"
        assert key == "sftp/2026/05/14/abc.tif"
        return self._payload

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self._steps.append("upload")
        self.uploads.append((bucket, key, data, content_type))


def _context_stub(*, use_mock_classifier: bool = False):
    settings = SimpleNamespace(
        minio_raw_bucket="documents-raw",
        minio_overlay_bucket="documents-overlays",
        use_mock_classifier=use_mock_classifier,
    )
    return SimpleNamespace(settings=settings)


def _payload() -> ClassificationJob:
    return ClassificationJob(
        batch_id=uuid4(),
        blob_key="sftp/2026/05/14/abc.tif",
        source_filename="scan_001.tif",
        sftp_user="vendor-1",
        request_id=uuid4(),
        received_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_process_classification_job_happy_path_writes_overlay_and_prediction() -> None:
    steps: list[str] = []
    payload = _payload()
    context = _context_stub(use_mock_classifier=False)
    blob = _FakeBlobClient(payload=b"raw-tiff", steps=steps)

    async def prediction_writer(**kwargs) -> None:
        steps.append("record")
        assert kwargs["batch_id"] == payload.batch_id
        assert kwargs["label"] == "memo"
        assert kwargs["confidence"] == 0.91
        assert kwargs["top5"][0] == ("memo", 0.91)
        assert kwargs["overlay_blob_key"] == f"overlays/{payload.batch_id}.png"
        assert kwargs["model_sha256"] == "sha-123"
        assert kwargs["request_id"] == payload.request_id

    async def failed_batch_writer(**kwargs) -> None:
        raise AssertionError("failed_batch_writer should not be called on happy path")

    def predictor(document_bytes: bytes, *, use_mock_classifier: bool) -> InferenceResult:
        steps.append("predict")
        assert document_bytes == b"raw-tiff"
        assert use_mock_classifier is False
        return InferenceResult(
            label="memo",
            confidence=0.91,
            top5=[
                ("memo", 0.91),
                ("invoice", 0.04),
                ("letter", 0.03),
                ("form", 0.01),
                ("budget", 0.01),
            ],
            model_sha256="sha-123",
        )

    def overlay_renderer(document_bytes: bytes, *, label: str, confidence: float) -> bytes:
        steps.append("overlay")
        assert document_bytes == b"raw-tiff"
        assert label == "memo"
        assert confidence == 0.91
        return b"png-bytes"

    await process_classification_job(
        payload=payload,
        context=context,
        blob_client=blob,
        prediction_writer=prediction_writer,
        failed_batch_writer=failed_batch_writer,
        predictor=predictor,
        overlay_renderer=overlay_renderer,
    )

    assert steps == ["download", "predict", "overlay", "upload", "record"]
    assert blob.uploads == [
        (
            "documents-overlays",
            f"overlays/{payload.batch_id}.png",
            b"png-bytes",
            "image/png",
        )
    ]


@pytest.mark.asyncio
async def test_process_classification_job_invalid_image_marks_failed_and_stops() -> None:
    steps: list[str] = []
    payload = _payload()
    context = _context_stub(use_mock_classifier=False)
    blob = _FakeBlobClient(payload=b"corrupted", steps=steps)

    async def prediction_writer(**kwargs) -> None:
        raise AssertionError("prediction_writer should not be called for invalid images")

    failed_calls: list[dict] = []

    async def failed_batch_writer(**kwargs) -> None:
        steps.append("mark_failed")
        failed_calls.append(kwargs)

    def predictor(document_bytes: bytes, *, use_mock_classifier: bool) -> InferenceResult:
        steps.append("predict")
        raise InvalidImageError("bad image")

    def overlay_renderer(document_bytes: bytes, *, label: str, confidence: float) -> bytes:
        raise AssertionError("overlay_renderer should not be called for invalid images")

    await process_classification_job(
        payload=payload,
        context=context,
        blob_client=blob,
        prediction_writer=prediction_writer,
        failed_batch_writer=failed_batch_writer,
        predictor=predictor,
        overlay_renderer=overlay_renderer,
    )

    assert steps == ["download", "predict", "mark_failed"]
    assert len(failed_calls) == 1
    assert failed_calls[0]["batch_id"] == payload.batch_id
    assert failed_calls[0]["request_id"] == payload.request_id
    assert failed_calls[0]["failure_reason"].startswith("worker_invalid_image")
    assert blob.uploads == []


def test_predict_document_bytes_mock_mode_returns_fixed_prediction() -> None:
    result = predict_document_bytes(b"ignored", use_mock_classifier=True)
    assert result.label == "letter"
    assert result.confidence == 0.95
    assert len(result.top5) == 5
    assert result.top5[0] == ("letter", 0.95)
    assert result.model_sha256 == "mock-model"


def test_predict_document_bytes_invalid_image_raises() -> None:
    with pytest.raises(InvalidImageError):
        predict_document_bytes(b"not-an-image", use_mock_classifier=False)


def test_render_overlay_png_returns_png_bytes() -> None:
    image = Image.new("L", (24, 24), color=128)

    # keep this explicit to avoid relying on temporary files in unit tests
    from io import BytesIO

    raw_bytes = BytesIO()
    image.save(raw_bytes, format="TIFF")

    overlay = render_overlay_png(raw_bytes.getvalue(), label="memo", confidence=0.88)
    assert overlay.startswith(b"\x89PNG\r\n\x1a\n")
