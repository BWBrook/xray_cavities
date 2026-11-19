"""Compare gravity work and total energy outside the discretely flagged injector sphere."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np

from measure_injector_faces import METHODS
from measure_outer_tracer_gravity import MASS_UNIT, SOLVER_LENGTH_CM, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS, WORK_FIELDS
from measure_q031_fluxes import parse_pluto_parameters
from snapshot_energy import SECONDS_PER_MYR, load_environment, sha256_file, write_rows


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
BOUNDARIES = ("outer_active_cell", "linear_to_boundary_face")
RULES = {"left": 0., "trapezoid": .5, "right": 1.}
ARCHIVE = Path(__file__).resolve().parents[2]/"docs/science/assets/outer_tracer_gravity_2026-11-19/compact_inputs.zip"


def read_domain(path):
    with zipfile.ZipFile(path) as bundle:
        digests = json.loads(bundle.read("provenance.json"))["compact_csv_sha256"]
        tables = []
        for name in ("stock.csv", "rates.csv", "source_check.csv"):
            data = bundle.read(name)
            if hashlib.sha256(data).hexdigest() != digests[name]:
                raise ValueError(f"unexpected archived {name} digest")
            tables.append([r for r in csv.DictReader(io.StringIO(data.decode())) if r["surface"] == "domain_boundary"])
    stock = {(r["case"], int(r["index"])): (float(r["age_myr"]), float(r["gravitational_erg"])) for r in tables[0]}
    flux = {(r["case"], int(r["index"]), r["method"]): float(r["potential_flux_outward_erg_s"]) for r in tables[1]}
    rules = {"left_rectangle":"left", "right_rectangle":"right", "trapezoid":"trapezoid"}
    total = {(r["case"], int(r["end_index"]), r["method"], rules[r["rule"]]): float(r["inferred_energy_source_erg"])
             for r in tables[2] if r["inferred_energy_source_erg"]}
    return stock, flux, total


def patch_terms(arrays, environment, radial_table, radius):
    axes = [arrays[axis].astype(float) for axis in "xyz"]
    nodes = [arrays[axis+"_edges"].astype(float) for axis in "xyz"]
    if any(not (e[0] < -radius < radius < e[-1]) or len(e) != len(a)+1
           or not np.all((e[:-1] < a) & (a < e[1:])) for e,a in zip(nodes,axes,strict=True)):
        raise ValueError("patch must enclose the entire flagged sphere on native edges")
    z,y,x = np.ix_(*axes[::-1])
    dz,dy,dx = np.ix_(*(np.diff(e) for e in nodes[::-1]))
    radius2 = x*x + y*y + z*z
    sphere = radius2 <= radius**2
    r = np.sqrt(radius2)
    if np.any(r == 0.) or r.max() > radial_table[-1,0]:
        raise ValueError("undefined or untabulated radial force at a patch centre")
    rho = arrays["rho"].astype(float)
    velocity = [arrays[name].astype(float) for name in ("vx1","vx2","vx3")]
    if (rho.shape != r.shape or any(v.shape != r.shape for v in velocity) or
            not np.all(np.isfinite(rho) & (rho > 0.)) or not all(np.all(np.isfinite(v)) for v in velocity)):
        raise ValueError("invalid patch density or velocity")
    gas_mass = rho*dx*dy*dz*MASS_UNIT
    v_radial = (velocity[0]*x+velocity[1]*y+velocity[2]*z)/r
    g = np.interp(r, radial_table[:,0], radial_table[:,1])
    work = gas_mass * v_radial * g * UNIT_VELOCITY_CMS
    flags = (v_radial < 0., v_radial > 0., np.ones(r.shape,dtype=bool))
    return (int(sphere.sum()), float(np.sum(gas_mass*environment.potential_at_radius(r*UNIT_LENGTH_CM),where=sphere)),
            [float(np.sum(work,where=sphere & f)) for f in flags], [float(np.sum(work,where=f)) for f in flags])


def snapshot_data(request_dir, results, case, indices, stock, require_outer):
    request_path = request_dir/"request.json"
    request_hash = sha256_file(request_path)
    request = json.loads(request_path.read_text())
    for name in ("atmosphere.csv","pluto.ini"):
        if sha256_file(request_dir/name) != request["static_sha256"][name]:
            raise ValueError(f"changed {case} {name}")
    params = parse_pluto_parameters(request_dir/"pluto.ini")
    if request["case"] != case or params["JET_INJECTION_HEIGHT"] != .75 or any(params[f"JET_X{d}O"] != 0 for d in (1,2,3)):
        raise ValueError(f"unexpected injection geometry for {case}")
    power = 2*params["JET_PWR"]
    environment = load_environment(request_dir/"atmosphere.csv")
    radial_table = np.loadtxt(request_dir/"atmosphere.csv",usecols=(0,5))
    radial_table[:,0] /= SOLVER_LENGTH_CM
    snapshots = {}
    for idx in sorted(indices):
        receipt_name = f"snapshot_{idx:04d}.json"
        patch_dir = results/case/"patch"
        receipt = json.loads((patch_dir/receipt_name).read_text())
        item = request["history"][idx]
        patch_path = patch_dir/f"patch_{idx:04d}.npz"
        if (receipt["mode"] != "patch" or receipt["request_sha256"] != request_hash or
                receipt["case"] != case or item["index"] != idx or receipt["index"] != idx or
                receipt["historical_native_sha256"] != item["native"]["sha256"] or
                receipt["fixed_receipt_sha256"] != item["fixed_receipt_sha256"] or
                receipt["patch_sha256"] != sha256_file(patch_path) or receipt["time_code"] != item["time_code"] or
                receipt["age_myr"] != item["age_myr"] or receipt["age_myr"] != stock[case,idx][0]):
            raise ValueError(f"patch identity differs at {case}/{idx}")
        with np.load(patch_path,allow_pickle=False) as patch:
            count, potential, flagged, padded = patch_terms(patch,environment,radial_table,.75)
        if count != 14328:
            raise ValueError(f"flagged-cell inventory differs at {case}/{idx}")
        outside = [None]*3
        outer_path = results/case/"outer"/receipt_name
        if outer_path.exists():
            outer = json.loads(outer_path.read_text())
            if outer["mode"] != "outer" or any(outer[key] != receipt[key] for key in
                    ("case","index","age_myr","time_code","request_sha256","analysis_sha256","fixed_receipt_sha256","historical_native_sha256")):
                raise ValueError(f"outer identity differs at {case}/{idx}")
            full = outer["gravity"]["whole_grid"]
            saved = outer["gravity"]["inside_p4"]
            scale = max(abs(padded[0])+abs(padded[1]),1.)
            if (not all(math.isfinite(full[key]) for key in WORK_FIELDS) or
                    not all(math.isclose(saved[key],value,rel_tol=0.,abs_tol=1.e-11*scale)
                            for key,value in zip(WORK_FIELDS,padded,strict=True))):
                raise ValueError(f"padded patch and outer p4 gravity disagree at {case}/{idx}")
            outside = [float(full[f])-v for f,v in zip(WORK_FIELDS,flagged,strict=True)]
            if not math.isclose(outside[2],outside[0]+outside[1],rel_tol=0.,
                                abs_tol=1.e-11*max(abs(full[WORK_FIELDS[0]])+abs(full[WORK_FIELDS[1]]),1.)):
                raise ValueError(f"signed radial work does not sum outside the sphere at {case}/{idx}")
        elif require_outer:
            raise ValueError(f"missing outer gravity at {case}/{idx}")
        snapshots[idx] = dict(case=case,index=idx,age_myr=item["age_myr"],flagged_cells=count,
                              patch_sha256=receipt["patch_sha256"],flagged_potential_erg=potential,
                              **{"flagged_"+k:v for k,v in zip(WORK_FIELDS,flagged,strict=True)},
                              **{"outside_"+k:v for k,v in zip(WORK_FIELDS,outside,strict=True)})
    return snapshots,power,params["JET_END_TIME"]


def signed_summary(base, case):
    if not (base/"injector_snapshot_rates.csv").exists():
        base = base/case
    with (base/"injector_snapshot_rates.csv").open(newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["case"] == case and r["region"] == "net"]
    rates = {(int(r["index"]),r["method"]):r for r in rows}
    with (base/"injector_interval_balances.csv").open(newline="") as handle:
        rows_i = [r for r in csv.DictReader(handle) if r["case"] == case]
    intervals = {(int(r["start_index"]),int(r["end_index"]),r["method"],r["rule"]):r for r in rows_i}
    idx = {i for i,m in rates}
    expected_i = {(i-1,i,m,t) for i in idx if i-1 in idx for m in METHODS for t in RULES}
    if (not rates or len(rates) != len(rows) or len(intervals) != len(rows_i) or
            set(rates) != {(i,m) for i in idx for m in METHODS} or set(intervals) != expected_i):
        raise ValueError(f"incomplete or duplicate signed summary for {case}")
    return rates,intervals,idx


def compare_interval(dphi_domain,dphi_flagged,domain_transport,injector_transport,label,residual,direct):
    exterior_work = -((dphi_domain-dphi_flagged)+(domain_transport-injector_transport))/label
    gap = None if direct is None else direct-exterior_work
    return dict(outside_delta_potential_over_label=(dphi_domain-dphi_flagged)/label,
                outside_potential_transport_over_label=(domain_transport-injector_transport)/label,
                potential_continuity_work_over_label=exterior_work,direct_net_work_over_label=direct,
                outside_total_residual_over_label=residual,direct_minus_continuity_work_over_label=gap,
                hydro_balance_minus_direct_work_over_label=None if gap is None else residual-gap)


def compare_case(requests,results,summary,domain,case,require_outer):
    stock,flux,source = domain
    rates,intervals,idx = signed_summary(summary,case)
    snapshots,power,jet_end = snapshot_data(requests/case,results,case,idx,stock,require_outer)
    for (i,_),r in rates.items():
        if r["patch_sha256"] != snapshots[i]["patch_sha256"] or float(r["age_myr"]) != snapshots[i]["age_myr"]:
            raise ValueError(f"signed flux input differs at {case}/{i}")
    comparisons = []
    for (a,b,method,rule),r in sorted(intervals.items()):
        left,right = snapshots[a],snapshots[b]
        dt = (right["age_myr"]-left["age_myr"])*SECONDS_PER_MYR
        label = (min(right["age_myr"],jet_end)-min(left["age_myr"],jet_end))*SECONDS_PER_MYR*power
        if dt <= 0. or label <= 0.:
            raise ValueError("invalid duration or labelled interval energy")
        w = RULES[rule]
        weights = [(a,1.-w),(b,w)]
        inj_transport = dt*power*sum(v*float(rates[i,method]["potential_energy_over_label"]) for i,v in weights)
        if not math.isclose(inj_transport/label,float(r["net_gas_plus_potential"])-float(r["net_gas"]),
                            rel_tol=0.,abs_tol=2.e-12):
            raise ValueError(f"integrated injector potential transport disagrees at {case}/{b}/{method}/{rule}")
        dphi_flag = right["flagged_potential_erg"]-left["flagged_potential_erg"]
        dphi_domain = stock[case,b][1]-stock[case,a][1]
        direct = [None]*3
        if left["outside_net_erg_s"] is not None and right["outside_net_erg_s"] is not None:
            direct = [dt/label*sum(v*snapshots[i]["outside_"+f] for i,v in weights) for f in WORK_FIELDS]
        for boundary in BOUNDARIES:
            residual_text = r["outside_flagged_sphere_"+boundary]
            key = case,b,boundary,rule
            if key not in source:
                if residual_text:
                    raise ValueError("unexpected invalid linear endpoint balance")
                continue
            residual = float(residual_text)
            original = source[key]/label-float(r["flagged_total_energy_change"])-float(r["net_gas_plus_potential"])
            if not math.isclose(residual,original,rel_tol=1.e-12,abs_tol=1.e-12):
                raise ValueError(f"exterior total residual disagrees at {case}/{b}/{method}/{boundary}/{rule}")
            transport = dt*sum(v*flux[case,i,boundary] for i,v in weights if v)
            comparisons.append(dict(case=case,start_index=a,end_index=b,start_myr=left["age_myr"],end_myr=right["age_myr"],
                injector_method=method,boundary_method=boundary,rule=rule,labelled_energy_erg=label,
                flagged_delta_potential_over_label=dphi_flag/label,injector_potential_flux_integral_over_label=inj_transport/label,
                direct_inward_motion_work_over_label=direct[0],direct_outward_motion_work_over_label=direct[1],
                **compare_interval(dphi_domain,dphi_flag,transport,inj_transport,label,residual,direct[2])))
    return list(snapshots.values()),comparisons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("requests","results","signed_summary","output"):
        parser.add_argument(arg,type=Path)
    parser.add_argument("--compact",type=Path,default=ARCHIVE,help="public compact_inputs.zip")
    parser.add_argument("--cases",nargs="+",choices=CASES,default=CASES)
    parser.add_argument("--require-outer",action="store_true",help="require validated full-grid gravity for every patch")
    args = parser.parse_args()
    domain = read_domain(args.compact)
    stocks,balances = [],[]
    for case in args.cases:
        s,b = compare_case(args.requests,args.results,args.signed_summary,domain,case,args.require_outer)
        stocks.extend(s)
        balances.extend(b)
    if not balances:
        raise ValueError("no consecutive captured snapshots")
    args.output.mkdir(parents=True,exist_ok=True)
    write_rows(args.output/"flagged_sphere_gravity_snapshots.csv",stocks)
    write_rows(args.output/"flagged_sphere_gravity_intervals.csv",balances)


if __name__ == "__main__":
    main()
