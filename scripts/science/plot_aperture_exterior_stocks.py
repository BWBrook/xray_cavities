"""Check the exterior stocks against the older spherical integration and plot the eligible comparisons."""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from four_case_energy_partition import ASSETS, CASES, ENERGY, PINS, PUBLISHED, SPHERES, checked, csv_rows


REVIEW = ASSETS / "aperture_transport_review_2026-11-27"
OUT = ASSETS / "aperture_partition_followup_2026-11-27/exterior_stocks.png"
COLOURS = {"R100": "#116380", "R300": "#a74512"}


def exterior_stocks():
    sphere_hashes = json.loads(checked(SPHERES / "review_manifest.json", PINS[SPHERES / "review_manifest.json"]))["files"]
    stock_hashes = json.loads((PUBLISHED / "verification.json").read_bytes())["products_sha256"]
    boxes = {(r["case"], int(r["snapshot_index"])): r
             for r in csv_rows(checked(PUBLISHED / "box_components.csv", stock_hashes["box_components.csv"]))
             if (r["aperture"], r["region"]) == ("fixed_inset_box", "all")}
    eligible = {(r["case"], int(r["snapshot_index"]), r["aperture"])
                for r in csv_rows(checked(PUBLISHED / "sphere_components.csv", stock_hashes["sphere_components.csv"]))
                if r["region"] == "all" and r["inside_50kpc_inset"] == "True" and int(r["snapshot_index"]) > 0}
    digest = json.loads((REVIEW / "summary.json").read_bytes())["tables"]["exterior.csv"]
    reported = csv_rows(checked(REVIEW / "exterior.csv", digest))
    review = {(r["case"], int(r["end_index"]), r["aperture"]): r for r in reported}
    if len(reported) != len(review) or eligible != review.keys():
        raise ValueError("Eligible inset-box and reviewed rows differ")

    result = {}
    for case in CASES:
        name = f"budgets/{case}/measurements.csv"
        for row in csv_rows(checked(SPHERES / name, sphere_hashes[name]["sha256"])):
            i = int(row["snapshot_index"])
            key = (case, i, "R" + row["speed_threshold_km_s"])
            if key not in eligible:
                continue
            box = boxes[case, i]
            d = float(box["cumulative_net_gas_delivery_erg"])
            age = float(box["actual_age_myr"])
            if age != float(row["actual_time_myr"]) or age != float(review[key]["actual_age_myr"]):
                raise ValueError(f"Unmatched epoch at {key}")
            for component in ENERGY:
                delta = (float(box[component + "_delta_erg"]) - float(row["all_" + component + "_delta_erg"])) / d
                prefix = "stored" if component == "total" else component
                expected = float(review[key][prefix + "_between_aperture_and_inset_box_over_delivery"])
                if not math.isclose(delta, expected, rel_tol=0., abs_tol=2e-13):
                    raise ValueError(f"Independent spherical extraction differs at {key} for {component}")
                if component == "total":
                    adjusted = float(review[key]["later_radius_outward_minus_stored_ahead_over_delivery"])
                    result[key] = (age, 100 * delta, 100 * adjusted)
    if result.keys() != eligible:
        raise ValueError("The spherical archive lacks a required measurement")
    return result


def plot(path):
    values = exterior_stocks()
    fig, (left, right) = plt.subplots(1, 2, figsize=(9.5, 3.9), layout="constrained", width_ratios=(1.55, 1))
    left.set(title="Low-power cluster", xlabel="Age (Myr)", ylabel="Energy outside the sphere\n(% of cumulative injector delivery)")
    right.set(title="Other runs", xlabel="Largest absolute exterior change\n(% of cumulative injector delivery)",
              yticks=[0, 1, 2], yticklabels=["C-HI", "G-HI", "G-LO"], ylim=(2.5, -.5), xlim=(-.0005, .0205),
              xticks=[0., .005, .010, .015, .020], xticklabels=["0", "0.005", "0.010", "0.015", "0.020"])
    left.axhline(0, color="#777777", lw=.7)
    for name, colour in COLOURS.items():
        series = sorted(v for (c, _, a), v in values.items() if (c, a) == ("C-LO", name))
        age, stock, account = zip(*series)
        left.plot(age, stock, color=colour, lw=2)
        left.plot(age, account, color=colour, ls="none", marker="o", mfc="white", ms=3.8,
                  markevery=[i for i in range(len(series)) if (i + 1) % 5 == 0])
        offset = -.12 if name == "R100" else .12
        for j, case in enumerate(("C-HI", "G-HI", "G-LO")):
            maximum = max(abs(v[1]) for (c, _, a), v in values.items() if (c, a) == (case, name))
            right.scatter(maximum, j + offset, color=colour, s=30, zorder=3)
    for ax in (left, right):
        ax.spines[["top", "right"]].set_visible(False)
    left.grid(axis="y", color=".88", lw=.6)
    right.grid(axis="x", color=".88", lw=.6)
    handles = [Line2D([], [], color=c, lw=2, label=n) for n, c in COLOURS.items()]
    handles.append(Line2D([], [], color=".25", marker="o", mfc="white", lw=0, label="Later-radius account (C-LO)"))
    fig.legend(handles=handles, loc="outside lower center", ncols=3, frameon=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=175, facecolor="white")
    plt.close(fig)
    print(f"Checked four components at {len(values)} eligible aperture-epochs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    plot(parser.parse_args().out)
