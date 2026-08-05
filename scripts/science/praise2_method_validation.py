#!/usr/bin/env python3
"""Mechanical contract and audit helpers for the high-level PRAiSE2 API.

The module is deliberately an adapter, not a replacement for ``praise2``.
It keeps the cache in its PLUTO code-unit representation until the pinned
high-level call performs the unit conversion, and it refuses to manufacture
state-trajectory evidence because PRAiSE2 does not expose those states.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from astropy import units as u
from scipy.signal import savgol_filter


EXPECTED_PRAISE2_COMMIT = "e80252cf35ff5a06166240e2867d3d485aaf6956"
EXPECTED_PRAISE2_SOURCE_SHA256 = "ad664648040c4330ce124fdde7b739b7cd701759a52569863fc79460895f9668"
DEFAULT_PRAISE2_SOURCE = Path(
    "/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py"
)
LOSS_CODES = {0: "lossless", 1: "adiabatic", 4: "full"}
PRESSURE_MODES = ("unsmoothed", "log_savgol")
LOG_SAVGOL_WINDOW = 5
LOG_SAVGOL_POLYORDER = 3
NUMERIC_RTOL = 1.0e-10
NUMERIC_ATOL = 0.0
EMISSIVITY_UNIT = u.W / (u.Hz * u.m**3 * u.sr)


class ProvenanceError(ValueError):
    """Raised when the requested high-level implementation is ambiguous."""


class OutputAuditError(ValueError):
    """Raised when a PRAiSE2 output cannot be audited without coercion."""


@dataclass(frozen=True)
class Praise2UnitValues:
    """Astropy unit facade consumed by ``praise2.praise``."""

    time: u.Quantity
    density: u.Quantity
    pressure: u.Quantity


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit_for_source(path: Path) -> str:
    # praise2.py is inside src/plutokore; walk up to the checkout root.
    # .../<checkout>/src/plutokore/radio/praise2.py
    root = path.parents[3] if len(path.parents) > 3 else path.parent
    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProvenanceError(f"cannot resolve git commit for {path}") from exc


def resolve_praise2_provenance(
    source_path: Path | str = DEFAULT_PRAISE2_SOURCE,
    *,
    expected_commit: str = EXPECTED_PRAISE2_COMMIT,
    expected_source_sha256: str = EXPECTED_PRAISE2_SOURCE_SHA256,
    commit_proof_path: Path | str | None = None,
) -> dict[str, str]:
    """Resolve and verify the exact high-level callable implementation.

    Both the source digest and the containing checkout commit are required;
    either mismatch fails closed.  Importing is performed only after the
    identity checks, and the callable's module/name are recorded explicitly.
    """
    path = Path(source_path).expanduser().resolve()
    if not path.is_file() or path.name != "praise2.py":
        raise ProvenanceError(f"PRAiSE2 source is not a file named praise2.py: {path}")
    source_sha256 = _sha256(path)
    if source_sha256 != expected_source_sha256:
        raise ProvenanceError(
            f"PRAiSE2 source SHA mismatch: {source_sha256} != {expected_source_sha256}"
        )
    proof_commit = None
    if commit_proof_path is not None:
        proof = Path(commit_proof_path).expanduser().resolve()
        if not proof.is_file() or proof.is_symlink():
            raise ProvenanceError(f"PRAiSE2 commit proof is not a regular file: {proof}")
        proof_commit = proof.read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{40}", proof_commit):
            raise ProvenanceError("PRAiSE2 commit proof must contain exactly one 40-hex commit")
    try:
        commit = _git_commit_for_source(path)
        verification = "live_git"
    except ProvenanceError:
        if proof_commit is None:
            raise
        commit = proof_commit
        verification = "staged_commit_proof"
    if proof_commit is not None and verification == "live_git" and commit != proof_commit:
        raise ProvenanceError("PRAiSE2 live Git commit disagrees with staged commit proof")
    if commit != expected_commit:
        raise ProvenanceError(f"PRAiSE2 commit mismatch: {commit} != {expected_commit}")
    spec = importlib.util.spec_from_file_location("praise2_pinned", path)
    if spec is None or spec.loader is None:
        raise ProvenanceError(f"cannot load PRAiSE2 source: {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ProvenanceError(f"cannot import pinned PRAiSE2 source: {path}") from exc
    callable_obj = getattr(module, "praise", None)
    if not callable(callable_obj):
        raise ProvenanceError("praise2.praise is not callable")
    return {
        "callable": "plutokore.radio.praise2.praise",
        "module": str(path),
        "source_sha256": source_sha256,
        "commit": commit,
        "commit_verification": verification,
    }


def loss_code_mapping(losses: int | Sequence[int] = (0, 1, 4)) -> dict[int, str]:
    """Validate and return the exact loss switches used by PRAiSE2."""
    requested = [losses] if isinstance(losses, (int, np.integer)) else list(losses)
    if not requested or any(int(code) not in LOSS_CODES for code in requested):
        raise ValueError("losses must contain only PRAiSE2 codes 0 (none), 1 (adiabatic), 4 (full)")
    if len(set(map(int, requested))) != len(requested):
        raise ValueError("losses must not contain duplicate switches")
    return {int(code): LOSS_CODES[int(code)] for code in requested}


def _required_array(cache: Mapping[str, Any], key: str) -> np.ndarray:
    if key not in cache:
        raise ValueError(f"cache is missing required field {key!r}")
    return np.asarray(cache[key])


def _map_last_shock(last: np.ndarray, n: int, nt: int, *, component: int = 2) -> tuple[np.ndarray, str]:
    if last.ndim == 2:
        if last.shape != (n, nt):
            raise ValueError("last_shock_time shape must match pressure history")
        mapped = np.full((n, nt, 3), np.nan, dtype=last.dtype)
        mapped[:, :, component] = last
        return mapped, f"singleton_source_mapped_to_component_{component}"
    if last.ndim == 3 and last.shape[:2] == (n, nt):
        if last.shape[2] <= component:
            raise ValueError("last_shock_time lacks requested PRAiSE2 component")
        return np.array(last, copy=True), "multi_component_source_preserved"
    raise ValueError("last_shock_time must have shape (particle,time) or (particle,time,component)")


def prepare_pressure_for_praise2(
    pressure: np.ndarray,
    *,
    pressure_mode: str = "unsmoothed",
) -> tuple[np.ndarray, dict[str, Any]]:
    """Prepare only pressure; high-level internal smoothing remains disabled."""
    if pressure_mode not in PRESSURE_MODES:
        raise ValueError("linear-domain smoothing is prohibited; use unsmoothed or log_savgol")
    result = np.array(pressure, dtype=float, copy=True)
    if result.ndim != 2:
        raise ValueError("pressure must be a (particle,time) array")
    if pressure_mode == "unsmoothed":
        return result, {"pressure_mode": "unsmoothed", "praise2_window_width": 0}
    for row in range(result.shape[0]):
        finite = np.isfinite(result[row])
        start = int(np.argmax(finite)) if finite.any() else result.shape[1]
        if start == result.shape[1] or not finite[start:].all() or np.any(result[row, start:] <= 0):
            raise ValueError("log_savgol requires a contiguous finite positive post-injection history")
        if result.shape[1] - start < LOG_SAVGOL_WINDOW:
            continue
        result[row, start:] = np.exp(savgol_filter(np.log(result[row, start:]), LOG_SAVGOL_WINDOW, LOG_SAVGOL_POLYORDER, mode="nearest"))
    return result, {
        "pressure_mode": "log_savgol",
        "pressure_transform": "exp(savgol_filter(log(pressure), window=5, polyorder=3, mode=nearest))",
        "praise2_window_width": 0,
        "density_smoothing": "disabled",
    }


def build_praise2_particle_contract(
    cache: Mapping[str, Any],
    *,
    unit_values: Praise2UnitValues,
    rows: Sequence[int] | None = None,
    lst_index: int = 2,
    pressure_mode: str = "unsmoothed",
) -> dict[str, Any]:
    """Build a deterministic PRAiSE2 particle call contract from cache arrays."""
    pressure = _required_array(cache, "pressure")
    density = _required_array(cache, "density")
    tracer = _required_array(cache, "tracer")
    times = _required_array(cache, "times")
    ids = _required_array(cache, "endpoint_ids")
    if pressure.ndim != 2 or density.shape != pressure.shape or tracer.shape != pressure.shape:
        raise ValueError("pressure, density, and tracer must share shape (particle,time)")
    n, nt = pressure.shape
    if times.ndim != 1 or times.size != nt or not np.all(np.isfinite(times)) or not np.all(np.diff(times) > 0):
        raise ValueError("times must be finite and strictly increasing")
    if ids.ndim != 1 or ids.size != n or np.unique(ids).size != n:
        raise ValueError("endpoint_ids must be unique and aligned to cache rows")
    if rows is None:
        selected = np.arange(n, dtype=int)
    else:
        selected = np.asarray(rows, dtype=int)
        if selected.ndim != 1 or np.any(selected < 0) or np.any(selected >= n) or np.unique(selected).size != selected.size:
            raise ValueError("rows must be unique valid cache row indices")
    last = _required_array(cache, "last_shock_time")
    mapped_last, last_semantics = _map_last_shock(last, n, nt, component=lst_index)
    selected_pressure, pressure_metadata = prepare_pressure_for_praise2(pressure[selected], pressure_mode=pressure_mode)
    part_data = {
        "pressure": selected_pressure,
        "density": np.array(density[selected], dtype=float, copy=True),
        "tracer": np.array(tracer[selected], dtype=float, copy=True),
        "last_shock_time": np.array(mapped_last[selected], dtype=float, copy=True),
    }
    sim = SimpleNamespace(unit_values=unit_values)
    return {
        "sim": sim,
        "part_data": part_data,
        "part_times": np.array(times, dtype=float, copy=True),
        "max_output": int(nt - 1),
        "emit_outputs": [int(nt - 1)],
        "physical_ids": np.array(ids[selected], copy=True),
        "selected_rows": selected.copy(),
        "lst_index": int(lst_index),
        "pressure_metadata": pressure_metadata,
        "last_shock_semantics": last_semantics,
        "praise2_window_width": 0,
    }


def build_praise2_call_kwargs(
    contract: Mapping[str, Any],
    *,
    frequencies: Sequence[float] = (0.15, 1.4),
    redshift: float = 0.05,
    eta: float = 0.03,
    s: float = 2.2,
    gmin: float = 500.0,
    gmax: float = 1.0e5,
    particle_spacing: u.Quantity = 0.01 * u.Myr,
    losses: Sequence[int] = (0, 1, 4),
) -> dict[str, Any]:
    """Materialize the exact, auditable keyword call to ``praise2.praise``."""
    mapping = loss_code_mapping(losses)
    if not isinstance(particle_spacing, u.Quantity) or not particle_spacing.unit.is_equivalent(u.Myr):
        raise ValueError("particle_spacing must be an Astropy time quantity")
    freq_ghz = np.asarray(frequencies, dtype=float)
    if freq_ghz.ndim != 1 or freq_ghz.size == 0 or np.any(~np.isfinite(freq_ghz)) or np.any(freq_ghz <= 0):
        raise ValueError("frequencies must be finite positive GHz values")
    return {
        "sim": contract["sim"],
        "part_data": contract["part_data"],
        "part_times": contract["part_times"],
        "max_output": contract["max_output"],
        "emit_outputs": contract["emit_outputs"],
        "output_system": "particles",
        "freqs": (freq_ghz * u.GHz).si.value,
        "redshift": float(redshift),
        "eta": float(eta),
        "s": float(s),
        "gmin": float(gmin),
        "gmax": float(gmax),
        "lst_index": int(contract["lst_index"]),
        "losses": list(mapping),
        "window_width": 0,
        "particle_spacing": particle_spacing.to(u.Myr),
    }


def praise2_method_parameters(call_kwargs: Mapping[str, Any]) -> dict[str, Any]:
    """Return JSON-friendly parameters separately from executable kwargs."""
    freqs = np.asarray(call_kwargs["freqs"], dtype=float)
    return {
        "loss_codes": {int(code): LOSS_CODES[int(code)] for code in call_kwargs["losses"]},
        "frequencies_GHz": (freqs * u.Hz).to_value(u.GHz).tolist(),
        "redshift": float(call_kwargs["redshift"]),
        "eta": float(call_kwargs["eta"]),
        "s": float(call_kwargs["s"]),
        "gmin": float(call_kwargs["gmin"]),
        "gmax": float(call_kwargs["gmax"]),
        "particle_spacing_Myr": float(call_kwargs["particle_spacing"].to_value(u.Myr)),
        "window_width": int(call_kwargs["window_width"]),
        "output_system": str(call_kwargs["output_system"]),
    }


def extract_praise2_outputs(
    result: Mapping[str, Any],
    *,
    expected_rows: int,
    expected_frequencies: int,
    expected_redshifts: int = 1,
    expected_part_output: int | None = None,
) -> dict[str, Any]:
    """Normalize output entries and audit shape, units, and raw nonfinites."""
    branches: dict[str, Any] = {}
    expected_shape = (expected_rows, expected_frequencies, expected_redshifts)
    for code, name in LOSS_CODES.items():
        if name not in result or not result[name]:
            raise OutputAuditError(f"PRAiSE2 result is missing branch {name!r}")
        entry = result[name][-1]
        if "emis" not in entry:
            raise OutputAuditError(f"PRAiSE2 branch {name!r} lacks emissivity")
        raw = entry["emis"]
        values = raw.to_value(EMISSIVITY_UNIT) if hasattr(raw, "to_value") else np.asarray(raw)
        values = np.asarray(values)
        if values.shape != expected_shape:
            raise OutputAuditError(f"{name} emissivity shape {values.shape} != {expected_shape}")
        part_output = int(entry.get("part_output", -1))
        if expected_part_output is not None and part_output != int(expected_part_output):
            raise OutputAuditError(
                f"{name} part_output {part_output} != expected endpoint {expected_part_output}"
            )
        classes = np.full(values.shape, "finite", dtype="U8")
        classes[np.isnan(values)] = "nan"
        classes[np.isposinf(values)] = "+inf"
        classes[np.isneginf(values)] = "-inf"
        branches[name] = {
            "values": values.copy(),
            "unit": str(getattr(raw, "unit", EMISSIVITY_UNIT)),
            "shape": list(values.shape),
            "nonfinite_count": int(np.count_nonzero(~np.isfinite(values))),
            "nonfinite_classes": classes,
            "part_output": part_output,
        }
    return {"branches": branches, "raw_nonfinites_preserved": True}


def compare_numeric_arrays(left: Any, right: Any, *, rtol: float = NUMERIC_RTOL, atol: float = NUMERIC_ATOL) -> dict[str, Any]:
    """Compare numeric arrays without coercing nonfinite values."""
    a, b = np.asarray(left), np.asarray(right)
    if a.shape != b.shape:
        return {"equal": False, "reason": "shape_mismatch", "left_shape": list(a.shape), "right_shape": list(b.shape)}
    masks_equal = np.array_equal(np.isfinite(a), np.isfinite(b))
    classes_equal = np.array_equal(_classes(a), _classes(b))
    finite_equal = np.allclose(a[np.isfinite(a)], b[np.isfinite(b)], rtol=rtol, atol=atol) if masks_equal and np.any(np.isfinite(a)) else masks_equal
    return {"equal": bool(masks_equal and classes_equal and finite_equal), "nonfinite_masks_equal": bool(masks_equal), "classes_equal": bool(classes_equal), "finite_values_equal": bool(finite_equal), "rtol": rtol, "atol": atol}


def compare_output_audits(left: Mapping[str, Any], right: Mapping[str, Any], *, rtol: float = NUMERIC_RTOL, atol: float = NUMERIC_ATOL) -> dict[str, Any]:
    """Compare normalized branches, preserving exact class and shape gates."""
    left_branches = left.get("branches", {})
    right_branches = right.get("branches", {})
    if set(left_branches) != set(right_branches):
        return {"equal": False, "reason": "branch_set_mismatch"}
    branch_comparisons = {}
    for name in sorted(left_branches):
        a, b = left_branches[name], right_branches[name]
        comparison = compare_numeric_arrays(a["values"], b["values"], rtol=rtol, atol=atol)
        comparison["part_output_equal"] = a.get("part_output") == b.get("part_output")
        comparison["unit_equal"] = a.get("unit") == b.get("unit")
        comparison["equal"] = bool(comparison["equal"] and comparison["part_output_equal"] and comparison["unit_equal"])
        branch_comparisons[name] = comparison
    return {"equal": all(item["equal"] for item in branch_comparisons.values()), "branches": branch_comparisons, "rtol": rtol, "atol": atol}


def compare_contract_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Apply exact gates to selected physical IDs and cache row order."""
    left_ids = np.asarray(left.get("physical_ids")); right_ids = np.asarray(right.get("physical_ids"))
    left_rows = np.asarray(left.get("selected_rows")); right_rows = np.asarray(right.get("selected_rows"))
    ids_equal = np.array_equal(left_ids, right_ids)
    rows_equal = np.array_equal(left_rows, right_rows)
    return {"equal": bool(ids_equal and rows_equal), "physical_ids_equal": bool(ids_equal), "selected_row_order_equal": bool(rows_equal)}


def _classes(values: np.ndarray) -> np.ndarray:
    out = np.full(values.shape, "finite", dtype="U8")
    out[np.isnan(values)] = "nan"; out[np.isposinf(values)] = "+inf"; out[np.isneginf(values)] = "-inf"
    return out


def deterministic_repeat(run: Callable[[], Any], audit: Callable[[Any], Any], *, repeats: int = 2) -> dict[str, Any]:
    """Run and audit the same call repeatedly; return fail-closed equality."""
    if repeats < 2:
        raise ValueError("repeats must be at least two")
    outputs = [audit(run()) for _ in range(repeats)]
    fingerprints = [_fingerprint(value) for value in outputs]
    equal = all(value == fingerprints[0] for value in fingerprints[1:])
    return {"repeat_count": repeats, "deterministic": bool(equal), "fingerprints": fingerprints, "audits": outputs}


def _fingerprint(value: Any) -> str:
    """Canonical digest supporting nested dictionaries and ndarray values."""
    digest = hashlib.sha256()
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            digest.update(str(key).encode("utf-8")); digest.update(_fingerprint(value[key]).encode("ascii"))
    elif isinstance(value, np.ndarray):
        digest.update(str(value.dtype).encode("ascii")); digest.update(repr(value.shape).encode("ascii"))
        if value.dtype.kind in "fc":
            digest.update(_classes(value).tobytes())
            canonical = np.nan_to_num(value, nan=0.0, posinf=0.0, neginf=0.0)
            digest.update(np.ascontiguousarray(canonical).tobytes())
        else:
            digest.update(np.ascontiguousarray(value).tobytes())
    elif isinstance(value, (list, tuple)):
        for item in value:
            digest.update(_fingerprint(item).encode("ascii"))
    else:
        digest.update(repr(value).encode("utf-8"))
    return digest.hexdigest()


def state_trajectory_audit() -> dict[str, str]:
    """Explicitly record that high-level PRAiSE2 does not expose states."""
    return {"status": "not_observable", "reason": "praise2.praise returns emissivity products only; gamma/state trajectories are not part of its public result"}


__all__ = [
    "EXPECTED_PRAISE2_COMMIT", "EXPECTED_PRAISE2_SOURCE_SHA256", "LOSS_CODES", "NUMERIC_RTOL", "NUMERIC_ATOL",
    "Praise2UnitValues", "ProvenanceError", "OutputAuditError", "resolve_praise2_provenance", "loss_code_mapping",
    "prepare_pressure_for_praise2", "build_praise2_particle_contract", "build_praise2_call_kwargs", "praise2_method_parameters", "extract_praise2_outputs", "compare_numeric_arrays", "compare_output_audits", "compare_contract_identity",
    "deterministic_repeat", "state_trajectory_audit",
]
