#!/usr/bin/env python3
"""Build no-jet-calibrated selected-age native 3D shock-energy products."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from pluto_h5_level3_ambient_extract import (
    UNIT_ENERGY_ERG,
    derive_widths,
    read_and_validate_axes,
    read_axis,
    require_datasets,
)
from snapshot_energy import (
    Geometry,
    build_geometry,
    injected_energy,
    load_environment,
    write_json,
    write_rows,
)
from snapshot_shock_energy import (
    AMBIENT_TRACER_MAX,
    MIN_SELECTED_CELLS,
    THRESHOLD_FACTORS,
    ShockThresholds,
    add_shock_energy,
    build_processed_and_front_masks,
    derive_control_thresholds,
    empty_shock_energy,
    entropy_excess,
    select_seeded_components,
    shock_energy_slice,
)


FRONT_SEED_RADIUS_KPC = 4.0
FRONT_SEED_HALF_WIDTH_KPC = 5.0
FRONT_MATCH_TOLERANCE_KPC = 10.0
CONTROL_SAMPLE_STRIDE = 4
SIDES = ("negative_z", "positive_z")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"invalid CSV schema: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _single_timestep(path: Path) -> tuple[str, float, tuple[int, int, int]]:
    with h5py.File(path, "r") as h5:
        groups = [(name, value) for name, value in h5.items() if isinstance(value, h5py.Group) and "vars" in value]
        if len(groups) != 1:
            raise ValueError(f"expected one timestep group in {path}, found {len(groups)}")
        name, group = groups[0]
        shape = require_datasets(h5, name)
        return name, float(group.attrs["Time"]), shape


def calibrate_control(
    *,
    environment: str,
    control_files: Sequence[Path],
    output_csv: Path,
    sample_stride: int = CONTROL_SAMPLE_STRIDE,
) -> dict[str, Any]:
    if output_csv.exists():
        raise ValueError(f"refusing to overwrite control calibration: {output_csv}")
    if len(control_files) < 2 or sample_stride < 1:
        raise ValueError("control calibration needs a baseline, later snapshots, and positive stride")
    inspected = [(path, *_single_timestep(path)) for path in control_files]
    inspected.sort(key=lambda item: item[2])
    baseline_path, baseline_timestep, baseline_time, baseline_shape = inspected[0]
    if abs(baseline_time) > 1.0e-8:
        raise ValueError(f"control baseline is not at zero time: {baseline_time}")
    pressure_samples: list[np.ndarray] = []
    density_samples: list[np.ndarray] = []
    entropy_samples: list[np.ndarray] = []
    with h5py.File(baseline_path, "r") as baseline_h5:
        baseline_vars = baseline_h5[f"/{baseline_timestep}/vars"]
        for path, timestep, time_code, shape in inspected[1:]:
            if shape != baseline_shape or time_code <= baseline_time:
                raise ValueError(f"control shape/time mismatch: {path}")
            with h5py.File(path, "r") as current_h5:
                read_and_validate_axes(
                    base=baseline_h5,
                    final=current_h5,
                    nz=shape[0],
                    ny=shape[1],
                    nx=shape[2],
                )
                current_vars = current_h5[f"/{timestep}/vars"]
                for iz in range(0, shape[0], sample_stride):
                    rho0 = np.asarray(
                        baseline_vars["rho"][iz, ::sample_stride, ::sample_stride], dtype=np.float64
                    )
                    pressure0 = np.asarray(
                        baseline_vars["prs"][iz, ::sample_stride, ::sample_stride], dtype=np.float64
                    )
                    rho = np.asarray(
                        current_vars["rho"][iz, ::sample_stride, ::sample_stride], dtype=np.float64
                    )
                    pressure = np.asarray(
                        current_vars["prs"][iz, ::sample_stride, ::sample_stride], dtype=np.float64
                    )
                    if np.any(rho <= 0.0) or np.any(rho0 <= 0.0) or np.any(pressure <= 0.0) or np.any(pressure0 <= 0.0):
                        raise ValueError(f"non-positive control density/pressure in {path}")
                    rho_ratio = rho / rho0
                    pressure_ratio = pressure / pressure0
                    pressure_samples.append(np.maximum(pressure_ratio - 1.0, 0.0).astype(np.float32))
                    density_samples.append(np.maximum(rho_ratio - 1.0, 0.0).astype(np.float32))
                    entropy_samples.append(
                        np.maximum(entropy_excess(pressure_ratio, rho_ratio), 0.0).astype(np.float32)
                    )
    thresholds = derive_control_thresholds(
        pressure_excess_samples=np.concatenate(pressure_samples),
        density_excess_samples=np.concatenate(density_samples),
        entropy_excess_samples=np.concatenate(entropy_samples),
    )
    source = ";".join(str(item[0]) for item in inspected)
    row = thresholds.as_row(environment=environment, source=source) | {
        "control_file_count": len(inspected),
        "control_grid_shape_nz_ny_nx": "x".join(str(value) for value in baseline_shape),
        "control_sample_stride": sample_stride,
        "control_baseline_sha256": sha256_file(baseline_path),
    }
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_rows(output_csv, [row])
    return row


def _load_thresholds(path: Path) -> tuple[ShockThresholds, dict[str, str]]:
    rows = read_rows(path)
    if len(rows) != 1:
        raise ValueError("control calibration must contain exactly one row")
    thresholds = ShockThresholds.from_row(rows[0])
    if thresholds.control_joint_exceedance_fraction > 1.0e-6:
        raise ValueError("control false-positive gate failed")
    return thresholds, rows[0]


def _front_rows(path: Path, snapshot_index: int) -> dict[str, dict[str, str]]:
    rows = [
        row
        for row in read_rows(path)
        if int(row["snapshot_index"]) == snapshot_index
        and math.isclose(float(row["velocity_threshold_factor"]), 1.0, rel_tol=0.0, abs_tol=1.0e-12)
    ]
    by_side = {row["side"]: row for row in rows}
    if set(by_side) != set(SIDES):
        raise ValueError(f"accepted shock rows missing for snapshot {snapshot_index}")
    return by_side


def _create_ratio_cache(
    *,
    baseline_h5_path: Path,
    baseline_timestep: str,
    target_h5_path: Path,
    target_timestep: str,
    shape: tuple[int, int, int],
    cache_root: Path,
) -> dict[str, np.memmap]:
    cache_root.mkdir(parents=True)
    paths = {
        "pressure_ratio": cache_root / "pressure_ratio.npy",
        "density_ratio": cache_root / "density_ratio.npy",
        "entropy": cache_root / "entropy.npy",
        "ambient": cache_root / "ambient.npy",
    }
    arrays = {
        "pressure_ratio": np.lib.format.open_memmap(paths["pressure_ratio"], mode="w+", dtype=np.float32, shape=shape),
        "density_ratio": np.lib.format.open_memmap(paths["density_ratio"], mode="w+", dtype=np.float32, shape=shape),
        "entropy": np.lib.format.open_memmap(paths["entropy"], mode="w+", dtype=np.float32, shape=shape),
        "ambient": np.lib.format.open_memmap(paths["ambient"], mode="w+", dtype=bool, shape=shape),
    }
    with h5py.File(baseline_h5_path, "r") as baseline_h5, h5py.File(target_h5_path, "r") as target_h5:
        if require_datasets(baseline_h5, baseline_timestep) != shape or require_datasets(target_h5, target_timestep) != shape:
            raise ValueError("baseline/target shape mismatch")
        read_and_validate_axes(base=baseline_h5, final=target_h5, nz=shape[0], ny=shape[1], nx=shape[2])
        baseline_vars = baseline_h5[f"/{baseline_timestep}/vars"]
        target_vars = target_h5[f"/{target_timestep}/vars"]
        for iz in range(shape[0]):
            rho0 = np.asarray(baseline_vars["rho"][iz], dtype=np.float64)
            pressure0 = np.asarray(baseline_vars["prs"][iz], dtype=np.float64)
            rho = np.asarray(target_vars["rho"][iz], dtype=np.float64)
            pressure = np.asarray(target_vars["prs"][iz], dtype=np.float64)
            tracer = np.asarray(target_vars["tr1"][iz], dtype=np.float64)
            if np.any(rho <= 0.0) or np.any(rho0 <= 0.0) or np.any(pressure <= 0.0) or np.any(pressure0 <= 0.0):
                raise ValueError(f"non-positive density/pressure at z index {iz}")
            rho_ratio = rho / rho0
            pressure_ratio = pressure / pressure0
            arrays["pressure_ratio"][iz] = pressure_ratio
            arrays["density_ratio"][iz] = rho_ratio
            arrays["entropy"][iz] = entropy_excess(pressure_ratio, rho_ratio)
            arrays["ambient"][iz] = np.clip(tracer, 0.0, 1.0) <= AMBIENT_TRACER_MAX
    for array in arrays.values():
        array.flush()
    return arrays


def _side_slice(z_kpc: np.ndarray, side: str) -> slice:
    indices = np.flatnonzero(z_kpc < 0.0 if side == "negative_z" else z_kpc > 0.0)
    if not indices.size or not np.all(np.diff(indices) == 1):
        raise ValueError(f"{side} z cells are missing or non-contiguous")
    return slice(int(indices[0]), int(indices[-1]) + 1)


def _build_masks(
    *,
    ratio_cache: Mapping[str, np.ndarray],
    geometry: Geometry,
    thresholds: ShockThresholds,
    front_rows: Mapping[str, Mapping[str, str]],
    cache_root: Path,
) -> tuple[dict[float, np.memmap], dict[tuple[float, str], dict[str, Any]]]:
    radius_xy = np.sqrt(geometry.x_kpc[None, :] ** 2 + geometry.y_kpc[:, None] ** 2)
    masks: dict[float, np.memmap] = {}
    diagnostics: dict[tuple[float, str], dict[str, Any]] = {}
    for factor in THRESHOLD_FACTORS:
        mask = np.lib.format.open_memmap(
            cache_root / f"selected_mask_{factor:g}.npy",
            mode="w+",
            dtype=bool,
            shape=ratio_cache["entropy"].shape,
        )
        mask[:] = False
        for side in SIDES:
            accepted = front_rows[side]
            common = {
                "accepted_front_kpc": accepted.get("shock_distance_kpc", ""),
                "accepted_mach_kinematic": accepted.get("mach_kinematic", ""),
                "front_seed_radius_kpc": FRONT_SEED_RADIUS_KPC,
                "front_seed_half_width_kpc": FRONT_SEED_HALF_WIDTH_KPC,
                "front_match_tolerance_kpc": FRONT_MATCH_TOLERANCE_KPC,
            }
            if accepted.get("status") != "detected" or not accepted.get("shock_distance_kpc"):
                diagnostics[(factor, side)] = common | {"status": "unresolved_no_accepted_front"}
                continue
            mach = float(accepted["mach_kinematic"]) if accepted.get("mach_kinematic") else math.nan
            if not math.isfinite(mach) or mach <= 1.0:
                diagnostics[(factor, side)] = common | {"status": "unresolved_non_supersonic_front"}
                continue
            section = _side_slice(geometry.z_kpc, side)
            processed, front = build_processed_and_front_masks(
                pressure_ratio=ratio_cache["pressure_ratio"][section],
                density_ratio=ratio_cache["density_ratio"][section],
                entropy_delta=ratio_cache["entropy"][section],
                ambient_mask=ratio_cache["ambient"][section],
                thresholds=thresholds,
                factor=factor,
            )
            front_distance = float(accepted["shock_distance_kpc"])
            z_values = geometry.z_kpc[section]
            seed_z = np.abs(np.abs(z_values) - front_distance) <= FRONT_SEED_HALF_WIDTH_KPC
            seed = front & seed_z[:, None, None] & (radius_xy[None, :, :] <= FRONT_SEED_RADIUS_KPC)
            labels_path = cache_root / f"labels_{factor:g}_{side}.npy"
            labels = np.lib.format.open_memmap(labels_path, mode="w+", dtype=np.int32, shape=processed.shape)
            selected, component = select_seeded_components(
                processed,
                seed,
                labels=labels,
                minimum_cells=MIN_SELECTED_CELLS,
            )
            del labels
            labels_path.unlink()
            status = component["status"]
            extent = ""
            offset = ""
            boundary_touch = False
            if status == "quantitative_seeded_component":
                occupied_z = np.flatnonzero(np.any(selected, axis=(1, 2)))
                extent = float(np.max(np.abs(z_values[occupied_z])))
                offset = extent - front_distance
                outer_z_index = 0 if side == "negative_z" else len(z_values) - 1
                boundary_touch = bool(
                    np.any(selected[outer_z_index])
                    or np.any(selected[:, 0, :])
                    or np.any(selected[:, -1, :])
                    or np.any(selected[:, :, 0])
                    or np.any(selected[:, :, -1])
                )
                if boundary_touch:
                    status = "unresolved_boundary_touch"
                elif abs(offset) > FRONT_MATCH_TOLERANCE_KPC:
                    status = "unresolved_front_extent_mismatch"
            if status == "quantitative_seeded_component":
                mask[section] = selected
            diagnostics[(factor, side)] = common | component | {
                "status": status,
                "front_seed_cell_count": int(np.count_nonzero(seed)),
                "selected_extent_kpc": extent,
                "front_extent_offset_kpc": offset,
                "boundary_touch": boundary_touch,
            }
            del processed, front, seed, selected
        mask.flush()
        masks[factor] = mask
    return masks, diagnostics


def _integrate_masks(
    *,
    baseline_h5_path: Path,
    baseline_timestep: str,
    target_h5_path: Path,
    target_timestep: str,
    geometry: Geometry,
    masks: Mapping[float, np.ndarray],
) -> dict[tuple[float, str], dict[str, float]]:
    totals = {(factor, side): empty_shock_energy() for factor in THRESHOLD_FACTORS for side in SIDES}
    potential = np.load(geometry.potential_path, mmap_mode="r")
    with h5py.File(baseline_h5_path, "r") as baseline_h5, h5py.File(target_h5_path, "r") as target_h5:
        baseline_vars = baseline_h5[f"/{baseline_timestep}/vars"]
        target_vars = target_h5[f"/{target_timestep}/vars"]
        for iz, z_value in enumerate(geometry.z_kpc):
            rho0 = np.asarray(baseline_vars["rho"][iz], dtype=np.float64)
            pressure0 = np.asarray(baseline_vars["prs"][iz], dtype=np.float64)
            v10 = np.asarray(baseline_vars["vx1"][iz], dtype=np.float64)
            v20 = np.asarray(baseline_vars["vx2"][iz], dtype=np.float64)
            v30 = np.asarray(baseline_vars["vx3"][iz], dtype=np.float64)
            rho = np.asarray(target_vars["rho"][iz], dtype=np.float64)
            pressure = np.asarray(target_vars["prs"][iz], dtype=np.float64)
            tracer = np.asarray(target_vars["tr1"][iz], dtype=np.float64)
            v1 = np.asarray(target_vars["vx1"][iz], dtype=np.float64)
            v2 = np.asarray(target_vars["vx2"][iz], dtype=np.float64)
            v3 = np.asarray(target_vars["vx3"][iz], dtype=np.float64)
            volume = geometry.volume_xy_kpc2 * geometry.dz_kpc[iz]
            side = "negative_z" if z_value < 0.0 else "positive_z"
            for factor, mask in masks.items():
                if not np.any(mask[iz]):
                    continue
                values = shock_energy_slice(
                    rho=rho,
                    pressure=pressure,
                    velocity_squared=v1**2 + v2**2 + v3**2,
                    tracer=tracer,
                    baseline_rho=rho0,
                    baseline_pressure=pressure0,
                    baseline_velocity_squared=v10**2 + v20**2 + v30**2,
                    volume_kpc3=volume,
                    potential_cm2_s2=potential[iz],
                    mask=mask[iz],
                )
                add_shock_energy(totals[(factor, side)], values)
    return totals


def _energy_columns(values: Mapping[str, float], injected: float) -> dict[str, Any]:
    return dict(values) | {
        "shock_fraction_of_injected": values["total_delta_erg"] / injected if injected > 0.0 else "",
        "irreversible_fraction_of_injected": (
            values["irreversible_heating_erg"] / injected if injected > 0.0 else ""
        ),
    }


def analyze_case(
    *,
    case: str,
    source_manifest: Path,
    shock_dynamics: Path,
    environment_table: Path,
    control_calibration: Path,
    output_root: Path,
) -> dict[str, Any]:
    if output_root.exists():
        raise ValueError(f"refusing to overwrite native shock output: {output_root}")
    output_root.mkdir(parents=True)
    manifest = read_rows(source_manifest)
    if {row["case"] for row in manifest} != {case}:
        raise ValueError("source manifest case mismatch")
    thresholds, control_row = _load_thresholds(control_calibration)
    environment = load_environment(environment_table)
    baseline_paths = {(row["baseline_h5"], row["baseline_timestep"]) for row in manifest}
    if len(baseline_paths) != 1:
        raise ValueError("source manifest must use one baseline")
    baseline_path_text, baseline_timestep = next(iter(baseline_paths))
    baseline_path = Path(baseline_path_text)
    first_shape = tuple(int(value) for value in manifest[0]["shape_nz_ny_nx"].split("x"))
    geometry_cache = output_root / "cache" / "phi0_cm2_s2.npy"
    geometry = build_geometry(
        baseline_h5=baseline_path,
        baseline_timestep=baseline_timestep,
        shape=first_shape,
        environment=environment,
        cache_path=geometry_cache,
    )
    rows: list[dict[str, Any]] = []
    for source in manifest:
        snapshot_index = int(source["snapshot_index"])
        shape = tuple(int(value) for value in source["shape_nz_ny_nx"].split("x"))
        if shape != first_shape:
            raise ValueError("selected-age manifest shape drift")
        snapshot_cache = output_root / "cache" / f"snapshot_{snapshot_index:04d}"
        ratio_cache = _create_ratio_cache(
            baseline_h5_path=baseline_path,
            baseline_timestep=baseline_timestep,
            target_h5_path=Path(source["input_h5"]),
            target_timestep=source["timestep"],
            shape=shape,
            cache_root=snapshot_cache,
        )
        accepted_fronts = _front_rows(shock_dynamics, snapshot_index)
        masks, diagnostics = _build_masks(
            ratio_cache=ratio_cache,
            geometry=geometry,
            thresholds=thresholds,
            front_rows=accepted_fronts,
            cache_root=snapshot_cache,
        )
        totals = _integrate_masks(
            baseline_h5_path=baseline_path,
            baseline_timestep=baseline_timestep,
            target_h5_path=Path(source["input_h5"]),
            target_timestep=source["timestep"],
            geometry=geometry,
            masks=masks,
        )
        one_sided, bipolar = injected_energy(
            float(source["actual_time_myr"]),
            one_sided_power_erg_s=float(source["jet_power_one_sided_erg_s"]),
            jet_start_myr=0.0,
            jet_active_myr=50.0,
        )
        for factor in THRESHOLD_FACTORS:
            side_rows: list[dict[str, Any]] = []
            p_cut, rho_cut, entropy_cut = thresholds.scaled(factor)
            for side in SIDES:
                diagnostic = diagnostics[(factor, side)]
                quantitative = diagnostic["status"] == "quantitative_seeded_component"
                base = {
                    "case": case,
                    "snapshot_index": snapshot_index,
                    "actual_time_myr": float(source["actual_time_myr"]),
                    "side": side,
                    "threshold_factor": factor,
                    "status": diagnostic["status"],
                    "accepted_front_kpc": diagnostic["accepted_front_kpc"],
                    "accepted_mach_kinematic": diagnostic["accepted_mach_kinematic"],
                    "pressure_excess_threshold": p_cut,
                    "density_excess_threshold": rho_cut,
                    "entropy_excess_threshold": entropy_cut,
                    "ambient_tracer_max": AMBIENT_TRACER_MAX,
                    "component_count": diagnostic.get("component_count", ""),
                    "selected_component_count": diagnostic.get("selected_component_count", ""),
                    "front_seed_cell_count": diagnostic.get("front_seed_cell_count", ""),
                    "selected_extent_kpc": diagnostic.get("selected_extent_kpc", ""),
                    "front_extent_offset_kpc": diagnostic.get("front_extent_offset_kpc", ""),
                    "boundary_touch": diagnostic.get("boundary_touch", ""),
                    "control_environment": control_row["environment"],
                    "control_role": control_row["control_role"],
                    "background_subtraction_status": "static_baseline_only_no_resolution_matched_control",
                }
                if quantitative:
                    base |= _energy_columns(totals[(factor, side)], one_sided)
                else:
                    base |= {key: "" for key in _energy_columns(empty_shock_energy(), one_sided)}
                rows.append(base)
                side_rows.append(base)
            bilateral = all(row["status"] == "quantitative_seeded_component" for row in side_rows)
            bipolar_base = dict(side_rows[0])
            bipolar_base.update({
                "side": "bipolar_total",
                "status": "quantitative_bilateral" if bilateral else "unresolved_bilateral_gate",
                "accepted_front_kpc": "",
                "accepted_mach_kinematic": (
                    sum(float(row["accepted_mach_kinematic"]) for row in side_rows) / 2.0 if bilateral else ""
                ),
                "component_count": (
                    sum(int(row["component_count"]) for row in side_rows) if bilateral else ""
                ),
                "selected_component_count": (
                    sum(int(row["selected_component_count"]) for row in side_rows) if bilateral else ""
                ),
                "front_seed_cell_count": (
                    sum(int(row["front_seed_cell_count"]) for row in side_rows) if bilateral else ""
                ),
                "selected_extent_kpc": "",
                "front_extent_offset_kpc": "",
                "boundary_touch": any(str(row["boundary_touch"]).lower() == "true" for row in side_rows),
            })
            if bilateral:
                combined = empty_shock_energy()
                add_shock_energy(combined, totals[(factor, "negative_z")])
                add_shock_energy(combined, totals[(factor, "positive_z")])
                bipolar_base |= _energy_columns(combined, bipolar)
            else:
                bipolar_base |= {key: "" for key in _energy_columns(empty_shock_energy(), bipolar)}
            rows.append(bipolar_base)
        del ratio_cache, masks
        shutil.rmtree(snapshot_cache)
        print(f"native_shock_snapshot_complete={case}/{snapshot_index}", flush=True)
    write_rows(output_root / "native_shock_energy_selected_age.csv", rows)
    shutil.copy2(source_manifest, output_root / "source_manifest.csv")
    shutil.copy2(shock_dynamics, output_root / "accepted_axial_shock_dynamics.csv")
    shutil.copy2(control_calibration, output_root / "control_threshold_calibration.csv")
    metadata = {
        "status": "complete_selected_age_native_shock_partition",
        "case": case,
        "selected_age_count": len(manifest),
        "row_count": len(rows),
        "primary_threshold_factor": 1.0,
        "threshold_factors": list(THRESHOLD_FACTORS),
        "shock_processed_mask": "ambient entropy-excess component connected to compressed axial-front seed",
        "front_validation": "accepted outward axial shock position and Mach > 1",
        "control_role": "coarse no-jet dimensionless noise calibration; not cellwise subtraction",
        "energy_reference": "same production-grid cell at t=0",
        "potential_convention": "centre-zero integral of initial static-atmosphere gravity",
        "irreversible_heating": "p - p0*(rho/rho0)^gamma within selected ambient mask",
        "boundary_status": "selected mask fails closed if it touches a physical domain face",
        "g_hi_50_status": "excluded",
    }
    write_json(output_root / "selected_age_native_shock_metadata.json", metadata)
    shutil.rmtree(output_root / "cache")
    manifest_path = output_root / "local_asset_manifest.sha256"
    manifest_path.write_text(
        "\n".join(
            f"{sha256_file(path)}  {path.name}"
            for path in sorted(output_root.iterdir())
            if path.is_file() and path != manifest_path
        )
        + "\n"
    )
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    control = subparsers.add_parser("calibrate")
    control.add_argument("--environment", required=True)
    control.add_argument("--control-file", action="append", required=True, type=Path)
    control.add_argument("--output-csv", required=True, type=Path)
    control.add_argument("--sample-stride", type=int, default=CONTROL_SAMPLE_STRIDE)
    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--case", required=True)
    analyze.add_argument("--source-manifest", required=True, type=Path)
    analyze.add_argument("--shock-dynamics", required=True, type=Path)
    analyze.add_argument("--environment-table", required=True, type=Path)
    analyze.add_argument("--control-calibration", required=True, type=Path)
    analyze.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "calibrate":
        result = calibrate_control(
            environment=args.environment,
            control_files=args.control_file,
            output_csv=args.output_csv,
            sample_stride=args.sample_stride,
        )
    else:
        result = analyze_case(
            case=args.case,
            source_manifest=args.source_manifest,
            shock_dynamics=args.shock_dynamics,
            environment_table=args.environment_table,
            control_calibration=args.control_calibration,
            output_root=args.output_root,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
