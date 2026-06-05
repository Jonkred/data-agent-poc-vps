#!/bin/bash
# 10-validate.sh — Validação completa Sprint 1
set -uo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
CH="http://localhost:8123"
AUTH="poc_user:click2024"

PASS=0; FAIL=0

check() {
  local label="$1"; local cmd="$2"
  if bash -c "$cmd" > /dev/null 2>&1; then
    echo "  ✔ $label"; PASS=$((PASS+1))
  else
    echo "  ✘ $label"; FAIL=$((FAIL+1))
  fi
}

cd "$COMPOSE_DIR" 2>/dev/null || true

echo ""
echo "══════════════════════════════════════════"
echo "  VALIDAÇÃO SPRINT 1 — POC VPS"
echo "══════════════════════════════════════════"

echo ""
echo "── Sistema ──────────────────────────────"
check "Docker rodando"       "docker info > /dev/null 2>&1"
check "Swap ativo"           "swapon --show | grep -q swap"
check "UFW ativo"            "ufw status | grep -q 'Status: active'"
check "swappiness = 10"      "[ \"\$(cat /proc/sys/vm/swappiness)\" = '10' ]"
DISK=$(df / | awk 'NR==2{gsub("%",""); print $5}')
check "Disco abaixo de 70% (atual: ${DISK}%)" "[ '${DISK}' -lt 70 ]"

echo ""
echo "── Containers ───────────────────────────"
check "Postgres healthy" \
  "docker inspect --format='{{.State.Health.Status}}' compose-core-postgres-1 2>/dev/null | grep -q healthy"
check "Airflow webserver healthy" \
  "docker inspect --format='{{.State.Health.Status}}' compose-core-airflow-webserver-1 2>/dev/null | grep -q healthy"
check "MinIO healthy" \
  "docker inspect --format='{{.State.Health.Status}}' compose-core-minio-1 2>/dev/null | grep -q healthy"
check "ClickHouse healthy" \
  "docker inspect --format='{{.State.Health.Status}}' compose-core-clickhouse-1 2>/dev/null | grep -q healthy"
check "FastAPI /health" \
  "curl -sf http://localhost:8000/health 2>/dev/null | grep -q ok"

echo ""
echo "── Dados ────────────────────────────────"
check "MinIO bucket 'raw'" \
  "docker run --rm --network compose-core_poc-net --entrypoint sh minio/mc:latest \
    -c 'mc alias set l http://minio:9000 minioadmin minio2024 --quiet && mc ls l' \
    2>/dev/null | grep -q raw"
check "MinIO bucket 'bronze'" \
  "docker run --rm --network compose-core_poc-net --entrypoint sh minio/mc:latest \
    -c 'mc alias set l http://minio:9000 minioadmin minio2024 --quiet && mc ls l' \
    2>/dev/null | grep -q bronze"
check "ClickHouse tabela ingestion_control" \
  "curl -sf '$CH/' -u '$AUTH' \
    --data-binary 'EXISTS TABLE poc_dw.ingestion_control FORMAT TabSeparated' \
    2>/dev/null | grep -q '^1'"
check "ClickHouse tabela ingestion_runs" \
  "curl -sf '$CH/' -u '$AUTH' \
    --data-binary 'EXISTS TABLE poc_dw.ingestion_runs FORMAT TabSeparated' \
    2>/dev/null | grep -q '^1'"
check "dbt debug OK" \
  "source '$POC_DIR/.venv/dbt/bin/activate' 2>/dev/null && \
   cd '$POC_DIR/dbt' && \
   dbt debug --quiet 2>&1 | grep -q 'All checks passed'"

echo ""
echo "── Recursos ─────────────────────────────"
free -h | awk 'NR==2{printf "  RAM: Total=%-6s Usado=%-6s Disponível=%s\n", $2, $3, $7}'
RAM_AVAIL=$(free -m | awk 'NR==2{print $7}')
check "RAM livre > 2 GB (atual: ${RAM_AVAIL} MB)" "[ '${RAM_AVAIL}' -gt 2000 ]"

echo ""
echo "  Containers (memória):"
docker stats --no-stream --format \
  "  {{printf \"%-45s\" .Name}} {{.MemUsage}}" 2>/dev/null \
  | grep compose-core || true

echo ""
echo "══════════════════════════════════════════"
printf "  RESULTADO: %d aprovados · %d falhos\n" "$PASS" "$FAIL"
echo "══════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "  ⚠ Corrija os itens ✘ antes de avançar para a Sprint 2."
  echo "  Dica: docker compose logs <servico>"
  exit 1
fi

echo ""
echo "  ✔ Sprint 1 completa! Próximo passo: Sprint 2 — scraping."
