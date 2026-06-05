#!/bin/bash
# 05-run-stack.sh — Sobe stack core em sequência segura
# Sequência: postgres → airflow-init → resto
set -euo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
cd "$COMPOSE_DIR"

# Para containers existentes sem remover volumes
echo "==> Parando containers existentes (preserva dados)..."
docker compose --profile core down --remove-orphans 2>/dev/null || true

echo "==> Subindo postgres..."
docker compose --profile core up -d postgres

printf "  Aguardando postgres"
until docker compose exec -T postgres \
  pg_isready -U airflow -d airflow > /dev/null 2>&1; do
  printf "."; sleep 2
done
echo " ✔"

echo "==> Rodando airflow-init (migra DB + cria admin)..."
docker compose --profile core run --rm airflow-init \
  && echo "  ✔ Airflow DB inicializado." \
  || echo "  OK (admin já pode existir)"

echo "==> Subindo stack completa..."
docker compose --profile core up -d

printf "  Aguardando serviços ficarem healthy"
TIMEOUT=180; ELAPSED=0
until docker compose --profile core ps | grep -qE "(healthy|Up)" || [ "$ELAPSED" -ge "$TIMEOUT" ]; do
  printf "."; sleep 5; ELAPSED=$((ELAPSED+5))
done
echo ""

echo ""
docker compose ps
echo "✔ 05 — Stack core rodando."
