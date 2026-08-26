#!/usr/bin/env python3
"""Build the compact Goal 063 background and shock-validity synthesis."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib.pyplot as plt


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
CLUSTER_CASES = ("C-HI", "C-LO")
EARLY_CONTROL_MAX_MYR = 20.0
DOMAIN_EDGE_KPC = 250.0
MINIMUM_MARGIN_HALF_WIDTHS = 4.0
ENERGY_TERMS = (
    "outer_thermal_delta_erg",
    "outer_kinetic_delta_erg",
    "outer_gravitational_delta_erg",
    "outer_total_delta_erg",
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def number(row: Mapping[str, str], field: str) -> float:
    value = row[field]
    if value == "":
        return math.nan
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite {field}: {value}")
    return parsed


def paired_background_rows(background_root: Path) -> list[dict[str, Any]]:
    tables = {
        case: {int(row["snapshot_index"]): row for row in read_rows(background_root / case / "background_summary.csv")}
        for case in CLUSTER_CASES
    }
    if set(tables["C-HI"]) != set(tables["C-LO"]):
        raise ValueError("cluster anchor-age grids differ")
    output: list[dict[str, Any]] = []
    for index in sorted(tables["C-HI"]):
        high, low = tables["C-HI"][index], tables["C-LO"][index]
        for term in ENERGY_TERMS:
            high_value, low_value = number(high, term), number(low, term)
            ratio = low_value / high_value if high_value != 0.0 else math.nan
            output.append({
                "snapshot_index": index,
                "c_hi_time_myr": number(high, "actual_time_myr"),
                "c_lo_time_myr": number(low, "actual_time_myr"),
                "energy_term": term.removeprefix("outer_").removesuffix("_delta_erg"),
                "c_hi_outer_delta_erg": high_value,
                "c_lo_outer_delta_erg": low_value,
                "c_lo_to_c_hi_ratio": ratio,
                "absolute_fractional_difference": (
                    abs(low_value - high_value) / max(abs(low_value), abs(high_value))
                    if max(abs(low_value), abs(high_value)) > 0.0 else ""
                ),
                "early_far_field_control": index > 0 and number(high, "actual_time_myr") <= EARLY_CONTROL_MAX_MYR,
            })
    return output


def c_lo_accounting_rows(background_root: Path) -> list[dict[str, Any]]:
    output = []
    for row in read_rows(background_root / "C-LO" / "background_summary.csv"):
        injected = number(row, "injected_energy_erg")
        global_total = number(row, "global_total_delta_erg")
        outer_total = number(row, "outer_total_delta_erg")
        output.append({
            "snapshot_index": int(row["snapshot_index"]),
            "actual_time_myr": number(row, "actual_time_myr"),
            "global_accounted_delta_erg": global_total,
            "far_field_delta_erg": outer_total,
            "inside_100_kpc_remainder_erg": global_total - outer_total,
            "global_fraction_of_injected": global_total / injected if injected > 0.0 else "",
            "far_field_fraction_of_injected": outer_total / injected if injected > 0.0 else "",
            "inside_100_kpc_fraction_of_injected": (global_total - outer_total) / injected if injected > 0.0 else "",
            "far_field_fraction_of_global": outer_total / global_total if global_total != 0.0 else "",
            "far_field_tracer_volume_fraction": number(row, "outer_tracer_volume_fraction"),
            "interpretation": "upper_bound_on_jet_affected_energy_not_background_corrected",
        })
    return output


def finite_jump(row: Mapping[str, str]) -> bool:
    return all(row[field] != "" and math.isfinite(float(row[field])) for field in ("pressure_jump_ratio", "density_jump_ratio"))


def side_geometry_valid(row: Mapping[str, str]) -> bool:
    if row["status"] != "detected" or not finite_jump(row):
        return False
    distance = number(row, "shock_distance_kpc")
    uncertainty = number(row, "position_uncertainty_kpc")
    return DOMAIN_EDGE_KPC - distance >= MINIMUM_MARGIN_HALF_WIDTHS * uncertainty


def _fit_indices(valid_indices: Sequence[int], local_index: int) -> list[int]:
    if len(valid_indices) < 3:
        return []
    start = max(0, min(local_index - 1, len(valid_indices) - 3))
    return list(valid_indices[start:start + 3])


def shock_validity_rows(shock_path: Path) -> list[dict[str, Any]]:
    rows = read_rows(shock_path)
    output: list[dict[str, Any]] = []
    for case in CASES:
        case_rows = [row for row in rows if row["case"] == case]
        by_side = {
            side: {int(row["snapshot_index"]): row for row in case_rows if row["side"] == side}
            for side in ("negative_z", "positive_z")
        }
        if any(set(table) != set(range(51)) for table in by_side.values()):
            raise ValueError(f"incomplete shock surface: {case}")
        side_valid = {
            side: {index: side_geometry_valid(row) for index, row in table.items()}
            for side, table in by_side.items()
        }
        detected_indices = {
            side: [index for index, row in table.items() if row["status"] == "detected"]
            for side, table in by_side.items()
        }
        for index in range(51):
            position_valid = all(side_valid[side][index] for side in by_side)
            fit_valid = True
            fit_members: list[str] = []
            for side in by_side:
                if index not in detected_indices[side]:
                    fit_valid = False
                    continue
                members = _fit_indices(detected_indices[side], detected_indices[side].index(index))
                fit_members.append(f"{side}:{'/'.join(map(str, members))}")
                fit_valid &= bool(members) and all(side_valid[side][member] for member in members)
            distances = [number(by_side[side][index], "shock_distance_kpc") for side in by_side if by_side[side][index]["shock_distance_kpc"]]
            margins = [DOMAIN_EDGE_KPC - value for value in distances]
            output.append({
                "case": case,
                "snapshot_index": index,
                "actual_time_myr": number(by_side["negative_z"][index], "actual_time_myr"),
                "both_side_position_and_jump_valid": position_valid,
                "three_snapshot_kinematics_valid": fit_valid,
                "minimum_domain_margin_kpc": min(margins) if margins else "",
                "fit_members": ";".join(fit_members),
            })
    return output


def shock_window_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for case in CASES:
        selected = [row for row in rows if row["case"] == case]
        position = [row for row in selected if row["both_side_position_and_jump_valid"]]
        kinematic = [row for row in selected if row["three_snapshot_kinematics_valid"]]
        output.append({
            "case": case,
            "last_position_valid_snapshot": max(int(row["snapshot_index"]) for row in position),
            "last_position_valid_time_myr": max(float(row["actual_time_myr"]) for row in position),
            "last_kinematics_valid_snapshot": max(int(row["snapshot_index"]) for row in kinematic),
            "last_kinematics_valid_time_myr": max(float(row["actual_time_myr"]) for row in kinematic),
        })
    return output


def make_figure(
    background_root: Path,
    paired: Sequence[Mapping[str, Any]],
    c_lo: Sequence[Mapping[str, Any]],
    shock_rows: Sequence[Mapping[str, Any]],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), constrained_layout=True)
    for case, color in (("C-HI", "#176b87"), ("C-LO", "#c44e52")):
        rows = read_rows(background_root / case / "background_summary.csv")
        x = [number(row, "actual_time_myr") for row in rows if number(row, "injected_energy_erg") > 0.0]
        y = [number(row, "outer_total_fraction_of_injected") for row in rows if number(row, "injected_energy_erg") > 0.0]
        axes[0, 0].plot(x, y, marker="o", label=case, color=color)
    axes[0, 0].set(title="Far-field energy / injected energy", xlabel="Age (Myr)", ylabel="Ratio", yscale="log")
    axes[0, 0].legend(frameon=False)

    total = [row for row in paired if row["energy_term"] == "total" and int(row["snapshot_index"]) > 0]
    axes[0, 1].plot([row["c_hi_time_myr"] for row in total], [row["c_hi_outer_delta_erg"] for row in total], marker="o", label="C-HI")
    axes[0, 1].plot([row["c_lo_time_myr"] for row in total], [row["c_lo_outer_delta_erg"] for row in total], marker="s", label="C-LO")
    axes[0, 1].axvspan(0, EARLY_CONTROL_MAX_MYR, color="#dddddd", alpha=0.5, label="clean early control")
    axes[0, 1].set(title="Absolute far-field total change", xlabel="Age (Myr)", ylabel="Energy (erg)")
    axes[0, 1].legend(frameon=False)

    selected_c_lo = [row for row in c_lo if row["global_fraction_of_injected"] != ""]
    x = [row["actual_time_myr"] for row in selected_c_lo]
    axes[1, 0].plot(x, [row["global_fraction_of_injected"] for row in selected_c_lo], marker="o", label="whole domain")
    axes[1, 0].plot(x, [row["far_field_fraction_of_injected"] for row in selected_c_lo], marker="s", label="r >= 100 kpc")
    axes[1, 0].plot(x, [row["inside_100_kpc_fraction_of_injected"] for row in selected_c_lo], marker="^", label="inside 100 kpc")
    axes[1, 0].set(title="C-LO accounted-energy decomposition", xlabel="Age (Myr)", ylabel="Fraction of injected energy")
    axes[1, 0].legend(frameon=False)

    g_hi = [row for row in shock_rows if row["case"] == "G-HI" and int(row["snapshot_index"]) > 0]
    axes[1, 1].plot([row["actual_time_myr"] for row in g_hi], [row["minimum_domain_margin_kpc"] for row in g_hi], color="#75507b")
    axes[1, 1].axvline(45.99958358613507, color="#2e8b57", linestyle="--", label="last valid speed")
    axes[1, 1].axvline(46.99914999860678, color="#b22222", linestyle=":", label="last valid position")
    axes[1, 1].axhline(0.0, color="black", linewidth=0.8)
    axes[1, 1].set(title="G-HI shock margin to domain edge", xlabel="Age (Myr)", ylabel="Minimum margin (kpc)")
    axes[1, 1].legend(frameon=False)

    for axis in axes.flat:
        axis.grid(alpha=0.2)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def build(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    background_root = Path(args.background_root)
    paired = paired_background_rows(background_root)
    c_lo = c_lo_accounting_rows(background_root)
    shock_rows = shock_validity_rows(Path(args.shock_timeseries))
    shock_summary = shock_window_summary(shock_rows)

    early = [row for row in paired if row["early_far_field_control"]]
    max_early_difference = max(float(row["absolute_fractional_difference"]) for row in early)
    endpoint = next(row for row in c_lo if int(row["snapshot_index"]) == 50)
    g_hi = next(row for row in shock_summary if row["case"] == "G-HI")
    if int(g_hi["last_position_valid_snapshot"]) != 47 or int(g_hi["last_kinematics_valid_snapshot"]) != 46:
        raise ValueError(f"G-HI validity window drift: {g_hi}")

    write_rows(output / "paired_far_field_comparison.csv", paired)
    write_rows(output / "c_lo_background_accounting.csv", c_lo)
    write_rows(output / "shock_validity_by_snapshot.csv", shock_rows)
    write_rows(output / "shock_validity_window.csv", shock_summary)
    make_figure(background_root, paired, c_lo, shock_rows, output / "cluster_background_and_age_validity.png")

    decision = {
        "status": "complete_cluster_background_age_validity_synthesis",
        "decision_label": "C_LO_LARGE_NORMALIZED_BUDGET_BACKGROUND_DOMINATED_SHOCK_WINDOWS_LOCKED",
        "maximum_early_far_field_fractional_difference": max_early_difference,
        "c_lo_endpoint_global_fraction_of_injected": endpoint["global_fraction_of_injected"],
        "c_lo_endpoint_far_field_fraction_of_injected": endpoint["far_field_fraction_of_injected"],
        "c_lo_endpoint_inside_100_kpc_fraction_of_injected": endpoint["inside_100_kpc_fraction_of_injected"],
        "c_lo_endpoint_far_field_fraction_of_global": endpoint["far_field_fraction_of_global"],
        "g_hi_last_position_valid_snapshot": g_hi["last_position_valid_snapshot"],
        "g_hi_last_kinematics_valid_snapshot": g_hi["last_kinematics_valid_snapshot"],
        "scientific_limits": [
            "paired jet simulations are not an unforced no-jet control",
            "inside-100-kpc remainder is an upper bound, not a background-corrected jet efficiency",
            "technical shock-domain validity does not impose a new physical shock-strength threshold",
        ],
    }
    (output / "cluster_background_age_validity_metadata.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")
    return decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--background-root", type=Path, required=True)
    parser.add_argument("--shock-timeseries", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    result = build(build_parser().parse_args(argv))
    print(f"status={result['status']}")
    print(f"decision_label={result['decision_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
