#!/usr/bin/env python3
"""Build the aligned C-HI 5 Myr smoke comparison package."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def read_metric_csv(path: Path) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            out[row["metric"]] = (row["value"], row.get("unit", ""))
    return out


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def f(value: str | float | int) -> float:
    return float(value)


def metric(metrics: dict[str, tuple[str, str]], name: str) -> float:
    return f(metrics[name][0])


def select_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise KeyError(f"no row matching {criteria}")


def centres_to_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("need at least two coordinate centres")
    mids = 0.5 * (values[:-1] + values[1:])
    first = values[0] - (mids[0] - values[0])
    last = values[-1] + (values[-1] - mids[-1])
    return np.concatenate([[first], mids, [last]])


def log10_positive(values: np.ndarray) -> np.ndarray:
    out = np.full_like(values, np.nan, dtype=float)
    mask = np.isfinite(values) & (values > 0.0)
    out[mask] = np.log10(values[mask])
    return out


def cmap_with_background(name: str):
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad("#f2f2f2")
    return cmap


def load_matrix(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter="\t")


def write_metrics(path: Path, rows: list[dict[str, str | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["category", "metric", "value", "unit", "source"]
    with path.open("w", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def add_cavity_boundaries(ax: plt.Axes, cavity_boundary: Path) -> None:
    by_side: dict[str, list[tuple[float, float]]] = {}
    with cavity_boundary.open(newline="") as f_in:
        for row in csv.DictReader(f_in, delimiter="\t"):
            by_side.setdefault(row["side"], []).append((f(row["x_kpc"]), f(row["z_kpc"])))
    for side, points in by_side.items():
        xy = np.asarray(points)
        colour = "#41ab5d" if side == "positive_z" else "#238b45"
        ax.plot(xy[:, 0], xy[:, 1], color=colour, lw=1.4, alpha=0.95)


def plot_package(
    *,
    output_png: Path,
    xraise_dir: Path,
    radio_dir: Path,
    cavity_boundary: Path,
    energy_values_1e59: list[float],
    energy_labels: list[str],
    radio_luminosity: float,
    lobe_ratio: float,
) -> None:
    x_xray = np.loadtxt(xraise_dir / "x_kpc.tsv")
    z_xray = np.loadtxt(xraise_dir / "z_kpc.tsv")
    x_radio = np.loadtxt(radio_dir / "x_kpc.tsv")
    z_radio = np.loadtxt(radio_dir / "z_kpc.tsv")

    xray = load_matrix(xraise_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv")
    tracer = load_matrix(xraise_dir / "tracer_max_los.tsv")
    radio = load_matrix(radio_dir / "radio_150mhz_particle_loss_mjy_sr.tsv")

    fig, axes = plt.subplots(2, 2, figsize=(11.2, 9.2), constrained_layout=True)
    xlim = (-42.0, 42.0)
    zlim = (-48.0, 48.0)

    panels = [
        (
            axes[0, 0],
            x_xray,
            z_xray,
            log10_positive(xray),
            "XRAiSE 1 keV corrected X-ray",
            "log10 mJy sr$^{-1}$",
            "magma",
        ),
        (
            axes[0, 1],
            x_radio,
            z_radio,
            log10_positive(radio),
            "150 MHz particle-loss radio",
            "log10 mJy sr$^{-1}$",
            "magma",
        ),
        (
            axes[1, 0],
            x_xray,
            z_xray,
            np.where(tracer > 0.0, tracer, np.nan),
            "Tracer maximum along line of sight",
            "max tracer",
            "viridis",
        ),
    ]

    for ax, x, z, values, title, label, cmap in panels:
        mesh = ax.pcolormesh(
            centres_to_edges(x),
            centres_to_edges(z),
            values,
            shading="auto",
            cmap=cmap_with_background(cmap),
        )
        add_cavity_boundaries(ax, cavity_boundary)
        cbar = fig.colorbar(mesh, ax=ax, shrink=0.84)
        cbar.set_label(label)
        ax.set_title(title)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        ax.set_xlim(*xlim)
        ax.set_ylim(*zlim)
        ax.set_aspect("equal", adjustable="box")

    metric_ax = axes[1, 1]
    metric_ax.set_title("Scalar comparison")
    y = np.arange(len(energy_values_1e59))
    metric_ax.barh(y, energy_values_1e59, color=["#3969ac", "#4baf4f", "#cc503e"])
    metric_ax.set_yticks(y, energy_labels)
    metric_ax.invert_yaxis()
    metric_ax.set_xlabel("energy (1e59 erg)")
    metric_ax.grid(axis="x", color="#dddddd", lw=0.7)
    metric_ax.set_xlim(0, max(energy_values_1e59) * 1.22)
    for idx, value in enumerate(energy_values_1e59):
        metric_ax.text(value + 0.04, idx, f"{value:.2f}", va="center", fontsize=9)
    metric_ax.text(
        0.04,
        0.05,
        f"Radio L_150: {radio_luminosity:.3e} W Hz$^{{-1}}$\n"
        f"lobe balance ratio: {lobe_ratio:.4f}",
        transform=metric_ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.8, "edgecolor": "#cccccc"},
    )

    fig.suptitle("C-HI aligned 5 Myr / 0 degree smoke comparison", fontsize=14)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quicklook-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_to5_quicklook_2026-05-10",
    )
    parser.add_argument(
        "--xraise-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_xraise_grid_smoke_2026-05-10",
    )
    parser.add_argument(
        "--cavity-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_cavity_stub_2026-05-10",
    )
    parser.add_argument(
        "--radio-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_particle_radio_smoke_2026-05-10",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_aligned_comparison_2026-05-10",
    )
    args = parser.parse_args()

    level1 = read_metric_csv(args.quicklook_dir / "level1_injected_energy.csv")
    level2_rows = read_rows(args.quicklook_dir / "level2_tracer_lobe_truth.csv")
    cavity_rows = read_rows(args.cavity_dir / "cavity_stub_summary.csv")
    xray = read_metric_csv(args.xraise_dir / "xraise_grid_smoke_summary.csv")
    radio = read_metric_csv(args.radio_dir / "particle_radio_smoke_summary.csv")
    radio_lobes = read_rows(args.radio_dir / "particle_radio_lobe_summary.csv")

    level2_default = select_row(level2_rows, threshold="5e-03", side="bipolar_total")
    neg_lobe = select_row(radio_lobes, side="negative_z")
    pos_lobe = select_row(radio_lobes, side="positive_z")

    p_v_total = sum(f(row["pV_erg"]) for row in cavity_rows)
    four_p_v_total = sum(f(row["four_pV_erg"]) for row in cavity_rows)
    sound_age_mean = sum(f(row["sound_age_myr"]) for row in cavity_rows) / len(cavity_rows)
    radio_total = metric(radio, "bipolar_total_lossy_luminosity_doppler")
    radio_lobe_ratio = f(pos_lobe["lossy_luminosity_doppler_w_hz"]) / f(
        neg_lobe["lossy_luminosity_doppler_w_hz"]
    )

    metrics: list[dict[str, str | float]] = [
        {
            "category": "target",
            "metric": "grid_time",
            "value": metric(radio, "grid_time_myr"),
            "unit": "Myr",
            "source": "particle_radio_smoke_summary.csv",
        },
        {
            "category": "truth_level1",
            "metric": "injected_energy_one_sided_elapsed",
            "value": metric(level1, "injected_energy_one_sided_elapsed"),
            "unit": "erg",
            "source": "level1_injected_energy.csv",
        },
        {
            "category": "truth_level1",
            "metric": "injected_energy_bipolar_elapsed",
            "value": metric(level1, "injected_energy_bipolar_elapsed"),
            "unit": "erg",
            "source": "level1_injected_energy.csv",
        },
        {
            "category": "truth_level2",
            "metric": "tracer_lobe_volume_bipolar",
            "value": f(level2_default["volume_kpc3"]),
            "unit": "kpc^3",
            "source": "level2_tracer_lobe_truth.csv",
        },
        {
            "category": "truth_level2",
            "metric": "tracer_lobe_total_energy_bipolar",
            "value": f(level2_default["total_energy_erg"]),
            "unit": "erg",
            "source": "level2_tracer_lobe_truth.csv",
        },
        {
            "category": "cavity",
            "metric": "pV_bipolar",
            "value": p_v_total,
            "unit": "erg",
            "source": "cavity_stub_summary.csv",
        },
        {
            "category": "cavity",
            "metric": "four_pV_bipolar",
            "value": four_p_v_total,
            "unit": "erg",
            "source": "cavity_stub_summary.csv",
        },
        {
            "category": "cavity",
            "metric": "sound_age_mean",
            "value": sound_age_mean,
            "unit": "Myr",
            "source": "cavity_stub_summary.csv",
        },
        {
            "category": "xray",
            "metric": "corrected_xray_max",
            "value": metric(xray, "corrected_xray_max"),
            "unit": "mJy sr^-1",
            "source": "xraise_grid_smoke_summary.csv",
        },
        {
            "category": "xray",
            "metric": "corrected_xray_sum",
            "value": metric(xray, "corrected_xray_sum"),
            "unit": "mJy sr^-1 pixels",
            "source": "xraise_grid_smoke_summary.csv",
        },
        {
            "category": "radio",
            "metric": "radio_map_max",
            "value": metric(radio, "radio_map_max_mjy_sr"),
            "unit": "mJy sr^-1",
            "source": "particle_radio_smoke_summary.csv",
        },
        {
            "category": "radio",
            "metric": "radio_luminosity_bipolar",
            "value": radio_total,
            "unit": "W Hz^-1",
            "source": "particle_radio_smoke_summary.csv",
        },
        {
            "category": "radio",
            "metric": "radio_lobe_balance_positive_over_negative",
            "value": radio_lobe_ratio,
            "unit": "ratio",
            "source": "particle_radio_lobe_summary.csv",
        },
    ]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_metrics(args.output_dir / "aligned_smoke_metrics.csv", metrics)
    plot_package(
        output_png=args.output_dir / "c_hi_aligned_comparison_maps.png",
        xraise_dir=args.xraise_dir,
        radio_dir=args.radio_dir,
        cavity_boundary=args.cavity_dir / "cavity_ellipse_boundary_0deg.tsv",
        energy_values_1e59=[
            metric(level1, "injected_energy_bipolar_elapsed") / 1.0e59,
            f(level2_default["total_energy_erg"]) / 1.0e59,
            four_p_v_total / 1.0e59,
        ],
        energy_labels=["Injected", "Tracer lobe", "4pV cavity"],
        radio_luminosity=radio_total,
        lobe_ratio=radio_lobe_ratio,
    )
    print(f"wrote {args.output_dir}")


if __name__ == "__main__":
    main()
