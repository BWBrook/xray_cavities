"""Measure the signed injector delivery in one saved paired-restart float snapshot."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np

from check_entropy_restart_control import catalogue, labelled_power
from measure_injector_faces import FIELDS, METHODS, measure
from measure_q031_fluxes import derive_control_box, parse_pluto_parameters, read_grid
from pluto_h5_level3_ambient_extract import (
    UNIT_DENSITY_CGS as D, UNIT_ENERGY_ERG, UNIT_LENGTH_CM as L, UNIT_VELOCITY_CMS as V,
    require_datasets,
)
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import load_environment, sha256_file, write_json


MASS_RATE_UNIT = D * L**2 * V
POWER_UNIT = D * L**2 * V**3
INJECTOR_RADIUS = 0.75
OUTER_RADIUS = 0.85


def snapshot_patch(arm, index):
    outputs = arm / "outputs"
    time_catalogue, _, step = catalogue(outputs)[index]
    path = outputs / f"data.{index:04d}.flt.h5"
    group = f"Timestep_{index}"
    with h5py.File(path, "r") as h5:
        shape = require_datasets(h5, group)
        variables = h5[group]["vars"]
        if shape != (1014, 960, 960) or any(variables[f].dtype != np.dtype("<f4") for f in FIELDS):
            raise ValueError("expected the six production-grid float fields")
        time = float(h5[group].attrs["Time"])
        if not math.isclose(time, time_catalogue, rel_tol=0, abs_tol=0.001):
            raise ValueError(f"{group} time differs from the float catalogue")
        grid = read_grid(h5, shape, grid_file=outputs / "grid.out")
        box = derive_control_box(grid, injection_height_kpc=INJECTOR_RADIUS,
                                 centre_kpc=(0., 0., 0.), padding_cells=4)
        bounds = ((box.i0, box.i1+1), (box.j0, box.j1+1), (box.k0, box.k1+1))
        selection = tuple(slice(a, b) for a, b in reversed(bounds))
        patch = {f: variables[f][selection] for f in FIELDS}
        centres = tuple(getattr(grid, axis)[a:b] for axis, (a, b) in zip("xyz", bounds, strict=True))
        edges = tuple(getattr(grid, axis+"_edges")[a:b+1] for axis, (a, b) in zip("xyz", bounds, strict=True))
        grid_digest = hashlib.sha256()
        for axis in ("x", "y", "z", "x_edges", "y_edges", "z_edges"):
            grid_digest.update(getattr(grid, axis).astype("<f8", copy=False).tobytes())
    digest = hashlib.sha256()
    for f in FIELDS:
        digest.update(patch[f].tobytes())
    metadata = dict(index=index, time_code=time, age_myr=time/CODE_TIME_PER_MYR, step=step,
                    bounds_xyz=bounds, grid_axes_sha256=grid_digest.hexdigest(),
                    patch_fields_sha256=digest.hexdigest(), file_size_bytes=path.stat().st_size)
    return metadata, patch, centres, edges


def measure_patch(patch, centres, edges, atmosphere):
    z, y, x = np.ix_(*centres[::-1])
    dz, dy, dx = np.ix_(*(np.diff(e) for e in edges[::-1]))
    radius2 = x*x + y*y + z*z
    volume = dx * dy * dz
    rho = patch["rho"].astype(float)
    speed2 = sum(patch[f].astype(float)**2 for f in ("vx1", "vx2", "vx3"))

    def potential(radius):
        return atmosphere.potential_at_radius(radius * L) / V**2

    phi = potential(np.sqrt(radius2))
    thermal = 1.5 * patch["prs"].astype(float)
    kinetic = 0.5 * rho * speed2

    def storage(mask):
        def integral(density):
            return float(np.sum(density * volume, where=mask))

        return dict(cells=int(np.count_nonzero(mask)),
                    thermal_erg=integral(thermal)*UNIT_ENERGY_ERG,
                    kinetic_erg=integral(kinetic)*UNIT_ENERGY_ERG,
                    gas_erg=integral(thermal + kinetic)*UNIT_ENERGY_ERG,
                    potential_erg=integral(rho*phi)*UNIT_ENERGY_ERG,
                    total_erg=integral(thermal + rho*(0.5*speed2 + phi))*UNIT_ENERGY_ERG,
                    mass_g=integral(rho)*D*L**3, tagged_mass_g=integral(rho*patch["tr1"])*D*L**3)

    def physical_rates(row):
        return dict(mass_g_s=row["mass"]*MASS_RATE_UNIT, tracer_mass_g_s=row["tracer_mass"]*MASS_RATE_UNIT,
                    gas_energy_erg_s=row["gas_energy"]*POWER_UNIT,
                    potential_energy_erg_s=row["potential_energy"]*POWER_UNIT,
                    total_energy_erg_s=row["gas_plus_potential"]*POWER_UNIT,
                    face_count=row["n_faces"], hll_fallback_faces=row["n_hll_fallback"])

    injector = {m: {} for m in METHODS}
    for row in measure(patch, centres, edges, radius=INJECTOR_RADIUS, potential=potential):
        region = row["region"]
        if row["n_cells"] != {"cap": 504, "stationary": 13824, "net": 14328}[region]:
            raise ValueError(f"injector {region} mask differs from the production geometry")
        injector[row["method"]][region] = physical_rates(row)

    outer = {r["method"]: physical_rates(r)
             for r in measure(patch, centres, edges, radius=OUTER_RADIUS, potential=potential)
             if r["region"] == "net"}
    return dict(flagged_storage=storage(radius2 <= INJECTOR_RADIUS**2), rates=injector,
                spheres={"0.85": dict(storage=storage(radius2 <= OUTER_RADIUS**2), rates=outer)})


def measure_snapshot(arm, index):
    arm = arm.resolve(strict=True)
    restart = json.loads((arm.parent / "restart.json").read_text())
    case = arm.parent.name
    if restart["case"] != case or arm.name not in ("ON", "OFF"):
        raise ValueError("invalid paired-restart case or switch label")
    ini = arm / "pluto.ini"
    if sha256_file(ini) != restart["paired_runtime_sha256"]:
        raise ValueError("runtime configuration differs from the staged pair")
    params = parse_pluto_parameters(ini)
    if (params["JET_INJECTION_HEIGHT"] != INJECTOR_RADIUS or params["JET_ROTATION_ANGLE"] != 0
            or any(params[f"JET_X{k}O"] != 0 for k in (1, 2, 3))):
        raise ValueError("expected the central, unrotated production injector")
    atmosphere = load_environment(arm / restart["atmosphere"])
    metadata, patch, centres, edges = snapshot_patch(arm, index)
    power = 2 * params["JET_PWR"]
    if power != labelled_power(case):
        raise ValueError(f"{case} has a different bipolar jet power from the production case")
    return dict(case=case, arm=arm.name, primary_method="linear_snapshot_flags",
                labelled_power_erg_s=power, labelled_mass_rate_g_s=2*power/(params["JET_SPD"]*V)**2,
                atmosphere_sha256=atmosphere.source_sha256, **metadata,
                **measure_patch(patch, centres, edges, atmosphere))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", type=Path)
    parser.add_argument("index", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_json(args.output, measure_snapshot(args.arm, args.index))
