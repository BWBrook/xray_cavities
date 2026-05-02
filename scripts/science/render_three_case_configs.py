#!/usr/bin/env python3
"""Render dry-run configuration bundles for the three-case science suite.

This is a static/config-generation helper only. It does not build PLUTO and it
does not launch simulations. The generated bundles are intended to be copied to
Nectar or kunanyi once the real Stewart environment assets are known.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SECONDS_PER_MYR = 1_000_000.0 * 365.25 * 24.0 * 3600.0
ACTIVE_TIME_MYR = 300.0
SNAPSHOTS_MYR = [100.0, 200.0, 300.0]
VIEWS_DEG = [0.0, 45.0, 90.0]


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    environment: str
    jet_power_erg_s: float
    jet_power_w: str
    jet_speed_c: float
    role: str


CASES = {
    "C-HI": CaseSpec(
        case_id="C-HI",
        environment="cluster",
        jet_power_erg_s=1.0e45,
        jet_power_w="1e38",
        jet_speed_c=0.1,
        role="first high-visibility validation case",
    ),
    "C-LO": CaseSpec(
        case_id="C-LO",
        environment="cluster",
        jet_power_erg_s=1.0e43,
        jet_power_w="1e36",
        jet_speed_c=0.1,
        role="baseline science anchor",
    ),
    "G-LO": CaseSpec(
        case_id="G-LO",
        environment="group",
        jet_power_erg_s=1.0e43,
        jet_power_w="1e36",
        jet_speed_c=0.1,
        role="environment-dependence case",
    ),
}


GRIDS = {
    "micro": {
        "description": "syntax/smoke grid only; not a science rehearsal",
        "x1": (-12.0, 48, 12.0),
        "x2": (-12.0, 48, 12.0),
        "x3": (-18.0, 72, 18.0),
        "first_dt": "1.0e-3",
    },
    "nectar_placeholder": {
        "description": (
            "placeholder for resized-Nectar rehearsal; replace after Stewart "
            "environment extents are confirmed"
        ),
        "x1": (-24.0, 96, 24.0),
        "x2": (-24.0, 96, 24.0),
        "x3": (-36.0, 144, 36.0),
        "first_dt": "1.0e-3",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render config bundles for the three-case xray_cavities suite."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/science/three_case_configs"),
        help="Output directory for generated case bundles.",
    )
    parser.add_argument(
        "--variant",
        choices=["hydro", "particles", "both"],
        default="hydro",
        help="Generate particle-free, particle-enabled, or both variants.",
    )
    parser.add_argument(
        "--grid",
        choices=sorted(GRIDS),
        default="micro",
        help="Grid preset. Micro is for syntax/smoke tests only.",
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=sorted(CASES),
        help="Case ID to render. May be repeated. Defaults to all cases.",
    )
    parser.add_argument(
        "--cluster-tabulated",
        help="Path to confirmed Stewart cluster tabulated environment file.",
    )
    parser.add_argument(
        "--group-tabulated",
        help="Path to confirmed Stewart group tabulated environment file.",
    )
    parser.add_argument(
        "--cluster-external-data",
        help="Path to confirmed Stewart cluster external .dbl file.",
    )
    parser.add_argument(
        "--cluster-external-grid",
        help="Path to confirmed Stewart cluster external grid.out file.",
    )
    parser.add_argument(
        "--group-external-data",
        help="Path to confirmed Stewart group external .dbl file.",
    )
    parser.add_argument(
        "--group-external-grid",
        help="Path to confirmed Stewart group external grid.out file.",
    )
    parser.add_argument(
        "--require-assets",
        action="store_true",
        help="Fail if either the cluster or group environment is still a placeholder.",
    )
    parser.add_argument(
        "--check-local-assets",
        action="store_true",
        help="Also require supplied asset paths to exist on this local filesystem.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output directory if it already exists.",
    )
    return parser.parse_args()


def selected_variants(value: str) -> list[str]:
    if value == "both":
        return ["hydro", "particles"]
    return [value]


def selected_cases(values: list[str] | None) -> list[CaseSpec]:
    if values:
        return [CASES[value] for value in values]
    return [CASES["C-HI"], CASES["C-LO"], CASES["G-LO"]]


def environment_for(case: CaseSpec, args: argparse.Namespace) -> dict[str, str | bool]:
    prefix = case.environment
    tabulated = getattr(args, f"{prefix}_tabulated")
    external_data = getattr(args, f"{prefix}_external_data")
    external_grid = getattr(args, f"{prefix}_external_grid")

    if tabulated:
        env = {
            "kind": "tabulated",
            "status": "provided",
            "tabulated_data": tabulated,
            "external_data": "",
            "external_grid": "",
            "density_profile_define": "ENV_TABULATED",
        }
    elif external_data and external_grid:
        env = {
            "kind": "external",
            "status": "provided",
            "tabulated_data": "",
            "external_data": external_data,
            "external_grid": external_grid,
            "density_profile_define": "ENV_EXTERNAL",
        }
    else:
        label = prefix.upper()
        env = {
            "kind": "placeholder",
            "status": "missing_stewart_asset",
            "tabulated_data": f"NEEDS_STEWART_{label}_TABULATED.csv",
            "external_data": f"NEEDS_STEWART_{label}_DATA.dbl",
            "external_grid": f"NEEDS_STEWART_{label}_GRID.grid.out",
            "density_profile_define": "ENV_TABULATED",
        }

    if args.check_local_assets and env["status"] == "provided":
        paths = []
        if env["kind"] == "tabulated":
            paths.append(str(env["tabulated_data"]))
        else:
            paths.extend([str(env["external_data"]), str(env["external_grid"])])
        missing = [path for path in paths if not Path(path).expanduser().exists()]
        if missing:
            raise SystemExit(
                "Supplied environment path(s) are not visible locally: "
                + ", ".join(missing)
            )

    return env


def render_environment_ini(env: dict[str, str | bool]) -> str:
    return f"""[External Environment]

ExternalData {env["external_data"]}
ExternalGrid {env["external_grid"]}

[Tabulated Environment]

TabulatedData {env["tabulated_data"]}
"""


def particle_settings(variant: str) -> dict[str, str]:
    if variant == "particles":
        return {
            "particles_define": "PARTICLES_LP",
            "particles_raise": "YES",
            "nparticles_line": "Nparticles          -1    16.0",
            "particles_dbl_line": "particles_dbl       100.0  -1",
            "inject_frequency": "1.0",
        }

    return {
        "particles_define": "NO",
        "particles_raise": "NO",
        "nparticles_line": "Nparticles          -1    -1",
        "particles_dbl_line": "particles_dbl       -1.0  -1",
        "inject_frequency": "1.0",
    }


def render_pluto_ini(case: CaseSpec, variant: str, grid_name: str) -> str:
    grid = GRIDS[grid_name]
    particles = particle_settings(variant)
    x1_beg, x1_n, x1_end = grid["x1"]
    x2_beg, x2_n, x2_end = grid["x2"]
    x3_beg, x3_n, x3_end = grid["x3"]

    return f"""[Grid]

X1-grid  1  {x1_beg}   {x1_n}  u   {x1_end}
X2-grid  1  {x2_beg}   {x2_n}  u   {x2_end}
X3-grid  1  {x3_beg}   {x3_n}  u   {x3_end}

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
tstop            {ACTIVE_TIME_MYR:.1f}
first_dt         {grid["first_dt"]}

[Solver]

Solver           hllc

[Boundary]

X1-beg           outflow
X1-end           outflow
X2-beg           outflow
X2-end           outflow
X3-beg           outflow
X3-end           outflow

[Static Grid Output]

log_dir          ./outputs/logs
output_dir       ./outputs
uservar          0
dbl              100.0  -1   single_file
flt              -1.0   -1   single_file
dbl.h5           -1.0   -1
flt.h5           -1.0   -1
vtk              -1.0   -1   single_file
tab              -1.0   -1
ppm              -1.0   -1
png              -1.0   -1
log              100
analysis         -1.0   -1

[Chombo HDF5 output]

Checkpoint_interval  25.0  0
Plot_interval        -1.0  0

[Particles]

{particles["nparticles_line"]}
{particles["particles_dbl_line"]}
particles_flt       -1.0  -1
particles_vtk       -1.0  -1
particles_tab       -1.0  -1

[Parameters]

JET_PWR                     {case.jet_power_erg_s:.6g}
JET_SPD                     {case.jet_speed_c}
JET_CHI                     100.0
JET_OA_PRIMARY              15.0
JET_OA_SECONDARY            15.0
JET_INJECTION_HEIGHT        1.0
JET_INITIAL_RADIUS          1.0
JET_X1O                     0.0
JET_X2O                     0.0
JET_X3O                     0.0
JET_ROTATION_ANGLE          0.0
JET_START_TIME              0.0
JET_END_TIME                300.0
JET_ACTIVE_TIME             300.0
JET_EPISODES                1.0
ENV_RHO_0                   2.4e-27
ENV_R_SCALING               144.0
ENV_DELTA_NFW               0.0
ENV_B_EXPONENT              0.38
ENV_TEMP                    3.462e7
ENV_X1O                     0.0
ENV_X2O                     0.0
ENV_X3O                     0.0
PART_INJECT_FREQUENCY       {particles["inject_frequency"]}
STELLAR_MASS                0.0
"""


def definitions_overrides(env: dict[str, str | bool], variant: str) -> dict[str, dict[str, str]]:
    particles = particle_settings(variant)
    return {
        "definitions.h": {
            "PHYSICS": "HD",
            "DIMENSIONS": "3",
            "GEOMETRY": "CARTESIAN",
            "BODY_FORCE": "VECTOR",
            "PARTICLES": particles["particles_define"],
            "EOS": "IDEAL",
        },
        "definitions_usr.h": {
            "DENSITY_PROFILE": str(env["density_profile_define"]),
            "JET_DENSITY_CALCULATION": "DENSITY_LENGTH_SCALE",
            "JET_INJECTION_ROTATED": "NO",
            "JET_RELATIVISTIC_DENSITY": "NO",
            "PARTICLES_LP_RAISE": particles["particles_raise"],
        },
    }


def injected_energy(case: CaseSpec) -> dict[str, float]:
    one_sided = case.jet_power_erg_s * ACTIVE_TIME_MYR * SECONDS_PER_MYR
    return {
        "one_sided_erg": one_sided,
        "bipolar_erg": 2.0 * one_sided,
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def render_case(
    root: Path,
    case: CaseSpec,
    variant: str,
    grid_name: str,
    env: dict[str, str | bool],
) -> None:
    case_dir = root / case.case_id / variant
    case_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "spec_version": "three-case-v0.1",
        "case": asdict(case),
        "variant": variant,
        "grid": {"name": grid_name, **GRIDS[grid_name]},
        "simulation_defaults": {
            "physics": "HD",
            "geometry": "CARTESIAN",
            "jet_relativistic_density": "NO",
            "opening_angle_primary_deg": 15.0,
            "opening_angle_secondary_deg": 15.0,
            "jet_end_time_myr": ACTIVE_TIME_MYR,
            "jet_active_time_myr": ACTIVE_TIME_MYR,
            "tracer_threshold_default": 5.0e-3,
            "tracer_threshold_sensitivity": [1.0e-3, 1.0e-2],
        },
        "sampling": {
            "snapshots_myr": SNAPSHOTS_MYR,
            "views_deg": VIEWS_DEG,
        },
        "environment": env,
        "truth_conventions": {
            "jet_power_is_assumed_one_sided_until_confirmed": True,
            "injected_energy": injected_energy(case),
        },
        "production_gate": (
            "Do not launch production until the environment status is provided "
            "and the Nectar no-jet stability gate is green."
        ),
    }

    (case_dir / "pluto.ini").write_text(render_pluto_ini(case, variant, grid_name))
    (case_dir / "environment.ini").write_text(render_environment_ini(env))
    write_json(case_dir / "case_manifest.json", manifest)
    write_json(case_dir / "definitions_overrides.json", definitions_overrides(env, variant))


def render_readme(root: Path, cases: Iterable[CaseSpec], variants: Iterable[str], grid_name: str) -> None:
    case_list = ", ".join(case.case_id for case in cases)
    variant_list = ", ".join(variants)
    text = f"""# Generated Three-Case Config Bundles

Generated by `scripts/science/render_three_case_configs.py`.

- cases: {case_list}
- variants: {variant_list}
- grid preset: `{grid_name}`

These bundles are dry-run launch packages. They are not a production approval.

Each case variant contains:

- `pluto.ini`
- `environment.ini`
- `definitions_overrides.json`
- `case_manifest.json`

Production remains blocked until the real Stewart cluster and group
environment files are supplied and the Nectar environment gates are green.
"""
    (root / "README.md").write_text(text)


def main() -> int:
    args = parse_args()
    cases = selected_cases(args.case)
    variants = selected_variants(args.variant)

    envs = {case.environment: environment_for(case, args) for case in cases}
    if args.require_assets:
        missing = sorted(
            {
                case.environment
                for case in cases
                if envs[case.environment]["status"] != "provided"
            }
        )
        if missing:
            raise SystemExit(
                "Missing confirmed Stewart environment asset(s): " + ", ".join(missing)
            )

    output = args.output
    if output.exists():
        if not args.force:
            raise SystemExit(f"{output} already exists; use --force to overwrite")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for case in cases:
        env = envs[case.environment]
        for variant in variants:
            render_case(output, case, variant, args.grid, env)

    render_readme(output, cases, variants, args.grid)
    print(f"Rendered {len(cases) * len(variants)} config bundle(s) under {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
