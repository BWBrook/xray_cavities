#!/usr/bin/env python3
"""Validate and package the selected-age native shock-energy surface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
EXPECTED_AGES = {
    "C-HI": (10, 20, 30, 40, 50),
    "C-LO": (10, 20, 30, 40, 50),
    "G-HI": (10, 20, 30, 40),
    "G-LO": (10, 20, 30, 40, 50),
}
THRESHOLD_FACTORS = (0.5, 1.0, 2.0)
SIDES = ("negative_z", "positive_z", "bipolar_total")
ALLOWED_STATUSES = {
    "quantitative_seeded_component",
    "quantitative_bilateral",
    "unresolved_bilateral_gate",
    "unresolved_no_accepted_front",
    "unresolved_non_supersonic_front",
    "unresolved_no_seeded_component",
    "unresolved_too_small",
    "unresolved_boundary_touch",
    "unresolved_front_extent_mismatch",
}
ENERGY_FIELDS = (
    "thermal_delta_erg",
    "kinetic_delta_erg",
    "gravitational_delta_erg",
    "total_delta_erg",
    "irreversible_heating_erg",
    "mask_volume_kpc3",
    "ambient_weighted_volume_kpc3",
    "ambient_weighted_mass_g",
    "selected_cell_count",
    "shock_fraction_of_injected",
    "irreversible_fraction_of_injected",
)
DECISION_LABEL = "SELECTED_AGE_NATIVE_SHOCK_PARTITION_GREEN_C_LO_LATE_FAIL_CLOSED"


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value: Any, *, context: str, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ProductError(f"non-numeric {context}: {value!r}") from exc
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise ProductError(f"invalid {context}: {value!r}")
    return result


def verify_manifest(root: Path) -> None:
    manifest = root / "local_asset_manifest.sha256"
    for line in manifest.read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = root / name
        if not path.is_file() or sha256_file(path) != digest:
            raise ProductError(f"asset-manifest mismatch: {path}")


def optional_summary(values: Sequence[float]) -> tuple[Any, Any, Any]:
    if not values:
        return "", "", ""
    return statistics.median(values), min(values), max(values)


def load_shock_surface(shock_root: Path) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, Any]],
    list[dict[str, str]],
]:
    combined: list[dict[str, str]] = []
    primary: list[dict[str, str]] = []
    sensitivity: list[dict[str, Any]] = []
    for case in CASES:
        case_root = shock_root / case
        verify_manifest(case_root)
        metadata = json.loads((case_root / "selected_age_native_shock_metadata.json").read_text())
        if metadata.get("status") != "complete_selected_age_native_shock_partition":
            raise ProductError(f"{case}: completion metadata failed")
        rows = read_rows(case_root / "native_shock_energy_selected_age.csv")
        expected_keys = {
            (case, age, side, factor)
            for age in EXPECTED_AGES[case]
            for side in SIDES
            for factor in THRESHOLD_FACTORS
        }
        observed_keys = {
            (row["case"], int(row["snapshot_index"]), row["side"], float(row["threshold_factor"]))
            for row in rows
        }
        if observed_keys != expected_keys or len(rows) != len(expected_keys):
            raise ProductError(f"{case}: selected-age coverage failed")
        for row in rows:
            if row["status"] not in ALLOWED_STATUSES:
                raise ProductError(f"{case}: unexpected status {row['status']}")
            quantitative = row["status"].startswith("quantitative_")
            if quantitative:
                for field in ENERGY_FIELDS:
                    finite(row[field], context=f"{case}/{field}")
                if finite(row["mask_volume_kpc3"], context="mask volume", positive=True) <= 0.0:
                    raise ProductError(f"{case}: invalid mask volume")
                if finite(row["selected_cell_count"], context="selected cells") < 100:
                    raise ProductError(f"{case}: insufficient selected-cell support")
            elif any(row[field] for field in ENERGY_FIELDS):
                raise ProductError(f"{case}: unresolved row contains quantitative values")
        combined.extend(rows)
        bipolar = [row for row in rows if row["side"] == "bipolar_total"]
        by_key = {
            (int(row["snapshot_index"]), float(row["threshold_factor"])): row for row in bipolar
        }
        for age in EXPECTED_AGES[case]:
            primary_row = by_key[(age, 1.0)]
            primary.append(primary_row)
            for factor in THRESHOLD_FACTORS:
                row = by_key[(age, factor)]
                output: dict[str, Any] = {
                    "case": case,
                    "snapshot_index": age,
                    "actual_time_myr": row["actual_time_myr"],
                    "threshold_factor": factor,
                    "status": row["status"],
                    "shock_fraction_of_injected": row["shock_fraction_of_injected"],
                    "irreversible_fraction_of_injected": row[
                        "irreversible_fraction_of_injected"
                    ],
                    "mask_volume_kpc3": row["mask_volume_kpc3"],
                    "total_delta_erg": row["total_delta_erg"],
                    "relative_shock_fraction_to_primary": "",
                    "relative_irreversible_fraction_to_primary": "",
                    "relative_volume_to_primary": "",
                }
                if row["status"] == "quantitative_bilateral" and primary_row[
                    "status"
                ] == "quantitative_bilateral":
                    for source, target in (
                        ("shock_fraction_of_injected", "relative_shock_fraction_to_primary"),
                        (
                            "irreversible_fraction_of_injected",
                            "relative_irreversible_fraction_to_primary",
                        ),
                        ("mask_volume_kpc3", "relative_volume_to_primary"),
                    ):
                        denominator = finite(primary_row[source], context=f"primary {source}")
                        output[target] = finite(row[source], context=source) / denominator
                sensitivity.append(output)
    controls = [
        read_rows(shock_root / "calibration" / f"{environment}_control_thresholds.csv")[0]
        for environment in ("cluster", "group")
    ]
    for row in controls:
        if int(row["control_file_count"]) != 6:
            raise ProductError("control snapshot count drifted")
        if row["control_grid_shape_nz_ny_nx"] != "500x400x400":
            raise ProductError("control grid shape drifted")
        if finite(row["control_joint_exceedance_fraction"], context="control exceedance") > 1e-6:
            raise ProductError("no-jet false-positive gate failed")
    if len(combined) != 171 or len(primary) != 19 or len(sensitivity) != 57:
        raise ProductError("full selected-age shock surface count failed")
    return combined, primary, sensitivity, controls


def case_summaries(
    primary: Sequence[Mapping[str, str]], sensitivity: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    for case in CASES:
        rows = [row for row in primary if row["case"] == case]
        quantitative = [row for row in rows if row["status"] == "quantitative_bilateral"]
        shock = [finite(row["shock_fraction_of_injected"], context="shock fraction") for row in quantitative]
        irreversible = [
            finite(row["irreversible_fraction_of_injected"], context="irreversible fraction")
            for row in quantitative
        ]
        half = [
            finite(row["relative_shock_fraction_to_primary"], context="half threshold ratio")
            for row in sensitivity
            if row["case"] == case
            and float(row["threshold_factor"]) == 0.5
            and row["relative_shock_fraction_to_primary"] != ""
        ]
        double = [
            finite(row["relative_shock_fraction_to_primary"], context="double threshold ratio")
            for row in sensitivity
            if row["case"] == case
            and float(row["threshold_factor"]) == 2.0
            and row["relative_shock_fraction_to_primary"] != ""
        ]
        shock_median, shock_min, shock_max = optional_summary(shock)
        irreversible_median, irreversible_min, irreversible_max = optional_summary(irreversible)
        half_median, half_min, half_max = optional_summary(half)
        double_median, double_min, double_max = optional_summary(double)
        output.append(
            {
                "case": case,
                "selected_age_count": len(rows),
                "quantitative_primary_count": len(quantitative),
                "unresolved_primary_count": len(rows) - len(quantitative),
                "primary_status_by_age": ";".join(
                    f"{row['snapshot_index']}:{row['status']}" for row in rows
                ),
                "shock_fraction_median": shock_median,
                "shock_fraction_min": shock_min,
                "shock_fraction_max": shock_max,
                "irreversible_fraction_median": irreversible_median,
                "irreversible_fraction_min": irreversible_min,
                "irreversible_fraction_max": irreversible_max,
                "half_threshold_ratio_median": half_median,
                "half_threshold_ratio_min": half_min,
                "half_threshold_ratio_max": half_max,
                "double_threshold_ratio_median": double_median,
                "double_threshold_ratio_min": double_min,
                "double_threshold_ratio_max": double_max,
                "interpretation_status": (
                    "late_age_fail_closed_non_supersonic_front"
                    if case == "C-LO"
                    else "quantitative_all_selected_ages"
                ),
            }
        )
    return output


def shock_additions(row: Mapping[str, str]) -> dict[str, Any]:
    quantitative = row["status"] == "quantitative_bilateral"
    return {
        "native_shock_threshold_factor": 1.0,
        "native_shock_status": row["status"],
        "native_shock_thermal_delta_erg": row["thermal_delta_erg"] if quantitative else "",
        "native_shock_kinetic_delta_erg": row["kinetic_delta_erg"] if quantitative else "",
        "native_shock_gravitational_delta_erg": (
            row["gravitational_delta_erg"] if quantitative else ""
        ),
        "native_shock_total_delta_erg": row["total_delta_erg"] if quantitative else "",
        "native_shock_irreversible_heating_erg": (
            row["irreversible_heating_erg"] if quantitative else ""
        ),
        "native_shock_mask_volume_kpc3": row["mask_volume_kpc3"] if quantitative else "",
        "native_shock_fraction_of_injected": (
            row["shock_fraction_of_injected"] if quantitative else ""
        ),
        "native_shock_irreversible_fraction_of_injected": (
            row["irreversible_fraction_of_injected"] if quantitative else ""
        ),
        "native_shock_control_role": row["control_role"],
        "native_shock_background_status": row["background_subtraction_status"],
    }


def join_goal066(
    *,
    primary: Sequence[Mapping[str, str]],
    native_path: Path,
    matched_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shock_by_key = {(row["case"], int(row["snapshot_index"])): row for row in primary}
    expected = {
        *((case, age) for case in ("C-HI", "C-LO", "G-LO") for age in (10, 20, 30, 40, 50)),
        *(("G-HI", age) for age in (10, 20, 30, 40)),
    }
    if set(shock_by_key) != expected:
        raise ProductError("primary shock keys do not match accepted Goal 066 surface")
    native_rows = read_rows(native_path)
    if {(row["case"], int(row["snapshot_index"])) for row in native_rows} != expected:
        raise ProductError("Goal 066 native keys do not match accepted surface")
    native_output = []
    for row in native_rows:
        key = (row["case"], int(row["snapshot_index"]))
        addition = shock_additions(shock_by_key[key])
        ratio: Any = ""
        if addition["native_shock_total_delta_erg"] != "":
            ambient = finite(row["ambient_total_delta_erg"], context="ambient total")
            if ambient != 0.0:
                ratio = finite(
                    addition["native_shock_total_delta_erg"], context="shock total"
                ) / ambient
        native_output.append(
            dict(row)
            | addition
            | {
                "native_shock_to_ambient_total": ratio,
                "native_shock_interpretation": (
                    "descriptive_background_dominated"
                    if row["case"] == "C-LO"
                    else (
                        "quantitative_selected_region_partition"
                        if addition["native_shock_total_delta_erg"] != ""
                        else "fail_closed_unresolved"
                    )
                ),
            }
        )
    matched_rows = read_rows(matched_path)
    matched_output = []
    for row in matched_rows:
        key = (row["case"], int(row["snapshot_index"]))
        if key not in shock_by_key:
            raise ProductError(f"Goal 066 observer row lacks shock key: {key}")
        addition = shock_additions(shock_by_key[key])
        observer_to_shock: Any = ""
        if row["observer_enthalpy_erg"] and addition["native_shock_total_delta_erg"] != "":
            observer_to_shock = finite(
                row["observer_enthalpy_erg"], context="observer enthalpy"
            ) / finite(addition["native_shock_total_delta_erg"], context="shock total", positive=True)
        matched_output.append(
            dict(row)
            | addition
            | {"observer_enthalpy_to_native_shock_total": observer_to_shock}
        )
    return native_output, matched_output


def make_figure(
    primary: Sequence[Mapping[str, str]],
    sensitivity: Sequence[Mapping[str, Any]],
    output_path: Path,
) -> None:
    colours = {"C-HI": "#2166ac", "C-LO": "#67a9cf", "G-HI": "#b2182b", "G-LO": "#ef8a62"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharex=True)
    for case in CASES:
        rows = sorted(
            (row for row in primary if row["case"] == case),
            key=lambda row: int(row["snapshot_index"]),
        )
        quantitative = [row for row in rows if row["status"] == "quantitative_bilateral"]
        ages = [int(row["snapshot_index"]) for row in quantitative]
        for axis, field, ylabel in (
            (axes[0], "shock_fraction_of_injected", "Shock-region energy / injected energy"),
            (
                axes[1],
                "irreversible_fraction_of_injected",
                "Irreversible heating / injected energy",
            ),
        ):
            values = [float(row[field]) for row in quantitative]
            axis.plot(ages, values, marker="o", color=colours[case], label=case)
            lower, upper = [], []
            for age in ages:
                candidates = [
                    float(row[field])
                    for row in sensitivity
                    if row["case"] == case
                    and int(row["snapshot_index"]) == age
                    and row[field] != ""
                ]
                lower.append(min(candidates))
                upper.append(max(candidates))
            axis.fill_between(ages, lower, upper, color=colours[case], alpha=0.14)
            axis.set_ylabel(ylabel)
        unresolved = [int(row["snapshot_index"]) for row in rows if row["status"] != "quantitative_bilateral"]
        for axis in axes:
            axis.scatter(unresolved, [0.0] * len(unresolved), marker="x", s=45, color=colours[case])
    for axis in axes:
        axis.axhline(0.0, color="#555555", linewidth=0.7)
        axis.set_xlabel("Source age (Myr)")
        axis.grid(alpha=0.22)
    axes[0].legend(frameon=False, ncol=2)
    axes[1].text(
        0.98,
        0.04,
        "Shading: 0.5–2× threshold range\n×: prespecified fail-closed row",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        fontsize=8.5,
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def build_product(
    *,
    shock_root: Path,
    goal066_native: Path,
    goal066_matched: Path,
    output_root: Path,
) -> dict[str, Any]:
    if output_root.exists():
        raise ProductError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True)
    combined, primary, sensitivity, controls = load_shock_surface(shock_root)
    summaries = case_summaries(primary, sensitivity)
    native_join, matched_join = join_goal066(
        primary=primary,
        native_path=goal066_native,
        matched_path=goal066_matched,
    )
    quantitative_count = sum(row["status"] == "quantitative_bilateral" for row in primary)
    unresolved = [
        f"{row['case']}/{row['snapshot_index']}:{row['status']}"
        for row in primary
        if row["status"] != "quantitative_bilateral"
    ]
    decision = [{
        "decision_label": DECISION_LABEL,
        "prespecified_case_age_count": len(primary),
        "quantitative_primary_count": quantitative_count,
        "unresolved_primary_count": len(primary) - quantitative_count,
        "unresolved_primary_rows": ";".join(unresolved),
        "threshold_factor_surface": "0.5/1.0/2.0; primary=1.0",
        "control_status": "cluster_and_group_environment_matched_noise_controls_zero_joint_exceedance",
        "scheduler_status": "789813_F_Exit1_postvalidation_schema_typo",
        "science_worker_status": "all_four_case_workers_exit_0",
        "recovery_status": "compact_outputs_validated_and_packaged_without_hdf5_rerun",
        "interpretation": "quantitative_where_bilateral; late_C-LO_censored_by_non_supersonic_front",
    }]
    outputs = {
        "native_shock_energy_selected_age.csv": combined,
        "primary_shock_partition.csv": primary,
        "threshold_sensitivity.csv": sensitivity,
        "case_summary.csv": summaries,
        "control_calibration_summary.csv": controls,
        "goal066_native_shock_context.csv": native_join,
        "goal066_matched_xray_shock_context.csv": matched_join,
        "scientific_decision_summary.csv": decision,
    }
    for name, rows in outputs.items():
        write_rows(output_root / name, rows)
    figure_name = "selected_age_native_shock_partition.png"
    make_figure(primary, sensitivity, output_root / figure_name)
    metadata = {
        "status": "complete_product_recovered_no_hdf5_rerun",
        "decision_label": DECISION_LABEL,
        "scheduler_job": "789813.kunanyi-ohpc",
        "scheduler_exit_status": 1,
        "scheduler_failure_stage": "post_analysis_schema_validation",
        "case_worker_exit_status": {case: 0 for case in CASES},
        "prespecified_row_count": len(combined),
        "primary_case_age_count": len(primary),
        "quantitative_primary_count": quantitative_count,
        "unresolved_primary_count": len(primary) - quantitative_count,
        "threshold_sensitivity_row_count": len(sensitivity),
        "goal066_native_join_count": len(native_join),
        "goal066_matched_join_count": len(matched_join),
        "control_role": "environment-matched dimensionless-noise calibration; not cellwise subtraction",
        "hdf5_recompute_performed": False,
        "figure": figure_name,
        "outputs": list(outputs),
    }
    metadata_path = output_root / "selected_age_native_shock_closeout_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    manifest = output_root / "local_asset_manifest.sha256"
    manifest.write_text(
        "\n".join(
            f"{sha256_file(path)}  {path.name}"
            for path in sorted(output_root.iterdir())
            if path.is_file() and path != manifest
        )
        + "\n"
    )
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shock-root", required=True, type=Path)
    parser.add_argument("--goal066-native", required=True, type=Path)
    parser.add_argument("--goal066-matched", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = build_product(
        shock_root=args.shock_root,
        goal066_native=args.goal066_native,
        goal066_matched=args.goal066_matched,
        output_root=args.output_root,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
