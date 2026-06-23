#!/usr/bin/env python3
"""Build the Goal 012 final C-HI 90-degree viewing-angle package."""

from __future__ import annotations

import argparse
import importlib.util
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
BASE_HELPER = ROOT / "scripts/science/build_final_45deg_viewing_angle_broadening.py"
DEFAULT_GOAL005 = ASSET_ROOT / "c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
DEFAULT_GOAL011 = ASSET_ROOT / "c_hi_final_45deg_viewing_angle_broadening_2026-06-23"
DEFAULT_OUTPUT = ASSET_ROOT / "c_hi_final_90deg_viewing_angle_broadening_2026-06-23"
TARGET_VIEW_ANGLE_DEG = 90.0
TRIO_METRICS = {
    "raw_xray_max": "mJy sr^-1",
    "corrected_xray_max": "mJy sr^-1",
    "raw_xray_sum": "mJy sr^-1 pixels",
    "corrected_xray_sum": "mJy sr^-1 pixels",
    "correction_ratio_positive_max": "dimensionless",
    "correction_ratio_positive_sum": "dimensionless pixels",
}


def load_base_module():
    spec = importlib.util.spec_from_file_location("build_final_45deg_viewing_angle_broadening", BASE_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load helper module: {BASE_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_base_module()


def require_remote_stdout_markers(path: Path) -> dict[str, str]:
    text = path.read_text()
    for marker in ("hdf5_preflight=passed", "xray_90deg_validation=passed", "cavity_validation=passed", "finished_utc="):
        if marker not in text:
            raise ValueError(f"remote stdout missing marker: {marker}")
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line and not line.lstrip().startswith('"'):
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
        elif "final_90deg_viewing_angle_broadening_2026-06-23.tar.gz" in line:
            parts = line.split()
            if len(parts) >= 2 and len(parts[0]) == 64:
                out["summary_archive_sha256"] = parts[0]
    return out


def comparison_rows_90(baseline_summary: dict[str, float], target_summary: dict[str, float]) -> list[dict[str, Any]]:
    rows = []
    for metric, unit in TRIO_METRICS.items():
        baseline = baseline_summary[metric]
        target = target_summary[metric]
        rows.append(
            {
                "metric": metric,
                "value_0deg": baseline,
                "value_90deg": target,
                "ratio_90deg_to_0deg": target / baseline,
                "unit": unit,
                "interpretation": "projection diagnostic; pixel sums are not luminosity integrals",
            }
        )
    return rows


def trio_comparison_rows(
    baseline_summary: dict[str, float],
    angle45_summary: dict[str, float],
    angle90_summary: dict[str, float],
) -> list[dict[str, Any]]:
    rows = []
    for metric, unit in TRIO_METRICS.items():
        value_0 = baseline_summary[metric]
        value_45 = angle45_summary[metric]
        value_90 = angle90_summary[metric]
        rows.append(
            {
                "metric": metric,
                "value_0deg": value_0,
                "value_45deg": value_45,
                "value_90deg": value_90,
                "ratio_45deg_to_0deg": value_45 / value_0,
                "ratio_90deg_to_0deg": value_90 / value_0,
                "ratio_90deg_to_45deg": value_90 / value_45,
                "unit": unit,
                "interpretation": "projection diagnostic; pixel sums are not luminosity integrals",
            }
        )
    return rows


def read_view_payload(xraise_dir: Path, *, axis_name: str) -> dict[str, Any]:
    x_path = xraise_dir / ("x_kpc.tsv" if axis_name == "x" else "u_kpc.tsv")
    z_path = xraise_dir / "z_kpc.tsv"
    xray_path = xraise_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv"
    tracer_path = xraise_dir / "tracer_max_los.tsv"
    axis = base.read_vector(x_path)
    z = base.read_vector(z_path)
    xray = base.read_positive_matrix(xray_path)
    tracer = base.read_matrix(tracer_path)
    if xray.shape != (z.size, axis.size):
        raise ValueError(f"{xray_path}: shape does not match axes")
    if tracer.shape != (z.size, axis.size):
        raise ValueError(f"{tracer_path}: shape does not match axes")
    return {"axis": axis, "z": z, "xray": xray, "tracer": tracer}


def plot_trio(
    *,
    output_png: Path,
    goal005_dir: Path,
    goal011_dir: Path,
    output_dir: Path,
    boundary_90: Path,
) -> None:
    views = [
        {
            "title": "Accepted 0 deg",
            "xlabel": "x (kpc)",
            "axis_field": "x_kpc",
            "boundary": goal005_dir / "cavity_stub/cavity_ellipse_boundary_0deg.tsv",
            "payload": read_view_payload(goal005_dir / "xraise_grid", axis_name="x"),
        },
        {
            "title": "Accepted 45 deg",
            "xlabel": "u (kpc)",
            "axis_field": "u_kpc",
            "boundary": goal011_dir / "cavity_stub/cavity_ellipse_boundary_45deg.tsv",
            "payload": read_view_payload(goal011_dir / "xraise_grid_45deg", axis_name="u"),
        },
        {
            "title": "New 90 deg",
            "xlabel": "u (kpc)",
            "axis_field": "u_kpc",
            "boundary": boundary_90,
            "payload": read_view_payload(output_dir / "xraise_grid_90deg", axis_name="u"),
        },
    ]
    xray_logs = [base.log10_positive(view["payload"]["xray"]) for view in views]
    vmin, vmax = base.robust_limits(*xray_logs)
    tracer_vmax = float(max(np.nanmax(view["payload"]["tracer"]) for view in views))
    tracer_vmax = max(tracer_vmax, base.TRACER_THRESHOLD)
    xray_cmap = plt.get_cmap("magma").copy()
    xray_cmap.set_bad(xray_cmap(0.12))

    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.2), constrained_layout=True)
    xray_mesh = None
    tracer_mesh = None
    for idx, view in enumerate(views):
        payload = view["payload"]
        axis = payload["axis"]
        z = payload["z"]
        x_edges = base.centres_to_edges(axis)
        z_edges = base.centres_to_edges(z)

        xray_mesh = axes[0, idx].pcolormesh(
            x_edges,
            z_edges,
            xray_logs[idx],
            shading="auto",
            cmap=xray_cmap,
            vmin=vmin,
            vmax=vmax,
        )
        base.add_tracer_contour(axes[0, idx], axis, z, payload["tracer"])
        base.add_boundary(axes[0, idx], view["boundary"], x_field=view["axis_field"])
        base.set_panel(axes[0, idx], title=f"{view['title']}: corrected 1 keV X-ray", xlabel=view["xlabel"])

        tracer_mesh = axes[1, idx].pcolormesh(
            x_edges,
            z_edges,
            payload["tracer"],
            shading="auto",
            cmap="viridis",
            vmin=0.0,
            vmax=tracer_vmax,
        )
        base.add_boundary(axes[1, idx], view["boundary"], x_field=view["axis_field"])
        base.set_panel(axes[1, idx], title=f"{view['title']}: max tracer along LOS", xlabel=view["xlabel"])

    fig.colorbar(xray_mesh, ax=axes[0, :], shrink=0.9, label="log10 corrected mJy sr$^{-1}$")
    fig.colorbar(tracer_mesh, ax=axes[1, :], shrink=0.9, label="max tracer")
    fig.suptitle("C-HI final endpoint 0/45/90 deg projection-sensitivity comparison", fontsize=13.5)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def build_package(*, goal005_dir: Path, goal011_dir: Path, output_dir: Path) -> dict[str, Any]:
    baseline_xraise = goal005_dir / "xraise_grid"
    angle45_xraise = goal011_dir / "xraise_grid_45deg"
    angle90_xraise = output_dir / "xraise_grid_90deg"
    target_cavity = output_dir / "cavity_stub"
    remote_logs = output_dir / "remote_logs"

    base.validate_xraise_metadata(baseline_xraise / "xraise_grid_smoke_metadata.json", expected_view_angle_deg=None)
    base.validate_xraise_metadata(angle45_xraise / "xraise_grid_smoke_metadata.json", expected_view_angle_deg=45.0)
    target_metadata = base.validate_xraise_metadata(
        angle90_xraise / "xraise_grid_smoke_metadata.json",
        expected_view_angle_deg=TARGET_VIEW_ANGLE_DEG,
    )

    baseline_summary = base.validate_xraise_summary(baseline_xraise / "xraise_grid_smoke_summary.csv")
    angle45_summary = base.validate_xraise_summary(angle45_xraise / "xraise_grid_smoke_summary.csv")
    angle90_summary = base.validate_xraise_summary(angle90_xraise / "xraise_grid_smoke_summary.csv")
    cavity_rows = base.read_rows(target_cavity / "cavity_stub_summary.csv")
    base.validate_cavity_rows(cavity_rows)

    remote_stdout = remote_logs / "c_hi_final_90deg_viewing_angle_broadening.out"
    remote_stderr = remote_logs / "c_hi_final_90deg_viewing_angle_broadening.err"
    remote_info = require_remote_stdout_markers(remote_stdout)
    if remote_stderr.stat().st_size != 0:
        raise ValueError(f"remote stderr is non-empty: {remote_stderr}")

    boundary_90 = target_cavity / "cavity_ellipse_boundary_90deg.tsv"
    base.write_rows(
        boundary_90,
        base.projected_boundary_rows(cavity_rows, view_angle_deg=TARGET_VIEW_ANGLE_DEG),
        delimiter="\t",
    )

    comparison_path = output_dir / "viewing_angle_comparison.csv"
    trio_path = output_dir / "viewing_angle_trio_comparison.csv"
    projection_path = output_dir / "projection_metrics.csv"
    energy_path = output_dir / "cavity_energy_convention.csv"
    provenance_path = output_dir / "product_provenance.csv"
    metadata_path = output_dir / "final_90deg_viewing_angle_metadata.json"
    summary_path = output_dir / "final_90deg_viewing_angle_summary.md"
    figure_path = output_dir / "c_hi_final_90deg_viewing_angle_broadening.png"

    base.write_rows(comparison_path, comparison_rows_90(baseline_summary, angle90_summary))
    base.write_rows(trio_path, trio_comparison_rows(baseline_summary, angle45_summary, angle90_summary))
    base.write_rows(projection_path, base.projection_metric_rows(cavity_rows, view_angle_deg=TARGET_VIEW_ANGLE_DEG))
    base.write_rows(energy_path, base.energy_rows(cavity_rows))
    plot_trio(
        output_png=figure_path,
        goal005_dir=goal005_dir,
        goal011_dir=goal011_dir,
        output_dir=output_dir,
        boundary_90=boundary_90,
    )

    archive = remote_logs / "final_90deg_viewing_angle_broadening_2026-06-23.tar.gz"
    provenance = base.provenance_rows(
        [
            (archive, "fetched_remote_archive", "Kunanyi stage archive"),
            (remote_stdout, "remote_stdout", "Kunanyi PBS stdout"),
            (remote_stderr, "remote_stderr", "Kunanyi PBS stderr"),
            (angle90_xraise / "xraise_grid_smoke_metadata.json", "xraise_90deg_metadata", "fetched archive"),
            (angle90_xraise / "xraise_grid_smoke_summary.csv", "xraise_90deg_summary", "fetched archive"),
            (angle90_xraise / "xray_1kev_xraise_corrected_mjy_sr.tsv", "xraise_90deg_corrected_map", "fetched archive"),
            (angle90_xraise / "tracer_max_los.tsv", "xraise_90deg_tracer_map", "fetched archive"),
            (target_cavity / "cavity_stub_summary.csv", "cavity_3d_summary", "fetched archive"),
            (boundary_90, "cavity_projected_90deg_boundary", "local package transform"),
            (goal011_dir / "viewing_angle_comparison.csv", "accepted_45deg_comparison", "accepted Goal 011 asset"),
            (baseline_xraise / "xraise_grid_smoke_summary.csv", "baseline_0deg_summary", "accepted Goal 005 asset"),
        ],
        root=ROOT,
    )
    base.write_rows(provenance_path, provenance)

    metadata = {
        "package": "c_hi_final_90deg_viewing_angle_broadening_2026-06-23",
        "status": "complete_product",
        "case": "C-HI",
        "endpoint": "final 50 Myr",
        "view_angles_deg": [0.0, 45.0, 90.0],
        "target_view_angle_deg": TARGET_VIEW_ANGLE_DEG,
        "remote_job_id": remote_info.get("jobid", "699822.kunanyi-ohpc"),
        "remote_stage": remote_info.get("stage_dir"),
        "remote_analysis_root": remote_info.get("analysis_root"),
        "remote_archive_sha256": remote_info.get("summary_archive_sha256", ""),
        "target_projection": target_metadata.get("projection"),
        "validation_markers": {
            "hdf5_preflight": "hdf5_preflight=passed" in remote_stdout.read_text(),
            "xray_90deg": "xray_90deg_validation=passed" in remote_stdout.read_text(),
            "cavity": "cavity_validation=passed" in remote_stdout.read_text(),
            "stderr_empty": remote_stderr.stat().st_size == 0,
        },
        "outputs": {
            "figure": base.display_path(figure_path),
            "viewing_angle_comparison": base.display_path(comparison_path),
            "viewing_angle_trio_comparison": base.display_path(trio_path),
            "projection_metrics": base.display_path(projection_path),
            "cavity_energy_convention": base.display_path(energy_path),
            "product_provenance": base.display_path(provenance_path),
            "projected_boundary_90deg": base.display_path(boundary_90),
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
                "# C-HI Final 90-Degree Viewing-Angle Broadening Summary",
                "",
                "Status: `complete_product`.",
                "",
                f"Remote job: `{metadata['remote_job_id']}`.",
                "",
                "The fetched 90-degree X-ray grid passed remote HDF5 preflight, X-ray validation,",
                "and cavity validation. Local packaging projects the 3D tracer-defined cavity",
                "ellipsoids into the 90-degree `u-z` sky plane for display and compares",
                "the result against accepted 0-degree and 45-degree products.",
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
    parser.add_argument("--goal005-dir", type=Path, default=DEFAULT_GOAL005)
    parser.add_argument("--goal011-dir", type=Path, default=DEFAULT_GOAL011)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_package(goal005_dir=args.goal005_dir, goal011_dir=args.goal011_dir, output_dir=args.output_dir)
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
