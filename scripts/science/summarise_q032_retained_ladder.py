#!/usr/bin/env python3
"""Summarise the retained 60-view Q-032 method ladder (PBS 870640).

All-sides statistics count an undetected side as zero recovered volume.
Ratios compare the recovered mask's revolution volume with the projected
tracer mask's revolution volume (tr1 LOS max > 1e-3), not native 3D truth.
G-HI at 50 Myr is excluded from scientific summaries, as its packaging
receipt requires. Factorial contrasts sum both sides per case/age/view and
use ages 20-40 Myr, where all four cases are eligible.

With ``--native-root`` (the Q-029 ``remote_analysis`` directory), recovered
volumes are also compared with the native 3D binary tr1 > 1e-3 lobe volume
of the same case, age and hemisphere.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import statistics

EXCLUDED = {("G-HI", "50")}
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
CONTRASTS = {
    "cluster_power": ("C-HI", "C-LO"),
    "group_power": ("G-HI", "G-LO"),
    "high_power_environment": ("C-HI", "G-HI"),
    "low_power_environment": ("C-LO", "G-LO"),
}
CONTRAST_AGES = ("20", "30", "40")


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [row for row in csv.DictReader(handle) if (row["case"], row["snapshot_index"]) not in EXCLUDED]


def detected(row: dict[str, str]) -> bool:
    return row["detected"] == "True"


def ratio(row: dict[str, str]) -> float:
    return float(row["volume_revolution_kpc3"]) / float(row["tracer_revolution_volume_kpc3"]) if detected(row) else 0.0


def completeness(row: dict[str, str]) -> float:
    return float(row["tracer_completeness"]) if detected(row) else 0.0


def quartiles(values: list[float]) -> tuple[float, float, float]:
    q1, q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, q2, q3


def group_rows(rows, run, **match):
    return [r for r in rows if r["run"] == run and all(r[k] == v for k, v in match.items())]


def summary(rows, run, scope, subset):
    hits = [r for r in subset if detected(r)]
    q1, q2, q3 = quartiles([ratio(r) for r in subset])
    return {
        "run": run,
        "scope": scope,
        "sides": len(subset),
        "sides_detected": len(hits),
        "zero_overlap_detections": sum(float(r["tracer_completeness"]) == 0.0 for r in hits),
        "ratio_q25_all_sides": q1,
        "ratio_median_all_sides": q2,
        "ratio_q75_all_sides": q3,
        "completeness_median_all_sides": statistics.median(completeness(r) for r in subset),
        "purity_median_detected": statistics.median(float(r["tracer_purity"]) for r in hits) if hits else math.nan,
        "views_connected_cross_midplane": sum(
            r["topology_class"] == "connected_cross_midplane_component" for r in subset if r["side"] == "positive_z"
        ),
    }


def contrasts(rows, run):
    recovered: dict[tuple, float] = {}
    tracer: dict[tuple, float] = {}
    for r in group_rows(rows, run):
        key = (r["case"], r["snapshot_index"], r["view"])
        recovered[key] = recovered.get(key, 0.0) + (float(r["volume_revolution_kpc3"]) if detected(r) else 0.0)
        tracer[key] = tracer.get(key, 0.0) + float(r["tracer_revolution_volume_kpc3"])
    out = []
    for name, (a, b) in CONTRASTS.items():
        rec, ref = [], []
        for age in CONTRAST_AGES:
            for view in ("0deg", "45deg", "90deg"):
                ka, kb = (a, age, view), (b, age, view)
                ref.append(math.log10(tracer[ka] / tracer[kb]))
                if recovered[ka] > 0 and recovered[kb] > 0:
                    rec.append(math.log10(recovered[ka] / recovered[kb]))
        out.append({
            "run": run,
            "contrast": name,
            "numerator": a,
            "denominator": b,
            "pairs": len(ref),
            "pairs_both_detected": len(rec),
            "tracer_log10_median": statistics.median(ref),
            "recovered_log10_median": statistics.median(rec) if rec else math.nan,
        })
    return out


def native_volumes(root: Path) -> dict[tuple[str, str, str], float]:
    volumes = {}
    for path in sorted(root.glob("*/native_energy_selected_age.csv")):
        with path.open(newline="") as handle:
            for r in csv.DictReader(handle):
                if r["partition_method"] == "binary_threshold_1e-3" and r["side"] != "bipolar_total":
                    volumes[(r["case"], r["snapshot_index"], r["side"])] = float(r["lobe_volume_kpc3"])
    return volumes


def native_reference(rows, runs, volumes):
    out = []
    for run in runs:
        for case in CASES:
            subset = group_rows(rows, run, case=case)
            native = [volumes[(r["case"], r["snapshot_index"], r["side"])] for r in subset]
            recovered = [float(r["volume_revolution_kpc3"]) if detected(r) else 0.0 for r in subset]
            out.append({
                "run": run,
                "case": case,
                "sides": len(subset),
                "recovered_over_native_median_all_sides": statistics.median(a / b for a, b in zip(recovered, native)),
                "tracer_projection_over_native_median": statistics.median(
                    float(r["tracer_revolution_volume_kpc3"]) / b for r, b in zip(subset, native)
                ),
            })
    return out


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rows", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--native-root", type=Path)
    args = parser.parse_args()
    rows = load(args.rows)
    runs = sorted({r["run"] for r in rows})
    summaries = []
    for run in runs:
        summaries.append(summary(rows, run, "all", group_rows(rows, run)))
        for case in CASES:
            summaries.append(summary(rows, run, case, group_rows(rows, run, case=case)))
        for age in ("10", "20", "30", "40", "50"):
            summaries.append(summary(rows, run, f"age_{age}", group_rows(rows, run, snapshot_index=age)))
        for view in ("0deg", "45deg", "90deg"):
            summaries.append(summary(rows, run, f"view_{view}", group_rows(rows, run, view=view)))
    aperture = []
    for case in CASES:
        for age in ("10", "20", "30", "40", "50"):
            subset = group_rows(rows, "legacy_area_1pct", case=case, snapshot_index=age)
            if subset:
                aperture.append({
                    "case": case,
                    "age_myr": age,
                    "tracer_area_inside_aperture_fraction_median": statistics.median(
                        float(r["tracer_area_inside_aperture_fraction"]) for r in subset
                    ),
                })
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "summary.csv", summaries)
    write(args.output / "factorial_contrasts.csv", [c for run in runs for c in contrasts(rows, run)])
    write(args.output / "tracer_aperture_coverage.csv", aperture)
    if args.native_root:
        write(args.output / "native_reference.csv", native_reference(rows, runs, native_volumes(args.native_root)))


if __name__ == "__main__":
    main()
