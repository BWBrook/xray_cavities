"""Plot current whole-cocoon enthalpy and regional stock changes per measured injector delivery."""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from four_case_energy_partition import PUBLISHED, checked, csv_rows
from restate_native_delivery import CASES, ROOT


AGES = (10, 20, 30, 40, 50)
OUTPUT = ROOT / "manuscript/figures/native_delivered_energy_partition.png"
ENERGY_RECEIPT = "e0ea49059f1dbb85089d342d35a958e56d86f333231d77795507293043e48593"


def load_points():
    energy = json.loads(checked(PUBLISHED / "verification.json", ENERGY_RECEIPT))

    def table(name, **selection):
        data = csv_rows(checked(PUBLISHED / name, energy["products_sha256"][name]))
        selected = {}
        for row in data:
            if all(row[field] == value for field, value in selection.items()):
                key = row["case"], int(row["snapshot_index"])
                if key in selected:
                    raise ValueError(f"Duplicate {name} row at {key}")
                selected[key] = row
        return selected

    snapshots = table("snapshots.csv")
    cocoon = table("box_components.csv", aperture="whole_grid", region="cocoon")
    ambient = table("selected_age_components.csv", aperture="R100", region="ambient", snapshot_index="30")
    selected = [(c, i) for c, last in CASES.items() for i in AGES if i <= last]
    if set(ambient) != {(case, 30) for case in CASES}:
        raise ValueError("Expected an ambient thermal measurement in each case at 30 Myr")

    points = []
    for case, i in selected:
        snap, region = snapshots[case, i], cocoon[case, i]
        age = float(snap["actual_age_myr"])
        gas = float(snap["cumulative_net_gas_delivery_erg"])
        row = {"case": case, "index": i, "age": age}
        quantities = [
            ("primary", snap, "native_lobe_2p5pV_erg", "native_lobe_2p5pV_over_delivery"),
            ("comparison", snap, "native_lobe_4pV_erg", "native_lobe_4pV_over_delivery"),
            ("cocoon", region, "total_delta_erg", "total_over_delivery"),
        ]
        if i == 30:
            quantities.append(("ambient", ambient[case, i], "thermal_delta_erg", "thermal_over_delivery"))
        for key, r, erg, ratio in quantities:
            if gas <= 0 or float(r["cumulative_net_gas_delivery_erg"]) != gas or float(r["actual_age_myr"]) != age:
                raise ValueError(f"Invalid supply or unmatched output time at {case}/{i}")
            row[key] = float(r[erg]) / gas
            if not math.isclose(row[key], float(r[ratio]), rel_tol=2e-11, abs_tol=2e-11):
                raise ValueError(f"Published ratio differs at {case}/{i}: {ratio}")
        if not math.isclose(row["comparison"], 1.6 * row["primary"], rel_tol=2e-11):
            raise ValueError(f"Enthalpy convention differs at {case}/{i}")
        points.append(row)
    return points


def build(path):
    points = load_points()
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.2), sharex=True, sharey=True)
    colors = ("#0072B2", "#B45309", "#008260", "#8B4781")
    for ax, case in zip(axes.flat, CASES, strict=True):
        rows = [r for r in points if r["case"] == case]
        ages = [r["age"] for r in rows]
        for key, name, color, marker, line, width in (
            ("primary", "Cocoon 2.5pV (primary)", colors[0], "o", "-", 2.2),
            ("comparison", "Cocoon 4pV (comparison)", colors[1], "s", "--", 1.25),
            ("cocoon", "Cocoon ΔE", colors[2], "^", "-", 1.55),
        ):
            ax.plot(ages, [r[key] for r in rows], color=color, marker=marker, markersize=5.2,
                    markerfacecolor="white" if key == "comparison" else color, linewidth=width, ls=line,
                    zorder=3 if key == "primary" else 2, label=name)
        ambient, = [r for r in rows if "ambient" in r]
        ax.plot(ambient["age"], ambient["ambient"], linestyle="none", marker="D", markersize=9,
                markeredgewidth=1.5, markeredgecolor=colors[3], markerfacecolor="none", zorder=4,
                label=r"Ambient $\Delta E_{\rm thermal}$ in R100 (30 Myr)")
        ax.set(title=case, xlim=(7.5, 52.5), ylim=(-.25, 1.75), xticks=AGES, yticks=(-.25, 0, .5, 1, 1.5))
        ax.axhline(1, color=".38", ls=":", lw=1.0, zorder=0)
        ax.axhline(0, color=".6", lw=.7, zorder=0)
        ax.grid(axis="y", color=".90", lw=.65)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.suptitle("Cocoon enthalpy and regional energy change", fontsize=15, y=.985)
    fig.supylabel(r"Energy / net injector gas delivery ($D_{\rm gas}$)", x=.018, y=.58, fontsize=11)
    fig.supxlabel("Actual simulation age (Myr)", y=.107, fontsize=11)
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .015), ncols=2, frameon=False, fontsize=9)
    fig.subplots_adjust(left=.09, right=.985, top=.895, bottom=.185, wspace=.085, hspace=.22)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=215, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    build(parser.parse_args().out)
