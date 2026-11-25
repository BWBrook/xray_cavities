"""Independently refit the three G-HI/20 slab images and account for the removed emission."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from review_source_excluded_backgrounds import AXES, View


REFERENCE_SHA = "46935fca242ddc96c4ad8776db1b4e00e76ec27f9215a923308e29f323d99e80"
MASK = "mask_retained_linear_v100_deficit_threshold_observer_radial_0.05_exact_projection_refit"
FIELDS = {
    "current": "brightness_current_retained_linear_whole",
    "initial": "brightness_initial_retained_linear_whole",
    "tracer_path": "path_C_kpc",
    "current_lobe": "brightness_current_retained_linear_C",
    "initial_on_current_lobe": "brightness_initial_retained_linear_C",
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def fraction(n, d):
    return n / d if d else None


def check_maps(maps, parent, height):
    for field, array in maps.items():
        if array.shape != parent[field].shape or not np.isfinite(array).all():
            raise ValueError(f"{field} has an invalid shape or nonfinite values")
    # The archived emissivity extrapolation is signed. Only path lengths
    # must grow monotonically with integration depth.
    path = maps["tracer_path"]
    if np.any(path < 0) or np.any(path > np.minimum(height, parent["tracer_path"]) * (1 + 1e-10)):
        raise ValueError("Tracer path exceeds its physical bounds")
    for member in ("current_lobe", "initial_on_current_lobe"):
        if np.any(maps[member][path == 0] != 0):
            raise ValueError(f"{member} has emission on a sightline without tracer cells")


def integrator(dz, du, rows):
    def integral(field):
        # First sum over physical x-cell widths, then over the selected z rows.
        row_sum = np.einsum("ij,j->i", field[rows], du)
        return float(np.sum(dz[rows] * row_sum))
    return integral


def geometry(total, target, full_depth, depth, mask):
    overlap = total(mask & target)
    selected, lobe = total(mask), total(target)
    return {
        "selected_kpc2": selected, "lobe_kpc2": lobe, "overlap_kpc2": overlap,
        "missed_kpc2": total(target & ~mask), "false_kpc2": total(mask & ~target),
        "completeness": fraction(overlap, lobe), "purity": fraction(overlap, selected),
        "slab_area_retained_fraction": fraction(total(depth > 0), total(full_depth > 0)),
        "slab_volume_retained_fraction": fraction(total(depth), total(full_depth)),
    }


def emission_mixture(total, region, full, slab):
    """Matched sky area and current tracer-cell membership at both epochs."""
    def integral(field):
        return total(np.where(region, field, 0))

    initial = integral(full["initial"])
    current = integral(full["current"])
    slab_initial = integral(slab["initial"])
    slab_current = integral(slab["current"])
    wing_initial = integral(full["initial"] - slab["initial"])
    wing_current = integral(full["current"] - slab["current"])
    lobe_change = integral(slab["initial_on_current_lobe"] - slab["current_lobe"])
    ambient_change = integral((slab["initial"] - slab["initial_on_current_lobe"])
                              - (slab["current"] - slab["current_lobe"]))
    wing_change = wing_initial - wing_current
    residual = fraction(current - initial + lobe_change + ambient_change + wing_change, initial)
    if residual is not None and abs(residual) > 1e-11:
        raise ValueError(f"Physical depression fails component closure: {residual}")
    return {
        "full_initial_brightness_area": initial, "full_current_brightness_area": current,
        "slab_initial_brightness_area": slab_initial, "slab_current_brightness_area": slab_current,
        "wings_initial_brightness_area": wing_initial, "wings_current_brightness_area": wing_current,
        "slab_share_initial_flux": fraction(slab_initial, initial),
        "full_depression": fraction(initial - current, initial),
        "slab_depression": fraction(slab_initial - slab_current, slab_initial),
        "wings_depression": fraction(wing_change, wing_initial),
        "slab_lobe_depression_over_full_initial": fraction(lobe_change, initial),
        "slab_ambient_depression_over_full_initial": fraction(ambient_change, initial),
        "wings_depression_over_full_initial": fraction(wing_change, initial),
        "closure_over_full_initial": residual,
    }


def measure(reference_file, projection_file):
    if digest(reference_file) != REFERENCE_SHA:
        raise ValueError("The archived full-depth G-HI/20 view has a different digest")
    with np.load(reference_file, allow_pickle=False) as obs:
        axes = {k: obs[k] for k in AXES}
        reference = {name: obs[field] for name, field in FIELDS.items()}
        reference_mask = obs[MASK]
    maps = {"full": reference}
    output = {"reference_sha256": REFERENCE_SHA,
              "detector_sha256": digest(Path(__file__).with_name("review_source_excluded_backgrounds.py")),
              "masks": {}, "areas": [], "emission_mixture": [], "selected_exterior": []}
    if projection_file:
        output["projection_sha256"] = digest(projection_file)
        with np.load(projection_file, allow_pickle=False) as data:
            if any(not np.array_equal(data[k], v) for k, v in axes.items()):
                raise ValueError("Native and archived sky axes differ")
            maps = {depth: {name: data[f"{name}_{depth}"] for name in FIELDS}
                    for depth in ("full", "slab30", "slab10")}
        for field in FIELDS:
            np.testing.assert_allclose(maps["full"][field], reference[field], rtol=1e-10, atol=0, err_msg=field)
        check_maps(maps["slab30"], maps["full"], 60)
        check_maps(maps["slab10"], maps["slab30"], 20)

    full = maps["full"]
    full_path = full["tracer_path"]
    _, ue, z, ze = (axes[k] for k in AXES)
    if ze[np.searchsorted(z, 0)] != 0:
        raise ValueError("The z midplane bisects a detector row")
    dz, du = np.diff(ze), np.diff(ue)
    for depth, fields in maps.items():
        current, initial, path = (fields[name] for name in ("current", "initial", "tracer_path"))
        view = View("G-HI_0020_0deg", "development", axes, current, initial, path, None, None)
        fit, _, _ = view.profiles(current, np.zeros(current.shape, dtype=bool))
        mask = view.outline(fit)
        if depth == "full" and not np.array_equal(mask, reference_mask):
            raise ValueError("Full-depth outline disagrees with the archived exact projection refit")
        output["masks"][depth] = hashlib.sha256(mask.tobytes(order="C")).hexdigest()
        exterior = mask & (full_path == 0)
        integrate = integrator(dz, du, slice(None))
        flux_now, flux_zero = (integrate(np.where(exterior, field, 0)) for field in (current, initial))
        bg = np.interp(view.radius, view.centres, fit)
        output["selected_exterior"].append({
            "depth": depth, "area_kpc2": integrate(exterior),
            "initial_dimmed_5pct_kpc2": integrate(exterior & view.dimmed),
            "physical_deficit_fraction": fraction(flux_zero - flux_now, flux_zero),
            "fitted_background_over_initial": fraction(integrate(np.where(exterior, bg, 0)), flux_zero),
        })
        padded = np.pad(view.search, 1)
        interior = view.search & padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
        for side, rows in (("negative_z", z < 0), ("positive_z", z > 0), ("both", slice(None))):
            total = integrator(dz, du, rows)
            for ref, ref_path in (("full_lobe", full_path), ("slab_lobe", path)):
                truth = ref_path > 0
                key = {"depth": depth, "hemisphere": side, "target": ref}
                output["areas"].append({**key, **geometry(total, truth, full_path, path, mask),
                                        "native_lobe_kpc3": total(ref_path),
                                        "lobe_outside_aperture_kpc2": total(truth & ~view.search),
                                        "selection_touches_aperture": bool((mask[rows] & ~interior[rows]).any())})
                if depth != "full":
                    output["emission_mixture"].append({**key, **emission_mixture(total, truth, full, fields)})
            if depth != "full":
                missed = (full_path > 0) & ~reference_mask
                output["emission_mixture"].append({
                    "depth": depth, "hemisphere": side, "target": "missed_by_full_depth_detector",
                    **emission_mixture(total, missed, full, fields),
                })
    return output


def compare(result, directory):
    report = json.loads((directory / "score_receipt.json").read_text())
    if report["candidate_mask_sha256"] != result["masks"]:
        raise ValueError("A candidate mask differs from the primary reconstruction")
    key = ("depth", "hemisphere", "target")
    with (directory / "areas.csv").open(newline="") as stream:
        reader = list(csv.DictReader(stream))
    primary = {tuple(r[k] for k in key): r for r in reader}
    if len(primary) != len(reader) or set(primary) != {tuple(r[k] for k in key) for r in result["areas"]}:
        raise ValueError("Primary score rows do not match the independent sample")
    maximum = {}
    for row in result["areas"]:
        original = primary[tuple(row[k] for k in key)]
        for name in row.keys() - set(key):
            computed, main = row[name], original[name]
            if isinstance(computed, bool):
                if str(computed).lower() != main.lower():
                    raise ValueError(f"{name} disagrees for {[row[k] for k in key]}")
                continue
            if computed is None:
                if main:
                    raise ValueError(f"{name} should be undefined")
                continue
            expected = float(main)
            if not np.isclose(expected, computed, rtol=1e-11, atol=1e-11):
                raise ValueError(f"{[row[k] for k in key]}/{name} differs: {expected} vs {computed}")
            maximum[name] = max(maximum.get(name, 0.), abs(computed - expected))
    with (directory / "filling.csv").open(newline="") as stream:
        exterior = {r["depth"]: r for r in csv.DictReader(stream)
                    if r["region"] == "selected_outside_full_lobe" and r["hemisphere"] == "both"}
    if set(exterior) != {r["depth"] for r in result["selected_exterior"]}:
        raise ValueError("Exterior brightness comparisons do not cover all depths")
    for row in result["selected_exterior"]:
        for name in row.keys() - {"depth"}:
            value = exterior[row["depth"]][name]
            if row[name] is None and value == "":
                continue
            np.testing.assert_allclose(row[name], float(value), rtol=1e-11, atol=1e-11)
    return {"rows": len(reader), "masks": len(result["masks"]), "max_absolute_error": maximum,
            "exterior_brightness_comparisons": len(exterior)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--projection", type=Path, help="New native projections.npz; omit for the archived baseline alone")
    parser.add_argument("--compare", type=Path, help="Compare saved measurements with the primary scoring directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.reference, args.projection)
    if args.compare:
        result["comparison"] = compare(result, args.compare)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
