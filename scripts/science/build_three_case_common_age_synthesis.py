#!/usr/bin/env python3
"""Merge Goal 041 case products with the accepted Goal 040 endpoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
GOAL041 = ROOT / "docs/science/assets/three_case_common_age_evolution_2026-07-13"
GOAL040 = ROOT / "docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12"
CASES = ("C-HI", "C-LO", "G-LO")
AGES = (10, 20, 30, 40, 50)
VIEWS = ("0deg", "45deg", "90deg")
DEPTHS = ("minor", "geometric", "major")
ENERGY_MODELS = (("pV", 1.0, "pV"), ("2.5pV", 2.5, "2_5pV"), ("4pV", 4.0, "4pV"))
AUTHORITATIVE_JET_POWER_ERG_S = {"C-HI": 1.0e45, "C-LO": 1.0e43, "G-LO": 1.0e43}
ENVIRONMENT_FAMILY = {"C-HI": "Stewart_cluster_002003", "C-LO": "Stewart_cluster_002003", "G-LO": "Stewart_group_002031"}
SECONDS_PER_MYR = 3.15576e13
KPC_CM = 3.0856775814913673e21
BASE_THRESHOLD = 0.005


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"missing input: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"duplicate or missing CSV header: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty input: {path}")
    return rows


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"JSON input is not an object: {path}")
    return value


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no output rows for {path}")
    fields = list(rows[0])
    if len(fields) != len(set(fields)) or any(set(row) != set(fields) for row in rows):
        raise ValueError(f"inconsistent output schema: {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def number(value: Any, *, context: str, positive: bool = False) -> float:
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise ValueError(f"invalid numeric value for {context}: {value!r}")
    return result


def ratio(numerator: float, denominator: float) -> float:
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("ratio requires finite numerator and positive denominator")
    return numerator / denominator


def threshold(value: Any) -> float:
    return float(value)


def boolean(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def validate_authoritative_power(case: str, value: float) -> None:
    expected = AUTHORITATIVE_JET_POWER_ERG_S[case]
    if not math.isclose(float(value), expected, rel_tol=1.0e-12, abs_tol=0.0):
        raise ValueError(
            f"{case} authoritative jet power is {expected:.12g} erg/s, got {value:.12g}"
        )


def _compact(case: str) -> Path:
    return GOAL041 / "review_products" / case / "compact"


def _validate_compact_manifest(case: str) -> None:
    compact = _compact(case)
    metadata = read_json(compact / "goal041_metadata.json")
    if metadata.get("status") != "complete_case_product_pending_endpoint_merge":
        raise ValueError(f"Goal 041 case product is not complete: {case}")
    for line in (compact / "goal041_sha256_manifest.sha256").read_text().splitlines():
        expected, name = line.split(None, 1)
        path = compact / name.strip()
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"Goal 041 compact hash mismatch: {case}/{path.name}")


def _manifest_by_case_age() -> dict[tuple[str, int], dict[str, str]]:
    result: dict[tuple[str, int], dict[str, str]] = {}
    for case in CASES:
        rows = read_rows(_compact(case) / "source_time_manifest_case.csv")
        for row in rows:
            key = (case, int(row["nominal_age_myr"]))
            if key in result:
                raise ValueError(f"duplicate source manifest key: {key}")
            result[key] = row
    if set(result) != {(case, age) for case in CASES for age in AGES}:
        raise ValueError("source manifests do not cover all case-age combinations")
    return result


def _endpoint_level1(case: str) -> dict[str, str]:
    path = GOAL040 / "remote_products" / "products" / case / "truth" / "level1_injected_energy.csv"
    return {row["metric"]: row["value"] for row in read_rows(path)}


def _level2_row(case: str, age: int) -> dict[str, str]:
    if age < 50:
        rows = read_rows(_compact(case) / "level2_truth.csv")
        selected = [
            row for row in rows
            if int(row["nominal_age_myr"]) == age
            and math.isclose(threshold(row["threshold"]), BASE_THRESHOLD)
            and row["side"] == "bipolar_total"
        ]
    else:
        path = GOAL040 / "remote_products" / "products" / case / "truth" / "level2_tracer_lobe_truth.csv"
        selected = [
            row for row in read_rows(path)
            if math.isclose(threshold(row["threshold"]), BASE_THRESHOLD)
            and row["side"] == "bipolar_total"
        ]
    if len(selected) != 1:
        raise ValueError(f"missing unique Level 2 bipolar row for {case}/{age}")
    return selected[0]


def _level3_row(case: str, age: int, side: str = "bipolar_total") -> dict[str, str]:
    selected = [
        row for row in read_rows(_compact(case) / "level3_ambient_energy.csv")
        if int(row["nominal_age_myr"]) == age and row["side"] == side
    ]
    if len(selected) != 1:
        raise ValueError(f"missing unique Level 3 row for {case}/{age}/{side}")
    return selected[0]


def _build_provenance(manifests: dict[tuple[str, int], dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        endpoint_level1 = _endpoint_level1(case)
        endpoint_power = number(endpoint_level1["jet_power_one_sided"], context=f"{case} endpoint power", positive=True)
        validate_authoritative_power(case, endpoint_power)
        for age in AGES:
            source = manifests[(case, age)]
            reported = number(source["jet_power_erg_s"], context=f"{case}/{age} manifest power", positive=True)
            expected = AUTHORITATIVE_JET_POWER_ERG_S[case]
            corrected = not math.isclose(reported, expected, rel_tol=1.0e-12, abs_tol=0.0)
            if corrected and case != "C-HI":
                raise ValueError(f"unexpected power mismatch for {case}/{age}")
            rows.append({
                "case": case,
                "nominal_age_myr": age,
                "actual_time_myr": source["actual_time_myr"],
                "environment_family": ENVIRONMENT_FAMILY[case],
                "source_goal": "Goal 040" if age == 50 else "Goal 041",
                "endpoint_reuse_id": source["endpoint_reuse_id"],
                "source_manifest_one_sided_power_erg_s": reported,
                "authoritative_one_sided_power_erg_s": expected,
                "accepted_endpoint_one_sided_power_erg_s": endpoint_power,
                "power_binding_status": (
                    "accepted_goal040_authoritative" if age == 50
                    else "corrected_from_authoritative_contract" if corrected
                    else "authoritative_manifest_match"
                ),
                "gravity_status": "excluded_blocked_missing_potential",
                "inference_scope": "descriptive_single_simulation_case",
            })
    return rows


def _build_truth(provenance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    provenance_by_key = {(row["case"], row["nominal_age_myr"]): row for row in provenance}
    rows: list[dict[str, Any]] = []
    for case in CASES:
        for age in AGES:
            provenance_row = provenance_by_key[(case, age)]
            actual = number(provenance_row["actual_time_myr"], context="actual age", positive=True)
            power = AUTHORITATIVE_JET_POWER_ERG_S[case]
            injected = 2.0 * power * actual * SECONDS_PER_MYR
            level2 = _level2_row(case, age)
            level3 = _level3_row(case, age)
            level2_thermal = number(level2["thermal_energy_erg"], context="Level 2 thermal")
            level2_kinetic = number(level2["kinetic_energy_erg"], context="Level 2 kinetic")
            level2_total = number(level2["total_energy_erg"], context="Level 2 total", positive=True)
            if not math.isclose(level2_thermal + level2_kinetic, level2_total, rel_tol=1.0e-9):
                raise ValueError(f"Level 2 energy sum mismatch for {case}/{age}")
            level3_thermal = number(level3["thermal_delta_erg"], context="Level 3 thermal")
            level3_kinetic = number(level3["kinetic_delta_erg"], context="Level 3 kinetic")
            level3_total = number(level3["thermal_plus_kinetic_delta_erg"], context="Level 3 total", positive=True)
            if not math.isclose(level3_thermal + level3_kinetic, level3_total, rel_tol=1.0e-9):
                raise ValueError(f"Level 3 energy sum mismatch for {case}/{age}")
            rows.append({
                "case": case,
                "nominal_age_myr": age,
                "actual_time_myr": actual,
                "source_goal": provenance_row["source_goal"],
                "one_sided_jet_power_erg_s": power,
                "power_binding_status": provenance_row["power_binding_status"],
                "injected_energy_bipolar_elapsed_erg": injected,
                "level2_tracer_threshold": BASE_THRESHOLD,
                "level2_volume_kpc3": number(level2["volume_kpc3"], context="Level 2 volume", positive=True),
                "level2_thermal_energy_erg": level2_thermal,
                "level2_kinetic_energy_erg": level2_kinetic,
                "level2_total_energy_erg": level2_total,
                "level3_thermal_delta_erg": level3_thermal,
                "level3_kinetic_delta_erg": level3_kinetic,
                "level3_thermal_plus_kinetic_delta_erg": level3_total,
                "level2_total_over_injected": ratio(level2_total, injected),
                "level3_thermal_over_injected": ratio(level3_thermal, injected),
                "level3_kinetic_over_injected": ratio(level3_kinetic, injected),
                "level3_total_over_injected": ratio(level3_total, injected),
                "level3_thermal_fraction": ratio(level3_thermal, level3_total),
                "ratio_interpretation": "normalized_response_not_closed_energy_partition",
                "gravity_status": "excluded_blocked_missing_potential",
            })
    return rows


def _observer_source(case: str, age: int) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]]]:
    if age < 50:
        summary = [row for row in read_rows(_compact(case) / "xray_recovery_summary.csv") if int(row["nominal_age_myr"]) == age]
        alignment = [row for row in read_rows(_compact(case) / "projected_tracer_alignment.csv") if int(row["nominal_age_myr"]) == age and math.isclose(threshold(row["tracer_threshold"]), BASE_THRESHOLD)]
        projection = {
            row["view"]: row for row in read_rows(_compact(case) / "projection_validation.csv")
            if int(row["nominal_age_myr"]) == age
        }
    else:
        summary = [row for row in read_rows(GOAL040 / "xray_recovery_summary.csv") if row["case"] == case]
        alignment = [row for row in read_rows(GOAL040 / "projected_tracer_alignment.csv") if row["case"] == case and math.isclose(threshold(row["tracer_threshold"]), BASE_THRESHOLD)]
        endpoint = [row for row in read_rows(GOAL041 / "endpoint_reuse_contract.csv") if row["case"] == case]
        projection = {
            row["view"]: {
                "projection_accumulator": row["projection_accumulator"],
                "empty_column_fraction": "",
                "status": "accepted_goal040_reuse",
            }
            for row in endpoint
        }
    if len(summary) != 3 or len(alignment) != 3 or set(projection) != set(VIEWS):
        raise ValueError(f"observer surface incomplete for {case}/{age}")
    return summary, alignment, projection


def _build_observer(truth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    truth = {(row["case"], row["nominal_age_myr"]): row for row in truth_rows}
    rows: list[dict[str, Any]] = []
    for case in CASES:
        for age in AGES:
            summaries, alignments, projection = _observer_source(case, age)
            alignment_by_view = {row["view"]: row for row in alignments}
            for summary in summaries:
                view = summary["view"]
                aligned = alignment_by_view[view]
                topology = summary["topology_class"]
                component_count = int(summary["component_count"])
                valid = topology == "two_separate_components" and component_count == 2
                volume = number(summary["volume_geometric_depth_kpc3"], context="X-ray volume")
                mean_deficit = summary["mean_fractional_deficit"]
                mean_deficit_value: float | str = "" if str(mean_deficit).lower() == "nan" else number(mean_deficit, context="mean deficit")
                if volume == 0.0 and topology != "no_significant_component":
                    raise ValueError(f"zero X-ray volume without no-component status: {case}/{age}/{view}")
                rows.append({
                    "case": case,
                    "nominal_age_myr": age,
                    "actual_time_myr": truth[(case, age)]["actual_time_myr"],
                    "view": view,
                    "source_goal": "Goal 040" if age == 50 else "Goal 041",
                    "candidate_selection_basis": summary["candidate_selection_basis"],
                    "radial_bin_kpc": summary["radial_bin_kpc"],
                    "radial_smoothing_kpc": summary["radial_smoothing_kpc"],
                    "candidate_fraction_percent": summary["candidate_fraction_percent"],
                    "component_count": component_count,
                    "topology_class": topology,
                    "retained_area_kpc2": summary["retained_area_kpc2"],
                    "mean_fractional_deficit": mean_deficit_value,
                    "area_integrated_fractional_deficit_kpc2": summary["area_integrated_fractional_deficit_kpc2"],
                    "volume_minor_depth_kpc3": summary["volume_minor_depth_kpc3"],
                    "volume_geometric_depth_kpc3": summary["volume_geometric_depth_kpc3"],
                    "volume_major_depth_kpc3": summary["volume_major_depth_kpc3"],
                    "volume_geometric_over_level2": ratio(volume, truth[(case, age)]["level2_volume_kpc3"]),
                    "tracer_threshold": BASE_THRESHOLD,
                    "tracer_intersection_over_union": aligned["intersection_over_union"],
                    "tracer_dice": aligned["dice"],
                    "xray_precision": aligned["xray_precision"],
                    "tracer_recall": aligned["tracer_recall"],
                    "projection_accumulator": projection[view]["projection_accumulator"],
                    "empty_column_fraction": projection[view].get("empty_column_fraction", ""),
                    "quantitative_volume_valid": str(valid).lower(),
                    "topology_interpretation": "quantitative_two_component" if valid else "diagnostic_only_topology_failure",
                })
    return rows


def _shell_rows(case: str, age: int) -> dict[str, dict[str, str]]:
    if age < 50:
        rows = [row for row in read_rows(_compact(case) / "cavity_shell_context.csv") if int(row["nominal_age_myr"]) == age]
    else:
        rows = [row for row in read_rows(GOAL040 / "tracer_shell_pressure_context.csv") if row["case"] == case]
    result = {row["side"]: row for row in rows}
    if set(result) != {"negative_z", "positive_z"}:
        raise ValueError(f"shell context incomplete for {case}/{age}")
    return result


def _endpoint_hybrid_rows(case: str, truth: dict[tuple[str, int], dict[str, Any]]) -> list[dict[str, Any]]:
    alignment_rows = [row for row in read_rows(GOAL040 / "xray_truth_alignment.csv") if row["case"] == case]
    recovery = {row["view"]: row for row in read_rows(GOAL040 / "xray_recovery_summary.csv") if row["case"] == case}
    shell = _shell_rows(case, 50)
    level1 = truth[(case, 50)]["injected_energy_bipolar_elapsed_erg"]
    level2 = truth[(case, 50)]["level2_total_energy_erg"]
    level3 = truth[(case, 50)]["level3_thermal_plus_kinetic_delta_erg"]
    rows: list[dict[str, Any]] = []
    for aligned in alignment_rows:
        view = aligned["view"]
        topology = recovery[view]["topology_class"]
        valid = topology == "two_separate_components" and int(recovery[view]["component_count"]) == 2
        if not valid:
            raise ValueError(f"accepted endpoint is not side assignable for {case}/{view}")
        for depth in DEPTHS:
            for model, factor, prefix in ENERGY_MODELS:
                side_output: list[dict[str, Any]] = []
                for side in ("negative_z", "positive_z"):
                    volume = number(aligned[f"xray_volume_{depth}_depth_{side}_kpc3"], context="endpoint side volume", positive=True)
                    energy = number(aligned[f"hybrid_{prefix}_{depth}_depth_{side}_erg"], context="endpoint side energy", positive=True)
                    pressure = number(aligned[f"{side}_pressure_dyn_cm2"], context="endpoint side pressure", positive=True)
                    shell_row = shell[side]
                    ages = {name: number(shell_row[name], context=name, positive=True) for name in ("sound_age_myr", "buoyancy_age_myr", "refill_age_myr")}
                    row = {
                        "case": case, "nominal_age_myr": 50, "actual_time_myr": truth[(case, 50)]["actual_time_myr"],
                        "view": view, "side": side, "volume_depth_assumption": f"{depth}_depth",
                        "energy_model": model, "topology_status": topology,
                        "energy_pressure_convention": "side_specific_tracer_shell_pressure",
                        "pressure_aggregation": "single_side", "pressure_dyn_cm2": pressure,
                        "volume_kpc3": volume, "energy_erg": energy,
                        "pV_erg": energy if factor == 1.0 else "", "two_point_five_pV_erg": energy if factor == 2.5 else "", "four_pV_erg": energy if factor == 4.0 else "",
                        "ratio_to_level1_injected_energy": ratio(energy, level1 / 2.0),
                        "ratio_to_level2_5e-3_total_energy": ratio(energy, number(_level2_side(case, 50, side)["total_energy_erg"], context="Level 2 side energy", positive=True)),
                        "ratio_to_level3_thermal_plus_kinetic": ratio(energy, number(_level3_row(case, 50, side)["thermal_plus_kinetic_delta_erg"], context="Level 3 side energy", positive=True)),
                        "sound_age_myr": ages["sound_age_myr"], "buoyancy_age_myr": ages["buoyancy_age_myr"], "refill_age_myr": ages["refill_age_myr"],
                        "sound_power_erg_s": energy / (ages["sound_age_myr"] * SECONDS_PER_MYR),
                        "buoyancy_power_erg_s": energy / (ages["buoyancy_age_myr"] * SECONDS_PER_MYR),
                        "refill_power_erg_s": energy / (ages["refill_age_myr"] * SECONDS_PER_MYR),
                        "shell_age_role": "tracer_geometry_proxy_sound_primary_buoyancy_refill_provisional",
                        "power_aggregation": "single_side_energy_over_age", "gravity_status": "excluded_blocked",
                        "source_goal": "Goal 040", "quantitative_energy_valid": "true", "quantitative_power_valid": "true",
                    }
                    side_output.append(row)
                    rows.append(row)
                total_energy = sum(number(row["energy_erg"], context="side energy") for row in side_output)
                total_volume = sum(number(row["volume_kpc3"], context="side volume") for row in side_output)
                bipolar = dict(side_output[0])
                bipolar.update({
                    "side": "bipolar_total", "pressure_aggregation": "side_specific_energy_sum",
                    "pressure_dyn_cm2": sum(number(row["pressure_dyn_cm2"], context="pressure") for row in side_output) / 2.0,
                    "volume_kpc3": total_volume, "energy_erg": total_energy,
                    "pV_erg": total_energy if factor == 1.0 else "", "two_point_five_pV_erg": total_energy if factor == 2.5 else "", "four_pV_erg": total_energy if factor == 4.0 else "",
                    "ratio_to_level1_injected_energy": ratio(total_energy, level1),
                    "ratio_to_level2_5e-3_total_energy": ratio(total_energy, level2),
                    "ratio_to_level3_thermal_plus_kinetic": ratio(total_energy, level3),
                    "sound_age_myr": sum(number(row["sound_age_myr"], context="age") for row in side_output) / 2.0,
                    "buoyancy_age_myr": sum(number(row["buoyancy_age_myr"], context="age") for row in side_output) / 2.0,
                    "refill_age_myr": sum(number(row["refill_age_myr"], context="age") for row in side_output) / 2.0,
                    "sound_power_erg_s": sum(number(row["sound_power_erg_s"], context="power") for row in side_output),
                    "buoyancy_power_erg_s": sum(number(row["buoyancy_power_erg_s"], context="power") for row in side_output),
                    "refill_power_erg_s": sum(number(row["refill_power_erg_s"], context="power") for row in side_output),
                    "power_aggregation": "sum_side_powers",
                })
                expected = number(aligned[f"hybrid_{prefix}_{depth}_depth_erg"], context="locked endpoint energy", positive=True)
                if not math.isclose(total_energy, expected, rel_tol=1.0e-12):
                    raise ValueError(f"endpoint hybrid reconstruction mismatch for {case}/{view}/{depth}/{model}")
                rows.append(bipolar)
    return rows


def _level2_side(case: str, age: int, side: str) -> dict[str, str]:
    if age < 50:
        source = read_rows(_compact(case) / "level2_truth.csv")
        selected = [row for row in source if int(row["nominal_age_myr"]) == age and math.isclose(threshold(row["threshold"]), BASE_THRESHOLD) and row["side"] == side]
    else:
        source = read_rows(GOAL040 / "remote_products" / "products" / case / "truth" / "level2_tracer_lobe_truth.csv")
        selected = [row for row in source if math.isclose(threshold(row["threshold"]), BASE_THRESHOLD) and row["side"] == side]
    if len(selected) != 1:
        raise ValueError(f"missing Level 2 side row for {case}/{age}/{side}")
    return selected[0]


def _build_hybrid(truth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    truth = {(row["case"], row["nominal_age_myr"]): row for row in truth_rows}
    rows: list[dict[str, Any]] = []
    for case in CASES:
        for source in read_rows(_compact(case) / "cavity_energy_power_alignment.csv"):
            age = int(source["nominal_age_myr"])
            energy = number(source["energy_erg"], context="hybrid energy")
            level1_denominator = truth[(case, age)]["injected_energy_bipolar_elapsed_erg"]
            if source["side"] != "bipolar_total":
                level1_denominator /= 2.0
            level2_denominator = number(_level2_side(case, age, source["side"])["total_energy_erg"], context="Level 2 denominator", positive=True)
            level3_denominator = number(_level3_row(case, age, source["side"])["thermal_plus_kinetic_delta_erg"], context="Level 3 denominator", positive=True)
            valid = source["topology_status"] == "two_separate_components"
            output: dict[str, Any] = dict(source)
            output["ratio_to_level1_injected_energy"] = ratio(energy, level1_denominator)
            output["ratio_to_level2_5e-3_total_energy"] = ratio(energy, level2_denominator)
            output["ratio_to_level3_thermal_plus_kinetic"] = ratio(energy, level3_denominator)
            output["source_goal"] = "Goal 041"
            output["quantitative_energy_valid"] = str(valid).lower()
            output["quantitative_power_valid"] = str(valid and bool(source["sound_power_erg_s"])).lower()
            rows.append(output)
        rows.extend(_endpoint_hybrid_rows(case, truth))
    return rows


def _method_source(case: str, age: int) -> list[dict[str, str]]:
    if age < 50:
        return [row for row in read_rows(_compact(case) / "xray_method_sensitivity.csv") if int(row["nominal_age_myr"]) == age]
    return [row for row in read_rows(GOAL040 / "method_sensitivity.csv") if row["case"] == case]


def _build_sensitivity(truth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    truth = {(row["case"], row["nominal_age_myr"]): row for row in truth_rows}
    rows: list[dict[str, Any]] = []
    for case in CASES:
        for age in AGES:
            shell = _shell_rows(case, age)
            mean_pressure = sum(number(row["ambient_pressure_dyn_cm2"], context="shell pressure", positive=True) for row in shell.values()) / 2.0
            for view in VIEWS:
                protocols = [row for row in _method_source(case, age) if row["view"] == view]
                if len(protocols) != 15:
                    raise ValueError(f"method grid does not contain 15 rows for {case}/{age}/{view}")
                base = [row for row in protocols if boolean(row["is_base"])]
                if len(base) != 1:
                    raise ValueError(f"method grid does not contain one base row for {case}/{age}/{view}")
                valid = [row for row in protocols if row["topology_class"] == "two_separate_components" and int(row["component_count"]) == 2]
                volumes = [number(row["volume_geometric_depth_kpc3"], context="sensitivity volume", positive=True) for row in valid]
                ratios = [ratio(2.5 * mean_pressure * volume * KPC_CM**3, truth[(case, age)]["injected_energy_bipolar_elapsed_erg"]) for volume in volumes]
                rows.append({
                    "case": case, "nominal_age_myr": age, "view": view,
                    "source_goal": "Goal 040" if age == 50 else "Goal 041",
                    "base_topology_class": base[0]["topology_class"],
                    "base_component_count": base[0]["component_count"],
                    "protocol_count": len(protocols), "valid_protocol_count": len(valid),
                    "valid_protocol_fraction": len(valid) / len(protocols),
                    "validity_basis": "two_separate_components_component_count_2",
                    "valid_volume_min_kpc3": min(volumes) if volumes else "",
                    "valid_volume_median_kpc3": median(volumes) if volumes else "",
                    "valid_volume_max_kpc3": max(volumes) if volumes else "",
                    "valid_2_5pV_over_injected_min": min(ratios) if ratios else "",
                    "valid_2_5pV_over_injected_median": median(ratios) if ratios else "",
                    "valid_2_5pV_over_injected_max": max(ratios) if ratios else "",
                    "sensitivity_interpretation": "prespecified_method_envelope_not_sampling_uncertainty",
                })
    return rows


def _build_contrasts(truth_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    truth = {(row["case"], row["nominal_age_myr"]): row for row in truth_rows}
    rows: list[dict[str, Any]] = []
    for left, right, interpretation in (
        ("C-HI", "C-LO", "same_environment_family_power_associated_descriptive_contrast"),
        ("C-LO", "G-LO", "same_nominal_power_environment_associated_descriptive_contrast"),
    ):
        for age in AGES:
            for metric in ("level2_total_over_injected", "level3_total_over_injected"):
                left_value = number(truth[(left, age)][metric], context=metric, positive=True)
                right_value = number(truth[(right, age)][metric], context=metric, positive=True)
                rows.append({
                    "left_case": left, "right_case": right, "nominal_age_myr": age,
                    "metric": metric, "left_value": left_value, "right_value": right_value,
                    "left_minus_right": left_value - right_value,
                    "left_over_right": ratio(left_value, right_value),
                    "contrast_interpretation": interpretation,
                    "identification_status": "descriptive_confounded_single_simulation_cases",
                })
    return rows


def _write_figures(output_dir: Path, truth: list[dict[str, Any]], observer: list[dict[str, Any]], hybrid: list[dict[str, Any]]) -> None:
    colors = {"C-HI": "#b23a48", "C-LO": "#2878b5", "G-LO": "#3f8f5f"}
    view_styles = {"0deg": "-", "45deg": "--", "90deg": ":"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), constrained_layout=True)
    for case in CASES:
        case_rows = sorted((row for row in truth if row["case"] == case), key=lambda row: row["nominal_age_myr"])
        ages = [row["nominal_age_myr"] for row in case_rows]
        axes[0].plot(ages, [row["level2_total_over_injected"] for row in case_rows], marker="o", color=colors[case], label=case)
        axes[1].plot(ages, [row["level3_thermal_over_injected"] for row in case_rows], marker="o", color=colors[case], label=f"{case} thermal")
        axes[1].plot(ages, [row["level3_kinetic_over_injected"] for row in case_rows], marker="s", linestyle="--", color=colors[case], label=f"{case} kinetic")
    for ax in axes:
        ax.set_yscale("log")
        ax.set_xlabel("Nominal age (Myr)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Normalized response")
    axes[0].set_title("Level 2 tracer-lobe total / elapsed injection")
    axes[1].set_title("Level 3 ambient change / elapsed injection")
    axes[0].legend(frameon=False)
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    fig.suptitle("Three-case common-age energy responses (not a closed energy partition)")
    fig.savefig(output_dir / "energy_response_evolution.png", dpi=180, facecolor="white")
    plt.close(fig)

    hybrid_lookup = {
        (row["case"], int(row["nominal_age_myr"]), row["view"]): row
        for row in hybrid
        if row["side"] == "bipolar_total"
        and row["volume_depth_assumption"] == "geometric_depth"
        and row["energy_model"] == "2.5pV"
    }
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), constrained_layout=True)
    panels = (
        ("mean_fractional_deficit", "Mean X-ray fractional deficit", False),
        ("tracer_recall", "Tracer recall at threshold 0.005", False),
        ("volume_geometric_over_level2", "X-ray geometric volume / Level 2 volume", True),
        ("hybrid_2_5pV_over_injected", "Hybrid geometric 2.5pV / elapsed injection", True),
    )
    observer_lookup = {(row["case"], int(row["nominal_age_myr"]), row["view"]): row for row in observer}
    for ax, (metric, title, require_valid) in zip(axes.flat, panels, strict=True):
        for case in CASES:
            for view in VIEWS:
                x: list[int] = []
                y: list[float] = []
                invalid_ages: list[int] = []
                for age in AGES:
                    obs = observer_lookup[(case, age, view)]
                    valid = obs["quantitative_volume_valid"] == "true"
                    if metric == "hybrid_2_5pV_over_injected":
                        source = hybrid_lookup[(case, age, view)]
                        value = source["ratio_to_level1_injected_energy"]
                        valid = source["quantitative_energy_valid"] == "true"
                    else:
                        value = obs[metric]
                    if value != "" and (valid or not require_valid):
                        x.append(age)
                        y.append(number(value, context=metric))
                    elif require_valid:
                        invalid_ages.append(age)
                if x:
                    ax.plot(x, y, color=colors[case], linestyle=view_styles[view], marker="o", markersize=3, label=f"{case} {view}")
                if invalid_ages:
                    ax.scatter(invalid_ages, [0.0] * len(invalid_ages), color=colors[case], marker="x", s=25)
        ax.set_title(title)
        ax.set_xlabel("Nominal age (Myr)")
        ax.grid(alpha=0.25)
    axes[0, 0].set_ylabel("Descriptive response")
    axes[1, 0].set_ylabel("Quantitative only when topology-valid")
    axes[0, 0].legend(frameon=False, fontsize=6, ncol=3)
    fig.suptitle("Observer recovery and hybrid proxy evolution; x marks topology-invalid ages")
    fig.savefig(output_dir / "observer_hybrid_evolution.png", dpi=180, facecolor="white")
    plt.close(fig)


def _correction_rows() -> list[dict[str, Any]]:
    return [{
        "case": "C-HI",
        "source_manifest_affected_nominal_ages_myr": "10;20;30;40;50",
        "derived_outputs_corrected_nominal_ages_myr": "10;20;30;40",
        "reported_one_sided_power_erg_s": 1.0e44,
        "authoritative_one_sided_power_erg_s": 1.0e45,
        "correction_factor": 10.0,
        "correction_scope": "derived_level1_and_dependent_ratios_only",
        "unmodified_surfaces": "retrieved compact archives; XRAiSE; Level2; Level3; cavity geometry; shell context",
        "authority": "docs/science/three_case_spec.md; docs/codex_utas_phys_hons_meeting_2_action_plan.md; accepted Goal 040 Level1",
        "interpretation": "Goal041 source-manifest packaging error; no simulation or observational product rerun required",
    }]


def _validation_rows(provenance: list[dict[str, Any]], truth: list[dict[str, Any]], observer: list[dict[str, Any]], hybrid: list[dict[str, Any]], sensitivity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        ("compact_sha256_manifests", all((_validate_compact_manifest(case) is None) for case in CASES), "three case manifests verified"),
        ("case_age_coverage", len(provenance) == 15 and len(truth) == 15, "3 cases x 5 ages"),
        ("observer_coverage", len(observer) == 45, "3 cases x 5 ages x 3 views"),
        ("hybrid_coverage", len(hybrid) == 963, "returned age rows plus 243 endpoint rows"),
        ("method_sensitivity_coverage", len(sensitivity) == 45 and all(int(row["protocol_count"]) == 15 for row in sensitivity), "45 panels x 15 protocols"),
        ("authoritative_power_binding", all(number(row["one_sided_jet_power_erg_s"], context="power") == AUTHORITATIVE_JET_POWER_ERG_S[row["case"]] for row in truth), "frozen three-case power contract"),
        ("endpoint_method_contract", all(row["candidate_selection_basis"] == "projected_physical_area_fraction" and float(row["radial_bin_kpc"]) == 5.0 and float(row["radial_smoothing_kpc"]) == 10.0 and float(row["candidate_fraction_percent"]) == 1.0 for row in observer), "Goal040 physical-area base method"),
        ("topology_invalid_values_flagged", all(row["quantitative_volume_valid"] == "false" for row in observer if row["topology_class"] != "two_separate_components" or int(row["component_count"]) != 2), "connected/missing/multiple masks diagnostic only"),
        ("gravity_excluded", all(row["gravity_status"] == "excluded_blocked_missing_potential" for row in truth), "no gravitational normalization emitted"),
    ]
    rows = [{"gate": name, "status": "passed" if passed else "failed", "evidence": evidence} for name, passed, evidence in checks]
    if not all(row["status"] == "passed" for row in rows):
        failed = [row["gate"] for row in rows if row["status"] != "passed"]
        raise ValueError(f"synthesis validation failed: {failed}")
    return rows


def _write_manifest(output_dir: Path) -> None:
    target = output_dir / "local_asset_manifest.sha256"
    lines = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path != target:
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    target.write_text("\n".join(lines) + "\n")


def build_synthesis(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        _validate_compact_manifest(case)
    manifests = _manifest_by_case_age()
    provenance = _build_provenance(manifests)
    truth = _build_truth(provenance)
    observer = _build_observer(truth)
    hybrid = _build_hybrid(truth)
    sensitivity = _build_sensitivity(truth)
    contrasts = _build_contrasts(truth)
    corrections = _correction_rows()
    validation = _validation_rows(provenance, truth, observer, hybrid, sensitivity)

    write_rows(output_dir / "case_age_provenance.csv", provenance)
    write_rows(output_dir / "truth_energy_evolution.csv", truth)
    write_rows(output_dir / "observer_recovery_evolution.csv", observer)
    write_rows(output_dir / "hybrid_cavity_evolution.csv", hybrid)
    write_rows(output_dir / "method_sensitivity_summary.csv", sensitivity)
    write_rows(output_dir / "descriptive_contrasts.csv", contrasts)
    write_rows(output_dir / "correction_register.csv", corrections)
    write_rows(output_dir / "validation_report.csv", validation)
    _write_figures(output_dir, truth, observer, hybrid)

    metadata = {
        "status": "complete_local_synthesis",
        "decision_label": "THREE_CASE_COMMON_AGE_SYNTHESIS_COMPLETE",
        "cases": list(CASES), "nominal_ages_myr": list(AGES), "views": list(VIEWS),
        "authoritative_one_sided_jet_power_erg_s": AUTHORITATIVE_JET_POWER_ERG_S,
        "corrections": corrections,
        "row_counts": {
            "case_age_provenance": len(provenance), "truth_energy_evolution": len(truth),
            "observer_recovery_evolution": len(observer), "hybrid_cavity_evolution": len(hybrid),
            "method_sensitivity_summary": len(sensitivity), "descriptive_contrasts": len(contrasts),
            "validation_report": len(validation),
        },
        "scientific_scope": "descriptive_three_case_production_prove_out",
        "replication": "one deterministic simulation per case; ages and views are not independent replicates",
        "ratio_interpretation": "normalized responses, not a closed energy partition or efficiency estimate",
        "topology_rule": "quantitative volumes and hybrid trajectories require exactly two separate components",
        "projection_uncertainty": "three-view sensitivity only, not sampling uncertainty",
        "method_uncertainty": "prespecified 15-protocol envelope only",
        "gravity_status": "excluded_blocked_missing_potential",
        "publication_ready": False,
        "final_observational_topology_frozen": False,
        "next_step": "scientific review and raw-data lifecycle decision; no additional compute required for Goal041",
    }
    (output_dir / "three_case_common_age_synthesis_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    _write_manifest(output_dir)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=GOAL041 / "synthesis")
    args = parser.parse_args()
    metadata = build_synthesis(args.output_dir)
    print(f"status={metadata['status']}")
    print(f"decision_label={metadata['decision_label']}")


if __name__ == "__main__":
    main()
