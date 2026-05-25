#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_WORKDIR="${REMOTE_WORKDIR:-/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles}"
JOB_ID="${1:-${JOB_ID:-}}"

# Home-network default. Override these for campus direct or Nectar fallback.
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"

quote() {
  printf "%q" "$1"
}

REMOTE_CMD=$(cat <<'REMOTE'
set -euo pipefail
PROBLEM="${REMOTE_WORKDIR}/problem"
OUTPUTS="${PROBLEM}/outputs"
MARKERS="${REMOTE_WORKDIR}/markers"
LOGS="${REMOTE_WORKDIR}/job_logs"

echo "REMOTE_WORKDIR=${REMOTE_WORKDIR}"
echo "HOST=$(hostname)"
echo "NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [ -n "${JOB_ID}" ]; then
  echo
  echo "=== qstat -xf ${JOB_ID} ==="
  qstat -xf "${JOB_ID}" 2>&1 | egrep 'Job Id:|Job_Name|job_state|queue|Exit_status|resources_used\.|Resource_List\.|comment|ctime|etime|qtime|stime|obittime|exec_host' || true
fi

echo
echo "=== markers ==="
ls -l "${MARKERS}" 2>&1 || true
for marker in DONE FAILED; do
  if [ -f "${MARKERS}/${marker}" ]; then
    echo "--- ${MARKERS}/${marker}"
    cat "${MARKERS}/${marker}" || true
  fi
done
if [ -d "${MARKERS}/history" ]; then
  echo "--- marker history"
  find "${MARKERS}/history" -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %s %f\n' | sort | tail -20
fi

echo
echo "=== latest restart candidates ==="
for kind in dbl.h5 dbl; do
  out_file="${OUTPUTS}/${kind}.out"
  if [ ! -f "${out_file}" ]; then
    echo "${kind}: no catalogue"
    continue
  fi
  latest=$(awk 'NF && $1 ~ /^[0-9]+$/ {n=$1} END{if (n != "") print n}' "${out_file}")
  if [ -z "${latest:-}" ]; then
    echo "${kind}: no numeric entries"
    continue
  fi
  if [ "${kind}" = "dbl.h5" ]; then
    restart_file=$(printf "%s/data.%04d.dbl.h5" "${OUTPUTS}" "${latest}")
  else
    restart_file=$(printf "%s/data.%04d.dbl" "${OUTPUTS}" "${latest}")
  fi
  if [ -f "${restart_file}" ]; then
    size=$(stat -c %s "${restart_file}" 2>/dev/null || wc -c < "${restart_file}")
    echo "${kind}: latest=${latest} file=${restart_file} size=${size}"
  else
    echo "${kind}: latest=${latest} missing_file=${restart_file}"
  fi
  echo "--- tail ${out_file}"
  tail -n 8 "${out_file}" || true
done

echo
echo "=== output counts ==="
printf "data h5 count: "
find "${OUTPUTS}" -maxdepth 1 -type f -name 'data.*.h5' | wc -l
printf "particle dbl count: "
find "${OUTPUTS}" -maxdepth 1 -type f -name 'particles.*.dbl' | wc -l
du -sh "${OUTPUTS}" 2>/dev/null || true

echo
echo "=== recent output files ==="
find "${OUTPUTS}" -maxdepth 1 -type f \( -name 'data.*.h5' -o -name 'particles.*.dbl' -o -name '*.out' \) -printf '%TY-%Tm-%Td %TH:%TM:%TS %14s %f\n' | sort | tail -80

echo
echo "=== recent job logs ==="
find "${LOGS}" -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %s %f\n' 2>/dev/null | sort | tail -30 || true

echo
echo "=== recent MPI/PLUTO log summaries ==="
find "${OUTPUTS}/logs" -maxdepth 1 -type f -name 'pluto_*.log' -printf '%TY-%Tm-%Td %TH:%TM:%TS %s %p\n' 2>/dev/null | sort | tail -6 | while read -r _ _ _ log_path; do
  echo "--- ${log_path}"
  grep -niE 'Fatal: UD endpoint|unhandled timeout|Killed by signal|segmentation fault|MPI_ABORT|HDF5|Starting computation|^step:|RUN_KIND|maxtime|walltime|error|abort|failed' "${log_path}" | tail -60 || true
done
REMOTE
)

REMOTE_CMD="REMOTE_WORKDIR=$(quote "$REMOTE_WORKDIR")
JOB_ID=$(quote "$JOB_ID")
${REMOTE_CMD}"

cd "${ROOT}"
scripts/kunanyi/run_on_kunanyi.sh "${REMOTE_CMD}"
