#!/usr/bin/env python3
"""Stream a sparse PLUTO particle-output window without a dense HDF5 cache."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


CODE_TIME_PER_MYR = 306.6013937879523
FIELD_LIMIT = 128


@dataclass(frozen=True)
class ParticleHeader:
    field_names: list[str]
    field_dim: list[int]
    field_offsets: dict[str, int]
    nparticles: int
    time_code: float
    step_number: int | None
    total_width: int
    payload_offset: int


@dataclass
class ParticleOutput:
    index: int
    path: Path
    header: ParticleHeader
    data: np.memmap


def parse_header(path: Path) -> ParticleHeader:
    raw = path.read_bytes()[:32768].decode("ascii", errors="ignore")
    field_names: list[str] = []
    field_dim: list[int] = []
    nparticles: int | None = None
    time_code = float("nan")
    step_number: int | None = None
    endianity = "little"

    for line in raw.splitlines():
        if not line.startswith("#"):
            break
        parts = line.split()
        if len(parts) < 3:
            continue
        key = parts[1]
        if key == "field_names":
            field_names = parts[2:]
        elif key == "field_dim":
            field_dim = [int(value) for value in parts[2:]]
        elif key == "nparticles":
            nparticles = int(parts[-1])
        elif key == "time":
            time_code = float(parts[-1])
        elif key == "stepNumber":
            step_number = int(parts[-1])
        elif key == "endianity":
            endianity = parts[-1]

    if not field_names or not field_dim:
        raise ValueError(f"Could not parse particle fields from {path}")
    if len(field_names) != len(field_dim):
        raise ValueError(f"field_names/field_dim mismatch in {path}")
    if len(field_names) > FIELD_LIMIT:
        raise ValueError(f"Too many particle fields in {path}: {len(field_names)}")
    if nparticles is None:
        raise ValueError(f"Could not parse nparticles from {path}")
    if endianity != "little":
        raise ValueError(f"Unsupported particle endianity in {path}: {endianity}")

    field_offsets: dict[str, int] = {}
    offset = 0
    for name, width in zip(field_names, field_dim):
        field_offsets[name] = offset
        offset += width
    payload_offset = path.stat().st_size - nparticles * offset * 8
    if payload_offset < 0:
        raise ValueError(f"Computed negative payload offset for {path}")
    return ParticleHeader(
        field_names=field_names,
        field_dim=field_dim,
        field_offsets=field_offsets,
        nparticles=nparticles,
        time_code=time_code,
        step_number=step_number,
        total_width=offset,
        payload_offset=payload_offset,
    )


def particle_path(particle_dir: Path, output_index: int) -> Path:
    path = particle_dir / f"particles.{output_index:04d}.dbl"
    if path.exists():
        return path
    raise FileNotFoundError(path)


def read_particle_output(particle_dir: Path, output_index: int) -> ParticleOutput:
    path = particle_path(particle_dir, output_index)
    header = parse_header(path)
    data = np.memmap(
        path,
        dtype=np.dtype("<f8"),
        mode="r",
        offset=header.payload_offset,
        shape=(header.nparticles, header.total_width),
    )
    return ParticleOutput(index=output_index, path=path, header=header, data=data)


def column(output: ParticleOutput, field: str, component: int = 0) -> np.ndarray:
    if field not in output.header.field_offsets:
        raise KeyError(f"{output.path} missing field {field}")
    dim = output.header.field_dim[output.header.field_names.index(field)]
    if component >= dim:
        raise KeyError(f"{output.path} missing component {field}[{component}]")
    offset = output.header.field_offsets[field] + component
    return np.asarray(output.data[:, offset])


def candidate_mask(output: ParticleOutput, tracer_threshold: float) -> np.ndarray:
    ids = column(output, "id")
    tracer = column(output, "tracer")
    density = column(output, "density")
    pressure = column(output, "pressure")
    x = column(output, "x1")
    y = column(output, "x2")
    z = column(output, "x3")
    return (
        np.isfinite(ids)
        & np.isfinite(x)
        & np.isfinite(y)
        & np.isfinite(z)
        & np.isfinite(tracer)
        & np.isfinite(density)
        & np.isfinite(pressure)
        & (tracer >= tracer_threshold)
        & (density > 0.0)
        & (pressure > 0.0)
    )


def deterministic_cap(ids: np.ndarray, max_selected: int) -> list[int]:
    unique_ids = np.unique(np.asarray(ids, dtype=np.int64))
    if max_selected <= 0 or unique_ids.size <= max_selected:
        return [int(value) for value in unique_ids]
    pick = np.unique(np.linspace(0, unique_ids.size - 1, max_selected, dtype=np.int64))
    return [int(value) for value in unique_ids[pick]]


def finite_range(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.min(finite)), float(np.max(finite)))


def side_masks(z: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "negative_z": z < 0.0,
        "positive_z": z >= 0.0,
    }


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def select_target_ids(target: ParticleOutput, tracer_threshold: float, max_selected: int) -> tuple[list[int], int]:
    mask = candidate_mask(target, tracer_threshold)
    ids = column(target, "id")[mask]
    return deterministic_cap(ids, max_selected), int(mask.sum())


def scalar_value(output: ParticleOutput, row_index: int, field: str) -> float:
    return float(output.data[row_index, output.header.field_offsets[field]])


def selected_rows(output: ParticleOutput, selected_ids: list[int]) -> np.ndarray:
    ids = column(output, "id").astype(np.int64)
    return np.flatnonzero(np.isin(ids, np.asarray(selected_ids, dtype=np.int64)))


def output_summary(
    output: ParticleOutput,
    selected_row_indices: np.ndarray,
    selected_count: int,
    tracer_threshold: float,
    code_time_per_myr: float,
) -> dict:
    x = column(output, "x1")
    y = column(output, "x2")
    z = column(output, "x3")
    tinj = column(output, "tinj")
    tracer = column(output, "tracer")
    density = column(output, "density")
    pressure = column(output, "pressure")
    x_min, x_max = finite_range(x)
    y_min, y_max = finite_range(y)
    z_min, z_max = finite_range(z)
    tinj_min, tinj_max = finite_range(tinj / code_time_per_myr)
    tracer_min, tracer_max = finite_range(tracer)
    density_min, density_max = finite_range(density)
    pressure_min, pressure_max = finite_range(pressure)
    target_candidate_count = int(candidate_mask(output, tracer_threshold).sum())
    present = int(selected_row_indices.size)
    return {
        "output_index": output.index,
        "path": str(output.path),
        "time_code": float(output.header.time_code),
        "time_myr": float(output.header.time_code / code_time_per_myr),
        "stepNumber": output.header.step_number,
        "nparticles": output.header.nparticles,
        "target_candidate_count": target_candidate_count,
        "selected_present_count": present,
        "selected_missing_count": selected_count - present,
        "x_min_kpc": x_min,
        "x_max_kpc": x_max,
        "y_min_kpc": y_min,
        "y_max_kpc": y_max,
        "z_min_kpc": z_min,
        "z_max_kpc": z_max,
        "tinj_min_myr": tinj_min,
        "tinj_max_myr": tinj_max,
        "tracer_min": tracer_min,
        "tracer_max": tracer_max,
        "density_min": density_min,
        "density_max": density_max,
        "pressure_min": pressure_min,
        "pressure_max": pressure_max,
    }


def side_summary(output: ParticleOutput, selected_row_indices: np.ndarray) -> list[dict]:
    z = column(output, "x3")
    selected_mask = np.zeros(output.header.nparticles, dtype=bool)
    selected_mask[selected_row_indices] = True
    rows = []
    for side, mask in side_masks(z).items():
        side_z = z[mask]
        z_min, z_max = finite_range(side_z)
        rows.append(
            {
                "output_index": output.index,
                "side": side,
                "particle_count": int(mask.sum()),
                "selected_present_count": int(np.count_nonzero(mask & selected_mask)),
                "z_min_kpc": z_min,
                "z_max_kpc": z_max,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--particle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--end-index", type=int, required=True)
    parser.add_argument("--target-index", type=int, required=True)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-selected-ids", type=int, default=20000)
    parser.add_argument("--tracer-threshold", type=float, default=5.0e-3)
    parser.add_argument("--code-time-per-myr", type=float, default=CODE_TIME_PER_MYR)
    args = parser.parse_args()

    if args.stride <= 0:
        raise ValueError("--stride must be positive")
    if args.end_index < args.start_index:
        raise ValueError("--end-index must be >= --start-index")

    output_indices = list(range(args.start_index, args.end_index + 1, args.stride))
    if args.target_index not in output_indices:
        output_indices.append(args.target_index)
        output_indices = sorted(set(output_indices))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    target = read_particle_output(args.particle_dir, args.target_index)
    selected_ids, target_candidate_count = select_target_ids(
        target,
        args.tracer_threshold,
        args.max_selected_ids,
    )
    selected_id_set = set(selected_ids)
    selected_count = len(selected_ids)

    summary_rows: list[dict] = []
    side_rows: list[dict] = []
    lifecycle: dict[int, dict] = {
        particle_id: {
            "id": particle_id,
            "output_count": 0,
            "first_output": None,
            "last_output": None,
            "first_time_myr": None,
            "last_time_myr": None,
            "x_first_kpc": None,
            "y_first_kpc": None,
            "z_first_kpc": None,
            "x_last_kpc": None,
            "y_last_kpc": None,
            "z_last_kpc": None,
        }
        for particle_id in selected_ids
    }
    trajectory_rows = 0
    trajectory_path = args.output_dir / "particle_sparse_window_trajectory.tsv"
    with trajectory_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "output_index",
                "time_code",
                "time_myr",
                "id",
                "x_kpc",
                "y_kpc",
                "z_kpc",
                "vx1",
                "vx2",
                "vx3",
                "tinj_myr",
                "age_myr",
                "tracer",
                "density",
                "pressure",
            ]
        )
        for output_index in output_indices:
            output = read_particle_output(args.particle_dir, output_index)
            indices = selected_rows(output, selected_ids)
            summary_rows.append(
                output_summary(
                    output,
                    indices,
                    selected_count,
                    args.tracer_threshold,
                    args.code_time_per_myr,
                )
            )
            side_rows.extend(side_summary(output, indices))
            time_myr = float(output.header.time_code / args.code_time_per_myr)
            for row_index in indices:
                particle_id = int(scalar_value(output, row_index, "id"))
                if particle_id not in selected_id_set:
                    continue
                x = scalar_value(output, row_index, "x1")
                y = scalar_value(output, row_index, "x2")
                z = scalar_value(output, row_index, "x3")
                tinj_myr = scalar_value(output, row_index, "tinj") / args.code_time_per_myr
                age_myr = time_myr - tinj_myr
                vx1 = scalar_value(output, row_index, "vx1")
                vx2 = scalar_value(output, row_index, "vx2")
                vx3 = scalar_value(output, row_index, "vx3")
                tracer = scalar_value(output, row_index, "tracer")
                density = scalar_value(output, row_index, "density")
                pressure = scalar_value(output, row_index, "pressure")
                writer.writerow(
                    [
                        output.index,
                        float(output.header.time_code),
                        time_myr,
                        particle_id,
                        x,
                        y,
                        z,
                        vx1,
                        vx2,
                        vx3,
                        tinj_myr,
                        age_myr,
                        tracer,
                        density,
                        pressure,
                    ]
                )
                state = lifecycle[particle_id]
                if state["output_count"] == 0:
                    state["first_output"] = output.index
                    state["first_time_myr"] = time_myr
                    state["x_first_kpc"] = x
                    state["y_first_kpc"] = y
                    state["z_first_kpc"] = z
                state["output_count"] += 1
                state["last_output"] = output.index
                state["last_time_myr"] = time_myr
                state["x_last_kpc"] = x
                state["y_last_kpc"] = y
                state["z_last_kpc"] = z
                trajectory_rows += 1

    lifecycle_rows: list[dict] = []
    for particle_id in selected_ids:
        state = lifecycle[particle_id]
        count = int(state["output_count"])
        dx = float(state["x_last_kpc"] - state["x_first_kpc"]) if count else float("nan")
        dy = float(state["y_last_kpc"] - state["y_first_kpc"]) if count else float("nan")
        dz = float(state["z_last_kpc"] - state["z_first_kpc"]) if count else float("nan")
        lifecycle_rows.append(
            {
                **state,
                "present_fraction": count / len(output_indices),
                "displacement_kpc": math.sqrt(dx * dx + dy * dy + dz * dz) if count else float("nan"),
            }
        )

    write_csv(
        args.output_dir / "particle_sparse_window_summary.csv",
        summary_rows,
        [
            "output_index",
            "path",
            "time_code",
            "time_myr",
            "stepNumber",
            "nparticles",
            "target_candidate_count",
            "selected_present_count",
            "selected_missing_count",
            "x_min_kpc",
            "x_max_kpc",
            "y_min_kpc",
            "y_max_kpc",
            "z_min_kpc",
            "z_max_kpc",
            "tinj_min_myr",
            "tinj_max_myr",
            "tracer_min",
            "tracer_max",
            "density_min",
            "density_max",
            "pressure_min",
            "pressure_max",
        ],
    )
    write_csv(
        args.output_dir / "particle_sparse_window_side_summary.csv",
        side_rows,
        ["output_index", "side", "particle_count", "selected_present_count", "z_min_kpc", "z_max_kpc"],
    )
    write_csv(
        args.output_dir / "particle_sparse_window_lifecycle.csv",
        lifecycle_rows,
        [
            "id",
            "output_count",
            "first_output",
            "last_output",
            "first_time_myr",
            "last_time_myr",
            "x_first_kpc",
            "y_first_kpc",
            "z_first_kpc",
            "x_last_kpc",
            "y_last_kpc",
            "z_last_kpc",
            "present_fraction",
            "displacement_kpc",
        ],
    )

    metadata = {
        "particle_dir": str(args.particle_dir),
        "output_dir": str(args.output_dir),
        "start_index": args.start_index,
        "end_index": args.end_index,
        "target_index": args.target_index,
        "stride": args.stride,
        "window_indices": output_indices,
        "tracer_threshold": args.tracer_threshold,
        "max_selected_ids": args.max_selected_ids,
        "target_candidate_count": target_candidate_count,
        "selected_id_count": selected_count,
        "selected_ids": selected_ids,
        "trajectory_rows": trajectory_rows,
        "code_time_per_myr": args.code_time_per_myr,
        "outputs": sorted(path.name for path in args.output_dir.iterdir() if path.is_file()),
    }
    (args.output_dir / "particle_sparse_window_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: metadata[k] for k in ["target_index", "target_candidate_count", "selected_id_count", "trajectory_rows"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
