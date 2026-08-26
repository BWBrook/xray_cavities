#!/usr/bin/env python3
"""Build the first descriptive synthesis of the matched four-case fluid census."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
DOMAIN_HALF_Z_KPC = 250.0
PRIMARY_SHOCK_THRESHOLD = 1.0


class SynthesisError(RuntimeError):
    """Raised when the retrieved census violates its locked contract."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SynthesisError(f"empty input table: {path}")
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise SynthesisError(f"refusing to write empty table: {path}")
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _float(row: Mapping[str, Any], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise SynthesisError(f"missing or invalid {field}") from exc
    if not math.isfinite(value):
        raise SynthesisError(f"non-finite {field}")
    return value


def _optional_float(row: Mapping[str, Any], field: str) -> float | None:
    raw = row.get(field, "")
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise SynthesisError(f"invalid optional {field}") from exc
    return value if math.isfinite(value) else None


def _csv_optional(value: float | None) -> float | str:
    return "" if value is None else value


def _fraction(value: float, injected: float) -> float | str:
    return value / injected if injected > 0.0 else ""


def load_surfaces(input_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load the locked primary energy and shock rows for all four cases."""
    energy_output: list[dict[str, Any]] = []
    shock_output: list[dict[str, Any]] = []
    for case in CASES:
        case_root = input_root / case
        energy_rows = _read_csv(case_root / "energy_partition_timeseries.csv")
        shock_rows = _read_csv(case_root / "shock_dynamics.csv")
        primary_energy = [
            row
            for row in energy_rows
            if row["partition_method"] == "fractional" and row["side"] == "bipolar_total"
        ]
        primary_shocks = [
            row
            for row in shock_rows
            if math.isclose(
                _float(row, "velocity_threshold_factor"),
                PRIMARY_SHOCK_THRESHOLD,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        ]
        if len(primary_energy) != 51 or len(primary_shocks) != 102:
            raise SynthesisError(f"{case} primary surface is incomplete")
        if [int(row["snapshot_index"]) for row in primary_energy] != list(range(51)):
            raise SynthesisError(f"{case} energy indices are not 0..50")

        for row in primary_energy:
            injected = _float(row, "injected_energy_erg")
            gas_total = _float(row, "gas_total_delta_erg")
            lobe_total = _float(row, "lobe_total_erg")
            residual = _float(row, "unattributed_residual_erg")
            energy_output.append(
                {
                    "case": case,
                    "snapshot_index": int(row["snapshot_index"]),
                    "actual_time_myr": _float(row, "actual_time_myr"),
                    "injected_energy_erg": injected,
                    "gas_thermal_delta_erg": _float(row, "gas_thermal_delta_erg"),
                    "gas_kinetic_delta_erg": _float(row, "gas_kinetic_delta_erg"),
                    "gas_gravitational_delta_erg": _float(row, "gas_gravitational_delta_erg"),
                    "gas_total_delta_erg": gas_total,
                    "lobe_thermal_erg": _float(row, "lobe_thermal_erg"),
                    "lobe_kinetic_erg": _float(row, "lobe_kinetic_erg"),
                    "lobe_gravitational_erg": _float(row, "lobe_gravitational_erg"),
                    "lobe_total_erg": lobe_total,
                    "lobe_volume_kpc3": _float(row, "lobe_volume_kpc3"),
                    "gas_thermal_fraction_of_injected": _fraction(_float(row, "gas_thermal_delta_erg"), injected),
                    "gas_kinetic_fraction_of_injected": _fraction(_float(row, "gas_kinetic_delta_erg"), injected),
                    "gas_gravitational_fraction_of_injected": _fraction(_float(row, "gas_gravitational_delta_erg"), injected),
                    "gas_total_fraction_of_injected": _fraction(gas_total, injected),
                    "lobe_total_fraction_of_injected": _fraction(lobe_total, injected),
                    "accounted_fraction_of_injected": _fraction(gas_total + lobe_total, injected),
                    "unattributed_residual_fraction_of_injected": _fraction(residual, injected),
                    "boundary_status": row["boundary_status"],
                    "residual_interpretation": row["residual_interpretation"],
                }
            )

        for row in primary_shocks:
            shock_output.append(
                {
                    "case": case,
                    "snapshot_index": int(row["snapshot_index"]),
                    "actual_time_myr": _float(row, "actual_time_myr"),
                    "side": row["side"],
                    "status": row["status"],
                    "shock_distance_kpc": _csv_optional(_optional_float(row, "shock_distance_kpc")),
                    "position_uncertainty_kpc": _csv_optional(_optional_float(row, "position_uncertainty_kpc")),
                    "shock_speed_km_s": _csv_optional(_optional_float(row, "shock_speed_km_s")),
                    "shock_speed_uncertainty_km_s": _csv_optional(_optional_float(row, "shock_speed_uncertainty_km_s")),
                    "ambient_sound_speed_km_s": _csv_optional(_optional_float(row, "ambient_sound_speed_km_s")),
                    "mach_kinematic": _csv_optional(_optional_float(row, "mach_kinematic")),
                    "pressure_jump_ratio": _csv_optional(_optional_float(row, "pressure_jump_ratio")),
                    "density_jump_ratio": _csv_optional(_optional_float(row, "density_jump_ratio")),
                }
            )
    return energy_output, shock_output


def endpoint_rows(
    energy_rows: Sequence[Mapping[str, Any]], shock_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for case in CASES:
        energy = next(
            row for row in energy_rows if row["case"] == case and row["snapshot_index"] == 50
        )
        shocks = [
            row for row in shock_rows if row["case"] == case and row["snapshot_index"] == 50
        ]
        by_side = {row["side"]: row for row in shocks}
        distances = [float(row["shock_distance_kpc"]) for row in shocks if row["shock_distance_kpc"] != ""]
        if len(distances) != 2:
            raise SynthesisError(f"{case} endpoint shock surface is incomplete")
        output.append(
            {
                "case": case,
                "actual_time_myr": energy["actual_time_myr"],
                "gas_thermal_fraction_of_injected": energy["gas_thermal_fraction_of_injected"],
                "gas_kinetic_fraction_of_injected": energy["gas_kinetic_fraction_of_injected"],
                "gas_gravitational_fraction_of_injected": energy["gas_gravitational_fraction_of_injected"],
                "gas_total_fraction_of_injected": energy["gas_total_fraction_of_injected"],
                "lobe_total_fraction_of_injected": energy["lobe_total_fraction_of_injected"],
                "accounted_fraction_of_injected": energy["accounted_fraction_of_injected"],
                "unattributed_residual_fraction_of_injected": energy["unattributed_residual_fraction_of_injected"],
                "negative_z_shock_distance_kpc": by_side["negative_z"]["shock_distance_kpc"],
                "positive_z_shock_distance_kpc": by_side["positive_z"]["shock_distance_kpc"],
                "minimum_domain_margin_kpc": DOMAIN_HALF_Z_KPC - max(distances),
                "negative_z_mach_kinematic": by_side["negative_z"]["mach_kinematic"],
                "positive_z_mach_kinematic": by_side["positive_z"]["mach_kinematic"],
                "absolute_residual_exceeds_injected": abs(float(energy["unattributed_residual_fraction_of_injected"])) > 1.0,
            }
        )
    return output


def contrast_rows(endpoints: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    lookup = {row["case"]: row for row in endpoints}
    comparisons = (
        ("power_effect_in_cluster", "C-HI", "C-LO"),
        ("power_effect_in_group", "G-HI", "G-LO"),
        ("environment_effect_at_high_power", "G-HI", "C-HI"),
        ("environment_effect_at_low_power", "G-LO", "C-LO"),
    )
    metrics = (
        "gas_thermal_fraction_of_injected",
        "gas_kinetic_fraction_of_injected",
        "gas_gravitational_fraction_of_injected",
        "gas_total_fraction_of_injected",
        "lobe_total_fraction_of_injected",
        "accounted_fraction_of_injected",
        "unattributed_residual_fraction_of_injected",
        "minimum_domain_margin_kpc",
    )
    output: list[dict[str, Any]] = []
    for comparison, numerator_case, denominator_case in comparisons:
        for metric in metrics:
            numerator = float(lookup[numerator_case][metric])
            denominator = float(lookup[denominator_case][metric])
            positive_ratio = numerator / denominator if numerator > 0.0 and denominator > 0.0 else ""
            output.append(
                {
                    "comparison": comparison,
                    "metric": metric,
                    "numerator_case": numerator_case,
                    "denominator_case": denominator_case,
                    "numerator_value": numerator,
                    "denominator_value": denominator,
                    "difference": numerator - denominator,
                    "positive_value_ratio": positive_ratio,
                    "interpretation_scope": "descriptive_2x2_contrast_no_replicate_inference",
                }
            )
    return output


def _plot(
    path: Path,
    energy_rows: Sequence[Mapping[str, Any]],
    shock_rows: Sequence[Mapping[str, Any]],
) -> None:
    colors = {"C": "#2463A7", "G": "#D97924"}
    styles = {"HI": "-", "LO": "--"}
    markers = {"C": "o", "G": "s"}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), constrained_layout=True)
    panels = (
        (axes[0, 0], "gas_total_fraction_of_injected", "Ambient total / injected", "log"),
        (axes[0, 1], "lobe_total_fraction_of_injected", "Direct tracer-lobe total / injected", "linear"),
        (axes[1, 0], "gas_gravitational_fraction_of_injected", "Ambient gravitational change / injected", "log"),
    )
    for axis, field, title, scale in panels:
        for case in CASES:
            environment, power = case.split("-")
            rows = [row for row in energy_rows if row["case"] == case and row[field] != ""]
            axis.plot(
                [row["actual_time_myr"] for row in rows],
                [row[field] for row in rows],
                color=colors[environment], linestyle=styles[power], linewidth=2,
                marker=markers[environment], markevery=10, markersize=4, label=case,
            )
        axis.set_title(title)
        axis.set_xlabel("Source age (Myr)")
        axis.set_ylabel("Fraction of cumulative bipolar injection")
        axis.set_yscale(scale)
        axis.grid(True, color="#D7DADF", linewidth=0.7, alpha=0.8)
        axis.axhline(1.0, color="#444444", linewidth=0.9, linestyle=":")

    axis = axes[1, 1]
    for case in CASES:
        environment, power = case.split("-")
        by_index: dict[int, list[float]] = {}
        for row in shock_rows:
            if row["case"] != case or row["shock_distance_kpc"] == "":
                continue
            by_index.setdefault(int(row["snapshot_index"]), []).append(float(row["shock_distance_kpc"]))
        indices = sorted(index for index, values in by_index.items() if len(values) == 2)
        times = [next(row["actual_time_myr"] for row in shock_rows if row["case"] == case and row["snapshot_index"] == index) for index in indices]
        means = [float(np.mean(by_index[index])) for index in indices]
        lows = [min(by_index[index]) for index in indices]
        highs = [max(by_index[index]) for index in indices]
        axis.fill_between(times, lows, highs, color=colors[environment], alpha=0.08)
        axis.plot(
            times, means, color=colors[environment], linestyle=styles[power], linewidth=2,
            marker=markers[environment], markevery=10, markersize=4, label=case,
        )
    axis.axhline(DOMAIN_HALF_Z_KPC, color="#444444", linewidth=1.0, linestyle=":", label="Domain edge")
    axis.set_title("Primary axial shock distance")
    axis.set_xlabel("Source age (Myr)")
    axis.set_ylabel("Mean two-sided distance (kpc)")
    axis.grid(True, color="#D7DADF", linewidth=0.7, alpha=0.8)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.025))
    fig.suptitle("Four-case fluid census", fontsize=15, color="#20242A", y=1.065)
    fig.text(
        0.5, 1.035,
        "Annual snapshots; fractional tracer partition; primary shock threshold. Lines are descriptive simulation trajectories.",
        ha="center", va="center", fontsize=9, color="#4A4F57",
    )
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build(input_root: Path, output_root: Path) -> dict[str, Any]:
    input_root = Path(input_root)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    targets = (
        output_root / "primary_fluid_timeseries.csv",
        output_root / "primary_shock_timeseries.csv",
        output_root / "endpoint_factorial_summary.csv",
        output_root / "endpoint_factorial_contrasts.csv",
        output_root / "four_case_fluid_census.png",
        output_root / "four_case_fluid_census_synthesis_metadata.json",
    )
    if any(path.exists() or path.is_symlink() for path in targets):
        raise SynthesisError("refusing to overwrite existing synthesis output")
    energy, shocks = load_surfaces(input_root)
    endpoints = endpoint_rows(energy, shocks)
    contrasts = contrast_rows(endpoints)
    _write_csv(targets[0], energy)
    _write_csv(targets[1], shocks)
    _write_csv(targets[2], endpoints)
    _write_csv(targets[3], contrasts)
    _plot(targets[4], energy, shocks)
    c_lo = next(row for row in endpoints if row["case"] == "C-LO")
    g_hi = next(row for row in endpoints if row["case"] == "G-HI")
    result = {
        "status": "complete_four_case_fluid_census_synthesis",
        "decision_label": "FOUR_CASE_FLUID_CENSUS_GREEN_C_LO_ENERGY_BASELINE_AND_G_HI_BOUNDARY_GATES_EXPOSED",
        "case_count": 4,
        "snapshot_count": len(energy),
        "primary_shock_row_count": len(shocks),
        "endpoint_row_count": len(endpoints),
        "contrast_row_count": len(contrasts),
        "observations": {
            "c_lo_endpoint_absolute_residual_fraction": abs(float(c_lo["unattributed_residual_fraction_of_injected"])),
            "g_hi_endpoint_minimum_domain_margin_kpc": float(g_hi["minimum_domain_margin_kpc"]),
        },
        "interpretation_limits": [
            "factorial contrasts are descriptive because there is one deterministic simulation per cell",
            "boundary energy flux is unmeasured and the closure residual is not cocoon energy",
            "C-LO absolute energy comparison needs a background-evolution diagnosis before scientific promotion",
            "late G-HI shock kinematics are limited by proximity to the axial domain edge",
        ],
    }
    targets[5].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.input_root, args.output_root)
    except (OSError, SynthesisError, ValueError) as exc:
        print(f"synthesis_error={exc}")
        return 2
    print(f"decision_label={result['decision_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
