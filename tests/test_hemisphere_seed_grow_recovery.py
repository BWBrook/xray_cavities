from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
RECOVERY_SCRIPT = ROOT / "scripts/science/three_case_cavity_recovery.py"
SEED_GROW_SCRIPT = ROOT / "scripts/science/hemisphere_seed_grow_recovery.py"
SYNTHETIC_ROOT = (
    ROOT
    / "docs/science/assets/xray_cavity_production_validation_2026-07-23/"
    "failed_run/synthetic"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def modules():
    recovery = _load_module("three_case_cavity_recovery", RECOVERY_SCRIPT)
    method = _load_module("hemisphere_seed_grow_recovery", SEED_GROW_SCRIPT)
    return recovery, method


def _load_synthetic(case: str, product: str) -> dict[str, np.ndarray]:
    directory = SYNTHETIC_ROOT / case / product
    return {
        "corrected": np.loadtxt(
            directory / "xray_1kev_xraise_corrected_mjy_sr.tsv", delimiter="\t"
        ),
        "tracer": np.loadtxt(directory / "tracer_max_los.tsv", delimiter="\t"),
        "horizontal": np.loadtxt(directory / "x_kpc.tsv"),
        "vertical": np.loadtxt(directory / "z_kpc.tsv"),
    }


def _summarize_mask(recovery, mask, horizontal, vertical):
    area = float(recovery._cell_area_grid(horizontal, vertical)[mask].sum())
    component = recovery.Component(1, mask, area)
    return recovery.summarize_components(
        (component,), horizontal, vertical
    )[0]


@pytest.mark.skipif(not SYNTHETIC_ROOT.is_dir(), reason="local Goal 044 maps unavailable")
@pytest.mark.parametrize("case", ("axisymmetric", "nonaxisymmetric"))
@pytest.mark.parametrize(
    ("angle_deg", "product"),
    ((0, "direct0"), (45, "edge45"), (90, "edge90")),
)
def test_fixed_method_on_unique_goal044_synthetic_angles(
    modules, case: str, angle_deg: int, product: str
) -> None:
    recovery, method = modules
    values = _load_synthetic(case, product)

    result = method.recover_hemisphere_seed_grow(
        values["corrected"], values["horizontal"], values["vertical"]
    )

    assert (
        result.background_method
        == "fixture_informed_pipeline_validation_background"
    )
    assert result.background_diagnostics.degree == 6
    assert result.background_diagnostics.converged
    area = recovery._cell_area_grid(values["horizontal"], values["vertical"])
    _, zz = np.meshgrid(values["horizontal"], values["vertical"])
    for side, hemisphere_mask in (
        ("negative_z", zz < 0.0),
        ("positive_z", zz > 0.0),
    ):
        side_result = result.hemispheres[side]
        target_area = float(area[result.candidate_roi & hemisphere_mask].sum()) * 0.01
        seed_area = float(area[side_result.seed_mask].sum())
        strict_seed_area = float(
            area[
                result.candidate_roi
                & hemisphere_mask
                & (result.deficit > side_result.seed_threshold)
            ].sum()
        )
        assert strict_seed_area < target_area
        assert seed_area >= target_area

    if angle_deg == 45:
        # Preserve the invalidated radial result as a diagnostic while the
        # production segmentation uses the predeclared 2-D background.
        assert result.radial_outer_annulus_threshold == pytest.approx(
            0.5461837405130109
        )

    assert result.detected_sides == ("negative_z", "positive_z")
    truth = values["tracer"] >= 5.0e-3
    for side, hemisphere_mask in (
        ("negative_z", zz < 0.0),
        ("positive_z", zz > 0.0),
    ):
        side_result = result.hemispheres[side]
        assert side_result.primary is not None
        assert not side_result.primary.summary.crosses_z_zero
        metrics = method.area_weighted_truth_metrics(
            side_result.primary.mask,
            truth & hemisphere_mask,
            values["horizontal"],
            values["vertical"],
        )
        assert metrics.precision >= 0.90
        assert metrics.intersection_over_union >= 0.50
        assert metrics.centroid_error_kpc <= 10.0
        assert metrics.area_absolute_relative_error <= 0.25
        truth_summary = _summarize_mask(
            recovery,
            truth & hemisphere_mask,
            values["horizontal"],
            values["vertical"],
        )
        predicted_volume = side_result.primary.summary.volumes_kpc3[
            "geometric_depth"
        ]
        truth_volume = truth_summary.volumes_kpc3["geometric_depth"]
        assert abs(predicted_volume - truth_volume) / truth_volume <= 0.30
        fragment_area = sum(
            fragment.area_kpc2
            for fragment in side_result.secondary_fragments
        )
        assert fragment_area / side_result.primary.area_kpc2 <= 0.10
        assert method.is_resolved_geometry(
            side_result.primary.mask,
            values["horizontal"],
            values["vertical"],
        )


@pytest.mark.skipif(not SYNTHETIC_ROOT.is_dir(), reason="local Goal 044 maps unavailable")
def test_polynomial_background_degree_sweep_is_stable_not_a_knife_edge(
    modules,
) -> None:
    _, method = modules
    values = _load_synthetic("nonaxisymmetric", "edge45")

    report = method.polynomial_background_stability(
        values["corrected"], values["horizontal"], values["vertical"]
    )

    assert tuple(item.degree for item in report.degrees) == (5, 6, 7)
    assert all(item.converged for item in report.degrees)
    assert all(
        np.isfinite(item.condition_number) and item.condition_number < 1.0e6
        for item in report.degrees
    )
    assert all(
        np.isfinite(item.blocked_cv_rmse_log_intensity)
        for item in report.degrees
    )
    assert report.degree6_not_numerical_knife_edge


def test_primary_component_and_secondary_fragments_are_explicit(modules) -> None:
    _, method = modules
    axis = np.linspace(-200.0, 200.0, 101)
    xx, zz = np.meshgrid(axis, axis)
    corrected = np.ones_like(xx)
    large = (xx / 18.0) ** 2 + ((zz + 55.0) / 20.0) ** 2 <= 1.0
    small = ((xx - 48.0) / 11.0) ** 2 + ((zz + 76.0) / 13.0) ** 2 <= 1.0
    corrected[large | small] = 0.5

    result = method.recover_hemisphere_seed_grow(corrected, axis, axis)

    negative = result.hemispheres["negative_z"]
    assert negative.primary is not None
    assert len(negative.secondary_fragments) == 1
    assert negative.primary.area_kpc2 > negative.secondary_fragments[0].area_kpc2
    assert negative.primary.summary.area_kpc2 == pytest.approx(
        negative.primary.area_kpc2
    )
    np.testing.assert_array_equal(negative.mask, large | small)
    assert result.hemispheres["positive_z"].primary is None


@pytest.mark.skipif(not SYNTHETIC_ROOT.is_dir(), reason="local Goal 044 maps unavailable")
@pytest.mark.parametrize("case", ("axisymmetric", "nonaxisymmetric"))
@pytest.mark.parametrize("product", ("direct0", "edge45", "edge90"))
def test_smooth_background_control_has_zero_detections(
    modules, case: str, product: str
) -> None:
    _, method = modules
    values = _load_synthetic(case, product)
    control = method.make_smooth_background_control(
        values["corrected"], values["horizontal"], values["vertical"]
    )

    result = method.recover_hemisphere_seed_grow(
        control, values["horizontal"], values["vertical"]
    )

    assert result.detected_sides == ()
    assert not np.any(result.observer_mask)


@pytest.mark.skipif(not SYNTHETIC_ROOT.is_dir(), reason="local Goal 044 maps unavailable")
@pytest.mark.parametrize("case", ("axisymmetric", "nonaxisymmetric"))
@pytest.mark.parametrize("product", ("direct0", "edge45", "edge90"))
@pytest.mark.parametrize("retained_side", ("negative_z", "positive_z"))
def test_one_sided_ablation_detects_exactly_the_retained_side(
    modules, case: str, product: str, retained_side: str
) -> None:
    _, method = modules
    values = _load_synthetic(case, product)
    original = values["corrected"].copy()
    smooth = method.make_smooth_background_control(
        values["corrected"], values["horizontal"], values["vertical"]
    )
    control = method.make_one_sided_ablation_control(
        values["corrected"],
        values["horizontal"],
        values["vertical"],
        retained_side=retained_side,
    )

    result = method.recover_hemisphere_seed_grow(
        control, values["horizontal"], values["vertical"]
    )

    np.testing.assert_array_equal(values["corrected"], original)
    _, zz = np.meshgrid(values["horizontal"], values["vertical"])
    ablated_side = zz >= 0.0 if retained_side == "negative_z" else zz <= 0.0
    np.testing.assert_allclose(
        control[ablated_side], smooth[ablated_side], rtol=0.0, atol=0.0
    )
    assert result.detected_sides == (retained_side,)


def test_truth_metrics_use_physical_area_and_report_geometry_errors(modules) -> None:
    _, method = modules
    horizontal = np.array([0.0, 1.0, 4.0])
    vertical = np.array([0.0, 2.0])
    observer = np.zeros((2, 3), dtype=bool)
    truth = np.zeros_like(observer)
    observer[0, [0, 2]] = True
    truth[0, [0, 1]] = True

    metrics = method.area_weighted_truth_metrics(
        observer, truth, horizontal, vertical
    )

    assert metrics.predicted_area_kpc2 == pytest.approx(8.0)
    assert metrics.truth_area_kpc2 == pytest.approx(6.0)
    assert metrics.intersection_area_kpc2 == pytest.approx(2.0)
    assert metrics.precision == pytest.approx(0.25)
    assert metrics.recall == pytest.approx(1.0 / 3.0)
    assert metrics.intersection_over_union == pytest.approx(1.0 / 6.0)
    assert metrics.centroid_x_error_kpc == pytest.approx(7.0 / 3.0)
    assert metrics.centroid_z_error_kpc == pytest.approx(0.0)
    assert metrics.centroid_error_kpc == pytest.approx(7.0 / 3.0)
    assert metrics.area_signed_relative_error == pytest.approx(1.0 / 3.0)
    assert metrics.area_absolute_relative_error == pytest.approx(1.0 / 3.0)


def test_resolved_geometry_rejects_sparse_or_rank_deficient_masks(modules) -> None:
    _, method = modules
    axis = np.arange(-2.0, 3.0)
    one_row = np.zeros((5, 5), dtype=bool)
    one_row[2, 1:4] = True
    diagonal = np.eye(5, dtype=bool)
    resolved = np.zeros((5, 5), dtype=bool)
    resolved[1:4, 1:4] = True

    assert not method.is_resolved_geometry(one_row, axis, axis)
    assert not method.is_resolved_geometry(diagonal, axis, axis)
    assert method.geometry_resolution(diagonal, axis, axis).covariance_rank == 1
    assert method.is_resolved_geometry(resolved, axis, axis)
