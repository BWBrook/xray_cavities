"""Tabulate selected ages and plot each moving sphere's outward transport and membership correction."""
import argparse
import csv
import gzip
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from summarise_aperture_transport import CASES, APERTURES


CASES_IN_FIGURE = ("C-HI", "C-LO", "G-HI", "G-LO")
COLOURS = {"R100": "#146481", "R300": "#aa4b10"}
ASSET = Path(__file__).resolve().parents[2] / "docs/science/assets/aperture_transport_2026-11-26"


def load(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as source:
        return list(csv.DictReader(source))


def ratio(row, key):
    return float(row["cumulative_" + key + "_erg"]) / float(row["cumulative_delivered_gas_erg"])


def shell_balance(case, balances):
    rows = []
    for end in range(1, CASES[case] + 1):
        def pair(method, rule):
            return [balances[name, end, method, rule] for name in APERTURES]
        outer, inner = pair("centered_primitives", "symmetric_fixed")
        row = {"case": case, "end_index": end, "actual_age_myr": outer["end_age_myr"],
               "R100_kpc": outer["end_radius_kpc"], "R300_kpc": inner["end_radius_kpc"],
               "both_geometrically_complete": all(r["end_geometry_complete"] == "True" for r in (outer, inner))}
        for prefix in ("", "cumulative_"):
            def difference(key, outer=outer, inner=inner):
                field = prefix + key + "_erg"
                return float(outer[field]) - float(inner[field])
            delivery = float(outer[prefix + "delivered_gas_erg"])
            stock = difference("stock_change")
            motion = difference("membership_correction")
            net_in = -difference("total_energy_outward")
            residual = difference("aperture_residual")
            if abs(math.fsum((stock, -motion, -net_in, -residual))) > 1e-11 * delivery:
                raise ValueError("Difference of the two aperture balances fails to reproduce the shell change")
            row[prefix + "delivered_gas_erg"] = delivery
            for key, value in (("shell_stock_change", stock), ("change_from_membership", motion),
                               ("net_transport_into_shell", net_in), ("residual_difference", residual)):
                row[prefix + key + "_erg"] = value
                row[prefix + key + "_over_delivery"] = value / delivery
            for method, rule in (("donor_cell_primitives", "symmetric_fixed"), ("centered_primitives", "old_fixed"),
                                 ("centered_primitives", "new_fixed"), ("centered_primitives", "moving_endpoints")):
                large, small = pair(method, rule)
                row[prefix + method + "_" + rule + "_net_into_shell_over_delivery"] = -difference("total_energy_outward", large, small) / delivery
        rows.append(row)
    return rows


def write_rows(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create(tables, output):
    primary = load(tables / "primary_balances.csv")
    if len(primary) != 2*sum(CASES.values()):
        raise ValueError("Incomplete signed primary interval series")
    selected, shells = [], []
    fig, axes = plt.subplots(2, 4, figsize=(13.7, 6), sharex=True, sharey="row", layout="constrained")
    for column, case in enumerate(CASES_IN_FIGURE):
        all_balances = load(tables / f"balances_{case}.csv.gz")
        balances = {(r["aperture"], int(r["end_index"]), r["face_method"], r["integration_rule"]): r for r in all_balances}
        if len(balances) != len(all_balances):
            raise ValueError("Repeated integration estimate")
        shells.extend(shell_balance(case, balances))
        components = {(r["aperture"], int(r["end_index"])): r for r in load(tables / f"transport_{case}.csv.gz")
                      if (r["face_method"], r["integration_rule"], r["boundary_part"])
                      == ("centered_primitives", "symmetric_fixed", "total")}
        for name in APERTURES:
            rows = sorted((r for r in primary if r["case"] == case and r["aperture"] == name), key=lambda r:int(r["end_index"]))
            if [int(r["end_index"]) for r in rows] != list(range(1, CASES[case] + 1)):
                raise ValueError("Gap in registered transport history")
            dates = [float(r["end_age_myr"]) for r in rows]
            last_complete = max(int(r["end_index"]) for r in rows if r["end_geometry_complete"] == "True")
            if name == "R100":
                fixed = [[100 * ratio(balances[name, int(r["end_index"]), "centered_primitives", rule], "total_energy_outward")
                          for r in rows] for rule in ("old_fixed", "new_fixed")]
                axes[0, column].fill_between(dates, *fixed, color=COLOURS[name], alpha=.15, linewidth=0)
            for i, key in enumerate(("total_energy_outward", "membership_correction")):
                ax = axes[i, column]
                series = [100*ratio(r, key) for r in rows]
                ax.plot(dates, series, color=COLOURS[name], lw=1.9, ls="-" if name == "R100" else "--")
            for r in rows:
                end = int(r["end_index"])
                if end not in (10, 20, 30, 40, last_complete, CASES[case]):
                    continue
                comp = components[name, end]
                d = float(r["cumulative_delivered_gas_erg"])
                def amt(key):
                    return float(r["cumulative_" + key + "_erg"])
                def at(method, rule, quantity="total_energy_outward"):
                    return ratio(balances[name, end, method, rule], quantity)
                selected.append(dict(case=case, index=end, actual_age_myr=r["end_age_myr"], aperture=name,
                                     radius_kpc=r["end_radius_kpc"], geometrically_complete=r["end_geometry_complete"],
                                     intersects_box_faces=r["end_domain_contact"], cocoon_contacts_box=r["end_cocoon_contacts_domain"],
                                     cumulative_delivered_gas_erg=d, stored_change_over_delivery=amt("stock_change")/d,
                                     membership_over_delivery=amt("membership_correction")/d,
                                     outward_over_delivery=amt("total_energy_outward")/d,
                                     outward_minus_membership_over_delivery=(amt("total_energy_outward")-amt("membership_correction"))/d,
                                     outward_on_box_faces_over_delivery=amt("box_energy_outward")/d,
                                     thermal_advection_over_delivery=float(comp["cumulative_thermal_advective_outward_erg"])/d,
                                     pressure_work_over_delivery=float(comp["cumulative_pressure_work_outward_erg"])/d,
                                     kinetic_outward_over_delivery=float(comp["cumulative_kinetic_outward_erg"])/d,
                                     gravitational_outward_over_delivery=float(comp["cumulative_gravitational_outward_erg"])/d,
                                     aperture_residual_over_delivery=amt("aperture_residual")/d,
                                     full_grid_residual_over_delivery=amt("archived_grid_residual")/d,
                                     residual_difference_over_delivery=amt("aperture_minus_grid_residual")/d,
                                     outward_donor_over_delivery=at("donor_cell_primitives","symmetric_fixed"),
                                     outward_on_old_radii_over_delivery=at("centered_primitives","old_fixed"),
                                     outward_on_new_radii_over_delivery=at("centered_primitives","new_fixed"),
                                     outward_moving_endpoints_over_delivery=at("centered_primitives","moving_endpoints"),
                                     residual_donor_over_delivery=at("donor_cell_primitives", "symmetric_fixed", "aperture_residual"),
                                     residual_old_fixed_over_delivery=at("centered_primitives", "old_fixed", "aperture_residual"),
                                     residual_new_fixed_over_delivery=at("centered_primitives", "new_fixed", "aperture_residual"),
                                     residual_moving_endpoints_over_delivery=at("centered_primitives", "moving_endpoints", "aperture_residual")))
        clipped = [float(r["end_age_myr"]) for r in primary if r["case"] == case and r["end_geometry_complete"] == "False"]
        for ax in axes[:,column]:
            ax.axhline(0, color="#707070", lw=.7, zorder=0)
            ax.grid(axis="y", color="#ddd", lw=.65)
            ax.spines[["top","right"]].set_visible(False)
            ax.tick_params(labelsize=9)
            if clipped:
                ax.axvspan(min(clipped), max(clipped), color="#c8c4bc", alpha=.3, lw=0, zorder=0)
        axes[0,column].set_title(case)
        axes[1,column].set_xlabel("Age (Myr)")
        axes[1,column].set_xticks([0,10,20,30,40,50])
    axes[0,0].set_ylabel("Net energy carried outward\n(% of cumulative delivery)")
    axes[1,0].set_ylabel("Energy change from aperture motion\n(% of cumulative delivery)")
    fig.legend(handles=[Line2D([0],[0], color=COLOURS["R100"], lw=2, label="R100"),
                        Line2D([0],[0], color=COLOURS["R300"], lw=2, ls="--", label="R300"),
                        Patch(facecolor=COLOURS["R100"], alpha=.15, label="R100 using earlier or later radius"),
                        Patch(color="#c8c4bc", alpha=.5, label="Sphere extends beyond grid")],
               loc="outside lower center", ncols=4, frameon=False)
    output.mkdir(parents=True,exist_ok=True)
    fig.savefig(output/"cumulative_aperture_transport.png",dpi=170,facecolor="white")
    plt.close(fig)
    write_rows(output / "selected_age_transport.csv", selected)
    write_rows(output / "shell_balance.csv", shells)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables",type=Path,default=ASSET/"tables")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    create(args.tables,args.output)
