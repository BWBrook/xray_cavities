#!/usr/bin/env python3
"""Actual-cache PRAiSE2 versus lower-level endpoint comparison driver.

This driver is deliberately diagnostic-only.  It shares the exact Goal 051
cache rows and selection order with the lower-level adapter, preserves raw
nonfinite values, and always holds the decision while public PRAiSE2 state
trajectories remain unobservable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np
from astropy import units as u

from scripts.science import diagnose_g_lo_adiabatic_recovery as adiabatic
from scripts.science import diagnose_g_lo_stable_method_value as stable
from scripts.science import run_g_lo_radio_history_value as workflow
from scripts.science.g_lo_radio_method_value import calculate_praise_pair
from scripts.science.praise2_method_validation import (
    EMISSIVITY_UNIT,
    NUMERIC_ATOL,
    NUMERIC_RTOL,
    Praise2UnitValues,
    build_praise2_call_kwargs,
    build_praise2_particle_contract,
    compare_numeric_arrays,
    extract_praise2_outputs,
    resolve_praise2_provenance,
    state_trajectory_audit,
)


SAMPLE_SIZE = 4096
FREQUENCIES_GHZ = (0.15, 1.4)
PRESSURE_MODES = ("unsmoothed", "log_savgol")
DECISION = "HOLD"
DECISION_LABEL = "PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION"


class Praise2DiagnosticError(RuntimeError):
    """Raised when the actual-cache comparison cannot satisfy its contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_json_safe(value), indent=2, sort_keys=True) + "\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_praise2(source: Path):
    spec = importlib.util.spec_from_file_location("praise2_pinned_validation", source)
    if spec is None or spec.loader is None:
        raise Praise2DiagnosticError(f"cannot load PRAiSE2 source: {source}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise Praise2DiagnosticError("cannot import pinned PRAiSE2 source") from exc
    if not callable(getattr(module, "praise", None)):
        raise Praise2DiagnosticError("praise2.praise is not callable")
    return module


def _cache_to_contract(raw: Mapping[str, Any], mode: str) -> dict[str, Any]:
    last = np.asarray(raw["last_shock_time"])
    if last.ndim == 3 and last.shape[2] == 1:
        last = last[:, :, 0]
    return build_praise2_particle_contract(
        {
            "endpoint_ids": raw["physical_ids"],
            "times": raw["time"],
            "pressure": raw["pressure"],
            "density": raw["density"],
            "tracer": raw["tracer"],
            "last_shock_time": last,
        },
        unit_values=Praise2UnitValues(
            time=(workflow.TIME_UNIT_S * u.s).to(u.Myr),
            density=workflow.DENSITY_UNIT_KG_M3 * u.kg / u.m**3,
            pressure=workflow.PRESSURE_UNIT_PA * u.Pa,
        ),
        pressure_mode=mode,
        lst_index=2,
    )


def _group_high_level_outputs(
    raw: Mapping[str, Any],
    *,
    mode: str,
    praise2: Any,
    window_width: int = 0,
    frequencies: Sequence[float] = FREQUENCIES_GHZ,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run PRAiSE2 on identically sliced post-injection groups.

    The high-level API cannot consume leading NaN prefixes safely.  Each group
    is therefore shifted to a zero-origin time axis; subtracting the same
    offset from ``last_shock_time`` preserves every interval and shock age.
    Singleton groups use only the public lossless branch and carry the
    approved instantaneous convention as an external tag.
    """
    if window_width not in (0, 5):
        raise Praise2DiagnosticError("PRAiSE2 diagnostic window must be 0 or 5")
    frequencies = np.asarray(frequencies, dtype=float)
    if frequencies.ndim != 1 or frequencies.size == 0 or np.any(frequencies <= 0):
        raise Praise2DiagnosticError("PRAiSE2 frequencies must be a positive one-dimensional array")
    pressure = np.asarray(raw["pressure"])
    n = pressure.shape[0]
    starts = np.argmax(np.isfinite(pressure), axis=1)
    if np.any(~np.isfinite(pressure[np.arange(n), -1])):
        raise Praise2DiagnosticError("selected pressure endpoint is non-finite")
    high_values = {
        name: np.full((n, frequencies.size, 1), np.nan, dtype=float)
        for name in ("lossless", "adiabatic", "full")
    }
    provenance: dict[str, Any] = {"groups": [], "singleton_rows": []}
    for start in sorted(np.unique(starts).tolist()):
        rows = np.flatnonzero(starts == start)
        width = np.asarray(raw["time"])[start:].size
        # Keep a singleton at its absolute endpoint time so praise2's
        # uniform-time setup has a non-empty interval; multi-step groups can
        # safely use a zero-origin translation that preserves all intervals.
        offset = 0.0 if width == 1 else float(np.asarray(raw["time"])[start])
        group_last = np.asarray(raw["last_shock_time"])[rows, start:]
        # Keep a true 2-D source series so the core embeds it explicitly at
        # PRAiSE2 component 2. Only squeeze a 3-D singleton source component.
        if group_last.ndim == 3 and group_last.shape[2] == 1:
            group_last = group_last[:, :, 0]
        group_cache = {
            "endpoint_ids": np.asarray(raw["physical_ids"])[rows],
            "times": np.asarray(raw["time"])[start:] - offset,
            "pressure": np.asarray(raw["pressure"])[rows, start:],
            "density": np.asarray(raw["density"])[rows, start:],
            "tracer": np.asarray(raw["tracer"])[rows, start:],
            "last_shock_time": group_last - offset,
        }
        contract = build_praise2_particle_contract(
            group_cache,
            unit_values=Praise2UnitValues(
                # praise2 compares ``pt[-1].value`` to particle_spacing.value;
                # both must be expressed in Myr, not seconds.
                time=(workflow.TIME_UNIT_S * u.s).to(u.Myr),
                density=workflow.DENSITY_UNIT_KG_M3 * u.kg / u.m**3,
                pressure=workflow.PRESSURE_UNIT_PA * u.Pa,
            ),
            pressure_mode=mode,
            lst_index=2,
        )
        width = contract["part_data"]["pressure"].shape[1]
        endpoint_myr = float((contract["part_times"][-1] * contract["sim"].unit_values.time).to_value(u.Myr))
        if width > 1 and endpoint_myr < 0.01:
            raise Praise2DiagnosticError(
                "PRAiSE2 0.01 Myr uniform resampler cannot represent this short post-injection group"
            )
        uniform_indices = _praise2_uniform_indices(
            contract, 0.01 * u.Myr
        )
        if uniform_indices.size == 0 or int(uniform_indices[0]) != 0:
            raise Praise2DiagnosticError(
                "PRAiSE2 uniform resampler does not cover the group start"
            )
        endpoint_source_index = int(uniform_indices[-1])
        source_times_myr = (
            np.asarray(contract["part_times"], dtype=float)
            * contract["sim"].unit_values.time
        ).to_value(u.Myr)
        endpoint_lag_myr = float(source_times_myr[-1] - source_times_myr[endpoint_source_index])
        spacing_myr = 0.01
        final_source_step_myr = (
            float(source_times_myr[-1] - source_times_myr[-2]) if width > 1 else 0.0
        )
        endpoint_lag_limit_myr = max(spacing_myr, final_source_step_myr)
        lag_tolerance = np.finfo(float).eps * max(1.0, abs(endpoint_myr)) * 32
        if (
            endpoint_lag_myr < -lag_tolerance
            or endpoint_lag_myr > endpoint_lag_limit_myr + lag_tolerance
        ):
            raise Praise2DiagnosticError(
                "PRAiSE2 uniform resampler endpoint lag exceeds one source interval"
            )
        resampling_provenance = {
            "source_width": int(width),
            "uniform_width": int(uniform_indices.size),
            "omitted_source_count": int(width - uniform_indices.size),
            "endpoint_source_index": endpoint_source_index,
            "endpoint_lag_Myr": endpoint_lag_myr,
            "endpoint_lag_limit_Myr": endpoint_lag_limit_myr,
            "final_source_step_Myr": final_source_step_myr,
            "particle_spacing_Myr": spacing_myr,
        }
        if width == 1:
            kwargs = build_praise2_call_kwargs(contract, frequencies=frequencies, losses=(0,), particle_spacing=0.01 * u.Myr)
            kwargs["window_width"] = window_width
            result = praise2.praise(**kwargs)
            raw_loss = result.get("lossless", [{}])[-1].get("emis")
            if raw_loss is None:
                raise Praise2DiagnosticError("PRAiSE2 singleton lossless output is missing")
            values = np.asarray(raw_loss.to_value(EMISSIVITY_UNIT) if hasattr(raw_loss, "to_value") else raw_loss, dtype=float)
            if values.shape != (len(rows), frequencies.size, 1):
                raise Praise2DiagnosticError("PRAiSE2 singleton output shape mismatch")
            for name in high_values:
                high_values[name][rows] = values
            provenance["singleton_rows"].extend(rows.astype(int).tolist())
            provenance["groups"].append({"start": int(start), "rows": rows.astype(int).tolist(), "width": 1, "branch_policy": "external_approved_singleton_convention", "state_validation_scope": "none", "window_width": int(window_width), **resampling_provenance})
            continue
        kwargs = build_praise2_call_kwargs(contract, frequencies=frequencies, losses=(0, 1, 4), particle_spacing=0.01 * u.Myr)
        kwargs["window_width"] = window_width
        result = praise2.praise(**kwargs)
        audit = extract_praise2_outputs(
            result,
            expected_rows=len(rows),
            expected_frequencies=frequencies.size,
            expected_part_output=endpoint_source_index,
        )
        for name in high_values:
            high_values[name][rows] = audit["branches"][name]["values"]
        provenance["groups"].append({"start": int(start), "rows": rows.astype(int).tolist(), "width": int(width), "branch_policy": "direct_high_level_loss_codes_0_1_4", "state_validation_scope": "none", "window_width": int(window_width), **resampling_provenance})
    return {"branches": {name: {"values": values, "nonfinite_count": int(np.count_nonzero(~np.isfinite(values)))} for name, values in high_values.items()}}, provenance


def _praise2_uniform_indices(contract: Mapping[str, Any], particle_spacing: u.Quantity) -> np.ndarray:
    """Reproduce praise2's source-index selection before invoking the API."""
    part_times = np.asarray(contract["part_times"], dtype=float)
    time_unit = contract["sim"].unit_values.time
    pt = part_times * time_unit
    desired = np.arange(0.0, pt[-1].value, step=particle_spacing.to_value(u.Myr)) * u.Myr
    if desired.size == 0:
        return np.empty(0, dtype=np.int64)
    indices = np.argmin(np.abs(np.subtract.outer(pt.to_value(u.Myr), desired.to_value(u.Myr))), axis=0)
    if np.any(np.diff(indices) < 0):
        raise Praise2DiagnosticError("PRAiSE2 uniform source indices are not monotone")
    return np.unique(indices).astype(np.int64)


def _class(value: float) -> str:
    if np.isnan(value):
        return "nan"
    if np.isposinf(value):
        return "+inf"
    if np.isneginf(value):
        return "-inf"
    return "finite"


def _endpoint_rows(
    selection: Sequence[Mapping[str, Any]],
    high: Mapping[str, Any],
    lower: Mapping[str, Any],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in ("lossless", "adiabatic", "full"):
        lower_name = "none" if branch == "lossless" else branch
        high_values = high["branches"][branch]["values"][:, :, 0]
        lower_values = np.asarray(getattr(lower[lower_name], "value", lower[lower_name]))
        for i, selected in enumerate(selection):
            for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                hv = float(high_values[i, frequency_index])
                lv = float(lower_values[i, frequency_index])
                compared = compare_numeric_arrays(np.asarray([hv]), np.asarray([lv]), rtol=NUMERIC_RTOL, atol=NUMERIC_ATOL)
                rows.append({
                    "pressure_mode": mode,
                    "loss_branch": branch,
                    "sample_index": int(selected["sample_index"]),
                    "cache_row": int(selected["cache_row"]),
                    "physical_id": int(selected["physical_id"]),
                    "frequency_GHz": float(frequency),
                    "high_value": hv,
                    "lower_value": lv,
                    "high_class": _class(hv),
                    "lower_class": _class(lv),
                    "class_equal": _class(hv) == _class(lv),
                    "nonfinite_mask_equal": compared["nonfinite_masks_equal"],
                    "numerical_equal": compared["finite_values_equal"],
                })
    return rows


def _write_npz(path: Path, arrays: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **{key: np.asarray(value) for key, value in arrays.items()})
    temporary.replace(path)


def _array_fingerprint(arrays: Mapping[str, Any]) -> str:
    """Stable digest of endpoint arrays, retaining raw NaN/Inf bit patterns."""
    digest = hashlib.sha256()
    for name in sorted(arrays):
        value = np.asarray(arrays[name])
        digest.update(name.encode("utf-8")); digest.update(str(value.dtype).encode("ascii")); digest.update(repr(value.shape).encode("ascii"))
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def diagnose_praise2_method_validation(
    cache: Path,
    selection_csv: Path,
    output_dir: Path,
    *,
    expected_cache_sha256: str,
    expected_selection_sha256: str,
    expected_selection_count: int = SAMPLE_SIZE,
    praise2_source: Path = Path("/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py"),
    commit_proof_path: Path | None = None,
) -> dict[str, Any]:
    cache, selection_csv, output_dir = map(lambda value: Path(value).resolve(), (cache, selection_csv, output_dir))
    if not cache.is_file() or cache.is_symlink() or not selection_csv.is_file() or selection_csv.is_symlink():
        raise Praise2DiagnosticError("cache and selection must be regular files")
    cache_hash, selection_hash = _sha256(cache), _sha256(selection_csv)
    if cache_hash != expected_cache_sha256:
        raise Praise2DiagnosticError("cache SHA-256 does not match immutable input")
    if selection_hash != expected_selection_sha256:
        raise Praise2DiagnosticError("selection SHA-256 does not match immutable input")
    provenance = resolve_praise2_provenance(praise2_source, commit_proof_path=commit_proof_path)
    praise2 = _load_praise2(Path(praise2_source).resolve())
    if output_dir.exists() and (output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir())):
        raise Praise2DiagnosticError("refusing to overwrite non-empty output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
            expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
            expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
            expected_trim_single_record_overlap_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_single_record_overlap_rows"],
        )
        selected_rows, selection = stable.read_exact_selection(selection_csv, h5, expected_count=expected_selection_count)
        raw = adiabatic._read_treated_sample(h5, selected_rows, plan)
        physical, unit_provenance = workflow.convert_code_cache_to_physical(
            raw, shock_threshold=float(h5.attrs["shock_threshold"]), shock_component=int(h5.attrs["shock_component"])
        )
    if len(selection) != expected_selection_count or not np.array_equal(selected_rows, np.asarray([r["cache_row"] for r in selection], dtype=np.int64)):
        raise Praise2DiagnosticError("selection row order changed after existing reader")
    summary: dict[str, Any] = {
        "status": "diagnostic_complete",
        "decision": DECISION,
        "decision_label": DECISION_LABEL,
        "cache_sha256": cache_hash,
        "selection_sha256": selection_hash,
        "selection_count": len(selection),
        "selection_order": "exact CSV sample_index order 0..n-1",
        "provenance": provenance,
        "unit_provenance": unit_provenance,
        "tolerances": {"rtol": NUMERIC_RTOL, "atol": NUMERIC_ATOL, "identity_gates": "exact"},
        "state_observability": state_trajectory_audit(),
        "comparison_scope": "Goal049_raw_lower_level",
        "goal051_stable_comparison": {
            "implemented": False,
            "status": "not_implemented_requires_retrieved_goal051_outputs",
            "promotion_gate": "hold_until_goal051_stable_outputs_are_retrieved_and_compared",
        },
        "modes": {},
    }
    all_rows: list[dict[str, Any]] = []
    all_forensics: list[dict[str, Any]] = []
    for mode in PRESSURE_MODES:
        high_audit, group_provenance = _group_high_level_outputs(raw, mode=mode, praise2=praise2)
        lower_input = dict(physical)
        lower_result = calculate_praise_pair(
            lower_input,
            frequencies=FREQUENCIES_GHZ,
            z=workflow.PRIMARY_CONTRACT["redshift"],
            s=workflow.PRIMARY_CONTRACT["s"], eta=workflow.PRIMARY_CONTRACT["eta"],
            gmin=workflow.PRIMARY_CONTRACT["gmin"], gmax=workflow.PRIMARY_CONTRACT["gmax"],
            lst_index=0, pressure_mode=mode, diagnostic=True,
            singleton_policy="instantaneous_recent_shock", include_adiabatic=True,
        )
        rows = _endpoint_rows(selection, high_audit, lower_result, mode=mode)
        all_rows.extend(rows)
        for record in lower_result.get("nonfinite_diagnostics", {}).get("records", []):
            all_forensics.append({"pressure_mode": mode, **dict(record)})
        _write_npz(output_dir / f"praise2_{mode}_endpoint.npz", {
            "physical_ids": np.asarray([r["physical_id"] for r in selection], dtype=np.int64),
            "high_lossless": high_audit["branches"]["lossless"]["values"],
            "high_adiabatic": high_audit["branches"]["adiabatic"]["values"],
            "high_full": high_audit["branches"]["full"]["values"],
            "lower_lossless": np.asarray(getattr(lower_result["none"], "value", lower_result["none"])),
            "lower_adiabatic": np.asarray(getattr(lower_result["adiabatic"], "value", lower_result["adiabatic"])),
            "lower_full": np.asarray(getattr(lower_result["full"], "value", lower_result["full"])),
        })
        high_arrays = {name: high_audit["branches"][name]["values"] for name in ("lossless", "adiabatic", "full")}
        lower_arrays = {name: np.asarray(getattr(lower_result[key], "value", lower_result[key])) for name, key in (("lossless", "none"), ("adiabatic", "adiabatic"), ("full", "full"))}
        summary["modes"][mode] = {
            "row_count": len(rows),
            "lower_nonfinite_diagnostics": lower_result.get("nonfinite_diagnostics", {}),
            "lower_comparator": "Goal049_raw_lower_level_calculate_praise_pair",
            "high_nonfinite_counts": {name: branch["nonfinite_count"] for name, branch in high_audit["branches"].items()},
            "group_provenance": group_provenance,
            "state_validation_scope": "none",
            "single_run_fingerprints": {
                "high_level_endpoint_arrays": _array_fingerprint(high_arrays),
                "lower_level_endpoint_arrays": _array_fingerprint(lower_arrays),
                "repeat_execution": "not_run; this is a single-run fingerprint, not deterministic-repeat evidence",
            },
        }
    fields = list(all_rows[0]) if all_rows else ["pressure_mode", "loss_branch"]
    _write_csv(output_dir / "praise2_vs_goal049_raw_lower_endpoint.csv", all_rows, fields)
    forensic_fields = sorted({key for record in all_forensics for key in record}) or ["pressure_mode"]
    _write_csv(output_dir / "goal049_raw_lower_forensics.csv", all_forensics, forensic_fields)
    gate_rows = [
        {"gate": "exact_selection_order", "passed": True},
        {"gate": "input_hashes", "passed": True},
        {"gate": "pinned_praise2_provenance", "passed": True},
        {"gate": "goal051_stable_comparison_available", "passed": False},
        {"gate": "state_trajectory_observable", "passed": False},
        {"gate": "decision", "passed": False},
    ]
    _write_csv(output_dir / "praise2_gate_summary.csv", gate_rows, ("gate", "passed"))
    _write_json(output_dir / "praise2_method_validation_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--selection-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-cache-sha256", required=True)
    parser.add_argument("--expected-selection-sha256", required=True)
    parser.add_argument("--praise2-source", type=Path, default=Path("/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py"))
    parser.add_argument("--commit-proof-path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = diagnose_praise2_method_validation(**vars(args))
    except (Praise2DiagnosticError, ValueError, OSError, KeyError) as exc:
        print(f"PRAISE2_METHOD_VALIDATION_ERROR: {exc}")
        return 2
    return 3 if result.get("decision") == DECISION else 0


if __name__ == "__main__":
    raise SystemExit(main())
