#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE=${OFFICIAL_JET_ASSIGNMENT_BASE:-"$HOME/work/pluto-onboarding/official_jet_assignment"}
PROJECT=${XRAY_CAVITIES_PROJECT:-"$HOME/papers/xray_cavities"}
LOGS="$BASE/logs"

mkdir -p "$LOGS"

"$SCRIPT_DIR/run_official_jet_assignment.sh" 2>&1 | tee "$LOGS/run_official_jet_assignment.log"
uv run --project "$PROJECT" python "$SCRIPT_DIR/analyze_official_jet_assignment.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] official jet assignment workflow complete"
