"""Compare the signed solver correction and lobe enthalpy gain over the same two Myr."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
LOW = ASSETS / "low_power_entropy_result_2026-11-23"


def paired_values():
    high_grid = json.loads((ASSETS/"entropy_restart_review_2026-11-23/summary.json").read_text())
    high_lobes = json.loads((ASSETS/"entropy_lobe_review_2026-11-23/summary.json").read_text())
    vals = {}
    for case in ("G-HI", "C-HI"):
        lobe = high_lobes[case]
        vals[case] = (high_grid[case+"/ON"]["counter_net"], lobe["enthalpy_gain_10_to_12_per_delivered_on"],
                      lobe["enthalpy_gain_10_to_12_per_delivered_off"])
    with (LOW/"on_counter_windows.csv").open() as f:
        grid = {r["case"]: float(r["entropy_net_over_label"]) for r in csv.DictReader(f)
                if r["start_index"] == "10" and r["end_index"] == "30"}
    with (LOW/"lobe_paired_effects.csv").open() as f:
        for r in csv.DictReader(f):
            if float(r["tracer_cut"]) == .001:
                vals[r["case"]] = (grid[r["case"]], float(r["gain_over_post_seed_gas_on"]),
                                   float(r["gain_over_post_seed_gas_off"]))
    return vals


def plot():
    vals = paired_values()
    fig, (grid, lobe) = plt.subplots(1, 2, figsize=(8.5, 3.35), gridspec_kw={"width_ratios": [1, 1.5]})
    fig.subplots_adjust(left=.13, right=.985, top=.76, bottom=.20, wspace=.29)
    cases = ("C-HI", "C-LO", "G-HI", "G-LO")
    for y, case in enumerate(cases):
        net, on, off = (100*x for x in vals[case])
        grid.barh(y, net, height=.36, color="#3e6270", zorder=2)
        grid.text(net + (.28 if net >= 0 else -.28), y, f"{net:+.1f}%", va="center",
                  ha="left" if net >= 0 else "right", fontsize=9)
        for offset, value, color in ((-.17, on, "#aeb8bd"), (.17, off, "#226578")):
            lobe.barh(y+offset, value, height=.25, color=color, zorder=2)
            lobe.text(value+1.6, y+offset, f"{value:.1f}%", va="center", fontsize=8.5)
    for ax in (grid, lobe):
        ax.set_ylim(3.65, -.65)
        ax.grid(axis="x", color="#e0e5e6", linewidth=.7, zorder=0)
        ax.spines[["left","right","top"]].set_visible(False)
        ax.spines["bottom"].set_color("#7c898e")
        ax.tick_params(axis="both", length=0, labelsize=9, pad=4)
        ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    grid.set_yticks(range(len(cases)), cases)
    lobe.set_yticks([])
    grid.set_xlim(-15, 7)
    grid.set_xticks([-10, -5, 0, 5])
    lobe.set_xlim(0, 105)
    lobe.set_xticks([0, 25, 50, 75, 100])
    grid.axvline(0, color="#506167", lw=.8, zorder=1)
    grid.set_title("Energy added or removed\nby the update", fontsize=11, loc="left", pad=14)
    lobe.set_title("Lobe enthalpy gained", fontsize=11, loc="left", pad=30)
    lobe.legend([plt.Rectangle((0, 0), 1, 1, color=c) for c in ("#aeb8bd", "#226578")],
                ["Update on", "Update off"], frameon=False, fontsize=9, ncol=2,
                loc="lower left", bbox_to_anchor=(0, .97), borderaxespad=0, handlelength=1.2)
    grid.set_xlabel("Share of labelled jet input", fontsize=9.5, labelpad=7)
    lobe.set_xlabel("Share of gas energy delivered", fontsize=9.5, labelpad=7)
    fig.savefig(LOW/"four_case_entropy_response.png", dpi=205, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    plot()
