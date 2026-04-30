#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE=${JET_SETUP_TINY_3D_BASE:-"$HOME/work/pluto-onboarding/jet_setup_tiny_3d_cart"}
PROJECT=${XRAY_CAVITIES_PROJECT:-"$HOME/papers/xray_cavities"}
LOGS="$BASE/logs"

mkdir -p "$LOGS"

"$SCRIPT_DIR/run_tiny_3d_cart.sh" 2>&1 | tee "$LOGS/run_tiny_3d_cart.log"
uv run --project "$PROJECT" python "$SCRIPT_DIR/analyze_tiny_3d_cart.py" 2>&1 | tee "$LOGS/analyze.log"

echo "[done] tiny 3D Cartesian jet-setup workflow complete"
