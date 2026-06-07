#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_TEMPLATE="${REMOTE_TEMPLATE:-${REMOTE_BASE}/jet_setup_production_template_latest.pbs}"
REMOTE_WRAPPER="${REMOTE_WRAPPER:-${REMOTE_BASE}/c_hi_fullgrid_agn_impi_80node_restart_probe.pbs}"
REMOTE_WORKDIR="${REMOTE_WORKDIR:-/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles}"
REMOTE_CONFIG_DIR="${REMOTE_CONFIG_DIR:-${REMOTE_BASE}/c_hi_fullgrid_startup_2026-05-19/C-HI/particles}"
EXPECTED_RESTART_INDEX="${EXPECTED_RESTART_INDEX:-9}"
ENABLE_JUMPBOX_SSH_URL="${ENABLE_JUMPBOX_SSH_URL:-https://<tpac-host>/pun/sys/enable_ssh/}"
TPAC_ENABLE_BROWSER="${TPAC_ENABLE_BROWSER:-Google Chrome}"
TPAC_ENABLE_WAIT_SECONDS="${TPAC_ENABLE_WAIT_SECONDS:-12}"

LOCAL_TEMPLATE="${LOCAL_TEMPLATE:-${ROOT}/scripts/kunanyi/jet_setup_production_template.pbs}"
LOCAL_WRAPPER="${LOCAL_WRAPPER:-${ROOT}/scripts/kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.pbs}"

# Home-network default. Override for campus direct or Nectar fallback:
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox TPAC_SCP_HOST=kunanyi ...
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar TPAC_SCP_HOST=kunanyi-via-nectar ...
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"
export TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"

if [ ! -f "${LOCAL_TEMPLATE}" ] || [ ! -f "${LOCAL_WRAPPER}" ]; then
  echo "Missing local PBS template or AGN 80-node restart-probe wrapper." >&2
  exit 2
fi

quote() {
  printf "%q" "$1"
}

cd "${ROOT}"

open -a "${TPAC_ENABLE_BROWSER}" "${ENABLE_JUMPBOX_SSH_URL}"
sleep "${TPAC_ENABLE_WAIT_SECONDS}"

echo "[stage] copying updated PBS template and AGN 80-node restart-probe wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_TEMPLATE}" "${REMOTE_TEMPLATE}"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_WRAPPER}" "${REMOTE_WRAPPER}"

REMOTE_CMD=$(cat <<'REMOTE'
set -euo pipefail
PROBLEM="${REMOTE_WORKDIR}/problem"
OUTPUTS="${PROBLEM}/outputs"
MARKERS="${REMOTE_WORKDIR}/markers"

test -f "${REMOTE_TEMPLATE}"
test -f "${REMOTE_WRAPPER}"
test -f "${REMOTE_CONFIG_DIR}/pluto.ini"
test -f "${REMOTE_CONFIG_DIR}/environment.ini"
test -f "${REMOTE_CONFIG_DIR}/case_manifest.json"
test -f "${REMOTE_CONFIG_DIR}/definitions_overrides.json"
test -x "${PROBLEM}/pluto"
test -f "${OUTPUTS}/dbl.h5.out"
test -f "${OUTPUTS}/flt.h5.out"
test -f "${OUTPUTS}/restart.out"
test -f "${OUTPUTS}/particles.4277.dbl"

module purge
module use /ds/projects/agn/modulefiles
ml intel impi hdf5/1.12.1p zfp/0.5.5
printf 'AGN_RESTART_PROBE_MODULE_LIST_BEGIN\n'
module list 2>&1
printf 'AGN_RESTART_PROBE_MODULE_LIST_END\n'
printf 'AGN_RESTART_PROBE_MPICC=%s\n' "$(command -v mpicc)"
printf 'AGN_RESTART_PROBE_MPIRUN=%s\n' "$(command -v mpirun)"
printf 'AGN_RESTART_PROBE_HDF5_DIR=%s\n' "${HDF5_DIR:-}"
printf 'AGN_RESTART_PROBE_HDF5_USE_FILE_LOCKING=FALSE\n'

latest=$(awk 'NF && $1 ~ /^[0-9]+$/ {n=$1} END{if (n != "") print n}' "${OUTPUTS}/dbl.h5.out")
if [ -z "${latest:-}" ]; then
  echo "No numeric restart entries in ${OUTPUTS}/dbl.h5.out" >&2
  exit 3
fi
if [ "${latest}" -ne "${EXPECTED_RESTART_INDEX}" ]; then
  echo "Latest restart index ${latest} does not equal EXPECTED_RESTART_INDEX=${EXPECTED_RESTART_INDEX}" >&2
  exit 4
fi
restart_file=$(printf "%s/data.%04d.dbl.h5" "${OUTPUTS}" "${latest}")
test -f "${restart_file}"

if command -v h5dump >/dev/null 2>&1; then
  h5dump -d "/Timestep_${latest}/vars/rho" -s 0,0,0 -c 1,1,1 "${restart_file}" >/dev/null
fi

mkdir -p "${MARKERS}/history"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
for marker in DONE FAILED; do
  if [ -f "${MARKERS}/${marker}" ]; then
    cp -p "${MARKERS}/${marker}" "${MARKERS}/history/${marker}.${stamp}.before_agn_80node_restart_probe"
    rm -f "${MARKERS:?}/${marker}"
  fi
done

printf 'AGN_RESTART_PROBE_REMOTE_WORKDIR=%s\n' "${REMOTE_WORKDIR}"
printf 'AGN_RESTART_PROBE_REMOTE_CONFIG_DIR=%s\n' "${REMOTE_CONFIG_DIR}"
printf 'AGN_RESTART_PROBE_RESTART_INDEX=%s\n' "${latest}"
printf 'AGN_RESTART_PROBE_RESTART_FILE=%s\n' "${restart_file}"
printf 'AGN_RESTART_PROBE_DBL_H5_TAIL=\n'
tail -n 5 "${OUTPUTS}/dbl.h5.out"
printf 'AGN_RESTART_PROBE_FLT_H5_TAIL=\n'
tail -n 5 "${OUTPUTS}/flt.h5.out"

job_id=$(qsub "${REMOTE_WRAPPER}")
echo SUBMITTED_JOB_ID=${job_id}
qstat -f "${job_id}" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|comment' || true
REMOTE
)

REMOTE_CMD="REMOTE_TEMPLATE=$(quote "$REMOTE_TEMPLATE")
REMOTE_WRAPPER=$(quote "$REMOTE_WRAPPER")
REMOTE_WORKDIR=$(quote "$REMOTE_WORKDIR")
REMOTE_CONFIG_DIR=$(quote "$REMOTE_CONFIG_DIR")
EXPECTED_RESTART_INDEX=$(quote "$EXPECTED_RESTART_INDEX")
${REMOTE_CMD}"

echo "[submit] validating restart state and submitting ${REMOTE_WRAPPER}"
scripts/kunanyi/run_on_kunanyi.sh "${REMOTE_CMD}"
