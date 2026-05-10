#!/usr/bin/env python3
"""Plot the first-pass C-HI cavity-protocol stub."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def log10_positive(values: np.ndarray) -> np.ndarray:
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        return np.full_like(values, np.nan, dtype=float)
    floor = max(float(np.nanpercentile(positive, 1)), float(np.nanmin(positive)), 1e-300)
    return np.log10(np.where(values > 0, values, floor))


def read_summary(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_ellipse(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    data = np.genfromtxt(path, delimiter="\t", names=True, dtype=None, encoding="utf-8")
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for side in np.unique(data["side"]):
        mask = data["side"] == side
        out[str(side)] = (data["x_kpc"][mask], data["z_kpc"][mask])
    return out


def plot(observable_dir: Path, cavity_dir: Path, output_png: Path) -> None:
    x = np.loadtxt(observable_dir / "x_kpc.tsv")
    z = np.loadtxt(observable_dir / "z_kpc.tsv")
    xray = np.loadtxt(observable_dir / "xray_1kev_raw_mjy_sr.tsv", delimiter="\t")
    tracer = np.loadtxt(observable_dir / "tracer_max_los.tsv", delimiter="\t")
    ellipses = read_ellipse(cavity_dir / "cavity_ellipse_boundary_0deg.tsv")
    summary = read_summary(cavity_dir / "cavity_stub_summary.csv")

    extent = [float(x.min()), float(x.max()), float(z.min()), float(z.max())]
    xx, zz = np.meshgrid(x, z)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), constrained_layout=True)

    im0 = axes[0].imshow(
        log10_positive(xray),
        origin="lower",
        extent=extent,
        aspect="equal",
        interpolation="nearest",
        cmap="viridis",
    )
    fig.colorbar(im0, ax=axes[0], shrink=0.82, label="log10 raw 1 keV mJy sr$^{-1}$")
    axes[0].contour(xx, zz, tracer, levels=[5e-3], colors="white", linewidths=0.7)
    axes[0].set_title("X-ray bridge map with cavity ellipses")

    im1 = axes[1].imshow(
        tracer,
        origin="lower",
        extent=extent,
        aspect="equal",
        interpolation="nearest",
        cmap="magma",
        vmin=0,
        vmax=1,
    )
    fig.colorbar(im1, ax=axes[1], shrink=0.82, label="max tracer LOS")
    axes[1].contour(xx, zz, tracer, levels=[5e-3], colors="white", linewidths=0.7)
    axes[1].set_title("Tracer boundary and ellipsoid fit")

    colors = {"negative_z": "#62d7ff", "positive_z": "#ffdc5e"}
    for ax in axes:
        for side, (ex, ez) in ellipses.items():
            ax.plot(ex, ez, color=colors.get(side, "black"), linewidth=1.8, label=side)
        ax.set_xlim(-45, 45)
        ax.set_ylim(-45, 45)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        ax.legend(loc="upper right", fontsize=8)

    text_lines = []
    for row in summary:
        label = "-" if row["side"] == "negative_z" else "+"
        text_lines.append(
            f"{label}z: pV={float(row['pV_erg']):.2e} erg, "
            f"4pV={float(row['four_pV_erg']):.2e} erg, "
            f"t_s={float(row['sound_age_myr']):.1f} Myr"
        )
    axes[1].text(
        0.02,
        0.02,
        "\n".join(text_lines),
        transform=axes[1].transAxes,
        fontsize=8,
        color="white",
        bbox={"facecolor": "black", "alpha": 0.45, "edgecolor": "none", "pad": 4},
    )

    fig.suptitle("C-HI 5 Myr cavity-protocol stub", fontsize=14)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("observable_dir", type=Path)
    parser.add_argument("cavity_dir", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()
    plot(args.observable_dir, args.cavity_dir, args.output_png)


if __name__ == "__main__":
    main()
