#!/usr/bin/env python3
"""Cell-wise energy and initial-potential methods for PLUTO snapshot science."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import numpy as np

from pluto_h5_level3_ambient_extract import (
    COORDINATE_ATOL_KPC,
    GAMMA_GAS,
    REQUIRED_DATASETS,
    UNIT_DENSITY_CGS,
    UNIT_ENERGY_ERG,
    UNIT_LENGTH_CM,
    UNIT_VELOCITY_CMS,
    derive_widths,
    read_and_validate_axes,
    read_axis,
    require_datasets,
)
from select_common_age_hdf5 import CODE_TIME_PER_MYR, Snapshot, inspect_outputs


METHOD_VERSION = 1
SECONDS_PER_MYR = 3.15576e13
SIDES = ("negative_z", "positive_z", "bipolar_total")
TRACER_THRESHOLDS = (1.0e-3, 5.0e-3, 1.0e-2)
ENERGY_FIELDS = (
    "thermal_erg",
    "kinetic_erg",
    "gravitational_erg",
    "volume_kpc3",
    "mass_g",
    "cell_equivalent",
)

@dataclass(frozen=True)
class EnvironmentProfile:
    radius_cm: np.ndarray
    density_g_cm3: np.ndarray
    pressure_dyn_cm2: np.ndarray
    gravity_cm_s2: np.ndarray
    potential_cm2_s2: np.ndarray
    gravity_max_abs_delta_cm_s2: float
    gravity_max_relative_delta: float
    source_sha256: str

    def potential_at_radius(self, radius_cm: np.ndarray) -> np.ndarray:
        values = np.asarray(radius_cm, dtype=float)
        if np.any(values < 0.0) or float(np.max(values, initial=0.0)) > self.radius_cm[-1] * (1.0 + 1.0e-10):
            raise ValueError("grid radius falls outside the tabulated environment")
        return np.interp(values, self.radius_cm, self.potential_cm2_s2)

    def sound_speed_at_radius(self, radius_cm: float) -> float:
        if radius_cm < 0.0 or radius_cm > self.radius_cm[-1] * (1.0 + 1.0e-10):
            raise ValueError("shock radius falls outside the tabulated environment")
        pressure = float(np.interp(radius_cm, self.radius_cm, self.pressure_dyn_cm2))
        density = float(np.interp(radius_cm, self.radius_cm, self.density_g_cm3))
        return math.sqrt(GAMMA_GAS * pressure / density)


@dataclass(frozen=True)
class Geometry:
    x_kpc: np.ndarray
    y_kpc: np.ndarray
    z_kpc: np.ndarray
    dx_kpc: np.ndarray
    dy_kpc: np.ndarray
    dz_kpc: np.ndarray
    volume_xy_kpc2: np.ndarray
    potential_path: Path


@dataclass(frozen=True)
class BaselineState:
    totals: dict[str, dict[str, float]]
    axial_profile: list[dict[str, float]]
    velocity_cut_code: float
    baseline_noise_code: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError(f"no rows to write: {path}")
    fields = list(materialized[0])
    if len(fields) != len(set(fields)) or any(list(row) != fields for row in materialized):
        raise ValueError(f"inconsistent output schema: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(materialized)
    temporary.replace(path)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"invalid CSV schema: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def load_environment(path: Path, *, gravity_rtol: float = 1.0e-8) -> EnvironmentProfile:
    values = np.loadtxt(path, dtype=float, ndmin=2)
    if values.ndim != 2 or values.shape[1] != 6 or values.shape[0] < 2:
        raise ValueError("environment table must have at least two rows and six columns")
    if not np.all(np.isfinite(values)):
        raise ValueError("environment table contains non-finite values")
    radius, density, pressure = values[:, 0], values[:, 1], values[:, 2]
    gravity_a, gravity_b = values[:, 4], values[:, 5]
    if radius[0] != 0.0 or not np.all(np.diff(radius) > 0.0):
        raise ValueError("environment radius must start at zero and increase strictly")
    if np.any(density <= 0.0) or np.any(pressure <= 0.0):
        raise ValueError("environment density and pressure must be positive")
    abs_delta = np.abs(gravity_a - gravity_b)
    scale = np.maximum(np.maximum(np.abs(gravity_a), np.abs(gravity_b)), np.finfo(float).tiny)
    relative_delta = abs_delta / scale
    if not np.allclose(gravity_a, gravity_b, rtol=gravity_rtol, atol=1.0e-20):
        raise ValueError(
            "environment gravity columns disagree: "
            f"max_relative_delta={float(np.max(relative_delta)):.8g}"
        )
    gravity = 0.5 * (np.abs(gravity_a) + np.abs(gravity_b))
    increments = 0.5 * (gravity[:-1] + gravity[1:]) * np.diff(radius)
    potential = np.concatenate(([0.0], np.cumsum(increments, dtype=np.float64)))
    return EnvironmentProfile(
        radius_cm=radius,
        density_g_cm3=density,
        pressure_dyn_cm2=pressure,
        gravity_cm_s2=gravity,
        potential_cm2_s2=potential,
        gravity_max_abs_delta_cm_s2=float(np.max(abs_delta)),
        gravity_max_relative_delta=float(np.max(relative_delta)),
        source_sha256=sha256_file(path),
    )


def canonical_snapshot_chain(outputs_dirs: Sequence[Path]) -> list[Snapshot]:
    """Return one canonical snapshot per output index, preferring later segments."""

    if not outputs_dirs:
        raise ValueError("at least one output directory is required")
    by_index: dict[int, Snapshot] = {}
    for outputs_dir in outputs_dirs:
        for snapshot in inspect_outputs(outputs_dir):
            previous = by_index.get(snapshot.output_index)
            if previous is not None:
                if previous.shape != snapshot.shape or not math.isclose(
                    previous.time_code, snapshot.time_code, rel_tol=0.0, abs_tol=1.0e-6
                ):
                    raise ValueError(
                        "overlapping run segments disagree for output "
                        f"{snapshot.output_index}: {previous.input_h5} vs {snapshot.input_h5}"
                    )
            by_index[snapshot.output_index] = snapshot
    snapshots = [by_index[index] for index in sorted(by_index)]
    if not snapshots or snapshots[0].output_index != 0:
        raise ValueError("canonical snapshot chain has no output-zero baseline")
    if not all(b.time_code > a.time_code for a, b in zip(snapshots, snapshots[1:])):
        raise ValueError("canonical snapshot times are not strictly increasing")
    shapes = {snapshot.shape for snapshot in snapshots}
    if len(shapes) != 1:
        raise ValueError(f"canonical snapshot chain contains multiple grid shapes: {shapes}")
    return snapshots


def injected_energy(
    time_myr: float,
    *,
    one_sided_power_erg_s: float,
    jet_start_myr: float,
    jet_active_myr: float,
) -> tuple[float, float]:
    if one_sided_power_erg_s <= 0.0 or jet_active_myr < 0.0:
        raise ValueError("jet power must be positive and active time non-negative")
    elapsed = min(max(time_myr - jet_start_myr, 0.0), jet_active_myr)
    one_sided = one_sided_power_erg_s * elapsed * SECONDS_PER_MYR
    return one_sided, 2.0 * one_sided


def tracer_partitions(tracer: np.ndarray) -> list[tuple[str, str, np.ndarray]]:
    clipped = np.clip(np.asarray(tracer, dtype=float), 0.0, 1.0)
    partitions = [("fractional", "", clipped)]
    for threshold in TRACER_THRESHOLDS:
        label = f"{threshold:.0e}".replace("e-0", "e-")
        partitions.append((f"binary_threshold_{label}", label, (clipped >= threshold).astype(float)))
    return partitions


def empty_energy_totals() -> dict[str, float]:
    return {field: 0.0 for field in ENERGY_FIELDS}


def add_energy(target: dict[str, float], source: Mapping[str, float]) -> None:
    for field in ENERGY_FIELDS:
        target[field] += float(source[field])


def slice_energy(
    *,
    rho: np.ndarray,
    pressure: np.ndarray,
    velocity_squared: np.ndarray,
    weight: np.ndarray,
    volume_kpc3: np.ndarray,
    potential_cm2_s2: np.ndarray,
) -> dict[str, float]:
    weighted_volume = weight * volume_kpc3
    mass_g = rho * weighted_volume * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
    return {
        "thermal_erg": float(np.sum(weight * pressure * volume_kpc3) / (GAMMA_GAS - 1.0) * UNIT_ENERGY_ERG),
        "kinetic_erg": float(np.sum(0.5 * weight * rho * velocity_squared * volume_kpc3) * UNIT_ENERGY_ERG),
        "gravitational_erg": float(np.sum(mass_g * potential_cm2_s2)),
        "volume_kpc3": float(np.sum(weighted_volume)),
        "mass_g": float(np.sum(mass_g)),
        "cell_equivalent": float(np.sum(weight)),
    }


def build_geometry(
    *,
    baseline_h5: Path,
    baseline_timestep: str,
    shape: tuple[int, int, int],
    environment: EnvironmentProfile,
    cache_path: Path,
) -> Geometry:
    nz, ny, nx = shape
    with h5py.File(baseline_h5, "r") as h5:
        x = read_axis(h5, "X", nz=nz, ny=ny, nx=nx)
        y = read_axis(h5, "Y", nz=nz, ny=ny, nx=nx)
        z = read_axis(h5, "Z", nz=nz, ny=ny, nx=nx)
    dx, dy, dz = derive_widths(x), derive_widths(y), derive_widths(z)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    potential = np.lib.format.open_memmap(cache_path, mode="w+", dtype=np.float64, shape=shape)
    xy_radius_squared = x[None, :] ** 2 + y[:, None] ** 2
    for iz, z_value in enumerate(z):
        radius_cm = np.sqrt(xy_radius_squared + z_value**2) * UNIT_LENGTH_CM
        potential[iz] = environment.potential_at_radius(radius_cm)
    potential.flush()
    del potential
    return Geometry(
        x_kpc=x,
        y_kpc=y,
        z_kpc=z,
        dx_kpc=dx,
        dy_kpc=dy,
        dz_kpc=dz,
        volume_xy_kpc2=dy[:, None] * dx[None, :],
        potential_path=cache_path,
    )


def axial_tube_mask(geometry: Geometry, tube_radius_kpc: float) -> np.ndarray:
    if tube_radius_kpc <= 0.0:
        raise ValueError("axial tube radius must be positive")
    radius = np.sqrt(geometry.x_kpc[None, :] ** 2 + geometry.y_kpc[:, None] ** 2)
    mask = radius <= tube_radius_kpc
    if not np.any(mask):
        raise ValueError("axial tube contains no cells")
    return mask


def prepare_baseline(
    *,
    baseline: Snapshot,
    geometry: Geometry,
    tube_radius_kpc: float,
    velocity_floor_code: float,
    velocity_noise_multiplier: float,
) -> BaselineState:
    totals = {side: empty_energy_totals() for side in SIDES}
    tube = axial_tube_mask(geometry, tube_radius_kpc)
    profile: list[dict[str, float]] = []
    potential = np.load(geometry.potential_path, mmap_mode="r")
    with h5py.File(baseline.input_h5, "r") as h5:
        require_datasets(h5, baseline.timestep)
        for iz, z_value in enumerate(geometry.z_kpc):
            variables = h5[f"/{baseline.timestep}/vars"]
            rho = np.asarray(variables["rho"][iz], dtype=float)
            pressure = np.asarray(variables["prs"][iz], dtype=float)
            vx1 = np.asarray(variables["vx1"][iz], dtype=float)
            vx2 = np.asarray(variables["vx2"][iz], dtype=float)
            vx3 = np.asarray(variables["vx3"][iz], dtype=float)
            volume = geometry.volume_xy_kpc2 * geometry.dz_kpc[iz]
            values = slice_energy(
                rho=rho,
                pressure=pressure,
                velocity_squared=vx1**2 + vx2**2 + vx3**2,
                weight=np.ones_like(rho),
                volume_kpc3=volume,
                potential_cm2_s2=potential[iz],
            )
            side = "negative_z" if z_value < 0.0 else "positive_z"
            add_energy(totals[side], values)
            add_energy(totals["bipolar_total"], values)
            profile.append(
                {
                    "z_kpc": float(z_value),
                    "dz_kpc": float(geometry.dz_kpc[iz]),
                    "rho_code": float(np.mean(rho[tube])),
                    "pressure_code": float(np.mean(pressure[tube])),
                    "vz_code": float(np.mean(vx3[tube])),
                }
            )
    baseline_noise = float(np.quantile(np.abs([row["vz_code"] for row in profile]), 0.999))
    velocity_cut = max(float(velocity_floor_code), float(velocity_noise_multiplier) * baseline_noise)
    return BaselineState(totals, profile, velocity_cut, baseline_noise)


def _validate_snapshot_coordinates(
    baseline_h5: h5py.File,
    target_h5: h5py.File,
    shape: tuple[int, int, int],
) -> None:
    nz, ny, nx = shape
    read_and_validate_axes(base=baseline_h5, final=target_h5, nz=nz, ny=ny, nx=nx)


def analyze_snapshot(
    *,
    case: str,
    snapshot: Snapshot,
    baseline: Snapshot,
    baseline_state: BaselineState,
    geometry: Geometry,
    one_sided_power_erg_s: float,
    jet_start_myr: float,
    jet_active_myr: float,
    tube_radius_kpc: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current: dict[str, dict[str, dict[str, float]]] = {}
    threshold_labels: dict[str, str] = {}
    for mode, threshold, _ in tracer_partitions(np.zeros((1, 1))):
        current[mode] = {
            side: {f"gas_{field}": 0.0 for field in ENERGY_FIELDS}
            | {f"lobe_{field}": 0.0 for field in ENERGY_FIELDS}
            for side in SIDES
        }
        threshold_labels[mode] = threshold
    tube = axial_tube_mask(geometry, tube_radius_kpc)
    profile: list[dict[str, Any]] = []
    potential = np.load(geometry.potential_path, mmap_mode="r")
    with h5py.File(baseline.input_h5, "r") as base_h5, h5py.File(snapshot.input_h5, "r") as target_h5:
        if require_datasets(target_h5, snapshot.timestep) != snapshot.shape:
            raise ValueError(f"snapshot shape drift: {snapshot.input_h5}:{snapshot.timestep}")
        _validate_snapshot_coordinates(base_h5, target_h5, snapshot.shape)
        variables = target_h5[f"/{snapshot.timestep}/vars"]
        for iz, z_value in enumerate(geometry.z_kpc):
            rho = np.asarray(variables["rho"][iz], dtype=float)
            pressure = np.asarray(variables["prs"][iz], dtype=float)
            tracer = np.asarray(variables["tr1"][iz], dtype=float)
            vx1 = np.asarray(variables["vx1"][iz], dtype=float)
            vx2 = np.asarray(variables["vx2"][iz], dtype=float)
            vx3 = np.asarray(variables["vx3"][iz], dtype=float)
            v2 = vx1**2 + vx2**2 + vx3**2
            volume = geometry.volume_xy_kpc2 * geometry.dz_kpc[iz]
            side = "negative_z" if z_value < 0.0 else "positive_z"
            for mode, _, lobe_weight in tracer_partitions(tracer):
                for component, weight in (("gas", 1.0 - lobe_weight), ("lobe", lobe_weight)):
                    values = slice_energy(
                        rho=rho,
                        pressure=pressure,
                        velocity_squared=v2,
                        weight=weight,
                        volume_kpc3=volume,
                        potential_cm2_s2=potential[iz],
                    )
                    prefixed = {f"{component}_{key}": value for key, value in values.items()}
                    for target_side in (side, "bipolar_total"):
                        for key, value in prefixed.items():
                            current[mode][target_side][key] += value
            base_row = baseline_state.axial_profile[iz]
            profile.append(
                {
                    "snapshot_index": snapshot.output_index,
                    "actual_time_myr": snapshot.actual_time_myr,
                    "z_kpc": float(z_value),
                    "dz_kpc": float(geometry.dz_kpc[iz]),
                    "rho_code": float(np.mean(rho[tube])),
                    "pressure_code": float(np.mean(pressure[tube])),
                    "vz_code": float(np.mean(vx3[tube])),
                    "baseline_rho_code": base_row["rho_code"],
                    "baseline_pressure_code": base_row["pressure_code"],
                    "baseline_vz_code": base_row["vz_code"],
                }
            )

    one_sided_injected, bipolar_injected = injected_energy(
        snapshot.actual_time_myr,
        one_sided_power_erg_s=one_sided_power_erg_s,
        jet_start_myr=jet_start_myr,
        jet_active_myr=jet_active_myr,
    )
    rows: list[dict[str, Any]] = []
    for mode in current:
        for side in SIDES:
            values = current[mode][side]
            initial = baseline_state.totals[side]
            gas_thermal = values["gas_thermal_erg"] - initial["thermal_erg"]
            gas_kinetic = values["gas_kinetic_erg"] - initial["kinetic_erg"]
            gas_gravity = values["gas_gravitational_erg"] - initial["gravitational_erg"]
            gas_total = gas_thermal + gas_kinetic + gas_gravity
            lobe_total = (
                values["lobe_thermal_erg"]
                + values["lobe_kinetic_erg"]
                + values["lobe_gravitational_erg"]
            )
            injected = bipolar_injected if side == "bipolar_total" else one_sided_injected
            unattributed = injected - gas_total - lobe_total
            rows.append(
                {
                    "case": case,
                    "snapshot_index": snapshot.output_index,
                    "actual_time_code": snapshot.time_code,
                    "actual_time_myr": snapshot.actual_time_myr,
                    "side": side,
                    "partition_method": mode,
                    "tracer_threshold": threshold_labels[mode],
                    "gas_thermal_delta_erg": gas_thermal,
                    "gas_kinetic_delta_erg": gas_kinetic,
                    "gas_gravitational_delta_erg": gas_gravity,
                    "gas_total_delta_erg": gas_total,
                    "lobe_thermal_erg": values["lobe_thermal_erg"],
                    "lobe_kinetic_erg": values["lobe_kinetic_erg"],
                    "lobe_gravitational_erg": values["lobe_gravitational_erg"],
                    "lobe_total_erg": lobe_total,
                    "lobe_volume_kpc3": values["lobe_volume_kpc3"],
                    "lobe_mass_g": values["lobe_mass_g"],
                    "lobe_cell_equivalent": values["lobe_cell_equivalent"],
                    "gas_volume_kpc3": values["gas_volume_kpc3"],
                    "gas_mass_g": values["gas_mass_g"],
                    "injected_energy_erg": injected,
                    "boundary_energy_erg": "",
                    "boundary_status": "unmeasured_from_retained_snapshots",
                    "unattributed_residual_erg": unattributed,
                    "closure_fraction_of_injected": unattributed / injected if injected > 0.0 else "",
                    "residual_interpretation": "not_promoted_to_cocoon_boundary_unresolved",
                }
            )
    return rows, profile


def snapshot_identity(snapshot: Snapshot, environment: EnvironmentProfile) -> dict[str, Any]:
    return {
        "method_version": METHOD_VERSION,
        "input_h5": str(snapshot.input_h5),
        "input_size_bytes": snapshot.file_size_bytes,
        "timestep": snapshot.timestep,
        "output_index": snapshot.output_index,
        "time_code": snapshot.time_code,
        "shape": list(snapshot.shape),
        "environment_sha256": environment.source_sha256,
    }
