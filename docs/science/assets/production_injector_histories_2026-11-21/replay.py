"""Recompute the full-history diagnostic from the published PBS tables."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
CASES = {"C-HI": 50, "C-LO": 50, "G-HI": 47, "G-LO": 50}
PRIMARY = "linear_snapshot_flags"
OUTER = "outer_active_cell"


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def check_equal(a, b):
    if not math.isclose(float(a), float(b), rel_tol=2.e-11, abs_tol=2.e-12):
        raise ValueError(f"Independent estimates differ: {a} versus {b}")


def load_tables():
    receipt = json.loads((HERE / "verification.json").read_text())
    archive = HERE / "history_tables.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != receipt["public_zip_sha256"]:
        raise ValueError("Unexpected numerical archive")
    tables = {}
    with zipfile.ZipFile(archive) as bundle:
        for name, expected in receipt["public_member_sha256"].items():
            data = bundle.read(name)
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Checksum differs for {name}")
            tables[name] = list(csv.DictReader(io.StringIO(data.decode())))
    return tables


def compare(tables):
    gravity = tables["comparison/flagged_sphere_gravity_intervals.csv"]
    outer = tables["comparison/native_outer_snapshot_summary.csv"]
    signed = tables["comparison/native_signed_tracer_transport.csv"]
    canonical = {(r["case"], int(r["end_index"])): r for r in gravity
                 if (r["injector_method"], r["boundary_method"], r["rule"]) == (PRIMARY, OUTER, "trapezoid")}
    if len(gravity) != 4720 or len(canonical) != 197:
        raise ValueError("Incomplete gravity comparison")
    budgets = read_csv(HERE / "case_energy_budgets.csv")
    for case, last in CASES.items():
        energy = {int(r["end_index"]): r for r in tables[f"native/summary/{case}/injector_interval_balances.csv"]
                  if r["method"] == PRIMARY and r["rule"] == "trapezoid"}
        if set(energy) != set(range(1, last + 1)):
            raise ValueError(f"Incomplete energy history for {case}")
        for reported in (r for r in budgets if r["case"] == case):
            start, end = int(reported["start_index"]), int(reported["end_index"])
            labels = {i: float(canonical[case, i]["labelled_energy_erg"]) for i in range(start+1, end+1)}
            denom = math.fsum(labels.values())
            check_equal(denom, reported["labelled_energy_erg"])
            for field in ("cap_gas", "stationary_gas", "net_gas", "native_volume_observed_tracer",
                          "outside_flagged_sphere_outer_active_cell", "outside_flagged_sphere_linear_to_boundary_face"):
                if any(energy[i][field] == "" for i in labels):
                    if reported[field] != "":
                        raise ValueError(f"Filled an unavailable {field} at {case}/{end}")
                    continue
                check_equal(math.fsum(label * float(energy[i][field]) for i, label in labels.items())/denom, reported[field])
        support = [r for r in outer if r["case"] == case and int(r["index"]) <= 30]
        if len(support) != 31 or any(float(r[k]) != 0 for r in support for k in
                                     ("shell_raw_tagged_mass_g", "tagged_inward_g_s", "tagged_outward_g_s")):
            raise ValueError(f"Thirty-Myr boundary inventory differs for {case}")
        print(f"{case}: minimum raw tracer clearance through 30 Myr "
              f"{min(float(r['min_margin_raw_positive_kpc']) for r in support):.2f} kpc")
    direction_file = HERE / "face_direction_history.csv"
    c_receipt = json.loads((HERE / "c_solver_receipt.json").read_text())
    if hashlib.sha256(direction_file.read_bytes()).hexdigest() != c_receipt["output_sha256"][direction_file.name]:
        raise ValueError("Independent cap flux table differs")
    evolved = [r for r in read_csv(direction_file) if int(r["index"]) > 0]
    if len(evolved) != 197:
        raise ValueError("Incomplete post-startup cap history")
    for r in evolved:
        check_equal(float(r["axial_tagged_mass_over_label"]) + float(r["lateral_tagged_mass_over_label"]), r["cap_tagged_mass_over_label"])
    shares = [float(r["lateral_flux_over_cap_excess"]) for r in evolved]
    print(f"Lateral share of excess cap mass after startup: {100*min(shares):.2f}–{100*max(shares):.2f}%")
    ghi = [r for r in gravity if r["case"] == "G-HI"]
    residuals = [float(r["outside_total_residual_over_label"]) for r in ghi]
    if len(ghi) != 1120 or max(residuals) >= 0:
        raise ValueError("G-HI exterior result differs")
    fraction = max(abs(float(r["direct_minus_continuity_work_over_label"])/x) for r,x in zip(ghi, residuals))
    g = canonical["G-HI",30]
    print(f"G-HI 29–30 Myr: direct work {100*float(g['direct_net_work_over_label']):.3f}%, "
          f"continuity work {100*float(g['potential_continuity_work_over_label']):.3f}%, "
          f"exterior residual {100*float(g['outside_total_residual_over_label']):.3f}% of label")
    print(f"Largest gravity-estimate discrepancy relative to the G-HI residual: {100*fraction:.3f}%")
    leaking = [r for r in signed if r["rule"] == "trapezoid" and float(r["tagged_net_outward_over_label"]) != 0]
    if len(leaking) != 1 or (leaking[0]["case"], leaking[0]["end_index"]) != ("G-HI", "47"):
        raise ValueError("Sampled boundary transport differs")
    print(f"G-HI 46–47 Myr: signed trapezoidal loss {100*float(leaking[0]['tagged_net_outward_over_label']):.5f}% of interval label")
    return canonical, outer


def plot(canonical, outer, path):
    import matplotlib.pyplot as plt

    fig, (work, mass) = plt.subplots(1, 2, figsize=(10.5, 4.4), layout="constrained")
    annual = [canonical["G-HI", i] for i in range(1, 48)]
    ages = [float(r["end_myr"]) for r in annual]
    for field, label, color in (("outside_total_residual_over_label", "Exterior energy residual", "#9a3d26"),
                                ("direct_net_work_over_label", "Direct gravitational work", "#205777"),
                                ("direct_minus_continuity_work_over_label", "Direct minus inferred work", "#287653")):
        work.plot(ages, [100*float(r[field]) for r in annual], label=label, color=color, lw=2)
    work.axhline(0, lw=.6, color=".4", zorder=0)
    work.set(title="G-HI energy outside the injector", xlabel="Interval end (Myr)", ylabel="% of labelled interval energy")
    work.legend(frameon=False, fontsize=9)
    mass.axhspan(0, 20, color="#ece8e1", zorder=0)
    for (case, _), color, line in zip(CASES.items(), ("#9a3d26","#9a3d26","#205777","#205777"), ("-","--","-","--")):
        rows = sorted((r for r in outer if r["case"] == case), key=lambda r: int(r["index"]))
        mass.plot([float(r["age_myr"]) for r in rows], [float(r["min_margin_raw_positive_kpc"]) for r in rows],
                  label=case, color=color, linestyle=line, lw=2)
    mass.set(title="Distance of any jet tracer from a face", xlabel="Saved age (Myr)", ylabel="Minimum clearance (kpc)", ylim=(-5, None))
    mass.text(1, 7, "Outer 20 kpc", color=".32", fontsize=9)
    mass.legend(frameon=False, ncol=2, fontsize=9)
    for ax in (work, mass):
        ax.spines[["top","right"]].set_visible(False)
    fig.savefig(path, dpi=175)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figure", type=Path)
    args = parser.parse_args()
    primary, boundary = compare(load_tables())
    if args.figure:
        plot(primary, boundary, args.figure)
