"""Plot current whole-cocoon enthalpy and regional stock changes per measured injector delivery."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from four_case_energy_partition import PUBLISHED, checked, csv_rows
from four_case_shock_partition import OUT as DOWNSTREAM, SIDES, keyed, match
from restate_native_delivery import CASES, ROOT


AGES = (10, 20, 30, 40, 50)
OUTPUT = ROOT / "manuscript/figures/native_delivered_energy_partition.png"
ENERGY_RECEIPT = "e0ea49059f1dbb85089d342d35a958e56d86f333231d77795507293043e48593"
FRONT_RECEIPT = "848acaf62d27d885b2fb6d3b109c2b28d5acf30c6f5863c7cb77f0d83fd1bea4"


def load_points():
    energy = json.loads(checked(PUBLISHED / "verification.json", ENERGY_RECEIPT))
    front = json.loads(checked(DOWNSTREAM / "summary.json", FRONT_RECEIPT))

    def table(directory, hashes, name):
        return csv_rows(checked(directory / name, hashes[name]))

    energy_hashes, front_hashes = energy["products_sha256"], front["product_sha256"]
    keys = ("case", "snapshot_index")
    snapshots = keyed(table(PUBLISHED, energy_hashes, "snapshots.csv"), keys)
    cocoon = keyed((r for r in table(PUBLISHED, energy_hashes, "box_components.csv")
                    if r["aperture"] == "whole_grid" and r["region"] == "cocoon"), keys)
    downstream = keyed((r for r in table(DOWNSTREAM, front_hashes, "downstream_components.csv")
                        if r["side"] == "bipolar_total" and float(r["threshold_factor"]) == 1), keys)
    axial = keyed(table(DOWNSTREAM, front_hashes, "axial_evidence.csv"), (*keys, "side"))
    selected = [(c, i) for c, last in CASES.items() for i in AGES if i <= last]
    if set(downstream) != set(selected):
        raise ValueError("Downstream row inventory differs from the 19 selected case-ages")

    points, bilateral, censored = [], set(), set()
    for case, i in selected:
        snap, region, candidate = (t[case, i] for t in (snapshots, cocoon, downstream))
        age = float(snap["actual_age_myr"])
        gas = float(snap["cumulative_net_gas_delivery_erg"])
        match(float(region["cumulative_net_gas_delivery_erg"]), gas, "cocoon denominator")
        match(float(candidate["cumulative_bipolar_gas_delivery_erg"]), gas, "front denominator")
        sides = [axial[case, i, s] for s in SIDES]
        if gas <= 0 or any(float(r["actual_age_myr"]) != age for r in (region, candidate, *sides)):
            raise ValueError(f"Invalid supply or unmatched output time at {case}/{i}")
        row = {"case": case, "index": i, "age": age}
        for key, r, erg, ratio in (
            ("primary", snap, "native_lobe_2p5pV_erg", "native_lobe_2p5pV_over_delivery"),
            ("comparison", snap, "native_lobe_4pV_erg", "native_lobe_4pV_over_delivery"),
            ("cocoon", region, "total_delta_erg", "total_over_delivery"),
        ):
            row[key] = float(r[erg]) / gas
            match(row[key], float(r[ratio]), ratio)
        match(row["comparison"], 1.6*row["primary"], "enthalpy convention")
        if candidate["status"] == "unresolved_bilateral_gate":
            if candidate["downstream_total_change_erg"] or candidate["downstream_total_change_over_delivery"]:
                raise ValueError(f"A censored selection has a downstream value at {case}/{i}")
            row["downstream"], row["jumps"] = None, False
            censored.add((case, i))
        elif candidate["status"] == "quantitative_bilateral":
            row["downstream"] = float(candidate["downstream_total_change_erg"]) / gas
            match(row["downstream"], float(candidate["downstream_total_change_over_delivery"]), "downstream stock")
            jumps = [float(s["pressure_jump_ratio"]) > 1 and 1 < float(s["density_jump_ratio"]) < 4 for s in sides]
            if jumps != [s["both_jump_machs_defined"] == "True" for s in sides]:
                raise ValueError(f"Axial jump evidence disagrees at {case}/{i}")
            row["jumps"] = all(jumps)
            if row["jumps"]:
                bilateral.add(f"{case}/{i}")
        else:
            raise ValueError(f"Unrecognised bilateral status at {case}/{i}")
        points.append(row)
    if (bilateral != set(front["qualified_with_both_jump_inversions_on_both_sides"])
            or censored != {("C-LO", i) for i in (20, 30, 40, 50)}):
        raise ValueError("Jump classifications or censored case-ages differ from the source review")
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
        for jumps, face, name in (
            (True, colors[3], "Selected ambient ΔE, bilateral pressure and density jumps"),
            (False, "none", "Selected ambient ΔE, other candidate fronts"),
        ):
            valid = [r for r in rows if r["downstream"] is not None and r["jumps"] == jumps]
            ax.plot([r["age"] for r in valid], [r["downstream"] for r in valid], marker="D", linestyle="none",
                    markersize=7, markeredgewidth=1.45, markeredgecolor=colors[3], markerfacecolor=face, label=name)
        if case == "C-LO":
            ax.text(.04, .94, "No bilateral selection at 20–50 Myr", color=colors[3], fontsize=8,
                    transform=ax.transAxes, va="top")
        ax.set(title=case, xlim=(7.5, 52.5), ylim=(-.25, 1.75), xticks=AGES, yticks=(-.25, 0, .5, 1, 1.5))
        ax.axhline(1, color=".38", ls=":", lw=1.0, zorder=0)
        ax.axhline(0, color=".6", lw=.7, zorder=0)
        ax.grid(axis="y", color=".90", lw=.65)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.suptitle("Cocoon enthalpy and regional energy change", fontsize=15, y=.985)
    fig.supylabel(r"Energy / net injector gas delivery ($D_{\rm gas}$)", x=.018, y=.58, fontsize=11)
    fig.supxlabel("Actual simulation age (Myr)", y=.142, fontsize=11)
    fig.legend(handles[:3], labels[:3], loc="lower center", bbox_to_anchor=(.5, .070), ncols=3, frameon=False, fontsize=9)
    fig.legend(handles[3:], labels[3:], loc="lower center", bbox_to_anchor=(.5, .021), ncols=2, frameon=False, fontsize=9)
    fig.subplots_adjust(left=.09, right=.985, top=.895, bottom=.223, wspace=.085, hspace=.22)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=215, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    build(parser.parse_args().out)
