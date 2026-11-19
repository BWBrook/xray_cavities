from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts/science"))
import calibrate_nozzle_flux as calibration
import measure_q031_fluxes as flux
from snapshot_energy import EnvironmentProfile


def model():
    radius = np.array([0., 8.*flux.UNIT_LENGTH_CM])
    ones = np.ones(2)
    env = EnvironmentProfile(radius, ones*calibration.SOLVER_DENSITY, ones*calibration.SOLVER_PRESSURE,
                             ones*0, ones*0, 0., 0., "fixture")
    return calibration.Jet(1.e44, 0.1, np.pi/12, 0.75, 0.2, 0.3, 1.e-6, env)


def mesh():
    edges = [np.linspace(-2., 2., n+1) for n in (40, 36, 38)]
    # The native reader preserves stored centre offsets within each physical cell.
    centres = [0.49 * node[:-1] + 0.51 * node[1:] for node in edges]
    return calibration.make_grid(centres, edges)


def test_cropped_stencil_agrees_with_dense_native_float32_input():
    grid, jet = mesh(), model()
    box = flux.derive_control_box(grid, injection_height_kpc=jet.source_radius,
                                  centre_kpc=(0., 0., 0.), padding_cells=2)
    dense = {name: value.astype("f4") for name, value in
             jet.state(grid.x[None, None, :], grid.y[None, :, None], grid.z[:, None, None]).items()}
    patch, small_box = calibration.face_patch(grid, box, 1)
    observed = calibration.sample_surfaces(jet, patch, small_box)
    for method in flux.CONTROL_RECONSTRUCTIONS:
        expected = flux.measure_control_surface(dense, grid, jet.environment, box, method)
        assert [row for row in observed if row["method"] == method] == [{"method": method, **row} for row in expected]


@pytest.mark.parametrize("factor", [1, 4, 8])
def test_subdivision_keeps_same_six_physical_faces(factor):
    grid = mesh()
    box = flux.derive_control_box(grid, injection_height_kpc=0.75, centre_kpc=(0., 0., 0.), padding_cells=1)
    patch, measured = calibration.face_patch(grid, box, factor)
    for axis, index in zip("xyz", "ijk", strict=True):
        old_lo, old_hi = getattr(box, index+"0"), getattr(box, index+"1")+1
        new_lo, new_hi = getattr(measured, index+"0"), getattr(measured, index+"1")+1
        assert new_hi - new_lo == factor * (old_hi - old_lo)
        np.testing.assert_array_equal(getattr(patch, axis+"_edges")[[new_lo, new_hi]],
                                      getattr(grid, axis+"_edges")[[old_lo, old_hi]])


def test_known_cone_conserves_kinetic_but_enthalpy_varies_across_boxes():
    jet = model()
    a, b = (calibration.continuum(jet, (h, h)) for h in (0.8, 1.6))
    assert a["kinetic_flux_outward_erg_s"] == b["kinetic_flux_outward_erg_s"]
    assert a["potential_flux_outward_erg_s"] == 0
    assert b["enthalpy_flux_outward_erg_s"]/a["enthalpy_flux_outward_erg_s"] == pytest.approx(2**(-4/3))
    assert a["kinetic_flux_outward_erg_s"] / a["mass_flux_outward_g_s"] == pytest.approx(
        0.5*(jet.speed*flux.UNIT_VELOCITY_CMS)**2)
    # Two equal counterjets point radially outward, including below the origin.
    state = jet.state(np.array([0., 0., 1.]), 0., np.array([-1., 1., 1.]))
    np.testing.assert_array_equal(state["vx3"], [-jet.speed, jet.speed, 0.])
