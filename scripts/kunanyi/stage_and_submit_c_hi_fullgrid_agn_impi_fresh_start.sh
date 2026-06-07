#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_TEMPLATE="${REMOTE_TEMPLATE:-${REMOTE_BASE}/jet_setup_production_template_latest.pbs}"
REMOTE_WRAPPER="${REMOTE_WRAPPER:-${REMOTE_BASE}/c_hi_fullgrid_agn_impi_fresh_start.pbs}"
REMOTE_WORKDIR="${REMOTE_WORKDIR:-/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles}"
REMOTE_CONFIG_DIR="${REMOTE_CONFIG_DIR:-${REMOTE_BASE}/c_hi_fullgrid_startup_2026-05-19/C-HI/particles}"
ALLOW_EXISTING_RUN_ROOT="${ALLOW_EXISTING_RUN_ROOT:-0}"

LOCAL_TEMPLATE="${LOCAL_TEMPLATE:-${ROOT}/scripts/kunanyi/jet_setup_production_template.pbs}"
LOCAL_WRAPPER="${LOCAL_WRAPPER:-${ROOT}/scripts/kunanyi/c_hi_fullgrid_agn_impi_fresh_start.pbs}"

# Home-network default. Override for campus direct or Nectar fallback:
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox TPAC_SCP_HOST=kunanyi ...
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar TPAC_SCP_HOST=kunanyi-via-nectar ...
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"
export TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"

if [ ! -f "${LOCAL_TEMPLATE}" ] || [ ! -f "${LOCAL_WRAPPER}" ]; then
  echo "Missing local PBS template or AGN fresh-start wrapper." >&2
  exit 2
fi

quote() {
  printf "%q" "$1"
}

cd "${ROOT}"

scripts/kunanyi/enable_jumpbox_ssh_safari.sh

echo "[stage] copying updated PBS template and AGN fresh-start wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_TEMPLATE}" "${REMOTE_TEMPLATE}"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_WRAPPER}" "${REMOTE_WRAPPER}"

REMOTE_CMD=$(cat <<'REMOTE'
set -euo pipefail
PROBLEM="${REMOTE_WORKDIR}/problem"
OUTPUTS="${PROBLEM}/outputs"

test -f "${REMOTE_TEMPLATE}"
test -f "${REMOTE_WRAPPER}"
test -f "${REMOTE_CONFIG_DIR}/pluto.ini"
test -f "${REMOTE_CONFIG_DIR}/environment.ini"
test -f "${REMOTE_CONFIG_DIR}/case_manifest.json"
test -f "${REMOTE_CONFIG_DIR}/definitions_overrides.json"

if [ "${ALLOW_EXISTING_RUN_ROOT}" != "1" ] && [ -d "${OUTPUTS}" ] && find "${OUTPUTS}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  echo "Refusing fresh start because ${OUTPUTS} already contains files. Set ALLOW_EXISTING_RUN_ROOT=1 to override." >&2
  exit 5
fi

module purge
module use /ds/projects/agn/modulefiles
ml intel impi hdf5/1.12.1p zfp/0.5.5
printf 'AGN_FRESH_MODULE_LIST_BEGIN\n'
module list 2>&1
printf 'AGN_FRESH_MODULE_LIST_END\n'
printf 'AGN_FRESH_MPICC=%s\n' "$(command -v mpicc)"
printf 'AGN_FRESH_MPIRUN=%s\n' "$(command -v mpirun)"
printf 'AGN_FRESH_HDF5_DIR=%s\n' "${HDF5_DIR:-}"
printf 'AGN_FRESH_REMOTE_WORKDIR=%s\n' "${REMOTE_WORKDIR}"
printf 'AGN_FRESH_REMOTE_CONFIG_DIR=%s\n' "${REMOTE_CONFIG_DIR}"
printf 'AGN_FRESH_HDF5_USE_FILE_LOCKING=FALSE\n'

job_id=$(qsub "${REMOTE_WRAPPER}")
echo SUBMITTED_JOB_ID=${job_id}
qstat -f "${job_id}" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|comment' || true
REMOTE
)

REMOTE_CMD="REMOTE_TEMPLATE=$(quote "$REMOTE_TEMPLATE")
REMOTE_WRAPPER=$(quote "$REMOTE_WRAPPER")
REMOTE_WORKDIR=$(quote "$REMOTE_WORKDIR")
REMOTE_CONFIG_DIR=$(quote "$REMOTE_CONFIG_DIR")
ALLOW_EXISTING_RUN_ROOT=$(quote "$ALLOW_EXISTING_RUN_ROOT")
${REMOTE_CMD}"

echo "[submit] validating fresh-run state and submitting ${REMOTE_WRAPPER}"
scripts/kunanyi/run_on_kunanyi.sh "${REMOTE_CMD}"
