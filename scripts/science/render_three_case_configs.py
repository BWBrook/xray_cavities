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
DEFAULT_DURATION_MYR = 50.0
DEFAULT_SNAPSHOT_INTERVAL_MYR = 1.0
DEFAULT_DBL_H5_INTERVAL_MYR = 5.0
DEFAULT_PARTICLE_INTERVAL_MYR = 0.01
DEFAULT_PARTICLES_PER_INJECTION = 32.0
CODE_TIME_PER_MYR = 306.601393788
EARLY_DIAGNOSTIC_SNAPSHOTS_MYR = [1.0, 2.0, 3.0, 4.0, 5.0]
VIEWS_DEG = [0.0, 45.0, 90.0]
JET_CHI = "1.0"
JET_INJECTION_HEIGHT_KPC = "0.75"
JET_INITIAL_RADIUS_KPC = "0.1"


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
    "stewart_stretched_200": {
        "description": (
            "stretched CosmoDRAGoN-style grid copied from the old Stewart "
            "cluster 002_003/F.ini template; retained for provenance only "
            "after Patrick/Stas requested an extended X3 domain"
        ),
        "x1_line": "X1-grid     5   -200 330 s -10 100 s -2.5 100 u 2.5 100 s 10 330 s 200",
        "x2_line": "X2-grid     5   -200 330 s -10 100 s -2.5 100 u 2.5 100 s 10 330 s 200",
        "x3_line": "X3-grid     5   -200 330 s -10 100 s -2.5 100 u 2.5 100 s 10 330 s 200",
        "first_dt": "1.0e-5",
        "source": "env/extracted/inis/002_003/F.ini",
        "open_issue": (
            "Superseded for C-HI by stewart_stretched_250 after the "
            "2026-05-08 Patrick/Stas feedback."
        ),
    },
    "stewart_stretched_250": {
        "description": (
            "C-HI supervisor-approved grid after the 2026-05-08 feedback: "
            "X1/X2 retain the historical +/-200 kpc Stewart patching, while "
            "X3 is extended to +/-250 kpc with 357 outer stretch cells on "
            "each side so the cell size near 200 kpc matches the old grid."
        ),
        "x1_line": "X1-grid     5   -200 330 s -10 100 s -2.5 100 u 2.5 100 s 10 330 s 200",
        "x2_line": "X2-grid     5   -200 330 s -10 100 s -2.5 100 u 2.5 100 s 10 330 s 200",
        "x3_line": "X3-grid     5   -250 357 s -10 100 s -2.5 100 u 2.5 100 s 10 357 s 250",
        "first_dt": "1.0e-5",
        "source": "env/extracted/inis/002_003/F.ini plus Patrick/Stas 2026-05-08 feedback",
        "resolution_note": (
            "Using the PLUTO stretched-grid recurrence, the old 10-200 kpc "
            "outer patch has dx~1.6923 kpc at 200 kpc. Extending X3 from "
            "10 to 250 kpc with the same central dx and N=357 gives "
            "dx~1.6930 kpc in the cell spanning 200 kpc."
        ),
    },
    "kunanyi_single_node_250": {
        "description": (
            "single-node C-HI particle shakedown grid: full +/-200 kpc X1/X2 "
            "and +/-250 kpc X3 extents with the original 0.05 kpc central jet "
            "resolution retained, but reduced outer stretch counts so the "
            "problem fits one 128 GB Kunanyi node. This is not the final "
            "production grid."
        ),
        "x1_line": "X1-grid     5   -200 72 s -10 80 s -2.5 100 u 2.5 80 s 10 72 s 200",
        "x2_line": "X2-grid     5   -200 72 s -10 80 s -2.5 100 u 2.5 80 s 10 72 s 200",
        "x3_line": "X3-grid     5   -250 96 s -10 80 s -2.5 100 u 2.5 80 s 10 96 s 250",
        "first_dt": "1.0e-5",
        "source": "derived from stewart_stretched_250 after one-node particle memory gate",
        "resolution_note": (
            "Central -2.5..2.5 kpc region remains 100 uniform cells, so "
            "dx=0.05 kpc around the inlet. Outer stretches are intentionally "
            "coarser than the production grid to keep this as a single-node "
            "build/run/restart rehearsal."
        ),
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
        choices=["env_gate", "hydro", "particles", "both"],
        default="particles",
        help=(
            "Generate no-jet environment-gate, particle-free debug, "
            "particle-enabled nominal science, or both jet variants."
        ),
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
    parser.add_argument(
        "--duration-myr",
        type=float,
        default=DEFAULT_DURATION_MYR,
        help="Physical run duration in Myr for tstop/output conversion.",
    )
    parser.add_argument(
        "--snapshot-interval-myr",
        type=float,
        default=DEFAULT_SNAPSHOT_INTERVAL_MYR,
        help="Physical science-output cadence in Myr, rendered in PLUTO code time.",
    )
    parser.add_argument(
        "--dbl-h5-interval-myr",
        dest="dbl_h5_interval_myr",
        type=float,
        default=None,
        help=(
            "Physical dbl.h5 cadence in Myr, rendered in PLUTO code time. "
            "Static-grid PLUTO uses dbl.h5 files for restarts."
        ),
    )
    parser.add_argument(
        "--checkpoint-interval-myr",
        dest="dbl_h5_interval_myr",
        type=float,
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--particle-interval-myr",
        type=float,
        default=DEFAULT_PARTICLE_INTERVAL_MYR,
        help="Particle output and injection cadence in physical Myr.",
    )
    parser.add_argument(
        "--particles-per-injection",
        type=float,
        default=DEFAULT_PARTICLES_PER_INJECTION,
        help="Second field of Nparticles for the particle-enabled variant.",
    )
    args = parser.parse_args()
    if args.dbl_h5_interval_myr is None:
        args.dbl_h5_interval_myr = DEFAULT_DBL_H5_INTERVAL_MYR
    return args


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
    external_data = env["external_data"] or "UNUSED_FOR_TABULATED_ENVIRONMENT.dbl"
    external_grid = env["external_grid"] or "UNUSED_FOR_TABULATED_ENVIRONMENT.grid.out"
    return f"""[External Environment]

ExternalData {external_data}
ExternalGrid {external_grid}

[Tabulated Environment]

TabulatedData {env["tabulated_data"]}
"""


def fmt_number(value: float) -> str:
    text = f"{value:.8g}"
    if "e" not in text and "." not in text:
        text += ".0"
    return text


def particle_settings(
    variant: str,
    particle_interval_myr: float,
    particles_per_injection: float,
) -> dict[str, str]:
    particle_interval_code = particle_interval_myr * CODE_TIME_PER_MYR
    inject_frequency = fmt_number(particle_interval_myr)
    if variant == "particles":
        return {
            "particles_define": "PARTICLES_LP",
            "particles_raise": "YES",
            "nparticles_line": (
                f"Nparticles          -1    {fmt_number(particles_per_injection)}"
            ),
            "particles_dbl_line": f"particles_dbl       {particle_interval_code:.8f}  -1",
            "inject_frequency": inject_frequency,
        }

    return {
        "particles_define": "NO",
        "particles_raise": "NO",
        "nparticles_line": "Nparticles          -1    -1",
        "particles_dbl_line": "particles_dbl       -1.0  -1",
        "inject_frequency": inject_frequency,
    }


def render_pluto_ini(
    case: CaseSpec,
    variant: str,
    grid_name: str,
    duration_myr: float,
    snapshot_interval_myr: float,
    dbl_h5_interval_myr: float,
    particle_interval_myr: float,
    particles_per_injection: float,
) -> str:
    grid = GRIDS[grid_name]
    particles = particle_settings(variant, particle_interval_myr, particles_per_injection)
    if "x1_line" in grid:
        x1_line = str(grid["x1_line"])
        x2_line = str(grid["x2_line"])
        x3_line = str(grid["x3_line"])
    else:
        x1_beg, x1_n, x1_end = grid["x1"]
        x2_beg, x2_n, x2_end = grid["x2"]
        x3_beg, x3_n, x3_end = grid["x3"]
        x1_line = f"X1-grid  1  {x1_beg}   {x1_n}  u   {x1_end}"
        x2_line = f"X2-grid  1  {x2_beg}   {x2_n}  u   {x2_end}"
        x3_line = f"X3-grid  1  {x3_beg}   {x3_n}  u   {x3_end}"
    tstop_code = duration_myr * CODE_TIME_PER_MYR
    snapshot_code = snapshot_interval_myr * CODE_TIME_PER_MYR
    dbl_h5_code = dbl_h5_interval_myr * CODE_TIME_PER_MYR
    jet_end_time_myr = 0.0 if variant == "env_gate" else duration_myr
    jet_active_time_myr = 0.0 if variant == "env_gate" else duration_myr

    return f"""[Grid]

{x1_line}
{x2_line}
{x3_line}

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
tstop            {tstop_code:.8f}
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
dbl              -1.0   -1   single_file
flt              -1.0   -1   single_file
dbl.h5           {dbl_h5_code:.8f}  -1
flt.h5           {snapshot_code:.8f}  -1
vtk              -1.0   -1   single_file
tab              -1.0   -1
ppm              -1.0   -1
png              -1.0   -1
log              100
analysis         -1.0   -1

[Chombo HDF5 output]

Checkpoint_interval  -1.0  0
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
JET_CHI                     {JET_CHI}
JET_OA_PRIMARY              15.0
JET_OA_SECONDARY            15.0
JET_INJECTION_HEIGHT        {JET_INJECTION_HEIGHT_KPC}
JET_INITIAL_RADIUS          {JET_INITIAL_RADIUS_KPC}
JET_X1O                     0.0
JET_X2O                     0.0
JET_X3O                     0.0
JET_ROTATION_ANGLE          0.0
JET_START_TIME              0.0
JET_END_TIME                {jet_end_time_myr:.8f}
JET_ACTIVE_TIME             {jet_active_time_myr:.8f}
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


def definitions_overrides(
    env: dict[str, str | bool],
    variant: str,
    particle_interval_myr: float,
    particles_per_injection: float,
) -> dict[str, dict[str, str]]:
    particles = particle_settings(variant, particle_interval_myr, particles_per_injection)
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


def injected_energy(case: CaseSpec, active_time_myr: float) -> dict[str, float]:
    one_sided = case.jet_power_erg_s * active_time_myr * SECONDS_PER_MYR
    return {
        "one_sided_erg": one_sided,
        "bipolar_erg": 2.0 * one_sided,
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def pluto_value(text: str, key: str, field_index: int = 1) -> str | None:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) > field_index and parts[0] == key:
            return parts[field_index]
    return None


def render_validation(
    pluto_text: str,
    case: CaseSpec,
    variant: str,
    duration_myr: float,
    snapshot_interval_myr: float,
    dbl_h5_interval_myr: float,
    particle_interval_myr: float,
    particles_per_injection: float,
) -> dict[str, object]:
    active_time_myr = 0.0 if variant == "env_gate" else duration_myr
    particles = particle_settings(variant, particle_interval_myr, particles_per_injection)
    checks = [
        ("tstop", "tstop", 1, f"{duration_myr * CODE_TIME_PER_MYR:.8f}"),
        ("dbl", "dbl", 1, "-1.0"),
        (
            "dbl.h5",
            "dbl.h5",
            1,
            f"{dbl_h5_interval_myr * CODE_TIME_PER_MYR:.8f}",
        ),
        (
            "flt.h5",
            "flt.h5",
            1,
            f"{snapshot_interval_myr * CODE_TIME_PER_MYR:.8f}",
        ),
        ("Checkpoint_interval", "Checkpoint_interval", 1, "-1.0"),
        ("particles_dbl", "particles_dbl", 1, pluto_value(particles["particles_dbl_line"], "particles_dbl") or "-1.0"),
        ("Nparticles_second_field", "Nparticles", 2, fmt_number(particles_per_injection) if variant == "particles" else "-1"),
        ("JET_PWR", "JET_PWR", 1, f"{case.jet_power_erg_s:.6g}"),
        ("JET_SPD", "JET_SPD", 1, str(case.jet_speed_c)),
        ("JET_CHI", "JET_CHI", 1, JET_CHI),
        ("JET_INJECTION_HEIGHT", "JET_INJECTION_HEIGHT", 1, JET_INJECTION_HEIGHT_KPC),
        ("JET_INITIAL_RADIUS", "JET_INITIAL_RADIUS", 1, JET_INITIAL_RADIUS_KPC),
        ("JET_END_TIME", "JET_END_TIME", 1, f"{active_time_myr:.8f}"),
        ("JET_ACTIVE_TIME", "JET_ACTIVE_TIME", 1, f"{active_time_myr:.8f}"),
        (
            "PART_INJECT_FREQUENCY",
            "PART_INJECT_FREQUENCY",
            1,
            particles["inject_frequency"],
        ),
    ]
    results = {
        label: {
            "expected": expected,
            "rendered": pluto_value(pluto_text, key, field_index),
            "ok": pluto_value(pluto_text, key, field_index) == expected,
        }
        for label, key, field_index, expected in checks
    }
    return {
        "ok": all(item["ok"] for item in results.values()),
        "checks": results,
        "note": (
            "This static validation checks the generated pluto.ini against the "
            "run definition. A later gate should compare PLUTO startup logs "
            "against these same intended values."
        ),
    }


def stage_environment_assets(
    case_dir: Path,
    env: dict[str, str | bool],
) -> dict[str, str | bool]:
    """Copy visible environment assets into the launch bundle.

    The generated `environment.ini` should be runnable after the case directory
    is staged to a remote host. Keep the original source paths in the manifest
    for provenance, but point PLUTO at local filenames when the assets are
    visible on this machine.
    """

    staged = dict(env)
    if staged.get("status") != "provided":
        return staged

    if staged.get("kind") == "tabulated":
        source = Path(str(staged["tabulated_data"])).expanduser()
        staged["source_tabulated_data"] = str(staged["tabulated_data"])
        if source.exists():
            target = case_dir / source.name
            shutil.copy2(source, target)
            staged["tabulated_data"] = target.name
        return staged

    if staged.get("kind") == "external":
        for key, source_key in (
            ("external_data", "source_external_data"),
            ("external_grid", "source_external_grid"),
        ):
            source = Path(str(staged[key])).expanduser()
            staged[source_key] = str(staged[key])
            if source.exists():
                target = case_dir / source.name
                shutil.copy2(source, target)
                staged[key] = target.name

    return staged


def render_case(
    root: Path,
    case: CaseSpec,
    variant: str,
    grid_name: str,
    env: dict[str, str | bool],
    duration_myr: float,
    snapshot_interval_myr: float,
    dbl_h5_interval_myr: float,
    particle_interval_myr: float,
    particles_per_injection: float,
) -> None:
    case_dir = root / case.case_id / variant
    case_dir.mkdir(parents=True, exist_ok=True)
    launch_env = stage_environment_assets(case_dir, env)
    active_time_myr = 0.0 if variant == "env_gate" else duration_myr
    snapshot_interval_code = snapshot_interval_myr * CODE_TIME_PER_MYR
    dbl_h5_interval_code = dbl_h5_interval_myr * CODE_TIME_PER_MYR
    particle_interval_code = particle_interval_myr * CODE_TIME_PER_MYR
    run_definition = {
        "case_id": case.case_id,
        "run_name": f"{case.case_id}_{variant}",
        "variant": variant,
        "environment": launch_env,
        "science_intent": {
            "role": case.role,
            "jet_power_erg_s_one_sided": case.jet_power_erg_s,
            "jet_speed_c": case.jet_speed_c,
            "opening_angle_primary_deg": 15.0,
            "opening_angle_secondary_deg": 15.0,
            "particles_enabled": variant == "particles",
            "duration_myr": duration_myr,
            "active_time_myr": active_time_myr,
            "snapshot_interval_myr": snapshot_interval_myr,
            "dbl_h5_interval_myr": dbl_h5_interval_myr,
            "chombo_checkpoint_interval": "disabled",
            "particle_interval_myr": particle_interval_myr,
            "particles_per_injection": (
                particles_per_injection if variant == "particles" else None
            ),
            "views_deg": VIEWS_DEG,
            "early_diagnostic_snapshots_myr": EARLY_DIAGNOSTIC_SNAPSHOTS_MYR,
        },
        "unit_contract": {
            "tstop": "PLUTO code time",
            "static_grid_output_intervals": "PLUTO code time",
            "static_grid_dbl_h5_restart_outputs": "PLUTO code time",
            "chombo_checkpoint_interval": "disabled for static-grid PLUTO",
            "JET_START_TIME": "Myr",
            "JET_END_TIME": "Myr",
            "JET_ACTIVE_TIME": "Myr",
            "PART_INJECT_FREQUENCY": "Myr",
            "jet_injection_dimensions": "kpc",
            "environment_offsets": "kpc",
            "JET_PWR": "one-sided erg/s",
        },
    }
    manifest = {
        "spec_version": "three-case-v0.2",
        "case": asdict(case),
        "variant": variant,
        "grid": {"name": grid_name, **GRIDS[grid_name]},
        "time_conversion": {
            "code_time_per_myr": CODE_TIME_PER_MYR,
            "duration_myr": duration_myr,
            "tstop_code_time": duration_myr * CODE_TIME_PER_MYR,
            "snapshot_interval_myr": snapshot_interval_myr,
            "snapshot_interval_code_time": snapshot_interval_code,
            "dbl_h5_interval_myr": dbl_h5_interval_myr,
            "dbl_h5_interval_code_time": dbl_h5_interval_code,
            "particle_interval_myr": particle_interval_myr,
            "particle_interval_code_time": particle_interval_code,
            "chombo_checkpoint_interval": "disabled",
            "note": (
                "PLUTO core time controls and output intervals use code time; "
                "JET_END_TIME and JET_ACTIVE_TIME are physical Myr parameters."
            ),
        },
        "simulation_defaults": {
            "physics": "HD",
            "geometry": "CARTESIAN",
            "jet_relativistic_density": "NO",
            "opening_angle_primary_deg": 15.0,
            "opening_angle_secondary_deg": 15.0,
            "jet_chi": float(JET_CHI),
            "jet_injection_height_kpc": float(JET_INJECTION_HEIGHT_KPC),
            "jet_initial_radius_kpc": float(JET_INITIAL_RADIUS_KPC),
            "jet_end_time_myr": active_time_myr,
            "jet_active_time_myr": active_time_myr,
            "particles_enabled": variant == "particles",
            "particle_interval_myr": particle_interval_myr if variant == "particles" else None,
            "particles_per_injection": (
                particles_per_injection if variant == "particles" else None
            ),
            "tracer_threshold_default": 5.0e-3,
            "tracer_threshold_sensitivity": [1.0e-3, 1.0e-2],
        },
        "sampling": {
            "early_diagnostic_snapshots_myr": EARLY_DIAGNOSTIC_SNAPSHOTS_MYR,
            "snapshot_interval_myr": snapshot_interval_myr,
            "views_deg": VIEWS_DEG,
            "views_are_post_processing_only": True,
        },
        "environment": launch_env,
        "truth_conventions": {
            "jet_power_is_one_sided": True,
            "injected_energy": injected_energy(
                case, active_time_myr
            ),
        },
        "production_gate": (
            "Do not launch multi-day production until generated config files "
            "have been reviewed by Patrick/Stas and the kunanyi environment, "
            "MPI, HDF5, and restart path are green."
        ),
    }

    pluto_text = render_pluto_ini(
        case,
        variant,
        grid_name,
        duration_myr,
        snapshot_interval_myr,
        dbl_h5_interval_myr,
        particle_interval_myr,
        particles_per_injection,
    )
    (case_dir / "pluto.ini").write_text(pluto_text)
    (case_dir / "environment.ini").write_text(render_environment_ini(launch_env))
    write_json(case_dir / "run_definition.json", run_definition)
    write_json(case_dir / "case_manifest.json", manifest)
    write_json(
        case_dir / "render_validation.json",
        render_validation(
            pluto_text,
            case,
            variant,
            duration_myr,
            snapshot_interval_myr,
            dbl_h5_interval_myr,
            particle_interval_myr,
            particles_per_injection,
        ),
    )
    write_json(
        case_dir / "definitions_overrides.json",
        definitions_overrides(
            launch_env,
            variant,
            particle_interval_myr,
            particles_per_injection,
        ),
    )


def render_readme(
    root: Path,
    cases: Iterable[CaseSpec],
    variants: Iterable[str],
    grid_name: str,
    duration_myr: float,
    snapshot_interval_myr: float,
    dbl_h5_interval_myr: float,
    particle_interval_myr: float,
    particles_per_injection: float,
) -> None:
    case_list = ", ".join(case.case_id for case in cases)
    variant_list = ", ".join(variants)
    text = f"""# Generated Three-Case Config Bundles

Generated by `scripts/science/render_three_case_configs.py`.

- cases: {case_list}
- variants: {variant_list}
- grid preset: `{grid_name}`
- duration: `{duration_myr} Myr`
- science-output cadence: `{snapshot_interval_myr} Myr`
- dbl.h5 restart-output cadence: `{dbl_h5_interval_myr} Myr`
- Chombo `Checkpoint_interval`: disabled for static-grid PLUTO
- particle cadence: `{particle_interval_myr} Myr`
- particles per injection: `{particles_per_injection}`
- PLUTO code-time conversion: `{CODE_TIME_PER_MYR} code units per Myr`

These bundles are dry-run launch packages. They are not a production approval.
The nominal science variant is `particles`; `hydro` is retained as a narrow
debugging fallback.

Unit contract:

- PLUTO `tstop` and static-grid output intervals are rendered in PLUTO code
  time.
- `JET_END_TIME` and `JET_ACTIVE_TIME` are rendered in physical Myr.
- `PART_INJECT_FREQUENCY` is rendered in physical Myr.
- `JET_PWR` is one-sided jet power.

Each case variant contains:

- `pluto.ini`
- `environment.ini`
- `run_definition.json`
- `definitions_overrides.json`
- `case_manifest.json`
- `render_validation.json`

Multi-day production remains blocked until Patrick/Stas review the generated
configuration package and the production-like kunanyi environment/MPI/HDF5
gate is green.
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
            render_case(
                output,
                case,
                variant,
                args.grid,
                env,
                args.duration_myr,
                args.snapshot_interval_myr,
                args.dbl_h5_interval_myr,
                args.particle_interval_myr,
                args.particles_per_injection,
            )

    render_readme(
        output,
        cases,
        variants,
        args.grid,
        args.duration_myr,
        args.snapshot_interval_myr,
        args.dbl_h5_interval_myr,
        args.particle_interval_myr,
        args.particles_per_injection,
    )
    print(f"Rendered {len(cases) * len(variants)} config bundle(s) under {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
