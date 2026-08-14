#!/usr/bin/env python3
"""Axial shock detection, kinematics, and Rankine-Hugoniot checks."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS,
    UNIT_LENGTH_CM,
    UNIT_VELOCITY_CMS,
)
from select_common_age_hdf5 import Snapshot
from snapshot_energy import EnvironmentProfile, SECONDS_PER_MYR


SHOCK_THRESHOLD_FACTORS = (0.5, 1.0, 2.0)

def contiguous_runs(indices: np.ndarray) -> list[np.ndarray]:
    if indices.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(indices) != 1) + 1
    return [group for group in np.split(indices, breaks) if group.size]


def _rh_mach_from_pressure(ratio: float) -> float | None:
    if not math.isfinite(ratio) or ratio <= 1.0:
        return None
    value = (ratio * (GAMMA_GAS + 1.0) + (GAMMA_GAS - 1.0)) / (2.0 * GAMMA_GAS)
    return math.sqrt(value) if value >= 1.0 else None


def _rh_mach_from_density(ratio: float) -> float | None:
    if not math.isfinite(ratio) or ratio <= 1.0:
        return None
    denominator = (GAMMA_GAS + 1.0) - ratio * (GAMMA_GAS - 1.0)
    if denominator <= 0.0:
        return None
    value = 2.0 * ratio / denominator
    return math.sqrt(value) if value >= 1.0 else None


def detect_shock(
    profile_rows: Sequence[Mapping[str, Any]],
    *,
    side: str,
    velocity_cut_code: float,
    disturbance_fraction: float,
    min_contiguous_cells: int,
) -> dict[str, Any] | None:
    if side not in ("negative_z", "positive_z"):
        raise ValueError(f"invalid shock side: {side}")
    if velocity_cut_code <= 0.0 or disturbance_fraction <= 0.0 or min_contiguous_cells < 1:
        raise ValueError("invalid shock detection parameters")
    z = np.asarray([float(row["z_kpc"]) for row in profile_rows])
    vz = np.asarray([float(row["vz_code"]) for row in profile_rows])
    rho = np.asarray([float(row["rho_code"]) for row in profile_rows])
    pressure = np.asarray([float(row["pressure_code"]) for row in profile_rows])
    rho0 = np.asarray([float(row["baseline_rho_code"]) for row in profile_rows])
    pressure0 = np.asarray([float(row["baseline_pressure_code"]) for row in profile_rows])
    disturbance = np.maximum(np.abs(rho / rho0 - 1.0), np.abs(pressure / pressure0 - 1.0))
    if side == "positive_z":
        mask = (z > 0.0) & (vz > velocity_cut_code) & (disturbance >= disturbance_fraction)
    else:
        mask = (z < 0.0) & (vz < -velocity_cut_code) & (disturbance >= disturbance_fraction)
    runs = [run for run in contiguous_runs(np.flatnonzero(mask)) if len(run) >= min_contiguous_cells]
    if not runs:
        return None
    run = max(runs, key=lambda group: float(np.max(np.abs(z[group]))))
    index = int(run[-1] if side == "positive_z" else run[0])
    inner_direction = -1 if side == "positive_z" else 1
    outer_direction = 1 if side == "positive_z" else -1
    inner = [index + inner_direction * step for step in (1, 2)]
    outer = [index + outer_direction * step for step in (1, 2)]
    if min(inner + outer) < 0 or max(inner + outer) >= len(z):
        pressure_ratio = density_ratio = math.nan
    else:
        pressure_ratio = float(np.mean(pressure[inner]) / np.mean(pressure[outer]))
        density_ratio = float(np.mean(rho[inner]) / np.mean(rho[outer]))
    return {
        "shock_index": index,
        "shock_z_kpc": float(z[index]),
        "shock_distance_kpc": float(abs(z[index])),
        "position_uncertainty_kpc": 0.5 * float(profile_rows[index]["dz_kpc"]),
        "candidate_run_cells": int(len(run)),
        "velocity_code": float(vz[index]),
        "disturbance_fraction": float(disturbance[index]),
        "pressure_jump_ratio": pressure_ratio,
        "density_jump_ratio": density_ratio,
        "mach_rh_pressure": _rh_mach_from_pressure(pressure_ratio),
        "mach_rh_density": _rh_mach_from_density(density_ratio),
    }


def local_three_point_slope(
    times_myr: np.ndarray,
    distances_kpc: np.ndarray,
    uncertainties_kpc: np.ndarray,
    index: int,
) -> tuple[float, float] | None:
    if len(times_myr) < 3:
        return None
    start = max(0, min(index - 1, len(times_myr) - 3))
    selected = slice(start, start + 3)
    t = times_myr[selected]
    d = distances_kpc[selected]
    u = uncertainties_kpc[selected]
    centred = t - np.mean(t)
    sxx = float(np.sum(centred**2))
    if sxx <= 0.0:
        return None
    slope = float(np.sum(centred * (d - np.mean(d))) / sxx)
    slope_uncertainty = float(math.sqrt(np.sum((centred * u) ** 2)) / sxx)
    return slope, slope_uncertainty


def build_shock_rows(
    *,
    case: str,
    profiles: Sequence[Sequence[Mapping[str, Any]]],
    snapshots: Sequence[Snapshot],
    environment: EnvironmentProfile,
    primary_velocity_cut_code: float,
    disturbance_fraction: float,
    min_contiguous_cells: int,
) -> list[dict[str, Any]]:
    detections: dict[tuple[float, str], list[dict[str, Any] | None]] = {}
    for factor in SHOCK_THRESHOLD_FACTORS:
        for side in ("negative_z", "positive_z"):
            detections[(factor, side)] = [
                detect_shock(
                    profile,
                    side=side,
                    velocity_cut_code=primary_velocity_cut_code * factor,
                    disturbance_fraction=disturbance_fraction,
                    min_contiguous_cells=min_contiguous_cells,
                )
                for profile in profiles
            ]
    rows: list[dict[str, Any]] = []
    for factor in SHOCK_THRESHOLD_FACTORS:
        for side in ("negative_z", "positive_z"):
            detected = detections[(factor, side)]
            valid_indices = [index for index, value in enumerate(detected) if value is not None]
            valid_times = np.asarray([snapshots[index].actual_time_myr for index in valid_indices], dtype=float)
            valid_distances = np.asarray([detected[index]["shock_distance_kpc"] for index in valid_indices], dtype=float)
            valid_uncertainties = np.asarray([detected[index]["position_uncertainty_kpc"] for index in valid_indices], dtype=float)
            valid_lookup = {snapshot_index: local_index for local_index, snapshot_index in enumerate(valid_indices)}
            for snapshot_index, snapshot in enumerate(snapshots):
                detection = detected[snapshot_index]
                base = {
                    "case": case,
                    "snapshot_index": snapshot.output_index,
                    "actual_time_myr": snapshot.actual_time_myr,
                    "side": side,
                    "velocity_threshold_factor": factor,
                    "velocity_cut_code": primary_velocity_cut_code * factor,
                    "velocity_cut_km_s": primary_velocity_cut_code * factor * UNIT_VELOCITY_CMS / 1.0e5,
                    "disturbance_threshold_fraction": disturbance_fraction,
                    "minimum_contiguous_cells": min_contiguous_cells,
                    "status": "detected" if detection is not None else "not_detected",
                }
                if detection is None:
                    rows.append(base | {
                        "shock_z_kpc": "", "shock_distance_kpc": "", "position_uncertainty_kpc": "",
                        "candidate_run_cells": "", "shock_speed_km_s": "", "shock_speed_uncertainty_km_s": "",
                        "ambient_sound_speed_km_s": "", "mach_kinematic": "", "pressure_jump_ratio": "",
                        "density_jump_ratio": "", "mach_rh_pressure": "", "mach_rh_density": "",
                    })
                    continue
                local_index = valid_lookup[snapshot_index]
                slope = local_three_point_slope(valid_times, valid_distances, valid_uncertainties, local_index)
                if slope is None:
                    speed_km_s = speed_uncertainty_km_s = sound_km_s = mach = ""
                else:
                    conversion = UNIT_LENGTH_CM / SECONDS_PER_MYR / 1.0e5
                    speed_km_s = abs(slope[0]) * conversion
                    speed_uncertainty_km_s = slope[1] * conversion
                    sound_km_s = environment.sound_speed_at_radius(
                        float(detection["shock_distance_kpc"]) * UNIT_LENGTH_CM
                    ) / 1.0e5
                    mach = speed_km_s / sound_km_s
                rows.append(base | {
                    "shock_z_kpc": detection["shock_z_kpc"],
                    "shock_distance_kpc": detection["shock_distance_kpc"],
                    "position_uncertainty_kpc": detection["position_uncertainty_kpc"],
                    "candidate_run_cells": detection["candidate_run_cells"],
                    "shock_speed_km_s": speed_km_s,
                    "shock_speed_uncertainty_km_s": speed_uncertainty_km_s,
                    "ambient_sound_speed_km_s": sound_km_s,
                    "mach_kinematic": mach,
                    "pressure_jump_ratio": detection["pressure_jump_ratio"],
                    "density_jump_ratio": detection["density_jump_ratio"],
                    "mach_rh_pressure": detection["mach_rh_pressure"] if detection["mach_rh_pressure"] is not None else "",
                    "mach_rh_density": detection["mach_rh_density"] if detection["mach_rh_density"] is not None else "",
                })
    return rows
