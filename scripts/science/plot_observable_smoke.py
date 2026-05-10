#!/usr/bin/env python3
"""Plot compact C-HI observable-smoke products."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_matrix(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter="\t")


def log10_positive(values: np.ndarray) -> np.ndarray:
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        return np.full_like(values, np.nan, dtype=float)
    floor = np.nanpercentile(positive, 1)
    floor = max(floor, np.nanmin(positive), 1e-300)
    return np.log10(np.where(values > 0, values, floor))


def plot(input_dir: Path, output_png: Path) -> None:
    x = np.loadtxt(input_dir / "x_kpc.tsv")
    z = np.loadtxt(input_dir / "z_kpc.tsv")
    xray = load_matrix(input_dir / "xray_1kev_raw_mjy_sr.tsv")
    radio = load_matrix(input_dir / "radio_150mhz_proxy_mjy_sr.tsv")
    tracer = load_matrix(input_dir / "tracer_max_los.tsv")
    particles = np.genfromtxt(
        input_dir / "particle_positions_0deg.tsv",
        delimiter="\t",
        names=True,
    )

    extent = [float(x.min()), float(x.max()), float(z.min()), float(z.max())]
    central_xlim = (-45, 45)
    central_zlim = (-55, 55)

    fig, axes = plt.subplots(2, 2, figsize=(11, 9), constrained_layout=True)

    panels = [
        (axes[0, 0], log10_positive(xray), "X-ray raw grid SB", "log10 mJy sr$^{-1}$", None),
        (axes[0, 1], log10_positive(xray), "X-ray central view", "log10 mJy sr$^{-1}$", "central"),
        (axes[1, 0], log10_positive(radio), "Radio proxy central view", "log10 mJy sr$^{-1}$", "central"),
        (axes[1, 1], tracer, "Particles and lobe boundary", "max tracer LOS", "central"),
    ]

    for ax, data, title, label, mode in panels:
        im = ax.imshow(
            data,
            origin="lower",
            extent=extent,
            aspect="equal",
            interpolation="nearest",
            cmap="magma" if "Radio" in title else "viridis",
        )
        cbar = fig.colorbar(im, ax=ax, shrink=0.84)
        cbar.set_label(label)
        ax.set_title(title)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        if mode == "central":
            ax.set_xlim(*central_xlim)
            ax.set_ylim(*central_zlim)

    xx, zz = np.meshgrid(x, z)
    for ax in (axes[0, 1], axes[1, 0], axes[1, 1]):
        ax.contour(xx, zz, tracer, levels=[5e-3], colors="white", linewidths=0.7, alpha=0.9)

    axes[1, 1].scatter(
        particles["x_kpc"],
        particles["z_kpc"],
        s=0.2,
        c="cyan",
        alpha=0.22,
        linewidths=0,
    )

    fig.suptitle("C-HI 5 Myr, 0 degree observable smoke", fontsize=14)
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
