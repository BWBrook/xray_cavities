"""Fit radial backgrounds to the remaining sky after a projected source exclusion."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter1d

import three_case_cavity_recovery as recovery


SECTORS = 12
MIN_PIXELS = 8
MIN_SECTORS = 3
MODELS = ("flat", "log_slope")


@dataclass
class RadialFit:
    backgrounds: dict[str, np.ndarray | None]
    status: dict[str, str]
    rows: list[dict]


def _widths(centres, edges):
    edges = np.asarray(edges, dtype=float)
    if edges.shape != (len(centres) + 1,) or not np.all(np.isfinite(edges)):
        raise ValueError("each axis needs finite native edges for every pixel")
    widths = np.diff(edges)
    if not (np.all(widths > 0) and np.all(np.diff(centres) > 0) or
            np.all(widths < 0) and np.all(np.diff(centres) < 0)):
        raise ValueError("edges and centres must have the same strict ordering")
    if np.any(centres <= np.minimum(edges[:-1], edges[1:])) or np.any(centres >= np.maximum(edges[:-1], edges[1:])):
        raise ValueError("pixel centres must lie within their native edges")
    return np.abs(widths)


def _sector_bits(sector_ids):
    return sum(1 << int(sector) for sector in np.unique(sector_ids))


def _optional(value):
    return float(value) if np.isfinite(value) else None


class RadialImage:
    """Reuse exact physical areas, ring membership and the original fit across exclusions."""

    def __init__(self, image, horizontal_axis_kpc, z_axis_kpc, horizontal_edges_kpc, z_edges_kpc):
        values = np.asarray(image, dtype=float)
        u, z = np.asarray(horizontal_axis_kpc, dtype=float), np.asarray(z_axis_kpc, dtype=float)
        recovery.validate_map_and_axes(values, u, z)
        self._area = np.outer(_widths(z, z_edges_kpc), _widths(u, horizontal_edges_kpc)).ravel()
        self._values = values.ravel()
        self._radius = np.hypot(u[None, :], z[:, None])
        self._roi = recovery.build_elliptical_roi(u, z, recovery.BACKGROUND_RADIUS_KPC, recovery.BACKGROUND_RADIUS_KPC)
        self.baseline = recovery.compute_azimuthal_median_background(
            values, u, z, background_roi=self._roi, radial_bin_kpc=recovery.RADIAL_BIN_KPC,
            radial_smoothing_kpc=recovery.RADIAL_SMOOTHING_KPC,
        )
        angle = np.mod(np.arctan2(z[:, None], u[None, :]), 2 * np.pi)
        self._sectors = np.minimum((angle * (SECTORS / (2 * np.pi))).astype(np.intp), SECTORS - 1).ravel()

        radius = self._radius.ravel()
        roi_pixels = np.flatnonzero(self._roi)
        step = recovery.RADIAL_BIN_KPC
        self._edges = step * np.arange(int(np.floor(radius[roi_pixels].max() / step)) + 2)
        self._centres = (self._edges[:-1] + self._edges[1:]) / 2
        index = np.searchsorted(self._edges, radius[roi_pixels], side="right") - 1
        order = np.argsort(index, kind="stable")
        splits = np.searchsorted(index[order], np.arange(1, len(self._centres)))
        groups = np.split(roi_pixels[order], splits)
        self._valid = [group[self._values[group] > 0] for group in groups]
        self._reference_rows = []
        medians = np.full(self._centres.shape, np.nan)
        for i, (group, valid) in enumerate(zip(groups, self._valid, strict=True)):
            if valid.size:
                medians[i] = np.median(self._values[valid])
            bits = _sector_bits(self._sectors[valid])
            self._reference_rows.append(dict(
                bin_index=i, r_inner_kpc=float(self._edges[i]), r_outer_kpc=float(self._edges[i + 1]),
                r_center_kpc=float(self._centres[i]), roi_pixels=group.size,
                roi_area_kpc2=float(self._area[group].sum()), valid_pixels=valid.size,
                valid_area_kpc2=float(self._area[valid].sum()), valid_sectors=bits.bit_count(),
                valid_sector_bits=bits, full_median=_optional(medians[i]),
                required_pixels=min(MIN_PIXELS, valid.size),
                required_sectors=min(MIN_SECTORS, bits.bit_count()),
            ))
        # The frozen fitter ends its mesh at the last original positive pixel.
        # Keep rows for any farther map pixels, but preserve that smoothing boundary.
        self._fit_bins = int(np.flatnonzero(np.isfinite(medians))[-1]) + 1
        supported = np.isfinite(medians)
        reference = np.interp(self._centres, self._centres[supported], medians[supported])
        self._baseline_profile = self._smooth(reference)

    def _smooth(self, filled):
        profile = gaussian_filter1d(
            filled[:self._fit_bins], sigma=recovery.RADIAL_SMOOTHING_KPC / recovery.RADIAL_BIN_KPC,
            mode="nearest",
        )
        return np.pad(profile, (0, len(filled) - len(profile)), mode="edge")

    def _project(self, profile):
        centres = self._centres[:self._fit_bins]
        image = np.interp(np.minimum(self._radius, centres[-1]), centres, profile[:self._fit_bins])
        image[~self._roi] = np.nan
        return image

    def fit(self, excluded):
        """Exclude Boolean sky pixels only from the median. Both fits use the original radial mesh.

        Direct support needs eight retained pixels in at least three of twelve 30-degree sectors,
        capped at the positive pixel/sector counts originally available in that annulus. Interior
        gaps interpolate median brightness linearly in radius. Both models extend the last median
        outward. Before 10-kpc Gaussian smoothing, the inward model is either the first median or
        an exponential anchored there, with log slope estimated from the first three supported
        medians (two when only two exist). Smoothing may round the ends of a flat continuation.
        """
        excluded = np.asarray(excluded)
        if excluded.shape != self._roi.shape or excluded.dtype != bool:
            raise ValueError("exclusion must be a Boolean mask on the original sky grid")
        mask = excluded.ravel()
        rows, measured = [], np.full(self._centres.shape, np.nan)
        changed = False
        for i, (valid, ref) in enumerate(zip(self._valid, self._reference_rows, strict=True)):
            kept = valid[~mask[valid]]
            changed |= kept.size != valid.size
            bits = _sector_bits(self._sectors[kept])
            median = float(np.median(self._values[kept])) if kept.size else None
            if kept.size and kept.size >= ref["required_pixels"] and bits.bit_count() >= ref["required_sectors"]:
                measured[i] = median
            area = float(self._area[kept].sum())
            rows.append(dict(
                **ref, retained_pixels=kept.size, retained_area_kpc2=area,
                retained_area_fraction=area / ref["valid_area_kpc2"] if valid.size else None,
                retained_sectors=bits.bit_count(), retained_sector_bits=bits, retained_median=median,
                support_class="unconstrained", baseline_profile=float(self._baseline_profile[i]),
                flat_unsmoothed=None, flat_profile=None, log_slope_unsmoothed=None, log_slope_profile=None,
            ))

        indices = np.flatnonzero(np.isfinite(measured))
        backgrounds = dict.fromkeys(MODELS)
        if not indices.size:
            return RadialFit(backgrounds, dict.fromkeys(MODELS, "no_supported_annuli"), rows)

        first, last = indices[0], indices[-1]
        for i, row in enumerate(rows):
            if np.isfinite(measured[i]):
                row["support_class"] = "direct"
            elif i < first:
                row["support_class"] = "inner_extrapolated"
            elif i > last:
                row["support_class"] = "outer_extrapolated"
            else:
                row["support_class"] = "interpolated"

        if changed and indices.size == 1 and len(rows) > 1:
            return RadialFit(backgrounds, dict.fromkeys(MODELS, "one_supported_annulus"), rows)

        filled = np.interp(self._centres, self._centres[indices], measured[indices])
        status = dict.fromkeys(MODELS, "ok")
        flat = self._smooth(filled)
        backgrounds["flat"] = self._project(flat) if changed else self.baseline
        log_filled, log_profile = filled, flat
        if changed and first > 0:
            anchors = indices[:3]
            radius = self._centres[anchors]
            offset = radius - radius.mean()
            slope = np.dot(offset, np.log(measured[anchors])) / np.dot(offset, offset)
            log_filled = filled.copy()
            log_brightness = np.log(measured[first]) + slope * (self._centres[:first] - self._centres[first])
            with np.errstate(over="ignore", under="ignore"):
                log_filled[:first] = np.exp(log_brightness)
            if np.any(~np.isfinite(log_filled) | (log_filled <= 0)):
                status["log_slope"] = "nonfinite_inward_continuation"
                log_profile = None
            else:
                log_profile = self._smooth(log_filled)
        if log_profile is not None:
            backgrounds["log_slope"] = backgrounds["flat"] if log_profile is flat else self._project(log_profile)
        for i, row in enumerate(rows):
            row.update(flat_unsmoothed=float(filled[i]), flat_profile=float(flat[i]))
            if log_profile is not None:
                row.update(log_slope_unsmoothed=float(log_filled[i]), log_slope_profile=float(log_profile[i]))
        return RadialFit(backgrounds, status, rows)


def prepare_radial_fit(image, horizontal_axis_kpc, z_axis_kpc, horizontal_edges_kpc, z_edges_kpc):
    return RadialImage(image, horizontal_axis_kpc, z_axis_kpc, horizontal_edges_kpc, z_edges_kpc)
