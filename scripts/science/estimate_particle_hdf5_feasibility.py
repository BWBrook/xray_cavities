#!/usr/bin/env python3
"""Estimate feasibility of building a full plutokore particle-HDF5 cache."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import plutokore as pk


GIB = 1024**3


def as_int(value: Any) -> int:
    return int(float(value))


def write_metric_csv(path: Path, metrics: dict[str, tuple[Any, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        for name, (value, unit) in metrics.items():
            writer.writerow([name, value, unit])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--datatype", choices=["float", "double"], default="float")
    parser.add_argument(
        "--peak-multiplier",
        type=float,
        default=10.0,
        help=(
            "Safety multiplier from raw float64 matrix bytes to expected peak RSS. "
            "Earlier C-HI particle-HDF5 runs showed large overhead from Python, "
            "plutokore tables, compression, and temporary arrays."
        ),
    )
    parser.add_argument(
        "--max-memory-gib",
        type=float,
        default=128.0,
        help="Memory ceiling used for the build recommendation.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sim = pk.PlutoSimulation(
        simulation_name="C-HI",
        simulation_directory=args.sim_dir,
        simulation_description="C-HI full-grid final particle-HDF5 feasibility",
        datatype=args.datatype,
        dimensions=3,
        file_format="HDF5",
    )

    last_output_number = int(sim.particle_outputs)
    last_output = sim.load_particle_output(last_output_number)
    total_outputs = last_output_number + 1
    total_particles = as_int(last_output.id.max())

    field_rows: list[dict[str, Any]] = []
    total_field_width = 0
    for name, dim in zip(last_output.field_names, last_output.field_dim):
        width = as_int(dim)
        total_field_width += width
        elements = total_particles * total_outputs * width
        field_rows.append(
            {
                "field": str(name),
                "field_dim": width,
                "shape": f"{total_particles}x{total_outputs}"
                + (f"x{width}" if width != 1 else ""),
                "elements": elements,
                "raw_float64_gib": elements * 8 / GIB,
                "saved_float32_gib": elements * 4 / GIB,
            }
        )

    raw_float64_bytes = total_particles * total_outputs * total_field_width * 8
    saved_float32_bytes = total_particles * total_outputs * total_field_width * 4
    estimated_peak_bytes = raw_float64_bytes * args.peak_multiplier
    recommended = estimated_peak_bytes <= args.max_memory_gib * GIB

    particle_files = sorted(args.sim_dir.glob("particles.*.dbl"))
    metrics: dict[str, tuple[Any, str]] = {
        "simulation_directory": (str(args.sim_dir), "path"),
        "grid_outputs": (int(sim.total_outputs), "outputs"),
        "last_particle_output": (last_output_number, "index"),
        "particle_output_count": (total_outputs, "outputs"),
        "particle_file_count": (len(particle_files), "files"),
        "total_particles_from_final_id": (total_particles, "particles"),
        "field_count": (len(field_rows), "fields"),
        "total_field_width": (total_field_width, "scalar_field_equivalents"),
        "raw_float64_matrix_gib": (raw_float64_bytes / GIB, "GiB"),
        "saved_float32_matrix_gib": (saved_float32_bytes / GIB, "GiB"),
        "peak_multiplier": (args.peak_multiplier, "factor"),
        "estimated_peak_gib": (estimated_peak_bytes / GIB, "GiB"),
        "max_memory_gib": (args.max_memory_gib, "GiB"),
        "full_history_build_recommended": (str(recommended), "boolean"),
    }

    summary = {
        "metrics": {name: {"value": value, "unit": unit} for name, (value, unit) in metrics.items()},
        "fields": field_rows,
        "recommendation": (
            "BUILD_PLAUSIBLE_WITH_DECLARED_MEMORY"
            if recommended
            else "DO_NOT_BUILD_FULL_HISTORY_CACHE_WITH_CURRENT_APPROACH"
        ),
    }

    write_metric_csv(args.output_dir / "particle_hdf5_feasibility_summary.csv", metrics)
    with (args.output_dir / "particle_hdf5_feasibility_fields.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "field",
                "field_dim",
                "shape",
                "elements",
                "raw_float64_gib",
                "saved_float32_gib",
            ],
        )
        writer.writeheader()
        writer.writerows(field_rows)
    (args.output_dir / "particle_hdf5_feasibility_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
