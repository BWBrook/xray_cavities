#!/usr/bin/env python3
"""Plot the C-HI XRAiSE grid-corrected smoke product."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def log10_positive(values: np.ndarray) -> np.ndarray:
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        return np.full_like(values, np.nan, dtype=float)
    floor = max(float(np.nanpercentile(positive, 1)), float(np.nanmin(positive)), 1e-300)
    return np.log10(np.where(values > 0, values, floor))


def plot(product_dir: Path, output_png: Path) -> None:
    x = np.loadtxt(product_dir / "x_kpc.tsv")
    z = np.loadtxt(product_dir / "z_kpc.tsv")
    raw = np.loadtxt(product_dir / "xray_1kev_raw_mjy_sr.tsv", delimiter="\t")
    corrected = np.loadtxt(product_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv", delimiter="\t")
    ratio = np.loadtxt(product_dir / "xray_1kev_correction_ratio.tsv", delimiter="\t")
    tracer = np.loadtxt(product_dir / "tracer_max_los.tsv", delimiter="\t")
    metadata = json.loads((product_dir / "xraise_grid_smoke_metadata.json").read_text())

    extent = [float(x.min()), float(x.max()), float(z.min()), float(z.max())]
    xx, zz = np.meshgrid(x, z)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), constrained_layout=True)

    panels = [
        (axes[0], log10_positive(raw), "pre-correction", "log10 mJy sr$^{-1}$", "viridis"),
        (axes[1], log10_positive(corrected), "APEC + Gaunt corrected", "log10 mJy sr$^{-1}$", "viridis"),
        (axes[2], np.where(ratio > 0, ratio, np.nan), "correction ratio", "corrected / raw", "magma"),
    ]
    for ax, image, title, label, cmap in panels:
        im = ax.imshow(
            image,
            origin="lower",
            extent=extent,
            aspect="equal",
            interpolation="nearest",
            cmap=cmap,
        )
        ax.contour(xx, zz, tracer, levels=[5e-3], colors="white", linewidths=0.6)
        ax.set_xlim(-45, 45)
        ax.set_ylim(-45, 45)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        ax.set_title(title)
        fig.colorbar(im, ax=ax, shrink=0.82, label=label)

    stats = metadata["corrected_stats_mjy_sr"]
    axes[1].text(
        0.02,
        0.02,
        f"max={stats['max']:.2e}\nsum={stats['sum']:.2e}",
        transform=axes[1].transAxes,
        fontsize=8,
        color="white",
        bbox={"facecolor": "black", "alpha": 0.45, "edgecolor": "none", "pad": 4},
    )
    fig.suptitle(f"C-HI XRAiSE grid smoke, t={metadata['time_myr']:.4f} Myr", fontsize=14)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("product_dir", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()
    plot(args.product_dir, args.output_png)


if __name__ == "__main__":
    main()
