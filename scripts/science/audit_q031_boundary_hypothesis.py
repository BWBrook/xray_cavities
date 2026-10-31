#!/usr/bin/env python3
"""Audit the Q-031 boundary-inflow closure hypothesis from compact local evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
NATIVE_ROOT = ROOT / "docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis"
WHOLE_GRID = ROOT / "docs/science/assets/whole_grid_energy_closure_2026-10-21/whole_grid_energy_comparison.csv"
OUTPUT = ROOT / "docs/science/assets/q031_boundary_hypothesis_2026-10-31"
ENVIRONMENTS = {
    "C": ROOT / "env/extracted/environments/tabulated/tabulated_cosmo_002003.csv",
    "G": ROOT / "env/extracted/environments/tabulated/tabulated_cosmo_002031.csv",
}
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
POWER_ONE_SIDED = {"HI": 1.0e45, "LO": 1.0e43}
KPC_CM = 3.0856775814913673e21
LIGHT_SPEED_CM_S = 2.99792458e10
SECONDS_PER_MYR = 365.25 * 86400 * 1.0e6
JET_SPEED_CM_S = 0.1 * LIGHT_SPEED_CM_S
JET_HALF_ANGLE_RAD = math.radians(15.0)
JET_SOLID_ANGLE_SR = 2.0 * math.pi * (1.0 - math.cos(JET_HALF_ANGLE_RAD))
JET_INJECTION_RADIUS_CM = 0.75 * KPC_CM
JET_AREA_CM2 = JET_SOLID_ANGLE_SR * JET_INJECTION_RADIUS_CM**2
GAMMA = 5.0 / 3.0
FACE_GEOMETRY_KPC = {
    "x_y": (200.0, 200.0, 250.0),
    "z": (250.0, 200.0, 200.0),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def interpolate(values: np.ndarray, radius_cm: np.ndarray, target_cm: np.ndarray | float) -> np.ndarray | float:
    return np.interp(target_cm, radius_cm, values)


def load_environment(path: Path) -> dict[str, np.ndarray]:
    values = np.loadtxt(path, dtype=float, ndmin=2)
    radius = values[:, 0]
    gravity = 0.5 * (np.abs(values[:, 4]) + np.abs(values[:, 5]))
    potential = np.concatenate(([0.0], np.cumsum(0.5 * (gravity[:-1] + gravity[1:]) * np.diff(radius))))
    return {"radius": radius, "density": values[:, 1], "pressure": values[:, 2], "potential": potential}


def face_scenarios(environment: str, profile: dict[str, np.ndarray], samples: int) -> list[dict]:
    rows = []
    for face, (fixed_kpc, extent_a_kpc, extent_b_kpc) in FACE_GEOMETRY_KPC.items():
        a = (np.arange(samples, dtype=float) + 0.5) * extent_a_kpc / samples
        b = (np.arange(samples, dtype=float) + 0.5) * extent_b_kpc / samples
        radius = np.sqrt(fixed_kpc**2 + a[:, None] ** 2 + b[None, :] ** 2) * KPC_CM
        density = interpolate(profile["density"], profile["radius"], radius)
        pressure = interpolate(profile["pressure"], profile["radius"], radius)
        potential = interpolate(profile["potential"], profile["radius"], radius)
        specific = GAMMA / (GAMMA - 1.0) * pressure / density + potential
        for weighting, value in (
            ("area", float(np.mean(specific))),
            ("density", float(np.sum(specific * density) / np.sum(density))),
        ):
            rows.append(
                {
                    "environment": environment,
                    "face_family": face,
                    "weighting_scenario": weighting,
                    "fixed_coordinate_kpc": fixed_kpc,
                    "transverse_extent_a_kpc": extent_a_kpc,
                    "transverse_extent_b_kpc": extent_b_kpc,
                    "specific_enthalpy_plus_potential_erg_g": value,
                    "quadrature_midpoints_per_axis": samples,
                    "status": "scenario_not_measured_mass_flux_weighting",
                }
            )
    return rows


def nozzle_prediction(case: str, profile: dict[str, np.ndarray]) -> dict:
    power = POWER_ONE_SIDED[case.split("-")[1]]
    density_at_inlet = float(profile["density"][0])
    pressure_at_inlet = float(profile["pressure"][0])
    l1b_cm = math.sqrt(2.0 * power / (density_at_inlet * JET_SPEED_CM_S**3 * JET_SOLID_ANGLE_SR))
    density_at_l1b = float(interpolate(profile["density"], profile["radius"], l1b_cm))
    density_surface = density_at_l1b * (l1b_cm / JET_INJECTION_RADIUS_CM) ** 2
    pressure_surface = pressure_at_inlet * (density_surface / density_at_l1b) ** GAMMA
    mass_flux_bipolar = 2.0 * density_surface * JET_SPEED_CM_S * JET_AREA_CM2
    kinetic_power_bipolar = 0.5 * mass_flux_bipolar * JET_SPEED_CM_S**2
    enthalpy_power_bipolar = 2.0 * GAMMA / (GAMMA - 1.0) * pressure_surface * JET_SPEED_CM_S * JET_AREA_CM2
    nominal_power_bipolar = 2.0 * power
    return {
        "case": case,
        "one_sided_configured_power_erg_s": power,
        "l1b_kpc": l1b_cm / KPC_CM,
        "density_at_l1b_over_density_at_inlet": density_at_l1b / density_at_inlet,
        "nozzle_surface_density_g_cm3": density_surface,
        "nozzle_surface_pressure_dyn_cm2": pressure_surface,
        "analytic_bipolar_mass_flux_g_s": mass_flux_bipolar,
        "analytic_bipolar_mass_per_10myr_g": mass_flux_bipolar * 10.0 * SECONDS_PER_MYR,
        "analytic_bipolar_kinetic_power_erg_s": kinetic_power_bipolar,
        "analytic_bipolar_enthalpy_power_erg_s": enthalpy_power_bipolar,
        "analytic_total_power_over_configured_bipolar_power": (kinetic_power_bipolar + enthalpy_power_bipolar) / nominal_power_bipolar,
        "status": "continuum_source_prediction_not_measured_discrete_nozzle_flux",
    }


def load_native_rows() -> dict[tuple[str, int], dict]:
    selected = {}
    for case in CASES:
        path = NATIVE_ROOT / case / "native_energy_selected_age.csv"
        with path.open(newline="") as handle:
            rows = csv.DictReader(handle)
            for row in rows:
                if row["side"] == "bipolar_total" and row["partition_method"] == "binary_threshold_1e-3":
                    selected[(case, int(row["snapshot_index"]))] = row
    return selected


def load_whole_grid_rows() -> dict[tuple[str, int], dict]:
    with WHOLE_GRID.open(newline="") as handle:
        return {(row["case"], int(row["snapshot_index"])): row for row in csv.DictReader(handle)}


def git_state(path: Path) -> dict:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(path), *args], check=True, text=True, capture_output=True
        ).stdout.strip()

    status = run("status", "--short", "--branch")
    return {"path": str(path), "commit": run("rev-parse", "HEAD"), "status_short_branch": status, "dirty": len(status.splitlines()) > 1}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--jet-setup", type=Path, default=Path("/Users/bwbrook/git/utas-agn/jet-setup"))
    parser.add_argument("--pluto", type=Path, default=Path("/Users/bwbrook/git/utas-agn/pluto"))
    parser.add_argument("--face-samples", type=int, default=1000)
    args = parser.parse_args()
    if args.face_samples < 10:
        raise ValueError("face-samples must be at least 10")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    profiles = {environment: load_environment(path) for environment, path in ENVIRONMENTS.items()}
    face_rows = [row for environment in ("C", "G") for row in face_scenarios(environment, profiles[environment], args.face_samples)]
    nozzle_rows = [nozzle_prediction(case, profiles[case[0]]) for case in CASES]
    nozzle = {row["case"]: row for row in nozzle_rows}
    native = load_native_rows()
    whole = load_whole_grid_rows()
    scenario_values = {
        environment: [row["specific_enthalpy_plus_potential_erg_g"] for row in face_rows if row["environment"] == environment]
        for environment in ("C", "G")
    }

    age_rows = []
    for case in CASES:
        for index in (10, 20, 30, 40, 50):
            key = (case, index)
            if key not in native:
                continue
            nr = native[key]
            wr = whole[key]
            time_myr = float(nr["actual_time_myr"])
            mass_delta = float(nr["current_mass_g"]) - float(nr["initial_mass_g"])
            analytic_jet_mass = nozzle[case]["analytic_bipolar_mass_flux_g_s"] * time_myr * SECONDS_PER_MYR
            inferred_boundary_mass = mass_delta - analytic_jet_mass
            delta_energy = float(wr["delta_total_erg"])
            nominal_energy = float(wr["injected_energy_erg"])
            corrected = [
                (delta_energy - inferred_boundary_mass * specific) / nominal_energy
                for specific in scenario_values[case[0]]
            ]
            age_rows.append(
                {
                    "case": case,
                    "snapshot_index": index,
                    "actual_time_myr": time_myr,
                    "observed_whole_grid_mass_delta_g": mass_delta,
                    "analytic_continuum_jet_mass_g": analytic_jet_mass,
                    "inferred_boundary_mass_g": inferred_boundary_mass,
                    "observed_whole_grid_energy_delta_erg": delta_energy,
                    "configured_nominal_jet_energy_erg": nominal_energy,
                    "uncorrected_energy_over_nominal": delta_energy / nominal_energy,
                    "excess_over_nominal_per_observed_mass_delta_erg_g": (delta_energy - nominal_energy) / mass_delta,
                    "boundary_corrected_ratio_scenario_min": min(corrected),
                    "boundary_corrected_ratio_scenario_max": max(corrected),
                    "status": "endpoint_mass_times_face_specific_energy_scenario_not_time_integrated_solver_flux",
                }
            )

    paired_rows = []
    age_lookup = {(row["case"], row["snapshot_index"]): row for row in age_rows}
    for environment in ("C", "G"):
        for index in (10, 20, 30, 40, 50):
            hi_key, lo_key = (f"{environment}-HI", index), (f"{environment}-LO", index)
            if hi_key not in age_lookup or lo_key not in age_lookup:
                continue
            hi, lo = age_lookup[hi_key], age_lookup[lo_key]
            observed = hi["observed_whole_grid_mass_delta_g"] - lo["observed_whole_grid_mass_delta_g"]
            predicted = hi["analytic_continuum_jet_mass_g"] - lo["analytic_continuum_jet_mass_g"]
            paired_rows.append(
                {
                    "environment": environment,
                    "snapshot_index": index,
                    "hi_actual_time_myr": hi["actual_time_myr"],
                    "lo_actual_time_myr": lo["actual_time_myr"],
                    "observed_hi_minus_lo_mass_delta_g": observed,
                    "analytic_nozzle_hi_minus_lo_mass_g": predicted,
                    "observed_over_analytic_nozzle_difference": observed / predicted,
                    "status": "paired_global_difference_not_identified_as_jet_mass",
                }
            )

    output_files = {
        "face_specific_energy_scenarios.csv": face_rows,
        "age_boundary_correction_scenarios.csv": age_rows,
        "analytic_nozzle_prediction.csv": nozzle_rows,
        "paired_mass_comparison.csv": paired_rows,
    }
    for name, rows in output_files.items():
        write_csv(args.output_dir / name, rows)

    source_files = [WHOLE_GRID, *ENVIRONMENTS.values()]
    source_files.extend(NATIVE_ROOT / case / "native_energy_selected_age.csv" for case in CASES)
    support_files = [
        ROOT / "docs/science/assets/c_hi_fullgrid_startup_2026-05-19/config/definitions_overrides.json",
        ROOT / "docs/science/assets/stewart_cluster_asset_restore_c_lo_preflight_2026-07-03/rendered_c_lo_config/C-LO/particles/definitions_overrides.json",
        ROOT / "docs/science/assets/g_hi_full_history_production_2026-08-20/rendered_config/G-HI/particles/definitions_overrides.json",
        ROOT / "docs/science/assets/g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/remote_stage/rendered_g_lo_config/G-LO/particles/definitions_overrides.json",
        ROOT / "docs/science/assets/g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/remote_stage/completion_evidence/run_logs/pluto.0.log",
    ]
    provenance = {
        "status": "compact_hypothesis_audit_complete_solver_flux_unmeasured",
        "scope": "19 retained selected-age whole-grid rows; no raw HDF5 reread and no remote work",
        "methods": {
            "potential": "centre-zero trapezoidal integral of absolute tabulated gravity",
            "boundary_specific_energy": "gamma/(gamma-1)*p/rho + phi evaluated on continuous rectangular face quadrature",
            "boundary_correction": "endpoint inferred boundary mass times one of four face/weighting scenarios",
            "nozzle": "continuum DENSITY_LENGTH_SCALE source prediction; discrete Cartesian nozzle flux unmeasured",
        },
        "interpretation_limits": [
            "face area and density weightings are scenarios, not uncertainty bounds or measured mass-flux weights",
            "endpoint mass does not identify the time-integrated outer-boundary energy flux",
            "HI-minus-LO global mass difference does not independently identify jet mass",
            "configured power times age is a nominal source target, not a measured numerical source accumulator",
            "local source repositories are contextual evidence and are not asserted to be the exact production binary",
        ],
        "input_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in source_files + support_files},
        "script_sha256": sha256(Path(__file__)),
        "local_source_repositories": {
            "jet_setup": git_state(args.jet_setup),
            "pluto": git_state(args.pluto),
        },
    }
    provenance_path = args.output_dir / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    manifest_paths = [args.output_dir / name for name in output_files] + [provenance_path]
    with (args.output_dir / "manifest.sha256").open("w") as handle:
        for path in sorted(manifest_paths):
            handle.write(f"{sha256(path)}  {path.name}\n")

    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "face_rows": len(face_rows),
                "age_rows": len(age_rows),
                "nozzle_rows": len(nozzle_rows),
                "paired_rows": len(paired_rows),
                "c_lo_50_corrected_range": [
                    next(row for row in age_rows if row["case"] == "C-LO" and row["snapshot_index"] == 50)["boundary_corrected_ratio_scenario_min"],
                    next(row for row in age_rows if row["case"] == "C-LO" and row["snapshot_index"] == 50)["boundary_corrected_ratio_scenario_max"],
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
