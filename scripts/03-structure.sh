#!/bin/bash
# 03-structure.sh — Estrutura de diretórios, copia arquivos do repo e gera .env
set -euo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

echo "==> Criando estrutura em $POC_DIR..."
mkdir -p "$COMPOSE_DIR"
mkdir -p "$POC_DIR"/{dags,dbt/{models/{bronze,silver,gold},tests,macros},data_contracts}
mkdir -p "$POC_DIR"/src/{core,connectors,pdf,warehouse,agent_tools,llm}
mkdir -p "$POC_DIR"/tests/{unit,integration,fixtures}
mkdir -p "$POC_DIR/docs"

echo "==> Copiando arquivos do repositório..."
cp "$REPO_DIR/src/agent_tools/api.py" \
   "$POC_DIR/src/agent_tools/api.py"

cp "$REPO_DIR/infra/compose-core/clickhouse-config.xml" \
   "$COMPOSE_DIR/clickhouse-config.xml"

cp "$REPO_DIR/infra/compose-core/clickhouse-users.xml" \
   "$COMPOSE_DIR/clickhouse-users.xml"

[ -f "$REPO_DIR/dbt/dbt_project.yml" ] && \
  cp "$REPO_DIR/dbt/dbt_project.yml" "$POC_DIR/dbt/dbt_project.yml"

# Copia modelos de exemplo se existirem
for layer in bronze silver gold; do
  src="$REPO_DIR/dbt/models/$layer"
  dst="$POC_DIR/dbt/models/$layer"
  [ -d "$src" ] && cp -rn "$src/." "$dst/" 2>/dev/null || true
done

echo "==> Gerando .env com segredos..."
FERNET_KEY=$(python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
WEB_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
API_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > "$COMPOSE_DIR/.env" <<ENVEOF
# POC Data Agent VPS — $(date '+%Y-%m-%d')
# Gerado automaticamente. NÃO commitir este arquivo.

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

CLICKHOUSE_DB=poc_dw
CLICKHOUSE_USER=poc_user
CLICKHOUSE_PASSWORD=click2024

FASTAPI_SECRET_KEY=${API_SECRET}
DOMAIN=localhost
QDRANT_API_KEY=poc2024qdrant
OLLAMA_MODEL=qwen2.5:1.5b
ENVEOF

echo "  .env criado em $COMPOSE_DIR/.env"
echo "✔ 03 — Estrutura criada."
