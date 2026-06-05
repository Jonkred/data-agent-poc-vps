#!/bin/bash
# 08-clickhouse-init.sh — Cria banco poc_dw e tabelas de controle
# Usa docker compose exec (não HTTP) para evitar timeout no startup
set -euo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
cd "$COMPOSE_DIR"

CH_EXEC="docker compose exec -T clickhouse clickhouse-client"
CH_USER="--user=poc_user --password=click2024"

echo "==> Aguardando ClickHouse via client (max 180s)..."
SECONDS=0
until $CH_EXEC --query "SELECT 1" > /dev/null 2>&1; do
  if [ "$SECONDS" -gt 180 ]; then
    echo ""
    echo "  ERRO: ClickHouse não respondeu em 180s. Logs:"
    docker logs compose-core-clickhouse-1 2>&1 | tail -30
    exit 1
  fi
  printf "."; sleep 3
done
echo " ✔"

run_sql() {
  $CH_EXEC $CH_USER --query "$1" > /dev/null
}

echo "==> Criando banco poc_dw..."
run_sql "CREATE DATABASE IF NOT EXISTS poc_dw"
echo "  ✔ poc_dw"

echo "==> Criando tabelas..."

run_sql "CREATE TABLE IF NOT EXISTS poc_dw.ingestion_control
(
    source_name       String,
    entity_name       String,
    extraction_key    String,
    last_hash         String   DEFAULT '',
    last_status       String   DEFAULT '',
    last_error        String   DEFAULT '',
    last_extracted_at DateTime DEFAULT now(),
    run_id            String   DEFAULT ''
)
ENGINE = ReplacingMergeTree
ORDER BY (source_name, entity_name, extraction_key)"
echo "  ✔ ingestion_control"

run_sql "CREATE TABLE IF NOT EXISTS poc_dw.ingestion_runs
(
    run_id            String,
    source_name       String,
    entity_name       String,
    dag_id            String   DEFAULT '',
    task_id           String   DEFAULT '',
    start_time        DateTime DEFAULT now(),
    end_time          Nullable(DateTime),
    status            String   DEFAULT '',
    records_extracted Int64    DEFAULT 0,
    records_loaded    Int64    DEFAULT 0,
    raw_path          String   DEFAULT '',
    error_message     String   DEFAULT ''
)
ENGINE = MergeTree
ORDER BY (source_name, start_time)"
echo "  ✔ ingestion_runs"

run_sql "CREATE TABLE IF NOT EXISTS poc_dw.ingestion_errors
(
    run_id        String,
    source_name   String,
    entity_name   String,
    error_time    DateTime DEFAULT now(),
    error_type    String   DEFAULT '',
    error_message String   DEFAULT '',
    stack_trace   String   DEFAULT ''
)
ENGINE = MergeTree
ORDER BY (source_name, error_time)"
echo "  ✔ ingestion_errors"

run_sql "CREATE TABLE IF NOT EXISTS poc_dw.data_quality_results
(
    run_id         String,
    model_name     String,
    test_name      String,
    dimension      String   DEFAULT '',
    status         String   DEFAULT '',
    failures_count Int64    DEFAULT 0,
    tested_at      DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (model_name, tested_at)"
echo "  ✔ data_quality_results"

echo ""
echo "  Tabelas em poc_dw:"
$CH_EXEC $CH_USER --query "SHOW TABLES FROM poc_dw FORMAT PrettyCompact"

echo "✔ 08 — ClickHouse inicializado."
