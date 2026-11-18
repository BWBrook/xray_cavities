"""Compare 36 matched cumulative source-balance scenarios at each saved age."""
import argparse
import csv
import hashlib
import itertools
import math
from pathlib import Path

import matplotlib.pyplot as plt

# Three complete histories and the verified 0–46 prefix from the failed G-HI job.
HISTORIES = {
    "C-HI": (50, "4ab40fc4f0ebef8b59e12cae43ff230b89c5377a414bfc50290093dbddc53232"),
    "C-LO": (50, "0a2dc0c6386ef819506bddd0629e2de3432c051dd2c4a378c2cfd1511d800b3a"),
    "G-HI": (46, "bfd99488dd79617b3183123bed08f20ac52bc3f37aecc5ffd6400867ea17f352"),
    "G-LO": (50, "4ee094ef4c711009300808d8fe2ae79754543f6eb4ddb4a918d64c2a1215c0ff"),
}
FACES = ("outer_active_cell", "linear_to_boundary_face")
SCENARIOS = set(itertools.product(
    FACES, ("left_rectangle", "trapezoid", "right_rectangle"),
    ("centered_primitives", "donor_cell_primitives"), ("1", "2", "4"),
))
REGIONS = ("domain", "nozzle", "outside_nozzle")


def summarize(path):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    case = rows[0]["case"]
    count, digest = HISTORIES[case]
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f"{case}: input differs from the reviewed source balances")
    by_age = {}
    for row in rows:
        by_age.setdefault(float(row["interval_end_myr"]), []).append(row)
    if len(by_age) != count:
        raise ValueError(f"{case}: incomplete age selection")
    summary = []
    previous = 0.0
    for index, (age, records) in enumerate(sorted(by_age.items()), 1):
        keys = {(r["domain_reconstruction"], r["temporal_quadrature"],
                 r["nozzle_reconstruction"], r["nozzle_padding_cells"]) for r in records}
        if len(records) != len(SCENARIOS) or keys != SCENARIOS:
            raise ValueError(f"{case}/{index}: missing or duplicate scenario")
        power = 2e45 if case.endswith("HI") else 2e43
        label = power * min(age, 50.0) * (365.25 * 86400 * 1e6)
        for row in records:
            if float(row["interval_start_myr"]) != previous or row["case"] != case:
                raise ValueError(f"{case}/{index}: inconsistent case or interval")
            if not math.isclose(float(row["nominal_configured_bipolar_energy_erg"]), label, rel_tol=1e-12):
                raise ValueError(f"{case}/{index}: inconsistent normalization")
            for region in REGIONS:
                row[region] = float(row[f"{region}_cumulative_inferred_internal_energy_source_erg"]) / label
            if not math.isclose(row["outside_nozzle"], row["domain"] - row["nozzle"], abs_tol=1e-12):
                raise ValueError(f"{case}/{index}: outside source balance disagrees with constituent volumes")
        previous = age
        for face, quadrature in sorted({(r["domain_reconstruction"], r["temporal_quadrature"]) for r in records}):
            group = [r for r in records if (r["domain_reconstruction"], r["temporal_quadrature"]) == (face, quadrature)]
            result = dict(case=case, index=index, age_myr=age, face=face, quadrature=quadrature,
                          label_erg=label, whole_grid_over_label=group[0]["domain"])
            for region in ("nozzle", "outside_nozzle"):
                values = [r[region] for r in group]
                result[region + "_min"] = min(values)
                result[region + "_max"] = max(values)
            summary.append(result)
    return case, summary


def plot(histories, path):
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.4), sharex=True, layout="constrained")
    for ax, case in zip(axes.flat, HISTORIES):
        rows = [r for r in histories[case] if r["index"] >= 10]
        ages = sorted({r["age_myr"] for r in rows})
        for face, color, name in zip(FACES, ("#176f95", "#d26729"), ("Outer active cell", "Linear to face")):
            series = [r for r in rows if r["face"] == face]
            lower = [min(r["outside_nozzle_min"] for r in series if r["age_myr"] == age) for age in ages]
            upper = [max(r["outside_nozzle_max"] for r in series if r["age_myr"] == age) for age in ages]
            ax.fill_between(ages, lower, upper, color=color, alpha=0.23, label=name)
            ax.plot(ages, lower, color=color, linewidth=1)
            ax.plot(ages, upper, color=color, linewidth=1)
        ax.axhline(0, color="0.22", lw=1, ls=":")
        ax.set_title(case + ("  ·  partial through 46 Myr" if case == "G-HI" else ""))
        if case != "C-LO":
            ax.set_ylim(-0.15, 0.16)
        ax.grid(axis="y", alpha=.2)
        ax.spines[["right", "top"]].set_visible(False)
    axes[1, 0].legend(frameon=False, fontsize=9, loc="upper right")
    fig.supxlabel("Age (Myr)")
    fig.supylabel("Cumulative outside-nozzle balance / labelled input")
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tables", nargs=4, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    histories = dict(summarize(p) for p in args.tables)
    if histories.keys() != HISTORIES.keys():
        raise ValueError("Expected the four reviewed cases")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "scenario_histories.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=histories["C-HI"][0], lineterminator="\n")
        writer.writeheader()
        for case in HISTORIES:
            writer.writerows(histories[case])
    plot(histories, args.output / "flux_histories.png")


if __name__ == "__main__":
    main()
