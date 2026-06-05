#!/bin/bash
# 00-base-vps.sh — Configuração base: pacotes, UFW, fail2ban
set -euo pipefail

echo "==> Atualizando sistema..."
apt update -qq
apt upgrade -y -qq

echo "==> Instalando pacotes base..."
apt install -y -qq \
  curl git unzip vim htop ufw fail2ban \
  python3 python3-venv python3-full \
  ca-certificates gnupg lsb-release

echo "==> Configurando UFW..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   comment "SSH"
ufw allow 80/tcp   comment "HTTP"
ufw allow 443/tcp  comment "HTTPS"
ufw allow 8080/tcp comment "Airflow UI"
ufw allow 9001/tcp comment "MinIO Console"
ufw allow 8123/tcp comment "ClickHouse HTTP"
ufw allow 8000/tcp comment "FastAPI"
ufw --force enable
ufw status

echo "==> Configurando fail2ban..."
systemctl enable fail2ban --quiet
systemctl start fail2ban

echo "✔ 00 — Base VPS configurada."
