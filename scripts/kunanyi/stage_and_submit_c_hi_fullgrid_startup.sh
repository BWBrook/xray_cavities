#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

LOCAL_CONFIG_DIR="${LOCAL_CONFIG_DIR:-${ROOT}/build/science/c_hi_fullgrid_startup_2026-05-19}"
REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_CONFIG_DIR="${REMOTE_CONFIG_DIR:-${REMOTE_BASE}/c_hi_fullgrid_startup_2026-05-19}"
REMOTE_TEMPLATE="${REMOTE_TEMPLATE:-${REMOTE_BASE}/jet_setup_production_template_latest.pbs}"
REMOTE_WRAPPER="${REMOTE_WRAPPER:-${REMOTE_BASE}/c_hi_fullgrid_startup_checkpoint.pbs}"

LOCAL_TEMPLATE="${LOCAL_TEMPLATE:-${ROOT}/scripts/kunanyi/jet_setup_production_template.pbs}"
LOCAL_WRAPPER="${LOCAL_WRAPPER:-${ROOT}/scripts/kunanyi/c_hi_fullgrid_startup_checkpoint.pbs}"

if [ ! -f "${LOCAL_CONFIG_DIR}/C-HI/particles/pluto.ini" ]; then
  cat >&2 <<EOF
Missing rendered config bundle:
  ${LOCAL_CONFIG_DIR}

Render it first with:
  uv run python scripts/science/render_three_case_configs.py \\
    --variant particles --case C-HI --grid stewart_stretched_250 \\
    --duration-myr 50 --snapshot-interval-myr 1 --dbl-h5-interval-myr 5 \\
    --particle-interval-myr 0.01 --particles-per-injection 32 \\
    --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \\
    --check-local-assets --output build/science/c_hi_fullgrid_startup_2026-05-19 --force
EOF
  exit 2
fi

if [ ! -f "${LOCAL_TEMPLATE}" ] || [ ! -f "${LOCAL_WRAPPER}" ]; then
  echo "Missing local PBS template or wrapper." >&2
  exit 2
fi

# Default to the direct MacBook jumpbox route. If the direct route is not
# reachable, callers can override both aliases, for example:
#
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar \
#   TPAC_SCP_HOST=kunanyi-via-nectar \
#   scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox}"
export TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi}"

cd "${ROOT}"

scripts/kunanyi/enable_jumpbox_ssh_safari.sh

echo "[stage] preparing remote directory ${REMOTE_CONFIG_DIR}"
scripts/kunanyi/run_on_kunanyi.sh \
  "set -euo pipefail; mkdir -p '${REMOTE_BASE}'; rm -rf '${REMOTE_CONFIG_DIR}'"

echo "[stage] copying full-grid config bundle"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_CONFIG_DIR}" "${REMOTE_BASE}/"

echo "[stage] copying PBS template and wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_TEMPLATE}" "${REMOTE_TEMPLATE}"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_WRAPPER}" "${REMOTE_WRAPPER}"

echo "[submit] submitting ${REMOTE_WRAPPER}"
scripts/kunanyi/run_on_kunanyi.sh "set -euo pipefail
test -f '${REMOTE_CONFIG_DIR}/C-HI/particles/pluto.ini'
test -f '${REMOTE_CONFIG_DIR}/C-HI/particles/render_validation.json'
test -f '${REMOTE_TEMPLATE}'
test -f '${REMOTE_WRAPPER}'
grep -q 'Nparticles[[:space:]]*-1[[:space:]]*32.0' '${REMOTE_CONFIG_DIR}/C-HI/particles/pluto.ini'
python3 - <<'PY'
import json
from pathlib import Path
p = Path('${REMOTE_CONFIG_DIR}/C-HI/particles/render_validation.json')
data = json.loads(p.read_text())
if not data.get('ok'):
    raise SystemExit('render_validation.json is not ok')
print('REMOTE_RENDER_VALIDATION_OK=1')
print('NPARTICLES=' + data['checks']['Nparticles_second_field']['rendered'])
PY
job_id=\$(qsub '${REMOTE_WRAPPER}')
echo SUBMITTED_JOB_ID=\${job_id}
qstat -f \"\${job_id}\" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|comment' || true"
