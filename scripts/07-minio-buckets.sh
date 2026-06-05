#!/bin/bash
# 07-minio-buckets.sh — Cria buckets no MinIO
set -euo pipefail

BUCKETS="raw bronze screenshots pdfs"

echo "==> Aguardando MinIO health..."
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; do
  printf "."; sleep 3
done
echo " ✔"

echo "==> Criando buckets: $BUCKETS"
# Usa --entrypoint sh para entrar no container minio/mc como shell
docker run --rm \
  --network compose-core_poc-net \
  --entrypoint sh \
  minio/mc:latest \
  -c "mc alias set local http://minio:9000 minioadmin minio2024 --quiet && \
      mc mb --ignore-existing $(echo $BUCKETS | sed 's/\([^ ]*\)/local\/\1/g') && \
      echo '' && mc ls local"

echo "✔ 07 — Buckets MinIO criados."
