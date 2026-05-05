#!/usr/bin/env python3
"""Render jet-setup environment-stability tests for Stewart tabulated assets."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


CODE_TIME_PER_MYR = 306.601393788


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create jet-setup run-tests.py compatible no-jet stability tests "
            "for the Stewart cluster and group tabulated environments."
        )
    )
    parser.add_argument("--cluster-tabulated", type=Path, required=True)
    parser.add_argument("--group-tabulated", type=Path, required=True)
    parser.add_argument(
        "--verify-script",
        type=Path,
        default=Path(
            "/Users/bwbrook/git/utas-agn/jet-setup/test/environment/"
            "verify-environment-stability.py"
        ),
        help="Path to jet-setup's verify-environment-stability.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/science/stewart_environment_gate_tests"),
    )
    parser.add_argument("--duration-myr", type=float, default=300.0)
    parser.add_argument("--cells", type=int, default=50)
    parser.add_argument("--half-width-kpc", type=float, default=100.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def require_file(path: Path) -> Path:
    path = path.expanduser()
    if not path.is_file():
        raise SystemExit(f"required file not found: {path}")
    return path


def render_test_ini(label: str, csv_name: str) -> str:
    return f"""[Info]
Name = Stewart {label} tabulated 3D Cartesian no-jet stability gate
Description = Stability gate for the confirmed Stewart {label} radially averaged tabulated environment
ExtraFiles = environment.ini,{csv_name},verify-environment-stability.py

[Definitions]
PHYSICS = HD
DIMENSIONS = 3
COMPONENTS = 3
GEOMETRY = CARTESIAN
BODY_FORCE = VECTOR
TIME_STEPPING = RK2

[DefinitionsUser]
DENSITY_PROFILE = ENV_TABULATED
JET_RELATIVISTIC_DENSITY = NO
JET_INJECTION_ROTATED = NO
PARTICLES_LP_RAISE = NO

[Verify]
Script = verify-environment-stability.py
"""


def render_environment_ini(csv_name: str) -> str:
    return f"""[External Environment]

ExternalData UNUSED_FOR_TABULATED_ENVIRONMENT.dbl
ExternalGrid UNUSED_FOR_TABULATED_ENVIRONMENT.grid.out

[Tabulated Environment]

TabulatedData ./{csv_name}
"""


def render_pluto_ini(duration_myr: float, cells: int, half_width_kpc: float) -> str:
    tstop = duration_myr * CODE_TIME_PER_MYR
    output_interval = min(100.0, duration_myr) * CODE_TIME_PER_MYR
    first_dt = max(1.0, CODE_TIME_PER_MYR * 0.01)
    lo = -abs(half_width_kpc)
    hi = abs(half_width_kpc)
    return f"""[Grid]

X1-grid 1 {lo:.6g} {cells} u {hi:.6g}
X2-grid 1 {lo:.6g} {cells} u {hi:.6g}
X3-grid 1 {lo:.6g} {cells} u {hi:.6g}

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

CFL              0.33
CFL_max_var      1.1
tstop            {tstop:.8f}
first_dt         {first_dt:.8f}

[Solver]

Solver           hllc

[Boundary]

X1-beg           reflective
X1-end           reflective
X2-beg           reflective
X2-end           reflective
X3-beg           reflective
X3-end           reflective

[Static Grid Output]

uservar          0
dbl              {output_interval:.8f}  -1   single_file
flt              -1.0  -1   single_file
vtk              -1.0  -1   single_file
tab              -1.0  -1
ppm              -1.0  -1
log              10
analysis         -1.0  -1

[Chombo HDF5 output]

Checkpoint_interval  -1.0  0
Plot_interval        -1.0  0

[Particles]

Nparticles          -1    -1
particles_dbl       -1.0  -1
particles_flt       -1.0  -1
particles_vtk       -1.0  -1
particles_tab       -1.0  -1

[Parameters]

JET_PWR                     1e45
JET_SPD                     0.1
JET_CHI                     100.0
JET_OA_PRIMARY              15.0
JET_OA_SECONDARY            15.0
JET_INJECTION_HEIGHT        0.2
JET_INITIAL_RADIUS          0.2
JET_X1O                     0.0
JET_X2O                     0.0
JET_X3O                     0.0
JET_ROTATION_ANGLE          0.0
JET_START_TIME              0.0
JET_END_TIME                0.0
JET_ACTIVE_TIME             0.0
JET_EPISODES                1.0
ENV_RHO_0                   2.4e-27
ENV_R_SCALING               144.0
ENV_DELTA_NFW               0.0
ENV_B_EXPONENT              0.38
ENV_TEMP                    3.462e7
ENV_X1O                     0.0
ENV_X2O                     0.0
ENV_X3O                     0.0
PART_INJECT_FREQUENCY       1.0
STELLAR_MASS                0.0
"""


def write_case(
    root: Path,
    label: str,
    source_csv: Path,
    verify_script: Path,
    duration_myr: float,
    cells: int,
    half_width_kpc: float,
) -> None:
    target = root / label
    target.mkdir(parents=True, exist_ok=True)
    csv_name = source_csv.name
    shutil.copy2(source_csv, target / csv_name)
    shutil.copy2(verify_script, target / "verify-environment-stability.py")
    (target / "test.ini").write_text(render_test_ini(label, csv_name))
    (target / "environment.ini").write_text(render_environment_ini(csv_name))
    (target / "pluto.ini").write_text(
        render_pluto_ini(duration_myr, cells, half_width_kpc)
    )


def main() -> int:
    args = parse_args()
    cluster = require_file(args.cluster_tabulated)
    group = require_file(args.group_tabulated)
    verify_script = require_file(args.verify_script)

    output = args.output
    if output.exists():
        if not args.force:
            raise SystemExit(f"{output} already exists; use --force to overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    write_case(
        output,
        "cluster_002003",
        cluster,
        verify_script,
        args.duration_myr,
        args.cells,
        args.half_width_kpc,
    )
    write_case(
        output,
        "group_002031",
        group,
        verify_script,
        args.duration_myr,
        args.cells,
        args.half_width_kpc,
    )
    print(f"Rendered Stewart environment gate tests under {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
