#!/usr/bin/env bash
set -euo pipefail
BASE=/home/bwbrook/work/pluto-onboarding/kh_instability
LOGS=$BASE/logs
mkdir -p "$LOGS"

"$BASE/scripts/run_kh_matrix.sh" 2>&1 | tee "$LOGS/run_matrix.log"
uv run --project /home/bwbrook/papers/xray_cavities python "$BASE/scripts/analyze_kh.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] KH workflow complete"
