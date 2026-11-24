"""Check the full original exterior 5%-deficit arcs in the exposed G-HI/20 maps."""

import argparse
import json
from pathlib import Path

import numpy as np

from compare_compressive_front import ANGLES, AXES, HASH, ORANGE, PRODUCER_SHA, SOURCE_HASHES
from compare_compressive_front import view_inputs, write_rows
from xray_cavity_method_ladder import deficit_threshold, observer_radial_background


NATIVE_RECEIPT_SHA = "eab950abbd5ed5afe30f4f2703cf16539f318a32a50d15df6ebb877087599bde"
THRESHOLD = 0.05


def view_rows(angle, original, native):
    if any(not np.array_equal(original[key], native[key]) for key in AXES):
        raise ValueError(f"Unmatched sky coordinates at {angle} degrees")
    grid, _, _, _, backgrounds, exterior = view_inputs(original)
    current = original["brightness_current_retained_linear_whole"]
    initial = original["brightness_initial_retained_linear_whole"]
    original_background = backgrounds[ORANGE]
    replaced = current + native["front_initial_brightness"] - native["front_current_brightness"]
    refitted_background = observer_radial_background(replaced, grid.u, grid.z)
    fixed, refitted = (
        deficit_threshold(replaced, grid.u, grid.z, background=background,
                          background_label="observer_radial", threshold=THRESHOLD)
        for background in (original_background, refitted_background)
    )
    fixed_mask, refitted_mask = fixed.mask, refitted.mask
    z = grid.z[:, None]
    for side, select in (("negative_z", exterior & (z < 0)),
                         ("positive_z", exterior & (z > 0)),
                         ("both", exterior)):
        weights = grid.area[select]
        area = weights.sum()
        if not area or np.any(initial[select] <= 0) or np.any(original_background[select] <= 0):
            raise ValueError(f"Invalid area or brightness denominator at {angle}/{side}")

        def integrate(field):
            return np.sum(weights * field[select])

        def area_percent(condition):
            return 100 * (weights[condition[select]].sum() / area)

        initial_flux = integrate(initial)
        current_flux = integrate(current)
        background_flux = integrate(original_background)
        yield {
            "view_deg": angle,
            "hemisphere": side,
            "original_exterior_area_kpc2": area,
            "current_vs_initial_brightness_pct": 100 * (current_flux / initial_flux - 1),
            "original_background_vs_initial_pct": 100 * (background_flux / initial_flux - 1),
            "original_background_minus_current_pct_of_background": 100 * (1 - current_flux / background_flux),
            "area_dimmed_over_5pct_vs_initial_pct": area_percent(current < (1 - THRESHOLD) * initial),
            "replacement_vs_current_brightness_pct": 100 * (integrate(replaced) / current_flux - 1),
            "replacement_background_vs_original_pct": 100 * (integrate(refitted_background) / background_flux - 1),
            "area_above_5pct_with_fixed_background_pct": area_percent(fixed.deficit > THRESHOLD),
            "area_above_5pct_with_refitted_background_pct": area_percent(refitted.deficit > THRESHOLD),
            "area_retained_with_fixed_background_pct": area_percent(fixed_mask),
            "area_retained_with_refitted_background_pct": area_percent(refitted_mask),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path, help="Original G-HI_0020 emission directory")
    parser.add_argument("--native", required=True, type=Path, help="Final native front emission directory")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV")
    args = parser.parse_args()
    for folder, expected in ((args.inputs, PRODUCER_SHA), (args.native, NATIVE_RECEIPT_SHA)):
        if HASH(folder / "completion.json") != expected:
            raise ValueError(f"Unexpected G-HI/20 producer receipt in {folder}")
    native_products = json.loads((args.native / "completion.json").read_text())["files"]
    inputs = []
    for angle in ANGLES:
        name = f"G-HI_0020_{angle}deg.npz"
        original, native = args.inputs / name, args.native / name
        if HASH(original) != SOURCE_HASHES[angle] or HASH(native) != native_products[name]["sha256"]:
            raise ValueError(f"G-HI/20 map identity differs for {name}")
        inputs.append((angle, original, native))
    rows = []
    for angle, original, native in inputs:
        with np.load(original, allow_pickle=False) as obs, np.load(native, allow_pickle=False) as front:
            rows.extend(view_rows(angle, obs, front))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_rows(args.output, rows)


if __name__ == "__main__":
    main()
