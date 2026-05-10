#!/usr/bin/env python3
"""Run a minimal XRAiSE/PRAiSE particle-loss smoke from processed particles."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import astropy.units as u
import plutokore as pk


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("xraise", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stats(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    positive = finite[finite > 0]
    out: dict[str, Any] = {
        "finite_count": int(finite.size),
        "positive_count": int(positive.size),
        "nan_count": int(values.size - finite.size),
    }
    if finite.size:
        out.update({"min": float(finite.min()), "max": float(finite.max()), "mean": float(finite.mean())})
    if positive.size:
        out.update(
            {
                "positive_min": float(positive.min()),
                "positive_max": float(positive.max()),
                "positive_mean": float(positive.mean()),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-dir", type=Path, required=True)
    parser.add_argument("--particle-hdf5", type=Path, required=True)
    parser.add_argument("--xraise-py", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--grid-output", type=int, default=8)
    parser.add_argument("--frequency-hz", type=float, default=2.417990504024e17)
    parser.add_argument("--redshift", type=float, default=0.05)
    parser.add_argument("--losses", type=int, default=4)
    parser.add_argument("--particle-sampling-myr", type=float, default=0.01)
    parser.add_argument("--lst-index", type=int, default=2)
    parser.add_argument("--window-width", type=int, default=5)
    parser.add_argument("--smooth-order", type=int, default=3)
    parser.add_argument("--datatype", choices=["float", "double"], default="float")
    args = parser.parse_args()

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    xraise = load_module(args.xraise_py)
    sim = pk.PlutoSimulation(
        simulation_name="C-HI",
        simulation_directory=args.sim_dir,
        simulation_description="C-HI XRAiSE particle-loss smoke",
        datatype=args.datatype,
        dimensions=3,
        file_format="HDF5",
    )
    particle_data, particle_times = pk.particles.load_particle_data_hdf5(
        sim,
        args.particle_hdf5,
    )

    loss_dict = xraise.praise(
        sim=sim,
        part_data=particle_data,
        part_times=particle_times,
        max_output=args.grid_output,
        emit_outputs=[args.grid_output],
        redshift=[args.redshift],
        freqs=np.array([args.frequency_hz], dtype=float),
        eta=0.03,
        s=2.2,
        gmin=500,
        gmax=1.0e5,
        lst_index=args.lst_index,
        losses=[args.losses],
        window_width=args.window_width,
        smooth_order=args.smooth_order,
        particle_spacing=args.particle_sampling_myr * u.Myr,
        time_execution=True,
        output_system="grid",
    )

    key = "full" if args.losses == 4 else next(iter(loss_dict))
    entry = loss_dict[key][0]
    emissivity = entry["emis"].to_value(u.W / (u.Hz * u.m**3 * u.sr))
    part_output = int(entry["part_output"])
    grid_time_myr = float(sim.times[args.grid_output].to(u.Myr).value)
    particle_time_myr = float(particle_times[part_output] * sim.unit_values.time.to(u.Myr).value)

    np.save(out_dir / "particle_loss_factor.npy", emissivity)
    flat = emissivity[:, 0, 0]
    sample_count = min(1000, flat.shape[0])
    sample = np.column_stack((np.arange(sample_count), flat[:sample_count]))
    np.savetxt(
        out_dir / "particle_loss_factor_first1000.tsv",
        sample,
        delimiter="\t",
        header="particle_index\tloss_factor",
        comments="",
        fmt=["%d", "%.10e"],
    )

    metadata = {
        "sim_dir": str(args.sim_dir),
        "particle_hdf5": str(args.particle_hdf5),
        "xraise_py": str(args.xraise_py),
        "grid_output": args.grid_output,
        "grid_time_myr": grid_time_myr,
        "particle_output": part_output,
        "particle_time_myr": particle_time_myr,
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "loss_key": key,
        "losses": args.losses,
        "emissivity_shape": list(emissivity.shape),
        "particle_sampling_myr": args.particle_sampling_myr,
        "stats": stats(emissivity),
    }
    (out_dir / "particle_loss_smoke_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )

    with (out_dir / "particle_loss_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["grid_output", args.grid_output, "index"])
        writer.writerow(["grid_time_myr", grid_time_myr, "Myr"])
        writer.writerow(["particle_output", part_output, "index"])
        writer.writerow(["particle_time_myr", particle_time_myr, "Myr"])
        writer.writerow(["emissivity_shape", "x".join(str(v) for v in emissivity.shape), "array"])
        for name, value in metadata["stats"].items():
            writer.writerow([name, value, "loss_factor"])

    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
