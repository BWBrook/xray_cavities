#!/usr/bin/env python3
"""Run a compact XRAiSE grid X-ray smoke on a PLUTO static-grid HDF5 output.

This uses the supplied XRAiSE thermal bremsstrahlung helper plus the supplied
APEC and Gaunt correction tables. It deliberately excludes the particle-loss
kernel, which is a separate heavier runtime gate.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.interpolate import RegularGridInterpolator

CODE_TIME_PER_MYR = 306.6013937879523
KPC_M = 3.0856775814913673e19
UNIT_DENSITY_SI = 1.0023678e-21
UNIT_PRESSURE_SI = UNIT_DENSITY_SI * 2.99792458e8 * 2.99792458e8
DEFAULT_FREQ_HZ = 2.417990504024e17


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("xraise", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def widths_from_centres(values: np.ndarray) -> np.ndarray:
    widths = np.empty_like(values, dtype=float)
    if values.size == 1:
        widths[0] = 1.0
        return widths
    widths[1:-1] = 0.5 * (values[2:] - values[:-2])
    widths[0] = values[1] - values[0]
    widths[-1] = values[-1] - values[-2]
    return np.abs(widths)


def write_vector(path: Path, values: np.ndarray) -> None:
    np.savetxt(path, values, fmt="%.10g")


def write_matrix(path: Path, values: np.ndarray) -> None:
    np.savetxt(path, values, fmt="%.10e", delimiter="\t")


def stats(values: np.ndarray) -> dict[str, float | int]:
    finite = values[np.isfinite(values)]
    positive = finite[finite > 0]
    out: dict[str, float | int] = {
        "finite_cells": int(finite.size),
        "positive_cells": int(positive.size),
    }
    if finite.size:
        out.update(
            {
                "min": float(np.nanmin(finite)),
                "max": float(np.nanmax(finite)),
                "sum": float(np.nansum(finite)),
            }
        )
    if positive.size:
        out.update(
            {
                "positive_min": float(np.nanmin(positive)),
                "positive_max": float(np.nanmax(positive)),
                "positive_sum": float(np.nansum(positive)),
            }
        )
    return out


def read_coords(h5: h5py.File) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = h5["/cell_coords/X"][0, 0, :].astype(float)
    y = h5["/cell_coords/Y"][0, :, 0].astype(float)
    z = h5["/cell_coords/Z"][:, 0, 0].astype(float)
    return x, y, z


def make_interpolators(apec_path: Path, gaunt_path: Path):
    raw_apec = np.genfromtxt(apec_path, delimiter=",", filling_values=np.nan)
    apec_reds = raw_apec[0, 1:]
    apec_temps = raw_apec[1:, 0]
    apec_grid = raw_apec[1:, 1:]
    valid_cols = np.isfinite(apec_reds)
    valid_rows = np.isfinite(apec_temps)
    apec_reds = apec_reds[valid_cols]
    apec_temps = apec_temps[valid_rows]
    apec_grid = apec_grid[valid_rows][:, valid_cols]
    apec_interp = RegularGridInterpolator(
        (apec_temps, apec_reds),
        apec_grid,
        bounds_error=False,
        fill_value=None,
    )

    gaunt = np.load(gaunt_path)
    gaunt_interp = RegularGridInterpolator(
        (gaunt["T"], gaunt["f"]),
        gaunt["g"],
        bounds_error=False,
        fill_value=None,
    )
    return apec_interp, gaunt_interp


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    xraise = load_module(args.xraise_py)
    apec_interp, gaunt_interp = make_interpolators(args.apec_table, args.gaunt_lut)

    freqs = np.array([args.frequency_hz], dtype=float)
    redshifts = np.array([args.redshift], dtype=float)

    with h5py.File(args.input_h5, "r") as h5:
        group = h5[f"/{args.timestep}"]
        time_code = float(group.attrs["Time"])
        rho_ds = h5[f"/{args.timestep}/vars/rho"]
        prs_ds = h5[f"/{args.timestep}/vars/prs"]
        trc_ds = h5[f"/{args.timestep}/vars/tr1"]
        x, y, z = read_coords(h5)
        dy_m = widths_from_centres(y) * KPC_M

        nz, ny, nx = rho_ds.shape
        xray_raw = np.zeros((nz, nx), dtype=np.float64)
        xray_corrected = np.zeros((nz, nx), dtype=np.float64)
        tracer_max = np.zeros((nz, nx), dtype=np.float64)

        for start in range(0, ny, args.y_chunk):
            stop = min(start + args.y_chunk, ny)
            rho = rho_ds[:, start:stop, :].astype(np.float64) * UNIT_DENSITY_SI
            prs = prs_ds[:, start:stop, :].astype(np.float64) * UNIT_PRESSURE_SI
            trc = trc_ds[:, start:stop, :].astype(np.float64)

            grid_emis, temp_k = xraise.grid_bremsstrahlung(
                rho,
                prs,
                frequencies=freqs,
                redshifts=redshifts,
            )
            grid_emis = np.nan_to_num(grid_emis, nan=0.0, posinf=0.0, neginf=0.0)
            raw = grid_emis[:, :, :, 0, 0]

            temp_kev = temp_k * 8.617333262e-8
            red_grid = np.full_like(temp_kev, args.redshift, dtype=float)
            apec = apec_interp(np.stack([temp_kev, red_grid], axis=-1))

            freq_grid = np.full_like(temp_k, args.frequency_hz, dtype=float)
            gaunt = gaunt_interp(np.stack([temp_k, freq_grid], axis=-1))
            corrected = np.nan_to_num(raw * apec * gaunt, nan=0.0, posinf=0.0, neginf=0.0)

            path_m = dy_m[start:stop][np.newaxis, :, np.newaxis]
            xray_raw += np.sum(raw * path_m, axis=1) / 1.0e-29
            xray_corrected += np.sum(corrected * path_m, axis=1) / 1.0e-29
            tracer_max = np.maximum(tracer_max, np.nanmax(trc, axis=1))

    ratio = np.divide(
        xray_corrected,
        xray_raw,
        out=np.zeros_like(xray_corrected),
        where=xray_raw > 0,
    )

    write_vector(out_dir / "x_kpc.tsv", x)
    write_vector(out_dir / "z_kpc.tsv", z)
    write_matrix(out_dir / "xray_1kev_raw_mjy_sr.tsv", xray_raw)
    write_matrix(out_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv", xray_corrected)
    write_matrix(out_dir / "xray_1kev_correction_ratio.tsv", ratio)
    write_matrix(out_dir / "tracer_max_los.tsv", tracer_max)

    metadata: dict[str, Any] = {
        "input_h5": str(args.input_h5),
        "timestep": args.timestep,
        "time_code": time_code,
        "time_myr": time_code / CODE_TIME_PER_MYR,
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "grid_shape_nz_ny_nx": [int(nz), int(ny), int(nx)],
        "y_chunk": args.y_chunk,
        "xraise_source": str(args.xraise_py),
        "apec_table": str(args.apec_table),
        "gaunt_lut": str(args.gaunt_lut),
        "method": "xraise.grid_bremsstrahlung plus supplied APEC and Gaunt corrections",
        "raw_stats_mjy_sr": stats(xray_raw),
        "corrected_stats_mjy_sr": stats(xray_corrected),
        "correction_ratio_stats": stats(ratio[ratio > 0]),
    }
    (out_dir / "xraise_grid_smoke_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )

    with (out_dir / "xraise_grid_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["time_myr", f"{metadata['time_myr']:.16g}", "Myr"])
        writer.writerow(["frequency_hz", f"{args.frequency_hz:.16g}", "Hz"])
        writer.writerow(["redshift", f"{args.redshift:.16g}", "dimensionless"])
        writer.writerow(["raw_xray_max", f"{metadata['raw_stats_mjy_sr']['max']:.16g}", "mJy sr^-1"])
        writer.writerow(["corrected_xray_max", f"{metadata['corrected_stats_mjy_sr']['max']:.16g}", "mJy sr^-1"])
        writer.writerow(["raw_xray_sum", f"{metadata['raw_stats_mjy_sr']['sum']:.16g}", "mJy sr^-1 pixels"])
        writer.writerow(["corrected_xray_sum", f"{metadata['corrected_stats_mjy_sr']['sum']:.16g}", "mJy sr^-1 pixels"])
        writer.writerow(["correction_ratio_positive_max", f"{metadata['correction_ratio_stats'].get('positive_max', 0.0):.16g}", "dimensionless"])
        writer.writerow(["correction_ratio_positive_sum", f"{metadata['correction_ratio_stats'].get('positive_sum', 0.0):.16g}", "dimensionless pixels"])

    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-h5", type=Path, required=True)
    parser.add_argument("--timestep", default="Timestep_8")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--xraise-py", type=Path, required=True)
    parser.add_argument("--apec-table", type=Path, required=True)
    parser.add_argument("--gaunt-lut", type=Path, required=True)
    parser.add_argument("--frequency-hz", type=float, default=DEFAULT_FREQ_HZ)
    parser.add_argument("--redshift", type=float, default=0.05)
    parser.add_argument("--y-chunk", type=int, default=8)
    args = parser.parse_args()
    metadata = run(args)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
