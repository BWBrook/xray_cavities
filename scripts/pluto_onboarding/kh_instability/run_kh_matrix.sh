#!/usr/bin/env bash
set -euo pipefail

export PLUTO_DIR=/home/bwbrook/git/utas-agn/pluto
BASE=/home/bwbrook/work/pluto-onboarding/kh_instability
BUILDS=$BASE/builds
RUNS=$BASE/runs
LOGS=$BASE/logs
TEMPLATE=$PLUTO_DIR/Test_Problems/MHD/Rayleigh_Taylor/definitions_03.h

mkdir -p "$BUILDS" "$RUNS" "$LOGS"

write_init() {
  local target="$1"
  cat > "$target" <<'SRC'
#include "pluto.h"

/* ********************************************************************* */
void Init (double *v, double x1, double x2, double x3)
/*
 *
 *********************************************************************** */
{
  const double v0 = 0.25;
  const double a  = 0.01;
  const double b  = 0.1;
  const double eps = 0.01*v0;
  const double kx = 2.0*CONST_PI*x1;
  const double arg = (x2*x2)/(b*b);

  v[RHO] = 1.0;
  v[PRS] = 1.0;
  v[VX1] = -v0*tanh(x2/a);
  v[VX2] = eps*sin(kx)*exp(-arg);
  v[VX3] = 0.0;
  v[TRC] = (x2 < 0.0 ? 1.0 : 0.0);
}

/* ********************************************************************* */
void InitDomain (Data *d, Grid *grid)
/*! 
 * Assign initial condition by looping over the computational domain.
 *********************************************************************** */
{
}

/* ********************************************************************* */
void Analysis (const Data *d, Grid *grid)
/* 
 *
 *********************************************************************** */
{
}

/* ********************************************************************* */
void UserDefBoundary (const Data *d, RBox *box, int side, Grid *grid)
/*
 *
 *********************************************************************** */
{
}
SRC
}

write_definitions() {
  local target="$1"
  local recon="$2"
  local tstep="$3"
  cp "$TEMPLATE" "$target"
  perl -0pi -e 's/^#define  BODY_FORCE\s+\S+/#define  BODY_FORCE                     NO/m; s/^#define  RECONSTRUCTION\s+\S+/#define  RECONSTRUCTION                 '$recon'/m; s/^#define  TIME_STEPPING\s+\S+/#define  TIME_STEPPING                  '$tstep'/m; s/^#define  NTRACER\s+\S+/#define  NTRACER                        1/m; s/^#define  USER_DEF_PARAMETERS\s+\S+/#define  USER_DEF_PARAMETERS            3/m' "$target"
}

write_ini() {
  local target="$1"
  cat > "$target" <<INI
[Grid]

X1-grid  1   0.0   256   u   1.0
X2-grid  1  -1.0   512   u   1.0
X3-grid  1   0.0     1   u   1.0

[Time]

CFL            0.4
CFL_max_var    1.1
tstop          5.0
first_dt       1.e-4

[Solver]

Solver        roe

[Boundary]

X1-beg    periodic
X1-end    periodic
X2-beg    outflow
X2-end    outflow
X3-beg    outflow
X3-end    outflow

[Static Grid Output]

uservar    0
dbl        0.5  -1   single_file
flt       -1.0  -1   single_file
vtk       -1.0  -1   multiple_files
tab       -1.0  -1
ppm       -1.0  -1
png       -1.0  -1
log         10
analysis  -1.0  -1

[Chombo HDF5 output]

Checkpoint_interval  -1.0  0
Plot_interval        -1.0  0

[Parameters]

ETA                         2.0
GRAV                        -0.1
CHI                         0.0
INI
}

build_case() {
  local scheme="$1"
  local recon="$2"
  local tstep="$3"
  local build_dir="$BUILDS/$scheme"
  mkdir -p "$build_dir"
  echo "[build] $scheme"
  rm -f "$build_dir"/init.c "$build_dir"/definitions.h "$build_dir"/makefile "$build_dir"/pluto.ini
  write_init "$build_dir/init.c"
  write_definitions "$build_dir/definitions.h" "$recon" "$tstep"
  write_ini "$build_dir/pluto.ini"
  cat > "$build_dir/makefile" <<MAKE
ARCH         = Linux.gcc.defs
MAKE
  (
    cd "$build_dir"
    python3 - <<PY
import sys
sys.path.append("$PLUTO_DIR/Tools/Python")
from make_problem import MakeProblem
MakeProblem("$build_dir", "$PLUTO_DIR", 1, 1)
PY
    write_init "$build_dir/init.c"
    make clean
    make -j16
  ) | tee "$LOGS/build_${scheme}.log"
}

run_case() {
  local scheme="$1"
  local case_dir="$RUNS/$scheme"
  mkdir -p "$case_dir"
  ln -sfn "$BUILDS/$scheme/pluto" "$case_dir/pluto"
  write_ini "$case_dir/pluto.ini"
  echo "[run] $scheme"
  (
    cd "$case_dir"
    rm -f data.* *.dbl *.flt *.vtk *.tab dbl.out flt.out vtk.out tab.out grid.out restart.out analysis.out time.out pluto.log
    ./pluto -i pluto.ini > pluto.log 2>&1
  )
  if [ ! -f "$case_dir/data.0010.dbl" ]; then
    echo "[error] expected final output missing for $scheme" >&2
    return 1
  fi
}

build_case flat_euler FLAT EULER
build_case linear_rk2 LINEAR RK2
build_case parabolic_rk3 PARABOLIC RK3

for scheme in flat_euler linear_rk2 parabolic_rk3; do
  run_case "$scheme"
done

echo "[done] KH instability matrix complete"
