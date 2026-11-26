"""Check the slab flux and area tables on the original, released tracer footprint."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

REGISTRATION = (Path(__file__).resolve().parents[2] / "docs/science/assets"
                / "four_case_midplane_slabs_2026-11-26/registration.json")


def table(path, column=None, value=None):
    with path.open() as handle:
        return {(r["depth"], r["hemisphere"]): r for r in csv.DictReader(handle)
                if column is None or r[column] == value}


def check_unit(unit, native, scores, released_tracer, producer_receipts):
    name = unit["case_age"]
    old = (producer_receipts / f"{name}.json").read_bytes()
    if hashlib.sha256(old).hexdigest() != unit["previous_producer_sha256"]:
        raise ValueError(f"{name}: historical producer differs from registration")
    target = released_tracer / f"{name}_0deg.truth.npz"
    if hashlib.sha256(target.read_bytes()).hexdigest() != json.loads(old)["files"][target.name]["sha256"]:
        raise ValueError(f"{name}: released tracer raster differs from historical producer")
    areas = table(scores / name / "areas.csv", "target", "full_lobe")
    controls = table(scores / name / "time_zero_controls.csv")
    fluxes = table(scores / name / "depth_flux.csv", "sightlines", "lobe")
    errors = []
    with np.load(target, allow_pickle=False) as ref, np.load(native / name / "projections.npz", allow_pickle=False) as maps:
        u, z = ref["horizontal_axis_kpc"], ref["z_axis_kpc"]
        area = np.outer(np.diff(ref["z_edges_kpc"]), np.diff(ref["horizontal_edges_kpc"]))
        footprint = ref["path_C_kpc"] > 0
        if not np.array_equal(ref["path_C_kpc"], maps["tracer_path_full"]):
            raise ValueError(f"{name}: historical and extracted paths differ")
        aperture = np.hypot(u[None, :], z[:, None]) <= 120
        for side, take in (("negative_z", z < 0), ("positive_z", z > 0), ("both", np.ones(len(z), dtype=bool))):
            on = footprint & take[:, None]
            off = ~footprint & take[:, None] & aperture
            weights = np.where(on, area, 0.0)
            for depth in ("full", "slab30", "slab10"):
                t, initial = maps["current_" + depth], maps["initial_" + depth]
                valid = (initial > 0) & np.isfinite(initial) & np.isfinite(t)
                dim, bright = valid & (t < .95 * initial), valid & (t > 1.05 * initial)
                f0, ft = (np.einsum("ij,ij->", weights, image) for image in (initial, t))
                key = (depth, side)
                comparisons = (
                    (weights.sum(), areas[key]["lobe_kpc2"]),
                    (area[on & ~aperture].sum(), areas[key]["lobe_outside_aperture_kpc2"]),
                    (area[on & dim].sum(), controls[key]["dimmed_on_lobe_kpc2"]),
                    (area[off & dim].sum(), controls[key]["dimmed_off_lobe_in_search_kpc2"]),
                    (area[on & bright].sum(), controls[key]["brightened_on_lobe_kpc2"]),
                    (area[off & bright].sum(), controls[key]["brightened_off_lobe_in_search_kpc2"]),
                    (f0, fluxes[key]["initial_flux"]), (ft, fluxes[key]["current_flux"]),
                    (1 - ft / f0, fluxes[key]["matched_deficit"]),
                )
                for direct, saved in comparisons:
                    error = abs(direct - float(saved)) / max(1.0, abs(float(saved)))
                    if not np.isfinite(error) or error > 1e-10:
                        raise ValueError(f"{name}/{depth}/{side}: direct value {direct} differs from {saved}")
                    errors.append(float(error))
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("native", "scores", "released-tracer", "producer-receipts", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    units = json.loads(REGISTRATION.read_bytes())["science"]
    errors = []
    for unit in units:
        errors.extend(check_unit(unit, args.native, args.scores, args.released_tracer, args.producer_receipts))
    receipt = {"case_ages": len(units), "side_depth_values_checked": len(errors),
               "largest_absolute_difference_scaled_by_max_one_and_reference": max(errors),
               "registration_sha256": hashlib.sha256(REGISTRATION.read_bytes()).hexdigest(),
               "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "reference": "Original released full-depth tracer raster, separately bound to the sealed producer",
               "scope": "Footprint and aperture areas, dimmed and brightened areas on and off the lobe, both fluxes and matched deficit"}
    args.out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
