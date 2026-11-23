"""Compare the independent G-HI/20 front with the three exposed X-ray images."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from dataclasses import dataclass
from pathlib import Path

import build_q032_source_emission as emission
import numpy as np
from run_background_refit_blind import AXES, validate_axes
from scipy.ndimage import binary_erosion, binary_fill_holes
from scipy.spatial import cKDTree

HASH = emission.native.sha256_file
ANGLES = (0, 45, 90)
BLUE, ORANGE = emission.METHODS
SIDES = ("negative_z", "positive_z")
ARMS = {
    "primary": "front_path_kpc",
    "loose": "front_path_loose_kpc",
    "tight": "front_path_tight_kpc",
    "wide": "front_path_wide_kpc",
}
SOURCE_HASHES = {
    0: "46935fca242ddc96c4ad8776db1b4e00e76ec27f9215a923308e29f323d99e80",
    45: "fb0ed2f4b706b00cbb13a28c0fe87ae7455a25e3cf8c562f6dcacc122b1ac896",
    90: "d77542fff88a0866e772623a6595f1a8babebb9a5d0dae5f349262b1576b5956",
}
AGE = 19.999614294878622
PRODUCER_SHA = "4ca1a4f445ae1d65d6a7aa7619ccea7745d545266656875ddfb469487affd31e"


def write_rows(path, rows):
    if not rows:
        raise ValueError(f"No rows for {path}")
    with (
        path.open("wb") as raw,
        io.TextIOWrapper(
            gzip.GzipFile(fileobj=raw, filename="", mode="wb", mtime=0)
            if path.suffix == ".gz"
            else raw,
            newline="",
        ) as out,
    ):
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@dataclass
class Grid:
    u: np.ndarray
    ue: np.ndarray
    z: np.ndarray
    ze: np.ndarray

    @property
    def area(self):
        return np.diff(self.ze)[:, None] * np.diff(self.ue)[None, :]


@dataclass
class Edges:
    lo: np.ndarray
    hi: np.ndarray
    length: np.ndarray
    row: np.ndarray
    col: np.ndarray
    exterior: np.ndarray
    pixel_width: np.ndarray

    @property
    def mid(self):
        return (self.hi + self.lo) * 0.5


def segments(mask, grid):
    """Return exposed physical pixel faces and the occupied pixel at each face."""
    mask = np.asarray(mask, dtype=bool)
    occupied = np.pad(mask, 1)
    exterior_air = ~binary_fill_holes(occupied)
    los, his, rows, cols, exterior, widths = [], [], [], [], [], []
    du, dz = np.diff(grid.ue), np.diff(grid.ze)
    for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        neighbour = occupied[
            1 + dr : 1 + dr + mask.shape[0], 1 + dc : 1 + dc + mask.shape[1]
        ]
        iz, iu = np.nonzero(mask & ~neighbour)
        lo = np.column_stack((grid.ue[iu + int(dc == 1)], grid.ze[iz + int(dr == 1)]))
        hi = lo.copy()
        if dr:
            hi[:, 0] = grid.ue[iu + 1]
        else:
            hi[:, 1] = grid.ze[iz + 1]
        los.append(lo)
        his.append(hi)
        rows.append(iz)
        cols.append(iu)
        exterior.append(exterior_air[iz + 1 + dr, iu + 1 + dc])
        widths.append(dz[iz] if dr else du[iu])
    lo, hi = np.concatenate(los), np.concatenate(his)
    return Edges(
        lo,
        hi,
        np.linalg.norm(hi - lo, axis=1),
        np.concatenate(rows),
        np.concatenate(cols),
        np.concatenate(exterior),
        np.concatenate(widths),
    )


class ContourDistance:
    def __init__(self, mask, grid):
        self.mask = mask
        self.grid = grid
        self.edges = segments(mask, grid)
        self.tree = cKDTree(self.edges.mid) if self.edges.length.size else None

    def signed(self, points):
        """Exact point-to-segment distance on the non-uniform rectangular grid."""
        if self.tree is None or not len(points):
            return np.full(len(points), np.nan), np.full(len(points), -1, dtype=int)
        if len(points) > 256:
            results = [
                self.signed(points[start : start + 256])
                for start in range(0, len(points), 256)
            ]
            return tuple(np.concatenate(group) for group in zip(*results))
        midpoint_distance, _ = self.tree.query(points)
        # No segment with a midpoint beyond this bound can beat the first candidate.
        candidates = self.tree.query_ball_point(
            points, midpoint_distance + self.edges.length.max() / 2 + 1e-12
        )
        lengths = np.fromiter(map(len, candidates), dtype=int, count=len(candidates))
        if np.any(lengths == 0):
            raise ValueError("Missing nearest physical edge candidate")
        references = np.concatenate(candidates).astype(int)
        expanded = np.repeat(points, lengths, axis=0)
        closest = np.clip(
            expanded, self.edges.lo[references], self.edges.hi[references]
        )
        dsq = np.sum((expanded - closest) ** 2, axis=1)
        starts = np.r_[0, np.cumsum(lengths)[:-1]]
        minima = np.minimum.reduceat(dsq, starts)
        # Use the lowest candidate occurrence when edges meet at the same corner.
        positions = np.arange(len(dsq))
        nearest = np.minimum.reduceat(
            np.where(dsq == np.repeat(minima, lengths), positions, len(dsq)), starts
        )
        g = self.grid
        j = np.searchsorted(g.ue, points[:, 0], side="right") - 1
        i = np.searchsorted(g.ze, points[:, 1], side="right") - 1
        valid = (
            (i >= 0) & (i < self.mask.shape[0]) & (j >= 0) & (j < self.mask.shape[1])
        )
        sign = np.ones(len(points))
        sign[valid] = np.where(self.mask[i[valid], j[valid]], -1, 1)
        return sign * np.sqrt(minima), references[nearest]


def lateral_pixels(orange, tracer, u):
    outside = np.zeros_like(orange)
    for direction in (-1, 1):
        position = direction * u
        half = position > 0
        selected = tracer[:, half]
        limit = np.max(np.where(selected, position[half], -np.inf), axis=1)
        outside[:, half] = (
            orange[:, half]
            & np.isfinite(limit)[:, None]
            & (position[half] > limit[:, None])
        )
    return outside


def profile_indices(g, lateral, path):
    rows = []
    du = np.diff(g.ue)
    for side, use in zip(SIDES, (g.z < 0, g.z > 0)):
        indices = np.flatnonzero(use)
        for label, feature in (("lateral_arc", lateral), ("lobe", path)):
            integral = np.sum(feature[indices] * du, axis=1)
            index = int(indices[np.argmax(integral)]) if np.max(integral) > 0 else None
            rows.append((side, label, index))
    return rows


def weighted_quantile(data, weights, q):
    ordered = np.argsort(data, kind="stable")
    points = np.cumsum(weights[ordered])
    target = np.clip(q, 0, 1) * points[-1]
    return float(data[ordered[min(np.searchsorted(points, target), len(points) - 1)]])


def separation_rows(angle, g, orange, blue, lateral, references):
    rows = []
    detectors = [
        ("orange_5pct", segments(orange, g)),
        ("blue_seed_grow", segments(blue, g)),
    ]
    for ref_name, (footprint, resolution) in references.items():
        ref = ContourDistance(footprint, g)
        for method, observed in detectors:
            if observed.length.size:
                signed, near = ref.signed(observed.mid)
            else:
                signed, near = np.empty(0), np.empty(0, dtype=int)
            subsets = {"all": np.ones(len(signed), dtype=bool)}
            if method == "orange_5pct":
                subsets["lateral_arc"] = lateral[observed.row, observed.col]
            for subset, select in subsets.items():
                for side, h in zip(
                    SIDES, (g.z[observed.row] < 0, g.z[observed.row] > 0)
                ):
                    selection = select & h
                    d = signed[selection]
                    length = observed.length[selection]
                    nearest = near[selection]
                    reference_half = (
                        g.z[ref.edges.row] < 0
                        if side == "negative_z"
                        else g.z[ref.edges.row] > 0
                    )
                    local_count = int(reference_half.sum())
                    row = {
                        "view_deg": angle,
                        "reference": ref_name,
                        "method": method,
                        "observer_region": subset,
                        "hemisphere": side,
                        "segments": len(d),
                        "observed_perimeter_kpc": float(length.sum()),
                        "reference_segments": len(ref.edges.length),
                        "same_hemisphere_reference_segments": local_count,
                    }
                    stats = {
                        "nearest_in_other_hemisphere_fraction": None,
                        "signed_p10_kpc": None,
                        "signed_median_kpc": None,
                        "signed_p90_kpc": None,
                        "abs_median_kpc": None,
                        "within_one_sky_pixel_fraction": None,
                        "signed_median_native_cells": None,
                        "within_one_native_cell_fraction": None,
                        "inner_hole_edge_within_one_native_cell_fraction": None,
                        "outer_edge_within_one_native_cell_fraction": None,
                        "farther_inside_fraction": None,
                        "farther_outside_fraction": None,
                    }
                    if len(d) and local_count:
                        stats["nearest_in_other_hemisphere_fraction"] = float(
                            length[~reference_half[nearest]].sum() / length.sum()
                        )
                        for q, name in (
                            (0.1, "signed_p10_kpc"),
                            (0.5, "signed_median_kpc"),
                            (0.9, "signed_p90_kpc"),
                        ):
                            stats[name] = weighted_quantile(d, length, q)

                        def share(flag, physical_length=length):
                            return float(
                                physical_length[flag].sum() / physical_length.sum()
                            )

                        stats["abs_median_kpc"] = weighted_quantile(
                            np.abs(d), length, 0.5
                        )
                        stats["within_one_sky_pixel_fraction"] = share(
                            np.abs(d) <= ref.edges.pixel_width[nearest]
                        )
                        if resolution is not None:
                            scale = resolution[
                                ref.edges.row[nearest], ref.edges.col[nearest]
                            ]
                            if not np.all(np.isfinite(scale) & (scale > 0)):
                                raise ValueError(
                                    "missing native resolution at a front pixel"
                                )
                            near_scale = np.abs(d) <= scale
                            stats.update(
                                signed_median_native_cells=weighted_quantile(
                                    d / scale, length, 0.5
                                ),
                                within_one_native_cell_fraction=share(near_scale),
                                inner_hole_edge_within_one_native_cell_fraction=share(
                                    near_scale & ~ref.edges.exterior[nearest]
                                ),
                                outer_edge_within_one_native_cell_fraction=share(
                                    near_scale & ref.edges.exterior[nearest]
                                ),
                                farther_inside_fraction=share(d < -scale),
                                farther_outside_fraction=share(d > scale),
                            )
                    rows.append({**row, **stats})
    return rows


def view_inputs(data):
    g = Grid(*validate_axes(data, data["path_C_kpc"].shape))
    path = data["path_C_kpc"]
    raw = data["retained_image"]
    masks = {
        method: data[f"original_mask_{method}"].astype(bool)
        for method in (BLUE, ORANGE)
    }
    backgrounds = {
        method: data[f"original_background_{method}"] for method in (BLUE, ORANGE)
    }
    lateral = lateral_pixels(masks[ORANGE], path > 0, g.u)
    return g, path, raw, masks, backgrounds, lateral


def baseline(inputs, output):
    receipt_path = inputs / "completion.json"
    if HASH(receipt_path) != PRODUCER_SHA:
        raise ValueError("original development producer receipt hash differs")
    receipt = json.loads(receipt_path.read_text())
    if (receipt["case"], receipt["snapshot_index"], receipt["actual_time_myr"]) != (
        "G-HI",
        20,
        AGE,
    ):
        raise ValueError("Development receipt identity mismatch")
    stats, profile_list, dist, controls = [], [], [], {}
    for angle in ANGLES:
        p = inputs / f"G-HI_0020_{angle}deg.npz"
        if (
            HASH(p) != SOURCE_HASHES[angle]
            or receipt["files"][p.name]["sha256"] != SOURCE_HASHES[angle]
        ):
            raise ValueError(f"Development map identity differs at {angle} degrees")
        with np.load(p, allow_pickle=False) as data:
            g, path, raw, masks, bg, lateral = view_inputs(data)
            controls[angle] = velocity_replacement_control(
                inputs, receipt, angle, data, g, path, raw, masks, bg
            )
            dist += separation_rows(
                angle,
                g,
                masks[ORANGE],
                masks[BLUE],
                lateral,
                {"full_lobe": (path > 0, None)},
            )
            for side, name, i in profile_indices(g, lateral, path):
                profile_list.append(
                    {
                        "view_deg": angle,
                        "hemisphere": side,
                        "profile": name,
                        "row": i,
                        "z_kpc": g.z[i] if i is not None else None,
                    }
                )
            for side, half in zip(SIDES, (g.z[:, None] < 0, g.z[:, None] > 0)):
                for m in [ORANGE, BLUE]:
                    selected = masks[m] & half
                    tracer = (path > 0) & half
                    area = g.area
                    stats.append(
                        {
                            "view_deg": angle,
                            "hemisphere": side,
                            "method": m,
                            "selected_kpc2": area[selected].sum(),
                            "tracer_kpc2": area[tracer].sum(),
                            "tracer_missed_kpc2": area[tracer & ~selected].sum(),
                            "selected_outside_kpc2": area[selected & ~tracer].sum(),
                            "lateral_orange_kpc2": area[lateral & half].sum()
                            if m == ORANGE
                            else None,
                        }
                    )
    write_rows(output / "original_geometry.csv", stats)
    write_rows(output / "profile_positions.csv", profile_list)
    write_rows(output / "original_contour_to_lobe.csv", dist)
    checks = {
        "case": "G-HI",
        "snapshot_index": 20,
        "actual_time_myr": AGE,
        "view_map_sha256": SOURCE_HASHES,
        "source_receipt_sha256": HASH(receipt_path),
        "qualifications": receipt["scientific_qualification"]["holds"],
        "native_source_sha256": {
            r["role"]: r["sha256"] for r in receipt["provenance"]["native_inputs"]
        },
        "historical_velocity_replacement_control": controls,
    }
    (output / "observer_inputs.json").write_text(json.dumps(checks, indent=2) + "\n")
    return checks


def emission_partition(data, native):
    fields = {}
    checks = {}
    for state in ("current", "initial"):
        whole = data[f"brightness_{state}_retained_linear_whole"]
        parts = {
            "whole": whole,
            "lobe": data[f"brightness_{state}_retained_linear_C"],
            "front": native[f"front_{state}_brightness"],
            "rest": native[f"rest_{state}_brightness"],
        }
        total = parts["lobe"] + parts["front"] + parts["rest"]
        if any(
            a.shape != whole.shape or not np.isfinite(a).all() for a in parts.values()
        ):
            raise ValueError(f"{state}: non-finite or mismatched projected emission")
        scale = (
            np.abs(parts["lobe"])
            + np.abs(parts["front"])
            + np.abs(parts["rest"])
            + np.abs(whole)
        )
        checks[state] = emission.closure(
            f"{state} C + front + complement vs whole", total, whole, scale
        )
        relative = np.divide(
            np.abs(total - whole), scale, out=np.zeros_like(scale), where=scale > 0
        )
        checks[state]["max_per_pixel_relative_error"] = float(relative.max())
        if relative.max() > 1e-8:
            raise ValueError(f"{state}: local projected emission partition failed")
        if f"lobe_{state}_brightness" in native:
            checks[state]["independent_lobe"] = emission.closure(
                f"{state} re-integrated lobe",
                native[f"lobe_{state}_brightness"],
                parts["lobe"],
            )
        fields[state] = parts
    return fields, checks


def measurement_regions(masks, tracer, lateral):
    return {
        "missed_lobe_orange": tracer & ~masks[ORANGE],
        "missed_lobe_blue": tracer & ~masks[BLUE],
        "orange_lateral_excess": lateral,
        "orange_lateral_perimeter": lateral & ~binary_erosion(masks[ORANGE]),
        "full_lobe_sightlines": tracer,
    }


def footprint_overlap(angle, g, selected_regions, native):
    primary = native["front_path_kpc"] > 0
    other = native["other_path_kpc"] > 0
    boundary = native["boundary_path_kpc"] > 0
    area = g.area
    rows = []
    for name, region in selected_regions.items():
        for side, half in zip(SIDES, (g.z[:, None] < 0, g.z[:, None] > 0)):
            selected = region & half
            total = float(area[selected].sum())
            row = {
                "view_deg": angle,
                "hemisphere": side,
                "region": name,
                "area_kpc2": total,
            }
            for cat, mask in [
                ("dominant", primary),
                ("other_detached", other),
                ("boundary_connected", boundary),
                ("dominant_and_alternative", primary & (other | boundary)),
                ("no_compression", ~(primary | other | boundary)),
            ]:
                row[cat + "_area_fraction"] = (
                    float(area[selected & mask].sum() / total) if total else None
                )
            rows.append(row)
    return rows


def region_rows(angle, g, fields, regions, radial_background):
    rows = []
    area = g.area
    for name, boolean in regions.items():
        for side, half in zip(SIDES, (g.z[:, None] < 0, g.z[:, None] > 0)):
            select = boolean & half
            weights = area[select]
            row = {
                "view_deg": angle,
                "hemisphere": side,
                "region": name,
                "pixels": int(select.sum()),
                "area_kpc2": float(weights.sum()),
            }
            for component in ("lobe", "front", "rest", "whole"):
                now = float(np.sum(weights * fields["current"][component][select]))
                initial = float(np.sum(weights * fields["initial"][component][select]))
                row[f"{component}_current"] = now
                row[f"{component}_initial"] = initial
                row[f"{component}_current_minus_initial"] = now - initial
            background = float(np.sum(weights * radial_background[select]))
            row["radial_background_minus_current_whole"] = (
                background - row["whole_current"]
            )
            denom = row["lobe_initial"] - row["lobe_current"]
            # A signed filling ratio is undefined for an unresolved or zero lobe decrement.
            scale = abs(row["lobe_initial"]) + abs(row["lobe_current"])
            row["front_gain_over_lobe_deficit"] = (
                row["front_current_minus_initial"] / denom
                if denom > max(1e-12 * scale, 0)
                else None
            )
            rows.append(row)
    return rows


def recovery_metrics(g, mask, path, side_mask, reference_mask):
    select = mask & side_mask
    tracer = (path > 0) & side_mask
    area = g.area
    found = float(area[select].sum())
    target = float(area[tracer].sum())
    overlap = float(area[select & tracer].sum())
    volume = emission.native.exact_abs_u_moments(select, g.ue, g.ze)[
        "symmetrized_revolution_kpc3"
    ]
    native_volume = float(np.sum(area * path * side_mask))
    aperture = g.u[None, :] ** 2 + g.z[:, None] ** 2 <= 120**2
    return {
        "selected_kpc2": found,
        "added_vs_baseline_kpc2": float(area[select & ~reference_mask].sum()),
        "lost_vs_baseline_kpc2": float(
            area[reference_mask & side_mask & ~select].sum()
        ),
        "truth_kpc2": target,
        "false_area_kpc2": found - overlap,
        "completeness": overlap / target if target else None,
        "purity": overlap / found if found else None,
        "truth_outside_aperture_fraction": float(
            area[tracer & ~aperture].sum() / target
        )
        if target
        else None,
        "touches_aperture": bool(emission.ladder.touches_aperture(select, g.u, g.z)),
        "nondetection": not bool(select.any()),
        "inferred_volume_kpc3": float(volume),
        "native_lobe_kpc3": native_volume,
        "inferred_over_native": volume / native_volume if native_volume else None,
    }


def observer_replacement(angle, g, raw, path, masks, bg, fields, data, retained_z):
    original = emission.original_observers(raw, g.u, retained_z)
    now = fields["current"]["whole"]
    replacement = now + fields["initial"]["front"] - fields["current"]["front"]
    baseline_refit = emission.original_observers(now, g.u, g.z)
    changed_refit = emission.original_observers(replacement, g.u, g.z)
    rows = []
    display = {}
    for method in (ORANGE, BLUE):
        if not np.array_equal(
            original[method]["mask"], masks[method]
        ) or not np.allclose(
            original[method]["background"],
            bg[method],
            equal_nan=True,
            atol=0,
            rtol=2e-10,
        ):
            raise ValueError(
                f"original G-HI observer failed to reproduce {angle}/{method}"
            )
        original[method]["background"] = bg[method]
        modes = {
            "original": masks[method],
            "exact_original_background": emission.detect_fixed(
                now, g.u, g.z, method, original[method]
            ),
            "exact_refit_background": baseline_refit[method]["mask"],
            "replace_same_cells_original_background": emission.detect_fixed(
                replacement, g.u, g.z, method, original[method]
            ),
            "replace_same_cells_refit_background": changed_refit[method]["mask"],
        }
        for name, suffix in (
            ("exact_original_background", "exact_projection_fixed"),
            ("exact_refit_background", "exact_projection_refit"),
        ):
            if not np.array_equal(
                modes[name], data[f"mask_retained_linear_v100_{method}_{suffix}"]
            ):
                raise ValueError(
                    f"original exact-edge comparator failed at {angle}/{method}/{name}"
                )
        for mode, selection in modes.items():
            reference = {
                "replace_same_cells_original_background": "exact_original_background",
                "replace_same_cells_refit_background": "exact_refit_background",
            }.get(mode, "original")
            for side, half in zip(SIDES, (g.z[:, None] < 0, g.z[:, None] > 0)):
                rows.append(
                    dict(
                        view_deg=angle,
                        method=method,
                        comparison=mode,
                        hemisphere=side,
                        reference=reference,
                        **recovery_metrics(g, selection, path, half, modes[reference]),
                    )
                )
        display[method] = modes
    display["image"] = replacement
    display["radial_background_refit"] = changed_refit[ORANGE]["background"]
    return rows, display


def original_z_axis(inputs, receipt, angle):
    path = (
        inputs.parent.parent
        / "compact_inputs"
        / "geometry"
        / f"{angle}deg"
        / "z_kpc.tsv"
    )
    if (
        HASH(path)
        != receipt["provenance"]["compact_inputs"][f"view{angle}_vertical"]["sha256"]
    ):
        raise ValueError("original text-axis identity mismatch")
    return np.loadtxt(path)


def velocity_replacement_control(inputs, receipt, angle, data, g, path, raw, masks, bg):
    # This is a reproducibility control for the optics. It never defines a compression front.
    saved = {}
    for epoch in ("initial", "current"):
        for new, old in [("front", "A_v100"), ("rest", "E_v100")]:
            saved[f"{new}_{epoch}_brightness"] = data[
                f"brightness_{epoch}_retained_linear_{old}"
            ]
    fields, closure = emission_partition(data, saved)
    _, display = observer_replacement(
        angle,
        g,
        raw,
        path,
        masks,
        bg,
        fields,
        data,
        original_z_axis(inputs, receipt, angle),
    )
    n = 0
    for method in (ORANGE, BLUE):
        for mode, old in [
            ("replace_same_cells_original_background", "ambient_replaced_fixed"),
            ("replace_same_cells_refit_background", "ambient_replaced_refit"),
        ]:
            if not np.array_equal(
                display[method][mode], data[f"mask_retained_linear_v100_{method}_{old}"]
            ):
                raise ValueError(
                    f"Older 100 km/s replacement control failed for {angle}/{method}/{mode}"
                )
            n += 1
    return {
        "original_detector_masks_matched": 2,
        "exact_original_fixed_and_refitted_masks_matched": 4,
        "velocity_replacement_fixed_and_refitted_masks_matched": n,
        "brightness_partition": closure,
    }


def write_profile_values(
    angle, g, indices, fields, path, raw, bg, native, display, masks
):
    rows = []
    for side, label, i in indices:
        if i is None:
            continue
        for j in np.flatnonzero(np.abs(g.u) <= 125):
            row = {
                "view_deg": angle,
                "hemisphere": side,
                "profile": label,
                "z_kpc": g.z[i],
                "u_kpc": g.u[j],
                "u_left_kpc": g.ue[j],
                "u_right_kpc": g.ue[j + 1],
                "lobe_path_kpc": path[i, j],
                "front_path_kpc": native["front_path_kpc"][i, j],
                "raw_brightness": raw[i, j],
                "original_radial_background": bg[ORANGE][i, j],
                "original_seed_background": bg[BLUE][i, j],
                "exact_brightness": fields["current"]["whole"][i, j],
                "front_current": fields["current"]["front"][i, j],
                "front_initial": fields["initial"]["front"][i, j],
                "lobe_current": fields["current"]["lobe"][i, j],
                "rest_current": fields["current"]["rest"][i, j],
                "replacement": display["image"][i, j],
                "replacement_radial_background": display["radial_background_refit"][
                    i, j
                ],
                "original_blue": int(masks[BLUE][i, j]),
                "original_orange": int(masks[ORANGE][i, j]),
            }
            rows.append(row)
    return rows


def run(inputs, native_dir, front_receipt, output):
    # The retained map receipt binds its full native inputs, independently of the new front extraction.
    checks = baseline(inputs, output)
    source = json.loads((inputs / "completion.json").read_text())
    receipt = json.loads(front_receipt.read_text())
    native_products = receipt["files"]
    bound_native = receipt["native_inputs_sha256"]
    if receipt["source_producer_sha256"] != PRODUCER_SHA:
        raise ValueError("front receipt binds a different development-map producer")
    geometry_only = receipt.get("product", "").startswith("native geometry ready")
    for name in ("current_h5", "initial_h5", "grid_file", "environment"):
        if bound_native[name] != checks["native_source_sha256"][name]:
            raise ValueError(f"front and observer native identities differ for {name}")
    if (receipt["case"], receipt["snapshot_index"]) != ("G-HI", 20) or abs(
        receipt["actual_time_myr"] - AGE
    ) > 1e-8:
        raise ValueError("front receipt differs from the exposed case or time")
    overlap = []
    distances = []
    regions = []
    recovery = []
    profiles = []
    per_view = {}
    from render_compressive_front import overlay_figure, profile_figure, shared_norms

    norms = shared_norms(inputs)
    for angle in ANGLES:
        name = f"G-HI_0020_{angle}deg.npz"
        front_path = native_dir / name
        expected = native_products[name]
        if isinstance(expected, dict):
            expected = expected["sha256"]
        if HASH(front_path) != expected:
            raise ValueError(f"front input hash mismatch at {angle} degrees")
        with (
            np.load(inputs / name, allow_pickle=False) as data,
            np.load(front_path, allow_pickle=False) as archive,
        ):
            native = {key: archive[key] for key in archive.files}
            g, path, raw, masks, bg, lateral = view_inputs(data)
            if any(not np.array_equal(data[key], native[key]) for key in AXES):
                raise ValueError("front and observer sky grids differ")
            for k in (*ARMS.values(), "other_path_kpc", "boundary_path_kpc"):
                if (
                    native[k].shape != path.shape
                    or not np.isfinite(native[k]).all()
                    or (native[k] < 0).any()
                ):
                    raise ValueError(f"invalid front path: {k}")
            refs = {
                arm: (
                    native[key] > 0,
                    native["front_resolution_kpc"] if arm == "primary" else None,
                )
                for arm, key in ARMS.items()
            }
            refs.update(
                other_compressions=(native["other_path_kpc"] > 0, None),
                boundary_connected=(native["boundary_path_kpc"] > 0, None),
            )
            distances += separation_rows(
                angle, g, masks[ORANGE], masks[BLUE], lateral, refs
            )
            overlap.extend(
                footprint_overlap(
                    angle, g, measurement_regions(masks, path > 0, lateral), native
                )
            )
            positions = profile_indices(g, lateral, path)
            if geometry_only:
                overlay_figure(
                    angle,
                    g,
                    raw,
                    bg,
                    masks,
                    path,
                    native,
                    None,
                    positions,
                    norms,
                    output,
                )
                per_view[angle] = {
                    "native_map_sha256": expected,
                    "primary_pixels": int(refs["primary"][0].sum()),
                }
                continue
            fields, closure = emission_partition(data, native)
            captured = float(np.sum(g.area * path))
            native_volume = source["projection"][str(angle)]["native_volume_integrals"][
                "path_C_kpc"
            ]
            if not np.isclose(captured, native_volume, rtol=1e-9, atol=0):
                raise ValueError("sky does not capture the native tracer volume")
            regions += region_rows(
                angle,
                g,
                fields,
                measurement_regions(masks, path > 0, lateral),
                bg[ORANGE],
            )
            row, display = observer_replacement(
                angle,
                g,
                raw,
                path,
                masks,
                bg,
                fields,
                data,
                original_z_axis(inputs, source, angle),
            )
            recovery += row
            profiles += write_profile_values(
                angle, g, positions, fields, path, raw, bg, native, display, masks
            )
            overlay_figure(
                angle,
                g,
                raw,
                bg,
                masks,
                path,
                native,
                display,
                positions,
                norms,
                output,
            )
            profile_figure(
                angle, g, positions, raw, bg, fields, path, native, display, output
            )
            per_view[angle] = {
                "native_map_sha256": expected,
                "closure": closure,
                "captured_lobe_kpc3": captured,
                "whole_grid_lobe_kpc3": native_volume,
                "primary_pixels": int(refs["primary"][0].sum()),
                "disconnected_pixels": int(refs["other_compressions"][0].sum()),
                "boundary_pixels": int(refs["boundary_connected"][0].sum()),
            }
    for name, values in [
        ("front_contour_separations.csv", distances),
        ("front_sightline_overlap.csv", overlap),
        ("emission_regions.csv", regions),
        ("replacement_recovery.csv", recovery),
        ("transverse_profiles.csv.gz", profiles),
    ]:
        if values:
            write_rows(output / name, values)
    result = {
        "phase": "geometry_only" if geometry_only else "geometry_and_emissivity",
        "analysis_sha256": {
            p.name: HASH(p)
            for p in [
                Path(__file__),
                Path(__file__).with_name("render_compressive_front.py"),
                Path(emission.__file__),
            ]
        },
        "snapshot": "G-HI/20",
        "actual_time_myr": AGE,
        "observer_input_hashes": checks,
        "front_receipt_sha256": HASH(front_receipt),
        "views": per_view,
        "products": {p.name: HASH(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "comparison_receipt.json").write_text(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--front-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.native) != bool(args.front_receipt):
        parser.error(
            "supply the native projection directory and its completion receipt together"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    if args.native:
        run(args.inputs, args.native, args.front_receipt, args.output)
    else:
        baseline(args.inputs, args.output)


if __name__ == "__main__":
    main()
