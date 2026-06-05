#!/bin/bash
# 05-run-stack.sh — Sobe stack core em sequência segura
# Usa "up -d" inteligente: recria apenas os containers que mudaram de config.
set -euo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
cd "$COMPOSE_DIR"

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
  || echo "  OK (admin pode já existir)"

echo "==> Subindo stack completa (recria containers que mudaram)..."
docker compose --profile core up -d

printf "  Aguardando containers ficarem healthy"
TIMEOUT=180; ELAPSED=0
until docker compose --profile core ps | grep -qE "healthy" \
  || [ "$ELAPSED" -ge "$TIMEOUT" ]; do
  printf "."; sleep 5; ELAPSED=$((ELAPSED+5))
done
echo ""

echo ""
docker compose ps
echo "✔ 05 — Stack core rodando."
