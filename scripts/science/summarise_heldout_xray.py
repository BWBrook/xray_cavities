"""Reproduce DET-05 from the sealed score table and, optionally, the original private archives."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from statistics import median
import tarfile

import numpy as np

SCIENCE = Path(__file__).resolve().parents[2] / "docs/science"
CUSTODY = SCIENCE / "assets/xray_prediction_seal_2026-11-23"
TABLE = SCIENCE / "assets/heldout_xray_2026-11-24/scores.csv.gz"
MODES = ("observer_refit", "ambient_replaced_refit")
METHODS = ("seed_grow_goal045", "deficit_threshold_observer_radial_0.05")
SIDES = ("negative_z", "positive_z")


def read_scores(seal, receipt):
    data = gzip.decompress(TABLE.read_bytes())
    if hashlib.sha256(data).hexdigest() != receipt["release"]["scores_sha256"]:
        raise ValueError("Decompressed score table differs from the original-site receipt")
    scores = list(csv.DictReader(io.StringIO(data.decode())))
    expected = {(unit["unit_id"], label["key"], side) for unit in seal["units"]
                for label in seal["label_definitions"] for side in SIDES}
    keys = {(r["unit_id"], r["key"], r["hemisphere"]) for r in scores}
    if len(keys) != len(scores) or keys != expected:
        raise ValueError("Score rows differ from the sealed cohort and labels")
    return scores


def primary_results(scores):
    config = SCIENCE.parents[1] / "configs/background_refit_blind_2026-11-11.json"
    criteria = json.loads(config.read_text())["criteria"]
    for row in scores:
        if row["kind"] == "science":
            passed = (float(row["completeness"]) >= criteria["minimum_completeness"]
                      and float(row["purity"] or 0) >= criteria["minimum_purity"]
                      and row["aperture_contact"] == "False")
        else:
            passed = row["nondetection"] == "True"
        if passed != (row["generalization_criterion_passed"] == "True"):
            raise ValueError("Per-side verdict differs from the frozen rule")
    science = [r for r in scores if r["kind"] == "science"]
    controls = [r for r in scores if r["kind"] == "initial_null"]
    primary = [r for r in science if r["primary"] == "True"]
    result = []
    for mode in MODES:
        for method in METHODS:
            rows = [r for r in primary if (r["mode"], r["method"]) == (mode, method)]
            nulls = [r for r in controls if (r["primary"], r["mode"], r["method"]) == ("True", mode, method)]
            completeness = [float(r["completeness"]) for r in rows]
            result.append(dict(mode=mode, method=method, science_sides=len(rows),
                               passed=sum(r["generalization_criterion_passed"] == "True" for r in rows),
                               median_completeness=median(completeness), best_completeness=max(completeness),
                               nondetections=sum(r["nondetection"] == "True" for r in rows),
                               aperture_contacts=sum(r["aperture_contact"] == "True" for r in rows),
                               aperture_limited=sum(float(r["truth_fraction_inside_candidate_aperture"]) < .75 for r in rows),
                               null_sides=len(nulls), null_selections=sum(r["nondetection"] == "False" for r in nulls)))
    sensitivity = Counter()
    for row in science:
        if (row["mode"], row["method"], row["correction"]) == (MODES[1], METHODS[1], "retained_linear"):
            sensitivity[int(row["velocity_cut_km_s"])] += (row["generalization_criterion_passed"] == "True")
    early = [r for r in primary if r["mode"] == MODES[0] and r["snapshot_index"] == "10" and r["case"] in ("C-LO", "G-LO")]
    return {"primary": result, "all_null_side_labels": len(controls),
            "all_null_selections": sum(r["nondetection"] == "False" for r in controls),
            "assisted_radial_passes_by_velocity_km_s": dict(sorted(sensitivity.items())),
            "low_power_10_myr_image_only_method_sides": len(early),
            "low_power_10_myr_image_only_nondetections": sum(r["nondetection"] == "True" for r in early)}


def verify_archive(path, expected):
    with path.open("rb") as src:
        if hashlib.file_digest(src, "sha256").hexdigest() != expected:
            raise ValueError(f"Archive differs from the custody record: {path.name}")


def read_npz(archive, member):
    with archive.extractfile(member) as source:
        return np.load(io.BytesIO(source.read()), allow_pickle=False)


def verify_aperture(masks, labels, uid, scores):
    # A selected centre touches the rim if it or a face neighbour lies outside the circle.
    u2, z2 = np.square(masks["horizontal_axis_kpc"]), np.square(masks["z_axis_kpc"])

    def furthest_axis_value(values):
        extended = np.pad(values, 1, constant_values=np.inf)
        return np.maximum.reduce((extended[:-2], extended[1:-1], extended[2:]))

    along_u = z2[:, None] + furthest_axis_value(u2)[None, :]
    along_z = furthest_axis_value(z2)[:, None] + u2[None, :]
    rim = np.maximum(along_u, along_z) > 120**2
    z = masks["z_axis_kpc"]
    contacts = 0
    for label in labels:
        key = label["key"]
        selected_rim = masks[key].astype(bool) & rim
        for side, half in zip(SIDES, (z < 0, z > 0), strict=True):
            contact = np.any(selected_rim[half])
            if contact != (scores[uid, key, side]["aperture_contact"] == "True"):
                raise ValueError(f"{uid} {key} {side}: aperture contact differs")
            contacts += int(contact)
    return contacts


def raster_results(scores, seal, receipt, prediction_tar, target_tar):
    original = json.loads((CUSTODY / "archive_verification.json").read_text())
    verify_archive(prediction_tar, original["archive_sha256"])
    verify_archive(target_tar, receipt["release"]["archive_sha256"])
    by_side = {(r["unit_id"], r["key"], r["hemisphere"]): r for r in scores}
    contacts = 0
    geometry, exterior = [], []
    with tarfile.open(prediction_tar, "r:") as predictions, tarfile.open(target_tar, "r:") as targets:
        for unit in seal["units"]:
            uid, view = unit["unit_id"], unit["file"]
            initial = f'{unit["case"]}_0000_{unit["view_deg"]}deg.npz'
            with (read_npz(targets, f"truth/{uid}.truth.npz") as target,
                  read_npz(predictions, f"predictions/{view}") as masks,
                  read_npz(predictions, f"map_inputs/{view}") as current,
                  read_npz(predictions, f"map_inputs/{initial}") as baseline):
                contacts += verify_aperture(masks, seal["label_definitions"], uid, by_side)
                if unit["kind"] == "initial_null":
                    continue
                for name in ("horizontal_edges_kpc", "z_edges_kpc", "z_axis_kpc"):
                    if any(not np.array_equal(target[name], other[name]) for other in (masks, current, baseline)):
                        raise ValueError(f"{uid}: projection coordinates differ")
                path = target["path_C_kpc"].astype(float)
                area = np.outer(np.diff(target["z_edges_kpc"]), np.diff(target["horizontal_edges_kpc"]))
                volume = area * path
                z = target["z_axis_kpc"]
                for method in METHODS:
                    key = f"observer_refit__{method}__retained_linear__v0"
                    mask = masks[key].astype(bool)
                    for side, half in zip(SIDES, (z < 0, z > 0), strict=True):
                        native_volume = volume[half].sum()
                        row = by_side[uid, key, side]
                        geometry.append(dict(method=method, case=unit["case"], age=unit["snapshot_index"],
                                             completeness=float(row["completeness"]),
                                             volume_coverage=volume[half][mask[half]].sum() / native_volume,
                                             volume_ratio=float(row["revolution_volume_kpc3"]) / native_volume))
                    if method == METHODS[1]:
                        false = mask & (path == 0)
                        brightness = "brightness_current_retained_linear_whole"
                        dimmed = current[brightness] < .95 * baseline[brightness]
                        exterior.append(dict(case=unit["case"], selected=area[mask].sum(), false=area[false].sum(),
                                             dimmed_false=area[false & dimmed].sum()))
    outcomes = {}
    for method in METHODS:
        rows = [r for r in geometry if r["method"] == method]
        ratios = np.array([r["volume_ratio"] for r in rows])
        detected = np.log10(ratios[ratios > 0])
        low, high = np.quantile(detected, (.16, .84))
        outcomes[method] = {"median_volume_coverage": median(r["volume_coverage"] for r in rows),
                            "median_volume_ratio": float(np.median(ratios)), "detected_sides": len(detected),
                            "detected_volume_ratio_p84_minus_p16_dex": float(high - low)}
    cluster = [r for r in geometry if r["method"] == METHODS[1] and r["case"] == "C-HI" and r["age"] >= 20]
    volume_ratios = [r["volume_ratio"] for r in cluster]
    completeness = [r["completeness"] for r in cluster]
    high_false = Counter(r["case"] for r in exterior if r["false"] > .20 * r["selected"])
    return {"contact_rows_checked": len(by_side), "contact_positive": contacts,
            "image_only_by_method": outcomes, "radial_brightness_views": len(exterior),
            "radial_selected_kpc2": sum(r["selected"] for r in exterior),
            "radial_false_kpc2": sum(r["false"] for r in exterior),
            "radial_dimmed_false_kpc2": sum(r["dimmed_false"] for r in exterior),
            "radial_views_over_20pct_false_by_case": {case: high_false[case] for case in sorted({r["case"] for r in exterior})},
            "cluster_high_20_to_50": {"sides": len(cluster), "volume_ratio_range": [min(volume_ratios), max(volume_ratios)],
                                       "completeness_range": [min(completeness), max(completeness)]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-archives", type=Path, nargs=2, metavar=("PREDICTIONS_TAR", "TARGETS_TAR"),
                        help="also reproduce the post-hoc depth weighting and exterior brightness measurements")
    args = parser.parse_args()
    seal = json.loads((CUSTODY / "seal.json").read_text())
    receipt = json.loads((CUSTODY / "private_scoring_custody.json").read_text())
    scores = read_scores(seal, receipt)
    result = primary_results(scores)
    if args.private_archives:
        result["post_hoc"] = raster_results(scores, seal, receipt, *args.private_archives)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
