#!/usr/bin/env python3
"""Build one validated Q-031 native path-length and shell-emission pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import numpy as np
from scipy.sparse import csr_matrix

SCIENCE_DIR = Path(__file__).resolve().parent
if str(SCIENCE_DIR) not in sys.path:
    sys.path.insert(0, str(SCIENCE_DIR))

import build_selected_age_native_shock as native_shock
import pluto_h5_level3_ambient_extract as pluto
import snapshot_energy
import snapshot_shock_energy
import xraise_grid_smoke as renderer

SNAPSHOT_INDEX = 40
VIEWS = (0, 45, 90)
SIDES = ("negative_z", "positive_z", "bipolar_total")
REGIONS = ("cocoon", "shocked_ambient", "unshocked_ambient")
PATH_REGIONS = ("whole", "cocoon", "ambient_total", "shocked_ambient", "unshocked_ambient")
CONVENTIONS = ("retained_linear", "clamp_each_coordinate")
STATES = ("current", "initial")
TRACER_THRESHOLD = 1.0e-3
KEV_PER_K = 8.617333262e-8
TEXT_RTOL = 5.1e-10
MASS_FACTOR = pluto.UNIT_DENSITY_CGS * pluto.UNIT_LENGTH_CM**3
BRIGHTNESS_VOLUME_FACTOR = renderer.KPC_M / 1.0e-29
DENSITY_LOG10_EDGES = np.linspace(-30.0, 30.0, 121)
TEMPERATURE_LOG10_EDGES = np.linspace(-10.0, 30.0, 161)
UNITS = {
    "coordinates_and_path_lengths": "kpc",
    "pixel_area": "kpc^2",
    "volume": "kpc^3",
    "density_input": "PLUTO code density",
    "pressure_input": "PLUTO code pressure",
    "mass": "g",
    "temperature": "K",
    "apec_temperature_coordinate": "keV",
    "frequency": "Hz",
    "brightness": "mJy sr^-1",
    "brightness_area_integral": "mJy sr^-1 kpc^2",
    "tracer": "dimensionless stored value promoted to float64",
}


def require_columns(rows: Sequence[Mapping[str, str]], required: Sequence[str], label: str) -> None:
    missing = sorted(set(required) - set(rows[0]))
    if missing:
        raise ValueError(f"{label} schema is missing required columns: {missing}")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"invalid CSV schema: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError(f"no rows to write: {path}")
    fields = list(materialized[0])
    if any(list(row) != fields for row in materialized):
        raise ValueError("inconsistent output row schema")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(materialized)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stat_identity(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
    }


def capture_input_state(
    *,
    native_paths: Sequence[Path],
    hashed_paths: Sequence[Path],
) -> dict[str, dict[str, Any]]:
    return {
        "native_stat_identity": {str(path): stat_identity(path) for path in native_paths},
        "compact_sha256": {str(path): sha256_file(path) for path in hashed_paths},
    }


def verify_input_state(
    before: Mapping[str, Mapping[str, Any]],
    *,
    native_paths: Sequence[Path],
    hashed_paths: Sequence[Path],
) -> dict[str, dict[str, Any]]:
    after = capture_input_state(native_paths=native_paths, hashed_paths=hashed_paths)
    if after != before:
        changed = sorted(
            key
            for section in before
            for key, value in before[section].items()
            if after[section].get(key) != value
        )
        raise ValueError(f"input drift during extraction: {changed}")
    return after


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def select_source(path: Path, case: str) -> dict[str, str]:
    rows = read_rows(path)
    require_columns(
        rows,
        (
            "case", "snapshot_index", "actual_time_myr", "actual_time_code", "input_h5",
            "timestep", "baseline_h5", "baseline_timestep", "shape_nz_ny_nx",
        ),
        "source manifest",
    )
    matches = [
        row for row in rows
        if row.get("case") == case and int(row.get("snapshot_index", -1)) == SNAPSHOT_INDEX
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {case} snapshot-40 source row; found {len(matches)}")
    row = matches[0]
    if row.get("timestep") != "Timestep_40":
        raise ValueError("snapshot 40 must bind Timestep_40")
    code_from_myr = float(row["actual_time_myr"]) * renderer.CODE_TIME_PER_MYR
    if not math.isclose(float(row["actual_time_code"]), code_from_myr, rel_tol=2e-14, abs_tol=2e-10):
        raise ValueError("source manifest time-code/time-Myr mismatch")
    return row


def parse_shape(text: str) -> tuple[int, int, int]:
    values = tuple(int(value) for value in text.split("x"))
    if len(values) != 3 or min(values) < 2:
        raise ValueError(f"invalid native shape: {text}")
    return values


def assert_close(
    label: str,
    actual: float,
    expected: float,
    *,
    rtol: float = 2e-11,
    atol: float = 1e-8,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise ValueError(f"{label} mismatch: actual={actual:.17g} reference={expected:.17g}")


def lightweight_geometry(
    baseline_path: Path,
    baseline_timestep: str,
    current_path: Path,
    current_timestep: str,
    shape: tuple[int, int, int],
    cache_dir: Path,
) -> tuple[snapshot_energy.Geometry, float]:
    with h5py.File(baseline_path, "r") as baseline, h5py.File(current_path, "r") as current:
        if pluto.require_datasets(baseline, baseline_timestep) != shape:
            raise ValueError("baseline shape does not match source manifest")
        if pluto.require_datasets(current, current_timestep) != shape:
            raise ValueError("current shape does not match source manifest")
        x, y, z = pluto.read_and_validate_axes(
            base=baseline, final=current, nz=shape[0], ny=shape[1], nx=shape[2]
        )
        baseline_time = float(baseline[baseline_timestep].attrs["Time"])
        current_time = float(current[current_timestep].attrs["Time"])
    if not math.isfinite(baseline_time) or abs(baseline_time) > 1e-8:
        raise ValueError(f"baseline timestep is not t0: {baseline_time}")
    if not math.isfinite(current_time):
        raise ValueError("current HDF5 time is non-finite")
    dx, dy, dz = (pluto.derive_widths(axis) for axis in (x, y, z))
    return (
        snapshot_energy.Geometry(
            x_kpc=x,
            y_kpc=y,
            z_kpc=z,
            dx_kpc=dx,
            dy_kpc=dy,
            dz_kpc=dz,
            volume_xy_kpc2=np.outer(dy, dx),
            potential_path=cache_dir / "unused_potential.npy",
        ),
        current_time,
    )


def side_selector(z: np.ndarray, side: str) -> np.ndarray:
    if side == "negative_z":
        return z < 0
    if side == "positive_z":
        return z > 0
    if side == "bipolar_total":
        return z != 0
    raise ValueError(f"unknown side: {side}")


def reference_rows(
    case: str,
    source: Mapping[str, str],
    native_energy: Path,
    native_shock_energy: Path,
    tracer_precision: Path,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, str]]:
    native_rows = read_rows(native_energy)
    shock_rows = read_rows(native_shock_energy)
    precision_rows = read_rows(tracer_precision)
    require_columns(
        native_rows,
        (
            "case", "snapshot_index", "actual_time_myr", "side", "partition_method",
            "actual_time_code", "tracer_threshold", "threshold_comparison", "lobe_cell_equivalent",
            "lobe_volume_kpc3", "lobe_mass_g", "gas_mass_g", "masked_initial_lobe_mass_g",
            "initial_mass_g", "current_mass_g",
        ),
        "native-energy reference",
    )
    require_columns(
        shock_rows,
        (
            "case", "snapshot_index", "actual_time_myr", "side", "threshold_factor", "status",
            "pressure_excess_threshold", "density_excess_threshold", "entropy_excess_threshold",
            "ambient_tracer_max", "ambient_energy_weighting", "control_environment", "control_role",
            "mask_volume_kpc3", "selected_cell_count",
        ),
        "native-shock reference",
    )
    require_columns(
        precision_rows,
        (
            "case", "snapshot_index", "actual_time_myr", "input_h5", "timestep", "tracer_min",
            "tracer_max", "tracer_outside_unit_interval_count", "raw_tracer_dtype",
            "raw_dtype_quantized_threshold", "raw_dtype_quantized_equality_cell_count",
            "raw_dtype_quantized_equality_volume_kpc3", "exact_double_equality_cell_count",
            "primary_threshold_float64",
        ),
        "tracer-precision reference",
    )
    native_matches = [
        row for row in native_rows
        if row.get("case") == case
        and int(row.get("snapshot_index", -1)) == SNAPSHOT_INDEX
        and row.get("partition_method") == "binary_threshold_1e-3"
    ]
    shock_matches = [
        row for row in shock_rows
        if row.get("case") == case
        and int(row.get("snapshot_index", -1)) == SNAPSHOT_INDEX
        and math.isclose(float(row.get("threshold_factor", "nan")), 1.0, abs_tol=1e-12)
    ]
    precision = [
        row for row in precision_rows
        if row.get("case") == case and int(row.get("snapshot_index", -1)) == SNAPSHOT_INDEX
    ]
    if len(native_matches) != len(SIDES) or len(shock_matches) != len(SIDES):
        raise ValueError("native reference rows are missing or duplicated")
    native = {row["side"]: row for row in native_matches}
    shock = {row["side"]: row for row in shock_matches}
    if set(native) != set(SIDES) or set(shock) != set(SIDES) or len(precision) != 1:
        raise ValueError("native reference rows are incomplete or duplicated")
    expected_time = float(source["actual_time_myr"])
    for label, rows in (("native", native_matches), ("shock", shock_matches)):
        for row in rows:
            if not math.isclose(float(row["actual_time_myr"]), expected_time, rel_tol=0, abs_tol=1e-10):
                raise ValueError(f"{label} reference age does not match selected source")
    for row in native_matches:
        if not math.isclose(
            float(row["actual_time_code"]),
            float(source["actual_time_code"]),
            rel_tol=0,
            abs_tol=1e-8,
        ):
            raise ValueError("native reference code time does not match selected source")
    expected = {
        "negative_z": "quantitative_seeded_component",
        "positive_z": "quantitative_seeded_component",
        "bipolar_total": "quantitative_bilateral",
    }
    for side, status in expected.items():
        if shock[side].get("status") != status:
            raise ValueError(f"native shock reference is not quantitative for {side}")
        if not math.isclose(float(shock[side]["ambient_tracer_max"]), TRACER_THRESHOLD, abs_tol=1e-15):
            raise ValueError(f"native shock ambient threshold mismatch for {side}")
        if shock[side].get("ambient_energy_weighting") != "binary_full_cell":
            raise ValueError(f"native shock weighting contract mismatch for {side}")
    precision_row = precision[0]
    if precision_row.get("input_h5") != source["input_h5"]:
        raise ValueError("tracer precision source identity mismatch")
    if precision_row.get("timestep") != source["timestep"]:
        raise ValueError("tracer precision timestep mismatch")
    if not math.isclose(float(precision_row["actual_time_myr"]), expected_time, rel_tol=0, abs_tol=1e-10):
        raise ValueError("tracer precision age mismatch")
    if not math.isclose(
        float(precision_row["primary_threshold_float64"]),
        TRACER_THRESHOLD,
        rel_tol=0,
        abs_tol=1e-15,
    ):
        raise ValueError("tracer precision primary threshold mismatch")
    return native, shock, precision_row


def validated_front_rows(
    path: Path,
    *,
    case: str,
    source: Mapping[str, str],
) -> dict[str, dict[str, str]]:
    all_rows = read_rows(path)
    require_columns(
        all_rows,
        (
            "case", "snapshot_index", "actual_time_myr", "side", "velocity_threshold_factor",
            "status", "shock_z_kpc", "shock_distance_kpc", "mach_kinematic",
        ),
        "accepted-front reference",
    )
    candidates = [
        row for row in all_rows
        if int(row.get("snapshot_index", -1)) == SNAPSHOT_INDEX
        and math.isclose(float(row.get("velocity_threshold_factor", "nan")), 1.0, abs_tol=1e-12)
    ]
    matches = [row for row in candidates if row.get("case") == case]
    if len(candidates) != len(matches):
        raise ValueError("accepted front reference mixes cases at snapshot 40")
    if len(matches) != 2 or {row.get("side") for row in matches} != {"negative_z", "positive_z"}:
        raise ValueError("accepted front rows are missing or duplicated")
    for row in matches:
        if not math.isclose(
            float(row["actual_time_myr"]),
            float(source["actual_time_myr"]),
            rel_tol=0,
            abs_tol=1e-10,
        ):
            raise ValueError("accepted front age does not match selected source")
        shock_z = float(row["shock_z_kpc"])
        distance = float(row["shock_distance_kpc"])
        expected_sign = -1.0 if row["side"] == "negative_z" else 1.0
        if not math.isfinite(shock_z) or math.copysign(1.0, shock_z) != expected_sign:
            raise ValueError("accepted front signed position is inconsistent with side")
        if not math.isclose(abs(shock_z), distance, rel_tol=0, abs_tol=1e-10):
            raise ValueError("accepted front signed position/distance mismatch")
    return native_shock._front_rows(path, SNAPSHOT_INDEX)


def validate_calibration_bindings(
    *,
    case: str,
    calibration_path: Path,
    thresholds: Any,
    calibration_row: Mapping[str, str],
    shock_reference: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    rows = read_rows(calibration_path)
    require_columns(
        rows,
        (
            "environment", "control_role", "adopted_pressure_excess",
            "adopted_density_excess", "adopted_entropy_excess",
            "control_joint_exceedance_fraction",
        ),
        "control calibration",
    )
    if len(rows) != 1 or dict(rows[0]) != dict(calibration_row):
        raise ValueError("control calibration must contain exactly the loaded row")
    expected_prefix = "cluster_" if case == "C-HI" else "group_"
    if not calibration_row["environment"].startswith(expected_prefix):
        raise ValueError(f"{case} calibration environment has the wrong family")
    adopted = {
        "pressure_excess_threshold": float(thresholds.pressure_excess),
        "density_excess_threshold": float(thresholds.density_excess),
        "entropy_excess_threshold": float(thresholds.entropy_excess),
    }
    for side, row in shock_reference.items():
        if row["control_environment"] != calibration_row["environment"]:
            raise ValueError(f"{side} shock reference control environment mismatch")
        if row["control_role"] != calibration_row["control_role"]:
            raise ValueError(f"{side} shock reference control role mismatch")
        for field_name, expected in adopted.items():
            if not math.isclose(float(row[field_name]), expected, rel_tol=0, abs_tol=1e-15):
                raise ValueError(f"{side} shock reference {field_name} mismatch")
    return {
        "environment": calibration_row["environment"],
        "control_role": calibration_row["control_role"],
        "adopted_thresholds": adopted,
        "shock_reference_rows_bound": True,
    }


def validate_native_masks(
    *,
    geometry: snapshot_energy.Geometry,
    shock_mask: np.ndarray,
    diagnostics: Mapping[tuple[float, str], Mapping[str, Any]],
    native_reference: Mapping[str, Mapping[str, str]],
    shock_reference: Mapping[str, Mapping[str, str]],
    current_path: Path,
    current_timestep: str,
    precision_reference: Mapping[str, str],
) -> dict[str, Any]:
    volumes = geometry.dz_kpc[:, None, None] * geometry.volume_xy_kpc2[None, :, :]
    cocoon_volume = {side: 0.0 for side in SIDES}
    cocoon_count = {side: 0 for side in SIDES}
    equality_count = exact_count = 0
    equality_volume = 0.0
    tracer_min = math.inf
    tracer_max = -math.inf
    tracer_outside_count = 0
    with h5py.File(current_path, "r") as h5:
        tracer_ds = h5[f"/{current_timestep}/vars/tr1"]
        raw_dtype = str(tracer_ds.dtype)
        quantized = float(tracer_ds.dtype.type(TRACER_THRESHOLD))
        for iz in range(tracer_ds.shape[0]):
            tracer = np.asarray(tracer_ds[iz], dtype=np.float64)
            if not np.all(np.isfinite(tracer)):
                raise ValueError(f"non-finite tracer at z index {iz}")
            tracer_min = min(tracer_min, float(np.min(tracer)))
            tracer_max = max(tracer_max, float(np.max(tracer)))
            tracer_outside_count += int(np.count_nonzero((tracer < 0) | (tracer > 1)))
            equality = tracer == quantized
            equality_count += int(np.count_nonzero(equality))
            equality_volume += float(np.sum(volumes[iz][equality]))
            exact_count += int(np.count_nonzero(tracer == TRACER_THRESHOLD))
            cocoon = tracer > TRACER_THRESHOLD
            slice_side = "negative_z" if geometry.z_kpc[iz] < 0 else "positive_z"
            for side in (slice_side, "bipolar_total"):
                cocoon_count[side] += int(np.count_nonzero(cocoon))
                cocoon_volume[side] += float(np.sum(volumes[iz][cocoon]))
    result: dict[str, Any] = {"sides": {}}
    for side in SIDES:
        if side != "bipolar_total" and diagnostics[(1.0, side)]["status"] != "quantitative_seeded_component":
            raise ValueError(f"shock classification unavailable for {side}")
        zmask = side_selector(geometry.z_kpc, side)
        shock_count = int(np.count_nonzero(shock_mask[zmask]))
        shock_volume = float(np.sum(volumes[zmask] * shock_mask[zmask]))
        assert_close(
            f"{side} cocoon volume",
            cocoon_volume[side],
            float(native_reference[side]["lobe_volume_kpc3"]),
        )
        if not math.isclose(
            float(native_reference[side]["tracer_threshold"]),
            TRACER_THRESHOLD,
            rel_tol=0,
            abs_tol=1e-15,
        ):
            raise ValueError(f"{side} native tracer-threshold reference mismatch")
        if native_reference[side].get("threshold_comparison") != "float64_stored_value_strict_gt":
            raise ValueError(f"{side} native tracer comparison contract mismatch")
        if cocoon_count[side] != int(float(native_reference[side]["lobe_cell_equivalent"])):
            raise ValueError(f"{side} cocoon cell-count reference mismatch")
        if shock_count != int(float(shock_reference[side]["selected_cell_count"])):
            raise ValueError(f"{side} shock cell-count reference mismatch")
        assert_close(
            f"{side} shock volume",
            shock_volume,
            float(shock_reference[side]["mask_volume_kpc3"]),
        )
        result["sides"][side] = {
            "cocoon_cell_count": cocoon_count[side],
            "cocoon_volume_kpc3": cocoon_volume[side],
            "shock_cell_count": shock_count,
            "shock_volume_kpc3": shock_volume,
            "shock_status": (
                diagnostics[(1.0, side)]["status"]
                if side != "bipolar_total" else "quantitative_bilateral"
            ),
        }
    expected_quantized = float(precision_reference["raw_dtype_quantized_threshold"])
    if raw_dtype != precision_reference["raw_tracer_dtype"]:
        raise ValueError("raw tracer dtype differs from precision reference")
    if quantized != expected_quantized:
        raise ValueError("raw tracer quantized threshold differs from reference")
    if equality_count != int(precision_reference["raw_dtype_quantized_equality_cell_count"]):
        raise ValueError("raw tracer threshold-equality count differs from reference")
    assert_close(
        "raw tracer threshold-equality volume",
        equality_volume,
        float(precision_reference["raw_dtype_quantized_equality_volume_kpc3"]),
        rtol=2e-11,
        atol=1e-12,
    )
    if exact_count != int(precision_reference["exact_double_equality_cell_count"]):
        raise ValueError("exact float64 threshold-equality count differs from reference")
    assert_close("tracer minimum", tracer_min, float(precision_reference["tracer_min"]), rtol=0, atol=1e-12)
    assert_close("tracer maximum", tracer_max, float(precision_reference["tracer_max"]), rtol=0, atol=1e-12)
    if tracer_outside_count != int(precision_reference["tracer_outside_unit_interval_count"]):
        raise ValueError("tracer outside-unit-interval count differs from reference")
    result["tracer_precision"] = {
        "raw_dtype": raw_dtype,
        "float64_threshold": TRACER_THRESHOLD,
        "raw_dtype_quantized_threshold": quantized,
        "raw_dtype_quantized_equality_cell_count": equality_count,
        "raw_dtype_quantized_equality_volume_kpc3": equality_volume,
        "exact_float64_equality_cell_count": exact_count,
        "tracer_min": tracer_min,
        "tracer_max": tracer_max,
        "tracer_outside_unit_interval_count": tracer_outside_count,
    }
    return result


@dataclass(frozen=True)
class TableBundle:
    apec: Any
    gaunt: Any
    apec_temp_bounds_kev: tuple[float, float]
    apec_redshift_bounds: tuple[float, float]
    gaunt_temp_bounds_k: tuple[float, float]
    gaunt_frequency_bounds_hz: tuple[float, float]


def load_tables(apec_path: Path, gaunt_path: Path) -> TableBundle:
    apec, gaunt = renderer.make_interpolators(apec_path, gaunt_path)
    raw = np.genfromtxt(apec_path, delimiter=",", filling_values=np.nan)
    lut = np.load(gaunt_path)
    bounds = (
        (float(np.nanmin(raw[1:, 0])), float(np.nanmax(raw[1:, 0]))),
        (float(np.nanmin(raw[0, 1:])), float(np.nanmax(raw[0, 1:]))),
        (float(np.min(lut["T"])), float(np.max(lut["T"]))),
        (float(np.min(lut["f"])), float(np.max(lut["f"]))),
    )
    if any(not (math.isfinite(lo) and math.isfinite(hi) and lo < hi) for lo, hi in bounds):
        raise ValueError("invalid interpolation-table bounds")
    return TableBundle(apec, gaunt, *bounds)


def cell_emissivity(
    *,
    xraise: Any,
    tables: TableBundle,
    rho_code: np.ndarray,
    pressure_code: np.ndarray,
    frequency_hz: float,
    redshift: float,
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, np.ndarray]]:
    grid, temperature_k = xraise.grid_bremsstrahlung(
        rho_code * renderer.UNIT_DENSITY_SI,
        pressure_code * renderer.UNIT_PRESSURE_SI,
        frequencies=np.array([frequency_hz], dtype=float),
        redshifts=np.array([redshift], dtype=float),
    )
    raw_before = np.asarray(grid[..., 0, 0], dtype=np.float64)
    raw = np.nan_to_num(raw_before, nan=0.0, posinf=0.0, neginf=0.0)
    temperature_k = np.asarray(temperature_k, dtype=np.float64)
    if not np.all(np.isfinite(temperature_k)) or np.any(temperature_k <= 0):
        raise ValueError("XRAiSE returned non-finite or non-positive temperature")
    temperature_kev = temperature_k * KEV_PER_K
    red = np.full_like(temperature_kev, redshift)
    freq = np.full_like(temperature_k, frequency_hz)
    retained_before = raw * tables.apec(np.stack((temperature_kev, red), axis=-1)) * tables.gaunt(
        np.stack((temperature_k, freq), axis=-1)
    )
    clamp_before = raw * tables.apec(
        np.stack(
            (
                np.clip(temperature_kev, *tables.apec_temp_bounds_kev),
                np.clip(red, *tables.apec_redshift_bounds),
            ),
            axis=-1,
        )
    ) * tables.gaunt(
        np.stack(
            (
                np.clip(temperature_k, *tables.gaunt_temp_bounds_k),
                np.clip(freq, *tables.gaunt_frequency_bounds_hz),
            ),
            axis=-1,
        )
    )
    result = {
        "retained_linear_before": retained_before,
        "retained_linear": np.nan_to_num(retained_before, nan=0.0, posinf=0.0, neginf=0.0),
        "clamp_each_coordinate_before": clamp_before,
        "clamp_each_coordinate": np.nan_to_num(clamp_before, nan=0.0, posinf=0.0, neginf=0.0),
    }
    flags = {
        "apec_temperature": (temperature_kev < tables.apec_temp_bounds_kev[0])
        | (temperature_kev > tables.apec_temp_bounds_kev[1]),
        "apec_redshift": (red < tables.apec_redshift_bounds[0])
        | (red > tables.apec_redshift_bounds[1]),
        "gaunt_temperature": (temperature_k < tables.gaunt_temp_bounds_k[0])
        | (temperature_k > tables.gaunt_temp_bounds_k[1]),
        "gaunt_frequency": (freq < tables.gaunt_frequency_bounds_hz[0])
        | (freq > tables.gaunt_frequency_bounds_hz[1]),
        "raw_nonfinite": ~np.isfinite(raw_before),
    }
    flags["any"] = flags["apec_temperature"] | flags["apec_redshift"] | flags["gaunt_temperature"] | flags["gaunt_frequency"]
    return result, temperature_k, flags


@dataclass
class RegionStats:
    cell_count: int = 0
    volume_kpc3: float = 0.0
    current_mass_g: float = 0.0
    initial_mass_g: float = 0.0
    mass_delta_positive_g: float = 0.0
    mass_delta_negative_g: float = 0.0
    rho_volume_sum: dict[str, float] = field(default_factory=lambda: {state: 0.0 for state in STATES})
    rho_min: dict[str, float] = field(default_factory=lambda: {state: math.inf for state in STATES})
    rho_max: dict[str, float] = field(default_factory=lambda: {state: -math.inf for state in STATES})
    temp_volume_sum: dict[str, float] = field(default_factory=lambda: {state: 0.0 for state in STATES})
    oor_cell_count: dict[str, int] = field(default_factory=lambda: {state: 0 for state in STATES})
    oor_volume: dict[str, float] = field(default_factory=lambda: {state: 0.0 for state in STATES})
    raw_kernel_nonfinite_cell_count: dict[str, int] = field(
        default_factory=lambda: {state: 0 for state in STATES}
    )
    raw_kernel_nonfinite_volume: dict[str, float] = field(
        default_factory=lambda: {state: 0.0 for state in STATES}
    )
    correction_oor_count: dict[str, dict[str, int]] = field(
        default_factory=lambda: {
            state: {coordinate: 0 for coordinate in (
                "apec_temperature", "apec_redshift", "gaunt_temperature", "gaunt_frequency"
            )}
            for state in STATES
        }
    )
    emission: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            f"{state}_{convention}": {
                "signed": 0.0,
                "absolute": 0.0,
                "positive": 0.0,
                "negative": 0.0,
                "temperature_numerator": 0.0,
                "oor_signed": 0.0,
                "oor_absolute": 0.0,
                "negative_cell_count": 0,
                "nonfinite_cell_count": 0,
                "nonfinite_volume_kpc3": 0.0,
            }
            for state in STATES for convention in CONVENTIONS
        }
    )
    density_volume_hist: dict[str, np.ndarray] = field(
        default_factory=lambda: {
            state: np.zeros(len(DENSITY_LOG10_EDGES) - 1) for state in STATES
        }
    )
    temperature_volume_hist: dict[str, np.ndarray] = field(
        default_factory=lambda: {
            state: np.zeros(len(TEMPERATURE_LOG10_EDGES) - 1) for state in STATES
        }
    )
    density_emission_hist: dict[str, dict[str, np.ndarray]] = field(
        default_factory=lambda: {
            f"{state}_{convention}": {
                "signed": np.zeros(len(DENSITY_LOG10_EDGES) - 1),
                "absolute": np.zeros(len(DENSITY_LOG10_EDGES) - 1),
            }
            for state in STATES for convention in CONVENTIONS
        }
    )
    temperature_emission_hist: dict[str, dict[str, np.ndarray]] = field(
        default_factory=lambda: {
            f"{state}_{convention}": {
                "signed": np.zeros(len(TEMPERATURE_LOG10_EDGES) - 1),
                "absolute": np.zeros(len(TEMPERATURE_LOG10_EDGES) - 1),
            }
            for state in STATES for convention in CONVENTIONS
        }
    )

    def add(
        self,
        *,
        mask: np.ndarray,
        volume: np.ndarray,
        rho: Mapping[str, np.ndarray],
        temperature: Mapping[str, np.ndarray],
        emissivity: Mapping[str, Mapping[str, np.ndarray]],
        flags: Mapping[str, Mapping[str, np.ndarray]],
    ) -> None:
        if not np.any(mask):
            return
        selected_volume = volume[mask]
        self.cell_count += int(np.count_nonzero(mask))
        self.volume_kpc3 += float(np.sum(selected_volume))
        masses: dict[str, np.ndarray] = {}
        for state in STATES:
            density = rho[state][mask]
            masses[state] = density * selected_volume * MASS_FACTOR
            setattr(self, f"{state}_mass_g", getattr(self, f"{state}_mass_g") + float(np.sum(masses[state])))
            self.rho_volume_sum[state] += float(np.sum(density * selected_volume))
            self.rho_min[state] = min(self.rho_min[state], float(np.min(density)))
            self.rho_max[state] = max(self.rho_max[state], float(np.max(density)))
            self.temp_volume_sum[state] += float(np.sum(temperature[state][mask] * selected_volume))
            self.density_volume_hist[state] += np.histogram(
                np.log10(density), bins=DENSITY_LOG10_EDGES, weights=selected_volume
            )[0]
            selected_temperature = temperature[state][mask]
            self.temperature_volume_hist[state] += np.histogram(
                np.log10(selected_temperature),
                bins=TEMPERATURE_LOG10_EDGES,
                weights=selected_volume,
            )[0]
            oor = flags[state]["any"] & mask
            self.oor_cell_count[state] += int(np.count_nonzero(oor))
            self.oor_volume[state] += float(np.sum(volume[oor]))
            raw_nonfinite = flags[state]["raw_nonfinite"] & mask
            self.raw_kernel_nonfinite_cell_count[state] += int(np.count_nonzero(raw_nonfinite))
            self.raw_kernel_nonfinite_volume[state] += float(np.sum(volume[raw_nonfinite]))
            for coordinate in self.correction_oor_count[state]:
                self.correction_oor_count[state][coordinate] += int(
                    np.count_nonzero(flags[state][coordinate] & mask)
                )
            for convention in CONVENTIONS:
                key = f"{state}_{convention}"
                before = emissivity[state][f"{convention}_before"]
                values = emissivity[state][convention][mask] * selected_volume * BRIGHTNESS_VOLUME_FACTOR
                target = self.emission[key]
                target["signed"] += float(np.sum(values))
                target["absolute"] += float(np.sum(np.abs(values)))
                target["positive"] += float(np.sum(values[values > 0]))
                target["negative"] += float(np.sum(values[values < 0]))
                target["temperature_numerator"] += float(
                    np.sum(
                        emissivity[state][convention][mask]
                        * temperature[state][mask]
                        * selected_volume
                        * BRIGHTNESS_VOLUME_FACTOR
                    )
                )
                target["oor_signed"] += float(
                    np.sum(emissivity[state][convention][oor] * volume[oor] * BRIGHTNESS_VOLUME_FACTOR)
                )
                target["oor_absolute"] += float(
                    np.sum(np.abs(emissivity[state][convention][oor] * volume[oor] * BRIGHTNESS_VOLUME_FACTOR))
                )
                before_selected = before[mask]
                target["negative_cell_count"] += int(
                    np.count_nonzero(np.isfinite(before_selected) & (before_selected < 0))
                )
                target["nonfinite_cell_count"] += int(np.count_nonzero(~np.isfinite(before[mask])))
                invalid_corrected = (~np.isfinite(before)) & mask
                target["nonfinite_volume_kpc3"] += float(np.sum(volume[invalid_corrected]))
                cell_emission = emissivity[state][convention][mask] * selected_volume * BRIGHTNESS_VOLUME_FACTOR
                self.density_emission_hist[key]["signed"] += np.histogram(
                    np.log10(density), bins=DENSITY_LOG10_EDGES, weights=cell_emission
                )[0]
                self.density_emission_hist[key]["absolute"] += np.histogram(
                    np.log10(density), bins=DENSITY_LOG10_EDGES, weights=np.abs(cell_emission)
                )[0]
                self.temperature_emission_hist[key]["signed"] += np.histogram(
                    np.log10(selected_temperature),
                    bins=TEMPERATURE_LOG10_EDGES,
                    weights=cell_emission,
                )[0]
                self.temperature_emission_hist[key]["absolute"] += np.histogram(
                    np.log10(selected_temperature),
                    bins=TEMPERATURE_LOG10_EDGES,
                    weights=np.abs(cell_emission),
                )[0]
        delta_mass = masses["current"] - masses["initial"]
        self.mass_delta_positive_g += float(np.sum(delta_mass[delta_mass > 0]))
        self.mass_delta_negative_g += float(np.sum(delta_mass[delta_mass < 0]))

    def output_row(self, case: str, region: str, side: str) -> dict[str, Any]:
        row: dict[str, Any] = {
            "case": case,
            "snapshot_index": SNAPSHOT_INDEX,
            "region": region,
            "side": side,
            "cell_count": self.cell_count,
            "volume_kpc3": self.volume_kpc3,
            "current_mass_g": self.current_mass_g,
            "initial_mass_g": self.initial_mass_g,
            "mass_delta_net_g": self.current_mass_g - self.initial_mass_g,
            "mass_delta_positive_g": self.mass_delta_positive_g,
            "mass_delta_negative_g": self.mass_delta_negative_g,
        }
        for state in STATES:
            row[f"{state}_density_code_volume_mean"] = (
                self.rho_volume_sum[state] / self.volume_kpc3 if self.volume_kpc3 else ""
            )
            row[f"{state}_density_code_min"] = self.rho_min[state] if self.cell_count else ""
            row[f"{state}_density_code_max"] = self.rho_max[state] if self.cell_count else ""
            row[f"{state}_temperature_k_volume_mean"] = (
                self.temp_volume_sum[state] / self.volume_kpc3 if self.volume_kpc3 else ""
            )
            row[f"{state}_oor_any_cell_count"] = self.oor_cell_count[state]
            row[f"{state}_oor_any_volume_kpc3"] = self.oor_volume[state]
            row[f"{state}_oor_any_volume_fraction"] = (
                self.oor_volume[state] / self.volume_kpc3 if self.volume_kpc3 else ""
            )
            row[f"{state}_raw_kernel_nonfinite_cell_count_before_sanitization"] = (
                self.raw_kernel_nonfinite_cell_count[state]
            )
            row[f"{state}_raw_kernel_nonfinite_volume_kpc3_before_sanitization"] = (
                self.raw_kernel_nonfinite_volume[state]
            )
            for coordinate, count in self.correction_oor_count[state].items():
                row[f"{state}_{coordinate}_oor_cell_count"] = count
            for convention in CONVENTIONS:
                prefix = f"{state}_{convention}"
                values = self.emission[prefix]
                row[f"{prefix}_emissivity_integral_mjy_sr_kpc2"] = values["signed"]
                row[f"{prefix}_absolute_emissivity_integral_mjy_sr_kpc2"] = values["absolute"]
                row[f"{prefix}_positive_emissivity_integral_mjy_sr_kpc2"] = values["positive"]
                row[f"{prefix}_negative_emissivity_integral_mjy_sr_kpc2"] = values["negative"]
                row[f"{prefix}_emission_weighted_temperature_k"] = (
                    values["temperature_numerator"] / values["signed"]
                    if values["signed"] > 0 else ""
                )
                row[f"{prefix}_oor_signed_emissivity_mjy_sr_kpc2"] = values["oor_signed"]
                row[f"{prefix}_oor_absolute_emissivity_mjy_sr_kpc2"] = values["oor_absolute"]
                row[f"{prefix}_oor_fraction_of_absolute_emissivity"] = (
                    values["oor_absolute"] / values["absolute"] if values["absolute"] > 0 else ""
                )
                row[f"{prefix}_negative_cell_count"] = values["negative_cell_count"]
                row[f"{prefix}_nonfinite_cell_count_before_sanitization"] = values["nonfinite_cell_count"]
                row[f"{prefix}_nonfinite_volume_kpc3_before_sanitization"] = values[
                    "nonfinite_volume_kpc3"
                ]
        for convention in CONVENTIONS:
            current = self.emission[f"current_{convention}"]["signed"]
            initial = self.emission[f"initial_{convention}"]["signed"]
            row[f"delta_{convention}_emissivity_integral_mjy_sr_kpc2"] = current - initial
        return row

    def distributions(self, case: str, region: str, side: str) -> dict[str, Any]:
        return {
            "case": case,
            "snapshot_index": SNAPSHOT_INDEX,
            "region": region,
            "side": side,
            "density_log10_code_edges": DENSITY_LOG10_EDGES.tolist(),
            "temperature_log10_k_edges": TEMPERATURE_LOG10_EDGES.tolist(),
            "density_volume_weight_kpc3": {
                state: self.density_volume_hist[state].tolist() for state in STATES
            },
            "temperature_volume_weight_kpc3": {
                state: self.temperature_volume_hist[state].tolist() for state in STATES
            },
            "density_emission_weight_mjy_sr_kpc2": {
                key: {kind: values.tolist() for kind, values in histograms.items()}
                for key, histograms in self.density_emission_hist.items()
            },
            "temperature_emission_weight_mjy_sr_kpc2": {
                key: {kind: values.tolist() for kind, values in histograms.items()}
                for key, histograms in self.temperature_emission_hist.items()
            },
        }


def make_map_accumulators(
    geometry: snapshot_energy.Geometry,
    projected_u_bins: int,
) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for view in VIEWS:
        method = renderer.resolve_projection_method(float(view), "auto")
        if view == 0:
            horizontal = geometry.x_kpc.copy()
            horizontal_edges = renderer.centres_to_edges(horizontal)
        else:
            horizontal, horizontal_edges = renderer.projected_axis(
                geometry.x_kpc,
                geometry.y_kpc,
                view_angle_deg=float(view),
                projected_u_bins=projected_u_bins,
            )
        map_shape = (len(geometry.z_kpc), len(horizontal))
        maps: dict[str, np.ndarray] = {
            f"path_{region}_kpc": np.zeros(map_shape, dtype=np.float64)
            for region in PATH_REGIONS
        }
        maps["tracer_max"] = np.zeros(map_shape, dtype=np.float64)
        for state in STATES:
            for convention in CONVENTIONS:
                for region in (*REGIONS, "whole"):
                    maps[f"brightness_{region}_{state}_{convention}"] = np.zeros(map_shape)
                    maps[f"temperature_numerator_{region}_{state}_{convention}"] = np.zeros(map_shape)
        result[view] = {
            "method": method,
            "horizontal": horizontal,
            "horizontal_edges": horizontal_edges,
            "maps": maps,
        }
    return result


def make_refined_geometry_accumulators(
    geometry: snapshot_energy.Geometry,
    projected_u_bins: int,
    refinement_factor: int,
) -> dict[int, dict[str, Any]]:
    if refinement_factor < 2:
        raise ValueError("geometry refinement factor must be at least two")
    result: dict[int, dict[str, Any]] = {}
    for view in (45, 90):
        horizontal, edges = renderer.projected_axis(
            geometry.x_kpc,
            geometry.y_kpc,
            view_angle_deg=float(view),
            projected_u_bins=projected_u_bins * refinement_factor,
        )
        shape = (len(geometry.z_kpc), len(horizontal))
        result[view] = {
            "method": "edge_overlap_uniform_cell_projection",
            "horizontal": horizontal,
            "horizontal_edges": edges,
            "maps": {
                "path_cocoon_kpc": np.zeros(shape, dtype=np.float64),
                "tracer_max": np.zeros(shape, dtype=np.float64),
            },
        }
    return result


def accumulate_direct_y(
    target: np.ndarray,
    values: np.ndarray,
    y_widths_kpc: np.ndarray,
    scale: float,
) -> None:
    target += np.sum(values * y_widths_kpc[None, :, None], axis=1) * scale


def accumulate_overlap(
    target: np.ndarray,
    values: np.ndarray,
    cell_indices: np.ndarray,
    bin_indices: np.ndarray,
    path_weights: np.ndarray,
    scale: float,
) -> None:
    for iz in range(values.shape[0]):
        weighted = values[iz].ravel()[cell_indices] * path_weights
        target[iz] += np.bincount(bin_indices, weights=weighted, minlength=target.shape[1]) * scale


def accumulate_overlap_fields(
    *,
    maps: Mapping[str, np.ndarray],
    fields: Mapping[str, np.ndarray],
    cell_indices: np.ndarray,
    bin_indices: np.ndarray,
    path_weights: np.ndarray,
    source_cell_count: int,
    z_batch: int = 8,
) -> None:
    """Project many scalar fields through one accepted overlap operator."""

    names = list(fields)
    target_bins = next(iter(maps.values())).shape[1]
    operator = csr_matrix(
        (path_weights, (cell_indices, bin_indices)),
        shape=(source_cell_count, target_bins),
    )
    nz = next(iter(fields.values())).shape[0]
    for start in range(0, nz, z_batch):
        stop = min(start + z_batch, nz)
        block = stop - start
        stacked = np.stack(
            [np.asarray(fields[name][start:stop], dtype=np.float64).reshape(block, -1) for name in names]
        )
        projected = operator.T.dot(stacked.reshape(len(names) * block, source_cell_count).T).T
        projected = np.asarray(projected).reshape(len(names), block, target_bins)
        for index, name in enumerate(names):
            scale = 1.0 if name.startswith("path_") else renderer.KPC_M / 1.0e-29
            maps[name][start:stop] += projected[index] * scale


def accumulate_tracer_overlap(
    target: np.ndarray,
    tracer: np.ndarray,
    cell_indices: np.ndarray,
    bin_indices: np.ndarray,
) -> None:
    for iz in range(tracer.shape[0]):
        by_bin = np.zeros(target.shape[1], dtype=np.float64)
        np.maximum.at(by_bin, bin_indices, tracer[iz].ravel()[cell_indices])
        target[iz] = np.maximum(target[iz], by_bin)


def project_chunk(
    *,
    accumulators: Mapping[int, Mapping[str, Any]],
    geometry: snapshot_energy.Geometry,
    start: int,
    stop: int,
    fields: Mapping[str, np.ndarray],
    tracer: np.ndarray,
) -> None:
    x_edges = renderer.centres_to_edges(geometry.x_kpc)
    global_y_edges = renderer.centres_to_edges(geometry.y_kpc)
    for view, bundle in accumulators.items():
        maps = bundle["maps"]
        if view == 0:
            for name, values in fields.items():
                scale = 1.0 if name.startswith("path_") else renderer.KPC_M / 1.0e-29
                accumulate_direct_y(maps[name], values, geometry.dy_kpc[start:stop], scale)
            maps["tracer_max"] = np.maximum(maps["tracer_max"], np.max(tracer, axis=1))
            continue
        cell_indices, bin_indices, weights = renderer.projected_overlap_contributions(
            x_edges=x_edges,
            y_edges_chunk=global_y_edges[start : stop + 1],
            u_edges=bundle["horizontal_edges"],
            view_angle_deg=float(view),
        )
        accumulate_overlap_fields(
            maps=maps,
            fields=fields,
            cell_indices=cell_indices,
            bin_indices=bin_indices,
            path_weights=weights,
            source_cell_count=(stop - start) * len(geometry.x_kpc),
        )
        accumulate_tracer_overlap(maps["tracer_max"], tracer, cell_indices, bin_indices)


def closure_check(
    label: str,
    lhs: np.ndarray,
    rhs: np.ndarray,
    *,
    rtol: float = 3e-11,
    atol: float = 2e-10,
) -> dict[str, float]:
    difference = lhs - rhs
    max_abs = float(np.max(np.abs(difference), initial=0))
    scale = float(max(np.max(np.abs(lhs), initial=0), np.max(np.abs(rhs), initial=0), 1.0))
    if max_abs > atol + rtol * scale:
        raise ValueError(f"{label} closure failed: max_abs={max_abs:.17g}, scale={scale:.17g}")
    return {"max_abs": max_abs, "relative_to_peak": max_abs / scale}


def validate_projected_integral(
    label: str,
    projected_map: np.ndarray,
    pixel_area: np.ndarray,
    selected_rows: np.ndarray,
    cell_integral: float,
) -> float:
    projected_integral = float(
        np.sum(projected_map[selected_rows] * pixel_area[selected_rows])
    )
    assert_close(
        label,
        projected_integral,
        cell_integral,
        rtol=4e-11,
        atol=2e-7,
    )
    return projected_integral


def text_comparison(
    label: str,
    actual: np.ndarray,
    retained: np.ndarray,
) -> dict[str, float]:
    if actual.shape != retained.shape:
        raise ValueError(f"{label} shape mismatch: {actual.shape} vs {retained.shape}")
    delta = actual - retained
    max_abs = float(np.max(np.abs(delta), initial=0))
    scale = float(max(np.max(np.abs(retained), initial=0), 1.0))
    tolerance = TEXT_RTOL * np.abs(retained) + 32 * np.finfo(np.float64).eps * scale
    if np.any(np.abs(delta) > tolerance):
        raise ValueError(f"{label} retained reproduction failed: max_abs={max_abs:.17g}")
    return {
        "max_abs": max_abs,
        "relative_to_retained_peak": max_abs / scale,
        "max_fraction_of_text_precision_tolerance": float(
            np.max(np.abs(delta) / tolerance, initial=0)
        ),
    }


def retained_view(root: Path, view: int) -> Path:
    path = root / f"xraise_grid_{view}deg"
    names = {
        "xray_1kev_xraise_corrected_mjy_sr.tsv",
        "tracer_max_los.tsv",
        "z_kpc.tsv",
        "xraise_grid_smoke_metadata.json",
        "x_kpc.tsv" if view == 0 else "u_kpc.tsv",
    }
    missing = sorted(name for name in names if not (path / name).is_file())
    if missing:
        raise ValueError(f"retained view {view} is incomplete: {missing}")
    return path


def validate_retained_metadata(
    *,
    retained_dirs: Mapping[int, Path],
    source: Mapping[str, str],
    original_current_path: str,
    shape: tuple[int, int, int],
    projected_u_bins: int,
    y_chunk: int,
    frequency_hz: float,
    redshift: float,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for view, directory in retained_dirs.items():
        metadata = json.loads((directory / "xraise_grid_smoke_metadata.json").read_text())
        expected = {
            "input_h5": original_current_path,
            "timestep": source["timestep"],
            "grid_shape_nz_ny_nx": list(shape),
            "y_chunk": y_chunk,
        }
        for key, value in expected.items():
            if metadata.get(key) != value:
                raise ValueError(
                    f"retained {view}deg metadata {key} mismatch: "
                    f"{metadata.get(key)!r} vs {value!r}"
                )
        numeric = {
            "time_code": float(source["actual_time_code"]),
            "frequency_hz": frequency_hz,
            "redshift": redshift,
        }
        for key, value in numeric.items():
            if not math.isclose(float(metadata.get(key, math.nan)), value, rel_tol=2e-14, abs_tol=1e-10):
                raise ValueError(f"retained {view}deg metadata {key} mismatch")
        projection = metadata.get("projection", {})
        if not math.isclose(float(projection.get("view_angle_deg", math.nan)), view, abs_tol=1e-12):
            raise ValueError(f"retained {view}deg view-angle metadata mismatch")
        expected_bins = shape[2] if view == 0 else projected_u_bins
        if int(projection.get("sky_horizontal_bins", -1)) != expected_bins:
            raise ValueError(f"retained {view}deg projected-bin metadata mismatch")
        expected_method = renderer.resolve_projection_method(float(view), "auto")
        if projection.get("projected_accumulation") != expected_method:
            raise ValueError(f"retained {view}deg projection method metadata mismatch")
        result[f"{view}deg"] = {
            "source_identity_match": True,
            "timestep_match": True,
            "time_match": True,
            "shape_match": True,
            "axes_and_projection_contract_match": True,
        }
    return result


def exact_abs_u_moments(
    mask: np.ndarray,
    u_edges: np.ndarray,
    z_edges: np.ndarray,
) -> dict[str, float | int]:
    """Integrate |u| exactly within rectangular pixels, including u=0 crossings."""

    dz = np.diff(z_edges)
    left, right = u_edges[:-1], u_edges[1:]
    negative_moment = np.where(
        right <= 0,
        0.5 * (left * left - right * right),
        np.where(left < 0, 0.5 * left * left, 0.0),
    )
    positive_moment = np.where(
        left >= 0,
        0.5 * (right * right - left * left),
        np.where(right > 0, 0.5 * right * right, 0.0),
    )
    negative = float(np.sum(mask * dz[:, None] * negative_moment[None, :]))
    positive = float(np.sum(mask * dz[:, None] * positive_moment[None, :]))
    centre_moment = float(
        np.sum(mask * dz[:, None] * np.diff(u_edges)[None, :] * np.abs(0.5 * (left + right))[None, :])
    )
    return {
        "negative_u_revolution_kpc3": 2 * math.pi * negative,
        "positive_u_revolution_kpc3": 2 * math.pi * positive,
        "symmetrized_revolution_kpc3": math.pi * (negative + positive),
        "centre_approximation_symmetrized_kpc3": math.pi * centre_moment,
        "central_crossing_pixel_count": int(
            np.count_nonzero(mask[:, (left < 0) & (right > 0)])
        ),
    }


def ellipse_volumes(mask: np.ndarray, horizontal: np.ndarray, z: np.ndarray) -> dict[str, float]:
    import xray_cavity_method_ladder

    result = xray_cavity_method_ladder.side_volumes(mask, horizontal, z)
    return {key: result[key] for key in ("minor_depth", "geometric_depth", "major_depth")}


def map_checks_and_budgets(
    *,
    case: str,
    accumulators: Mapping[int, Mapping[str, Any]],
    geometry: snapshot_energy.Geometry,
    retained_root: Path,
    native_validation: Mapping[str, Any],
    refined_geometry: Mapping[int, Mapping[str, Any]],
    refinement_factor: int,
    region_statistics: Mapping[tuple[str, str], RegionStats],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: dict[str, Any] = {}
    budgets: list[dict[str, Any]] = []
    z_edges = renderer.centres_to_edges(geometry.z_kpc)
    for view, bundle in accumulators.items():
        maps = bundle["maps"]
        horizontal = bundle["horizontal"]
        horizontal_edges = bundle["horizontal_edges"]
        area = np.diff(z_edges)[:, None] * np.diff(horizontal_edges)[None, :]
        view_checks: dict[str, Any] = {
            "projection_method": bundle["method"],
            "path_partition": {
                "whole": closure_check(
                    f"{view}deg whole path",
                    maps["path_whole_kpc"],
                    maps["path_cocoon_kpc"] + maps["path_ambient_total_kpc"],
                ),
                "ambient": closure_check(
                    f"{view}deg ambient path",
                    maps["path_ambient_total_kpc"],
                    maps["path_shocked_ambient_kpc"] + maps["path_unshocked_ambient_kpc"],
                ),
            },
            "brightness_partition": {},
            "native_volume_recovery": {},
            "cell_volume_recovery": {},
            "emission_integral_recovery": {},
            "retained_reproduction": {},
            "tracer_support": {},
            "geometry_estimators": {},
        }
        for state in STATES:
            for convention in CONVENTIONS:
                component_sum = sum(
                    (maps[f"brightness_{region}_{state}_{convention}"] for region in REGIONS),
                    np.zeros_like(maps["path_whole_kpc"]),
                )
                view_checks["brightness_partition"][f"{state}_{convention}"] = closure_check(
                    f"{view}deg {state} {convention} brightness",
                    maps[f"brightness_whole_{state}_{convention}"],
                    component_sum,
                )

        retained = retained_view(retained_root, view)
        retained_horizontal = np.loadtxt(retained / ("x_kpc.tsv" if view == 0 else "u_kpc.tsv"))
        retained_z = np.loadtxt(retained / "z_kpc.tsv")
        text_comparison(f"{view}deg horizontal axis", horizontal, retained_horizontal)
        text_comparison(f"{view}deg z axis", geometry.z_kpc, retained_z)
        retained_brightness = np.loadtxt(
            retained / "xray_1kev_xraise_corrected_mjy_sr.tsv", delimiter="\t"
        )
        retained_tracer = np.loadtxt(retained / "tracer_max_los.tsv", delimiter="\t")
        view_checks["retained_reproduction"]["whole_current_retained_linear"] = text_comparison(
            f"{view}deg whole current retained map",
            maps["brightness_whole_current_retained_linear"],
            retained_brightness,
        )
        view_checks["retained_reproduction"]["tracer_max"] = text_comparison(
            f"{view}deg retained tracer", maps["tracer_max"], retained_tracer
        )
        metadata = json.loads((retained / "xraise_grid_smoke_metadata.json").read_text())
        if metadata.get("projection", {}).get("projected_accumulation") != bundle["method"]:
            raise ValueError(f"retained {view}deg projection method mismatch")

        native_support = maps["path_cocoon_kpc"] > 0
        retained_support = retained_tracer > TRACER_THRESHOLD
        mismatch = native_support != retained_support
        serialization_bounded = mismatch & (
            np.isclose(retained_tracer, TRACER_THRESHOLD, rtol=0, atol=5.1e-13)
            | np.isclose(maps["tracer_max"], TRACER_THRESHOLD, rtol=0, atol=5.1e-11)
        )
        unexplained = mismatch & ~serialization_bounded
        view_checks["tracer_support"] = {
            "mismatch_pixel_count": int(np.count_nonzero(mismatch)),
            "mismatch_area_kpc2": float(np.sum(area[mismatch])),
            "serialization_bounded_pixel_count": int(np.count_nonzero(serialization_bounded)),
            "serialization_bounded_area_kpc2": float(np.sum(area[serialization_bounded])),
            "unexplained_pixel_count": int(np.count_nonzero(unexplained)),
            "unexplained_area_kpc2": float(np.sum(area[unexplained])),
            "mismatch_max_abs_from_threshold": (
                float(np.max(np.abs(retained_tracer[mismatch] - TRACER_THRESHOLD)))
                if np.any(mismatch) else 0.0
            ),
        }
        if np.any(unexplained):
            raise ValueError(f"{view}deg retained/native tracer support mismatch is unexplained")

        zz = np.broadcast_to(geometry.z_kpc[:, None], maps["path_whole_kpc"].shape)
        uu = np.broadcast_to(horizontal[None, :], maps["path_whole_kpc"].shape)
        aperture = uu * uu + zz * zz <= 120.0**2
        for side in SIDES:
            side_rows = side_selector(geometry.z_kpc, side)
            expected_volumes = {
                "whole": region_statistics[("whole", side)].volume_kpc3,
                "cocoon": region_statistics[("cocoon", side)].volume_kpc3,
                "ambient_total": (
                    region_statistics[("shocked_ambient", side)].volume_kpc3
                    + region_statistics[("unshocked_ambient", side)].volume_kpc3
                ),
                "shocked_ambient": region_statistics[("shocked_ambient", side)].volume_kpc3,
                "unshocked_ambient": region_statistics[("unshocked_ambient", side)].volume_kpc3,
            }
            for region, expected_volume in expected_volumes.items():
                projected_volume = validate_projected_integral(
                    f"{view}deg {side} {region} cell-volume integral",
                    maps[f"path_{region}_kpc"],
                    area,
                    side_rows,
                    expected_volume,
                )
                view_checks["cell_volume_recovery"][f"{side}_{region}"] = {
                    "projected_path_area_kpc3": projected_volume,
                    "cell_volume_kpc3": expected_volume,
                    "residual_kpc3": projected_volume - expected_volume,
                }
            for region, native_key in (
                ("cocoon", "cocoon_volume_kpc3"),
                ("shocked_ambient", "shock_volume_kpc3"),
            ):
                projected = float(np.sum(maps[f"path_{region}_kpc"][side_rows] * area[side_rows]))
                native = float(native_validation["sides"][side][native_key])
                view_checks["native_volume_recovery"][f"{side}_{region}"] = {
                    "projected_kpc3": projected,
                    "native_kpc3": native,
                    "difference_kpc3": projected - native,
                }
                assert_close(
                    f"{view}deg {side} {region} projected volume",
                    projected,
                    native,
                    rtol=3e-11,
                    atol=2e-7,
                )
            for region in (*REGIONS, "whole"):
                for state in STATES:
                    for convention in CONVENTIONS:
                        cell_emission = region_statistics[(region, side)].emission[
                            f"{state}_{convention}"
                        ]["signed"]
                        projected_emission = validate_projected_integral(
                            f"{view}deg {side} {region} {state} {convention} emission integral",
                            maps[f"brightness_{region}_{state}_{convention}"],
                            area,
                            side_rows,
                            cell_emission,
                        )
                        key = f"{side}_{region}_{state}_{convention}"
                        view_checks["emission_integral_recovery"][key] = {
                            "projected_map_area_integral_mjy_sr_kpc2": projected_emission,
                            "cell_emissivity_volume_integral_mjy_sr_kpc2": cell_emission,
                            "residual_mjy_sr_kpc2": projected_emission - cell_emission,
                        }
            footprint = (maps["path_cocoon_kpc"] > 0) & side_rows[:, None]
            estimators = exact_abs_u_moments(footprint, horizontal_edges, z_edges)
            estimators.update(ellipse_volumes(footprint, horizontal, geometry.z_kpc))
            path_fraction = np.divide(
                maps["path_cocoon_kpc"],
                maps["path_whole_kpc"],
                out=np.zeros_like(maps["path_cocoon_kpc"]),
                where=maps["path_whole_kpc"] > 0,
            )
            estimators["minimum_los_cocoon_path_fraction_sensitivity"] = {}
            for threshold in (1e-6, 0.01, 0.5):
                threshold_mask = (path_fraction >= threshold) & side_rows[:, None]
                sensitivity = exact_abs_u_moments(threshold_mask, horizontal_edges, z_edges)
                sensitivity["support_area_kpc2"] = float(np.sum(area[threshold_mask]))
                estimators["minimum_los_cocoon_path_fraction_sensitivity"][
                    f"minimum_fraction_{threshold:g}"
                ] = sensitivity
            if view == 0:
                estimators["bin_refinement"] = {
                    "status": "not_applicable_direct_native_x_axis",
                    "factor": refinement_factor,
                }
            else:
                refined = refined_geometry[view]
                refined_path = refined["maps"]["path_cocoon_kpc"]
                refined_edges = refined["horizontal_edges"]
                refined_area = np.diff(z_edges)[:, None] * np.diff(refined_edges)[None, :]
                refined_footprint = (refined_path > 0) & side_rows[:, None]
                refined_values = exact_abs_u_moments(refined_footprint, refined_edges, z_edges)
                refined_values.update(
                    ellipse_volumes(refined_footprint, refined["horizontal"], geometry.z_kpc)
                )
                refined_values["support_area_kpc2"] = float(np.sum(refined_area[refined_footprint]))
                refined_values["projected_cocoon_volume_kpc3"] = float(
                    np.sum(refined_path[side_rows] * refined_area[side_rows])
                )
                assert_close(
                    f"{view}deg refined {side} cocoon projected volume",
                    refined_values["projected_cocoon_volume_kpc3"],
                    float(native_validation["sides"][side]["cocoon_volume_kpc3"]),
                    rtol=3e-11,
                    atol=2e-7,
                )
                estimators["bin_refinement"] = {
                    "status": "evaluated",
                    "factor": refinement_factor,
                    "refined": refined_values,
                }
            view_checks["geometry_estimators"][side] = estimators
            supports = {
                "cocoon_footprint": footprint,
                "cocoon_footprint_within_120kpc": footprint & aperture,
                "full_120kpc_aperture": side_rows[:, None] & aperture,
            }
            for support_name, support in supports.items():
                for convention in CONVENTIONS:
                    deltas = {
                        region: maps[f"brightness_{region}_current_{convention}"]
                        - maps[f"brightness_{region}_initial_{convention}"]
                        for region in REGIONS
                    }
                    dcoc = float(np.sum(np.maximum(-deltas["cocoon"], 0)[support] * area[support]))
                    esh = float(np.sum(np.maximum(deltas["shocked_ambient"], 0)[support] * area[support]))
                    shock_net = float(np.sum(deltas["shocked_ambient"][support] * area[support]))
                    for region, delta in deltas.items():
                        budgets.append({
                            "case": case,
                            "snapshot_index": SNAPSHOT_INDEX,
                            "view_deg": view,
                            "side": side,
                            "support": support_name,
                            "convention": convention,
                            "region": region,
                            "signed_change_mjy_sr_kpc2": float(np.sum(delta[support] * area[support])),
                            "positive_change_mjy_sr_kpc2": float(
                                np.sum(np.maximum(delta, 0)[support] * area[support])
                            ),
                            "negative_change_mjy_sr_kpc2": float(
                                np.sum(np.minimum(delta, 0)[support] * area[support])
                            ),
                            "D_coc_mjy_sr_kpc2": dcoc,
                            "E_sh_mjy_sr_kpc2": esh,
                            "E_sh_over_D_coc": esh / dcoc if dcoc > 0 else None,
                            "shock_net_over_D_coc": shock_net / dcoc if dcoc > 0 else None,
                        })
        checks[f"{view}deg"] = view_checks
    return checks, budgets


def summary_partition_checks(
    statistics: Mapping[tuple[str, str], RegionStats],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for side in SIDES:
        whole = statistics[("whole", side)]
        components = [statistics[(region, side)] for region in REGIONS]
        side_checks: dict[str, Any] = {}
        if whole.cell_count != sum(item.cell_count for item in components):
            raise ValueError(f"{side} regional cell-count partition failed")
        side_checks["cell_count"] = whole.cell_count
        for field_name in (
            "volume_kpc3",
            "current_mass_g",
            "initial_mass_g",
            "mass_delta_positive_g",
            "mass_delta_negative_g",
        ):
            actual = getattr(whole, field_name)
            expected = sum(getattr(item, field_name) for item in components)
            assert_close(
                f"{side} regional {field_name} partition",
                actual,
                expected,
                rtol=3e-12,
                atol=1e-9,
            )
            side_checks[field_name] = {
                "whole": actual,
                "component_sum": expected,
                "residual": actual - expected,
            }
        mass_delta_net = whole.current_mass_g - whole.initial_mass_g
        assert_close(
            f"{side} whole cellwise signed mass-change partition",
            whole.mass_delta_positive_g + whole.mass_delta_negative_g,
            mass_delta_net,
            rtol=3e-12,
            atol=1e-9,
        )
        side_checks["mass_delta_net_g"] = {
            "current_minus_initial": mass_delta_net,
            "positive_plus_negative": whole.mass_delta_positive_g + whole.mass_delta_negative_g,
        }
        for state in STATES:
            for convention in CONVENTIONS:
                key = f"{state}_{convention}"
                actual = whole.emission[key]["signed"]
                expected = sum(item.emission[key]["signed"] for item in components)
                assert_close(
                    f"{side} regional {key} cell-emission partition",
                    actual,
                    expected,
                    rtol=3e-12,
                    atol=1e-9,
                )
                side_checks[f"{key}_emission"] = {
                    "whole": actual,
                    "component_sum": expected,
                    "residual": actual - expected,
                }
        result[side] = side_checks
    return result


def validate_native_mass_anchors(
    statistics: Mapping[tuple[str, str], RegionStats],
    native_reference: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for side in SIDES:
        cocoon = statistics[("cocoon", side)]
        shocked = statistics[("shocked_ambient", side)]
        unshocked = statistics[("unshocked_ambient", side)]
        whole = statistics[("whole", side)]
        anchors = {
            "cocoon_current_mass_g": (
                cocoon.current_mass_g,
                float(native_reference[side]["lobe_mass_g"]),
            ),
            "cocoon_initial_through_current_mask_mass_g": (
                cocoon.initial_mass_g,
                float(native_reference[side]["masked_initial_lobe_mass_g"]),
            ),
            "whole_current_mass_g": (
                whole.current_mass_g,
                float(native_reference[side]["current_mass_g"]),
            ),
            "whole_initial_mass_g": (
                whole.initial_mass_g,
                float(native_reference[side]["initial_mass_g"]),
            ),
            "ambient_current_mass_g": (
                shocked.current_mass_g + unshocked.current_mass_g,
                float(native_reference[side]["gas_mass_g"]),
            ),
        }
        side_result: dict[str, Any] = {}
        for name, (actual, reference) in anchors.items():
            assert_close(
                f"{side} {name}", actual, reference, rtol=3e-12, atol=1e20
            )
            side_result[name] = {
                "actual": actual,
                "reference": reference,
                "residual": actual - reference,
            }
        result[side] = side_result
    return result


def npz_payload(bundle: Mapping[str, Any], geometry: snapshot_energy.Geometry) -> dict[str, np.ndarray]:
    maps = bundle["maps"]
    payload: dict[str, np.ndarray] = {
        "horizontal_kpc": bundle["horizontal"],
        "horizontal_edges_kpc": bundle["horizontal_edges"],
        "z_kpc": geometry.z_kpc,
        "z_edges_kpc": renderer.centres_to_edges(geometry.z_kpc),
        "shock_quantitative_bilateral": np.asarray(True),
    }
    payload.update(maps)
    for state in STATES:
        for convention in CONVENTIONS:
            for region in (*REGIONS, "whole"):
                numerator = maps[f"temperature_numerator_{region}_{state}_{convention}"]
                denominator = maps[f"brightness_{region}_{state}_{convention}"]
                payload[f"temperature_{region}_{state}_{convention}_k"] = np.divide(
                    numerator,
                    denominator,
                    out=np.full_like(numerator, np.nan),
                    where=denominator > 0,
                )
            for region in (*REGIONS, "whole"):
                payload[f"brightness_{region}_delta_{convention}"] = (
                    maps[f"brightness_{region}_current_{convention}"]
                    - maps[f"brightness_{region}_initial_{convention}"]
                )
    return payload


def run_case(args: argparse.Namespace) -> dict[str, Any]:
    if args.case not in {"C-HI", "G-HI"}:
        raise ValueError("the authorised pilot contains only C-HI and G-HI")
    if args.snapshot_index != SNAPSHOT_INDEX:
        raise ValueError("the authorised pilot is fixed to snapshot 40")
    if args.output_dir.exists():
        raise ValueError(f"refusing to overwrite output directory: {args.output_dir}")
    if args.cache_dir.exists():
        raise ValueError(f"refusing to overwrite cache directory: {args.cache_dir}")
    if args.projected_u_bins < 2 or args.y_chunk < 1:
        raise ValueError("projection bins and y chunk must be positive")
    if args.geometry_refinement_factor < 2:
        raise ValueError("geometry refinement factor must be at least two")

    compact_inputs = (
        args.source_manifest,
        args.shock_dynamics,
        args.control_calibration,
        args.native_energy_reference,
        args.native_shock_reference,
        args.tracer_precision_reference,
        args.xraise_py,
        args.apec_table,
        args.gaunt_lut,
    )
    for path in compact_inputs:
        if not path.is_file():
            raise ValueError(f"required input does not exist: {path}")
    source_manifest_sha_before_read = sha256_file(args.source_manifest)
    source = select_source(args.source_manifest, args.case)
    shape = parse_shape(source["shape_nz_ny_nx"])
    if shape == (1014, 960, 960) and (args.projected_u_bins != 960 or args.y_chunk != 8):
        raise ValueError("native production requires projected-u-bins=960 and y-chunk=8")
    original_current = source["input_h5"]
    original_baseline = source["baseline_h5"]
    current_path = Path(original_current)
    baseline_path = Path(original_baseline)
    if not current_path.is_file() or not baseline_path.is_file():
        raise ValueError(
            "manifest native input unavailable after explicit path mapping: "
            f"current={current_path} baseline={baseline_path}"
        )
    retained_dirs = {view: retained_view(args.retained_views_root, view) for view in VIEWS}
    science_code_paths = (
        Path(__file__).resolve(),
        Path(native_shock.__file__).resolve(),
        Path(snapshot_shock_energy.__file__).resolve(),
        Path(snapshot_energy.__file__).resolve(),
        Path(pluto.__file__).resolve(),
        Path(renderer.__file__).resolve(),
        (SCIENCE_DIR / "xray_cavity_method_ladder.py").resolve(),
        (SCIENCE_DIR / "three_case_cavity_recovery.py").resolve(),
    )
    retained_inputs: list[Path] = []
    for view, directory in retained_dirs.items():
        retained_inputs.extend(
            (
                directory / ("x_kpc.tsv" if view == 0 else "u_kpc.tsv"),
                directory / "z_kpc.tsv",
                directory / "xray_1kev_xraise_corrected_mjy_sr.tsv",
                directory / "tracer_max_los.tsv",
                directory / "xraise_grid_smoke_metadata.json",
            )
        )
    input_state_before = capture_input_state(
        native_paths=(current_path, baseline_path),
        hashed_paths=(*compact_inputs, *retained_inputs, *science_code_paths),
    )
    if input_state_before["compact_sha256"][str(args.source_manifest)] != source_manifest_sha_before_read:
        raise ValueError("source manifest changed while selecting snapshot 40")
    retained_metadata_validation = validate_retained_metadata(
        retained_dirs=retained_dirs,
        source=source,
        original_current_path=original_current,
        shape=shape,
        projected_u_bins=args.projected_u_bins,
        y_chunk=args.y_chunk,
        frequency_hz=args.frequency_hz,
        redshift=args.redshift,
    )
    native_reference, shock_reference, precision_reference = reference_rows(
        args.case,
        source,
        args.native_energy_reference,
        args.native_shock_reference,
        args.tracer_precision_reference,
    )
    thresholds, calibration_row = native_shock._load_thresholds(args.control_calibration)
    calibration_validation = validate_calibration_bindings(
        case=args.case,
        calibration_path=args.control_calibration,
        thresholds=thresholds,
        calibration_row=calibration_row,
        shock_reference=shock_reference,
    )
    fronts = validated_front_rows(
        args.shock_dynamics, case=args.case, source=source
    )

    args.cache_dir.mkdir(parents=True)
    geometry, current_time = lightweight_geometry(
        baseline_path,
        source["baseline_timestep"],
        current_path,
        source["timestep"],
        shape,
        args.cache_dir,
    )
    assert_close(
        "HDF5/source time code",
        current_time,
        float(source["actual_time_code"]),
        rtol=0,
        atol=1e-8,
    )
    ratio_cache = native_shock._create_ratio_cache(
        baseline_h5_path=baseline_path,
        baseline_timestep=source["baseline_timestep"],
        target_h5_path=current_path,
        target_timestep=source["timestep"],
        shape=shape,
        cache_root=args.cache_dir / "ratios_and_masks",
    )
    masks, diagnostics = native_shock._build_masks(
        ratio_cache=ratio_cache,
        geometry=geometry,
        thresholds=thresholds,
        front_rows=fronts,
        cache_root=args.cache_dir / "ratios_and_masks",
    )
    shock_mask = masks[1.0]
    native_validation = validate_native_masks(
        geometry=geometry,
        shock_mask=shock_mask,
        diagnostics=diagnostics,
        native_reference=native_reference,
        shock_reference=shock_reference,
        current_path=current_path,
        current_timestep=source["timestep"],
        precision_reference=precision_reference,
    )

    xraise = renderer.load_module(args.xraise_py)
    tables = load_tables(args.apec_table, args.gaunt_lut)
    accumulators = make_map_accumulators(geometry, args.projected_u_bins)
    refined_geometry = make_refined_geometry_accumulators(
        geometry, args.projected_u_bins, args.geometry_refinement_factor
    )
    statistics = {
        (region, side): RegionStats()
        for region in (*REGIONS, "whole") for side in SIDES
    }
    with h5py.File(baseline_path, "r") as baseline, h5py.File(current_path, "r") as current:
        baseline_vars = baseline[f"/{source['baseline_timestep']}/vars"]
        current_vars = current[f"/{source['timestep']}/vars"]
        for start in range(0, shape[1], args.y_chunk):
            stop = min(start + args.y_chunk, shape[1])
            density = {
                "current": np.asarray(current_vars["rho"][:, start:stop, :], dtype=np.float64),
                "initial": np.asarray(baseline_vars["rho"][:, start:stop, :], dtype=np.float64),
            }
            pressure = {
                "current": np.asarray(current_vars["prs"][:, start:stop, :], dtype=np.float64),
                "initial": np.asarray(baseline_vars["prs"][:, start:stop, :], dtype=np.float64),
            }
            tracer = np.asarray(current_vars["tr1"][:, start:stop, :], dtype=np.float64)
            if not np.all(np.isfinite(tracer)):
                raise ValueError(f"non-finite tracer in y rows {start}:{stop}")
            if any(
                not np.all(np.isfinite(array)) or np.any(array <= 0)
                for array in (*density.values(), *pressure.values())
            ):
                raise ValueError(f"invalid density/pressure in y rows {start}:{stop}")
            cocoon = tracer > TRACER_THRESHOLD
            ambient = ~cocoon
            shocked = np.asarray(shock_mask[:, start:stop, :], dtype=bool)
            if np.any(shocked & cocoon):
                raise ValueError("Q-029 shocked-ambient mask overlaps strict cocoon mask")
            unshocked = ambient & ~shocked
            region_masks = {
                "cocoon": cocoon,
                "shocked_ambient": shocked,
                "unshocked_ambient": unshocked,
                "whole": np.ones_like(cocoon),
            }
            emissivity: dict[str, dict[str, np.ndarray]] = {}
            temperature: dict[str, np.ndarray] = {}
            flags: dict[str, dict[str, np.ndarray]] = {}
            for state in STATES:
                emissivity[state], temperature[state], flags[state] = cell_emissivity(
                    xraise=xraise,
                    tables=tables,
                    rho_code=density[state],
                    pressure_code=pressure[state],
                    frequency_hz=args.frequency_hz,
                    redshift=args.redshift,
                )
            volume = (
                geometry.dz_kpc[:, None, None]
                * geometry.dy_kpc[None, start:stop, None]
                * geometry.dx_kpc[None, None, :]
            )
            for region, mask in region_masks.items():
                for side in SIDES:
                    statistics[(region, side)].add(
                        mask=mask & side_selector(geometry.z_kpc, side)[:, None, None],
                        volume=volume,
                        rho=density,
                        temperature=temperature,
                        emissivity=emissivity,
                        flags=flags,
                    )
            projected_fields: dict[str, np.ndarray] = {
                "path_whole_kpc": np.ones_like(tracer),
                "path_cocoon_kpc": cocoon,
                "path_ambient_total_kpc": ambient,
                "path_shocked_ambient_kpc": shocked,
                "path_unshocked_ambient_kpc": unshocked,
            }
            for state in STATES:
                for convention in CONVENTIONS:
                    for region, mask in region_masks.items():
                        corrected = emissivity[state][convention]
                        projected_fields[f"brightness_{region}_{state}_{convention}"] = corrected * mask
                        projected_fields[f"temperature_numerator_{region}_{state}_{convention}"] = (
                            corrected * temperature[state] * mask
                        )
            project_chunk(
                accumulators=accumulators,
                geometry=geometry,
                start=start,
                stop=stop,
                fields=projected_fields,
                tracer=tracer,
            )
            project_chunk(
                accumulators=refined_geometry,
                geometry=geometry,
                start=start,
                stop=stop,
                fields={"path_cocoon_kpc": cocoon},
                tracer=tracer,
            )

    regional_partition_validation = summary_partition_checks(statistics)
    native_mass_validation = validate_native_mass_anchors(statistics, native_reference)
    validation, budgets = map_checks_and_budgets(
        case=args.case,
        accumulators=accumulators,
        geometry=geometry,
        retained_root=args.retained_views_root,
        native_validation=native_validation,
        refined_geometry=refined_geometry,
        refinement_factor=args.geometry_refinement_factor,
        region_statistics=statistics,
    )
    input_state_after = verify_input_state(
        input_state_before,
        native_paths=(current_path, baseline_path),
        hashed_paths=(*compact_inputs, *retained_inputs, *science_code_paths),
    )
    summary_rows = [
        statistics[(region, side)].output_row(args.case, region, side)
        for region in (*REGIONS, "whole") for side in SIDES
    ]
    distributions = [
        statistics[(region, side)].distributions(args.case, region, side)
        for region in (*REGIONS, "whole") for side in SIDES
    ]
    whole_stats = statistics[("whole", "bipolar_total")]
    raw_nonfinite_total = sum(whole_stats.raw_kernel_nonfinite_cell_count.values())
    corrected_nonfinite_total = sum(
        int(whole_stats.emission[f"{state}_{convention}"]["nonfinite_cell_count"])
        for state in STATES for convention in CONVENTIONS
    )
    out_of_range_total = sum(whole_stats.oor_cell_count.values())
    finite_negative_retained_total = sum(
        int(whole_stats.emission[f"{state}_retained_linear"]["negative_cell_count"])
        for state in STATES
    )
    validation_scope = (
        "source-bound extraction, Q-029 mask reproduction, projection and partition closure, "
        "and output integrity; not physical emissivity acceptance"
    )
    if raw_nonfinite_total or corrected_nonfinite_total:
        scientific_interpretation_status = "not_supported_until_nonfinite_materiality_review"
    else:
        scientific_interpretation_status = "pending_emissivity_diagnostic_review"
    scientific_interpretation_flags = {
        "raw_kernel_nonfinite_sanitized": raw_nonfinite_total > 0,
        "corrected_nonfinite_sanitized": corrected_nonfinite_total > 0,
        "finite_negative_retained_linear": finite_negative_retained_total > 0,
        "out_of_table_domain": out_of_range_total > 0,
    }
    interpretation_diagnostics = {
        "raw_kernel_nonfinite_cell_count_initial_plus_current": raw_nonfinite_total,
        "corrected_nonfinite_cell_count_all_states_and_conventions": corrected_nonfinite_total,
        "table_out_of_range_cell_count_initial_plus_current": out_of_range_total,
        "finite_negative_retained_linear_cell_count_initial_plus_current": (
            finite_negative_retained_total
        ),
        "finite_negative_retained_emissivity_preserved": True,
        "nonfinite_renderer_values_sanitized_only_after_reporting": True,
        "clamp_is_sensitivity_not_uncertainty_bound": True,
    }
    summary = {
        "status": "validated",
        "validation_scope": validation_scope,
        "scientific_interpretation_status": scientific_interpretation_status,
        "scientific_interpretation_flags": scientific_interpretation_flags,
        "interpretation_diagnostics": interpretation_diagnostics,
        "case": args.case,
        "snapshot_index": SNAPSHOT_INDEX,
        "views": list(VIEWS),
        "conventions": list(CONVENTIONS),
        "shock_validity": "quantitative_bilateral",
        "native_validation": native_validation,
        "calibration_validation": calibration_validation,
        "retained_metadata_validation": retained_metadata_validation,
        "validation_diagnostics": validation,
        "regional_partition_validation": regional_partition_validation,
        "native_mass_validation": native_mass_validation,
        "declared_side_view_budgets": budgets,
        "summary_rows": summary_rows,
        "density_temperature_distributions": distributions,
        "table_bounds": {
            "apec_temperature_kev": tables.apec_temp_bounds_kev,
            "apec_redshift": tables.apec_redshift_bounds,
            "gaunt_temperature_k": tables.gaunt_temp_bounds_k,
            "gaunt_frequency_hz": tables.gaunt_frequency_bounds_hz,
        },
        "units": UNITS,
    }

    args.output_dir.mkdir()
    for view, bundle in accumulators.items():
        np.savez_compressed(
            args.output_dir / f"native_emission_{view}deg.npz",
            **npz_payload(bundle, geometry),
        )
    write_rows(args.output_dir / "summary.csv", summary_rows)
    write_json(args.output_dir / "summary.json", summary)
    provenance = {
        "status": "validated",
        "validation_scope": validation_scope,
        "scientific_interpretation_status": scientific_interpretation_status,
        "scientific_interpretation_flags": scientific_interpretation_flags,
        "interpretation_diagnostics": interpretation_diagnostics,
        "case": args.case,
        "snapshot_index": SNAPSHOT_INDEX,
        "views": list(VIEWS),
        "conventions": list(CONVENTIONS),
        "validation_diagnostics": validation,
        "regional_partition_validation": regional_partition_validation,
        "native_mass_validation": native_mass_validation,
        "retained_metadata_validation": retained_metadata_validation,
        "source_manifest_row": source,
        "source_resolution": {
            "current_identity": original_current,
            "current_resolved": str(current_path.resolve()),
            "baseline_identity": original_baseline,
            "baseline_resolved": str(baseline_path.resolve()),
        },
        "native_hdf5": {
            "current_size_bytes": current_path.stat().st_size,
            "current_mtime_ns": current_path.stat().st_mtime_ns,
            "baseline_size_bytes": baseline_path.stat().st_size,
            "baseline_mtime_ns": baseline_path.stat().st_mtime_ns,
            "current_time_code": current_time,
            "pre_read_identities": {
                "current": input_state_before["native_stat_identity"][str(current_path)],
                "baseline": input_state_before["native_stat_identity"][str(baseline_path)],
            },
            "post_read_identities": {
                "current": input_state_after["native_stat_identity"][str(current_path)],
                "baseline": input_state_after["native_stat_identity"][str(baseline_path)],
            },
        },
        "input_stability": {
            "verified_unchanged": True,
            "before": input_state_before,
            "after": input_state_after,
        },
        "compact_input_sha256": input_state_before["compact_sha256"],
        "science_code_sha256": {
            str(path): input_state_before["compact_sha256"][str(path)]
            for path in science_code_paths
        },
        "retained_views": {
            f"{view}deg": {
                "root": str(retained_dirs[view]),
                "metadata_sha256": sha256_file(retained_dirs[view] / "xraise_grid_smoke_metadata.json"),
                "corrected_map_sha256": sha256_file(
                    retained_dirs[view] / "xray_1kev_xraise_corrected_mjy_sr.tsv"
                ),
                "tracer_map_sha256": sha256_file(retained_dirs[view] / "tracer_max_los.tsv"),
            }
            for view in VIEWS
        },
        "definitions": {
            "cocoon": "float64(stored tr1) > 1e-3, full native cells",
            "ambient_total": "exact valid-fluid complement: float64(stored tr1) <= 1e-3",
            "shocked_ambient": "frozen Q-029 factor-one quantitative seeded component",
            "unshocked_ambient": "ambient_total minus shocked_ambient",
            "baseline": "case-specific timestep zero through current Eulerian region masks",
            "retained_linear": "renderer linear extrapolation with finite negatives preserved",
            "clamp_each_coordinate": "each APEC/Gaunt coordinate clamped to its own bounds",
        },
        "projection": {
            "projected_u_bins": args.projected_u_bins,
            "y_chunk": args.y_chunk,
            "methods": {f"{view}deg": accumulators[view]["method"] for view in VIEWS},
            "global_y_edges_per_chunk": True,
            "geometry_refinement_factor": args.geometry_refinement_factor,
        },
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "units": UNITS,
        "calibration_row": calibration_row,
        "calibration_validation": calibration_validation,
        "front_rows": fronts,
        "mask_diagnostics_factor_one": {
            side: diagnostics[(1.0, side)] for side in ("negative_z", "positive_z")
        },
        "cache_removed_after_manifest": not args.keep_cache,
    }
    write_json(args.output_dir / "provenance.json", provenance)
    exact_outputs = [
        args.output_dir / "native_emission_0deg.npz",
        args.output_dir / "native_emission_45deg.npz",
        args.output_dir / "native_emission_90deg.npz",
        args.output_dir / "summary.csv",
        args.output_dir / "summary.json",
        args.output_dir / "provenance.json",
    ]
    manifest = "".join(f"{sha256_file(path)}  {path.name}\n" for path in exact_outputs)
    (args.output_dir / "manifest.sha256").write_text(manifest)
    if not args.keep_cache:
        shutil.rmtree(args.cache_dir)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=("C-HI", "G-HI"))
    parser.add_argument("--snapshot-index", type=int, default=SNAPSHOT_INDEX)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--shock-dynamics", type=Path, required=True)
    parser.add_argument("--control-calibration", type=Path, required=True)
    parser.add_argument("--native-energy-reference", type=Path, required=True)
    parser.add_argument("--native-shock-reference", type=Path, required=True)
    parser.add_argument("--tracer-precision-reference", type=Path, required=True)
    parser.add_argument("--retained-views-root", type=Path, required=True)
    parser.add_argument("--xraise-py", type=Path, required=True)
    parser.add_argument("--apec-table", type=Path, required=True)
    parser.add_argument("--gaunt-lut", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--projected-u-bins", type=int, default=960)
    parser.add_argument("--y-chunk", type=int, default=8)
    parser.add_argument("--geometry-refinement-factor", type=int, default=2)
    parser.add_argument("--frequency-hz", type=float, default=renderer.DEFAULT_FREQ_HZ)
    parser.add_argument("--redshift", type=float, default=0.05)
    parser.add_argument("--keep-cache", action="store_true")
    return parser


def main() -> None:
    result = run_case(build_parser().parse_args())
    print(f"status={result['status']} case={result['case']}")


if __name__ == "__main__":
    main()
