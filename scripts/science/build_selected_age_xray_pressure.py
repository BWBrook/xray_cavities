#!/usr/bin/env python3
"""Build the observer-only pressure and cavity-enthalpy path for selected ages."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCIENCE_DIR = Path(__file__).resolve().parent
for import_root in (ROOT, SCIENCE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from scripts.science import build_three_case_cavity_recovery as recovery_builder
from scripts.science import three_case_cavity_recovery as recovery
from scripts.science.xray_pressure_deprojection import (
    component_orientation_rad,
    deproject_pressure,
    ellipsoid_average_pressure,
    pressure_at_radius,
)


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
VIEWS = ("0deg", "45deg", "90deg")
DEPTHS = ("minor", "geometric", "major")
ALPHAS = (("2.5pV", 2.5), ("4pV", 4.0))
KPC_CM = 3.0856775814913673e21
RADIAL_EDGES_KPC = np.arange(0.0, 185.0, 5.0)
DEPROJECTION_REGULARIZATION = 1.0e-6


class ProductError(ValueError):
    pass


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ProductError(f"duplicate or missing header in {path}")
        rows = list(reader)
    if not rows:
        raise ProductError(f"empty table: {path}")
    return rows


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ProductError(f"refusing to write empty table: {path}")
    fields = list(rows[0])
    if len(fields) != len(set(fields)) or any(set(row) != set(fields) for row in rows):
        raise ProductError(f"inconsistent output schema for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_matrix(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t")
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ProductError(f"invalid matrix: {path}")
    return values


def load_vector(path: Path) -> np.ndarray:
    values = np.loadtxt(path)
    if values.ndim != 1 or values.size < 2 or not np.all(np.isfinite(values)):
        raise ProductError(f"invalid vector: {path}")
    return values


def xray_only_components(
    corrected_xray: np.ndarray,
    horizontal_kpc: np.ndarray,
    vertical_kpc: np.ndarray,
) -> tuple[np.ndarray, str, list[recovery.Component], list[recovery.ComponentSummary]]:
    """Apply the accepted cavity detector without loading or consulting tracer."""

    spec = recovery.MapSpec(
        case="xray_only",
        view="xray_only",
        corrected_xray="in_memory",
        tracer_max_los="not_loaded",
        horizontal_axis="in_memory",
        z_axis="in_memory",
        source_type="selected_age_xray_pressure",
    )
    loaded = recovery.LoadedMap(
        spec=spec,
        corrected_xray=corrected_xray,
        tracer_max_los=np.zeros_like(corrected_xray),
        horizontal_axis=horizontal_kpc,
        z_axis=vertical_kpc,
    )
    mask, _deficit, _threshold, selected = recovery_builder._observer_mask(
        loaded,
        radial_bin_kpc=recovery.RADIAL_BIN_KPC,
        radial_smoothing_kpc=recovery.RADIAL_SMOOTHING_KPC,
        candidate_fraction_percent=1.0,
    )
    summaries = recovery.summarize_components(
        selected.components,
        horizontal_kpc,
        vertical_kpc,
    )
    pairs = sorted(zip(selected.components, summaries, strict=True), key=lambda pair: pair[1].centroid_z_kpc)
    components = [pair[0] for pair in pairs]
    summaries = [pair[1] for pair in pairs]
    return mask, recovery_builder._topology_class(summaries), components, summaries


def _side_assignment(summaries: Sequence[recovery.ComponentSummary], topology: str) -> dict[int, str]:
    if topology != "two_separate_components" or len(summaries) != 2:
        return {}
    assignment: dict[int, str] = {}
    for index, summary in enumerate(summaries):
        if summary.crosses_z_zero or summary.centroid_z_kpc == 0.0:
            return {}
        side = "negative_z" if summary.centroid_z_kpc < 0.0 else "positive_z"
        if side in assignment.values():
            return {}
        assignment[index] = side
    return assignment if set(assignment.values()) == {"negative_z", "positive_z"} else {}


def build_product(
    *,
    case: str,
    source_manifest: Path,
    analysis_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    if case not in CASES:
        raise ProductError(f"unsupported case: {case}")
    manifests = read_rows(source_manifest)
    expected_ages = {10, 20, 30, 40} if case == "G-HI" else {10, 20, 30, 40, 50}
    observed_ages = {int(row["snapshot_index"]) for row in manifests}
    if observed_ages != expected_ages:
        raise ProductError(f"selected-age manifest mismatch for {case}: {sorted(observed_ages)}")
    if output_root.exists():
        raise ProductError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True)

    topology_rows: list[dict[str, Any]] = []
    profile_rows: list[dict[str, Any]] = []
    enthalpy_rows: list[dict[str, Any]] = []
    for manifest in sorted(manifests, key=lambda row: int(row["snapshot_index"])):
        snapshot = int(manifest["snapshot_index"])
        actual_time = float(manifest["actual_time_myr"])
        for view in VIEWS:
            directory = analysis_root / f"age_{snapshot:02d}" / f"xraise_grid_{view}"
            horizontal_path = directory / ("x_kpc.tsv" if view == "0deg" else "u_kpc.tsv")
            horizontal = load_vector(horizontal_path)
            vertical = load_vector(directory / "z_kpc.tsv")
            corrected = load_matrix(directory / "xray_1kev_xraise_corrected_mjy_sr.tsv")
            emission_measure = load_matrix(directory / "xray_emission_measure_rho2_kg2_m5.tsv")
            temperature_numerator = load_matrix(
                directory / "xray_corrected_temperature_numerator_mjy_k_sr.tsv"
            )
            metadata = json.loads((directory / "xraise_grid_smoke_metadata.json").read_text())
            pressure_inputs = metadata.get("pressure_deprojection_inputs", {})
            if pressure_inputs.get("tracer_used") is not False:
                raise ProductError(f"observer pressure path does not prove tracer exclusion: {case}/{snapshot}/{view}")
            mean_molecular_weight = float(pressure_inputs["effective_mean_molecular_weight"])
            mask, topology, components, summaries = xray_only_components(
                corrected,
                horizontal,
                vertical,
            )
            pressure = deproject_pressure(
                emission_measure_rho2_kg2_m5=emission_measure,
                corrected_xray_mjy_sr=corrected,
                corrected_temperature_numerator_mjy_k_sr=temperature_numerator,
                horizontal_kpc=horizontal,
                vertical_kpc=vertical,
                radial_edges_kpc=RADIAL_EDGES_KPC,
                cavity_mask=mask,
                effective_mean_molecular_weight=mean_molecular_weight,
                regularization=DEPROJECTION_REGULARIZATION,
            )
            if float(np.min(pressure.annular_unmasked_fractions)) < 0.5:
                raise ProductError(f"insufficient ambient annular support: {case}/{snapshot}/{view}")
            topology_rows.append(
                {
                    "case": case,
                    "snapshot_index": snapshot,
                    "actual_time_myr": actual_time,
                    "view": view,
                    "topology_class": topology,
                    "component_count": len(summaries),
                    "quantitative_cavity_valid": topology == "two_separate_components",
                    "observer_mask_role": "xray_only_excluded_from_ambient_profile",
                    "tracer_loaded_or_used": False,
                    "minimum_annular_unmasked_fraction": float(np.min(pressure.annular_unmasked_fractions)),
                    "emission_measure_fit_relative_residual": pressure.emission_measure_relative_residual,
                    "corrected_xray_fit_relative_residual": pressure.corrected_xray_relative_residual,
                    "temperature_numerator_fit_relative_residual": pressure.temperature_numerator_relative_residual,
                    "temperature_direct_shell_count": int(
                        np.count_nonzero(pressure.temperature_direct_shell_mask)
                    ),
                    "temperature_interpolated_shell_count": int(
                        pressure.temperature_direct_shell_mask.size
                        - np.count_nonzero(pressure.temperature_direct_shell_mask)
                    ),
                    "temperature_support_relative_floor": pressure.temperature_support_relative_floor,
                }
            )
            for radial_index in range(len(pressure.radial_centres_kpc)):
                profile_rows.append(
                    {
                        "case": case,
                        "snapshot_index": snapshot,
                        "actual_time_myr": actual_time,
                        "view": view,
                        "radial_bin_index": radial_index,
                        "radial_inner_kpc": pressure.radial_edges_kpc[radial_index],
                        "radial_outer_kpc": pressure.radial_edges_kpc[radial_index + 1],
                        "radial_centre_kpc": pressure.radial_centres_kpc[radial_index],
                        "density_rms_kg_m3": pressure.density_rms_kg_m3[radial_index],
                        "temperature_k": pressure.temperature_k[radial_index],
                        "temperature_directly_constrained": bool(
                            pressure.temperature_direct_shell_mask[radial_index]
                        ),
                        "pressure_dyn_cm2": pressure.pressure_dyn_cm2[radial_index],
                        "annular_emission_measure_kg2_m5": pressure.annular_emission_measure_kg2_m5[radial_index],
                        "annular_corrected_xray_mjy_sr": pressure.annular_corrected_xray_mjy_sr[radial_index],
                        "annular_temperature_numerator_mjy_k_sr": pressure.annular_temperature_numerator_mjy_k_sr[radial_index],
                        "annular_pixel_count": pressure.annular_pixel_counts[radial_index],
                        "annular_unmasked_fraction": pressure.annular_unmasked_fractions[radial_index],
                        "effective_mean_molecular_weight": mean_molecular_weight,
                        "deprojection_method": "spherical_nonnegative_first_difference_regularized",
                        "deprojection_regularization": DEPROJECTION_REGULARIZATION,
                    }
                )
            sides = _side_assignment(summaries, topology)
            if not sides:
                enthalpy_rows.append(
                    {
                        "case": case,
                        "snapshot_index": snapshot,
                        "actual_time_myr": actual_time,
                        "view": view,
                        "side": "not_assignable",
                        "topology_class": topology,
                        "quantitative_cavity_valid": False,
                        "component_index": "",
                        "volume_depth_assumption": "",
                        "pressure_method": "",
                        "energy_model": "",
                        "alpha": "",
                        "centroid_radius_kpc": "",
                        "pressure_dyn_cm2": "",
                        "volume_kpc3": "",
                        "enthalpy_erg": "",
                        "tracer_loaded_or_used": False,
                    }
                )
                continue
            for component_index, (component, summary) in enumerate(
                zip(components, summaries, strict=True), start=1
            ):
                side = sides[component_index - 1]
                orientation = component_orientation_rad(component.mask, horizontal, vertical)
                centroid_radius = math.hypot(summary.centroid_x_kpc, summary.centroid_z_kpc)
                midpoint_pressure = float(
                    pressure_at_radius(
                        centroid_radius,
                        pressure.radial_centres_kpc,
                        pressure.pressure_dyn_cm2,
                    )
                )
                for depth in DEPTHS:
                    depth_key = f"{depth}_depth"
                    volume = summary.volumes_kpc3[depth_key]
                    average_pressure = ellipsoid_average_pressure(
                        centroid_horizontal_kpc=summary.centroid_x_kpc,
                        centroid_vertical_kpc=summary.centroid_z_kpc,
                        major_semiaxis_kpc=summary.major_semiaxis_kpc,
                        minor_semiaxis_kpc=summary.minor_semiaxis_kpc,
                        los_semiaxis_kpc=summary.depths_kpc[depth_key],
                        orientation_rad=orientation,
                        radial_centres_kpc=pressure.radial_centres_kpc,
                        pressure_dyn_cm2=pressure.pressure_dyn_cm2,
                    )
                    for pressure_method, pressure_value in (
                        ("midpoint", midpoint_pressure),
                        ("ellipsoid_volume_average", average_pressure),
                    ):
                        for energy_model, alpha in ALPHAS:
                            enthalpy_rows.append(
                                {
                                    "case": case,
                                    "snapshot_index": snapshot,
                                    "actual_time_myr": actual_time,
                                    "view": view,
                                    "side": side,
                                    "topology_class": topology,
                                    "quantitative_cavity_valid": True,
                                    "component_index": component_index,
                                    "volume_depth_assumption": f"{depth}_depth",
                                    "pressure_method": pressure_method,
                                    "energy_model": energy_model,
                                    "alpha": alpha,
                                    "centroid_radius_kpc": centroid_radius,
                                    "pressure_dyn_cm2": pressure_value,
                                    "volume_kpc3": volume,
                                    "enthalpy_erg": alpha * pressure_value * volume * KPC_CM**3,
                                    "tracer_loaded_or_used": False,
                                }
                            )

    expected_views = len(expected_ages) * len(VIEWS)
    if len(topology_rows) != expected_views or len(profile_rows) != expected_views * (len(RADIAL_EDGES_KPC) - 1):
        raise ProductError("selected-age observer pressure coverage is incomplete")
    write_rows(output_root / "xray_topology_summary.csv", topology_rows)
    write_rows(output_root / "xray_pressure_profiles.csv", profile_rows)
    write_rows(output_root / "xray_cavity_enthalpy_selected_age.csv", enthalpy_rows)
    write_rows(output_root / "source_manifest.csv", manifests)
    metadata = {
        "status": "complete_selected_age_xray_pressure_product",
        "case": case,
        "selected_ages_myr": sorted(expected_ages),
        "views": list(VIEWS),
        "observer_independence": "X-ray-only cavity geometry and pressure; tracer not loaded",
        "pressure_method": "spherical non-negative deprojection of rho^2 and corrected-X-ray temperature inputs",
        "radial_edges_kpc": RADIAL_EDGES_KPC.tolist(),
        "deprojection_regularization": DEPROJECTION_REGULARIZATION,
        "temperature_support_relative_floor": 1.0e-12,
        "enthalpy_conventions": [name for name, _ in ALPHAS],
        "row_counts": {
            "xray_topology_summary.csv": len(topology_rows),
            "xray_pressure_profiles.csv": len(profile_rows),
            "xray_cavity_enthalpy_selected_age.csv": len(enthalpy_rows),
        },
    }
    (output_root / "selected_age_xray_pressure_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    manifest_path = output_root / "local_asset_manifest.sha256"
    manifest_path.write_text(
        "\n".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
            for path in sorted(output_root.iterdir())
            if path.is_file() and path != manifest_path
        )
        + "\n"
    )
    return metadata


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    metadata = build_product(
        case=args.case,
        source_manifest=args.source_manifest,
        analysis_root=args.analysis_root,
        output_root=args.output_root,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
