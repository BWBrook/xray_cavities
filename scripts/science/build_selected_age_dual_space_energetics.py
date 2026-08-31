#!/usr/bin/env python3
"""Join independent selected-age native-grid and X-ray energetics ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
GAMMA = 5.0 / 3.0
KPC_CM = 3.0856775814913673e21


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


def finite(value: Any, *, context: str, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ProductError(f"non-numeric {context}: {value!r}") from exc
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise ProductError(f"invalid {context}: {value!r}")
    return result


def native_selected_rows(native_case_age_path: Path) -> list[dict[str, Any]]:
    rows = read_rows(native_case_age_path)
    expected = {
        *((case, age) for case in ("C-HI", "C-LO", "G-LO") for age in (10, 20, 30, 40, 50)),
        *(("G-HI", age) for age in (10, 20, 30, 40)),
    }
    observed = {(row["case"], int(row["snapshot_index"])) for row in rows}
    if observed != expected or len(rows) != len(expected):
        raise ProductError("native selected-age surface must contain the 19 accepted case-ages")
    output: list[dict[str, Any]] = []
    for row in rows:
        lobe_thermal = finite(row["direct_lobe_thermal_erg"], context="lobe thermal", positive=True)
        lobe_volume = finite(row["direct_lobe_volume_kpc3"], context="lobe volume", positive=True)
        lobe_pv = (GAMMA - 1.0) * lobe_thermal
        lobe_pressure = lobe_pv / (lobe_volume * KPC_CM**3)
        retained = finite(row["ambient_total_delta_erg"], context="ambient total") + finite(
            row["direct_lobe_total_erg"], context="lobe total"
        )
        injected = finite(row["injected_energy_erg"], context="injected energy", positive=True)
        output.append(
            {
                "case": row["case"],
                "snapshot_index": int(row["snapshot_index"]),
                "actual_time_myr": finite(row["actual_time_myr"], context="actual time", positive=True),
                "native_partition_method": "fractional_tracer_cellwise_initial_state_subtraction",
                "lobe_volume_kpc3": lobe_volume,
                "lobe_pressure_volume_erg": lobe_pv,
                "lobe_mean_pressure_dyn_cm2": lobe_pressure,
                "lobe_enthalpy_2p5pv_erg": 2.5 * lobe_pv,
                "lobe_enthalpy_4pv_erg": 4.0 * lobe_pv,
                "lobe_thermal_erg": lobe_thermal,
                "lobe_kinetic_erg": finite(row["direct_lobe_kinetic_erg"], context="lobe kinetic"),
                "lobe_gravitational_erg": finite(
                    row["direct_lobe_gravitational_erg"], context="lobe gravitational"
                ),
                "lobe_total_erg": finite(row["direct_lobe_total_erg"], context="lobe total"),
                "ambient_thermal_delta_erg": finite(
                    row["ambient_thermal_delta_erg"], context="ambient thermal"
                ),
                "ambient_kinetic_delta_erg": finite(
                    row["ambient_kinetic_delta_erg"], context="ambient kinetic"
                ),
                "ambient_gravitational_delta_erg": finite(
                    row["ambient_gravitational_delta_erg"], context="ambient gravitational"
                ),
                "ambient_total_delta_erg": finite(row["ambient_total_delta_erg"], context="ambient total"),
                "retained_energy_erg": retained,
                "injected_energy_erg": injected,
                "boundary_status": row["boundary_status"],
                "closure_fraction_of_injected": finite(
                    row["closure_fraction_of_injected"], context="closure fraction"
                ),
                "ambient_energy_interpretation": row["ambient_energy_interpretation"],
                "mean_mach_kinematic": row["mean_mach_kinematic"],
                "shock_fraction_status": "pending_native_3d_shock_mask",
                "native_selected_age_status": "valid",
            }
        )
    return output


def aggregate_observer_rows(rows: Iterable[Mapping[str, str]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        if str(row.get("quantitative_cavity_valid", "")).lower() != "true":
            continue
        key = (
            row["case"],
            int(row["snapshot_index"]),
            row["view"],
            row["volume_depth_assumption"],
            row["pressure_method"],
            row["energy_model"],
            finite(row["alpha"], context="observer alpha", positive=True),
        )
        groups[key].append(row)
    output: dict[tuple[Any, ...], dict[str, Any]] = {}
    for key, side_rows in groups.items():
        if {row["side"] for row in side_rows} != {"negative_z", "positive_z"} or len(side_rows) != 2:
            raise ProductError(f"observer side coverage is incomplete for {key}")
        alpha = float(key[-1])
        volume = sum(finite(row["volume_kpc3"], context="observer volume", positive=True) for row in side_rows)
        enthalpy = sum(finite(row["enthalpy_erg"], context="observer enthalpy", positive=True) for row in side_rows)
        pressure = enthalpy / (alpha * volume * KPC_CM**3)
        output[key] = {
            "observer_volume_kpc3": volume,
            "observer_effective_pressure_dyn_cm2": pressure,
            "observer_enthalpy_erg": enthalpy,
        }
    return output


def build_product(
    *,
    native_case_age_path: Path,
    observer_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    if output_root.exists():
        raise ProductError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True)
    native = native_selected_rows(native_case_age_path)
    native_by_key = {(row["case"], row["snapshot_index"]): row for row in native}
    topology: list[dict[str, str]] = []
    observer_enthalpy: list[dict[str, str]] = []
    pressure_profiles: list[dict[str, str]] = []
    for case in CASES:
        case_root = observer_root / case
        topology.extend(read_rows(case_root / "xray_topology_summary.csv"))
        observer_enthalpy.extend(read_rows(case_root / "xray_cavity_enthalpy_selected_age.csv"))
        pressure_profiles.extend(read_rows(case_root / "xray_pressure_profiles.csv"))
    if len(topology) != 57:
        raise ProductError(f"observer topology surface must contain 57 case-age-views, got {len(topology)}")
    observer_groups = aggregate_observer_rows(observer_enthalpy)
    matched: list[dict[str, Any]] = []
    for topology_row in topology:
        case = topology_row["case"]
        snapshot = int(topology_row["snapshot_index"])
        native_row = native_by_key.get((case, snapshot))
        if native_row is None:
            raise ProductError(f"observer row lacks accepted native row: {case}/{snapshot}")
        common = {
            "case": case,
            "snapshot_index": snapshot,
            "actual_time_myr": native_row["actual_time_myr"],
            "view": topology_row["view"],
            "topology_class": topology_row["topology_class"],
            "quantitative_cavity_valid": topology_row["quantitative_cavity_valid"],
            "volume_depth_assumption": "",
            "pressure_method": "",
            "energy_model": "",
            "alpha": "",
            "observer_volume_kpc3": "",
            "native_lobe_volume_kpc3": native_row["lobe_volume_kpc3"],
            "volume_recovery": "",
            "observer_effective_pressure_dyn_cm2": "",
            "native_lobe_mean_pressure_dyn_cm2": native_row["lobe_mean_pressure_dyn_cm2"],
            "pressure_recovery": "",
            "observer_enthalpy_erg": "",
            "native_lobe_enthalpy_erg": "",
            "retained_energy_erg": native_row["retained_energy_erg"],
            "injected_energy_erg": native_row["injected_energy_erg"],
            "ratio_to_native_lobe_enthalpy": "",
            "factorized_volume_times_pressure": "",
            "factorization_relative_error": "",
            "ratio_to_retained_energy": "",
            "ratio_to_injected_energy": "",
            "mean_mach_kinematic": native_row["mean_mach_kinematic"],
            "shock_fraction_status": native_row["shock_fraction_status"],
            "boundary_status": native_row["boundary_status"],
            "ambient_energy_interpretation": native_row["ambient_energy_interpretation"],
            "total_outburst_ratio_status": (
                "unresolved_background_dominated" if case == "C-LO" else "descriptive_boundary_unresolved"
            ),
            "matched_status": "unresolved_observer_topology",
        }
        if str(topology_row["quantitative_cavity_valid"]).lower() != "true":
            matched.append(common)
            continue
        keys = [
            key for key in observer_groups if key[:3] == (case, snapshot, topology_row["view"])
        ]
        if len(keys) != 12:
            raise ProductError(f"expected 12 observer method rows for {case}/{snapshot}/{topology_row['view']}")
        for key in sorted(keys, key=lambda item: tuple(str(value) for value in item[3:])):
            _case, _snapshot, _view, depth, pressure_method, energy_model, alpha = key
            observer = observer_groups[key]
            native_enthalpy = (
                native_row["lobe_enthalpy_2p5pv_erg"] if alpha == 2.5 else native_row["lobe_enthalpy_4pv_erg"]
            )
            volume_recovery = observer["observer_volume_kpc3"] / native_row["lobe_volume_kpc3"]
            pressure_recovery = (
                observer["observer_effective_pressure_dyn_cm2"]
                / native_row["lobe_mean_pressure_dyn_cm2"]
            )
            lobe_recovery = observer["observer_enthalpy_erg"] / native_enthalpy
            factorized = volume_recovery * pressure_recovery
            relative_error = abs(lobe_recovery - factorized) / lobe_recovery
            if relative_error > 1.0e-10:
                raise ProductError(f"volume-pressure factorization failed for {key}")
            matched.append(
                {
                    **common,
                    "volume_depth_assumption": depth,
                    "pressure_method": pressure_method,
                    "energy_model": energy_model,
                    "alpha": alpha,
                    "observer_volume_kpc3": observer["observer_volume_kpc3"],
                    "volume_recovery": volume_recovery,
                    "observer_effective_pressure_dyn_cm2": observer[
                        "observer_effective_pressure_dyn_cm2"
                    ],
                    "pressure_recovery": pressure_recovery,
                    "observer_enthalpy_erg": observer["observer_enthalpy_erg"],
                    "native_lobe_enthalpy_erg": native_enthalpy,
                    "ratio_to_native_lobe_enthalpy": lobe_recovery,
                    "factorized_volume_times_pressure": factorized,
                    "factorization_relative_error": relative_error,
                    "ratio_to_retained_energy": observer["observer_enthalpy_erg"]
                    / native_row["retained_energy_erg"],
                    "ratio_to_injected_energy": observer["observer_enthalpy_erg"]
                    / native_row["injected_energy_erg"],
                    "matched_status": "quantitative_dual_space_match",
                }
            )

    summary_rows: list[dict[str, Any]] = []
    for case in CASES:
        primary = [
            row
            for row in matched
            if row["case"] == case
            and row["matched_status"] == "quantitative_dual_space_match"
            and row["volume_depth_assumption"] == "geometric_depth"
            and row["pressure_method"] == "ellipsoid_volume_average"
            and row["energy_model"] == "2.5pV"
        ]
        topology_case = [row for row in topology if row["case"] == case]
        values = {
            metric: np.array([float(row[metric]) for row in primary], dtype=float)
            for metric in (
                "volume_recovery",
                "pressure_recovery",
                "ratio_to_native_lobe_enthalpy",
                "ratio_to_retained_energy",
                "ratio_to_injected_energy",
            )
        }
        row: dict[str, Any] = {
            "case": case,
            "selected_age_view_count": len(topology_case),
            "quantitative_primary_count": len(primary),
            "topology_failure_count": sum(
                str(item["quantitative_cavity_valid"]).lower() != "true" for item in topology_case
            ),
            "primary_method": "geometric_depth_ellipsoid_volume_average_2.5pV",
            "total_outburst_ratio_status": (
                "unresolved_background_dominated" if case == "C-LO" else "descriptive_boundary_unresolved"
            ),
            "shock_fraction_status": "pending_native_3d_shock_mask",
        }
        for metric, data in values.items():
            row[f"{metric}_median"] = float(np.median(data)) if data.size else ""
            row[f"{metric}_min"] = float(np.min(data)) if data.size else ""
            row[f"{metric}_max"] = float(np.max(data)) if data.size else ""
        summary_rows.append(row)

    write_rows(output_root / "native_grid_selected_age.csv", native)
    write_rows(output_root / "xray_pressure_profiles.csv", pressure_profiles)
    write_rows(output_root / "xray_topology_summary.csv", topology)
    write_rows(output_root / "xray_cavity_enthalpy_selected_age.csv", observer_enthalpy)
    write_rows(output_root / "matched_native_xray_energetics.csv", matched)
    write_rows(output_root / "energetics_audit_summary.csv", summary_rows)
    metadata = {
        "status": "complete_selected_age_dual_space_energetics_audit",
        "decision_scope": "selected-age proof before annual extension",
        "accepted_case_age_count": len(native),
        "observer_case_age_view_count": len(topology),
        "matched_row_count": len(matched),
        "native_observer_independence": "joined only after independent products completed",
        "shock_extension_status": "pending native 3D shock mask; no shock fraction claimed",
        "g_hi_50_status": "excluded",
        "primary_observer_method": "geometric LOS depth, ellipsoid-volume-averaged X-ray-deprojected pressure, 2.5pV",
    }
    (output_root / "selected_age_dual_space_energetics_metadata.json").write_text(
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
    parser.add_argument("--native-case-age-path", type=Path, required=True)
    parser.add_argument("--observer-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    metadata = build_product(
        native_case_age_path=args.native_case_age_path,
        observer_root=args.observer_root,
        output_root=args.output_root,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
