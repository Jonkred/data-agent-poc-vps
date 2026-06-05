#!/bin/bash
# 04-compose.sh — Gera docker-compose.yml na VPS
set -euo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

echo "==> Copiando docker-compose.yml do repositório..."
cp "$REPO_DIR/infra/compose-core/docker-compose.yml" \
   "$COMPOSE_DIR/docker-compose.yml"

echo "==> Validando YAML..."
cd "$COMPOSE_DIR"
docker compose --profile core config --quiet
echo "  ✔ YAML válido."

echo "✔ 04 — docker-compose.yml pronto."
