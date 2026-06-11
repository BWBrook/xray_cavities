#!/usr/bin/env python3
"""Generate a selected-ID sparse PRAiSE-compatible loss table."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pluto_particle_sparse_window import CODE_TIME_PER_MYR, column, read_particle_output


C_LIGHT = 2.99792458e8
UNIT_DENSITY_SI = 1.0023678e-21
UNIT_PRESSURE_SI = UNIT_DENSITY_SI * C_LIGHT * C_LIGHT


@dataclass
class SparseParticleData:
    selected_ids: list[int]
    output_indices: list[int]
    part_times: np.ndarray
    part_data: dict[str, np.ndarray]
    present_counts: list[int]
    missing_counts: list[int]
    code_time_per_myr: float
    metadata: dict[str, Any]


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("xraise", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stats(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    positive = finite[finite > 0.0]
    out: dict[str, Any] = {
        "finite_count": int(finite.size),
        "positive_count": int(positive.size),
        "nan_count": int(values.size - finite.size),
    }
    if finite.size:
        out.update(
            {
                "min": float(np.min(finite)),
                "max": float(np.max(finite)),
                "mean": float(np.mean(finite)),
                "sum": float(np.sum(finite)),
            }
        )
    if positive.size:
        out.update(
            {
                "positive_min": float(np.min(positive)),
                "positive_max": float(np.max(positive)),
                "positive_mean": float(np.mean(positive)),
            }
        )
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_subset(ids: list[int], max_selected_ids: int) -> list[int]:
    if max_selected_ids <= 0 or len(ids) <= max_selected_ids:
        return list(ids)
    if max_selected_ids == 1:
        return [ids[0]]
    indices = np.unique(np.linspace(0, len(ids) - 1, max_selected_ids, dtype=np.int64))
    return [ids[int(index)] for index in indices]


def read_sparse_metadata(sparse_window_dir: Path) -> dict[str, Any]:
    metadata_path = sparse_window_dir / "particle_sparse_window_metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(metadata_path)
    metadata = json.loads(metadata_path.read_text())
    for key in ("selected_ids", "window_indices", "target_index"):
        if key not in metadata:
            raise ValueError(f"{metadata_path} missing required key: {key}")
    return metadata


def row_lookup(output) -> dict[int, int]:
    ids = column(output, "id")
    return {int(value): index for index, value in enumerate(ids) if np.isfinite(value)}


def require_particle_fields(output) -> None:
    required = {"id", "density", "pressure", "tracer", "last_shock_time"}
    missing = sorted(required - set(output.header.field_offsets))
    if missing:
        raise ValueError(f"{output.path} missing required particle fields: {', '.join(missing)}")
    last_shock_dim = output.header.field_dim[output.header.field_names.index("last_shock_time")]
    if last_shock_dim < 3:
        raise ValueError(f"{output.path} last_shock_time has {last_shock_dim} components, expected at least 3")


def build_sparse_particle_data(
    *,
    particle_dir: Path,
    sparse_window_dir: Path,
    max_selected_ids: int,
) -> SparseParticleData:
    metadata = read_sparse_metadata(sparse_window_dir)
    output_indices = [int(value) for value in metadata["window_indices"]]
    selected_ids = deterministic_subset([int(value) for value in metadata["selected_ids"]], max_selected_ids)
    code_time_per_myr = float(metadata.get("code_time_per_myr", CODE_TIME_PER_MYR))

    particle_count = len(selected_ids)
    output_count = len(output_indices)
    part_times = np.full(output_count, np.nan, dtype=np.float64)
    part_data = {
        "density": np.full((particle_count, output_count), np.nan, dtype=np.float64),
        "pressure": np.full((particle_count, output_count), np.nan, dtype=np.float64),
        "tracer": np.full((particle_count, output_count), np.nan, dtype=np.float64),
        "last_shock_time": np.full((particle_count, output_count, 3), np.nan, dtype=np.float64),
    }
    present_counts: list[int] = []
    missing_counts: list[int] = []

    for output_pos, output_index in enumerate(output_indices):
        output = read_particle_output(particle_dir, output_index)
        require_particle_fields(output)
        part_times[output_pos] = float(output.header.time_code)
        lookup = row_lookup(output)
        present = 0
        for selected_pos, particle_id in enumerate(selected_ids):
            row_index = lookup.get(particle_id)
            if row_index is None:
                continue
            present += 1
            part_data["density"][selected_pos, output_pos] = column(output, "density")[row_index]
            part_data["pressure"][selected_pos, output_pos] = column(output, "pressure")[row_index]
            part_data["tracer"][selected_pos, output_pos] = column(output, "tracer")[row_index]
            for component in range(3):
                part_data["last_shock_time"][selected_pos, output_pos, component] = column(
                    output,
                    "last_shock_time",
                    component,
                )[row_index]
        present_counts.append(present)
        missing_counts.append(particle_count - present)

    target_index = int(metadata["target_index"])
    if target_index in output_indices:
        target_pos = output_indices.index(target_index)
        if missing_counts[target_pos] != 0:
            raise ValueError(
                f"{missing_counts[target_pos]} selected IDs are missing at target output {target_index}"
            )

    return SparseParticleData(
        selected_ids=selected_ids,
        output_indices=output_indices,
        part_times=part_times,
        part_data=part_data,
        present_counts=present_counts,
        missing_counts=missing_counts,
        code_time_per_myr=code_time_per_myr,
        metadata=metadata,
    )


def validate_loss_factors(selected_ids: list[int], loss_factors: np.ndarray) -> np.ndarray:
    values = np.asarray(loss_factors, dtype=np.float64).reshape(-1)
    if values.size != len(selected_ids):
        raise ValueError(f"loss factor count {values.size} does not match selected ID count {len(selected_ids)}")
    bad_finite = np.flatnonzero(~np.isfinite(values))
    if bad_finite.size:
        particle_id = selected_ids[int(bad_finite[0])]
        raise ValueError(f"loss factor for particle ID {particle_id} must be finite")
    bad_negative = np.flatnonzero(values < 0.0)
    if bad_negative.size:
        particle_id = selected_ids[int(bad_negative[0])]
        raise ValueError(f"loss factor for particle ID {particle_id} must be non-negative")
    return values


def run_praise(
    *,
    xraise_py: Path,
    shaped: SparseParticleData,
    frequency_hz: float,
    redshift: float,
    eta: float,
    s: float,
    gmin: float,
    gmax: float,
    losses: int,
    lst_index: int,
    window_width: int,
    smooth_order: int,
    particle_spacing_myr: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    import astropy.units as u

    xraise = load_module(xraise_py)
    sim = SimpleNamespace(
        unit_values=SimpleNamespace(
            time=(1.0 / shaped.code_time_per_myr) * u.Myr,
            density=UNIT_DENSITY_SI * u.kg / (u.m**3),
            pressure=UNIT_PRESSURE_SI * u.Pa,
        )
    )
    loss_dict = xraise.praise(
        sim=sim,
        part_data=shaped.part_data,
        part_times=shaped.part_times,
        max_output=len(shaped.part_times) - 1,
        emit_outputs=[len(shaped.part_times) - 1],
        redshift=[redshift],
        freqs=np.array([frequency_hz], dtype=float),
        eta=eta,
        s=s,
        gmin=gmin,
        gmax=gmax,
        lst_index=lst_index,
        losses=[losses],
        window_width=window_width,
        smooth_order=smooth_order,
        particle_spacing=particle_spacing_myr * u.Myr,
        time_execution=True,
        output_system="particles",
    )
    key = "full" if losses == 4 else next(iter(loss_dict))
    entry = loss_dict[key][0]
    raw = entry["emis"]
    if hasattr(raw, "to_value"):
        values = raw.to_value(u.W / (u.Hz * u.m**3 * u.sr))
    else:
        values = np.asarray(raw, dtype=np.float64)
    loss_factors = validate_loss_factors(shaped.selected_ids, values[:, 0, 0])
    return loss_factors, {"loss_key": key, "part_output": int(entry.get("part_output", -1))}


def write_loss_outputs(
    *,
    output_dir: Path,
    shaped: SparseParticleData,
    loss_factors: np.ndarray,
    praise_metadata: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    table_path = output_dir / "sparse_praise_loss_table.csv"
    with table_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "loss_factor"])
        for particle_id, loss_factor in zip(shaped.selected_ids, loss_factors):
            writer.writerow([particle_id, f"{loss_factor:.17g}"])

    sample_path = output_dir / "sparse_praise_loss_table_first1000.tsv"
    sample_count = min(1000, len(shaped.selected_ids))
    with sample_path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["id", "loss_factor"])
        for particle_id, loss_factor in zip(shaped.selected_ids[:sample_count], loss_factors[:sample_count]):
            writer.writerow([particle_id, f"{loss_factor:.17g}"])

    target_index = int(shaped.metadata["target_index"])
    target_pos = shaped.output_indices.index(target_index) if target_index in shaped.output_indices else -1
    metadata = {
        "particle_dir": str(args.particle_dir),
        "sparse_window_dir": str(args.sparse_window_dir),
        "xraise_py": str(args.xraise_py),
        "output_dir": str(output_dir),
        "loss_table": str(table_path),
        "target_index": target_index,
        "window_indices": shaped.output_indices,
        "selected_id_count": len(shaped.selected_ids),
        "max_selected_ids": args.max_selected_ids,
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "eta": args.eta,
        "s": args.s,
        "gmin": args.gmin,
        "gmax": args.gmax,
        "losses": args.losses,
        "lst_index": args.lst_index,
        "window_width": args.window_width,
        "smooth_order": args.smooth_order,
        "particle_spacing_myr": args.particle_spacing_myr,
        "praise": praise_metadata,
        "coverage": {
            "present_counts": shaped.present_counts,
            "missing_counts": shaped.missing_counts,
            "missing_at_target": shaped.missing_counts[target_pos] if target_pos >= 0 else None,
        },
        "loss_factor_stats": stats(loss_factors),
        "loss_table_sha256": sha256(table_path),
        "science_status": "sparse-window PRAiSE-compatible loss table; not a final science radio product",
    }
    metadata_path = output_dir / "sparse_praise_loss_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    with (output_dir / "sparse_praise_loss_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["selected_id_count", len(shaped.selected_ids), "count"])
        writer.writerow(["target_index", target_index, "index"])
        writer.writerow(["frequency_hz", args.frequency_hz, "Hz"])
        writer.writerow(["redshift", args.redshift, "dimensionless"])
        writer.writerow(["loss_table_sha256", metadata["loss_table_sha256"], "sha256"])
        for name, value in metadata["loss_factor_stats"].items():
            writer.writerow([f"loss_factor_{name}", value, "dimensionless"])

    return metadata


def run(args: argparse.Namespace) -> dict[str, Any]:
    shaped = build_sparse_particle_data(
        particle_dir=args.particle_dir,
        sparse_window_dir=args.sparse_window_dir,
        max_selected_ids=args.max_selected_ids,
    )
    loss_factors, praise_metadata = run_praise(
        xraise_py=args.xraise_py,
        shaped=shaped,
        frequency_hz=args.frequency_hz,
        redshift=args.redshift,
        eta=args.eta,
        s=args.s,
        gmin=args.gmin,
        gmax=args.gmax,
        losses=args.losses,
        lst_index=args.lst_index,
        window_width=args.window_width,
        smooth_order=args.smooth_order,
        particle_spacing_myr=args.particle_spacing_myr,
    )
    metadata = write_loss_outputs(
        output_dir=args.output_dir,
        shaped=shaped,
        loss_factors=loss_factors,
        praise_metadata=praise_metadata,
        args=args,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--particle-dir", type=Path, required=True)
    parser.add_argument("--sparse-window-dir", type=Path, required=True)
    parser.add_argument("--xraise-py", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-selected-ids", type=int, default=0)
    parser.add_argument("--frequency-hz", type=float, default=1.5e8)
    parser.add_argument("--redshift", type=float, default=0.05)
    parser.add_argument("--eta", type=float, default=0.03)
    parser.add_argument("--s", type=float, default=2.2)
    parser.add_argument("--gmin", type=float, default=500.0)
    parser.add_argument("--gmax", type=float, default=1.0e5)
    parser.add_argument("--losses", type=int, default=4)
    parser.add_argument("--lst-index", type=int, default=2)
    parser.add_argument("--window-width", type=int, default=5)
    parser.add_argument("--smooth-order", type=int, default=3)
    parser.add_argument("--particle-spacing-myr", type=float, default=0.01)
    args = parser.parse_args()

    if args.max_selected_ids < 0:
        raise ValueError("--max-selected-ids must be non-negative")
    if args.frequency_hz <= 0.0:
        raise ValueError("--frequency-hz must be positive")
    if args.particle_spacing_myr <= 0.0:
        raise ValueError("--particle-spacing-myr must be positive")
    run(args)


if __name__ == "__main__":
    main()
