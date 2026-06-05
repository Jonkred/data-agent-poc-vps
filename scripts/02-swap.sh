#!/bin/bash
# 02-swap.sh — Cria swap de 8 GB com swappiness=10
set -euo pipefail

SWAP_FILE="/swap"
SWAP_SIZE="8G"

if swapon --show | grep -q "$SWAP_FILE"; then
  echo "  Swap já existe. Nada a fazer."
  exit 0
fi

echo "==> Criando swap de $SWAP_SIZE em $SWAP_FILE..."
fallocate -l "$SWAP_SIZE" "$SWAP_FILE"
chmod 600 "$SWAP_FILE"
mkswap "$SWAP_FILE"
swapon "$SWAP_FILE"

grep -q "$SWAP_FILE" /etc/fstab || \
  echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab

echo "==> Configurando swappiness=10..."
sysctl -w vm.swappiness=10
echo "vm.swappiness=10" > /etc/sysctl.d/99-swappiness.conf

echo "  Swap: $(swapon --show | tail -1)"
echo "✔ 02 — Swap configurado."
