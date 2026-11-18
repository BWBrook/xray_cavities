"""Compare stored energy in the four completed inset-box histories."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt


# Accepted completion receipts bind every native compact product below.
RECEIPTS = {
    "C-HI": "b5300a70230ee343b8d4d72eddd137760045d268e0e2c1b2d78b8acec4627a4f",
    "C-LO": "4fed63215e4e5b37e6b9f24562528542ff5abf16c5d45a7890c2b3397732824a",
    "G-HI": "9bac8c77d2dcef62d6f9c6109a2a1a0747eb17464cb544c0f29b2a18d149657d",
    "G-LO": "3f5e7361e2f1c4779de01da4edb062ad62b0f264f9a179f4d47c1d9ff1cced6a",
}


def load_history(directory):
    raw = (directory / "completion.json").read_bytes()
    receipt = json.loads(raw)
    case = receipt["case"]
    if hashlib.sha256(raw).hexdigest() != RECEIPTS[case]:
        raise ValueError(f"{case}: unexpected completion receipt")
    products = {Path(product["path"]).name: product for product in receipt["products"]}
    rows = []
    for index in receipt["indices"]:
        name = f"snapshot_{index:04d}.json"
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != products[name]["sha256"]:
            raise ValueError(f"{case}: {name} differs from its receipt")
        snapshot = json.loads(raw)
        regions = snapshot["regions"]
        exterior = regions["outside_fixed_inset_box"]["partitions"]["all"]
        rows.append({
            "case": case, "index": index, "age_myr": snapshot["actual_time_myr"],
            "labelled_input_erg": snapshot["labelled_input_erg"],
            "fixed_box_over_label": regions["fixed_inset_box"]["partitions"]["all"]["total_over_labelled_input"],
            "R100_over_label": regions["R100"]["partitions"]["all"]["total_over_labelled_input"],
            "whole_grid_over_label": regions["whole_grid"]["partitions"]["all"]["total_over_labelled_input"],
            "exterior_total_delta_erg": exterior["total_delta_erg"],
            "exterior_thermal_plus_kinetic_delta_erg": exterior["thermal_plus_kinetic_delta_erg"],
            "exterior_mass_delta_g": exterior["mass_delta_g"],
            "cocoon_inside_box": snapshot["operational_coverage"]["current_cocoon"]["all_selected_cells_inside_fixed_inset_box"],
            "R100_inside_box": snapshot["speed_apertures"]["R100"]["geometrically_complete_in_fixed_inset_box"],
        })
    return case, rows


def write_comparison(directories, output):
    histories = dict(load_history(directory) for directory in directories)
    if histories.keys() != RECEIPTS.keys():
        raise ValueError("Expected one accepted fixed-budget history for each of the four cases")
    output.mkdir(parents=True, exist_ok=True)
    with (output / "histories.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=histories["C-HI"][0].keys(), lineterminator="\n")
        writer.writeheader()
        for case in RECEIPTS:
            writer.writerows(histories[case])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), layout="constrained")
    for case, color in zip(RECEIPTS, ("#194d80", "#4285ae", "#a03b17", "#d27628")):
        rows = [row for row in histories[case] if row["labelled_input_erg"] > 0]
        ages = [row["age_myr"] for row in rows]
        style = "-" if case.endswith("HI") else "--"
        for axis, key in zip(axes, ("fixed_box_over_label", "exterior_total_delta_erg")):
            axis.plot(ages, [row[key] for row in rows], style, color=color, label=case, lw=2)
        first_exit = next((row for row in rows if not row["cocoon_inside_box"]), None)
        if first_exit:
            axes[0].plot(first_exit["age_myr"], first_exit["fixed_box_over_label"], "o",
                         color=color, markerfacecolor="white", markersize=7)
    axes[0].axhline(1, lw=0.9, ls=":", color="0.35")
    axes[0].set(title="Energy stored inside the fixed box", ylabel="Stored change / labelled jet input")
    axes[0].legend(frameon=False, ncols=2, loc="upper left")
    axes[1].set(title="Energy stored outside the fixed box", ylabel="Stored change (erg)", yscale="log")
    for axis in axes:
        axis.set_xlabel("Age (Myr)")
        axis.spines[["right", "top"]].set_visible(False)
        axis.grid(axis="y", alpha=.2)
    fig.supxlabel("Open circles mark the first snapshot with traced lobe cells outside the box.", fontsize=9)
    fig.savefig(output / "fixed_histories.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("histories", nargs=4, type=Path, help="Four fixed-budget output directories")
    args = parser.parse_args()
    write_comparison(args.histories, args.output)
