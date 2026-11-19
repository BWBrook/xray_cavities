"""Match the two manufactured fields and the 29–30 Myr production measurements by estimator."""
from __future__ import annotations

import argparse
import csv
import math
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from calibrate_nozzle_flux import CASES, PADDINGS
from measure_q031_fluxes import CONTROL_RECONSTRUCTIONS, SECONDS_PER_MYR


def read_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def unique_index(pairs):
    index = {}
    for key, value in pairs:
        if key in index:
            raise ValueError(f"duplicate measurement: {key}")
        index[key] = value
    return index


def match(primary, averages, production):
    measured = unique_index(((r["case"], int(r["padding_cells"]), r["method"]), r)
                            for r in read_rows(primary) if r["subdivision"] == "1")
    volume = unique_index(((r["case"], int(r["padding_cells"]), r["reconstruction"]), r)
                          for r in read_rows(averages) if r["quadrature_order"] == "16")
    pairs, endpoints = [], []
    for path in production:
        for r in read_rows(path.with_name("instantaneous_surface_fluxes.csv")):
            if (r["surface"].startswith("nozzle_control_p") and r["face"] == "closed_surface_total"
                    and int(r["snapshot_index"]) in (29, 30)):
                pad = int(r["surface"].removeprefix("nozzle_control_p"))
                endpoints.append(((r["case"], pad, r["reconstruction"], int(r["snapshot_index"])), r))
        for r in read_rows(path):
            if (r["surface"].startswith("nozzle_control_p") and r["temporal_quadrature"] == "trapezoid"
                    and abs(float(r["interval_start_myr"])-29) < 0.01 and abs(float(r["interval_end_myr"])-30) < 0.01):
                pad = int(r["surface"].removeprefix("nozzle_control_p"))
                pairs.append(((r["case"], pad, r["reconstruction"]), r))
    history = unique_index(pairs)
    fluxes = unique_index(endpoints)
    keys = [(case, pad, method) for case in CASES for pad in PADDINGS for method in CONTROL_RECONSTRUCTIONS]
    if not set(keys) == measured.keys() == volume.keys() == history.keys():
        raise ValueError("expected all six original nozzle reconstructions in each of four cases")
    rows = []
    for case, pad, method in keys:
        key = (case, pad, method)
        raw, avg, run = measured[key], volume[key], history[key]
        centre = float(raw["total_energy_over_label"])
        reference = float(raw["total_energy_reference_over_label"])
        if (centre != float(avg["total_energy_cell_centre_over_label"])
                or reference != float(avg["total_energy_reference_over_label"])):
            raise ValueError(f"manufactured references disagree: {key}")
        label = float(raw["bipolar_label_erg_s"])*float(run["interval_duration_myr"])*SECONDS_PER_MYR
        transport = float(run["integrated_energy_flux_outward_erg"])/label
        storage = float(run["storage_energy_change_erg"])/label
        source = float(run["inferred_internal_energy_source_erg"])/label
        if not math.isclose(source, storage + transport, rel_tol=1e-12):
            raise ValueError(f"production balance mismatch: {key}")
        left, right = (fluxes[(*key, index)] for index in (29, 30))
        if (float(left["actual_time_myr"]) != float(run["interval_start_myr"])
                or float(right["actual_time_myr"]) != float(run["interval_end_myr"])):
            raise ValueError(f"production snapshots and interval ages disagree: {key}")
        power = float(raw["bipolar_label_erg_s"])
        components = {}
        for name in ("kinetic", "enthalpy", "potential"):
            field = name + "_flux_outward_erg_s"
            components["production_" + name + "_transport_over_interval_label"] = (
                float(left[field]) + float(right[field])) / (2 * power)
        if not math.isclose(sum(components.values()), transport, abs_tol=1e-12):
            raise ValueError(f"production flux components do not sum to transport: {key}")
        rows.append({"case": case, "padding_cells": pad, "reconstruction": method, "reference_over_label": reference,
                     "cell_centre_over_label": centre, "conservative_average_over_label": float(avg["total_energy_conservative_average_over_label"]),
                     "interval_start_myr": run["interval_start_myr"], "interval_end_myr": run["interval_end_myr"],
                     "production_transport_over_interval_label": transport, "production_storage_change_over_interval_label": storage,
                     "production_source_over_interval_label": source, **components})
    return rows


def plot(rows, path):
    fig, axes = plt.subplots(2, 4, figsize=(10.6, 5.6), sharex=True, sharey=True)
    series = [
        ("reference_over_label", "Continuum reference", "#555555", "", "--"),
        ("cell_centre_over_label", "Point-sampled jet", "#0072B2", "o", "-"),
        ("conservative_average_over_label", "Volume-averaged jet", "#009E73", "^", "-"),
        ("production_source_over_interval_label", "Production, 29–30 Myr", "#D55E00", "s", "-"),
    ]
    for column, case in enumerate(CASES):
        axes[0, column].set_title(case, loc="left", weight="bold")
        for row_index, method in enumerate(CONTROL_RECONSTRUCTIONS):
            ax = axes[row_index, column]
            selected = [r for r in rows if r["case"] == case and r["reconstruction"] == method]
            for field, name, colour, marker, style in series:
                ax.plot([r["padding_cells"] for r in selected], [r[field] for r in selected],
                        color=colour, marker=marker, ls=style, label=name, markersize=4.5, linewidth=1.4)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_xticks(PADDINGS)
            ax.grid(axis="y", alpha=0.21)
            ax.set_xlim(0.72, 4.28)
    axes[0, 0].set_ylabel("Centred primitives\nFraction of labelled power")
    axes[1, 0].set_ylabel("Donor cell\nFraction of labelled power")
    fig.subplots_adjust(left=0.10, right=0.985, top=0.92, bottom=0.20, hspace=0.18, wspace=0.12)
    fig.supxlabel("Control-box padding (native cells)", y=0.105, fontsize=10)
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="lower center", ncol=4, frameon=False, fontsize=9)
    fig.savefig(path, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--averages", required=True, type=Path)
    parser.add_argument("--production", required=True, type=Path, nargs=4)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    comparison = match(args.primary, args.averages, args.production)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        stage = Path(tmp) / "results"
        stage.mkdir()
        with (stage/"matched_nozzle_flux.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(comparison[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(comparison)
        plot(comparison, stage/"nozzle_flux_calibration.png")
        stage.rename(args.output)
