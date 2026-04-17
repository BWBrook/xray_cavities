#!/usr/bin/env bash
set -euo pipefail
BASE=/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep
LOGS=$BASE/logs
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$LOGS"

"$BASE/scripts/run_parameter_sweep.sh" 2>&1 | tee "$LOGS/run_parameter_sweep.log"
uv run --project /home/bwbrook/papers/xray_cavities python "$BASE/scripts/analyze_parameter_sweep.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] jet parameter sweep workflow complete"
