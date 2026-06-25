#!/usr/bin/env python3
"""Package Goal 016 refined-projection rerun comparison assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
DEFAULT_ASSET_DIR = ASSET_ROOT / "c_hi_refined_projection_viewing_rerun_2026-06-25"
DEFAULT_ACCEPTED = {
    "90deg": ASSET_ROOT / "c_hi_final_90deg_viewing_angle_broadening_2026-06-23" / "xraise_grid_90deg",
    "45deg": ASSET_ROOT / "c_hi_final_45deg_viewing_angle_broadening_2026-06-23" / "xraise_grid_45deg",
}
DEFAULT_STRIPING = (
    ASSET_ROOT / "c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24" / "striping_diagnostics.csv"
)
REFINED_DIRS = {
    "90deg": "xraise_grid_90deg_refined",
    "45deg": "xraise_grid_45deg_refined",
}
LAYER_FILES = {
    "raw_xray": "xray_1kev_raw_mjy_sr.tsv",
    "corrected_xray": "xray_1kev_xraise_corrected_mjy_sr.tsv",
    "correction_ratio": "xray_1kev_correction_ratio.tsv",
}
EXPECTED_ACCUMULATOR = "edge_overlap_uniform_cell_projection"
EMPTY_COLUMNS = [
    "view",
    "layer",
    "accepted_empty_columns",
    "accepted_empty_column_fraction",
    "accepted_positive_columns",
    "accepted_positive_mask_equal_to_raw",
    "refined_empty_columns",
    "refined_empty_column_fraction",
    "refined_positive_columns",
    "refined_positive_mask_equal_to_raw",
    "empty_columns_delta",
    "empty_column_fraction_delta",
    "assessment",
]
PROJECTION_COLUMNS = [
    "view",
    "view_angle_deg",
    "projected_accumulation",
    "sky_horizontal_bins",
    "sky_horizontal_min_kpc",
    "sky_horizontal_max_kpc",
    "raw_positive_cells",
    "raw_finite_cells",
    "raw_min_mjy_sr",
    "raw_max_mjy_sr",
    "raw_sum_mjy_sr_pixels",
    "corrected_positive_cells",
    "corrected_finite_cells",
    "corrected_min_mjy_sr",
    "corrected_max_mjy_sr",
    "corrected_sum_mjy_sr_pixels",
    "correction_ratio_positive_cells",
    "correction_ratio_finite_cells",
    "correction_ratio_min",
    "correction_ratio_max",
    "correction_ratio_sum",
]
SUMMARY_COLUMNS = [
    "view",
    "metric",
    "unit",
    "accepted_value",
    "refined_value",
    "absolute_delta",
    "relative_delta_fraction",
    "assessment",
]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_summary(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: empty summary")
    return {row["metric"]: row for row in rows}


def read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def read_matrix(path: Path) -> np.ndarray:
    matrix = np.loadtxt(path, delimiter="\t")
    if matrix.ndim != 2:
        raise ValueError(f"{path}: expected a two-dimensional matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{path}: non-finite values")
    return np.asarray(matrix, dtype=float)


def read_striping_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if row.get("view") in REFINED_DIRS and row.get("layer") in LAYER_FILES:
            out[(row["view"], row["layer"])] = row
    return out


def read_refined_empty_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        out[row["layer"]] = row
    return out


def parse_columns(matrix_shape: str) -> int:
    try:
        return int(matrix_shape.split("x", 1)[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(f"could not parse matrix column count from {matrix_shape!r}") from exc


def locate_product_root(path: Path) -> Path:
    if all((path / dirname).is_dir() for dirname in REFINED_DIRS.values()):
        return path
    candidates = [child for child in path.iterdir() if child.is_dir()]
    for candidate in candidates:
        if all((candidate / dirname).is_dir() for dirname in REFINED_DIRS.values()):
            return candidate
    raise FileNotFoundError(f"could not find refined product root under {path}")


def extract_archive(archive: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    resolved_target = target.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            member_target = (target / member.name).resolve()
            if os.path.commonpath([str(resolved_target), str(member_target)]) != str(resolved_target):
                raise ValueError(f"unsafe archive member path: {member.name}")
        tar.extractall(target, members=members, filter="data")
    return locate_product_root(target)


def refined_mask_matches(product_dir: Path) -> dict[str, str]:
    raw = read_matrix(product_dir / LAYER_FILES["raw_xray"])
    raw_mask = raw > 0.0
    out: dict[str, str] = {"raw_xray": "true"}
    for layer, filename in LAYER_FILES.items():
        if layer == "raw_xray":
            continue
        values = read_matrix(product_dir / filename)
        out[layer] = "true" if np.array_equal(values > 0.0, raw_mask) else "false"
    return out


def projection_metric_rows(product_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for view, dirname in REFINED_DIRS.items():
        product_dir = product_root / dirname
        metadata = read_json(product_dir / "xraise_grid_smoke_metadata.json")
        projection = metadata["projection"]
        accumulator = projection.get("projected_accumulation")
        if accumulator != EXPECTED_ACCUMULATOR:
            raise ValueError(f"{product_dir}: projected_accumulation={accumulator!r}")
        raw = metadata["raw_stats_mjy_sr"]
        corrected = metadata["corrected_stats_mjy_sr"]
        ratio = metadata["correction_ratio_stats"]
        rows.append(
            {
                "view": view,
                "view_angle_deg": f"{float(projection['view_angle_deg']):.16g}",
                "projected_accumulation": accumulator,
                "sky_horizontal_bins": int(projection["sky_horizontal_bins"]),
                "sky_horizontal_min_kpc": f"{float(projection['sky_horizontal_min_kpc']):.16g}",
                "sky_horizontal_max_kpc": f"{float(projection['sky_horizontal_max_kpc']):.16g}",
                "raw_positive_cells": int(raw["positive_cells"]),
                "raw_finite_cells": int(raw["finite_cells"]),
                "raw_min_mjy_sr": f"{float(raw['min']):.16g}",
                "raw_max_mjy_sr": f"{float(raw['max']):.16g}",
                "raw_sum_mjy_sr_pixels": f"{float(raw['sum']):.16g}",
                "corrected_positive_cells": int(corrected["positive_cells"]),
                "corrected_finite_cells": int(corrected["finite_cells"]),
                "corrected_min_mjy_sr": f"{float(corrected['min']):.16g}",
                "corrected_max_mjy_sr": f"{float(corrected['max']):.16g}",
                "corrected_sum_mjy_sr_pixels": f"{float(corrected['sum']):.16g}",
                "correction_ratio_positive_cells": int(ratio["positive_cells"]),
                "correction_ratio_finite_cells": int(ratio["finite_cells"]),
                "correction_ratio_min": f"{float(ratio['min']):.16g}",
                "correction_ratio_max": f"{float(ratio['max']):.16g}",
                "correction_ratio_sum": f"{float(ratio['sum']):.16g}",
            }
        )
    return rows


def empty_column_comparison_rows(product_root: Path, accepted_striping: Path) -> list[dict[str, Any]]:
    historical = read_striping_rows(accepted_striping)
    rows: list[dict[str, Any]] = []
    for view, dirname in REFINED_DIRS.items():
        product_dir = product_root / dirname
        metadata = read_json(product_dir / "xraise_grid_smoke_metadata.json")
        total_columns = int(metadata["projection"]["sky_horizontal_bins"])
        refined_empty = read_refined_empty_rows(product_dir / "refined_projection_empty_columns.csv")
        refined_mask_match = refined_mask_matches(product_dir)
        for layer in LAYER_FILES:
            accepted = historical[(view, layer)]
            accepted_empty = int(accepted["empty_column_count"])
            accepted_fraction = float(accepted["empty_column_fraction"])
            accepted_columns = parse_columns(accepted["matrix_shape"])
            refined_count = int(refined_empty[layer]["empty_columns"])
            refined_fraction = float(refined_empty[layer]["empty_column_fraction"])
            if accepted_empty > 0 and refined_count == 0:
                assessment = "empty_column_artifact_removed"
            elif refined_count < accepted_empty:
                assessment = "empty_column_artifact_reduced"
            elif refined_count == accepted_empty:
                assessment = "unchanged"
            else:
                assessment = "worse"
            rows.append(
                {
                    "view": view,
                    "layer": layer,
                    "accepted_empty_columns": accepted_empty,
                    "accepted_empty_column_fraction": f"{accepted_fraction:.16g}",
                    "accepted_positive_columns": accepted_columns - accepted_empty,
                    "accepted_positive_mask_equal_to_raw": accepted["positive_mask_equal_to_raw"],
                    "refined_empty_columns": refined_count,
                    "refined_empty_column_fraction": f"{refined_fraction:.16g}",
                    "refined_positive_columns": total_columns - refined_count,
                    "refined_positive_mask_equal_to_raw": refined_mask_match[layer],
                    "empty_columns_delta": refined_count - accepted_empty,
                    "empty_column_fraction_delta": f"{refined_fraction - accepted_fraction:.16g}",
                    "assessment": assessment,
                }
            )
    return rows


def scalar_assessment(metric: str, relative_delta: float) -> str:
    if metric.endswith("_sum") and abs(relative_delta) < 1.0e-12:
        return "conserved_within_roundoff"
    if "correction_ratio_positive_sum" == metric and relative_delta > 0.0:
        return "positive_pixel_support_expanded"
    if metric.endswith("_max") and abs(relative_delta) < 5.0e-3:
        return "small_bin_distribution_change"
    return "review"


def summary_comparison_rows(product_root: Path, accepted_dirs: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for view, dirname in REFINED_DIRS.items():
        accepted = read_summary(accepted_dirs[view] / "xraise_grid_smoke_summary.csv")
        refined = read_summary(product_root / dirname / "xraise_grid_smoke_summary.csv")
        for metric, accepted_row in accepted.items():
            if metric not in refined:
                continue
            accepted_value = float(accepted_row["value"])
            refined_value = float(refined[metric]["value"])
            delta = refined_value - accepted_value
            rel_delta = math.nan if accepted_value == 0.0 else delta / accepted_value
            rows.append(
                {
                    "view": view,
                    "metric": metric,
                    "unit": accepted_row["unit"],
                    "accepted_value": f"{accepted_value:.16g}",
                    "refined_value": f"{refined_value:.16g}",
                    "absolute_delta": f"{delta:.16g}",
                    "relative_delta_fraction": "nan" if math.isnan(rel_delta) else f"{rel_delta:.16g}",
                    "assessment": scalar_assessment(metric, 0.0 if math.isnan(rel_delta) else rel_delta),
                }
            )
    return rows


def provenance_rows(
    *,
    asset_dir: Path,
    archive: Path,
    stdout_path: Path,
    stderr_path: Path,
    product_root: Path,
) -> list[dict[str, str]]:
    meta90 = read_json(product_root / REFINED_DIRS["90deg"] / "xraise_grid_smoke_metadata.json")
    meta45 = read_json(product_root / REFINED_DIRS["45deg"] / "xraise_grid_smoke_metadata.json")
    rows = [
        ("pbs_job_id", "700044.kunanyi-ohpc"),
        ("pbs_job_name", "c_hi_xrefprj"),
        ("pbs_exit_status", "0"),
        ("pbs_walltime_used", "00:22:01"),
        ("remote_stage", "/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun"),
        (
            "remote_archive",
            "/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun/"
            "refined_projection_viewing_rerun_2026-06-25.tar.gz",
        ),
        (
            "remote_analysis_root",
            "/scratch/bwbrook/xray_cavities_analysis/2026-06-25-c-hi-refined-projection-viewing-rerun",
        ),
        ("input_h5", str(meta90["input_h5"])),
        ("timestep", str(meta90["timestep"])),
        ("local_archive", display_path(archive)),
        ("local_archive_sha256", sha256_file(archive)),
        ("local_stdout", display_path(stdout_path)),
        ("local_stdout_sha256", sha256_file(stdout_path)),
        ("local_stderr", display_path(stderr_path)),
        ("local_stderr_sha256", sha256_file(stderr_path)),
        ("local_stderr_bytes", str(stderr_path.stat().st_size)),
        ("projection.projected_accumulation.90deg", str(meta90["projection"]["projected_accumulation"])),
        ("projection.projected_accumulation.45deg", str(meta45["projection"]["projected_accumulation"])),
        ("product_bundle", display_path(asset_dir)),
    ]
    return [{"key": key, "value": value} for key, value in rows]


def build_metadata(
    *,
    archive: Path,
    stdout_path: Path,
    stderr_path: Path,
    projection_rows: list[dict[str, Any]],
    empty_rows: list[dict[str, Any]],
    scalar_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_view_layer = {(row["view"], row["layer"]): row for row in empty_rows}
    by_view_metric = {(row["view"], row["metric"]): row for row in scalar_rows}
    result_label = (
        "REFINED_PROJECTION_FIXES_EMPTY_COLUMN_FAILURE"
        if int(by_view_layer[("90deg", "corrected_xray")]["refined_empty_columns"]) == 0
        else "REFINED_PROJECTION_DOES_NOT_FIX_EMPTY_COLUMN_FAILURE"
    )
    views: dict[str, Any] = {}
    for projection_row in projection_rows:
        view = str(projection_row["view"])
        views[view] = {
            "view_angle_deg": float(projection_row["view_angle_deg"]),
            "projected_accumulation": projection_row["projected_accumulation"],
            "raw_xray_empty_columns": {
                "accepted": int(by_view_layer[(view, "raw_xray")]["accepted_empty_columns"]),
                "refined": int(by_view_layer[(view, "raw_xray")]["refined_empty_columns"]),
            },
            "corrected_xray_empty_columns": {
                "accepted": int(by_view_layer[(view, "corrected_xray")]["accepted_empty_columns"]),
                "refined": int(by_view_layer[(view, "corrected_xray")]["refined_empty_columns"]),
            },
            "correction_ratio_empty_columns": {
                "accepted": int(by_view_layer[(view, "correction_ratio")]["accepted_empty_columns"]),
                "refined": int(by_view_layer[(view, "correction_ratio")]["refined_empty_columns"]),
            },
            "raw_xray_sum_relative_delta": float(by_view_metric[(view, "raw_xray_sum")]["relative_delta_fraction"]),
            "corrected_xray_sum_relative_delta": float(
                by_view_metric[(view, "corrected_xray_sum")]["relative_delta_fraction"]
            ),
            "correction_ratio_positive_sum_relative_delta": float(
                by_view_metric[(view, "correction_ratio_positive_sum")]["relative_delta_fraction"]
            ),
        }
    return {
        "status": "complete_product",
        "result_label": result_label,
        "job": {
            "id": "700044.kunanyi-ohpc",
            "name": "c_hi_xrefprj",
            "exit_status": 0,
            "walltime": "00:22:01",
        },
        "archive_sha256": sha256_file(archive),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_sha256": sha256_file(stderr_path),
        "stderr_bytes": stderr_path.stat().st_size,
        "views": views,
        "caveat": (
            "This package validates a projection-method repair for existing-output C-HI views; "
            "it is not a publication-ready observable product."
        ),
    }


def build_package(
    *,
    asset_dir: Path,
    product_root: Path,
    archive: Path,
    stdout_path: Path,
    stderr_path: Path,
    accepted_dirs: dict[str, Path],
    accepted_striping: Path,
) -> dict[str, Any]:
    projection_rows = projection_metric_rows(product_root)
    empty_rows = empty_column_comparison_rows(product_root, accepted_striping)
    scalar_rows = summary_comparison_rows(product_root, accepted_dirs)
    provenance = provenance_rows(
        asset_dir=asset_dir,
        archive=archive,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        product_root=product_root,
    )
    metadata = build_metadata(
        archive=archive,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        projection_rows=projection_rows,
        empty_rows=empty_rows,
        scalar_rows=scalar_rows,
    )
    write_rows(asset_dir / "refined_projection_metrics.csv", projection_rows, PROJECTION_COLUMNS)
    write_rows(asset_dir / "empty_column_before_after.csv", empty_rows, EMPTY_COLUMNS)
    write_rows(asset_dir / "refined_vs_accepted_xray_summary.csv", scalar_rows, SUMMARY_COLUMNS)
    write_rows(asset_dir / "product_provenance.csv", provenance, ["key", "value"])
    (asset_dir / "refined_projection_viewing_rerun_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--remote-product-dir", type=Path)
    parser.add_argument(
        "--archive",
        type=Path,
        default=DEFAULT_ASSET_DIR / "remote_logs/refined_projection_viewing_rerun_2026-06-25.tar.gz",
    )
    parser.add_argument(
        "--stdout",
        type=Path,
        default=DEFAULT_ASSET_DIR / "remote_logs/c_hi_refined_projection_viewing_rerun.out",
    )
    parser.add_argument(
        "--stderr",
        type=Path,
        default=DEFAULT_ASSET_DIR / "remote_logs/c_hi_refined_projection_viewing_rerun.err",
    )
    parser.add_argument("--accepted-90-dir", type=Path, default=DEFAULT_ACCEPTED["90deg"])
    parser.add_argument("--accepted-45-dir", type=Path, default=DEFAULT_ACCEPTED["45deg"])
    parser.add_argument("--accepted-striping", type=Path, default=DEFAULT_STRIPING)
    args = parser.parse_args()

    accepted_dirs = {"90deg": args.accepted_90_dir, "45deg": args.accepted_45_dir}
    args.asset_dir.mkdir(parents=True, exist_ok=True)
    if args.remote_product_dir is not None:
        product_root = locate_product_root(args.remote_product_dir)
        metadata = build_package(
            asset_dir=args.asset_dir,
            product_root=product_root,
            archive=args.archive,
            stdout_path=args.stdout,
            stderr_path=args.stderr,
            accepted_dirs=accepted_dirs,
            accepted_striping=args.accepted_striping,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="goal016-refined-projection-") as temp_name:
            product_root = extract_archive(args.archive, Path(temp_name))
            metadata = build_package(
                asset_dir=args.asset_dir,
                product_root=product_root,
                archive=args.archive,
                stdout_path=args.stdout,
                stderr_path=args.stderr,
                accepted_dirs=accepted_dirs,
                accepted_striping=args.accepted_striping,
            )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
