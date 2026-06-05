#!/bin/bash
# 09-dbt-setup.sh — Instala dbt-core + dbt-clickhouse em virtualenv isolado
# Resolve o erro PEP 668 do Ubuntu 22.04+/24.04 (externally-managed-environment)
set -euo pipefail

POC_DIR="${POC_DIR:-$HOME/data-agent-poc}"
DBT_VENV="$POC_DIR/.venv/dbt"
DBT_DIR="$POC_DIR/dbt"

echo "==> Instalando python3-venv (necessário no Ubuntu 22.04+)..."
apt install -y python3-venv python3-full --quiet 2>/dev/null || true

echo "==> Criando virtualenv em $DBT_VENV..."
python3 -m venv "$DBT_VENV"
source "$DBT_VENV/bin/activate"
pip install --upgrade pip --quiet
pip install dbt-core dbt-clickhouse --quiet
dbt --version
echo "  ✔ dbt instalado no venv."

echo "==> Gerando ~/.dbt/profiles.yml..."
mkdir -p ~/.dbt
cat > ~/.dbt/profiles.yml << 'PROF'
poc_dw:
  target: dev
  outputs:
    dev:
      type: clickhouse
      host: localhost
      port: 8123
      user: poc_user
      password: click2024
      database: poc_dw
      schema: poc_dw
      secure: false
      connect_timeout: 10
      send_receive_timeout: 300
PROF
echo "  ✔ profiles.yml criado."

echo "==> Verificando dbt_project.yml..."
[ -f "$DBT_DIR/dbt_project.yml" ] && echo "  ✔ dbt_project.yml existe." || \
  echo "  WARN: dbt_project.yml não encontrado em $DBT_DIR"

echo "==> Testando conexão dbt..."
cd "$DBT_DIR"
dbt debug 2>&1 | grep -E "OK|FAIL|Connection|check" || true

# Alias permanente para ativar o venv facilmente
grep -q "alias dbt-poc" ~/.bashrc 2>/dev/null || \
  echo "alias dbt-poc='source $DBT_VENV/bin/activate && cd $DBT_DIR'" >> ~/.bashrc

echo ""
echo "  Para usar: source $DBT_VENV/bin/activate"
echo "  Atalho:    dbt-poc  (após abrir nova sessão SSH)"
echo "✔ 09 — dbt configurado."
