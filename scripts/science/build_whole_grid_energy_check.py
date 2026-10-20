#!/usr/bin/env python3
"""Compare existing Q-029 whole-grid changes with injection, without shock cuts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
COMPONENTS = ("thermal", "kinetic", "gravitational")
PRIMARY = "binary_threshold_1e-3"
SECONDS_PER_MYR = 365.25 * 86400 * 1e6
TOLERANCE = 1e-9
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis"
DEFAULT_OUTPUT = ROOT / "docs/science/assets/whole_grid_energy_closure_2026-10-21"


def analyse(source_root: Path) -> tuple[list[dict], dict]:
    results, checks, sources = [], {}, {}

    def check(name: str, difference: float, scale: float) -> None:
        error = abs(difference) / scale
        if not math.isfinite(error) or error > TOLERANCE:
            raise ValueError(f"{name}: normalized difference {error}")
        checks[name] = max(checks.get(name, 0.0), error)

    for case in CASES:
        path = source_root / case / "native_energy_selected_age.csv"
        sources[case] = {"path": str(path.relative_to(ROOT)),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        primary = sorted((r for r in rows if r["side"] == "bipolar_total"
                          and r["partition_method"] == PRIMARY),
                         key=lambda r: float(r["actual_time_myr"]))
        expected = [10, 20, 30, 40] if case == "G-HI" else [10, 20, 30, 40, 50]
        if [int(r["snapshot_index"]) for r in primary] != expected:
            raise ValueError(f"Unexpected snapshot coverage for {case}")
        for row in primary:
            n = int(row["snapshot_index"])
            time = float(row["actual_time_myr"])
            injected = float(row["injected_energy_erg"])
            if not (injected > 0 and abs(time - n) < 0.01):
                raise ValueError(f"Invalid age or injection: {case}/{n}")
            power = 2e45 if case.endswith("HI") else 2e43
            check("injection_vs_bipolar_power_time", injected - power * min(time, 50) * SECONDS_PER_MYR, injected)
            if float(row["current_cell_equivalent"]) != 960 * 960 * 1014:
                raise ValueError(f"Unexpected physical cell count: {case}/{n}")
            result = dict(case=case, snapshot_index=n, actual_time_myr=time,
                          bipolar_power_erg_s=power, injected_energy_erg=injected)
            for component in COMPONENTS:
                initial = float(row[f"initial_{component}_erg"])
                current = float(row[f"current_{component}_erg"])
                delta = float(row[f"retained_{component}_delta_erg"])
                lobe = float(row[f"lobe_region_{component}_delta_erg"])
                ambient = float(row[f"ambient_region_{component}_delta_erg"])
                check("absolute_sums_vs_cellwise_change", current - initial - delta, injected)
                check("region_partition_vs_cellwise_change", lobe + ambient - delta, injected)
                check("initial_state_constancy", initial - float(primary[0][f"initial_{component}_erg"]), max(abs(initial), injected))
                result.update({f"initial_{component}_erg": initial,
                               f"current_{component}_erg": current,
                               f"delta_{component}_erg": delta,
                               f"delta_{component}_over_injected": delta / injected,
                               f"cocoon_region_delta_{component}_erg": lobe,
                               f"ambient_region_delta_{component}_erg": ambient})
            total = math.fsum(result[f"delta_{c}_erg"] for c in COMPONENTS)
            check("components_vs_recorded_total", total - float(row["retained_energy_erg"]), injected)
            check("reported_closure_residual", injected - total - float(row["unattributed_residual_erg"]), injected)
            for other in rows:
                if int(other["snapshot_index"]) == n and other["side"] == "bipolar_total":
                    check("whole_grid_independent_of_tracer_partition", float(other["retained_energy_erg"]) - total, injected)
            for component in COMPONENTS:
                field = f"retained_{component}_delta_erg"
                halves = [float(r[field]) for r in rows if int(r["snapshot_index"]) == n
                          and r["partition_method"] == PRIMARY and r["side"] in ("negative_z", "positive_z")]
                if len(halves) != 2:
                    raise ValueError(f"Missing hemisphere for {case}/{n}")
                check("hemispheres_vs_whole_grid", math.fsum(halves) - result[f"delta_{component}_erg"], injected)
            result.update(delta_total_erg=total, delta_total_over_injected=total / injected,
                          injection_minus_delta_erg=injected - total,
                          injection_minus_delta_over_injected=(injected - total) / injected)
            results.append(result)
    summary = {"status": "compact_table_comparison_complete_physical_closure_unresolved",
               "source_commit": "c730e4e", "sources": sources, "snapshot_count": len(results),
               "checks_max_normalized_difference": checks,
               "numerical_check_tolerance": TOLERANCE,
               "scope": "19 existing selected ages; no HDF5 reread, no shock or cavity selection",
               "cases": {}}
    for case in CASES:
        selected = [r for r in results if r["case"] == case]
        ratios = [r["delta_total_over_injected"] for r in selected]
        summary["cases"][case] = dict(ratio_min=min(ratios), ratio_max=max(ratios),
                                       points=[dict(snapshot_index=r["snapshot_index"],
                                                    ratio=r["delta_total_over_injected"]) for r in selected])
    return results, summary


def plot(rows: list[dict], output: Path, normalized: bool) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11})
    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.2), sharex=True)
    colours = {"thermal": "#be4b35", "kinetic": "#0072b2", "gravitational": "#16835c"}
    for ax, case in zip(axes.flat, CASES):
        selected = [r for r in rows if r["case"] == case]
        times = [r["actual_time_myr"] for r in selected]
        denominator = [r["injected_energy_erg"] if normalized else 1 for r in selected]
        total = [r["delta_total_erg"] / d for r, d in zip(selected, denominator)]
        ax.plot(times, total, "o-", color="#222222", lw=2.2, label="Total grid change")
        for component in COMPONENTS:
            ax.plot(times, [r[f"delta_{component}_erg"] / d for r, d in zip(selected, denominator)],
                    ".-", color=colours[component], lw=1.6, label=component.capitalize())
        if normalized:
            ax.axhline(1, color="#666666", ls="--", lw=1.4, label="Injected energy")
        else:
            ax.plot(times, [r["injected_energy_erg"] for r in selected], "--", color="#666666",
                    lw=1.6, label="Injected energy")
            ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0), useMathText=True)
        ax.set_title(case)
        ax.set_xlim(7, 53)
        ax.set_xticks([10, 20, 30, 40, 50])
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.18)
        ax.set_ylabel(r"$\Delta E / E_{\rm injected}$" if normalized else "Energy change [erg]")
        if case == "G-HI":
            ax.text(0.98, 0.94, "50 Myr excluded", transform=ax.transAxes, ha="right", va="top", fontsize=10)
    for ax in axes[-1]:
        ax.set_xlabel("Simulation age [Myr]")
    fig.suptitle("Whole-grid energy change compared with jet injection", y=0.98, fontsize=16)
    fig.text(0.5, 0.935, "All physical cells; initial state subtracted; no shock selection", ha="center", fontsize=11)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.005))
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.16, top=0.86, wspace=0.25, hspace=0.3)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows, summary = analyse(args.source_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "whole_grid_energy_comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    plot(rows, args.output_dir / "whole_grid_energy_ratios.png", normalized=True)
    plot(rows, args.output_dir / "whole_grid_energy_absolute.png", normalized=False)
    print(json.dumps({"cases": summary["cases"], "checks": summary["checks_max_normalized_difference"]}, indent=2))


if __name__ == "__main__":
    main()
