#!/usr/bin/env python3
"""Build the compact Goal 041 common-age surface for one case.

The observer mask and sensitivity calculations are delegated to the accepted
Goal 040 recovery implementation.  This module handles deterministic product
assembly, time propagation, validation, and lifecycle provenance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SCIENCE_DIR = Path(__file__).resolve().parent
if str(SCIENCE_DIR) not in sys.path:
    sys.path.insert(0, str(SCIENCE_DIR))

import build_three_case_cavity_recovery as recovery_builder  # noqa: E402
import three_case_cavity_recovery as recovery  # noqa: E402


CASES = ("C-HI", "C-LO", "G-LO")
AUTHORITATIVE_JET_POWER_ERG_S = {"C-HI": 1.0e45, "C-LO": 1.0e43, "G-LO": 1.0e43}
AGES = (10, 20, 30, 40, 50)
VIEWS = ("0deg", "45deg", "90deg")
SIDES = ("negative_z", "positive_z", "bipolar_total")
TRACER_THRESHOLDS = ("1e-3", "5e-3", "1e-2")
KPC_CM = 3.0856775814913673e21
SECONDS_PER_MYR = 3.15576e13
GRAVITY_STATUS = "excluded_blocked"
COMPACT_TABLES = (
    "xray_recovery_summary.csv", "xray_component_summary.csv",
    "projected_tracer_alignment.csv", "xray_method_sensitivity.csv",
    "projection_validation.csv", "level1_truth.csv", "level2_truth.csv",
    "cavity_shell_context.csv", "level3_ambient_energy.csv",
    "cavity_energy_power_alignment.csv", "source_time_manifest_case.csv",
    "product_dependency_ledger.csv",
)


def read_rows(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"missing product: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"duplicate or missing header in {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty product: {path}")
    return rows


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON product: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON product is not an object: {path}")
    return value


def finite(value: Any, *, context: str, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric {context}: {value!r}") from exc
    if not math.isfinite(result) or (positive and result <= 0.0):
        qualifier = "finite positive" if positive else "finite"
        raise ValueError(f"{context} is not {qualifier}: {value!r}")
    return result


def safe_ratio(numerator: Any, denominator: Any) -> float | str:
    try:
        numerator_value = float(numerator)
        denominator_value = float(denominator)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(numerator_value) or not math.isfinite(denominator_value) or denominator_value == 0.0:
        return ""
    result = numerator_value / denominator_value
    return result if math.isfinite(result) else ""


def normalize_threshold(value: Any) -> str:
    """Normalize C/Python scientific notation to the compact truth keys."""

    number = finite(value, context="tracer threshold", positive=True)
    return f"{number:.0e}".replace("e-0", "e-").replace("e+0", "e+")


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    fields = list(rows[0])
    if len(fields) != len(set(fields)) or any(set(row) != set(fields) for row in rows):
        raise ValueError(f"inconsistent or duplicate output schema for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _manifest_rows(path: Path, case: str) -> list[dict[str, str]]:
    rows = read_rows(path)
    selected = [row for row in rows if row.get("case") == case]
    if len(selected) != len(AGES):
        raise ValueError(f"source manifest must contain five rows for {case}")
    by_age: dict[int, dict[str, str]] = {}
    for row in selected:
        age = int(row["nominal_age_myr"])
        if age in by_age or age not in AGES:
            raise ValueError(f"invalid or duplicate manifest age for {case}: {age}")
        finite(row["actual_time_myr"], context=f"manifest actual age {case}/{age}", positive=True)
        finite(row["time_code"], context=f"manifest time code {case}/{age}", positive=True)
        if abs(float(row["actual_time_myr"]) - age) > 0.05:
            raise ValueError(f"manifest selected age exceeds tolerance for {case}/{age}")
        if row.get("selection_status") != "selected":
            raise ValueError(f"manifest selection status is not selected for {case}/{age}")
        if row.get("endpoint_reuse_id") != f"{case}:50myr":
            raise ValueError(f"manifest endpoint reuse binding drift for {case}/{age}")
        manifest_power = finite(
            row.get("jet_power_erg_s"),
            context=f"manifest jet power {case}/{age}",
            positive=True,
        )
        if not math.isclose(
            manifest_power,
            AUTHORITATIVE_JET_POWER_ERG_S[case],
            rel_tol=1.0e-12,
            abs_tol=0.0,
        ):
            raise ValueError(
                f"manifest jet power violates the authoritative three-case contract "
                f"for {case}/{age}: {manifest_power:.12g}"
            )
        if abs(finite(row.get("baseline_time_myr"), context=f"baseline time {case}/{age}")) > 1.0e-6:
            raise ValueError(f"manifest baseline is not zero-time for {case}/{age}")
        if row.get("baseline_grid_shape_nz_ny_nx") != row.get("grid_shape_nz_ny_nx"):
            raise ValueError(f"manifest baseline grid shape mismatch for {case}/{age}")
        expected_action = "reuse_endpoint_plus_level3" if age == 50 else "compute_new"
        if row.get("action") != expected_action or row.get("compute_level3", "").lower() != "true":
            raise ValueError(f"invalid manifest flags for {case}/{age}")
        if age < 50 and not all(row.get(name, "").lower() == "true" for name in ("compute_xray", "compute_truth_cavity")):
            raise ValueError(f"missing compute flags for {case}/{age}")
        if age == 50 and any(row.get(name, "").lower() != "false" for name in ("compute_xray", "compute_truth_cavity")):
            raise ValueError(f"endpoint reuse flags are not closed for {case}/{age}")
        by_age[age] = row
    if set(by_age) != set(AGES):
        raise ValueError(f"source manifest does not cover {AGES}")
    return [by_age[age] for age in AGES]


def _xraise_paths(age_dir: Path, view: str) -> tuple[Path, Path, Path, Path]:
    directory = age_dir / f"xraise_grid_{view}"
    horizontal_name = "x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"
    horizontal = directory / horizontal_name
    if not horizontal.is_file():
        horizontal = directory / "x_kpc.tsv"
    return (
        directory / "xray_1kev_xraise_corrected_mjy_sr.tsv",
        directory / "tracer_max_los.tsv",
        horizontal,
        directory / "z_kpc.tsv",
    )


def _load_map(age_dir: Path, case: str, view: str, actual_age: float) -> tuple[recovery.LoadedMap, dict[str, str]]:
    xray, tracer, horizontal, vertical = _xraise_paths(age_dir, view)
    for path in (xray, tracer, horizontal, vertical):
        if not path.is_file():
            raise ValueError(f"missing XRAiSE map product: {path}")
    spec = recovery.MapSpec(
        case=case, view=view, corrected_xray=str(xray), tracer_max_los=str(tracer),
        horizontal_axis=str(horizontal), z_axis=str(vertical), source_type="local_common_age",
    )
    loaded = recovery.load_accepted_map(spec)
    metadata_path = xray.parent / "xraise_grid_smoke_metadata.json"
    summary_path = xray.parent / "xraise_grid_smoke_summary.csv"
    metadata = read_json(metadata_path)
    summary = read_rows(summary_path)
    metrics = {row.get("metric", ""): row.get("value", "") for row in summary}
    for metric in ("time_myr", "corrected_xray_max", "corrected_xray_sum", "correction_ratio_positive_max", "correction_ratio_positive_sum"):
        finite(metrics.get(metric), context=f"{case}/{view}/{metric}", positive=True)
    if abs(float(metrics["time_myr"]) - actual_age) > 1.0e-6:
        raise ValueError(f"XRAiSE time mismatch for {case}/{view}: {metrics['time_myr']} versus {actual_age}")
    projection = metadata.get("projection", {})
    accumulator = projection.get("projected_accumulation")
    expected = "direct_y_axis_sum" if view == "0deg" else "edge_overlap_uniform_cell_projection"
    if accumulator != expected:
        raise ValueError(f"wrong projection accumulator for {case}/{view}: {accumulator!r}")
    empty_path = xray.parent / "projection_empty_columns.csv"
    if empty_path.is_file():
        empty_rows = read_rows(empty_path)
        matching = [row for row in empty_rows if row.get("layer") == "corrected_xray"]
        if len(matching) != 1:
            raise ValueError(f"missing corrected empty-column validation for {xray.parent}")
        empty_fraction = finite(matching[0]["empty_column_fraction"], context=f"{case}/{view} empty-column fraction")
    else:
        values = loaded.corrected_xray
        empty_fraction = float(np.mean(~np.any(np.isfinite(values) & (values > 0.0), axis=0)))
    if empty_fraction > 0.05:
        raise ValueError(f"empty-column fraction exceeds 0.05 for {case}/{view}: {empty_fraction}")
    return loaded, {
        "case": case, "view": view, "actual_time_myr": actual_age,
        "projection_accumulator": accumulator, "empty_column_fraction": empty_fraction,
        "corrected_xray_max": float(metrics["corrected_xray_max"]),
        "corrected_xray_sum": float(metrics["corrected_xray_sum"]),
        "status": "validated",
    }


def _with_time(row: dict[str, Any], *, case: str, nominal: int, actual: float) -> dict[str, Any]:
    return {"case": case, "nominal_age_myr": nominal, "actual_time_myr": actual, **row}


def _truth_rows(age_dir: Path, case: str, nominal: int, actual: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    truth_dir = age_dir / "truth"
    level1_source = read_rows(truth_dir / "level1_injected_energy.csv")
    level2_source = read_rows(truth_dir / "level2_tracer_lobe_truth.csv")
    level1_time = [row for row in level1_source if row.get("metric") == "time_myr"]
    if len(level1_time) != 1 or abs(finite(level1_time[0].get("value"), context=f"Level 1 time {case}/{nominal}") - actual) > 1.0e-6:
        raise ValueError(f"Level 1 time mismatch for {case}/{nominal}")
    level1 = [_with_time({"metric": row.get("metric", ""), "value": row.get("value", ""), "unit": row.get("unit", "")}, case=case, nominal=nominal, actual=actual) for row in level1_source]
    level2: list[dict[str, Any]] = []
    for row in level2_source:
        if abs(finite(row.get("time_myr"), context=f"Level 2 time {case}/{nominal}") - actual) > 1.0e-6:
            raise ValueError(f"Level 2 time mismatch for {case}/{nominal}")
        threshold = normalize_threshold(row.get("threshold"))
        if threshold not in TRACER_THRESHOLDS or row.get("side") not in SIDES:
            raise ValueError(f"invalid Level 2 row in {truth_dir}")
        for field in ("volume_kpc3", "total_energy_erg", "cell_count"):
            finite(row.get(field), context=f"Level 2 {case}/{nominal}/{field}", positive=True)
        normalized = dict(row)
        normalized["threshold"] = threshold
        level2.append(_with_time(normalized, case=case, nominal=nominal, actual=actual))
    expected = {(threshold, side) for threshold in TRACER_THRESHOLDS for side in SIDES}
    observed = {(row["threshold"], row["side"]) for row in level2}
    if observed != expected:
        raise ValueError(f"Level 2 threshold/side coverage is incomplete for {case}/{nominal}")
    return level1, level2


def _cavity_rows(age_dir: Path, case: str, nominal: int, actual: float) -> list[dict[str, Any]]:
    rows = read_rows(age_dir / "cavity" / "cavity_stub_summary.csv")
    if {row.get("side") for row in rows} != {"negative_z", "positive_z"} or len(rows) != 2:
        raise ValueError(f"cavity shell must have one row per z side for {case}/{nominal}")
    for row in rows:
        if abs(finite(row.get("time_myr"), context=f"cavity time {case}/{nominal}/{row.get('side')}") - actual) > 1.0e-6:
            raise ValueError(f"cavity time mismatch for {case}/{nominal}/{row.get('side')}")
        for field in ("ambient_pressure_dyn_cm2", "sound_age_myr", "buoyancy_age_myr", "refill_age_myr"):
            finite(row.get(field), context=f"cavity {case}/{nominal}/{row['side']}/{field}", positive=True)
    return [_with_time(dict(row), case=case, nominal=nominal, actual=actual) for row in rows]


def _level3_rows(age_dir: Path, case: str, nominal: int, actual: float) -> list[dict[str, Any]]:
    directory = age_dir / "level3"
    source = directory / "level3_extractor_output.csv"
    if not source.is_file():
        source = directory / "level3_ambient_energy.csv"
    rows = read_rows(source)
    if {row.get("side") for row in rows} != set(SIDES) or len(rows) != 3:
        raise ValueError(f"Level 3 side coverage is incomplete for {case}/{nominal}")
    for row in rows:
        finite(row.get("ambient_cell_count"), context=f"Level 3 {case}/{nominal}/cell count", positive=True)
        finite(row.get("ambient_volume_kpc3"), context=f"Level 3 {case}/{nominal}/volume", positive=True)
        for field in ("thermal_delta_erg", "kinetic_delta_erg", "thermal_plus_kinetic_delta_erg"):
            finite(row.get(field), context=f"Level 3 {case}/{nominal}/{field}")
        if not math.isclose(float(row["thermal_plus_kinetic_delta_erg"]), float(row["thermal_delta_erg"]) + float(row["kinetic_delta_erg"]), rel_tol=1e-9, abs_tol=0.0):
            raise ValueError(f"Level 3 thermal+kinetic accumulator mismatch for {case}/{nominal}/{row['side']}")
    return [
        {**_with_time(dict(row), case=case, nominal=nominal, actual=actual), "gravity_status": GRAVITY_STATUS, "gravity_delta_erg": ""}
        for row in rows
    ]


def _level1_energy(rows: list[dict[str, Any]], metric: str) -> float:
    selected = [row for row in rows if row.get("metric") == metric]
    if len(selected) != 1:
        raise ValueError(f"missing unique Level 1 metric {metric}")
    return finite(selected[0]["value"], context=metric, positive=True)


def _level2_energy(rows: list[dict[str, Any]], side: str) -> float:
    selected = [row for row in rows if row.get("threshold") == "5e-3" and row.get("side") == side]
    if len(selected) != 1:
        raise ValueError(f"missing unique Level 2 5e-3 row for {side}")
    return finite(selected[0]["total_energy_erg"], context=f"Level 2 {side}", positive=True)


def build_energy_rows(
    *, case: str, nominal: int, actual: float, summary: dict[str, Any], component_rows: list[dict[str, Any]],
    cavity_rows: list[dict[str, Any]], level1_rows: list[dict[str, Any]], level2_rows: list[dict[str, Any]], level3_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Align shell pressures/ages to safely assignable X-ray components."""

    cavity_by_side = {row["side"]: row for row in cavity_rows}
    topology = str(summary["topology_class"])
    assignable = len(component_rows) == 2 and all(not str(row.get("crosses_z_zero", "")).lower() in {"true", "1", "yes"} for row in component_rows)
    components_by_side: dict[str, dict[str, Any]] = {}
    if assignable:
        for row in component_rows:
            z = finite(row["centroid_z_kpc"], context="X-ray component centroid")
            side = "negative_z" if z < 0.0 else "positive_z" if z > 0.0 else ""
            if not side or side in components_by_side:
                assignable = False
                break
            components_by_side[side] = row
        assignable = assignable and set(components_by_side) == {"negative_z", "positive_z"}
    models = (("pV", 1.0), ("2.5pV", 2.5), ("4pV", 4.0))
    rows: list[dict[str, Any]] = []

    def row_for(side: str, depth: str, factor: float, *, component: dict[str, Any] | None, pressure: float, age_values: dict[str, float] | None, convention: str) -> dict[str, Any]:
        volume = sum(float(component[f"volume_{depth}_depth_kpc3"]) for component in [component] if component is not None)
        energy = pressure * volume * KPC_CM**3 * factor
        l1 = _level1_energy(level1_rows, "injected_energy_one_sided_elapsed" if side != "bipolar_total" else "injected_energy_bipolar_elapsed")
        l2 = _level2_energy(level2_rows, side)
        l3 = next(row for row in level3_rows if row["side"] == side)
        l3_energy = float(l3["thermal_plus_kinetic_delta_erg"])
        output: dict[str, Any] = {
            "case": case, "nominal_age_myr": nominal, "actual_time_myr": actual,
            "view": summary["view"], "side": side,
            "volume_depth_assumption": f"{depth}_depth",
            "energy_model": next(name for name, value in models if value == factor),
            "topology_status": topology, "energy_pressure_convention": convention,
            "pressure_aggregation": "single_side" if side != "bipolar_total" else "not_applicable",
            "pressure_dyn_cm2": pressure, "volume_kpc3": volume, "energy_erg": energy,
            "pV_erg": energy if factor == 1.0 else "", "two_point_five_pV_erg": energy if factor == 2.5 else "", "four_pV_erg": energy if factor == 4.0 else "",
            "ratio_to_level1_injected_energy": safe_ratio(energy, l1),
            "ratio_to_level2_5e-3_total_energy": safe_ratio(energy, l2),
            "ratio_to_level3_thermal_plus_kinetic": safe_ratio(energy, l3_energy),
            "sound_age_myr": "" if age_values is None else age_values["sound_age_myr"],
            "buoyancy_age_myr": "" if age_values is None else age_values["buoyancy_age_myr"],
            "refill_age_myr": "" if age_values is None else age_values["refill_age_myr"],
            "sound_power_erg_s": "" if age_values is None else energy / (age_values["sound_age_myr"] * SECONDS_PER_MYR),
            "buoyancy_power_erg_s": "" if age_values is None else energy / (age_values["buoyancy_age_myr"] * SECONDS_PER_MYR),
            "refill_power_erg_s": "" if age_values is None else energy / (age_values["refill_age_myr"] * SECONDS_PER_MYR),
            "shell_age_role": "tracer_geometry_proxy_sound_primary_buoyancy_refill_provisional" if age_values is not None else "unavailable_ambiguous_topology",
            "power_aggregation": "single_side_energy_over_age" if age_values is not None else "unavailable",
            "gravity_status": GRAVITY_STATUS,
        }
        return output

    for depth in ("minor", "geometric", "major"):
        if assignable:
            for _, factor in models:
                side_rows = []
                for side in ("negative_z", "positive_z"):
                    shell = cavity_by_side[side]
                    ages = {key: finite(shell[key], context=key, positive=True) for key in ("sound_age_myr", "buoyancy_age_myr", "refill_age_myr")}
                    side_rows.append(row_for(side, depth, factor, component=components_by_side[side], pressure=float(shell["ambient_pressure_dyn_cm2"]), age_values=ages, convention="side_specific_tracer_shell_pressure"))
                rows.extend(side_rows)
                bipolar_pressure = (float(cavity_by_side["negative_z"]["ambient_pressure_dyn_cm2"]) + float(cavity_by_side["positive_z"]["ambient_pressure_dyn_cm2"])) / 2.0
                bipolar = row_for("bipolar_total", depth, factor, component=None, pressure=bipolar_pressure, age_values=None, convention="side_specific_tracer_shell_pressure")
                component_volumes = [float(components_by_side[side][f"volume_{depth}_depth_kpc3"]) for side in ("negative_z", "positive_z")]
                bipolar["volume_kpc3"] = sum(component_volumes)
                bipolar["energy_erg"] = sum(float(item["energy_erg"]) for item in side_rows)
                bipolar["pV_erg"] = bipolar["energy_erg"] if factor == 1.0 else ""
                bipolar["two_point_five_pV_erg"] = bipolar["energy_erg"] if factor == 2.5 else ""
                bipolar["four_pV_erg"] = bipolar["energy_erg"] if factor == 4.0 else ""
                bipolar["ratio_to_level1_injected_energy"] = safe_ratio(bipolar["energy_erg"], _level1_energy(level1_rows, "injected_energy_bipolar_elapsed"))
                bipolar["ratio_to_level2_5e-3_total_energy"] = safe_ratio(bipolar["energy_erg"], _level2_energy(level2_rows, "bipolar_total"))
                bipolar["ratio_to_level3_thermal_plus_kinetic"] = safe_ratio(bipolar["energy_erg"], float(next(row for row in level3_rows if row["side"] == "bipolar_total")["thermal_plus_kinetic_delta_erg"]))
                bipolar["pressure_aggregation"] = "side_specific_energy_sum"
                for key in ("sound_age_myr", "buoyancy_age_myr", "refill_age_myr"):
                    bipolar[key] = (float(cavity_by_side["negative_z"][key]) + float(cavity_by_side["positive_z"][key])) / 2.0
                for age_key, power_key in (("sound_age_myr", "sound_power_erg_s"), ("buoyancy_age_myr", "buoyancy_power_erg_s"), ("refill_age_myr", "refill_power_erg_s")):
                    bipolar[power_key] = sum(float(item[power_key]) for item in side_rows)
                bipolar["shell_age_role"] = "tracer_geometry_proxy_sound_primary_buoyancy_refill_provisional"
                bipolar["power_aggregation"] = "sum_side_powers"
                rows.append(bipolar)
        else:
            pressure = (float(cavity_by_side["negative_z"]["ambient_pressure_dyn_cm2"]) + float(cavity_by_side["positive_z"]["ambient_pressure_dyn_cm2"])) / 2.0
            for model, factor in models:
                total_volume = sum(float(row[f"volume_{depth}_depth_kpc3"]) for row in component_rows)
                row = row_for("bipolar_total", depth, factor, component=None, pressure=pressure, age_values=None, convention="bipolar_mean_shell_pressure")
                row["volume_kpc3"] = total_volume
                row["energy_erg"] = pressure * total_volume * KPC_CM**3 * factor
                for field in ("pV_erg", "two_point_five_pV_erg", "four_pV_erg"):
                    row[field] = row["energy_erg"] if (field, factor) in (("pV_erg", 1.0), ("two_point_five_pV_erg", 2.5), ("four_pV_erg", 4.0)) else ""
                row["ratio_to_level1_injected_energy"] = safe_ratio(row["energy_erg"], _level1_energy(level1_rows, "injected_energy_bipolar_elapsed"))
                row["ratio_to_level2_5e-3_total_energy"] = safe_ratio(row["energy_erg"], _level2_energy(level2_rows, "bipolar_total"))
                row["ratio_to_level3_thermal_plus_kinetic"] = safe_ratio(row["energy_erg"], float(next(item for item in level3_rows if item["side"] == "bipolar_total")["thermal_plus_kinetic_delta_erg"]))
                row["pressure_aggregation"] = "mean_pressure_bipolar_proxy"
                rows.append(row)
    return rows


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dependency_rows(*, manifest_rows: list[dict[str, str]], analysis_root: Path) -> list[dict[str, Any]]:
    case = manifest_rows[0]["case"]
    rows: list[dict[str, Any]] = []
    for row in manifest_rows:
        rows.append({
            "case": case,
            "nominal_age_myr": row["nominal_age_myr"],
            "actual_time_myr": row["actual_time_myr"],
            "remote_path": row["input_h5"],
            "size_bytes": row["file_size_bytes"],
            "sha256": "",
            "sha256_status": "not_rehashed_large_canonical_source",
            "canonical_copy_status": "canonical_remote_run_output",
            "data_class": "raw_snapshot_source",
            "lifecycle_state": "PROMOTED_SOURCE_PROTECTED",
            "dependency": "Goal 041 age-axis analysis and synthesis",
            "deletion_authority": "barry_only_after_goal041_synthesis_acceptance",
        })
    baseline = manifest_rows[0]
    rows.append({
        "case": case,
        "nominal_age_myr": 0,
        "actual_time_myr": baseline["baseline_time_myr"],
        "remote_path": baseline["baseline_h5"],
        "size_bytes": baseline["baseline_file_size_bytes"],
        "sha256": "",
        "sha256_status": "not_rehashed_large_canonical_source",
        "canonical_copy_status": "canonical_remote_run_output",
        "data_class": "zero_time_baseline",
        "lifecycle_state": "PROMOTED_SOURCE_PROTECTED",
        "dependency": "Goal 041 Level 3 thermal and kinetic deltas",
        "deletion_authority": "barry_only_after_goal041_synthesis_acceptance",
    })
    for path in sorted(analysis_root.rglob("*.tsv")):
        try:
            nominal = int(next(part for part in path.parts if part.startswith("age_") and part.endswith("myr"))[4:-3])
        except (StopIteration, ValueError) as exc:
            raise ValueError(f"cannot bind generated array to nominal age: {path}") from exc
        actual = next(row["actual_time_myr"] for row in manifest_rows if int(row["nominal_age_myr"]) == nominal)
        rows.append({
            "case": case,
            "nominal_age_myr": nominal,
            "actual_time_myr": actual,
            "remote_path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
            "sha256_status": "computed_after_validation",
            "canonical_copy_status": "canonical_goal041_analysis_output",
            "data_class": "processed_full_array",
            "lifecycle_state": "VALIDATED_INTERMEDIATE_PROTECTED",
            "dependency": "Goal 041 compact synthesis and figure review",
            "deletion_authority": "barry_only_after_goal041_synthesis_acceptance",
        })
    return rows


def write_sha256_manifest(output_dir: Path) -> None:
    target = output_dir / "goal041_sha256_manifest.sha256"
    lines = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path != target:
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    target.write_text("\n".join(lines) + "\n")


def build_analysis(*, case: str, source_manifest: Path, analysis_root: Path, compact_output: Path) -> dict[str, Any]:
    if case not in CASES:
        raise ValueError(f"unsupported case: {case}")
    manifest_rows = _manifest_rows(source_manifest, case)
    compact_output.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    tracer_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    level1_rows: list[dict[str, Any]] = []
    level2_rows: list[dict[str, Any]] = []
    cavity_rows: list[dict[str, Any]] = []
    level3_rows: list[dict[str, Any]] = []
    energy_rows: list[dict[str, Any]] = []
    for manifest_row in manifest_rows:
        nominal = int(manifest_row["nominal_age_myr"])
        actual = float(manifest_row["actual_time_myr"])
        age_dir = analysis_root / f"age_{nominal}myr"
        age_level3 = _level3_rows(age_dir, case, nominal, actual)
        level3_rows.extend(age_level3)
        if manifest_row["compute_xray"].lower() != "true":
            continue
        age_level1, age_level2 = _truth_rows(age_dir, case, nominal, actual)
        age_cavity = _cavity_rows(age_dir, case, nominal, actual)
        level1_rows.extend(age_level1)
        level2_rows.extend(age_level2)
        cavity_rows.extend(age_cavity)
        for view in VIEWS:
            loaded, projection = _load_map(age_dir, case, view, actual)
            map_analysis = recovery_builder.analyse_loaded_map(loaded, time_myr=actual)
            summary = {**map_analysis.summary_row, "nominal_age_myr": nominal, "actual_time_myr": actual}
            summary_rows.append(summary)
            components = [_with_time(row, case=case, nominal=nominal, actual=actual) for row in map_analysis.component_rows]
            tracers = [_with_time(row, case=case, nominal=nominal, actual=actual) for row in map_analysis.tracer_rows]
            component_rows.extend(components)
            tracer_rows.extend(tracers)
            sensitivity_rows.extend(_with_time(row, case=case, nominal=nominal, actual=actual) for row in recovery_builder._sensitivity_rows(loaded))
            projection_rows.append({**projection, "nominal_age_myr": nominal})
            energy_rows.extend(build_energy_rows(case=case, nominal=nominal, actual=actual, summary=summary, component_rows=components, cavity_rows=age_cavity, level1_rows=age_level1, level2_rows=age_level2, level3_rows=age_level3))

    if len(summary_rows) != 12 or len(projection_rows) != 12:
        raise ValueError("expected four new ages by three views")
    if len(sensitivity_rows) != 180:
        raise ValueError("expected the full 15-protocol grid for four ages by three views")
    if len(level2_rows) != 36 or len(cavity_rows) != 8 or len(level3_rows) != 15:
        raise ValueError("truth/cavity/Level 3 common-age coverage is incomplete")

    dependency = dependency_rows(manifest_rows=manifest_rows, analysis_root=analysis_root)
    _write_rows(compact_output / "xray_recovery_summary.csv", summary_rows)
    _write_rows(compact_output / "xray_component_summary.csv", component_rows or [{"status": "no_components"}])
    _write_rows(compact_output / "projected_tracer_alignment.csv", tracer_rows)
    _write_rows(compact_output / "xray_method_sensitivity.csv", sensitivity_rows)
    _write_rows(compact_output / "projection_validation.csv", projection_rows)
    _write_rows(compact_output / "level1_truth.csv", level1_rows)
    _write_rows(compact_output / "level2_truth.csv", level2_rows)
    _write_rows(compact_output / "cavity_shell_context.csv", cavity_rows)
    _write_rows(compact_output / "level3_ambient_energy.csv", level3_rows)
    _write_rows(compact_output / "cavity_energy_power_alignment.csv", energy_rows)
    _write_rows(compact_output / "source_time_manifest_case.csv", manifest_rows)
    _write_rows(compact_output / "product_dependency_ledger.csv", dependency)
    metadata = {
        "status": "complete_case_product_pending_endpoint_merge", "goal": "041", "case": case,
        "nominal_ages_myr": list(AGES), "views": list(VIEWS),
        "new_xray_truth_cavity_ages_myr": [10, 20, 30, 40],
        "level3_ages_myr": list(AGES),
        "endpoint_reuse": "Goal 040 accepted X-ray recovery and Level 1/2/cavity surface",
        "observer_protocol": "Goal 040 physical-area recovery reused",
        "projection_accumulators": {"0deg": "direct_y_axis_sum", "45deg": "edge_overlap_uniform_cell_projection", "90deg": "edge_overlap_uniform_cell_projection"},
        "gravity_status": GRAVITY_STATUS,
        "tracer_role": "post_hoc_validation_only",
        "archive_policy": "compact CSV/JSON/TXT/log/checksum/provenance only; TSV arrays remain remote under analysis root",
        "row_counts": {name.removesuffix(".csv"): sum(1 for _ in read_rows(compact_output / name)) for name in COMPACT_TABLES},
        "dependency_count": len(dependency),
    }
    metadata_path = compact_output / "goal041_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    write_sha256_manifest(compact_output)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, choices=CASES)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--compact-output", type=Path, required=True)
    args = parser.parse_args()
    metadata = build_analysis(case=args.case, source_manifest=args.source_manifest, analysis_root=args.analysis_root, compact_output=args.compact_output)
    print(f"goal041_analysis=complete case={metadata['case']} compact_output={args.compact_output}")


if __name__ == "__main__":
    main()
