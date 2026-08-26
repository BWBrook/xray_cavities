#!/usr/bin/env python3
"""Build a corrected-PRAiSE2 selected-age radio surface for one case.

The retained history cache is grouped by effective injection column so each
history is evaluated once for all requested ages.  Ray tracing uses particle
coordinates from the exact PRAiSE2 source output selected for each group; an
earlier snapshot never borrows endpoint coordinates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np
from astropy import units as u

from scripts.science.g_lo_particle_history import HistoryError, parse_particle_file
from scripts.science.g_lo_radio_method_value import derive_support_bound
from scripts.science.praise2_method_validation import (
    EMISSIVITY_UNIT,
    Praise2UnitValues,
    build_praise2_call_kwargs,
    build_praise2_particle_contract,
)
from scripts.science.run_g_lo_radio_history_value import (
    DENSITY_UNIT_KG_M3,
    INTENSITY_UNIT,
    KPC_TO_M,
    PRESSURE_TREATMENT_CONTRACT,
    PRESSURE_UNIT_PA,
    TIME_UNIT_S,
    _component_labels_from_original_z,
    _raytrace_component_cropped,
    _validate_completed_cache,
    build_pressure_treatment_plan,
)


SNAPSHOT_INDICES = (10, 20, 30, 40, 50)
PARTICLE_OUTPUTS = (1000, 2000, 3000, 4000, 5000)
FREQUENCIES_GHZ = np.asarray((0.15, 0.5, 1.4, 4.5, 15.0), dtype=float)
VIEWS_DEG = (0.0, 45.0, 90.0)
PRIMARY_VIEW_DEG = 45.0
RED_SHIFT = 0.05
ETA = 0.03
S = 2.2
GMIN = 500.0
GMAX = 1.0e5
PARTICLE_SPACING_MYR = 0.01
PRAISE2_WINDOW_WIDTH = 5
PIXEL_SIZE_KPC = 1.8
RAY_STEP_KPC = 0.1
EXPECTED_PRAISE2_COMMIT = "73210e15d4c60e77ffb317b3ee2b9209c049edd4"
EXPECTED_PRAISE2_SOURCE_SHA256 = (
    "eeee367581829b4dd779992c6b582a1676b796fc792b0bb70b8e9c13ee193895"
)


class SnapshotRadioError(RuntimeError):
    """Raised when causal matching, PRAiSE2, or ray tracing fails closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    def safe(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(key): safe(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [safe(child) for child in item]
        if isinstance(item, np.ndarray):
            return safe(item.tolist())
        if isinstance(item, np.generic):
            return safe(item.item())
        if isinstance(item, Path):
            return str(item)
        return item

    path.write_text(json.dumps(safe(value), indent=2, sort_keys=True) + "\n")


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise SnapshotRadioError(f"refusing to write empty table: {path.name}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def load_praise2(source: Path, commit_proof: Path) -> tuple[Any, dict[str, Any]]:
    source = Path(source).resolve()
    commit_proof = Path(commit_proof).resolve()
    source_hash = sha256_file(source)
    commit = commit_proof.read_text().strip()
    if source.name != "praise2.py" or source_hash != EXPECTED_PRAISE2_SOURCE_SHA256:
        raise SnapshotRadioError("corrected PRAiSE2 source identity mismatch")
    if commit != EXPECTED_PRAISE2_COMMIT:
        raise SnapshotRadioError("corrected PRAiSE2 commit proof mismatch")
    spec = importlib.util.spec_from_file_location("goal058_corrected_praise2", source)
    if spec is None or spec.loader is None:
        raise SnapshotRadioError("cannot load corrected PRAiSE2 source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "praise", None)):
        raise SnapshotRadioError("corrected PRAiSE2 source lacks praise()")
    return module, {
        "callable": "plutokore.radio.praise2.praise",
        "source": str(source),
        "source_sha256": source_hash,
        "commit": commit,
        "commit_verification": "staged_commit_proof",
    }


def load_fluid_times(path: Path, *, case: str) -> dict[int, float]:
    with Path(path).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    times = {
        int(row["snapshot_index"]): float(row["actual_time_myr"])
        for row in rows
        if row.get("case") == case
        and int(row["snapshot_index"]) in SNAPSHOT_INDICES
    }
    if set(times) != set(SNAPSHOT_INDICES) or any(
        not math.isfinite(value) for value in times.values()
    ):
        raise SnapshotRadioError(
            f"fluid manifest lacks the five selected radio snapshots for {case}"
        )
    return times


def effective_start_columns(plan: Mapping[str, Any], output_count: int) -> np.ndarray:
    records = np.asarray(plan["effective_history_records"], dtype=np.int64)
    active = np.asarray(plan["active_mask"], dtype=bool)
    if records.ndim != 1 or active.shape != records.shape:
        raise SnapshotRadioError("pressure-treatment arrays do not align")
    starts = np.full(records.shape, -1, dtype=np.int64)
    starts[active] = int(output_count) - records[active]
    if np.any(starts[active] < 0) or np.any(starts[active] >= output_count):
        raise SnapshotRadioError("effective history start is outside the cache")
    return starts


def adiabatic_index(pressure_pa: np.ndarray, density_kg_m3: np.ndarray) -> np.ndarray:
    theta = pressure_pa / (density_kg_m3 * 299792458.0**2)
    enthalpy = 2.5 * theta + np.sqrt(2.25 * theta**2 + 1.0)
    return (enthalpy - 1.0) / (enthalpy - 1.0 - theta)


def magnetic_field_ug(pressure_code: np.ndarray, density_code: np.ndarray) -> np.ndarray:
    pressure_pa = np.asarray(pressure_code, dtype=float) * PRESSURE_UNIT_PA
    density_si = np.asarray(density_code, dtype=float) * DENSITY_UNIT_KG_M3
    if np.any(pressure_pa <= 0.0) or np.any(density_si <= 0.0):
        raise SnapshotRadioError("magnetic-field state must have positive pressure and density")
    gamma_c = adiabatic_index(pressure_pa, density_si)
    energy_density = ETA * pressure_pa / ((gamma_c - 1.0) * (ETA + 1.0))
    field_tesla = np.sqrt(2.0 * 1.25663706212e-6 * energy_density)
    result = field_tesla * 1.0e10
    if np.any(~np.isfinite(result)) or np.any(result <= 0.0):
        raise SnapshotRadioError("model magnetic field is non-finite or non-positive")
    return result


def audit_branch_entry(
    entry: Mapping[str, Any],
    *,
    rows: int,
    target_relative: int,
    require_finite: bool = True,
) -> tuple[np.ndarray, int]:
    if "emis" not in entry or "part_output" not in entry:
        raise SnapshotRadioError("PRAiSE2 branch entry is incomplete")
    values = entry["emis"]
    values = values.to_value(EMISSIVITY_UNIT) if hasattr(values, "to_value") else values
    values = np.asarray(values, dtype=np.float64)
    if values.shape != (rows, len(FREQUENCIES_GHZ), 1):
        raise SnapshotRadioError(f"unexpected PRAiSE2 emissivity shape: {values.shape}")
    values = values[:, :, 0]
    if require_finite and (np.any(~np.isfinite(values)) or np.any(values < 0.0)):
        raise SnapshotRadioError("PRAiSE2 returned non-finite or negative emissivity")
    source_relative = int(entry["part_output"])
    if source_relative < 0 or source_relative > target_relative:
        raise SnapshotRadioError("PRAiSE2 selected future particle information")
    return values, source_relative


def run_praise_group(
    *,
    h5: h5py.File,
    rows: np.ndarray,
    start_column: int,
    target_columns: Sequence[int],
    praise2: Any,
) -> dict[int, dict[str, Any]]:
    rows = np.asarray(rows, dtype=np.int64)
    target_columns = tuple(int(value) for value in target_columns if value >= start_column)
    if rows.size == 0 or not target_columns:
        return {}
    times = np.asarray(h5["times"][start_column:], dtype=np.float64)
    pressure = np.asarray(h5["pressure"][rows, start_column:], dtype=np.float64)
    density = np.asarray(h5["density"][rows, start_column:], dtype=np.float64)
    tracer = np.asarray(h5["tracer"][rows, start_column:], dtype=np.float64)
    last = np.asarray(h5["last_shock_time"][rows, start_column:], dtype=np.float64)
    if any(array.shape != pressure.shape for array in (density, tracer, last)):
        raise SnapshotRadioError("group histories do not align")
    if np.any(~np.isfinite(pressure)) or np.any(pressure <= 0.0):
        raise SnapshotRadioError("effective group pressure is not a positive finite suffix")
    contract = build_praise2_particle_contract(
        {
            "endpoint_ids": np.asarray(h5["endpoint_ids"][rows], dtype=np.int64),
            # Preserve the native absolute simulation clock. Grouping is only
            # a memory strategy; it must not alter the published API's time
            # grid or turn an injection shock at t>0 into lst==0.
            "times": times,
            "pressure": pressure,
            "density": density,
            "tracer": tracer,
            "last_shock_time": last,
        },
        unit_values=Praise2UnitValues(
            time=(TIME_UNIT_S * u.s).to(u.Myr),
            density=DENSITY_UNIT_KG_M3 * u.kg / u.m**3,
            pressure=PRESSURE_UNIT_PA * u.Pa,
        ),
        pressure_mode="unsmoothed",
        lst_index=2,
    )
    relative_targets = [column - start_column for column in target_columns]
    kwargs = build_praise2_call_kwargs(
        contract,
        frequencies=FREQUENCIES_GHZ,
        redshift=RED_SHIFT,
        eta=ETA,
        s=S,
        gmin=GMIN,
        gmax=GMAX,
        particle_spacing=PARTICLE_SPACING_MYR * u.Myr,
        losses=(0, 4),
    )
    kwargs["emit_outputs"] = relative_targets
    kwargs["window_width"] = PRAISE2_WINDOW_WIDTH
    result = praise2.praise(**kwargs)
    lossless_entries = result.get("lossless", [])
    full_entries = result.get("full", [])
    if len(lossless_entries) != len(target_columns) or len(full_entries) != len(target_columns):
        raise SnapshotRadioError("PRAiSE2 output count differs from requested snapshots")
    output: dict[int, dict[str, Any]] = {}
    for target, relative, lossless_entry, full_entry in zip(
        target_columns, relative_targets, lossless_entries, full_entries, strict=True
    ):
        lossless, lossless_source = audit_branch_entry(
            lossless_entry, rows=len(rows), target_relative=relative
        )
        full, full_source = audit_branch_entry(
            full_entry,
            rows=len(rows),
            target_relative=relative,
            require_finite=relative != 0,
        )
        if lossless_source != full_source:
            raise SnapshotRadioError("PRAiSE2 loss branches selected different source outputs")
        singleton = relative == 0
        if singleton:
            full = lossless.copy()
        pressure_at_source = pressure[:, lossless_source]
        density_at_source = density[:, lossless_source]
        output[target] = {
            "lossless": lossless,
            "full": full,
            "source_column": start_column + lossless_source,
            "magnetic_field_ug": magnetic_field_ug(pressure_at_source, density_at_source),
            "singleton_external_convention": singleton,
        }
    return output


def cache_identity(h5: h5py.File, path: Path, target_columns: Sequence[int]) -> dict[str, Any]:
    return {
        "cache_path": str(Path(path).resolve()),
        "cache_sha256": sha256_file(path),
        "endpoint_ids_sha256": hashlib.sha256(h5["endpoint_ids"][:].tobytes()).hexdigest(),
        "target_columns": list(map(int, target_columns)),
        "frequencies_ghz": FREQUENCIES_GHZ.tolist(),
        "praise2_commit": EXPECTED_PRAISE2_COMMIT,
        "praise2_window_width": PRAISE2_WINDOW_WIDTH,
    }


def prepare_emissivity_store(
    path: Path,
    *,
    identity: Mapping[str, Any],
    target_columns: Sequence[int],
    particle_count: int,
    output_count: int,
    resume: bool,
) -> h5py.File:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not resume:
        raise SnapshotRadioError(f"refusing to overwrite emissivity store: {path}")
    h5 = h5py.File(path, "a")
    encoded = json.dumps(dict(identity), sort_keys=True)
    if "identity" in h5.attrs:
        if h5.attrs["identity"] != encoded:
            h5.close()
            raise SnapshotRadioError("resume emissivity-store identity mismatch")
        return h5
    h5.attrs["identity"] = encoded
    h5.create_dataset("target_columns", data=np.asarray(target_columns, dtype=np.int64))
    chunks = (1, min(2048, particle_count), len(FREQUENCIES_GHZ))
    for name in ("lossless", "full"):
        h5.create_dataset(
            name,
            shape=(len(target_columns), particle_count, len(FREQUENCIES_GHZ)),
            dtype="f8",
            chunks=chunks,
            fillvalue=np.nan,
        )
    h5.create_dataset(
        "magnetic_field_ug",
        shape=(len(target_columns), particle_count),
        dtype="f8",
        chunks=(1, min(4096, particle_count)),
        fillvalue=np.nan,
    )
    h5.create_dataset(
        "source_column",
        shape=(len(target_columns), particle_count),
        dtype="i4",
        chunks=(1, min(4096, particle_count)),
        fillvalue=-1,
    )
    h5.create_dataset(
        "active",
        shape=(len(target_columns), particle_count),
        dtype="bool",
        chunks=(1, min(4096, particle_count)),
        fillvalue=False,
    )
    h5.create_dataset("completed_start", shape=(output_count,), dtype="bool", fillvalue=False)
    h5.flush()
    return h5


def build_emissivity_store(
    cache: Path,
    store_path: Path,
    praise2: Any,
    *,
    resume: bool,
) -> dict[str, Any]:
    cache = Path(cache)
    with h5py.File(cache, "r") as source:
        complete = _validate_completed_cache(source)
        output_indices = np.asarray(source["output_indices"][:], dtype=np.int64)
        if not np.array_equal(output_indices, np.arange(len(output_indices))):
            raise SnapshotRadioError("history cache output indices are not the canonical 0..5000 chain")
        target_columns = [int(np.flatnonzero(output_indices == value)[0]) for value in PARTICLE_OUTPUTS]
        plan = build_pressure_treatment_plan(
            source,
            expected_trim_rows=PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
            expected_no_positive_rows=PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
            expected_single_record_rows=PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
            expected_trim_single_record_overlap_rows=PRESSURE_TREATMENT_CONTRACT[
                "expected_trim_single_record_overlap_rows"
            ],
            enforce_expected_counts=False,
        )
        starts = effective_start_columns(plan, len(output_indices))
        active_plan = np.asarray(plan["active_mask"], dtype=bool)
        identity = cache_identity(source, cache, target_columns)
        with prepare_emissivity_store(
            store_path,
            identity=identity,
            target_columns=target_columns,
            particle_count=complete["endpoint_count"],
            output_count=len(output_indices),
            resume=resume,
        ) as store:
            for start in sorted(np.unique(starts[active_plan]).tolist()):
                if bool(store["completed_start"][start]):
                    continue
                rows = np.flatnonzero(active_plan & (starts == start))
                group = run_praise_group(
                    h5=source,
                    rows=rows,
                    start_column=start,
                    target_columns=target_columns,
                    praise2=praise2,
                )
                for target, values in group.items():
                    target_index = target_columns.index(target)
                    store["lossless"][target_index, rows, :] = values["lossless"]
                    store["full"][target_index, rows, :] = values["full"]
                    store["magnetic_field_ug"][target_index, rows] = values[
                        "magnetic_field_ug"
                    ]
                    store["source_column"][target_index, rows] = values["source_column"]
                    store["active"][target_index, rows] = True
                store.flush()
                store["completed_start"][start] = True
                store.flush()
                print(f"praise_group_complete start_column={start} rows={len(rows)}", flush=True)
            counts: list[int] = []
            source_ranges: list[list[int]] = []
            for target_index, target in enumerate(target_columns):
                expected = active_plan & (starts <= target)
                actual = np.asarray(store["active"][target_index], dtype=bool)
                if not np.array_equal(actual, expected):
                    raise SnapshotRadioError("emissivity active mask differs from treatment history")
                values = np.asarray(store["lossless"][target_index, expected, :])
                full = np.asarray(store["full"][target_index, expected, :])
                fields = np.asarray(store["magnetic_field_ug"][target_index, expected])
                sources = np.asarray(store["source_column"][target_index, expected])
                if (
                    np.any(~np.isfinite(values))
                    or np.any(~np.isfinite(full))
                    or np.any(values < 0.0)
                    or np.any(full < 0.0)
                    or np.any(~np.isfinite(fields))
                    or np.any(fields <= 0.0)
                    or np.any(sources > target)
                ):
                    raise SnapshotRadioError("emissivity-store final validation failed")
                counts.append(int(np.count_nonzero(expected)))
                source_ranges.append([int(sources.min()), int(sources.max())])
            store.attrs["status"] = "complete_corrected_praise2_emissivity"
            store.flush()
    return {
        "status": "complete_corrected_praise2_emissivity",
        "target_columns": target_columns,
        "active_particle_counts": counts,
        "source_column_ranges": source_ranges,
        "singleton_external_counts": [
            int(np.count_nonzero(active_plan & (starts == target)))
            for target in target_columns
        ],
        "store_path": str(store_path),
        "identity": identity,
    }


def align_particle_ids(parsed_ids: np.ndarray, desired_ids: np.ndarray) -> np.ndarray:
    parsed_ids = np.asarray(parsed_ids, dtype=np.int64)
    desired_ids = np.asarray(desired_ids, dtype=np.int64)
    order = np.argsort(parsed_ids)
    sorted_ids = parsed_ids[order]
    positions = np.searchsorted(sorted_ids, desired_ids)
    valid = positions < len(sorted_ids)
    if not np.all(valid) or not np.array_equal(sorted_ids[positions], desired_ids):
        raise SnapshotRadioError("particle source file lacks required cache IDs")
    return order[positions]


def load_particle_paths(path: Path) -> dict[int, Path]:
    values = json.loads(Path(path).read_text())
    if not isinstance(values, list) or len(values) != 5001:
        raise SnapshotRadioError("particle-path manifest must contain outputs 0..5000")
    result: dict[int, Path] = {}
    for expected_index, value in enumerate(values):
        source = Path(value)
        parts = source.name.split(".")
        if (
            len(parts) != 3
            or parts[0] != "particles"
            or parts[1] != f"{expected_index:04d}"
            or parts[2] != "dbl"
        ):
            raise SnapshotRadioError("particle-path manifest order or filename drifted")
        if not source.is_file():
            raise SnapshotRadioError(f"particle source is missing: {source}")
        result[expected_index] = source
    return result


def load_particle_states(
    *,
    cache: h5py.File,
    active_rows: np.ndarray,
    source_columns: np.ndarray,
    particle_paths: Mapping[int, Path],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    ids = np.asarray(cache["endpoint_ids"][active_rows], dtype=np.int64)
    positions = np.empty((len(active_rows), 3), dtype=np.float64)
    velocities = np.empty_like(positions)
    source_times = np.empty(len(active_rows), dtype=np.float64)
    files: list[dict[str, Any]] = []
    output_indices = np.asarray(cache["output_indices"][:], dtype=np.int64)
    cache_times = np.asarray(cache["times"][:], dtype=np.float64)
    for column in sorted(np.unique(source_columns).tolist()):
        select = source_columns == column
        output_index = int(output_indices[column])
        path = particle_paths[output_index]
        parsed = parse_particle_file(
            path,
            fields=("x1", "x2", "x3", "vx1", "vx2", "vx3"),
        )
        if not math.isclose(parsed.header.time, cache_times[column], rel_tol=0.0, abs_tol=1.0e-9):
            raise SnapshotRadioError("particle source time differs from history cache")
        aligned = align_particle_ids(parsed.ids, ids[select])
        positions[select] = np.column_stack(
            [parsed.fields[name][aligned] for name in ("x1", "x2", "x3")]
        )
        velocities[select] = np.column_stack(
            [parsed.fields[name][aligned] for name in ("vx1", "vx2", "vx3")]
        )
        source_times[select] = parsed.header.time
        files.append(
            {
                "output_index": output_index,
                "cache_column": int(column),
                "time_code": parsed.header.time,
                "path": str(path),
                "file_size_bytes": parsed.header.file_size,
                "selected_particle_count": int(np.count_nonzero(select)),
            }
        )
    beta = np.linalg.norm(velocities, axis=1)
    if (
        np.any(~np.isfinite(positions))
        or np.any(~np.isfinite(beta))
        or np.any(beta >= 1.0)
    ):
        raise SnapshotRadioError("matched particle coordinates or velocities are invalid")
    return positions, velocities, {
        "source_time_code_min": float(source_times.min()),
        "source_time_code_max": float(source_times.max()),
        "source_files": files,
    }


def luminosity_from_map(values: np.ndarray, *, pixel_size_kpc: float) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 3 or np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise SnapshotRadioError("ray map must be a finite non-negative cube")
    pixel_area_m2 = (float(pixel_size_kpc) * KPC_TO_M) ** 2
    return 4.0 * math.pi * np.sum(values, axis=(0, 1)) * pixel_area_m2


def raytrace_snapshot(
    *,
    snapshot_index: int,
    fluid_time_myr: float,
    cache: h5py.File,
    store: h5py.File,
    target_index: int,
    particle_paths: Mapping[int, Path],
    view_deg: float,
    kd_jobs: int,
    case: str,
) -> dict[str, Any]:
    active = np.asarray(store["active"][target_index], dtype=bool)
    rows = np.flatnonzero(active)
    source_columns = np.asarray(store["source_column"][target_index, rows], dtype=np.int64)
    positions, velocities, source = load_particle_states(
        cache=cache,
        active_rows=rows,
        source_columns=source_columns,
        particle_paths=particle_paths,
    )
    lossless = np.asarray(store["lossless"][target_index, rows, :], dtype=np.float64)
    full = np.asarray(store["full"][target_index, rows, :], dtype=np.float64)
    field = np.asarray(store["magnetic_field_ug"][target_index, rows], dtype=np.float64)
    combined = np.column_stack(
        (lossless, full, lossless[:, 2] * field, full[:, 2] * field)
    ) * EMISSIVITY_UNIT
    labels, component_provenance = _component_labels_from_original_z(positions)
    support_bound = derive_support_bound(positions, multiplier=2.0)
    ray_map, ray_metadata = _raytrace_component_cropped(
        coords=positions,
        velocity=velocities,
        emissivity=combined,
        labels=labels,
        view_deg=view_deg,
        delta_r=RAY_STEP_KPC,
        pixel_size=PIXEL_SIZE_KPC,
        support_bound=support_bound,
        kd_jobs=kd_jobs,
    )
    map_values = ray_map.to_value(INTENSITY_UNIT)
    luminosity = luminosity_from_map(map_values, pixel_size_kpc=PIXEL_SIZE_KPC)
    lossless_field = float(luminosity[10] / luminosity[2])
    full_field = float(luminosity[11] / luminosity[7])
    particle_time_max = source["source_time_code_max"] * TIME_UNIT_S / (1.0 * u.Myr).to_value(u.s)
    particle_time_min = source["source_time_code_min"] * TIME_UNIT_S / (1.0 * u.Myr).to_value(u.s)
    if particle_time_max > fluid_time_myr + 1.0e-8:
        raise SnapshotRadioError("ray trace uses particle state later than the fluid snapshot")
    source_output_indices = [int(item["output_index"]) for item in source["source_files"]]
    rows_out: list[dict[str, Any]] = []
    for loss_model, offset, effective_field in (
        ("lossless", 0, lossless_field),
        ("full_loss", 5, full_field),
    ):
        for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
            rows_out.append(
                {
                    "case": case,
                    "snapshot_index": snapshot_index,
                    "fluid_time_myr": fluid_time_myr,
                    "particle_output_index": max(source_output_indices),
                    "particle_output_index_min": min(source_output_indices),
                    "particle_time_myr": particle_time_max,
                    "particle_time_myr_min": particle_time_min,
                    "particle_time_offset_myr": fluid_time_myr - particle_time_max,
                    "view": f"{int(view_deg)}deg",
                    "frequency_ghz": float(frequency),
                    "loss_model": loss_model,
                    "luminosity_w_hz": float(luminosity[offset + frequency_index]),
                    "effective_magnetic_field_ug": effective_field,
                    "active_particle_count": len(rows),
                    "method": "corrected_praise2_native_window5_raytrace",
                }
            )
    return {
        "status": "complete_radio_view",
        "snapshot_index": snapshot_index,
        "view_deg": view_deg,
        "rows": rows_out,
        "source": source,
        "component_provenance": component_provenance,
        "raytrace": {
            key: ray_metadata[key]
            for key in (
                "grid_shape",
                "view_deg",
                "delta_r_kpc",
                "pixel_size_kpc",
                "support_bound_kpc",
                "kd_jobs",
                "path_conversion",
            )
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    if output_root.exists() and not args.resume:
        raise SnapshotRadioError(f"refusing to overwrite output root: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    work_root = output_root / ".work"
    checkpoint_root = work_root / "raytrace_checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    praise2, praise2_provenance = load_praise2(args.praise2_source, args.praise2_commit_proof)
    fluid_times = load_fluid_times(args.fluid_manifest, case=args.case)
    particle_paths = load_particle_paths(args.particle_paths_json)
    store_path = work_root / "corrected_praise2_emissivity.h5"
    emissivity = build_emissivity_store(
        args.cache, store_path, praise2, resume=args.resume
    )
    view_rows: list[dict[str, Any]] = []
    checkpoint_records: list[dict[str, Any]] = []
    with h5py.File(args.cache, "r") as cache, h5py.File(store_path, "r") as store:
        if store.attrs.get("status") != "complete_corrected_praise2_emissivity":
            raise SnapshotRadioError("emissivity store is not complete")
        for target_index, snapshot_index in enumerate(SNAPSHOT_INDICES):
            for view in VIEWS_DEG:
                checkpoint = checkpoint_root / f"snapshot_{snapshot_index:02d}_view_{int(view):02d}.json"
                if checkpoint.is_file():
                    record = json.loads(checkpoint.read_text())
                    if record.get("status") != "complete_radio_view":
                        raise SnapshotRadioError("raytrace checkpoint is incomplete")
                else:
                    record = raytrace_snapshot(
                        snapshot_index=snapshot_index,
                        fluid_time_myr=fluid_times[snapshot_index],
                        cache=cache,
                        store=store,
                        target_index=target_index,
                        particle_paths=particle_paths,
                        view_deg=view,
                        kd_jobs=args.kd_jobs,
                        case=args.case,
                    )
                    write_json(checkpoint, record)
                view_rows.extend(record["rows"])
                checkpoint_records.append(record)
                print(f"raytrace_complete snapshot={snapshot_index} view={view:g}", flush=True)
    expected_view_rows = len(SNAPSHOT_INDICES) * len(VIEWS_DEG) * 2 * len(FREQUENCIES_GHZ)
    if len(view_rows) != expected_view_rows:
        raise SnapshotRadioError("radio view surface is incomplete")
    primary_rows = [row for row in view_rows if row["view"] == f"{int(PRIMARY_VIEW_DEG)}deg"]
    if len(primary_rows) != len(SNAPSHOT_INDICES) * 2 * len(FREQUENCIES_GHZ):
        raise SnapshotRadioError("primary radio surface is incomplete")
    write_rows(output_root / "radio_view_luminosity.csv", view_rows)
    write_rows(output_root / "radio_luminosity_timeseries.csv", primary_rows)
    write_rows(
        output_root / "radio_source_files.csv",
        [
            {
                "snapshot_index": record["snapshot_index"],
                "view": f"{int(record['view_deg'])}deg",
                **source,
            }
            for record in checkpoint_records
            for source in record["source"]["source_files"]
        ],
    )
    metadata = {
        "status": "complete_corrected_praise2_snapshot_radio",
        "case": args.case,
        "snapshots": list(SNAPSHOT_INDICES),
        "frequencies_ghz": FREQUENCIES_GHZ,
        "loss_models": ["lossless", "full_loss"],
        "views_deg": list(VIEWS_DEG),
        "primary_integrated_view_deg": PRIMARY_VIEW_DEG,
        "primary_view_rationale": "predeclared middle orientation; 0 and 90 degrees retained as sensitivity",
        "praise2": praise2_provenance,
        "praise2_window_width": PRAISE2_WINDOW_WIDTH,
        "praise2_pressure_preparation": "approved joint-initialization-zero trim, then native published linear Savitzky-Golay window 5",
        "singleton_policy": "instantaneous recent shock: full-loss equals lossless at the first effective record",
        "causal_matching": "exact PRAiSE2-selected source output coordinates; all source times not later than fluid snapshot",
        "raytrace": {
            "pixel_size_kpc": PIXEL_SIZE_KPC,
            "ray_step_kpc": RAY_STEP_KPC,
            "component_partition": "original-coordinate z sign, deterministic support partition only",
            "full_maps_retained": False,
            "reason": "selected-age scalar luminosity and field products answer Goal 064; transient maps avoid bulky duplicate evidence",
        },
        "emissivity": emissivity,
    }
    write_json(output_root / "g_lo_snapshot_radio_metadata.json", metadata)
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=("C-HI", "C-LO", "G-HI", "G-LO"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--fluid-manifest", type=Path, required=True)
    parser.add_argument("--particle-paths-json", type=Path, required=True)
    parser.add_argument("--praise2-source", type=Path, required=True)
    parser.add_argument("--praise2-commit-proof", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--kd-jobs", type=int, default=16)
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except (SnapshotRadioError, HistoryError, OSError, ValueError) as exc:
        print(f"radio_error={exc}")
        return 2
    print(f"status={result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
