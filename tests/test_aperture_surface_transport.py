import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import aperture_surface_transport as transport
from measure_q031_fluxes import Grid
from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS, UNIT_DENSITY_CGS, UNIT_ENERGY_ERG, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS,
)


def grid_from(x, y, z):
    edges = [np.array(e, dtype=float) for e in (x, y, z)]
    centres = [0.5 * (e[:-1] + e[1:]) for e in edges]
    return Grid(*centres, *[np.diff(e) for e in edges], *edges)


def stretched():
    return grid_from([-7, -3, -1.5, -.1, 1.6, 3.1, 7],
                     [-6.8, -3.6, -2.1, -.85, .25, 1.9, 4.2, 6],
                     [-7, -4, -2, -.5, .7, 1.8, 3.4, 6.6])


class Potential:
    def __init__(self, shift=0.):
        self.shift = shift

    def potential_at_radius(self, cm):
        return self.shift + (np.asarray(cm) / UNIT_LENGTH_CM)**2 * 2.e14


def fields(grid, t):
    z, y, x = np.meshgrid(grid.z, grid.y, grid.x, indexing="ij")
    return {"rho": 2 + .007 * x - .012 * y + t * (.02 * z + .01 * x**2),
            "prs": .08 + .002 * x + .0003 * z**2 + t * (.001 * y**2 - .002 * x),
            "vx1": .0009 * (2*x - .2*y + 1 + t),
            "vx2": .001 * (-y + .1*z**2) + .001 * t,
            "vx3": .0002 * (z**2 - 3*x + t*y)}


def direct_cells(grid, r):
    if r is None:
        return set()
    cutoff = np.nextafter(r, np.inf)
    return {(iz, iy, ix) for iz, z in enumerate(grid.z) for iy, y in enumerate(grid.y)
            for ix, x in enumerate(grid.x) if math.sqrt((y*y + x*x) + z*z) <= cutoff}


def direct_flux(grid, cells, now, potential, donor=False):
    axes = (grid.z, grid.y, grid.x)
    edges = (grid.z_edges, grid.y_edges, grid.x_edges)
    keys = ("vx3", "vx2", "vx1")
    dims = tuple(map(len, axes))
    parts = ("internal", "domain")
    rates = {k: np.zeros(5) for k in parts}
    faces = {k: 0 for k in parts}
    areas = {k: 0. for k in parts}
    box = {f"{a}_{s}": 0 for a in ("x", "y", "z") for s in ("negative", "positive")}
    for cell in sorted(cells):
        for axis in range(3):
            for sign in (-1, 1):
                neighbour = list(cell)
                neighbour[axis] += sign
                other = tuple(neighbour)
                if other in cells:
                    continue
                i = cell[axis]
                point = edges[axis][i + int(sign > 0)]
                area = math.prod(edges[k][cell[k]+1] - edges[k][cell[k]] for k in range(3) if k != axis)
                xyz = [a[k] for a, k in zip(axes, cell)]
                xyz[axis] = point
                phi = potential.potential_at_radius(math.hypot(*xyz) * UNIT_LENGTH_CM)
                state = {k: a[cell] for k, a in now.items()}
                if 0 <= other[axis] < dims[axis]:
                    part = "internal"
                    distance = (point - axes[axis][i]) / (axes[axis][other[axis]] - axes[axis][i])
                    interpolated = {k: (1 - distance) * state[k] + distance * now[k][other] for k in now}
                    if donor:
                        if sign * interpolated[keys[axis]] < 0:
                            state = {k: a[other] for k, a in now.items()}
                    else:
                        state = interpolated
                else:
                    part = "domain"
                    box[f"{'zyx'[axis]}_{'positive' if sign > 0 else 'negative'}"] += 1
                flow = sign * state[keys[axis]] * UNIT_VELOCITY_CMS * area * UNIT_LENGTH_CM**2
                mass = state["rho"] * UNIT_DENSITY_CGS * flow
                work = state["prs"] * UNIT_DENSITY_CGS * UNIT_VELOCITY_CMS**2 * flow
                kinetic = mass * .5 * sum((state[k] * UNIT_VELOCITY_CMS)**2 for k in keys)
                rates[part] += [mass, work/(GAMMA_GAS-1.), work, kinetic, mass*phi]
                faces[part] += 1
                areas[part] += area
    return rates, faces, areas, box


def direct_stock(grid, r, now, initial, potential):
    terms = []
    for k, j, i in direct_cells(grid, r):
        cell = (k, j, i)
        vol = grid.dx[i] * grid.dy[j] * grid.dz[k]
        mass = vol * transport.MASS_UNIT * (now["rho"][cell] - initial["rho"][cell])
        heat = vol * UNIT_ENERGY_ERG * (now["prs"][cell] - initial["prs"][cell]) / (GAMMA_GAS - 1.)
        ke = 0.
        for coeff, state in [(1., now), (-1., initial)]:
            v2 = sum(state[v][cell]**2 for v in ("vx1", "vx2", "vx3"))
            ke += coeff * state["rho"][cell] * .5 * v2 * vol * UNIT_ENERGY_ERG
        radius = math.hypot(grid.x[i], grid.y[j], grid.z[k])
        terms.append((mass, heat, ke, mass * potential.potential_at_radius(radius*UNIT_LENGTH_CM)))
    return np.array([math.fsum(t[k] for t in terms) for k in range(4)])


def measured(grid, now, initial, radii, env=None, tile=(2, 3, 2)):
    return transport.measure_snapshot(current=now, initial=initial, grid=grid, environment=env or Potential(),
                                     radii=radii, tile_shape=tile)


def test_stretched_hdf_faces_match_bruteforce_and_include_box_patches(tmp_path):
    grid = stretched()
    env = Potential()
    initial, now = fields(grid, 0), fields(grid, 2)
    radii = {"R100": {"previous": 2.4, "current": 6.7, "next": 14.},
             "R300": {"previous": None, "current": 2.4, "next": 1.3}}
    with h5py.File(tmp_path / "fields.h5", "w") as h:
        curr, before = h.create_group("now"), h.create_group("before")
        for key in now:
            curr[key], before[key] = now[key], initial[key]
        out = measured(grid, curr, before, radii, env)
        assert json.loads(json.dumps(out, allow_nan=False)) == out
    for name, roles in radii.items():
        for role, r in roles.items():
            result = out["apertures"][name]["surfaces"][role]
            cells = direct_cells(grid, r)
            assert result["cell_count"] == len(cells)
            assert result["volume_kpc3"] == pytest.approx(sum(grid.dx[i]*grid.dy[j]*grid.dz[k] for k,j,i in cells))
            for method in transport.CONTROL_RECONSTRUCTIONS:
                ref, fc, fa, box = direct_flux(grid, cells, now, env, donor=method=="donor_cell_primitives")
                for part in ("internal", "domain"):
                    assert result["geometry"][part]["face_count"] == fc[part]
                    assert result["geometry"][part]["area_kpc2"] == pytest.approx(fa[part])
                    rates = result["flux"][method][part]
                    values = [rates[k] for k in ("mass_flux_outward_g_s", "thermal_advective_flux_outward_erg_s",
                              "pressure_work_outward_erg_s", "kinetic_flux_outward_erg_s", "gravitational_flux_outward_erg_s")]
                    np.testing.assert_allclose(values, ref[part], rtol=2e-13, atol=0)
                    assert rates["gas_flux_outward_erg_s"] == pytest.approx(sum(values[1:4]))
                    assert rates["total_energy_flux_outward_erg_s"] == pytest.approx(sum(values[1:]))
                assert result["domain_contact"] == bool(fc["domain"])
                assert {key: v["face_count"] for key,v in result["box_faces"].items()} == box
    whole = out["apertures"]["R100"]["surfaces"]["next"]
    assert not whole["sphere_fully_inside_domain"] and whole["geometry"]["internal"]["face_count"] == 0
    surface = out["apertures"]["R100"]["surfaces"]["current"]
    assert not surface["sphere_fully_inside_domain"] and surface["geometry"]["internal"]["face_count"] > 0


def test_signed_sweep_is_exact_discrete_reynolds_split_for_moving_or_empty_aperture():
    g, env = stretched(), Potential()
    f0, a, b = (fields(g, t) for t in (0, 1, 2))
    for r0, r1 in ((2.55, 6.5), (6.5, 2.55), (None, 2.55), (2.55, None), (1.5, 1.5)):
        rn = {"R100":{"current":r0, "next":r1}, "R300":{"current":r0, "next":r1}}
        rp = {"R100":{"previous":r0, "current":r1}, "R300":{"previous":r0, "current":r1}}
        ca = measured(g, a, f0, rn, env)["apertures"]["R100"]["sweeps"]["current_to_next"]
        cb = measured(g, b, f0, rp, env)["apertures"]["R100"]["sweeps"]["previous_to_current"]
        a0, a1, b0, b1 = (direct_stock(g, r, f, f0, env) for f,r in [(a,r0),(a,r1),(b,r0),(b,r1)])
        for shell, expected in ((ca, a1-a0), (cb, b1-b0)):
            np.testing.assert_allclose([shell[k] for k in transport.STOCK_FIELDS], expected, rtol=1e-12)
            assert shell["cell_count_delta"]==len(direct_cells(g,r1))-len(direct_cells(g,r0))
            assert shell["total_energy_erg"]==pytest.approx(sum(expected[1:]))
        entry = .5*np.array([ca[k]+cb[k] for k in transport.STOCK_FIELDS])
        evolution = .5*((b0-a0)+(b1-a1))
        np.testing.assert_allclose(entry + evolution, b1 - a0, rtol=2.e-12)


def test_linear_velocity_manufactured_mass_pressure_work_and_potential_reference():
    g = stretched()
    z,y,x = np.meshgrid(g.z,g.y,g.x,indexing="ij")
    one = np.ones_like(x)
    now = {"rho": 3*one, "prs": .11*one, "vx1": .002*x, "vx2": -.003*y, "vx3": -.0007*z}
    initial = {**now, "rho":2.95*one}
    radii = {"R100":{"previous":1.0, "current":2.55}, "R300":{"current":1.45}}
    native = measured(g, now, initial, radii)
    shifted = measured(g, now, initial, radii, env=Potential(shift=9.e15))
    surface = native["apertures"]["R100"]["surfaces"]["current"]
    assert not surface["domain_contact"]
    rates = surface["flux"]["centered_primitives"]["total"]
    volume_code = surface["volume_kpc3"]
    outward = (.002-.003-.0007)*volume_code*UNIT_LENGTH_CM**2*UNIT_VELOCITY_CMS
    assert rates["mass_flux_outward_g_s"] == pytest.approx(3*UNIT_DENSITY_CGS*outward)
    expected_work = .11*UNIT_DENSITY_CGS*UNIT_VELOCITY_CMS**2*outward
    assert rates["pressure_work_outward_erg_s"] == pytest.approx(expected_work)
    assert rates["thermal_advective_flux_outward_erg_s"] == pytest.approx(expected_work/(GAMMA_GAS-1.))
    for method in transport.CONTROL_RECONSTRUCTIONS:
        old = surface["flux"][method]["total"]
        new = shifted["apertures"]["R100"]["surfaces"]["current"]["flux"][method]["total"]
        assert new["gravitational_flux_outward_erg_s"] - old["gravitational_flux_outward_erg_s"] == pytest.approx(9.e15*old["mass_flux_outward_g_s"])
    old = native["apertures"]["R100"]["sweeps"]["previous_to_current"]
    new = shifted["apertures"]["R100"]["sweeps"]["previous_to_current"]
    assert new["gravitational_erg"] - old["gravitational_erg"] == pytest.approx(9.e15*old["mass_g"])


def test_center_tie_empty_aperture_and_same_state_sweep():
    g = grid_from(*[[-1.5, -.5, .5, 1.5]]*3)
    f0 = fields(g, 0)
    just_under = np.nextafter(1., 0.)
    radii = {"R100":{"previous":None, "current":just_under, "next":np.nextafter(just_under,0.)},
             "R300":{"current":0.}}
    out = measured(g, f0, f0, radii, tile=(1,1,1))["apertures"]
    a = out["R100"]["surfaces"]
    assert a["previous"]["cell_count"] == 0 and a["previous"]["sphere_fully_inside_domain"] is None
    assert a["current"]["cell_count"] == 7 and a["next"]["cell_count"] == 1
    assert out["R300"]["surfaces"]["current"]["cell_count"] == 1
    assert a["current"]["sphere_fully_inside_domain"] and a["current"]["domain_contact"]
    for row in out["R100"]["sweeps"].values():
        assert all(row[k]==0 for k in transport.STOCK_FIELDS)
    assert out["R300"]["sweeps"] == {}


def test_sparse_reads_skip_unaffected_tiles_and_initial_when_radius_does_not_move():
    e = np.arange(-24.5,25.5,1.)
    g = grid_from(e,e,e)
    now = fields(g, 0)
    class Tracking:
        def __init__(self,a):
            self.array, self.shape, self.cells = a, a.shape, 0
        def __getitem__(self,key):
            arr = self.array[key]
            self.cells += arr.size
            return arr
    current = {k:Tracking(a) for k,a in now.items()}
    initial = {k:Tracking(a) for k,a in now.items()}
    radii = {"R100":{"previous":2.3,"current":2.3},"R300":{"current":1.}}
    result = measured(g,current,initial,radii,tile=(4,5,6))
    assert 0 < current["rho"].cells < now["rho"].size / 8
    assert initial["rho"].cells == 0 and result["primitive_tiles_read"]["initial"] == 0
    a = result["apertures"]["R100"]["surfaces"]["current"]["flux"]["centered_primitives"]["total"]
    b = measured(g,now,now,radii,tile=(100,100,100))["apertures"]["R100"]["surfaces"]["current"]["flux"]["centered_primitives"]["total"]
    for k in a:
        assert a[k] == pytest.approx(b[k])
