#!/usr/bin/env python3
"""Last-shock-only PRAiSE/PRAiSE2 particle comparison for Goal 056."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np
from astropy import units as u
from scipy.signal import savgol_filter

from scripts.science import diagnose_g_lo_adiabatic_recovery as recovery
from scripts.science import diagnose_g_lo_full_loss_recurrence as stable_full
from scripts.science import diagnose_g_lo_stable_method_value as stable_selection
from scripts.science import diagnose_praise2_method_validation as praise2_driver
from scripts.science import run_g_lo_radio_history_value as workflow
from scripts.science.g_lo_radio_method_value import calculate_praise_pair
from scripts.science.praise2_method_validation import (
    EMISSIVITY_UNIT,
    Praise2UnitValues,
    build_praise2_call_kwargs,
    build_praise2_particle_contract,
    resolve_praise2_provenance,
)


EXPECTED_CACHE_SHA256 = "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30"
EXPECTED_SELECTION_SHA256 = "35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df"
EXPECTED_COMPARATOR_SHA256 = "5fa466a1db5450921cd4b95785c0b949a499fd4457cc62da18333061dee8ebeb"
EXPECTED_PLUTOKORE_COMMIT = "e80252cf35ff5a06166240e2867d3d485aaf6956"
EXPECTED_SELECTION_COUNT = 4096
PROJECT_FREQUENCIES_GHZ = np.asarray([0.15, 1.4])
SPECTRUM_FREQUENCIES_GHZ = np.geomspace(0.05, 10.0, 13)
MATERIAL_RATIO = 1.05
MATERIAL_ALPHA_DELTA = 0.02
DETAIL_TARGET = 12
TIME_MYR_S = float((1 * u.Myr).to_value(u.s))


class LastShockDiagnosticError(RuntimeError):
    """Raised when the comparison cannot satisfy its declared contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise LastShockDiagnosticError(f"refusing to write empty table: {path.name}")
    fields = list(rows[0])
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _write_csv_gz(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise LastShockDiagnosticError(f"refusing to write empty table: {path.name}")
    fields = list(rows[0])
    with gzip.open(path, "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def latest_shock_index(times: Any, last_shock_series: Any) -> int:
    """Return the first recorded output at or after the endpoint latest shock."""
    time = np.asarray(times, dtype=float)
    last = np.asarray(last_shock_series, dtype=float)
    if time.ndim != 1 or last.shape != time.shape or time.size == 0:
        raise LastShockDiagnosticError("time and last-shock histories must be aligned")
    finite_last = last[np.isfinite(last)]
    if finite_last.size == 0 or finite_last[-1] <= 0:
        raise LastShockDiagnosticError("particle lacks a finite positive latest shock")
    index = int(np.searchsorted(time, finite_last[-1], side="left"))
    if index >= time.size:
        raise LastShockDiagnosticError("latest shock lies after the endpoint")
    return index


def smoothing_scope(pressure: Any, times: Any, last_shock_series: Any) -> dict[str, Any]:
    """Classify whether native linear SG imports pre-shock values after the shock."""
    raw = np.asarray(pressure, dtype=float)
    time = np.asarray(times, dtype=float)
    last = np.asarray(last_shock_series, dtype=float)
    finite = np.flatnonzero(np.isfinite(raw))
    if finite.size == 0 or finite[-1] != raw.size - 1:
        raise LastShockDiagnosticError("pressure history must end in a finite value")
    start = int(finite[0])
    values = raw[start:]
    if not np.all(np.isfinite(values)):
        raise LastShockDiagnosticError("pressure history has an internal non-finite gap")
    shock = latest_shock_index(time[start:], last[start:])
    full = savgol_filter(values, 5, 3, mode="nearest")
    post_only = savgol_filter(values[shock:], 5, 3, mode="nearest")
    retained = full[shock:]
    contamination = ~np.isclose(retained, post_only, rtol=1e-12, atol=0.0)
    changed = ~np.isclose(full, values, rtol=1e-12, atol=0.0)
    return {
        "finite_start_index": start,
        "shock_index_local": shock,
        "retained_count": int(retained.size),
        "pre_shock_changed": bool(np.any(changed[:shock])),
        "retained_changed": bool(np.any(changed[shock:])),
        "retained_stencil_contaminated": bool(np.any(contamination)),
        "retained_contaminated_count": int(np.count_nonzero(contamination)),
        "retained_nonpositive_count": int(np.count_nonzero(retained <= 0)),
        "retained_min_pressure": float(np.min(retained)),
    }


def _float(row: Mapping[str, Any], key: str) -> float:
    return float(row[key])


def select_representative_particles(
    comparison_rows: Sequence[Mapping[str, Any]], *, target: int = DETAIL_TARGET
) -> list[dict[str, Any]]:
    """Select a deterministic panel covering Patrick's requested regimes."""
    if target < 8 or len(comparison_rows) < target:
        raise LastShockDiagnosticError("representative panel is too small")
    rows = [dict(row) for row in comparison_rows]
    chosen: dict[int, set[str]] = {}

    def add(row: Mapping[str, Any], reason: str) -> None:
        pid = int(row["physical_id"])
        chosen.setdefault(pid, set()).add(reason)

    brightness_key = "unsmoothed_full_0.15GHz"
    numeric_rules = (
        ("bright", brightness_key, max),
        ("faint", brightness_key, min),
        ("long_history", "history_length", max),
        ("short_history", "history_length", min),
        ("old_shock", "shock_age", max),
        ("recent_shock", "shock_age", min),
        ("high_dynamic_range", "pressure_dynamic_range_log10", max),
        ("largest_smoothing_shift", "log_endpoint_relative_difference", lambda values: max(values, key=abs)),
    )
    for reason, key, chooser in numeric_rules:
        values = [_float(row, key) for row in rows]
        selected_value = chooser(values)
        candidates = [row for row in rows if _float(row, key) == selected_value]
        add(min(candidates, key=lambda row: int(row["physical_id"])), reason)

    for flag in ("True", "False"):
        candidates = [row for row in rows if str(row["affected_linear_sg"]) == flag]
        median = sorted(candidates, key=lambda row: (_float(row, brightness_key), int(row["physical_id"])))[len(candidates) // 2]
        add(median, f"smoothing_affected_{flag.lower()}_intermediate")
    for state in ("post_injection_recent", "post_injection_older"):
        candidates = [row for row in rows if row["shock_relative_state"] == state]
        if candidates:
            add(min(candidates, key=lambda row: int(row["physical_id"])), state)

    by_pid = {int(row["physical_id"]): row for row in rows}
    if len(chosen) < target:
        for row in sorted(rows, key=lambda item: hashlib.sha256(str(item["physical_id"]).encode()).hexdigest()):
            add(row, "deterministic_hash_fill")
            if len(chosen) >= target:
                break
    ordered = sorted(chosen, key=lambda pid: (min(chosen[pid]), pid))[:target]
    return [
        {
            **by_pid[pid],
            "panel_index": index,
            "panel_reason": ";".join(sorted(chosen[pid])),
        }
        for index, pid in enumerate(ordered)
    ]


def _spectral_index(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(values[:, 1] / values[:, 0]) / math.log(1.4 / 0.15)


def _value_class(value: float) -> str:
    if np.isnan(value):
        return "nan"
    if np.isposinf(value):
        return "+inf"
    if np.isneginf(value):
        return "-inf"
    if value == 0:
        return "zero"
    return "positive" if value > 0 else "negative"


def _method_difference(left: float, right: float) -> str:
    lc, rc = _value_class(left), _value_class(right)
    if lc in {"nan", "+inf", "-inf", "negative"} or rc in {"nan", "+inf", "-inf", "negative"}:
        return "numerical_failure"
    if lc != rc:
        return "cutoff_or_zero_change"
    if lc == "zero":
        return "both_zero"
    ratio = left / right
    return "material" if ratio > MATERIAL_RATIO or ratio < 1 / MATERIAL_RATIO else "minor"


def _run_praise2_endpoint(
    raw: Mapping[str, Any], praise2: Any, *, window_width: int,
    frequencies_ghz: Sequence[float] = PROJECT_FREQUENCIES_GHZ,
) -> tuple[np.ndarray, dict[str, Any]]:
    result, provenance = praise2_driver._group_high_level_outputs(
        raw,
        mode="unsmoothed",
        praise2=praise2,
        window_width=window_width,
        frequencies=frequencies_ghz,
    )
    values = np.asarray(result["branches"]["full"]["values"], dtype=float)[:, :, 0]
    return values, provenance


def _population_rows(
    selection: Sequence[Mapping[str, Any]],
    raw: Mapping[str, Any],
    p1_values: np.ndarray,
    p2_native: np.ndarray,
    p2_common: np.ndarray,
    goal050_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    goal050 = {int(row["physical_id"]): row for row in goal050_rows}
    alpha_p1, alpha_native, alpha_common = map(_spectral_index, (p1_values, p2_native, p2_common))
    output: list[dict[str, Any]] = []
    for index, selected in enumerate(selection):
        scope = smoothing_scope(
            np.asarray(raw["pressure"])[index],
            np.asarray(raw["time"]),
            np.asarray(raw["last_shock_time"])[index].reshape(len(raw["time"]), -1)[:, 0],
        )
        pid = int(selected["physical_id"])
        stable_row = goal050[pid]
        row: dict[str, Any] = {
            "sample_index": int(selected["sample_index"]),
            "cache_row": int(selected["cache_row"]),
            "physical_id": pid,
            "analysis_weight": float(selected["analysis_weight"]),
            "history_length": int(selected["history_length"]),
            "shock_age": float(selected["shock_age"]),
            "affected_linear_sg": str(selected["affected_linear_sg"]),
            **scope,
            "praise1_alpha": float(alpha_p1[index]),
            "praise2_native_alpha": float(alpha_native[index]),
            "praise2_common_alpha": float(alpha_common[index]),
            "native_vs_praise1_alpha_delta": float(alpha_native[index] - alpha_p1[index]),
        }
        for frequency_index, label in enumerate(("0.15", "1.4")):
            p1 = float(p1_values[index, frequency_index])
            native = float(p2_native[index, frequency_index])
            common = float(p2_common[index, frequency_index])
            stable_value = float(stable_row[f"unsmoothed_full_{label}GHz"])
            row.update({
                f"praise1_{label}GHz": p1,
                f"praise2_native_{label}GHz": native,
                f"praise2_common_{label}GHz": common,
                f"goal050_stable_{label}GHz": stable_value,
                f"native_vs_praise1_{label}GHz_class": _method_difference(native, p1),
                f"common_vs_praise1_{label}GHz_class": _method_difference(common, p1),
                f"native_over_praise1_{label}GHz": native / p1 if native > 0 and p1 > 0 else None,
                f"common_over_praise1_{label}GHz": common / p1 if common > 0 and p1 > 0 else None,
            })
        output.append(row)
    return output


def _summary_rows(population: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    predicates = {
        "pressure_difference_only_before_latest_shock": lambda row: bool(row["pre_shock_changed"]) and not bool(row["retained_changed"]),
        "smoothing_stencil_enters_retained_interval": lambda row: bool(row["retained_stencil_contaminated"]),
        "retained_nonpositive_native_pressure": lambda row: int(row["retained_nonpositive_count"]) > 0,
        "native_numerical_failure": lambda row: any(row[f"native_vs_praise1_{f}GHz_class"] == "numerical_failure" for f in ("0.15", "1.4")),
        "native_cutoff_or_zero_change": lambda row: any(row[f"native_vs_praise1_{f}GHz_class"] == "cutoff_or_zero_change" for f in ("0.15", "1.4")),
        "native_material_emissivity_change": lambda row: any(row[f"native_vs_praise1_{f}GHz_class"] == "material" for f in ("0.15", "1.4")),
        "native_material_spectral_index_change": lambda row: math.isfinite(float(row["native_vs_praise1_alpha_delta"])) and abs(float(row["native_vs_praise1_alpha_delta"])) > MATERIAL_ALPHA_DELTA,
        "native_difference_after_both_methods_zero": lambda row: all(_value_class(float(row[f"praise1_{f}GHz"])) == "zero" and _value_class(float(row[f"praise2_native_{f}GHz"])) == "zero" for f in ("0.15", "1.4")),
    }
    total_weight = sum(float(row["analysis_weight"]) for row in population)
    rows = []
    for category, predicate in predicates.items():
        matching = [row for row in population if predicate(row)]
        weight = sum(float(row["analysis_weight"]) for row in matching)
        rows.append({
            "category": category,
            "particle_count": len(matching),
            "particle_fraction": len(matching) / len(population),
            "represented_weight": weight,
            "represented_weight_fraction": weight / total_weight,
        })
    return rows


def _evaluation_indices(time: np.ndarray, shock_index: int) -> list[int]:
    endpoint = len(time) - 1
    if shock_index >= endpoint:
        return [endpoint]
    first = min(shock_index + 1, endpoint)
    midpoint = first + (endpoint - first) // 2
    return sorted(set([first, midpoint, endpoint]))


def _single_particle_contract(
    raw: Mapping[str, Any], row: int
) -> tuple[dict[str, Any], int]:
    pressure = np.asarray(raw["pressure"])[row]
    start = int(np.flatnonzero(np.isfinite(pressure))[0])
    last = np.asarray(raw["last_shock_time"])[row, start:]
    if last.ndim == 2 and last.shape[1] == 1:
        last = last[:, 0]
    source_time = np.asarray(raw["time"])[start:]
    offset = 0.0 if source_time.size == 1 else float(source_time[0])
    contract = build_praise2_particle_contract(
        {
            "endpoint_ids": np.asarray([raw["physical_ids"][row]]),
            "times": source_time - offset,
            "pressure": np.asarray(raw["pressure"])[row:row + 1, start:],
            "density": np.asarray(raw["density"])[row:row + 1, start:],
            "tracer": np.asarray(raw["tracer"])[row:row + 1, start:],
            "last_shock_time": last[None, ...] - offset,
        },
        unit_values=Praise2UnitValues(
            time=(workflow.TIME_UNIT_S * u.s).to(u.Myr),
            density=workflow.DENSITY_UNIT_KG_M3 * u.kg / u.m**3,
            pressure=workflow.PRESSURE_UNIT_PA * u.Pa,
        ),
        pressure_mode="unsmoothed",
        lst_index=2,
    )
    return contract, start


def _prepare_praise2_series(
    raw: Mapping[str, Any], row: int, praise2: Any, *, window_width: int
) -> dict[str, np.ndarray]:
    """Reproduce pinned PRAiSE2 resampling before replaying its recurrence."""
    contract, start = _single_particle_contract(raw, row)
    source_indices = praise2_driver._praise2_uniform_indices(contract, 0.01 * u.Myr)
    if source_indices.size == 0:
        raise LastShockDiagnosticError("PRAiSE2 uniform resampling produced no history")
    part_data = contract["part_data"]
    time_scale = float(contract["sim"].unit_values.time.to_value(u.Myr))
    pressure_scale = float(contract["sim"].unit_values.pressure.si.value)
    density_scale = float(contract["sim"].unit_values.density.si.value)
    time = np.asarray(contract["part_times"], dtype=float)[source_indices] * time_scale
    pressure = (
        np.asarray(part_data["pressure"], dtype=float)[0, source_indices]
        * pressure_scale
    )
    density = (
        np.asarray(part_data["density"], dtype=float)[0, source_indices]
        * density_scale
    )
    praise2.bfill(pressure[None, :])
    praise2.bfill(density[None, :])
    tracer = np.asarray(part_data["tracer"], dtype=float)[0, source_indices]
    last = (
        np.asarray(part_data["last_shock_time"], dtype=float)[
            0, source_indices, int(contract["lst_index"])
        ]
        * time_scale
    )
    if window_width:
        pressure = savgol_filter(pressure, window_width, 3, mode="nearest")
        density = savgol_filter(density, window_width, 3, mode="nearest")
    source_global_indices = start + source_indices.astype(int)
    absolute_time = (
        np.asarray(raw["time"], dtype=float)[source_global_indices]
        * workflow.TIME_UNIT_S
        / TIME_MYR_S
    )
    offset_myr = float(absolute_time[0] - time[0])
    return {
        "time": time,
        "time_absolute": absolute_time,
        "pressure": pressure,
        "density": density,
        "tracer": tracer,
        "last_shock": last,
        "last_shock_absolute": last + offset_myr,
        "source_local_indices": source_indices.astype(int),
        "source_global_indices": source_global_indices,
    }


def replay_praise2(
    praise2: Any,
    series: Mapping[str, np.ndarray],
    *,
    evaluation_index: int,
    frequencies_ghz: np.ndarray,
) -> dict[str, Any]:
    """Instrument the pinned PRAiSE2 recurrence without changing its equations."""
    time = np.asarray(series["time"], dtype=float)
    pressure = np.asarray(series["pressure"], dtype=float)
    density = np.asarray(series["density"], dtype=float)
    tracer = np.asarray(series["tracer"], dtype=float)
    last_shock = float(np.asarray(series["last_shock"])[evaluation_index])
    freq_hz = np.asarray(frequencies_ghz, dtype=float) * 1e9 * 1.05
    nf = len(freq_hz)
    gc_end = float(praise2.get_adiabatic_ind(pressure[evaluation_index], density[evaluation_index]))
    current = np.asarray([
        praise2.get_gamma_larmor(pressure[evaluation_index], gc_end, 0.03, frequency)
        for frequency in freq_hz
    ])
    trajectory = np.full((evaluation_index + 1, nf), np.nan)
    trajectory[evaluation_index] = current
    gamma = current.copy()
    injection_index = evaluation_index
    classification = "finite"
    for interval in range(evaluation_index - 1, -1, -1):
        if last_shock > time[interval]:
            injection_index = interval + 1
            break
        tn = time[interval] - last_shock
        tn1 = time[interval + 1] - last_shock
        gc = float(praise2.get_adiabatic_ind(pressure[interval], density[interval]))
        ap = float(praise2.get_ap(pressure[interval], pressure[interval + 1], tn, tn1))
        a2 = float(praise2.get_a2(pressure[interval], tn, tn1, ap, gc, 0.03, 0.05, 4))
        next_gamma = np.asarray([
            praise2.get_gamma(value, tn, tn1, ap, a2, gc, 4) for value in gamma
        ])
        if np.any(~np.isfinite(next_gamma)):
            classification = "numerical_nonfinite_zero"
        next_gamma[~np.isfinite(next_gamma) | (next_gamma <= 0)] = 0.0
        trajectory[interval] = next_gamma
        gamma = next_gamma
        if not np.any(gamma > 0):
            classification = "cutoff_zero"
            break
    emissivity = np.zeros(nf)
    if np.all(gamma > 0):
        K = float(praise2.get_K(praise2.get_kappa_nonumba(2.2), 2.2, gc_end, 500.0, 1e5))
        for index, frequency in enumerate(freq_hz):
            emissivity[index] = praise2.get_emissivity(
                pressure[evaluation_index], pressure[injection_index], current[index],
                gamma[index], gc_end, 0.03, frequency, 2.2,
                tracer[evaluation_index], K,
            )
    return {
        "trajectory": trajectory,
        "current_gamma": current,
        "injection_gamma": gamma,
        "injection_index": injection_index,
        "classification": classification,
        "emissivity": emissivity,
    }


def _run_praise2_actual_single(
    raw: Mapping[str, Any], row: int, praise2: Any, *, frequencies_ghz: np.ndarray,
    evaluation_global_indices: Sequence[int], window_width: int,
) -> dict[int, np.ndarray]:
    contract, start = _single_particle_contract(raw, row)
    singleton = np.asarray(contract["part_data"]["pressure"]).shape[1] == 1
    local_indices = [int(index - start) for index in evaluation_global_indices]
    retained_indices = set(
        praise2_driver._praise2_uniform_indices(contract, 0.01 * u.Myr).astype(int).tolist()
    )
    if any(index not in retained_indices for index in local_indices):
        raise LastShockDiagnosticError(
            "requested evaluation timestep is omitted by PRAiSE2 uniform resampling"
        )
    kwargs = build_praise2_call_kwargs(
        contract,
        frequencies=frequencies_ghz,
        losses=(0,) if singleton else (4,),
        particle_spacing=0.01 * u.Myr,
    )
    kwargs["emit_outputs"] = local_indices
    kwargs["window_width"] = window_width
    result = praise2.praise(**kwargs)
    entries = result["lossless" if singleton else "full"]
    if len(entries) != len(local_indices):
        raise LastShockDiagnosticError("PRAiSE2 did not return every requested timestep")
    outputs: dict[int, np.ndarray] = {}
    for global_index, local_index, entry in zip(
        evaluation_global_indices, local_indices, entries, strict=True
    ):
        if int(entry["part_output"]) != local_index:
            raise LastShockDiagnosticError("PRAiSE2 returned a different evaluation timestep")
        outputs[int(global_index)] = np.asarray(
            entry["emis"].to_value(EMISSIVITY_UNIT), dtype=float
        )[0, :, 0]
    return outputs


def _slice_physical(physical: Mapping[str, Any], row: int, endpoint: int) -> dict[str, np.ndarray]:
    sliced: dict[str, np.ndarray] = {}
    for key, value in physical.items():
        array = np.asarray(value)
        if key == "time":
            sliced[key] = array[:endpoint + 1]
        elif key in {"position", "velocity"}:
            sliced[key] = array[row:row + 1]
        elif key in {"physical_ids", "tinj"}:
            sliced[key] = array[row:row + 1]
        elif array.ndim >= 2:
            sliced[key] = array[row:row + 1, :endpoint + 1, ...]
    return sliced


def _goal050_stable_emissivity(
    stable: Mapping[str, Any], endpoint_gamma: Any, gamma_c: Any,
    pressure: Any, shock_index: int, tracer_endpoint: float,
    *, frequencies: Sequence[float],
) -> dict[str, Any]:
    """Reconstruct finite/cutoff Goal 050 values and retain unavailable states."""
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    trajectory = np.asarray(stable["trajectory"], dtype=float)
    states = np.asarray(stable["state"])
    if (
        endpoint.ndim != 1
        or trajectory.ndim != 3
        or states.shape != trajectory.shape
        or trajectory.shape[0] != 1
        or endpoint.size != trajectory.shape[2]
        or len(frequencies) != endpoint.size
    ):
        raise LastShockDiagnosticError("Goal 050 comparator shapes are incompatible")
    injection = trajectory[0, shock_index]
    classifications = [str(value) for value in states[0, shock_index]]
    values = np.full(endpoint.size, np.nan, dtype=float)
    policies: list[str] = []
    cutoff_states = {
        stable_full.STATE_PHYSICAL_CUTOFF,
        stable_full.STATE_GAMMA_INF_CUTOFF,
        stable_full.STATE_POST_CUTOFF,
    }
    for index, (frequency, classification) in enumerate(
        zip(frequencies, classifications, strict=True)
    ):
        if classification == stable_full.STATE_SUBRELATIVISTIC:
            policies.append("unavailable_subrelativistic_gamma")
            continue
        if classification == stable_full.STATE_FINITE and not (
            math.isfinite(float(endpoint[index]))
            and math.isfinite(float(injection[index]))
        ):
            policies.append("unavailable_nonfinite_gamma")
            continue
        reconstructed = stable_full.reconstruct_full_loss_injection_emissivity(
            endpoint[index:index + 1], injection[index:index + 1],
            gamma_c, pressure, shock_index, tracer_endpoint,
            classification=classification, frequencies=(frequency,),
        )
        values[index] = float(reconstructed[0])
        policies.append(
            "explicit_cutoff_zero"
            if classification in cutoff_states
            else "finite_trajectory_reconstruction"
        )
    return {
        "values": values,
        "classifications": classifications,
        "policies": policies,
    }


def _detailed_evidence(
    raw: Mapping[str, Any], physical: Mapping[str, Any], selection: Sequence[Mapping[str, Any]],
    panel: Sequence[Mapping[str, Any]], praise2: Any,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    by_pid = {int(row["physical_id"]): index for index, row in enumerate(selection)}
    trajectory_rows: list[dict[str, Any]] = []
    spectrum_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    pressure_rows: list[dict[str, Any]] = []
    for selected in panel:
        pid = int(selected["physical_id"])
        row = by_pid[pid]
        native_series = _prepare_praise2_series(raw, row, praise2, window_width=5)
        common_series = _prepare_praise2_series(raw, row, praise2, window_width=0)
        shock_local = latest_shock_index(native_series["time"], native_series["last_shock"])
        evaluations_local = _evaluation_indices(native_series["time"], shock_local)
        evaluations_global = [
            int(native_series["source_global_indices"][value])
            for value in evaluations_local
        ]
        for local_index in range(len(native_series["time"])):
            pressure_rows.append(
                {
                    "physical_id": pid,
                    "panel_index": int(selected["panel_index"]),
                    "history_global_index": int(
                        native_series["source_global_indices"][local_index]
                    ),
                    "time_Myr": float(native_series["time_absolute"][local_index]),
                    "latest_shock_Myr": float(
                        native_series["last_shock_absolute"][-1]
                    ),
                    "interval_scope": (
                        "retained_post_shock"
                        if local_index >= shock_local
                        else "pre_shock_provenance_only"
                    ),
                    "raw_pressure_Pa": float(common_series["pressure"][local_index]),
                    "praise2_native_smoothed_pressure_Pa": float(
                        native_series["pressure"][local_index]
                    ),
                    "native_minus_raw_pressure_Pa": float(
                        native_series["pressure"][local_index]
                        - common_series["pressure"][local_index]
                    ),
                }
            )
        actual_native = _run_praise2_actual_single(
            raw, row, praise2, frequencies_ghz=SPECTRUM_FREQUENCIES_GHZ,
            evaluation_global_indices=evaluations_global, window_width=5,
        )
        actual_common = _run_praise2_actual_single(
            raw, row, praise2, frequencies_ghz=SPECTRUM_FREQUENCIES_GHZ,
            evaluation_global_indices=evaluations_global, window_width=0,
        )
        for local_eval, global_eval in zip(evaluations_local, evaluations_global, strict=True):
            native_replay = replay_praise2(
                praise2, native_series, evaluation_index=local_eval,
                frequencies_ghz=SPECTRUM_FREQUENCIES_GHZ,
            )
            common_replay = replay_praise2(
                praise2, common_series, evaluation_index=local_eval,
                frequencies_ghz=SPECTRUM_FREQUENCIES_GHZ,
            )
            p1 = calculate_praise_pair(
                _slice_physical(physical, row, global_eval),
                frequencies=SPECTRUM_FREQUENCIES_GHZ,
                pressure_mode="unsmoothed", singleton_policy="instantaneous_recent_shock",
                diagnostic=True,
            )
            p1_values = np.asarray(p1["full"].to_value(EMISSIVITY_UNIT), dtype=float)[0]
            p1_group = p1["full_info"][0]
            p1_info = p1_group["info"]
            p1_times = np.asarray(p1_info["particle_times"], dtype=float)
            p1_pressure = np.asarray(p1_info["particle_pressure"], dtype=float)
            p1_gc = np.asarray(p1_group["adiabatic_eff"], dtype=float)
            p1_shock = np.asarray(p1_group["shock_index"], dtype=int)
            stable = stable_full.stable_full_loss_trajectory(
                np.asarray(p1_info["current_lorentz"], dtype=float), p1_times,
                p1_pressure, p1_gc, p1_shock, eta=0.03, z=0.05,
            )
            stable_comparator = _goal050_stable_emissivity(
                stable,
                np.asarray(p1_info["current_lorentz"], dtype=float)[0],
                p1_gc[0], p1_pressure[0], int(p1_shock[0]),
                float(_slice_physical(physical, row, global_eval)["tracer"][0, -1]),
                frequencies=SPECTRUM_FREQUENCIES_GHZ,
            )
            validation_rows.extend([
                {
                    "physical_id": pid,
                    "evaluation_global_index": global_eval,
                    "method": "praise2_native_replay",
                    "branch_policy": (
                        "external_approved_singleton_convention"
                        if len(native_series["time_absolute"]) == 1
                        else "direct_high_level_full_loss"
                    ),
                    "max_relative_difference": float(np.max(np.abs(native_replay["emissivity"] - actual_native[global_eval]) / np.maximum(np.abs(actual_native[global_eval]), np.finfo(float).tiny))),
                    "passed": bool(np.allclose(native_replay["emissivity"], actual_native[global_eval], rtol=1e-8, atol=0.0)),
                },
                {
                    "physical_id": pid,
                    "evaluation_global_index": global_eval,
                    "method": "praise2_common_replay",
                    "branch_policy": (
                        "external_approved_singleton_convention"
                        if len(common_series["time_absolute"]) == 1
                        else "direct_high_level_full_loss"
                    ),
                    "max_relative_difference": float(np.max(np.abs(common_replay["emissivity"] - actual_common[global_eval]) / np.maximum(np.abs(actual_common[global_eval]), np.finfo(float).tiny))),
                    "passed": bool(np.allclose(common_replay["emissivity"], actual_common[global_eval], rtol=1e-8, atol=0.0)),
                },
            ])
            time_myr = float(np.asarray(physical["time"])[global_eval] / TIME_MYR_S)
            for frequency_index, frequency in enumerate(SPECTRUM_FREQUENCIES_GHZ):
                spectrum_rows.append({
                    "physical_id": pid,
                    "panel_index": int(selected["panel_index"]),
                    "evaluation_global_index": global_eval,
                    "time_Myr": time_myr,
                    "frequency_GHz": float(frequency),
                    "praise2_native": float(actual_native[global_eval][frequency_index]),
                    "praise2_common_raw": float(actual_common[global_eval][frequency_index]),
                    "praise1_native_raw": float(p1_values[frequency_index]),
                    "goal050_stable": float(
                        stable_comparator["values"][frequency_index]
                    ),
                    "goal050_stable_classification": stable_comparator[
                        "classifications"
                    ][frequency_index],
                    "goal050_stable_policy": stable_comparator["policies"][
                        frequency_index
                    ],
                    "praise2_native_over_praise1": float(actual_native[global_eval][frequency_index] / p1_values[frequency_index]) if p1_values[frequency_index] > 0 else None,
                    "praise2_native_classification": native_replay["classification"],
                })
            project_indices = [int(np.argmin(np.abs(SPECTRUM_FREQUENCIES_GHZ - frequency))) for frequency in PROJECT_FREQUENCIES_GHZ]
            for method, replay in (("praise2_native", native_replay), ("praise2_common_raw", common_replay)):
                trajectory = np.asarray(replay["trajectory"])
                for time_index in range(shock_local, local_eval + 1):
                    for frequency, frequency_index in zip(PROJECT_FREQUENCIES_GHZ, project_indices, strict=True):
                        trajectory_rows.append({
                            "physical_id": pid,
                            "panel_index": int(selected["panel_index"]),
                            "evaluation_global_index": global_eval,
                            "method": method,
                            "history_global_index": int(
                                native_series["source_global_indices"][time_index]
                            ),
                            "time_Myr": float(
                                native_series["time_absolute"][time_index]
                            ),
                            "frequency_GHz": float(frequency),
                            "lorentz_factor": float(trajectory[time_index, frequency_index]),
                            "latest_shock_Myr": float(
                                native_series["last_shock_absolute"][local_eval]
                            ),
                        })
            stable_trajectory = np.asarray(stable["trajectory"])[0]
            for time_index in range(int(p1_shock[0]), len(p1_times)):
                for frequency, frequency_index in zip(PROJECT_FREQUENCIES_GHZ, project_indices, strict=True):
                    trajectory_rows.append({
                        "physical_id": pid,
                        "panel_index": int(selected["panel_index"]),
                        "evaluation_global_index": global_eval,
                        "method": "goal050_stable",
                        "history_global_index": global_eval - len(p1_times) + 1 + time_index,
                        "time_Myr": float(p1_times[time_index] / TIME_MYR_S),
                        "frequency_GHz": float(frequency),
                        "lorentz_factor": float(stable_trajectory[time_index, frequency_index]),
                        "latest_shock_Myr": float(
                            native_series["last_shock_absolute"][local_eval]
                        ),
                    })
    return trajectory_rows, spectrum_rows, validation_rows, pressure_rows


def _first_divergence_rows(
    panel: Sequence[Mapping[str, Any]],
    spectra: Sequence[Mapping[str, Any]],
    pressure_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for selected in panel:
        pid = int(selected["physical_id"])
        particle_spectra = sorted(
            (row for row in spectra if int(row["physical_id"]) == pid),
            key=lambda row: (
                int(row["evaluation_global_index"]), float(row["frequency_GHz"])
            ),
        )
        particle_pressure = [
            row
            for row in pressure_rows
            if int(row["physical_id"]) == pid
            and row["interval_scope"] == "retained_post_shock"
        ]
        pressure_changed = any(
            not math.isclose(
                float(row["raw_pressure_Pa"]),
                float(row["praise2_native_smoothed_pressure_Pa"]),
                rel_tol=1e-12,
                abs_tol=0.0,
            )
            for row in particle_pressure
        )
        retained_nonpositive = any(
            float(row["praise2_native_smoothed_pressure_Pa"]) <= 0
            for row in particle_pressure
        )
        divergence = None
        for row in particle_spectra:
            classification = _method_difference(
                float(row["praise2_native"]), float(row["praise1_native_raw"])
            )
            if classification in {"material", "cutoff_or_zero_change", "numerical_failure"}:
                divergence = (row, classification)
                break
        if divergence is None:
            rows.append(
                {
                    "physical_id": pid,
                    "first_evaluated_divergence_global_index": None,
                    "first_evaluated_divergence_time_Myr": None,
                    "frequency_GHz": None,
                    "classification": "no_material_divergence_at_evaluated_timesteps",
                    "physical_reason": (
                        "retained_pressure_changed_but_below_output_threshold"
                        if pressure_changed
                        else "no_retained_pressure_or_material_output_divergence"
                    ),
                }
            )
            continue
        row, classification = divergence
        if retained_nonpositive:
            reason = "native_smoothed_pressure_nonpositive_in_retained_interval"
        elif pressure_changed:
            reason = "native_smoothing_and_method_recurrence_or_coefficients"
        else:
            reason = "method_recurrence_or_coefficients_on_common_raw_input"
        rows.append(
            {
                "physical_id": pid,
                "first_evaluated_divergence_global_index": int(
                    row["evaluation_global_index"]
                ),
                "first_evaluated_divergence_time_Myr": float(row["time_Myr"]),
                "frequency_GHz": float(row["frequency_GHz"]),
                "classification": classification,
                "physical_reason": reason,
            }
        )
    return rows


def _make_figures(
    output_dir: Path, panel: Sequence[Mapping[str, Any]], population: Sequence[Mapping[str, Any]],
    trajectories: Sequence[Mapping[str, Any]], spectra: Sequence[Mapping[str, Any]],
    pressure_rows: Sequence[Mapping[str, Any]],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_dir = output_dir / "figures"
    figure_dir.mkdir()
    pop_by_pid = {int(row["physical_id"]): row for row in population}
    for selected in panel:
        pid = int(selected["physical_id"])
        tr = [row for row in trajectories if int(row["physical_id"]) == pid]
        sp = [row for row in spectra if int(row["physical_id"]) == pid]
        pr = [row for row in pressure_rows if int(row["physical_id"]) == pid]
        fig, axes = plt.subplots(2, 2, figsize=(12, 9))
        axes = axes.ravel()
        endpoint_eval = max(int(row["evaluation_global_index"]) for row in sp)
        axes[0].semilogy(
            [float(row["time_Myr"]) for row in pr],
            [float(row["raw_pressure_Pa"]) for row in pr],
            color="#0072B2", label="raw",
        )
        axes[0].semilogy(
            [float(row["time_Myr"]) for row in pr],
            [float(row["praise2_native_smoothed_pressure_Pa"]) for row in pr],
            color="#D55E00", linestyle="--", label="PRAiSE2 native SG",
        )
        for method, style in (("praise2_native", "-"), ("praise2_common_raw", "--"), ("goal050_stable", ":")):
            for frequency, colour in ((0.15, "#0072B2"), (1.4, "#D55E00")):
                rows = [row for row in tr if row["method"] == method and math.isclose(float(row["frequency_GHz"]), frequency) and int(row["evaluation_global_index"]) == endpoint_eval]
                if rows:
                    axes[1].plot([float(row["time_Myr"]) for row in rows], [float(row["lorentz_factor"]) for row in rows], style, color=colour, label=f"{method} {frequency:g} GHz")
        for method, style in (("praise2_native", "-"), ("praise2_common_raw", "--"), ("praise1_native_raw", "-."), ("goal050_stable", ":")):
            for evaluation in sorted({int(row["evaluation_global_index"]) for row in sp}):
                rows = [row for row in sp if int(row["evaluation_global_index"]) == evaluation]
                if not rows:
                    continue
                values = [float(row[method]) for row in rows]
                frequencies = [float(row["frequency_GHz"]) for row in rows]
                alpha = 0.35 + 0.65 * (evaluation == endpoint_eval)
                axes[2].loglog(frequencies, values, style, alpha=alpha, label=f"{method} t={rows[0]['time_Myr']:.2f}")
                if method in {"praise2_native", "praise2_common_raw"}:
                    denominator = np.asarray(
                        [float(row["praise1_native_raw"]) for row in rows]
                    )
                    numerator = np.asarray(values)
                    ratio = np.divide(
                        numerator,
                        denominator,
                        out=np.full_like(numerator, np.nan),
                        where=denominator > 0,
                    )
                    axes[3].semilogx(
                        frequencies, ratio, style, alpha=alpha,
                        label=f"{method}/PRAiSE t={rows[0]['time_Myr']:.2f}",
                    )
        shock = float(tr[0]["latest_shock_Myr"]) if tr else None
        if shock is not None:
            for axis in axes[:2]:
                axis.axvline(shock, color="black", linewidth=1, alpha=0.6, label="latest shock")
        axes[0].set(xlabel="Simulation time (Myr)", ylabel="Pressure (Pa)")
        axes[1].set(yscale="log", xlabel="Simulation time (Myr)", ylabel="Lorentz factor")
        axes[2].set(xlabel="Frequency (GHz)", ylabel="Emissivity")
        axes[3].axhline(1.0, color="black", linewidth=1, alpha=0.5)
        axes[3].set(xlabel="Frequency (GHz)", ylabel="Method / PRAiSE emissivity")
        for axis in axes:
            axis.legend(fontsize=5, ncol=2)
        fig.suptitle(f"Particle {pid}: {selected['panel_reason']}\nretained stencil contamination={pop_by_pid[pid]['retained_stencil_contaminated']}")
        fig.tight_layout()
        fig.savefig(figure_dir / f"particle_{pid}.png", dpi=160)
        plt.close(fig)


def diagnose(
    cache: Path, selection_csv: Path, comparator_csv: Path, output_dir: Path,
    *, praise2_source: Path, commit_proof: Path | None = None,
) -> dict[str, Any]:
    cache, selection_csv, comparator_csv, output_dir = map(Path, (cache, selection_csv, comparator_csv, output_dir))
    if output_dir.exists() or output_dir.is_symlink():
        raise LastShockDiagnosticError("refusing to overwrite output directory")
    if (
        _sha256(cache) != EXPECTED_CACHE_SHA256
        or _sha256(selection_csv) != EXPECTED_SELECTION_SHA256
        or _sha256(comparator_csv) != EXPECTED_COMPARATOR_SHA256
    ):
        raise LastShockDiagnosticError(
            "immutable cache, selection, or comparator hash mismatch"
        )
    provenance = resolve_praise2_provenance(praise2_source, commit_proof_path=commit_proof)
    if provenance["commit"] != EXPECTED_PLUTOKORE_COMMIT:
        raise LastShockDiagnosticError("pinned plutokore commit mismatch")
    praise2 = praise2_driver._load_praise2(praise2_source)
    comparator = _read_csv(comparator_csv)
    with h5py.File(cache, "r") as h5:
        workflow._validate_completed_cache(h5)
        selected_rows, selection = stable_selection.read_exact_selection(selection_csv, h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
            expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
            expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
            expected_trim_single_record_overlap_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_single_record_overlap_rows"],
        )
        raw = recovery._read_treated_sample(h5, selected_rows, plan)
        physical, unit_provenance = workflow.convert_code_cache_to_physical(
            raw, shock_threshold=float(h5.attrs["shock_threshold"]),
            shock_component=int(h5.attrs["shock_component"]),
        )
    selection_ids = {int(row["physical_id"]) for row in selection}
    comparator_ids = {int(row["physical_id"]) for row in comparator}
    if (
        len(selection) != EXPECTED_SELECTION_COUNT
        or len(comparator) != EXPECTED_SELECTION_COUNT
        or selection_ids != comparator_ids
    ):
        raise LastShockDiagnosticError(
            "selection and Goal 050 comparator are not the exact aligned 4096-particle panel"
        )
    p1 = calculate_praise_pair(
        physical, frequencies=PROJECT_FREQUENCIES_GHZ, pressure_mode="unsmoothed",
        singleton_policy="instantaneous_recent_shock", diagnostic=True,
    )
    p1_values = np.asarray(p1["full"].to_value(EMISSIVITY_UNIT), dtype=float)
    p2_native, native_provenance = _run_praise2_endpoint(raw, praise2, window_width=5)
    p2_common, common_provenance = _run_praise2_endpoint(raw, praise2, window_width=0)
    population = _population_rows(selection, raw, p1_values, p2_native, p2_common, comparator)
    summary_rows = _summary_rows(population)
    panel = select_representative_particles(comparator)
    special = [row for row in population if any(row[f"native_vs_praise1_{frequency}GHz_class"] in {"numerical_failure", "cutoff_or_zero_change"} for frequency in ("0.15", "1.4"))]
    panel_ids = {int(row["physical_id"]) for row in panel}
    comparator_by_pid = {int(row["physical_id"]): row for row in comparator}
    for row in special[:2]:
        pid = int(row["physical_id"])
        if pid not in panel_ids:
            panel.append({**comparator_by_pid[pid], "panel_index": len(panel), "panel_reason": "native_zero_or_failure"})
            panel_ids.add(pid)
    trajectories, spectra, validation, pressure_rows = _detailed_evidence(
        raw, physical, selection, panel, praise2
    )
    divergence_rows = _first_divergence_rows(panel, spectra, pressure_rows)
    output_dir.mkdir(parents=True)
    _write_csv(output_dir / "representative_particle_selection.csv", panel)
    _write_csv(output_dir / "population_particle_comparison.csv", population)
    _write_csv(output_dir / "population_summary.csv", summary_rows)
    _write_csv(output_dir / "replay_validation.csv", validation)
    _write_csv(output_dir / "particle_pressure_histories.csv", pressure_rows)
    _write_csv(output_dir / "first_evaluated_divergence.csv", divergence_rows)
    _write_csv_gz(output_dir / "lorentz_trajectories.csv.gz", trajectories)
    _write_csv_gz(output_dir / "particle_spectra.csv.gz", spectra)
    _make_figures(output_dir, panel, population, trajectories, spectra, pressure_rows)
    retained_nonpositive = next(row["particle_count"] for row in summary_rows if row["category"] == "retained_nonpositive_native_pressure")
    numerical_failures = next(row["particle_count"] for row in summary_rows if row["category"] == "native_numerical_failure")
    replay_failed = sum(not bool(row["passed"]) for row in validation)
    decision = "PASS" if retained_nonpositive == numerical_failures == replay_failed == 0 else "HOLD"
    decision_label = "PRAISE2_LAST_SHOCK_USABLE_INTERPRETABLE" if decision == "PASS" else "PRAISE2_LAST_SHOCK_HOLD_FOR_REVIEW"
    result = {
        "status": "complete_diagnostic",
        "decision": decision,
        "decision_label": decision_label,
        "cache_sha256": EXPECTED_CACHE_SHA256,
        "selection_sha256": EXPECTED_SELECTION_SHA256,
        "comparator_sha256": EXPECTED_COMPARATOR_SHA256,
        "selection_count": len(selection),
        "representative_count": len(panel),
        "praise2_provenance": provenance,
        "unit_provenance": unit_provenance,
        "native_group_provenance": native_provenance,
        "common_group_provenance": common_provenance,
        "material_thresholds": {"emissivity_ratio": MATERIAL_RATIO, "spectral_index_absolute_delta": MATERIAL_ALPHA_DELTA},
        "gates": {
            "retained_native_pressure_positive": retained_nonpositive == 0,
            "no_native_numerical_failure": numerical_failures == 0,
            "instrumented_replays_match_actual_calls": replay_failed == 0,
        },
    }
    (output_dir / "last_shock_comparison_summary.json").write_text(json.dumps(_json_safe(result), indent=2, sort_keys=True) + "\n")
    print(f"decision_label={decision_label}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--selection-csv", type=Path, required=True)
    parser.add_argument("--comparator-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--praise2-source", type=Path, required=True)
    parser.add_argument("--commit-proof", type=Path)
    args = parser.parse_args()
    try:
        result = diagnose(**vars(args))
    except (LastShockDiagnosticError, OSError, ValueError) as exc:
        print(f"infrastructure_error={exc}")
        return 2
    return 0 if result["decision"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
