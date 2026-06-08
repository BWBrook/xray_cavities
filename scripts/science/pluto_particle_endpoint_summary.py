#!/usr/bin/env python3
"""Summarise one PLUTO binary particle endpoint without a full history cache."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


CODE_TIME_PER_MYR = 306.6013937879523


def parse_header(path: Path) -> dict:
    text = path.read_bytes()[:16384].decode("ascii", errors="ignore")
    header: dict = {
        "field_names": [],
        "field_dim": [],
        "nparticles": None,
        "time": None,
        "stepNumber": None,
        "endianity": "little",
    }
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        parts = line.split()
        if len(parts) < 3:
            continue
        key = parts[1]
        if key == "field_names":
            header["field_names"] = parts[2:]
        elif key == "field_dim":
            header["field_dim"] = [int(x) for x in parts[2:]]
        elif key == "nparticles":
            header["nparticles"] = int(parts[-1])
        elif key == "time":
            header["time"] = float(parts[-1])
        elif key == "stepNumber":
            header["stepNumber"] = int(parts[-1])
        elif key == "endianity":
            header["endianity"] = parts[-1]

    if not header["field_names"] or not header["field_dim"]:
        raise ValueError(f"Could not find particle fields in {path}")
    if len(header["field_names"]) != len(header["field_dim"]):
        raise ValueError("field_names and field_dim lengths differ")
    if header["nparticles"] is None:
        raise ValueError(f"Could not find nparticles in {path}")
    if header["endianity"] != "little":
        raise ValueError(f"Unsupported endianity: {header['endianity']}")

    offsets = {}
    offset = 0
    for name, width in zip(header["field_names"], header["field_dim"]):
        offsets[name] = offset
        offset += width
    header["field_offsets"] = offsets
    header["total_width"] = offset
    header["payload_offset"] = path.stat().st_size - int(header["nparticles"]) * offset * 8
    if header["payload_offset"] < 0:
        raise ValueError("Computed negative particle payload offset")
    return header


def column(data: np.memmap, header: dict, field: str, component: int = 0) -> np.ndarray:
    offsets = header["field_offsets"]
    dims = dict(zip(header["field_names"], header["field_dim"]))
    if field not in offsets:
        raise KeyError(field)
    if component >= dims[field]:
        raise KeyError(f"{field}[{component}]")
    return np.asarray(data[:, offsets[field] + component])


def finite_stats(values: np.ndarray) -> dict:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "count": 0,
            "min": np.nan,
            "p05": np.nan,
            "p25": np.nan,
            "p50": np.nan,
            "p75": np.nan,
            "p95": np.nan,
            "max": np.nan,
            "mean": np.nan,
            "std": np.nan,
        }
    q05, q25, q50, q75, q95 = np.quantile(finite, [0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "count": int(finite.size),
        "min": float(np.min(finite)),
        "p05": float(q05),
        "p25": float(q25),
        "p50": float(q50),
        "p75": float(q75),
        "p95": float(q95),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite)),
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metric_csv(path: Path, rows: list[tuple[str, object, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "unit"])
        writer.writerows(rows)


def histogram_rows(name: str, values: np.ndarray, bins: int, unit: str) -> list[dict]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return []
    counts, edges = np.histogram(finite, bins=bins)
    return [
        {
            "histogram": name,
            "bin": i,
            "lo": float(edges[i]),
            "hi": float(edges[i + 1]),
            "count": int(count),
            "unit": unit,
        }
        for i, count in enumerate(counts)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--particle-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-label", default="C-HI full-grid endpoint")
    parser.add_argument("--code-time-per-myr", type=float, default=CODE_TIME_PER_MYR)
    parser.add_argument("--max-position-rows", type=int, default=20000)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    header = parse_header(args.particle_file)
    dtype = np.dtype("<f8")
    shape = (int(header["nparticles"]), int(header["total_width"]))
    data = np.memmap(args.particle_file, dtype=dtype, mode="r", offset=int(header["payload_offset"]), shape=shape)

    required = ["id", "x1", "x2", "x3", "tinj"]
    missing = [name for name in required if name not in header["field_offsets"]]
    if missing:
        raise ValueError(f"Missing required particle fields: {', '.join(missing)}")

    x = column(data, header, "x1")
    y = column(data, header, "x2")
    z = column(data, header, "x3")
    tinj = column(data, header, "tinj")
    current_code_time = float(header["time"]) if header["time"] is not None else np.nan
    tinj_myr = tinj / args.code_time_per_myr
    age_myr = (current_code_time - tinj) / args.code_time_per_myr

    metric_rows = [
        ("run_label", args.run_label, "text"),
        ("particle_file", str(args.particle_file), "path"),
        ("particle_file_bytes", args.particle_file.stat().st_size, "bytes"),
        ("nparticles", int(header["nparticles"]), "particles"),
        ("field_count", len(header["field_names"]), "fields"),
        ("total_field_width", int(header["total_width"]), "scalar_fields"),
        ("payload_offset", int(header["payload_offset"]), "bytes"),
        ("time_code", current_code_time, "code_time"),
        ("time_myr", current_code_time / args.code_time_per_myr, "Myr"),
        ("stepNumber", header["stepNumber"], "step"),
        ("x_min", float(np.nanmin(x)), "kpc"),
        ("x_max", float(np.nanmax(x)), "kpc"),
        ("y_min", float(np.nanmin(y)), "kpc"),
        ("y_max", float(np.nanmax(y)), "kpc"),
        ("z_min", float(np.nanmin(z)), "kpc"),
        ("z_max", float(np.nanmax(z)), "kpc"),
        ("tinj_min_myr", float(np.nanmin(tinj_myr)), "Myr"),
        ("tinj_max_myr", float(np.nanmax(tinj_myr)), "Myr"),
        ("age_min_myr", float(np.nanmin(age_myr)), "Myr"),
        ("age_max_myr", float(np.nanmax(age_myr)), "Myr"),
    ]
    write_metric_csv(args.output_dir / "particle_endpoint_summary.csv", metric_rows)

    field_rows = []
    dims = dict(zip(header["field_names"], header["field_dim"]))
    for field in header["field_names"]:
        for component in range(dims[field]):
            label = field if dims[field] == 1 else f"{field}_{component}"
            stats = finite_stats(column(data, header, field, component))
            field_rows.append({"field": field, "component": component, "label": label, **stats})
    write_csv(
        args.output_dir / "particle_field_summary.csv",
        field_rows,
        ["field", "component", "label", "count", "min", "p05", "p25", "p50", "p75", "p95", "max", "mean", "std"],
    )

    side_rows = []
    for side_name, mask in [
        ("negative_z_lobe", z < 0.0),
        ("positive_z_lobe", z >= 0.0),
    ]:
        count = int(np.count_nonzero(mask))
        row = {
            "side": side_name,
            "count": count,
            "fraction": count / int(header["nparticles"]),
        }
        for name, values, unit in [
            ("x", x, "kpc"),
            ("y", y, "kpc"),
            ("z", z, "kpc"),
            ("tinj", tinj_myr, "Myr"),
            ("age", age_myr, "Myr"),
        ]:
            stats = finite_stats(values[mask])
            row[f"{name}_min_{unit}"] = stats["min"]
            row[f"{name}_median_{unit}"] = stats["p50"]
            row[f"{name}_max_{unit}"] = stats["max"]
        side_rows.append(row)
    write_csv(args.output_dir / "particle_side_summary.csv", side_rows, list(side_rows[0].keys()))

    hist_rows = []
    hist_rows.extend(histogram_rows("tinj_myr", tinj_myr, 50, "Myr"))
    hist_rows.extend(histogram_rows("age_myr", age_myr, 50, "Myr"))
    hist_rows.extend(histogram_rows("z_kpc", z, 120, "kpc"))
    write_csv(args.output_dir / "particle_histograms.csv", hist_rows, ["histogram", "bin", "lo", "hi", "count", "unit"])

    n = int(header["nparticles"])
    sample_n = min(n, max(0, args.max_position_rows))
    indices = np.unique(np.linspace(0, n - 1, sample_n, dtype=np.int64)) if sample_n else np.array([], dtype=np.int64)
    ids = column(data, header, "id")
    with (args.output_dir / "particle_position_sample.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["row", "id", "x_kpc", "y_kpc", "z_kpc", "tinj_myr", "age_myr"])
        for idx in indices:
            writer.writerow([int(idx), int(ids[idx]), float(x[idx]), float(y[idx]), float(z[idx]), float(tinj_myr[idx]), float(age_myr[idx])])

    metadata = {
        "run_label": args.run_label,
        "particle_file": str(args.particle_file),
        "output_dir": str(args.output_dir),
        "code_time_per_myr": args.code_time_per_myr,
        "header": header,
        "outputs": sorted(path.name for path in args.output_dir.iterdir() if path.is_file()),
    }
    (args.output_dir / "particle_endpoint_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "nparticles": n, "time_myr": current_code_time / args.code_time_per_myr}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
