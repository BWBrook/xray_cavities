"""Measure full-grid stocks and six-face outward transport for one paired restart output."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import h5py
import numpy as np

import measure_q031_fluxes as flux
from check_entropy_restart_control import catalogue, paired_cases
from pluto_h5_level3_ambient_extract import UNIT_LENGTH_CM, require_datasets
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import load_environment, sha256_file, slice_energy


def measure(variables, grid, environment, *, slab_depth=4):
    shape = (len(grid.z), len(grid.y), len(grid.x))
    cache = flux.DomainPlaneCache.create(shape)
    fields = {name: variables[name] for name in flux.PRIMITIVE_FIELDS}
    hashes = {name: hashlib.sha256() for name in fields}
    if any(a.shape != shape or a.dtype.kind != "f" or a.dtype.itemsize != 4 for a in fields.values()):
        raise ValueError("expected five native float32 fields on the common grid")
    area = np.outer(grid.dy, grid.dx)
    rxy2 = grid.y[:, None]**2 + grid.x[None, :]**2
    parts = {name: [] for name in ("thermal_erg", "kinetic_erg", "gravitational_erg", "mass_g")}
    for start in range(0, shape[0], slab_depth):
        block = {name: field[start:start+slab_depth] for name, field in fields.items()}
        for name, values in block.items():
            hashes[name].update(np.ascontiguousarray(values, dtype="<f4"))
        for local, iz in enumerate(range(start, min(start + slab_depth, shape[0]))):
            state = flux._validate_primitive_state({name: slab[local] for name, slab in block.items()})
            cache.capture_z_slab(iz, state)
            radius = np.sqrt(rxy2 + grid.z[iz]**2) * UNIT_LENGTH_CM
            sample = slice_energy(
                rho=state["rho"], pressure=state["prs"], weight=1.0,
                velocity_squared=state["vx1"]**2 + state["vx2"]**2 + state["vx3"]**2,
                volume_kpc3=area * grid.dz[iz], potential_cm2_s2=environment.potential_at_radius(radius),
            )
            for name, values in parts.items():
                values.append(sample[name])
    stocks = {name: math.fsum(pieces) for name, pieces in parts.items()}
    stocks["total_energy_erg"] = math.fsum(stocks[k] for k in ("thermal_erg", "kinetic_erg", "gravitational_erg"))

    boundary = {}
    for method in flux.OUTER_RECONSTRUCTIONS:
        try:
            rows = flux.measure_domain_surface(variables, grid, environment, method, plane_cache=cache)
        except ValueError as error:
            if method != "linear_to_boundary_face" or str(error) != (
                "linear boundary-face reconstruction produced a non-physical primitive state"
            ):
                raise
            boundary[method] = dict(valid=False, reason=str(error), total_energy_flux_outward_erg_s=None, faces={})
            continue
        boundary[method] = {
            "valid": True, **{k: rows[-1][k] for k in flux.FLUX_FIELDS},
            "faces": {r["face"]: {k: r[k] for k in flux.FLUX_FIELDS} for r in rows[:-1]},
        }
    return stocks, boundary, {name: digest.hexdigest() for name, digest in hashes.items()}


def reduce_snapshot(arm, index):
    state = json.loads((arm.parent / "restart.json").read_text())
    if state["case"] != arm.parent.name or arm.name not in ("ON", "OFF"):
        raise ValueError("arm directory differs from the paired restart identity")
    if arm.name == "OFF":
        for case in paired_cases(state["case"]):
            if json.loads((arm.parent.parent / case / "gate.json").read_text())["passed"] is not True:
                raise ValueError(f"11-Myr control failed for {case}")
    series = json.loads((arm / "series.json").read_text())
    if series["arm"] != arm.name or series["case"] != state["case"]:
        raise ValueError("validated series belongs to another arm")
    series_ages = dict(zip(series["new_indices"], series["ages_myr"], strict=True))
    series_ages[10] = state["restart_time_code"] / CODE_TIME_PER_MYR
    outputs = arm / "outputs"
    path = outputs / f"data.{index:04d}.flt.h5"
    before = path.stat()
    group = f"Timestep_{index}"
    catalog_time, _, step = catalogue(outputs)[index]
    atmosphere = load_environment(arm / state["atmosphere"])
    grid_file = outputs / "grid.out"
    with h5py.File(path, "r") as h5:
        time = float(h5[group].attrs["Time"])
        age = time / CODE_TIME_PER_MYR
        if not math.isclose(time, catalog_time, abs_tol=.001, rel_tol=0) or age != series_ages[index]:
            raise ValueError(f"native time disagrees with the catalogue or series at {index}")
        shape = require_datasets(h5, group)
        grid = flux.read_grid(h5, shape, grid_file=grid_file)
        stock, boundary, hashes = measure(h5[group]["vars"], grid, atmosphere)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError(f"native snapshot changed during reduction at {index}")
    return {
        "case": state["case"], "arm": arm.name, "index": index, "step": step,
        "time_code": time, "age_myr": age, "storage": stock, "boundary": boundary,
        "input": {"filename": path.name, "bytes": before.st_size, "mtime_ns": before.st_mtime_ns,
                  "shape_zyx": shape, "field_sha256_c_order_float32_le": hashes,
                  "grid_out_sha256": sha256_file(grid_file), "edge_source": grid.edge_source,
                  "atmosphere_sha256": atmosphere.source_sha256},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", type=Path)
    parser.add_argument("index", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    record = reduce_snapshot(args.arm, args.index)
    payload = json.dumps(record, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False, mode="w") as tmp:
        tmp.write(payload)
    os.replace(tmp.name, args.output)


if __name__ == "__main__":
    main()
