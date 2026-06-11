#!/usr/bin/env python3
"""Build a sparse-window particle radio proxy from PLUTO trajectory rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


C_LIGHT = 2.99792458e8
KPC_M = 3.0856775814913673e19
MILLIJANSKY_SI = 1.0e-29
UNIT_DENSITY_SI = 1.0023678e-21
UNIT_PRESSURE_SI = UNIT_DENSITY_SI * C_LIGHT * C_LIGHT

TRAJECTORY_COLUMNS = [
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


def parse_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return float("nan")


def stats(values: np.ndarray) -> dict[str, float | int]:
    finite = values[np.isfinite(values)]
    positive = finite[finite > 0.0]
    out: dict[str, float | int] = {
        "finite_count": int(finite.size),
        "positive_count": int(positive.size),
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
                "positive_sum": float(np.sum(positive)),
            }
        )
    return out


def finite_range(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.min(finite)), float(np.max(finite)))


def read_metadata(sparse_dir: Path) -> dict[str, Any]:
    path = sparse_dir / "particle_sparse_window_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def read_sparse_window(
    sparse_dir: Path,
    target_index: int,
) -> tuple[dict[int, dict[str, float]], dict[int, float], dict[int, int], int]:
    trajectory_path = sparse_dir / "particle_sparse_window_trajectory.tsv"
    if not trajectory_path.exists():
        raise FileNotFoundError(trajectory_path)

    target_rows: dict[int, dict[str, float]] = {}
    pressure_history_max: dict[int, float] = {}
    history_counts: dict[int, int] = {}
    trajectory_rows = 0

    with trajectory_path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = sorted(set(TRAJECTORY_COLUMNS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{trajectory_path} missing columns: {', '.join(missing)}")

        for raw in reader:
            trajectory_rows += 1
            particle_id = int(parse_float(raw["id"]))
            output_index = int(parse_float(raw["output_index"]))
            pressure = parse_float(raw["pressure"])
            history_counts[particle_id] = history_counts.get(particle_id, 0) + 1
            if math.isfinite(pressure) and pressure > 0.0:
                pressure_history_max[particle_id] = max(
                    pressure_history_max.get(particle_id, 0.0),
                    pressure,
                )
            if output_index == target_index:
                target_rows[particle_id] = {name: parse_float(raw[name]) for name in TRAJECTORY_COLUMNS}

    return target_rows, pressure_history_max, history_counts, trajectory_rows


def parse_particle_id(value: str, *, context: str) -> int:
    particle_id = parse_float(value)
    if not math.isfinite(particle_id) or not particle_id.is_integer():
        raise ValueError(f"{context} must be an integer particle ID")
    return int(particle_id)


def table_delimiter(path: Path) -> str:
    if path.suffix.lower() in {".tsv", ".tab"}:
        return "\t"
    return ","


def read_external_loss_table(
    path: Path,
    selected_ids: np.ndarray,
    *,
    id_column: str,
    loss_factor_column: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)

    selected_id_list = [int(value) for value in selected_ids]
    selected_id_set = set(selected_id_list)
    loss_by_id: dict[int, float] = {}
    row_count = 0

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=table_delimiter(path))
        missing = sorted({id_column, loss_factor_column} - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{path} missing columns: {', '.join(missing)}")

        for raw in reader:
            row_count += 1
            particle_id = parse_particle_id(
                raw[id_column],
                context=f"loss-table {id_column} value on row {row_count}",
            )
            if particle_id in loss_by_id:
                raise ValueError(f"duplicate loss-table particle ID: {particle_id}")

            loss_factor = parse_float(raw[loss_factor_column])
            if not math.isfinite(loss_factor):
                raise ValueError(f"loss factor for particle ID {particle_id} must be finite")
            if loss_factor < 0.0:
                raise ValueError(f"loss factor for particle ID {particle_id} must be non-negative")
            loss_by_id[particle_id] = loss_factor

    missing_ids = sorted(selected_id_set - set(loss_by_id))
    if missing_ids:
        preview = ", ".join(str(value) for value in missing_ids[:20])
        suffix = "" if len(missing_ids) <= 20 else f", ... ({len(missing_ids)} total)"
        raise ValueError(f"missing loss factors for selected particle IDs: {preview}{suffix}")

    values = np.asarray([loss_by_id[particle_id] for particle_id in selected_id_list], dtype=np.float64)
    metadata = {
        "path": str(path),
        "delimiter": "tab" if table_delimiter(path) == "\t" else "comma",
        "id_column": id_column,
        "loss_factor_column": loss_factor_column,
        "table_rows": row_count,
        "matched_selected_ids": len(selected_id_list),
        "extra_ids": len(set(loss_by_id) - selected_id_set),
    }
    return values, metadata


def adiabatic_index(pressure_si: np.ndarray, density_si: np.ndarray) -> np.ndarray:
    theta = pressure_si / (density_si * C_LIGHT**2)
    enthalpy = 2.5 * theta + np.sqrt(2.25 * theta**2 + 1.0)
    return (enthalpy - 1.0) / (enthalpy - 1.0 - theta)


def get_kappa(s: float) -> float:
    return (
        math.gamma(0.25 * s + (19.0 / 12.0))
        * math.gamma(0.25 * s - (1.0 / 12.0))
        * math.gamma(0.25 * s + (5.0 / 4.0))
        / math.gamma(0.25 * s + (7.0 / 4.0))
    )


def get_k(kappa_s: float, s: float, gamma_c: np.ndarray, gmin: float, gmax: float) -> np.ndarray:
    mu0 = 1.25663706212e-06
    me = 9.1093837015e-31
    electron_charge = 1.602176634e-19
    denominator = (
        (np.power(gmin, 2.0 - s) - np.power(gmax, 2.0 - s)) / (s - 2.0)
        - (np.power(gmin, 1.0 - s) - np.power(gmax, 1.0 - s)) / (s - 1.0)
    )
    return (
        kappa_s
        / (np.power(me, (s + 3.0) / 2.0) * C_LIGHT * (s + 1.0))
        * np.power(((electron_charge**2) * mu0) / (2.0 * (gamma_c - 1.0)), (s + 5.0) / 4.0)
        * np.power(3.0 / np.pi, s / 2.0)
        / denominator
    )


def sync_lossless_emissivity(
    *,
    pressure_si: np.ndarray,
    density_si: np.ndarray,
    tracer: np.ndarray,
    frequency_hz: float,
    redshift: float,
    eta: float,
    s: float,
    gmin: float,
    gmax: float,
) -> np.ndarray:
    gamma_c = adiabatic_index(pressure_si, density_si)
    k_const = get_k(get_kappa(s), s, gamma_c, gmin, gmax)
    emitted_frequency = frequency_hz * (1.0 + redshift)
    return (
        (k_const / (4.0 * np.pi))
        * np.power(emitted_frequency, (1.0 - s) / 2.0)
        * (np.power(eta, (s + 1.0) / 4.0) / np.power(eta + 1.0, (s + 5.0) / 4.0))
        * (np.power(pressure_si, (s + 5.0) / 4.0) * tracer)
    )


def doppler_term(vx: np.ndarray, vy: np.ndarray, vz: np.ndarray, s: float) -> np.ndarray:
    vel2 = np.clip(vx * vx + vy * vy + vz * vz, 0.0, 0.999999)
    gamma = 1.0 / np.sqrt(1.0 - vel2)
    doppler = 1.0 / (gamma * (1.0 - vy))
    return np.power(doppler, 2.0 + ((s - 1.0) / 2.0))


def make_edges(limit: float, pixel: float) -> np.ndarray:
    n_each_side = int(math.ceil(limit / pixel))
    return np.linspace(-n_each_side * pixel, n_each_side * pixel, 2 * n_each_side + 1)


def side_masks(z: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "negative_z": z < 0.0,
        "positive_z": z >= 0.0,
        "bipolar_total": np.ones_like(z, dtype=bool),
    }


def bin_surface_brightness(
    *,
    x: np.ndarray,
    z: np.ndarray,
    values: np.ndarray,
    particle_volume_m3: np.ndarray,
    x_edges: np.ndarray,
    z_edges: np.ndarray,
) -> np.ndarray:
    pixel_area_m2 = np.diff(x_edges)[0] * np.diff(z_edges)[0] * KPC_M**2
    weights = values * particle_volume_m3 / pixel_area_m2 / MILLIJANSKY_SI
    hist, _, _ = np.histogram2d(z, x, bins=[z_edges, x_edges], weights=weights)
    return hist


def write_matrix(path: Path, values: np.ndarray) -> None:
    np.savetxt(path, values, delimiter="\t", fmt="%.9e")


def write_vector(path: Path, values: np.ndarray) -> None:
    np.savetxt(path, values, fmt="%.17g")


def selected_arrays(
    target_rows: dict[int, dict[str, float]],
    pressure_history_max: dict[int, float],
    history_counts: dict[int, int],
    tracer_threshold: float,
    window_count: int,
) -> dict[str, np.ndarray]:
    rows: list[dict[str, float]] = []
    for particle_id, row in target_rows.items():
        if (
            math.isfinite(row["x_kpc"])
            and math.isfinite(row["y_kpc"])
            and math.isfinite(row["z_kpc"])
            and math.isfinite(row["vx1"])
            and math.isfinite(row["vx2"])
            and math.isfinite(row["vx3"])
            and math.isfinite(row["tracer"])
            and math.isfinite(row["density"])
            and math.isfinite(row["pressure"])
            and row["tracer"] >= tracer_threshold
            and row["density"] > 0.0
            and row["pressure"] > 0.0
        ):
            pressure_max = pressure_history_max.get(particle_id, row["pressure"])
            loss_proxy = row["pressure"] / pressure_max if pressure_max > 0.0 else 0.0
            rows.append(
                {
                    **row,
                    "id": float(particle_id),
                    "pressure_history_max": pressure_max,
                    "history_rows": float(history_counts.get(particle_id, 0)),
                    "history_coverage_fraction": history_counts.get(particle_id, 0) / window_count,
                    "loss_proxy": min(1.0, max(0.0, loss_proxy)),
                }
            )

    names = [
        "id",
        "x_kpc",
        "y_kpc",
        "z_kpc",
        "vx1",
        "vx2",
        "vx3",
        "tracer",
        "density",
        "pressure",
        "pressure_history_max",
        "history_rows",
        "history_coverage_fraction",
        "loss_proxy",
        "time_myr",
        "age_myr",
    ]
    return {
        name: np.asarray([row[name] for row in rows], dtype=np.float64)
        for name in names
    }


def particle_volumes(
    z: np.ndarray,
    *,
    negative_volume_kpc3: float,
    positive_volume_kpc3: float,
    unit_volume_kpc3: float,
) -> tuple[np.ndarray, str]:
    volumes = np.zeros_like(z, dtype=np.float64)
    if negative_volume_kpc3 > 0.0 and positive_volume_kpc3 > 0.0:
        masks = side_masks(z)
        side_inputs = {
            "negative_z": negative_volume_kpc3,
            "positive_z": positive_volume_kpc3,
        }
        for side, volume_kpc3 in side_inputs.items():
            mask = masks[side]
            count = int(mask.sum())
            if count:
                volumes[mask] = (volume_kpc3 / count) * KPC_M**3
        assignment = "declared side volumes divided evenly across selected particles"
    else:
        volumes.fill(unit_volume_kpc3 * KPC_M**3)
        assignment = f"{unit_volume_kpc3} kpc^3 per selected particle"
    return volumes, assignment


def run(args: argparse.Namespace) -> dict[str, Any]:
    sparse_metadata = read_metadata(args.sparse_window_dir)
    target_index = args.target_index
    if target_index is None:
        if "target_index" not in sparse_metadata:
            raise ValueError("--target-index is required when sparse metadata lacks target_index")
        target_index = int(sparse_metadata["target_index"])
    window_indices = sparse_metadata.get("window_indices", [])
    window_count = len(window_indices) if window_indices else 1

    target_rows, pressure_history_max, history_counts, trajectory_rows = read_sparse_window(
        args.sparse_window_dir,
        target_index,
    )
    data = selected_arrays(
        target_rows,
        pressure_history_max,
        history_counts,
        args.tracer_threshold,
        window_count,
    )

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    particle_count = int(data["id"].size)
    pressure_si = data["pressure"] * UNIT_PRESSURE_SI
    density_si = data["density"] * UNIT_DENSITY_SI
    lossless = np.zeros(particle_count, dtype=np.float64)
    valid = (pressure_si > 0.0) & (density_si > 0.0)
    if particle_count:
        lossless[valid] = sync_lossless_emissivity(
            pressure_si=pressure_si[valid],
            density_si=density_si[valid],
            tracer=data["tracer"][valid],
            frequency_hz=args.frequency_hz,
            redshift=args.redshift,
            eta=args.eta,
            s=args.s,
            gmin=args.gmin,
            gmax=args.gmax,
        )
    lossless = np.nan_to_num(lossless, nan=0.0, posinf=0.0, neginf=0.0)
    doppler = doppler_term(data["vx1"], data["vx2"], data["vx3"], args.s) if particle_count else np.array([])
    if args.loss_table is None:
        loss_values = data["loss_proxy"]
        loss_model_key = "pressure_history_proxy"
        loss_model = "pressure-history attenuation proxy"
        loss_value_column = "loss_proxy"
        loss_map_file = "radio_150mhz_sparse_loss_proxy_mjy_sr.tsv"
        mean_loss_map_file = "radio_sparse_mean_loss_proxy.tsv"
        loss_definition = "clip(final pressure / maximum positive pressure across sparse window, 0, 1)"
        loss_method = (
            "lossless synchrotron emissivity from C-HI particle endpoint rows "
            "multiplied by sparse pressure-history loss proxy"
        )
        loss_table_metadata = None
    else:
        loss_values, loss_table_metadata = read_external_loss_table(
            args.loss_table,
            data["id"],
            id_column=args.loss_id_column,
            loss_factor_column=args.loss_factor_column,
        )
        loss_model_key = "external_praise_compatible"
        loss_model = "external PRAiSE-compatible particle loss table"
        loss_value_column = "loss_factor"
        loss_map_file = "radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv"
        mean_loss_map_file = "radio_sparse_mean_external_praise_loss.tsv"
        loss_definition = (
            "finite non-negative per-particle factor supplied by an external "
            "PRAiSE-compatible table keyed by selected particle ID"
        )
        loss_method = (
            "lossless synchrotron emissivity from C-HI particle endpoint rows "
            "multiplied by an external PRAiSE-compatible particle loss table"
        )

    lossy_rest = lossless * loss_values
    lossless_doppler = lossless * doppler
    lossy_doppler = lossy_rest * doppler

    particle_volume_m3, volume_assignment = particle_volumes(
        data["z_kpc"],
        negative_volume_kpc3=args.negative_volume_kpc3,
        positive_volume_kpc3=args.positive_volume_kpc3,
        unit_volume_kpc3=args.unit_volume_kpc3,
    )

    x_edges = make_edges(args.xlim_kpc, args.pixel_kpc)
    z_edges = make_edges(args.zlim_kpc, args.pixel_kpc)
    x_centres = 0.5 * (x_edges[:-1] + x_edges[1:])
    z_centres = 0.5 * (z_edges[:-1] + z_edges[1:])

    in_frame = (
        (data["x_kpc"] >= x_edges[0])
        & (data["x_kpc"] < x_edges[-1])
        & (data["z_kpc"] >= z_edges[0])
        & (data["z_kpc"] < z_edges[-1])
    )
    lossy_map = bin_surface_brightness(
        x=data["x_kpc"][in_frame],
        z=data["z_kpc"][in_frame],
        values=lossy_doppler[in_frame],
        particle_volume_m3=particle_volume_m3[in_frame],
        x_edges=x_edges,
        z_edges=z_edges,
    )
    lossless_map = bin_surface_brightness(
        x=data["x_kpc"][in_frame],
        z=data["z_kpc"][in_frame],
        values=lossless_doppler[in_frame],
        particle_volume_m3=particle_volume_m3[in_frame],
        x_edges=x_edges,
        z_edges=z_edges,
    )
    count_map, _, _ = np.histogram2d(
        data["z_kpc"][in_frame],
        data["x_kpc"][in_frame],
        bins=[z_edges, x_edges],
    )
    loss_sum_map, _, _ = np.histogram2d(
        data["z_kpc"][in_frame],
        data["x_kpc"][in_frame],
        bins=[z_edges, x_edges],
        weights=loss_values[in_frame],
    )
    mean_loss_map = np.divide(
        loss_sum_map,
        count_map,
        out=np.zeros_like(loss_sum_map),
        where=count_map > 0,
    )

    write_vector(out_dir / "x_kpc.tsv", x_centres)
    write_vector(out_dir / "z_kpc.tsv", z_centres)
    write_matrix(out_dir / loss_map_file, lossy_map)
    write_matrix(out_dir / "radio_150mhz_sparse_lossless_mjy_sr.tsv", lossless_map)
    write_matrix(out_dir / "radio_sparse_particle_count_map.tsv", count_map)
    write_matrix(out_dir / mean_loss_map_file, mean_loss_map)

    with (out_dir / "sparse_particle_radio_positions_0deg.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "particle_index",
                "id",
                "x_kpc",
                "y_kpc",
                "z_kpc",
                "tracer",
                "density",
                "pressure",
                "pressure_history_max",
                "history_rows",
                "history_coverage_fraction",
                loss_value_column,
                "doppler_term",
                "lossless_emissivity_si",
                "lossy_emissivity_si",
            ]
        )
        for index in range(particle_count):
            writer.writerow(
                [
                    index,
                    int(data["id"][index]),
                    data["x_kpc"][index],
                    data["y_kpc"][index],
                    data["z_kpc"][index],
                    data["tracer"][index],
                    data["density"][index],
                    data["pressure"][index],
                    data["pressure_history_max"][index],
                    int(data["history_rows"][index]),
                    data["history_coverage_fraction"][index],
                    loss_values[index],
                    doppler[index],
                    lossless[index],
                    lossy_doppler[index],
                ]
            )

    side_rows = []
    for side, mask in side_masks(data["z_kpc"]).items():
        side_count = int(mask.sum())
        volume_m3 = float(np.sum(particle_volume_m3[mask]))
        luminosity_rest = float(np.sum(lossy_rest[mask] * particle_volume_m3[mask]) * 4.0 * np.pi)
        luminosity_doppler = float(np.sum(lossy_doppler[mask] * particle_volume_m3[mask]) * 4.0 * np.pi)
        lossless_luminosity = float(np.sum(lossless_doppler[mask] * particle_volume_m3[mask]) * 4.0 * np.pi)
        xmin, xmax = finite_range(data["x_kpc"][mask])
        ymin, ymax = finite_range(data["y_kpc"][mask])
        zmin, zmax = finite_range(data["z_kpc"][mask])
        loss_stats = stats(loss_values[mask])
        side_rows.append(
            {
                "side": side,
                "particle_count": side_count,
                "volume_kpc3": volume_m3 / KPC_M**3,
                "lossy_luminosity_rest_w_hz": luminosity_rest,
                "lossy_luminosity_doppler_w_hz": luminosity_doppler,
                "lossless_luminosity_doppler_w_hz": lossless_luminosity,
                "x_min_kpc": xmin,
                "x_max_kpc": xmax,
                "y_min_kpc": ymin,
                "y_max_kpc": ymax,
                "z_min_kpc": zmin,
                "z_max_kpc": zmax,
                f"{loss_value_column}_min": loss_stats.get("min", float("nan")),
                f"{loss_value_column}_max": loss_stats.get("max", float("nan")),
                f"{loss_value_column}_mean": loss_stats.get("mean", float("nan")),
                f"{loss_value_column}_positive_count": loss_stats.get("positive_count", 0),
            }
        )

    with (out_dir / "sparse_particle_radio_lobe_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(side_rows[0]))
        writer.writeheader()
        writer.writerows(side_rows)

    map_positive = lossy_map[lossy_map > 0.0]
    metadata: dict[str, Any] = {
        "sparse_window_dir": str(args.sparse_window_dir),
        "sparse_window_metadata": sparse_metadata,
        "target_index": int(target_index),
        "target_rows": len(target_rows),
        "trajectory_rows": trajectory_rows,
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "tracer_threshold": args.tracer_threshold,
        "selected_particles": particle_count,
        "in_frame_particles": int(in_frame.sum()),
        "map_shape": list(lossy_map.shape),
        "pixel_kpc": args.pixel_kpc,
        "radio_map_min_mjy_sr": float(lossy_map.min()) if lossy_map.size else 0.0,
        "radio_map_max_mjy_sr": float(lossy_map.max()) if lossy_map.size else 0.0,
        "radio_map_sum_mjy_sr_pixel": float(lossy_map.sum()),
        "radio_positive_pixels": int(map_positive.size),
        "loss_model": loss_model,
        "loss_model_key": loss_model_key,
        "loss_value_column": loss_value_column,
        "loss_map_file": loss_map_file,
        "mean_loss_map_file": mean_loss_map_file,
        f"{loss_value_column}_definition": loss_definition,
        f"{loss_value_column}_stats": stats(loss_values),
        "volume_assignment": volume_assignment,
        "side_summary": side_rows,
        "projection": "0 deg, projected along simulation y onto x-z plane",
        "method": loss_method,
        "science_status": "local interface product only; not a final PRAiSE science radio product",
    }
    if loss_table_metadata is not None:
        metadata["loss_table"] = loss_table_metadata
    (out_dir / "sparse_particle_radio_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )

    with (out_dir / "sparse_particle_radio_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["target_index", int(target_index), "index"])
        writer.writerow(["frequency_hz", args.frequency_hz, "Hz"])
        writer.writerow(["selected_particles", particle_count, "count"])
        writer.writerow(["in_frame_particles", int(in_frame.sum()), "count"])
        writer.writerow(["radio_map_max_mjy_sr", metadata["radio_map_max_mjy_sr"], "mJy/sr"])
        writer.writerow(["radio_map_sum_mjy_sr_pixel", metadata["radio_map_sum_mjy_sr_pixel"], "mJy/sr_pixel_sum"])
        writer.writerow(["radio_positive_pixels", metadata["radio_positive_pixels"], "pixels"])
        writer.writerow(
            [
                f"{loss_value_column}_mean",
                metadata[f"{loss_value_column}_stats"].get("mean", float("nan")),
                "dimensionless",
            ]
        )
        for side in side_rows:
            writer.writerow(
                [
                    f"{side['side']}_lossy_luminosity_doppler",
                    side["lossy_luminosity_doppler_w_hz"],
                    "W/Hz",
                ]
            )

    print(json.dumps(metadata, indent=2, sort_keys=True))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sparse-window-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-index", type=int)
    parser.add_argument("--frequency-hz", type=float, default=1.5e8)
    parser.add_argument("--redshift", type=float, default=0.05)
    parser.add_argument("--eta", type=float, default=0.03)
    parser.add_argument("--s", type=float, default=2.2)
    parser.add_argument("--gmin", type=float, default=500.0)
    parser.add_argument("--gmax", type=float, default=1.0e5)
    parser.add_argument("--tracer-threshold", type=float, default=5.0e-3)
    parser.add_argument("--xlim-kpc", type=float, default=45.0)
    parser.add_argument("--zlim-kpc", type=float, default=230.0)
    parser.add_argument("--pixel-kpc", type=float, default=1.0)
    parser.add_argument("--negative-volume-kpc3", type=float, default=0.0)
    parser.add_argument("--positive-volume-kpc3", type=float, default=0.0)
    parser.add_argument("--unit-volume-kpc3", type=float, default=1.0)
    parser.add_argument("--loss-table", type=Path)
    parser.add_argument("--loss-id-column", default="id")
    parser.add_argument("--loss-factor-column", default="loss_factor")
    args = parser.parse_args()
    if args.pixel_kpc <= 0.0:
        raise ValueError("--pixel-kpc must be positive")
    if args.xlim_kpc <= 0.0 or args.zlim_kpc <= 0.0:
        raise ValueError("--xlim-kpc and --zlim-kpc must be positive")
    run(args)


if __name__ == "__main__":
    main()
