#!/usr/bin/env python3
"""Extract one native-grid speed-defined spherical energy budget.

The two apertures are set by the furthest current cell centre whose full
three-component speed reaches 100 or 300 km/s.  Every saved physical cell
whose centre lies at or inside that radius contributes to the budget,
irrespective of its speed.  Current binary tracer membership is applied to
the cell-wise current-minus-initial energy change.

This is a storage diagnostic.  It does not measure transport through the
moving spherical surface and therefore cannot certify energy closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from measure_q031_fluxes import Grid, read_grid
from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS,
    REQUIRED_DATASETS,
    UNIT_DENSITY_CGS,
    UNIT_ENERGY_ERG,
    UNIT_LENGTH_CM,
    UNIT_VELOCITY_CMS,
    require_datasets,
)
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR, load_environment


METHOD_VERSION = 2
SPEED_THRESHOLDS_KM_S = (100.0, 300.0)
TRACER_THRESHOLD = 1.0e-3
DEFAULT_SAFE_BUFFER_KPC = 40.0
COMPONENTS = ("thermal", "kinetic", "gravitational")
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
CASE_BIPOLAR_POWER_ERG_S = {
    "C-HI": 2.0e45,
    "C-LO": 2.0e43,
    "G-HI": 2.0e45,
    "G-LO": 2.0e43,
}
G_HI_FIRST_BOUNDARY_CONTAMINATED_INDEX = 48
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stat_identity(path: Path) -> dict[str, Any]:
    value = path.stat()
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f"input is not a regular file: {path}")
    return {
        "path": str(path.absolute()),
        "resolved_path": str(path.resolve()),
        "size_bytes": value.st_size,
        "mtime_ns": value.st_mtime_ns,
        "ctime_ns": value.st_ctime_ns,
        "device": value.st_dev,
        "inode": value.st_ino,
    }


def _stable(identities: Sequence[Mapping[str, Any]]) -> None:
    """Fail if a source changed; tolerate a device-only remount after hashing."""

    for expected in identities:
        path = Path(str(expected["path"]))
        actual = _stat_identity(path)
        mismatches = {
            key for key, value in actual.items()
            if key != "resolved_path" and expected.get(key) != value
        }
        if expected.get("resolved_path") != actual["resolved_path"]:
            mismatches.add("resolved_path")
        if not mismatches:
            continue
        digest = expected.get("sha256")
        if mismatches != {"device"} or not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise ValueError(f"input mutated during or after extraction: {path}")
        before = _stat_identity(path)
        observed_digest = _sha256(path)
        after = _stat_identity(path)
        if before != after or observed_digest != digest:
            raise ValueError(f"input mutated during or after extraction: {path}")


def _receipt_inputs(
    path: Path,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Any], dict[str, Any]]:
    before = _stat_identity(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("input receipt must be schema_version 1")
    records = payload.get("inputs")
    if not isinstance(records, dict):
        raise ValueError("input receipt has no inputs mapping")
    identity = {**before, "sha256": _sha256(path)}
    if _stat_identity(path) != before:
        raise ValueError("input receipt changed while it was read")
    return records, identity, payload


def bind_inputs(
    paths: Mapping[str, Path], input_receipt: Path | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str, dict[str, Any] | None]:
    """Bind native sources either to a validated receipt or full live hashes."""

    required = {"current_h5", "initial_h5", "environment"}
    if not required.issubset(paths) or any(not path.is_file() for path in paths.values()):
        raise ValueError("current, initial, environment, and any supplied grid inputs must exist")
    identities: list[dict[str, Any]] = []
    receipt_identity = None
    if input_receipt is None:
        for role, path in paths.items():
            before = _stat_identity(path)
            digest = _sha256(path)
            after = _stat_identity(path)
            if before != after:
                raise ValueError(f"input changed while hashing: {path}")
            identities.append({"role": role, **before, "sha256": digest})
        return identities, None, "direct_full_sha256", None

    records, receipt_identity, receipt_payload = _receipt_inputs(input_receipt)
    if set(records) != set(paths):
        raise ValueError(
            f"input receipt roles differ: expected {sorted(paths)}, observed {sorted(records)}"
        )
    for role, path in paths.items():
        record = records[role]
        if not isinstance(record, dict):
            raise ValueError(f"invalid input receipt record: {role}")
        digest = record.get("sha256")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise ValueError(f"input receipt lacks a valid SHA-256: {role}")
        actual = _stat_identity(path)
        expected_path = str(record.get("path", ""))
        expected_resolved = str(record.get("resolved_path", ""))
        if expected_path != actual["path"] or expected_resolved != actual["resolved_path"]:
            raise ValueError(f"input path differs from receipt: {role}")
        expected = {"role": role, **{key: record.get(key) for key in actual}, "sha256": digest}
        mismatches = {key for key, value in actual.items() if expected.get(key) != value}
        if mismatches:
            if mismatches != {"device"}:
                raise ValueError(f"input metadata differs from receipt: {role}: {sorted(mismatches)}")
            before = _stat_identity(path)
            observed_digest = _sha256(path)
            after = _stat_identity(path)
            if before != after or observed_digest != digest:
                raise ValueError(f"device-transition hash check failed: {role}")
            expected.update(actual)
        identities.append(expected)
    return identities, receipt_identity, "bound_input_receipt", receipt_payload


def _single_timestep(h5: h5py.File, requested: str | None, *, context: str) -> tuple[str, float, tuple[int, int, int]]:
    groups = [
        name for name, value in h5.items()
        if isinstance(value, h5py.Group) and "vars" in value
    ]
    if requested is None:
        if len(groups) != 1:
            raise ValueError(f"{context} must contain exactly one timestep group; found {groups}")
        requested = groups[0]
    if requested not in groups:
        raise ValueError(f"missing timestep {requested!r} in {context}")
    group = h5[requested]
    if "Time" not in group.attrs:
        raise ValueError(f"missing Time attribute in {context}:{requested}")
    time_code = float(group.attrs["Time"])
    if not math.isfinite(time_code):
        raise ValueError(f"non-finite Time attribute in {context}:{requested}")
    return requested, time_code, require_datasets(h5, requested)


def _validate_snapshot_index(path: Path, snapshot_index: int) -> None:
    match = re.fullmatch(r"data\.(\d+)\.(?:flt|dbl)\.h5", path.name)
    if match is not None and int(match.group(1)) != snapshot_index:
        raise ValueError("snapshot index disagrees with native HDF5 filename")


def _state(variables: Mapping[str, Any], iz: int, *, current: bool) -> dict[str, np.ndarray]:
    names = REQUIRED_DATASETS if current else ("rho", "prs", "vx1", "vx2", "vx3")
    result = {name: np.asarray(variables[name][iz, :, :], dtype=np.float64) for name in names}
    if any(not np.all(np.isfinite(values)) for values in result.values()):
        raise ValueError(f"non-finite primitive at z index {iz}")
    if np.any(result["rho"] <= 0.0) or np.any(result["prs"] <= 0.0):
        raise ValueError(f"non-positive density or pressure at z index {iz}")
    return result


def _speed_km_s(state: Mapping[str, np.ndarray]) -> np.ndarray:
    speed_code = np.sqrt(sum(state[name] ** 2 for name in ("vx1", "vx2", "vx3")))
    return speed_code * UNIT_VELOCITY_CMS / 1.0e5


def _validate_grid(grid: Grid, expected: Grid | None = None) -> None:
    for name in ("x", "y", "z", "x_edges", "y_edges", "z_edges"):
        values = getattr(grid, name)
        if not np.all(np.isfinite(values)) or not np.all(np.diff(values) > 0.0):
            raise ValueError(f"invalid grid axis: {name}")
        if expected is not None and not np.array_equal(values, getattr(expected, name)):
            raise ValueError(f"current grid differs from initial grid: {name}")


def _safe_axis_mask(edges: np.ndarray, buffer_kpc: float) -> np.ndarray:
    return (
        (edges[:-1] >= edges[0] + buffer_kpc)
        & (edges[1:] <= edges[-1] - buffer_kpc)
    )


def _safe_slice_mask(grid: Grid, iz: int, buffer_kpc: float) -> np.ndarray:
    x = _safe_axis_mask(grid.x_edges, buffer_kpc)
    y = _safe_axis_mask(grid.y_edges, buffer_kpc)
    z = _safe_axis_mask(grid.z_edges, buffer_kpc)[iz]
    return y[:, None] & x[None, :] & bool(z)


def _box_radius_limit(edges: Sequence[np.ndarray], buffer_kpc: float) -> float:
    limits = []
    for axis in edges:
        lower, upper = float(axis[0] + buffer_kpc), float(axis[-1] - buffer_kpc)
        if lower >= 0.0 or upper <= 0.0:
            raise ValueError("boundary-safe box does not contain the coordinate origin")
        limits.extend((-lower, upper))
    return min(limits)


def _cell_boundary_margin(grid: Grid, iz: int, iy: int, ix: int) -> float:
    return min(
        grid.x_edges[ix] - grid.x_edges[0],
        grid.x_edges[-1] - grid.x_edges[ix + 1],
        grid.y_edges[iy] - grid.y_edges[0],
        grid.y_edges[-1] - grid.y_edges[iy + 1],
        grid.z_edges[iz] - grid.z_edges[0],
        grid.z_edges[-1] - grid.z_edges[iz + 1],
    )


def discover_apertures(
    variables: Mapping[str, Any], grid: Grid, *, safe_buffer_kpc: float
) -> dict[str, Any]:
    """First bounded-memory pass: radii, tracer extent, and defining cells."""

    thresholds: dict[float, dict[str, Any]] = {
        value: {"qualifying_cell_count": 0, "qualifying_volume_kpc3": 0.0, "raw_radius_kpc": None}
        for value in SPEED_THRESHOLDS_KM_S
    }
    cocoon_count = 0
    cocoon_volume = 0.0
    cocoon_pv = []
    cocoon_radius = None
    tracer_min, tracer_max, tracer_outside = math.inf, -math.inf, 0
    area = grid.dy[:, None] * grid.dx[None, :]
    radius_xy2 = grid.y[:, None] ** 2 + grid.x[None, :] ** 2
    safe_x = _safe_axis_mask(grid.x_edges, safe_buffer_kpc)
    safe_y = _safe_axis_mask(grid.y_edges, safe_buffer_kpc)
    safe_z = _safe_axis_mask(grid.z_edges, safe_buffer_kpc)
    for iz, z_value in enumerate(grid.z):
        state = _state(variables, iz, current=True)
        speed = _speed_km_s(state)
        radius = np.sqrt(radius_xy2 + z_value**2)
        volume = area * grid.dz[iz]
        tracer = state["tr1"]
        tracer_min = min(tracer_min, float(np.min(tracer)))
        tracer_max = max(tracer_max, float(np.max(tracer)))
        tracer_outside += int(np.count_nonzero((tracer < 0.0) | (tracer > 1.0)))
        cocoon = tracer > TRACER_THRESHOLD
        if np.any(cocoon):
            cocoon_count += int(np.count_nonzero(cocoon))
            cocoon_volume += float(np.sum(volume[cocoon]))
            cocoon_pv.append(float(np.sum(state["prs"][cocoon] * volume[cocoon])) * UNIT_ENERGY_ERG)
            local = float(np.max(radius[cocoon]))
            cocoon_radius = local if cocoon_radius is None else max(cocoon_radius, local)
        for threshold, record in thresholds.items():
            selected = speed >= threshold
            if not np.any(selected):
                continue
            record["qualifying_cell_count"] += int(np.count_nonzero(selected))
            record["qualifying_volume_kpc3"] += float(np.sum(volume[selected]))
            masked_radius = np.where(selected, radius, -np.inf)
            flat = int(np.argmax(masked_radius))
            local_radius = float(masked_radius.reshape(-1)[flat])
            if record["raw_radius_kpc"] is None or local_radius > record["raw_radius_kpc"]:
                iy, ix = np.unravel_index(flat, radius.shape)
                record.update({
                    "raw_radius_kpc": local_radius,
                    "radius_defining_index_zyx": [iz, int(iy), int(ix)],
                    "radius_defining_xyz_kpc": [
                        float(grid.x[ix]), float(grid.y[iy]), float(z_value)
                    ],
                    "radius_defining_speed_km_s": float(speed[iy, ix]),
                    "radius_defining_velocity_km_s": [
                        float(state[name][iy, ix] * UNIT_VELOCITY_CMS / 1.0e5)
                        for name in ("vx1", "vx2", "vx3")
                    ],
                    "radius_defining_tracer": float(tracer[iy, ix]),
                    "radius_defining_cell_boundary_margin_kpc": _cell_boundary_margin(
                        grid, iz, int(iy), int(ix)
                    ),
                    "radius_defining_cell_inside_safe_box": bool(
                        safe_z[iz] and safe_y[iy] and safe_x[ix]
                    ),
                })
    return {
        "thresholds": thresholds,
        "cocoon": {
            "cell_count": cocoon_count,
            "volume_kpc3": cocoon_volume,
            "maximum_cell_radius_kpc": cocoon_radius,
            "pressure_volume_integral_erg": math.fsum(cocoon_pv),
        },
        "tracer_diagnostics": {
            "minimum": tracer_min,
            "maximum": tracer_max,
            "outside_unit_interval_cell_count": tracer_outside,
            "membership": "current stored float64 tr1 > 1e-3; exact complement is ambient",
            "handling": (
                "raw stored values used without clipping, tolerance, or repair; any value outside "
                "[0,1] places scientific interpretation on hold"
            ),
        },
    }


def _neighbour_count(
    variables: Mapping[str, Any], shape: tuple[int, int, int], index: Sequence[int], threshold: float
) -> int:
    iz, iy, ix = (int(value) for value in index)
    bounds = [
        (max(value - 1, 0), min(value + 2, size))
        for value, size in zip((iz, iy, ix), shape, strict=True)
    ]
    selection = tuple(slice(start, stop) for start, stop in bounds)
    velocity = [np.asarray(variables[name][selection], dtype=np.float64) for name in ("vx1", "vx2", "vx3")]
    if any(not np.all(np.isfinite(values)) for values in velocity):
        raise ValueError("non-finite velocity in radius-defining neighbourhood")
    selected = np.sqrt(sum(values**2 for values in velocity)) * UNIT_VELOCITY_CMS / 1.0e5 >= threshold
    centre = tuple(value - bounds[axis][0] for axis, value in enumerate((iz, iy, ix)))
    selected[centre] = False
    return int(np.count_nonzero(selected))


def _new_region_accumulator() -> dict[str, Any]:
    return {
        "cell_count": 0,
        "volume_kpc3": [],
        "cocoon_cell_count": 0,
        "cocoon_volume_kpc3": [],
        "components": {
            region: {component: [] for component in COMPONENTS}
            for region in ("all", "cocoon", "ambient")
        },
    }


def _add_region(
    accumulator: dict[str, Any], mask: np.ndarray, cocoon: np.ndarray,
    volume: np.ndarray, component_arrays: Mapping[str, np.ndarray]
) -> None:
    if not np.any(mask):
        return
    cocoon_mask = mask & cocoon
    ambient_mask = mask & ~cocoon
    accumulator["cell_count"] += int(np.count_nonzero(mask))
    accumulator["volume_kpc3"].append(float(np.sum(volume[mask])))
    accumulator["cocoon_cell_count"] += int(np.count_nonzero(cocoon_mask))
    accumulator["cocoon_volume_kpc3"].append(float(np.sum(volume[cocoon_mask])))
    for component, values in component_arrays.items():
        accumulator["components"]["all"][component].append(float(np.sum(values[mask])))
        accumulator["components"]["cocoon"][component].append(float(np.sum(values[cocoon_mask])))
        accumulator["components"]["ambient"][component].append(float(np.sum(values[ambient_mask])))


def _finish_components(values: Mapping[str, Sequence[float]], injected: float) -> dict[str, Any]:
    result = {f"{name}_delta_erg": math.fsum(parts) for name, parts in values.items()}
    result["total_delta_erg"] = math.fsum(result[f"{name}_delta_erg"] for name in COMPONENTS)
    result["total_over_injected"] = result["total_delta_erg"] / injected if injected > 0.0 else None
    return result


def _finish_region(accumulator: Mapping[str, Any], injected: float) -> dict[str, Any]:
    partitions = {
        name: _finish_components(accumulator["components"][name], injected)
        for name in ("all", "cocoon", "ambient")
    }
    residuals = {
        f"{component}_erg": (
            partitions["cocoon"][f"{component}_delta_erg"]
            + partitions["ambient"][f"{component}_delta_erg"]
            - partitions["all"][f"{component}_delta_erg"]
        )
        for component in (*COMPONENTS, "total")
    }
    scale = max(
        injected,
        *(abs(partitions["all"][f"{component}_delta_erg"]) for component in (*COMPONENTS, "total")),
        1.0,
    )
    tolerance = 1.0e-9 * scale
    if any(abs(value) > tolerance for value in residuals.values()):
        raise ValueError(f"binary tracer partition identity failed: {residuals}")
    return {
        "cell_count": int(accumulator["cell_count"]),
        "volume_kpc3": math.fsum(accumulator["volume_kpc3"]),
        "cocoon_cell_count": int(accumulator["cocoon_cell_count"]),
        "cocoon_volume_kpc3": math.fsum(accumulator["cocoon_volume_kpc3"]),
        "delta_erg": partitions["all"],
        "current_binary_partition": {
            "cocoon": partitions["cocoon"],
            "ambient": partitions["ambient"],
            "identity_residual_erg": residuals,
            "identity_tolerance_erg": tolerance,
            "identity_pass": True,
        },
    }


def _clipping_identity(
    sphere: Mapping[str, Any], safe: Mapping[str, Any], lost: Mapping[str, Any], injected: float
) -> dict[str, Any]:
    residuals = {
        f"{component}_erg": (
            safe["delta_erg"][f"{component}_delta_erg"]
            + lost["delta_erg"][f"{component}_delta_erg"]
            - sphere["delta_erg"][f"{component}_delta_erg"]
        )
        for component in (*COMPONENTS, "total")
    }
    scale = max(
        injected,
        *(abs(sphere["delta_erg"][f"{component}_delta_erg"]) for component in (*COMPONENTS, "total")),
        1.0,
    )
    tolerance = 1.0e-9 * scale
    cell_residual = safe["cell_count"] + lost["cell_count"] - sphere["cell_count"]
    cocoon_cell_residual = (
        safe["cocoon_cell_count"] + lost["cocoon_cell_count"] - sphere["cocoon_cell_count"]
    )
    if (
        cell_residual != 0
        or cocoon_cell_residual != 0
        or any(abs(value) > tolerance for value in residuals.values())
    ):
        raise ValueError("safe-box clipping does not partition the primary aperture")
    return {
        "pass": True,
        "cell_count_residual": cell_residual,
        "cocoon_cell_count_residual": cocoon_cell_residual,
        "energy_residual_erg": residuals,
        "energy_tolerance_erg": tolerance,
    }


def _new_disturbance() -> dict[str, Any]:
    return {
        "cell_count": 0,
        "flagged_cell_count": 0,
        "maximum_speed_km_s": 0.0,
        "maximum_speed_over_local_sound_speed": 0.0,
        "maximum_abs_pressure_fractional_change": 0.0,
        "maximum_abs_density_fractional_change": 0.0,
    }


def integrate_budgets(
    *, current: Mapping[str, Any], initial: Mapping[str, Any], grid: Grid,
    environment: Any, discovery: Mapping[str, Any], injected_energy_erg: float,
    safe_buffer_kpc: float
) -> dict[float, dict[str, Any]]:
    """Second bounded-memory pass over the same current and actual t=0 cells."""

    accumulators: dict[float, dict[str, Any]] = {}
    for threshold, aperture in discovery["thresholds"].items():
        if aperture["raw_radius_kpc"] is not None:
            accumulators[threshold] = {
                "sphere": _new_region_accumulator(),
                "safe": _new_region_accumulator(),
                "lost": _new_region_accumulator(),
                "disturbance": _new_disturbance(),
                "cocoon_outside_cell_count": 0,
                "cocoon_outside_volume_kpc3": [],
                "speed100_outside_cell_count": 0,
            }
    if not accumulators:
        return {}
    area = grid.dy[:, None] * grid.dx[None, :]
    radius_xy2 = grid.y[:, None] ** 2 + grid.x[None, :] ** 2
    for iz, z_value in enumerate(grid.z):
        now = _state(current, iz, current=True)
        before = _state(initial, iz, current=False)
        radius = np.sqrt(radius_xy2 + z_value**2)
        volume = area * grid.dz[iz]
        potential = environment.potential_at_radius(radius * UNIT_LENGTH_CM)
        speed = _speed_km_s(now)
        speed2 = sum(now[name] ** 2 for name in ("vx1", "vx2", "vx3"))
        speed20 = sum(before[name] ** 2 for name in ("vx1", "vx2", "vx3"))
        components = {
            "thermal": (
                (now["prs"] - before["prs"])
                * volume * UNIT_ENERGY_ERG / (GAMMA_GAS - 1.0)
            ),
            "kinetic": (
                0.5 * (now["rho"] * speed2 - before["rho"] * speed20)
                * volume * UNIT_ENERGY_ERG
            ),
            "gravitational": (
                (now["rho"] - before["rho"])
                * volume * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3 * potential
            ),
        }
        cocoon = now["tr1"] > TRACER_THRESHOLD
        safe = _safe_slice_mask(grid, iz, safe_buffer_kpc)
        sound_speed = np.sqrt(GAMMA_GAS * now["prs"] / now["rho"]) * UNIT_VELOCITY_CMS / 1.0e5
        pressure_change = np.abs(now["prs"] / before["prs"] - 1.0)
        density_change = np.abs(now["rho"] / before["rho"] - 1.0)
        mach = speed / sound_speed
        for threshold, bundle in accumulators.items():
            raw_radius = float(discovery["thresholds"][threshold]["raw_radius_kpc"])
            sphere = radius <= np.nextafter(raw_radius, math.inf)
            safe_sphere = sphere & safe
            lost = sphere & ~safe
            _add_region(bundle["sphere"], sphere, cocoon, volume, components)
            _add_region(bundle["safe"], safe_sphere, cocoon, volume, components)
            _add_region(bundle["lost"], lost, cocoon, volume, components)
            cocoon_outside = cocoon & ~sphere
            bundle["cocoon_outside_cell_count"] += int(np.count_nonzero(cocoon_outside))
            bundle["cocoon_outside_volume_kpc3"].append(float(np.sum(volume[cocoon_outside])))
            bundle["speed100_outside_cell_count"] += int(np.count_nonzero((speed >= 100.0) & ~sphere))
            outside = safe & ~sphere
            disturbance = bundle["disturbance"]
            disturbance["cell_count"] += int(np.count_nonzero(outside))
            if np.any(outside):
                flagged = outside & ((mach >= 0.05) | (pressure_change >= 0.01) | (density_change >= 0.01))
                disturbance["flagged_cell_count"] += int(np.count_nonzero(flagged))
                disturbance["maximum_speed_km_s"] = max(
                    disturbance["maximum_speed_km_s"], float(np.max(speed[outside]))
                )
                disturbance["maximum_speed_over_local_sound_speed"] = max(
                    disturbance["maximum_speed_over_local_sound_speed"], float(np.max(mach[outside]))
                )
                disturbance["maximum_abs_pressure_fractional_change"] = max(
                    disturbance["maximum_abs_pressure_fractional_change"], float(np.max(pressure_change[outside]))
                )
                disturbance["maximum_abs_density_fractional_change"] = max(
                    disturbance["maximum_abs_density_fractional_change"], float(np.max(density_change[outside]))
                )
    result: dict[float, dict[str, Any]] = {}
    cocoon_total_cells = int(discovery["cocoon"]["cell_count"])
    cocoon_total_volume = float(discovery["cocoon"]["volume_kpc3"])
    for threshold, bundle in accumulators.items():
        sphere = _finish_region(bundle["sphere"], injected_energy_erg)
        safe = _finish_region(bundle["safe"], injected_energy_erg)
        lost = _finish_region(bundle["lost"], injected_energy_erg)
        outside_cells = int(bundle["cocoon_outside_cell_count"])
        outside_volume = math.fsum(bundle["cocoon_outside_volume_kpc3"])
        result[threshold] = {
            "sphere_budget": sphere,
            "sphere_intersect_boundary_safe_box_budget": safe,
            "sphere_cells_outside_boundary_safe_box": lost,
            "safe_box_clipping_identity": _clipping_identity(
                sphere, safe, lost, injected_energy_erg
            ),
            "coverage": {
                "cocoon_total_cell_count": cocoon_total_cells,
                "cocoon_total_volume_kpc3": cocoon_total_volume,
                "cocoon_outside_aperture_cell_count": outside_cells,
                "cocoon_outside_aperture_volume_kpc3": outside_volume,
                "cocoon_cell_coverage_fraction": (
                    (cocoon_total_cells - outside_cells) / cocoon_total_cells
                    if cocoon_total_cells else None
                ),
                "cocoon_volume_coverage_fraction": (
                    (cocoon_total_volume - outside_volume) / cocoon_total_volume
                    if cocoon_total_volume else None
                ),
                "speed_ge_100_cells_outside_aperture": int(bundle["speed100_outside_cell_count"]),
                "outside_aperture_within_safe_box_disturbance": bundle["disturbance"] | {
                    "flag_rule": "Mach >= 0.05 or abs(p/p0-1) >= 0.01 or abs(rho/rho0-1) >= 0.01",
                    "role": "coverage diagnostic only; never changes the aperture",
                },
            },
        }
    return result


def _atomic_publish(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise ValueError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _qualification(holds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    materialized = [dict(item) for item in holds]
    return {
        "status": "held" if materialized else "unreviewed",
        "qualified": False,
        "holds": materialized,
        "scope": "execution and arithmetic do not confer scientific qualification",
    }


def _threshold_comparison(records: Mapping[str, Mapping[str, Any]], injected: float) -> dict[str, Any]:
    low, high = records["100"], records["300"]
    if low["measurement_status"] != "measured" or high["measurement_status"] != "measured":
        return {
            "measurement_status": "unavailable_unless_both_thresholds_exist",
            "scientific_qualification": _qualification([]),
            "definition": "conditional R100 budget minus R300 budget",
        }
    differences = {}
    for component in (*COMPONENTS, "total"):
        key = f"{component}_delta_erg"
        differences[key] = (
            low["sphere_budget"]["delta_erg"][key]
            - high["sphere_budget"]["delta_erg"][key]
        )
    differences["total_over_injected"] = differences["total_delta_erg"] / injected if injected > 0 else None
    holds = []
    for threshold, record in (("R100", low), ("R300", high)):
        for hold in record["scientific_qualification"]["holds"]:
            holds.append({**hold, "source_threshold": threshold})
    return {
        "measurement_status": "measured_conditional_diagnostic",
        "scientific_qualification": _qualification(holds),
        "definition": (
            "conditional R100 budget minus R300 budget on independently selected cell sets; "
            "not a nested-aperture qualification or closure result"
        ),
        "radius_difference_kpc": low["raw_radius_kpc"] - high["raw_radius_kpc"],
        "delta_difference_erg": differences,
    }


def extract_snapshot(
    *, case: str, snapshot_index: int, current_h5: Path, initial_h5: Path,
    environment_path: Path, output: Path, grid_file: Path | None = None,
    current_timestep: str | None = None, initial_timestep: str | None = None,
    safe_buffer_kpc: float = DEFAULT_SAFE_BUFFER_KPC,
    input_receipt: Path | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    if case not in CASES or snapshot_index < 0:
        raise ValueError("case must be one of C-HI, C-LO, G-HI, G-LO and snapshot index non-negative")
    if not math.isfinite(safe_buffer_kpc) or safe_buffer_kpc < 0.0:
        raise ValueError("safe buffer must be finite and non-negative")
    if case == "G-HI" and snapshot_index >= G_HI_FIRST_BOUNDARY_CONTAMINATED_INDEX:
        raise ValueError("G-HI snapshots 48-50 are boundary-contaminated and scientifically excluded")
    _validate_snapshot_index(current_h5, snapshot_index)
    _validate_snapshot_index(initial_h5, 0)
    paths = {"current_h5": current_h5, "initial_h5": initial_h5, "environment": environment_path}
    if grid_file is not None:
        paths["grid_file"] = grid_file
    identities, receipt_identity, provenance_mode, receipt_claims = bind_inputs(paths, input_receipt)
    if receipt_claims is not None:
        if receipt_claims.get("status") != "bound_spherical_budget_inputs":
            raise ValueError("input receipt status is not bound_spherical_budget_inputs")
        if receipt_claims.get("case") != case or receipt_claims.get("snapshot_index") != snapshot_index:
            raise ValueError("case or snapshot index differs from input receipt")
    environment = load_environment(environment_path)
    script_before = _stat_identity(Path(__file__))
    script_identity = {**script_before, "sha256": _sha256(Path(__file__))}
    if _stat_identity(Path(__file__)) != script_before:
        raise ValueError("extractor source changed while it was identified")
    with h5py.File(initial_h5, "r") as initial_file, h5py.File(current_h5, "r") as current_file:
        initial_name, initial_time_code, initial_shape = _single_timestep(
            initial_file, initial_timestep, context=str(initial_h5)
        )
        current_name, current_time_code, current_shape = _single_timestep(
            current_file, current_timestep, context=str(current_h5)
        )
        if initial_shape != current_shape:
            raise ValueError("current and initial native grid shapes differ")
        initial_age_myr = initial_time_code / CODE_TIME_PER_MYR
        age_myr = current_time_code / CODE_TIME_PER_MYR
        if abs(initial_age_myr) > 1.0e-6:
            raise ValueError("initial HDF5 surface is not at t=0")
        if not math.isfinite(age_myr) or age_myr < 0.0:
            raise ValueError("current HDF5 age must be finite and non-negative")
        if receipt_claims is not None:
            expected_current = receipt_claims.get("current", {})
            expected_initial = receipt_claims.get("initial", {})
            if (
                expected_current.get("timestep") != current_name
                or expected_initial.get("timestep") != initial_name
            ):
                raise ValueError("native timestep differs from input receipt")
            if not math.isclose(
                float(expected_current.get("time_code", math.nan)), current_time_code,
                rel_tol=0.0, abs_tol=1.0e-10,
            ) or not math.isclose(
                float(expected_initial.get("time_code", math.nan)), initial_time_code,
                rel_tol=0.0, abs_tol=1.0e-10,
            ):
                raise ValueError("native time differs from input receipt")
        initial_grid = read_grid(initial_file, initial_shape, grid_file=grid_file)
        current_grid = read_grid(current_file, current_shape, grid_file=grid_file)
        _validate_grid(initial_grid)
        _validate_grid(current_grid, initial_grid)
        grid = current_grid
        domain_radius_limit = _box_radius_limit(
            (grid.x_edges, grid.y_edges, grid.z_edges), 0.0
        )
        safe_radius_limit = _box_radius_limit(
            (grid.x_edges, grid.y_edges, grid.z_edges), safe_buffer_kpc
        )
        current_vars = current_file[f"/{current_name}/vars"]
        initial_vars = initial_file[f"/{initial_name}/vars"]
        discovery = discover_apertures(
            current_vars, grid, safe_buffer_kpc=safe_buffer_kpc
        )
        r100 = discovery["thresholds"][100.0]
        r300 = discovery["thresholds"][300.0]
        if (
            r300["qualifying_cell_count"] > r100["qualifying_cell_count"]
            or (
                r300["raw_radius_kpc"] is not None
                and (
                    r100["raw_radius_kpc"] is None
                    or r300["raw_radius_kpc"] > r100["raw_radius_kpc"]
                )
            )
        ):
            raise ValueError("300-km/s qualifying cells are not a subset of 100-km/s cells")
        for threshold, record in discovery["thresholds"].items():
            if record["raw_radius_kpc"] is not None:
                neighbours = _neighbour_count(
                    current_vars, current_shape, record["radius_defining_index_zyx"], threshold
                )
                record["radius_defining_same_threshold_neighbour_count"] = neighbours
                record["isolated_radius_defining_fast_cell"] = neighbours == 0
        active_age_myr = min(max(age_myr, 0.0), 50.0)
        injected = CASE_BIPOLAR_POWER_ERG_S[case] * active_age_myr * SECONDS_PER_MYR
        native_enthalpy = {
            "definition": "alpha times sum of current pressure times full cell volume over all current tr1 > 1e-3 cells",
            "scope": "entire saved native lobe; independent of either speed-defined aperture",
            "relationship_to_energy_ledger": "proxy comparison only; never add enthalpy to the thermal/kinetic/gravitational ledger",
            "conventions": {
                f"{alpha:g}": {
                    "enthalpy_erg": alpha * discovery["cocoon"]["pressure_volume_integral_erg"],
                    "enthalpy_over_injected": (
                        alpha * discovery["cocoon"]["pressure_volume_integral_erg"] / injected
                        if injected > 0.0 else None
                    ),
                }
                for alpha in (2.5, 4.0)
            },
        }
        integrated = integrate_budgets(
            current=current_vars,
            initial=initial_vars,
            grid=grid,
            environment=environment,
            discovery=discovery,
            injected_energy_erg=injected,
            safe_buffer_kpc=safe_buffer_kpc,
        )
    _stable(identities)
    if receipt_identity is not None:
        _stable([receipt_identity])
    _stable([script_identity])
    external_identity_hold = {
        "code": "external_native_case_configuration_environment_identity_unverified",
        "detail": (
            "the extractor binds files and declared labels but does not validate the simulation "
            "configuration or prove that the environment belongs to the declared native case"
        ),
    }
    global_holds: list[dict[str, Any]] = [external_identity_hold]
    tracer_outside = int(discovery["tracer_diagnostics"]["outside_unit_interval_cell_count"])
    if tracer_outside:
        global_holds.append({
            "code": "tracer_values_outside_unit_interval_unreviewed",
            "cell_count": tracer_outside,
            "detail": "raw tracer values retained; no tolerance, clipping, or repair applied",
        })
    native_enthalpy["scientific_qualification"] = _qualification([dict(item) for item in global_holds])
    base_holds = [dict(item) for item in global_holds]
    records: dict[str, dict[str, Any]] = {}
    for threshold in SPEED_THRESHOLDS_KM_S:
        aperture = dict(discovery["thresholds"][threshold])
        key = f"{threshold:g}"
        if aperture["raw_radius_kpc"] is None:
            records[key] = {
                "speed_threshold_km_s": threshold,
                "measurement_status": "unavailable_no_cells_meet_speed_threshold",
                "scientific_qualification": _qualification([]),
                "raw_radius_kpc": None,
                "budget": None,
            }
            continue
        radius = float(aperture["raw_radius_kpc"])
        domain_complete = radius <= domain_radius_limit
        safe_complete = radius <= safe_radius_limit
        threshold_holds = [dict(item) for item in base_holds]
        if not domain_complete:
            hold = {
                "code": "domain_truncated_raw_spherical_selection",
                "detail": (
                    "raw radius exceeds the domain-box inscribed radius; measured cells do not "
                    "constitute a geometrically complete sphere"
                ),
            }
            threshold_holds.append(hold)
            global_holds.append({**hold, "threshold_km_s": threshold})
        if not safe_complete:
            hold = {
                "code": "boundary_safe_box_conflict",
                "detail": (
                    "raw radius exceeds the candidate safe-box inscribed radius; the clipped "
                    "ledger is conditional and the uncut ledger remains primary"
                ),
            }
            threshold_holds.append(hold)
            global_holds.append({**hold, "threshold_km_s": threshold})
        records[key] = {
            "speed_threshold_km_s": threshold,
            "measurement_status": "measured",
            "scientific_qualification": _qualification(threshold_holds),
            **aperture,
            "aperture_membership": "saved physical cells with centre radius r_i <= raw_radius_kpc",
            "cell_weighting": "full finite-volume cells; no partial-volume weighting",
            "padding_kpc": 0.0,
            "padding_reason": "none: the discrete estimand is cell-centre membership and <= includes every radius-defining cell",
            "domain_box_inscribed_radius_kpc": domain_radius_limit,
            "boundary_safe_box_inscribed_radius_kpc": safe_radius_limit,
            "sphere_geometrically_complete_in_domain_box": domain_complete,
            "sphere_geometrically_complete_in_boundary_safe_box": safe_complete,
            "domain_geometry_status": (
                "complete_sphere" if domain_complete else "domain_truncated_spherical_cell_selection"
            ),
            "boundary_safe_conflict": not safe_complete,
            "review_flags": {
                "isolated_radius_defining_fast_cell": aperture[
                    "isolated_radius_defining_fast_cell"
                ],
                "cocoon_outside_aperture_cell_count": integrated[threshold]["coverage"][
                    "cocoon_outside_aperture_cell_count"
                ],
                "disturbed_cells_outside_aperture_within_safe_box": integrated[threshold][
                    "coverage"
                ]["outside_aperture_within_safe_box_disturbance"]["flagged_cell_count"],
            },
            **integrated[threshold],
        }
        if (
            threshold == 100.0
            and records[key]["coverage"]["speed_ge_100_cells_outside_aperture"] != 0
        ):
            raise ValueError("R100 aperture does not contain every >=100-km/s cell")
    result = {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "execution_status": "completed_spherical_energy_budget_measurement",
        "scientific_qualification": _qualification(global_holds),
        "case": case,
        "snapshot_index": snapshot_index,
        "current_timestep": current_name,
        "initial_timestep": initial_name,
        "current_time_code": current_time_code,
        "actual_time_myr": age_myr,
        "initial_time_myr": initial_age_myr,
        "configured_case_index_exclusion_gate": {
            "status": "passed",
            "scope": "known G-HI indices 48-50 only; not general scientific validation",
        },
        "shape_nz_ny_nx": list(current_shape),
        "bipolar_power_erg_s": CASE_BIPOLAR_POWER_ERG_S[case],
        "injection_active_age_myr": active_age_myr,
        "injected_energy_erg": injected,
        "injection_definition": "labelled bipolar power times actual age, capped at 50 Myr",
        "speed_definition": "sqrt(vx1^2 + vx2^2 + vx3^2) in the current native surface",
        "threshold_operator": ">=",
        "energy_estimand": "sum over the current aperture of current minus actual t=0 cell energy",
        "thermal_definition": "(p(t)-p(0))*V/(gamma-1)",
        "kinetic_definition": "0.5*(rho(t)*|v(t)|^2-rho(0)*|v(0)|^2)*V",
        "gravitational_definition": "(rho(t)-rho(0))*Phi0(r)*V with fixed centre-zero initial potential",
        "partition_definition": "current full-cell tr1 > 1e-3 and exact complement applied to the same cell-wise deltas",
        "safe_box": {
            "buffer_from_each_domain_face_kpc": safe_buffer_kpc,
            "membership": "complete cells inside all six inset faces",
            "role": "conditional boundary-sensitivity cut, not the primary complete aperture",
        },
        "cocoon_global": discovery["cocoon"],
        "native_lobe_enthalpy": native_enthalpy,
        "tracer_diagnostics": discovery["tracer_diagnostics"],
        "thresholds": records,
        "threshold_comparison": _threshold_comparison(records, injected),
        "interpretation_limits": [
            "storage change in a time-varying sphere is not moving-boundary energy closure",
            "energy transport through either spherical surface is unmeasured",
            "the sphere-intersect-safe-box budget is a conditional clipping diagnostic and can exclude jet-affected gas",
            "one deterministic simulation per case provides no replicate-based population uncertainty",
            "the 1 percent pressure/density and Mach 0.05 coverage flags diagnose, but do not define, disturbance",
        ],
        "provenance": {
            "mode": provenance_mode,
            "native_semantic_identity_gate": {
                "status": "external_validation_required",
                "requirements": [
                    "case identity",
                    "compiled and runtime configuration identity",
                    "case-appropriate environment identity",
                ],
                "scope": (
                    "this extractor verifies bound files and declared labels only; a synthetic "
                    "or self-authored binding receipt cannot qualify a native production result"
                ),
            },
            "input_receipt": receipt_identity,
            "input_receipt_claims": (
                {
                    "status": receipt_claims["status"],
                    "case": receipt_claims["case"],
                    "snapshot_index": receipt_claims["snapshot_index"],
                    "current": receipt_claims["current"],
                    "initial": receipt_claims["initial"],
                }
                if receipt_claims is not None else None
            ),
            "inputs": identities,
            "extractor": script_identity,
            "environment_sha256": environment.source_sha256,
            "input_stability": "metadata checked after both passes; device-only transitions require full SHA-256",
        },
    }
    _atomic_publish(output, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--snapshot-index", type=int, required=True)
    parser.add_argument("--current-h5", type=Path, required=True)
    parser.add_argument("--initial-h5", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--grid-file", type=Path)
    parser.add_argument("--current-timestep")
    parser.add_argument("--initial-timestep")
    parser.add_argument("--safe-buffer-kpc", type=float, default=DEFAULT_SAFE_BUFFER_KPC)
    parser.add_argument("--input-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    extract_snapshot(
        case=args.case,
        snapshot_index=args.snapshot_index,
        current_h5=args.current_h5,
        initial_h5=args.initial_h5,
        environment_path=args.environment,
        grid_file=args.grid_file,
        current_timestep=args.current_timestep,
        initial_timestep=args.initial_timestep,
        safe_buffer_kpc=args.safe_buffer_kpc,
        input_receipt=args.input_receipt,
        output=args.output,
    )


if __name__ == "__main__":
    main()
