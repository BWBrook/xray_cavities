"""Clip previously fitted G-HI/20 X-ray candidates to the projected native front."""

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

import compare_compressive_front as front
import source_excluded_inputs as sources
import xray_cavity_method_ladder as ladder
from ghi20_exterior_arc_check import NATIVE_RECEIPT_SHA


SCIENCE = sources.SCIENCE
PROTOCOL = SCIENCE / "ghi20_front_constraint_protocol_2026-11-25.md"
OUTPUT = SCIENCE / "assets/ghi20_front_constraint_2026-11-25"
DET06 = SCIENCE / "assets/source_excluded_backgrounds_2026-11-25"
DET06_HASH = {
    "radial_support.csv.gz": "c741ccdca7949412200adc7cb33d4c71d284739f5278ef0ae8fc80242a81d05f",
    "scores.csv.gz": "d5a783a0c8215d587f200b0f80d2386752d421df14463267331eb1e4338c42cc",
}


def array_hash(a):
    return hashlib.sha256(a.tobytes(order="C")).hexdigest()


def front_interior(path, grid, native_touches_boundary):
    if path.shape != (grid.z.size, grid.u.size) or not np.isfinite(path).all() or (path < 0).any():
        raise ValueError("Invalid native front path lengths")
    occupied = path > 0
    four, eight = (ndimage.generate_binary_structure(2, n) for n in (1, 2))
    counts = [ndimage.label(occupied, structure=s)[1] for s in (four, eight)]
    interiors = [ndimage.binary_fill_holes(occupied, structure=s) for s in (four, eight)]
    inside = interiors[0]
    rim = bool(occupied[[0, -1], :].any() or occupied[:, [0, -1]].any())
    a, b, c, d = occupied[:-1, :-1], occupied[:-1, 1:], occupied[1:, :-1], occupied[1:, 1:]
    diagonals = int(np.count_nonzero((a == d) & (b == c) & (a != b)))
    zu = [np.searchsorted(centres, 0) for centres in (grid.z, grid.u)]
    if any(i == 0 or i == n for i, n in zip(zu, occupied.shape, strict=True)):
        raise ValueError("Detector does not bracket the source")
    iz, iu = zu
    source_inside = bool(inside[iz-1:iz+1, iu-1:iu+1].all())
    reasons = []
    if counts != [1, 1]:
        reasons.append("empty or competing components")
    if rim or native_touches_boundary:
        reasons.append("front touches detector or native domain boundary")
    if diagonals or not np.array_equal(*interiors):
        reasons.append("ambiguous diagonal enclosure")
    if not source_inside:
        reasons.append("source open to exterior sky")
    geometry = {
        "status": "unscored" if reasons else "closed", "reason": ", ".join(reasons),
        "components_4": counts[0], "components_8": counts[1], "diagonal_junctions": diagonals,
        "detector_edge_contact": rim, "native_boundary_contact": native_touches_boundary,
        "source_inside": source_inside, "filled_hole_pixels": int(np.count_nonzero(inside & ~occupied)),
        "footprint_kpc2": float(grid.area[occupied].sum()),
        "inside_kpc2": None if reasons else float(grid.area[inside].sum()),
        "inside_sha256": None if reasons else array_hash(inside),
    }
    return (None if reasons else inside), geometry


def ratio(x, y):
    return x / y if y else None


def area_scores(candidate, truth, inside, area):
    selected_true = candidate & truth
    selected_false = candidate & ~truth
    def measure(mask):
        return float(area[mask].sum())

    true_before, false_before = measure(selected_true), measure(selected_false)
    true_lost, false_removed = measure(selected_true & ~inside), measure(selected_false & ~inside)
    true_after, false_after = measure(selected_true & inside), measure(selected_false & inside)
    for before, kept, removed in ((true_before, true_after, true_lost), (false_before, false_after, false_removed)):
        if not np.isclose(before, kept + removed, atol=1e-8, rtol=1e-12):
            raise ValueError("Clipped and retained areas fail to partition the original")
    target = measure(truth)
    return {
        "lobe_area_kpc2": target, "lobe_outside_front_kpc2": measure(truth & ~inside),
        "false_before_kpc2": false_before, "false_removed_kpc2": false_removed,
        "false_after_kpc2": false_after, "fraction_false_removed": ratio(false_removed, false_before),
        "true_before_kpc2": true_before, "true_lost_kpc2": true_lost, "true_after_kpc2": true_after,
        "fraction_selected_true_lost": ratio(true_lost, true_before),
        "fraction_full_lobe_lost": ratio(true_lost, target),
        "completeness_before": ratio(true_before, target), "completeness_after": ratio(true_after, target),
        "purity_before": ratio(true_before, true_before + false_before),
        "purity_after": ratio(true_after, true_after + false_after),
    }


def radial_candidate(image, background, grid):
    return ladder.deficit_threshold(image, grid.u, grid.z, background=background,
                                    background_label="archived_radial", threshold=0.05).mask


def det06_records():
    records = {}
    for name, digest in DET06_HASH.items():
        path = DET06 / name
        sources.verify_archive(path, digest)
        with gzip.open(path, "rt", newline="") as f:
            records[name] = [r for r in csv.DictReader(f) if r["kind"] == "development"
                             and r["case"] == "G-HI" and r["index"] == "20" and r["arm"] == "speed_100"]
    return records


def speed_candidates(view, grid, records):
    bins = sorted((r for r in records["radial_support.csv.gz"] if r["unit_id"] == view.unit_id),
                  key=lambda r: int(r["bin_index"]))
    centres = np.array([float(r["r_center_kpc"]) for r in bins])
    radius = np.hypot(grid.u[None, :], grid.z[:, None])
    roi = ladder._rois(grid.u, grid.z)[0]
    for fit in ("flat", "log_slope"):
        profile = [float(r[fit + "_profile"]) for r in bins]
        background = np.interp(radius, centres, profile)
        background[~roi] = np.nan
        mask = radial_candidate(view.image, background, grid)
        ref, = (r for r in records["scores.csv.gz"] if r["unit_id"] == view.unit_id
                and r["continuation"] == fit and r["side"] == "both")
        if ref["status"] != "ok" or array_hash(mask) != ref["mask_sha256"]:
            raise ValueError(f"{view.unit_id}: DET-06 {fit} candidate differs")
        yield "speed100_" + fit, (mask, background)


def existing_candidates(view, grid, obs, native, records, prior):
    original = front.emission.original_observers(obs["retained_image"], grid.u, view.historical_detector_z_axis_kpc)
    candidates = {}
    for key, method in (("original_radial", front.ORANGE), ("original_seed_grow", front.BLUE)):
        mask = obs["original_mask_" + method]
        background = obs["original_background_" + method]
        if (mask.dtype != bool or not np.array_equal(mask, original[method]["mask"])
                or not np.allclose(background, original[method]["background"], rtol=2e-10, atol=0, equal_nan=True)):
            raise ValueError(f"{view.unit_id}: original {method} did not replay")
        candidates[key] = mask, background

    baseline = ladder.observer_radial_background(view.image, grid.u, grid.z)
    if not np.array_equal(radial_candidate(view.image, baseline, grid), view.baseline_mask):
        raise ValueError(f"{view.unit_id}: exact-edge unmasked reference differs")
    candidates["exact_radial"] = view.baseline_mask, baseline
    replacement = view.image + native["front_initial_brightness"] - native["front_current_brightness"]
    refit = ladder.observer_radial_background(replacement, grid.u, grid.z)
    changed = radial_candidate(replacement, refit, grid)
    for side, half in zip(front.SIDES, (grid.z[:, None] < 0, grid.z[:, None] > 0), strict=True):
        ref = prior[view.view_deg, side]
        metrics = front.recovery_metrics(grid, changed, view.target_path_kpc, half, view.baseline_mask)
        sources.check_metrics(view.unit_id, ref, metrics)
    candidates["replacement_refit_radial"] = changed, refit
    candidates.update(speed_candidates(view, grid, records))
    return candidates


def run(inputs, native_dir, out):
    sources.verify_archive(native_dir / "completion.json", NATIVE_RECEIPT_SHA)
    native_receipt = json.loads((native_dir / "completion.json").read_text())
    if ((native_receipt["case"], native_receipt["snapshot_index"], native_receipt["actual_time_myr"],
         native_receipt["source_producer_sha256"]) != ("G-HI", 20, front.AGE, front.PRODUCER_SHA)):
        raise ValueError("Wrong case, age or observer source for native front")
    with (sources.FRONT / "replacement_recovery.csv").open(newline="") as f:
        prior = {(int(r["view_deg"]), r["hemisphere"]): r for r in csv.DictReader(f)
                 if r["method"] == front.ORANGE and r["comparison"] == "replace_same_cells_refit_background"}
    records = det06_records()
    geometry_rows, scores, bindings = [], [], {}
    for view in sources.development_views(inputs):
        angle = view.view_deg
        name = view.unit_id + ".npz"
        native_sha = native_receipt["files"][name]["sha256"]
        sources.verify_archive(native_dir / name, native_sha)
        if any(view.provenance[k + "_sha256"] != digest for k, digest in native_receipt["native_inputs_sha256"].items()):
            raise ValueError(f"{name}: native source files differ")
        grid = front.Grid(*front.validate_axes(view.axes, view.image.shape))
        if (grid.z == 0).any() or grid.ze[np.searchsorted(grid.z, 0)] != 0:
            raise ValueError(f"{name}: hemisphere split bisects a detector cell")
        area = grid.area
        truth = view.target_path_kpc > 0
        with np.load(inputs / name, allow_pickle=False) as obs, np.load(native_dir / name, allow_pickle=False) as native:
            if any(not np.array_equal(native[k], axis) for k, axis in view.axes.items()):
                raise ValueError(f"{name}: front and observer axes differ")
            candidates = existing_candidates(view, grid, obs, native, records, prior)
            bindings[view.unit_id] = {
                "observer_sha256": view.provenance["maps_sha256"], "native_front_sha256": native_sha,
                "tracer_footprint_sha256": array_hash(truth),
                "candidates": {key: {"before_mask_sha256": array_hash(mask), "background_sha256": array_hash(bg)}
                               for key, (mask, bg) in candidates.items()},
            }
            for arm, field in front.ARMS.items():
                boundary = bool(native_receipt["component_summaries"][arm]["boundary_components"])
                inside, geometry = front_interior(native[field], grid, boundary)
                geometry_rows.append({"view_deg": angle, "front": arm, **geometry})
                if inside is None:
                    continue
                for key, (mask, _) in candidates.items():
                    clipped_sha = array_hash(mask & inside)
                    sides = {}
                    for side, rows in (("negative_z", grid.z < 0), ("positive_z", grid.z > 0),
                                       ("both", slice(None))):
                        side_scores = area_scores(mask[rows], truth[rows], inside[rows], area[rows])
                        sides[side] = side_scores
                        scores.append({"view_deg": angle, "front": arm, "candidate": key, "hemisphere": side,
                                       "clipped_bipolar_mask_sha256": clipped_sha, **side_scores})
                    for field in side_scores:
                        if field.endswith("_kpc2") and not np.isclose(sides["both"][field],
                                sum(sides[s][field] for s in front.SIDES), rtol=1e-12, atol=1e-8):
                            raise ValueError(f"{name}/{key}/{arm}: hemisphere sums differ for {field}")
    out.mkdir(parents=True, exist_ok=True)
    front.write_rows(out / "front_geometry.csv", geometry_rows)
    if scores:
        front.write_rows(out / "area_scores.csv", scores)
    else:
        (out / "area_scores.csv").write_text("view_deg,front,candidate,hemisphere\n")
    receipt = {
        "case": "G-HI", "actual_age_myr": front.AGE, "protocol_sha256": front.HASH(PROTOCOL),
        "measurement_code_sha256": front.HASH(Path(__file__)), "native_source_sha256": native_receipt["native_inputs_sha256"],
        "native_receipt_sha256": NATIVE_RECEIPT_SHA, "observer_receipt_sha256": front.PRODUCER_SHA,
        "previous_observer_comparison_sha256": sources.FRONT_COMPARISON_SHA, "det06_tables_sha256": DET06_HASH,
        "bindings": bindings, "geometry_rows": len(geometry_rows), "score_rows": len(scores),
        "products": {name: front.HASH(out / name) for name in ("front_geometry.csv", "area_scores.csv")},
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True, help="Original G-HI/20 emission projection directory")
    parser.add_argument("--native", type=Path, required=True, help="Native G-HI/20 front projection directory")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.inputs, args.native, args.out)
