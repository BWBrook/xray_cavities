#!/usr/bin/env python3
"""Build the preprocessed particle HDF5 expected by the GRAiLE/XRAiSE driver."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import plutokore as pk


def finite_stats(values: np.ndarray) -> dict[str, Any]:
    finite = np.asarray(values)[np.isfinite(values)]
    out: dict[str, Any] = {
        "finite_count": int(finite.size),
        "nan_count": int(np.size(values) - finite.size),
    }
    if finite.size:
        out.update(
            {
                "min": float(np.min(finite)),
                "max": float(np.max(finite)),
                "mean": float(np.mean(finite)),
            }
        )
    return out


def save_uncompressed_hdf5(
    particle_data: dict[str, np.ndarray],
    particle_times: np.ndarray,
    output_hdf5: Path,
) -> None:
    output_hdf5.parent.mkdir(parents=True, exist_ok=True)
    if output_hdf5.exists():
        output_hdf5.unlink()

    with h5py.File(output_hdf5, "w") as h5:
        group = h5.require_group("particle_data")
        for name, values in particle_data.items():
            group.create_dataset(
                name,
                data=np.asarray(values, dtype=np.float32),
                maxshape=[None] * values.ndim,
                chunks=True,
                compression="gzip",
                compression_opts=1,
                shuffle=True,
            )
        h5.create_dataset(
            "time",
            data=np.asarray(particle_times, dtype=np.float32),
            maxshape=[None],
            chunks=True,
            compression="gzip",
            compression_opts=1,
            shuffle=True,
        )


def write_summary(
    output_dir: Path,
    sim: pk.PlutoSimulation,
    particle_data: dict[str, np.ndarray],
    particle_times: np.ndarray,
    output_hdf5: Path,
) -> dict[str, Any]:
    field_summary: list[dict[str, Any]] = []
    for name, values in particle_data.items():
        row = {
            "field": name,
            "shape": "x".join(str(v) for v in values.shape),
            "dtype": str(values.dtype),
        }
        row.update(finite_stats(values))
        field_summary.append(row)

    metadata = {
        "simulation_directory": str(sim.directory),
        "output_hdf5": str(output_hdf5),
        "grid_outputs": int(sim.total_outputs),
        "particle_outputs": int(sim.particle_outputs),
        "particle_time_count": int(particle_times.shape[0]),
        "particle_time_min_code": float(np.nanmin(particle_times)),
        "particle_time_max_code": float(np.nanmax(particle_times)),
        "particle_time_min_myr": float(np.nanmin(particle_times * sim.unit_values.time.to("Myr").value)),
        "particle_time_max_myr": float(np.nanmax(particle_times * sim.unit_values.time.to("Myr").value)),
        "fields": field_summary,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "particle_hdf5_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )

    with (output_dir / "particle_hdf5_field_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "field",
                "shape",
                "dtype",
                "finite_count",
                "nan_count",
                "min",
                "max",
                "mean",
            ],
        )
        writer.writeheader()
        for row in field_summary:
            writer.writerow(row)

    with (output_dir / "particle_hdf5_summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["grid_outputs", sim.total_outputs, "index"])
        writer.writerow(["particle_outputs", sim.particle_outputs, "index"])
        writer.writerow(["particle_time_count", particle_times.shape[0], "outputs"])
        writer.writerow(["particle_time_max_code", metadata["particle_time_max_code"], "code_time"])
        writer.writerow(["particle_time_max_myr", metadata["particle_time_max_myr"], "Myr"])
        writer.writerow(["field_count", len(field_summary), "fields"])
        writer.writerow(["output_hdf5", output_hdf5, "path"])

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-hdf5", type=Path, required=True)
    parser.add_argument("--datatype", choices=["float", "double"], default="float")
    args = parser.parse_args()

    sim = pk.PlutoSimulation(
        simulation_name="C-HI",
        simulation_directory=args.sim_dir,
        simulation_description="C-HI particles HDF5 smoke",
        datatype=args.datatype,
        dimensions=3,
        file_format="HDF5",
    )
    print(sim)
    particle_data, particle_times = pk.particles.load_all_particles(sim)
    save_uncompressed_hdf5(particle_data, particle_times, args.output_hdf5)
    metadata = write_summary(args.output_dir, sim, particle_data, particle_times, args.output_hdf5)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
