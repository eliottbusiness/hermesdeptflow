#!/usr/bin/env bash
set -euo pipefail
if ! command -v hermes >/dev/null 2>&1; then
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
fi
hermes doctor || true
echo "[OK] Hermes disponible. Lance 'hermes setup' si necessaire."
