"""Audit the published radial baselines for 66 views and recompute fits on five views."""

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import label

from source_excluded_inputs import AXES, SCIENCE, SIDES, iter_source_views


SAMPLE = {"G-HI_0020_0deg", "G-HI_0020_45deg", "G-HI_0020_90deg", "C-HI_0050_45deg", "G-LO_0030_90deg"}
PUBLISHED_SCORES = "717680dbe1c5ac98c579aee1681cf527385115c73f4aac6678b19050470cee11"
RADIAL_LABEL = "observer_refit__deficit_threshold_observer_radial_0.05__retained_linear__v0"
NATIVE_MASKS = ["tracer_footprint", "speed_ge_30", "speed_ge_100", "speed_ge_300",
                "pressure_changed", "density_changed", "boundary_thermo_changed"]


def compare(context, actual, expected):
    if isinstance(expected, (float, np.floating)):
        agrees = actual is not None and np.isclose(actual, expected, rtol=5e-12, atol=3e-11)
    else:
        agrees = actual == expected
    if not agrees:
        raise ValueError(f"{context}: {actual!r} differs from independently expected {expected!r}")


def published_rows():
    data = gzip.decompress((SCIENCE / "assets/heldout_xray_2026-11-24/scores.csv.gz").read_bytes())
    compare("published DET-05 score checksum", hashlib.sha256(data).hexdigest(), PUBLISHED_SCORES)
    rows = {(r["unit_id"], r["hemisphere"]): r for r in csv.DictReader(io.StringIO(data.decode()))
            if r["key"] == RADIAL_LABEL}
    compare("published radial rows", len(rows), 132)
    return rows


def test_baseline(result, public, side):
    row = result["arms"]["original"]["scores"]["flat"][side]
    f = row["truth_outside_aperture_fraction"]
    expected = {
        "unit_id": result["unit_id"], "case": result["case"], "snapshot_index": str(result["index"]),
        "view_deg": str(result["angle"]), "kind": result["kind"], "hemisphere": side,
        "key": RADIAL_LABEL, "mode": "observer_refit", "method": "deficit_threshold_observer_radial_0.05",
        "correction": "retained_linear", "truth_assisted_input": "False", "velocity_cut_km_s": "0",
        "primary": "True", "qualification_holds": result["qualifications"],
        "recovered_area_kpc2": row["selected_kpc2"], "truth_area_kpc2": row["truth_kpc2"],
        "intersection_area_kpc2": row["intersection_kpc2"], "completeness": row["completeness"],
        "purity": row["purity"], "nondetection": row["nondetection"], "aperture_contact": row["touches_aperture"],
        "truth_fraction_inside_candidate_aperture": None if f is None else 1 - f,
        "revolution_volume_kpc3": row["inferred_volume_kpc3"], "generalization_criterion_passed": row["screen_passed"],
    }
    compare("DET-05 column set", public.keys(), expected.keys())
    for name, value in expected.items():
        field = public[name]
        if name == "qualification_holds":
            actual = json.loads(field)
        elif not field:
            actual = None
        elif isinstance(value, bool):
            actual = field == "True"
        elif isinstance(value, float):
            actual = float(field)
        else:
            actual = field
        compare(f"{result['unit_id']}/{side}/{name}", actual, value)


def rim_of(aperture):
    # A selected pixel touches the aperture when at least one of its four face neighbours is outside.
    p = np.pad(aperture, 1)
    return ~(p[2:, 1:-1] & p[:-2, 1:-1] & p[1:-1, 2:] & p[1:-1, :-2])


def direct_profile(view, radius, area, excluded, arm, physical):
    """Work in literal two-dimensional rings. Smooth by explicit finite Gaussian convolution."""
    u, _, z, _ = (view.axes[k] for k in AXES)
    sky = view.image
    roi = radius <= 180
    valid = roi & np.isfinite(sky) & (sky > 0)
    sector = np.floor(np.mod(np.arctan2(z[:, None], u), 2*np.pi) / (np.pi/6)).astype(int) % 12
    rows = arm["bins"]
    centres = np.arange(2.5, radius[roi].max() + 2.5, 5.)
    compare("registered annulus count", len(rows), len(centres))
    medians = []
    original = []
    for i, r in enumerate(rows):
        inner, outer = 5*i, 5*(i+1)
        ring = roi & (radius >= inner) & (radius < outer)
        available = ring & valid
        kept = available & ~excluded
        sets = [np.unique(sector[mask]) for mask in (available, kept)]
        n, n_kept = (int(np.count_nonzero(m)) for m in (available, kept))
        median = float(np.median(sky[kept])) if n_kept else None
        original_median = float(np.median(sky[available])) if n else None
        original.append(np.nan if original_median is None else original_median)
        absolute = float(area[available].sum())
        retained = float(area[kept].sum())
        measurements = {
            "bin_index": i, "r_inner_kpc": float(inner), "r_outer_kpc": float(outer),
            "r_center_kpc": float(centres[i]), "roi_pixels": int(ring.sum()), "roi_area_kpc2": float(area[ring].sum()),
            "valid_pixels": n, "valid_area_kpc2": absolute, "valid_sectors": len(sets[0]),
            "retained_area_kpc2": retained, "retained_pixels": n_kept, "retained_sectors": len(sets[1]),
            "retained_area_fraction": retained / absolute if n else None,
            "valid_sector_bits": sum(2**int(s) for s in sets[0]), "retained_sector_bits": sum(2**int(s) for s in sets[1]),
            "required_pixels": min(n, 8), "required_sectors": min(len(sets[0]), 3),
            "full_median": original_median, "retained_median": median,
        }
        measurements["retained_tracer_kpc2"] = float(area[kept & physical["tracer_footprint"]].sum())
        if "pressure_changed" in physical:
            changes = {key: physical[key] for key in ("pressure_changed", "density_changed", "boundary_thermo_changed")}
            changes["thermo_changed"] = changes["pressure_changed"] | changes["density_changed"]
            for key, changed_mask in changes.items():
                measurements["retained_" + key + "_kpc2"] = float(area[kept & changed_mask].sum())
        for name, value in measurements.items():
            compare(f"{view.unit_id}/bin{i}/{name}", r[name], value)
        is_direct = n_kept >= min(n,8) and len(sets[1]) >= min(len(sets[0]),3) and n_kept > 0
        medians.append(median if is_direct else np.nan)
    medians = np.asarray(medians)
    direct = np.flatnonzero(np.isfinite(medians))
    changed = np.any(excluded & valid)
    status = "no_supported_annuli" if direct.size == 0 else (
        "one_supported_annulus" if changed and direct.size == 1 and len(rows) > 1 else "ok")
    compare("flat status", arm["status"]["flat"], status)
    if status != "ok":
        compare("unsupported fit has no scores", arm["scores"], {})
        return None
    first, last = direct[0], direct[-1]
    filled = np.interp(centres, centres[direct], medians[direct])
    slope = filled.copy()
    if first > 0 and changed:
        anchors = direct[:3]
        a, _ = np.polyfit(centres[anchors], np.log(medians[anchors]), 1)
        slope[:first] = medians[first] * np.exp(a * (centres[:first] - centres[first]))

    original = np.array(original)
    original_direct = np.isfinite(original)
    stop = np.flatnonzero(original_direct)[-1] + 1
    kernel = np.exp(-.5*(np.arange(-8,9) / 2.)**2)
    kernel /= kernel.sum()

    def smoothed(values):
        result = np.convolve(np.pad(values[:stop], 8, mode="edge"), kernel, mode="valid")
        return np.pad(result, (0, len(rows)-stop), mode="edge")

    reference = smoothed(np.interp(centres, centres[original_direct], original[original_direct]))
    profile = smoothed(filled)
    slope_profile = smoothed(slope)
    classes = []
    for i, r in enumerate(rows):
        support = ("direct" if np.isfinite(medians[i]) else "inner_extrapolated" if i < first
                   else "outer_extrapolated" if i > last else "interpolated")
        classes.append(support)
        for name, value in (("support_class", support), ("flat_unsmoothed", filled[i]), ("flat_profile", profile[i]),
                            ("baseline_profile", reference[i]), ("log_slope_unsmoothed", slope[i]),
                            ("log_slope_profile", slope_profile[i])):
            compare(f"{view.unit_id}/bin{i}/{name}", r[name], value)
    for name, value in {"central_extrapolation_kpc": first*5., "min_direct_inner_kpc": first*5.,
                        "n_direct": len(direct), "n_bracketed": classes.count("interpolated"),
                        "n_outer_extrapolated": classes.count("outer_extrapolated")}.items():
        compare(f"{view.unit_id}/coverage/{name}", arm["coverage"][name], value)
    return np.interp(radius, centres, profile)


def select(view, radius, background):
    u, _, z, _ = (view.axes[k] for k in AXES)
    # The frozen component screen uses widths from centre spacings. Published scores use native edges.
    screen_area = np.outer(np.gradient(z), np.gradient(u))
    support = (radius <= 120) & (view.image < .95*background)
    accepted = np.zeros_like(support)
    for half in (z < 0, z > 0):
        components, _ = label(support[half], np.ones((3, 3), bool))
        large = np.bincount(components.ravel(), weights=screen_area[half].ravel()) >= 25
        large[0] = False
        accepted[half] = large[components]
    return accepted


def geometry(view, mask, area, radius, side):
    _, ue, z, ze = (view.axes[k] for k in AXES)
    half = (z < 0 if side == "negative_z" else z > 0 if side == "positive_z" else np.ones(z.size, bool))[:, None]
    selected = mask & half
    target = (view.target_path_kpc > 0) & half
    truth, found, overlap = (float(area[m].sum()) for m in (target, selected, target & selected))
    outside = selected & ~target
    initial = view.initial_image
    v = float(np.sum((area * view.target_path_kpc)[target]))
    # Integral of |u| du has primitive u|u|/2, including edges spanning zero.
    volume_elements = np.outer(np.diff(ze), .5*np.pi*np.diff(ue*np.abs(ue)))
    volume = float(volume_elements[selected].sum())
    comp, purity = overlap/truth if truth else None, overlap/found if found else None
    contact = bool(np.any(selected & rim_of(radius <= 120)))
    values = dict(selected_kpc2=found, intersection_kpc2=overlap, truth_kpc2=truth,
                  false_area_kpc2=float(area[outside].sum()), completeness=comp, purity=purity,
                  truth_outside_aperture_fraction=float(area[target & (radius > 120)].sum()) / truth if truth else None,
                  nondetection=not bool(found), touches_aperture=contact, inferred_volume_kpc3=volume,
                  native_lobe_kpc3=v, inferred_over_native=volume/v if v else None,
                  captured_native_kpc3=float((area * view.target_path_kpc)[selected].sum()),
                  false_dimmed_over_5pct_kpc2=float(area[outside & (initial > 0) & (view.image < .95*initial)].sum()),
                  added_vs_baseline_kpc2=float(area[selected & ~view.baseline_mask].sum()),
                  lost_vs_baseline_kpc2=float(area[half & view.baseline_mask & ~mask].sum()))
    if side != "both":
        values["screen_passed"] = not found if view.kind == "initial_null" else bool(comp and comp >= .75
                                                                      and purity and purity >= .95 and not contact)
    return values


def native_masks(directory, view, result):
    folder = directory / f"{view.case}_{view.snapshot_index:04d}"
    receipt = folder / "completion.json"
    packed = folder / (view.unit_id + ".npz")
    receipt_bytes = receipt.read_bytes()
    raw = packed.read_bytes()
    native = json.loads(receipt_bytes)
    compare("native receipt digest", result["native_support"]["native_receipt_sha256"], hashlib.sha256(receipt_bytes).hexdigest())
    compare("native raster digest", result["native_support"]["native_map_sha256"], hashlib.sha256(raw).hexdigest())
    compare("completed native raster digest", native["files"][packed.name]["sha256"], hashlib.sha256(raw).hexdigest())
    compare("source producer", native["producer_sha256"], view.provenance["producer_receipt_sha256"])
    for role in ("current_h5", "initial_h5", "grid_file"):
        compare("bound " + role, native["native_inputs"][role]["sha256"], view.provenance[role + "_sha256"])
    with np.load(io.BytesIO(raw), allow_pickle=False) as f:
        if any(not np.array_equal(view.axes[k], f[k]) for k in AXES):
            raise ValueError(f"{view.unit_id}: native sky coordinates differ")
        masks = {k: f[k] for k in NATIVE_MASKS}
    tracer = masks["tracer_footprint"]
    if any(m.dtype != bool or m.shape != view.image.shape for m in masks.values()):
        raise ValueError(f"{view.unit_id}: invalid native footprint grid")
    if (np.any(masks["speed_ge_300"] & ~masks["speed_ge_100"]) or np.any(masks["speed_ge_100"] & ~masks["speed_ge_30"])
            or np.any(masks["boundary_thermo_changed"] & ~(masks["pressure_changed"] | masks["density_changed"]))):
        raise ValueError(f"{view.unit_id}: native footprint nesting differs")
    if not tracer.any() or (view.kind != "initial_null" and not np.array_equal(tracer, view.target_path_kpc > 0)):
        raise ValueError(f"{view.unit_id}: physical tracer identity differs")
    return masks


def run(args):
    table = published_rows()
    counts = Counter()
    sampled, controls, slow, file_hashes, exposed_speed = {}, {}, {}, {}, {}
    sources = iter_source_views(args.exposed_dir, args.prediction_tar, args.truth_tar)
    for view in sources:
        uid = view.unit_id
        if view.kind == "initial_null" and args.pilot:
            continue
        payload = (args.results / uid / "result.json").read_bytes()
        file_hashes[uid] = hashlib.sha256(payload).hexdigest()
        result = json.loads(payload)
        compare(uid + "/identity", (result["unit_id"], result["kind"]), (uid, view.kind))
        for key in ("maps_sha256", "truth_sha256", "baseline_sha256"):
            compare(uid + "/" + key, result["original_inputs"][key], view.provenance[key])
        counts["views"] += 1
        u, ue, z, ze = (view.axes[k] for k in AXES)
        radius = np.hypot(u, z[:, None])
        area = np.multiply.outer(np.diff(ze), np.diff(ue))
        rim = rim_of(radius <= 120)
        original = result["arms"]["original"]["scores"]["flat"]
        if not args.pilot:
            compare(uid + "/original mask digest", result["arms"]["original"]["mask_sha256"]["flat"],
                    hashlib.sha256(view.baseline_mask.tobytes(order="C")).hexdigest())
        for side, half in zip(SIDES, (z<0,z>0), strict=True):
            compare(uid + "/original_contact/" + side, original[side]["touches_aperture"],
                    bool(np.any((rim & view.baseline_mask)[half])))
            if view.kind != "development":
                test_baseline(result, table[uid, side], side)
                counts["all_24_published_columns_checked_side_rows"] += 1
        valid = (radius <= 180) & np.isfinite(view.image) & (view.image > 0)
        masks = ({"tracer_footprint": view.target_path_kpc > 0} if args.pilot else native_masks(args.native_root, view, result))
        tracer = masks["tracer_footprint"]
        fits = {"original": np.zeros(tracer.shape, bool), "tracer": tracer}
        if not args.pilot:
            fits.update({f"speed_{c}":masks[f"speed_ge_{c}"] for c in (30,100,300)})
            counts["nested_physical_footprints"] += 1
            if view.kind == "development":
                exposed_speed[uid] = {}
                with np.load(args.exposed_dir / (uid + ".npz"), allow_pickle=False) as archived:
                    for cut in (30, 100, 300):
                        ambient = archived[f"path_A_v{cut}_kpc"] > 0
                        all_gas = masks[f"speed_ge_{cut}"]
                        compare(uid + f"/speed{cut} missing moving ambient", bool(np.any(ambient & ~all_gas)), False)
                        compare(uid + f"/speed{cut} excess outside lobe", bool(np.any(all_gas & ~ambient & ~tracer)), False)
                        exposed_speed[uid][cut] = {"moving_ambient_pixels": int(ambient.sum()),
                                                  "additional_fast_tracer_only_pixels": int((all_gas & ~ambient).sum())}
        for name, exclusion in fits.items():
            arm = result["arms"][name]
            continuations = ["flat"] if name == "original" else ["flat", "log_slope"]
            defined = {c for c in continuations if arm["status"][c] == "ok"}
            compare(uid + "/" + name + "/defined scores", set(arm["scores"]), defined)
            if not args.pilot:
                compare(uid + "/" + name + "/defined mask hashes", set(arm["mask_sha256"]), defined)
            remaining = tracer & ~exclusion
            retained = valid & ~exclusion
            checks = {"tracer_sky_kpc2": area[tracer].sum(), "unmasked_tracer_sky_kpc2": area[remaining].sum(),
                      "retained_tracer_kpc2": area[retained & tracer].sum(), "retained_area_kpc2": area[retained].sum(),
                      "excluded_area_kpc2": area[valid & exclusion].sum(), "valid_area_kpc2": area[valid].sum()}
            if not args.pilot:
                for k in ("pressure_changed", "density_changed", "boundary_thermo_changed"):
                    checks["retained_" + k + "_kpc2"] = area[retained & masks[k]].sum()
                union = masks["pressure_changed"] | masks["density_changed"]
                checks["retained_thermo_changed_kpc2"] = area[retained & union].sum()
            for field, measurement in checks.items():
                compare(uid + "/" + name + "/" + field, arm["coverage"][field], measurement)
            if name == "speed_100":
                slow[uid] = float(checks["retained_tracer_kpc2"])
            if view.kind == "initial_null":
                compare(uid + "/initial_evaluation_target", bool(view.target_path_kpc.any()), False)
                for key in ("pressure_changed", "density_changed", "boundary_thermo_changed"):
                    compare(uid + "/initial_" + key, bool(masks[key].any()), False)
                for continuation, score in arm["scores"].items():
                    for side in SIDES:
                        compare(uid + "/null_area", score[side]["truth_kpc2"], 0.)
                        compare(uid + "/null_fraction", score[side]["completeness"], None)
                        compare(uid + "/null_verdict", score[side]["screen_passed"], score[side]["nondetection"])
                    if score["both"]["nondetection"]:
                        empty = hashlib.sha256(bytes(view.image.size)).hexdigest()
                        compare(uid + "/empty initial " + name + "/" + continuation, arm["mask_sha256"][continuation], empty)
                controls.setdefault(uid, {"physical_nozzle_pixels": int(tracer.sum()),
                                          "physical_nozzle_area_kpc2": float(area[tracer].sum())})[name] = {
                    "excluded_pixels": int(exclusion.sum()), "unmasked_nozzle_pixels": int(remaining.sum()),
                    "flat_fit_status": arm["status"]["flat"],
                    "flat_detected_sides": ([s for s in SIDES if not arm["scores"]["flat"][s]["nondetection"]]
                                            if "flat" in defined else None)}
            if uid not in SAMPLE or name not in {"tracer", "speed_100"}:
                continue
            bg = direct_profile(view, radius, area, exclusion, arm, masks)
            if bg is None:
                sampled.setdefault(uid,{})[name] = {"status": arm["status"]["flat"]}
                continue
            selected = select(view, radius, bg)
            digest = hashlib.sha256(selected.tobytes(order="C")).hexdigest()
            if not args.pilot:
                compare(uid + "/" + name + "/flat pixel digest", arm["mask_sha256"]["flat"], digest)
            for side in (*SIDES, "both"):
                for field, value in geometry(view, selected, area, radius, side).items():
                    compare(f"{uid}/{name}/flat/{side}/{field}", arm["scores"]["flat"][side][field], value)
            sampled.setdefault(uid,{})[name] = {"bins": len(arm["bins"]), "flat_mask_sha256": digest, "selected_pixels": int(selected.sum()),
                "negative_contact": bool(np.any((selected & rim)[z < 0])), "positive_contact": bool(np.any((selected & rim)[z > 0]))}
    compare("sample inventory", set(sampled), SAMPLE)
    compare("total rows", counts["all_24_published_columns_checked_side_rows"], 108 if args.pilot else 132)
    return {"phase": "tracer_pilot" if args.pilot else "native_comparison", "counts": counts, "sampled": sampled,
            "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "result_json_sha256": file_hashes, "published_scores_sha256": PUBLISHED_SCORES,
            "exposed_speed_against_archived_tracer_negative_speed_paths": exposed_speed,
            "initial_nozzle_and_arms_with_detected_sides": controls, "speed100_retained_tracer_sightlines_kpc2": slow,
            "method": "Uses the common hash-bound original image/tracer loader and supplied native projections. "
                      "Recomputes annulus selection, medians, flat and log profile continuation, Gaussian convolution, "
                      "flat-continuation selection, contact, exact-edge areas and volumes independently. "
                      "Shares SciPy's 8-neighbour labelling primitive with the original detector."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("exposed-dir", "prediction-tar", "truth-tar", "results", "out"):
        p.add_argument("--" + arg, type=Path, required=True)
    p.add_argument("--native-root", type=Path)
    p.add_argument("--pilot", action="store_true", help="check the 57 evolved tracer-only views")
    args = p.parse_args()
    if args.native_root is None and not args.pilot:
        p.error("the complete comparison requires --native-root")
    audit = run(args)
    args.out.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    print(json.dumps(audit["counts"]))
