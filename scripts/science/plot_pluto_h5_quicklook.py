#!/usr/bin/env python3
"""Plot compact PLUTO HDF5 quick-look products extracted on a compute node."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CODE_TIME_PER_MYR = 306.6013937879523


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--label", default="PLUTO quick-look")
    return parser.parse_args()


def load_vector(path: Path) -> np.ndarray:
    return np.loadtxt(path)


def load_matrix(path: Path) -> np.ndarray:
    return np.loadtxt(path)


def load_metrics(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        return {row["metric"]: row["value"] for row in csv.DictReader(handle)}


def signed_log10(values: np.ndarray, floor: float = 1.0e-30) -> np.ndarray:
    clipped = np.maximum(np.abs(values), floor)
    return np.sign(values) * np.log10(clipped)


def plot_maps(
    input_dir: Path,
    output_dir: Path,
    label: str,
    time_myr: float,
    suffix: str,
    zoom: bool = False,
) -> Path:
    x = load_vector(input_dir / "x_centres.tsv")
    z = load_vector(input_dir / "z_centres.tsv")
    rho = load_matrix(input_dir / "slice_xz_rho.tsv")
    prs = load_matrix(input_dir / "slice_xz_prs.tsv")
    tr1 = load_matrix(input_dir / "slice_xz_tr1.tsv")
    vx3 = load_matrix(input_dir / "slice_xz_vx3.tsv")

    panels = [
        (np.log10(np.maximum(rho, 1.0e-30)), "log10 density", "magma"),
        (np.log10(np.maximum(prs, 1.0e-30)), "log10 pressure", "viridis"),
        (np.log10(np.maximum(tr1, 1.0e-12)), "log10 tracer", "inferno"),
        (vx3, "vz", "RdBu_r"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    for ax, (image, title, cmap) in zip(axes.ravel(), panels):
        kwargs = {}
        if title == "vz":
            vmax = float(np.nanpercentile(np.abs(image), 99.5))
            kwargs = {"vmin": -vmax, "vmax": vmax}
        mesh = ax.pcolormesh(z, x, image.T, shading="auto", cmap=cmap, **kwargs)
        ax.set_title(title)
        ax.set_xlabel("z (kpc)")
        ax.set_ylabel("x (kpc)")
        if zoom:
            ax.set_xlim(-15, 15)
            ax.set_ylim(-10, 10)
        fig.colorbar(mesh, ax=ax, pad=0.01)

    zoom_text = "central zoom" if zoom else "full domain"
    fig.suptitle(f"{label}: x-z mid-plane at y=0, {zoom_text}, t={time_myr:.3f} Myr")
    path = output_dir / f"c_hi_quicklook_midplane_maps{suffix}.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_axis_profile(input_dir: Path, output_dir: Path, label: str, time_myr: float) -> Path:
    profile = np.genfromtxt(input_dir / "axis_profile_z.tsv", names=True, delimiter="\t")
    z = profile["z"]

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True, sharex=True)
    axes[0, 0].plot(z, profile["rho"])
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_ylabel("density")
    axes[0, 0].set_title("jet-axis density")

    axes[0, 1].plot(z, profile["prs"])
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_ylabel("pressure")
    axes[0, 1].set_title("jet-axis pressure")

    axes[1, 0].plot(z, profile["tr1"])
    axes[1, 0].set_yscale("log")
    axes[1, 0].set_ylabel("tracer")
    axes[1, 0].set_xlabel("z (kpc)")
    axes[1, 0].set_title("jet-axis tracer")

    axes[1, 1].plot(z, profile["vx3"])
    axes[1, 1].axhline(0.0, color="0.7", linewidth=1)
    axes[1, 1].set_ylabel("vz")
    axes[1, 1].set_xlabel("z (kpc)")
    axes[1, 1].set_title("jet-axis z velocity")

    fig.suptitle(f"{label}: axis profiles at x=0, y=0, t={time_myr:.3f} Myr")
    path = output_dir / "c_hi_quicklook_axis_profiles.png"
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def write_summary(
    output_dir: Path,
    label: str,
    metrics: dict[str, str],
    map_path: Path,
    zoom_map_path: Path,
    profile_path: Path,
) -> Path:
    time_code = float(metrics["time_code"])
    time_myr = time_code / CODE_TIME_PER_MYR
    lines = [
        f"# {label} Quick-look Diagnostics",
        "",
        f"- PLUTO code time: `{time_code:.6g}`",
        f"- Physical time, using `{CODE_TIME_PER_MYR:.6f}` code units per Myr: `{time_myr:.4f} Myr`",
        f"- Grid shape, `nz, ny, nx`: `{metrics['nz']}, {metrics['ny']}, {metrics['nx']}`",
        f"- Tracer range: `{float(metrics['tracer_min']):.3e}` to `{float(metrics['tracer_max']):.3e}`",
        f"- Tracer mean: `{float(metrics['tracer_mean']):.3e}`",
        "",
        "## Tracer Extent",
        "",
        "| Threshold | Cells | x range (kpc) | y range (kpc) | z range (kpc) |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for threshold in ("1e-03", "5e-03", "1e-02"):
        count = metrics.get(f"tracer_cells_gt_{threshold}", "0")
        if int(float(count)) > 0:
            xr = f"{float(metrics[f'tracer_x_min_gt_{threshold}']):.3g} to {float(metrics[f'tracer_x_max_gt_{threshold}']):.3g}"
            yr = f"{float(metrics[f'tracer_y_min_gt_{threshold}']):.3g} to {float(metrics[f'tracer_y_max_gt_{threshold}']):.3g}"
            zr = f"{float(metrics[f'tracer_z_min_gt_{threshold}']):.3g} to {float(metrics[f'tracer_z_max_gt_{threshold}']):.3g}"
        else:
            xr = yr = zr = "-"
        lines.append(f"| `{threshold}` | {count} | {xr} | {yr} | {zr} |")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Mid-plane maps, full domain: `{map_path.name}`",
            f"- Mid-plane maps, central zoom: `{zoom_map_path.name}`",
            f"- Axis profiles: `{profile_path.name}`",
            "",
            "This is an early-segment run-health diagnostic, not a science measurement.",
            "",
        ]
    )
    path = output_dir / "c_hi_quicklook_summary.md"
    path.write_text("\n".join(lines))
    return path


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics(args.input_dir / "summary_metrics.csv")
    time_myr = float(metrics["time_code"]) / CODE_TIME_PER_MYR
    map_path = plot_maps(args.input_dir, args.output_dir, args.label, time_myr, "", zoom=False)
    zoom_map_path = plot_maps(
        args.input_dir,
        args.output_dir,
        args.label,
        time_myr,
        "_central_zoom",
        zoom=True,
    )
    profile_path = plot_axis_profile(args.input_dir, args.output_dir, args.label, time_myr)
    summary_path = write_summary(
        args.output_dir,
        args.label,
        metrics,
        map_path,
        zoom_map_path,
        profile_path,
    )
    print(f"wrote {map_path}")
    print(f"wrote {zoom_map_path}")
    print(f"wrote {profile_path}")
    print(f"wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
