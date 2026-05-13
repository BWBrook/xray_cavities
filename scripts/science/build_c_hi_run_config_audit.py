#!/usr/bin/env python3
"""Build a compact configuration audit for the reduced-grid C-HI run."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / "build/science/kunanyi_stage_2026-05-08/"
    "c_hi_run_config_audit_inputs_2026-05-13"
)
DEFAULT_COMPACT = (
    ROOT
    / "build/science/kunanyi_stage_2026-05-08/"
    "c_hi_8mini_691422_compact_2026-05-13"
)
DEFAULT_OUTPUT = ROOT / "docs/science/assets/c_hi_run_configuration_audit_2026-05-13"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_pluto_ini(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        parts = line.split()
        if not parts:
            continue
        sections[current][parts[0]] = " ".join(parts[1:])
    return sections


def parse_grid(path: Path) -> dict[str, list[tuple[float, float]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    cursor = 0
    while cursor < len(lines) and (
        not lines[cursor].strip()
        or lines[cursor].lstrip().startswith("#")
    ):
        cursor += 1

    axes: dict[str, list[tuple[float, float]]] = {}
    for axis in ("X1", "X2", "X3"):
        n = int(lines[cursor].strip())
        cursor += 1
        cells: list[tuple[float, float]] = []
        for _ in range(n):
            parts = lines[cursor].split()
            cells.append((float(parts[1]), float(parts[2])))
            cursor += 1
        axes[axis] = cells
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
    return axes


def dx_near(cells: list[tuple[float, float]], coord: float) -> float:
    centers = np.array([(lo + hi) / 2.0 for lo, hi in cells])
    widths = np.array([hi - lo for lo, hi in cells])
    idx = int(np.argmin(np.abs(centers - coord)))
    return float(widths[idx])


def cell_center_near(cells: list[tuple[float, float]], coord: float) -> float:
    centers = np.array([(lo + hi) / 2.0 for lo, hi in cells])
    idx = int(np.argmin(np.abs(centers - coord)))
    return float(centers[idx])


def summarize_grid(axes: dict[str, list[tuple[float, float]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for axis, cells in axes.items():
        widths = np.array([hi - lo for lo, hi in cells], dtype=float)
        row: dict[str, Any] = {
            "axis": axis,
            "cells": len(cells),
            "min_kpc": cells[0][0],
            "max_kpc": cells[-1][1],
            "min_dx_kpc": float(widths.min()),
            "median_dx_kpc": float(np.median(widths)),
            "max_dx_kpc": float(widths.max()),
            "center_dx_kpc": dx_near(cells, 0.0),
            "edge_dx_kpc": float(max(widths[0], widths[-1])),
        }
        for coord in (10.0, 50.0, 100.0, 200.0, 250.0):
            if cells[0][0] <= coord <= cells[-1][1]:
                row[f"dx_near_{int(coord)}kpc"] = dx_near(cells, coord)
                row[f"center_near_{int(coord)}kpc"] = cell_center_near(cells, coord)
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def file_kind(path: str) -> str:
    name = Path(path).name
    if name.endswith(".flt.h5"):
        return "flt.h5"
    if name.endswith(".dbl.h5"):
        return "dbl.h5"
    if name.startswith("particles.") and name.endswith(".dbl"):
        return "particles.dbl"
    return "other"


def output_index(path: str) -> int | None:
    m = re.search(r"\.(\d+)\.", Path(path).name)
    if not m:
        return None
    return int(m.group(1))


def human_gb(num_bytes: float) -> str:
    return f"{num_bytes / 1.0e9:.2f} GB"


def summarize_outputs(path: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            item = {
                "path": row[0],
                "bytes": int(row[1]),
                "mtime": row[2] if len(row) > 2 else "",
                "index": output_index(row[0]),
            }
            grouped[file_kind(row[0])].append(item)

    rows: list[dict[str, Any]] = []
    for kind in ("flt.h5", "dbl.h5", "particles.dbl"):
        items = grouped.get(kind, [])
        if not items:
            continue
        indices = [item["index"] for item in items if item["index"] is not None]
        sizes = [item["bytes"] for item in items]
        rows.append(
            {
                "kind": kind,
                "count": len(items),
                "first_index": min(indices) if indices else "",
                "last_index": max(indices) if indices else "",
                "min_file_size_bytes": min(sizes),
                "max_file_size_bytes": max(sizes),
                "typical_file_size": human_gb(float(np.median(sizes))),
                "total_size": human_gb(float(sum(sizes))),
            }
        )
    return rows


def parse_output_times(path: Path, code_time_per_myr: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            idx = int(parts[0])
            code_time = float(parts[1])
            step = int(parts[3])
        except ValueError:
            continue
        rows.append(
            {
                "index": idx,
                "time_myr": code_time / code_time_per_myr,
                "step": step,
            }
        )
    return rows


def parse_pbs_log(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {
            "PBS_JOBID",
            "PBS_QUEUE",
            "CASE_ID",
            "CASE_VARIANT",
            "CASE_CONFIG_DIR",
            "WORKDIR",
            "MODULES",
            "HDF5_DIR",
            "PLUTO_MAXTIME_HOURS",
            "mpicc",
            "mpirun",
            "NRANKS",
            "RUN_KIND",
            "RUN_ARGS",
        }:
            out[key] = value
    return out


def plot_grid(axes: dict[str, list[tuple[float, float]]], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    for axis, cells in axes.items():
        centers = np.array([(lo + hi) / 2.0 for lo, hi in cells])
        widths = np.array([hi - lo for lo, hi in cells])
        ax.plot(np.abs(centers), widths, lw=1.8, label=axis)
    ax.set_yscale("log")
    ax.set_xlabel("absolute coordinate (kpc)")
    ax.set_ylabel("cell width (kpc)")
    ax.set_title("Reduced-grid C-HI cell width profile")
    ax.grid(True, which="both", alpha=0.25)
    for coord in (2.5, 10.0, 200.0, 250.0):
        ax.axvline(coord, color="#777777", lw=0.8, ls="--", alpha=0.55)
    ax.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--compact-dir", type=Path, default=DEFAULT_COMPACT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    config_dir = args.input_dir / "config"
    metadata_dir = args.input_dir / "metadata"
    pbs_log = args.compact_dir / "pbs/c_hi_8node_mini_production.out"

    manifest = json.loads(read_text(config_dir / "case_manifest.json"))
    pluto = parse_pluto_ini(config_dir / "pluto.ini")
    axes = parse_grid(config_dir / "grid.out")
    grid_rows = summarize_grid(axes)
    output_rows = summarize_outputs(metadata_dir / "output_file_sizes.tsv")
    code_time_per_myr = float(manifest["time_conversion"]["code_time_per_myr"])
    flt_times = parse_output_times(config_dir / "flt.h5.out", code_time_per_myr)
    dbl_times = parse_output_times(config_dir / "dbl.h5.out", code_time_per_myr)
    pbs = parse_pbs_log(pbs_log)

    summary = {
        "case": manifest["case"],
        "variant": manifest["variant"],
        "environment": manifest["environment"],
        "grid_manifest": manifest["grid"],
        "simulation_defaults": manifest["simulation_defaults"],
        "truth_conventions": manifest["truth_conventions"],
        "time_conversion": manifest["time_conversion"],
        "pluto_grid": pluto["Grid"],
        "pluto_static_outputs": pluto["Static Grid Output"],
        "pluto_particles": pluto["Particles"],
        "pluto_parameters": pluto["Parameters"],
        "pbs": pbs,
        "final_flt": flt_times[-1],
        "final_dbl": dbl_times[-1],
        "grid_summary": grid_rows,
        "output_summary": output_rows,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "grid_resolution_summary.csv", grid_rows)
    write_csv(args.output_dir / "output_file_size_summary.csv", output_rows)
    write_csv(args.output_dir / "flt_output_times.csv", flt_times)
    write_csv(args.output_dir / "dbl_output_times.csv", dbl_times)
    plot_grid(axes, args.output_dir / "c_hi_reduced_grid_cell_widths.png")
    (args.output_dir / "run_config_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output_dir}")


if __name__ == "__main__":
    main()
