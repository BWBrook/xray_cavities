"""Independently score the two orange candidates in Patrick's projected-front test.

The input maps are the archived November 23 projections. The first candidate
is the binary mask in the original panel. The replacement candidate uses the
independently implemented radial refit from the November 25 DET-06 review.
Only --compare reads the main analysis table, after computing all measurements.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform

import numpy as np

from review_source_excluded_backgrounds import AXES, View

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "docs/science/assets/compressive_front_observer_2026-11-23"
PROTOCOL = ROOT / "docs/science/ghi20_front_constraint_protocol_2026-11-25.md"
REFERENCE_HASH = "3d8752d647cf50475c5838568eaac3cd3cb060de0863271947a75a005f61500b"
METHOD = "deficit_threshold_observer_radial_0.05"
COMPARISONS = {"original_radial": "original",
               "replacement_refit_radial": "replace_same_cells_refit_background"}
FRONTS = {"primary": "front_path_kpc", "loose": "front_path_loose_kpc",
          "tight": "front_path_tight_kpc", "wide": "front_path_wide_kpc"}
SIDES = ("negative_z", "positive_z", "both")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked(path, expected):
    if digest(path) != expected:
        raise ValueError(f"Input digest changed for {path.name}")
    return path


def mask_hash(mask):
    return hashlib.sha256(np.asarray(mask, dtype=np.uint8).tobytes()).hexdigest()


def trace_interior(footprint, ue, ze):
    """Trace exposed pixel edges and classify pixel centres by crossing parity."""
    if any(np.any(side) for side in (footprint[0], footprint[-1], footprint[:, 0], footprint[:, -1])):
        raise ValueError("Front touches detector boundary")
    origin = [np.flatnonzero(edges == 0) for edges in (ze, ue)]
    if any(len(index) != 1 for index in origin):
        raise ValueError("Source does not meet four native cells")
    i, j = (index.item() for index in origin)
    if not footprint[i-1:i+1, j-1:j+1].all():
        raise ValueError("Open or ambiguous source enclosure")

    padded = np.pad(footprint, 1)
    edges = (
        (padded[:-2, 1:-1], (0, 0), (0, 1)),
        (padded[2:, 1:-1], (1, 0), (1, 1)),
        (padded[1:-1, :-2], (0, 0), (1, 0)),
        (padded[1:-1, 2:], (0, 1), (1, 1)),
    )
    neighbours = defaultdict(list)
    for adjacent, start, end in edges:
        for row, col in np.argwhere(footprint & ~adjacent):
            a = (int(row) + start[0], int(col) + start[1])
            b = (int(row) + end[0], int(col) + end[1])
            neighbours[a].append(b)
            neighbours[b].append(a)
    if any(len(connected) != 2 for connected in neighbours.values()):
        raise ValueError("Branch or corner-only connection in projected boundary")

    start = min(neighbours)
    boundary = [start]
    previous, current = start, neighbours[start][0]
    while current != start:
        boundary.append(current)
        a, b = neighbours[current]
        previous, current = current, (a if a != previous else b)
    if len(boundary) != len(neighbours):
        raise ValueError("Multiple cycles, including a possible inner hole; review this geometry")

    boundary.append(start)
    crossings = defaultdict(list)
    signed_double_area = []
    for (i, j), (k, l) in zip(boundary, boundary[1:]):
        signed_double_area.append(ue[j] * ze[k] - ue[l] * ze[i])
        if i != k:
            crossings[min(i, k)].append(j)
    inside = np.zeros_like(footprint)
    for row, locations in crossings.items():
        locations.sort()
        if len(locations) % 2:
            raise ValueError("Unpaired contour intersection")
        for left, right in zip(locations[::2], locations[1::2]):
            inside[row, left:right] = True
    if not np.array_equal(inside, footprint):
        raise ValueError("The native projected mask and rasterized polygon differ")
    return inside, len(boundary) - 1, abs(math.fsum(signed_double_area)) / 2


def areas(mask, ue, ze):
    """Integrate each horizontal span between its physical edges, then sum by side."""
    split = np.flatnonzero(ze == 0).item()
    sums = [[], []]
    for i in np.flatnonzero(mask.any(axis=1)):
        runs = np.flatnonzero(np.diff(mask[i].astype(np.int8), prepend=0, append=0))
        width = math.fsum(ue[right] - ue[left] for left, right in zip(runs[::2], runs[1::2]))
        sums[int(i >= split)].append(width * (ze[i+1] - ze[i]))
    negative, positive = map(math.fsum, sums)
    return dict(zip(SIDES, (negative, positive, negative + positive)))


def ratio(x, y):
    return x / y if y else None


def score(deg, front, name, truth, candidate, inside, ue, ze):
    true = candidate & truth
    false = candidate & ~truth
    masks = {"lobe_kpc2": truth, "true_before_kpc2": true, "false_before_kpc2": false,
             "true_after_kpc2": true & inside, "false_after_kpc2": false & inside,
             "true_lost_kpc2": true & ~inside, "false_removed_kpc2": false & ~inside,
             "lobe_outside_front_kpc2": truth & ~inside}
    measures = {field: areas(mask, ue, ze) for field, mask in masks.items()}
    rows = []
    for side in SIDES:
        row = {key: value[side] for key, value in measures.items()}
        for when in ("before", "after"):
            overlap = row[f"true_{when}_kpc2"]
            selected = overlap + row[f"false_{when}_kpc2"]
            row[f"selected_{when}_kpc2"] = selected
            row[f"completeness_{when}"] = ratio(overlap, row["lobe_kpc2"])
            row[f"purity_{when}"] = ratio(overlap, selected)
        row["false_removed_fraction"] = ratio(row["false_removed_kpc2"], row["false_before_kpc2"])
        row["true_lost_fraction"] = ratio(row["true_lost_kpc2"], row["true_before_kpc2"])
        rows.append(dict(view_deg=deg, hemisphere=side, front=front, candidate=name, **row))
    return rows


def check_historical_rows(rows, reference_file):
    with reference_file.open() as stream:
        baselines = {(int(r["view_deg"]), r["hemisphere"], r["comparison"]): r
                     for r in csv.DictReader(stream) if r["method"] == METHOD}
    fields = {"selected_before_kpc2": "selected_kpc2", "lobe_kpc2": "truth_kpc2",
              "false_before_kpc2": "false_area_kpc2", "completeness_before": "completeness",
              "purity_before": "purity"}
    differences = {key: [] for key in fields}
    for r in rows:
        if r["hemisphere"] == "both" or r["front"] != "primary":
            continue
        old = baselines[r["view_deg"], r["hemisphere"], COMPARISONS[r["candidate"]]]
        for field, old_field in fields.items():
            differences[field].append(abs(r[field] - float(old[old_field])))
            if not math.isclose(r[field], float(old[old_field]), rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"Original November 23 baseline differs: {old_field} at {old}")
    return {key: max(values) for key, values in differences.items()}


def measure(maps, front):
    receipt = json.loads(checked(REFERENCE / "comparison_receipt.json", REFERENCE_HASH).read_text())
    old = receipt["observer_input_hashes"]
    checked(maps / "completion.json", old["source_receipt_sha256"])
    native = json.loads(checked(front / "completion.json", receipt["front_receipt_sha256"]).read_text())
    if native["native_inputs_sha256"] != old["native_source_sha256"]:
        raise ValueError("Native inputs differ between producers")
    if native["source_producer_sha256"] != old["source_receipt_sha256"]:
        raise ValueError("Different emission producer")
    if any(native["component_summaries"][arm]["boundary_cells"] for arm in FRONTS):
        raise ValueError("Native boundary component present")
    rows, geometry, hashes, clipped_masks = [], [], {}, {}
    for deg in (0, 45, 90):
        filename = f"G-HI_0020_{deg}deg.npz"
        fhash = receipt["views"][str(deg)]["native_map_sha256"]
        if native["files"][filename]["sha256"] != fhash:
            raise ValueError(f"Native map binding differs for {filename}")
        mhash = old["view_map_sha256"][str(deg)]
        with np.load(checked(maps / filename, mhash)) as m, np.load(checked(front / filename, fhash)) as f:
            axes = {key: f[key] for key in AXES}
            if any(not np.array_equal(v, m[k]) for k, v in axes.items()):
                raise ValueError(f"Observer and native axes differ at {deg} degrees")
            ue, ze = axes["horizontal_edges_kpc"], axes["z_edges_kpc"]
            if np.any(np.diff(ue) <= 0) or np.any(np.diff(ze) <= 0):
                raise ValueError("Detector edges out of order")
            path = m["path_C_kpc"]
            replacement = (m["brightness_current_retained_linear_whole"] + f["front_initial_brightness"]
                           - f["front_current_brightness"])
            refit = View(filename, "development", axes, replacement,
                         m["brightness_initial_retained_linear_whole"], path, None, None)
            fit, _, first = refit.profiles(replacement, np.zeros_like(replacement, dtype=bool))
            if first != 0:
                raise ValueError("Replacement image lacks its central fit bin")
            candidates = {"original_radial": m[f"original_mask_{METHOD}"].astype(bool),
                          "replacement_refit_radial": refit.outline(fit)}
            hashes[deg] = {"observer_npz": mhash, "front_npz": fhash,
                           "candidate_uint8_rowmajor": {key: mask_hash(v) for key, v in candidates.items()}}
            for arm, key in FRONTS.items():
                inside, vertices, polygon_area = trace_interior(f[key] > 0, ue, ze)
                scanline_area = areas(inside, ue, ze)["both"]
                if not math.isclose(scanline_area, polygon_area, rel_tol=1e-12):
                    raise ValueError("Polygon and scanline area disagree")
                geometry.append(dict(view_deg=deg, front=arm, exterior_vertices=vertices,
                                     inside_uint8_rowmajor_sha256=mask_hash(inside),
                                     polygon_area_kpc2=polygon_area, scanline_area_kpc2=scanline_area))
                for name, candidate in candidates.items():
                    rows.extend(score(deg, arm, name, path > 0, candidate, inside, ue, ze))
                    clipped_masks[deg, arm, name] = mask_hash(candidate & inside)
    old_table = checked(REFERENCE / "replacement_recovery.csv", receipt["products"]["replacement_recovery.csv"])
    return {"protocol_commit": "3bf61df", "protocol_sha256": digest(PROTOCOL),
            "november23_comparison_receipt_sha256": REFERENCE_HASH,
            "november23_baseline_sha256": digest(old_table),
            "reviewed_candidates": list(COMPARISONS), "input_and_candidate_sha256": hashes,
            "replacement_detector_sha256": digest(Path(__file__).with_name("review_source_excluded_backgrounds.py")),
            "geometry": geometry, "november23_max_absolute_difference": check_historical_rows(rows, old_table),
            "rows": rows}, clipped_masks


def compare_scores(independent, clipped_masks, score_file):
    fields = {"lobe_kpc2": "lobe_area_kpc2", "true_lost_fraction": "fraction_selected_true_lost",
              "false_removed_fraction": "fraction_false_removed"}
    shared = ("lobe_outside_front_kpc2", "false_before_kpc2", "false_removed_kpc2", "false_after_kpc2",
              "true_before_kpc2", "true_lost_kpc2", "true_after_kpc2",
              "completeness_before", "completeness_after", "purity_before", "purity_after")
    fields.update({name: name for name in shared})
    fields["fraction_full_lobe_lost"] = "fraction_full_lobe_lost"

    def row_key(r):
        return int(r["view_deg"]), r["front"], r["candidate"], r["hemisphere"]

    with score_file.open() as stream:
        selected = [r for r in csv.DictReader(stream) if r["candidate"] in COMPARISONS]
    primary = {row_key(r): r for r in selected}
    if len(selected) != len(primary) or set(primary) != {row_key(r) for r in independent}:
        raise ValueError("Independent and main score tables have different row keys")
    max_error = dict.fromkeys(fields.values(), 0.0)
    for r in independent:
        key = row_key(r)
        published = primary[key]
        if clipped_masks[key[:3]] != published["clipped_bipolar_mask_sha256"]:
            raise ValueError(f"Clipped candidate mask differs for {key[:3]}")
        extended = dict(r, fraction_full_lobe_lost=ratio(r["true_lost_kpc2"], r["lobe_kpc2"]))
        for ours, theirs in fields.items():
            actual, expected = extended[ours], float(published[theirs])
            max_error[theirs] = max(max_error[theirs], abs(actual - expected))
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"{theirs} differs for {key}")
    return {"area_scores_sha256": digest(score_file), "rows_matched": len(independent),
            "distinct_clipped_masks_checked": len(clipped_masks), "max_absolute_difference": max_error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--front", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare", type=Path, help="Verify the independent results against an area_scores.csv")
    args = parser.parse_args()
    result, clipped_masks = measure(args.maps, args.front)
    if args.compare:
        raw = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
        result["independent_measurement_sha256"] = hashlib.sha256(raw).hexdigest()
        result["main_table_comparison"] = compare_scores(result["rows"], clipped_masks, args.compare)
        result["software"] = {"python": platform.python_version(), "numpy": version("numpy"),
                              "scipy": version("scipy"), "scikit-image": version("scikit-image"),
                              "review_script_sha256": digest(Path(__file__))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
