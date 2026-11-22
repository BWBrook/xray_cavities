import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from measure_entropy_injector_snapshot import D, L, V, measure_patch


def test_diverging_uniform_streams_preserve_flux_units_gauge_and_tracer():
    centres = (np.arange(-19, 19, dtype=float) + 0.5) * 0.05
    edges = np.arange(-19, 20, dtype=float) * 0.05
    z, y, x = np.meshgrid(centres, centres, centres, indexing="ij")
    radius2 = x*x + y*y + z*z
    density, pressure, speed, tracer, phi = 2., 0.3, 0.04, 0.7, -0.9
    ones = np.ones_like(x)
    patch = dict(rho=density*ones, prs=pressure*ones, vx1=speed*np.sign(x),
                 vx2=0.*ones, vx3=0.*ones, tr1=tracer*ones)

    class ConstantPotential:
        def potential_at_radius(self, radius):
            return np.full_like(radius, phi * V**2)

    result = measure_patch(patch, (centres,)*3, (edges,)*3, ConstantPotential())
    for radius in (0.75, 0.85):
        if radius == 0.75:
            rates = {m: regions["net"] for m, regions in result["rates"].items()}
            for m, row in rates.items():
                regions = result["rates"][m]
                assert row["mass_g_s"] == pytest.approx(regions["cap"]["mass_g_s"] + regions["stationary"]["mass_g_s"])
            stock = result["flagged_storage"]
        else:
            outer = result["spheres"]["0.85"]
            rates, stock = outer["rates"], outer["storage"]
        cells = radius2 <= radius**2
        projected_area = np.count_nonzero(np.any(cells, axis=2)) * 0.05**2
        volume = np.count_nonzero(cells) * 0.05**3
        mdot = 2 * projected_area * speed * density * D * L**2 * V
        energy_density = 1.5*pressure + 0.5*density*speed**2
        power = 2 * projected_area * speed * (energy_density + pressure) * D * L**2 * V**3
        for row in rates.values():
            assert row["mass_g_s"] == pytest.approx(mdot)
            assert row["tracer_mass_g_s"] == pytest.approx(mdot*tracer)
            assert row["gas_energy_erg_s"] == pytest.approx(power)
            assert row["total_energy_erg_s"] == pytest.approx(power + mdot*phi*V**2)
        assert stock["total_erg"] == pytest.approx((energy_density + density*phi)*volume*D*L**3*V**2)
        assert stock["tagged_mass_g"] == pytest.approx(tracer*density*volume*D*L**3)
