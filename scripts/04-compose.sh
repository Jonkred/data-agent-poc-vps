#!/bin/bash
# 04-compose.sh — Valida docker-compose.yml
#
# O docker-compose.yml já está no repo em infra/compose-core/.
# Não há nada a copiar — só valida o YAML.
set -euo pipefail

POC_DIR="${POC_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_DIR="$POC_DIR/infra/compose-core"
cd "$COMPOSE_DIR"

echo "==> Validando docker-compose.yml..."
docker compose --profile core config --quiet
echo "  ✔ YAML válido."
echo "✔ 04 — docker-compose.yml pronto."
