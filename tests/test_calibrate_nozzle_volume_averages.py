import math
import sys
from pathlib import Path

import numpy as np
import pytest

SCIENCE = Path(__file__).resolve().parents[1] / "scripts/science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))
import calibrate_nozzle_volume_averages as calibration


class ConstantCone:
    angle = math.atan(0.2)

    def state(self, x, y, z):
        cone = np.hypot(x, y) <= z * math.tan(self.angle)
        return {
            "rho": np.where(cone, 2.0, 1.0), "prs": np.where(cone, 0.1, 0.2),
            "vx1": np.zeros_like(x), "vx2": np.zeros_like(y), "vx3": np.where(cone, 0.5, 0.0),
        }


def test_mixed_cell_recovers_integrated_mass_momentum_and_energy():
    jet = ConstantCone()
    bounds = ((0.0, 1.0), (0.0, 1.0), (1.0, 2.0))
    fraction = (math.pi / 4) * math.tan(jet.angle)**2 * (2**3 - 1) / 3
    rho, pressure, vx, vy, vz = calibration.average_primitives(jet, bounds, 16)
    gamma = calibration.flux.GAMMA_GAS
    thermal = (0.1 * fraction + 0.2 * (1.0 - fraction)) / (gamma - 1.0)
    kinetic = 0.5 * 2.0 * 0.5**2 * fraction
    assert rho == pytest.approx(1.0 + fraction, abs=2e-13, rel=0)
    assert (vx, vy) == (0.0, 0.0)
    assert rho * vz == pytest.approx(fraction, abs=2e-13, rel=0)
    cell_energy = pressure / (gamma - 1.0) + 0.5 * rho * vz**2
    assert cell_energy == pytest.approx(thermal + kinetic, abs=2e-13, rel=0)
    assert pressure > thermal * (gamma - 1.0)


@pytest.mark.parametrize(("bounds", "expected"), [
    (((0., .05), (0., .05), (1., 1.1)), (2., .1, 0., 0., .5)),
    (((.5, .6), (.5, .6), (1., 1.1)), (1., .2, 0., 0., 0.)),
])
def test_uniform_cell_preserves_the_primitive_state(bounds, expected):
    actual = calibration.average_primitives(ConstantCone(), bounds, 4)
    assert actual == pytest.approx(expected, abs=8e-15, rel=0)
