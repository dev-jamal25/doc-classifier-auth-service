from __future__ import annotations

from redis import Redis
from rq import Queue, Retry

from app.domain.queue import ClassificationJob

DEFAULT_CLASSIFICATION_HANDLER = "app.entrypoints.worker.classify_document_job"


class QueueError(RuntimeError):
    """Raised when queue operations fail."""


class QueueClient:
    def __init__(
        self,
        *,
        redis_url: str,
        queue_name: str = "doc-jobs",
        classification_handler: str = DEFAULT_CLASSIFICATION_HANDLER,
    ) -> None:
        self._redis = Redis.from_url(redis_url)
        self._queue = Queue(name=queue_name, connection=self._redis)
        self._classification_handler = classification_handler

    def enqueue_classification(self, job: ClassificationJob) -> str:
        payload = job.model_dump(mode="json")
        retry = Retry(max=3, interval=[10, 30, 60])
        try:
            queued_job = self._queue.enqueue(
                self._classification_handler,
                payload,
                retry=retry,
            )
        except Exception as exc:
            raise QueueError("Failed to enqueue classification job.") from exc
        return queued_job.id

    def health_check(self) -> bool:
        try:
            return bool(self._redis.ping())
        except Exception:
            return False
