#!/usr/bin/env python3
"""Observer-side physical-scale cavity recovery for the accepted endpoints.

This module deliberately stops at projected X-ray recovery and tracer
validation.  Tracer arrays are loaded only for downstream validation metrics;
they are never used to construct the observer-side mask.
"""

from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d, label


ROOT = Path(__file__).resolve().parents[2]
CHI0 = ROOT / "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid"
CHI_REFINED_ARCHIVE = (
    ROOT
    / "docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/remote_logs/"
    "refined_projection_viewing_rerun_2026-06-25.tar.gz"
)
CLO_ROOT = ROOT / "docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products"
GLO_ROOT = ROOT / "docs/science/assets/g_lo_endpoint_first_products_and_three_case_comparison_2026-07-12/review_products"

CORRECTED_XRAY_NAME = "xray_1kev_xraise_corrected_mjy_sr.tsv"
TRACER_NAME = "tracer_max_los.tsv"
HORIZONTAL_AXIS_NAME = "x_kpc.tsv"
VERTICAL_AXIS_NAME = "z_kpc.tsv"

BACKGROUND_RADIUS_KPC = 180.0
CANDIDATE_RADIUS_KPC = 120.0
ROI_SEMIAXES_KPC = (BACKGROUND_RADIUS_KPC, BACKGROUND_RADIUS_KPC)
GAUSSIAN_SCALES_KPC = (15.0, 20.0, 30.0)
RADIAL_BIN_KPC = 5.0
RADIAL_SMOOTHING_KPC = 10.0
LOW_RESIDUAL_FRACTIONS_PERCENT = (0.5, 1.0, 2.0, 3.0, 5.0)
CONNECTIVITY = 8
MIN_COMPONENT_AREA_KPC2 = 25.0
TRACER_THRESHOLDS = (1.0e-3, 5.0e-3, 1.0e-2)


@dataclass(frozen=True)
class MapSpec:
    """Stable identifiers for one accepted case/view map triple."""

    case: str
    view: str
    corrected_xray: str
    tracer_max_los: str
    horizontal_axis: str
    z_axis: str
    source_type: str
    archive_path: str | None = None


@dataclass(frozen=True)
class LoadedMap:
    spec: MapSpec
    corrected_xray: np.ndarray
    tracer_max_los: np.ndarray
    horizontal_axis: np.ndarray
    z_axis: np.ndarray


@dataclass(frozen=True)
class Component:
    label: int
    mask: np.ndarray
    area_kpc2: float


@dataclass(frozen=True)
class ComponentSelection:
    labels: np.ndarray
    components: tuple[Component, ...]
    cell_area_kpc2: float


@dataclass(frozen=True)
class ComponentSummary:
    label: int
    area_kpc2: float
    centroid_x_kpc: float
    centroid_z_kpc: float
    crosses_z_zero: bool
    major_semiaxis_kpc: float
    minor_semiaxis_kpc: float
    depths_kpc: dict[str, float]
    volumes_kpc3: dict[str, float]


def validate_map_and_axes(
    values: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> None:
    """Validate a finite map whose physical axes are strictly monotonic."""

    values = np.asarray(values, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    if values.ndim != 2:
        raise ValueError("map must be two-dimensional")
    if not np.all(np.isfinite(values)):
        raise ValueError("map must contain only finite values")
    if horizontal.ndim != 1 or vertical.ndim != 1:
        raise ValueError("physical axes must be one-dimensional")
    if values.shape != (vertical.size, horizontal.size):
        raise ValueError("map shape must match vertical and horizontal axes")
    for name, axis in (("horizontal", horizontal), ("vertical", vertical)):
        if not np.all(np.isfinite(axis)):
            raise ValueError(f"{name} axis must contain only finite values")
        differences = np.diff(axis)
        if differences.size == 0 or not (
            np.all(differences > 0.0) or np.all(differences < 0.0)
        ):
            raise ValueError(f"{name} axis must be strictly monotonic")


def _axis_cell_widths(axis: np.ndarray) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    if axis.size < 2:
        raise ValueError("an axis needs at least two cell centres")
    differences = np.diff(axis)
    if not (np.all(differences > 0.0) or np.all(differences < 0.0)):
        raise ValueError("axis must be strictly monotonic")
    edges = np.empty(axis.size + 1, dtype=float)
    edges[1:-1] = (axis[:-1] + axis[1:]) / 2.0
    edges[0] = axis[0] - differences[0] / 2.0
    edges[-1] = axis[-1] + differences[-1] / 2.0
    return np.abs(np.diff(edges))


def pixel_sigmas_for_physical_scale(
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    scale_kpc: float,
) -> tuple[float, float]:
    """Return ``(sigma_z_pixels, sigma_horizontal_pixels)`` for a kpc scale."""

    if not np.isfinite(scale_kpc) or scale_kpc <= 0.0:
        raise ValueError("scale_kpc must be finite and positive")
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    horizontal_spacing = float(np.median(_axis_cell_widths(horizontal)))
    vertical_spacing = float(np.median(_axis_cell_widths(vertical)))
    return scale_kpc / vertical_spacing, scale_kpc / horizontal_spacing


def build_elliptical_roi(
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    semi_horizontal_kpc: float = ROI_SEMIAXES_KPC[0],
    semi_vertical_kpc: float = ROI_SEMIAXES_KPC[1],
) -> np.ndarray:
    """Build a common elliptical ROI on the physical coordinate grid."""

    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    if semi_horizontal_kpc <= 0.0 or semi_vertical_kpc <= 0.0:
        raise ValueError("ROI semiaxes must be positive")
    validate_map_and_axes(
        np.ones((vertical.size, horizontal.size), dtype=float), horizontal, vertical
    )
    xx, zz = np.meshgrid(horizontal, vertical)
    return (xx / semi_horizontal_kpc) ** 2 + (zz / semi_vertical_kpc) ** 2 <= 1.0


def compute_physical_gaussian_background(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    scale_kpc: float,
    roi_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Smooth X-rays at a physical scale using normalized valid-weight convolution.

    The ROI is included in the valid-weight mask.  Dividing the convolution of
    values by the convolution of valid weights prevents the implicit zero
    padding at the ROI boundary from creating an artificial deficit.
    """

    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    validate_map_and_axes(values, horizontal, vertical)
    if roi_mask is None:
        roi = np.ones(values.shape, dtype=bool)
    else:
        roi = np.asarray(roi_mask, dtype=bool)
        if roi.shape != values.shape:
            raise ValueError("roi_mask must have the same shape as corrected_xray")
    valid = roi & np.isfinite(values)
    sigma = pixel_sigmas_for_physical_scale(horizontal, vertical, scale_kpc=scale_kpc)
    weights = valid.astype(float)
    numerator = gaussian_filter(np.where(valid, values, 0.0), sigma=sigma, mode="constant", cval=0.0)
    denominator = gaussian_filter(weights, sigma=sigma, mode="constant", cval=0.0)
    background = np.full(values.shape, np.nan, dtype=float)
    np.divide(numerator, denominator, out=background, where=denominator > 0.0)
    background[~roi] = np.nan
    return background


def compute_azimuthal_median_background(
    corrected_xray: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    background_roi: np.ndarray,
    radial_bin_kpc: float = RADIAL_BIN_KPC,
    radial_smoothing_kpc: float = RADIAL_SMOOTHING_KPC,
) -> np.ndarray:
    """Estimate a tracer-blind radial background from azimuthal medians.

    Medians in fixed-width physical annuli suppress localized cavities while
    retaining the ambient halo gradient. Missing annuli are linearly
    interpolated before the one-dimensional physical-scale smoothing step.
    """

    values = np.asarray(corrected_xray, dtype=float)
    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    roi = np.asarray(background_roi, dtype=bool)
    validate_map_and_axes(values, horizontal, vertical)
    if roi.shape != values.shape:
        raise ValueError("background_roi must have the same shape as corrected_xray")
    if not np.isfinite(radial_bin_kpc) or radial_bin_kpc <= 0.0:
        raise ValueError("radial_bin_kpc must be finite and positive")
    if not np.isfinite(radial_smoothing_kpc) or radial_smoothing_kpc < 0.0:
        raise ValueError("radial_smoothing_kpc must be finite and non-negative")

    xx, zz = np.meshgrid(horizontal, vertical)
    radius = np.hypot(xx, zz)
    finite_support = roi & np.isfinite(values) & (values > 0.0)
    if not np.any(finite_support):
        raise ValueError("background_roi contains no finite positive X-ray support")
    max_radius = float(np.max(radius[finite_support]))
    edges = np.arange(0.0, max_radius + radial_bin_kpc, radial_bin_kpc)
    if edges.size < 2:
        edges = np.array([0.0, radial_bin_kpc])
    if edges[-1] <= max_radius:
        edges = np.append(edges, edges[-1] + radial_bin_kpc)
    centers = 0.5 * (edges[:-1] + edges[1:])
    profile = np.full(centers.shape, np.nan, dtype=float)
    for index, (inner, outer) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        annulus = finite_support & (radius >= inner) & (radius < outer)
        if np.any(annulus):
            profile[index] = float(np.median(values[annulus]))
    valid_profile = np.isfinite(profile)
    if not np.any(valid_profile):
        raise ValueError("could not estimate any finite radial profile bins")
    profile = np.interp(centers, centers[valid_profile], profile[valid_profile])
    if radial_smoothing_kpc > 0.0:
        profile = gaussian_filter1d(
            profile,
            sigma=radial_smoothing_kpc / radial_bin_kpc,
            mode="nearest",
        )
    background = np.interp(np.minimum(radius, centers[-1]), centers, profile)
    background[~roi] = np.nan
    return background


def compute_fractional_deficit(corrected_xray: np.ndarray, background: np.ndarray) -> np.ndarray:
    """Compute ``(background - corrected_xray) / background`` where defined."""

    values = np.asarray(corrected_xray, dtype=float)
    smooth = np.asarray(background, dtype=float)
    if values.shape != smooth.shape or values.ndim != 2:
        raise ValueError("corrected_xray and background must be matching two-dimensional arrays")
    result = np.full(values.shape, np.nan, dtype=float)
    valid = np.isfinite(values) & np.isfinite(smooth) & (smooth > 0.0)
    np.divide(smooth - values, smooth, out=result, where=valid)
    return result


def select_low_percentile_candidate(
    residual_or_deficit: np.ndarray,
    roi_mask: np.ndarray,
    *,
    fraction: float,
    high_values_are_candidates: bool = False,
) -> tuple[np.ndarray, float]:
    """Select a percentile tail inside the ROI without using tracer data.

    Residuals normally use the low tail.  Fractional deficits use the high
    tail by passing ``high_values_are_candidates=True``.
    """

    values = np.asarray(residual_or_deficit, dtype=float)
    roi = np.asarray(roi_mask, dtype=bool)
    if values.ndim != 2 or roi.shape != values.shape:
        raise ValueError("residual_or_deficit and roi_mask must be matching two-dimensional arrays")
    if not np.isfinite(fraction) or not (0.0 < fraction < 100.0):
        raise ValueError("fraction must be between 0 and 100")
    support = roi & np.isfinite(values)
    if not np.any(support):
        raise ValueError("ROI contains no finite candidate support")
    threshold = float(
        np.percentile(values[support], 100.0 - fraction if high_values_are_candidates else fraction)
    )
    candidate = support & (values >= threshold if high_values_are_candidates else values <= threshold)
    return candidate, threshold


def select_area_fraction_candidate(
    residual_or_deficit: np.ndarray,
    roi_mask: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    fraction: float,
    high_values_are_candidates: bool = False,
) -> tuple[np.ndarray, float]:
    """Select a percentile tail weighted by projected physical cell area.

    The threshold is the value where cumulative physical area first reaches
    the requested fraction. All cells tied at that threshold are retained, so
    symmetric equal-valued regions are not split by array order.
    """

    values = np.asarray(residual_or_deficit, dtype=float)
    roi = np.asarray(roi_mask, dtype=bool)
    if values.ndim != 2:
        raise ValueError("residual_or_deficit must be two-dimensional")
    validate_map_and_axes(
        np.ones(values.shape, dtype=float), horizontal_axis_kpc, vertical_axis_kpc
    )
    if roi.shape != values.shape:
        raise ValueError("residual_or_deficit and roi_mask must have matching shapes")
    if not np.isfinite(fraction) or not (0.0 < fraction < 100.0):
        raise ValueError("fraction must be between 0 and 100")
    support = roi & np.isfinite(values)
    if not np.any(support):
        raise ValueError("ROI contains no finite candidate support")
    area_grid = _cell_area_grid(horizontal_axis_kpc, vertical_axis_kpc)
    flat_indices = np.flatnonzero(support)
    order = np.argsort(values.ravel()[flat_indices], kind="stable")
    if high_values_are_candidates:
        order = order[::-1]
    ranked = flat_indices[order]
    target_area = float(area_grid[support].sum()) * fraction / 100.0
    cumulative_area = np.cumsum(area_grid.ravel()[ranked])
    cutoff_index = min(int(np.searchsorted(cumulative_area, target_area, side="left")), ranked.size - 1)
    threshold = float(values.ravel()[ranked[cutoff_index]])
    candidate = support & (
        values >= threshold if high_values_are_candidates else values <= threshold
    )
    return candidate, threshold


def _cell_area_grid(horizontal_axis_kpc: np.ndarray, vertical_axis_kpc: np.ndarray) -> np.ndarray:
    return np.outer(_axis_cell_widths(np.asarray(vertical_axis_kpc)), _axis_cell_widths(np.asarray(horizontal_axis_kpc)))


def label_and_filter_components(
    candidate_mask: np.ndarray,
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
    *,
    min_area_kpc2: float = MIN_COMPONENT_AREA_KPC2,
    connectivity: int = CONNECTIVITY,
) -> ComponentSelection:
    """Label 8-connected candidates and retain components above physical area."""

    candidate = np.asarray(candidate_mask, dtype=bool)
    validate_map_and_axes(candidate.astype(float), horizontal_axis_kpc, vertical_axis_kpc)
    if connectivity not in (4, 8):
        raise ValueError("connectivity must be 4 or 8")
    if not np.isfinite(min_area_kpc2) or min_area_kpc2 <= 0.0:
        raise ValueError("min_area_kpc2 must be finite and positive")
    structure = np.ones((3, 3), dtype=int) if connectivity == 8 else np.array(
        [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=int
    )
    labels, count = label(candidate, structure=structure)
    area_grid = _cell_area_grid(horizontal_axis_kpc, vertical_axis_kpc)
    components: list[Component] = []
    for component_label in range(1, count + 1):
        component_mask = labels == component_label
        area = float(area_grid[component_mask].sum())
        if area >= min_area_kpc2:
            components.append(Component(component_label, component_mask, area))
    cell_area = float(np.median(area_grid))
    return ComponentSelection(labels, tuple(components), cell_area)


def summarize_components(
    components: Iterable[Component],
    horizontal_axis_kpc: np.ndarray,
    vertical_axis_kpc: np.ndarray,
) -> list[ComponentSummary]:
    """Summarise retained components in physical coordinates.

    For a uniformly filled ellipse, each principal second moment is
    ``a**2 / 4`` or ``b**2 / 4``.  Therefore the reported projected semiaxis
    is ``2 * sqrt(moment)``; the factor of two is the moment-to-semiaxis
    conversion used here.
    """

    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(vertical_axis_kpc, dtype=float)
    shape = (vertical.size, horizontal.size)
    validate_map_and_axes(np.ones(shape, dtype=float), horizontal, vertical)
    xx, zz = np.meshgrid(horizontal, vertical)
    area_grid = _cell_area_grid(horizontal, vertical)
    summaries: list[ComponentSummary] = []
    for component in components:
        if component.mask.shape != shape:
            raise ValueError("component mask does not match physical axes")
        mask = component.mask
        weights = area_grid[mask]
        total_area = float(weights.sum())
        if total_area <= 0.0:
            raise ValueError("component must have positive physical area")
        x_values = xx[mask]
        z_values = zz[mask]
        centroid_x = float(np.average(x_values, weights=weights))
        centroid_z = float(np.average(z_values, weights=weights))
        centered = np.column_stack((x_values - centroid_x, z_values - centroid_z))
        covariance = np.array(
            [
                [np.sum(weights * centered[:, 0] * centered[:, 0]), np.sum(weights * centered[:, 0] * centered[:, 1])],
                [np.sum(weights * centered[:, 1] * centered[:, 0]), np.sum(weights * centered[:, 1] * centered[:, 1])],
            ],
            dtype=float,
        ) / total_area
        eigenvalues = np.linalg.eigvalsh(covariance)
        minor = 2.0 * np.sqrt(max(float(eigenvalues[0]), 0.0))
        major = 2.0 * np.sqrt(max(float(eigenvalues[1]), 0.0))
        depths = {
            "minor_depth": minor,
            "geometric_depth": float(np.sqrt(major * minor)),
            "major_depth": major,
        }
        volumes = {
            name: float(4.0 / 3.0 * np.pi * major * minor * depth)
            for name, depth in depths.items()
        }
        summaries.append(
            ComponentSummary(
                label=component.label,
                area_kpc2=total_area,
                centroid_x_kpc=centroid_x,
                centroid_z_kpc=centroid_z,
                crosses_z_zero=bool(np.any(z_values < 0.0) and np.any(z_values > 0.0)),
                major_semiaxis_kpc=major,
                minor_semiaxis_kpc=minor,
                depths_kpc=depths,
                volumes_kpc3=volumes,
            )
        )
    return summaries


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator:
        return float(numerator / denominator)
    return 1.0 if numerator == 0 else 0.0


def tracer_validation_metrics(
    observer_mask: np.ndarray,
    tracer_max_los: np.ndarray,
    *,
    threshold: float,
) -> dict[str, float]:
    """Compare a fixed observer mask with a tracer mask at one threshold.

    This function only reads the observer mask; it cannot change how that mask
    was constructed.  Empty-set ratios use one when both relevant sets are
    empty, avoiding an undefined metric for an empty support.
    """

    observer = np.asarray(observer_mask, dtype=bool)
    tracer_values = np.asarray(tracer_max_los, dtype=float)
    if observer.ndim != 2 or tracer_values.shape != observer.shape:
        raise ValueError("observer_mask and tracer_max_los must be matching two-dimensional arrays")
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("threshold must be finite and positive")
    if not np.all(np.isfinite(tracer_values)):
        raise ValueError("tracer_max_los must contain only finite values")
    tracer = tracer_values >= threshold
    intersection = int(np.count_nonzero(observer & tracer))
    observer_count = int(np.count_nonzero(observer))
    tracer_count = int(np.count_nonzero(tracer))
    union = int(np.count_nonzero(observer | tracer))
    return {
        "intersection_over_union": _safe_ratio(intersection, union),
        "dice": _safe_ratio(2 * intersection, observer_count + tracer_count),
        "xray_precision": _safe_ratio(intersection, observer_count),
        "tracer_recall": _safe_ratio(intersection, tracer_count),
    }


def _archive_member(view: str, name: str) -> str:
    return (
        "2026-06-25-c-hi-refined-projection-viewing-rerun/"
        f"xraise_grid_{view}_refined/{name}"
    )


def _archive_source(archive_path: Path, name: str, view: str) -> str:
    return f"{archive_path}::{_archive_member(view, name)}"


def _local_source(directory: Path, name: str) -> str:
    return str(directory / name)


def accepted_case_view_manifest(root: Path = ROOT) -> tuple[MapSpec, ...]:
    """Return the deterministic manifest for all three cases and three views."""

    chi_archive = root / CHI_REFINED_ARCHIVE.relative_to(ROOT)
    chi0 = root / CHI0.relative_to(ROOT)
    clo_root = root / CLO_ROOT.relative_to(ROOT)
    glo_root = root / GLO_ROOT.relative_to(ROOT)
    specs: list[MapSpec] = []
    for case in ("C-HI", "C-LO", "G-LO"):
        for view in ("0deg", "45deg", "90deg"):
            if case == "C-HI" and view != "0deg":
                sources = {
                    "corrected_xray": _archive_source(chi_archive, CORRECTED_XRAY_NAME, view),
                    "tracer_max_los": _archive_source(chi_archive, TRACER_NAME, view),
                    "horizontal_axis": _archive_source(chi_archive, HORIZONTAL_AXIS_NAME, view),
                    "z_axis": _archive_source(chi_archive, VERTICAL_AXIS_NAME, view),
                }
                specs.append(
                    MapSpec(case, view, **sources, source_type="refined_tar_archive", archive_path=str(chi_archive))
                )
                continue
            if case == "C-HI":
                directory = chi0
            elif case == "C-LO":
                directory = clo_root / f"xraise_grid_{view}"
            else:
                directory = glo_root / f"xraise_grid_{view}"
            specs.append(
                MapSpec(
                    case,
                    view,
                    corrected_xray=_local_source(directory, CORRECTED_XRAY_NAME),
                    tracer_max_los=_local_source(directory, TRACER_NAME),
                    horizontal_axis=_local_source(directory, HORIZONTAL_AXIS_NAME),
                    z_axis=_local_source(directory, VERTICAL_AXIS_NAME),
                    source_type="local_accepted",
                )
            )
    return tuple(specs)


def _load_source(source: str) -> np.ndarray:
    if "::" not in source:
        return np.loadtxt(source, delimiter="\t")
    archive_name, member_name = source.split("::", 1)
    with tarfile.open(archive_name, "r:gz") as archive:
        handle = archive.extractfile(member_name)
        if handle is None:
            raise FileNotFoundError(member_name)
        return np.loadtxt(io.StringIO(handle.read().decode("utf-8")), delimiter="\t")


def load_accepted_map(spec: MapSpec) -> LoadedMap:
    """Load one accepted triple, reading archive members without extraction."""

    corrected_xray = np.asarray(_load_source(spec.corrected_xray), dtype=float)
    tracer_max_los = np.asarray(_load_source(spec.tracer_max_los), dtype=float)
    horizontal_axis = np.asarray(_load_source(spec.horizontal_axis), dtype=float)
    z_axis = np.asarray(_load_source(spec.z_axis), dtype=float)
    validate_map_and_axes(corrected_xray, horizontal_axis, z_axis)
    if tracer_max_los.shape != corrected_xray.shape:
        raise ValueError(f"tracer shape does not match {spec.case}/{spec.view}")
    if not np.all(np.isfinite(tracer_max_los)):
        raise ValueError(f"tracer map is not finite for {spec.case}/{spec.view}")
    return LoadedMap(spec, corrected_xray, tracer_max_los, horizontal_axis, z_axis)


def load_accepted_maps(manifest: Iterable[MapSpec] | None = None) -> Iterator[LoadedMap]:
    """Lazily yield all nine accepted maps in manifest order."""

    for spec in accepted_case_view_manifest() if manifest is None else manifest:
        yield load_accepted_map(spec)
