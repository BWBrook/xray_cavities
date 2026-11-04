#!/usr/bin/env python3
"""Report raw spherical storage measurements, preserving missing data and holds."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from extract_spherical_energy_budget import CASES, COMPONENTS


def collect(paths: list[Path], case: str, indices: list[int]) -> tuple[list[dict], dict[str, str]]:
    records = {}
    hashes = {}
    for path in paths:
        raw = path.read_bytes()
        data = json.loads(raw)
        if data.get("execution_status") != "completed_spherical_energy_budget_measurement":
            raise ValueError(f"not a completed spherical measurement: {path}")
        if data["case"] != case:
            raise ValueError(f"case mismatch: {path}")
        index = data["snapshot_index"]
        if index not in indices or index in records:
            raise ValueError(f"unexpected or duplicate snapshot {index}")
        records[index] = data
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
    rows = []
    for index in indices:
        data = records.get(index)
        for speed in (100, 300):
            item = data["thresholds"][str(speed)] if data else None
            row = {
                "case": case, "snapshot_index": index, "speed_threshold_km_s": speed,
                "actual_time_myr": data["actual_time_myr"] if data else None,
                "measurement_status": item["measurement_status"] if item else "not_measured",
                "raw_radius_kpc": item["raw_radius_kpc"] if item else None,
                "domain_geometry_status": item.get("domain_geometry_status") if item else None,
                "measurement_hold_codes": ";".join(sorted({h["code"] for h in item["scientific_qualification"]["holds"]})) if item else "",
                "native_enthalpy_hold_codes": ";".join(sorted({h["code"] for h in data["native_lobe_enthalpy"]["scientific_qualification"]["holds"]})) if data else "",
                "global_hold_codes": ";".join(sorted({h["code"] for h in data["scientific_qualification"]["holds"]})) if data else "",
                "injected_energy_erg": data["injected_energy_erg"] if data else None,
                "cocoon_volume_kpc3": data["cocoon_global"]["volume_kpc3"] if data else None,
            }
            sphere = item.get("sphere_budget") if item else None
            for part in ("all", "cocoon", "ambient"):
                values = (sphere["delta_erg"] if part == "all" else sphere["current_binary_partition"][part]) if sphere else None
                for component in (*COMPONENTS, "total"):
                    energy = values[f"{component}_delta_erg"] if values else None
                    row[f"{part}_{component}_delta_erg"] = energy
                    row[f"{part}_{component}_over_injected"] = energy / row["injected_energy_erg"] if energy is not None and row["injected_energy_erg"] > 0 else None
            for alpha in ("2.5", "4"):
                proxy = data["native_lobe_enthalpy"]["conventions"][alpha] if data else None
                row[f"native_enthalpy_{alpha}_erg"] = proxy["enthalpy_erg"] if proxy else None
                row[f"native_enthalpy_{alpha}_over_injected"] = proxy["enthalpy_over_injected"] if proxy else None
            rows.append(row)
    return rows, hashes


def plot(rows: list[dict], output: Path, case: str) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    colors = {100: "#0072B2", 300: "#D55E00"}
    for speed in (100, 300):
        selected = [row for row in rows if row["speed_threshold_km_s"] == speed]
        x = np.array([r["actual_time_myr"] if r["actual_time_myr"] is not None else np.nan for r in selected])
        for ax, field in zip(axes.flat, ("raw_radius_kpc", "all_total_over_injected", "cocoon_total_over_injected", "ambient_total_over_injected")):
            y = np.array([r[field] if r[field] is not None else np.nan for r in selected])
            ax.plot(x, y, "o-", ms=3, color=colors[speed], label=f"{speed} km/s")
            truncated = np.array([r["domain_geometry_status"] == "domain_truncated_spherical_cell_selection" for r in selected])
            if np.any(truncated):
                ax.scatter(x[truncated], y[truncated], marker="x", s=45, color="black", zorder=4)
    native = [r for r in rows if r["speed_threshold_km_s"] == 100]
    for alpha, style in (("2.5", "--"), ("4", ":")):
        axes[0, 1].plot(
            [r["actual_time_myr"] if r["actual_time_myr"] is not None else np.nan for r in native],
            [r[f"native_enthalpy_{alpha}_over_injected"] if r[f"native_enthalpy_{alpha}_over_injected"] is not None else np.nan for r in native],
            style, color="#444444", label=f"Native lobe {alpha}pV",
        )
    titles = ("Speed-defined radius", "Total storage change and native proxies", "Cocoon storage change", "Ambient storage change")
    for ax, title in zip(axes.flat, titles):
        ax.set_title(title)
        ax.set_xlabel("Actual simulation age (Myr)")
        ax.grid(alpha=0.2)
        if ax is axes[0, 0]:
            ax.set_ylabel("Radius (kpc)")
        else:
            ax.axhline(1, color="#777777", lw=0.8)
            ax.axhline(0, color="#bbbbbb", lw=0.6)
            ax.set_ylabel("Energy / labelled bipolar input")
        ax.legend(fontsize=8)
    absent = sum(r["measurement_status"] == "not_measured" for r in rows) // 2
    unavailable = sum(r["measurement_status"].startswith("unavailable") for r in rows)
    fig.suptitle(f"{case}: raw measurements; qualification holds retained\n{absent} snapshots not measured; {unavailable} threshold measurements unavailable. × = domain truncated", fontsize=11)
    fig.savefig(output / f"{case}_spherical_budgets.png", dpi=180)
    fig.savefig(output / f"{case}_spherical_budgets.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(13, 7), constrained_layout=True, sharex=True)
    component_colors = {"thermal": "#D55E00", "kinetic": "#0072B2", "gravitational": "#009E73", "total": "#222222"}
    for row_index, speed in enumerate((100, 300)):
        selected = [r for r in rows if r["speed_threshold_km_s"] == speed]
        x = [r["actual_time_myr"] if r["actual_time_myr"] is not None else np.nan for r in selected]
        for ax, part in zip(axes[row_index], ("all", "cocoon", "ambient")):
            for component in (*COMPONENTS, "total"):
                field = f"{part}_{component}_over_injected"
                y = [r[field] if r[field] is not None else np.nan for r in selected]
                ax.plot(x, y, "o-", ms=3, color=component_colors[component], label=component)
            ax.axhline(0, color="#bbbbbb", lw=0.6)
            ax.axhline(1, color="#777777", lw=0.8, ls=":")
            ax.set_title(f"{part.capitalize()} — {speed} km/s aperture")
            ax.set_xlabel("Actual simulation age (Myr)")
            ax.set_ylabel("Storage change / labelled bipolar input")
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8)
    fig.suptitle(f"{case}: component storage changes; qualification holds retained\nMoving apertures are not closed energy budgets; missing measurements remain gaps", fontsize=11)
    fig.savefig(output / f"{case}_spherical_components.png", dpi=180)
    fig.savefig(output / f"{case}_spherical_components.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--indices", type=int, nargs="+", required=True)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(set(args.indices)) != len(args.indices) or any(i < 0 or (args.case == "G-HI" and i >= 48) for i in args.indices):
        parser.error("indices must be unique, nonnegative and scientifically retained")
    rows, hashes = collect(args.inputs, args.case, sorted(args.indices))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "measurements.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plot(rows, args.output_dir, args.case)
    products = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output_dir.iterdir()}
    (args.output_dir / "summary_receipt.json").write_text(json.dumps({
        "status": "summarized_raw_measurements", "case": args.case,
        "expected_indices": sorted(args.indices), "input_sha256": hashes, "products_sha256": products,
        "interpretation": "Time-varying aperture storage is not energy closure. Native enthalpy is a separate global lobe proxy, not an additive energy term. Blank values are unavailable or not measured; never zero-imputed.",
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
