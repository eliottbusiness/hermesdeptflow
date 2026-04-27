#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
echo "[OK] SDR IA installe. Active avec: source .venv/bin/activate"
