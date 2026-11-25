"""Recompute the G-HI/20 headline from published per-lobe areas."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets/ghi20_front_constraint_2026-11-25"
AREAS = ("false_before_kpc2", "false_removed_kpc2", "false_after_kpc2", "true_before_kpc2",
         "true_lost_kpc2", "true_after_kpc2", "lobe_area_kpc2")


def read_scores(assets):
    receipt = json.loads((assets / "receipt.json").read_text())
    for name, digest in receipt["products"].items():
        with (assets / name).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != digest:
                raise ValueError(f"{name} differs from its measurement receipt")
    with (assets / "area_scores.csv").open(newline="") as f:
        return list(csv.DictReader(f))


def totals(rows):
    counts = {k: sum(float(r[k]) for r in rows) for k in AREAS}
    for time in ("before", "after"):
        true, false = (counts[f"{name}_{time}_kpc2"] for name in ("true", "false"))
        counts["purity_" + time] = true / (true + false) if true + false else None
        counts["completeness_" + time] = true / counts["lobe_area_kpc2"]
    false = counts["false_before_kpc2"]
    counts["fraction_false_removed"] = counts["false_removed_kpc2"] / false if false else None
    return counts


def figure(views, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.25), sharey=True, layout="constrained")
    for ax, title in zip(axes, ("Selected area outside the lobe", "Full projected lobe area"), strict=True):
        ax.set_title(title, loc="left", fontsize=12, fontweight="medium")
        ax.set_xlabel("Projected area (thousand kpc²)")
        ax.set_xlim(0, 12.25)
        ax.set_yticks((0, 1, 2), ["0°", "45°", "90°"])
        ax.set_ylim(2.5, -0.65)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="both", length=0)
        ax.xaxis.set_major_locator(MultipleLocator(2))
        ax.grid(axis="x", alpha=0.18)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Viewing azimuth")
    for i, row in enumerate(views):
        before, kept, removed, covered, full = (row[k] / 1000 for k in
            ("false_before_kpc2", "false_after_kpc2", "false_removed_kpc2", "true_after_kpc2", "lobe_area_kpc2"))
        labels = i == 0
        axes[0].barh(i, kept, height=0.4, color="#63421F", label="Still selected" if labels else None)
        axes[0].barh(i, removed, left=kept, height=0.4, color="#E6B675", label="Removed" if labels else None)
        axes[0].text(before + 0.12, i, f"{row['fraction_false_removed']:.1%} removed", va="center", fontsize=9)
        axes[1].barh(i, covered, height=0.4, color="#226961", label="Selected before and after" if labels else None)
        axes[1].barh(i, full - covered, left=covered, height=0.4, color="#DCE5E3", label="Missed" if labels else None)
        axes[1].text(covered / 2, i, f"{row['completeness_after']:.1%}", ha="center", va="center", color="white", fontsize=9)
    for ax in axes:
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.26), ncols=2, frameon=False, fontsize=8)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()
    rows = read_scores(args.assets)
    primary = [r for r in rows if r["candidate"] == "original_radial" and r["front"] == "primary"
               and r["hemisphere"] in ("negative_z", "positive_z")]
    if {(int(r["view_deg"]), r["hemisphere"]) for r in primary} != {
            (v, side) for v in (0, 45, 90) for side in ("negative_z", "positive_z")} or len(primary) != 6:
        raise ValueError("The pooled three-view result requires six scored hemispheres")
    views = [totals([r for r in primary if int(r["view_deg"]) == v]) for v in (0, 45, 90)]
    print(json.dumps({"by_azimuth": dict(zip((0, 45, 90), views, strict=True)), "pooled": totals(primary)}, indent=2))
    if args.figure:
        figure(views, args.figure)
