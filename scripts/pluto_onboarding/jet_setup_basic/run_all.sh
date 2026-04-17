#!/usr/bin/env bash
set -euo pipefail
BASE=/home/bwbrook/work/pluto-onboarding/jet_setup_basic
LOGS=$BASE/logs
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$LOGS"

"$BASE/scripts/run_basic_jet.sh" 2>&1 | tee "$LOGS/run_basic_jet.log"
uv run --project /home/bwbrook/papers/xray_cavities python "$BASE/scripts/analyze_basic_jet.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] jet-setup basic workflow complete"
