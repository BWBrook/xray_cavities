"""Compare saved-time injector fluxes with the independently archived growth in tagged mass."""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from capture_injector_states import sha
from measure_injector_faces import FIELDS, METHODS, REGIONS, measure
from measure_q031_fluxes import parse_pluto_parameters
from pluto_h5_level3_ambient_extract import UNIT_DENSITY_CGS as D, UNIT_LENGTH_CM as L, UNIT_VELOCITY_CMS as V
from snapshot_energy import SECONDS_PER_MYR, load_environment


def write_table(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def divide(a, b):
    return a/b if b else None


def reduce_case(request_dir, result_dir, reference, domain=None, require_outer=False):
    request = json.loads((request_dir / "request.json").read_text())
    case = request["case"]
    for name, expected in request["static_sha256"].items():
        if sha(request_dir / name) != expected:
            raise ValueError(f"Static input mismatch: {case}/{name}")
    atmosphere = load_environment(request_dir / "atmosphere.csv")
    params = parse_pluto_parameters(request_dir / "pluto.ini")
    power = 2*params["JET_PWR"]
    labelled_mass_rate = 2*power / (params["JET_SPD"]*V)**2
    mass_scale = D*L**2*V / labelled_mass_rate
    power_scale = D*L**2*V**3 / power
    request_hash = sha(request_dir / "request.json")
    rows = {}
    tagged = {}
    energy = {}
    outer = {}
    for receipt_path in sorted((result_dir / case / "patch").glob("snapshot_*.json")):
        receipt = json.loads(receipt_path.read_text())
        i = receipt["index"]
        item = request["history"][i]
        patch_path = receipt_path.with_name(f"patch_{i:04d}.npz")
        if (receipt["case"] != case or receipt["mode"] != "patch" or receipt["request_sha256"] != request_hash
                or receipt["fixed_receipt_sha256"] != item["fixed_receipt_sha256"]
                or receipt["historical_native_sha256"] != item["native"]["sha256"]
                or receipt["time_code"] != item["time_code"] or receipt["age_myr"] != item["age_myr"]
                or receipt["patch_sha256"] != sha(patch_path)):
            raise ValueError(f"Invalid patch receipt: {receipt_path}")
        with np.load(patch_path, allow_pickle=False) as archive:
            centres = tuple(archive[d].astype(float) for d in "xyz")
            edges = tuple(archive[d+"_edges"].astype(float) for d in "xyz")
            patch = {name: archive[name] for name in FIELDS}
        z, y, x = np.ix_(*centres[::-1])
        dz, dy, dx = np.ix_(*(np.diff(a) for a in edges[::-1]))
        sphere = x*x + y*y + z*z <= .75**2
        rho = patch["rho"].astype(float)
        volume = dx*dy*dz
        tagged[i] = float(np.sum(rho*patch["tr1"]*volume, where=sphere))*D*L**3
        speed2 = sum(patch[name].astype(float)**2 for name in ("vx1", "vx2", "vx3"))
        phi = atmosphere.potential_at_radius(np.sqrt(x*x+y*y+z*z)*L) / V**2
        density_e = 1.5*patch["prs"].astype(float) + rho*(.5*speed2 + phi)
        energy[i] = float(np.sum(density_e*volume, where=sphere))*D*L**3*V**2
        outer_path = result_dir / case / "outer" / receipt_path.name
        if outer_path.is_file():
            o = json.loads(outer_path.read_text())
            if (o["mode"] != "outer" or any(o[k] != receipt[k] for k in
                    ("case", "index", "time_code", "request_sha256", "analysis_sha256", "historical_native_sha256"))):
                raise ValueError(f"Outer-scan receipt differs at {case}/{i}")
            outer[i] = (o["tracer"]["whole_grid"]["raw_tagged_mass_g"],
                        sum(f["tagged_net_outward_g_s"] for f in o["face_tracer"].values()))
        elif require_outer:
            raise ValueError(f"Missing outer scan at {case}/{i}")
        measured = measure(patch, centres, edges,
                           potential=lambda r: atmosphere.potential_at_radius(r*L) / V**2)
        for r in measured:
            region, method = r["region"], r["method"]
            if r["n_cells"] != {"net": 14328, "cap": 504, "stationary": 13824}[region]:
                raise ValueError(f"Unexpected geometric mask at {case}/{i}/{region}")
            rows[i, method, region] = dict(
                case=case, index=i, age_myr=item["age_myr"], method=method, region=region,
                mass_over_label=r["mass"]*mass_scale, tracer_over_label=r["tracer_mass"]*mass_scale,
                gas_energy_over_label=r["gas_energy"]*power_scale, potential_energy_over_label=r["potential_energy"]*power_scale,
                total_energy_over_label=r["gas_plus_potential"]*power_scale,
                gas_energy_out_over_label=r["gas_energy_out"]*power_scale,
                gas_energy_in_over_label=r["gas_energy_in"]*power_scale,
                specific_gas_energy_on_mass_out_faces_erg_g=divide(r["gas_energy_on_mass_out_faces"]*V**2, r["mass_out"]),
                share_out_energy_on_return_wave_faces=divide(r["return_wave_gas_energy_out"], r["gas_energy_out"]),
                share_out_energy_hot_exterior_sets_wave=divide(r["hotter_outside_sets_wave_gas_energy_out"], r["gas_energy_out"]),
                share_out_tracer_hot_exterior_sets_wave=divide(r["hotter_outside_sets_wave_tracer_mass_out"], r["tracer_mass_out"]),
                face_count=r["n_faces"], shock_fallback_faces=r["n_hll_fallback"],
                flagged_tracer_max_abs_error=r["tracer_max_abs_error"], flagged_speed_min=r["speed_min"],
                flagged_speed_max=r["speed_max"], flagged_transverse_speed_max=r["transverse_speed_max"],
                patch_sha256=receipt["patch_sha256"])
    if not tagged:
        raise ValueError(f"No captured patches for {case}")
    intervals = []
    for i in sorted(tagged):
        if i-1 not in tagged:
            continue
        ref = reference[case, i]
        elapsed = (request["history"][i]["age_myr"]-request["history"][i-1]["age_myr"])*SECONDS_PER_MYR
        label = float(ref["labelled_mass_g"])
        active = (min(request["history"][i]["age_myr"], params["JET_END_TIME"])
                  - min(request["history"][i-1]["age_myr"], params["JET_END_TIME"]))*SECONDS_PER_MYR
        if not math.isclose(label, labelled_mass_rate*active, rel_tol=2e-12):
            raise ValueError(f"Reference mass and native interval differ at {case}/{i}")
        duration_factor = labelled_mass_rate*elapsed/label
        flagged_change = (tagged[i]-tagged[i-1])/label
        energy_label = power*active
        flagged_energy_change = (energy[i]-energy[i-1])/energy_label
        for method in METHODS:
            for rule, w in (("left", 0.), ("trapezoid", .5), ("right", 1.)):
                def interp(region, field):
                    return ((1-w)*rows[i-1, method, region][field] + w*rows[i, method, region][field])*duration_factor

                cap, still, net = [interp(region, "tracer_over_label") for region in REGIONS]
                if abs(cap+still-net) > 1.e-12*max(1., abs(net)):
                    raise ValueError("Component tracer fluxes do not close")
                observed = float(ref["delta_over_label"])
                exact_observed = net_out = closure = None
                if i-1 in outer and i in outer:
                    exact_observed = (outer[i][0] - outer[i-1][0])/label
                    net_out = ((1-w)*outer[i-1][1] + w*outer[i][1])*elapsed/label
                    closure = net + flagged_change - net_out - exact_observed
                delivery = interp("net", "total_energy_over_label")
                balances = {}
                for boundary in ("outer_active_cell", "linear_to_boundary_face"):
                    source = None if domain is None else domain.get((case, i, boundary, rule))
                    unavailable = case == "G-HI" and i == 47 and boundary == "linear_to_boundary_face" and rule != "left"
                    if domain is not None and (source is None) != unavailable:
                        raise ValueError(f"Domain balance coverage differs at {case}/{i}/{boundary}/{rule}")
                    balances["outside_flagged_sphere_"+boundary] = (source/energy_label - delivery - flagged_energy_change
                                                                     if source is not None else None)
                intervals.append(dict(case=case, start_index=i-1, end_index=i, method=method, rule=rule,
                                      cap_tracer=cap, stationary_tracer=still, net_tracer=net,
                                      flagged_tagged_storage_change=flagged_change, observed_tracer=observed,
                                      predicted_minus_observed_before_outer_correction=net+flagged_change-observed,
                                      native_volume_observed_tracer=exact_observed, outer_face_net_tracer=net_out,
                                      tracer_closure_with_native_volume_and_outer_flux=closure,
                                      cap_gas=interp("cap", "gas_energy_over_label"),
                                      stationary_gas=interp("stationary", "gas_energy_over_label"),
                                      net_gas=interp("net", "gas_energy_over_label"),
                                      net_gas_plus_potential=delivery, flagged_total_energy_change=flagged_energy_change,
                                      **balances))
    return list(rows.values()), intervals


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("requests", "results", "tagged_mass_intervals", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--cases", nargs="+", default=["C-HI", "C-LO", "G-HI", "G-LO"])
    parser.add_argument("--domain-balances", type=Path, required=True)
    parser.add_argument("--require-outer", action="store_true")
    args = parser.parse_args()
    with args.tagged_mass_intervals.open() as stream:
        reference = {(r["case"], int(r["end_index"])): r for r in csv.DictReader(stream)}
    with args.domain_balances.open() as stream:
        rule_names = {"left_rectangle": "left", "right_rectangle": "right", "trapezoid": "trapezoid"}
        domain = {(r["case"], int(r["end_index"]), r["method"], rule_names[r["rule"]]):
                  float(r["inferred_energy_source_erg"]) for r in csv.DictReader(stream)
                  if r["surface"] == "domain_boundary"}
    outputs, pairs = [], []
    for case in args.cases:
        new_rows, new_intervals = reduce_case(args.requests / case, args.results, reference, domain, args.require_outer)
        outputs.extend(new_rows)
        pairs.extend(new_intervals)
    args.output.mkdir(parents=True, exist_ok=True)
    write_table(args.output / "injector_snapshot_rates.csv", outputs)
    if pairs:
        write_table(args.output / "injector_interval_balances.csv", pairs)
