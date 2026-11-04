from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "scripts" / "science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))

import independent_bow_shock as shock
import validate_independent_bow_shock as validation


@pytest.fixture(scope="module")
def production_grid() -> shock.Grid3D:
    return shock.parse_pluto_grid(validation.PRODUCTION_GRID)


@pytest.fixture(scope="module")
def atmosphere() -> validation.Atmosphere:
    return validation.Atmosphere.read(validation.GROUP_ATMOSPHERE)


def test_retained_grid_is_exact_production_stretched_geometry(production_grid: shock.Grid3D) -> None:
    assert production_grid.shape == (1014, 960, 960)
    dx, dy, dz = production_grid.widths
    assert dx.min() == pytest.approx(0.05)
    assert dx.max() / dx.min() > 30.0
    assert dz.max() / dz.min() > 40.0
    assert np.allclose(production_grid.x, 0.5 * (production_grid.x_edges[:-1] + production_grid.x_edges[1:]))


@pytest.mark.parametrize("mach", [1.1, 1.5, 3.0])
def test_rankine_hugoniot_inversions_are_exact(mach: float) -> None:
    pressure, density, temperature = shock.rh_jump_ratios(mach)
    assert float(shock.mach_from_pressure_ratio(pressure)) == pytest.approx(mach)
    assert float(shock.mach_from_density_ratio(density)) == pytest.approx(mach)
    assert temperature > 1.0


@pytest.mark.parametrize("mach", [1.1, 1.5, 3.0])
@pytest.mark.parametrize("normal", [(1.0, 0.0, 0.0), (1.0, 2.0, 3.0)])
def test_exact_shocks_recover_position_mach_and_direction_on_native_grid(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
    mach: float,
    normal: tuple[float, float, float],
) -> None:
    grid = validation.local_patch(production_grid, (45.0, -25.0, 70.0))
    fields, truth = validation.exact_shock(
        grid, atmosphere, mach=mach, normal_xyz=validation.unit(normal),
    )
    row = validation.evaluate_shock(fields, grid, truth, mach=mach, mach_min=1.1)
    assert row["positive_gate_pass"]
    assert row["position_error_cells_p95"] <= 2.0
    assert row["mach_pressure_median"] == pytest.approx(mach, rel=0.1)
    assert row["mach_density_median"] == pytest.approx(mach, rel=0.1)
    assert row["normal_abs_dot_median"] > 0.75


def test_threshold_sensitivity_has_expected_positive_selection(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
) -> None:
    grid = validation.local_patch(production_grid, (0.0, 0.0, 0.0))
    fields, truth = validation.exact_shock(
        grid, atmosphere, mach=1.1, normal_xyz=validation.unit((1.0, 1.0, 0.0)),
    )
    low = validation.evaluate_shock(fields, grid, truth, mach=1.1, mach_min=1.05)
    baseline = validation.evaluate_shock(fields, grid, truth, mach=1.1, mach_min=1.1)
    high = validation.evaluate_shock(fields, grid, truth, mach=1.1, mach_min=1.2)
    assert low["positive_gate_pass"]
    assert baseline["positive_gate_pass"]
    assert not high["detected"]
    assert high["positive_gate_pass"]


def test_compression_plateau_yields_one_axis_candidate_per_stencil(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
) -> None:
    grid = validation.local_patch(production_grid, (0.0, 0.0, 0.0))
    fields, _ = validation.exact_shock(
        grid, atmosphere, mach=1.5, normal_xyz=validation.unit((1.0, 0.0, 0.0)),
    )
    found = shock.collect_shock_candidates_tiled(
        fields, grid, mach_min=1.1, tile_shape_zyx=(10, 11, 12), halo_cells=4,
    )
    assert len(found)
    by_tangential_stencil: dict[tuple[int, int], set[int]] = {}
    for z, y, x in found.indices_zyx:
        by_tangential_stencil.setdefault((int(z), int(y)), set()).add(int(x))
    assert max(map(len, by_tangential_stencil.values())) == 1


@pytest.mark.parametrize("contrast", [10.0, 100.0])
def test_pressure_balanced_contacts_do_not_flag(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
    contrast: float,
) -> None:
    grid = validation.local_patch(production_grid, (45.0, -25.0, 70.0))
    fields = validation.pressure_balanced_contact(
        grid, atmosphere, contrast=contrast, normal_xyz=validation.unit((1.0, 2.0, 3.0)),
    )
    for mach_min in validation.MACH_THRESHOLDS:
        assert len(shock.collect_shock_candidates_tiled(fields, grid, mach_min=mach_min)) == 0


def test_rarefaction_does_not_flag(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
) -> None:
    grid = validation.local_patch(production_grid, (0.0, 0.0, 0.0))
    fields = validation.rarefaction_fan(grid, atmosphere, normal_xyz=validation.unit((1.0, 1.0, 0.0)))
    for mach_min in validation.MACH_THRESHOLDS:
        assert len(shock.collect_shock_candidates_tiled(fields, grid, mach_min=mach_min)) == 0


def test_sound_wave_is_preserved_as_a_low_threshold_counterexample(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
) -> None:
    grid = validation.local_patch(production_grid, (0.0, 0.0, 0.0))
    fields = validation.isentropic_sound_wave(
        grid, atmosphere, normal_xyz=validation.unit((1.0, 2.0, 3.0)),
    )
    low = shock.collect_shock_candidates_tiled(fields, grid, mach_min=1.05)
    baseline = shock.collect_shock_candidates_tiled(fields, grid, mach_min=1.1)
    assert len(low) > 0
    assert np.median(low.mach_pressure) == pytest.approx(1.085, abs=0.002)
    assert np.median(low.mach_density) == pytest.approx(1.085, abs=0.002)
    assert len(baseline) == 0


def test_tiled_and_in_memory_results_match(
    production_grid: shock.Grid3D,
    atmosphere: validation.Atmosphere,
) -> None:
    grid = validation.local_patch(production_grid, (45.0, -25.0, 70.0))
    fields, _ = validation.exact_shock(
        grid, atmosphere, mach=1.5, normal_xyz=validation.unit((1.0, 2.0, 3.0)),
    )
    direct = shock.find_shock_candidates(fields, grid, mach_min=1.1)
    tiled = shock.collect_shock_candidates_tiled(
        fields, grid, mach_min=1.1, tile_shape_zyx=(11, 13, 12), halo_cells=4,
    )
    assert set(map(tuple, direct.indices_zyx)) == set(map(tuple, tiled.indices_zyx))
    direct_by_index = {tuple(index): value for index, value in zip(direct.indices_zyx, direct.mach_pressure, strict=True)}
    for index, value in zip(tiled.indices_zyx, tiled.mach_pressure, strict=True):
        assert value == pytest.approx(direct_by_index[tuple(index)], rel=1.0e-12)


class SliceTracker:
    def __init__(self, values: np.ndarray):
        self.values = values
        self.shape = values.shape
        self.requests: list[tuple[slice, slice, slice]] = []

    def __getitem__(self, item: tuple[slice, slice, slice]) -> np.ndarray:
        self.requests.append(item)
        return self.values[item]


def test_tiled_reader_never_requests_a_full_3d_field(production_grid: shock.Grid3D) -> None:
    grid = validation.local_patch(production_grid, (0.0, 0.0, 0.0), cells=33)
    base = np.ones(grid.shape, dtype=float)
    fields = {
        "rho": SliceTracker(base),
        "prs": SliceTracker(base),
        "vx1": SliceTracker(np.zeros_like(base)),
        "vx2": SliceTracker(np.zeros_like(base)),
        "vx3": SliceTracker(np.zeros_like(base)),
    }
    tile_shape = (9, 10, 11)
    halo = 4
    assert list(shock.iter_shock_candidates_tiled(
        fields, grid, tile_shape_zyx=tile_shape, halo_cells=halo,
    )) == []
    for tracked in fields.values():
        assert tracked.requests
        for request in tracked.requests:
            extents = tuple(item.stop - item.start for item in request)
            assert all(extent <= tile + 2 * halo for extent, tile in zip(extents, tile_shape, strict=True))
            assert extents != grid.shape


def test_compact_science_gate_reports_no_promotion() -> None:
    result = validation.run_validation(compact=True)
    assert result["summary"]["baseline_1.1_gate_pass"]
    assert not result["summary"]["all_threshold_validation_pass"]
    assert result["summary"]["promotion_status"] == "FAIL_NO_PROMOTION"
    assert result["summary"]["sound_wave_1.05_flagged_scenarios"] == 1
