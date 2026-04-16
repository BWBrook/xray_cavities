#!/usr/bin/env bash
set -euo pipefail
BASE=/home/bwbrook/work/pluto-onboarding/rt_instability
LOGS=$BASE/logs
mkdir -p "$LOGS"

"$BASE/scripts/run_rt_matrix.sh" 2>&1 | tee "$LOGS/run_matrix.log"
uv run --project /home/bwbrook/papers/xray_cavities python "$BASE/scripts/analyze_rt.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] RT workflow complete"
