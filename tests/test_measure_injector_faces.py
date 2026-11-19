from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import measure_injector_faces as injector


def uniform_patch():
    edges = [np.arange(-20, 21) / 20] * 3
    centres = [(edge[1:] + edge[:-1]) * 0.5 for edge in edges]
    z, y, x = np.meshgrid(*centres[::-1], indexing="ij")
    sphere = x*x + y*y + z*z <= 0.75**2
    cap = x*x + y*y <= (z * np.tan(np.pi / 12))**2
    radius = np.sqrt(x*x + y*y + z*z)
    patch = {
        "rho": np.ones_like(x), "prs": np.full_like(x, 0.001),
        "vx1": cap * 0.1 * x / radius, "vx2": cap * 0.1 * y / radius,
        "vx3": cap * 0.1 * z / radius, "tr1": cap.astype(float),
    }
    return patch, centres, edges, sphere


@pytest.mark.parametrize("normal", [-3., -0.1, 0., 0.1, 3.])
def test_constant_state_is_physical_euler_flux(normal):
    inside = np.array([[1.5, .3, normal, .2, -.4, .75]])
    outside = inside.copy()
    outside[:, 5] = .25
    for flagged in (False, True):
        rates, _, _ = injector._face_flux(inside, outside, np.array([flagged]))
        mass = 1.5 * normal
        kinetic = .5 * (normal**2 + .2**2 + .4**2)
        assert rates["mass"][0] == pytest.approx(mass)
        assert rates["gas_energy"][0] == pytest.approx(normal * (.3 * 2.5 + 1.5 * kinetic))
        assert rates["tracer_mass"][0] == pytest.approx(mass * (.75 if mass > 0 else .25))
        assert rates["donor_kinetic"][0] == pytest.approx(mass * kinetic)


def test_hll_smears_a_stationary_density_contact_and_upwinds_its_tracer():
    inside = np.array([[4., 1., 0., 0., 0., .75]])
    outside = np.array([[1., 1., 0., 0., 0., .125]])
    exact, waves, fallback = injector._face_flux(inside, outside, np.array([False]))
    assert exact["mass"][0] == exact["gas_energy"][0] == 0.
    assert not fallback[0]
    assert all(mask[0] for mask in waves.values())
    smeared, _, fallback = injector._face_flux(inside, outside, np.array([True]))
    assert fallback[0]
    assert smeared["mass"][0] == pytest.approx(1.5 * np.sqrt(5 / 3))
    assert smeared["tracer_mass"][0] == pytest.approx(.75 * smeared["mass"][0])
    assert smeared["gas_energy"][0] == 0


def test_mirror_orientations_negate_all_rates():
    inn = np.array([[1., .5, .1, .7, -.8, 1.], [.5, .3, 3., .4, .2, .3]])
    out = np.array([[.1, 1., -.4, .6, .5, 0.], [1., .2, 2., .3, .8, .2]])
    mirror_inn, mirror_out = out.copy(), inn.copy()
    mirror_inn[:, 2] *= -1
    mirror_out[:, 2] *= -1
    for flags in ([False, False], [True, True]):
        fwd = injector._face_flux(inn, out, np.array(flags))[0]
        rev = injector._face_flux(mirror_inn, mirror_out, np.array(flags))[0]
        for field in injector.RATES:
            np.testing.assert_allclose(fwd[field], -rev[field], rtol=1e-13, atol=1e-14)


def test_reproduces_production_mesh_and_additive_signed_gross_totals():
    patch, centres, edges, _ = uniform_patch()
    rows = injector.measure({k: v.astype("f4") for k, v in patch.items()}, centres, edges,
                            potential=lambda r: 2 + 0*r)
    assert len(rows) == len(injector.METHODS) * 3
    for method in injector.METHODS:
        cap, sta, net = [r for r in rows if r["method"] == method]
        assert (cap["region"], sta["region"], net["region"]) == injector.REGIONS
        assert (cap["n_faces"], net["n_faces"]) == (168, 4296)
        assert (cap["n_cells"], net["n_cells"]) == (504, 14328)
        assert cap["tracer_max_abs_error"] == sta["tracer_max_abs_error"] == 0
        assert cap["speed_min"] == pytest.approx(.1, rel=5e-8)
        assert cap["transverse_speed_max"] < 1e-8
        assert sta["speed_max"] == 0.
        assert net["area"] == pytest.approx(4296 * .05**2)
        for field in (*injector.RATES, "potential_energy", "gas_plus_potential"):
            assert net[field] == pytest.approx(cap[field] + sta[field])
            assert net[field] == pytest.approx(net[field + "_out"] - net[field + "_in"])
        assert net["potential_energy"] == pytest.approx(2 * net["mass"])
        assert net["gas_plus_potential"] == pytest.approx(net["gas_energy"] + net["potential_energy"])
        for row in (cap, sta, net):
            for wave in ("return_wave", "outside_incoming", "outside_sets_wave", "hotter_outside_sets_wave"):
                for field in ("mass", "tracer_mass", "gas_energy"):
                    assert 0 <= row[wave + "_" + field + "_out"] <= row[field + "_out"] + 1e-12


def test_plm_exact_for_linear_density_flow_by_volume_divergence():
    patch, centres, edges, sphere = uniform_patch()
    x = centres[0][None, None, :]
    patch["rho"][:] = 2 + x
    patch["prs"][:] = .1
    patch["vx1"][:] = 4.
    patch["vx2"][:] = 0.
    patch["vx3"][:] = 0.
    patch["tr1"][:] = .3
    rows = injector.measure(patch, centres, edges, potential=lambda r: r*r)
    result = next(r for r in rows if (r["region"], r["method"]) == ("net", "linear_snapshot_flags"))
    volume = sphere.sum() * .05**3
    assert result["mass"] == pytest.approx(4. * volume)
    assert result["gas_energy"] == pytest.approx(.5 * 4.**3 * volume)
    assert result["tracer_mass"] == pytest.approx(.3 * 4. * volume)
    z, y, x = np.meshgrid(*centres[::-1], indexing="ij")
    phi_div = x*x + y*y + z*z + 2*x*(2 + x) + .05**2 / 4
    assert result["potential_energy"] == pytest.approx(4. * phi_div[sphere].sum() * .05**3)
    assert result["n_hll_fallback"] == 0


def test_shock_flag_needs_both_compression_and_pressure_jump():
    state = np.zeros((5, 5, 5, 6))
    state[..., 1] = 1.
    state[..., 3, 1] = 7.
    state[..., 3, 2] = -1.
    widths = [np.ones(5)] * 3
    assert injector._shock_mask(state, widths)[2, 2, 2]
    state[..., 3, 2] = 1.
    assert not injector._shock_mask(state, widths)[2, 2, 2]
    state[..., 3, 2] = -1.
    state[..., 3, 1] = 6.
    assert not injector._shock_mask(state, widths)[2, 2, 2]


def test_rejects_incomplete_sphere_and_nonpositive_pressure():
    patch, centres, edges, _ = uniform_patch()
    with pytest.raises(ValueError, match="cropped"):
        injector.measure({k: v[..., 6:] for k, v in patch.items()},
                         (centres[0][6:], *centres[1:]), (edges[0][6:], *edges[1:]))
    patch["prs"][20, 20, 20] = -1
    with pytest.raises(ValueError, match="nonpositive"):
        injector.measure(patch, centres, edges)
