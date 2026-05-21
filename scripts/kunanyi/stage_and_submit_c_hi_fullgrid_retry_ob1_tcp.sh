#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_TEMPLATE="${REMOTE_TEMPLATE:-${REMOTE_BASE}/jet_setup_production_template_latest.pbs}"
REMOTE_WRAPPER="${REMOTE_WRAPPER:-${REMOTE_BASE}/c_hi_fullgrid_startup_retry_ob1_tcp.pbs}"
REMOTE_WORKDIR="${REMOTE_WORKDIR:-/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles}"

LOCAL_TEMPLATE="${LOCAL_TEMPLATE:-${ROOT}/scripts/kunanyi/jet_setup_production_template.pbs}"
LOCAL_WRAPPER="${LOCAL_WRAPPER:-${ROOT}/scripts/kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.pbs}"

if [ ! -f "${LOCAL_TEMPLATE}" ] || [ ! -f "${LOCAL_WRAPPER}" ]; then
  echo "Missing local PBS template or retry wrapper." >&2
  exit 2
fi

cd "${ROOT}"

echo "[stage] copying updated PBS template and retry wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_TEMPLATE}" "${REMOTE_TEMPLATE}"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_WRAPPER}" "${REMOTE_WRAPPER}"

echo "[submit] submitting ${REMOTE_WRAPPER}"
scripts/kunanyi/run_on_kunanyi.sh "set -euo pipefail
test -f '${REMOTE_TEMPLATE}'
test -f '${REMOTE_WRAPPER}'
test -f '${REMOTE_WORKDIR}/problem/outputs/dbl.h5.out'
test -f '${REMOTE_WORKDIR}/problem/outputs/data.0000.dbl.h5'
test -f '${REMOTE_WORKDIR}/problem/pluto'
grep -q 'RESTART_POLICY=.*auto' '${REMOTE_WRAPPER}'
grep -q 'OMPI_MCA_pml' '${REMOTE_WRAPPER}'
printf 'RETRY_REMOTE_WORKDIR=%s\n' '${REMOTE_WORKDIR}'
printf 'RETRY_OUTPUT_HEAD=\n'
tail -n 5 '${REMOTE_WORKDIR}/problem/outputs/dbl.h5.out'
job_id=\$(qsub '${REMOTE_WRAPPER}')
echo SUBMITTED_JOB_ID=\${job_id}
qstat -f \"\${job_id}\" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|comment' || true"
