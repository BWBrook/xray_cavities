#!/usr/bin/env python3
"""Build an honest morphology figure for the three endpoint cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm


ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path("docs/science/assets")
DATA_ROOT = Path(os.environ.get("XRAY_CAVITIES_DATA", ROOT)).expanduser()
GOAL039 = ROOT / ASSETS / "g_lo_endpoint_first_products_and_three_case_comparison_2026-07-12"
GOAL036 = DATA_ROOT / ASSETS / "c_lo_endpoint_first_products_2026-07-07/review_products"
GOAL039_DATA = DATA_ROOT / ASSETS / "g_lo_endpoint_first_products_and_three_case_comparison_2026-07-12"
CHI0 = DATA_ROOT / ASSETS / "c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid"
CHI_REFINED_ARCHIVE = DATA_ROOT / ASSETS / "c_hi_refined_projection_viewing_rerun_2026-06-25/remote_logs/refined_projection_viewing_rerun_2026-06-25.tar.gz"
ARRAY_NAME = "xray_1kev_xraise_corrected_mjy_sr.tsv"
LARGE_FILE_THRESHOLD = 5 * 1024 * 1024


def _require_bulk_data(paths: list[Path]) -> None:
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise SystemExit(
            f"Bulk simulation outputs not found under {DATA_ROOT} (first missing: {missing[0]}).\n"
            "They are not stored in git. Restore them with\n"
            "  rsync -a nectar:/data/share/xray_cavities/ <data-root>/\n"
            "and set XRAY_CAVITIES_DATA=<data-root> (default: the repository root); see README.md, section Bulk data."
        )


def _load_tsv(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t")
    if values.ndim != 2 or not np.isfinite(values).any():
        raise ValueError(f"invalid map: {path}")
    return values


def _load_chi_refined(view: str) -> np.ndarray:
    member = (
        "2026-06-25-c-hi-refined-projection-viewing-rerun/"
        f"xraise_grid_{view}_refined/{ARRAY_NAME}"
    )
    with tarfile.open(CHI_REFINED_ARCHIVE, "r:gz") as archive:
        handle = archive.extractfile(member)
        if handle is None:
            raise FileNotFoundError(member)
        return np.loadtxt(io.StringIO(handle.read().decode("utf-8")), delimiter="\t")


def _maps() -> dict[tuple[str, str], tuple[np.ndarray, str]]:
    _require_bulk_data(
        [CHI0 / ARRAY_NAME, CHI_REFINED_ARCHIVE]
        + [GOAL036 / f"xraise_grid_{view}" / ARRAY_NAME for view in ("0deg", "45deg", "90deg")]
        + [GOAL039_DATA / "review_products" / f"xraise_grid_{view}" / ARRAY_NAME for view in ("0deg", "45deg", "90deg")]
    )
    maps: dict[tuple[str, str], tuple[np.ndarray, str]] = {}
    maps[("C-HI", "0deg")] = (_load_tsv(CHI0 / ARRAY_NAME), str(CHI0 / ARRAY_NAME))
    for view in ("45deg", "90deg"):
        maps[("C-HI", view)] = (_load_chi_refined(view), f"{CHI_REFINED_ARCHIVE}::{view}")
    for view in ("0deg", "45deg", "90deg"):
        c_lo = GOAL036 / f"xraise_grid_{view}" / ARRAY_NAME
        g_lo = GOAL039_DATA / "review_products" / f"xraise_grid_{view}" / ARRAY_NAME
        maps[("C-LO", view)] = (_load_tsv(c_lo), str(c_lo))
        maps[("G-LO", view)] = (_load_tsv(g_lo), str(g_lo))
    return maps


def write_bundle_inventory(output_dir: Path) -> None:
    large_rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"large_file_inventory.csv", "local_asset_manifest.sha256"}:
            continue
        size = path.stat().st_size
        if size > LARGE_FILE_THRESHOLD:
            role = "immutable_remote_archive" if path.suffix == ".gz" else "parseable_endpoint_review_array"
            large_rows.append(
                {"size_bytes": size, "path": str(path.relative_to(output_dir)), "role": role}
            )
    with (output_dir / "large_file_inventory.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["size_bytes", "path", "role"])
        writer.writeheader()
        writer.writerows(large_rows)

    manifest = output_dir / "local_asset_manifest.sha256"
    lines = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path != manifest:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(output_dir)}")
    manifest.write_text("\n".join(lines) + "\n")


def build_comparison(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = GOAL039 / "review_products/three_case_endpoint_comparison.csv"
    rows = list(csv.DictReader(comparison_path.open()))
    by_panel = {(row["case"], row["view"]): row for row in rows}
    case_order = ("C-HI", "C-LO", "G-LO")
    views = ("0deg", "45deg", "90deg")
    if set(by_panel) != {(case, view) for case in case_order for view in views}:
        raise ValueError("comparison table does not cover all nine panels")
    maps = _maps()

    plt.rcParams.update({"font.size": 9, "axes.titleweight": "semibold"})
    fig, axes = plt.subplots(3, 3, figsize=(12.2, 11.4), constrained_layout=True)
    panels = []
    for row_index, case in enumerate(case_order):
        for column_index, view in enumerate(views):
            ax = axes[row_index, column_index]
            values, source = maps[(case, view)]
            positive = values[np.isfinite(values) & (values > 0)]
            if positive.size == 0:
                raise ValueError(f"no positive values for {case}/{view}")
            vmin = float(np.percentile(positive, 1.0))
            vmax = float(np.percentile(positive, 99.8))
            if vmax <= vmin:
                vmax = float(positive.max())
            ax.imshow(values, origin="lower", cmap="magma", norm=LogNorm(vmin=vmin, vmax=vmax), aspect="auto")
            ratio = float(by_panel[(case, view)]["corrected_sum_ratio_to_c_hi"])
            ax.set_title(f"{case} | {view} | sum/C-HI = {ratio:.3g}")
            ax.set_xticks([])
            ax.set_yticks([])
            if column_index == 0:
                ax.set_ylabel(case)
            panels.append(
                {
                    "case": case,
                    "view": view,
                    "source": source,
                    "shape": list(values.shape),
                    "positive_percentile_1": vmin,
                    "positive_percentile_99_8": vmax,
                    "corrected_sum_ratio_to_c_hi": ratio,
                }
            )

    fig.suptitle(
        "50 Myr endpoint corrected 1 keV X-ray morphology\n"
        "Independent log scaling per panel; use annotations/table for absolute comparison",
        fontsize=14,
    )
    figure_path = output_dir / "g_lo_three_case_endpoint_comparison.png"
    fig.savefig(figure_path, dpi=180, facecolor="white")
    plt.close(fig)

    metadata = {
        "status": "complete_product",
        "decision_label": "THREE_CASE_ENDPOINT_FIRST_PRODUCTS_COMPLETE",
        "case_order": list(case_order),
        "views": list(views),
        "map_scaling": "independent_per_panel_log_percentile",
        "scaling_warning": "panel colours are not on a common absolute scale",
        "quantitative_authority": "three_case_endpoint_comparison.csv",
        "comparison_table": str(comparison_path),
        "panels": panels,
    }
    (output_dir / "g_lo_three_case_endpoint_comparison_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    write_bundle_inventory(output_dir)
    print("status=complete_product")
    print("decision_label=THREE_CASE_ENDPOINT_FIRST_PRODUCTS_COMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=GOAL039)
    args = parser.parse_args()
    build_comparison(args.output_dir)


if __name__ == "__main__":
    main()
