from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/snapshot_shock_energy.py")


def load_module():
    science_dir = str(SCRIPT.resolve().parent)
    if science_dir not in sys.path:
        sys.path.insert(0, science_dir)
    spec = importlib.util.spec_from_file_location("snapshot_shock_energy", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_control_calibration_uses_prespecified_floors_and_zero_joint_false_positives() -> None:
    module = load_module()
    pressure = np.linspace(0.0, 0.003, 20_000)
    density = np.linspace(0.0, 0.002, 20_000)
    entropy = np.linspace(0.0, 0.001, 20_000)

    thresholds = module.derive_control_thresholds(
        pressure_excess_samples=pressure,
        density_excess_samples=density,
        entropy_excess_samples=entropy,
    )

    assert thresholds.pressure_excess == module.PRESSURE_EXCESS_FLOOR
    assert thresholds.density_excess == module.DENSITY_EXCESS_FLOOR
    assert thresholds.entropy_excess == module.ENTROPY_EXCESS_FLOOR
    assert thresholds.control_joint_exceedance_fraction == 0.0


def test_front_requires_joint_compression_while_processed_mask_retains_entropy_component() -> None:
    module = load_module()
    thresholds = module.ShockThresholds(
        pressure_excess=0.05,
        density_excess=0.03,
        entropy_excess=0.02,
        control_sample_count=100,
        control_joint_exceedance_fraction=0.0,
        pressure_control_quantile=0.0,
        density_control_quantile=0.0,
        entropy_control_quantile=0.0,
        pressure_control_max=0.0,
        density_control_max=0.0,
        entropy_control_max=0.0,
    )
    pressure = np.asarray([1.10, 1.01, 1.10])
    density = np.asarray([1.05, 1.00, 1.01])
    entropy = np.asarray([0.03, 0.03, 0.005])
    ambient = np.ones(3, dtype=bool)

    processed, front = module.build_processed_and_front_masks(
        pressure_ratio=pressure,
        density_ratio=density,
        entropy_delta=entropy,
        ambient_mask=ambient,
        thresholds=thresholds,
        factor=1.0,
    )

    assert processed.tolist() == [True, True, False]
    assert front.tolist() == [True, False, False]


def test_seeded_component_selection_excludes_unconnected_entropy_island() -> None:
    module = load_module()
    candidate = np.zeros((8, 8, 8), dtype=bool)
    candidate[1:4, 1:4, 1:4] = True
    candidate[5:7, 5:7, 5:7] = True
    seed = np.zeros_like(candidate)
    seed[1, 1, 1] = True

    selected, diagnostics = module.select_seeded_components(candidate, seed, minimum_cells=5)

    assert diagnostics["status"] == "quantitative_seeded_component"
    assert diagnostics["selected_component_count"] == 1
    assert np.all(selected[1:4, 1:4, 1:4])
    assert not np.any(selected[5:7, 5:7, 5:7])


@pytest.mark.parametrize("tracer", [0.0, 5.0e-4, 1.0e-3])
def test_shock_energy_slice_uses_full_cells_and_cellwise_baseline(tracer: float) -> None:
    module = load_module()
    shape = (1, 1)
    values = module.shock_energy_slice(
        rho=np.full(shape, 2.0),
        pressure=np.full(shape, 4.0),
        velocity_squared=np.full(shape, 4.0),
        tracer=np.full(shape, tracer),
        baseline_rho=np.ones(shape),
        baseline_pressure=np.ones(shape),
        baseline_velocity_squared=np.zeros(shape),
        volume_kpc3=np.ones(shape),
        potential_cm2_s2=np.full(shape, 5.0),
        mask=np.ones(shape, dtype=bool),
    )

    assert values["thermal_delta_erg"] == pytest.approx(
        3.0 / (module.GAMMA_GAS - 1.0) * module.UNIT_ENERGY_ERG
    )
    assert values["kinetic_delta_erg"] == pytest.approx(4.0 * module.UNIT_ENERGY_ERG)
    assert values["gravitational_delta_erg"] == pytest.approx(
        module.UNIT_DENSITY_CGS * module.UNIT_LENGTH_CM**3 * 5.0
    )
    assert values["irreversible_heating_erg"] == pytest.approx(
        (4.0 - 2.0**module.GAMMA_GAS)
        / (module.GAMMA_GAS - 1.0)
        * module.UNIT_ENERGY_ERG
    )
    assert values["total_delta_erg"] == pytest.approx(
        values["thermal_delta_erg"]
        + values["kinetic_delta_erg"]
        + values["gravitational_delta_erg"]
    )
    assert values["ambient_weighted_volume_kpc3"] == values["mask_volume_kpc3"] == 1.0
    assert values["ambient_weighted_mass_g"] == pytest.approx(
        2.0 * module.UNIT_DENSITY_CGS * module.UNIT_LENGTH_CM**3
    )


@pytest.mark.parametrize("tracer", [np.nextafter(1.0e-3, np.inf), np.nan, np.inf])
def test_shock_energy_rejects_cocoon_overlap_and_nonfinite_tracer(tracer: float) -> None:
    module = load_module()
    one = np.ones((1, 1))
    with pytest.raises(ValueError, match="cocoon|tracer must be finite"):
        module.shock_energy_slice(
            rho=one, pressure=one, velocity_squared=one,
            tracer=np.full_like(one, tracer), baseline_rho=one,
            baseline_pressure=one, baseline_velocity_squared=one,
            volume_kpc3=one, potential_cm2_s2=one, mask=one.astype(bool),
        )
