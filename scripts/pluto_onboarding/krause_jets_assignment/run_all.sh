#!/usr/bin/env bash
set -euo pipefail
BASE=/home/bwbrook/work/pluto-onboarding/krause_jets_assignment
LOGS=$BASE/logs
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$LOGS"

"$BASE/scripts/run_krause_assignment.sh" 2>&1 | tee "$LOGS/run_krause_assignment.log"
uv run --project /home/bwbrook/papers/xray_cavities python "$BASE/scripts/analyze_krause_assignment.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] Krause-style jet assignment workflow complete"
