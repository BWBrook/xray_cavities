#!/usr/bin/env python3
"""Compare observational cavity ages and their inferred powers in four cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import shutil
import tarfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
XRAY_ROOT = (
    ASSET_ROOT
    / "four_case_selected_age_observables_2026-08-26"
    / "four_case_xray_complete/review_products/products"
)
FLUID_ROOT = ASSET_ROOT / "four_case_fluid_snapshot_census_2026-08-25"
SPECTRAL_ROOT = ASSET_ROOT / "four_case_boundary_spectral_field_review_2026-08-28"
DEFAULT_OUTPUT_ROOT = ASSET_ROOT / "four_case_cavity_age_method_comparison_2026-08-28"
AXIAL_ARCHIVE = (
    FLUID_ROOT / "remote_logs/four_case_fluid_snapshot_census_2026-08-25.tar.gz"
)
GROUP_ENVIRONMENT = (
    ASSET_ROOT
    / "g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12"
    / "remote_stage/rendered_g_lo_config/G-LO/particles/tabulated_cosmo_002031.csv"
)

CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
VIEWS = ("0deg", "45deg", "90deg")
SIDES = ("negative_z", "positive_z")
AGE_METHODS = (
    "true_source_age",
    "sound_crossing_age",
    "buoyant_rise_age",
    "refill_age",
    "shock_kinematic_age",
    "spectral_age_mean_pressure",
    "spectral_age_emissivity_weighted",
)
CASE_POWER_ERG_S = {
    "C-HI": 2.0e45,
    "C-LO": 2.0e43,
    "G-HI": 2.0e45,
    "G-LO": 2.0e43,
}
EXCLUDED_SCIENCE_CASE_AGES = {("G-HI", 50)}

GAMMA_AMBIENT = 5.0 / 3.0
DRAG_COEFFICIENT = 0.75
C_CM_S = 2.99792458e10
C_KM_S = C_CM_S / 1.0e5
KPC_CM = 3.085677581491367e21
SECONDS_PER_MYR = 365.25 * 24.0 * 3600.0 * 1.0e6
ENERGY_FACTORS = {"2.5pV": 2.5, "4pV": 4.0}


class ComparisonError(RuntimeError):
    """Raised when an accepted compact input violates the comparison contract."""


def read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ComparisonError(f"refusing to write an empty table: {path.name}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    lines = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.name != "local_asset_manifest.sha256":
            lines.append(f"{sha256_file(path)}  {path.name}")
    (root / "local_asset_manifest.sha256").write_text("\n".join(lines) + "\n")


def finite(value: Any, context: str, *, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ComparisonError(f"{context} must be numeric") from exc
    if not math.isfinite(result):
        raise ComparisonError(f"{context} must be finite")
    if positive and result <= 0.0:
        raise ComparisonError(f"{context} must be positive")
    return result


def bool_value(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _archive_profile(
    archive: tarfile.TarFile, case: str, snapshot_index: int
) -> list[dict[str, str]]:
    member = f"./{case}/per_snapshot/snapshot_{snapshot_index:04d}_axial_profile.csv"
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ComparisonError(f"fluid archive lacks {member}")
    return list(csv.DictReader(io.TextIOWrapper(extracted)))


def load_initial_atmospheres() -> dict[str, dict[str, np.ndarray]]:
    profiles: dict[str, dict[str, np.ndarray]] = {}
    with tarfile.open(AXIAL_ARCHIVE, "r:gz") as archive:
        for case in CASES:
            rows = [
                row
                for row in _archive_profile(archive, case, 0)
                if finite(row["z_kpc"], f"{case} z") >= 1.0
            ]
            radius = np.asarray([finite(row["z_kpc"], f"{case} z") for row in rows])
            density = np.asarray(
                [finite(row["baseline_rho_code"], f"{case} rho", positive=True) for row in rows]
            )
            pressure = np.asarray(
                [finite(row["baseline_pressure_code"], f"{case} p", positive=True) for row in rows]
            )
            if not np.all(np.diff(radius) > 0.0):
                raise ComparisonError(f"{case} initial radial profile is not ordered")
            sound = np.sqrt(GAMMA_AMBIENT * pressure / density) * C_KM_S
            pressure_gradient = np.gradient(pressure, radius, edge_order=2)
            gravity = -pressure_gradient / density * C_CM_S**2 / KPC_CM
            if np.any(gravity <= 0.0):
                raise ComparisonError(f"{case} initial hydrostatic gravity is non-positive")
            profiles[case] = {
                "radius_kpc": radius,
                "density_code": density,
                "pressure_code": pressure,
                "sound_speed_km_s": sound,
                "gravity_cm_s2": gravity,
            }

    for first, second in (("C-HI", "C-LO"), ("G-HI", "G-LO")):
        for field in ("radius_kpc", "density_code", "pressure_code"):
            if not np.allclose(profiles[first][field], profiles[second][field], rtol=1e-10, atol=0.0):
                raise ComparisonError(f"matched environment profiles disagree: {first}/{second} {field}")
    return profiles


def validate_group_atmosphere(profile: Mapping[str, np.ndarray]) -> dict[str, float]:
    raw = np.loadtxt(GROUP_ENVIRONMENT)
    raw_radius_kpc = raw[:, 0] / KPC_CM
    raw_sound_km_s = np.sqrt(GAMMA_AMBIENT * raw[:, 2] / raw[:, 1]) / 1.0e5
    raw_gravity = np.abs(raw[:, 4])
    radius = profile["radius_kpc"]
    selected = (radius >= 1.0) & (radius <= 240.0)
    expected_sound = np.interp(radius[selected], raw_radius_kpc, raw_sound_km_s)
    expected_gravity = np.interp(radius[selected], raw_radius_kpc, raw_gravity)
    sound_relative = np.abs(profile["sound_speed_km_s"][selected] - expected_sound) / expected_sound
    gravity_relative = np.abs(profile["gravity_cm_s2"][selected] - expected_gravity) / expected_gravity
    return {
        "sound_speed_max_relative_difference": float(np.max(sound_relative)),
        "gravity_median_relative_difference": float(np.median(gravity_relative)),
        "gravity_max_relative_difference": float(np.max(gravity_relative)),
    }


def atmosphere_at(
    profile: Mapping[str, np.ndarray], radius_kpc: float
) -> tuple[float, float]:
    radius = profile["radius_kpc"]
    if radius_kpc < float(radius[0]) or radius_kpc > float(radius[-1]):
        raise ComparisonError(f"cavity radius {radius_kpc} kpc lies outside atmosphere profile")
    sound = float(np.interp(radius_kpc, radius, profile["sound_speed_km_s"]))
    gravity = float(np.interp(radius_kpc, radius, profile["gravity_cm_s2"]))
    if sound <= 0.0 or gravity <= 0.0:
        raise ComparisonError("interpolated atmosphere is not physical")
    return sound, gravity


def sound_age_myr(radius_kpc: float, sound_speed_km_s: float) -> float:
    return radius_kpc * KPC_CM / (sound_speed_km_s * 1.0e5) / SECONDS_PER_MYR


def buoyant_age_myr(
    radius_kpc: float,
    gravity_cm_s2: float,
    volume_kpc3: float,
    cross_section_kpc2: float,
) -> tuple[float, float]:
    terminal_velocity = math.sqrt(
        2.0
        * gravity_cm_s2
        * volume_kpc3
        * KPC_CM**3
        / (DRAG_COEFFICIENT * cross_section_kpc2 * KPC_CM**2)
    )
    age = radius_kpc * KPC_CM / terminal_velocity / SECONDS_PER_MYR
    return age, terminal_velocity / 1.0e5


def refill_age_myr(effective_radius_kpc: float, gravity_cm_s2: float) -> float:
    return (
        2.0
        * math.sqrt(effective_radius_kpc * KPC_CM / gravity_cm_s2)
        / SECONDS_PER_MYR
    )


def _valid_energy_rows(case: str) -> dict[tuple[int, str, str], dict[str, str]]:
    rows = read_rows(XRAY_ROOT / case / "xray_cavity_energy.csv")
    result: dict[tuple[int, str, str], dict[str, str]] = {}
    for row in rows:
        age = int(row["snapshot_index"])
        if (
            bool_value(row["quantitative_energy_valid"])
            and row["volume_depth_assumption"] == "geometric_depth"
            and row["energy_model"] == "pV"
            and (case, age) not in EXCLUDED_SCIENCE_CASE_AGES
        ):
            result[(age, row["view"], row["side"])] = row
    return result


def build_xray_geometry(
    atmospheres: Mapping[str, Mapping[str, np.ndarray]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for case in CASES:
        energy_rows = _valid_energy_rows(case)
        components = read_rows(XRAY_ROOT / case / "xray_component_summary.csv")
        valid_keys = sorted(
            {
                (age, view)
                for age, view, side in energy_rows
                if side == "bipolar_total"
            }
        )
        for age, view in valid_keys:
            selected = [
                row
                for row in components
                if int(row["snapshot_index"]) == age and row["view"] == view
            ]
            if len(selected) != 2 or any(bool_value(row["crosses_z_zero"]) for row in selected):
                raise ComparisonError(f"accepted cavity topology is not two-sided: {case}/{age}/{view}")
            by_side: dict[str, dict[str, str]] = {}
            for row in selected:
                z = finite(row["centroid_z_kpc"], "component centroid z")
                side = "negative_z" if z < 0.0 else "positive_z"
                if side in by_side:
                    raise ComparisonError(f"duplicate component side: {case}/{age}/{view}/{side}")
                by_side[side] = row
            if set(by_side) != set(SIDES):
                raise ComparisonError(f"missing component side: {case}/{age}/{view}")

            for side in SIDES:
                component = by_side[side]
                energy = energy_rows[(age, view, side)]
                horizontal = finite(component["centroid_horizontal_kpc"], "component horizontal")
                z = finite(component["centroid_z_kpc"], "component z")
                projected_radius = math.hypot(horizontal, z)
                major = finite(component["major_semiaxis_kpc"], "component major", positive=True)
                minor = finite(component["minor_semiaxis_kpc"], "component minor", positive=True)
                depth = finite(component["geometric_depth_kpc"], "component depth", positive=True)
                volume = finite(component["volume_geometric_depth_kpc3"], "component volume", positive=True)
                energy_volume = finite(energy["volume_kpc3"], "energy volume", positive=True)
                if not math.isclose(volume, energy_volume, rel_tol=1e-10, abs_tol=0.0):
                    raise ComparisonError(f"component/energy volume mismatch: {case}/{age}/{view}/{side}")
                cross_section = math.pi * minor * depth
                effective_radius = (3.0 * volume / (4.0 * math.pi)) ** (1.0 / 3.0)
                sound_speed, gravity = atmosphere_at(atmospheres[case], projected_radius)
                sound_age = sound_age_myr(projected_radius, sound_speed)
                buoy_age, terminal_speed = buoyant_age_myr(
                    projected_radius, gravity, volume, cross_section
                )
                refill_age = refill_age_myr(effective_radius, gravity)
                output.append(
                    {
                        "case": case,
                        "snapshot_index": age,
                        "actual_time_myr": finite(component["actual_time_myr"], "actual time"),
                        "view": view,
                        "side": side,
                        "projected_cavity_radius_kpc": projected_radius,
                        "major_semiaxis_kpc": major,
                        "minor_semiaxis_kpc": minor,
                        "geometric_depth_kpc": depth,
                        "volume_kpc3": volume,
                        "cross_section_kpc2": cross_section,
                        "effective_radius_kpc": effective_radius,
                        "initial_atmosphere_sound_speed_km_s": sound_speed,
                        "initial_atmosphere_gravity_cm_s2": gravity,
                        "terminal_buoyant_speed_km_s": terminal_speed,
                        "terminal_speed_over_sound_speed": terminal_speed / sound_speed,
                        "sound_crossing_age_myr": sound_age,
                        "buoyant_rise_age_myr": buoy_age,
                        "buoyant_to_sound_age_ratio": buoy_age / sound_age,
                        "refill_age_myr": refill_age,
                        "pV_erg": finite(energy["energy_erg"], "pV energy", positive=True),
                        "pressure_dyn_cm2": finite(energy["pressure_dyn_cm2"], "pressure", positive=True),
                        "pressure_role": energy["pressure_role"],
                        "geometry_role": "xray_component_geometric_depth",
                        "projection_role": "projected_observer_plane_distance",
                    }
                )
    if len(output) % 2 != 0:
        raise ComparisonError("X-ray geometry surface is not bipolar")
    return output


def _group_by_key(
    rows: Iterable[Mapping[str, Any]], fields: Sequence[str]
) -> dict[tuple[Any, ...], list[Mapping[str, Any]]]:
    result: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        result[tuple(row[field] for field in fields)].append(row)
    return result


def load_shocks() -> dict[tuple[str, int, str], dict[str, str]]:
    result: dict[tuple[str, int, str], dict[str, str]] = {}
    for row in read_rows(FLUID_ROOT / "primary_shock_timeseries.csv"):
        key = (row["case"], int(row["snapshot_index"]), row["side"])
        result[key] = row
    return result


def load_spectral() -> dict[tuple[str, int, str, str], dict[str, str]]:
    treatment_map = {
        "tracer_lobe_mean_pressure": "spectral_age_mean_pressure",
        "emissivity_weighted_1p4ghz": "spectral_age_emissivity_weighted",
    }
    result: dict[tuple[str, int, str, str], dict[str, str]] = {}
    for row in read_rows(SPECTRAL_ROOT / "spectral_age_field_comparison.csv"):
        method = treatment_map[row["field_treatment"]]
        result[(row["case"], int(row["snapshot_index"]), row["view"], method)] = row
    return result


def shock_side_age(row: Mapping[str, str]) -> tuple[float | None, str]:
    if row["status"] != "detected":
        return None, "shock_not_detected"
    speed = finite(row["shock_speed_km_s"] or 0.0, "shock speed")
    mach = finite(row["mach_kinematic"] or 0.0, "shock Mach")
    if speed <= 0.0:
        return None, "zero_or_negative_shock_speed"
    if mach <= 1.0:
        return None, "subsonic_disturbance_not_shock"
    distance = finite(row["shock_distance_kpc"], "shock distance", positive=True)
    return sound_age_myr(distance, speed), "quantitative_supersonic_shock"


def build_age_estimates(
    geometry_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped = _group_by_key(geometry_rows, ("case", "snapshot_index", "view"))
    shocks = load_shocks()
    spectral = load_spectral()
    output: list[dict[str, Any]] = []
    for (case, age, view), sides in sorted(grouped.items()):
        side_rows = {row["side"]: row for row in sides}
        if set(side_rows) != set(SIDES):
            raise ComparisonError(f"age surface lacks both sides: {case}/{age}/{view}")
        actual_time = finite(side_rows["negative_z"]["actual_time_myr"], "actual time", positive=True)

        method_values: list[dict[str, Any]] = [
            {
                "method": "true_source_age",
                "negative": actual_time,
                "positive": actual_time,
                "combined": actual_time,
                "limit": "none",
                "status": "quantitative_simulation_truth",
                "fitted_break_ghz": "",
                "magnetic_field_ug": "",
            }
        ]
        for method, field in (
            ("sound_crossing_age", "sound_crossing_age_myr"),
            ("buoyant_rise_age", "buoyant_rise_age_myr"),
            ("refill_age", "refill_age_myr"),
        ):
            negative = finite(side_rows["negative_z"][field], field, positive=True)
            positive = finite(side_rows["positive_z"][field], field, positive=True)
            method_values.append(
                {
                    "method": method,
                    "negative": negative,
                    "positive": positive,
                    "combined": 0.5 * (negative + positive),
                    "limit": "none",
                    "status": "quantitative_xray_component_geometry",
                    "fitted_break_ghz": "",
                    "magnetic_field_ug": "",
                }
            )

        shock_values = {
            side: shock_side_age(shocks[(case, int(age), side)]) for side in SIDES
        }
        if all(shock_values[side][0] is not None for side in SIDES):
            negative_shock = float(shock_values["negative_z"][0])
            positive_shock = float(shock_values["positive_z"][0])
            combined_shock: float | str = 0.5 * (negative_shock + positive_shock)
            shock_status = "quantitative_bipolar_supersonic_shock"
        else:
            negative_shock = shock_values["negative_z"][0] or ""
            positive_shock = shock_values["positive_z"][0] or ""
            combined_shock = ""
            shock_status = ";".join(sorted({value[1] for value in shock_values.values()}))
        method_values.append(
            {
                "method": "shock_kinematic_age",
                "negative": negative_shock,
                "positive": positive_shock,
                "combined": combined_shock,
                "limit": "not_available" if combined_shock == "" else "none",
                "status": shock_status,
                "fitted_break_ghz": "",
                "magnetic_field_ug": "",
            }
        )

        for method in (
            "spectral_age_mean_pressure",
            "spectral_age_emissivity_weighted",
        ):
            row = spectral[(case, int(age), view, method)]
            value = finite(row["spectral_age_myr"], "spectral age", positive=True)
            limit = (
                "upper_limit"
                if row["spectral_age_limit_direction"] == "spectral_age_upper_limit"
                else "none"
            )
            method_values.append(
                {
                    "method": method,
                    "negative": "",
                    "positive": "",
                    "combined": value,
                    "limit": limit,
                    "status": row["science_interpretation"],
                    "fitted_break_ghz": finite(row["fitted_break_ghz"], "break", positive=True),
                    "magnetic_field_ug": finite(row["magnetic_field_ug"], "field", positive=True),
                }
            )

        if {value["method"] for value in method_values} != set(AGE_METHODS):
            raise ComparisonError(f"age method coverage is incomplete: {case}/{age}/{view}")
        for value in method_values:
            combined = value["combined"]
            output.append(
                {
                    "case": case,
                    "snapshot_index": age,
                    "actual_time_myr": actual_time,
                    "view": view,
                    "age_method": value["method"],
                    "negative_side_age_myr": value["negative"],
                    "positive_side_age_myr": value["positive"],
                    "combined_age_myr": combined,
                    "age_to_true_ratio": "" if combined == "" else float(combined) / actual_time,
                    "age_limit_direction": value["limit"],
                    "fitted_break_ghz": value["fitted_break_ghz"],
                    "magnetic_field_ug": value["magnetic_field_ug"],
                    "status": value["status"],
                    "G_HI_50_excluded": case == "G-HI" and int(age) == 50,
                }
            )
    return output


def build_cavity_powers(
    geometry_rows: Sequence[Mapping[str, Any]],
    age_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    geometry = _group_by_key(geometry_rows, ("case", "snapshot_index", "view"))
    output: list[dict[str, Any]] = []
    side_methods = {
        "sound_crossing_age",
        "buoyant_rise_age",
        "refill_age",
        "shock_kinematic_age",
    }
    for age_row in age_rows:
        key = (age_row["case"], age_row["snapshot_index"], age_row["view"])
        sides = {row["side"]: row for row in geometry[key]}
        total_pv = sum(finite(sides[side]["pV_erg"], "side pV", positive=True) for side in SIDES)
        for energy_model, factor in ENERGY_FACTORS.items():
            energy = factor * total_pv
            age = age_row["combined_age_myr"]
            if age == "":
                power: float | str = ""
                ratio: float | str = ""
                power_limit = "not_available"
                status = f"excluded_age_method:{age_row['status']}"
            else:
                if age_row["age_method"] in side_methods:
                    side_ages = {
                        "negative_z": age_row["negative_side_age_myr"],
                        "positive_z": age_row["positive_side_age_myr"],
                    }
                    if any(side_ages[side] == "" for side in SIDES):
                        raise ComparisonError(f"side ages missing for quantitative method: {key}")
                    power = sum(
                        factor
                        * finite(sides[side]["pV_erg"], "side pV", positive=True)
                        / (finite(side_ages[side], "side age", positive=True) * SECONDS_PER_MYR)
                        for side in SIDES
                    )
                else:
                    power = energy / (finite(age, "combined age", positive=True) * SECONDS_PER_MYR)
                ratio = power / CASE_POWER_ERG_S[age_row["case"]]
                power_limit = (
                    "lower_limit"
                    if age_row["age_limit_direction"] == "upper_limit"
                    else "none"
                )
                status = "quantitative_censored" if power_limit == "lower_limit" else "quantitative"
            output.append(
                {
                    "case": age_row["case"],
                    "snapshot_index": age_row["snapshot_index"],
                    "actual_time_myr": age_row["actual_time_myr"],
                    "view": age_row["view"],
                    "cavity_energy_model": energy_model,
                    "cavity_energy_erg": energy,
                    "age_method": age_row["age_method"],
                    "combined_age_myr": age,
                    "age_limit_direction": age_row["age_limit_direction"],
                    "inferred_cavity_power_erg_s": power,
                    "known_bipolar_power_erg_s": CASE_POWER_ERG_S[age_row["case"]],
                    "inferred_to_known_power_ratio": ratio,
                    "power_limit_direction": power_limit,
                    "status": status,
                    "pressure_role": "side_specific_tracer_shell_proxy",
                    "volume_role": "xray_component_geometric_depth",
                }
            )
    return output


def build_method_summary(
    age_rows: Sequence[Mapping[str, Any]],
    power_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    ages = _group_by_key(age_rows, ("case", "age_method"))
    powers = _group_by_key(power_rows, ("case", "age_method", "cavity_energy_model"))
    output: list[dict[str, Any]] = []
    for case in CASES:
        for method in AGE_METHODS:
            selected_ages = ages[(case, method)]
            quantitative_ages = [row for row in selected_ages if row["combined_age_myr"] != ""]
            exact_ages = [
                row for row in quantitative_ages if row["age_limit_direction"] == "none"
            ]
            age_ratios = [
                finite(row["age_to_true_ratio"], "age ratio", positive=True)
                for row in exact_ages
            ]
            for energy_model in ENERGY_FACTORS:
                selected_powers = powers[(case, method, energy_model)]
                quantitative_powers = [row for row in selected_powers if row["inferred_cavity_power_erg_s"] != ""]
                exact_powers = [
                    row for row in quantitative_powers if row["power_limit_direction"] == "none"
                ]
                power_ratios = [
                    finite(row["inferred_to_known_power_ratio"], "power ratio", positive=True)
                    for row in exact_powers
                ]
                output.append(
                    {
                        "case": case,
                        "age_method": method,
                        "cavity_energy_model": energy_model,
                        "available_age_rows": len(quantitative_ages),
                        "exact_age_rows": len(exact_ages),
                        "total_cavity_rows": len(selected_ages),
                        "spectral_age_upper_limit_rows": sum(
                            row["age_limit_direction"] == "upper_limit" for row in quantitative_ages
                        ),
                        "median_exact_age_to_true_ratio": ""
                        if not age_ratios
                        else float(np.median(age_ratios)),
                        "available_power_rows": len(quantitative_powers),
                        "exact_power_rows": len(exact_powers),
                        "power_lower_limit_rows": sum(
                            row["power_limit_direction"] == "lower_limit" for row in quantitative_powers
                        ),
                        "median_exact_inferred_to_known_power_ratio": ""
                        if not power_ratios
                        else float(np.median(power_ratios)),
                        "minimum_exact_inferred_to_known_power_ratio": ""
                        if not power_ratios
                        else min(power_ratios),
                        "maximum_exact_inferred_to_known_power_ratio": ""
                        if not power_ratios
                        else max(power_ratios),
                        "summary_role": "exact_values_only_with_censoring_counts_not_survival_analysis",
                    }
                )
    return output


METHOD_LABELS = {
    "true_source_age": "True age",
    "sound_crossing_age": "Sound crossing",
    "buoyant_rise_age": "Buoyant rise",
    "refill_age": "Refill",
    "shock_kinematic_age": "Shock kinematic",
    "spectral_age_mean_pressure": "Spectral, mean p",
    "spectral_age_emissivity_weighted": "Spectral, emiss. wtd.",
}
METHOD_COLORS = {
    "sound_crossing_age": "#0072B2",
    "buoyant_rise_age": "#D55E00",
    "refill_age": "#009E73",
    "shock_kinematic_age": "#CC0000",
    "spectral_age_mean_pressure": "#7A5195",
    "spectral_age_emissivity_weighted": "#00A6A6",
}


def _median_age_surface(
    rows: Sequence[Mapping[str, Any]], case: str, method: str
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row["case"] == case
        and row["age_method"] == method
        and row["combined_age_myr"] != ""
    ]
    grouped = _group_by_key(selected, ("snapshot_index",))
    output = []
    for (age,), values in sorted(grouped.items()):
        exact = [row for row in values if row["age_limit_direction"] == "none"]
        limits = [row for row in values if row["age_limit_direction"] == "upper_limit"]
        plotted = exact or limits
        output.append(
            {
                "age": finite(values[0]["actual_time_myr"], "actual time", positive=True),
                "estimate": float(
                    np.median(
                        [finite(row["combined_age_myr"], "age", positive=True) for row in plotted]
                    )
                ),
                "upper_limit": not exact,
                "upper_limit_estimate": ""
                if not limits
                else float(
                    np.median(
                        [finite(row["combined_age_myr"], "age", positive=True) for row in limits]
                    )
                ),
            }
        )
    return output


def plot_age_comparison(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.8), sharex=True, sharey=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        axis.plot([0, 55], [0, 55], color="0.45", linewidth=1.2, label="True age")
        for method, color in METHOD_COLORS.items():
            surface = _median_age_surface(rows, case, method)
            if not surface:
                continue
            axis.plot(
                [row["age"] for row in surface],
                [row["estimate"] for row in surface],
                color=color,
                linewidth=1.5,
                marker="o",
                markersize=5,
                label=METHOD_LABELS[method],
            )
            limits = [row for row in surface if row["upper_limit_estimate"] != ""]
            if limits:
                axis.scatter(
                    [row["age"] for row in limits],
                    [row["upper_limit_estimate"] for row in limits],
                    marker="v",
                    facecolors="white",
                    edgecolors=color,
                    s=65,
                    linewidths=1.5,
                    label="Spectral upper limit"
                    if method == "spectral_age_mean_pressure"
                    else None,
                    zorder=5,
                )
        axis.set_title(case)
        axis.set_xlim(0, 55)
        axis.set_ylim(0, 150)
        axis.grid(alpha=0.25)
    for axis in axes[-1, :]:
        axis.set_xlabel("True simulation age [Myr]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Inferred age [Myr]")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
    fig.suptitle("Cavity and radio age estimators (view medians)")
    fig.tight_layout(rect=(0, 0.12, 1, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_buoyancy_sound_ratio(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    colors = {"0deg": "#0072B2", "45deg": "#D55E00", "90deg": "#009E73"}
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), sharex=True, sharey=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        for view in VIEWS:
            selected = [row for row in rows if row["case"] == case and row["view"] == view]
            axis.scatter(
                [row["actual_time_myr"] for row in selected],
                [row["buoyant_to_sound_age_ratio"] for row in selected],
                color=colors[view],
                s=28,
                alpha=0.78,
                label=view,
            )
        axis.axhline(2.0, color="0.25", linestyle="--", linewidth=1.1)
        axis.set_title(case)
        axis.grid(alpha=0.25)
    for axis in axes[-1, :]:
        axis.set_xlabel("True simulation age [Myr]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Buoyant / sound age")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle("Buoyant age is not fixed at twice the sound-crossing age")
    fig.tight_layout(rect=(0, 0.09, 1, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_power_recovery(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    methods = list(AGE_METHODS)
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), sharex=True, sharey=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        for energy_model, marker, color, offset in (
            ("2.5pV", "o", "#0072B2", -0.10),
            ("4pV", "s", "#D55E00", 0.10),
        ):
            for index, method in enumerate(methods):
                selected = [
                    row
                    for row in rows
                    if row["case"] == case
                    and row["age_method"] == method
                    and row["cavity_energy_model"] == energy_model
                    and row["inferred_to_known_power_ratio"] != ""
                ]
                if not selected:
                    continue
                exact = [row for row in selected if row["power_limit_direction"] == "none"]
                limits = [row for row in selected if row["power_limit_direction"] == "lower_limit"]
                exact_values = [
                    finite(row["inferred_to_known_power_ratio"], "power ratio", positive=True)
                    for row in exact
                ]
                if exact_values:
                    x_values = np.full(len(exact_values), index + offset)
                    axis.scatter(x_values, exact_values, marker=marker, color=color, s=20, alpha=0.25)
                    axis.scatter(
                        [index + offset],
                        [float(np.median(exact_values))],
                        marker=marker,
                        color=color,
                        edgecolors="black",
                        linewidths=0.6,
                        s=70,
                        label=energy_model if index == 0 else None,
                        zorder=5,
                    )
                if limits:
                    axis.scatter(
                        np.full(len(limits), index + offset),
                        [
                            finite(row["inferred_to_known_power_ratio"], "power limit", positive=True)
                            for row in limits
                        ],
                        marker="^",
                        facecolors="white",
                        edgecolors=color,
                        linewidths=1.0,
                        s=34,
                        label="Lower limit" if case == "C-HI" and energy_model == "2.5pV" and index == 5 else None,
                        zorder=4,
                    )
        axis.axhline(1.0, color="0.25", linestyle="--", linewidth=1.1)
        axis.set_yscale("log")
        axis.set_title(case)
        axis.grid(alpha=0.2, axis="y")
    for axis in axes[-1, :]:
        axis.set_xticks(range(len(methods)))
        axis.set_xticklabels([METHOD_LABELS[method] for method in methods], rotation=35, ha="right")
    for axis in axes[:, 0]:
        axis.set_ylabel("Inferred / known bipolar jet power")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
    fig.suptitle("Cavity-power recovery under seven age treatments")
    fig.tight_layout(rect=(0, 0.18, 1, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run(output_root: Path, *, force: bool = False) -> dict[str, Any]:
    output_root = Path(output_root)
    if output_root.exists():
        if not force:
            raise ComparisonError(f"output root already exists: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    atmospheres = load_initial_atmospheres()
    atmosphere_validation = validate_group_atmosphere(atmospheres["G-LO"])
    geometry_rows = build_xray_geometry(atmospheres)
    age_rows = build_age_estimates(geometry_rows)
    power_rows = build_cavity_powers(geometry_rows, age_rows)
    summary_rows = build_method_summary(age_rows, power_rows)

    write_rows(output_root / "xray_cavity_age_geometry.csv", geometry_rows)
    write_rows(output_root / "age_method_comparison.csv", age_rows)
    write_rows(output_root / "cavity_power_method_comparison.csv", power_rows)
    write_rows(output_root / "age_power_method_summary.csv", summary_rows)
    plot_age_comparison(output_root / "age_estimator_comparison.png", age_rows)
    plot_buoyancy_sound_ratio(output_root / "buoyancy_to_sound_ratio.png", geometry_rows)
    plot_power_recovery(output_root / "cavity_power_recovery_by_age_method.png", power_rows)

    buoyancy_ratios = [finite(row["buoyant_to_sound_age_ratio"], "ratio", positive=True) for row in geometry_rows]
    shock_rows = [row for row in age_rows if row["age_method"] == "shock_kinematic_age"]
    spectral_rows = [row for row in age_rows if row["age_method"].startswith("spectral_age_")]
    metadata = {
        "status": "complete_four_case_cavity_age_method_comparison",
        "cases": list(CASES),
        "selected_ages_myr": list(AGES),
        "views": list(VIEWS),
        "excluded_science_case_ages": [
            {"case": case, "snapshot_index": age, "reason": "boundary_contaminated"}
            for case, age in sorted(EXCLUDED_SCIENCE_CASE_AGES)
        ],
        "age_methods": list(AGE_METHODS),
        "energy_models": ENERGY_FACTORS,
        "geometry_contract": {
            "distance": "projected distance from origin to X-ray component centroid",
            "volume": "geometric-depth X-ray component ellipsoid",
            "buoyant_cross_section": "pi times projected minor semiaxis times geometric line-of-sight depth",
            "refill_radius": "volume-equivalent spherical radius",
            "pressure": "accepted side-specific tracer-shell pressure proxy",
        },
        "atmosphere_contract": {
            "state": "initial static atmosphere",
            "minimum_profile_radius_kpc": 1.0,
            "central_exclusion_reason": "exclude the nozzle-regularised injection region",
            "sound_speed": "sqrt(gamma p0/rho0)",
            "gravity": "-(1/rho0) dp0/dr from the accepted initial axial profile",
            "gamma": GAMMA_AMBIENT,
            "group_tabulated_profile_validation": atmosphere_validation,
        },
        "shock_contract": {
            "age": "instantaneous shock distance divided by centred shock speed",
            "validity": "both sides detected with positive speed and kinematic Mach greater than one",
        },
        "spectral_contract": {
            "field_treatments": ["tracer_lobe_mean_pressure", "emissivity_weighted_1p4ghz"],
            "breaks_above_15_GHz": "spectral-age upper limits and cavity-power lower limits",
        },
        "row_counts": {
            "quantitative_cavity_views": len(geometry_rows) // 2,
            "xray_cavity_age_geometry": len(geometry_rows),
            "age_method_comparison": len(age_rows),
            "cavity_power_method_comparison": len(power_rows),
            "age_power_method_summary": len(summary_rows),
        },
        "buoyant_to_sound_age_ratio": {
            "minimum": min(buoyancy_ratios),
            "median": float(np.median(buoyancy_ratios)),
            "maximum": max(buoyancy_ratios),
        },
        "shock_age_rows": {
            "quantitative": sum(row["combined_age_myr"] != "" for row in shock_rows),
            "excluded": sum(row["combined_age_myr"] == "" for row in shock_rows),
        },
        "spectral_age_rows": {
            "total": len(spectral_rows),
            "upper_limits": sum(row["age_limit_direction"] == "upper_limit" for row in spectral_rows),
        },
        "input_provenance": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
            }
            for path in (
                AXIAL_ARCHIVE,
                GROUP_ENVIRONMENT,
                FLUID_ROOT / "primary_shock_timeseries.csv",
                SPECTRAL_ROOT / "spectral_age_field_comparison.csv",
                *(XRAY_ROOT / case / filename for case in CASES for filename in (
                    "xray_cavity_energy.csv",
                    "xray_component_summary.csv",
                )),
            )
        ],
    }
    write_json(output_root / "review_metadata.json", metadata)
    write_manifest(output_root)
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args.output_root, force=args.force)
    except (OSError, ValueError, ComparisonError) as exc:
        print(f"comparison_error={exc}")
        return 2
    print(f"status={result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
