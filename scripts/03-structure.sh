#!/bin/bash
# 03-structure.sh — Cria diretórios de runtime e gera .env
#
# NÃO copia arquivos do repo — eles já estão no lugar certo.
# O repo É o projeto: docker-compose.yml, api.py, dbt_project.yml etc.
# estão em suas posições finais desde o clone.
#
# O que este script faz:
#   1. Cria subdiretórios não rastreados pelo git (src/core, src/llm, etc.)
#   2. Gera infra/compose-core/.env com segredos (gitignored)
set -euo pipefail

POC_DIR="${POC_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"

echo "==> Criando diretórios de runtime (não rastreados pelo git)..."
mkdir -p "$POC_DIR/src/core"
mkdir -p "$POC_DIR/src/connectors"
mkdir -p "$POC_DIR/src/pdf"
mkdir -p "$POC_DIR/src/warehouse"
mkdir -p "$POC_DIR/src/llm"
mkdir -p "$POC_DIR/tests/unit"
mkdir -p "$POC_DIR/tests/integration"
mkdir -p "$POC_DIR/tests/fixtures"
mkdir -p "$POC_DIR/docs"
echo "  ✔ Diretórios prontos."

if [ -f "$COMPOSE_DIR/.env" ]; then
  echo "  ✔ .env já existe — mantendo segredos existentes."
  exit 0
fi

echo "==> Gerando .env com segredos..."
FERNET_KEY=$(python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
WEB_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
API_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > "$COMPOSE_DIR/.env" <<ENVEOF
# POC Data Agent VPS — $(date '+%Y-%m-%d')
# Gerado por setup.sh. NÃO commitar — arquivo está em .gitignore.

POSTGRES_USER=airflow
POSTGRES_PASSWORD=poc2024pg
POSTGRES_DB=airflow

AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__FERNET_KEY=${FERNET_KEY}
AIRFLOW__WEBSERVER__SECRET_KEY=${WEB_SECRET}
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__LOGGING__LOGGING_LEVEL=WARNING

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minio2024
MINIO_ENDPOINT=http://minio:9000

CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=poc_dw
CLICKHOUSE_USER=poc_user
CLICKHOUSE_PASSWORD=click2024
CLICKHOUSE_CONNECT_TIMEOUT=10
CLICKHOUSE_READ_TIMEOUT=120

PUBLIC_API_COUNTRIES_URL=https://restcountries.com/v3.1/all?fields=cca2,name,region,population,flags
PUBLIC_API_TIMEOUT=30
PUBLIC_API_MAX_RECORDS=300
PUBLIC_API_BATCH_SIZE=50
PIPELINE_SOURCE_NAME=rest_countries
PIPELINE_ENTITY_NAME=countries
PIPELINE_TARGET_TABLE=bronze_rest_countries
PIPELINE_SCHEMA_VERSION=v1

FASTAPI_SECRET_KEY=${API_SECRET}
DOMAIN=localhost
QDRANT_API_KEY=poc2024qdrant
OLLAMA_MODEL=qwen2.5:1.5b
ENVEOF

echo "  ✔ .env criado em $COMPOSE_DIR/.env"
echo "✔ 03 — Estrutura pronta."
