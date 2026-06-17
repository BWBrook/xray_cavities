#!/usr/bin/env python3
"""Extract Level 3 ambient thermal/kinetic energy from two PLUTO HDF5 outputs."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np


GAMMA_GAS = 5.0 / 3.0
UNIT_DENSITY_CGS = 1.0023678e-24
UNIT_LENGTH_CM = 3.0856775814913673e21
UNIT_VELOCITY_CMS = 2.99792458e10
UNIT_ENERGY_ERG = UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS * UNIT_VELOCITY_CMS * UNIT_LENGTH_CM**3
REQUIRED_DATASETS = ("rho", "prs", "tr1", "vx1", "vx2", "vx3")
SIDES = ("negative_z", "positive_z", "bipolar_total")
COORDINATE_ATOL_KPC = 1.0e-10


@dataclass
class Accumulator:
    ambient_cell_count: int = 0
    ambient_volume_kpc3: float = 0.0
    thermal_delta_code: float = 0.0
    kinetic_delta_code: float = 0.0

    def add(self, *, count: int, volume: float, thermal: float, kinetic: float) -> None:
        self.ambient_cell_count += int(count)
        self.ambient_volume_kpc3 += float(volume)
        self.thermal_delta_code += float(thermal)
        self.kinetic_delta_code += float(kinetic)


def dataset_path(timestep: str, name: str) -> str:
    return f"/{timestep}/vars/{name}"


def require_datasets(h5: h5py.File, timestep: str) -> tuple[int, int, int]:
    shape = None
    missing = []
    for name in REQUIRED_DATASETS:
        path = dataset_path(timestep, name)
        if path not in h5:
            missing.append(path)
            continue
        current_shape = tuple(h5[path].shape)
        if shape is None:
            shape = current_shape
        elif current_shape != shape:
            raise ValueError(f"dataset shape mismatch in {timestep}: {path} {current_shape} vs {shape}")
    if missing:
        raise ValueError(f"missing datasets: {', '.join(missing)}")
    assert shape is not None
    if len(shape) != 3:
        raise ValueError(f"expected 3D vars for {timestep}, got shape {shape}")
    return int(shape[0]), int(shape[1]), int(shape[2])


def read_axis(h5: h5py.File, axis: str, *, nz: int, ny: int, nx: int) -> np.ndarray:
    data = h5[f"/cell_coords/{axis}"]
    if data.ndim == 1:
        return np.asarray(data[:], dtype=float)
    if axis == "X":
        return np.asarray(data[0, ny // 2, :], dtype=float)
    if axis == "Y":
        return np.asarray(data[0, :, nx // 2], dtype=float)
    if axis == "Z":
        return np.asarray(data[:, ny // 2, nx // 2], dtype=float)
    raise ValueError(f"unknown axis {axis}")


def derive_widths(centres: np.ndarray) -> np.ndarray:
    centres = np.asarray(centres, dtype=float)
    if centres.size == 0:
        raise ValueError("axis has no coordinates")
    if centres.size == 1:
        return np.ones(1, dtype=float)
    widths = np.empty_like(centres)
    widths[0] = abs(centres[1] - centres[0])
    widths[-1] = abs(centres[-1] - centres[-2])
    if centres.size > 2:
        widths[1:-1] = abs(0.5 * (centres[2:] - centres[:-2]))
    return widths


def validate_coordinate_axis(
    *,
    axis: str,
    baseline_values: np.ndarray,
    final_values: np.ndarray,
    atol: float = COORDINATE_ATOL_KPC,
) -> None:
    if baseline_values.shape != final_values.shape:
        raise ValueError(
            f"coordinate shape mismatch for {axis}: "
            f"baseline={baseline_values.shape} final={final_values.shape}"
        )
    if not np.allclose(baseline_values, final_values, rtol=0.0, atol=atol, equal_nan=False):
        max_abs = float(np.max(np.abs(baseline_values - final_values)))
        raise ValueError(f"coordinate mismatch for {axis}: max_abs_delta={max_abs:.17g} kpc")


def read_and_validate_axes(
    *,
    base: h5py.File,
    final: h5py.File,
    nz: int,
    ny: int,
    nx: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axes: dict[str, np.ndarray] = {}
    for axis in ("X", "Y", "Z"):
        baseline_axis = read_axis(base, axis, nz=nz, ny=ny, nx=nx)
        final_axis = read_axis(final, axis, nz=nz, ny=ny, nx=nx)
        expected_len = {"X": nx, "Y": ny, "Z": nz}[axis]
        if len(final_axis) != expected_len or len(baseline_axis) != expected_len:
            raise ValueError(f"coordinate axis {axis} length does not match grid shape")
        validate_coordinate_axis(axis=axis, baseline_values=baseline_axis, final_values=final_axis)
        axes[axis] = final_axis
    return axes["X"], axes["Y"], axes["Z"]


def read_slab(h5: h5py.File, timestep: str, name: str, iz: int) -> np.ndarray:
    return np.asarray(h5[dataset_path(timestep, name)][iz, :, :], dtype=float)


def accumulate_slice(
    acc: dict[str, Accumulator],
    *,
    z_value: float,
    volume_2d: np.ndarray,
    ambient_mask: np.ndarray,
    thermal_code: np.ndarray,
    kinetic_code: np.ndarray,
) -> None:
    side = "negative_z" if z_value < 0.0 else "positive_z"
    for key in (side, "bipolar_total"):
        mask = ambient_mask
        acc[key].add(
            count=int(np.count_nonzero(mask)),
            volume=float(np.sum(volume_2d[mask])),
            thermal=float(np.sum(thermal_code[mask])),
            kinetic=float(np.sum(kinetic_code[mask])),
        )


def output_rows(acc: dict[str, Accumulator], tracer_threshold: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for side in SIDES:
        item = acc[side]
        thermal_erg = item.thermal_delta_code * UNIT_ENERGY_ERG
        kinetic_erg = item.kinetic_delta_code * UNIT_ENERGY_ERG
        rows.append(
            {
                "side": side,
                "tracer_threshold": f"{tracer_threshold:.0e}",
                "ambient_cell_count": item.ambient_cell_count,
                "ambient_volume_kpc3": item.ambient_volume_kpc3,
                "thermal_delta_code": item.thermal_delta_code,
                "kinetic_delta_code": item.kinetic_delta_code,
                "thermal_delta_erg": thermal_erg,
                "kinetic_delta_erg": kinetic_erg,
                "thermal_plus_kinetic_delta_erg": thermal_erg + kinetic_erg,
            }
        )
    return rows


def write_rows(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def extract_level3(
    *,
    baseline_h5: Path,
    baseline_timestep: str,
    final_h5: Path,
    final_timestep: str,
    output_csv: Path,
    tracer_threshold: float = 5.0e-3,
) -> list[dict[str, object]]:
    with h5py.File(baseline_h5, "r") as base, h5py.File(final_h5, "r") as final:
        base_shape = require_datasets(base, baseline_timestep)
        final_shape = require_datasets(final, final_timestep)
        if base_shape != final_shape:
            raise ValueError(f"shape mismatch: baseline={base_shape} final={final_shape}")

        nz, ny, nx = final_shape
        x, y, z = read_and_validate_axes(base=base, final=final, nz=nz, ny=ny, nx=nx)
        dx = derive_widths(x)
        dy = derive_widths(y)
        dz = derive_widths(z)
        volume_xy = dy[:, None] * dx[None, :]

        acc = {side: Accumulator() for side in SIDES}
        for iz in range(nz):
            volume_2d = volume_xy * dz[iz]
            tr1_final = read_slab(final, final_timestep, "tr1", iz)
            ambient_mask = tr1_final <= tracer_threshold
            prs_delta = read_slab(final, final_timestep, "prs", iz) - read_slab(
                base,
                baseline_timestep,
                "prs",
                iz,
            )
            thermal_code = prs_delta * volume_2d / (GAMMA_GAS - 1.0)

            rho_final = read_slab(final, final_timestep, "rho", iz)
            rho_base = read_slab(base, baseline_timestep, "rho", iz)
            v2_final = (
                read_slab(final, final_timestep, "vx1", iz) ** 2
                + read_slab(final, final_timestep, "vx2", iz) ** 2
                + read_slab(final, final_timestep, "vx3", iz) ** 2
            )
            v2_base = (
                read_slab(base, baseline_timestep, "vx1", iz) ** 2
                + read_slab(base, baseline_timestep, "vx2", iz) ** 2
                + read_slab(base, baseline_timestep, "vx3", iz) ** 2
            )
            kinetic_code = 0.5 * (rho_final * v2_final - rho_base * v2_base) * volume_2d
            accumulate_slice(
                acc,
                z_value=float(z[iz]),
                volume_2d=volume_2d,
                ambient_mask=ambient_mask,
                thermal_code=thermal_code,
                kinetic_code=kinetic_code,
            )

    rows = output_rows(acc, tracer_threshold)
    write_rows(output_csv, rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-h5", type=Path, required=True)
    parser.add_argument("--baseline-timestep", default="Timestep_0")
    parser.add_argument("--final-h5", type=Path, required=True)
    parser.add_argument("--final-timestep", default="Timestep_51")
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--tracer-threshold", type=float, default=5.0e-3)
    args = parser.parse_args()
    extract_level3(
        baseline_h5=args.baseline_h5,
        baseline_timestep=args.baseline_timestep,
        final_h5=args.final_h5,
        final_timestep=args.final_timestep,
        output_csv=args.output_csv,
        tracer_threshold=args.tracer_threshold,
    )


if __name__ == "__main__":
    main()
