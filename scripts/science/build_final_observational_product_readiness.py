#!/usr/bin/env python3
"""Build the Goal 007 final C-HI observational-product readiness package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
DEFAULT_GOAL005 = ASSET_ROOT / "c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
DEFAULT_GOAL003 = ASSET_ROOT / "c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11"
DEFAULT_GOAL002 = ASSET_ROOT / "c_hi_fullgrid_final_sparse_praise_loss_2026-06-11"
DEFAULT_OUTPUT = ASSET_ROOT / "c_hi_final_observational_product_readiness_2026-06-16"
TRACER_THRESHOLD = 5.0e-3
GOAL005_MAIN_X_HALF_WIDTH_KPC = 45.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_vector(path: Path) -> np.ndarray:
    values = np.loadtxt(path)
    if values.ndim != 1 or values.size < 2:
        raise ValueError(f"{path} must contain a one-dimensional vector")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path} contains non-finite coordinates")
    return np.asarray(values, dtype=float)


def read_positive_matrix(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t")
    if values.ndim != 2:
        raise ValueError(f"{path} must contain a two-dimensional matrix")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path} contains non-finite values")
    if np.nanmax(values) <= 0.0:
        raise ValueError(f"{path} must contain positive values")
    return np.asarray(values, dtype=float)


def centres_to_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("need at least two coordinate centres")
    mids = 0.5 * (values[:-1] + values[1:])
    first = values[0] - (mids[0] - values[0])
    last = values[-1] + (values[-1] - mids[-1])
    return np.concatenate([[first], mids, [last]])


def log10_positive(values: np.ndarray) -> np.ndarray:
    out = np.full(values.shape, np.nan, dtype=float)
    mask = np.isfinite(values) & (values > 0.0)
    out[mask] = np.log10(values[mask])
    return out


def boxcar_mean(values: np.ndarray, width: int) -> np.ndarray:
    if width < 3 or width % 2 == 0:
        raise ValueError("boxcar width must be an odd integer >= 3")
    radius = width // 2
    padded = np.pad(values, ((radius, radius), (radius, radius)), mode="edge")
    cumsum = np.pad(padded, ((1, 0), (1, 0)), mode="constant").cumsum(axis=0).cumsum(axis=1)
    total = cumsum[width:, width:] - cumsum[:-width, width:] - cumsum[width:, :-width] + cumsum[:-width, :-width]
    return total / float(width * width)


def robust_limits(values: np.ndarray, *, lower: float = 1.0, upper: float = 99.5) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("cannot calculate limits for an all-non-finite array")
    lo, hi = np.percentile(finite, [lower, upper])
    if math.isclose(float(lo), float(hi)):
        hi = lo + 1.0
    return float(lo), float(hi)


def symmetric_limit(values: np.ndarray, *, percentile: float = 99.0) -> float:
    finite = np.abs(values[np.isfinite(values)])
    if finite.size == 0:
        raise ValueError("cannot calculate symmetric limit for an all-non-finite array")
    limit = float(np.percentile(finite, percentile))
    return limit if limit > 0.0 else 1.0


def add_cavity_boundaries(ax: plt.Axes, cavity_boundary: Path) -> None:
    colours = {"negative_z": "#1f77b4", "positive_z": "#d62728"}
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in read_rows(cavity_boundary, delimiter="\t"):
        grouped.setdefault(row["side"], []).append((float(row["x_kpc"]), float(row["z_kpc"])))
    for side, points in grouped.items():
        coords = np.asarray(points, dtype=float)
        if coords.size:
            ax.plot(coords[:, 0], coords[:, 1], color=colours.get(side, "black"), lw=1.2, alpha=0.95)


def add_tracer_contour(ax: plt.Axes, x: np.ndarray, z: np.ndarray, tracer: np.ndarray, threshold: float) -> None:
    mask = np.where(tracer >= threshold, 1.0, 0.0)
    if np.nanmin(mask) < 0.5 < np.nanmax(mask):
        ax.contour(x, z, mask, levels=[0.5], colors=["#00bcd4"], linewidths=0.7, alpha=0.8)


def set_panel_geometry(ax: plt.Axes, *, title: str, xlim: tuple[float, float], zlim: tuple[float, float]) -> None:
    ax.set_title(title, fontsize=10.5, pad=6)
    ax.set_xlabel("x (kpc)")
    ax.set_ylabel("z (kpc)")
    ax.set_xlim(*xlim)
    ax.set_ylim(*zlim)
    ax.set_aspect("equal", adjustable="box")


def plot_product(
    *,
    output_png: Path,
    x: np.ndarray,
    z: np.ndarray,
    xray_log10: np.ndarray,
    tracer: np.ndarray,
    residual: np.ndarray,
    cavity_boundary: Path,
    wide_xlim: tuple[float, float],
    wide_zlim: tuple[float, float],
    focus_xlim: tuple[float, float],
    focus_zlim: tuple[float, float],
    tracer_threshold: float,
) -> None:
    x_edges = centres_to_edges(x)
    z_edges = centres_to_edges(z)
    xray_vmin, xray_vmax = robust_limits(xray_log10, lower=0.5, upper=99.7)
    residual_limit = symmetric_limit(residual, percentile=99.0)

    fig = plt.figure(figsize=(11.2, 8.8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0])
    wide_ax = fig.add_subplot(grid[:, 0])
    focus_ax = fig.add_subplot(grid[0, 1])
    residual_ax = fig.add_subplot(grid[1, 1])

    wide_mesh = wide_ax.pcolormesh(
        x_edges,
        z_edges,
        xray_log10,
        shading="auto",
        cmap="magma",
        vmin=xray_vmin,
        vmax=xray_vmax,
    )
    add_tracer_contour(wide_ax, x, z, tracer, tracer_threshold)
    add_cavity_boundaries(wide_ax, cavity_boundary)
    set_panel_geometry(wide_ax, title="Wide-field 1 keV X-ray context", xlim=wide_xlim, zlim=wide_zlim)
    fig.colorbar(wide_mesh, ax=wide_ax, shrink=0.82, label="log10 mJy sr$^{-1}$")

    focus_mesh = focus_ax.pcolormesh(
        x_edges,
        z_edges,
        xray_log10,
        shading="auto",
        cmap="magma",
        vmin=xray_vmin,
        vmax=xray_vmax,
    )
    add_tracer_contour(focus_ax, x, z, tracer, tracer_threshold)
    add_cavity_boundaries(focus_ax, cavity_boundary)
    set_panel_geometry(focus_ax, title="Cavity-focused X-ray detail", xlim=focus_xlim, zlim=focus_zlim)
    fig.colorbar(focus_mesh, ax=focus_ax, shrink=0.8, label="log10 mJy sr$^{-1}$")

    residual_mesh = residual_ax.pcolormesh(
        x_edges,
        z_edges,
        residual,
        shading="auto",
        cmap="coolwarm",
        vmin=-residual_limit,
        vmax=residual_limit,
    )
    add_tracer_contour(residual_ax, x, z, tracer, tracer_threshold)
    add_cavity_boundaries(residual_ax, cavity_boundary)
    set_panel_geometry(residual_ax, title="Log X-ray residual", xlim=focus_xlim, zlim=focus_zlim)
    fig.colorbar(residual_mesh, ax=residual_ax, shrink=0.8, label="log10 residual")

    fig.suptitle("C-HI final endpoint observational-product readiness", fontsize=13)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def row_for_file(path: Path, *, role: str, source: str) -> dict[str, Any]:
    return {
        "role": role,
        "source": source,
        "path": str(path),
        "sha256": sha256_file(path),
    }


def build_provenance_rows(goal005_dir: Path, goal003_dir: Path, goal002_dir: Path) -> list[dict[str, Any]]:
    xraise_dir = goal005_dir / "xraise_grid"
    cavity_dir = goal005_dir / "cavity_stub"
    return [
        row_for_file(xraise_dir / "x_kpc.tsv", role="x_axis", source="Goal 005 local asset"),
        row_for_file(xraise_dir / "z_kpc.tsv", role="z_axis", source="Goal 005 local asset"),
        row_for_file(
            xraise_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv",
            role="corrected_xray_surface_brightness",
            source="Goal 005 local asset",
        ),
        row_for_file(xraise_dir / "tracer_max_los.tsv", role="tracer_overlay", source="Goal 005 local asset"),
        row_for_file(
            xraise_dir / "xraise_grid_smoke_metadata.json",
            role="xray_metadata",
            source="Goal 005 local asset",
        ),
        row_for_file(
            cavity_dir / "cavity_ellipse_boundary_0deg.tsv",
            role="tracer_defined_cavity_boundary_overlay",
            source="Goal 005 local asset",
        ),
        row_for_file(
            cavity_dir / "cavity_stub_summary.csv",
            role="cavity_stub_summary",
            source="Goal 005 local asset",
        ),
        row_for_file(
            goal005_dir / "final_xray_cavity_alignment_lobes.csv",
            role="accepted_cavity_truth_radio_scalars",
            source="Goal 005 local asset",
        ),
        row_for_file(
            goal003_dir / "bridge_external_loss_volume_coupled/sparse_particle_radio_lobe_summary.csv",
            role="particle_emissivity_radio_diagnostic",
            source="Goal 003 local asset",
        ),
        row_for_file(
            goal002_dir / "sparse_praise_loss_table.csv",
            role="selected_id_sparse_praise_loss_table",
            source="Goal 002 local asset",
        ),
    ]


def build_topology_rows(*, tracer_midplane_connected: bool) -> list[dict[str, Any]]:
    return [
        {
            "aspect": "xray_readiness",
            "status": "ready_for_review_not_method_freeze",
            "evidence": "Wide-field and residual panels expose more shell/cavity context than the Goal 005 narrow plot.",
            "limitation": "No new observational X-ray cavity fit is performed in Goal 007.",
            "recommendation": "Send to Patrick-agent for product-readiness review before broadening.",
        },
        {
            "aspect": "topology_convention",
            "status": "connected_envelope_vs_two_tracer_lobes_requires_review",
            "evidence": "The existing method reports two tracer-defined north/south ellipsoids; Patrick-agent notes the plotted X-ray shell/cavity may read as visually connected.",
            "limitation": "The current ellipses are diagnostic overlays from tracer/hydro extents, not X-ray-fitted observational cavities.",
            "recommendation": "Treat connected-envelope versus separate-lobe topology as an explicit review decision.",
        },
        {
            "aspect": "tracer_midplane_connection",
            "status": "connected" if tracer_midplane_connected else "not_connected_in_midplane_band",
            "evidence": "Derived from the accepted tracer_max_los map using tracer >= 5e-3 within |z| <= 5 kpc.",
            "limitation": "Tracer connectivity is a hydro/tracer diagnostic, not direct X-ray evidence.",
            "recommendation": "Use only as an overlay/interpreter aid in the observational-product review.",
        },
        {
            "aspect": "xray_fit_status",
            "status": "not_implemented",
            "evidence": "Goal 005 cavity boundaries come from tracer-defined ellipsoids.",
            "limitation": "An observational X-ray cavity fit on the X-ray surface-brightness map remains missing.",
            "recommendation": "Make X-ray-based cavity fitting or a reviewed topology convention the next method goal if Patrick-agent holds.",
        },
    ]


def build_radio_rows() -> list[dict[str, Any]]:
    return [
        {
            "item": "sparse_praise_loss_table",
            "current_status": "selected-particle loss/emissivity diagnostic",
            "not_yet_validated_as": "radio surface-brightness observable",
            "next_requirement": "Preserve as provenance for future raytraced radio products.",
        },
        {
            "item": "particle_binned_150mhz_map",
            "current_status": "debug morphology and scalar comparator",
            "not_yet_validated_as": "beam-convolved or raytraced radio map",
            "next_requirement": "Generate full raytraced radio surface-brightness at two or more frequencies.",
        },
        {
            "item": "goal003_volume_coupled_l150",
            "current_status": "volume-coupled sparse scalar comparator",
            "not_yet_validated_as": "production radio observable",
            "next_requirement": "Use only as a scalar continuity check until radio raytracing is validated.",
        },
    ]


def build_package(
    *,
    goal005_dir: Path,
    goal003_dir: Path,
    goal002_dir: Path,
    output_dir: Path,
    contrast_boxcar_pixels: int = 41,
    focus_x_half_width_kpc: float = 90.0,
    focus_z_half_width_kpc: float = 235.0,
) -> dict[str, Any]:
    xraise_dir = goal005_dir / "xraise_grid"
    cavity_dir = goal005_dir / "cavity_stub"
    x = read_vector(xraise_dir / "x_kpc.tsv")
    z = read_vector(xraise_dir / "z_kpc.tsv")
    xray = read_positive_matrix(xraise_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv")
    tracer = read_positive_matrix(xraise_dir / "tracer_max_los.tsv")
    if xray.shape != (z.size, x.size):
        raise ValueError(f"X-ray shape {xray.shape} does not match axes {(z.size, x.size)}")
    if tracer.shape != xray.shape:
        raise ValueError(f"tracer shape {tracer.shape} does not match X-ray shape {xray.shape}")

    xray_log10 = log10_positive(xray)
    smooth = boxcar_mean(xray_log10, contrast_boxcar_pixels)
    residual = xray_log10 - smooth

    wide_xlim = (float(x.min()), float(x.max()))
    wide_zlim = (float(z.min()), float(z.max()))
    focus_xlim = (
        max(float(x.min()), -focus_x_half_width_kpc),
        min(float(x.max()), focus_x_half_width_kpc),
    )
    focus_zlim = (
        max(float(z.min()), -focus_z_half_width_kpc),
        min(float(z.max()), focus_z_half_width_kpc),
    )
    wide_x_width = wide_xlim[1] - wide_xlim[0]
    goal005_x_width = 2.0 * GOAL005_MAIN_X_HALF_WIDTH_KPC
    if wide_x_width <= goal005_x_width:
        raise ValueError("wide-field product is not wider than the Goal 005 main X-ray view")

    output_dir.mkdir(parents=True, exist_ok=True)
    figure_path = output_dir / "c_hi_final_observational_product_readiness.png"
    plot_product(
        output_png=figure_path,
        x=x,
        z=z,
        xray_log10=xray_log10,
        tracer=tracer,
        residual=residual,
        cavity_boundary=cavity_dir / "cavity_ellipse_boundary_0deg.tsv",
        wide_xlim=wide_xlim,
        wide_zlim=wide_zlim,
        focus_xlim=focus_xlim,
        focus_zlim=focus_zlim,
        tracer_threshold=TRACER_THRESHOLD,
    )

    z_midplane = np.abs(z) <= 5.0
    tracer_midplane_connected = bool(np.any(tracer[z_midplane, :] >= TRACER_THRESHOLD))
    topology_rows = build_topology_rows(tracer_midplane_connected=tracer_midplane_connected)
    radio_rows = build_radio_rows()
    provenance_rows = build_provenance_rows(goal005_dir, goal003_dir, goal002_dir)
    write_rows(output_dir / "xray_topology_readiness.csv", topology_rows)
    write_rows(output_dir / "radio_observable_status.csv", radio_rows)
    write_rows(output_dir / "product_provenance.csv", provenance_rows)

    metadata = {
        "product": "c_hi_final_observational_product_readiness",
        "date": "2026-06-16",
        "snapshot": "50 Myr final C-HI endpoint",
        "timestep": "Timestep_51",
        "projection_angle": "0 deg, projected along simulation y axis",
        "xray_map_file": str(xraise_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv"),
        "tracer_file": str(xraise_dir / "tracer_max_los.tsv"),
        "cavity_boundary_file": str(cavity_dir / "cavity_ellipse_boundary_0deg.tsv"),
        "figure_file": str(figure_path),
        "wide_field_fov_kpc": {
            "x_min": wide_xlim[0],
            "x_max": wide_xlim[1],
            "z_min": wide_zlim[0],
            "z_max": wide_zlim[1],
            "x_width": wide_x_width,
            "goal005_main_x_width": goal005_x_width,
        },
        "focus_fov_kpc": {
            "x_min": focus_xlim[0],
            "x_max": focus_xlim[1],
            "z_min": focus_zlim[0],
            "z_max": focus_zlim[1],
        },
        "image_stretch": {
            "surface_brightness": "log10(corrected 1 keV mJy sr^-1), robust 0.5-99.7 percentile color limits",
            "contrast": "log10(corrected X-ray) minus boxcar-smoothed log10(corrected X-ray)",
        },
        "contrast_method": {
            "name": "boxcar_unsharp_residual",
            "boxcar_pixels": contrast_boxcar_pixels,
            "residual_units": "log10 mJy sr^-1 residual",
        },
        "tracer_threshold": f"{TRACER_THRESHOLD:.0e}",
        "overlay_statement": "Tracer contours and cavity ellipses are diagnostic overlays; the ellipses are not X-ray-fitted cavities.",
        "topology_statement": "Ready for Patrick-agent review; current evidence should be read as connected-envelope versus two-tracer-lobe topology unresolved for observational fitting.",
        "radio_diagnostic_limitation": "Sparse PRAiSE/particle-binned radio products remain particle-emissivity diagnostics, not validated radio observables.",
        "recommended_next_goal": "full raytraced radio surface-brightness at two or more frequencies plus an X-ray-based cavity/topology fitting method if Patrick-agent continues HOLD",
        "ready_for_patrick_review": True,
        "provenance_rows": len(provenance_rows),
        "topology_rows": len(topology_rows),
        "radio_status_rows": len(radio_rows),
    }
    (output_dir / "observational_product_readiness_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal005-dir", type=Path, default=DEFAULT_GOAL005)
    parser.add_argument("--goal003-dir", type=Path, default=DEFAULT_GOAL003)
    parser.add_argument("--goal002-dir", type=Path, default=DEFAULT_GOAL002)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contrast-boxcar-pixels", type=int, default=41)
    parser.add_argument("--focus-x-half-width-kpc", type=float, default=90.0)
    parser.add_argument("--focus-z-half-width-kpc", type=float, default=235.0)
    args = parser.parse_args()
    metadata = build_package(
        goal005_dir=args.goal005_dir,
        goal003_dir=args.goal003_dir,
        goal002_dir=args.goal002_dir,
        output_dir=args.output_dir,
        contrast_boxcar_pixels=args.contrast_boxcar_pixels,
        focus_x_half_width_kpc=args.focus_x_half_width_kpc,
        focus_z_half_width_kpc=args.focus_z_half_width_kpc,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
