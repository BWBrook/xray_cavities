#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plutokore as pk

BASE = Path(
    os.environ.get(
        "JET_SETUP_TINY_3D_BASE",
        str(Path.home() / "work/pluto-onboarding/jet_setup_tiny_3d_cart"),
    )
)
RESULTS = BASE / "results"
PLOTS = BASE / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)


def load(index: int):
    return pk.simulations.load_timestep_data(
        index,
        str(RESULTS),
        suppress_output=True,
        mmap=True,
        datatype="double",
    )


def field(sim, *names: str) -> np.ndarray:
    for name in names:
        if hasattr(sim, name):
            return np.asarray(getattr(sim, name))
    raise AttributeError(names)


def orient_xyz(sim, arr: np.ndarray) -> np.ndarray:
    nx, ny, nz = len(sim.x1), len(sim.x2), len(sim.x3)
    if arr.shape == (nz, ny, nx):
        return np.transpose(arr, (2, 1, 0))
    if arr.shape == (nx, ny, nz):
        return arr
    raise ValueError(f"unexpected shape {arr.shape}; expected {(nz, ny, nx)} or {(nx, ny, nz)}")


def main() -> None:
    nlast = pk.simulations.get_output_count(str(RESULTS))
    sim = load(nlast)
    rho = orient_xyz(sim, field(sim, "rho"))
    vx3 = orient_xyz(sim, field(sim, "vx3", "v3"))
    x = np.asarray(sim.x1)
    y = np.asarray(sim.x2)
    z = np.asarray(sim.x3)
    ix0 = int(np.nanargmin(np.abs(x)))
    iy0 = int(np.nanargmin(np.abs(y)))
    velocity_mask = np.abs(vx3) > 1.0e-3

    if np.any(velocity_mask):
        z_extent = float(np.nanmax(np.abs(z[np.any(np.any(velocity_mask, axis=0), axis=0)])))
        velocity_cells = int(np.sum(velocity_mask))
    else:
        z_extent = 0.0
        velocity_cells = 0

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8), constrained_layout=True)
    panels = [
        (axes[0, 0], z, x, np.log10(rho[:, iy0, :]), "log10 density, y=0", "x"),
        (axes[0, 1], z, y, np.log10(rho[ix0, :, :]), "log10 density, x=0", "y"),
        (axes[1, 0], z, x, vx3[:, iy0, :], "axial velocity, y=0", "x"),
        (axes[1, 1], z, y, vx3[ix0, :, :], "axial velocity, x=0", "y"),
    ]
    for ax, xx, yy, image, title, ylabel in panels:
        mesh = ax.pcolormesh(xx, yy, image, shading="auto", cmap="magma" if "density" in title else "RdBu_r")
        ax.set_title(title)
        ax.set_xlabel("z")
        ax.set_ylabel(ylabel)
        fig.colorbar(mesh, ax=ax, pad=0.01)
    fig.suptitle(f"Tiny 3D Cartesian jet-setup smoke, output {nlast}, t={float(sim.SimTime):.2f}", y=1.02)
    fig.savefig(PLOTS / "tiny_3d_cart_slices.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    metrics = {
        "final_output": nlast,
        "time": float(sim.SimTime),
        "shape": "x".join(map(str, rho.shape)),
        "rho_min": float(np.nanmin(rho)),
        "rho_max": float(np.nanmax(rho)),
        "max_abs_vx3": float(np.nanmax(np.abs(vx3))),
        "velocity_cells_gt_1e_minus_3": velocity_cells,
        "velocity_abs_z_extent": z_extent,
    }
    with (PLOTS / "tiny_3d_cart_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics))
        writer.writeheader()
        writer.writerow(metrics)
    (PLOTS / "tiny_3d_cart_summary.md").write_text(
        "# Tiny 3D Cartesian jet-setup Smoke Summary\n\n"
        f"- Final output: `{nlast}` at `t = {float(sim.SimTime):.3f}`\n"
        f"- Grid shape, x by y by z: `{metrics['shape']}`\n"
        f"- Density range: `{metrics['rho_min']:.3e}` to `{metrics['rho_max']:.3e}`\n"
        f"- Maximum absolute axial velocity: `{metrics['max_abs_vx3']:.3e}`\n"
        f"- Cells with `|vx3| > 1e-3`: `{velocity_cells}`\n"
        f"- Absolute z extent of the axial-velocity mask: `{z_extent:.3f}`\n"
        "\nThis is a geometry/build/output smoke test only, not a science-resolution run.\n"
    )
    print("[done] tiny 3D Cartesian analysis complete")
    for path in sorted(PLOTS.iterdir()):
        print(f"saved {path}")


if __name__ == "__main__":
    main()
