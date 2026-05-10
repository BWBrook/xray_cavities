#!/usr/bin/env python3
"""Compare C-HI particle radio smoke products from two NUMBA thread counts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


MATRIX_FILES = [
    "radio_150mhz_particle_loss_mjy_sr.tsv",
    "radio_150mhz_particle_lossless_mjy_sr.tsv",
    "radio_particle_count_map.tsv",
    "radio_particle_mean_loss_factor.tsv",
]
VECTOR_FILES = ["x_kpc.tsv", "z_kpc.tsv"]
TEXT_FILES = [
    "particle_radio_positions_0deg.tsv",
    "particle_radio_smoke_summary.csv",
    "particle_radio_lobe_summary.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_matrix(path: Path) -> np.ndarray:
    return np.loadtxt(path, delimiter="\t")


def max_relative_difference(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.maximum(np.maximum(np.abs(a), np.abs(b)), 1.0)
    return float(np.max(np.abs(a - b) / denom))


def compare_array(name: str, a: np.ndarray, b: np.ndarray, rtol: float) -> dict[str, str | float | int | bool]:
    if a.shape != b.shape:
        return {
            "product": name,
            "shape_threads1": "x".join(map(str, a.shape)),
            "shape_threads4": "x".join(map(str, b.shape)),
            "max_abs_diff": float("nan"),
            "max_rel_diff": float("nan"),
            "sum_abs_diff": float("nan"),
            "nonzero_diff_count": -1,
            "allclose": False,
        }
    diff = np.abs(a - b)
    return {
        "product": name,
        "shape_threads1": "x".join(map(str, a.shape)),
        "shape_threads4": "x".join(map(str, b.shape)),
        "max_abs_diff": float(diff.max()) if diff.size else 0.0,
        "max_rel_diff": max_relative_difference(a, b) if diff.size else 0.0,
        "sum_abs_diff": float(diff.sum()) if diff.size else 0.0,
        "nonzero_diff_count": int(np.count_nonzero(diff)),
        "allclose": bool(np.allclose(a, b, rtol=rtol, atol=0.0, equal_nan=True)),
    }


def read_metric_csv(path: Path) -> dict[str, tuple[float, str]]:
    out: dict[str, tuple[float, str]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[row["metric"]] = (float(row["value"]), row.get("unit", ""))
            except ValueError:
                continue
    return out


def read_lobe_csv(path: Path) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            side = row["side"]
            for key, value in row.items():
                if key == "side":
                    continue
                try:
                    out[(side, key)] = float(value)
                except (TypeError, ValueError):
                    continue
    return out


def compare_metric_dicts(
    label: str,
    a: dict[str | tuple[str, str], float | tuple[float, str]],
    b: dict[str | tuple[str, str], float | tuple[float, str]],
) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for key in sorted(set(a) & set(b), key=str):
        aval_raw = a[key]
        bval_raw = b[key]
        unit = ""
        aval = aval_raw
        bval = bval_raw
        if isinstance(aval_raw, tuple):
            aval = aval_raw[0]
            unit = aval_raw[1]
        if isinstance(bval_raw, tuple):
            bval = bval_raw[0]
            unit = unit or bval_raw[1]
        aval_f = float(aval)
        bval_f = float(bval)
        denom = max(abs(aval_f), abs(bval_f), 1.0)
        if isinstance(key, tuple):
            metric_name = ":".join(key)
        else:
            metric_name = key
        rows.append(
            {
                "source": label,
                "metric": metric_name,
                "threads1_value": aval_f,
                "threads4_value": bval_f,
                "abs_diff": abs(aval_f - bval_f),
                "rel_diff": abs(aval_f - bval_f) / denom,
                "unit": unit,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def log10_positive(values: np.ndarray) -> np.ndarray:
    out = np.full_like(values, np.nan, dtype=float)
    mask = np.isfinite(values) & (values > 0.0)
    out[mask] = np.log10(values[mask])
    return out


def plot_diff(threads1_dir: Path, threads4_dir: Path, output_png: Path) -> None:
    x = np.loadtxt(threads1_dir / "x_kpc.tsv")
    z = np.loadtxt(threads1_dir / "z_kpc.tsv")
    a = load_matrix(threads1_dir / "radio_150mhz_particle_loss_mjy_sr.tsv")
    b = load_matrix(threads4_dir / "radio_150mhz_particle_loss_mjy_sr.tsv")
    diff = b - a
    rel = np.divide(np.abs(diff), np.maximum(np.maximum(np.abs(a), np.abs(b)), 1.0))
    rel_log = np.full_like(rel, np.nan, dtype=float)
    rel_mask = rel > 0.0
    rel_log[rel_mask] = np.log10(rel[rel_mask])
    extent = [float(x.min()), float(x.max()), float(z.min()), float(z.max())]

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.8), constrained_layout=True)
    panels = [
        (axes[0, 0], log10_positive(a), "NUMBA 1 thread", "log10 mJy sr$^{-1}$", "magma"),
        (axes[0, 1], log10_positive(b), "NUMBA 4 threads", "log10 mJy sr$^{-1}$", "magma"),
        (axes[1, 0], diff, "4 threads - 1 thread", "mJy sr$^{-1}$", "coolwarm"),
        (axes[1, 1], rel_log, "Relative difference", "log10 rel diff", "viridis"),
    ]
    for ax, data, title, label, cmap_name in panels:
        cmap = plt.get_cmap(cmap_name).copy()
        cmap.set_bad("#f2f2f2")
        im = ax.imshow(data, origin="lower", extent=extent, aspect="equal", interpolation="nearest", cmap=cmap)
        cbar = fig.colorbar(im, ax=ax, shrink=0.84)
        cbar.set_label(label)
        ax.set_title(title)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        ax.set_xlim(-42, 42)
        ax.set_ylim(-48, 48)
    fig.suptitle("C-HI particle radio determinism check", fontsize=14)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads1-dir", type=Path, required=True)
    parser.add_argument("--threads4-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rtol", type=float, default=1.0e-10)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    array_rows = []
    for filename in MATRIX_FILES:
        array_rows.append(
            compare_array(
                filename,
                load_matrix(args.threads1_dir / filename),
                load_matrix(args.threads4_dir / filename),
                args.rtol,
            )
        )
    for filename in VECTOR_FILES:
        array_rows.append(
            compare_array(
                filename,
                np.loadtxt(args.threads1_dir / filename),
                np.loadtxt(args.threads4_dir / filename),
                args.rtol,
            )
        )

    metric_rows = []
    metric_rows.extend(
        compare_metric_dicts(
            "particle_radio_smoke_summary.csv",
            read_metric_csv(args.threads1_dir / "particle_radio_smoke_summary.csv"),
            read_metric_csv(args.threads4_dir / "particle_radio_smoke_summary.csv"),
        )
    )
    metric_rows.extend(
        compare_metric_dicts(
            "particle_radio_lobe_summary.csv",
            read_lobe_csv(args.threads1_dir / "particle_radio_lobe_summary.csv"),
            read_lobe_csv(args.threads4_dir / "particle_radio_lobe_summary.csv"),
        )
    )

    hashes = {
        "threads1": {filename: sha256(args.threads1_dir / filename) for filename in MATRIX_FILES + VECTOR_FILES + TEXT_FILES},
        "threads4": {filename: sha256(args.threads4_dir / filename) for filename in MATRIX_FILES + VECTOR_FILES + TEXT_FILES},
    }
    hash_rows = []
    for filename in MATRIX_FILES + VECTOR_FILES + TEXT_FILES:
        hash_rows.append(
            {
                "product": filename,
                "threads1_sha256": hashes["threads1"][filename],
                "threads4_sha256": hashes["threads4"][filename],
                "exact_match": hashes["threads1"][filename] == hashes["threads4"][filename],
            }
        )

    write_csv(
        args.output_dir / "determinism_array_diff.csv",
        array_rows,
        [
            "product",
            "shape_threads1",
            "shape_threads4",
            "max_abs_diff",
            "max_rel_diff",
            "sum_abs_diff",
            "nonzero_diff_count",
            "allclose",
        ],
    )
    write_csv(
        args.output_dir / "determinism_metric_diff.csv",
        metric_rows,
        ["source", "metric", "threads1_value", "threads4_value", "abs_diff", "rel_diff", "unit"],
    )
    write_csv(
        args.output_dir / "determinism_hashes.csv",
        hash_rows,
        ["product", "threads1_sha256", "threads4_sha256", "exact_match"],
    )

    max_array_rel = max(float(row["max_rel_diff"]) for row in array_rows)
    max_metric_rel = max(float(row["rel_diff"]) for row in metric_rows) if metric_rows else 0.0
    exact_hashes = all(row["exact_match"] for row in hash_rows)
    arrays_allclose = all(bool(row["allclose"]) for row in array_rows)
    passed = arrays_allclose and max_metric_rel <= args.rtol
    summary = {
        "threads1_dir": str(args.threads1_dir),
        "threads4_dir": str(args.threads4_dir),
        "rtol": args.rtol,
        "arrays_allclose": arrays_allclose,
        "exact_hashes": exact_hashes,
        "max_array_rel_diff": max_array_rel,
        "max_metric_rel_diff": max_metric_rel,
        "passed": passed,
        "note": "exact_hashes can be false if metadata contains path or runtime-specific text; pass is numeric.",
    }
    (args.output_dir / "determinism_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with (args.output_dir / "determinism_summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["arrays_allclose", arrays_allclose, "boolean"])
        writer.writerow(["exact_hashes", exact_hashes, "boolean"])
        writer.writerow(["max_array_rel_diff", max_array_rel, "relative"])
        writer.writerow(["max_metric_rel_diff", max_metric_rel, "relative"])
        writer.writerow(["passed", passed, "boolean"])

    plot_diff(args.threads1_dir, args.threads4_dir, args.output_dir / "c_hi_particle_radio_determinism.png")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
