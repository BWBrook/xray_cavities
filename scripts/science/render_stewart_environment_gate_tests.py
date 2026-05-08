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
        "--makefile-template",
        type=Path,
        default=Path(
            "/Users/bwbrook/git/utas-agn/jet-setup/test/environment/"
            "tabulated/makefile"
        ),
        help="Path to a jet-setup environment test makefile template.",
    )
    parser.add_argument(
        "--definitions-template",
        type=Path,
        default=Path("/Users/bwbrook/git/utas-agn/jet-setup/src/definitions.h"),
        help="Path to a jet-setup definitions.h template.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/science/stewart_environment_gate_tests"),
    )
    parser.add_argument("--duration-myr", type=float, default=300.0)
    parser.add_argument("--cells", type=int, default=50)
    parser.add_argument("--half-width-kpc", type=float, default=100.0)
    parser.add_argument(
        "--cells-per-kpc",
        type=float,
        help=(
            "If set, derive per-axis cell counts from half-widths. For example, "
            "--half-width-kpc 200 --cells-per-kpc 1 gives 400 cells per axis."
        ),
    )
    parser.add_argument("--x-cells", type=int)
    parser.add_argument("--y-cells", type=int)
    parser.add_argument("--z-cells", type=int)
    parser.add_argument("--x-half-width-kpc", type=float)
    parser.add_argument("--y-half-width-kpc", type=float)
    parser.add_argument("--z-half-width-kpc", type=float)
    parser.add_argument(
        "--output-interval-myr",
        type=float,
        help="Static dbl output cadence in Myr. Defaults to min(100, duration).",
    )
    parser.add_argument(
        "--hdf5-interval-myr",
        type=float,
        default=-1.0,
        help="Static dbl.h5 output cadence in Myr. Use a positive value to enable.",
    )
    parser.add_argument(
        "--checkpoint-interval-myr",
        type=float,
        default=-1.0,
        help=(
            "Deprecated/ignored for static-grid PLUTO. Restarts use dbl or "
            "dbl.h5 outputs; Chombo Checkpoint_interval is always disabled."
        ),
    )
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
ExtraFiles = environment.ini,{csv_name},verify-environment-stability.py,definitions.h,local_make

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


def render_definitions_no_particles(template: str) -> str:
    lines: list[str] = []
    for line in template.splitlines():
        words = line.split()
        if len(words) >= 3 and words[0] == "#define" and words[1] == "PARTICLES":
            lines.append("#define  PARTICLES                      NO")
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def render_local_make() -> str:
    return """OBJ += coordinates.o jet.o units.o environment_utilities.o environment.o tools_usr.o read_external_pressure.o galaxy.o
HEADERS += definitions_usr.h pluto_usr.h structs_usr.h coordinates.h jet.h units.h environment_utilities.h environment.h tools_usr.h read_external_pressure.h galaxy.h
"""


def render_environment_ini(csv_name: str) -> str:
    return f"""[External Environment]

ExternalData UNUSED_FOR_TABULATED_ENVIRONMENT.dbl
ExternalGrid UNUSED_FOR_TABULATED_ENVIRONMENT.grid.out

[Tabulated Environment]

TabulatedData ./{csv_name}
"""


def code_interval(value_myr: float) -> float:
    if value_myr <= 0.0:
        return -1.0
    return value_myr * CODE_TIME_PER_MYR


def axis_grid_line(axis: str, cells: int, half_width_kpc: float) -> str:
    lo = -abs(half_width_kpc)
    hi = abs(half_width_kpc)
    return f"{axis}-grid 1 {lo:.6g} {cells} u {hi:.6g}"


def render_pluto_ini(
    duration_myr: float,
    x_cells: int,
    y_cells: int,
    z_cells: int,
    x_half_width_kpc: float,
    y_half_width_kpc: float,
    z_half_width_kpc: float,
    output_interval_myr: float,
    hdf5_interval_myr: float,
    checkpoint_interval_myr: float,
) -> str:
    tstop = duration_myr * CODE_TIME_PER_MYR
    output_interval = output_interval_myr * CODE_TIME_PER_MYR
    hdf5_interval = code_interval(hdf5_interval_myr)
    first_dt = max(1.0, CODE_TIME_PER_MYR * 0.01)
    return f"""[Grid]

{axis_grid_line("X1", x_cells, x_half_width_kpc)}
{axis_grid_line("X2", y_cells, y_half_width_kpc)}
{axis_grid_line("X3", z_cells, z_half_width_kpc)}

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

log_dir          ./outputs/logs
output_dir       ./outputs
uservar          0
dbl              {output_interval:.8f}  -1   single_file
flt              -1.0  -1   single_file
dbl.h5           {hdf5_interval:.8f}  -1
flt.h5           -1.0  -1
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
JET_CHI                     1.0
JET_OA_PRIMARY              15.0
JET_OA_SECONDARY            15.0
JET_INJECTION_HEIGHT        0.75
JET_INITIAL_RADIUS          0.1
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
PART_INJECT_FREQUENCY       0.01
STELLAR_MASS                0.0
"""


def write_case(
    root: Path,
    label: str,
    source_csv: Path,
    verify_script: Path,
    makefile_template: Path,
    definitions_template: Path,
    duration_myr: float,
    x_cells: int,
    y_cells: int,
    z_cells: int,
    x_half_width_kpc: float,
    y_half_width_kpc: float,
    z_half_width_kpc: float,
    output_interval_myr: float,
    hdf5_interval_myr: float,
    checkpoint_interval_myr: float,
) -> None:
    target = root / label
    target.mkdir(parents=True, exist_ok=True)
    csv_name = source_csv.name
    shutil.copy2(source_csv, target / csv_name)
    shutil.copy2(verify_script, target / "verify-environment-stability.py")
    shutil.copy2(makefile_template, target / "makefile")
    (target / "definitions.h").write_text(
        render_definitions_no_particles(definitions_template.read_text())
    )
    (target / "local_make").write_text(render_local_make())
    (target / "test.ini").write_text(render_test_ini(label, csv_name))
    (target / "environment.ini").write_text(render_environment_ini(csv_name))
    (target / "pluto.ini").write_text(
        render_pluto_ini(
            duration_myr,
            x_cells,
            y_cells,
            z_cells,
            x_half_width_kpc,
            y_half_width_kpc,
            z_half_width_kpc,
            output_interval_myr,
            hdf5_interval_myr,
            checkpoint_interval_myr,
        )
    )


def axis_settings(args: argparse.Namespace) -> tuple[int, int, int, float, float, float, float]:
    x_half = args.x_half_width_kpc or args.half_width_kpc
    y_half = args.y_half_width_kpc or args.half_width_kpc
    z_half = args.z_half_width_kpc or args.half_width_kpc

    def cells(explicit: int | None, half_width: float) -> int:
        if explicit is not None:
            return explicit
        if args.cells_per_kpc is not None:
            return int(round(2.0 * half_width * args.cells_per_kpc))
        return args.cells

    x_cells = cells(args.x_cells, x_half)
    y_cells = cells(args.y_cells, y_half)
    z_cells = cells(args.z_cells, z_half)
    if min(x_cells, y_cells, z_cells) <= 0:
        raise SystemExit("all axis cell counts must be positive")
    output_interval_myr = args.output_interval_myr or min(100.0, args.duration_myr)
    return x_cells, y_cells, z_cells, x_half, y_half, z_half, output_interval_myr


def main() -> int:
    args = parse_args()
    cluster = require_file(args.cluster_tabulated)
    group = require_file(args.group_tabulated)
    verify_script = require_file(args.verify_script)
    makefile_template = require_file(args.makefile_template)
    definitions_template = require_file(args.definitions_template)

    output = args.output
    if output.exists():
        if not args.force:
            raise SystemExit(f"{output} already exists; use --force to overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (
        x_cells,
        y_cells,
        z_cells,
        x_half,
        y_half,
        z_half,
        output_interval_myr,
    ) = axis_settings(args)

    write_case(
        output,
        "cluster_002003",
        cluster,
        verify_script,
        makefile_template,
        definitions_template,
        args.duration_myr,
        x_cells,
        y_cells,
        z_cells,
        x_half,
        y_half,
        z_half,
        output_interval_myr,
        args.hdf5_interval_myr,
        args.checkpoint_interval_myr,
    )
    write_case(
        output,
        "group_002031",
        group,
        verify_script,
        makefile_template,
        definitions_template,
        args.duration_myr,
        x_cells,
        y_cells,
        z_cells,
        x_half,
        y_half,
        z_half,
        output_interval_myr,
        args.hdf5_interval_myr,
        args.checkpoint_interval_myr,
    )
    print(f"Rendered Stewart environment gate tests under {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
