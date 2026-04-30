#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REMOTE_CMD="$(cat <<'REMOTE'
set -e
echo "HOST=$(hostname -f)"
echo "--- module version ---"
module --version 2>&1 | head -5
echo "--- targeted module avail ---"
for pat in gcc GCC intel Intel oneapi OneAPI openmpi OpenMPI mpi MPI hdf5 HDF5 netcdf NetCDF cmake CMake python Python git Git; do
  echo "### ${pat}"
  module --terse avail "${pat}" 2>&1 | head -40
done
REMOTE
)"

"$SCRIPT_DIR/run_on_kunanyi.sh" "$REMOTE_CMD"
