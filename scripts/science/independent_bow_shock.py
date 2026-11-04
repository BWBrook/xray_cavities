#!/usr/bin/env python3
"""Independent local Rankine--Hugoniot shock finder on a Cartesian grid.

The detector intentionally uses only primitive hydrodynamic fields.  Pressure
defines the local jump direction, while the velocity divergence supplies the
compression gate.  All derivatives and interpolation coordinates are physical
cell-centre coordinates, so stretched-grid cells are not treated as unit cubes.

``iter_shock_candidates_tiled`` is the production-facing entry point.  It
accepts NumPy arrays, memory maps, or HDF5-like datasets and reads bounded 3-D
tiles with a four-cell halo.  The caller can reduce each returned batch into a
ray front without retaining a full-domain candidate mask.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import numpy as np
from scipy.interpolate import RegularGridInterpolator


GAMMA = 5.0 / 3.0
REQUIRED_FIELDS = ("rho", "prs", "vx1", "vx2", "vx3")


@dataclass(frozen=True)
class Grid3D:
    """Cell-centred Cartesian geometry; array order is ``(z, y, x)``."""

    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    x_edges: np.ndarray
    y_edges: np.ndarray
    z_edges: np.ndarray

    def __post_init__(self) -> None:
        for name in ("x", "y", "z"):
            centres = np.asarray(getattr(self, name), dtype=float)
            edges = np.asarray(getattr(self, f"{name}_edges"), dtype=float)
            if centres.ndim != 1 or edges.shape != (centres.size + 1,):
                raise ValueError(f"invalid {name} axis geometry")
            if centres.size < 7 or np.any(np.diff(centres) <= 0.0) or np.any(np.diff(edges) <= 0.0):
                raise ValueError(f"{name} axis must contain at least seven increasing cells")
            if not np.allclose(centres, 0.5 * (edges[:-1] + edges[1:]), rtol=0.0, atol=5.0e-10):
                raise ValueError(f"{name} centres are inconsistent with edges")

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.z.size, self.y.size, self.x.size

    @property
    def widths(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return np.diff(self.x_edges), np.diff(self.y_edges), np.diff(self.z_edges)

    def subgrid(self, z_slice: slice, y_slice: slice, x_slice: slice) -> Grid3D:
        axes = []
        for name, item in zip(("x", "y", "z"), (x_slice, y_slice, z_slice), strict=True):
            if item.step not in (None, 1) or item.start is None or item.stop is None:
                raise ValueError("subgrid slices must be explicit, contiguous half-open ranges")
            centres = getattr(self, name)[item]
            edges = getattr(self, f"{name}_edges")[item.start:item.stop + 1]
            axes.extend((centres, edges))
        x, x_edges, y, y_edges, z, z_edges = axes
        return Grid3D(x, y, z, x_edges, y_edges, z_edges)


@dataclass(frozen=True)
class CandidateBatch:
    """Accepted cells from one tile, with indices in the parent grid."""

    indices_zyx: np.ndarray
    coordinates_xyz: np.ndarray
    normals_xyz: np.ndarray
    divergence: np.ndarray
    pressure_ratio: np.ndarray
    density_ratio: np.ndarray
    temperature_ratio: np.ndarray
    mach_pressure: np.ndarray
    mach_density: np.ndarray

    def __len__(self) -> int:
        return int(self.indices_zyx.shape[0])

    @classmethod
    def empty(cls) -> CandidateBatch:
        return cls(
            np.empty((0, 3), dtype=np.int64),
            np.empty((0, 3), dtype=float),
            np.empty((0, 3), dtype=float),
            *(np.empty(0, dtype=float) for _ in range(6)),
        )

    @classmethod
    def concatenate(cls, batches: Sequence[CandidateBatch]) -> CandidateBatch:
        nonempty = [batch for batch in batches if len(batch)]
        if not nonempty:
            return cls.empty()
        return cls(*(np.concatenate([getattr(batch, field) for batch in nonempty], axis=0)
                     for field in cls.__dataclass_fields__))


def parse_pluto_grid(path: Path) -> Grid3D:
    """Read exact PLUTO ``grid.out`` edges."""

    rows = []
    for line in path.read_text().splitlines():
        fields = line.strip().split()
        if fields and not fields[0].startswith("#"):
            rows.append(fields)
    cursor = 0
    axes = []
    for axis in ("X1", "X2", "X3"):
        while cursor < len(rows) and len(rows[cursor]) != 1:
            cursor += 1
        if cursor == len(rows):
            raise ValueError(f"missing {axis} count in {path}")
        count = int(rows[cursor][0])
        cursor += 1
        left = np.empty(count, dtype=float)
        right = np.empty(count, dtype=float)
        for offset in range(count):
            if cursor == len(rows) or len(rows[cursor]) != 3:
                raise ValueError(f"missing {axis} cell {offset + 1} in {path}")
            index, lo, hi = rows[cursor]
            cursor += 1
            if int(index) != offset + 1:
                raise ValueError(f"non-sequential {axis} cell index in {path}")
            left[offset], right[offset] = float(lo), float(hi)
        if not np.allclose(right[:-1], left[1:], rtol=0.0, atol=1.0e-9):
            raise ValueError(f"non-contiguous {axis} edges in {path}")
        edges = np.concatenate((left[:1], right))
        axes.append((0.5 * (edges[:-1] + edges[1:]), edges))
    return Grid3D(axes[0][0], axes[1][0], axes[2][0], axes[0][1], axes[1][1], axes[2][1])


def mach_from_pressure_ratio(ratio: np.ndarray | float, gamma: float = GAMMA) -> np.ndarray:
    ratio = np.asarray(ratio, dtype=float)
    value = (ratio * (gamma + 1.0) + (gamma - 1.0)) / (2.0 * gamma)
    return np.where((ratio > 1.0) & (value >= 1.0), np.sqrt(value), np.nan)


def mach_from_density_ratio(ratio: np.ndarray | float, gamma: float = GAMMA) -> np.ndarray:
    ratio = np.asarray(ratio, dtype=float)
    denominator = (gamma + 1.0) - ratio * (gamma - 1.0)
    value = np.divide(2.0 * ratio, denominator, out=np.full_like(ratio, np.nan), where=denominator > 0.0)
    return np.where((ratio > 1.0) & (denominator > 0.0) & (value >= 1.0), np.sqrt(value), np.nan)


def rh_jump_ratios(mach: float, gamma: float = GAMMA) -> tuple[float, float, float]:
    if not math.isfinite(mach) or mach < 1.0:
        raise ValueError("shock Mach number must be finite and at least one")
    pressure = (2.0 * gamma * mach * mach - (gamma - 1.0)) / (gamma + 1.0)
    density = (gamma + 1.0) * mach * mach / ((gamma - 1.0) * mach * mach + 2.0)
    return pressure, density, pressure / density


def _interpolator(values: np.ndarray, grid: Grid3D) -> RegularGridInterpolator:
    return RegularGridInterpolator(
        (grid.z, grid.y, grid.x), values, method="linear", bounds_error=False, fill_value=np.nan,
    )


def _sample(interpolator: RegularGridInterpolator, points_xyz: np.ndarray) -> np.ndarray:
    return np.asarray(interpolator(points_xyz[:, (2, 1, 0)]), dtype=float)


def _dominant_normal_peak(
    compression: np.ndarray,
    indices: np.ndarray,
    normals_xyz: np.ndarray,
) -> np.ndarray:
    """Keep one side of a tied compression plateau along the local normal."""

    keep = np.zeros(indices.shape[0], dtype=bool)
    shape = np.asarray(compression.shape)
    for row, (index, normal) in enumerate(zip(indices, normals_xyz, strict=True)):
        xyz_axis = int(np.argmax(np.abs(normal)))
        zyx_axis = 2 - xyz_axis
        direction = 1 if normal[xyz_axis] >= 0.0 else -1
        upstream = index.copy()
        downstream = index.copy()
        upstream[zyx_axis] -= direction
        downstream[zyx_axis] += direction
        if (np.any(upstream < 0) or np.any(upstream >= shape)
                or np.any(downstream < 0) or np.any(downstream >= shape)):
            continue
        value = compression[tuple(index)]
        before = compression[tuple(upstream)]
        after = compression[tuple(downstream)]
        scale = max(abs(value), abs(before), abs(after), 1.0)
        tolerance = 64.0 * np.finfo(float).eps * scale
        keep[row] = value > before + tolerance and value >= after - tolerance
    return keep


def find_shock_candidates(
    fields: Mapping[str, np.ndarray],
    grid: Grid3D,
    *,
    mach_min: float = 1.1,
    mach_agreement_fraction: float = 0.2,
    core_slices: tuple[slice, slice, slice] | None = None,
) -> CandidateBatch:
    """Find accepted shock cells in one in-memory patch.

    ``core_slices`` restricts emitted cells while retaining the surrounding
    patch as a derivative/interpolation halo.  It is used by the tiled reader.
    """

    if mach_min < 1.0 or not 0.0 <= mach_agreement_fraction < 1.0:
        raise ValueError("invalid shock thresholds")
    missing = set(REQUIRED_FIELDS) - set(fields)
    if missing:
        raise ValueError(f"missing primitive fields: {sorted(missing)}")
    arrays = {name: np.asarray(fields[name], dtype=float) for name in REQUIRED_FIELDS}
    if any(value.shape != grid.shape for value in arrays.values()):
        raise ValueError("primitive fields and grid have different shapes")
    if any(not np.all(np.isfinite(value)) for value in arrays.values()):
        raise ValueError("primitive fields contain non-finite values")
    if np.any(arrays["rho"] <= 0.0) or np.any(arrays["prs"] <= 0.0):
        raise ValueError("density and pressure must be positive")

    pressure = arrays["prs"]
    dp_dz, dp_dy, dp_dx = np.gradient(pressure, grid.z, grid.y, grid.x, edge_order=2)
    dvx_dx = np.gradient(arrays["vx1"], grid.x, axis=2, edge_order=2)
    dvy_dy = np.gradient(arrays["vx2"], grid.y, axis=1, edge_order=2)
    dvz_dz = np.gradient(arrays["vx3"], grid.z, axis=0, edge_order=2)
    divergence = dvx_dx + dvy_dy + dvz_dz
    gradient_norm = np.sqrt(dp_dx * dp_dx + dp_dy * dp_dy + dp_dz * dp_dz)
    minimum_spacing = min(
        float(np.min(np.diff(grid.x))),
        float(np.min(np.diff(grid.y))),
        float(np.min(np.diff(grid.z))),
    )
    gradient_floor = (
        128.0 * np.finfo(float).eps
        * max(float(np.max(np.abs(pressure))), np.finfo(float).tiny)
        / minimum_spacing
    )
    candidate_mask = (divergence < 0.0) & (gradient_norm > gradient_floor)
    if core_slices is not None:
        if len(core_slices) != 3:
            raise ValueError("core_slices must be ordered (z, y, x)")
        core = np.zeros(grid.shape, dtype=bool)
        core[core_slices] = True
        candidate_mask &= core
    indices = np.argwhere(candidate_mask)
    if not indices.size:
        return CandidateBatch.empty()
    normals = np.column_stack((
        dp_dx[tuple(indices.T)], dp_dy[tuple(indices.T)], dp_dz[tuple(indices.T)],
    ))
    normals /= gradient_norm[tuple(indices.T)][:, None]
    compression = -divergence
    peak = _dominant_normal_peak(compression, indices, normals)
    indices, normals = indices[peak], normals[peak]
    if not indices.size:
        return CandidateBatch.empty()

    x_width, y_width, z_width = grid.widths
    local_widths = np.column_stack((
        x_width[indices[:, 2]], y_width[indices[:, 1]], z_width[indices[:, 0]],
    ))
    effective_width = 1.0 / np.sqrt(np.sum((normals / local_widths) ** 2, axis=1))
    coordinates = np.column_stack((
        grid.x[indices[:, 2]], grid.y[indices[:, 1]], grid.z[indices[:, 0]],
    ))
    displacement = 2.0 * effective_width[:, None] * normals
    minus, plus = coordinates - displacement, coordinates + displacement

    pressure_i = _interpolator(pressure, grid)
    rho_i = _interpolator(arrays["rho"], grid)
    pressure_minus, pressure_plus = _sample(pressure_i, minus), _sample(pressure_i, plus)
    rho_minus, rho_plus = _sample(rho_i, minus), _sample(rho_i, plus)
    plus_is_downstream = pressure_plus >= pressure_minus
    pressure_up = np.where(plus_is_downstream, pressure_minus, pressure_plus)
    pressure_down = np.where(plus_is_downstream, pressure_plus, pressure_minus)
    rho_up = np.where(plus_is_downstream, rho_minus, rho_plus)
    rho_down = np.where(plus_is_downstream, rho_plus, rho_minus)
    pressure_ratio = pressure_down / pressure_up
    density_ratio = rho_down / rho_up
    temperature_ratio = (pressure_down / rho_down) / (pressure_up / rho_up)
    mach_pressure = mach_from_pressure_ratio(pressure_ratio)
    mach_density = mach_from_density_ratio(density_ratio)
    roundoff = 64.0 * np.finfo(float).eps * np.maximum(mach_pressure, 1.0)
    accepted = (
        np.isfinite(mach_pressure)
        & np.isfinite(mach_density)
        & (mach_pressure + roundoff >= mach_min)
        & (temperature_ratio > 1.0)
        & (np.abs(mach_pressure - mach_density) <= mach_agreement_fraction * mach_pressure)
    )
    return CandidateBatch(
        indices[accepted], coordinates[accepted], normals[accepted],
        divergence[tuple(indices[accepted].T)], pressure_ratio[accepted], density_ratio[accepted],
        temperature_ratio[accepted], mach_pressure[accepted], mach_density[accepted],
    )


def _tile_ranges(size: int, tile: int) -> Iterator[tuple[int, int]]:
    if tile < 1:
        raise ValueError("tile extents must be positive")
    for start in range(0, size, tile):
        yield start, min(start + tile, size)


def iter_shock_candidates_tiled(
    fields: Mapping[str, object],
    grid: Grid3D,
    *,
    mach_min: float = 1.1,
    mach_agreement_fraction: float = 0.2,
    tile_shape_zyx: tuple[int, int, int] = (16, 128, 128),
    halo_cells: int = 4,
) -> Iterator[CandidateBatch]:
    """Yield accepted candidates while reading only one haloed tile at a time."""

    if halo_cells < 3:
        raise ValueError("at least three halo cells are required by the +/-2-cell stencil")
    if len(tile_shape_zyx) != 3:
        raise ValueError("tile_shape_zyx must contain three extents")
    missing = set(REQUIRED_FIELDS) - set(fields)
    if missing:
        raise ValueError(f"missing primitive fields: {sorted(missing)}")
    for name in REQUIRED_FIELDS:
        if tuple(getattr(fields[name], "shape", ())) != grid.shape:
            raise ValueError(f"{name} shape differs from grid")
    ranges = [_tile_ranges(size, tile) for size, tile in zip(grid.shape, tile_shape_zyx, strict=True)]
    z_ranges, y_ranges, x_ranges = (list(item) for item in ranges)
    for z0, z1 in z_ranges:
        for y0, y1 in y_ranges:
            for x0, x1 in x_ranges:
                starts = (max(0, z0 - halo_cells), max(0, y0 - halo_cells), max(0, x0 - halo_cells))
                stops = (
                    min(grid.shape[0], z1 + halo_cells),
                    min(grid.shape[1], y1 + halo_cells),
                    min(grid.shape[2], x1 + halo_cells),
                )
                outer = tuple(slice(start, stop) for start, stop in zip(starts, stops, strict=True))
                if any(stop - start < 7 for start, stop in zip(starts, stops, strict=True)):
                    continue
                patch = {name: np.asarray(fields[name][outer], dtype=float) for name in REQUIRED_FIELDS}
                patch_grid = grid.subgrid(*outer)
                core = (
                    slice(z0 - starts[0], z1 - starts[0]),
                    slice(y0 - starts[1], y1 - starts[1]),
                    slice(x0 - starts[2], x1 - starts[2]),
                )
                result = find_shock_candidates(
                    patch, patch_grid, mach_min=mach_min,
                    mach_agreement_fraction=mach_agreement_fraction, core_slices=core,
                )
                if len(result):
                    offsets = np.asarray(starts, dtype=np.int64)
                    yield replace(result, indices_zyx=result.indices_zyx + offsets)


def collect_shock_candidates_tiled(*args, **kwargs) -> CandidateBatch:
    """Convenience collector for small patches and tests."""

    return CandidateBatch.concatenate(list(iter_shock_candidates_tiled(*args, **kwargs)))
