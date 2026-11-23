"""Measure native lobe enthalpy and current-aperture R100 storage in a paired restart."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import h5py
import numpy as np

from check_entropy_restart_control import catalogue
from extract_spherical_energy_budget import TRACER_THRESHOLD, _box_radius_limit, _speed_km_s, _validate_grid
from measure_q031_fluxes import read_grid
from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS, REQUIRED_DATASETS, UNIT_DENSITY_CGS, UNIT_ENERGY_ERG, UNIT_LENGTH_CM, require_datasets,
)
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import load_environment, sha256_file


CUTS = (TRACER_THRESHOLD, 0.005, 0.01)
VELOCITIES = ("vx1", "vx2", "vx3")


def read_physical(fields, names, selection):
    result = {name: np.asarray(fields[name][selection], dtype=np.float64) for name in names}
    if any(not np.isfinite(values).all() for values in result.values()):
        raise ValueError("non-finite native field")
    if any((result[name] <= 0).any() for name in ("prs", "rho") if name in result):
        raise ValueError("non-positive native pressure or density")
    return result


def scan_lobe(fields, grid, with_sphere):
    cells = [0] * len(CUTS)
    volumes = [[] for _ in CUTS]
    pvs = [[] for _ in CUTS]
    digests = {name: hashlib.sha256() for name in ("prs", "tr1")}
    area = grid.dy[:, None] * grid.dx[None, :]
    xy2 = grid.y[:, None]**2 + grid.x[None, :]**2
    max_lobe2 = max_fast2 = -1.0
    defining_cell = None
    outside_unit = 0
    for iz, z in enumerate(grid.z):
        raw = {name: fields[name][iz] for name in digests}
        for name, digest in digests.items():
            digest.update(np.ascontiguousarray(raw[name], dtype="<f4"))
        # Float32 representations of the decimal cuts can lie on either side.
        tracer = raw["tr1"].astype(np.float64)
        pressure = raw["prs"].astype(np.float64)
        if not np.isfinite(tracer).all() or not np.isfinite(pressure).all() or (pressure <= 0).any():
            raise ValueError(f"invalid native pressure or tracer at z index {iz}")
        outside_unit += int(np.count_nonzero((tracer < 0) | (tracer > 1)))
        volume = area * grid.dz[iz]
        for n, cut in enumerate(CUTS):
            mask = tracer > cut
            if not mask.any():
                continue
            cells[n] += int(np.count_nonzero(mask))
            v = volume[mask]
            volumes[n].append(float(v.sum()))
            pvs[n].append(float((pressure[mask] * v).sum()) * UNIT_ENERGY_ERG)
            if n == 0:
                max_lobe2 = max(max_lobe2, float(xy2[mask].max() + z**2))
        if with_sphere:
            velocity = read_physical(fields, VELOCITIES, iz)
            fast = _speed_km_s(velocity) >= 100.0
            if fast.any():
                flat = int(np.argmax(np.where(fast, xy2, -np.inf)))
                iy, ix = np.unravel_index(flat, fast.shape)
                candidate = float(xy2[iy, ix] + z**2)
                if candidate > max_fast2:
                    max_fast2 = candidate
                    defining_cell = [iz, int(iy), int(ix)]
    if min(cells) == 0 or (with_sphere and defining_cell is None):
        raise ValueError("unresolved native lobe or 100 km/s aperture")
    lobes = [dict(tracer_cut=cut, cells=cells[n], volume_kpc3=math.fsum(volumes[n]),
                  enthalpy_2p5pv_erg=2.5 * math.fsum(pvs[n])) for n, cut in enumerate(CUTS)]
    return dict(lobes=lobes, lobe_outermost_centre_kpc=math.sqrt(max_lobe2),
                tracer_outside_unit_interval_cells=outside_unit,
                field_sha256={k: v.hexdigest() for k, v in digests.items()},
                r100_radius_kpc=math.sqrt(max_fast2) if with_sphere else None,
                r100_defining_cell_zyx=defining_cell)


def storage_in_sphere(current, initial, grid, environment, radius):
    limit = np.nextafter(radius, math.inf)
    xs, ys, zs = (slice(int(axis.searchsorted(-limit)), int(axis.searchsorted(limit, side="right")))
                  for axis in (grid.x, grid.y, grid.z))
    xy2 = grid.y[ys, None]**2 + grid.x[None, xs]**2
    area = grid.dy[ys, None] * grid.dx[None, xs]
    names = ("rho", "prs", *VELOCITIES)
    sums = {k: [] for k in ("thermal_delta_erg", "kinetic_delta_erg", "gravitational_delta_erg")}
    cell_count = 0
    for iz in range(zs.start, zs.stop):
        radius_kpc = np.sqrt(xy2 + grid.z[iz]**2)
        mask = radius_kpc <= limit
        if not mask.any():
            continue
        cell_count += int(np.count_nonzero(mask))
        now = read_physical(current, names, (iz, ys, xs))
        before = read_physical(initial, names, (iz, ys, xs))
        vol = area * grid.dz[iz]
        phi = environment.potential_at_radius(radius_kpc * UNIT_LENGTH_CM)
        v2 = sum(now[k]**2 for k in VELOCITIES)
        v20 = sum(before[k]**2 for k in VELOCITIES)
        for key, energy in (
            ("thermal_delta_erg", (now["prs"] - before["prs"]) * vol * UNIT_ENERGY_ERG / (GAMMA_GAS - 1)),
            ("kinetic_delta_erg", 0.5 * (now["rho"]*v2 - before["rho"]*v20) * vol * UNIT_ENERGY_ERG),
            ("gravitational_delta_erg", (now["rho"] - before["rho"]) * vol * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3 * phi),
        ):
            sums[key].append(float(energy[mask].sum()))
    components = {k: math.fsum(values) for k, values in sums.items()}
    box_limit = _box_radius_limit((grid.x_edges, grid.y_edges, grid.z_edges), 0.0)
    return dict(**components, total_delta_erg=math.fsum(components.values()), cells=cell_count,
                complete_sphere=bool(radius <= box_limit), box_radius_limit_kpc=box_limit)


def identity(path):
    s = path.stat()
    return dict(filename=path.name, bytes=s.st_size, mtime_ns=s.st_mtime_ns, device=s.st_dev, inode=s.st_ino)


def native_fields(h5, index):
    group = f"Timestep_{index}"
    shape = require_datasets(h5, group)
    fields = h5[group]["vars"]
    if shape != (1014, 960, 960) or any(fields[k].dtype != np.dtype("<f4") for k in REQUIRED_DATASETS):
        raise ValueError("expected production native float32 fields on the 1014 x 960 x 960 grid")
    return shape, fields, float(h5[group].attrs["Time"])


def measure(arm, index, initial_file, with_sphere):
    case = arm.parent.name
    restart = json.loads((arm.parent / "restart.json").read_text())
    series = json.loads((arm / "series.json").read_text())
    gate = json.loads((arm.parent / "gate.json").read_text())
    if (case not in ("G-HI", "C-HI") or arm.name not in ("ON", "OFF") or restart["case"] != case
            or (series["case"], series["arm"]) != (case, arm.name) or gate["case"] != case or gate["passed"] is not True):
        raise ValueError("restart identity or 11-Myr control differs")
    outputs = arm / "outputs"
    filename = outputs / f"data.{index:04d}.flt.h5"
    grid_file = outputs / "grid.out"
    before = identity(filename)
    ages = dict(zip(series["new_indices"], series["ages_myr"], strict=True))
    ages[10] = restart["restart_time_code"] / CODE_TIME_PER_MYR
    catalog_time, _, step = catalogue(outputs)[index]
    with h5py.File(filename, "r") as h5:
        shape, current, time = native_fields(h5, index)
        age = time / CODE_TIME_PER_MYR
        if age != ages[index] or not math.isclose(time, catalog_time, abs_tol=0.001, rel_tol=0):
            raise ValueError("snapshot time differs from verified series or catalogue")
        grid = read_grid(h5, shape, grid_file=grid_file)
        result = scan_lobe(current, grid, with_sphere)
        if with_sphere:
            baseline = identity(initial_file)
            environment = load_environment(arm / restart["atmosphere"])
            with h5py.File(initial_file, "r") as initial:
                initial_shape, fields, initial_time = native_fields(initial, 0)
                if initial_time != 0.0:
                    raise ValueError("production initial state is not at time zero")
                _validate_grid(grid, read_grid(initial, initial_shape, grid_file=grid_file))
                result["r100_storage"] = storage_in_sphere(current, fields, grid, environment, result["r100_radius_kpc"])
            if identity(initial_file) != baseline:
                raise ValueError("production initial snapshot changed during measurement")
            result.update(initial=baseline, atmosphere_sha256=environment.source_sha256)
    if before != identity(filename):
        raise ValueError("native restart snapshot changed during measurement")
    return dict(case=case, arm=arm.name, index=index, age_myr=age, time_code=time, step=step,
                source=before, grid_out_sha256=sha256_file(grid_file), **result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", type=Path)
    parser.add_argument("index", type=int)
    parser.add_argument("initial_file", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--lobe-only", action="store_true", help="measure the adjacent output used for time matching")
    args = parser.parse_args()
    record = measure(args.arm, args.index, args.initial_file, not args.lobe_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=args.output.parent, delete=False) as tmp:
        json.dump(record, tmp, indent=2, allow_nan=False)
        tmp.write("\n")
    os.replace(tmp.name, args.output)
