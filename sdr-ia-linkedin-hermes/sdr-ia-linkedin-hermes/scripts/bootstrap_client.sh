#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 1 ]; then
  echo "Usage: scripts/bootstrap_client.sh 'Nom Client'" >&2
  exit 1
fi
CLIENT_NAME="$1"
SLUG=$(echo "$CLIENT_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g')
CONFIG="configs/clients/${SLUG}.yaml"
sdr-ai init-client --name "$CLIENT_NAME" --out "$CONFIG"
cp hermes/templates/MEMORY.template.md "configs/clients/${SLUG}.MEMORY.md"
echo "[NEXT] Edite $CONFIG avec ICP/OFFRE/secrets, puis:"
echo "sdr-ai setup-crm --config $CONFIG"
echo "sdr-ai install-hermes --config $CONFIG --create-cron"
