"""Recompute the four manufactured exterior states and compare them with compiled PLUTO."""
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "scripts/science"))
from measure_injector_faces import measure


def check():
    fixture = json.loads((HERE / "cap_reference_fixture.json").read_text())
    with (HERE / "compiled_manufactured_controls.csv").open() as stream:
        targets = list(csv.DictReader(stream))
    centres, edges = (tuple(np.array(fixture["coordinates_kpc"][axis][key]) for axis in "xyz")
                      for key in ("centres", "edges"))
    z, y, x = np.meshgrid(*centres[::-1], indexing="ij")
    r = np.sqrt(x*x+y*y+z*z)
    sphere = r <= fixture["source_radius_kpc"]
    angle = math.radians(fixture["cone_half_angle_deg"])
    cone = np.hypot(x, y) <= np.abs(z)*math.tan(angle)
    for expected in targets:
        case, kind = expected["case"], expected["exterior"]
        jet = fixture["cases"][case]
        factor = (jet["jet_length_scale_kpc"]/r)**2
        rho = jet["jet_density_code"]*factor
        pressure = jet["jet_pressure_code"]*factor**fixture["gamma"]
        speed = jet["jet_speed_code"]
        if kind == "radial_everywhere":
            moving = np.ones_like(sphere)
        elif kind == "continuing_cone_matched_static_sheath":
            moving = cone
        else:
            if kind == "continuing_cone_static_atmosphere":
                moving, prescribed = cone, sphere | cone
            elif kind == "startup_initial_static_atmosphere":
                moving, prescribed = cone & sphere, sphere
            else:
                raise ValueError(kind)
            rho = np.where(prescribed, rho, np.interp(r, jet["ambient_radius_kpc"], jet["ambient_density_code"]))
            pressure = np.where(prescribed, pressure, np.interp(r, jet["ambient_radius_kpc"], jet["ambient_pressure_code"]))
        patch = dict(rho=rho, prs=pressure, tr1=moving.astype(float))
        patch.update({f"vx{i}": d*(moving*speed/r) for i, d in enumerate((x, y, z), 1)})
        rows = {row["region"]: row for row in measure(patch, centres, edges) if row["method"] == "linear_snapshot_flags"}
        cap = rows["cap"]
        continuum = 4*math.pi*(1-math.cos(angle))*jet["jet_density_code"]*jet["jet_length_scale_kpc"]**2*speed
        label = continuum/jet["prescribed_continuum_mass_over_label"]
        measured = dict(sphere_faces=rows["net"]["n_faces"], cap_faces=cap["n_faces"],
                        cap_tagged_mass_over_label=cap["tracer_mass"]/label,
                        cap_gas_energy_over_label=cap["gas_energy"]/(.5*speed**2*label),
                        cap_tagged_mass_out_on_hotter_exterior_fraction=cap["hotter_outside_sets_wave_tracer_mass_out"]/cap["tracer_mass_out"],
                        cap_hll_fallback=cap["n_hll_fallback"], stationary_hll_fallback=rows["stationary"]["n_hll_fallback"])
        for key, value in measured.items():
            if not math.isclose(value, float(expected[key]), rel_tol=2e-12, abs_tol=1e-14):
                raise ValueError(f"{case}/{kind}/{key}: {value} vs {expected[key]}")
    print(f"Verified {len(targets)} manufactured cases against compiled PLUTO")


if __name__ == "__main__":
    check()
