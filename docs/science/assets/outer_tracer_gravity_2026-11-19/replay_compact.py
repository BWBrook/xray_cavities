"""Reproduce four-case interval potential-energy and tracer-clearance diagnostics."""
import argparse
from contextlib import nullcontext
import csv
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import zipfile


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
RULES = {"left_rectangle": 0., "trapezoid": .5, "right_rectangle": 1.}
BOUNDARY = ("outer_active_cell", "linear_to_boundary_face")
NOZZLE = ("centered_primitives", "donor_cell_primitives")
PADS = (1, 2, 4)
SECONDS_PER_MYR = 3.15576e13


def index_table(path, names):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {tuple(int(row[key]) if key in ("index", "snapshot_index", "end_index") else row[key] for key in names): row
              for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate keys in {path.name}")
    return result


def save(path, rows, fields=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields if fields is not None else rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tracer_product(tracer_dir, rates):
    mass = index_table(tracer_dir/"tagged_mass_history.csv", ("case", "index"))
    bounds = index_table(tracer_dir/"sampled_tracer_boundary_integral_bounds.csv", ("case", "snapshot_index", "quadrature"))
    result = []
    for (case, i), row in mass.items():
        flux = rates[case, i, "domain_boundary", "outer_active_cell"]
        br = [bounds[case, i, rule] for rule in RULES]
        age = float(row["age_myr"])
        if float(flux["age_myr"]) != age or not all(float(b["t"]) == age for b in br):
            raise ValueError("tracer age disagrees with the energy or boundary record")
        result.append(dict(case=case, index=i, age_myr=age,
                      above_0p001_nearest_face_kpc=float(row["thresholded_lobe_face_margin_kpc"]),
                      gross_all_gas_outflow_across_six_faces_g_s=float(flux["mass_outflow_g_s"]),
                      sampled_cumulative_signed_lower_over_label=min(float(b["cumulative_lower_over_label"]) for b in br) if i else None,
                      sampled_cumulative_signed_upper_over_label=max(float(b["cumulative_upper_over_label"]) for b in br) if i else None))
    if len(result) != 201 or sum(r["index"] <= 30 for r in result) != 124:
        raise ValueError("incomplete tracer history")
    return result


def surface_balance(case, idx, surface, method, rule, stock, rates, checks):
    state = [stock[case, i, surface] for i in (idx-1, idx)]
    dt = (float(state[1]["age_myr"]) - float(state[0]["age_myr"])) * SECONDS_PER_MYR
    if dt <= 0.:
        raise ValueError("nonpositive interval")
    w = RULES[rule]
    samples = [(rates[(case, i, surface, method)], weight) for i, weight in ((idx-1, 1.-w), (idx, w)) if weight]
    fields = {}
    for name, stored, transported in (("potential", "gravitational_erg", "potential_flux_outward_erg_s"),
                                     ("total", "total_energy_erg", "total_energy_flux_outward_erg_s"),
                                     ("mass", "mass_g", "mass_flux_outward_g_s")):
        fields[name+"_storage"] = float(state[1][stored]) - float(state[0][stored])
        fields[name+"_transport"] = dt*sum(weight*float(row[transported]) for row, weight in samples)
        fields[name] = fields[name+"_storage"] + fields[name+"_transport"]
    expected = float(checks[case, idx, surface, method, rule]["inferred_energy_source_erg"])
    if not math.isclose(fields["total"], expected, rel_tol=1.e-11, abs_tol=1.e-12*dt*(2.e45 if case.endswith("HI") else 2.e43)):
        raise ValueError(f"published total source failed to replay for {(case,idx,surface,method,rule)}")
    return fields


def gravity_products(stock, rates, checks):
    records = []
    for case in CASES:
        last = 47 if case == "G-HI" else 50
        for idx in range(1, last+1):
            times = [float(stock[case, i, "domain_boundary"]["age_myr"]) for i in (idx-1, idx)]
            power = 2.e45 if case.endswith("HI") else 2.e43
            labelled = power*(min(times[1],50.) - min(times[0],50.))*SECONDS_PER_MYR
            surfaces = {}
            for pad, method, face, rule in product(PADS, NOZZLE, BOUNDARY, RULES):
                if case == "G-HI" and idx == 47 and face == "linear_to_boundary_face" and rule != "left_rectangle":
                    continue
                box = f"nozzle_control_p{pad}"
                for key in ((box,method,rule), ("domain_boundary",face,rule)):
                    if key not in surfaces:
                        surfaces[key] = surface_balance(case,idx,*key,stock,rates,checks)
                a, b = surfaces["domain_boundary",face,rule], surfaces[box,method,rule]
                def outside(field):
                    return a[field] - b[field]
                work = -(outside("potential_storage") + outside("potential_transport"))
                records.append(dict(case=case,start_index=idx-1,end_index=idx,start_myr=times[0],end_myr=times[1],
                    padding=pad,nozzle_method=method,boundary_method=face,rule=rule,labelled_energy_erg=labelled,
                    outside_delta_potential_over_label=outside("potential_storage")/labelled,
                    outside_potential_transport_over_label=outside("potential_transport")/labelled,
                    inferred_gravity_work_over_label=work/labelled, outside_total_residual_over_label=outside("total")/labelled,
                    outside_net_gas_source_g=outside("mass")))
    if len(records) != 7080:
        raise ValueError("unexpected number of matched complete interval reconstructions")
    grouped = {}
    for row in records:
        grouped.setdefault((row["case"],row["end_index"]),[]).append(row)
    result = []
    for (case, idx), group in grouped.items():
        canonical, = [r for r in group if (r["padding"], r["nozzle_method"], r["boundary_method"], r["rule"]) ==
                                           (2, NOZZLE[0], BOUNDARY[0], "trapezoid")]
        item = {k: canonical[k] for k in ("case", "start_index", "end_index", "start_myr", "end_myr", "labelled_energy_erg")}
        item["n_scenarios"] = len(group)
        for field in ("outside_delta_potential_over_label", "outside_potential_transport_over_label",
                      "inferred_gravity_work_over_label", "outside_total_residual_over_label", "outside_net_gas_source_g"):
            item["p2_centre_active_trapezoid_"+field] = canonical[field]
        for field in ("inferred_gravity_work_over_label", "outside_total_residual_over_label"):
            item["methods_min_"+field] = min(row[field] for row in group)
            item["methods_max_"+field] = max(row[field] for row in group)
        result.append(item)
    return records, result


def read_native(root, clearances):
    known = {(r["case"], r["index"]):r for r in clearances}
    rows, epochs = [], {}
    for path in sorted(root.glob("*/outer/snapshot_*.json")):
        data = json.loads(path.read_text())
        case, idx = data["case"], int(data["index"])
        key = case, idx
        if (key in epochs or path.parent.parent.name != case or path.name != f"snapshot_{idx:04d}.json"
                or key not in known or not math.isclose(data["age_myr"], known[key]["age_myr"], rel_tol=0., abs_tol=1.e-8)):
            raise ValueError(f"native snapshot identity or age disagrees: {path}")
        tracer = data["tracer"]
        if not math.isclose(tracer["min_margin_above_threshold_kpc"], known[key]["above_0p001_nearest_face_kpc"], rel_tol=0., abs_tol=1.e-6):
            raise ValueError(f"thresholded native clearance differs: {key}")
        faces = data["face_tracer"]
        if faces.keys() != {axis+"_"+side for axis in "xyz" for side in ("negative","positive")}:
            raise ValueError(f"missing native face in {key}")
        all_gas_out = sum(f["all_gas_outward_g_s"] for f in faces.values())
        if not math.isclose(all_gas_out, known[key]["gross_all_gas_outflow_across_six_faces_g_s"], rel_tol=1.e-10):
            raise ValueError(f"gross outward gas disagrees with retained fluxes: {key}")
        flow = {name:sum(f[name] for f in faces.values()) for name in ("tagged_inward_g_s","tagged_outward_g_s","tagged_net_outward_g_s")}
        row = dict(case=case,index=idx,age_myr=data["age_myr"],min_margin_raw_positive_kpc=tracer["min_margin_raw_positive_kpc"],
                   min_margin_above_threshold_kpc=tracer["min_margin_above_threshold_kpc"],
                   shell_raw_tagged_mass_g=tracer["boundary_shell"]["raw_tagged_mass_g"],
                   shell_dilute_tagged_mass_g=tracer["boundary_shell"]["dilute_tagged_mass_g"],
                   max_raw_tracer_at_face=max(f["raw_max"] for f in faces.values()),**flow)
        rows.append(row)
        epochs[key] = (row, data["gravity"])
    if not epochs:
        raise ValueError("no matching native snapshots")
    return epochs, rows


NATIVE_WORK = ("case", "start_index", "end_index", "padding", "nozzle_method", "boundary_method", "rule",
               "direct_inward_motion_work_over_label", "direct_outward_motion_work_over_label",
               "direct_net_work_over_label", "potential_continuity_work_over_label", "outside_total_residual_over_label",
               "direct_minus_continuity_work_over_label", "hydro_balance_minus_direct_work_over_label")


def check_work_partition(gravity, pad, epoch):
    fields = ("inward_motion_erg_s", "outward_motion_erg_s", "net_erg_s")
    whole, inside, outside = (gravity[key] for key in ("whole_grid", f"inside_p{pad}", f"outside_p{pad}"))
    for region in (whole, inside, outside):
        if not all(math.isfinite(region[f]) for f in fields):
            raise ValueError(f"nonfinite native gravity work at {epoch}, padding {pad}")
    for region in (whole, inside):
        inward, outward, net = (region[f] for f in fields)
        if abs(math.fsum((inward, outward, -net))) > 1.e-10 * (abs(inward) + abs(outward)):
            raise ValueError(f"native inward and outward work do not sum at {epoch}, padding {pad}")
    for field in fields:
        a, b, c = whole[field], inside[field], outside[field]
        # The producer subtracts before the cgs conversion and rounds all three stored powers independently.
        tolerance = 4 * math.ulp(max(abs(a), abs(b), abs(c)))
        if abs(math.fsum((a, -b, -c))) > tolerance:
            raise ValueError(f"native exterior {field} differs from whole minus inside at {epoch}, padding {pad}")


def join_native_work(epochs, scenarios):
    pads = {scenario["padding"] for scenario in scenarios}
    for epoch, (_, gravity) in epochs.items():
        if gravity:
            for pad in pads:
                check_work_partition(gravity, pad, epoch)
    rows = []
    for scenario in scenarios:
        case, a, b = scenario["case"], scenario["start_index"], scenario["end_index"]
        left, right = epochs.get((case,a)), epochs.get((case,b))
        if not left or not right or not left[1] or not right[1]:
            continue
        weight = RULES[scenario["rule"]]
        region = "outside_p"+str(scenario["padding"])
        scale = (scenario["end_myr"] - scenario["start_myr"])*SECONDS_PER_MYR/scenario["labelled_energy_erg"]
        direct = [scale*((1.-weight)*left[1][region][f] + weight*right[1][region][f])
                  for f in ("inward_motion_erg_s","outward_motion_erg_s","net_erg_s")]
        proxy = scenario["inferred_gravity_work_over_label"]
        residual = scenario["outside_total_residual_over_label"]
        gap = direct[-1] - proxy
        rows.append(dict(zip(NATIVE_WORK, [case,a,b,scenario["padding"],scenario["nozzle_method"],
                         scenario["boundary_method"],scenario["rule"],*direct,proxy,residual,gap,residual-gap],strict=True)))
    return rows


NATIVE_MASS = ("case","start_index","end_index","rule","labelled_mass_g",
               "tagged_inward_over_label","tagged_outward_over_label","tagged_net_outward_over_label",
               "cumulative_tagged_inward_over_label","cumulative_tagged_outward_over_label","cumulative_tagged_net_outward_over_label")


def join_native_mass(epochs, intervals, limits):
    rows, cumulative = [], {}
    for interval in intervals:
        case, a, b = interval["case"],interval["start_index"],interval["end_index"]
        if (case,a) not in epochs or (case,b) not in epochs:
            continue
        left, right = epochs[case,a][0],epochs[case,b][0]
        dt = (right["age_myr"] - left["age_myr"]) * SECONDS_PER_MYR
        label = 2*interval["labelled_energy_erg"]/(.1*2.99792458e10)**2
        for rule, weight in RULES.items():
            masses = [dt*((1.-weight)*left[k]+weight*right[k]) for k in
                      ("tagged_inward_g_s", "tagged_outward_g_s", "tagged_net_outward_g_s")]
            bound = limits[case,b,rule]
            if (masses[2] < float(bound["interval_signed_tracer_transport_lower_g"])-1.e-12*label or
                    masses[2] > float(bound["interval_signed_tracer_transport_upper_g"])+1.e-12*label):
                raise ValueError(f"native tracer transport outside older bounds: {(case,b,rule)}")
            previous = ([0.]*4 if a == 0 else cumulative.get((case,a,rule)))
            cfrac = [None]*3
            if previous is not None:
                cumulative[case,b,rule] = updated = [p+m for p,m in zip(previous,[label,*masses],strict=True)]
                cfrac = [n/updated[0] for n in updated[1:]]
            rows.append(dict(zip(NATIVE_MASS,[case,a,b,rule,label,*[v/label for v in masses],*cfrac],strict=True)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    parser.add_argument("--compact",type=Path,default=here/"compact_inputs.zip",help="compact input zip or directory")
    parser.add_argument("--tracer",type=Path,default=here.parent/"tracer_mass_budget_2026-11-19",help="existing public tracer tables")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--all-scenarios",type=Path,help="optional full 7,080-row gravity table")
    parser.add_argument("--native-root",type=Path,help="optional root with CASE/outer/snapshot_NNNN.json")
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with (zipfile.ZipFile(args.compact) if args.compact.is_file() else nullcontext()) as archive:
        root = zipfile.Path(archive) if archive else args.compact
        if archive:
            for name, expected in json.loads((root/"provenance.json").read_text())["compact_csv_sha256"].items():
                if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
                    raise ValueError(f"archived input hash differs for {name}")
        stock = index_table(root/"stock.csv", ("case","index","surface"))
        rates = index_table(root/"rates.csv", ("case","index","surface","method"))
        checks = index_table(root/"source_check.csv", ("case","end_index","surface","method","rule"))
    result = tracer_product(args.tracer, rates)
    scenarios, summary = gravity_products(stock,rates,checks)
    save(args.output/"saved_tracer_clearance.csv",result)
    save(args.output/"potential_work_intervals.csv",summary)
    if args.all_scenarios:
        save(args.all_scenarios,scenarios)
    if args.native_root:
        native, native_stocks = read_native(args.native_root,result)
        bounds = index_table(args.tracer/"sampled_tracer_boundary_integral_bounds.csv", ("case","snapshot_index","quadrature"))
        save(args.output/"native_outer_snapshot_summary.csv",native_stocks)
        save(args.output/"native_gravity_comparison.csv",join_native_work(native,scenarios),NATIVE_WORK)
        save(args.output/"native_signed_tracer_transport.csv",join_native_mass(native,summary,bounds),NATIVE_MASS)


if __name__ == "__main__":
    main()
