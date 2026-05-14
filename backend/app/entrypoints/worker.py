from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass
from uuid import UUID

from PIL import Image, ImageDraw, UnidentifiedImageError
from redis import Redis
from rq import Queue, Worker

from app.classifier.constants import CLASS_NAMES
from app.classifier.model import ClassifierError, get_model, verify_artifacts
from app.classifier.predict import InvalidImageError, predict_pil_image
from app.core.config import get_settings
from app.core.lifespan import AppContext, lifespan
from app.core.logging import configure_logging, request_id_var
from app.domain.enums import BatchState
from app.domain.queue import ClassificationJob
from app.infra.blob import BlobClient, BlobError
from app.infra.vault import load_secrets
from app.repositories.audit_log import AuditLogRepository
from app.repositories.batches import BatchRepository
from app.repositories.predictions import PredictionRepository
from app.services.audit_log import AuditLogService
from app.services.batches import BatchService
from app.services.predictions import PredictionService

logger = logging.getLogger(__name__)

_MOCK_LABEL = "letter"
_MOCK_CONFIDENCE = 0.95
_MOCK_MODEL_SHA = "mock-model"

_worker_context: AppContext | None = None


class WorkerStartupError(RuntimeError):
    """Raised when startup checks fail and worker boot should abort."""


@dataclass(slots=True, frozen=True)
class InferenceResult:
    label: str
    confidence: float
    top5: list[tuple[str, float]]
    model_sha256: str


def _set_worker_context(context: AppContext) -> None:
    global _worker_context
    _worker_context = context


def _resolve_worker_context() -> AppContext:
    if _worker_context is not None:
        return _worker_context

    settings = get_settings()
    configure_logging(settings, service="worker")
    secrets = load_secrets(settings)
    context = AppContext(settings=settings, secrets=secrets)
    _set_worker_context(context)
    return context


def _build_overlay_key(batch_id: UUID) -> str:
    return f"overlays/{batch_id}.png"


def _build_mock_top5() -> list[tuple[str, float]]:
    return [
        (_MOCK_LABEL, _MOCK_CONFIDENCE),
        (CLASS_NAMES[1], 0.02),
        (CLASS_NAMES[2], 0.01),
        (CLASS_NAMES[3], 0.01),
        (CLASS_NAMES[4], 0.01),
    ]


def predict_document_bytes(document_bytes: bytes, *, use_mock_classifier: bool) -> InferenceResult:
    if use_mock_classifier:
        return InferenceResult(
            label=_MOCK_LABEL,
            confidence=_MOCK_CONFIDENCE,
            top5=_build_mock_top5(),
            model_sha256=_MOCK_MODEL_SHA,
        )

    try:
        with Image.open(io.BytesIO(document_bytes)) as image:
            prediction = predict_pil_image(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError(f"PIL could not decode job image bytes: {exc}") from exc

    return InferenceResult(
        label=prediction.label_name,
        confidence=prediction.top1_confidence,
        top5=[(entry.label_name, entry.confidence) for entry in prediction.top5],
        model_sha256=prediction.model_sha256,
    )


def render_overlay_png(document_bytes: bytes, *, label: str, confidence: float) -> bytes:
    try:
        with Image.open(io.BytesIO(document_bytes)) as image:
            overlay = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError(f"Cannot render overlay: invalid image bytes ({exc})") from exc

    draw = ImageDraw.Draw(overlay)
    width, _ = overlay.size
    draw.rectangle((0, 0, width, 26), fill=(0, 0, 0))
    draw.text((6, 6), f"{label} {confidence:.3f}", fill=(255, 255, 255))

    output = io.BytesIO()
    overlay.save(output, format="PNG")
    return output.getvalue()


def _load_async_session_factory():
    from app.db.session import async_session_factory

    return async_session_factory


async def write_prediction_record(
    *,
    batch_id: UUID,
    label: str,
    confidence: float,
    top5: list[tuple[str, float]],
    overlay_blob_key: str,
    model_sha256: str,
    request_id: UUID,
) -> None:
    session_factory = _load_async_session_factory()
    async with session_factory() as session:
        prediction_service = PredictionService(
            PredictionRepository(session),
            BatchRepository(session),
            AuditLogService(AuditLogRepository(session)),
        )
        await prediction_service.record_prediction(
            batch_id=batch_id,
            label=label,
            confidence=confidence,
            top5=top5,
            overlay_blob_key=overlay_blob_key,
            model_sha256=model_sha256,
            request_id=request_id,
        )


async def mark_batch_failed(
    *,
    batch_id: UUID,
    request_id: UUID,
    failure_reason: str,
) -> None:
    session_factory = _load_async_session_factory()
    async with session_factory() as session:
        batch_service = BatchService(BatchRepository(session))
        await batch_service.change_state(
            batch_id=batch_id,
            new_state=BatchState.FAILED,
            failure_reason=failure_reason,
        )


async def process_classification_job(
    *,
    payload: ClassificationJob,
    context: AppContext,
    blob_client: BlobClient,
    prediction_writer=write_prediction_record,
    failed_batch_writer=mark_batch_failed,
    predictor=predict_document_bytes,
    overlay_renderer=render_overlay_png,
) -> None:
    settings = context.settings
    logger.info(
        "Starting worker classification job.",
        extra={
            "event": "worker_job_started",
            "batch_id": str(payload.batch_id),
            "blob_key": payload.blob_key,
            "source_filename": payload.source_filename,
        },
    )

    document_bytes = blob_client.download_file(settings.minio_raw_bucket, payload.blob_key)

    try:
        inference = predictor(
            document_bytes,
            use_mock_classifier=settings.use_mock_classifier,
        )
        overlay_png = overlay_renderer(
            document_bytes,
            label=inference.label,
            confidence=inference.confidence,
        )
    except InvalidImageError as exc:
        await failed_batch_writer(
            batch_id=payload.batch_id,
            request_id=payload.request_id,
            failure_reason=f"worker_invalid_image: {exc}",
        )
        logger.warning(
            "Worker marked batch failed due to invalid image bytes.",
            extra={
                "event": "worker_job_invalid_image_marked_failed",
                "batch_id": str(payload.batch_id),
                "blob_key": payload.blob_key,
            },
        )
        return

    overlay_key = _build_overlay_key(payload.batch_id)
    blob_client.put_object(
        settings.minio_overlay_bucket,
        overlay_key,
        overlay_png,
        content_type="image/png",
    )

    await prediction_writer(
        batch_id=payload.batch_id,
        label=inference.label,
        confidence=inference.confidence,
        top5=inference.top5,
        overlay_blob_key=overlay_key,
        model_sha256=inference.model_sha256,
        request_id=payload.request_id,
    )

    logger.info(
        "Worker classification job completed.",
        extra={
            "event": "worker_job_completed",
            "batch_id": str(payload.batch_id),
            "blob_key": payload.blob_key,
            "label": inference.label,
            "confidence": inference.confidence,
            "overlay_blob_key": overlay_key,
        },
    )


def classify_document_job(payload_dict: dict) -> None:
    payload = ClassificationJob.model_validate(payload_dict)
    context = _resolve_worker_context()

    token = request_id_var.set(str(payload.request_id))
    try:
        blob_client = BlobClient(
            endpoint=context.settings.minio_endpoint,
            access_key=context.secrets.minio.access_key,
            secret_key=context.secrets.minio.secret_key,
        )
        asyncio.run(
            process_classification_job(
                payload=payload,
                context=context,
                blob_client=blob_client,
            )
        )
    except BlobError:
        logger.exception(
            "Worker blob operation failed.",
            extra={
                "event": "worker_blob_operation_failed",
                "batch_id": str(payload.batch_id),
                "blob_key": payload.blob_key,
            },
        )
        raise
    except Exception:
        logger.exception(
            "Worker classification job failed.",
            extra={
                "event": "worker_job_failed",
                "batch_id": str(payload.batch_id),
                "blob_key": payload.blob_key,
            },
        )
        raise
    finally:
        request_id_var.reset(token)


def _assert_runtime_dependencies(context: AppContext) -> None:
    settings = context.settings
    secrets = context.secrets

    blob_client = BlobClient(
        endpoint=settings.minio_endpoint,
        access_key=secrets.minio.access_key,
        secret_key=secrets.minio.secret_key,
    )

    if not blob_client.health_check():
        raise WorkerStartupError("Blob storage health check failed at startup.")

    blob_client.ensure_bucket(settings.minio_raw_bucket)
    blob_client.ensure_bucket(settings.minio_overlay_bucket)

    redis_client = Redis.from_url(secrets.redis.url)
    try:
        if not redis_client.ping():
            raise WorkerStartupError("Queue health check failed at startup.")
    except Exception as exc:
        raise WorkerStartupError("Queue health check failed at startup.") from exc

    if settings.use_mock_classifier:
        logger.warning(
            "Worker started with mock classifier enabled.",
            extra={
                "event": "worker_mock_classifier_enabled",
                "label": _MOCK_LABEL,
                "confidence": _MOCK_CONFIDENCE,
            },
        )
        return

    try:
        verify_artifacts()
        get_model()  # preload once so startup fails fast if weights are invalid
    except ClassifierError as exc:
        raise WorkerStartupError("Classifier startup checks failed.") from exc


def run_worker(context: AppContext) -> None:
    _set_worker_context(context)
    _assert_runtime_dependencies(context)

    settings = context.settings
    redis_conn = Redis.from_url(context.secrets.redis.url)
    queue = Queue(settings.worker_queue_name, connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)

    logger.info(
        "Worker started.",
        extra={
            "event": "worker_started",
            "queue_name": settings.worker_queue_name,
        },
    )

    try:
        worker.work(with_scheduler=False, logging_level=settings.log_level.upper())
    finally:
        logger.info(
            "Worker stopped.",
            extra={
                "event": "worker_stopped",
            },
        )


async def main() -> None:
    async with lifespan("worker") as context:
        run_worker(context)


if __name__ == "__main__":
    asyncio.run(main())
