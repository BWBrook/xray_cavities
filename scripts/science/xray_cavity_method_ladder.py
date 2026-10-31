#!/usr/bin/env python3
"""Q-032 X-ray cavity method ladder with interchangeable backgrounds.

Three tracer-blind recovery methods share one interface:

- ``legacy_area_1pct``: the production selected-age path, which keeps the
  highest-deficit 1 per cent of projected area inside 120 kpc against an
  azimuthal-median background (``build_three_case_cavity_recovery``).
- ``seed_grow_goal045``: the validated Goal 045 hemisphere seed-and-grow
  method, with its degree-6 log-polynomial observer background.
- ``deficit_threshold``: every hemisphere component whose fractional deficit
  exceeds a declared threshold.

Each method runs against its own observer background or against an
externally supplied background, such as the cavity-free map of the same view
(the oracle rung). Each method returns per-side masks split at z = 0, the
production topology class of the unsplit retained mask, and per-side volumes
under the production ellipse-depth conventions plus a solid-of-revolution
estimate about the jet axis. All production views keep the jet axis in the
sky plane at u = 0, which is what makes that estimate available.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np
from scipy.ndimage import binary_erosion, label

SCIENCE_DIR = Path(__file__).resolve().parent
if str(SCIENCE_DIR) not in sys.path:
    sys.path.insert(0, str(SCIENCE_DIR))

import build_three_case_cavity_recovery as legacy_builder
import hemisphere_seed_grow_recovery as seed_grow_module
import three_case_cavity_recovery as recovery

LEGACY = "legacy_area_1pct"
SEED_GROW = "seed_grow_goal045"
THRESHOLD = "deficit_threshold"
OBSERVER = "observer"
SIDES = ("negative_z", "positive_z")
DEPTHS = ("minor_depth", "geometric_depth", "major_depth")
VOLUME_ESTIMATORS = (*DEPTHS, "revolution")
SUPPLIED_BACKGROUND_THRESHOLD_FLOOR = 1.0e-6


@dataclass(frozen=True)
class Recovery:
    method: str
    background: str
    threshold: float
    deficit: np.ndarray
    side_masks: dict[str, np.ndarray]
    topology_class: str

    @property
    def mask(self) -> np.ndarray:
        return self.side_masks["negative_z"] | self.side_masks["positive_z"]


def _rois(horizontal: np.ndarray, vertical: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (
        recovery.build_elliptical_roi(
            horizontal, vertical, recovery.BACKGROUND_RADIUS_KPC, recovery.BACKGROUND_RADIUS_KPC
        ),
        recovery.build_elliptical_roi(
            horizontal, vertical, recovery.CANDIDATE_RADIUS_KPC, recovery.CANDIDATE_RADIUS_KPC
        ),
    )


def _supplied_deficit(image: np.ndarray, background: np.ndarray, background_roi: np.ndarray) -> np.ndarray:
    masked = np.where(background_roi, np.asarray(background, dtype=float), np.nan)
    return recovery.compute_fractional_deficit(image, masked)


def _hemispheres(vertical: np.ndarray, shape: tuple[int, int]) -> dict[str, np.ndarray]:
    zz = np.broadcast_to(vertical[:, None], shape)
    return {"negative_z": zz < 0.0, "positive_z": zz > 0.0}


def _topology(mask: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> str:
    if not np.any(mask):
        return "no_significant_component"
    labels, count = label(mask, structure=np.ones((3, 3), dtype=int))
    components = [
        recovery.Component(index, labels == index, 1.0) for index in range(1, count + 1)
    ]
    return legacy_builder._topology_class(
        recovery.summarize_components(components, horizontal, vertical)
    )


def _split(mask: np.ndarray, vertical: np.ndarray) -> dict[str, np.ndarray]:
    halves = _hemispheres(vertical, mask.shape)
    return {side: mask & halves[side] for side in SIDES}


def legacy_area_fraction(
    image: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
    *,
    background: np.ndarray | None = None,
    background_label: str = OBSERVER,
) -> Recovery:
    background_roi, candidate_roi = _rois(horizontal, vertical)
    if background is None:
        background = recovery.compute_azimuthal_median_background(
            image, horizontal, vertical, background_roi=background_roi,
            radial_bin_kpc=recovery.RADIAL_BIN_KPC,
            radial_smoothing_kpc=recovery.RADIAL_SMOOTHING_KPC,
        )
    deficit = _supplied_deficit(image, background, background_roi)
    candidate, threshold = recovery.select_area_fraction_candidate(
        deficit, candidate_roi, horizontal, vertical, fraction=1.0, high_values_are_candidates=True,
    )
    selected = recovery.label_and_filter_components(
        candidate, horizontal, vertical,
        min_area_kpc2=recovery.MIN_COMPONENT_AREA_KPC2, connectivity=recovery.CONNECTIVITY,
    )
    retained = np.zeros(image.shape, dtype=bool)
    for component in selected.components:
        retained |= component.mask
    return Recovery(
        LEGACY, background_label, float(threshold), deficit,
        _split(retained, vertical), _topology(retained, horizontal, vertical),
    )


def seed_grow(
    image: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
    *,
    background: np.ndarray | None = None,
    background_label: str = OBSERVER,
) -> Recovery:
    if background is None:
        result = seed_grow_module.recover_hemisphere_seed_grow(image, horizontal, vertical)
        masks = {side: result.hemispheres[side].mask for side in SIDES}
        deficit, threshold = result.deficit, result.support_threshold
    else:
        background_roi, candidate_roi = _rois(horizontal, vertical)
        deficit = _supplied_deficit(image, background, background_roi)
        threshold = max(
            seed_grow_module.robust_outer_annulus_threshold(deficit, horizontal, vertical),
            SUPPLIED_BACKGROUND_THRESHOLD_FLOOR,
        )
        halves = _hemispheres(vertical, image.shape)
        masks = {
            side: seed_grow_module._recover_hemisphere(
                side, deficit, candidate_roi, halves[side], threshold, horizontal, vertical
            ).mask
            for side in SIDES
        }
    union = masks["negative_z"] | masks["positive_z"]
    return Recovery(
        SEED_GROW, background_label, float(threshold), deficit, masks,
        _topology(union, horizontal, vertical),
    )


def deficit_threshold(
    image: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
    *,
    background: np.ndarray,
    background_label: str,
    threshold: float,
) -> Recovery:
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("deficit threshold must be finite and positive")
    background_roi, candidate_roi = _rois(horizontal, vertical)
    deficit = _supplied_deficit(image, background, background_roi)
    support = candidate_roi & np.isfinite(deficit) & (deficit > threshold)
    masks: dict[str, np.ndarray] = {}
    for side, half in _hemispheres(vertical, image.shape).items():
        selected = recovery.label_and_filter_components(
            support & half, horizontal, vertical,
            min_area_kpc2=recovery.MIN_COMPONENT_AREA_KPC2, connectivity=recovery.CONNECTIVITY,
        )
        side_mask = np.zeros(image.shape, dtype=bool)
        for component in selected.components:
            side_mask |= component.mask
        masks[side] = side_mask
    union = masks["negative_z"] | masks["positive_z"]
    return Recovery(
        THRESHOLD, background_label, float(threshold), deficit, masks,
        _topology(union, horizontal, vertical),
    )


def observer_radial_background(image: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> np.ndarray:
    background_roi, _ = _rois(horizontal, vertical)
    return recovery.compute_azimuthal_median_background(
        image, horizontal, vertical, background_roi=background_roi,
        radial_bin_kpc=recovery.RADIAL_BIN_KPC,
        radial_smoothing_kpc=recovery.RADIAL_SMOOTHING_KPC,
    )


def null_calibrated_threshold(
    null: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray, *, quantile: float = 99.5, floor: float = 0.05,
) -> float:
    """Deficit threshold set by the observer radial background's error on a cavity-free map."""

    background = observer_radial_background(null, horizontal, vertical)
    deficit = recovery.compute_fractional_deficit(null, background)
    _, candidate_roi = _rois(horizontal, vertical)
    values = np.abs(deficit[candidate_roi & np.isfinite(deficit)])
    return max(floor, float(np.percentile(values, quantile)))


def side_volumes(mask: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> dict[str, float]:
    """Per-side volumes: production ellipse depths summed over components,
    and the Pappus solid of revolution about the jet axis (u = 0)."""

    area = recovery._cell_area_grid(horizontal, vertical)
    volumes = {name: 0.0 for name in VOLUME_ESTIMATORS}
    if not np.any(mask):
        return volumes
    labels, count = label(mask, structure=np.ones((3, 3), dtype=int))
    components = [
        recovery.Component(index, labels == index, float(area[labels == index].sum()))
        for index in range(1, count + 1)
    ]
    for summary in recovery.summarize_components(components, horizontal, vertical):
        for depth in DEPTHS:
            volumes[depth] += summary.volumes_kpc3[depth]
    abs_u = np.broadcast_to(np.abs(horizontal)[None, :], mask.shape)
    volumes["revolution"] = float(np.pi * np.sum(abs_u[mask] * area[mask]))
    return volumes


def touches_aperture(mask: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> bool:
    _, candidate_roi = _rois(horizontal, vertical)
    return bool(np.any(mask & ~binary_erosion(candidate_roi)))


def score_rows(
    result: Recovery,
    horizontal: np.ndarray,
    vertical: np.ndarray,
    *,
    truth_masks: Mapping[str, np.ndarray] | None = None,
    truth_volumes: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """One row per side with areas, volumes and optional truth comparison."""

    area = recovery._cell_area_grid(horizontal, vertical)
    _, candidate_roi = _rois(horizontal, vertical)
    rows: list[dict[str, Any]] = []
    for side in SIDES:
        mask = result.side_masks[side]
        volumes = side_volumes(mask, horizontal, vertical)
        row: dict[str, Any] = {
            "method": result.method,
            "background": result.background,
            "threshold": result.threshold,
            "topology_class": result.topology_class,
            "side": side,
            "detected": bool(np.any(mask)),
            "recovered_area_kpc2": float(area[mask].sum()),
            "touches_aperture": touches_aperture(mask, horizontal, vertical),
            **{f"volume_{name}_kpc3": volumes[name] for name in VOLUME_ESTIMATORS},
        }
        if truth_masks is not None and truth_volumes is not None:
            truth = np.asarray(truth_masks[side], dtype=bool)
            true_area = float(area[truth].sum())
            overlap = float(area[mask & truth].sum())
            true_volume = float(truth_volumes[side])
            row.update({
                "true_area_kpc2": true_area,
                "true_volume_kpc3": true_volume,
                "true_area_inside_aperture_fraction": (
                    float(area[truth & candidate_roi].sum()) / true_area if true_area else float("nan")
                ),
                "completeness": overlap / true_area if true_area else float("nan"),
                "purity": overlap / row["recovered_area_kpc2"] if row["recovered_area_kpc2"] else float("nan"),
                **{
                    f"volume_ratio_{name}": volumes[name] / true_volume if true_volume else float("nan")
                    for name in VOLUME_ESTIMATORS
                },
            })
        rows.append(row)
    return rows
