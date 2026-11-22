"""Plot the twenty saved-interval energy budgets for each paired entropy restart."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets/entropy_restart_result_2026-11-22"
CASES = {"G-HI": "High-power group jet", "C-HI": "High-power cluster jet"}
ON_COLOR = "#174d71"
STAGE_COLOR = "#ac461c"
OFF_COLOR = "#277767"
FIRST_COLOR = "#e9e7e0"


def read_intervals(source):
    columns = ("case", "arm", "start_index", "end_index", "start_age_myr", "end_age_myr",
               "injector_method", "outer_boundary", "time_rule", "exterior", "native_stage")
    data = np.genfromtxt(source, delimiter=",", names=True, usecols=columns, dtype=None,
                         encoding="utf-8", ndmin=1).view(np.recarray)
    keys = zip(data.case, data.arm, data.start_index, data.end_index)
    expected = {(case, arm, i, i + 1) for case in CASES for arm in ("ON", "OFF") for i in range(10, 30)}
    if len(data) != len(expected) or set(keys) != expected:
        raise ValueError("expected twenty distinct consecutive intervals for each case and arm")
    if not ((data.injector_method == "linear_snapshot_flags") & (data.outer_boundary == "outer_active_cell")
            & (data.time_rule == "trapezoid")).all():
        raise ValueError("input contains a non-primary energy budget")
    values = (data.start_age_myr, data.end_age_myr, data.exterior, data.native_stage)
    if not np.isfinite(values).all() or (data.end_age_myr <= data.start_age_myr).any():
        raise ValueError("invalid interval endpoint or energy value")
    return data[np.argsort(data.end_index)]


def midpoints(rows):
    return (rows.start_age_myr + rows.end_age_myr) / 2


def draw_off(ax, values):
    return ax.plot(midpoints(values), 100 * values.exterior, color=OFF_COLOR, linewidth=1.35,
                   linestyle="--", marker="s", markersize=2.8, label="OFF exterior residual")[0]


def style_axis(ax):
    ax.set_axisbelow(True)
    ax.grid(axis="y", linewidth=0.55, color="#e2e5e7")
    ax.axhline(0, color="#77838a", linewidth=0.8, zorder=1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#849098")
    ax.tick_params(colors="#34434c", labelsize=8.5)


def plot(source, output):
    data = read_intervals(source)
    on = data[data.arm == "ON"]
    off = data[data.arm == "OFF"]
    off_peak = np.abs(off.exterior).max()
    zoom_off = 0 < off_peak < np.abs((on.exterior, on.native_stage)).max() / 4
    rows = 2 if zoom_off else 1
    fig, axes = plt.subplots(rows, 2, squeeze=False, sharey="row", sharex=True,
                             figsize=(9.0, 4.85 if zoom_off else 3.8),
                             height_ratios=[3.0, 1.0] if zoom_off else [1.0])
    fig.subplots_adjust(left=0.095, right=0.98, top=0.78 if zoom_off else 0.71,
                        bottom=0.125, hspace=0.32, wspace=0.10)
    fig.text(0.095, 0.968, "Energy balance outside the injector", ha="left", va="top",
             fontsize=14, fontweight="bold", color="#1d2c36")
    for col, (case, description) in enumerate(CASES.items()):
        a = on[on.case == case]
        b = off[off.case == case]
        start = min(a.start_age_myr[0], b.start_age_myr[0])
        first_end = max(a.end_age_myr[0], b.end_age_myr[0])
        for axis in axes[:, col]:
            first = axis.axvspan(start, first_end, color=FIRST_COLOR, linewidth=0, zorder=0,
                                 label="First restart interval")
            style_axis(axis)
        ax = axes[0, col]
        exterior, = ax.plot(midpoints(a), 100 * a.exterior, color=ON_COLOR, linewidth=2.0,
                            label="ON exterior residual", zorder=3)
        stage, = ax.plot(midpoints(a), 100 * a.native_stage, linestyle="none", marker="o",
                         markerfacecolor="none", markeredgecolor=STAGE_COLOR, markeredgewidth=1.25,
                         markersize=5.2, label="ON native entropy update", zorder=4)
        off_line = draw_off(ax, b)
        ax.set_title(f"{case}   {description}", fontsize=10.5, fontweight="bold", loc="left", pad=7)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 2.5, 5, 10]))
        if zoom_off:
            detail = axes[1, col]
            draw_off(detail, b)
            detail.set_title("OFF residual, expanded scale", fontsize=8.5, loc="left", pad=4,
                             color=OFF_COLOR)
            detail.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 2.5, 5, 10]))
        if col == 0:
            fig.legend(handles=[exterior, stage, off_line, first], ncol=4, frameon=False,
                       bbox_to_anchor=(0.095, 0.895 if zoom_off else 0.885), loc="upper left",
                       borderaxespad=0, handlelength=2.2, columnspacing=1.5, fontsize=8.7)
    axes[0, 0].set_xlim(data.start_age_myr.min() - 0.015, data.end_age_myr.max() + 0.015)
    axes[0, 0].set_xticks([10, 10.5, 11, 11.5, 12])
    fig.supylabel("Energy (% of labelled input per interval)", x=0.018, fontsize=10)
    fig.supxlabel("Simulation age (Myr) at interval midpoint", y=0.027, fontsize=10)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ASSETS / "primary_intervals.csv")
    parser.add_argument("--output", type=Path, default=ASSETS / "paired_intervals.png")
    args = parser.parse_args()
    plot(args.input, args.output)
