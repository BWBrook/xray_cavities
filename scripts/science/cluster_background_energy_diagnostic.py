#!/usr/bin/env python3
"""Diagnose far-field atmospheric energy drift in the matched cluster pair."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from pluto_h5_level3_ambient_extract import (
    UNIT_LENGTH_CM,
    derive_widths,
    read_and_validate_axes,
    read_axis,
    require_datasets,
)
from snapshot_energy import (
    ENERGY_FIELDS,
    EnvironmentProfile,
    add_energy,
    canonical_snapshot_chain,
    empty_energy_totals,
    injected_energy,
    load_environment,
    slice_energy,
    write_json,
    write_rows,
)


METHOD_VERSION = 1
SHELL_EDGES_KPC = (0.0, 50.0, 100.0, 150.0, 200.0, math.inf)
OUTER_CONTROL_MIN_KPC = 100.0


@dataclass(frozen=True)
class ShellGeometry:
    x_kpc: np.ndarray
    y_kpc: np.ndarray
    z_kpc: np.ndarray
    dx_kpc: np.ndarray
    dy_kpc: np.ndarray
    dz_kpc: np.ndarray
    volume_xy_kpc2: np.ndarray


def shell_label(lower: float, upper: float) -> str:
    upper_text = "inf" if math.isinf(upper) else f"{int(upper):03d}"
    return f"r_{int(lower):03d}_{upper_text}_kpc"


def radial_shell_masks(radius_kpc: np.ndarray) -> list[tuple[str, np.ndarray]]:
    radius = np.asarray(radius_kpc, dtype=float)
    if np.any(~np.isfinite(radius)) or np.any(radius < 0.0):
        raise ValueError("radius must be finite and non-negative")
    output = []
    coverage = np.zeros(radius.shape, dtype=np.int8)
    for lower, upper in zip(SHELL_EDGES_KPC[:-1], SHELL_EDGES_KPC[1:]):
        mask = (radius >= lower) & (radius < upper)
        coverage += mask
        output.append((shell_label(lower, upper), mask))
    if not np.all(coverage == 1):
        raise ValueError("radial shells do not partition the grid")
    return output


def read_geometry(h5_path: Path, timestep: str, shape: tuple[int, int, int]) -> ShellGeometry:
    nz, ny, nx = shape
    with h5py.File(h5_path, "r") as h5:
        x = read_axis(h5, "X", nz=nz, ny=ny, nx=nx)
        y = read_axis(h5, "Y", nz=nz, ny=ny, nx=nx)
        z = read_axis(h5, "Z", nz=nz, ny=ny, nx=nx)
        require_datasets(h5, timestep)
    dx, dy, dz = derive_widths(x), derive_widths(y), derive_widths(z)
    return ShellGeometry(x, y, z, dx, dy, dz, dy[:, None] * dx[None, :])


def integrate_shells(
    *,
    h5_path: Path,
    timestep: str,
    shape: tuple[int, int, int],
    geometry: ShellGeometry,
    environment: EnvironmentProfile,
) -> dict[str, dict[str, float]]:
    totals = {
        shell_label(lower, upper): empty_energy_totals()
        | {"tracer_volume_kpc3": 0.0, "tracer_max": 0.0}
        for lower, upper in zip(SHELL_EDGES_KPC[:-1], SHELL_EDGES_KPC[1:])
    }
    xy_radius_squared = geometry.x_kpc[None, :] ** 2 + geometry.y_kpc[:, None] ** 2
    with h5py.File(h5_path, "r") as h5:
        if require_datasets(h5, timestep) != shape:
            raise ValueError(f"snapshot shape drift: {h5_path}:{timestep}")
        variables = h5[f"/{timestep}/vars"]
        for iz, z_value in enumerate(geometry.z_kpc):
            rho = np.asarray(variables["rho"][iz], dtype=float)
            pressure = np.asarray(variables["prs"][iz], dtype=float)
            tracer = np.clip(np.asarray(variables["tr1"][iz], dtype=float), 0.0, 1.0)
            vx1 = np.asarray(variables["vx1"][iz], dtype=float)
            vx2 = np.asarray(variables["vx2"][iz], dtype=float)
            vx3 = np.asarray(variables["vx3"][iz], dtype=float)
            volume = geometry.volume_xy_kpc2 * geometry.dz_kpc[iz]
            radius_kpc = np.sqrt(xy_radius_squared + z_value**2)
            potential = environment.potential_at_radius(radius_kpc * UNIT_LENGTH_CM)
            for label, mask in radial_shell_masks(radius_kpc):
                weight = mask.astype(float)
                values = slice_energy(
                    rho=rho,
                    pressure=pressure,
                    velocity_squared=vx1**2 + vx2**2 + vx3**2,
                    weight=weight,
                    volume_kpc3=volume,
                    potential_cm2_s2=potential,
                )
                add_energy(totals[label], values)
                totals[label]["tracer_volume_kpc3"] += float(np.sum(tracer * weight * volume))
                totals[label]["tracer_max"] = max(totals[label]["tracer_max"], float(np.max(tracer[mask], initial=0.0)))
    return totals


def read_reference(path: Path, case: str) -> dict[int, float]:
    with Path(path).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = {
        int(row["snapshot_index"]): float(row["gas_total_delta_erg"]) + float(row["lobe_total_erg"])
        for row in rows
        if row["case"] == case
        and row["side"] == "bipolar_total"
        and row["partition_method"] == "fractional"
    }
    if len(selected) != 51:
        raise ValueError("reference energy surface is not the accepted 51-row primary surface")
    return selected


def _sum_fields(rows: Sequence[Mapping[str, Any]], field: str) -> float:
    return float(sum(float(row[field]) for row in rows))


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    if output_root.exists() or output_root.is_symlink():
        raise ValueError(f"refusing to overwrite output root: {output_root}")
    output_root.mkdir(parents=True)
    snapshots = canonical_snapshot_chain([Path(path) for path in args.outputs_dir])
    by_index = {snapshot.output_index: snapshot for snapshot in snapshots}
    requested = list(args.snapshot_index)
    if len(requested) != len(set(requested)) or requested[0] != 0:
        raise ValueError("snapshot indices must be unique and begin with baseline index zero")
    if any(index not in by_index for index in requested):
        raise ValueError("one or more requested snapshots are unavailable")
    selected = [by_index[index] for index in requested]
    baseline = selected[0]
    geometry = read_geometry(baseline.input_h5, baseline.timestep, baseline.shape)
    environment = load_environment(Path(args.environment_table))
    reference = read_reference(Path(args.reference_energy), args.case)
    baseline_totals = integrate_shells(
        h5_path=baseline.input_h5,
        timestep=baseline.timestep,
        shape=baseline.shape,
        geometry=geometry,
        environment=environment,
    )
    shell_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for snapshot in selected:
        with h5py.File(baseline.input_h5, "r") as base_h5, h5py.File(snapshot.input_h5, "r") as target_h5:
            read_and_validate_axes(base=base_h5, final=target_h5, nz=baseline.shape[0], ny=baseline.shape[1], nx=baseline.shape[2])
        current = baseline_totals if snapshot.output_index == 0 else integrate_shells(
            h5_path=snapshot.input_h5,
            timestep=snapshot.timestep,
            shape=snapshot.shape,
            geometry=geometry,
            environment=environment,
        )
        _one_sided, injected = injected_energy(
            snapshot.actual_time_myr,
            one_sided_power_erg_s=args.jet_power_one_sided_erg_s,
            jet_start_myr=0.0,
            jet_active_myr=50.0,
        )
        snapshot_rows: list[dict[str, Any]] = []
        for lower, upper in zip(SHELL_EDGES_KPC[:-1], SHELL_EDGES_KPC[1:]):
            label = shell_label(lower, upper)
            initial = baseline_totals[label]
            target = current[label]
            thermal = target["thermal_erg"] - initial["thermal_erg"]
            kinetic = target["kinetic_erg"] - initial["kinetic_erg"]
            gravitational = target["gravitational_erg"] - initial["gravitational_erg"]
            total = thermal + kinetic + gravitational
            row = {
                "case": args.case,
                "snapshot_index": snapshot.output_index,
                "actual_time_myr": snapshot.actual_time_myr,
                "shell": label,
                "radius_min_kpc": lower,
                "radius_max_kpc": "" if math.isinf(upper) else upper,
                "thermal_delta_erg": thermal,
                "kinetic_delta_erg": kinetic,
                "gravitational_delta_erg": gravitational,
                "total_delta_erg": total,
                "shell_volume_kpc3": target["volume_kpc3"],
                "tracer_volume_kpc3": target["tracer_volume_kpc3"],
                "tracer_volume_fraction": target["tracer_volume_kpc3"] / target["volume_kpc3"],
                "tracer_max": target["tracer_max"],
                "injected_energy_erg": injected,
                "total_fraction_of_injected": total / injected if injected > 0.0 else "",
            }
            snapshot_rows.append(row)
            shell_rows.append(row)
        global_total = _sum_fields(snapshot_rows, "total_delta_erg")
        reference_total = reference[snapshot.output_index]
        reference_difference = global_total - reference_total
        relative_error: float | str
        if snapshot.output_index == 0:
            # Both surfaces are baseline-subtracted. Their tiny cancellation
            # residues do not define a meaningful relative error near zero.
            relative_error = ""
        else:
            scale = max(abs(reference_total), abs(global_total), 1.0)
            relative_error = abs(reference_difference) / scale
        outer = [row for row in snapshot_rows if float(row["radius_min_kpc"]) >= OUTER_CONTROL_MIN_KPC]
        outer_volume = _sum_fields(outer, "shell_volume_kpc3")
        outer_tracer = _sum_fields(outer, "tracer_volume_kpc3")
        outer_total = _sum_fields(outer, "total_delta_erg")
        summary_rows.append({
            "case": args.case,
            "snapshot_index": snapshot.output_index,
            "actual_time_myr": snapshot.actual_time_myr,
            "global_total_delta_erg": global_total,
            "reference_accounted_delta_erg": reference_total,
            "reference_absolute_difference_erg": reference_difference,
            "reference_relative_error": relative_error,
            "outer_control_min_radius_kpc": OUTER_CONTROL_MIN_KPC,
            "outer_thermal_delta_erg": _sum_fields(outer, "thermal_delta_erg"),
            "outer_kinetic_delta_erg": _sum_fields(outer, "kinetic_delta_erg"),
            "outer_gravitational_delta_erg": _sum_fields(outer, "gravitational_delta_erg"),
            "outer_total_delta_erg": outer_total,
            "outer_fraction_of_global_delta": outer_total / global_total if global_total != 0.0 else "",
            "outer_tracer_volume_fraction": outer_tracer / outer_volume,
            "injected_energy_erg": injected,
            "outer_total_fraction_of_injected": outer_total / injected if injected > 0.0 else "",
        })
        if relative_error != "" and relative_error > 1.0e-8:
            raise ValueError(f"shell reconstruction drift at snapshot {snapshot.output_index}: {relative_error}")
        print(f"snapshot_complete={snapshot.output_index} time_myr={snapshot.actual_time_myr:.12g}", flush=True)
    write_rows(output_root / "shell_energy_diagnostic.csv", shell_rows)
    write_rows(output_root / "background_summary.csv", summary_rows)
    result = {
        "status": "complete_cluster_background_energy_diagnostic",
        "method_version": METHOD_VERSION,
        "case": args.case,
        "snapshot_indices": requested,
        "shell_edges_kpc": [value if math.isfinite(value) else "inf" for value in SHELL_EDGES_KPC],
        "outer_control_min_radius_kpc": OUTER_CONTROL_MIN_KPC,
        "outer_control_interpretation": "far-field diagnostic; scientific control status requires shock and tracer checks",
        "environment_sha256": environment.source_sha256,
        "reference_energy_path": str(args.reference_energy),
        "maximum_reference_relative_error": max(
            float(row["reference_relative_error"])
            for row in summary_rows
            if row["reference_relative_error"] != ""
        ),
    }
    write_json(output_root / "cluster_background_energy_diagnostic_metadata.json", result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--outputs-dir", action="append", required=True, type=Path)
    parser.add_argument("--environment-table", required=True, type=Path)
    parser.add_argument("--reference-energy", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--jet-power-one-sided-erg-s", required=True, type=float)
    parser.add_argument("--snapshot-index", action="append", required=True, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(args)
    print(f"status={result['status']} case={result['case']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
