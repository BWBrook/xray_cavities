#!/usr/bin/env bash
set -euo pipefail

export PLUTO_DIR=${PLUTO_DIR:-"$HOME/git/utas-agn/pluto"}
BASE=${OFFICIAL_JET_ASSIGNMENT_BASE:-"$HOME/work/pluto-onboarding/official_jet_assignment"}
SRC="$PLUTO_DIR/Test_Problems/HD/Jet"
BUILD="$BASE/build"
RUNS="$BASE/runs"
RESULTS="$BASE/results"
LOGS="$BASE/logs"

RMAX=8.0
ZMAX=32.0
TSTOP=15.0
OUTPUT_INTERVAL=3.75
ETA=10.0
EXTERNAL_MACH=20.0

mkdir -p "$BUILD" "$RUNS" "$RESULTS" "$LOGS"

if [ ! -d "$SRC" ]; then
  echo "[error] PLUTO HD/Jet source not found at $SRC" >&2
  exit 1
fi

MACH=$(python3 - <<PY
import math
eta = float("$ETA")
mext = float("$EXTERNAL_MACH")
print(f"{mext / math.sqrt(eta):.12g}")
PY
)

patch_define() {
  local path="$1"
  local key="$2"
  local value="$3"
  python3 - "$path" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text().splitlines()
out = []
replaced = False
for line in lines:
    if line.startswith("#define") and len(line.split()) >= 2 and line.split()[1] == key:
        out.append(f"#define  {key.ljust(28)}   {value}")
        replaced = True
    else:
        out.append(line)
if not replaced:
    raise SystemExit(f"missing define {key} in {path}")
path.write_text("\n".join(out) + "\n")
PY
}

write_ini() {
  local target="$1"
  local cells_per_radius="$2"
  local nrad=$((cells_per_radius * 8))
  local nz=$((cells_per_radius * 32))
  cat > "$target" <<INI
[Grid]

X1-grid    1    0.0    ${nrad}    u    ${RMAX}
X2-grid    1    0.0    ${nz}      u    ${ZMAX}
X3-grid    1    0.0    1          u    1.0

[Chombo Refinement]

Levels           4
Ref_ratio        2 2 2 2 2
Regrid_interval  2 2 2 2
Refine_thresh    0.3
Tag_buffer_size  3
Block_factor     8
Max_grid_size    64
Fill_ratio       0.75

[Time]

CFL              0.35
CFL_max_var      1.1
tstop            ${TSTOP}
first_dt         1.e-4

[Solver]

Solver           hllc

[Boundary]

X1-beg        axisymmetric
X1-end        outflow
X2-beg        userdef
X2-end        outflow
X3-beg        periodic
X3-end        periodic

[Static Grid Output]

uservar    0
dbl        ${OUTPUT_INTERVAL}  -1   single_file
flt       -1.0                 -1   single_file
vtk       -1.0                 -1   single_file
tab       -1.0                 -1
ppm       -1.0                 -1
png       -1.0                 -1
log        20
analysis  -1.0                 -1

[Chombo HDF5 output]

Checkpoint_interval  -1.0  0
Plot_interval        -1.0  0

[Parameters]

ETA                         ${ETA}
MACH                        ${MACH}
INI
}

echo "[build] official PLUTO HD/Jet assignment binary"
rm -rf "$BUILD"
mkdir -p "$BUILD"
cp "$SRC/init.c" "$BUILD/init.c"
cp "$SRC/userdef_output.c" "$BUILD/userdef_output.c"
cp "$SRC/definitions_01.h" "$BUILD/definitions.h"
patch_define "$BUILD/definitions.h" DIMENSIONS 2
patch_define "$BUILD/definitions.h" GEOMETRY CYLINDRICAL
patch_define "$BUILD/definitions.h" RECONSTRUCTION LINEAR
patch_define "$BUILD/definitions.h" TIME_STEPPING RK2
patch_define "$BUILD/definitions.h" EOS IDEAL
patch_define "$BUILD/definitions.h" INCLUDE_JDIR TRUE
cat > "$BUILD/makefile" <<'MAKE'
ARCH         = Linux.gcc.defs
MAKE
write_ini "$BUILD/pluto.ini" 10

(
  cd "$BUILD"
  python3 - <<PY
import sys
sys.path.append("$PLUTO_DIR/Tools/Python")
from make_problem import MakeProblem
MakeProblem("$BUILD", "$PLUTO_DIR", 1, 1)
PY
  make clean
  make -j"$(nproc)"
) 2>&1 | tee "$LOGS/build.log"

if [ ! -x "$BUILD/pluto" ]; then
  echo "[error] build did not produce $BUILD/pluto" >&2
  exit 1
fi

run_case() {
  local case_name="$1"
  local cells_per_radius="$2"
  local case_dir="$RUNS/$case_name"
  local result_dir="$RESULTS/$case_name"

  echo "[run] $case_name (${cells_per_radius} cells per beam radius; external Mach ${EXTERNAL_MACH})"
  rm -rf "$case_dir" "$result_dir"
  mkdir -p "$case_dir" "$result_dir"
  cp "$BUILD/pluto" "$case_dir/pluto"
  cp "$BUILD/definitions.h" "$case_dir/definitions.h"
  write_ini "$case_dir/pluto.ini" "$cells_per_radius"

  (
    cd "$case_dir"
    rm -f data.*.dbl dbl.out grid.out restart.out analysis.out time.out pluto.log
    ./pluto -i pluto.ini > pluto.log 2>&1
  )

  if [ ! -f "$case_dir/dbl.out" ]; then
    echo "[error] expected dbl.out missing for $case_name" >&2
    exit 1
  fi

  local nlast
  nlast=$(tail -n 1 "$case_dir/dbl.out" | awk '{print $1}')
  if [ ! -f "$case_dir/data.$(printf '%04d' "$nlast").dbl" ]; then
    echo "[error] expected final dbl output missing for $case_name" >&2
    exit 1
  fi

  cp "$case_dir/pluto.ini" "$result_dir/"
  cp "$case_dir/definitions.h" "$result_dir/"
  cp "$case_dir/dbl.out" "$result_dir/"
  cp "$case_dir/grid.out" "$result_dir/"
  cp "$case_dir/time.out" "$result_dir/" 2>/dev/null || true
  cp "$case_dir/pluto.log" "$result_dir/"
  cp "$case_dir"/data.*.dbl "$result_dir/"
}

run_case r10 10
run_case r20 20

cat > "$RESULTS/run_metadata.txt" <<TXT
official_assignment=Martin Krause jet assignment supplied by Patrick
pluto_problem=Test_Problems/HD/Jet
geometry=CYLINDRICAL
dimensions=2
rmax=${RMAX}
zmax=${ZMAX}
tstop=${TSTOP}
output_interval=${OUTPUT_INTERVAL}
eta_ambient_over_jet=${ETA}
external_mach=${EXTERNAL_MACH}
internal_mach_parameter=${MACH}
pressure=1/gamma, matched at inlet and ambient
cases=r10,r20
TXT

echo "[done] official PLUTO HD/Jet assignment runs complete"
