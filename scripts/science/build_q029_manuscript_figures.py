#!/usr/bin/env python3
"""Build the active first Q030 manuscript figures from accepted Q029 products.

The script only consumes compact, accepted CSV products. It keeps unresolved
shock rows as gaps and excludes censored age estimates from quantitative
medians. Censored age and power limits are shown separately in the age/power
figure as open triangles labelled as medians of bounds.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets/q029_binary_native_refresh_2026-09-06"
FIGURE_DIR = ROOT / "manuscript/figures"
SUMMARY_PATH = ASSET_ROOT / "manuscript_summary.json"
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
AGE_METHODS = (
    "true_source_age",
    "sound_crossing_age",
    "buoyant_rise_age",
    "refill_age",
    "shock_kinematic_age",
    "spectral_age_mean_pressure",
    "spectral_age_emissivity_weighted",
)
METHOD_LABELS = {
    "true_source_age": "True",
    "sound_crossing_age": "Sound",
    "buoyant_rise_age": "Buoyant",
    "refill_age": "Refill",
    "shock_kinematic_age": "Shock",
    "spectral_age_mean_pressure": "Spectral\n(mean p)",
    "spectral_age_emissivity_weighted": "Spectral\n(emiss.)",
}
CASE_COLORS = {
    "C-HI": "#0072B2",
    "C-LO": "#D55E00",
    "G-HI": "#009E73",
    "G-LO": "#CC79A7",
}
NATIVE_METHOD = "binary_threshold_1e-3"
NATIVE_METHOD_FULL = (
    "binary_tr1_gt_1e-3_full_cell_initial_state_subtraction_proven_ge_equivalent"
)
EXPECTED_CASE_AGES = {
    case: tuple(age for age in AGES if not (case == "G-HI" and age == 50))
    for case in CASES
}


class FigureBuildError(RuntimeError):
    """Raised when an accepted compact input violates the figure contract."""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise FigureBuildError(f"empty input table: {path}")
    return rows


def number(row: dict[str, str], key: str, *, allow_blank: bool = False) -> float | None:
    value = row.get(key, "")
    if value in ("", None):
        if allow_blank:
            return None
        raise FigureBuildError(f"missing numeric value {key}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise FigureBuildError(f"non-numeric value in {key}: {value!r}") from exc
    if not math.isfinite(result):
        raise FigureBuildError(f"non-finite value in {key}")
    return result


def bool_value(value: str) -> bool:
    return str(value).strip().lower() == "true"


def nominal_age(value: float) -> int:
    age = int(round(value))
    if abs(value - age) > 0.02:
        raise FigureBuildError(f"actual age is not close to an accepted age: {value}")
    return age


def selected_native_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in CASES:
        path = ASSET_ROOT / "remote_analysis" / case / "native_energy_selected_age.csv"
        source = read_csv(path)
        selected = [
            row
            for row in source
            if row["side"] == "bipolar_total" and row["partition_method"] == NATIVE_METHOD
        ]
        expected = EXPECTED_CASE_AGES[case]
        if len(selected) != len(expected):
            raise FigureBuildError(f"{case}: expected {len(expected)} strict bipolar rows, got {len(selected)}")
        ages = tuple(sorted(nominal_age(number(row, "actual_time_myr")) for row in selected))
        if ages != expected:
            raise FigureBuildError(f"{case}: native ages {ages} do not match {expected}")
        for row in selected:
            for key in (
                "actual_time_myr",
                "lobe_enthalpy_2p5pv_erg",
                "lobe_enthalpy_4pv_erg",
                "lobe_region_total_delta_erg",
                "injected_energy_erg",
            ):
                number(row, key)
            rows.append(row)
    return sorted(rows, key=lambda row: (CASES.index(row["case"]), number(row, "actual_time_myr") or 0.0))


def shock_rows() -> list[dict[str, str]]:
    path = ASSET_ROOT / "shock_closeout/primary_shock_partition.csv"
    rows = read_csv(path)
    if len(rows) != sum(len(v) for v in EXPECTED_CASE_AGES.values()):
        raise FigureBuildError(f"shock table has {len(rows)} rows")
    seen: set[tuple[str, int]] = set()
    for row in rows:
        key = (row["case"], nominal_age(number(row, "actual_time_myr")))
        if key in seen or key[0] not in CASES or key[1] not in EXPECTED_CASE_AGES[key[0]]:
            raise FigureBuildError(f"unexpected or duplicate shock key: {key}")
        seen.add(key)
        if row["status"] == "quantitative_bilateral":
            number(row, "total_delta_erg")
            number(row, "shock_fraction_of_injected")
        elif row["status"] != "unresolved_bilateral_gate":
            raise FigureBuildError(f"unexpected shock status: {row['status']}")
    expected_keys = {(case, age) for case, ages in EXPECTED_CASE_AGES.items() for age in ages}
    if seen != expected_keys:
        raise FigureBuildError("shock rows do not cover the accepted case-age surface")
    return rows


def observer_rows() -> list[dict[str, str]]:
    path = ASSET_ROOT / "accepted_refresh/primary_join/matched_native_xray_energetics.csv"
    source = read_csv(path)
    rows = [
        row
        for row in source
        if bool_value(row["quantitative_cavity_valid"])
        and row["volume_depth_assumption"] == "geometric_depth"
        and row["pressure_method"] == "ellipsoid_volume_average"
        and row["energy_model"] == "2.5pV"
    ]
    if len(rows) != 37:
        raise FigureBuildError(f"primary observer selection has {len(rows)} rows, expected 37")
    for row in rows:
        if row["native_partition_method"] != NATIVE_METHOD_FULL:
            raise FigureBuildError("observer join uses an unexpected native partition method")
        for key in ("volume_recovery", "pressure_recovery", "ratio_to_native_lobe_enthalpy"):
            value = number(row, key)
            if value is None or value <= 0.0:
                raise FigureBuildError(f"observer recovery {key} must be positive")
    return sorted(rows, key=lambda row: (CASES.index(row["case"]), number(row, "actual_time_myr") or 0.0, row["view"]))


def age_summary_rows() -> list[dict[str, str]]:
    path = ASSET_ROOT / "power_refresh/age_power_method_summary.csv"
    source = read_csv(path)
    rows = [row for row in source if row["cavity_energy_model"] == "2.5pV"]
    if len(rows) != len(CASES) * len(AGE_METHODS):
        raise FigureBuildError(f"2.5pV age summary has {len(rows)} rows")
    expected = {(case, method) for case in CASES for method in AGE_METHODS}
    seen = {(row["case"], row["age_method"]) for row in rows}
    if seen != expected:
        raise FigureBuildError("age summary does not cover all cases and seven methods")
    for row in rows:
        for key in (
            "available_age_rows",
            "exact_age_rows",
            "total_cavity_rows",
            "spectral_age_upper_limit_rows",
            "available_power_rows",
            "exact_power_rows",
            "power_lower_limit_rows",
        ):
            number(row, key)
    return rows


def age_power_rows() -> list[dict[str, str]]:
    """Load the row-level age/power table for explicit spectral-limit markers."""
    path = ASSET_ROOT / "power_refresh/cavity_power_method_comparison.csv"
    source = read_csv(path)
    rows = [row for row in source if row["cavity_energy_model"] == "2.5pV"]
    if len(rows) != 259:
        raise FigureBuildError(f"refreshed 2.5pV age/power table has {len(rows)} rows")
    expected = {(case, method) for case in CASES for method in AGE_METHODS}
    if {(row["case"], row["age_method"]) for row in rows} != expected:
        raise FigureBuildError("refreshed age/power table misses a case-method combination")
    for row in rows:
        if row["age_limit_direction"] == "upper_limit":
            age = number(row, "combined_age_myr")
            true_age = number(row, "actual_time_myr")
            if age is None or true_age is None or age <= 0.0 or true_age <= 0.0:
                raise FigureBuildError("invalid age upper-limit row")
        if row["power_limit_direction"] == "lower_limit":
            ratio = number(row, "inferred_to_known_power_ratio")
            if ratio is None or ratio <= 0.0:
                raise FigureBuildError("invalid power lower-limit row")
    return rows


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_native_energetics(native: list[dict[str, str]], shock: list[dict[str, str]], path: Path) -> None:
    shock_lookup = {
        (row["case"], nominal_age(number(row, "actual_time_myr"))): row for row in shock
    }
    metrics = (
        ("Native 2.5pV / injected energy", "lobe_enthalpy_2p5pv_erg", "#0072B2", "o"),
        ("Native 4pV / injected energy", "lobe_enthalpy_4pv_erg", "#D55E00", "s"),
        ("Lobe current-region ΔE / injected energy", "lobe_region_total_delta_erg", "#009E73", "^"),
        ("Selected shock ΔE / injected energy", "shock", "#CC79A7", "D"),
    )
    by_case = {case: [row for row in native if row["case"] == case] for case in CASES}
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), sharex=True, sharey=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        rows = by_case[case]
        ages = np.asarray([number(row, "actual_time_myr") for row in rows], dtype=float)
        injected = np.asarray([number(row, "injected_energy_erg") for row in rows], dtype=float)
        for label, key, color, marker in metrics:
            if key == "shock":
                values = []
                for row in rows:
                    srow = shock_lookup[(case, nominal_age(number(row, "actual_time_myr")))]
                    values.append(
                        np.nan
                        if srow["status"] != "quantitative_bilateral"
                        else number(srow, "total_delta_erg") / number(row, "injected_energy_erg")
                    )
            else:
                values = [number(row, key) / number(row, "injected_energy_erg") for row in rows]
            axis.plot(ages, values, color=color, marker=marker, linewidth=1.6, markersize=5, label=label)
        axis.axhline(1.0, color="0.25", linestyle="--", linewidth=1.0)
        axis.axhline(0.0, color="0.45", linewidth=0.7)
        axis.set_title(case)
        axis.set_xlim(7.5, 52.5)
        axis.set_ylim(-0.22, 2.0)
        axis.set_xticks(AGES)
        axis.grid(alpha=0.22)
    for axis in axes[-1, :]:
        axis.set_xlabel("Actual simulation age [Myr]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Normalised energy")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=9)
    fig.suptitle("Native lobe and selected-shock energetics", y=0.99)
    fig.tight_layout(rect=(0, 0.12, 1, 0.96))
    _save(fig, path)


def plot_observer_recovery(rows: list[dict[str, str]], path: Path) -> None:
    metrics = (
        ("volume_recovery", "Cavity volume / native lobe volume"),
        ("pressure_recovery", "Ambient pressure / native lobe pressure"),
        ("ratio_to_native_lobe_enthalpy", "X-ray 2.5pV / native 2.5pV"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.6), sharey=True)
    for axis, (key, ylabel) in zip(axes, metrics, strict=True):
        for index, case in enumerate(CASES):
            selected = [row for row in rows if row["case"] == case]
            values = np.asarray([number(row, key) for row in selected], dtype=float)
            offsets = np.linspace(-0.18, 0.18, len(values)) if len(values) > 1 else np.zeros(1)
            axis.scatter(
                np.full(len(values), index, dtype=float) + offsets,
                values,
                s=22,
                alpha=0.62,
                color=CASE_COLORS[case],
                edgecolors="white",
                linewidths=0.35,
                zorder=3,
            )
            median = float(np.median(values))
            axis.plot(
                [index - 0.24, index + 0.24],
                [median, median],
                color=CASE_COLORS[case],
                linewidth=2.5,
                zorder=4,
            )
            axis.text(index, median * 1.18, f"{median:.3g}", ha="center", va="bottom", fontsize=7.5, color=CASE_COLORS[case])
        axis.axhspan(0.5, 2.0, color="#999999", alpha=0.13, zorder=0)
        axis.axhline(1.0, color="0.25", linestyle="--", linewidth=1.0, zorder=1)
        axis.axhline(0.5, color="0.45", linestyle=":", linewidth=0.8)
        axis.axhline(2.0, color="0.45", linestyle=":", linewidth=0.8)
        axis.set_yscale("log")
        axis.set_ylim(1.5e-3, 25)
        axis.set_xlim(-0.55, len(CASES) - 0.45)
        axis.set_xticks(range(len(CASES)), CASES)
        axis.set_title(ylabel, fontsize=10)
        axis.grid(alpha=0.2, axis="y")
    axes[0].set_ylabel("Observer / native recovery")
    fig.text(0.5, 0.02, "Individual points are accepted age-view products; coloured bars are case medians (n = 37 total)", ha="center", fontsize=9)
    fig.suptitle("Observer-like X-ray recovery at the true simulation age", y=1.02)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    _save(fig, path)


def plot_age_power(summary: list[dict[str, str]], age_power: list[dict[str, str]], path: Path) -> None:
    by_key = {(row["case"], row["age_method"]): row for row in summary}
    limit_rows: dict[tuple[str, str], list[float]] = defaultdict(list)
    power_limit_rows: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in age_power:
        if row["age_limit_direction"] == "upper_limit":
            limit_rows[(row["case"], row["age_method"])].append(
                number(row, "combined_age_myr") / number(row, "actual_time_myr")
            )
        if row["power_limit_direction"] == "lower_limit":
            power_limit_rows[(row["case"], row["age_method"])].append(
                number(row, "inferred_to_known_power_ratio")
            )
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0), sharex=True)
    for axis, median_key, limit_key, ylabel in (
        (axes[0], "median_exact_age_to_true_ratio", "age", "Arithmetic-mean side age / true age"),
        (axes[1], "median_exact_inferred_to_known_power_ratio", "power", "Inferred / known bipolar jet power"),
    ):
        for index, method in enumerate(AGE_METHODS):
            for case in CASES:
                row = by_key[(case, method)]
                if median_key == "median_exact_age_to_true_ratio":
                    value = number(row, median_key, allow_blank=True)
                    count = int(number(row, "exact_age_rows") or 0)
                    censored = int(number(row, "spectral_age_upper_limit_rows") or 0)
                    marker = "v"
                else:
                    value = number(row, median_key, allow_blank=True)
                    count = int(number(row, "exact_power_rows") or 0)
                    censored = int(number(row, "power_lower_limit_rows") or 0)
                    marker = "^"
                if value is not None and count:
                    axis.scatter(index, value, color=CASE_COLORS[case], s=64, edgecolors="black", linewidths=0.45, zorder=4)
                if censored:
                    if limit_key == "age":
                        limits = limit_rows.get((case, method), [])
                        limit_value = float(np.median(limits)) if limits else None
                    else:
                        limits = power_limit_rows.get((case, method), [])
                        limit_value = float(np.median(limits)) if limits else None
                    if limit_value is not None:
                        axis.scatter(index, limit_value, marker=marker, facecolors="white", edgecolors=CASE_COLORS[case], linewidths=1.2, s=58, zorder=5)
        axis.axhline(1.0, color="0.25", linestyle="--", linewidth=1.0)
        axis.set_yscale("log")
        axis.set_xlim(-0.55, len(AGE_METHODS) - 0.45)
        axis.set_xticks(range(len(AGE_METHODS)), [METHOD_LABELS[m] for m in AGE_METHODS], rotation=28, ha="right")
        axis.grid(alpha=0.2, axis="y")
        axis.set_ylabel(ylabel)
    axes[0].set_ylim(0.1, 10)
    axes[1].set_ylim(1e-4, 3)
    axes[0].set_title("Clock bias")
    axes[1].set_title("Power recovery")
    handles = [plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=CASE_COLORS[c], markeredgecolor="black", markersize=7, label=c) for c in CASES]
    handles.append(plt.Line2D([0], [0], marker="v", color="none", markerfacecolor="white", markeredgecolor="0.25", markersize=7, label="Age upper limit (median bound)"))
    handles.append(plt.Line2D([0], [0], marker="^", color="none", markerfacecolor="white", markeredgecolor="0.25", markersize=7, label="Power lower limit (median bound)"))
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.suptitle("Seven age methods: case medians from quantitative rows", y=1.02)
    fig.tight_layout(rect=(0, 0.16, 1, 0.95))
    _save(fig, path)


def summary_json(native: list[dict[str, str]], shock: list[dict[str, str]], observer: list[dict[str, str]], age_summary: list[dict[str, str]], age_power: list[dict[str, str]]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "status": "q029_first_q030_manuscript_figure_iteration",
        "native_partition": NATIVE_METHOD_FULL,
        "native_rows": len(native),
        "shock_rows": len(shock),
        "observer_rows": len(observer),
        "observer_selection": {
            "volume_depth_assumption": "geometric_depth",
            "pressure_method": "ellipsoid_volume_average",
            "energy_model": "2.5pV",
            "quantitative_rows": 37,
            "topology_censored_rows": 20,
        },
        "age_method_counts_note": "Finite and censored counts and medians are from the accepted Q029 power refresh; censored limits are retained separately and are not included in exact medians.",
        "power_refresh_convention": "Age summary uses arithmetic mean of side ages divided by true age; power uses sum(H_side/t_side) and therefore its effective age can differ from the plotted age summary.",
        "cases": {},
        "age_methods_2p5pv": {},
    }
    for case in CASES:
        nrows = [row for row in native if row["case"] == case]
        srows = [row for row in shock if row["case"] == case]
        orows = [row for row in observer if row["case"] == case]
        def range_ratio(key: str) -> dict[str, float]:
            vals = [number(row, key) / number(row, "injected_energy_erg") for row in nrows]
            return {"min": float(min(vals)), "max": float(max(vals))}
        case_out: dict[str, Any] = {
            "accepted_ages_myr": list(EXPECTED_CASE_AGES[case]),
            "native_h_over_einj": {
                "2.5pV": range_ratio("lobe_enthalpy_2p5pv_erg"),
                "4pV": range_ratio("lobe_enthalpy_4pv_erg"),
            },
            "native_lobe_current_region_delta_over_einj": range_ratio("lobe_region_total_delta_erg"),
            "shock_selected_total_over_einj": {
                "quantitative_ages_myr": [nominal_age(number(row, "actual_time_myr")) for row in srows if row["status"] == "quantitative_bilateral"],
                "quantitative_range": {
                    "min": float(min(number(row, "shock_fraction_of_injected") for row in srows if row["status"] == "quantitative_bilateral")),
                    "max": float(max(number(row, "shock_fraction_of_injected") for row in srows if row["status"] == "quantitative_bilateral")),
                } if any(row["status"] == "quantitative_bilateral" for row in srows) else None,
                "unresolved_ages_myr": [nominal_age(number(row, "actual_time_myr")) for row in srows if row["status"] != "quantitative_bilateral"],
            },
            "observer_recovery": {},
        }
        for key, name in (("volume_recovery", "volume"), ("pressure_recovery", "pressure"), ("ratio_to_native_lobe_enthalpy", "2.5pV")):
            values = [number(row, key) for row in orows]
            case_out["observer_recovery"][name] = {
                "median": float(np.median(values)),
                "factor_two_count": int(sum(0.5 <= value <= 2.0 for value in values)),
                "finite_count": len(values),
            }
        output["cases"][case] = case_out
    limit_values: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: {"age": [], "power": []})
    for row in age_power:
        key = (row["case"], row["age_method"])
        if row["age_limit_direction"] == "upper_limit":
            limit_values[key]["age"].append(number(row, "combined_age_myr") / number(row, "actual_time_myr"))
        if row["power_limit_direction"] == "lower_limit":
            limit_values[key]["power"].append(number(row, "inferred_to_known_power_ratio"))
    for row in age_summary:
        case = row["case"]
        method = row["age_method"]
        output["age_methods_2p5pv"].setdefault(method, {})[case] = {
            "age_finite_count": int(number(row, "exact_age_rows") or 0),
            "age_censored_upper_limit_count": int(number(row, "spectral_age_upper_limit_rows") or 0),
            "age_median_t_est_over_t_true": number(row, "median_exact_age_to_true_ratio", allow_blank=True),
            "power_finite_count": int(number(row, "exact_power_rows") or 0),
            "power_censored_lower_limit_count": int(number(row, "power_lower_limit_rows") or 0),
            "power_median_q_est_over_q_true": number(row, "median_exact_inferred_to_known_power_ratio", allow_blank=True),
            "age_censored_bound_median_t_est_over_t_true": float(np.median(limit_values[(case, method)]["age"])) if limit_values[(case, method)]["age"] else None,
            "power_censored_bound_median_q_est_over_q_true": float(np.median(limit_values[(case, method)]["power"])) if limit_values[(case, method)]["power"] else None,
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="overwrite generated figure and summary outputs")
    args = parser.parse_args()
    paths = [
        FIGURE_DIR / "q029_native_energetics.png",
        FIGURE_DIR / "q029_observer_recovery.png",
        FIGURE_DIR / "q029_age_power.png",
        SUMMARY_PATH,
    ]
    if not args.force:
        existing = [path for path in paths if path.exists()]
        if existing:
            raise FigureBuildError("outputs already exist; use --force to regenerate: " + ", ".join(map(str, existing)))
    native = selected_native_rows()
    shock = shock_rows()
    observer = observer_rows()
    age_summary = age_summary_rows()
    age_power = age_power_rows()
    plot_native_energetics(native, shock, paths[0])
    plot_observer_recovery(observer, paths[1])
    plot_age_power(age_summary, age_power, paths[2])
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary_json(native, shock, observer, age_summary, age_power), indent=2, sort_keys=True) + "\n")
    print(json.dumps({"figures": [str(path) for path in paths[:3]], "summary": str(SUMMARY_PATH)}, indent=2))


if __name__ == "__main__":
    main()
