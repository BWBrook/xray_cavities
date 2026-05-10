#!/usr/bin/env python3
"""Plot the C-HI particle-loss-aware radio smoke products."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_matrix(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter="\t")


def log10_positive(values: np.ndarray) -> np.ndarray:
    out = np.full_like(values, np.nan, dtype=float)
    mask = np.isfinite(values) & (values > 0)
    out[mask] = np.log10(values[mask])
    return out


def cmap_with_background(name: str):
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad("#f2f2f2")
    return cmap


def plot(input_dir: Path, output_png: Path) -> None:
    x = np.loadtxt(input_dir / "x_kpc.tsv")
    z = np.loadtxt(input_dir / "z_kpc.tsv")
    lossy = load_matrix(input_dir / "radio_150mhz_particle_loss_mjy_sr.tsv")
    lossless = load_matrix(input_dir / "radio_150mhz_particle_lossless_mjy_sr.tsv")
    counts = load_matrix(input_dir / "radio_particle_count_map.tsv")
    mean_loss = load_matrix(input_dir / "radio_particle_mean_loss_factor.tsv")
    particles = np.genfromtxt(
        input_dir / "particle_radio_positions_0deg.tsv",
        delimiter="\t",
        names=True,
    )
    occupancy_log = np.full_like(counts, np.nan, dtype=float)
    count_mask = counts > 0
    occupancy_log[count_mask] = np.log10(counts[count_mask])

    extent = [float(x.min()), float(x.max()), float(z.min()), float(z.max())]
    fig, axes = plt.subplots(2, 2, figsize=(11, 9), constrained_layout=True)

    panels = [
        (axes[0, 0], log10_positive(lossy), "150 MHz lossy particle map", "log10 mJy sr$^{-1}$", "magma"),
        (axes[0, 1], log10_positive(lossless), "150 MHz lossless particle map", "log10 mJy sr$^{-1}$", "magma"),
        (axes[1, 0], np.where(counts > 0, mean_loss, np.nan), "Mean loss factor per pixel", "loss factor", "viridis"),
        (axes[1, 1], occupancy_log, "Particle occupancy", "log10 count", "cividis"),
    ]

    for ax, data, title, label, cmap in panels:
        im = ax.imshow(
            data,
            origin="lower",
            extent=extent,
            aspect="equal",
            interpolation="nearest",
            cmap=cmap_with_background(cmap),
        )
        cbar = fig.colorbar(im, ax=ax, shrink=0.84)
        cbar.set_label(label)
        ax.set_title(title)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        ax.set_xlim(-42, 42)
        ax.set_ylim(-48, 48)

    axes[1, 1].scatter(
        particles["x_kpc"],
        particles["z_kpc"],
        s=0.25,
        c="white",
        alpha=0.18,
        linewidths=0,
    )

    fig.suptitle("C-HI 5 Myr, 0 degree, particle-loss-aware radio smoke", fontsize=14)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()
    plot(args.input_dir, args.output_png)


if __name__ == "__main__":
    main()
