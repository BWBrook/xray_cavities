#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_TEMPLATE="${REMOTE_TEMPLATE:-${REMOTE_BASE}/jet_setup_production_template_latest.pbs}"
REMOTE_WRAPPER="${REMOTE_WRAPPER:-${REMOTE_BASE}/c_hi_fullgrid_continue.pbs}"
REMOTE_WORKDIR="${REMOTE_WORKDIR:-/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles}"
MIN_RESTART_INDEX="${MIN_RESTART_INDEX:-0}"

LOCAL_TEMPLATE="${LOCAL_TEMPLATE:-${ROOT}/scripts/kunanyi/jet_setup_production_template.pbs}"
LOCAL_WRAPPER="${LOCAL_WRAPPER:-${ROOT}/scripts/kunanyi/c_hi_fullgrid_continue.pbs}"

# Home-network default. Override for campus direct or Nectar fallback:
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox TPAC_SCP_HOST=kunanyi ...
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar TPAC_SCP_HOST=kunanyi-via-nectar ...
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"
export TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"

if [ ! -f "${LOCAL_TEMPLATE}" ] || [ ! -f "${LOCAL_WRAPPER}" ]; then
  echo "Missing local PBS template or continuation wrapper." >&2
  exit 2
fi

quote() {
  printf "%q" "$1"
}

cd "${ROOT}"

scripts/kunanyi/enable_jumpbox_ssh_safari.sh

echo "[stage] copying updated PBS template and continuation wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_TEMPLATE}" "${REMOTE_TEMPLATE}"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_WRAPPER}" "${REMOTE_WRAPPER}"

REMOTE_CMD=$(cat <<'REMOTE'
set -euo pipefail
PROBLEM="${REMOTE_WORKDIR}/problem"
OUTPUTS="${PROBLEM}/outputs"
MARKERS="${REMOTE_WORKDIR}/markers"

test -f "${REMOTE_TEMPLATE}"
test -f "${REMOTE_WRAPPER}"
test -x "${PROBLEM}/pluto"
test -f "${OUTPUTS}/dbl.h5.out"

latest=$(awk 'NF && $1 ~ /^[0-9]+$/ {n=$1} END{if (n != "") print n}' "${OUTPUTS}/dbl.h5.out")
if [ -z "${latest:-}" ]; then
  echo "No numeric restart entries in ${OUTPUTS}/dbl.h5.out" >&2
  exit 3
fi
if [ "${latest}" -lt "${MIN_RESTART_INDEX}" ]; then
  echo "Latest restart index ${latest} is below MIN_RESTART_INDEX=${MIN_RESTART_INDEX}" >&2
  exit 4
fi
restart_file=$(printf "%s/data.%04d.dbl.h5" "${OUTPUTS}" "${latest}")
test -f "${restart_file}"

mkdir -p "${MARKERS}/history"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
for marker in DONE FAILED; do
  if [ -f "${MARKERS}/${marker}" ]; then
    cp -p "${MARKERS}/${marker}" "${MARKERS}/history/${marker}.${stamp}.before_submit"
    rm -f "${MARKERS:?}/${marker}"
  fi
done

printf 'CONTINUE_REMOTE_WORKDIR=%s\n' "${REMOTE_WORKDIR}"
printf 'CONTINUE_RESTART_INDEX=%s\n' "${latest}"
printf 'CONTINUE_RESTART_FILE=%s\n' "${restart_file}"
printf 'CONTINUE_DBL_H5_TAIL=\n'
tail -n 8 "${OUTPUTS}/dbl.h5.out"

job_id=$(qsub "${REMOTE_WRAPPER}")
echo SUBMITTED_JOB_ID=${job_id}
qstat -f "${job_id}" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|comment' || true
REMOTE
)

REMOTE_CMD="REMOTE_TEMPLATE=$(quote "$REMOTE_TEMPLATE")
REMOTE_WRAPPER=$(quote "$REMOTE_WRAPPER")
REMOTE_WORKDIR=$(quote "$REMOTE_WORKDIR")
MIN_RESTART_INDEX=$(quote "$MIN_RESTART_INDEX")
${REMOTE_CMD}"

echo "[submit] validating restart state and submitting ${REMOTE_WRAPPER}"
scripts/kunanyi/run_on_kunanyi.sh "${REMOTE_CMD}"
