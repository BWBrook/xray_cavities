#!/usr/bin/env python3
"""Measure snapshot-reconstructed Q-031 boundary and nozzle fluxes.

The reported fluxes are finite-volume diagnostics reconstructed from saved
cell-centred primitive variables.  They are not PLUTO Riemann fluxes.  Outward
flux is positive.  For a fixed control volume, the inferred internal source is

    source = storage_change + time_integral(outward_flux).

Including the fixed gravitational potential in both stored energy and the
advected Bernoulli function makes that identity appropriate for a static body
force, up to the discretisation and cadence errors exposed by the sensitivity
columns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import numpy as np

from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS,
    UNIT_DENSITY_CGS,
    UNIT_ENERGY_ERG,
    UNIT_LENGTH_CM,
    UNIT_VELOCITY_CMS,
    derive_widths,
    read_and_validate_axes,
    read_axis,
    require_datasets,
)
from select_common_age_hdf5 import BASELINE_ZERO_TOLERANCE_MYR, Snapshot, inspect_outputs
from snapshot_energy import (
    SECONDS_PER_MYR,
    canonical_snapshot_chain,
    load_environment,
    sha256_file,
)


METHOD_VERSION = 1
OUTER_RECONSTRUCTIONS = ("outer_active_cell", "linear_to_boundary_face")
CONTROL_RECONSTRUCTIONS = ("centered_primitives", "donor_cell_primitives")
FACE_NAMES = ("x_negative", "x_positive", "y_negative", "y_positive", "z_negative", "z_positive")
FLUX_FIELDS = (
    "mass_flux_outward_g_s",
    "mass_outflow_g_s",
    "mass_inflow_g_s",
    "enthalpy_flux_outward_erg_s",
    "kinetic_flux_outward_erg_s",
    "potential_flux_outward_erg_s",
    "total_energy_flux_outward_erg_s",
    "energy_outflow_erg_s",
    "energy_inflow_erg_s",
)
STORAGE_FIELDS = (
    "mass_g",
    "thermal_erg",
    "kinetic_erg",
    "gravitational_erg",
    "total_energy_erg",
)
PRIMITIVE_FIELDS = ("rho", "prs", "vx1", "vx2", "vx3")


@dataclass(frozen=True)
class Grid:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    dx: np.ndarray
    dy: np.ndarray
    dz: np.ndarray
    x_edges: np.ndarray
    y_edges: np.ndarray
    z_edges: np.ndarray
    edge_source: str = "provided"
    max_center_edge_residual_kpc: float = 0.0


@dataclass(frozen=True)
class ControlBox:
    i0: int
    i1: int
    j0: int
    j1: int
    k0: int
    k1: int
    source_i0: int
    source_i1: int
    source_j0: int
    source_j1: int
    source_k0: int
    source_k1: int
    source_cell_count: int
    padding_cells: int

    def contains(self, k: int, j: np.ndarray, i: np.ndarray) -> np.ndarray:
        return (
            (k >= self.k0)
            & (k <= self.k1)
            & (j >= self.j0)
            & (j <= self.j1)
            & (i >= self.i0)
            & (i <= self.i1)
        )


@dataclass
class DomainPlaneCache:
    shape: tuple[int, int, int]
    planes: dict[str, dict[int, dict[str, np.ndarray]]]
    captured_z_indices: set[int]

    @classmethod
    def create(cls, shape: tuple[int, int, int]) -> DomainPlaneCache:
        if len(shape) != 3 or min(shape) < 4:
            raise ValueError(f"domain plane cache requires three dimensions of at least four cells: {shape}")
        nz, ny, nx = shape
        axis_specs = {
            "x": (nx, (nz, ny)),
            "y": (ny, (nz, nx)),
            "z": (nz, (ny, nx)),
        }
        planes = {
            axis: {
                index: {
                    name: np.empty(plane_shape, dtype=np.float64)
                    for name in PRIMITIVE_FIELDS
                }
                for index in (0, 1, size - 2, size - 1)
            }
            for axis, (size, plane_shape) in axis_specs.items()
        }
        return cls(shape=shape, planes=planes, captured_z_indices=set())

    def capture_z_slab(self, iz: int, state: Mapping[str, np.ndarray]) -> None:
        nz, ny, nx = self.shape
        if iz < 0 or iz >= nz:
            raise ValueError(f"z-slab index {iz} is outside cache shape {self.shape}")
        if iz in self.captured_z_indices:
            raise ValueError(f"z-slab index {iz} was captured more than once")
        if set(state) != set(PRIMITIVE_FIELDS):
            raise ValueError(f"cache state fields differ from primitive contract: {sorted(state)}")
        if any(np.asarray(state[name]).shape != (ny, nx) for name in PRIMITIVE_FIELDS):
            raise ValueError(f"cache state shape differs from {(ny, nx)} at z index {iz}")
        for name in PRIMITIVE_FIELDS:
            values = np.asarray(state[name], dtype=np.float64)
            for index, cached in self.planes["x"].items():
                cached[name][iz, :] = values[:, index]
            for index, cached in self.planes["y"].items():
                cached[name][iz, :] = values[index, :]
            if iz in self.planes["z"]:
                self.planes["z"][iz][name][:, :] = values
        self.captured_z_indices.add(iz)

    def validate_complete(self) -> None:
        missing = sorted(set(range(self.shape[0])) - self.captured_z_indices)
        if missing:
            preview = ", ".join(str(index) for index in missing[:8])
            suffix = "" if len(missing) <= 8 else f", ... ({len(missing)} missing)"
            raise ValueError(f"incomplete domain plane cache; missing z slabs {preview}{suffix}")

    def primitive_state(self, selection: tuple[Any, Any, Any]) -> dict[str, np.ndarray]:
        self.validate_complete()
        integer_axes = [axis for axis, item in enumerate(selection) if isinstance(item, int)]
        full_slice_axes = [
            axis for axis, item in enumerate(selection)
            if isinstance(item, slice) and item.start is None and item.stop is None and item.step is None
        ]
        if len(integer_axes) != 1 or len(full_slice_axes) != 2:
            raise ValueError(f"domain cache only supports complete coordinate planes: {selection}")
        axis_number = integer_axes[0]
        axis = {0: "z", 1: "y", 2: "x"}[axis_number]
        index = int(selection[axis_number])
        if index < 0:
            index += self.shape[axis_number]
        if index not in self.planes[axis]:
            raise ValueError(f"domain plane {axis}={index} was not cached")
        return self.planes[axis][index]


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _atomic_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError(f"no rows to write: {path}")
    fields = list(materialized[0])
    if any(list(row) != fields for row in materialized):
        raise ValueError(f"inconsistent CSV schema: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(materialized)
    temporary.replace(path)


def _read_node_axis(h5: h5py.File, axis: str, expected: int) -> np.ndarray:
    data = h5[f"/node_coords/{axis}"]
    if data.ndim == 1:
        values = np.asarray(data[:], dtype=float)
    elif data.ndim == 3:
        if axis == "X":
            values = np.asarray(data[0, 0, :], dtype=float)
        elif axis == "Y":
            values = np.asarray(data[0, :, 0], dtype=float)
        elif axis == "Z":
            values = np.asarray(data[:, 0, 0], dtype=float)
        else:
            raise ValueError(axis)
    else:
        raise ValueError(f"unsupported /node_coords/{axis} rank {data.ndim}")
    if values.size != expected or not np.all(np.isfinite(values)) or not np.all(np.diff(values) > 0.0):
        raise ValueError(f"invalid /node_coords/{axis}: expected {expected} strictly increasing nodes")
    return values


def parse_grid_file(path: Path, shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lines = []
    for line in path.read_text().splitlines():
        fields = line.strip().split()
        if fields and not fields[0].startswith("#"):
            lines.append(fields)
    cursor = 0
    axes: list[np.ndarray] = []
    for expected_cells in (shape[2], shape[1], shape[0]):
        while cursor < len(lines) and len(lines[cursor]) != 1:
            cursor += 1
        if cursor >= len(lines):
            raise ValueError(f"missing axis count in {path}")
        try:
            count = int(lines[cursor][0])
        except ValueError as exc:
            raise ValueError(f"invalid axis count in {path}: {lines[cursor]}") from exc
        cursor += 1
        if count != expected_cells:
            raise ValueError(f"grid-file axis count {count} does not match HDF5 shape {expected_cells}")
        left = np.empty(count, dtype=float)
        right = np.empty(count, dtype=float)
        for offset in range(count):
            if cursor >= len(lines) or len(lines[cursor]) != 3:
                raise ValueError(f"missing grid cell {offset + 1} of {count} in {path}")
            index, lo, hi = lines[cursor]
            cursor += 1
            if int(index) != offset + 1:
                raise ValueError(f"non-sequential grid index {index} in {path}")
            left[offset], right[offset] = float(lo), float(hi)
        if not np.allclose(right[:-1], left[1:], rtol=0.0, atol=1.0e-10):
            raise ValueError(f"non-contiguous cell edges in {path}")
        axes.append(np.concatenate((left[:1], right)))
    return axes[0], axes[1], axes[2]


def read_grid(h5: h5py.File, shape: tuple[int, int, int], *, grid_file: Path | None = None) -> Grid:
    nz, ny, nx = shape
    x = read_axis(h5, "X", nz=nz, ny=ny, nx=nx)
    y = read_axis(h5, "Y", nz=nz, ny=ny, nx=nx)
    z = read_axis(h5, "Z", nz=nz, ny=ny, nx=nx)
    node_paths = tuple(f"/node_coords/{axis}" for axis in ("X", "Y", "Z"))
    if all(path in h5 for path in node_paths):
        x_edges = _read_node_axis(h5, "X", nx + 1)
        y_edges = _read_node_axis(h5, "Y", ny + 1)
        z_edges = _read_node_axis(h5, "Z", nz + 1)
        edge_source = "hdf5_node_coords"
        if grid_file is not None:
            file_edges = parse_grid_file(grid_file, shape)
            for axis, nodes, file_nodes in zip(("X", "Y", "Z"), (x_edges, y_edges, z_edges), file_edges, strict=True):
                if not np.allclose(nodes, file_nodes, rtol=0.0, atol=5.0e-5):
                    raise ValueError(f"HDF5 node_coords/{axis} disagrees with {grid_file}")
            edge_source = "hdf5_node_coords_crosschecked_grid_file"
    elif grid_file is not None:
        x_edges, y_edges, z_edges = parse_grid_file(grid_file, shape)
        edge_source = "grid_file"
    else:
        raise ValueError("HDF5 has no complete node_coords; --grid-file is required for exact FV geometry")
    residual = max(
        float(np.max(np.abs(x - 0.5 * (x_edges[:-1] + x_edges[1:])))),
        float(np.max(np.abs(y - 0.5 * (y_edges[:-1] + y_edges[1:])))),
        float(np.max(np.abs(z - 0.5 * (z_edges[:-1] + z_edges[1:])))),
    )
    scale = max(float(np.max(np.abs(x_edges))), float(np.max(np.abs(y_edges))), float(np.max(np.abs(z_edges))), 1.0)
    if residual > 5.0e-7 * scale:
        raise ValueError(f"cell centres disagree with exact edges: max residual {residual:.8g} kpc")
    return Grid(
        x, y, z, np.diff(x_edges), np.diff(y_edges), np.diff(z_edges),
        x_edges, y_edges, z_edges, edge_source, residual,
    )


def parse_pluto_parameters(path: Path) -> dict[str, float]:
    section = ""
    raw: dict[str, str] = {}
    found_parameters = False
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not stripped:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            found_parameters |= section == "Parameters"
            continue
        if section != "Parameters":
            continue
        fields = stripped.split()
        if len(fields) < 2:
            raise ValueError(f"invalid parameter line {line_number} in {path}")
        if fields[0] in raw:
            raise ValueError(f"duplicate parameter {fields[0]} in {path}")
        raw[fields[0]] = fields[1]
    if not found_parameters:
        raise ValueError(f"missing [Parameters] in {path}")
    required = (
        "JET_PWR", "JET_SPD", "JET_INJECTION_HEIGHT", "JET_INITIAL_RADIUS",
        "JET_X1O", "JET_X2O", "JET_X3O", "JET_ROTATION_ANGLE",
        "JET_START_TIME", "JET_END_TIME", "JET_ACTIVE_TIME", "JET_EPISODES",
    )
    result: dict[str, float] = {}
    for name in required:
        if name not in raw:
            raise ValueError(f"missing {name} in {path}")
        try:
            value = float(raw[name])
        except ValueError as exc:
            raise ValueError(f"non-numeric {name} in {path}") from exc
        if not math.isfinite(value):
            raise ValueError(f"non-finite {name} in {path}")
        result[name] = value
    if result["JET_PWR"] <= 0.0 or result["JET_SPD"] <= 0.0 or result["JET_INJECTION_HEIGHT"] <= 0.0:
        raise ValueError("jet power, speed and injection height must be positive")
    if result["JET_EPISODES"] != 1.0:
        raise ValueError("the nominal-energy comparator requires exactly one jet episode")
    expected_active = result["JET_END_TIME"] - result["JET_START_TIME"]
    if expected_active < 0.0 or not math.isclose(result["JET_ACTIVE_TIME"], expected_active, rel_tol=0.0, abs_tol=1.0e-10):
        raise ValueError("single-episode start/end/active times are inconsistent")
    return result


def parse_source_definitions(path: Path) -> dict[str, str]:
    text = path.read_text()
    names = (
        "DENSITY_PROFILE", "JET_INJECTION_ZONE", "JET_INJECTION_CAP",
        "JET_INJECTION_ROTATED", "JET_DENSITY_CALCULATION",
        "JET_RELATIVISTIC_DENSITY", "SUPERNOVAE_ENERGY_INPUT", "STELLAR_MASS_LOSS",
    )
    values: dict[str, str] = {}
    for name in names:
        matches = re.findall(rf"^\s*#define\s+{name}\s+(\w+)\s*$", text, flags=re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f"expected one active definition of {name} in {path}, found {matches}")
        values[name] = matches[0]
    expected = {
        "DENSITY_PROFILE": "ENV_TABULATED",
        "JET_INJECTION_ZONE": "SPHERICAL_INJECTION_ZONE",
        "JET_INJECTION_CAP": "YES",
        "JET_INJECTION_ROTATED": "NO",
        "JET_DENSITY_CALCULATION": "DENSITY_LENGTH_SCALE",
        "JET_RELATIVISTIC_DENSITY": "NO",
        "SUPERNOVAE_ENERGY_INPUT": "NO",
        "STELLAR_MASS_LOSS": "NO",
    }
    if values != expected:
        raise ValueError(f"unsupported source geometry {values}; implemented contract is {expected}")
    return values


def parse_core_definitions(path: Path) -> dict[str, str]:
    text = path.read_text()
    expected = {
        "PHYSICS": "HD", "DIMENSIONS": "3", "GEOMETRY": "CARTESIAN",
        "EOS": "IDEAL", "BODY_FORCE": "VECTOR", "COOLING": "NO",
    }
    values: dict[str, str] = {}
    for name, wanted in expected.items():
        matches = re.findall(rf"^\s*#define\s+{name}\s+(\w+)\s*$", text, flags=re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f"expected one active definition of {name} in {path}, found {matches}")
        values[name] = matches[0]
        if values[name] != wanted:
            raise ValueError(f"unsupported {name}={values[name]} in {path}; expected {wanted}")
    return values


def validate_absent_nonadvective_overrides(path: Path) -> dict[str, str]:
    text = path.read_text()
    result: dict[str, str] = {}
    for name in ("THERMAL_CONDUCTION", "VISCOSITY"):
        matches = re.findall(rf"^\s*#define\s+{name}\s+(\w+)\s*$", text, flags=re.MULTILINE)
        if not matches:
            result[name] = "no_problem_override; PLUTO default applies"
        elif matches == ["NO"]:
            result[name] = "explicitly_disabled"
        else:
            raise ValueError(
                f"unsupported {name} definition in {path}: {matches}; "
                "expected absence or exactly one definition set to NO"
            )
    return result


def validate_stationary_source(path: Path) -> str:
    text = path.read_text()
    matches = re.findall(r"^\s*#define\s+MOVING_INJECTION_REGION\s+(\w+)\s*$", text, flags=re.MULTILINE)
    if matches != ["MOVING_INJECTION_NONE"]:
        raise ValueError(f"source is not uniquely stationary in {path}: {matches}")
    return matches[0]


def validate_source_implementation(jet_source: Path, init_source: Path) -> None:
    jet_text = jet_source.read_text()
    init_text = init_source.read_text()
    required_jet = (
        "void Jet_WithinNozzle",
        "jtc->r <= jtc->jet_injection_properties->injection_region_radius",
    )
    required_init = (
        "JET_INJECTION_ZONE == SPHERICAL_INJECTION_ZONE", "if (within_r)",
        "FLAG_INTERNAL_BOUNDARY", "g_gamma = 5.0/3.0",
    )
    missing = [fragment for fragment in required_jet if fragment not in jet_text]
    missing += [fragment for fragment in required_init if fragment not in init_text]
    if missing:
        raise ValueError(f"source implementation does not match the spherical overwrite contract; missing {missing}")


def derive_control_box(
    grid: Grid,
    *,
    injection_height_kpc: float,
    centre_kpc: tuple[float, float, float],
    padding_cells: int = 1,
) -> ControlBox:
    if injection_height_kpc <= 0.0 or padding_cells < 1:
        raise ValueError("positive injection height and at least one padding cell are required")
    candidate_i = np.flatnonzero(np.abs(grid.x - centre_kpc[0]) <= injection_height_kpc)
    candidate_j = np.flatnonzero(np.abs(grid.y - centre_kpc[1]) <= injection_height_kpc)
    candidate_k = np.flatnonzero(np.abs(grid.z - centre_kpc[2]) <= injection_height_kpc)
    if not candidate_i.size or not candidate_j.size or not candidate_k.size:
        raise ValueError("the spherical injection region contains no candidate cell centres")
    xx = grid.x[candidate_i][None, None, :] - centre_kpc[0]
    yy = grid.y[candidate_j][None, :, None] - centre_kpc[1]
    zz = grid.z[candidate_k][:, None, None] - centre_kpc[2]
    source = xx * xx + yy * yy + zz * zz <= injection_height_kpc**2
    locations = np.argwhere(source)
    if locations.size == 0:
        raise ValueError("the spherical injection region contains no cell centres")
    local_min = locations.min(axis=0)
    local_max = locations.max(axis=0)
    k0s, j0s, i0s = candidate_k[local_min[0]], candidate_j[local_min[1]], candidate_i[local_min[2]]
    k1s, j1s, i1s = candidate_k[local_max[0]], candidate_j[local_max[1]], candidate_i[local_max[2]]
    k0, j0, i0 = int(k0s) - padding_cells, int(j0s) - padding_cells, int(i0s) - padding_cells
    k1, j1, i1 = int(k1s) + padding_cells, int(j1s) + padding_cells, int(i1s) + padding_cells
    if min(k0, j0, i0) < 1 or k1 >= grid.z.size - 1 or j1 >= grid.y.size - 1 or i1 >= grid.x.size - 1:
        raise ValueError("source-derived control box lacks an exterior neighbour on every face")
    return ControlBox(
        i0, i1, j0, j1, k0, k1,
        int(i0s), int(i1s), int(j0s), int(j1s), int(k0s), int(k1s),
        int(locations.shape[0]), padding_cells,
    )


def _primitive_state(variables: h5py.Group, selection: tuple[Any, Any, Any]) -> dict[str, np.ndarray]:
    state = {name: np.asarray(variables[name][selection], dtype=np.float64) for name in PRIMITIVE_FIELDS}
    return _validate_primitive_state(state)


def _validate_primitive_state(state: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    state = {name: np.asarray(state[name], dtype=np.float64) for name in PRIMITIVE_FIELDS}
    if any(not np.all(np.isfinite(value)) for value in state.values()):
        raise ValueError("non-finite primitive value on a measured surface")
    if np.any(state["rho"] <= 0.0) or np.any(state["prs"] <= 0.0):
        raise ValueError("non-positive density or pressure on a measured surface")
    return state


def _domain_primitive_state(
    variables: h5py.Group,
    selection: tuple[Any, Any, Any],
    plane_cache: DomainPlaneCache | None,
) -> dict[str, np.ndarray]:
    if plane_cache is None:
        return _primitive_state(variables, selection)
    return _validate_primitive_state(plane_cache.primitive_state(selection))


def _linear_outer_state(
    active: Mapping[str, np.ndarray], inner: Mapping[str, np.ndarray], *, face_fraction: float
) -> dict[str, np.ndarray]:
    if not math.isfinite(face_fraction) or face_fraction <= 0.0:
        raise ValueError("boundary extrapolation fraction must be positive and finite")
    result = {
        name: np.asarray(active[name]) + face_fraction * (np.asarray(active[name]) - np.asarray(inner[name]))
        for name in active
    }
    if np.any(result["rho"] <= 0.0) or np.any(result["prs"] <= 0.0) or any(not np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("linear boundary-face reconstruction produced a non-physical primitive state")
    return result


def _internal_face_state(
    inside: Mapping[str, np.ndarray],
    outside: Mapping[str, np.ndarray],
    *,
    normal_component: str,
    normal_sign: float,
    method: str,
    inside_distance: float,
    outside_distance: float,
) -> dict[str, np.ndarray]:
    if min(inside_distance, outside_distance) <= 0.0:
        raise ValueError("control face must lie strictly between adjacent cell centres")
    denominator = inside_distance + outside_distance
    centred = {
        name: (outside_distance * np.asarray(inside[name]) + inside_distance * np.asarray(outside[name])) / denominator
        for name in inside
    }
    if method == "centered_primitives":
        return centred
    if method != "donor_cell_primitives":
        raise ValueError(f"unknown control reconstruction: {method}")
    outward = normal_sign * centred[normal_component]
    return {name: np.where(outward >= 0.0, inside[name], outside[name]) for name in inside}


def flux_components(
    state: Mapping[str, np.ndarray],
    *,
    normal_component: str,
    normal_sign: float,
    area_kpc2: np.ndarray,
    potential_cm2_s2: np.ndarray,
) -> dict[str, float]:
    rho = np.asarray(state["rho"], dtype=float)
    pressure = np.asarray(state["prs"], dtype=float)
    v_normal = normal_sign * np.asarray(state[normal_component], dtype=float)
    v2 = sum(np.asarray(state[name], dtype=float) ** 2 for name in ("vx1", "vx2", "vx3"))
    area = np.broadcast_to(np.asarray(area_kpc2, dtype=float), rho.shape)
    phi_code = np.broadcast_to(np.asarray(potential_cm2_s2, dtype=float), rho.shape) / UNIT_VELOCITY_CMS**2
    mass_code = rho * v_normal * area
    enthalpy_code = mass_code * (GAMMA_GAS / (GAMMA_GAS - 1.0) * pressure / rho)
    kinetic_code = mass_code * (0.5 * v2)
    potential_code = mass_code * phi_code
    total_code = enthalpy_code + kinetic_code + potential_code
    mass_factor = UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS * UNIT_LENGTH_CM**2
    energy_factor = UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS**3 * UNIT_LENGTH_CM**2
    mass_cgs = mass_code * mass_factor
    total_cgs = total_code * energy_factor
    return {
        "mass_flux_outward_g_s": float(np.sum(mass_cgs)),
        "mass_outflow_g_s": float(np.sum(np.maximum(mass_cgs, 0.0))),
        "mass_inflow_g_s": float(np.sum(np.minimum(mass_cgs, 0.0))),
        "enthalpy_flux_outward_erg_s": float(np.sum(enthalpy_code) * energy_factor),
        "kinetic_flux_outward_erg_s": float(np.sum(kinetic_code) * energy_factor),
        "potential_flux_outward_erg_s": float(np.sum(potential_code) * energy_factor),
        "total_energy_flux_outward_erg_s": float(np.sum(total_cgs)),
        "energy_outflow_erg_s": float(np.sum(np.maximum(total_cgs, 0.0))),
        "energy_inflow_erg_s": float(np.sum(np.minimum(total_cgs, 0.0))),
    }


def _potential_on_face(environment: Any, a: np.ndarray, b: np.ndarray, fixed: float, *, axis: str) -> np.ndarray:
    if axis not in {"x", "y", "z"}:
        raise ValueError(axis)
    # a and b are ordered to match the two dimensions of the HDF5 face slice.
    radius = np.sqrt(fixed**2 + a[:, None] ** 2 + b[None, :] ** 2)
    return environment.potential_at_radius(radius * UNIT_LENGTH_CM)


def _sum_fluxes(rows: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    return {field: float(sum(float(row[field]) for row in rows)) for field in FLUX_FIELDS}


def measure_domain_surface(
    variables: h5py.Group,
    grid: Grid,
    environment: Any,
    method: str,
    *,
    plane_cache: DomainPlaneCache | None = None,
) -> list[dict[str, Any]]:
    if method not in OUTER_RECONSTRUCTIONS:
        raise ValueError(method)
    specs = (
        ("x_negative", (slice(None), slice(None), 0), (slice(None), slice(None), 1), "vx1", -1.0, grid.dz[:, None] * grid.dy[None, :], "x", grid.x_edges[0], grid.z, grid.y, grid.x[0], grid.x[1]),
        ("x_positive", (slice(None), slice(None), -1), (slice(None), slice(None), -2), "vx1", 1.0, grid.dz[:, None] * grid.dy[None, :], "x", grid.x_edges[-1], grid.z, grid.y, grid.x[-1], grid.x[-2]),
        ("y_negative", (slice(None), 0, slice(None)), (slice(None), 1, slice(None)), "vx2", -1.0, grid.dz[:, None] * grid.dx[None, :], "y", grid.y_edges[0], grid.z, grid.x, grid.y[0], grid.y[1]),
        ("y_positive", (slice(None), -1, slice(None)), (slice(None), -2, slice(None)), "vx2", 1.0, grid.dz[:, None] * grid.dx[None, :], "y", grid.y_edges[-1], grid.z, grid.x, grid.y[-1], grid.y[-2]),
        ("z_negative", (0, slice(None), slice(None)), (1, slice(None), slice(None)), "vx3", -1.0, grid.dy[:, None] * grid.dx[None, :], "z", grid.z_edges[0], grid.y, grid.x, grid.z[0], grid.z[1]),
        ("z_positive", (-1, slice(None), slice(None)), (-2, slice(None), slice(None)), "vx3", 1.0, grid.dy[:, None] * grid.dx[None, :], "z", grid.z_edges[-1], grid.y, grid.x, grid.z[-1], grid.z[-2]),
    )
    rows: list[dict[str, Any]] = []
    for face, active_sel, inner_sel, velocity, sign, area, axis, fixed, a, b, active_coordinate, inner_coordinate in specs:
        active = _domain_primitive_state(variables, active_sel, plane_cache)
        fraction = abs(fixed - active_coordinate) / abs(active_coordinate - inner_coordinate)
        state = active if method == "outer_active_cell" else _linear_outer_state(
            active, _domain_primitive_state(variables, inner_sel, plane_cache), face_fraction=fraction
        )
        potential = _potential_on_face(environment, a, b, fixed, axis=axis)
        values = flux_components(state, normal_component=velocity, normal_sign=sign, area_kpc2=area, potential_cm2_s2=potential)
        rows.append({
            "face": face, "face_coordinate_kpc": fixed,
            "face_area_kpc2": float(np.sum(area)),
            "normal_component": velocity, "normal_sign": sign, **values,
        })
    rows.append({
        "face": "closed_surface_total", "face_coordinate_kpc": "",
        "face_area_kpc2": float(sum(float(row["face_area_kpc2"]) for row in rows)),
        "normal_component": "", "normal_sign": "", **_sum_fluxes(rows),
    })
    return rows


def measure_control_surface(
    variables: h5py.Group, grid: Grid, environment: Any, box: ControlBox, method: str
) -> list[dict[str, Any]]:
    if method not in CONTROL_RECONSTRUCTIONS:
        raise ValueError(method)
    k, j, i = slice(box.k0, box.k1 + 1), slice(box.j0, box.j1 + 1), slice(box.i0, box.i1 + 1)
    specs = (
        ("x_negative", (k, j, box.i0), (k, j, box.i0 - 1), "vx1", -1.0, grid.dz[box.k0:box.k1+1, None] * grid.dy[None, box.j0:box.j1+1], "x", grid.x_edges[box.i0], grid.z[box.k0:box.k1+1], grid.y[box.j0:box.j1+1], grid.x[box.i0], grid.x[box.i0-1]),
        ("x_positive", (k, j, box.i1), (k, j, box.i1 + 1), "vx1", 1.0, grid.dz[box.k0:box.k1+1, None] * grid.dy[None, box.j0:box.j1+1], "x", grid.x_edges[box.i1+1], grid.z[box.k0:box.k1+1], grid.y[box.j0:box.j1+1], grid.x[box.i1], grid.x[box.i1+1]),
        ("y_negative", (k, box.j0, i), (k, box.j0 - 1, i), "vx2", -1.0, grid.dz[box.k0:box.k1+1, None] * grid.dx[None, box.i0:box.i1+1], "y", grid.y_edges[box.j0], grid.z[box.k0:box.k1+1], grid.x[box.i0:box.i1+1], grid.y[box.j0], grid.y[box.j0-1]),
        ("y_positive", (k, box.j1, i), (k, box.j1 + 1, i), "vx2", 1.0, grid.dz[box.k0:box.k1+1, None] * grid.dx[None, box.i0:box.i1+1], "y", grid.y_edges[box.j1+1], grid.z[box.k0:box.k1+1], grid.x[box.i0:box.i1+1], grid.y[box.j1], grid.y[box.j1+1]),
        ("z_negative", (box.k0, j, i), (box.k0 - 1, j, i), "vx3", -1.0, grid.dy[box.j0:box.j1+1, None] * grid.dx[None, box.i0:box.i1+1], "z", grid.z_edges[box.k0], grid.y[box.j0:box.j1+1], grid.x[box.i0:box.i1+1], grid.z[box.k0], grid.z[box.k0-1]),
        ("z_positive", (box.k1, j, i), (box.k1 + 1, j, i), "vx3", 1.0, grid.dy[box.j0:box.j1+1, None] * grid.dx[None, box.i0:box.i1+1], "z", grid.z_edges[box.k1+1], grid.y[box.j0:box.j1+1], grid.x[box.i0:box.i1+1], grid.z[box.k1], grid.z[box.k1+1]),
    )
    rows: list[dict[str, Any]] = []
    for face, inside_sel, outside_sel, velocity, sign, area, axis, fixed, a, b, inside_coordinate, outside_coordinate in specs:
        inside = _primitive_state(variables, inside_sel)
        outside = _primitive_state(variables, outside_sel)
        state = _internal_face_state(
            inside, outside, normal_component=velocity, normal_sign=sign, method=method,
            inside_distance=abs(inside_coordinate - fixed), outside_distance=abs(outside_coordinate - fixed),
        )
        potential = _potential_on_face(environment, a, b, fixed, axis=axis)
        values = flux_components(state, normal_component=velocity, normal_sign=sign, area_kpc2=area, potential_cm2_s2=potential)
        rows.append({
            "face": face, "face_coordinate_kpc": fixed,
            "face_area_kpc2": float(np.sum(area)),
            "normal_component": velocity, "normal_sign": sign, **values,
        })
    rows.append({
        "face": "closed_surface_total", "face_coordinate_kpc": "",
        "face_area_kpc2": float(sum(float(row["face_area_kpc2"]) for row in rows)),
        "normal_component": "", "normal_sign": "", **_sum_fluxes(rows),
    })
    return rows


def measure_storage(
    variables: h5py.Group,
    grid: Grid,
    environment: Any,
    boxes: Mapping[int, ControlBox],
    shell_layers: Sequence[int],
    *,
    domain_plane_cache: DomainPlaneCache | None = None,
) -> list[dict[str, Any]]:
    regions = (
        "whole_grid", *(f"nozzle_control_p{padding}" for padding in sorted(boxes)),
        *(f"boundary_layer_{n}" for n in shell_layers),
    )
    volume_geometries = {
        "exact_fv_nodes": (grid.dx, grid.dy, grid.dz),
        "legacy_midpoint_centres": (derive_widths(grid.x), derive_widths(grid.y), derive_widths(grid.z)),
    }
    totals = {
        (geometry, region): {field: 0.0 for field in STORAGE_FIELDS}
        for geometry in volume_geometries for region in regions
    }
    ny, nx = grid.y.size, grid.x.size
    if domain_plane_cache is not None and domain_plane_cache.shape != (grid.z.size, ny, nx):
        raise ValueError(
            f"domain plane cache shape {domain_plane_cache.shape} differs from grid "
            f"{(grid.z.size, ny, nx)}"
        )
    jj, ii = np.indices((ny, nx))
    xy2 = grid.y[:, None] ** 2 + grid.x[None, :] ** 2
    for iz, z_value in enumerate(grid.z):
        state = _primitive_state(variables, (iz, slice(None), slice(None)))
        if domain_plane_cache is not None:
            domain_plane_cache.capture_z_slab(iz, state)
        phi = environment.potential_at_radius(np.sqrt(xy2 + z_value**2) * UNIT_LENGTH_CM)
        v2 = state["vx1"]**2 + state["vx2"]**2 + state["vx3"]**2
        masks: dict[str, np.ndarray] = {
            "whole_grid": np.ones((ny, nx), dtype=bool),
        }
        for padding, box in boxes.items():
            masks[f"nozzle_control_p{padding}"] = box.contains(iz, jj, ii)
        for layers in shell_layers:
            masks[f"boundary_layer_{layers}"] = (
                (iz < layers) | (iz >= grid.z.size - layers)
                | (jj < layers) | (jj >= ny - layers)
                | (ii < layers) | (ii >= nx - layers)
            )
        for geometry, (dx, dy, dz) in volume_geometries.items():
            volume = dy[:, None] * dx[None, :] * dz[iz]
            mass = state["rho"] * volume * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
            values = {
                "mass_g": mass,
                "thermal_erg": state["prs"] * volume / (GAMMA_GAS - 1.0) * UNIT_ENERGY_ERG,
                "kinetic_erg": 0.5 * state["rho"] * v2 * volume * UNIT_ENERGY_ERG,
                "gravitational_erg": mass * phi,
            }
            for region, mask in masks.items():
                for field, array in values.items():
                    totals[(geometry, region)][field] += float(np.sum(array[mask]))
    rows = []
    for geometry in volume_geometries:
        for region in regions:
            values = totals[(geometry, region)]
            values["total_energy_erg"] = values["thermal_erg"] + values["kinetic_erg"] + values["gravitational_erg"]
            rows.append({"volume_geometry": geometry, "region": region, **values})
    return rows


def analyze_snapshot(
    snapshot: Snapshot,
    *,
    grid: Grid,
    environment: Any,
    boxes: Mapping[int, ControlBox],
    shell_layers: Sequence[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flux_rows: list[dict[str, Any]] = []
    with h5py.File(snapshot.input_h5, "r") as h5:
        if require_datasets(h5, snapshot.timestep) != snapshot.shape:
            raise ValueError(f"snapshot shape changed: {snapshot.input_h5}:{snapshot.timestep}")
        variables = h5[f"/{snapshot.timestep}/vars"]
        domain_plane_cache = DomainPlaneCache.create(snapshot.shape)
        storage_rows = measure_storage(
            variables, grid, environment, boxes, shell_layers,
            domain_plane_cache=domain_plane_cache,
        )
        for method in OUTER_RECONSTRUCTIONS:
            for row in measure_domain_surface(
                variables, grid, environment, method, plane_cache=domain_plane_cache,
            ):
                flux_rows.append({"surface": "domain_boundary", "reconstruction": method, **row})
        del domain_plane_cache
        for padding, box in sorted(boxes.items()):
            for method in CONTROL_RECONSTRUCTIONS:
                for row in measure_control_surface(variables, grid, environment, box, method):
                    flux_rows.append({"surface": f"nozzle_control_p{padding}", "reconstruction": method, **row})
    prefix = {
        "snapshot_index": snapshot.output_index,
        "actual_time_code": snapshot.time_code,
        "actual_time_myr": snapshot.actual_time_myr,
        "input_h5": str(snapshot.input_h5),
        "timestep": snapshot.timestep,
    }
    return ([prefix | row for row in flux_rows], [prefix | row for row in storage_rows])


def integrate_flux_series(
    flux_rows: Sequence[Mapping[str, Any]],
    storage_rows: Sequence[Mapping[str, Any]],
    *,
    one_sided_power_erg_s: float,
    jet_start_myr: float,
    jet_active_myr: float,
) -> list[dict[str, Any]]:
    storage = {
        (float(row["actual_time_myr"]), str(row["region"])): row
        for row in storage_rows if row["volume_geometry"] == "exact_fv_nodes"
    }
    series: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in flux_rows:
        if row["face"] == "closed_surface_total":
            series.setdefault((str(row["surface"]), str(row["reconstruction"])), []).append(row)
    output: list[dict[str, Any]] = []
    for (surface, reconstruction), rows in sorted(series.items()):
        ordered = sorted(rows, key=lambda row: float(row["actual_time_myr"]))
        region = "whole_grid" if surface == "domain_boundary" else surface
        cumulative_mass = {method: 0.0 for method in ("left_rectangle", "trapezoid", "right_rectangle")}
        cumulative_energy = {method: 0.0 for method in cumulative_mass}
        first_storage = storage[(float(ordered[0]["actual_time_myr"]), region)]
        for previous, current in zip(ordered, ordered[1:]):
            t0, t1 = float(previous["actual_time_myr"]), float(current["actual_time_myr"])
            dt_s = (t1 - t0) * SECONDS_PER_MYR
            if dt_s <= 0.0:
                raise ValueError("flux times are not strictly increasing")
            for quadrature, weight in (("left_rectangle", 0.0), ("trapezoid", 0.5), ("right_rectangle", 1.0)):
                mass_flux = (1.0 - weight) * float(previous["mass_flux_outward_g_s"]) + weight * float(current["mass_flux_outward_g_s"])
                energy_flux = (1.0 - weight) * float(previous["total_energy_flux_outward_erg_s"]) + weight * float(current["total_energy_flux_outward_erg_s"])
                interval_mass = mass_flux * dt_s
                interval_energy = energy_flux * dt_s
                cumulative_mass[quadrature] += interval_mass
                cumulative_energy[quadrature] += interval_energy
                current_storage = storage[(t1, region)]
                previous_storage = storage[(t0, region)]
                delta_mass = float(current_storage["mass_g"]) - float(previous_storage["mass_g"])
                delta_energy = float(current_storage["total_energy_erg"]) - float(previous_storage["total_energy_erg"])
                cumulative_storage_mass = float(current_storage["mass_g"]) - float(first_storage["mass_g"])
                cumulative_storage_energy = float(current_storage["total_energy_erg"]) - float(first_storage["total_energy_erg"])
                active_elapsed = min(max(t1 - jet_start_myr, 0.0), jet_active_myr)
                nominal = 2.0 * one_sided_power_erg_s * active_elapsed * SECONDS_PER_MYR
                source_energy = delta_energy + interval_energy
                cumulative_source_energy = cumulative_storage_energy + cumulative_energy[quadrature]
                output.append({
                    "surface": surface,
                    "storage_region": region,
                    "reconstruction": reconstruction,
                    "temporal_quadrature": quadrature,
                    "interval_start_myr": t0,
                    "interval_end_myr": t1,
                    "interval_duration_myr": t1 - t0,
                    "storage_mass_change_g": delta_mass,
                    "integrated_mass_flux_outward_g": interval_mass,
                    "inferred_internal_mass_source_g": delta_mass + interval_mass,
                    "storage_energy_change_erg": delta_energy,
                    "integrated_energy_flux_outward_erg": interval_energy,
                    "inferred_internal_energy_source_erg": source_energy,
                    "cumulative_storage_mass_change_g": cumulative_storage_mass,
                    "cumulative_integrated_mass_flux_outward_g": cumulative_mass[quadrature],
                    "cumulative_inferred_internal_mass_source_g": cumulative_storage_mass + cumulative_mass[quadrature],
                    "cumulative_storage_energy_change_erg": cumulative_storage_energy,
                    "cumulative_integrated_energy_flux_outward_erg": cumulative_energy[quadrature],
                    "cumulative_inferred_internal_energy_source_erg": cumulative_source_energy,
                    "nominal_configured_bipolar_energy_erg": nominal,
                    "cumulative_source_to_nominal_energy_ratio": cumulative_source_energy / nominal if nominal > 0.0 else "",
                })
    return output


def _snapshot_metadata(snapshot: Snapshot) -> dict[str, Any]:
    stat = snapshot.input_h5.stat()
    return {
        "path": str(snapshot.input_h5), "resolved_path": str(snapshot.input_h5.resolve()),
        "timestep": snapshot.timestep,
        "output_index": snapshot.output_index, "time_code": snapshot.time_code,
        "shape": list(snapshot.shape), "size_bytes": stat.st_size,
        "device": stat.st_dev, "inode": stat.st_ino,
        "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns,
    }


def _signature(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_analysis(
    *,
    case: str,
    outputs_dirs: Sequence[Path],
    environment_path: Path,
    pluto_ini: Path,
    problem_source_dir: Path,
    output_dir: Path,
    grid_file: Path | None = None,
    shell_layers: Sequence[int] = (1, 2, 4, 8),
    control_padding_cells: Sequence[int] = (1, 2, 4),
) -> dict[str, Any]:
    if not case:
        raise ValueError("case is required")
    if not shell_layers or any(layer < 1 for layer in shell_layers) or len(set(shell_layers)) != len(shell_layers):
        raise ValueError("shell layers must be unique positive integers")
    if not control_padding_cells or any(padding < 1 for padding in control_padding_cells) or len(set(control_padding_cells)) != len(control_padding_cells):
        raise ValueError("control padding values must be unique positive integers")
    raw_snapshots = [snapshot for outputs_dir in outputs_dirs for snapshot in inspect_outputs(outputs_dir)]
    snapshots = canonical_snapshot_chain(outputs_dirs)
    if abs(snapshots[0].actual_time_myr) > BASELINE_ZERO_TOLERANCE_MYR:
        raise ValueError("the canonical chain must start at the zero-time snapshot")
    parameters = parse_pluto_parameters(pluto_ini)
    definitions_path = problem_source_dir / "definitions.h"
    definitions_usr_path = problem_source_dir / "definitions_usr.h"
    jet_source_path = problem_source_dir / "jet.c"
    init_source_path = problem_source_dir / "init.c"
    pluto_usr_path = problem_source_dir / "pluto_usr.h"
    definitions = parse_source_definitions(definitions_usr_path)
    core_definitions = parse_core_definitions(definitions_path)
    absent_nonadvective_overrides = validate_absent_nonadvective_overrides(definitions_path)
    stationary_source = validate_stationary_source(pluto_usr_path)
    validate_source_implementation(jet_source_path, init_source_path)
    environment = load_environment(environment_path)
    with h5py.File(snapshots[0].input_h5, "r") as baseline_h5:
        grid = read_grid(baseline_h5, snapshots[0].shape, grid_file=grid_file)
    if max(shell_layers) * 2 >= min(grid.x.size, grid.y.size, grid.z.size):
        raise ValueError("largest boundary layer overlaps itself across the grid")
    centre = (-parameters["JET_X1O"], -parameters["JET_X2O"], -parameters["JET_X3O"])
    boxes = {
        padding: derive_control_box(
            grid,
            injection_height_kpc=parameters["JET_INJECTION_HEIGHT"],
            centre_kpc=centre,
            padding_cells=padding,
        )
        for padding in sorted(control_padding_cells)
    }
    snapshot_metadata = [_snapshot_metadata(snapshot) for snapshot in snapshots]
    raw_snapshot_metadata = [_snapshot_metadata(snapshot) for snapshot in raw_snapshots]
    raw_by_index: dict[int, list[Snapshot]] = {}
    for snapshot in raw_snapshots:
        raw_by_index.setdefault(snapshot.output_index, []).append(snapshot)
    overlap_audit = []
    canonical_by_index = {snapshot.output_index: snapshot for snapshot in snapshots}
    for index, candidates in sorted(raw_by_index.items()):
        if len(candidates) < 2:
            continue
        chosen = canonical_by_index[index]
        overlap_audit.append({
            "output_index": index,
            "candidate_count": len(candidates),
            "candidates": [_snapshot_metadata(candidate) for candidate in candidates],
            "canonical_choice": _snapshot_metadata(chosen),
            "time_shape_match": len({(candidate.time_code, candidate.shape) for candidate in candidates}) == 1,
            "size_match": len({candidate.input_h5.stat().st_size for candidate in candidates}) == 1,
            "payload_identity_checked": False,
        })
    problem_source_paths = {
        str(path.relative_to(problem_source_dir)): path
        for path in sorted(problem_source_dir.rglob("*"))
        if path.is_file() and path.suffix in {".c", ".h"}
    }
    if not problem_source_paths:
        raise ValueError(f"no C source files found in {problem_source_dir}")
    analysis_paths = {
        path.name: path
        for path in (
            Path(__file__).resolve(),
            Path(__file__).with_name("snapshot_energy.py").resolve(),
            Path(__file__).with_name("pluto_h5_level3_ambient_extract.py").resolve(),
            Path(__file__).with_name("select_common_age_hdf5.py").resolve(),
        )
    }
    problem_source_hashes = {name: sha256_file(path) for name, path in problem_source_paths.items()}
    analysis_hashes = {name: sha256_file(path) for name, path in analysis_paths.items()}
    signature_payload = {
        "method_version": METHOD_VERSION,
        "case": case,
        "snapshots": snapshot_metadata,
        "environment_path": str(environment_path.resolve()),
        "environment_sha256": sha256_file(environment_path),
        "pluto_ini_path": str(pluto_ini.resolve()),
        "pluto_ini_sha256": sha256_file(pluto_ini),
        "problem_source_dir": str(problem_source_dir.resolve()),
        "grid_geometry": {
            "edge_source": grid.edge_source,
            "grid_file": str(grid_file) if grid_file is not None else None,
            "grid_file_sha256": sha256_file(grid_file) if grid_file is not None else None,
            "max_cell_center_edge_midpoint_residual_kpc": grid.max_center_edge_residual_kpc,
        },
        "problem_source_hashes": problem_source_hashes,
        "analysis_implementation_hashes": analysis_hashes,
        "shell_layers": list(shell_layers),
        "control_padding_cells": list(sorted(control_padding_cells)),
        "control_boxes": {str(padding): box.__dict__ for padding, box in boxes.items()},
        "canonical_overlap_audit": overlap_audit,
    }
    analysis_signature = _signature(signature_payload)
    print(
        f"[q031-flux] case={case} snapshots={len(snapshots)} shape={snapshots[0].shape} "
        f"edge_source={grid.edge_source} control_padding={list(sorted(boxes))} "
        f"signature={analysis_signature}",
        flush=True,
    )
    checkpoint_dir = output_dir / "checkpoints"
    all_flux: list[dict[str, Any]] = []
    all_storage: list[dict[str, Any]] = []
    for ordinal, snapshot in enumerate(snapshots):
        started = time.monotonic()
        expected_metadata = snapshot_metadata[ordinal]
        if _snapshot_metadata(snapshot) != expected_metadata:
            raise ValueError(f"snapshot identity changed before analysis: {snapshot.input_h5}")
        checkpoint = checkpoint_dir / f"{ordinal:04d}-{snapshot.output_index:04d}.json"
        if checkpoint.exists():
            saved = json.loads(checkpoint.read_text())
            if saved.get("analysis_signature") != analysis_signature or saved.get("snapshot") != expected_metadata:
                raise ValueError(f"checkpoint provenance mismatch: {checkpoint}")
            flux_rows, storage_rows = saved["flux_rows"], saved["storage_rows"]
            action = "reused"
        else:
            with h5py.File(snapshots[0].input_h5, "r") as baseline_h5, h5py.File(snapshot.input_h5, "r") as target_h5:
                read_and_validate_axes(base=baseline_h5, final=target_h5, nz=snapshot.shape[0], ny=snapshot.shape[1], nx=snapshot.shape[2])
                target_grid = read_grid(target_h5, snapshot.shape, grid_file=grid_file)
                for axis in ("x_edges", "y_edges", "z_edges"):
                    if not np.array_equal(getattr(grid, axis), getattr(target_grid, axis)):
                        raise ValueError(f"snapshot exact node geometry changed for {axis}: {snapshot.input_h5}")
            flux_rows, storage_rows = analyze_snapshot(snapshot, grid=grid, environment=environment, boxes=boxes, shell_layers=shell_layers)
            if _snapshot_metadata(snapshot) != expected_metadata:
                raise ValueError(f"snapshot identity changed during analysis: {snapshot.input_h5}")
            _atomic_json(checkpoint, {
                "analysis_signature": analysis_signature,
                "snapshot": expected_metadata,
                "flux_rows": flux_rows,
                "storage_rows": storage_rows,
            })
            action = "computed"
        all_flux.extend({"case": case, **row} for row in flux_rows)
        all_storage.extend({"case": case, **row} for row in storage_rows)
        print(
            f"[q031-flux] {action} snapshot {ordinal+1}/{len(snapshots)} "
            f"index={snapshot.output_index} time_myr={snapshot.actual_time_myr:.9g} "
            f"elapsed_s={time.monotonic()-started:.3f}",
            flush=True,
        )
    if [_snapshot_metadata(snapshot) for snapshot in snapshots] != snapshot_metadata:
        raise ValueError("one or more native snapshot identities changed before finalization")
    if [_snapshot_metadata(snapshot) for snapshot in raw_snapshots] != raw_snapshot_metadata:
        raise ValueError("one or more canonical-chain candidate identities changed before finalization")
    if {name: sha256_file(path) for name, path in problem_source_paths.items()} != problem_source_hashes:
        raise ValueError("problem source changed during analysis")
    if {name: sha256_file(path) for name, path in analysis_paths.items()} != analysis_hashes:
        raise ValueError("analysis implementation changed during analysis")
    if sha256_file(environment_path) != signature_payload["environment_sha256"] or sha256_file(pluto_ini) != signature_payload["pluto_ini_sha256"]:
        raise ValueError("environment or rendered configuration changed during analysis")
    if grid_file is not None and sha256_file(grid_file) != signature_payload["grid_geometry"]["grid_file_sha256"]:
        raise ValueError("grid file changed during analysis")
    integrated = integrate_flux_series(
        all_flux,
        all_storage,
        one_sided_power_erg_s=parameters["JET_PWR"],
        jet_start_myr=parameters["JET_START_TIME"],
        jet_active_myr=parameters["JET_ACTIVE_TIME"],
    )
    integrated = [{"case": case, **row} for row in integrated]
    _atomic_csv(output_dir / "instantaneous_surface_fluxes.csv", all_flux)
    baseline_storage = {
        (row["volume_geometry"], row["region"]): row
        for row in all_storage
        if float(row["actual_time_myr"]) == min(float(item["actual_time_myr"]) for item in all_storage)
    }
    storage_with_delta = []
    for row in all_storage:
        baseline = baseline_storage[(str(row["volume_geometry"]), str(row["region"]))]
        storage_with_delta.append(row | {f"delta_{field}": float(row[field]) - float(baseline[field]) for field in STORAGE_FIELDS})
    _atomic_csv(output_dir / "region_storage.csv", storage_with_delta)
    _atomic_csv(output_dir / "integrated_control_balances.csv", integrated)
    provenance = {
        **signature_payload,
        "analysis_signature": analysis_signature,
        "source_definitions": definitions,
        "core_definitions": core_definitions,
        "absent_nonadvective_overrides": absent_nonadvective_overrides,
        "moving_injection_region": stationary_source,
        "canonical_overlap_policy": "for matching output indices, later supplied segments win only after time and shape agree; candidate metadata are reported but payload identity is not asserted",
        "pluto_parameters": parameters,
        "control_box_edges_kpc": {
            str(padding): {
                "x": [float(grid.x_edges[box.i0]), float(grid.x_edges[box.i1 + 1])],
                "y": [float(grid.y_edges[box.j0]), float(grid.y_edges[box.j1 + 1])],
                "z": [float(grid.z_edges[box.k0]), float(grid.z_edges[box.k1 + 1])],
            }
            for padding, box in boxes.items()
        },
        "domain_edges_kpc": {
            "x": [float(grid.x_edges[0]), float(grid.x_edges[-1])],
            "y": [float(grid.y_edges[0]), float(grid.y_edges[-1])],
            "z": [float(grid.z_edges[0]), float(grid.z_edges[-1])],
        },
        "sign_convention": "outward surface flux is positive; inward flux is negative",
        "scientific_status": "cell-centred snapshot reconstruction, not PLUTO numerical Riemann flux",
        "native_input_identity_scope": "resolved path, device, inode, size, ctime and mtime before/after each read and at finalization; native payloads are not rehashed",
        "energy_definition": "internal + kinetic + fixed centre-zero gravitational potential",
        "storage_geometry_note": "control balances use exact_fv_nodes; legacy_midpoint_centres is emitted only to reconcile earlier compact ledgers",
        "boundary_layer_definition": "cumulative union of the first and last n exact grid-cell layers on all six domain faces; overlapping edges and corners are counted once",
        "initial_state_note": "the retained t=0 snapshot is already nozzle-initialized; inferred cumulative source excludes the initial overwrite and measures post-baseline delivery",
        "sensitivity_note": "padding, centered/donor, linear boundary and temporal quadrature variants are reconstruction scenarios, not confidence bounds",
        "outputs": {},
    }
    _atomic_json(output_dir / "provenance.json", provenance)
    data_names = ("instantaneous_surface_fluxes.csv", "region_storage.csv", "integrated_control_balances.csv")
    provenance["outputs"] = {name: sha256_file(output_dir / name) for name in data_names}
    _atomic_json(output_dir / "provenance.json", provenance)
    output_names = (*data_names, "provenance.json")
    hashes = [{"sha256": sha256_file(output_dir / name), "filename": name} for name in output_names]
    _atomic_csv(output_dir / "manifest.sha256.csv", hashes)
    return provenance


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--outputs-dir", type=Path, action="append", required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--pluto-ini", type=Path, required=True)
    parser.add_argument("--problem-source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--grid-file", type=Path)
    parser.add_argument("--shell-layers", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--control-padding-cells", type=int, nargs="+", default=[1, 2, 4])
    args = parser.parse_args()
    run_analysis(
        case=args.case,
        outputs_dirs=args.outputs_dir,
        environment_path=args.environment,
        pluto_ini=args.pluto_ini,
        problem_source_dir=args.problem_source_dir,
        output_dir=args.output_dir,
        grid_file=args.grid_file,
        shell_layers=args.shell_layers,
        control_padding_cells=args.control_padding_cells,
    )


if __name__ == "__main__":
    main()
