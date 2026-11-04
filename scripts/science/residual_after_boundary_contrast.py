"""Whole-grid production excess left after subtracting the coarse boundary contrast.

Reads the production whole-grid closure table (2026-10-21) and the paired
no-jet outflow-minus-reflective H+P contrasts (2026-11-04), and writes the
residual excess per case and age, in units of the case's injected energy.
"""
import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHOLE_GRID = ROOT / "docs/science/assets/whole_grid_energy_closure_2026-10-21/whole_grid_energy_comparison.csv"
CONTRASTS = ROOT / "docs/science/assets/paired_boundary_comparison_2026-11-04/paired_contrasts.csv"
ATMOSPHERE = {"C": "cluster_002003", "G": "group_002031"}
# Production whole-grid mass gain at 50 Myr (prediction note, Q-029 ledgers).
PRODUCTION_MASS_50 = {"cluster_002003": 4.86e43, "group_002031": 2.38e42}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    contrast, mass50 = {}, {}
    with CONTRASTS.open() as handle:
        for row in csv.DictReader(handle):
            t = float(row["time_myr"])
            contrast[(row["case"], t)] = float(row["contrast_hp_erg"])
            if t == 50.0:
                mass50[row["case"]] = float(row["contrast_mass_g"])
    out = []
    with WHOLE_GRID.open() as handle:
        for row in csv.DictReader(handle):
            atm = ATMOSPHERE[row["case"][0]]
            t_actual = float(row["actual_time_myr"])
            t_nom = round(t_actual / 10) * 10.0
            if (atm, t_nom) not in contrast:
                continue
            e_inj = float(row["injected_energy_erg"])
            excess = float(row["delta_total_over_injected"]) - 1.0
            bnd = contrast[(atm, t_nom)] * (t_actual / t_nom) ** 2 / e_inj
            scale = PRODUCTION_MASS_50[atm] / mass50[atm]
            out.append({
                "case": row["case"], "time_myr": f"{t_actual:.4f}",
                "excess_over_injected": f"{excess:.5f}",
                "coarse_boundary_hp_over_injected": f"{bnd:.5f}",
                "residual_unscaled": f"{excess - bnd:+.5f}",
                "production_to_coarse_mass_ratio": f"{scale:.5f}",
                "residual_mass_scaled": f"{excess - bnd * scale:+.5f}",
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    for row in out:
        print(row)


if __name__ == "__main__":
    main()
