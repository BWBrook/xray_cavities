"""Analytic potential-energy transport across the reconstructed near-injector cells."""

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from entropy_localisation import D, L, V, cell_budgets, patch_geometry


class QuadraticPotential:
    def potential_at_radius(self, radius_cm):
        return (radius_cm / L) ** 2 * V**2


def test_uniform_flow_in_quadratic_potential_has_exact_signed_cell_transport():
    edges = np.arange(-19, 20) / 20.0
    centres = 0.5 * (edges[:-1] + edges[1:])
    nz = len(centres)
    shape = (nz, nz, nz)
    z, y, x = np.ix_(centres, centres, centres)
    rho, pressure = 1.2, 0.25
    vx, vy, vz = 0.7, -0.2, 0.1
    patch = {
        key: np.full(shape, value)
        for key, value in zip(
            ("rho", "prs", "vx1", "vx2", "vx3", "tr1"), (rho, pressure, vx, vy, vz, 0.5), strict=True
        )
    }
    for key in "xyz":
        patch[key] = centres
        patch[key + "_edges"] = edges
    geom = patch_geometry(patch, QuadraticPotential())
    stock, outward_flux, tracer = cell_budgets(patch, geom)
    _, shells, phi, volume, _ = geom
    valid = shells >= 0
    continuum = 2 * rho * (vx * x + vy * y + vz * z) * volume * D * L**2 * V**3
    expected_stock = (1.5 * pressure + rho * (0.5 * (vx**2 + vy**2 + vz**2) + phi)) * volume * D * L**3 * V**2
    np.testing.assert_allclose(stock, expected_stock)
    assert np.all(tracer == 0.5)
    for method in outward_flux:
        np.testing.assert_allclose(
            outward_flux[method][valid],
            continuum[valid],
            rtol=3.0e-12,
            atol=np.max(np.abs(continuum[valid])) * 2.0e-13,
        )
