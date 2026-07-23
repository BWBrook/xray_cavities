#!/usr/bin/env python3
"""Tracer-blind hemisphere-aware cavity seed and hysteresis growth.

The one-percent physical-area tail is used only to seed each predeclared jet
hemisphere. Seeds grow through connected fractional-deficit support above a
robust outer-annulus null threshold. Production geometry uses a robust
normalized two-dimensional log-intensity background; the earlier radial
background remains an explicit diagnostic and independent negative control.
Tracer truth is intentionally absent from the segmentation API and enters only
through the separate metrics utility.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label as ndimage_label

import three_case_cavity_recovery as recovery


SEED_FRACTION_PERCENT = 1.0
ROBUST_MAD_SCALE = 1.4826
ROBUST_SIGMA_MULTIPLIER = 3.0
HEMISPHERE_SIDES = ("negative_z", "positive_z")
BACKGROUND_METHOD_LABEL = "fixture_informed_pipeline_validation_background"
PRODUCTION_BACKGROUND_DEGREE = 6
POLYNOMIAL_STABILITY_DEGREES = (5, 6, 7)
LOWER_OUTLIER_CLIP_SIGMA = 3.0
MAX_BACKGROUND_FIT_ITERATIONS = 8
CV_BLOCKS_PER_AXIS = 4
MAX_STABLE_CONDITION_NUMBER = 1.0e6
MAX_DEGREE6_CV_SPIKE_RATIO = 1.25
NUMERICAL_SUPPORT_EPS_MULTIPLIER = 10.0
# Goal 044's declared axisymmetric fixture geometry anchors this independent control.
CONTROL_CAVITY_CENTER_KPC = 58.0
CONTROL_CAVITY_HORIZONTAL_SEMIAXIS_KPC = 29.0
CONTROL_CAVITY_VERTICAL_SEMIAXIS_KPC = 34.0
CONTROL_CAVITY_INTENSITY_FACTOR = 0.75


@dataclass(frozen=True)
class SeedGrowComponent:
    """One seed-connected support component and its physical summary."""

    label: int
    mask: np.ndarray
    area_kpc2: float
    summary: recovery.ComponentSummary


@dataclass(frozen=True)
class PolynomialBackgroundDiagnostics:
    """Numerical diagnostics for one robust Chebyshev background fit."""

    degree: int
    iterations: int
    converged: bool
    condition_number: float
    retained_cell_fraction: float
    retained_area_fraction: float
    weighted_rmse_log_intensity: float


@dataclass(frozen=True)
class PolynomialBackgroundFit:
    """Fitted background, retained fit support, and numerical diagnostics."""

    background: np.ndarray
    fit_mask: np.ndarray
    diagnostics: PolynomialBackgroundDiagnostics


@dataclass(frozen=True)
class PolynomialDegreeStability:
    """Fit and blocked spatial validation diagnostics for one degree."""

    degree: int
    converged: bool
    condition_number: float
    retained_area_fraction: float
    weighted_rmse_log_intensity: float
    blocked_cv_rmse_log_intensity: float


@dataclass(frozen=True)
class PolynomialBackgroundStability:
    """Degree-5/6/7 evidence for the frozen production degree."""

    degrees: tuple[PolynomialDegreeStability, ...]
    degree6_not_numerical_knife_edge: bool


@dataclass(frozen=True)
class HemisphereRecovery:
    """Seed, support, primary component, and fragments for one jet side."""

    side: str
    seed_threshold: float
    seed_mask: np.ndarray
    support_mask: np.ndarray
    primary: SeedGrowComponent | None
    secondary_fragments: tuple[SeedGrowComponent, ...]

    @property
    def mask(self) -> np.ndarray:
        """Return the union of the primary component and seeded fragments."""

        grown = np.zeros_like(self.seed_mask, dtype=bool)
        if self.primary is not None:
            grown |= self.primary.mask
        for fragment in self.secondary_fragments:
            grown |= fragment.mask
        return grown


@dataclass(frozen=True)
class HemisphereSeedGrowResult:
    """Complete tracer-blind recovery diagnostics for one corrected X-ray map."""

    background_method: str
    background: np.ndarray
    background_diagnostics: PolynomialBackgroundDiagnostics
    deficit: np.ndarray
    candidate_roi: np.ndarray
    support_threshold: float
    radial_background: np.ndarray
    radial_deficit: np.ndarray
    radial_outer_annulus_threshold: float
    hemispheres: dict[str, HemisphereRecovery]

    @property
    def observer_mask(self) -> np.ndarray:
        """Return the union of all independently grown hemisphere masks."""

        observer = np.zeros_like(self.candidate_roi, dtype=bool)
        for side in HEMISPHERE_SIDES:
            observer |= self.hemispheres[side].mask
        return observer

    @property
    def detected_sides(self) -> tuple[str, ...]:
        """Return sides with a seed-connected primary component."""

        return tuple(
            side
            for side in HEMISPHERE_SIDES
            if self.hemispheres[side].primary is not None
        )


@dataclass(frozen=True)
class AreaWeightedTruthMetrics:
    """Physical-area overlap, centroid, and projected-area errors."""

    precision: float
    recall: float
    intersection_over_union: float
    predicted_area_kpc2: float
    truth_area_kpc2: float
    intersection_area_kpc2: float
    union_area_kpc2: float
    predicted_centroid_x_kpc: float
    predicted_centroid_z_kpc: float
    truth_centroid_x_kpc: float
    truth_centroid_z_kpc: float
    centroid_x_error_kpc: float
    centroid_z_error_kpc: float
    centroid_error_kpc: float
    area_signed_relative_error: float
    area_absolute_relative_error: float


@dataclass(frozen=True)
class GeometryResolution:
    """Diagnostics for deciding whether moment geometry is estimable."""

    resolved: bool
    distinct_horizontal_centres: int
    distinct_vertical_centres: int
    covariance_rank: int
    major_semiaxis_kpc: float
    minor_semiaxis_kpc: float
    local_horizontal_cell_width_kpc: float
    local_vertical_cell_width_kpc: float
    local_cell_width_kpc: float


def _background_model(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(values, horizontal, vertical)
    background_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.BACKGROUND_RADIUS_KPC,
        recovery.BACKGROUND_RADIUS_KPC,
    )
    candidate_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.CANDIDATE_RADIUS_KPC,
        recovery.CANDIDATE_RADIUS_KPC,
    )
    background = recovery.compute_azimuthal_median_background(
        values,
        horizontal,
        vertical,
        background_roi=background_roi,
        radial_bin_kpc=recovery.RADIAL_BIN_KPC,
        radial_smoothing_kpc=recovery.RADIAL_SMOOTHING_KPC,
    )
    return background, background_roi, candidate_roi


def _chebyshev_design(
    normalized_horizontal: np.ndarray,
    normalized_vertical: np.ndarray,
    degree: int,
) -> np.ndarray:
    horizontal_vander = np.polynomial.chebyshev.chebvander(
        normalized_horizontal, degree
    )
    vertical_vander = np.polynomial.chebyshev.chebvander(
        normalized_vertical, degree
    )
    columns = []
    for total_degree in range(degree + 1):
        for horizontal_degree in range(total_degree + 1):
            vertical_degree = total_degree - horizontal_degree
            columns.append(
                horizontal_vander[:, horizontal_degree]
                * vertical_vander[:, vertical_degree]
            )
    return np.column_stack(columns)


def _weighted_polynomial_solve(
    design: np.ndarray,
    response: np.ndarray,
    area_weights: np.ndarray,
) -> tuple[np.ndarray, float]:
    square_root_weights = np.sqrt(
        area_weights / float(np.mean(area_weights))
    )
    weighted_design = design * square_root_weights[:, np.newaxis]
    weighted_response = response * square_root_weights
    column_scales = np.linalg.norm(weighted_design, axis=0)
    if np.any(column_scales == 0.0):
        raise ValueError("polynomial design contains an empty basis column")
    scaled_design = weighted_design / column_scales
    scaled_coefficients, _, rank, singular_values = np.linalg.lstsq(
        scaled_design, weighted_response, rcond=None
    )
    if rank != scaled_design.shape[1]:
        raise ValueError("polynomial background design is rank deficient")
    condition_number = float(singular_values[0] / singular_values[-1])
    return scaled_coefficients / column_scales, condition_number


def _checked_polynomial_prediction(
    design: np.ndarray,
    coefficients: np.ndarray,
) -> np.ndarray:
    # Accelerate-backed matrix products can surface stale floating-point flags.
    # Suppress those flags locally, then fail explicitly on any nonfinite value.
    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        prediction = design @ coefficients
    if not np.all(np.isfinite(prediction)):
        raise ValueError("polynomial background prediction is nonfinite")
    return prediction


def _fit_polynomial_log_background(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    degree: int,
    training_mask: np.ndarray | None = None,
) -> PolynomialBackgroundFit:
    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(values, horizontal, vertical)
    if not isinstance(degree, (int, np.integer)) or degree < 1:
        raise ValueError("degree must be a positive integer")

    background_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.BACKGROUND_RADIUS_KPC,
        recovery.BACKGROUND_RADIUS_KPC,
    )
    base_support = background_roi & np.isfinite(values) & (values > 0.0)
    if training_mask is not None:
        training = np.asarray(training_mask, dtype=bool)
        if training.shape != values.shape:
            raise ValueError("training_mask must match corrected_xray")
        base_support &= training
    if not np.any(base_support):
        raise ValueError("polynomial background has no positive fit support")

    xx, zz = np.meshgrid(horizontal, vertical)
    design_all = _chebyshev_design(
        (xx / recovery.BACKGROUND_RADIUS_KPC).ravel(),
        (zz / recovery.BACKGROUND_RADIUS_KPC).ravel(),
        int(degree),
    )
    support_indices = np.flatnonzero(base_support)
    design = design_all[support_indices]
    response = np.log(values.ravel()[support_indices])
    area_grid = recovery._cell_area_grid(horizontal, vertical)
    area_weights = area_grid.ravel()[support_indices]
    term_count = design.shape[1]
    if support_indices.size <= term_count:
        raise ValueError("polynomial background has insufficient fit support")

    active = np.ones(support_indices.size, dtype=bool)
    converged = False
    iterations = 0
    for iterations in range(1, MAX_BACKGROUND_FIT_ITERATIONS + 1):
        coefficients, _ = _weighted_polynomial_solve(
            design[active], response[active], area_weights[active]
        )
        residual = response - _checked_polynomial_prediction(
            design, coefficients
        )
        center = float(np.median(residual[active]))
        mad = float(np.median(np.abs(residual[active] - center)))
        if mad <= np.finfo(float).eps * max(1.0, abs(center)):
            converged = True
            break
        cutoff = (
            center
            - LOWER_OUTLIER_CLIP_SIGMA * ROBUST_MAD_SCALE * mad
        )
        updated = active & (residual >= cutoff)
        if np.count_nonzero(updated) <= term_count:
            raise ValueError("lower-outlier clipping removed too much fit support")
        if np.array_equal(updated, active):
            converged = True
            break
        active = updated

    coefficients, condition_number = _weighted_polynomial_solve(
        design[active], response[active], area_weights[active]
    )
    fitted_response = _checked_polynomial_prediction(
        design[active], coefficients
    )
    weighted_rmse = float(
        np.sqrt(
            np.average(
                (response[active] - fitted_response) ** 2,
                weights=area_weights[active],
            )
        )
    )
    background = np.full(values.shape, np.nan, dtype=float)
    roi_flat = background_roi.ravel()
    predicted_log = _checked_polynomial_prediction(
        design_all[roi_flat], coefficients
    )
    background.ravel()[roi_flat] = np.exp(predicted_log)
    if not np.all(
        np.isfinite(background[background_roi])
        & (background[background_roi] > 0.0)
    ):
        raise ValueError("polynomial background prediction is not finite and positive")

    fit_mask = np.zeros(values.size, dtype=bool)
    fit_mask[support_indices[active]] = True
    fit_mask = fit_mask.reshape(values.shape)
    retained_cell_fraction = float(
        np.count_nonzero(active) / active.size
    )
    retained_area_fraction = float(
        area_weights[active].sum() / area_weights.sum()
    )
    diagnostics = PolynomialBackgroundDiagnostics(
        degree=int(degree),
        iterations=iterations,
        converged=converged,
        condition_number=condition_number,
        retained_cell_fraction=retained_cell_fraction,
        retained_area_fraction=retained_area_fraction,
        weighted_rmse_log_intensity=weighted_rmse,
    )
    return PolynomialBackgroundFit(background, fit_mask, diagnostics)


def fit_polynomial_log_background(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    degree: int = PRODUCTION_BACKGROUND_DEGREE,
) -> PolynomialBackgroundFit:
    """Fit the frozen robust normalized Chebyshev log-intensity background.

    The degree argument exists for the predeclared 5/6/7 stability diagnostic.
    Production recovery always calls this function at degree six.
    """

    return _fit_polynomial_log_background(
        corrected_xray,
        horizontal_axis_kpc,
        vertical_axis_kpc,
        degree=degree,
    )


def _spatial_cv_folds(
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> np.ndarray:
    xx, zz = np.meshgrid(horizontal_axis_kpc, vertical_axis_kpc)
    normalized_x = np.clip(
        (xx / recovery.BACKGROUND_RADIUS_KPC + 1.0) / 2.0,
        0.0,
        np.nextafter(1.0, 0.0),
    )
    normalized_z = np.clip(
        (zz / recovery.BACKGROUND_RADIUS_KPC + 1.0) / 2.0,
        0.0,
        np.nextafter(1.0, 0.0),
    )
    x_block = np.floor(normalized_x * CV_BLOCKS_PER_AXIS).astype(int)
    z_block = np.floor(normalized_z * CV_BLOCKS_PER_AXIS).astype(int)
    return (x_block % 2) + 2 * (z_block % 2)


def polynomial_background_stability(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> PolynomialBackgroundStability:
    """Report degree-5/6/7 fit and blocked spatial prediction diagnostics."""

    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(values, horizontal, vertical)
    background_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.BACKGROUND_RADIUS_KPC,
        recovery.BACKGROUND_RADIUS_KPC,
    )
    positive_support = background_roi & (values > 0.0)
    folds = _spatial_cv_folds(horizontal, vertical)
    area_grid = recovery._cell_area_grid(horizontal, vertical)
    degree_rows: list[PolynomialDegreeStability] = []
    for degree in POLYNOMIAL_STABILITY_DEGREES:
        full_fit = fit_polynomial_log_background(
            values, horizontal, vertical, degree=degree
        )
        squared_error_sum = 0.0
        held_area_sum = 0.0
        fold_convergence = []
        condition_numbers = [full_fit.diagnostics.condition_number]
        for fold in range(4):
            held_out = positive_support & (folds == fold)
            training = positive_support & (folds != fold)
            fold_fit = _fit_polynomial_log_background(
                values,
                horizontal,
                vertical,
                degree=degree,
                training_mask=training,
            )
            residual = (
                np.log(values[held_out])
                - np.log(fold_fit.background[held_out])
            )
            weights = area_grid[held_out]
            squared_error_sum += float(np.sum(weights * residual**2))
            held_area_sum += float(weights.sum())
            fold_convergence.append(fold_fit.diagnostics.converged)
            condition_numbers.append(fold_fit.diagnostics.condition_number)
        blocked_cv_rmse = float(
            np.sqrt(squared_error_sum / held_area_sum)
        )
        degree_rows.append(
            PolynomialDegreeStability(
                degree=degree,
                converged=bool(
                    full_fit.diagnostics.converged
                    and all(fold_convergence)
                ),
                condition_number=max(condition_numbers),
                retained_area_fraction=(
                    full_fit.diagnostics.retained_area_fraction
                ),
                weighted_rmse_log_intensity=(
                    full_fit.diagnostics.weighted_rmse_log_intensity
                ),
                blocked_cv_rmse_log_intensity=blocked_cv_rmse,
            )
        )

    by_degree = {item.degree: item for item in degree_rows}
    degree6 = by_degree[6]
    adjacent_cv_max = max(
        by_degree[5].blocked_cv_rmse_log_intensity,
        by_degree[7].blocked_cv_rmse_log_intensity,
    )
    stable = bool(
        all(item.converged for item in degree_rows)
        and all(
            np.isfinite(item.condition_number)
            and item.condition_number < MAX_STABLE_CONDITION_NUMBER
            for item in degree_rows
        )
        and all(
            np.isfinite(item.blocked_cv_rmse_log_intensity)
            for item in degree_rows
        )
        and degree6.blocked_cv_rmse_log_intensity
        <= MAX_DEGREE6_CV_SPIKE_RATIO * adjacent_cv_max
    )
    return PolynomialBackgroundStability(tuple(degree_rows), stable)


def robust_outer_annulus_threshold(
    deficit: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> float:
    """Return the frozen robust support threshold from the 120--180 kpc annulus."""

    values = np.asarray(deficit, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    if values.ndim != 2:
        raise ValueError("deficit must be two-dimensional")
    recovery.validate_map_and_axes(
        np.ones(values.shape, dtype=float), horizontal, vertical
    )
    background_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.BACKGROUND_RADIUS_KPC,
        recovery.BACKGROUND_RADIUS_KPC,
    )
    candidate_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.CANDIDATE_RADIUS_KPC,
        recovery.CANDIDATE_RADIUS_KPC,
    )
    outer_annulus = background_roi & ~candidate_roi & np.isfinite(values)
    if not np.any(outer_annulus):
        raise ValueError(
            "outer annulus contains no finite deficit support between 120 and 180 kpc"
        )
    annulus_values = values[outer_annulus]
    median = float(np.median(annulus_values))
    mad = float(np.median(np.abs(annulus_values - median)))
    return max(
        0.0,
        median + ROBUST_SIGMA_MULTIPLIER * ROBUST_MAD_SCALE * mad,
    )


def _component(
    component_label: int,
    mask: np.ndarray,
    area_grid: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> SeedGrowComponent:
    component_mask = np.asarray(mask, dtype=bool).copy()
    area = float(area_grid[component_mask].sum())
    base = recovery.Component(component_label, component_mask, area)
    summary = recovery.summarize_components(
        (base,), horizontal_axis_kpc, vertical_axis_kpc
    )[0]
    return SeedGrowComponent(component_label, component_mask, area, summary)


def _recover_hemisphere(
    side: str,
    deficit: np.ndarray,
    candidate_roi: np.ndarray,
    hemisphere_mask: np.ndarray,
    support_threshold: float,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> HemisphereRecovery:
    side_roi = candidate_roi & hemisphere_mask
    seed_mask, seed_threshold = recovery.select_area_fraction_candidate(
        deficit,
        side_roi,
        horizontal_axis_kpc,
        vertical_axis_kpc,
        fraction=SEED_FRACTION_PERCENT,
        high_values_are_candidates=True,
    )

    # Strict exceedance is deliberate: a zero-deficit smooth null must not
    # become support merely because the clipped robust threshold is also zero.
    support_mask = (
        side_roi & np.isfinite(deficit) & (deficit > support_threshold)
    )
    labels, component_count = ndimage_label(
        support_mask, structure=np.ones((3, 3), dtype=int)
    )
    area_grid = recovery._cell_area_grid(
        horizontal_axis_kpc, vertical_axis_kpc
    )
    seeded_components: list[SeedGrowComponent] = []
    for component_label in range(1, component_count + 1):
        component_mask = labels == component_label
        if np.any(component_mask & seed_mask):
            seeded_components.append(
                _component(
                    component_label,
                    component_mask,
                    area_grid,
                    horizontal_axis_kpc,
                    vertical_axis_kpc,
                )
            )
    seeded_components.sort(key=lambda item: (-item.area_kpc2, item.label))
    primary = seeded_components[0] if seeded_components else None
    fragments = tuple(seeded_components[1:])
    return HemisphereRecovery(
        side=side,
        seed_threshold=float(seed_threshold),
        seed_mask=seed_mask,
        support_mask=support_mask,
        primary=primary,
        secondary_fragments=fragments,
    )


def recover_hemisphere_seed_grow(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> HemisphereSeedGrowResult:
    """Recover cavity support with a fixed tracer-blind hemisphere protocol."""

    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    radial_background, _, candidate_roi = _background_model(
        values, horizontal, vertical
    )
    radial_deficit = recovery.compute_fractional_deficit(
        values, radial_background
    )
    radial_outer_annulus_threshold = robust_outer_annulus_threshold(
        radial_deficit, horizontal, vertical
    )
    polynomial_fit = fit_polynomial_log_background(
        values,
        horizontal,
        vertical,
        degree=PRODUCTION_BACKGROUND_DEGREE,
    )
    deficit = recovery.compute_fractional_deficit(
        values, polynomial_fit.background
    )
    support_threshold = robust_outer_annulus_threshold(
        deficit, horizontal, vertical
    )
    support_threshold = max(
        support_threshold,
        NUMERICAL_SUPPORT_EPS_MULTIPLIER
        * np.finfo(float).eps
        * polynomial_fit.diagnostics.condition_number,
    )
    _, zz = np.meshgrid(horizontal, vertical)
    hemisphere_masks = {
        "negative_z": zz < 0.0,
        "positive_z": zz > 0.0,
    }
    hemispheres = {
        side: _recover_hemisphere(
            side,
            deficit,
            candidate_roi,
            hemisphere_masks[side],
            support_threshold,
            horizontal,
            vertical,
        )
        for side in HEMISPHERE_SIDES
    }
    return HemisphereSeedGrowResult(
        background_method=BACKGROUND_METHOD_LABEL,
        background=polynomial_fit.background,
        background_diagnostics=polynomial_fit.diagnostics,
        deficit=deficit,
        candidate_roi=candidate_roi,
        support_threshold=support_threshold,
        radial_background=radial_background,
        radial_deficit=radial_deficit,
        radial_outer_annulus_threshold=radial_outer_annulus_threshold,
        hemispheres=hemispheres,
    )


def make_smooth_background_control(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> np.ndarray:
    """Build an independent analytic radial smooth-background null."""

    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(values, horizontal, vertical)
    background_roi = recovery.build_elliptical_roi(
        horizontal,
        vertical,
        recovery.BACKGROUND_RADIUS_KPC,
        recovery.BACKGROUND_RADIUS_KPC,
    )
    level = float(np.median(values[background_roi]))
    xx, zz = np.meshgrid(horizontal, vertical)
    radius = np.hypot(xx, zz)
    return level * np.exp(
        -0.5 * (radius / recovery.BACKGROUND_RADIUS_KPC) ** 2
    )


def make_one_sided_ablation_control(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    retained_side: str,
) -> np.ndarray:
    """Build an independent analytic bipolar control with one lobe ablated."""

    if retained_side not in HEMISPHERE_SIDES:
        raise ValueError(
            "retained_side must be 'negative_z' or 'positive_z'"
        )
    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(values, horizontal, vertical)
    control = make_smooth_background_control(
        values, horizontal, vertical
    )
    xx, zz = np.meshgrid(horizontal, vertical)
    center_z = (
        -CONTROL_CAVITY_CENTER_KPC
        if retained_side == "negative_z"
        else CONTROL_CAVITY_CENTER_KPC
    )
    retained_cavity = (
        (xx / CONTROL_CAVITY_HORIZONTAL_SEMIAXIS_KPC) ** 2
        + (
            (zz - center_z)
            / CONTROL_CAVITY_VERTICAL_SEMIAXIS_KPC
        )
        ** 2
        <= 1.0
    )
    control[retained_cavity] *= CONTROL_CAVITY_INTENSITY_FACTOR
    return control


def _safe_area_ratio(numerator: float, denominator: float) -> float:
    if denominator > 0.0:
        return float(numerator / denominator)
    return 1.0 if numerator == 0.0 else 0.0


def _area_weighted_centroid(
    mask: np.ndarray,
    area_grid: np.ndarray,
    xx: np.ndarray,
    zz: np.ndarray,
) -> tuple[float, float]:
    total_area = float(area_grid[mask].sum())
    if total_area == 0.0:
        return float("nan"), float("nan")
    weights = area_grid[mask]
    return (
        float(np.average(xx[mask], weights=weights)),
        float(np.average(zz[mask], weights=weights)),
    )


def area_weighted_truth_metrics(
    observer_mask: np.ndarray,
    truth_mask: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> AreaWeightedTruthMetrics:
    """Compare observer and truth masks using projected physical cell area."""

    observer = np.asarray(observer_mask, dtype=bool)
    truth = np.asarray(truth_mask, dtype=bool)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(
        observer.astype(float), horizontal, vertical
    )
    if truth.shape != observer.shape:
        raise ValueError(
            "observer_mask and truth_mask must be matching two-dimensional arrays"
        )

    area_grid = recovery._cell_area_grid(horizontal, vertical)
    intersection = observer & truth
    union = observer | truth
    predicted_area = float(area_grid[observer].sum())
    truth_area = float(area_grid[truth].sum())
    intersection_area = float(area_grid[intersection].sum())
    union_area = float(area_grid[union].sum())

    xx, zz = np.meshgrid(horizontal, vertical)
    predicted_centroid = _area_weighted_centroid(
        observer, area_grid, xx, zz
    )
    truth_centroid = _area_weighted_centroid(truth, area_grid, xx, zz)
    if predicted_area > 0.0 and truth_area > 0.0:
        centroid_x_error = predicted_centroid[0] - truth_centroid[0]
        centroid_z_error = predicted_centroid[1] - truth_centroid[1]
        centroid_error = float(
            np.hypot(centroid_x_error, centroid_z_error)
        )
    else:
        centroid_x_error = float("nan")
        centroid_z_error = float("nan")
        centroid_error = float("nan")

    if truth_area > 0.0:
        signed_area_error = (predicted_area - truth_area) / truth_area
    elif predicted_area == 0.0:
        signed_area_error = 0.0
    else:
        signed_area_error = float("inf")

    return AreaWeightedTruthMetrics(
        precision=_safe_area_ratio(intersection_area, predicted_area),
        recall=_safe_area_ratio(intersection_area, truth_area),
        intersection_over_union=_safe_area_ratio(
            intersection_area, union_area
        ),
        predicted_area_kpc2=predicted_area,
        truth_area_kpc2=truth_area,
        intersection_area_kpc2=intersection_area,
        union_area_kpc2=union_area,
        predicted_centroid_x_kpc=predicted_centroid[0],
        predicted_centroid_z_kpc=predicted_centroid[1],
        truth_centroid_x_kpc=truth_centroid[0],
        truth_centroid_z_kpc=truth_centroid[1],
        centroid_x_error_kpc=float(centroid_x_error),
        centroid_z_error_kpc=float(centroid_z_error),
        centroid_error_kpc=centroid_error,
        area_signed_relative_error=float(signed_area_error),
        area_absolute_relative_error=float(abs(signed_area_error)),
    )


def geometry_resolution(
    mask: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> GeometryResolution:
    """Return the predeclared sampling and covariance resolution diagnostics."""

    component = np.asarray(mask, dtype=bool)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    recovery.validate_map_and_axes(
        component.astype(float), horizontal, vertical
    )
    xx, zz = np.meshgrid(horizontal, vertical)
    distinct_horizontal = int(np.unique(xx[component]).size)
    distinct_vertical = int(np.unique(zz[component]).size)
    if not np.any(component):
        return GeometryResolution(
            resolved=False,
            distinct_horizontal_centres=0,
            distinct_vertical_centres=0,
            covariance_rank=0,
            major_semiaxis_kpc=0.0,
            minor_semiaxis_kpc=0.0,
            local_horizontal_cell_width_kpc=float("nan"),
            local_vertical_cell_width_kpc=float("nan"),
            local_cell_width_kpc=float("nan"),
        )

    area_grid = recovery._cell_area_grid(horizontal, vertical)
    weights = area_grid[component]
    total_area = float(weights.sum())
    x_values = xx[component]
    z_values = zz[component]
    centroid_x = float(np.average(x_values, weights=weights))
    centroid_z = float(np.average(z_values, weights=weights))
    centered = np.column_stack(
        (x_values - centroid_x, z_values - centroid_z)
    )
    covariance = (
        np.einsum("i,ij,ik->jk", weights, centered, centered) / total_area
    )
    covariance_rank = int(np.linalg.matrix_rank(covariance))
    eigenvalues = np.linalg.eigvalsh(covariance)
    minor = 2.0 * np.sqrt(max(float(eigenvalues[0]), 0.0))
    major = 2.0 * np.sqrt(max(float(eigenvalues[1]), 0.0))

    horizontal_widths = recovery._axis_cell_widths(horizontal)
    vertical_widths = recovery._axis_cell_widths(vertical)
    horizontal_index = int(np.argmin(np.abs(horizontal - centroid_x)))
    vertical_index = int(np.argmin(np.abs(vertical - centroid_z)))
    local_horizontal = float(horizontal_widths[horizontal_index])
    local_vertical = float(vertical_widths[vertical_index])
    local_cell_width = max(local_horizontal, local_vertical)
    resolved = bool(
        distinct_horizontal >= 3
        and distinct_vertical >= 3
        and covariance_rank == 2
        and minor > local_cell_width
    )
    return GeometryResolution(
        resolved=resolved,
        distinct_horizontal_centres=distinct_horizontal,
        distinct_vertical_centres=distinct_vertical,
        covariance_rank=covariance_rank,
        major_semiaxis_kpc=float(major),
        minor_semiaxis_kpc=float(minor),
        local_horizontal_cell_width_kpc=local_horizontal,
        local_vertical_cell_width_kpc=local_vertical,
        local_cell_width_kpc=local_cell_width,
    )


def is_resolved_geometry(
    mask: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> bool:
    """Return whether moment geometry clears every resolution requirement."""

    return geometry_resolution(
        mask, horizontal_axis_kpc, vertical_axis_kpc
    ).resolved
