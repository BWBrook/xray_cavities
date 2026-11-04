#!/usr/bin/env python3
"""Synthetic validation of the independent native-grid bow-shock finder."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from independent_bow_shock import (
    GAMMA,
    Grid3D,
    collect_shock_candidates_tiled,
    parse_pluto_grid,
    rh_jump_ratios,
)


ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_GRID = ROOT / "docs/science/assets/g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/remote_stage/completion_evidence/grid.out"
GROUP_ATMOSPHERE = ROOT / "env/extracted/environments/tabulated/tabulated_cosmo_002031.csv"
KPC_CM = 3.0856775814913673e21
MACH_THRESHOLDS = (1.05, 1.1, 1.2)


@dataclass(frozen=True)
class Atmosphere:
    radius_kpc: np.ndarray
    density: np.ndarray
    pressure: np.ndarray

    @classmethod
    def read(cls, path: Path) -> Atmosphere:
        values = np.loadtxt(path, dtype=float, ndmin=2)
        if values.shape[1] < 3 or np.any(values[:, 0] < 0.0):
            raise ValueError(f"invalid atmosphere table: {path}")
        radius = values[:, 0] / KPC_CM
        if np.any(np.diff(radius) <= 0.0) or np.any(values[:, 1:3] <= 0.0):
            raise ValueError(f"non-monotone or non-positive atmosphere table: {path}")
        return cls(radius, values[:, 1], values[:, 2])

    def at_radius(self, radius_kpc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        density = np.interp(radius_kpc, self.radius_kpc, self.density)
        pressure = np.interp(radius_kpc, self.radius_kpc, self.pressure)
        return density, pressure


def unit(vector: tuple[float, float, float] | np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=float)
    norm = float(np.linalg.norm(value))
    if value.shape != (3,) or norm == 0.0:
        raise ValueError("normal must be a non-zero three-vector")
    return value / norm


def local_patch(grid: Grid3D, centre_xyz: tuple[float, float, float], cells: int = 27) -> Grid3D:
    if cells < 15 or cells % 2 == 0:
        raise ValueError("patch size must be odd and at least 15")
    half = cells // 2
    slices = []
    for axis, target in zip((grid.z, grid.y, grid.x), centre_xyz[::-1], strict=True):
        index = int(np.argmin(np.abs(axis - target)))
        start = min(max(index - half, 0), axis.size - cells)
        slices.append(slice(start, start + cells))
    return grid.subgrid(*slices)


def _geometry(grid: Grid3D, normal_xyz: np.ndarray, plane_fraction: float) -> tuple[np.ndarray, np.ndarray, float]:
    centre = np.array((grid.x[grid.x.size // 2], grid.y[grid.y.size // 2], grid.z[grid.z.size // 2]))
    widths = np.array((
        np.diff(grid.x_edges)[grid.x.size // 2],
        np.diff(grid.y_edges)[grid.y.size // 2],
        np.diff(grid.z_edges)[grid.z.size // 2],
    ))
    effective_width = 1.0 / math.sqrt(float(np.sum((normal_xyz / widths) ** 2)))
    zz, yy, xx = np.meshgrid(grid.z, grid.y, grid.x, indexing="ij")
    signed = (
        (xx - centre[0]) * normal_xyz[0]
        + (yy - centre[1]) * normal_xyz[1]
        + (zz - centre[2]) * normal_xyz[2]
        - plane_fraction * effective_width
    )
    return centre, signed, effective_width


def _background_on_feature_plane(
    grid: Grid3D,
    atmosphere: Atmosphere,
    signed_distance: np.ndarray,
    normal_xyz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Retain tangential stratification while isolating the prescribed jump.

    An exact planar Riemann problem cannot simultaneously retain the smooth
    atmosphere's normal pressure gradient.  Each normal column therefore uses
    the tabulated state at its projection onto the feature plane.  This makes
    the imposed discontinuity exactly Rankine--Hugoniot while still sampling
    the real G-HI atmosphere across the tangential directions.
    """

    zz, yy, xx = np.meshgrid(grid.z, grid.y, grid.x, indexing="ij")
    projected_x = xx - signed_distance * normal_xyz[0]
    projected_y = yy - signed_distance * normal_xyz[1]
    projected_z = zz - signed_distance * normal_xyz[2]
    radius = np.sqrt(projected_x**2 + projected_y**2 + projected_z**2)
    return atmosphere.at_radius(radius)


def exact_shock(
    grid: Grid3D,
    atmosphere: Atmosphere,
    *,
    mach: float,
    normal_xyz: np.ndarray,
    plane_fraction: float = 0.23,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    normal_xyz = unit(normal_xyz)
    centre, signed, effective_width = _geometry(grid, normal_xyz, plane_fraction)
    density0, pressure0 = _background_on_feature_plane(grid, atmosphere, signed, normal_xyz)
    pressure_jump, density_jump, _ = rh_jump_ratios(mach)
    downstream = signed >= 0.0
    density = density0 * np.where(downstream, density_jump, 1.0)
    pressure = pressure0 * np.where(downstream, pressure_jump, 1.0)
    sound_speed = np.sqrt(GAMMA * pressure0 / density0)
    speed = np.where(downstream, mach * sound_speed / density_jump, mach * sound_speed)
    fields = {
        "rho": density,
        "prs": pressure,
        "vx1": speed * normal_xyz[0],
        "vx2": speed * normal_xyz[1],
        "vx3": speed * normal_xyz[2],
    }
    return fields, {
        "centre_xyz": centre,
        "normal_xyz": normal_xyz,
        "effective_width": effective_width,
        "plane_fraction": plane_fraction,
    }


def pressure_balanced_contact(
    grid: Grid3D,
    atmosphere: Atmosphere,
    *,
    contrast: float,
    normal_xyz: np.ndarray,
) -> dict[str, np.ndarray]:
    normal_xyz = unit(normal_xyz)
    _, signed, _ = _geometry(grid, normal_xyz, 0.17)
    density0, pressure0 = _background_on_feature_plane(grid, atmosphere, signed, normal_xyz)
    density = density0 * np.where(signed >= 0.0, contrast, 1.0)
    zeros = np.zeros(grid.shape, dtype=float)
    return {"rho": density, "prs": pressure0, "vx1": zeros, "vx2": zeros.copy(), "vx3": zeros.copy()}


def isentropic_sound_wave(
    grid: Grid3D,
    atmosphere: Atmosphere,
    *,
    normal_xyz: np.ndarray,
) -> dict[str, np.ndarray]:
    normal_xyz = unit(normal_xyz)
    _, signed, effective_width = _geometry(grid, normal_xyz, -0.11)
    density0, pressure0 = _background_on_feature_plane(grid, atmosphere, signed, normal_xyz)
    phase = np.clip(signed / (0.55 * effective_width), -1.0, 1.0)
    pressure_factor = 1.0 + 0.1 * phase
    density_factor = pressure_factor ** (1.0 / GAMMA)
    speed = -phase * np.sqrt(GAMMA * pressure0 / density0) * 0.1 / GAMMA
    return {
        "rho": density0 * density_factor,
        "prs": pressure0 * pressure_factor,
        "vx1": speed * normal_xyz[0],
        "vx2": speed * normal_xyz[1],
        "vx3": speed * normal_xyz[2],
    }


def rarefaction_fan(
    grid: Grid3D,
    atmosphere: Atmosphere,
    *,
    normal_xyz: np.ndarray,
) -> dict[str, np.ndarray]:
    normal_xyz = unit(normal_xyz)
    _, signed, effective_width = _geometry(grid, normal_xyz, 0.09)
    density0, pressure0 = _background_on_feature_plane(grid, atmosphere, signed, normal_xyz)
    phase = np.clip(signed / (3.0 * effective_width), -1.0, 1.0)
    pressure_factor = 1.0 - 0.2 * phase
    density_factor = pressure_factor ** (1.0 / GAMMA)
    speed = phase * np.sqrt(GAMMA * pressure0 / density0) * 0.2 / GAMMA
    return {
        "rho": density0 * density_factor,
        "prs": pressure0 * pressure_factor,
        "vx1": speed * normal_xyz[0],
        "vx2": speed * normal_xyz[1],
        "vx3": speed * normal_xyz[2],
    }


def evaluate_shock(
    fields: dict[str, np.ndarray],
    grid: Grid3D,
    truth: dict[str, Any],
    *,
    mach: float,
    mach_min: float,
) -> dict[str, Any]:
    candidates = collect_shock_candidates_tiled(
        fields, grid, mach_min=mach_min, tile_shape_zyx=(11, 13, 12), halo_cells=4,
    )
    expected_detection = mach + 1.0e-12 >= mach_min
    row: dict[str, Any] = {
        "kind": "exact_shock",
        "mach_true": mach,
        "mach_min": mach_min,
        "expected_detection": expected_detection,
        "candidate_count": len(candidates),
        "detected": bool(len(candidates)),
    }
    if not len(candidates):
        row.update({"position_error_cells_p95": None, "mach_pressure_median": None,
                    "mach_density_median": None, "normal_abs_dot_median": None,
                    "positive_gate_pass": not expected_detection})
        return row
    normal = truth["normal_xyz"]
    plane_offset = truth["plane_fraction"] * truth["effective_width"]
    signed = np.sum((candidates.coordinates_xyz - truth["centre_xyz"]) * normal[None, :], axis=1) - plane_offset
    position_error = np.abs(signed) / truth["effective_width"]
    mach_pressure = float(np.median(candidates.mach_pressure))
    mach_density = float(np.median(candidates.mach_density))
    position_ok = float(np.percentile(position_error, 95.0)) <= 2.0
    recovery_ok = (
        abs(mach_pressure / mach - 1.0) <= 0.1
        and abs(mach_density / mach - 1.0) <= 0.1
    )
    row.update({
        "position_error_cells_p95": float(np.percentile(position_error, 95.0)),
        "mach_pressure_median": mach_pressure,
        "mach_density_median": mach_density,
        "normal_abs_dot_median": float(np.median(np.abs(np.sum(candidates.normals_xyz * normal[None, :], axis=1)))),
        "positive_gate_pass": expected_detection and position_ok and recovery_ok,
    })
    return row


def evaluate_negative(kind: str, fields: dict[str, np.ndarray], grid: Grid3D, mach_min: float, **metadata: Any) -> dict[str, Any]:
    candidates = collect_shock_candidates_tiled(
        fields, grid, mach_min=mach_min, tile_shape_zyx=(11, 13, 12), halo_cells=4,
    )
    result = {
        "kind": kind,
        "mach_min": mach_min,
        "candidate_count": len(candidates),
        "negative_gate_pass": len(candidates) == 0,
    }
    if len(candidates):
        result.update({
            "mach_pressure_min": float(np.min(candidates.mach_pressure)),
            "mach_pressure_median": float(np.median(candidates.mach_pressure)),
            "mach_pressure_max": float(np.max(candidates.mach_pressure)),
            "mach_density_median": float(np.median(candidates.mach_density)),
        })
    result.update(metadata)
    return result


def run_validation(*, compact: bool = False) -> dict[str, Any]:
    production = parse_pluto_grid(PRODUCTION_GRID)
    atmosphere = Atmosphere.read(GROUP_ATMOSPHERE)
    placements = {
        "central_uniform": (0.0, 0.0, 0.0),
        "outer_stretched": (45.0, -25.0, 70.0),
    }
    orientations = {
        "axis": unit((1.0, 0.0, 0.0)),
        "diagonal": unit((1.0, 1.0, 0.0)),
        "oblique": unit((1.0, 2.0, 3.0)),
    }
    if compact:
        placements = {"central_uniform": placements["central_uniform"]}
        orientations = {"oblique": orientations["oblique"]}
    shock_rows = []
    negative_rows = []
    for placement_name, centre in placements.items():
        grid = local_patch(production, centre)
        for orientation_name, normal in orientations.items():
            for mach in (1.1, 1.5, 3.0):
                fields, truth = exact_shock(grid, atmosphere, mach=mach, normal_xyz=normal)
                for mach_min in MACH_THRESHOLDS:
                    row = evaluate_shock(fields, grid, truth, mach=mach, mach_min=mach_min)
                    row.update({"placement": placement_name, "orientation": orientation_name})
                    shock_rows.append(row)
            for contrast in (10.0, 100.0):
                fields = pressure_balanced_contact(grid, atmosphere, contrast=contrast, normal_xyz=normal)
                for mach_min in MACH_THRESHOLDS:
                    negative_rows.append(evaluate_negative(
                        "pressure_balanced_contact", fields, grid, mach_min,
                        placement=placement_name, orientation=orientation_name, density_contrast=contrast,
                    ))
            fields = isentropic_sound_wave(grid, atmosphere, normal_xyz=normal)
            for mach_min in MACH_THRESHOLDS:
                negative_rows.append(evaluate_negative(
                    "isentropic_sound_wave_delta_p_over_p_0.1", fields, grid, mach_min,
                    placement=placement_name, orientation=orientation_name,
                ))
            fields = rarefaction_fan(grid, atmosphere, normal_xyz=normal)
            for mach_min in MACH_THRESHOLDS:
                negative_rows.append(evaluate_negative(
                    "rarefaction_fan", fields, grid, mach_min,
                    placement=placement_name, orientation=orientation_name,
                ))

    positive_failures = [row for row in shock_rows if not row["positive_gate_pass"]]
    negative_failures = [row for row in negative_rows if not row["negative_gate_pass"]]
    baseline_negative_failures = [row for row in negative_failures if row["mach_min"] == 1.1]
    sound_105 = [
        row for row in negative_rows
        if row["kind"].startswith("isentropic_sound_wave") and row["mach_min"] == 1.05
    ]
    summary = {
        "production_grid_shape_zyx": production.shape,
        "grid_source": str(PRODUCTION_GRID.relative_to(ROOT)),
        "atmosphere_source": str(GROUP_ATMOSPHERE.relative_to(ROOT)),
        "shock_scenarios": len(shock_rows),
        "negative_scenarios": len(negative_rows),
        "positive_failure_count": len(positive_failures),
        "negative_failure_count_all_thresholds": len(negative_failures),
        "negative_failure_count_at_baseline_1.1": len(baseline_negative_failures),
        "sound_wave_1.05_flagged_scenarios": sum(row["candidate_count"] > 0 for row in sound_105),
        "sound_wave_1.05_scenarios": len(sound_105),
        "baseline_1.1_gate_pass": not positive_failures and not baseline_negative_failures,
        "all_threshold_validation_pass": not positive_failures and not negative_failures,
        "promotion_status": "PASS" if not positive_failures and not negative_failures else "FAIL_NO_PROMOTION",
    }
    return {
        "summary": summary,
        "positive_failures": positive_failures,
        "negative_failures": negative_failures,
        "shock_rows": shock_rows,
        "negative_rows": negative_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true", help="Run one placement/orientation for a fast diagnostic.")
    parser.add_argument("--full-record", action="store_true", help="Print all validation rows, not only failures.")
    parser.add_argument("--allow-science-fail", action="store_true", help="Return zero even when the promotion gate fails.")
    args = parser.parse_args()
    result = run_validation(compact=args.compact)
    payload = result if args.full_record else {
        "summary": result["summary"],
        "positive_failures": result["positive_failures"],
        "negative_failures": result["negative_failures"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if result["summary"]["promotion_status"] != "PASS" and not args.allow_science_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
