#!/usr/bin/env python3
"""Goal 049 deterministic adapters and local numerical gates.

This module deliberately keeps the current plutokore calls at the centre of
the calculation.  The adapters only make their input and output semantics
explicit: cache IDs are physical identifiers, histories are SI-valued, and
ray-traced path integrals are converted from per-m3 to per-m2.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from astropy import units as u
from scipy.ndimage import label as connected_components
from scipy.signal import savgol_filter
from scipy.spatial import cKDTree

from plutokore.radio.praise import (
    calculate_praise_emissivity_numba,
    get_K,
    get_a2_numba,
    get_adiabatic_eff,
    get_ap_numba,
    get_c1,
    get_emissivity_numba,
    get_gamma_larmor_numba,
    praise_inner_numba,
)
from plutokore.radio.raytracing import raytrace_particles_multiple_freq

KPC_TO_M = 3.0856775814913673e19
PRIMARY_CONTRACT = {
    "frequencies_GHz": [0.15, 1.4],
    "redshift": 0.05,
    "s": 2.2,
    "eta": 0.03,
    "gmin": 500.0,
    "gmax": 1e5,
    "pixel_size_kpc": 1.8,
    "delta_r_kpc": 0.1,
    "ray_step_sensitivity_kpc": [0.05, 0.2],
    "pressure_mode": "unsmoothed",
    "singleton_policy": "instantaneous_recent_shock",
}
PRESSURE_MODES = ("unsmoothed", "log_savgol")
SINGLETON_POLICIES = ("fail_closed", "instantaneous_recent_shock")
LOG_SAVGOL_WINDOW = 5
LOG_SAVGOL_POLYORDER = 3


def _array(cache: Mapping[str, Any], key: str) -> np.ndarray:
    if key not in cache:
        raise ValueError(f"cache is missing required field {key!r}")
    return np.array(cache[key], dtype=float, copy=True)


def _normalise_cache(
    cache: Mapping[str, Any],
    *,
    pressure_mode: str = "unsmoothed",
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray, dict[str, Any]]:
    """Validate a SI cache and make a data-dict accepted by plutokore."""
    if pressure_mode not in PRESSURE_MODES:
        raise ValueError(
            f"pressure_mode must be one of {PRESSURE_MODES}; "
            "linear-domain smoothing is prohibited"
        )
    ids_value = cache.get("physical_ids", cache.get("id"))
    if ids_value is None:
        raise ValueError("cache is missing required field 'physical_ids' or 'id'")
    raw_ids = np.asarray(ids_value)
    if raw_ids.ndim == 2:
        if raw_ids.shape[1] == 0:
            raise ValueError("physical ID history has no time columns")
        ids = raw_ids[:, -1]
        if np.any(np.isfinite(raw_ids) & (raw_ids != ids[:, None])):
            raise ValueError("physical IDs must remain constant for each row")
    elif raw_ids.ndim == 1:
        ids = raw_ids
    else:
        raise ValueError("physical_ids must be one-dimensional or (particle, time)")
    if ids.size == 0 or not np.all(np.isfinite(ids)):
        raise ValueError("physical IDs must be finite")
    if not np.all(np.equal(ids, np.floor(ids))):
        raise ValueError("physical IDs must be integer-valued")
    ids = ids.astype(np.int64)
    if np.unique(ids).size != ids.size:
        raise ValueError("physical IDs must be unique")

    time = _array(cache, "time")
    if time.ndim != 1 or time.size < 2 or not np.all(np.isfinite(time)):
        raise ValueError("time history must be finite and one-dimensional")
    if not np.all(np.diff(time) > 0):
        raise ValueError("time history must be strictly increasing")
    n, nt = ids.size, time.size
    pressure = _array(cache, "pressure")
    density = _array(cache, "density")
    tracer = _array(cache, "tracer")
    if pressure.shape != (n, nt) or density.shape != (n, nt) or tracer.shape != (n, nt):
        raise ValueError("pressure, density, and tracer histories must have shape (particle, time)")
    starts = _validate_history(pressure, "pressure", positive=True)
    density_starts = _validate_history(density, "density", positive=True)
    tracer_starts = _validate_history(tracer, "tracer")
    if not (np.array_equal(starts, density_starts) and np.array_equal(starts, tracer_starts)):
        raise ValueError("history fields have inconsistent injection prefixes")
    tinj = None
    if "tinj" in cache:
        tinj = _array(cache, "tinj")
        if tinj.shape != (n,) or not np.all(np.isfinite(tinj)):
            raise ValueError("tinj must be a finite value for every particle")
        effective_start = time[starts]
        if np.any(tinj > effective_start):
            raise ValueError("tinj must not follow the effective history start")
    last = _array(cache, "last_shock_time")
    if last.ndim == 2 and last.shape == (n, nt):
        last = last[:, :, None]
    if last.ndim != 3 or last.shape[:2] != (n, nt) or last.shape[2] < 1:
        raise ValueError("last_shock_time must have shape (particle, time, >=1)")
    last_finite = np.all(np.isfinite(last), axis=2)
    if np.any(~last_finite[np.arange(n), -1]):
        raise ValueError("last_shock_time history endpoint must be finite")
    for row, start in enumerate(starts):
        if not last_finite[row, start:].all():
            raise ValueError("last_shock_time history has an internal/post-injection NaN gap")
        if np.any(last_finite[row, :start]):
            raise ValueError("last_shock_time history has an invalid pre-injection value")
    short_smoothing_rows = 0
    if pressure_mode == "log_savgol":
        for row, start in enumerate(starts):
            segment = pressure[row, start:]
            if segment.size < LOG_SAVGOL_WINDOW:
                short_smoothing_rows += 1
            else:
                pressure[row, start:] = np.exp(
                    savgol_filter(
                        np.log(segment),
                        LOG_SAVGOL_WINDOW,
                        LOG_SAVGOL_POLYORDER,
                        mode="nearest",
                    )
                )
        _validate_history(pressure, "log-SG pressure", positive=True)

    # The actual function uses pid as a row index in shocked_mask.  Dense IDs
    # are an adapter implementation detail; the original IDs are returned.
    dense = np.broadcast_to(np.arange(n, dtype=float)[:, None], (n, nt)).copy()
    data = {
        "id": dense,
        "pressure": pressure,
        "density": density,
        "tracer": tracer,
        "last_shock_time": last,
        "time": time,
    }
    metadata = {
        "physical_ids": ids.tolist(),
        "dense_id_index": "row order 0..n-1; physical IDs retained separately",
        "time_index": int(nt - 1),
        "history_columns_used": int(nt),
        "pressure_mode": pressure_mode,
        "pressure_transform": (
            "identity"
            if pressure_mode == "unsmoothed"
            else "exp(savgol_filter(log(pressure), window=5, polyorder=3, mode=nearest))"
        ),
        "pressure_smoothing_domain": (
            "none" if pressure_mode == "unsmoothed" else "natural_log_positive_pressure"
        ),
        "pressure_smoothing_window": (
            None if pressure_mode == "unsmoothed" else LOG_SAVGOL_WINDOW
        ),
        "pressure_smoothing_polyorder": (
            None if pressure_mode == "unsmoothed" else LOG_SAVGOL_POLYORDER
        ),
        "pressure_smoothing_boundary_mode": (
            None if pressure_mode == "unsmoothed" else "nearest"
        ),
        "short_history_rows_left_unsmoothed": int(short_smoothing_rows),
        "injection_prefix_lengths": starts.tolist(),
    }
    if tinj is not None:
        metadata.update({
            "tinj": tinj.tolist(),
            "effective_start_time": time[starts].tolist(),
            "effective_start_delay": (time[starts] - tinj).tolist(),
            "injection_time_semantics": (
                "original tinj is preserved; trimmed initialization records only "
                "move the effective PRAiSE history start"
            ),
        })
    return data, ids, time, metadata


def _frequency_quantity(frequencies: Any) -> u.Quantity:
    if isinstance(frequencies, u.Quantity):
        return frequencies.to(u.GHz)
    return np.asarray(frequencies, dtype=float) * u.GHz


def _validate_history(values: np.ndarray, name: str, *, positive: bool = False) -> np.ndarray:
    """Allow only a contiguous leading pre-injection NaN prefix."""
    finite = np.isfinite(values)
    starts = np.argmax(finite, axis=1)
    if np.any(~finite[np.arange(values.shape[0]), -1]):
        raise ValueError(f"{name} history endpoint must be finite")
    for row, start in enumerate(starts):
        if not finite[row, start:].all():
            raise ValueError(f"{name} history has an internal/post-injection NaN gap")
        if positive and np.any(values[row, start:] <= 0):
            raise ValueError(f"{name} history must be positive after injection")
    return starts


def _value_class(value: float) -> str:
    if np.isnan(value):
        return "nan"
    if np.isposinf(value):
        return "+inf"
    if np.isneginf(value):
        return "-inf"
    return "finite"


def _array_replay_matches(replayed: Any, returned: Any) -> bool:
    left = np.asarray(replayed)
    right = np.asarray(returned)
    return left.shape == right.shape and np.array_equal(left, right, equal_nan=True)


def _replay_praise_group(
    group_data: Mapping[str, np.ndarray],
    *,
    frequencies: u.Quantity,
    z: float,
    s: float,
    eta: float,
    gmin: float,
    gmax: float,
    losses: str,
    lst_index: int,
    gamma_inf: float,
) -> dict[str, Any]:
    """Replay the pinned upstream state machine for forensic classification.

    This intentionally mirrors ``calculate_praise_emissivity_numba`` rather
    than approximating the shock/no-emission logic.  It is diagnostic-only;
    no emissivity is changed here.
    """
    width = group_data["time"].size
    particle_mask = ~np.isnan(group_data["id"][:, width - 1])
    pid = group_data["id"][particle_mask, :width]
    pprs = group_data["pressure"][particle_mask, :width]
    prho = group_data["density"][particle_mask, :width]
    plst = group_data["last_shock_time"][particle_mask, :width, lst_index]
    pt = group_data["time"][:width]
    ptrc = group_data["tracer"][particle_mask, :width]
    shock_dt = np.diff(pt, append=pt[-1])
    shocked_age = pt - plst
    shocked_mask = np.column_stack(
        (
            pid[:, -1],
            pt.shape[0] - np.argmax((shocked_age < shock_dt)[:, ::-1], axis=1) - 1,
        )
    )
    shocked_mask[np.isnan(shocked_mask)] = 0
    shocked_mask = shocked_mask.astype(int)
    gamma_c = get_adiabatic_eff(pprs, prho)
    frequencies_si = frequencies.si.value * (1 + z)
    current_gamma = get_gamma_larmor_numba(
        freq=frequencies_si, eta=eta, p=pprs[:, -1], gamma_c=gamma_c[:, -1]
    )
    if losses in ("adiabatic", "full"):
        ap_arr = get_ap_numba(pprs[:, :-1], pprs[:, 1:], pt[:-1], pt[1:])
    else:
        ap_arr = np.zeros(pprs[:, :-1].shape)
    if losses in ("radiative", "full"):
        a2_arr = get_a2_numba(
            eta=eta,
            p=pprs[:, :-1],
            t_n=pt[:-1],
            t_nm1=pt[1:],
            a_p=ap_arr,
            gamma_c=gamma_c[:, :-1],
            z=z,
            c1=get_c1(),
        )
    else:
        a2_arr = np.zeros_like(ap_arr)
    injection_gamma = np.full((pid.shape[0], len(frequencies_si)), np.nan, dtype=float)
    no_emission = np.full((pid.shape[0], len(frequencies_si)), -1, dtype=int)
    praise_inner_numba(
        current_gamma.copy(), pt, gamma_c, ap_arr, a2_arr, shocked_mask,
        injection_gamma, gamma_inf, no_emission,
    )
    no_emission_mask = no_emission > shocked_mask[:, 1][:, None]
    injection_gamma[no_emission_mask] = np.nan
    injection_pressure = pprs[shocked_mask[:, 0], shocked_mask[:, 1]]
    # The backward loop visits indices width-2..0.  An endpoint-valued shock
    # index is therefore an unassigned injection state, not a valid
    # no-emission classification.
    shock_valid = (
        (shocked_mask[:, 0] == np.arange(shocked_mask.shape[0]))
        & (shocked_mask[:, 1] >= 0)
        & (shocked_mask[:, 1] < width - 1)
    )
    finite_time = bool(np.all(np.isfinite(pt)))
    finite_inputs = (
        np.all(np.isfinite(pprs), axis=1)
        & np.all(np.isfinite(prho), axis=1)
        & np.all(np.isfinite(ptrc), axis=1)
        & np.all(np.isfinite(plst), axis=1)
        & np.all(np.isfinite(gamma_c), axis=1)
        & np.all(np.isfinite(current_gamma), axis=1)
        & np.all(np.isfinite(ap_arr), axis=1)
        & np.all(np.isfinite(a2_arr), axis=1)
        & np.isfinite(injection_pressure)
        & finite_time
    )
    return {
        "shocked_mask": shocked_mask,
        "no_emission": no_emission,
        "no_emission_mask": no_emission_mask,
        "ap_arr": ap_arr,
        "a2_arr": a2_arr,
        "particle_pressure": pprs,
        "endpoint_tracer": ptrc[:, -1],
        "injection_pressure": injection_pressure,
        "injection_lorentz": injection_gamma,
        "current_lorentz": current_gamma,
        "finite_inputs_dynamics": finite_inputs,
        "shock_assignment_valid": shock_valid,
    }


def _forensic_records(
    *,
    pressure_mode: str,
    losses: str,
    start_index: int,
    rows: np.ndarray,
    physical_ids: np.ndarray,
    frequencies: np.ndarray,
    values: np.ndarray,
    replay: dict[str, Any],
    matched_values: np.ndarray | None,
    returned_info: Mapping[str, Any],
) -> list[dict[str, Any]]:
    replay_ok = (
        _array_replay_matches(replay["ap_arr"], returned_info.get("ap_arr"))
        and _array_replay_matches(replay["a2_arr"], returned_info.get("a2_arr"))
        and _array_replay_matches(
            replay["current_lorentz"], returned_info.get("current_lorentz")
        )
        and _array_replay_matches(
            replay["injection_lorentz"], returned_info.get("injection_lorentz")
        )
    )
    records = []
    for local_row, global_row in enumerate(rows.tolist()):
        for freq_index, frequency in enumerate(frequencies.tolist()):
            output_class = _value_class(float(values[local_row, freq_index]))
            matched_class = (
                _value_class(float(matched_values[local_row, freq_index]))
                if matched_values is not None else None
            )
            cutoff = bool(
                losses == "full"
                and output_class == "nan"
                and replay_ok
                and bool(replay["finite_inputs_dynamics"][local_row])
                and bool(replay["shock_assignment_valid"][local_row])
                and bool(replay["no_emission_mask"][local_row, freq_index])
                and matched_class == "finite"
            )
            classification = (
                "proven_full_loss_cutoff"
                if cutoff
                else ("finite" if output_class == "finite" else "unresolved_nonfinite")
            )
            records.append({
                "pressure_mode": pressure_mode,
                "loss_branch": losses,
                "start_index": int(start_index),
                "dense_row": int(global_row),
                "physical_id": int(physical_ids[global_row]),
                "frequency_GHz": float(frequency),
                "output_class": output_class,
                "matched_lossless_output_class": matched_class,
                "replay_verified": bool(replay_ok),
                "finite_inputs_dynamics": bool(
                    replay["finite_inputs_dynamics"][local_row]
                ),
                "shock_assignment_valid": bool(
                    replay["shock_assignment_valid"][local_row]
                ),
                "shock_index": int(replay["shocked_mask"][local_row, 1]),
                "no_emission_index": int(
                    replay["no_emission"][local_row, freq_index]
                ),
                "no_emission": bool(replay["no_emission_mask"][local_row, freq_index]),
                "endpoint_pressure_Pa": float(
                    replay["particle_pressure"][local_row, -1]
                ),
                "injection_pressure_Pa": float(
                    replay["injection_pressure"][local_row]
                ),
                "endpoint_tracer": float(replay["endpoint_tracer"][local_row]),
                "current_lorentz": float(
                    replay["current_lorentz"][local_row, freq_index]
                ),
                "injection_lorentz": float(
                    replay["injection_lorentz"][local_row, freq_index]
                ),
                "classification": classification,
            })
    return records


def calculate_praise_pair(cache: Mapping[str, Any], *, frequencies: Any = (0.15, 1.4),
                          z: float = 0.05, s: float = 2.2, eta: float = 0.03,
                          gmin: float = 500.0, gmax: float = 1e5,
                          lst_index: int = 1,
                          pressure_mode: str = "unsmoothed", gamma_inf: float = 1e50,
                          diagnostic: bool = False,
                          singleton_policy: str = "fail_closed",
                          include_adiabatic: bool = False) -> dict[str, Any]:
    """Run matched actual plutokore full-loss and lossless calls."""
    if singleton_policy not in SINGLETON_POLICIES:
        raise ValueError(f"singleton_policy must be one of {SINGLETON_POLICIES}")
    data, ids, time, metadata = _normalise_cache(
        cache,
        pressure_mode=pressure_mode,
    )
    effective_lst_index = 0 if data["last_shock_time"].shape[2] == 1 else int(lst_index)
    if effective_lst_index < 0 or effective_lst_index >= data["last_shock_time"].shape[2]:
        raise ValueError("lst_index is outside the last_shock_time component range")
    freq = _frequency_quantity(frequencies)
    starts = np.asarray(metadata["injection_prefix_lengths"], dtype=int)
    full_values = np.full((len(ids), len(freq)), np.nan, dtype=float)
    none_values = np.full_like(full_values, np.nan)
    adiabatic_values = np.full_like(full_values, np.nan)
    full_info: list[dict[str, Any]] = []
    none_info: list[dict[str, Any]] = []
    adiabatic_info: list[dict[str, Any]] = []
    forensic_records: list[dict[str, Any]] = []
    single_record_ids: list[int] = []
    output_unit = u.W / (u.Hz * u.m**3 * u.sr)
    for start in sorted(np.unique(starts).tolist()):
        rows = np.flatnonzero(starts == start)
        width = data["time"].size - start
        if width <= 0:
            raise ValueError("particle injection prefix reaches beyond the endpoint")
        if width == 1:
            if singleton_policy == "fail_closed":
                raise ValueError(
                    "single-record PRAiSE history requires an explicit singleton_policy"
                )
            if "tinj" not in metadata:
                raise ValueError(
                    "instantaneous recent-shock singleton policy requires tinj"
                )
            endpoint_time = float(data["time"][-1])
            final_interval = float(data["time"][-1] - data["time"][-2])
            pressure = data["pressure"][rows, -1]
            density = data["density"][rows, -1]
            tracer = data["tracer"][rows, -1]
            last_shock = data["last_shock_time"][rows, -1, effective_lst_index]
            tinj = np.asarray(metadata["tinj"], dtype=float)[rows]
            valid_state = (
                np.isfinite(pressure)
                & (pressure > 0)
                & np.isfinite(density)
                & (density > 0)
                & np.isfinite(tracer)
                & (tracer >= 0)
                & np.isfinite(last_shock)
                & np.isfinite(tinj)
            )
            recent_shock = (
                (tinj <= last_shock)
                & (last_shock <= endpoint_time)
                & ((endpoint_time - last_shock) <= final_interval)
            )
            if not np.all(valid_state & recent_shock):
                raise ValueError(
                    "single-record instantaneous recent-shock contract failed"
                )

            frequency_si = freq.si.value * (1.0 + float(z))
            gamma_c = get_adiabatic_eff(pressure, density)
            current_gamma = get_gamma_larmor_numba(
                freq=frequency_si,
                eta=eta,
                p=pressure,
                gamma_c=gamma_c,
            )
            emissivity = get_emissivity_numba(
                s=s,
                freq=frequency_si,
                eta=eta,
                gamma_c=gamma_c,
                p=pressure,
                p_inj=pressure,
                gm=current_gamma,
                gm_inj=current_gamma,
                tracer=tracer,
                K=get_K(s, gamma_c, gmin, gmax),
            )
            if not np.all(np.isfinite(emissivity)) and not diagnostic:
                raise ValueError(
                    "single-record instantaneous convention returned non-finite emissivity"
                )
            full_values[rows] = emissivity
            none_values[rows] = emissivity
            if include_adiabatic:
                adiabatic_values[rows] = emissivity
            single_record_ids.extend(ids[rows].astype(int).tolist())
            info = {
                "particle_times": np.asarray([endpoint_time], dtype=float),
                "current_lorentz": current_gamma,
                "ap_arr": np.empty((len(rows), 0), dtype=float),
                "a2_arr": np.empty((len(rows), 0), dtype=float),
                "particle_pressure": pressure[:, None],
                "injection_lorentz": current_gamma.copy(),
                "singleton_convention": "instantaneous_recent_shock",
            }
            singleton_provenance = {
                "start_index": start,
                "rows": rows,
                "shock_index": np.zeros(len(rows), dtype=np.int64),
                "injection_pressure": pressure.copy(),
                "adiabatic_eff": gamma_c[:, None],
            }
            full_info.append({**singleton_provenance, "info": info})
            none_info.append({**singleton_provenance, "info": info})
            if include_adiabatic:
                adiabatic_info.append(
                    {**singleton_provenance, "info": info}
                )
            if diagnostic:
                # There is no shock-loop replay for a singleton, but preserve
                # its exact branch values in the same forensic record schema.
                singleton_replay = {
                    "ap_arr": info["ap_arr"],
                    "a2_arr": info["a2_arr"],
                    "current_lorentz": current_gamma,
                    "injection_lorentz": current_gamma.copy(),
                    "shocked_mask": np.column_stack(
                        (np.arange(len(rows), dtype=int),
                         np.zeros(len(rows), dtype=int))
                    ),
                    "no_emission": np.full((len(rows), len(freq)), -1, dtype=int),
                    "no_emission_mask": np.zeros((len(rows), len(freq)), dtype=bool),
                    "particle_pressure": pressure[:, None],
                    "injection_pressure": pressure.copy(),
                    "endpoint_tracer": tracer.copy(),
                    "finite_inputs_dynamics": np.isfinite(emissivity).all(axis=1),
                    "shock_assignment_valid": np.ones(len(rows), dtype=bool),
                }
                singleton_values = np.asarray(emissivity, dtype=float)
                branches = [("full", singleton_values), ("none", singleton_values)]
                if include_adiabatic:
                    branches.append(("adiabatic", singleton_values))
                for branch, branch_values in branches:
                    forensic_records.extend(_forensic_records(
                        pressure_mode=pressure_mode,
                        losses=branch,
                        start_index=start,
                        rows=rows,
                        physical_ids=ids,
                        frequencies=freq.value,
                        values=branch_values,
                        replay=singleton_replay,
                        matched_values=(
                            singleton_values if branch == "full" else None
                        ),
                        returned_info=info,
                    ))
            continue
        dense_ids = np.broadcast_to(
            np.arange(len(rows), dtype=float)[:, None],
            (len(rows), width),
        ).copy()
        group_data = {
            "id": dense_ids,
            "pressure": data["pressure"][rows, start:],
            "density": data["density"][rows, start:],
            "tracer": data["tracer"][rows, start:],
            "last_shock_time": data["last_shock_time"][rows, start:, :],
            "time": data["time"][start:],
        }
        kwargs = dict(
            frequencies=freq,
            data_dict=group_data,
            z=z,
            time_index=width - 1,
            lst_index=effective_lst_index,
            gamma_inf=gamma_inf,
            gmin=gmin,
            gmax=gmax,
            s=s,
            eta=eta,
        )
        full_group, full_group_info = calculate_praise_emissivity_numba(
            **kwargs,
            losses="full",
        )
        none_group, none_group_info = calculate_praise_emissivity_numba(
            **kwargs,
            losses="none",
        )
        if include_adiabatic:
            adiabatic_group, adiabatic_group_info = calculate_praise_emissivity_numba(
                **kwargs,
                losses="adiabatic",
            )
        full_values[rows] = full_group.to_value(output_unit)
        none_values[rows] = none_group.to_value(output_unit)
        shock_dt = np.diff(group_data["time"], append=group_data["time"][-1])
        shocked_age = (
            group_data["time"][None, :]
            - group_data["last_shock_time"][:, :, effective_lst_index]
        )
        shock_index = (
            group_data["time"].size
            - np.argmax((shocked_age < shock_dt)[:, ::-1], axis=1)
            - 1
        ).astype(np.int64)
        injection_pressure = group_data["pressure"][
            np.arange(len(rows), dtype=np.int64),
            shock_index,
        ]
        group_provenance = {
            "start_index": start,
            "rows": rows,
            "shock_index": shock_index,
            "injection_pressure": injection_pressure,
            "adiabatic_eff": get_adiabatic_eff(
                group_data["pressure"],
                group_data["density"],
            ),
        }
        full_info.append({**group_provenance, "info": full_group_info})
        none_info.append({**group_provenance, "info": none_group_info})
        if include_adiabatic:
            adiabatic_values[rows] = adiabatic_group.to_value(output_unit)
            adiabatic_info.append(
                {**group_provenance, "info": adiabatic_group_info}
            )
        if diagnostic:
            full_replay = _replay_praise_group(
                group_data, frequencies=freq, z=z, s=s, eta=eta, gmin=gmin,
                gmax=gmax, losses="full", lst_index=effective_lst_index,
                gamma_inf=gamma_inf,
            )
            none_replay = _replay_praise_group(
                group_data, frequencies=freq, z=z, s=s, eta=eta, gmin=gmin,
                gmax=gmax, losses="none", lst_index=effective_lst_index,
                gamma_inf=gamma_inf,
            )
            adiabatic_replay = None
            if include_adiabatic:
                adiabatic_replay = _replay_praise_group(
                    group_data, frequencies=freq, z=z, s=s, eta=eta,
                    gmin=gmin, gmax=gmax, losses="adiabatic",
                    lst_index=effective_lst_index, gamma_inf=gamma_inf,
                )
            forensic_records.extend(_forensic_records(
                pressure_mode=pressure_mode, losses="full", start_index=start,
                rows=rows, physical_ids=ids, frequencies=freq.value,
                values=full_group.to_value(output_unit), replay=full_replay,
                matched_values=none_group.to_value(output_unit),
                returned_info=full_group_info,
            ))
            forensic_records.extend(_forensic_records(
                pressure_mode=pressure_mode, losses="none", start_index=start,
                rows=rows, physical_ids=ids, frequencies=freq.value,
                values=none_group.to_value(output_unit), replay=none_replay,
                matched_values=None, returned_info=none_group_info,
            ))
            if include_adiabatic and adiabatic_replay is not None:
                forensic_records.extend(_forensic_records(
                    pressure_mode=pressure_mode, losses="adiabatic",
                    start_index=start, rows=rows, physical_ids=ids,
                    frequencies=freq.value,
                    values=adiabatic_group.to_value(output_unit),
                    replay=adiabatic_replay, matched_values=None,
                    returned_info=adiabatic_group_info,
                ))
    full = full_values * output_unit
    none = none_values * output_unit
    nonfinite = (
        not np.all(np.isfinite(full_values))
        or not np.all(np.isfinite(none_values))
        or (
            include_adiabatic
            and not np.all(np.isfinite(adiabatic_values))
        )
    )
    if nonfinite and not diagnostic:
        raise ValueError("PRAiSE returned non-finite endpoint emissivities")
    metadata.update({
        "frequencies_GHz": [float(x) for x in freq.value], "z": float(z),
        "s": float(s), "eta": float(eta), "gmin": float(gmin), "gmax": float(gmax),
        "lst_index": effective_lst_index, "gamma_inf": float(gamma_inf),
        "actual_function": "plutokore.radio.praise.calculate_praise_emissivity_numba",
        "injection_group_count": int(len(np.unique(starts))),
        "pre_injection_handling": "trimmed_per_first_present_output",
        "singleton_policy": singleton_policy,
        "single_record_instantaneous_count": int(len(single_record_ids)),
        "single_record_instantaneous_ids": single_record_ids,
        "loss_branches": (
            ["full", "adiabatic", "none"]
            if include_adiabatic
            else ["full", "none"]
        ),
    })
    result = {"ids": ids, "full": full, "none": none, "full_info": full_info,
              "none_info": none_info, "metadata": metadata, "time": time}
    if include_adiabatic:
        result.update({
            "adiabatic": adiabatic_values * output_unit,
            "adiabatic_info": adiabatic_info,
        })
    if diagnostic:
        result["nonfinite_diagnostics"] = {
            "records": forensic_records,
            "nonfinite": bool(nonfinite),
            "proven_full_loss_cutoff_count": int(sum(
                r["classification"] == "proven_full_loss_cutoff" for r in forensic_records
            )),
            "unresolved_nonfinite_count": int(sum(
                r["classification"] == "unresolved_nonfinite" for r in forensic_records
            )),
            "record_count": int(len(forensic_records)),
        }
    return result


praise_emissivity_pair = calculate_praise_pair


def derive_support_bound(coords: Any, *, multiplier: float = 2.0) -> float:
    coords = np.asarray(coords, dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 3 or coords.shape[0] < 2 or not np.all(np.isfinite(coords)):
        raise ValueError("coords must be finite with shape (particle, 3), with at least two particles")
    nearest = cKDTree(coords).query(coords, k=2, workers=1)[0][:, 1]
    positive = nearest[np.isfinite(nearest) & (nearest > 0)]
    if positive.size == 0:
        raise ValueError("particle cloud has no positive nearest-neighbour spacing")
    return float(multiplier * np.median(positive))


def derive_component_labels(coords: Any, *, support_bound: float | None = None) -> np.ndarray:
    """Connected components under a deterministic nearest-neighbour radius."""
    xyz = np.asarray(coords, dtype=float)
    bound = derive_support_bound(xyz) if support_bound is None else float(support_bound)
    if not np.isfinite(bound) or bound <= 0:
        raise ValueError("support_bound must be finite and positive")
    tree = cKDTree(xyz)
    parent = np.arange(xyz.shape[0])
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in sorted(tree.query_pairs(bound)):
        ri, rj = root(i), root(j)
        if ri != rj:
            parent[rj] = ri
    roots = np.array([root(i) for i in range(xyz.shape[0])])
    _, labels = np.unique(roots, return_inverse=True)
    return labels.astype(int)


def raytrace_radio(*, coords: Any, vel_vec: Any, particle_emissivities: Any,
                   grid: tuple[np.ndarray, np.ndarray], ray_depth_lim: tuple[float, float],
                   rot_mat: Any | None = None, obs_normal: Any = (0.0, 1.0, 0.0),
                   s: float = 2.2, delta_r: float = 0.1, pixel_size_kpc: float = 1.8,
                   support_bound: float | None = None, component_labels: Any | None = None,
                   view_rotation_deg: float = 0.0, kd_jobs: int = 1) -> dict[str, Any]:
    """Call actual raytracing component-wise, preventing global Delaunay bridges."""
    xyz = coords.to_value(u.kpc) if isinstance(coords, u.Quantity) else np.asarray(coords, dtype=float)
    vel = vel_vec.to_value(u.dimensionless_unscaled) if isinstance(vel_vec, u.Quantity) else np.asarray(vel_vec, dtype=float)
    emis = particle_emissivities
    if not isinstance(emis, u.Quantity):
        emis = np.asarray(emis, dtype=float) * (u.W / (u.Hz * u.m**3 * u.sr))
    if xyz.ndim != 2 or xyz.shape[1] != 3 or vel.shape != xyz.shape or emis.shape[0] != xyz.shape[0]:
        raise ValueError("coords, vel_vec, and particle_emissivities have incompatible shapes")
    if not np.all(np.isfinite(vel)) or np.any(np.linalg.norm(vel, axis=1) >= 1.0):
        raise ValueError("vel_vec must be finite dimensionless beta vectors with norm < 1")
    bound = derive_support_bound(xyz) if support_bound is None else float(support_bound)
    labels = derive_component_labels(xyz, support_bound=bound) if component_labels is None else np.asarray(component_labels)
    if labels.ndim != 1 or labels.size != xyz.shape[0]:
        raise ValueError("component_labels must have one value per particle")
    if not isinstance(kd_jobs, int) or kd_jobs == 0 or kd_jobs < -1:
        raise ValueError("kd_jobs must be -1 or a positive integer")
    if rot_mat is None:
        angle = np.deg2rad(float(view_rotation_deg))
        # Jet axis is z and the default line of sight is y; views therefore
        # rotate the ray frame in the y-z plane (about the x axis).
        rot_mat = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(angle), -np.sin(angle)], [0.0, np.sin(angle), np.cos(angle)]])
    rot = np.asarray(rot_mat, dtype=float)
    if rot.shape != (3, 3):
        raise ValueError("rot_mat must have shape (3, 3)")
    if not np.allclose(rot @ rot.T, np.eye(3), rtol=0, atol=1e-12):
        raise ValueError("rot_mat must be orthogonal")
    frame_normal = np.asarray(obs_normal, dtype=float)
    if frame_normal.shape != (3,) or not np.all(np.isfinite(frame_normal)):
        raise ValueError("obs_normal must be a finite three-vector")
    # plutokore constructs ray points as row vectors (`ray_grid @ rot`) but
    # computes the Doppler normal as a column vector (`rot @ obs_normal`).
    # Pre-compensate its input so the internal Doppler direction is exactly
    # the physical direction followed by the cast ray.
    physical_ray_normal = frame_normal @ rot
    raytracer_obs_normal = rot.T @ physical_ray_normal
    components = sorted(np.unique(labels).tolist())
    total = None
    for component in components:
        select = labels == component
        if np.count_nonzero(select) < 4:
            raise ValueError(f"component {component} has fewer than four particles for Delaunay raytracing")
        part = raytrace_particles_multiple_freq(
            grid=grid, ray_depth_lim=ray_depth_lim, rot_mat=rot, delta_r=float(delta_r),
            coords=xyz[select], vel_vec=vel[select], obs_normal=raytracer_obs_normal,
            particle_emissivities=emis[select], s=float(s), dist_upper_bound=bound,
            kd_jobs=kd_jobs, kd_impl="scipy",
        )
        total = part if total is None else total + part
    # plutokore multiplies a per-m3 emissivity by the numeric ray step.  The
    # coordinates and delta_r are in kpc, so attach the physical metre factor
    # explicitly rather than leaving the result dimensionally per-m3.
    converted = (total * (KPC_TO_M * u.m)).to(u.W / (u.Hz * u.m**2 * u.sr))
    metadata = {
        "actual_function": "plutokore.radio.raytracing.raytrace_particles_multiple_freq",
        "component_count": len(components), "support_bound_kpc": bound,
        "delta_r_kpc": float(delta_r), "pixel_size_kpc": float(pixel_size_kpc),
        "view_rotation_deg": float(view_rotation_deg), "kpc_to_m": KPC_TO_M,
        "kd_jobs": int(kd_jobs),
        "input_units": "W Hz^-1 m^-3 sr^-1", "path_length_units": "m",
        "output_units": "W Hz^-1 m^-2 sr^-1",
        "dist_upper_bound_kpc": bound, "ray_step_kpc": float(delta_r),
        "pixel_kpc": float(pixel_size_kpc), "units": "W Hz^-1 m^-2 sr^-1",
        "rotation_matrix": rot.tolist(),
        "observing_frame_normal": frame_normal.tolist(),
        "physical_ray_normal": physical_ray_normal.tolist(),
        "raytracer_obs_normal_input": raytracer_obs_normal.tolist(),
        "doppler_normal_matches_cast_ray": True,
    }
    return {"map": converted, "metadata": metadata, "component_labels": labels}


def _extent(mask: np.ndarray) -> float:
    where = np.argwhere(mask)
    if where.size == 0:
        return 0.0
    return float(max(np.ptp(where[:, 0]) + 1, np.ptp(where[:, 1]) + 1))


def compare_loss_maps(full: Any, none: Any, *, threshold: float = 0.0, frequencies: Any | None = None) -> dict[str, float | int | bool]:
    f = np.asarray(getattr(full, "value", full), dtype=float)
    n = np.asarray(getattr(none, "value", none), dtype=float)
    if f.shape != n.shape:
        raise ValueError("full and none maps must have identical shape")
    if f.ndim == 3 and frequencies is not None and f.shape[-1] == len(_frequency_quantity(frequencies)):
        f, n = np.moveaxis(f, -1, 0), np.moveaxis(n, -1, 0)
    if f.ndim == 3:
        f0, n0 = f[0], n[0]
    else:
        f0, n0 = f, n
    sf, sn = float(np.sum(np.clip(f0, 0, None))), float(np.sum(np.clip(n0, 0, None)))
    log_ratio = float(np.log10(sf / sn)) if sf > 0 and sn > 0 else float("nan")
    mf, mn = f0 > threshold, n0 > threshold
    area_f, area_n = int(mf.sum()), int(mn.sum())
    extent_f, extent_n = _extent(mf), _extent(mn)
    dice = float(2 * np.logical_and(mf, mn).sum() / (mf.sum() + mn.sum())) if (mf.sum() + mn.sum()) else 1.0
    components_f = int(connected_components(mf)[1])
    components_n = int(connected_components(mn)[1])
    spectral_change = float("nan")
    if f.ndim == 3 and f.shape[0] >= 2 and frequencies is not None:
        fr = _frequency_quantity(frequencies).value
        both_f = (f[0] > threshold) & (f[1] > threshold)
        both_n = (n[0] > threshold) & (n[1] > threshold)
        if both_f.any() and both_n.any():
            # Project convention: S_nu ∝ nu^-alpha, so a steep spectrum has
            # positive alpha.
            alpha_f = -np.log(f[1][both_f] / f[0][both_f]) / np.log(fr[1] / fr[0])
            alpha_n = -np.log(n[1][both_n] / n[0][both_n]) / np.log(fr[1] / fr[0])
            spectral_change = float(np.nanmedian(alpha_f) - np.nanmedian(alpha_n))
    return {
        "log10_luminosity_ratio": log_ratio,
        "area_fraction_change": float(area_f / area_n - 1) if area_n else float("nan"),
        "extent_fraction_change": float(extent_f / extent_n - 1) if extent_n else float("nan"),
        "spectral_index_change": spectral_change,
        "dice_change": float(1 - dice), "mask_dice": dice,
        "component_change": int(components_f != components_n),
        "components_full": components_f, "components_none": components_n,
    }


def _material(metrics: Mapping[str, Any]) -> bool:
    return any(abs(float(metrics.get(key, 0.0))) >= limit for key, limit in (
        ("log10_luminosity_ratio", 0.10), ("area_fraction_change", 0.20),
        ("extent_fraction_change", 0.20), ("spectral_index_change", 0.10),
        ("dice_change", 0.10),
    ) if np.isfinite(float(metrics.get(key, np.nan)))) or bool(metrics.get("component_change", False))


def evaluate_materiality(view_metrics: Sequence[Mapping[str, Any]], sensitivity_metrics: Sequence[Sequence[Mapping[str, Any]]], *, numerical_error: float = 0.0) -> dict[str, Any]:
    material_views = [_material(m) for m in view_metrics]
    persistence = all(any(_material(m) for m in group) for group in sensitivity_metrics) if sensitivity_metrics else True
    directional = False
    directional_keys = (("log10_luminosity_ratio", 0.10), ("area_fraction_change", 0.20),
                        ("extent_fraction_change", 0.20), ("spectral_index_change", 0.10),
                        ("dice_change", 0.10))
    for key, limit in directional_keys:
        signs = [np.sign(float(m[key])) for m in view_metrics if key in m and np.isfinite(float(m[key])) and abs(float(m[key])) >= limit]
        if len(signs) >= 2 and (sum(signs) >= 2 or sum(signs) <= -2):
            directional = True
            break
    # Component/topology changes are directionless but are still valid only
    # when they persist in two or more views.
    topology_views = sum(bool(m.get("component_change", False)) for m in view_metrics)
    directional = directional or topology_views >= 2
    effect = max((abs(float(m.get(key, 0.0))) for m in view_metrics for key, _ in directional_keys
                  if np.isfinite(float(m.get(key, np.nan)))), default=0.0)
    error_ok = float(numerical_error) <= effect / 4 if effect > 0 else float(numerical_error) == 0
    return {"positive": bool(sum(material_views) >= 2 and directional and persistence and error_ok),
            "material_views": int(sum(material_views)), "required_views": 2,
            "same_direction": directional, "persistence": persistence, "numerical_error_ok": error_ok,
            "numerical_error": float(numerical_error)}


def validate(output_dir: Path) -> dict[str, Any]:
    """Run a compact deterministic actual-function smoke gate."""
    output_dir.mkdir(parents=True, exist_ok=True)
    times = np.arange(1, 7, dtype=float) * 1e13
    n = 8
    cache = {"physical_ids": np.arange(100, 100 + n) * 7, "time": times,
             "pressure": np.ones((n, 6)) * 1e-10, "density": np.ones((n, 6)) * 1e-21,
             "tracer": np.ones((n, 6)) * 0.8, "last_shock_time": np.zeros((n, 6, 3))}
    cache["last_shock_time"][:, :, 1] = times[0] / 2
    praise = calculate_praise_pair(cache)
    cube = np.array([[x, y, z] for x in (0.0, 1.0) for y in (0.0, 1.0) for z in (0.0, 1.0)])
    coords = np.vstack((cube, cube + np.array([10.0, 0.0, 0.0])))
    labels = np.r_[np.zeros(8, dtype=int), np.ones(8, dtype=int)]
    grid = (np.arange(-1.0, 12.0), np.arange(-1.0, 3.0))
    emissivity = np.ones((16, 1)) * (u.W / (u.Hz * u.m**3 * u.sr))
    ray_maps = {}
    for step in (0.05, 0.1, 0.2):
        ray_maps[str(step)] = raytrace_radio(
            coords=coords, vel_vec=np.ones((16, 3)) * 1e-6,
            particle_emissivities=emissivity, grid=grid, ray_depth_lim=(-1.0, 2.0),
            component_labels=labels, delta_r=step,
        )["map"]
    repeat_map = raytrace_radio(
        coords=coords, vel_vec=np.ones((16, 3)) * 1e-6,
        particle_emissivities=emissivity, grid=grid, ray_depth_lim=(-1.0, 2.0),
        component_labels=labels, delta_r=0.1, kd_jobs=2,
    )["map"]
    sums = {step: float(np.sum(value.value)) for step, value in ray_maps.items()}
    convergence = abs(sums["0.05"] - sums["0.1"]) / max(abs(sums["0.1"]), np.finfo(float).tiny)
    evidence = {"contract": PRIMARY_CONTRACT, "praise": praise["metadata"],
                "full_leq_none": bool(np.all(praise["full"].value <= praise["none"].value * (1 + 1e-10))),
                "ray_repeat_max_abs": float(np.max(np.abs(ray_maps["0.1"].value - repeat_map.value))),
                "ray_worker_determinism": {"reference_workers": 1, "comparison_workers": 2},
                "ray_step_sensitivity": {"integrated_sum": sums, "fine_vs_primary_fractional_change": float(convergence),
                                          "declared_steps_kpc": [0.05, 0.1, 0.2]},
                }
    (output_dir / "g_lo_radio_method_value.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    with (output_dir / "g_lo_radio_method_value.csv").open("w", newline="") as handle:
        writer = csv.writer(handle); writer.writerow(["gate", "passed"])
        writer.writerow(["full_leq_none", evidence["full_leq_none"]])
        writer.writerow(["ray_repeat_exact", evidence["ray_repeat_max_abs"] == 0.0])
        writer.writerow(["ray_step_sensitivity_recorded", True])
    return evidence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "validate":
        validate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
