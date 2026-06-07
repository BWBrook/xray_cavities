#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

LADDER_NODES="${LADDER_NODES:-8}"
LADDER_NCPUS_PER_NODE="${LADDER_NCPUS_PER_NODE:-28}"
LADDER_MPIPROCS_PER_NODE="${LADDER_MPIPROCS_PER_NODE:-28}"
LADDER_WALLTIME="${LADDER_WALLTIME:-02:00:00}"
PLUTO_MAXTIME_HOURS="${PLUTO_MAXTIME_HOURS:-0.5}"

REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_TEMPLATE="${REMOTE_TEMPLATE:-${REMOTE_BASE}/jet_setup_production_template_latest.pbs}"
REMOTE_WRAPPER="${REMOTE_WRAPPER:-${REMOTE_BASE}/c_hi_fullgrid_agn_impi_restart_ladder.pbs}"
REMOTE_CONFIG_DIR="${REMOTE_CONFIG_DIR:-${REMOTE_BASE}/c_hi_fullgrid_startup_2026-05-19/C-HI/particles}"
SOURCE_WORKDIR="${SOURCE_WORKDIR:-/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles}"
EXPECTED_RESTART_INDEX="${EXPECTED_RESTART_INDEX:-9}"
EXPECTED_PARTICLE_INDEX="${EXPECTED_PARTICLE_INDEX:-4277}"
ENABLE_JUMPBOX_SSH_URL="${ENABLE_JUMPBOX_SSH_URL:-https://<tpac-host>/pun/sys/enable_ssh/}"
TPAC_ENABLE_BROWSER="${TPAC_ENABLE_BROWSER:-Google Chrome}"
TPAC_ENABLE_WAIT_SECONDS="${TPAC_ENABLE_WAIT_SECONDS:-12}"
ALLOW_LADDER_RERUN="${ALLOW_LADDER_RERUN:-0}"

LOCAL_TEMPLATE="${LOCAL_TEMPLATE:-${ROOT}/scripts/kunanyi/jet_setup_production_template.pbs}"
LOCAL_WRAPPER="${LOCAL_WRAPPER:-${ROOT}/scripts/kunanyi/c_hi_fullgrid_agn_impi_restart_ladder.pbs}"

# Home-network default. Override for campus direct or Nectar fallback:
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox TPAC_SCP_HOST=kunanyi ...
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar TPAC_SCP_HOST=kunanyi-via-nectar ...
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"
export TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"

case "${LADDER_NODES}" in
  ''|*[!0-9]*)
    echo "LADDER_NODES must be a positive integer, got: ${LADDER_NODES}" >&2
    exit 2
    ;;
esac
if [ "${LADDER_NODES}" -le 0 ]; then
  echo "LADDER_NODES must be positive, got: ${LADDER_NODES}" >&2
  exit 2
fi

if [ ! -f "${LOCAL_TEMPLATE}" ] || [ ! -f "${LOCAL_WRAPPER}" ]; then
  echo "Missing local PBS template or AGN restart-ladder wrapper." >&2
  exit 2
fi

node_suffix=$(printf "%02dnode" "${LADDER_NODES}")
job_name="${JOB_NAME_OVERRIDE:-$(printf "c_hi_r9_%02dn" "${LADDER_NODES}")}"
remote_run_root="${REMOTE_RUN_ROOT:-/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-${node_suffix}}"
remote_stdout="${REMOTE_STDOUT:-${REMOTE_BASE}/c_hi_fullgrid_agn_impi_r9_ladder_${node_suffix}.out}"
remote_stderr="${REMOTE_STDERR:-${REMOTE_BASE}/c_hi_fullgrid_agn_impi_r9_ladder_${node_suffix}.err}"

quote() {
  printf "%q" "$1"
}

cd "${ROOT}"

open -a "${TPAC_ENABLE_BROWSER}" "${ENABLE_JUMPBOX_SSH_URL}"
sleep "${TPAC_ENABLE_WAIT_SECONDS}"

echo "[stage] copying updated PBS template and AGN restart-ladder wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_TEMPLATE}" "${REMOTE_TEMPLATE}"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_WRAPPER}" "${REMOTE_WRAPPER}"

REMOTE_CMD=$(cat <<'REMOTE'
set -euo pipefail
SOURCE_PROBLEM="${SOURCE_WORKDIR}/problem"
SOURCE_OUTPUTS="${SOURCE_PROBLEM}/outputs"
REMOTE_WORKDIR="${REMOTE_RUN_ROOT}/C-HI/particles"
PROBLEM="${REMOTE_WORKDIR}/problem"
OUTPUTS="${PROBLEM}/outputs"
MARKERS="${REMOTE_WORKDIR}/markers"
LOG_DIR="${REMOTE_WORKDIR}/job_logs"

test -f "${REMOTE_TEMPLATE}"
test -f "${REMOTE_WRAPPER}"
test -f "${REMOTE_CONFIG_DIR}/pluto.ini"
test -f "${REMOTE_CONFIG_DIR}/environment.ini"
test -f "${REMOTE_CONFIG_DIR}/case_manifest.json"
test -f "${REMOTE_CONFIG_DIR}/definitions_overrides.json"
test -x "${SOURCE_PROBLEM}/pluto"
test -f "${SOURCE_OUTPUTS}/dbl.h5.out"
test -f "${SOURCE_OUTPUTS}/flt.h5.out"
test -f "${SOURCE_OUTPUTS}/restart.out"

latest=$(awk 'NF && $1 ~ /^[0-9]+$/ {n=$1} END{if (n != "") print n}' "${SOURCE_OUTPUTS}/dbl.h5.out")
if [ -z "${latest:-}" ]; then
  echo "No numeric restart entries in ${SOURCE_OUTPUTS}/dbl.h5.out" >&2
  exit 3
fi
if [ "${latest}" -ne "${EXPECTED_RESTART_INDEX}" ]; then
  echo "Latest source restart index ${latest} does not equal EXPECTED_RESTART_INDEX=${EXPECTED_RESTART_INDEX}" >&2
  exit 4
fi

restart_file=$(printf "%s/data.%04d.dbl.h5" "${SOURCE_OUTPUTS}" "${latest}")
particle_file=$(printf "%s/particles.%04d.dbl" "${SOURCE_OUTPUTS}" "${EXPECTED_PARTICLE_INDEX}")
test -f "${restart_file}"
test -f "${particle_file}"

if [ -e "${REMOTE_WORKDIR}" ] && [ "${ALLOW_LADDER_RERUN}" != "1" ]; then
  echo "Remote ladder workdir already exists: ${REMOTE_WORKDIR}" >&2
  echo "Set ALLOW_LADDER_RERUN=1 to rebuild this rung workdir." >&2
  exit 5
fi
if [ -e "${REMOTE_WORKDIR}" ]; then
  rm -rf "${REMOTE_WORKDIR}"
fi
mkdir -p "${OUTPUTS}/logs" "${MARKERS}" "${LOG_DIR}"

cp -p "${SOURCE_PROBLEM}/pluto" "${PROBLEM}/pluto"
chmod +x "${PROBLEM}/pluto"
cp -p "${REMOTE_CONFIG_DIR}/pluto.ini" "${PROBLEM}/pluto.ini"
cp -p "${REMOTE_CONFIG_DIR}/environment.ini" "${PROBLEM}/environment.ini"
cp -p "${REMOTE_CONFIG_DIR}/case_manifest.json" "${PROBLEM}/case_manifest.json"
cp -p "${REMOTE_CONFIG_DIR}/definitions_overrides.json" "${PROBLEM}/definitions_overrides.json"
cp -p "${REMOTE_CONFIG_DIR}"/*.csv "${PROBLEM}/" 2>/dev/null || true
cp -p "${REMOTE_CONFIG_DIR}"/*.dbl "${PROBLEM}/" 2>/dev/null || true
cp -p "${REMOTE_CONFIG_DIR}"/*.grid.out "${PROBLEM}/" 2>/dev/null || true
cp -p "${SOURCE_OUTPUTS}/dbl.h5.out" "${OUTPUTS}/dbl.h5.out"
cp -p "${SOURCE_OUTPUTS}/flt.h5.out" "${OUTPUTS}/flt.h5.out"
cp -p "${SOURCE_OUTPUTS}/restart.out" "${OUTPUTS}/restart.out"
ln -s "${restart_file}" "$(printf "%s/data.%04d.dbl.h5" "${OUTPUTS}" "${latest}")"
if [ -f "$(printf "%s/data.%04d.dbl.xmf" "${SOURCE_OUTPUTS}" "${latest}")" ]; then
  ln -s "$(printf "%s/data.%04d.dbl.xmf" "${SOURCE_OUTPUTS}" "${latest}")" \
    "$(printf "%s/data.%04d.dbl.xmf" "${OUTPUTS}" "${latest}")"
fi
ln -s "${particle_file}" "$(printf "%s/particles.%04d.dbl" "${OUTPUTS}" "${EXPECTED_PARTICLE_INDEX}")"

module purge
module use /ds/projects/agn/modulefiles
ml intel impi hdf5/1.12.1p zfp/0.5.5
printf 'AGN_RESTART_LADDER_MODULE_LIST_BEGIN\n'
module list 2>&1
printf 'AGN_RESTART_LADDER_MODULE_LIST_END\n'
printf 'AGN_RESTART_LADDER_NODES=%s\n' "${LADDER_NODES}"
printf 'AGN_RESTART_LADDER_SELECT=%s:ncpus=%s:mpiprocs=%s\n' "${LADDER_NODES}" "${LADDER_NCPUS_PER_NODE}" "${LADDER_MPIPROCS_PER_NODE}"
printf 'AGN_RESTART_LADDER_WALLTIME=%s\n' "${LADDER_WALLTIME}"
printf 'AGN_RESTART_LADDER_PLUTO_MAXTIME_HOURS=%s\n' "${PLUTO_MAXTIME_HOURS}"
printf 'AGN_RESTART_LADDER_MPICC=%s\n' "$(command -v mpicc)"
printf 'AGN_RESTART_LADDER_MPIRUN=%s\n' "$(command -v mpirun)"
printf 'AGN_RESTART_LADDER_HDF5_DIR=%s\n' "${HDF5_DIR:-}"
printf 'AGN_RESTART_LADDER_HDF5_USE_FILE_LOCKING=FALSE\n'

if command -v h5dump >/dev/null 2>&1; then
  h5dump -d "/Timestep_${latest}/vars/rho" -s 0,0,0 -c 1,1,1 "${OUTPUTS}/data.$(printf "%04d" "${latest}").dbl.h5" >/dev/null
fi

printf 'AGN_RESTART_LADDER_REMOTE_WORKDIR=%s\n' "${REMOTE_WORKDIR}"
printf 'AGN_RESTART_LADDER_REMOTE_CONFIG_DIR=%s\n' "${REMOTE_CONFIG_DIR}"
printf 'AGN_RESTART_LADDER_SOURCE_WORKDIR=%s\n' "${SOURCE_WORKDIR}"
printf 'AGN_RESTART_LADDER_RESTART_INDEX=%s\n' "${latest}"
printf 'AGN_RESTART_LADDER_RESTART_FILE=%s\n' "${restart_file}"
printf 'AGN_RESTART_LADDER_PARTICLE_FILE=%s\n' "${particle_file}"
printf 'AGN_RESTART_LADDER_DBL_H5_TAIL=\n'
tail -n 5 "${OUTPUTS}/dbl.h5.out"
printf 'AGN_RESTART_LADDER_FLT_H5_TAIL=\n'
tail -n 5 "${OUTPUTS}/flt.h5.out"

qsub_vars=$(printf 'LADDER_NODES=%s,RUN_ROOT=%s,PLUTO_MAXTIME_HOURS=%s' \
  "${LADDER_NODES}" "${REMOTE_RUN_ROOT}" "${PLUTO_MAXTIME_HOURS}")

job_id=$(qsub \
  -N "${JOB_NAME}" \
  -l "select=${LADDER_NODES}:ncpus=${LADDER_NCPUS_PER_NODE}:mpiprocs=${LADDER_MPIPROCS_PER_NODE}" \
  -l "walltime=${LADDER_WALLTIME}" \
  -o "${REMOTE_STDOUT}" \
  -e "${REMOTE_STDERR}" \
  -v "${qsub_vars}" \
  "${REMOTE_WRAPPER}")
echo SUBMITTED_JOB_ID=${job_id}
qstat -f "${job_id}" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|Output_Path|Error_Path|comment' || true
REMOTE
)

REMOTE_CMD="REMOTE_TEMPLATE=$(quote "$REMOTE_TEMPLATE")
REMOTE_WRAPPER=$(quote "$REMOTE_WRAPPER")
REMOTE_CONFIG_DIR=$(quote "$REMOTE_CONFIG_DIR")
SOURCE_WORKDIR=$(quote "$SOURCE_WORKDIR")
EXPECTED_RESTART_INDEX=$(quote "$EXPECTED_RESTART_INDEX")
EXPECTED_PARTICLE_INDEX=$(quote "$EXPECTED_PARTICLE_INDEX")
ALLOW_LADDER_RERUN=$(quote "$ALLOW_LADDER_RERUN")
LADDER_NODES=$(quote "$LADDER_NODES")
LADDER_NCPUS_PER_NODE=$(quote "$LADDER_NCPUS_PER_NODE")
LADDER_MPIPROCS_PER_NODE=$(quote "$LADDER_MPIPROCS_PER_NODE")
LADDER_WALLTIME=$(quote "$LADDER_WALLTIME")
PLUTO_MAXTIME_HOURS=$(quote "$PLUTO_MAXTIME_HOURS")
REMOTE_RUN_ROOT=$(quote "$remote_run_root")
REMOTE_STDOUT=$(quote "$remote_stdout")
REMOTE_STDERR=$(quote "$remote_stderr")
JOB_NAME=$(quote "$job_name")
${REMOTE_CMD}"

echo "[submit] staging isolated ${LADDER_NODES}-node restart ladder rung and submitting ${REMOTE_WRAPPER}"
scripts/kunanyi/run_on_kunanyi.sh "${REMOTE_CMD}"
