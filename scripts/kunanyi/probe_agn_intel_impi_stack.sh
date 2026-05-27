#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Home-network default. Override for campus direct or Nectar fallback:
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox ...
#   TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar ...
export TPAC_JUMPBOX_ALIAS="${TPAC_JUMPBOX_ALIAS:-tpac-jumpbox-via-deep}"
export TPAC_CLUSTER_HOST="${TPAC_CLUSTER_HOST:-kunanyi}"

cd "${ROOT}"

scripts/kunanyi/run_on_kunanyi.sh 'set -u
status=0
echo AGN_INTEL_IMPI_PROBE_START=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo REMOTE_HOST=$(hostname)
echo ID
id

for p in /ds/projects/agn /ds/projects/agn/modulefiles /ds/projects/agn/libraries; do
  printf "PATH_STAT %s: " "$p"
  ls -ld "$p" 2>&1 || true
  printf "PATH_TEST %s: exists=%s dir=%s readable=%s executable=%s\n" \
    "$p" \
    "$([ -e "$p" ] && echo yes || echo no)" \
    "$([ -d "$p" ] && echo yes || echo no)" \
    "$([ -r "$p" ] && echo yes || echo no)" \
    "$([ -x "$p" ] && echo yes || echo no)"
done

if [ ! -x /ds/projects/agn ]; then
  echo "AGN_STACK_ACCESS=blocked_no_execute_on_/ds/projects/agn"
  status=10
fi

module purge
if module use /ds/projects/agn/modulefiles 2>/tmp/agn_module_use.err; then
  echo MODULE_USE_OK=/ds/projects/agn/modulefiles
else
  echo MODULE_USE_FAILED
  cat /tmp/agn_module_use.err
  status=11
fi

echo MODULE_AVAIL_AGN_FILTER
module --ignore-cache avail 2>&1 | grep -Ei "(^|[ /])(intel|impi|hdf5|zfp)(/|$)" | sed -n "1,200p" || true

if module load intel impi hdf5/1.12.1p zfp/0.5.5 2>/tmp/agn_module_load.err; then
  echo MODULE_LOAD_OK=agn_intel_impi_hdf5_zfp
else
  echo MODULE_LOAD_FAILED
  cat /tmp/agn_module_load.err
  status=12
fi

module list 2>&1 || true
printf "mpicc=%s\n" "$(command -v mpicc || true)"
printf "mpirun=%s\n" "$(command -v mpirun || true)"
printf "HDF5_DIR=%s\n" "${HDF5_DIR:-}"
printf "ZFP_DIR=%s\n" "${ZFP_DIR:-}"
printf "LD_LIBRARY_PATH=%s\n" "${LD_LIBRARY_PATH:-}"
echo AGN_INTEL_IMPI_PROBE_END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
exit "$status"
'
