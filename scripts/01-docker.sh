#!/bin/bash
# 01-docker.sh — Instala Docker CE + Compose plugin
# Compatível com Ubuntu 22.04 e 24.04
set -euo pipefail

echo "==> Removendo versões antigas..."
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

echo "==> Adicionando repositório oficial Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "==> Instalando Docker CE..."
apt update -qq
apt install -y -qq \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

systemctl enable docker --quiet
systemctl start docker

docker --version
docker compose version

echo "✔ 01 — Docker instalado."
