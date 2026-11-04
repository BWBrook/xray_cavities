#!/usr/bin/env python3
"""Compare paired no-jet boundary contrasts with the recorded BND-02 prediction.

Reads each run's per-update ``paired_nojet_budget.csv`` (six face rows per
state; whole-grid totals repeated on each row; cumulative face transport is
positive outward). For every state it reports the outflow-minus-reflective
contrasts in mass, hydrodynamic energy H and potential energy P, the share
of each explained by the face-transport contrast, and the ratio to the
prediction in ``docs/science/paired_nojet_boundary_prediction_2026-11-02.md``.

Verdict rules, fixed on 4 November 2026 before any 50-Myr ledger was read:
refuted if the final mass contrast is below the floor (1e43 g cluster,
5e41 g group), if the power-law growth exponent fitted to states at
t >= 5 Myr lies outside [1.6, 2.4], or if face transport explains less than
90% of the final mass or H contrast. Otherwise supported; "within factor 2"
and "within 30%" describe the final mass and H+P ratios to prediction.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

PREDICTION = {
    "cluster_002003": {"mass_g": 4.86e43, "h_erg": 3.4e59, "hp_erg": 7.2e59, "floor_g": 1e43},
    "group_002031": {"mass_g": 2.38e42, "h_erg": 4.2e57, "hp_erg": 1.3e58, "floor_g": 5e41},
}
T_REF_MYR = 50.0


def states(path: Path) -> dict[int, list[dict]]:
    out = defaultdict(list)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            out[int(row["state_step"])].append(row)
    return dict(out)


def totals(rows: list[dict]) -> dict[str, float]:
    first = rows[0]
    return {
        "time_myr": float(first["time_myr"]),
        "mass": float(first["mass_g"]),
        "h": float(first["hydro_total_erg"]),
        "p": float(first["potential_erg"]),
        "in_mass": -sum(float(r["cumulative_mass_net_g"]) for r in rows),
        "in_h": -sum(float(r["cumulative_hydro_net_erg"]) for r in rows),
        "in_p": -sum(float(r["cumulative_potential_net_erg"]) for r in rows),
    }


def contrasts(root: Path, case: str) -> list[dict]:
    runs = {bc: states(root / f"{case}_{bc}" / "paired_nojet_budget.csv") for bc in ("outflow", "reflective")}
    common = sorted(set(runs["outflow"]) & set(runs["reflective"]))
    base = {bc: totals(runs[bc][common[0]]) for bc in runs}
    pred = PREDICTION[case]
    out = []
    for step in common[1:]:
        now = {bc: totals(runs[bc][step]) for bc in runs}
        t = now["outflow"]["time_myr"]
        if abs(t - now["reflective"]["time_myr"]) > 1e-9 * max(t, 1.0):
            raise ValueError(f"{case} state {step}: pair ages differ")
        d = {k: (now["outflow"][k] - base["outflow"][k]) - (now["reflective"][k] - base["reflective"][k])
             for k in ("mass", "h", "p", "in_mass", "in_h", "in_p")}
        scale = (t / T_REF_MYR) ** 2
        out.append({
            "case": case,
            "state_step": step,
            "time_myr": t,
            "contrast_mass_g": d["mass"],
            "contrast_h_erg": d["h"],
            "contrast_p_erg": d["p"],
            "contrast_hp_erg": d["h"] + d["p"],
            "transport_explains_mass": d["in_mass"] / d["mass"],
            "transport_explains_h": d["in_h"] / d["h"],
            "transport_explains_hp": (d["in_h"] + d["in_p"]) / (d["h"] + d["p"]),
            "mass_over_t2_prediction": d["mass"] / (pred["mass_g"] * scale),
            "h_over_t2_prediction": d["h"] / (pred["h_erg"] * scale),
            "hp_over_t2_prediction": (d["h"] + d["p"]) / (pred["hp_erg"] * scale),
        })
    return out


def growth_exponent(rows: list[dict]) -> float:
    pts = [(math.log(r["time_myr"]), math.log(r["contrast_mass_g"])) for r in rows
           if r["time_myr"] >= 5.0 and r["contrast_mass_g"] > 0]
    if len(pts) < 2:
        return math.nan
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    return sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)


def verdict(case: str, rows: list[dict]) -> dict:
    final = rows[-1]
    exponent = growth_exponent(rows)
    reasons = []
    if final["time_myr"] >= T_REF_MYR * 0.99:
        if final["contrast_mass_g"] < PREDICTION[case]["floor_g"]:
            reasons.append("final mass contrast below floor")
        if not math.isnan(exponent) and not 1.6 <= exponent <= 2.4:
            reasons.append(f"growth exponent {exponent:.2f} outside [1.6, 2.4]")
    if min(final["transport_explains_mass"], final["transport_explains_h"]) < 0.9:
        reasons.append("face transport explains < 90% of the contrast")
    ratios = (final["mass_over_t2_prediction"], final["hp_over_t2_prediction"])
    return {
        "case": case,
        "final_time_myr": final["time_myr"],
        "complete_to_50_myr": final["time_myr"] >= T_REF_MYR * 0.99,
        "growth_exponent_t_ge_5myr": exponent,
        "final_mass_ratio": ratios[0],
        "final_hp_ratio": ratios[1],
        "within_factor_2": all(0.5 <= r <= 2 for r in ratios),
        "within_30_percent": all(1 / 1.3 <= r <= 1.3 for r in ratios),
        "refutations": reasons,
        "verdict": "refuted" if reasons else ("supported" if final["time_myr"] >= T_REF_MYR * 0.99 else "incomplete"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="directory holding <case>_<boundary>/paired_nojet_budget.csv")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows, verdicts = [], []
    for case in PREDICTION:
        if (args.root / f"{case}_outflow").exists():
            case_rows = contrasts(args.root, case)
            rows += case_rows
            verdicts.append(verdict(case, case_rows))
    with (args.output / "paired_contrasts.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "verdict.json").write_text(json.dumps(verdicts, indent=2) + "\n")
    print(json.dumps(verdicts, indent=2))


if __name__ == "__main__":
    main()
