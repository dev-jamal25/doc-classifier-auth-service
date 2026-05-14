#!/bin/sh
set -eu

echo "[vault-init] Seeding Vault KV paths at ${VAULT_ADDR}..."

vault kv put secret/doc-classifier/jwt \
  secret="dev-jwt-secret-do-not-use-in-prod" \
  algorithm="HS256" \
  exp_minutes=60

vault kv put secret/doc-classifier/db \
  database_url="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"

vault kv put secret/doc-classifier/minio \
  access_key="${MINIO_ROOT_USER}" \
  secret_key="${MINIO_ROOT_PASSWORD}"

vault kv put secret/doc-classifier/sftp \
  username="${SFTP_USERNAME}" \
  password="${SFTP_PASSWORD}"

vault kv put secret/doc-classifier/redis \
  url="redis://redis:6379/0"

echo "[vault-init] Done."
