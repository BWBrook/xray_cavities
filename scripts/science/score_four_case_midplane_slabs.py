"""Score one native case-age of the four-case midplane-slab protocol."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import score_ghi20_midplane_slabs as pilot
from score_ghi20_midplane_slabs import DEPTHS, FIELDS, HALVES, THRESHOLD, front, ladder, ratio


CUTS = (0.05, 0.06, 0.07, 0.08, 0.10, 0.15, 0.20)
PATH_EDGES = (0, 5, 10, 20, 30, 40, 50, 60, 100)
ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
NATIVE_CATALOG = ASSETS / "xray_prediction_seal_2026-11-23/native_inputs.csv"
NATIVE_CATALOG_SHA = "bf41d2e0e7aa143a68316c0a3aeffcbe49fa0c3bea7288c0183d0e555fbc2fb3"
PILOT_COMPLETION_SHA = "27ce38e78b2c93d28a7554d6f11e784a99580005e83e7f155098f1ed6d1ebcb2"
FLUX_FIELDS = ("initial", "current", "initial_on_current_lobe", "current_lobe")


def array_sha(values):
    return hashlib.sha256(np.ascontiguousarray(values).view(np.uint8)).hexdigest()


def read_projection(directory, completion_sha):
    completion_file = directory / "completion.json"
    if front.HASH(completion_file) != completion_sha:
        raise ValueError("Projection receipt differs from its supplied SHA-256")
    receipt = json.loads(completion_file.read_text())
    case, index = receipt["case"], receipt["snapshot_index"]
    if ((receipt["schema_version"], receipt["status"], receipt["energy_kev"], receipt["view_deg"],
         receipt["redshift"]) != (1, "complete", 1.0, 0, 0.05)
            or not np.isclose(receipt["frequency_hz"], 2.417990504024e17, rtol=1e-12, atol=0)):
        raise ValueError("Wrong emission setting, viewing angle or completion status")
    if (case, index) == ("G-HI", 20):
        if completion_sha != PILOT_COMPLETION_SHA:
            raise ValueError("Only the original exposed G-HI/20 receipt can be replayed")
    else:
        if front.HASH(NATIVE_CATALOG) != NATIVE_CATALOG_SHA:
            raise ValueError("Frozen native source inventory changed")
        with NATIVE_CATALOG.open(newline="") as stream:
            matches = [r for r in csv.DictReader(stream) if r["case"] == case and r["kind"] == "science"
                       and int(r["snapshot_index"]) == index]
        if len(matches) != 1:
            raise ValueError(f"Unregistered science output {case} index {index}")
        source = matches[0]
        inputs = receipt["native_inputs_sha256"]
        checks = (("current_h5", "current_h5_sha256"), ("initial_h5", "initial_h5_sha256"),
                  ("environment", "atmosphere_sha256"), ("grid_file", "grid_file_sha256"))
        if (any(inputs[name] != source[column] for name, column in checks)
                or receipt["native_receipt_sha256"] != source["native_input_receipt_sha256"]
                or receipt["native_shape_zyx"] != [int(x) for x in source["shape_z_y_x"].split("x")]
                or not np.isclose(receipt["actual_time_myr"], float(source["actual_age_myr"]), rtol=0, atol=1e-10)):
            raise ValueError("Projection inputs, mesh or age differ from the prebound native science output")
    for field in ("current_full", "initial_full", "tracer_path_full"):
        match = receipt["closure_against_previous"][field]
        if not (0 <= match["error_to_scale"] <= 4e-11) or (field == "tracer_path_full" and match["max_abs_error"] != 0):
            raise ValueError(f"Failed archived full-depth comparison for {field}")
    data_file = directory / "projections.npz"
    product = receipt["files"][data_file.name]
    if data_file.stat().st_size != product["size_bytes"] or front.HASH(data_file) != product["sha256"]:
        raise ValueError("Returned raster set differs from its authenticated completion")
    with np.load(data_file, allow_pickle=False) as data:
        fields = {depth: {name: data[f"{name}_{depth}"] for name in FIELDS} for depth in DEPTHS}
        shape = tuple(receipt["native_shape_zyx"][::2])
        grid = front.Grid(*front.validate_axes(data, shape))
    if not np.any(grid.ze == 0) or np.any(grid.z == 0):
        raise ValueError("Bipolar split must lie on a native sky-cell edge")
    for depth, limits in zip(DEPTHS, (receipt["y_extent_kpc"], (-30, 30), (-10, 10)), strict=True):
        info = receipt["depths"][depth]
        width = float(limits[1] - limits[0])
        maps = fields[depth]
        if (not np.allclose([info["y_min_kpc"], info["y_max_kpc"], info["integrated_width_kpc"]],
                            [*limits, width], rtol=0, atol=1e-9)
                or any(v.shape != shape or not np.isfinite(v).all() for v in maps.values())
                or np.any(maps["tracer_path"] < 0) or np.any(maps["tracer_path"] > width + 1e-9)):
            raise ValueError(f"Invalid emission raster, tracer path or native integration depth in {depth}")
    full, middle, inner = (fields[d]["tracer_path"] for d in DEPTHS)
    if any(np.any((narrow > wide + 1e-9) | ((narrow > 0) & (wide <= 0))) for narrow, wide in
           ((inner, middle), (middle, full))):
        raise ValueError("Tracer paths and footprints fail physical nesting")
    return receipt, grid, fields


def coverage_split(grid, current_mask, null_mask, full_path, physical_deficit):
    """Split registered coverage on the same evolved full tracer footprint at every depth."""
    area, truth = grid.area, full_path > 0
    valid = np.isfinite(physical_deficit)
    dimmed = valid & (physical_deficit > THRESHOLD)
    rows = []
    for name, side in zip(HALVES, pilot.sides(grid), strict=True):
        lobe = truth & side[:, None]
        overlap = lobe & current_mask
        on_null, covered_null = lobe & null_mask, overlap & null_mask
        lobe_area = float(area[lobe].sum())
        overlap_area = float(area[overlap].sum())
        null_area = float(area[on_null].sum())
        dimmed_overlap = float(area[overlap & dimmed].sum())
        rows.append({
            "hemisphere": name, "lobe_kpc2": lobe_area, "overlap_kpc2": overlap_area,
            "coverage": ratio(overlap_area, lobe_area),
            "lobe_in_control_outline_kpc2": null_area, "control_coverage": ratio(null_area, lobe_area),
            "overlap_in_control_outline_kpc2": float(area[covered_null].sum()),
            "overlap_outside_control_outline_kpc2": float(area[overlap & ~null_mask].sum()),
            "overlap_dimmed_kpc2": dimmed_overlap, "coverage_dimmed_only": ratio(dimmed_overlap, lobe_area),
            "overlap_not_dimmed_kpc2": float(area[overlap & valid & ~dimmed].sum()),
            "overlap_invalid_initial_kpc2": float(area[overlap & ~valid].sum()),
            "overlap_not_dimmed_in_control_outline_kpc2": float(area[covered_null & valid & ~dimmed].sum()),
            "dimmed_on_lobe_kpc2": float(area[lobe & dimmed].sum()),
            "dimmed_on_lobe_missed_kpc2": float(area[lobe & dimmed & ~current_mask].sum()),
        })
    return rows


def null_ladder(grid, image, background, initial):
    """One cut clears the full control only if both native hemispheres are fully evaluable and empty."""
    _, aperture = ladder._rois(grid.u, grid.z)
    area = grid.area
    rows = []
    first_clean = None
    for cut in CUTS:
        result = initial if cut == THRESHOLD else ladder.deficit_threshold(
            image, grid.u, grid.z, background=background, background_label="observer_radial", threshold=cut)
        mask = result.mask
        by_side = []
        for name, side in zip(HALVES, pilot.sides(grid), strict=True):
            search = aperture & side[:, None]
            invalid = search & ~np.isfinite(result.deficit)
            selected = mask & side[:, None]
            if selected.any():
                status = "failed_nonempty"
            elif invalid.any() or not search.any():
                status = "unscorable"
            else:
                status = "empty"
            by_side.append({"hemisphere": name, "cut": cut, "time_zero_status": status,
                            "selected_kpc2": float(area[selected].sum()),
                            "valid_search_kpc2": float(area[search & ~invalid].sum()),
                            "invalid_search_kpc2": float(area[invalid].sum()),
                            "touches_aperture": ladder.touches_aperture(selected, grid.u, grid.z)})
        rows.extend(by_side)
        if first_clean is None and all(r["time_zero_status"] == "empty" for r in by_side):
            first_clean = cut
    return first_clean, rows


def volume_closure(grid, fields, native_volumes):
    rows = []
    for depth in DEPTHS:
        volume_map = grid.area * fields[depth]["tracer_path"]
        for name, side in zip(HALVES, pilot.sides(grid), strict=True):
            projected = float(volume_map[side].sum())
            native = native_volumes[depth][name]
            if not np.isclose(projected, native, rtol=4e-11, atol=0):
                raise ValueError(f"Projected tracer volume differs from native cells for {depth}/{name}")
            rows.append({"depth": depth, "hemisphere": name, "projected_kpc3": projected,
                         "native_kpc3": native, "difference_kpc3": projected - native})
    return rows


def sightline_groups(path, full_mask):
    footprint = path > 0
    yield "lobe", "full_lobe", footprint
    for lo, hi in zip(PATH_EDGES[:-1], PATH_EDGES[1:], strict=True):
        yield f"path_{lo}_{hi}_kpc", "tracer_path", (path > lo) & (path <= hi)
    yield "path_over_100_kpc", "tracer_path", path > PATH_EDGES[-1]
    yield "detected_at_full_depth", "conditioned_on_full_depth_detector", footprint & full_mask
    yield "missed_at_full_depth", "conditioned_on_full_depth_detector", footprint & ~full_mask


def layer_scores(grid, fields, measured):
    """Sum all four emissivity fields on fixed sightlines, using physical sky-cell areas."""
    area = grid.area
    layer_defs = (("within_10_kpc", "slab10", None), ("10_to_30_kpc", "slab30", "slab10"),
                  ("beyond_30_kpc", "full", "slab30"), ("whole_sightline", "full", None))
    layers, depths = [], []
    for name, grouping, cells in sightline_groups(fields["full"]["tracer_path"], measured["full"]["mask"]):
        for hemisphere, side in zip(HALVES, pilot.sides(grid), strict=True):
            region = cells & side[:, None]
            weights = area[region]
            sky_area = float(weights.sum())
            base = {"sightlines": name, "grouping": grouping, "hemisphere": hemisphere, "area_kpc2": sky_area,
                    "region_status": "populated" if region.any() else "empty"}
            for depth in DEPTHS:
                detected_area = float(area[region & measured[depth]["mask"]].sum())
                base[f"detected_{depth}"] = ratio(detected_area, sky_area)
            samples = {d: {k: fields[d][k][region] for k in FLUX_FIELDS} for d in DEPTHS}
            flux = {d: {k: float(np.sum(weights * image)) for k, image in fields_at_depth.items()}
                    for d, fields_at_depth in samples.items()}
            full = flux["full"]
            layer_sum = dict.fromkeys(FLUX_FIELDS, 0.)
            for label, outer, inner in layer_defs:
                values = flux[outer] if inner is None else {
                    k: float(np.sum(weights * (samples[outer][k] - samples[inner][k]))) for k in FLUX_FIELDS}
                if label != "whole_sightline":
                    for key in FLUX_FIELDS:
                        layer_sum[key] += values[key]
                before, now = values["initial"], values["current"]
                lobe_before, lobe_now = values["initial_on_current_lobe"], values["current_lobe"]
                layers.append({
                    **base, "layer": label, "initial_flux": before, "current_flux": now,
                    "initial_lobe_flux": lobe_before, "current_lobe_flux": lobe_now,
                    "tracer_change_flux": lobe_now - lobe_before,
                    "ambient_change_flux": (now - lobe_now) - (before - lobe_before),
                    "share_of_initial_flux": ratio(before, full["initial"]),
                    "fractional_change": ratio(now - before, before),
                })
            for key, total in layer_sum.items():
                # Allow cancellation in signed emissivities at the summation round-off scale.
                scale = max(float(np.sum(weights * np.abs(samples[d][key]))) for d in DEPTHS)
                if abs(total - full[key]) > 4e-11 * scale:
                    raise ValueError(f"Three emission layers fail to sum at {name}/{hemisphere}/{key}")
            full_deficit = ratio(full["initial"] - full["current"], full["initial"])
            for depth in DEPTHS:
                f = flux[depth]
                before, now = f["initial"], f["current"]
                lobe_before, lobe_now = f["initial_on_current_lobe"], f["current_lobe"]
                deficit = ratio(before - now, before)
                unchanged = ratio(before - now, full["initial"])
                depths.append({
                    **base, "depth": depth, "initial_flux": before, "current_flux": now,
                    "initial_lobe_flux": lobe_before, "current_lobe_flux": lobe_now,
                    "tracer_change_flux": lobe_now - lobe_before,
                    "ambient_change_flux": (now - lobe_now) - (before - lobe_before),
                    "outer_initial_flux": full["initial"] - before, "outer_current_flux": full["current"] - now,
                    "matched_deficit": deficit, "unchanged_outer_deficit": unchanged,
                    "full_deficit": full_deficit,
                    "dilution_by_initial_outer_light": (
                        deficit - unchanged if deficit is not None and unchanged is not None else None),
                    "change_due_to_outer_brightening": (
                        unchanged - full_deficit if unchanged is not None and full_deficit is not None else None),
                })
    return layers, depths


def sensitivity_scores(grid, maps, background, first_clean, primary, areas, full_mask, full_path):
    if first_clean is None:
        clean_areas = []
    elif first_clean == THRESHOLD:
        clean_areas = areas
    else:
        selected = ladder.deficit_threshold(maps["current"], grid.u, grid.z, background=background,
                                            background_label="observer_radial", threshold=first_clean)
        clean_areas = pilot.area_scores(grid, selected.mask, full_mask, full_path, maps["tracer_path"])
    keys = ("selected_kpc2", "overlap_kpc2", "missed_kpc2", "false_kpc2", "completeness", "purity",
            "selection_touches_aperture")
    scores = {(r["hemisphere"], r["target"]): r for r in clean_areas}
    rows = []
    for row in areas:
        hemisphere, target = row["hemisphere"], row["target"]
        value = scores.get((hemisphere, target), {})
        rows.append({"hemisphere": hemisphere, "target": target, "primary_time_zero_status": primary,
                     "first_clean_status": "none_tested" if first_clean is None else "found",
                     "first_clean_cut": first_clean, "lobe_kpc2": row["lobe_kpc2"],
                     "lobe_outside_aperture_kpc2": row["lobe_outside_aperture_kpc2"],
                     **{k: value.get(k) for k in keys}})
    return rows


def run(projection_dir, completion_sha, full_mask_sha, output):
    if output.exists():
        raise FileExistsError(f"Score directory already exists: {output}")
    receipt, grid, fields = read_projection(projection_dir, completion_sha)
    identity = {k: receipt[k] for k in ("case", "snapshot_index", "actual_time_myr", "view_deg")}
    full_path = fields["full"]["tracer_path"]
    tables = {k: [] for k in ("areas", "filling", "radial_profiles", "time_zero_controls",
                              "coverage_controls", "control_ladder", "sensitivity")}
    tables["volume_closure"] = volume_closure(grid, fields, receipt["native_tracer_volume_kpc3"])
    measured, support, clean_cuts, initial_images = {}, {}, {}, {}
    for depth in DEPTHS:
        maps = fields[depth]
        initial, null_background, null_profile = pilot.radial_outline(maps["initial"], grid, depth, "initial")
        first_clean, cuts = null_ladder(grid, maps["initial"], null_background, initial)
        clean_cuts[depth] = first_clean
        initial_images[depth] = array_sha(maps["initial"])
        current, background, current_profile = pilot.radial_outline(maps["current"], grid, depth, "current")
        mask = current.mask
        if depth == "full" and array_sha(mask) != full_mask_sha:
            raise ValueError("Full-depth radial outline differs from the fixed case-age prediction")
        physical = ladder.recovery.compute_fractional_deficit(maps["current"], maps["initial"])
        measured[depth] = {"mask": mask, "fit_deficit": current.deficit, "initial_deficit": physical,
                           "initial_outline": initial}
        full_mask = measured["full"]["mask"]
        areas = pilot.area_scores(grid, mask, full_mask, full_path, maps["tracer_path"])
        controls = pilot.depth_controls(grid, initial, mask, full_path, physical)
        primary = next(r["time_zero_status"] for r in controls if r["hemisphere"] == "both")
        sensitivity = sensitivity_scores(grid, maps, background, first_clean, primary, areas, full_mask, full_path)
        coverages = coverage_split(grid, mask, initial.mask, full_path, physical)
        for row in coverages:
            s = next(r for r in sensitivity if r["hemisphere"] == row["hemisphere"] and r["target"] == "full_lobe")
            row.update(primary_time_zero_status=primary, first_clean_status=s["first_clean_status"],
                       first_clean_cut=first_clean, first_clean_coverage=s["completeness"],
                       first_clean_purity=s["purity"], first_clean_false_kpc2=s["false_kpc2"],
                       first_clean_touches_aperture=s["selection_touches_aperture"])
        for key, rows in (("coverage_controls", coverages), ("control_ladder", cuts), ("sensitivity", sensitivity),
                          ("time_zero_controls", controls), ("areas", areas),
                          ("filling", pilot.filling_scores(grid, maps, background, current.deficit, physical,
                                                          full_path, full_mask, mask))):
            tables[key].extend({"depth": depth, **row} for row in rows)
        tables["radial_profiles"].extend(current_profile + null_profile)
        support[depth] = {rows[0]["epoch"]: dict(Counter(r["support"] for r in rows))
                          for rows in (current_profile, null_profile)}
    tables["layers"], tables["depth_flux"] = layer_scores(grid, fields, measured)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp) / "scored"
        work.mkdir()
        for name, rows in tables.items():
            front.write_rows(work / f"{name}.csv", [{**identity, **row} for row in rows])
        display = pilot.plot_maps(work / "maps.png", grid, fields, measured, receipt["case"],
                                  receipt["actual_time_myr"], receipt["depths"]["full"])
        pilot.plot_profiles(work / "profiles.png", tables["radial_profiles"])
        pilot.plot_time_zero_controls(work / "time_zero_controls.png", grid, measured)
        result = {
            "schema_version": 1, **identity, "status": "complete", "energy_kev": receipt["energy_kev"],
            "frequency_hz": receipt["frequency_hz"], "redshift": receipt["redshift"],
            "projection_receipt_sha256": completion_sha, "projection_file_sha256": receipt["files"]["projections.npz"]["sha256"],
            "native_inputs_sha256": receipt["native_inputs_sha256"], "native_shape_zyx": receipt["native_shape_zyx"],
            "native_tracer_boundary_face_cells": receipt["tracer_boundary_face_cells"],
            "closure_against_previous": receipt["closure_against_previous"], "depths": receipt["depths"],
            "expected_full_depth_mask_sha256": full_mask_sha, "full_depth_candidate_matches_archive": True,
            "candidate_mask_sha256": {d: array_sha(m["mask"]) for d, m in measured.items()},
            "time_zero_mask_sha256": {d: array_sha(m["initial_outline"].mask) for d, m in measured.items()},
            "time_zero_image_sha256": initial_images,
            "sky_axes_sha256": {k: array_sha(v) for k, v in zip(front.AXES, (grid.u, grid.ue, grid.z, grid.ze),
                                                                 strict=True)},
            "time_zero_status": {r["depth"]: r["time_zero_status"] for r in tables["time_zero_controls"]
                                 if r["hemisphere"] == "both"},
            "first_clean_cut": clean_cuts, "support_by_5kpc_annulus": support,
            "detector": {"fit_radius_kpc": ladder.recovery.BACKGROUND_RADIUS_KPC,
                         "candidate_radius_kpc": ladder.recovery.CANDIDATE_RADIUS_KPC,
                         "radial_bin_kpc": ladder.recovery.RADIAL_BIN_KPC,
                         "smoothing_sigma_kpc": ladder.recovery.RADIAL_SMOOTHING_KPC,
                         "registered_strict_deficit_cut": THRESHOLD, "null_sensitivity_cuts": CUTS,
                         "min_component_kpc2": ladder.recovery.MIN_COMPONENT_AREA_KPC2,
                         "connectivity": ladder.recovery.CONNECTIVITY},
            "flux_integral_units": "mJy sr^-1 kpc^2", "figure": display,
            "scorer_sha256": front.HASH(Path(__file__)), "pilot_scorer_sha256": front.HASH(Path(pilot.__file__)),
            "products": {p.name: front.HASH(p) for p in sorted(work.iterdir())},
        }
        (work / "score_receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        work.rename(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection-dir", type=Path, required=True)
    parser.add_argument("--completion-sha256", required=True)
    parser.add_argument("--full-mask-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.projection_dir, args.completion_sha256, args.full_mask_sha256, args.out)
