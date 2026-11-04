#!/usr/bin/env python3
"""Compare paired no-jet energies after removing layers from all six faces."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile

import h5py
import numpy as np

from audit_nojet_controls import _state, _validate_grid, stat_identity
from measure_q031_fluxes import read_grid
from select_common_age_hdf5 import inspect_file
from snapshot_energy import SECONDS_PER_MYR, load_environment
from validate_paired_nojet_outputs import (
    FIELDS, GAMMA_GAS, UNIT_DENSITY_CGS, UNIT_ENERGY_ERG,
    UNIT_LENGTH_CM, UNIT_VELOCITY_CMS, _hash, _publish, _stable, validate_pair,
)


COMPONENTS = ("mass_g", "thermal_erg", "kinetic_erg", "gravitational_erg", "total_energy_erg")
ENERGY_COMPONENTS = COMPONENTS[1:]


def interior_mask(grid, iz: int, buffer_kpc: float) -> np.ndarray:
    """Keep only cells whose complete volume is inside the inset box."""
    x = ((grid.x_edges[:-1] >= grid.x_edges[0] + buffer_kpc)
         & (grid.x_edges[1:] <= grid.x_edges[-1] - buffer_kpc))
    y = ((grid.y_edges[:-1] >= grid.y_edges[0] + buffer_kpc)
         & (grid.y_edges[1:] <= grid.y_edges[-1] - buffer_kpc))
    z = (grid.z_edges[iz] >= grid.z_edges[0] + buffer_kpc
         and grid.z_edges[iz + 1] <= grid.z_edges[-1] - buffer_kpc)
    return y[:, None] & x[None, :] & z


def cell_difference(after, before, volume, potential):
    """Subtract primitives before multiplication to limit background cancellation."""
    density_delta = after["rho"] - before["rho"]
    mass = density_delta * volume * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
    speed2_after = sum(after[name]**2 for name in ("vx1", "vx2", "vx3"))
    speed2_before = sum(before[name]**2 for name in ("vx1", "vx2", "vx3"))
    result = {
        "mass_g": mass,
        "thermal_erg": (after["prs"] - before["prs"]) * volume * UNIT_ENERGY_ERG / (GAMMA_GAS - 1),
        "kinetic_erg": .5 * (after["rho"] * speed2_after - before["rho"] * speed2_before)
                       * volume * UNIT_ENERGY_ERG,
        "gravitational_erg": mass * potential,
    }
    result["total_energy_erg"] = sum(result[key] for key in COMPONENTS[1:4])
    return result


def measure_pair(initial_reflective, initial_outflow, reflective, outflow, *, grid,
                 environment, time_myr: float, buffers_kpc=(0., 1., 2., 4.)):
    buffers = tuple(float(value) for value in buffers_kpc)
    if (not buffers or buffers[0] != 0. or len(set(buffers)) != len(buffers)
            or not np.all(np.isfinite(buffers)) or any(value < 0 for value in buffers)
            or tuple(sorted(buffers)) != buffers):
        raise ValueError("buffers must be finite, unique, increasing and start at zero")
    if not np.isfinite(time_myr) or time_myr <= 0:
        raise ValueError("comparison age must be positive")
    _validate_grid(grid)
    rows = []
    for width in buffers:
        rows.append({"buffer_kpc": width, "cell_count": 0, "volume_kpc3": 0.,
                     **{kind: dict.fromkeys(COMPONENTS, 0.) for kind in
                        ("reflective_delta", "outflow_delta", "contrast", "contrast_cell_l1",
                         "reflective_delta_cell_l1", "outflow_delta_cell_l1")},
                     "mass_energy_equivalent_erg": dict.fromkeys(
                         ("reflective_delta", "outflow_delta", "contrast",
                          "reflective_delta_cell_l1", "outflow_delta_cell_l1", "contrast_cell_l1"), 0.)})
    boundary_cs_min, boundary_cs_max, domain_cs_max = np.inf, -np.inf, -np.inf
    area = grid.dy[:, None] * grid.dx[None, :]
    radius2_xy = grid.y[:, None]**2 + grid.x[None, :]**2
    inner_xy = np.ones((grid.y.size, grid.x.size), dtype=bool)
    inner_xy[[0, -1], :] = False
    inner_xy[:, [0, -1]] = False
    for iz, z in enumerate(grid.z):
        before = _state(initial_reflective, iz)
        other_before = _state(initial_outflow, iz)
        if any(not np.array_equal(before[name], other_before[name]) for name in FIELDS):
            raise ValueError(f"paired initial fields differ at z index {iz}")
        if any(np.any(before[name] != 0) for name in ("vx1", "vx2", "vx3")):
            raise ValueError("initial control velocity is not zero")
        ref, out = _state(reflective, iz), _state(outflow, iz)
        volume = area * grid.dz[iz]
        potential = environment.potential_at_radius(np.sqrt(radius2_xy + z*z) * UNIT_LENGTH_CM)
        values = {"reflective_delta": cell_difference(ref, before, volume, potential),
                  "outflow_delta": cell_difference(out, before, volume, potential),
                  "contrast": cell_difference(out, ref, volume, potential)}
        cs = np.sqrt(GAMMA_GAS * before["prs"] / before["rho"]) * UNIT_VELOCITY_CMS
        initial_h_plus_phi = (GAMMA_GAS / (GAMMA_GAS - 1) * before["prs"] / before["rho"]
                              * UNIT_VELOCITY_CMS**2 + potential)
        boundary = np.ones_like(inner_xy) if iz in (0, grid.z.size - 1) else ~inner_xy
        boundary_cs_min = min(boundary_cs_min, float(np.min(cs[boundary])))
        boundary_cs_max = max(boundary_cs_max, float(np.max(cs[boundary])))
        domain_cs_max = max(domain_cs_max, float(np.max(cs)))
        for row in rows:
            mask = interior_mask(grid, iz, row["buffer_kpc"])
            row["cell_count"] += int(np.count_nonzero(mask))
            row["volume_kpc3"] += float(np.sum(volume[mask]))
            for kind, components in values.items():
                for key, array in components.items():
                    row[kind][key] += float(np.sum(array[mask]))
                    row[kind + "_cell_l1"][key] += float(np.sum(np.abs(array[mask])))
                equivalent = components["mass_g"] * initial_h_plus_phi
                row["mass_energy_equivalent_erg"][kind] += float(np.sum(equivalent[mask]))
                row["mass_energy_equivalent_erg"][kind + "_cell_l1"] += float(np.sum(np.abs(equivalent[mask])))
        if iz % 50 == 0:
            print(f"paired_interior_z={iz}/{grid.z.size}", flush=True)
    if any(row["cell_count"] == 0 for row in rows):
        raise ValueError("an exclusion width leaves no complete physical cells")
    comparison = 2e43 * time_myr * SECONDS_PER_MYR
    for row in rows:
        denominator = abs(rows[0]["contrast"]["total_energy_erg"])
        row["total_contrast_over_low_power_comparison"] = row["contrast"]["total_energy_erg"] / comparison
        row["total_l1_over_low_power_comparison"] = row["contrast_cell_l1"]["total_energy_erg"] / comparison
        row["absolute_total_contrast_over_whole_grid_contrast"] = (
            abs(row["contrast"]["total_energy_erg"]) / denominator if denominator else None)
        row["boundary_l1_pass"] = {key: row["contrast_cell_l1"][key] <= .01 * comparison
                                    for key in ENERGY_COMPONENTS}
        row["boundary_all_components_pass"] = all(row["boundary_l1_pass"].values())
        row["background_drift_l1_pass"] = {
            kind: {key: row[kind + "_cell_l1"][key] <= .01 * comparison for key in ENERGY_COMPONENTS}
            for kind in ("reflective_delta", "outflow_delta")}
        row["background_stability_pass"] = all(
            value for components in row["background_drift_l1_pass"].values() for value in components.values())
        row["combined_interior_pass"] = row["boundary_all_components_pass"] and row["background_stability_pass"]
    first_pass = next((row["buffer_kpc"] for row in rows if row["boundary_all_components_pass"]), None)
    combined_pass = next((row["buffer_kpc"] for row in rows if row["combined_interior_pass"]), None)
    return {"regions": rows, "time_myr": time_myr,
            "low_power_comparison_erg": comparison,
            "comparison_role": "2e43 erg/s bipolar jet times age; actual injection is zero",
            "absolute_energy_tolerance_erg": .01 * comparison,
            "smallest_tested_passing_width_kpc": first_pass,
            "smallest_tested_stable_width_kpc": combined_pass,
            "adopted_coarse_width_at_50_myr_kpc": combined_pass if abs(time_myr - 50.) <= 1e-8 else None,
            "criterion": "all four energy components must pass the cellwise L1 boundary contrast <=0.01 S(t)",
            "adoption_criterion": "paired contrast and each twin's absolute background drift must all pass <=0.01 S(t); coarse controls only",
            "mass_energy_equivalent_definition": "cellwise mass change times initial specific enthalpy plus fixed potential; contextual only, no mass gate",
            "boundary_initial_cs_min_max_km_s": [boundary_cs_min / 1e5, boundary_cs_max / 1e5],
            "boundary_cs_times_age_min_max_kpc": [value * time_myr * SECONDS_PER_MYR / UNIT_LENGTH_CM
                                                 for value in (boundary_cs_min, boundary_cs_max)],
            "domain_initial_cs_max_km_s": domain_cs_max / 1e5,
            "membership": "complete cells inside all six inset faces; edges/corners counted once",
            "contrast_definition": "cellwise outflow minus reflective at equal time; initial fields verified identical",
            "potential_definition": "fixed initial tabulated potential, zero at centre",
            "limitations": ["cs times age is a local estimate, not integrated acoustic travel time",
                            "spatial discretisation can spread differences beyond the physical sound horizon",
                            "an interior storage comparison is not a closed-volume energy-conservation test"]}


def run_audit(*, reflective_run: Path, outflow_run: Path, environment_path: Path,
              snapshot_index: int, buffers_kpc, output: Path):
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    if snapshot_index <= 0:
        raise ValueError("snapshot index must be positive")
    source_names = (Path(__file__).name, "audit_nojet_controls.py", "measure_q031_fluxes.py",
                    "snapshot_energy.py", "select_common_age_hdf5.py",
                    "validate_paired_nojet_outputs.py", "pluto_h5_level3_ambient_extract.py")
    sources = [{**stat_identity(Path(__file__).with_name(name)),
                "sha256": _hash(Path(__file__).with_name(name))} for name in source_names]
    with tempfile.TemporaryDirectory(prefix="paired-interior-identity-") as directory:
        paired_identity = validate_pair([reflective_run / "output_receipt.json",
                                         outflow_run / "output_receipt.json"], Path(directory) / "pair.json")
    receipts, paths, identities = {}, {}, list(sources)
    environment = load_environment(environment_path)
    for boundary, root in (("reflective", reflective_run), ("outflow", outflow_run)):
        receipt_path = root / "output_receipt.json"
        receipt = json.loads(receipt_path.read_text())
        if (receipt.get("status") != "validated_paired_control_run"
                or receipt.get("boundary") != boundary or Path(receipt["run_dir"]) != root.absolute()):
            raise ValueError("run path or boundary differs from its validated receipt")
        table = receipt["input_files"][environment_path.name]
        if table["sha256"] != environment.source_sha256:
            raise ValueError("environment differs from validated run")
        receipts[boundary] = receipt
        identities.append({**stat_identity(receipt_path), "sha256": _hash(receipt_path)})
        for index in (0, snapshot_index):
            path = root / "outputs" / f"data.{index:04d}.dbl.h5"
            record = receipt["input_files"][path.name]
            _stable([record])
            paths[(boundary, index)] = path
            identities.append({**stat_identity(path), "sha256": record["sha256"]})
        grid_path = root / "outputs/grid.out"
        if _hash(grid_path) != receipt["input_files"]["grid.out"]["sha256"]:
            raise ValueError("grid.out differs from validated run")
        identities.append({**stat_identity(grid_path), "sha256": _hash(grid_path)})
    for key in ("case", "mode", "grid_geometry_hashes", "initial_field_hashes"):
        if receipts["outflow"][key] != receipts["reflective"][key]:
            raise ValueError(f"paired run receipts disagree: {key}")
    identities.append({**stat_identity(environment_path), "sha256": environment.source_sha256})
    with ExitStack() as stack:
        fields, ages, grid = {}, {}, None
        for (boundary, index), path in paths.items():
            records = inspect_file(path, output_index=index)
            if len(records) != 1:
                raise ValueError("snapshot must contain exactly one timestep")
            snapshot = records[0]
            h5 = stack.enter_context(h5py.File(path, "r"))
            observed = read_grid(h5, snapshot.shape, grid_file=path.parent / "grid.out")
            _validate_grid(observed, grid)
            grid = observed if grid is None else grid
            fields[(boundary, index)] = h5[f"{snapshot.timestep}/vars"]
            ages[(boundary, index)] = snapshot.actual_time_myr
        if any(abs(ages[(name, 0)]) > 1e-12 for name in receipts):
            raise ValueError("initial snapshot is not at zero time")
        age = ages[("reflective", snapshot_index)]
        if not np.isclose(age, ages[("outflow", snapshot_index)], rtol=0, atol=1e-10):
            raise ValueError("paired snapshot times differ")
        result = measure_pair(fields[("reflective", 0)], fields[("outflow", 0)],
                              fields[("reflective", snapshot_index)], fields[("outflow", snapshot_index)],
                              grid=grid, environment=environment, time_myr=age, buffers_kpc=buffers_kpc)
    _stable(identities)
    result.update({"status": "complete_paired_interior_audit", "case": receipts["reflective"]["case"],
                   "snapshot_index": snapshot_index, "inputs": identities,
                   "paired_identity": paired_identity,
                   "input_hash_scope": "validated snapshot hashes reused; metadata checked before/after; paired initial fields reread",
                   "source_sha256": {Path(row["path"]).name: row["sha256"] for row in sources}})
    _publish(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reflective-run", type=Path, required=True)
    parser.add_argument("--outflow-run", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--snapshot-index", type=int, default=1)
    parser.add_argument("--buffers-kpc", type=float, nargs="+", default=[0., 1., 2., 4.])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_audit(reflective_run=args.reflective_run, outflow_run=args.outflow_run,
              environment_path=args.environment, snapshot_index=args.snapshot_index,
              buffers_kpc=args.buffers_kpc, output=args.output)


if __name__ == "__main__":
    main()
