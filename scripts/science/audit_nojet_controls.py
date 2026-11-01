#!/usr/bin/env python3
"""Audit retained no-jet snapshots using exact cell volumes and bounded z slabs."""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from measure_q031_fluxes import Grid, read_grid
from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS, UNIT_DENSITY_CGS, UNIT_ENERGY_ERG, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS,
)
from select_common_age_hdf5 import BASELINE_ZERO_TOLERANCE_MYR, CODE_TIME_PER_MYR, Snapshot, inspect_file
from snapshot_energy import load_environment, sha256_file, write_json, write_rows


FIELDS = ("rho", "prs", "vx1", "vx2", "vx3", "tr1")
STORAGE = ("mass_g", "thermal_erg", "kinetic_erg", "gravitational_erg", "total_energy_erg")
LOW_POWER_COMPARISON_ERG = 3.15576e58
RADII_KPC = (10.0, 30.0, 80.0, 100.0)
FILE_PATTERN = re.compile(r"^data\.(\d+)\.dbl\.h5$")


@dataclass(frozen=True)
class AuditContract:
    case: str
    job_id: str
    environment_name: str
    environment_sha256: str
    shape: tuple[int, int, int]
    domain_half_widths_kpc: tuple[float, float, float]
    output_indices: tuple[int, ...]
    final_age_myr: float
    data_subdir: str = ""


CONTROL_CONTRACTS = {
    "cluster_002003": AuditContract("cluster_002003", "690366.kunanyi-ohpc", "tabulated_cosmo_002003.csv",
        "30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa",
        (500, 400, 400), (200., 200., 250.), tuple(range(6)), 50.),
    "group_002031": AuditContract("group_002031", "690371.kunanyi-ohpc", "tabulated_cosmo_002031.csv",
        "1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a",
        (500, 400, 400), (200., 200., 250.), tuple(range(6)), 50., "outputs"),
}
CORE_DEFINES = {
    "PHYSICS": "HD", "DIMENSIONS": "3", "GEOMETRY": "CARTESIAN", "BODY_FORCE": "VECTOR",
    "COOLING": "NO", "RECONSTRUCTION": "LINEAR", "TIME_STEPPING": "RK2", "NTRACER": "1",
    "SELF_GRAV": "NO", "PARTICLES": "NO", "DUST_FLUID": "NO", "EOS": "IDEAL",
    "ENTROPY_SWITCH": "SELECTIVE", "INCLUDE_LES": "NO", "THERMAL_CONDUCTION": "NO",
    "VISCOSITY": "NO", "RADIATION": "NO", "ROTATING_FRAME": "NO", "INTERNAL_BOUNDARY": "YES",
    "LIMITER": "MINMOD_LIM", "MU_NORM": "0.60364", "UNIT_DENSITY": "((CONST_amu)*MU_NORM)",
    "UNIT_LENGTH": "((CONST_pc)*1e3)", "UNIT_VELOCITY": "CONST_c", "INITIAL_SMOOTHING": "NO",
}
USER_DEFINES = {
    "DENSITY_PROFILE": "ENV_TABULATED", "JET_INJECTION_ZONE": "SPHERICAL_INJECTION_ZONE",
    "JET_INJECTION_CAP": "YES", "JET_INJECTION_ROTATED": "NO", "JET_DENSITY_CALCULATION": "DENSITY_JET_POWER",
    "JET_RELATIVISTIC_DENSITY": "NO", "SUPERNOVAE_ENERGY_INPUT": "NO", "STELLAR_MASS_LOSS": "NO",
    "PARTICLES_LP_RAISE": "NO",
}


def stat_identity(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {"path": str(path.absolute()), "resolved_path": str(path.resolve()),
            "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns,
            "device": stat.st_dev, "inode": stat.st_ino}


def identity(path: Path, *, include_text: bool = False) -> dict[str, Any]:
    before = stat_identity(path)
    result = {**before, "sha256": sha256_file(path)}
    if include_text:
        result["text"] = path.read_text()
    if stat_identity(path) != before:
        raise ValueError(f"input changed while identifying it: {path}")
    return result


def inspect_controls(paths: Sequence[Path], contract: AuditContract, output_index_file: Path) -> list[Snapshot]:
    snapshots = []
    for path in paths:
        match = FILE_PATTERN.fullmatch(path.name)
        if match is None:
            raise ValueError(f"unexpected snapshot name: {path}")
        records = inspect_file(path, output_index=int(match[1]))
        if len(records) != 1:
            raise ValueError(f"expected exactly one timestep in {path}")
        snapshots.extend(records)
    snapshots.sort(key=lambda snapshot: snapshot.time_code)
    if len(snapshots) < 2:
        raise ValueError("audit requires a zero-time and at least one later double-precision snapshot")
    if abs(snapshots[0].actual_time_myr) > BASELINE_ZERO_TOLERANCE_MYR:
        raise ValueError("first retained snapshot is not at zero time")
    if any(b.time_code <= a.time_code for a, b in zip(snapshots, snapshots[1:])):
        raise ValueError("retained snapshot times must be unique and strictly increasing")
    if len({snapshot.shape for snapshot in snapshots}) != 1:
        raise ValueError("control snapshot shapes differ")
    if snapshots[0].shape != contract.shape:
        raise ValueError(f"shape does not match the recorded control: {snapshots[0].shape}")
    if tuple(snapshot.output_index for snapshot in snapshots) != contract.output_indices:
        raise ValueError("snapshot indices do not match the complete retained-control contract")
    index_rows = {}
    for line in output_index_file.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if len(fields) != 12 or fields[4:6] != ["single_file", "little"] or fields[6:] != ["rho", "vx1", "vx2", "vx3", "prs", "tr1"]:
            raise ValueError(f"unexpected dbl.h5.out schema: {line}")
        index = int(fields[0])
        if index in index_rows:
            raise ValueError(f"duplicate output index in {output_index_file}: {index}")
        printed_time = Decimal(fields[1])
        if not printed_time.is_finite():
            raise ValueError("non-finite output-index time")
        rounding_tolerance = 0.5001 * 10.0**printed_time.as_tuple().exponent
        index_rows[index] = (float(printed_time), rounding_tolerance)
    if tuple(index_rows) != contract.output_indices:
        raise ValueError("output-index file does not match the complete retained-control contract")
    for snapshot in snapshots:
        time, tolerance = index_rows[snapshot.output_index]
        if abs(snapshot.time_code - time) > tolerance + 1e-10:
            raise ValueError(f"HDF5 time disagrees with output-index file: {snapshot.input_h5}")
    if abs(snapshots[-1].actual_time_myr - contract.final_age_myr) > BASELINE_ZERO_TOLERANCE_MYR:
        raise ValueError("final snapshot does not reach the contracted control age")
    return snapshots


def _validate_grid(grid: Grid, expected: Grid | None = None) -> None:
    for name in ("x", "y", "z", "x_edges", "y_edges", "z_edges"):
        values = getattr(grid, name)
        if not np.all(np.isfinite(values)) or not np.all(np.diff(values) > 0):
            raise ValueError(f"invalid grid axis: {name}")
        if expected is not None and not np.array_equal(values, getattr(expected, name)):
            raise ValueError(f"grid changed from baseline: {name}")


def _state(variables: h5py.Group, iz: int) -> dict[str, np.ndarray]:
    state = {name: np.asarray(variables[name][iz, :, :], dtype=np.float64) for name in FIELDS}
    if any(not np.all(np.isfinite(values)) for values in state.values()):
        raise ValueError(f"non-finite primitive at z index {iz}")
    if np.any(state["rho"] <= 0) or np.any(state["prs"] <= 0):
        raise ValueError(f"non-positive density/pressure at z index {iz}")
    if np.any(state["tr1"] != 0):
        raise ValueError(f"nonzero tracer violates no-jet control contract at z index {iz}")
    return state


def _energy(state: Mapping[str, np.ndarray], volume: np.ndarray,
            potential: np.ndarray) -> dict[str, np.ndarray]:
    mass = state["rho"] * volume * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
    velocity_squared = sum(state[name] ** 2 for name in ("vx1", "vx2", "vx3"))
    result = {
        "mass_g": mass,
        "thermal_erg": state["prs"] * volume * UNIT_ENERGY_ERG / (GAMMA_GAS - 1),
        "kinetic_erg": 0.5 * state["rho"] * velocity_squared * volume * UNIT_ENERGY_ERG,
        "gravitational_erg": mass * potential,
    }
    result["total_energy_erg"] = sum(result[name] for name in STORAGE[1:4])
    return result


def _new_region() -> dict[str, Any]:
    return {
        "cell_count": 0, "volume_kpc3": 0.0,
        "initial": dict.fromkeys(STORAGE, 0.0), "current": dict.fromkeys(STORAGE, 0.0),
        "delta": dict.fromkeys(STORAGE, 0.0), "extrema": {},
        "tracer_min": math.inf, "tracer_max": -math.inf, "nonzero_tracer_cells": 0,
        **{name: {"initial_volume_sum": 0.0, "current_volume_sum": 0.0,
                  "fractional_volume_sum": 0.0, "min_fractional_change": math.inf,
                  "max_fractional_change": -math.inf} for name in ("rho", "prs")},
    }


def _location(grid: Grid, iz: int, iy: int, ix: int, state: Mapping[str, np.ndarray],
              speed: np.ndarray, mach: np.ndarray) -> dict[str, Any]:
    coordinates = np.array([grid.x[ix], grid.y[iy], grid.z[iz]], dtype=float)
    radius = float(np.linalg.norm(coordinates))
    velocity = np.array([state[name][iy, ix] for name in ("vx1", "vx2", "vx3")]) * UNIT_VELOCITY_CMS / 1e5
    distances = [coordinates[0] - grid.x_edges[0], grid.x_edges[-1] - coordinates[0],
                 coordinates[1] - grid.y_edges[0], grid.y_edges[-1] - coordinates[1],
                 coordinates[2] - grid.z_edges[0], grid.z_edges[-1] - coordinates[2]]
    face_names = ("x_negative", "x_positive", "y_negative", "y_positive", "z_negative", "z_positive")
    sound_speed = math.sqrt(GAMMA_GAS * state["prs"][iy, ix] / state["rho"][iy, ix]) * UNIT_VELOCITY_CMS / 1e5
    return {
        "iz": iz, "iy": iy, "ix": ix, "x_kpc": float(coordinates[0]),
        "y_kpc": float(coordinates[1]), "z_kpc": float(coordinates[2]), "radius_kpc": radius,
        "nearest_boundary": face_names[int(np.argmin(distances))],
        "boundary_distance_kpc": min(distances),
        "speed_km_s": float(speed[iy, ix]), "mach": float(mach[iy, ix]),
        "sound_speed_km_s": sound_speed,
        "vx_km_s": float(velocity[0]), "vy_km_s": float(velocity[1]), "vz_km_s": float(velocity[2]),
        "radial_velocity_km_s": float(np.dot(velocity, coordinates) / radius) if radius else 0.0,
        "rho_code": float(state["rho"][iy, ix]), "prs_code": float(state["prs"][iy, ix]),
        "tracer": float(state["tr1"][iy, ix]),
    }


def measure_snapshot(*, current: h5py.Group, baseline: h5py.Group, grid: Grid,
                     environment: Any, boundary_layers: Sequence[int]) -> dict[str, dict[str, Any]]:
    names = ["whole_grid", "r_gt_100_kpc", *(f"r_lt_{radius:g}_kpc" for radius in RADII_KPC),
             *(f"boundary_layer_{layers}" for layers in boundary_layers)]
    totals = {name: _new_region() for name in names}
    ny, nx = grid.y.size, grid.x.size
    jj, ii = np.indices((ny, nx))
    xy_squared = grid.y[:, None] ** 2 + grid.x[None, :] ** 2
    area = grid.dy[:, None] * grid.dx[None, :]
    for iz, z_value in enumerate(grid.z):
        initial = _state(baseline, iz)
        state = _state(current, iz)
        radius = np.sqrt(xy_squared + z_value**2)
        volume = area * grid.dz[iz]
        potential = environment.potential_at_radius(radius * UNIT_LENGTH_CM)
        initial_energy, current_energy = _energy(initial, volume, potential), _energy(state, volume, potential)
        speed_code = np.sqrt(sum(state[name]**2 for name in ("vx1", "vx2", "vx3")))
        speed = speed_code * UNIT_VELOCITY_CMS / 1e5
        mach = speed_code / np.sqrt(GAMMA_GAS * state["prs"] / state["rho"])
        fractional = {name: (state[name] - initial[name]) / initial[name] for name in ("rho", "prs")}
        masks = {"whole_grid": np.ones((ny, nx), dtype=bool), "r_gt_100_kpc": radius > 100.0,
                 **{f"r_lt_{value:g}_kpc": radius < value for value in RADII_KPC}}
        for layers in boundary_layers:
            masks[f"boundary_layer_{layers}"] = (
                (iz < layers) | (iz >= grid.z.size - layers) | (jj < layers) | (jj >= ny - layers)
                | (ii < layers) | (ii >= nx - layers))
        for region, mask in masks.items():
            total = totals[region]
            count = int(np.count_nonzero(mask))
            if not count:
                continue
            total["cell_count"] += count
            total["volume_kpc3"] += float(np.sum(volume[mask]))
            for field in STORAGE:
                total["initial"][field] += float(np.sum(initial_energy[field][mask]))
                total["current"][field] += float(np.sum(current_energy[field][mask]))
                total["delta"][field] += float(np.sum((current_energy[field] - initial_energy[field])[mask]))
            for name in ("rho", "prs"):
                drift = total[name]
                drift["initial_volume_sum"] += float(np.sum(initial[name][mask] * volume[mask]))
                drift["current_volume_sum"] += float(np.sum(state[name][mask] * volume[mask]))
                drift["fractional_volume_sum"] += float(np.sum(fractional[name][mask] * volume[mask]))
                drift["min_fractional_change"] = min(drift["min_fractional_change"], float(np.min(fractional[name][mask])))
                drift["max_fractional_change"] = max(drift["max_fractional_change"], float(np.max(fractional[name][mask])))
            total["tracer_min"] = min(total["tracer_min"], float(np.min(state["tr1"][mask])))
            total["tracer_max"] = max(total["tracer_max"], float(np.max(state["tr1"][mask])))
            total["nonzero_tracer_cells"] += int(np.count_nonzero(state["tr1"][mask]))
            for label, values in (("maximum_speed", speed), ("maximum_mach", mach)):
                flat = int(np.argmax(np.where(mask, values, -np.inf)))
                iy, ix = np.unravel_index(flat, mask.shape)
                value = float(values[iy, ix])
                if label not in total["extrema"] or value > total["extrema"][label]["extremum_value"]:
                    total["extrema"][label] = {"extremum_value": value,
                        **_location(grid, iz, int(iy), int(ix), state, speed, mach)}
    return totals


def _rows(case: str, snapshot: Snapshot, totals: Mapping[str, Any]) -> tuple[list, list, list]:
    budgets, drifts, extrema = [], [], []
    for region, total in totals.items():
        common = {"case": case, "snapshot_index": snapshot.output_index, "timestep": snapshot.timestep,
                  "time_myr": snapshot.actual_time_myr, "region": region,
                  "cell_count": total["cell_count"], "volume_kpc3": total["volume_kpc3"]}
        budget = dict(common)
        for field in STORAGE:
            before, after, delta = (total[state][field] for state in ("initial", "current", "delta"))
            budget.update({f"initial_{field}": before, f"current_{field}": after, f"delta_{field}": delta,
                           f"delta_{field}_over_initial": delta / before if before else None})
            if field.endswith("_erg"):
                budget[f"delta_{field}_over_low_power_comparison"] = delta / LOW_POWER_COMPARISON_ERG
        budgets.append(budget)
        drift = dict(common)
        volume = total["volume_kpc3"]
        for name in ("rho", "prs"):
            data = total[name]
            for source, label in (("initial_volume_sum", "initial_volume_mean_code"),
                                  ("current_volume_sum", "current_volume_mean_code"),
                                  ("fractional_volume_sum", "volume_mean_fractional_change")):
                drift[f"{name}_{label}"] = data[source] / volume if volume else None
            for label in ("min_fractional_change", "max_fractional_change"):
                drift[f"{name}_{label}"] = data[label] if volume else None
        drift.update({"tracer_min": total["tracer_min"] if volume else None,
                      "tracer_max": total["tracer_max"] if volume else None,
                      "nonzero_tracer_cells": total["nonzero_tracer_cells"]})
        drifts.append(drift)
        for label, location in total["extrema"].items():
            extrema.append({**common, "extremum": label, **location})
    return budgets, drifts, extrema


def extract_motion_slice(*, current: h5py.Group, baseline: h5py.Group, grid: Grid,
                         maximum: Mapping[str, Any], age_myr: float) -> dict[str, np.ndarray]:
    iy = int(maximum["iy"])
    payload = {"x_kpc": grid.x.copy(), "z_kpc": grid.z.copy(), "y_kpc": np.asarray(grid.y[iy]),
               "x_edges_kpc": grid.x_edges.copy(), "z_edges_kpc": grid.z_edges.copy(),
               "selected_y_index": np.asarray(iy),
               "maximum_indices_zyx": np.asarray([maximum["iz"], iy, maximum["ix"]], dtype=np.int64),
               "time_myr": np.asarray(age_myr), "array_axis_order": np.asarray("z,x")}
    for prefix, variables in (("initial", baseline), ("current", current)):
        for name in ("rho", "prs", "vx1", "vx2", "vx3"):
            payload[f"{prefix}_{name}_code"] = np.asarray(variables[name][:, iy, :], dtype=np.float64)
    speed_code = np.sqrt(sum(payload[f"current_{name}_code"]**2 for name in ("vx1", "vx2", "vx3")))
    payload["speed_km_s"] = speed_code * UNIT_VELOCITY_CMS / 1e5
    payload["mach"] = speed_code / np.sqrt(GAMMA_GAS * payload["current_prs_code"] / payload["current_rho_code"])
    for name in ("rho", "prs"):
        payload[f"{name}_fractional_change"] = (payload[f"current_{name}_code"] - payload[f"initial_{name}_code"]) / payload[f"initial_{name}_code"]
    return payload


def render_motion_slice(path: Path, payload: Mapping[str, np.ndarray], case: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(10, 10), constrained_layout=True)
    panels = (("speed_km_s", "3D speed (km/s)", False), ("mach", "Local Mach number", False),
              ("rho_fractional_change", "Density change (%)", True),
              ("prs_fractional_change", "Pressure change (%)", True))
    iz, _, ix = payload["maximum_indices_zyx"]
    for axis, (name, label, signed) in zip(axes.flat, panels):
        values = payload[name] * (100. if signed else 1.)
        options: dict[str, Any] = {"cmap": "viridis", "vmin": 0., "vmax": max(float(np.max(values)), 1e-12)}
        if signed:
            bound = max(float(np.max(np.abs(values))), 1e-12)
            options = {"cmap": "RdBu_r", "vmin": -bound, "vmax": bound}
        mesh = axis.pcolormesh(payload["x_edges_kpc"], payload["z_edges_kpc"], values, shading="flat", **options)
        axis.plot(payload["x_kpc"][ix], payload["z_kpc"][iz], marker="x", color="white", markersize=8, markeredgewidth=2)
        axis.plot(payload["x_kpc"][ix], payload["z_kpc"][iz], marker="+", color="black", markersize=6, markeredgewidth=1)
        axis.set(xlabel="x (kpc)", ylabel="z (kpc)", title=label, aspect="equal")
        figure.colorbar(mesh, ax=axis, shrink=.85)
    stride_z = max(1, len(payload["z_kpc"]) // 18)
    stride_x = max(1, len(payload["x_kpc"]) // 18)
    vx = payload["current_vx1_code"][::stride_z, ::stride_x]
    vz = payload["current_vx3_code"][::stride_z, ::stride_x]
    if np.any(vx != 0) or np.any(vz != 0):
        axes[0, 0].quiver(payload["x_kpc"][::stride_x], payload["z_kpc"][::stride_z],
                          vx, vz, color="white", angles="xy")
    figure.suptitle(f"{case}: {float(payload['time_myr']):.3f} Myr, y = {float(payload['y_kpc']):.3f} kpc\n"
                   "Cross: global maximum-speed cell; arrows: in-plane velocity direction", fontsize=12)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _sections(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    section = ""
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            sections.setdefault(section, {})
        elif section:
            parts = line.split(None, 1)
            if len(parts) == 2:
                if parts[0] in sections[section]:
                    raise ValueError(f"duplicate configuration key: {section}/{parts[0]}")
                sections[section][parts[0]] = parts[1]
    return sections


def _validate_definitions(path: Path, expected: Mapping[str, str]) -> dict[str, str]:
    text = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.DOTALL)
    definitions: dict[str, set[str]] = {}
    for line in text.splitlines():
        match = re.match(r"\s*#define\s+(\w+)\s+(.+?)\s*$", line.split("//", 1)[0])
        if match:
            definitions.setdefault(match[1], set()).add(re.sub(r"\s+", "", match[2]))
    for name, value in expected.items():
        if definitions.get(name) != {re.sub(r"\s+", "", value)}:
            raise ValueError(f"control definition mismatch in {path}: {name}={definitions.get(name)}; expected {value}")
    return dict(expected)


def validate_contract(*, contract: AuditContract, case: str, job_id: str, control_root: Path,
                      environment_path: Path, environment_identity: Mapping[str, Any],
                      pluto_ini: Path, environment_ini: Path, definitions: Path,
                      definitions_user: Path) -> dict[str, Any]:
    if case != contract.case or job_id != contract.job_id:
        raise ValueError("case/job identity disagrees with the recorded control contract")
    if control_root.parts[-3:] != (case, job_id, "problem"):
        raise ValueError("control root must end with the recorded case/job/problem path")
    if environment_path.name != contract.environment_name or environment_identity["sha256"] != contract.environment_sha256:
        raise ValueError("environment filename/hash disagrees with the recorded control")
    reference = _sections(environment_ini).get("Tabulated Environment", {}).get("TabulatedData")
    if reference != f"./{contract.environment_name}":
        raise ValueError("environment.ini TabulatedData does not bind the contracted atmosphere")
    settings = _sections(pluto_ini)
    for axis in ("X1", "X2", "X3"):
        for side in ("beg", "end"):
            if settings.get("Boundary", {}).get(f"{axis}-{side}") != "reflective":
                raise ValueError("the recorded no-jet control requires six reflective faces")
    required_parameters = {"JET_START_TIME": 0., "JET_END_TIME": 0., "JET_ACTIVE_TIME": 0.,
                           "JET_PWR": 1e45, "JET_SPD": .1, "JET_CHI": 1., "JET_EPISODES": 1.,
                           "JET_INJECTION_HEIGHT": .75, "JET_INITIAL_RADIUS": .1,
                           "JET_OA_PRIMARY": 15., "JET_OA_SECONDARY": 15., "JET_ROTATION_ANGLE": 0.,
                           "JET_X1O": 0., "JET_X2O": 0., "JET_X3O": 0.,
                           "ENV_X1O": 0., "ENV_X2O": 0., "ENV_X3O": 0., "STELLAR_MASS": 0.}
    for name, wanted in required_parameters.items():
        raw = settings.get("Parameters", {}).get(name)
        if raw is None or not math.isfinite(float(raw)) or float(raw) != wanted:
            raise ValueError(f"recorded no-jet parameter mismatch: {name}={raw}; expected {wanted}")
    for name, wanted in (("CFL", .33), ("CFL_max_var", 1.1)):
        if float(settings.get("Time", {}).get(name, "nan")) != wanted:
            raise ValueError(f"control numerical setting mismatch: {name}")
    if settings.get("Solver", {}).get("Solver") != "hllc":
        raise ValueError("recorded control requires the HLLC solver")
    stop = float(settings.get("Time", {}).get("tstop", "nan")) / CODE_TIME_PER_MYR
    if not math.isfinite(stop) or abs(stop - contract.final_age_myr) > BASELINE_ZERO_TOLERANCE_MYR:
        raise ValueError("configured tstop disagrees with the required audit endpoint")
    for index, (cells, half_width) in enumerate(zip(reversed(contract.shape), contract.domain_half_widths_kpc), 1):
        fields = settings.get("Grid", {}).get(f"X{index}-grid", "").split()
        if (len(fields) != 5 or fields[0] != "1" or fields[3] != "u"
                or int(fields[2]) != cells or float(fields[1]) != -half_width or float(fields[4]) != half_width):
            raise ValueError("configured uniform grid disagrees with recorded control")
    return {"case": case, "job_id": job_id, "environment_sha256": contract.environment_sha256,
            "core_definitions": _validate_definitions(definitions, CORE_DEFINES),
            "user_definitions": _validate_definitions(definitions_user, USER_DEFINES),
            "expected_output_indices": list(contract.output_indices), "expected_final_age_myr": contract.final_age_myr,
            "source_disable_status": "zero active/start/end times and no tracer verified; compiled init/injection source not independently reconstructed"}


def run_audit(*, case: str, job_id: str, control_root: Path, data_dir: Path, environment_path: Path,
              pluto_ini: Path, environment_ini: Path, definitions: Path, definitions_user: Path,
              output_index_file: Path, output_dir: Path, grid_file: Path | None = None,
              config_files: Sequence[Path] = (), boundary_layers: Sequence[int] = (1, 2, 4, 8),
              contract: AuditContract | None = None) -> dict[str, Any]:
    if not case or not control_root.is_dir():
        raise ValueError("case and an existing control root are required")
    if output_dir.exists():
        raise ValueError(f"refusing to overwrite audit directory: {output_dir}")
    if not boundary_layers or any(value < 1 for value in boundary_layers) or len(set(boundary_layers)) != len(boundary_layers):
        raise ValueError("boundary layers must be unique positive integers")
    if contract is None:
        if case not in CONTROL_CONTRACTS:
            raise ValueError("unknown control case")
        contract = CONTROL_CONTRACTS[case]
    if data_dir.absolute() != (control_root / contract.data_subdir).absolute():
        raise ValueError("data directory is not the recorded control's output location")
    source_paths = [Path(__file__).with_name(name) for name in
                    ("audit_nojet_controls.py", "measure_q031_fluxes.py", "snapshot_energy.py",
                     "select_common_age_hdf5.py", "pluto_h5_level3_ambient_extract.py")]
    source_identities = [identity(path) for path in source_paths]
    files = list(dict.fromkeys([environment_path, pluto_ini, environment_ini, definitions, definitions_user,
                               output_index_file, *config_files, *([grid_file] if grid_file else [])]))
    config_identities = [identity(path, include_text=True) for path in files]
    paths = sorted(path for path in data_dir.iterdir() if FILE_PATTERN.fullmatch(path.name))
    input_identities = [{**stat_identity(path), "sha256": None,
                         "hash_status": "not_read; stat identity checked before and after streamed science read"}
                        for path in paths]
    verified_contract = validate_contract(contract=contract, case=case, job_id=job_id, control_root=control_root,
        environment_path=environment_path, environment_identity=config_identities[0], pluto_ini=pluto_ini,
        environment_ini=environment_ini, definitions=definitions, definitions_user=definitions_user)
    snapshots = inspect_controls(paths, contract, output_index_file)
    if 2 * max(boundary_layers) >= min(snapshots[0].shape):
        raise ValueError("largest boundary layer overlaps the opposite boundary")
    environment = load_environment(environment_path)
    baseline_snapshot = snapshots[0]
    budgets, drifts, extrema = [], [], []
    motion_slice = None
    with h5py.File(baseline_snapshot.input_h5, "r") as initial_h5:
        grid = read_grid(initial_h5, baseline_snapshot.shape, grid_file=grid_file)
        _validate_grid(grid)
        for edges, half_width in zip((grid.x_edges, grid.y_edges, grid.z_edges), contract.domain_half_widths_kpc):
            expected_edges = np.linspace(-half_width, half_width, len(edges))
            if not np.allclose(edges, expected_edges, rtol=0., atol=5e-5):
                raise ValueError("HDF5/grid.out geometry differs from the contracted uniform grid")
        for snapshot in snapshots:
            with h5py.File(snapshot.input_h5, "r") as current_h5:
                current_grid = read_grid(current_h5, snapshot.shape, grid_file=grid_file)
                _validate_grid(current_grid, grid)
                totals = measure_snapshot(current=current_h5[f"{snapshot.timestep}/vars"],
                    baseline=initial_h5[f"{baseline_snapshot.timestep}/vars"], grid=grid,
                    environment=environment, boundary_layers=boundary_layers)
                if snapshot is snapshots[-1]:
                    motion_slice = extract_motion_slice(current=current_h5[f"{snapshot.timestep}/vars"],
                        baseline=initial_h5[f"{baseline_snapshot.timestep}/vars"], grid=grid,
                        maximum=totals["whole_grid"]["extrema"]["maximum_speed"], age_myr=snapshot.actual_time_myr)
            budget_rows, drift_rows, extrema_rows = _rows(case, snapshot, totals)
            budgets.extend(budget_rows)
            drifts.extend(drift_rows)
            extrema.extend(extrema_rows)
            print(f"nojet_snapshot_complete={case}/{snapshot.output_index}; age_myr={snapshot.actual_time_myr:.8g}", flush=True)
    if sorted(path for path in data_dir.iterdir() if FILE_PATTERN.fullmatch(path.name)) != paths:
        raise ValueError("snapshot inventory changed during audit")
    for recorded in [*source_identities, *config_identities, *input_identities]:
        current_stat = stat_identity(Path(recorded["path"]))
        if any(recorded[key] != value for key, value in current_stat.items()):
            raise ValueError(f"input changed during audit: {recorded['path']}")
    metadata = {
        "status": "complete_existing_control_storage_and_motion_audit", "method_version": 2, "case": case,
        "job_id": job_id, "verified_control_contract": verified_contract,
        "control_root": str(control_root.absolute()), "data_dir": str(data_dir.absolute()),
        "snapshot_count": len(snapshots), "first_age_myr": snapshots[0].actual_time_myr,
        "last_age_myr": snapshots[-1].actual_time_myr, "shape_nz_ny_nx": list(snapshots[0].shape),
        "geometry": grid.edge_source, "max_center_edge_residual_kpc": grid.max_center_edge_residual_kpc,
        "domain_edges_kpc": {axis: [float(edges[0]), float(edges[-1])] for axis, edges in
                             (("x", grid.x_edges), ("y", grid.y_edges), ("z", grid.z_edges))},
        "radial_membership": "full-cell centre radius; enclosed r<R, outer r>100; strict comparisons",
        "boundary_layers": list(boundary_layers),
        "boundary_layer_membership": "union of outermost physical-cell layers on six faces; corners counted once; nested regions overlap",
        "physical_cell_contract": "HDF5 vars dimensions match active node/grid geometry; no ghost cells included",
        "potential": "fixed initial centre-zero integral of absolute tabulated gravity; unchanged at every age",
        "difference": "signed per-cell current minus same baseline cell, summed with exact FV volume",
        "comparison_energy_erg": LOW_POWER_COMPARISON_ERG,
        "comparison_energy_role": "50 Myr low-power bipolar jet comparison only; no energy is assumed injected into control",
        "velocity": "true three-component magnitude and local sqrt(gamma*p/rho); extrema evaluated independently",
        "extremum_tie_break": "first cell in increasing z,y,x index order",
        "maximum_location_boundary_distance": "cell centre to nearest physical domain face; not cell surface distance",
        "motion_slice": {"plane": "x-z at y of final global maximum-speed cell", "array_axis_order": "z,x",
                         "file": "final_motion_slice.npz", "figure": "final_motion_slice.png",
                         "selected_y_index": int(motion_slice["selected_y_index"]),
                         "maximum_indices_zyx": motion_slice["maximum_indices_zyx"].tolist(),
                         "fields": "initial/current rho,prs,vx1,vx2,vx3 in code units; derived speed km/s, Mach and signed fractional changes"},
        "radial_velocity_at_origin": "reported as zero by convention; radial direction undefined",
        "units": {"density_g_cm3": UNIT_DENSITY_CGS, "length_cm": UNIT_LENGTH_CM,
                  "velocity_cm_s": UNIT_VELOCITY_CMS, "gamma": GAMMA_GAS},
        "configuration": _sections(pluto_ini), "configuration_files": config_identities,
        "snapshot_files": input_identities,
        "analysis_sources": source_identities,
        "limitations": ["boundary mass/energy flux unmeasured; boundary-layer storage or inward edge velocity is not wall transport",
                        "initial nozzle and ongoing source disablement require source/config review; tracer values alone do not prove absence",
                        "stored configuration is provenance, not independent verification of compiled binary or unit definitions",
                        "coarse controls must not be subtracted cellwise from a different production grid",
                        "energy storage drift alone does not distinguish numerical error, source terms and physical boundary transport"],
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    write_rows(output_dir / "energy_mass_budgets.csv", budgets)
    write_rows(output_dir / "density_pressure_drift.csv", drifts)
    write_rows(output_dir / "motion_extrema.csv", extrema)
    np.savez_compressed(output_dir / "final_motion_slice.npz", **motion_slice)
    render_motion_slice(output_dir / "final_motion_slice.png", motion_slice, case)
    write_json(output_dir / "audit_metadata.json", metadata)
    manifest = {path.name: sha256_file(path) for path in sorted(output_dir.iterdir()) if path.is_file()}
    write_json(output_dir / "output_manifest.json", manifest)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=tuple(CONTROL_CONTRACTS))
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--pluto-ini", type=Path, required=True)
    parser.add_argument("--environment-ini", type=Path, required=True)
    parser.add_argument("--definitions", type=Path, required=True)
    parser.add_argument("--definitions-user", type=Path, required=True)
    parser.add_argument("--output-index-file", type=Path, required=True)
    parser.add_argument("--grid-file", type=Path)
    parser.add_argument("--config-file", type=Path, action="append", default=[])
    parser.add_argument("--boundary-layers", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run_audit(case=args.case, job_id=args.job_id, control_root=args.control_root, data_dir=args.data_dir,
              environment_path=args.environment, pluto_ini=args.pluto_ini, grid_file=args.grid_file,
              environment_ini=args.environment_ini, definitions=args.definitions, definitions_user=args.definitions_user,
              output_index_file=args.output_index_file,
              config_files=args.config_file, boundary_layers=args.boundary_layers, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
