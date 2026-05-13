from __future__ import annotations

import io
from urllib.parse import urlparse

from minio import Minio


class BlobError(RuntimeError):
    """Raised when MinIO operations fail."""


def _normalize_endpoint(endpoint: str) -> tuple[str, bool]:
    if "://" not in endpoint:
        return endpoint.rstrip("/"), False

    parsed = urlparse(endpoint)
    if not parsed.netloc:
        raise BlobError(f"Invalid MinIO endpoint: `{endpoint}`.")
    return parsed.netloc, parsed.scheme == "https"


class BlobClient:
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool | None = None,
    ) -> None:
        normalized_endpoint, inferred_secure = _normalize_endpoint(endpoint)
        self._client = Minio(
            endpoint=normalized_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=inferred_secure if secure is None else secure,
        )

    def download_file(self, bucket: str, key: str) -> bytes:
        try:
            response = self._client.get_object(bucket_name=bucket, object_name=key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except Exception as exc:
            raise BlobError(
                f"Failed to download object `{key}` from bucket `{bucket}`."
            ) from exc

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        try:
            payload = io.BytesIO(data)
            self._client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=payload,
                length=len(data),
                content_type=content_type,
            )
        except Exception as exc:
            raise BlobError(f"Failed to upload object `{key}` to bucket `{bucket}`.") from exc

    def ensure_bucket(self, bucket: str) -> None:
        try:
            if not self._client.bucket_exists(bucket_name=bucket):
                self._client.make_bucket(bucket_name=bucket)
        except Exception as exc:
            raise BlobError(f"Failed to ensure MinIO bucket `{bucket}`.") from exc

    def health_check(self) -> bool:
        try:
            self._client.list_buckets()
        except Exception:
            return False
        return True
