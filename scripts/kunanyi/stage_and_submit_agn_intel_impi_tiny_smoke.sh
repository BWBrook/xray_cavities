#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_BASE="${REMOTE_BASE:-/u/bwbrook/codex_kunanyi}"
REMOTE_SCRIPT="${REMOTE_SCRIPT:-${REMOTE_BASE}/jet_setup_tiny_3d_cart_agn_intel_impi_smoke.pbs}"
REMOTE_STDOUT="${REMOTE_STDOUT:-${REMOTE_BASE}/jet_setup_tiny_3d_cart_agn_intel_impi_smoke.out}"
REMOTE_STDERR="${REMOTE_STDERR:-${REMOTE_BASE}/jet_setup_tiny_3d_cart_agn_intel_impi_smoke.err}"
REMOTE_WORKDIR="${REMOTE_WORKDIR:-/scratch/bwbrook/jet_setup_smoke/tiny_3d_cart_agn_intel_impi}"
LOCAL_SCRIPT="${LOCAL_SCRIPT:-${ROOT}/scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs}"

# Home-network default. Override for campus direct or Nectar fallback:
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox TPAC_SCP_HOST=kunanyi ...
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar TPAC_SCP_HOST=kunanyi-via-nectar ...
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"
export TPAC_SCP_HOST="${TPAC_SCP_HOST:-kunanyi-via-deep}"

quote() {
  printf "%q" "$1"
}

cd "${ROOT}"

if [ ! -f "${LOCAL_SCRIPT}" ]; then
  echo "Missing local PBS smoke script: ${LOCAL_SCRIPT}" >&2
  exit 2
fi

scripts/kunanyi/enable_jumpbox_ssh_safari.sh

echo "[stage] copying tiny 3D smoke PBS wrapper"
scripts/kunanyi/copy_to_kunanyi.sh "${LOCAL_SCRIPT}" "${REMOTE_SCRIPT}"

REMOTE_CMD=$(cat <<'REMOTE'
set -euo pipefail

test -f "${REMOTE_SCRIPT}"

if [ ! -x /ds/projects/agn ]; then
  echo "[blocked] /ds/projects/agn is not traversable by this account." >&2
  ls -ld /ds/projects/agn >&2 || true
  id >&2
  exit 10
fi
if [ ! -d /ds/projects/agn/modulefiles ] || [ ! -d /ds/projects/agn/libraries ]; then
  echo "[blocked] expected AGN modulefiles/libraries are not visible." >&2
  ls -ld /ds/projects/agn /ds/projects/agn/modulefiles /ds/projects/agn/libraries >&2 || true
  exit 11
fi

module purge
module use /ds/projects/agn/modulefiles
ml intel impi hdf5/1.12.1p zfp/0.5.5

printf 'AGN_SMOKE_MODULE_LIST_BEGIN\n'
module list 2>&1
printf 'AGN_SMOKE_MODULE_LIST_END\n'
printf 'AGN_SMOKE_MPICC=%s\n' "$(command -v mpicc)"
printf 'AGN_SMOKE_MPIRUN=%s\n' "$(command -v mpirun)"
printf 'AGN_SMOKE_HDF5_DIR=%s\n' "${HDF5_DIR:-}"
printf 'AGN_SMOKE_ZFP_DIR=%s\n' "${ZFP_DIR:-}"

job_id=$(qsub \
  -o "${REMOTE_STDOUT}" \
  -e "${REMOTE_STDERR}" \
  -v KUNANYI_MODULE_STACK=agn_intel_impi,MPI_FLAVOR=intelmpi,WORKDIR="${REMOTE_WORKDIR}" \
  "${REMOTE_SCRIPT}")
echo SUBMITTED_JOB_ID=${job_id}
qstat -f "${job_id}" | egrep 'Job Id:|Job_Name|job_state|queue|Resource_List.select|Resource_List.walltime|Mail_Users|comment' || true
REMOTE
)

REMOTE_CMD="REMOTE_SCRIPT=$(quote "$REMOTE_SCRIPT")
REMOTE_STDOUT=$(quote "$REMOTE_STDOUT")
REMOTE_STDERR=$(quote "$REMOTE_STDERR")
REMOTE_WORKDIR=$(quote "$REMOTE_WORKDIR")
${REMOTE_CMD}"

echo "[submit] validating AGN Intel/IMPI stack and submitting tiny smoke"
scripts/kunanyi/run_on_kunanyi.sh "${REMOTE_CMD}"
