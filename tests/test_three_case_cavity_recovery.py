from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/three_case_cavity_recovery.py")


def load_module():
    spec = importlib.util.spec_from_file_location("three_case_cavity_recovery", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validates_finite_monotonic_map_and_rejects_bad_axes() -> None:
    module = load_module()
    values = np.ones((3, 4), dtype=float)
    x_kpc = np.array([-2.0, -1.0, 0.0, 1.0])
    z_kpc = np.array([-1.0, 0.0, 1.0])

    assert module.validate_map_and_axes(values, x_kpc, z_kpc) is None

    with pytest.raises(ValueError, match="finite"):
        module.validate_map_and_axes(np.array([[1.0, np.nan]]), [0.0, 1.0], [0.0])
    with pytest.raises(ValueError, match="strictly monotonic"):
        module.validate_map_and_axes(values, [0.0, 1.0, 1.0, 2.0], z_kpc)


def test_physical_gaussian_scale_uses_axis_specific_pixel_sigmas() -> None:
    module = load_module()
    x_kpc = np.arange(-6.0, 7.0, 2.0)
    z_kpc = np.arange(-10.0, 11.0, 5.0)

    sigmas = module.pixel_sigmas_for_physical_scale(x_kpc, z_kpc, scale_kpc=20.0)

    assert sigmas == pytest.approx((4.0, 10.0))


def test_normalized_background_has_no_roi_edge_deficit() -> None:
    module = load_module()
    x_kpc = np.arange(8.0)
    z_kpc = np.arange(8.0)
    values = np.full((8, 8), 7.0)
    roi = np.zeros_like(values, dtype=bool)
    roi[1:-1, 1:-1] = True

    background = module.compute_physical_gaussian_background(
        values, x_kpc, z_kpc, scale_kpc=2.0, roi_mask=roi
    )

    np.testing.assert_allclose(background[roi], 7.0, atol=1e-12)


def test_radial_background_recovers_bipolar_deficits_without_field_edge() -> None:
    module = load_module()
    x_kpc = np.linspace(-180.0, 180.0, 361)
    z_kpc = np.linspace(-180.0, 180.0, 361)
    xx, zz = np.meshgrid(x_kpc, z_kpc)
    radius = np.hypot(xx, zz)
    halo = 1000.0 / (1.0 + (radius / 55.0) ** 2)
    cavities = ((xx / 18.0) ** 2 + ((zz - 48.0) / 25.0) ** 2 <= 1.0) | (
        (xx / 18.0) ** 2 + ((zz + 48.0) / 25.0) ** 2 <= 1.0
    )
    xray = halo.copy()
    xray[cavities] *= 0.55
    # A deliberately dark edge ring must not enter the candidate aperture.
    xray[(radius > 165.0) & (radius < 178.0)] *= 0.4
    background_roi = radius <= 180.0
    candidate_roi = radius <= 120.0

    background = module.compute_azimuthal_median_background(
        xray,
        x_kpc,
        z_kpc,
        background_roi=background_roi,
        radial_bin_kpc=5.0,
        radial_smoothing_kpc=10.0,
    )
    deficit = module.compute_fractional_deficit(xray, background)
    mask, _ = module.select_low_percentile_candidate(
        deficit, candidate_roi, fraction=3.0, high_values_are_candidates=True
    )
    selected = module.label_and_filter_components(
        mask, x_kpc, z_kpc, min_area_kpc2=25.0, connectivity=8
    )
    summaries = module.summarize_components(selected.components, x_kpc, z_kpc)
    retained_mask = np.zeros_like(mask)
    for component in selected.components:
        retained_mask |= component.mask

    assert len(summaries) == 2
    assert sorted(np.sign(summary.centroid_z_kpc) for summary in summaries) == [-1.0, 1.0]
    assert all(35.0 < abs(summary.centroid_z_kpc) < 70.0 for summary in summaries)
    assert all(abs(summary.centroid_x_kpc) < 5.0 for summary in summaries)
    assert np.count_nonzero(retained_mask & ~cavities) == 0
    assert not np.any(mask & (radius > 120.0))


def test_roi_and_fractional_deficit_candidate_are_physical_and_tracer_blind() -> None:
    module = load_module()
    x_kpc = np.linspace(-3.0, 3.0, 7)
    z_kpc = np.linspace(-3.0, 3.0, 7)
    roi = module.build_elliptical_roi(x_kpc, z_kpc, 2.5, 2.5)
    background = np.ones((7, 7))
    xray = np.ones((7, 7))
    xray[3, 3] = 0.1
    deficit = module.compute_fractional_deficit(xray, background)
    observer_mask, _ = module.select_low_percentile_candidate(
        deficit, roi, fraction=10.0, high_values_are_candidates=True
    )
    tracer_a = np.zeros_like(xray)
    tracer_b = np.ones_like(xray)
    metrics_a = module.tracer_validation_metrics(observer_mask, tracer_a, threshold=0.5)
    metrics_b = module.tracer_validation_metrics(observer_mask, tracer_b, threshold=0.5)

    assert roi[3, 3]
    assert observer_mask[3, 3]
    np.testing.assert_array_equal(observer_mask, observer_mask.copy())
    assert metrics_a != metrics_b


def test_area_fraction_candidate_is_physical_across_pixel_spacings() -> None:
    module = load_module()
    selected_areas = []
    for spacing in (1.0, 2.0):
        axis = np.arange(-20.0, 20.0 + spacing, spacing)
        xx, zz = np.meshgrid(axis, axis)
        values = -(xx**2 + zz**2) + 0.01 * zz
        roi = xx**2 + zz**2 <= 15.0**2

        mask, _ = module.select_area_fraction_candidate(
            values,
            roi,
            axis,
            axis,
            fraction=10.0,
            high_values_are_candidates=True,
        )
        area = module._cell_area_grid(axis, axis)
        selected_areas.append(float(area[mask].sum()))
        target = float(area[roi].sum()) * 0.10
        assert selected_areas[-1] == pytest.approx(target, abs=spacing**2 * 2.0)

    assert selected_areas[0] == pytest.approx(selected_areas[1], rel=0.06)


def test_component_area_filter_is_in_kpc2() -> None:
    module = load_module()
    candidate = np.zeros((5, 5), dtype=bool)
    candidate[1:3, 1:3] = True
    x_kpc = np.arange(0.0, 10.0, 2.0)
    z_kpc = np.arange(0.0, 10.0, 2.0)

    selected = module.label_and_filter_components(candidate, x_kpc, z_kpc, min_area_kpc2=15.0)

    assert len(selected.components) == 1
    assert selected.components[0].area_kpc2 == pytest.approx(16.0)
    assert selected.cell_area_kpc2 == pytest.approx(4.0)


def test_component_moments_recover_synthetic_uniform_ellipse() -> None:
    module = load_module()
    x_kpc = np.linspace(-20.0, 20.0, 161)
    z_kpc = np.linspace(-12.0, 12.0, 97)
    xx, zz = np.meshgrid(x_kpc, z_kpc)
    candidate = (xx / 10.0) ** 2 + (zz / 6.0) ** 2 <= 1.0
    selected = module.label_and_filter_components(candidate, x_kpc, z_kpc, min_area_kpc2=25.0)

    summary = module.summarize_components(selected.components, x_kpc, z_kpc)[0]

    assert summary.centroid_x_kpc == pytest.approx(0.0, abs=0.2)
    assert summary.centroid_z_kpc == pytest.approx(0.0, abs=0.2)
    assert summary.major_semiaxis_kpc == pytest.approx(10.0, rel=0.05)
    assert summary.minor_semiaxis_kpc == pytest.approx(6.0, rel=0.05)
    assert summary.crosses_z_zero
    assert summary.volumes_kpc3["geometric_depth"] == pytest.approx(
        4.0 / 3.0 * np.pi * 10.0 * 6.0 * np.sqrt(60.0), rel=0.1
    )


def test_tracer_metrics_are_validation_only_and_do_not_change_observer_mask() -> None:
    module = load_module()
    observer_mask = np.zeros((4, 4), dtype=bool)
    observer_mask[1:3, 1:3] = True
    tracer = np.zeros((4, 4), dtype=float)
    tracer[2:, 2:] = 1.0
    before = observer_mask.copy()

    metrics = module.tracer_validation_metrics(observer_mask, tracer, threshold=0.5)

    np.testing.assert_array_equal(observer_mask, before)
    assert metrics["intersection_over_union"] == pytest.approx(1.0 / 7.0)
    assert metrics["dice"] == pytest.approx(2.0 / 8.0)
    assert metrics["xray_precision"] == pytest.approx(1.0 / 4.0)
    assert metrics["tracer_recall"] == pytest.approx(1.0 / 4.0)


def test_accepted_manifest_has_nine_deterministic_triples_and_archive_sources() -> None:
    module = load_module()

    manifest = module.accepted_case_view_manifest()

    assert len(manifest) == 9
    assert [(item.case, item.view) for item in manifest] == [
        (case, view) for case in ("C-HI", "C-LO", "G-LO") for view in ("0deg", "45deg", "90deg")
    ]
    assert sum(item.source_type == "refined_tar_archive" for item in manifest) == 2
    assert all(item.source_type == "refined_tar_archive" for item in manifest if item.case == "C-HI" and item.view != "0deg")
    assert all(item.source_type == "local_accepted" for item in manifest if not (item.case == "C-HI" and item.view != "0deg"))
    assert all(item.corrected_xray.endswith("xray_1kev_xraise_corrected_mjy_sr.tsv") for item in manifest)
    assert all(item.tracer_max_los.endswith("tracer_max_los.tsv") for item in manifest)
    assert all(item.horizontal_axis.endswith("x_kpc.tsv") for item in manifest)
    assert all(item.z_axis.endswith("z_kpc.tsv") for item in manifest)
