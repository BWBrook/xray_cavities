#!/usr/bin/env python3
"""Run the reusable per-snapshot fluid science contract for one PLUTO case.

This thin controller joins the cell-wise energy/potential and axial-shock
modules. X-ray/cavity and radio products retain their dedicated accepted
implementations and are joined during synthesis.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Sequence

from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import (
    ENERGY_FIELDS,
    METHOD_VERSION,
    SECONDS_PER_MYR,
    TRACER_THRESHOLDS,
    analyze_snapshot,
    build_geometry,
    canonical_snapshot_chain,
    injected_energy,
    load_environment,
    prepare_baseline,
    read_rows,
    slice_energy,
    snapshot_identity,
    tracer_partitions,
    write_json,
    write_rows,
)
from snapshot_shocks import (
    SHOCK_THRESHOLD_FACTORS,
    build_shock_rows,
    detect_shock,
    local_three_point_slope,
)

def run_chain(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    if output_root.exists() and not args.resume:
        raise ValueError(f"refusing to overwrite existing output root: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    per_snapshot = output_root / "per_snapshot"
    per_snapshot.mkdir(exist_ok=True)
    environment = load_environment(Path(args.environment_table))
    snapshots = canonical_snapshot_chain([Path(path) for path in args.outputs_dir])
    baseline = snapshots[0]
    geometry_cache = output_root / "cache" / "phi0_cm2_s2.npy"
    if geometry_cache.exists():
        geometry_cache.unlink()
    geometry = build_geometry(
        baseline_h5=baseline.input_h5,
        baseline_timestep=baseline.timestep,
        shape=baseline.shape,
        environment=environment,
        cache_path=geometry_cache,
    )
    baseline_state = prepare_baseline(
        baseline=baseline,
        geometry=geometry,
        tube_radius_kpc=args.tube_radius_kpc,
        velocity_floor_code=args.velocity_floor_code,
        velocity_noise_multiplier=args.velocity_noise_multiplier,
    )
    manifest_rows = [
        {
            "case": args.case,
            "snapshot_index": snapshot.output_index,
            "actual_time_code": snapshot.time_code,
            "actual_time_myr": snapshot.actual_time_myr,
            "input_h5": str(snapshot.input_h5),
            "timestep": snapshot.timestep,
            "file_size_bytes": snapshot.file_size_bytes,
            "shape_nz_ny_nx": "x".join(str(value) for value in snapshot.shape),
            "selection_rule": "later_promoted_segment_wins_identical_overlap",
        }
        for snapshot in snapshots
    ]
    write_rows(output_root / "snapshot_manifest.csv", manifest_rows)
    write_rows(output_root / "environment_validation.csv", [{
        "environment_table": str(args.environment_table),
        "source_sha256": environment.source_sha256,
        "row_count": len(environment.radius_cm),
        "radius_max_cm": environment.radius_cm[-1],
        "gravity_max_abs_delta_cm_s2": environment.gravity_max_abs_delta_cm_s2,
        "gravity_max_relative_delta": environment.gravity_max_relative_delta,
        "potential_zero_cm2_s2": environment.potential_cm2_s2[0],
        "potential_max_cm2_s2": environment.potential_cm2_s2[-1],
        "gravity_gate": "passed",
    }])
    all_energy: list[dict[str, Any]] = []
    all_profiles: list[list[dict[str, Any]]] = []
    for snapshot in snapshots:
        stem = f"snapshot_{snapshot.output_index:04d}"
        energy_path = per_snapshot / f"{stem}_energy.csv"
        profile_path = per_snapshot / f"{stem}_axial_profile.csv"
        marker_path = per_snapshot / f"{stem}_metadata.json"
        identity = snapshot_identity(snapshot, environment)
        if args.resume and energy_path.is_file() and profile_path.is_file() and marker_path.is_file():
            marker = json.loads(marker_path.read_text())
            if marker.get("identity") == identity and marker.get("status") == "complete":
                energy_rows = read_rows(energy_path)
                profile_rows = read_rows(profile_path)
                all_energy.extend(energy_rows)
                all_profiles.append(profile_rows)
                print(f"snapshot_reused={snapshot.output_index}", flush=True)
                continue
        energy_rows, profile_rows = analyze_snapshot(
            case=args.case,
            snapshot=snapshot,
            baseline=baseline,
            baseline_state=baseline_state,
            geometry=geometry,
            one_sided_power_erg_s=args.jet_power_one_sided_erg_s,
            jet_start_myr=args.jet_start_myr,
            jet_active_myr=args.jet_active_myr,
            tube_radius_kpc=args.tube_radius_kpc,
        )
        write_rows(energy_path, energy_rows)
        write_rows(profile_path, profile_rows)
        write_json(marker_path, {"identity": identity, "status": "complete"})
        all_energy.extend(energy_rows)
        all_profiles.append(profile_rows)
        print(f"snapshot_complete={snapshot.output_index} time_myr={snapshot.actual_time_myr:.12g}", flush=True)
    write_rows(output_root / "energy_partition_timeseries.csv", all_energy)
    shock_rows = build_shock_rows(
        case=args.case,
        profiles=all_profiles,
        snapshots=snapshots,
        environment=environment,
        primary_velocity_cut_code=baseline_state.velocity_cut_code,
        disturbance_fraction=args.disturbance_fraction,
        min_contiguous_cells=args.min_contiguous_cells,
    )
    write_rows(output_root / "shock_dynamics.csv", shock_rows)
    source_rows = []
    for snapshot in snapshots:
        one_sided, bipolar = injected_energy(
            snapshot.actual_time_myr,
            one_sided_power_erg_s=args.jet_power_one_sided_erg_s,
            jet_start_myr=args.jet_start_myr,
            jet_active_myr=args.jet_active_myr,
        )
        source_rows.append({
            "case": args.case,
            "snapshot_index": snapshot.output_index,
            "actual_time_myr": snapshot.actual_time_myr,
            "jet_power_one_sided_erg_s": args.jet_power_one_sided_erg_s,
            "jet_power_bipolar_erg_s": 2.0 * args.jet_power_one_sided_erg_s,
            "jet_start_myr": args.jet_start_myr,
            "jet_active_myr": args.jet_active_myr,
            "injected_energy_one_sided_erg": one_sided,
            "injected_energy_bipolar_erg": bipolar,
        })
    write_rows(output_root / "source_truth.csv", source_rows)
    metadata = {
        "status": "complete_fluid_snapshot_science",
        "method_version": METHOD_VERSION,
        "case": args.case,
        "snapshot_count": len(snapshots),
        "snapshot_indices": [snapshot.output_index for snapshot in snapshots],
        "partition_primary": "fractional tracer clip(tr1,0,1)",
        "partition_sensitivities": [f"binary tr1 >= {value:.0e}" for value in TRACER_THRESHOLDS],
        "pressure_partition_note": "mixed-cell pressure energy is split operationally by tracer fraction",
        "potential_convention": "centre-zero integral of mean absolute matched gravity columns",
        "boundary_status": "unmeasured_from_retained_snapshots",
        "residual_status": "not_promoted_to_cocoon_boundary_unresolved",
        "shock_contract": {
            "tube_radius_kpc": args.tube_radius_kpc,
            "baseline_velocity_noise_quantile": 0.999,
            "baseline_noise_code": baseline_state.baseline_noise_code,
            "velocity_noise_multiplier": args.velocity_noise_multiplier,
            "velocity_floor_code": args.velocity_floor_code,
            "primary_velocity_cut_code": baseline_state.velocity_cut_code,
            "disturbance_fraction": args.disturbance_fraction,
            "minimum_contiguous_cells": args.min_contiguous_cells,
            "threshold_factors": list(SHOCK_THRESHOLD_FACTORS),
            "kinematics": "local three-detected-snapshot linear fit",
            "independent_check": "two-cell upstream/downstream Rankine-Hugoniot ratios",
        },
        "environment_sha256": environment.source_sha256,
    }
    write_json(output_root / "g_lo_fluid_snapshot_science_metadata.json", metadata)
    if args.remove_geometry_cache_on_success:
        shutil.rmtree(output_root / "cache")
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--outputs-dir", action="append", required=True, type=Path)
    parser.add_argument("--environment-table", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--jet-power-one-sided-erg-s", type=float, default=1.0e43)
    parser.add_argument("--jet-start-myr", type=float, default=0.0)
    parser.add_argument("--jet-active-myr", type=float, default=50.0)
    parser.add_argument("--tube-radius-kpc", type=float, default=2.0)
    parser.add_argument("--velocity-floor-code", type=float, default=1.0e-4)
    parser.add_argument("--velocity-noise-multiplier", type=float, default=5.0)
    parser.add_argument("--disturbance-fraction", type=float, default=0.05)
    parser.add_argument("--min-contiguous-cells", type=int, default=2)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--remove-geometry-cache-on-success", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = run_chain(args)
    print(f"status={metadata['status']} snapshot_count={metadata['snapshot_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
