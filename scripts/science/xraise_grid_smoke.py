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
import math
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
BOLTZMANN_J_K = 1.380649e-23
PROTON_MASS_KG = 1.67262192369e-27


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


def centres_to_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("need at least two coordinate centres")
    mids = 0.5 * (values[:-1] + values[1:])
    first = values[0] - (mids[0] - values[0])
    last = values[-1] + (values[-1] - mids[-1])
    return np.concatenate([[first], mids, [last]])


def projected_axis(
    x: np.ndarray,
    y: np.ndarray,
    *,
    view_angle_deg: float,
    projected_u_bins: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    if projected_u_bins is None:
        projected_u_bins = len(x)
    if projected_u_bins < 2:
        raise ValueError("projected_u_bins must be at least 2")

    theta = math.radians(view_angle_deg)
    x_edges = centres_to_edges(x)
    y_edges = centres_to_edges(y)
    corner_u = [
        x_edge * math.cos(theta) - y_edge * math.sin(theta)
        for x_edge in (x_edges[0], x_edges[-1])
        for y_edge in (y_edges[0], y_edges[-1])
    ]
    u_edges = np.linspace(min(corner_u), max(corner_u), projected_u_bins + 1)
    u_centres = 0.5 * (u_edges[:-1] + u_edges[1:])
    return u_centres, u_edges


def resolve_projection_method(view_angle_deg: float, projection_mode: str) -> str:
    """Resolve the requested projection mode while preserving legacy defaults."""

    if projection_mode not in {"auto", "direct_axis", "edge_overlap"}:
        raise ValueError(f"unknown projection mode: {projection_mode}")
    at_zero = abs(view_angle_deg) <= 1.0e-12
    at_ninety = abs(view_angle_deg - 90.0) <= 1.0e-12
    if projection_mode == "auto":
        return "direct_y_axis_sum" if at_zero else "edge_overlap_uniform_cell_projection"
    if projection_mode == "direct_axis":
        if at_zero:
            return "direct_y_axis_sum"
        if at_ninety:
            return "direct_x_axis_sum"
        raise ValueError("direct_axis projection requires a view angle of exactly 0 or 90 degrees")
    return "edge_overlap_uniform_cell_projection"


def direct_x_axis_projection(
    *,
    raw: np.ndarray,
    corrected: np.ndarray,
    tracer: np.ndarray,
    x_width_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Integrate along native x cells and return columns ordered by increasing ``u=-y``."""

    weights = np.asarray(x_width_m, dtype=float)[np.newaxis, np.newaxis, :]
    raw_path = np.sum(raw * weights, axis=2)[:, ::-1]
    corrected_path = np.sum(corrected * weights, axis=2)[:, ::-1]
    tracer_max = np.nanmax(tracer, axis=2)[:, ::-1]
    return raw_path, corrected_path, tracer_max


def direct_x_axis_scalar_projection(values: np.ndarray, x_width_m: np.ndarray) -> np.ndarray:
    """Integrate one scalar field along native x cells in increasing ``u=-y`` order."""

    weights = np.asarray(x_width_m, dtype=float)[np.newaxis, np.newaxis, :]
    return np.sum(np.asarray(values, dtype=float) * weights, axis=2)[:, ::-1]


def projected_overlap_contributions(
    *,
    x_edges: np.ndarray,
    y_edges_chunk: np.ndarray,
    u_edges: np.ndarray,
    view_angle_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return cell-to-projected-bin path weights for edge-aware accumulation."""

    x_edges = np.asarray(x_edges, dtype=float)
    y_edges_chunk = np.asarray(y_edges_chunk, dtype=float)
    u_edges = np.asarray(u_edges, dtype=float)
    if x_edges.ndim != 1 or y_edges_chunk.ndim != 1 or u_edges.ndim != 1:
        raise ValueError("x_edges, y_edges_chunk, and u_edges must be one-dimensional")
    if x_edges.size < 2 or y_edges_chunk.size < 2 or u_edges.size < 2:
        raise ValueError("need at least one source cell and one projected bin")
    if np.any(np.diff(x_edges) <= 0.0) or np.any(np.diff(y_edges_chunk) <= 0.0):
        raise ValueError("source grid edges must be strictly increasing")

    u_widths = np.diff(u_edges)
    if np.any(u_widths <= 0.0):
        raise ValueError("projected u edges must be strictly increasing")

    theta = math.radians(view_angle_deg)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)

    x_left = x_edges[:-1]
    x_right = x_edges[1:]
    y_low = y_edges_chunk[:-1]
    y_high = y_edges_chunk[1:]
    cell_area = np.diff(y_edges_chunk)[:, np.newaxis] * np.diff(x_edges)[np.newaxis, :]

    corners = (
        x_left[np.newaxis, :] * cos_theta - y_low[:, np.newaxis] * sin_theta,
        x_left[np.newaxis, :] * cos_theta - y_high[:, np.newaxis] * sin_theta,
        x_right[np.newaxis, :] * cos_theta - y_low[:, np.newaxis] * sin_theta,
        x_right[np.newaxis, :] * cos_theta - y_high[:, np.newaxis] * sin_theta,
    )
    u_min = np.minimum.reduce(corners)
    u_max = np.maximum.reduce(corners)
    projected_width = u_max - u_min
    if np.any(projected_width <= 0.0):
        raise ValueError("projected source-cell width must be positive")

    first_bins = np.searchsorted(u_edges, u_min.ravel(), side="right") - 1
    last_bins = np.searchsorted(u_edges, u_max.ravel(), side="left") - 1
    first_bins = np.clip(first_bins, 0, len(u_widths) - 1)
    last_bins = np.clip(last_bins, 0, len(u_widths) - 1)

    flat_u_min = u_min.ravel()
    flat_u_max = u_max.ravel()
    flat_area = cell_area.ravel()
    flat_projected_width = projected_width.ravel()

    cell_indices: list[int] = []
    bin_indices: list[int] = []
    path_weights: list[float] = []
    for cell_index, (first_bin, last_bin) in enumerate(zip(first_bins, last_bins, strict=True)):
        for bin_index in range(int(first_bin), int(last_bin) + 1):
            overlap = min(flat_u_max[cell_index], u_edges[bin_index + 1]) - max(
                flat_u_min[cell_index], u_edges[bin_index]
            )
            if overlap <= 0.0:
                continue
            cell_indices.append(int(cell_index))
            bin_indices.append(bin_index)
            path_weights.append(
                float(flat_area[cell_index] * overlap / (flat_projected_width[cell_index] * u_widths[bin_index]))
            )

    if not cell_indices:
        return (
            np.array([], dtype=np.int64),
            np.array([], dtype=np.int64),
            np.array([], dtype=np.float64),
        )
    return (
        np.asarray(cell_indices, dtype=np.int64),
        np.asarray(bin_indices, dtype=np.int64),
        np.asarray(path_weights, dtype=np.float64),
    )


def accumulate_projected_chunk(
    *,
    raw_path: np.ndarray,
    corrected_path: np.ndarray,
    tracer_max: np.ndarray,
    raw: np.ndarray,
    corrected: np.ndarray,
    tracer: np.ndarray,
    x: np.ndarray,
    y_chunk: np.ndarray,
    x_widths: np.ndarray,
    y_widths_chunk: np.ndarray,
    u_edges: np.ndarray,
    view_angle_deg: float,
    x_edges: np.ndarray | None = None,
    y_edges_chunk: np.ndarray | None = None,
) -> None:
    u_widths = np.diff(u_edges)
    if np.any(u_widths <= 0.0):
        raise ValueError("projected u edges must be strictly increasing")

    if x_edges is None:
        x_edges = centres_to_edges(x)
    if y_edges_chunk is None:
        y_edges_chunk = centres_to_edges(y_chunk)
    if len(x_edges) != len(x) + 1:
        raise ValueError("x_edges length must be len(x) + 1")
    if len(y_edges_chunk) != len(y_chunk) + 1:
        raise ValueError("y_edges_chunk length must be len(y_chunk) + 1")

    flat_cells, flat_bins, flat_weights = projected_overlap_contributions(
        x_edges=x_edges,
        y_edges_chunk=y_edges_chunk,
        u_edges=u_edges,
        view_angle_deg=view_angle_deg,
    )
    if flat_cells.size == 0:
        return

    n_u = len(u_widths)

    for z_index in range(raw.shape[0]):
        raw_values = raw[z_index].ravel()[flat_cells] * flat_weights
        corrected_values = corrected[z_index].ravel()[flat_cells] * flat_weights
        raw_path[z_index] += np.bincount(flat_bins, weights=raw_values, minlength=n_u)
        corrected_path[z_index] += np.bincount(flat_bins, weights=corrected_values, minlength=n_u)

        tracer_values = np.nan_to_num(tracer[z_index].ravel()[flat_cells], nan=0.0, posinf=0.0, neginf=0.0)
        tracer_by_bin = np.zeros(n_u, dtype=np.float64)
        np.maximum.at(tracer_by_bin, flat_bins, tracer_values)
        tracer_max[z_index] = np.maximum(tracer_max[z_index], tracer_by_bin)


def accumulate_scalar_projected_chunk(
    *,
    target: np.ndarray,
    values: np.ndarray,
    x: np.ndarray,
    y_chunk: np.ndarray,
    u_edges: np.ndarray,
    view_angle_deg: float,
    x_edges: np.ndarray | None = None,
    y_edges_chunk: np.ndarray | None = None,
) -> None:
    """Accumulate one scalar field using the accepted edge-overlap projection."""

    if x_edges is None:
        x_edges = centres_to_edges(x)
    if y_edges_chunk is None:
        y_edges_chunk = centres_to_edges(y_chunk)
    flat_cells, flat_bins, flat_weights = projected_overlap_contributions(
        x_edges=x_edges,
        y_edges_chunk=y_edges_chunk,
        u_edges=u_edges,
        view_angle_deg=view_angle_deg,
    )
    if flat_cells.size == 0:
        return
    n_u = len(u_edges) - 1
    for z_index in range(values.shape[0]):
        weighted = values[z_index].ravel()[flat_cells] * flat_weights
        target[z_index] += np.bincount(flat_bins, weights=weighted, minlength=n_u)


def infer_mean_molecular_weight(
    rho_kg_m3: np.ndarray,
    pressure_pa: np.ndarray,
    temperature_k: np.ndarray,
) -> float:
    """Infer the XRAiSE temperature convention's effective molecular weight."""

    rho = np.asarray(rho_kg_m3, dtype=float)
    pressure = np.asarray(pressure_pa, dtype=float)
    temperature = np.asarray(temperature_k, dtype=float)
    valid = (
        np.isfinite(rho)
        & np.isfinite(pressure)
        & np.isfinite(temperature)
        & (rho > 0.0)
        & (pressure > 0.0)
        & (temperature > 0.0)
    )
    if not np.any(valid):
        raise ValueError("cannot infer mean molecular weight from empty positive sample")
    mu = rho[valid] * BOLTZMANN_J_K * temperature[valid] / (pressure[valid] * PROTON_MASS_KG)
    mu = mu[np.isfinite(mu) & (mu > 0.0)]
    if mu.size == 0:
        raise ValueError("mean molecular weight sample is non-finite")
    return float(np.median(mu))


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
        x_edges = centres_to_edges(x)
        y_edges = centres_to_edges(y)
        x_width_kpc = widths_from_centres(x)
        y_width_kpc = widths_from_centres(y)
        y_width_m = y_width_kpc * KPC_M

        nz, ny, nx = rho_ds.shape
        projection_method = resolve_projection_method(
            args.view_angle_deg, getattr(args, "projection_mode", "auto")
        )
        if projection_method == "direct_y_axis_sum":
            sky_x = x
            sky_edges = None
            n_sky = nx
        elif projection_method == "direct_x_axis_sum":
            sky_x = -y[::-1]
            sky_edges = None
            n_sky = ny
        else:
            sky_x, sky_edges = projected_axis(
                x,
                y,
                view_angle_deg=args.view_angle_deg,
                projected_u_bins=args.projected_u_bins,
            )
            n_sky = len(sky_x)
        xray_raw = np.zeros((nz, n_sky), dtype=np.float64)
        xray_corrected = np.zeros((nz, n_sky), dtype=np.float64)
        emission_measure_rho2 = np.zeros((nz, n_sky), dtype=np.float64)
        corrected_temperature_numerator = np.zeros((nz, n_sky), dtype=np.float64)
        tracer_max = np.zeros((nz, n_sky), dtype=np.float64)
        molecular_weight_samples: list[float] = []

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
            rho2 = np.square(rho)
            corrected_temperature = corrected * temp_k
            sample = (slice(None, None, 16), slice(None, None, 2), slice(None, None, 16))
            molecular_weight_samples.append(
                infer_mean_molecular_weight(rho[sample], prs[sample], temp_k[sample])
            )

            if projection_method == "direct_y_axis_sum":
                path_m = y_width_m[start:stop][np.newaxis, :, np.newaxis]
                xray_raw += np.sum(raw * path_m, axis=1) / 1.0e-29
                xray_corrected += np.sum(corrected * path_m, axis=1) / 1.0e-29
                emission_measure_rho2 += np.sum(rho2 * path_m, axis=1)
                corrected_temperature_numerator += (
                    np.sum(corrected_temperature * path_m, axis=1) / 1.0e-29
                )
                tracer_max = np.maximum(tracer_max, np.nanmax(trc, axis=1))
            elif projection_method == "direct_x_axis_sum":
                raw_path, corrected_path, tracer_path = direct_x_axis_projection(
                    raw=raw,
                    corrected=corrected,
                    tracer=trc,
                    x_width_m=x_width_kpc * KPC_M,
                )
                target = slice(ny - stop, ny - start)
                xray_raw[:, target] = raw_path / 1.0e-29
                xray_corrected[:, target] = corrected_path / 1.0e-29
                emission_measure_rho2[:, target] = direct_x_axis_scalar_projection(
                    rho2, x_width_kpc * KPC_M
                )
                corrected_temperature_numerator[:, target] = (
                    direct_x_axis_scalar_projection(corrected_temperature, x_width_kpc * KPC_M)
                    / 1.0e-29
                )
                tracer_max[:, target] = tracer_path
            else:
                raw_path = np.zeros_like(xray_raw)
                corrected_path = np.zeros_like(xray_corrected)
                accumulate_projected_chunk(
                    raw_path=raw_path,
                    corrected_path=corrected_path,
                    tracer_max=tracer_max,
                    raw=raw,
                    corrected=corrected,
                    tracer=trc,
                    x=x,
                    y_chunk=y[start:stop],
                    x_widths=x_width_kpc,
                    y_widths_chunk=y_width_kpc[start:stop],
                    u_edges=sky_edges,
                    view_angle_deg=args.view_angle_deg,
                    x_edges=x_edges,
                    y_edges_chunk=y_edges[start : stop + 1],
                )
                xray_raw += raw_path * KPC_M / 1.0e-29
                xray_corrected += corrected_path * KPC_M / 1.0e-29
                rho2_path = np.zeros_like(emission_measure_rho2)
                temperature_path = np.zeros_like(corrected_temperature_numerator)
                for target, values in (
                    (rho2_path, rho2),
                    (temperature_path, corrected_temperature),
                ):
                    accumulate_scalar_projected_chunk(
                        target=target,
                        values=values,
                        x=x,
                        y_chunk=y[start:stop],
                        u_edges=sky_edges,
                        view_angle_deg=args.view_angle_deg,
                        x_edges=x_edges,
                        y_edges_chunk=y_edges[start : stop + 1],
                    )
                emission_measure_rho2 += rho2_path * KPC_M
                corrected_temperature_numerator += temperature_path * KPC_M / 1.0e-29

    ratio = np.divide(
        xray_corrected,
        xray_raw,
        out=np.zeros_like(xray_corrected),
        where=xray_raw > 0,
    )
    emission_weighted_temperature = np.divide(
        corrected_temperature_numerator,
        xray_corrected,
        out=np.zeros_like(corrected_temperature_numerator),
        where=xray_corrected > 0,
    )
    effective_mean_molecular_weight = float(np.median(molecular_weight_samples))

    write_vector(out_dir / "x_kpc.tsv", sky_x)
    if abs(args.view_angle_deg) > 1.0e-12:
        write_vector(out_dir / "u_kpc.tsv", sky_x)
    write_vector(out_dir / "z_kpc.tsv", z)
    write_matrix(out_dir / "xray_1kev_raw_mjy_sr.tsv", xray_raw)
    write_matrix(out_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv", xray_corrected)
    write_matrix(out_dir / "xray_1kev_correction_ratio.tsv", ratio)
    write_matrix(out_dir / "xray_emission_measure_rho2_kg2_m5.tsv", emission_measure_rho2)
    write_matrix(
        out_dir / "xray_corrected_temperature_numerator_mjy_k_sr.tsv",
        corrected_temperature_numerator,
    )
    write_matrix(out_dir / "xray_emission_weighted_temperature_k.tsv", emission_weighted_temperature)
    write_matrix(out_dir / "tracer_max_los.tsv", tracer_max)

    metadata: dict[str, Any] = {
        "input_h5": str(args.input_h5),
        "timestep": args.timestep,
        "time_code": time_code,
        "time_myr": time_code / CODE_TIME_PER_MYR,
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "grid_shape_nz_ny_nx": [int(nz), int(ny), int(nx)],
        "projection": {
            "view_angle_deg": args.view_angle_deg,
            "requested_mode": getattr(args, "projection_mode", "auto"),
            "line_of_sight": "rotated in simulation x-y plane from +y toward +x",
            "sky_horizontal_axis": "u = x*cos(theta) - y*sin(theta)",
            "sky_horizontal_bins": int(n_sky),
            "sky_horizontal_min_kpc": float(sky_x[0]),
            "sky_horizontal_max_kpc": float(sky_x[-1]),
            "projected_accumulation": projection_method,
        },
        "y_chunk": args.y_chunk,
        "xraise_source": str(args.xraise_py),
        "apec_table": str(args.apec_table),
        "gaunt_lut": str(args.gaunt_lut),
        "method": "xraise.grid_bremsstrahlung plus supplied APEC and Gaunt corrections",
        "pressure_deprojection_inputs": {
            "emission_measure": "line-of-sight integral of mass_density_squared",
            "temperature": "corrected-X-ray-emissivity-weighted temperature",
            "effective_mean_molecular_weight": effective_mean_molecular_weight,
            "tracer_used": False,
        },
        "raw_stats_mjy_sr": stats(xray_raw),
        "corrected_stats_mjy_sr": stats(xray_corrected),
        "correction_ratio_stats": stats(ratio[ratio > 0]),
        "emission_measure_rho2_stats_kg2_m5": stats(emission_measure_rho2),
        "emission_weighted_temperature_stats_k": stats(emission_weighted_temperature),
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
        writer.writerow(["effective_mean_molecular_weight", f"{effective_mean_molecular_weight:.16g}", "dimensionless"])
        writer.writerow(["emission_measure_rho2_sum", f"{metadata['emission_measure_rho2_stats_kg2_m5']['sum']:.16g}", "kg^2 m^-5 pixels"])
        writer.writerow(["emission_weighted_temperature_positive_median", f"{np.median(emission_weighted_temperature[emission_weighted_temperature > 0]):.16g}", "K"])

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
    parser.add_argument("--view-angle-deg", type=float, default=0.0)
    parser.add_argument("--projected-u-bins", type=int, default=None)
    parser.add_argument(
        "--projection-mode",
        choices=("auto", "direct_axis", "edge_overlap"),
        default="auto",
        help="auto preserves legacy direct-y-at-zero behavior; direct_axis adds a native x sum at 90 degrees",
    )
    args = parser.parse_args()
    metadata = run(args)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
