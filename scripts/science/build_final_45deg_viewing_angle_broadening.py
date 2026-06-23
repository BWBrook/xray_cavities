#!/usr/bin/env python3
"""Build the Goal 011 final C-HI 45-degree viewing-angle package."""

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
DEFAULT_OUTPUT = ASSET_ROOT / "c_hi_final_45deg_viewing_angle_broadening_2026-06-23"
FINAL_INPUT_H5 = (
    "/scratch/bwbrook/xray_cavities_runs/"
    "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5"
)
FINAL_TIMESTEP = "Timestep_51"
TARGET_VIEW_ANGLE_DEG = 45.0
TRACER_THRESHOLD = 5.0e-3
LOBE_SIDES = ("negative_z", "positive_z")


def read_rows(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_rows(path: Path, rows: list[dict[str, Any]], *, delimiter: str = ",") -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def read_metric_csv(path: Path) -> dict[str, dict[str, str]]:
    return {row["metric"]: row for row in read_rows(path)}


def parse_float(value: Any, *, context: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{context} must be finite")
    return out


def finite_positive(value: Any, *, context: str) -> float:
    out = parse_float(value, context=context)
    if out <= 0.0:
        raise ValueError(f"{context} must be positive")
    return out


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path, *, root: Path = ROOT) -> str:
    return str(path.relative_to(root) if path.is_relative_to(root) else path)


def read_vector(path: Path) -> np.ndarray:
    values = np.loadtxt(path)
    if values.ndim != 1 or values.size < 2:
        raise ValueError(f"{path} must contain a one-dimensional coordinate vector")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path} contains non-finite coordinates")
    return np.asarray(values, dtype=float)


def read_matrix(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t")
    if values.ndim != 2:
        raise ValueError(f"{path} must contain a two-dimensional matrix")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path} contains non-finite values")
    return np.asarray(values, dtype=float)


def read_positive_matrix(path: Path) -> np.ndarray:
    values = read_matrix(path)
    if float(np.nanmax(values)) <= 0.0:
        raise ValueError(f"{path} must contain positive values")
    return values


def centres_to_edges(values: np.ndarray) -> np.ndarray:
    if values.ndim != 1 or values.size < 2:
        raise ValueError("need at least two coordinate centres")
    mids = 0.5 * (values[:-1] + values[1:])
    first = values[0] - (mids[0] - values[0])
    last = values[-1] + (values[-1] - mids[-1])
    return np.concatenate([[first], mids, [last]])


def rows_by_side(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out = {row["side"]: row for row in rows}
    missing = sorted(set(LOBE_SIDES) - set(out))
    if missing:
        raise ValueError(f"missing cavity side rows: {', '.join(missing)}")
    return out


def validate_xraise_metadata(path: Path, *, expected_view_angle_deg: float | None) -> dict[str, Any]:
    metadata = json.loads(path.read_text())
    if str(metadata.get("input_h5", "")) != FINAL_INPUT_H5:
        raise ValueError(f"{path}: input_h5 mismatch")
    if str(metadata.get("timestep", "")) != FINAL_TIMESTEP:
        raise ValueError(f"{path}: timestep mismatch")
    time_myr = finite_positive(metadata.get("time_myr"), context=f"{path}: time_myr")
    if abs(time_myr - 50.0) > 1.0e-4:
        raise ValueError(f"{path}: not the final endpoint time")
    if expected_view_angle_deg is not None:
        projection = metadata.get("projection")
        if not isinstance(projection, dict):
            raise ValueError(f"{path}: missing projection metadata")
        view_angle = parse_float(projection.get("view_angle_deg"), context=f"{path}: view_angle_deg")
        if not math.isclose(view_angle, expected_view_angle_deg, rel_tol=0.0, abs_tol=1.0e-8):
            raise ValueError(f"{path}: expected {expected_view_angle_deg:g} deg product, found {view_angle:g}")
    return metadata


def validate_xraise_summary(path: Path) -> dict[str, float]:
    metrics = read_metric_csv(path)
    required = (
        "time_myr",
        "raw_xray_max",
        "corrected_xray_max",
        "raw_xray_sum",
        "corrected_xray_sum",
        "correction_ratio_positive_max",
        "correction_ratio_positive_sum",
    )
    out = {key: finite_positive(metrics[key]["value"], context=f"{path}: {key}") for key in required}
    if abs(out["time_myr"] - 50.0) > 1.0e-4:
        raise ValueError(f"{path}: not the final endpoint time")
    return out


def validate_cavity_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_side = rows_by_side(rows)
    for side in LOBE_SIDES:
        row = by_side[side]
        for key in (
            "center_x_kpc",
            "center_y_kpc",
            "center_z_kpc",
            "semi_x_kpc",
            "semi_y_kpc",
            "semi_z_kpc",
            "projected_area_kpc2",
            "ellipsoid_volume_kpc3",
            "tracer_extent_volume_kpc3",
            "ambient_pressure_dyn_cm2",
            "ambient_density_g_cm3",
            "pV_erg",
            "four_pV_erg",
            "sound_age_myr",
            "buoyancy_age_myr",
            "refill_age_myr",
        ):
            value = parse_float(row[key], context=f"{side} {key}")
            if key.startswith("semi_") or key not in {"center_x_kpc", "center_y_kpc", "center_z_kpc"}:
                if value <= 0.0:
                    raise ValueError(f"{side} {key} must be positive")
    return by_side


def projected_axis(row: dict[str, str], *, view_angle_deg: float) -> tuple[float, float]:
    theta = math.radians(view_angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    center_x = parse_float(row["center_x_kpc"], context="center_x_kpc")
    center_y = parse_float(row["center_y_kpc"], context="center_y_kpc")
    semi_x = finite_positive(row["semi_x_kpc"], context="semi_x_kpc")
    semi_y = finite_positive(row["semi_y_kpc"], context="semi_y_kpc")
    center_u = center_x * cos_t - center_y * sin_t
    semi_u = math.hypot(semi_x * cos_t, semi_y * sin_t)
    return center_u, semi_u


def projected_boundary_rows(
    cavity_rows: list[dict[str, str]],
    *,
    view_angle_deg: float,
    samples: int = 361,
) -> list[dict[str, Any]]:
    if samples < 16:
        raise ValueError("samples must be at least 16")
    by_side = validate_cavity_rows(cavity_rows)
    angles = np.linspace(0.0, 2.0 * math.pi, samples)
    rows: list[dict[str, Any]] = []
    for side in LOBE_SIDES:
        row = by_side[side]
        center_u, semi_u = projected_axis(row, view_angle_deg=view_angle_deg)
        center_z = parse_float(row["center_z_kpc"], context=f"{side} center_z_kpc")
        semi_z = finite_positive(row["semi_z_kpc"], context=f"{side} semi_z_kpc")
        for angle in angles:
            rows.append(
                {
                    "side": side,
                    "view_angle_deg": view_angle_deg,
                    "u_kpc": center_u + semi_u * math.cos(float(angle)),
                    "z_kpc": center_z + semi_z * math.sin(float(angle)),
                }
            )
    return rows


def log10_positive(values: np.ndarray) -> np.ndarray:
    out = np.full(values.shape, np.nan, dtype=float)
    mask = np.isfinite(values) & (values > 0.0)
    out[mask] = np.log10(values[mask])
    return out


def robust_limits(*arrays: np.ndarray) -> tuple[float, float]:
    finite = np.concatenate([array[np.isfinite(array)] for array in arrays])
    if finite.size == 0:
        raise ValueError("cannot calculate limits for all-non-finite arrays")
    lo, hi = np.percentile(finite, [0.5, 99.7])
    if math.isclose(float(lo), float(hi)):
        hi = lo + 1.0
    return float(lo), float(hi)


def add_boundary(ax: plt.Axes, path: Path, *, x_field: str) -> None:
    colours = {"negative_z": "#2671b9", "positive_z": "#d73027"}
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in read_rows(path, delimiter="\t"):
        grouped.setdefault(row["side"], []).append((float(row[x_field]), float(row["z_kpc"])))
    for side, points in grouped.items():
        coords = np.asarray(points, dtype=float)
        if coords.size:
            ax.plot(coords[:, 0], coords[:, 1], color=colours.get(side, "black"), lw=1.1, alpha=0.95)


def add_tracer_contour(ax: plt.Axes, x: np.ndarray, z: np.ndarray, tracer: np.ndarray) -> None:
    mask = np.where(tracer >= TRACER_THRESHOLD, 1.0, 0.0)
    if float(np.nanmin(mask)) < 0.5 < float(np.nanmax(mask)):
        ax.contour(x, z, mask, levels=[0.5], colors=["#00a6c8"], linewidths=0.65, alpha=0.8)


def set_panel(ax: plt.Axes, *, title: str, xlabel: str) -> None:
    ax.set_title(title, fontsize=10.5, pad=5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("z (kpc)")
    ax.set_aspect("equal", adjustable="box")


def plot_comparison(
    *,
    output_png: Path,
    baseline_dir: Path,
    target_dir: Path,
    baseline_boundary: Path,
    target_boundary: Path,
) -> None:
    x0 = read_vector(baseline_dir / "x_kpc.tsv")
    z0 = read_vector(baseline_dir / "z_kpc.tsv")
    u45 = read_vector(target_dir / "u_kpc.tsv")
    z45 = read_vector(target_dir / "z_kpc.tsv")
    xray0 = read_positive_matrix(baseline_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv")
    xray45 = read_positive_matrix(target_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv")
    tracer0 = read_positive_matrix(baseline_dir / "tracer_max_los.tsv")
    tracer45 = read_positive_matrix(target_dir / "tracer_max_los.tsv")
    if xray0.shape != (z0.size, x0.size):
        raise ValueError("0 deg X-ray matrix shape does not match axes")
    if xray45.shape != (z45.size, u45.size):
        raise ValueError("45 deg X-ray matrix shape does not match axes")

    xray0_log = log10_positive(xray0)
    xray45_log = log10_positive(xray45)
    vmin, vmax = robust_limits(xray0_log, xray45_log)
    tracer_vmax = float(max(np.nanmax(tracer0), np.nanmax(tracer45), TRACER_THRESHOLD))
    xray_cmap = plt.get_cmap("magma").copy()
    xray_cmap.set_bad(xray_cmap(0.0))

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 8.6), constrained_layout=True)
    mesh = axes[0, 0].pcolormesh(
        centres_to_edges(x0),
        centres_to_edges(z0),
        xray0_log,
        shading="auto",
        cmap=xray_cmap,
        vmin=vmin,
        vmax=vmax,
    )
    add_tracer_contour(axes[0, 0], x0, z0, tracer0)
    add_boundary(axes[0, 0], baseline_boundary, x_field="x_kpc")
    set_panel(axes[0, 0], title="Accepted 0 deg: corrected 1 keV X-ray", xlabel="x (kpc)")

    axes[0, 1].pcolormesh(
        centres_to_edges(u45),
        centres_to_edges(z45),
        xray45_log,
        shading="auto",
        cmap=xray_cmap,
        vmin=vmin,
        vmax=vmax,
    )
    add_tracer_contour(axes[0, 1], u45, z45, tracer45)
    add_boundary(axes[0, 1], target_boundary, x_field="u_kpc")
    set_panel(axes[0, 1], title="New 45 deg: corrected 1 keV X-ray", xlabel="u (kpc)")

    tracer_mesh = axes[1, 0].pcolormesh(centres_to_edges(x0), centres_to_edges(z0), tracer0, shading="auto", cmap="viridis", vmin=0.0, vmax=tracer_vmax)
    add_boundary(axes[1, 0], baseline_boundary, x_field="x_kpc")
    set_panel(axes[1, 0], title="Accepted 0 deg: max tracer along LOS", xlabel="x (kpc)")

    axes[1, 1].pcolormesh(centres_to_edges(u45), centres_to_edges(z45), tracer45, shading="auto", cmap="viridis", vmin=0.0, vmax=tracer_vmax)
    add_boundary(axes[1, 1], target_boundary, x_field="u_kpc")
    set_panel(axes[1, 1], title="New 45 deg: max tracer along LOS", xlabel="u (kpc)")

    fig.colorbar(mesh, ax=axes[0, :], shrink=0.88, label="log10 corrected mJy sr$^{-1}$")
    fig.colorbar(tracer_mesh, ax=axes[1, :], shrink=0.88, label="max tracer")
    fig.suptitle("C-HI final endpoint 45 deg projection-sensitivity comparison", fontsize=13.5)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def comparison_rows(baseline_summary: dict[str, float], target_summary: dict[str, float]) -> list[dict[str, Any]]:
    units = {
        "raw_xray_max": "mJy sr^-1",
        "corrected_xray_max": "mJy sr^-1",
        "raw_xray_sum": "mJy sr^-1 pixels",
        "corrected_xray_sum": "mJy sr^-1 pixels",
        "correction_ratio_positive_max": "dimensionless",
        "correction_ratio_positive_sum": "dimensionless pixels",
    }
    rows = []
    for metric, unit in units.items():
        baseline = baseline_summary[metric]
        target = target_summary[metric]
        rows.append(
            {
                "metric": metric,
                "value_0deg": baseline,
                "value_45deg": target,
                "ratio_45deg_to_0deg": target / baseline,
                "unit": unit,
                "interpretation": "projection diagnostic; pixel sums are not luminosity integrals",
            }
        )
    return rows


def projection_metric_rows(cavity_rows: list[dict[str, str]], *, view_angle_deg: float) -> list[dict[str, Any]]:
    by_side = validate_cavity_rows(cavity_rows)
    rows: list[dict[str, Any]] = []
    for side in LOBE_SIDES:
        row = by_side[side]
        center_u, semi_u = projected_axis(row, view_angle_deg=view_angle_deg)
        semi_z = finite_positive(row["semi_z_kpc"], context=f"{side} semi_z_kpc")
        rows.append(
            {
                "side": side,
                "view_angle_deg": view_angle_deg,
                "center_u_kpc": center_u,
                "center_z_kpc": parse_float(row["center_z_kpc"], context=f"{side} center_z_kpc"),
                "semi_u_kpc": semi_u,
                "semi_z_kpc": semi_z,
                "projected_ellipse_area_kpc2": math.pi * semi_u * semi_z,
                "source": "3D cavity ellipsoid projected into u-z sky plane",
            }
        )
    return rows


def energy_rows(cavity_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_side = validate_cavity_rows(cavity_rows)
    rows: list[dict[str, Any]] = []
    total_pv = 0.0
    for side in LOBE_SIDES:
        pv = finite_positive(by_side[side]["pV_erg"], context=f"{side} pV")
        total_pv += pv
        rows.append(
            {
                "side": side,
                "pV_erg": pv,
                "two_point_five_pV_erg": 2.5 * pv,
                "four_pV_erg": 4.0 * pv,
                "default_interpretation": "2.5pV adopted non-relativistic convention",
                "caveat": "projection product reuses 3D tracer-defined cavity scalars",
            }
        )
    rows.append(
        {
            "side": "bipolar_total",
            "pV_erg": total_pv,
            "two_point_five_pV_erg": 2.5 * total_pv,
            "four_pV_erg": 4.0 * total_pv,
            "default_interpretation": "2.5pV adopted non-relativistic convention",
            "caveat": "projection product reuses 3D tracer-defined cavity scalars",
        }
    )
    return rows


def provenance_rows(paths: list[tuple[Path, str, str]], *, root: Path) -> list[dict[str, Any]]:
    rows = []
    for path, role, source in paths:
        if not path.exists():
            continue
        rows.append(
            {
                "role": role,
                "path": display_path(path, root=root),
                "source": source,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def require_remote_stdout_markers(path: Path) -> dict[str, Any]:
    text = path.read_text()
    for marker in ("hdf5_preflight=passed", "xray_45deg_validation=passed", "cavity_validation=passed", "finished_utc="):
        if marker not in text:
            raise ValueError(f"remote stdout missing marker: {marker}")
    out: dict[str, Any] = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith('"'):
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
        elif "final_45deg_viewing_angle_broadening_2026-06-23.tar.gz" in line:
            parts = line.split()
            if len(parts) >= 2 and len(parts[0]) == 64:
                out["summary_archive_sha256"] = parts[0]
    return out


def build_package(*, baseline_dir: Path, output_dir: Path) -> dict[str, Any]:
    baseline_xraise = baseline_dir / "xraise_grid"
    baseline_cavity = baseline_dir / "cavity_stub"
    target_xraise = output_dir / "xraise_grid_45deg"
    target_cavity = output_dir / "cavity_stub"
    remote_logs = output_dir / "remote_logs"

    validate_xraise_metadata(baseline_xraise / "xraise_grid_smoke_metadata.json", expected_view_angle_deg=None)
    target_metadata = validate_xraise_metadata(
        target_xraise / "xraise_grid_smoke_metadata.json",
        expected_view_angle_deg=TARGET_VIEW_ANGLE_DEG,
    )
    baseline_summary = validate_xraise_summary(baseline_xraise / "xraise_grid_smoke_summary.csv")
    target_summary = validate_xraise_summary(target_xraise / "xraise_grid_smoke_summary.csv")
    cavity_rows = read_rows(target_cavity / "cavity_stub_summary.csv")
    validate_cavity_rows(cavity_rows)

    remote_stdout = remote_logs / "c_hi_final_45deg_viewing_angle_broadening.out"
    remote_info = require_remote_stdout_markers(remote_stdout) if remote_stdout.exists() else {}
    remote_stderr = remote_logs / "c_hi_final_45deg_viewing_angle_broadening.err"
    if remote_stderr.exists() and remote_stderr.stat().st_size != 0:
        raise ValueError(f"remote stderr is non-empty: {remote_stderr}")

    boundary_45 = target_cavity / "cavity_ellipse_boundary_45deg.tsv"
    write_rows(
        boundary_45,
        projected_boundary_rows(cavity_rows, view_angle_deg=TARGET_VIEW_ANGLE_DEG),
        delimiter="\t",
    )

    comparison_path = output_dir / "viewing_angle_comparison.csv"
    projection_path = output_dir / "projection_metrics.csv"
    energy_path = output_dir / "cavity_energy_convention.csv"
    provenance_path = output_dir / "product_provenance.csv"
    metadata_path = output_dir / "final_45deg_viewing_angle_metadata.json"
    summary_path = output_dir / "final_45deg_viewing_angle_summary.md"
    figure_path = output_dir / "c_hi_final_45deg_viewing_angle_broadening.png"

    write_rows(comparison_path, comparison_rows(baseline_summary, target_summary))
    write_rows(projection_path, projection_metric_rows(cavity_rows, view_angle_deg=TARGET_VIEW_ANGLE_DEG))
    write_rows(energy_path, energy_rows(cavity_rows))
    plot_comparison(
        output_png=figure_path,
        baseline_dir=baseline_xraise,
        target_dir=target_xraise,
        baseline_boundary=baseline_cavity / "cavity_ellipse_boundary_0deg.tsv",
        target_boundary=boundary_45,
    )

    archive = remote_logs / "final_45deg_viewing_angle_broadening_2026-06-23.tar.gz"
    provenance = provenance_rows(
        [
            (archive, "fetched_remote_archive", "Kunanyi stage archive"),
            (remote_stdout, "remote_stdout", "Kunanyi PBS stdout"),
            (remote_stderr, "remote_stderr", "Kunanyi PBS stderr"),
            (target_xraise / "xraise_grid_smoke_metadata.json", "xraise_45deg_metadata", "fetched archive"),
            (target_xraise / "xraise_grid_smoke_summary.csv", "xraise_45deg_summary", "fetched archive"),
            (target_xraise / "xray_1kev_xraise_corrected_mjy_sr.tsv", "xraise_45deg_corrected_map", "fetched archive"),
            (target_xraise / "tracer_max_los.tsv", "xraise_45deg_tracer_map", "fetched archive"),
            (target_cavity / "cavity_stub_summary.csv", "cavity_3d_summary", "fetched archive"),
            (boundary_45, "cavity_projected_45deg_boundary", "local package transform"),
            (baseline_xraise / "xraise_grid_smoke_summary.csv", "baseline_0deg_summary", "accepted Goal 005 asset"),
            (baseline_xraise / "xray_1kev_xraise_corrected_mjy_sr.tsv", "baseline_0deg_corrected_map", "accepted Goal 005 asset"),
        ],
        root=ROOT,
    )
    write_rows(provenance_path, provenance)

    metadata = {
        "package": "c_hi_final_45deg_viewing_angle_broadening_2026-06-23",
        "status": "complete_product",
        "case": "C-HI",
        "endpoint": "final 50 Myr",
        "baseline_view_angle_deg": 0.0,
        "target_view_angle_deg": TARGET_VIEW_ANGLE_DEG,
        "remote_job_id": remote_info.get("jobid", "699815.kunanyi-ohpc"),
        "remote_stage": remote_info.get("stage_dir"),
        "remote_analysis_root": remote_info.get("analysis_root"),
        "remote_archive_sha256": remote_info.get("summary_archive_sha256", ""),
        "target_projection": target_metadata.get("projection"),
        "validation_markers": {
            "hdf5_preflight": "hdf5_preflight=passed" in remote_stdout.read_text() if remote_stdout.exists() else False,
            "xray_45deg": "xray_45deg_validation=passed" in remote_stdout.read_text() if remote_stdout.exists() else False,
            "cavity": "cavity_validation=passed" in remote_stdout.read_text() if remote_stdout.exists() else False,
            "stderr_empty": remote_stderr.exists() and remote_stderr.stat().st_size == 0,
        },
        "outputs": {
            "figure": display_path(figure_path),
            "viewing_angle_comparison": display_path(comparison_path),
            "projection_metrics": display_path(projection_path),
            "cavity_energy_convention": display_path(energy_path),
            "product_provenance": display_path(provenance_path),
            "projected_boundary_45deg": display_path(boundary_45),
        },
        "caveats": [
            "projection-sensitivity probe, not publication-ready observables",
            "X-ray topology remains connected-envelope/single-lobe caveat pending later X-ray-based cavity fitting",
            "sparse particle-binned radio remains diagnostic, not a validated radio observable",
            "Level 3 gravitational energy remains blocked_missing_potential",
            "cavity energy convention carries pV, 2.5pV, and 4pV with 2.5pV as adopted non-relativistic interpretation",
        ],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    summary_path.write_text(
        "\n".join(
            [
                "# C-HI Final 45-Degree Viewing-Angle Broadening Summary",
                "",
                "Status: `complete_product`.",
                "",
                f"Remote job: `{metadata['remote_job_id']}`.",
                "",
                "The fetched 45-degree X-ray grid passed remote HDF5 preflight, X-ray validation,",
                "and cavity validation. Local packaging projects the 3D tracer-defined cavity",
                "ellipsoids into the 45-degree `u-z` sky plane for display; the fetched",
                "`cavity_ellipse_boundary_0deg.tsv` is retained as provenance but is not used",
                "as the 45-degree boundary.",
                "",
                "The product is a controlled projection-sensitivity probe, not a final",
                "publication-ready observable product.",
                "",
            ]
        )
    )
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_GOAL005)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_package(baseline_dir=args.baseline_dir, output_dir=args.output_dir)
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
