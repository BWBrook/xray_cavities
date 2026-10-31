#!/usr/bin/env python3
"""Evaluate retained XRAiSE correction tables without reading native fields."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq

from xraise_grid_smoke import DEFAULT_FREQ_HZ, make_interpolators


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apec-table", type=Path, required=True)
    parser.add_argument("--gaunt-lut", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    expected = {
        "apec": "e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3",
        "gaunt": "64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747",
    }
    observed = {"apec": sha256(args.apec_table), "gaunt": sha256(args.gaunt_lut)}
    if observed != expected:
        raise ValueError(f"Retained table hash mismatch: {observed}")
    apec, gaunt = make_interpolators(args.apec_table, args.gaunt_lut)
    redshift = 0.05
    kev_per_k = 8.617333262e-8

    def factors(temperature):
        temperature = np.atleast_1d(temperature).astype(float)
        ap = np.column_stack((temperature, np.full_like(temperature, redshift)))
        gp = np.column_stack((temperature / kev_per_k,
                              np.full_like(temperature, DEFAULT_FREQ_HZ)))
        ac = ap.copy()
        gc = gp.copy()
        for points, interpolator in ((ac, apec), (gc, gaunt)):
            for axis, coordinates in enumerate(interpolator.grid):
                points[:, axis] = np.clip(points[:, axis], coordinates[0], coordinates[-1])
        av, gv = apec(ap), gaunt(gp)
        return np.column_stack((temperature, av, gv, av * gv, apec(ac) * gaunt(gc)))

    selected = np.array([5., 10., 15., 20., 50., 100., 1000.])
    knots = np.concatenate((apec.grid[0], gaunt.grid[0] * kev_per_k))
    grid = np.unique(np.concatenate((np.geomspace(5, 1000, 10001),
                                     knots[(knots >= 5) & (knots <= 1000)], selected)))
    curve = factors(grid)
    if not np.all(np.isfinite(curve)):
        raise ValueError("Nonfinite correction factor")
    roots = []
    for left, right in zip(curve[:-1], curve[1:]):
        if left[3] * right[3] < 0:
            roots.append(brentq(lambda t: factors(t)[0, 3], left[0], right[0]))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    header = ["temperature_kev", "apec_linear", "gaunt_linear", "product_linear", "product_clamp_each_coordinate"]
    for name, rows in (("selected_temperatures.csv", factors(selected)), ("correction_curve.csv", curve)):
        with (args.output_dir / name).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    for ax in axes:
        ax.plot(grid, curve[:, 3], label="Retained linear extrapolation", color="#2166ac")
        ax.plot(grid, curve[:, 4], "--", label="Clamp each table coordinate", color="#b35806")
        ax.scatter(selected, factors(selected)[:, 3], s=20, color="#2166ac", zorder=4)
        ax.axhline(0, color="0.5", linewidth=.7)
        ax.axvline(10, color="0.5", linestyle=":", label="APEC upper table edge")
        ax.set_xlabel("Temperature (keV)")
        ax.set_ylabel("APEC × Gaunt correction factor")
        ax.grid(alpha=.15)
    axes[0].set_xlim(5, 20)
    central = curve[(grid >= 5) & (grid <= 20), 3:]
    margin = max(float(np.ptp(central)) * .12, .05)
    axes[0].set_ylim(float(central.min()) - margin, float(central.max()) + margin)
    axes[0].set_title("Shell-temperature check")
    axes[0].legend(fontsize=8)
    axes[1].set_xscale("log")
    axes[1].set_xlim(5, 1000)
    axes[1].set_title("Extended extrapolation check")
    fig.suptitle("Retained XRAiSE tables · z = 0.05 · 1 keV frequency")
    fig.savefig(args.output_dir / "correction_curve.png", dpi=180)
    plt.close(fig)
    metadata = {
        "redshift": redshift, "frequency_hz": DEFAULT_FREQ_HZ,
        "kev_per_kelvin": kev_per_k, "table_sha256": observed,
        "table_paths": {"apec": str(args.apec_table), "gaunt": str(args.gaunt_lut)},
        "renderer_sha256": sha256(Path(__file__).with_name("xraise_grid_smoke.py")),
        "script_sha256": sha256(__file__), "zero_crossings_kev": roots,
        "sample_count": len(grid), "native_fields_read": False,
        "minimum_product_5_to_20_kev": float(central[:, 0].min()),
        "numpy_version": np.__version__,
    }
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    print(factors(selected))


if __name__ == "__main__":
    main()
