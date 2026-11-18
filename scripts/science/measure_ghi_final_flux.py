"""Measure the bounded G-HI index-47 addendum without repairing invalid states.

The caller supplies the original, pinned ``measure_q031_fluxes`` module on its
import path and owns native/source preflight and final stability checks.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

import measure_q031_fluxes as flux


METHOD_VERSION = 1


def _json_number(value: float) -> float | str:
    value = float(value)
    if math.isfinite(value):
        return value
    if math.isnan(value):
        return "nan"
    return "+inf" if value > 0 else "-inf"


def _face_states(cache: flux.DomainPlaneCache, grid: flux.Grid, face: str):
    axis = face[0]
    dimension, centres, edges = {
        "x": (2, grid.x, grid.x_edges),
        "y": (1, grid.y, grid.y_edges),
        "z": (0, grid.z, grid.z_edges),
    }[axis]
    negative = face.endswith("negative")
    active_index, inner_index = (0, 1) if negative else (len(centres)-1, len(centres)-2)
    active_selection = [slice(None)]*3
    inner_selection = [slice(None)]*3
    active_selection[dimension] = active_index
    inner_selection[dimension] = inner_index
    active = cache.primitive_state(tuple(active_selection))
    inner = cache.primitive_state(tuple(inner_selection))
    face_coordinate = float(edges[0 if negative else -1])
    fraction = abs(face_coordinate-float(centres[active_index])) / abs(float(centres[active_index])-float(centres[inner_index]))
    if not math.isfinite(fraction) or fraction <= 0:
        raise ValueError("boundary extrapolation fraction must be positive and finite")
    with np.errstate(over="ignore", invalid="ignore"):
        linear = {name: np.asarray(active[name]) + fraction*(np.asarray(active[name])-np.asarray(inner[name]))
                  for name in flux.PRIMITIVE_FIELDS}

    def location(position):
        active_zyx = [0, 0, 0]
        active_zyx[dimension] = active_index
        for dim, value in zip((d for d in range(3) if d != dimension), position, strict=True):
            active_zyx[dim] = int(value)
        inner_zyx = active_zyx.copy()
        inner_zyx[dimension] = inner_index
        active_xyz = [float(grid.x[active_zyx[2]]), float(grid.y[active_zyx[1]]), float(grid.z[active_zyx[0]])]
        inner_xyz = [float(grid.x[inner_zyx[2]]), float(grid.y[inner_zyx[1]]), float(grid.z[inner_zyx[0]])]
        face_xyz = active_xyz.copy()
        face_xyz[{"x": 0, "y": 1, "z": 2}[axis]] = face_coordinate
        return {"face_array_index": [int(i) for i in position],
                "active_cell_index_zyx": active_zyx, "inner_cell_index_zyx": inner_zyx,
                "active_cell_center_xyz_kpc": active_xyz,
                "inner_cell_center_xyz_kpc": inner_xyz, "face_xyz_kpc": face_xyz}

    return active, inner, linear, fraction, face_coordinate, location


def _primitive_report(state: Mapping[str, np.ndarray], *, active, inner, linear, location) -> dict[str, Any]:
    shape = np.asarray(state["rho"]).shape
    any_invalid = np.zeros(shape, dtype=bool)
    fields = {}
    for name in flux.PRIMITIVE_FIELDS:
        values = np.asarray(state[name], dtype=np.float64)
        if values.shape != shape:
            raise ValueError("boundary primitive shapes disagree")
        finite = np.isfinite(values)
        positive_required = name in {"rho", "prs"}
        nonpositive = values <= 0 if positive_required else np.zeros(shape, dtype=bool)
        invalid = ~finite | nonpositive
        any_invalid |= invalid
        finite_values = values[finite]
        entries = []
        for position in np.argwhere(invalid):
            key = tuple(int(i) for i in position)
            entries.append({**location(key), "value": _json_number(values[key]),
                            "active_value": _json_number(active[name][key]),
                            "inner_value": _json_number(inner[name][key]),
                            "linear_value": _json_number(linear[name][key])})
        fields[name] = {"positivity_required": positive_required,
                        "nonfinite_count": int(np.count_nonzero(~finite)),
                        "nonpositive_count": int(np.count_nonzero(nonpositive)),
                        "invalid_count": int(np.count_nonzero(invalid)),
                        "minimum_finite": float(np.min(finite_values)) if finite_values.size else None,
                        "maximum_finite": float(np.max(finite_values)) if finite_values.size else None,
                        "invalid_cells": entries}
    count = int(np.count_nonzero(any_invalid))
    return {"valid": count == 0, "cell_count": int(any_invalid.size),
            "invalid_cell_count": count, "fields": fields}


def diagnose_linear_boundaries(cache: flux.DomainPlaneCache, grid: flux.Grid) -> dict[str, Any]:
    """Collect every native and original-linear invalid face cell, without truncation."""
    cache.validate_complete()
    faces = []
    for face in flux.FACE_NAMES:
        active, inner, linear, fraction, coordinate, location = _face_states(cache, grid, face)
        reports = {name: _primitive_report(state, active=active, inner=inner, linear=linear, location=location)
                   for name, state in (("active", active), ("inner", inner), ("linear", linear))}
        expected_valid = all(record["valid"] for record in reports.values())
        gate_error = None
        try:
            checked_active = flux._validate_primitive_state(active)
            checked_inner = flux._validate_primitive_state(inner)
            with np.errstate(over="ignore", invalid="ignore"):
                checked_linear = flux._linear_outer_state(checked_active, checked_inner, face_fraction=fraction)
        except ValueError as error:
            gate_error = str(error)
        if expected_valid != (gate_error is None):
            raise RuntimeError("independent primitive diagnostic disagrees with original linear gate")
        if expected_valid and any(not np.array_equal(linear[name], checked_linear[name]) for name in flux.PRIMITIVE_FIELDS):
            raise RuntimeError("independent linear values differ from the original helper")
        faces.append({"face": face, "face_coordinate_kpc": coordinate, "face_fraction": fraction,
                      **reports, "original_linear_gate_passed": expected_valid,
                      "original_linear_gate_error": gate_error})
    invalid_faces = [record["face"] for record in faces if not record["original_linear_gate_passed"]]
    return {"definition": "active + face_fraction * (active - inner), unchanged original linear reconstruction",
            "nonfinite_encoding": "nan, +inf and -inf strings; invalid flux values are never published",
            "invalid_cell_inventory": "all invalid cells, independently for each face/state/primitive; no truncation",
            "native_primitives_valid": all(r["active"]["valid"] and r["inner"]["valid"] for r in faces),
            "all_faces_linear_valid": not invalid_faces, "invalid_faces": invalid_faces,
            "linear_invalid_cell_count_sum_over_faces": sum(r["linear"]["invalid_cell_count"] for r in faces),
            "faces": faces}


def measure_final_snapshot(snapshot, *, grid: flux.Grid, environment: Any,
                           boxes: Mapping[int, flux.ControlBox],
                           shell_layers: Sequence[int] = (1, 2, 4, 8)) -> dict[str, Any]:
    """Measure index 47 with strict original native gates and explicit linear availability.

    Storage uses the original whole-volume pass, which also fills its unchanged
    boundary cache. An invalid native field still fails the original storage
    gate; only failure of the optional linear extrapolation is represented as
    an unavailable branch in the returned addendum.
    """
    if snapshot.output_index != 47:
        raise ValueError("the final G-HI addendum is restricted to snapshot index 47")
    before = flux._snapshot_metadata(snapshot)
    with h5py.File(snapshot.input_h5, "r") as h5:
        if flux.require_datasets(h5, snapshot.timestep) != snapshot.shape:
            raise ValueError("snapshot shape changed before final G-HI measurement")
        variables = h5[f"/{snapshot.timestep}/vars"]
        cache = flux.DomainPlaneCache.create(snapshot.shape)
        storage = flux.measure_storage(variables, grid, environment, boxes, shell_layers, domain_plane_cache=cache)
        diagnostic = diagnose_linear_boundaries(cache, grid)
        rows = [{"surface": "domain_boundary", "reconstruction": "outer_active_cell", **row}
                for row in flux.measure_domain_surface(variables, grid, environment, "outer_active_cell", plane_cache=cache)]
        linear_valid = diagnostic["all_faces_linear_valid"]
        availability = {"domain_boundary": {
            "outer_active_cell": {"available": True, "reason": "original_native_gate_passed"},
            "linear_to_boundary_face": {"available": linear_valid,
                "reason": "all_six_faces_valid" if linear_valid else "invalid_linear_primitive_faces",
                "invalid_faces": diagnostic["invalid_faces"]}}}
        if linear_valid:
            rows.extend({"surface": "domain_boundary", "reconstruction": "linear_to_boundary_face", **row}
                        for row in flux.measure_domain_surface(variables, grid, environment, "linear_to_boundary_face", plane_cache=cache))
        for padding, box in sorted(boxes.items()):
            surface = f"nozzle_control_p{padding}"
            availability[surface] = {}
            for method in flux.CONTROL_RECONSTRUCTIONS:
                rows.extend({"surface": surface, "reconstruction": method, **row}
                            for row in flux.measure_control_surface(variables, grid, environment, box, method))
                availability[surface][method] = {"available": True, "reason": "original_native_gate_passed"}
    if flux._snapshot_metadata(snapshot) != before:
        raise ValueError("snapshot identity changed during final G-HI measurement")
    prefix = {"snapshot_index": snapshot.output_index, "actual_time_code": snapshot.time_code,
              "actual_time_myr": snapshot.actual_time_myr, "input_h5": str(snapshot.input_h5),
              "timestep": snapshot.timestep}
    return {"schema_version": 1, "method_version": METHOD_VERSION,
            "status": "measured_ghi_final_snapshot_addendum", "case": "G-HI", "snapshot": before,
            "flux_rows": [{**prefix, **row} for row in rows],
            "storage_rows": [{**prefix, **row} for row in storage],
            "linear_diagnostics": diagnostic, "surface_availability": availability,
            "scientific_qualification": {"qualified": False, "holds": [
                "addendum only; the original full flux request remains failed",
                "snapshot reconstruction is not solver-step delivery or source instrumentation",
                "linear branch is absent in its entirety if any native/linear face primitive is invalid"]}}
