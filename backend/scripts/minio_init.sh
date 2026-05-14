#!/bin/sh
set -eu

echo "[minio-init] Configuring MinIO alias..."
mc alias set local http://minio:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

echo "[minio-init] Ensuring buckets exist..."
mc mb --ignore-existing "local/${MINIO_RAW_BUCKET}"
mc mb --ignore-existing "local/${MINIO_OVERLAY_BUCKET}"

echo "[minio-init] Done."
