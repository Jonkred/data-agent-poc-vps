#!/bin/bash
# setup.sh — Orquestrador POC Data Agent VPS
# Idempotente: verifica cada etapa antes de executar
# Uso: bash setup.sh
#
# Variáveis de ambiente:
#   POC_DIR    — destino do projeto (padrão: $HOME/data-agent-poc)
#   SKIP_STEPS — lista separada por vírgula de etapas a pular (ex: "00,01")

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$REPO_DIR/scripts"
export POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
export COMPOSE_DIR="$POC_DIR/infra/compose-core"
export REPO_DIR

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✔ $*${NC}"; }
skip() { echo -e "${YELLOW}  ↷ $* — já feito, pulando.${NC}"; }
fail() { echo -e "${RED}  ✘ ERRO: $*${NC}"; exit 1; }
head() { echo -e "\n${CYAN}══ $* ══${NC}"; }

step() {
  local num="$1" label="$2" check="$3" script="$4"
  head "$num — $label"
  # Permite pular etapas via SKIP_STEPS="00,01"
  if [[ "${SKIP_STEPS:-}" == *"$num"* ]]; then
    skip "$label (forçado via SKIP_STEPS)"
    return 0
  fi
  if bash -c "$check" > /dev/null 2>&1; then
    skip "$label"
  else
    bash "$SCRIPTS_DIR/$script" || fail "Etapa $num falhou. Verifique o log acima."
    ok "$label concluído."
  fi
}

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║   POC Data Agent VPS — Setup Completo     ║"
echo "║   Destino: $POC_DIR"
echo "╚═══════════════════════════════════════════╝"
echo "  Repo:   $REPO_DIR"
echo "  Início: $(date '+%Y-%m-%d %H:%M:%S')"

step "00" "Base VPS (UFW, pacotes)"  \
  "ufw status 2>/dev/null | grep -q 'Status: active'"  \
  "00-base-vps.sh"

step "01" "Docker CE"  \
  "docker compose version > /dev/null 2>&1"  \
  "01-docker.sh"

step "02" "Swap 8 GB (swappiness=10)"  \
  "swapon --show 2>/dev/null | grep -q swap"  \
  "02-swap.sh"

step "03" "Estrutura do projeto e .env"  \
  "[ -f '$COMPOSE_DIR/.env' ]"  \
  "03-structure.sh"

step "04" "docker-compose.yml"  \
  "[ -f '$COMPOSE_DIR/docker-compose.yml' ]"  \
  "04-compose.sh"

step "05" "Subir stack core"  \
  "docker compose -f '$COMPOSE_DIR/docker-compose.yml' --profile core ps 2>/dev/null | grep -q 'healthy'"  \
  "05-run-stack.sh"

step "07" "MinIO — buckets"  \
  "docker run --rm --network compose-core_poc-net --entrypoint sh minio/mc:latest \
    -c 'mc alias set l http://minio:9000 minioadmin minio2024 --quiet 2>/dev/null && mc ls l 2>/dev/null' \
    2>/dev/null | grep -q 'raw'"  \
  "07-minio-buckets.sh"

step "08" "ClickHouse — tabelas de controle"  \
  "docker compose -f '$COMPOSE_DIR/docker-compose.yml' exec -T clickhouse \
    clickhouse-client --user=poc_user --password=click2024 \
    --query 'EXISTS TABLE poc_dw.ingestion_control FORMAT TabSeparated' \
    2>/dev/null | grep -q '^1'"  \
  "08-clickhouse-init.sh"

step "09" "dbt (venv + adapter ClickHouse)"  \
  "[ -f '$POC_DIR/.venv/dbt/bin/dbt' ]"  \
  "09-dbt-setup.sh"

step "10" "Validação Sprint 1"  \
  "false"  \
  "10-validate.sh"

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║   Setup concluído!                        ║"
echo "║   Airflow  → http://IP:8080               ║"
echo "║   MinIO    → http://IP:9001               ║"
echo "║   FastAPI  → http://IP:8000/docs          ║"
echo "╚═══════════════════════════════════════════╝"
echo "  Fim: $(date '+%Y-%m-%d %H:%M:%S')"
