#!/usr/bin/env python3
"""Measure fixed-inset storage, regional mass and potential-zero sensitivity.

This existing-output diagnostic reuses the native spherical extractor's input,
field and grid contracts. It measures all requested regions even when their
coverage flags fail. Snapshot storage cannot identify historical Riemann flux,
gravity-update, floor or conversion-repair contributions.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Mapping

import h5py
import numpy as np

import extract_spherical_energy_budget as native

METHOD_VERSION = 1
DEFAULT_INSET_KPC = 50.0
MASS_UNIT_G = native.UNIT_DENSITY_CGS * native.UNIT_LENGTH_CM**3
ENERGY_FIELDS = (*native.COMPONENTS, "gravitational_shifted")
REGIONS = ("all", "cocoon", "ambient")
SOURCE_FILES = (
    "extract_fixed_box_energy_budget.py", "extract_spherical_energy_budget.py",
    "measure_q031_fluxes.py", "pluto_h5_level3_ambient_extract.py",
    "select_common_age_hdf5.py", "snapshot_energy.py",
)


def _accumulator() -> dict[str, list[float]]:
    return {key: [] for key in ("cell_count", "volume_kpc3", "initial_mass_g", "current_mass_g", "mass_delta_g", *(f"{name}_delta_erg" for name in ENERGY_FIELDS))}


def _add(acc: dict[str, list[float]], mask: np.ndarray, volume: np.ndarray,
         mass0: np.ndarray, mass1: np.ndarray, mass_delta: np.ndarray,
         energy: Mapping[str, np.ndarray]) -> None:
    acc["cell_count"].append(int(np.count_nonzero(mask)))
    acc["volume_kpc3"].append(float(np.sum(volume, where=mask)))
    for key, values in (("initial_mass_g", mass0), ("current_mass_g", mass1), ("mass_delta_g", mass_delta)):
        acc[key].append(float(np.sum(values, where=mask)))
    for name, values in energy.items():
        acc[f"{name}_delta_erg"].append(float(np.sum(values, where=mask)))


def _finish(acc: Mapping[str, list[float]], labelled_input: float, shift: float) -> dict[str, Any]:
    r = {key: math.fsum(values) for key, values in acc.items()}
    r["cell_count"] = int(r["cell_count"])
    r["thermal_plus_kinetic_delta_erg"] = math.fsum(r[f"{name}_delta_erg"] for name in ("thermal", "kinetic"))
    r["total_delta_erg"] = math.fsum(r[f"{name}_delta_erg"] for name in native.COMPONENTS)
    mass_residual = r["current_mass_g"] - r["initial_mass_g"] - r["mass_delta_g"]
    mass_tolerance = 1.e-9*max(abs(r["initial_mass_g"]),abs(r["current_mass_g"]),1.)
    if abs(mass_residual)>mass_tolerance:
        raise ValueError("initial/current/delta mass identity failed")
    r["mass_balance_identity"] = {"pass": True, "residual_g": mass_residual, "tolerance_g": mass_tolerance}
    r["total_over_labelled_input"] = r["total_delta_erg"] / labelled_input if labelled_input > 0 else None
    predicted = r["gravitational_delta_erg"] + shift * r["mass_delta_g"]
    residual = r["gravitational_shifted_delta_erg"] - predicted
    scale = max(abs(predicted), abs(r["gravitational_delta_erg"]), abs(shift*r["mass_delta_g"]), labelled_input, 1.)
    if abs(residual) > 1.e-9*scale:
        raise ValueError("potential-zero shift identity failed")
    r["potential_zero_shift"] = {
        "shift_cm2_s2": shift,
        "predicted_gravitational_shifted_delta_erg": predicted,
        "identity_residual_erg": residual,
        "identity_tolerance_erg": 1.e-9*scale,
        "identity_pass": True,
        "total_response_erg_per_cm2_s2": r["mass_delta_g"],
    }
    return r


def _finish_partition(acc: Mapping[str, Any], labelled_input: float, shift: float) -> dict[str, Any]:
    result = {name: _finish(acc[name], labelled_input, shift) for name in REGIONS}
    residuals = {}
    for key in acc["all"]:
        residual = result["cocoon"][key] + result["ambient"][key] - result["all"][key]
        scale = max(abs(result[name][key]) for name in REGIONS)
        tolerance = 0. if key == "cell_count" else 1.e-9*max(scale, 1.)
        if abs(residual) > tolerance:
            raise ValueError(f"current-region partition identity failed: {key}")
        residuals[key] = residual
    return {"partitions": result, "partition_identity": {"pass": True, "residuals": residuals}}


def _new_extent() -> dict[str, Any]:
    return {"cell_count": 0, "maximum_radius_kpc": None,
            "minimum_domain_face_margin_kpc": None,
            "minimum_cell_face_kpc_xyz": None, "maximum_cell_face_kpc_xyz": None,
            "inside_inset_boundary_cell_count": 0}


def _extent(acc: dict[str, Any], mask: np.ndarray, inside: np.ndarray,
            inset_boundary: np.ndarray, grid: native.Grid, iz: int, radius: np.ndarray) -> None:
    count = int(np.count_nonzero(mask))
    acc["cell_count"] += count
    if not count:
        return
    iy, ix = np.nonzero(mask)
    low = [float(grid.x_edges[ix.min()]), float(grid.y_edges[iy.min()]), float(grid.z_edges[iz])]
    high = [float(grid.x_edges[ix.max()+1]), float(grid.y_edges[iy.max()+1]), float(grid.z_edges[iz+1])]
    if acc["minimum_cell_face_kpc_xyz"] is not None:
        low = [min(a,b) for a,b in zip(low,acc["minimum_cell_face_kpc_xyz"],strict=True)]
        high = [max(a,b) for a,b in zip(high,acc["maximum_cell_face_kpc_xyz"],strict=True)]
    acc["minimum_cell_face_kpc_xyz"] = low
    acc["maximum_cell_face_kpc_xyz"] = high
    margin = min(low[0]-grid.x_edges[0], grid.x_edges[-1]-high[0],
                 low[1]-grid.y_edges[0], grid.y_edges[-1]-high[1],
                 low[2]-grid.z_edges[0], grid.z_edges[-1]-high[2])
    acc["minimum_domain_face_margin_kpc"] = float(margin)
    acc["maximum_radius_kpc"] = max(float(np.max(radius, where=mask, initial=0.)), acc["maximum_radius_kpc"] or 0.)
    acc["inside_inset_boundary_cell_count"] += int(np.count_nonzero(mask & inside & inset_boundary))


def integrate(*, current: Mapping[str, Any], initial: Mapping[str, Any], grid: native.Grid,
              environment: Any, inset_kpc: float, labelled_input_erg: float,
              discovery: Mapping[str, Any], potential_zero_shift_cm2_s2: float = 0.) -> dict[str, Any]:
    selected_axes = [native._safe_axis_mask(axis, inset_kpc) for axis in (grid.x_edges,grid.y_edges,grid.z_edges)]
    if any(not np.any(axis) for axis in selected_axes):
        raise ValueError("fixed inset box contains no complete cells")
    bounds = [(int(np.flatnonzero(axis)[0]),int(np.flatnonzero(axis)[-1])) for axis in selected_axes]
    radius_limits = {"R100": discovery["thresholds"][100.]["raw_radius_kpc"],
                     "R300": discovery["thresholds"][300.]["raw_radius_kpc"]}
    names = ["whole_grid", "fixed_inset_box", "outside_fixed_inset_box", *[n for n,r in radius_limits.items() if r is not None]]
    budgets = {name: {part:_accumulator() for part in REGIONS} for name in names}
    flag_names = ("thermodynamic_ge_1pct", "speed_ge_30_km_s", "speed_ge_100_km_s", "speed_ge_300_km_s", "thermodynamic_ge_1pct_or_speed_ge_30_km_s", "current_cocoon")
    flags = {name: {"extent":_new_extent(), "inside":_accumulator(), "outside":_accumulator()} for name in flag_names}
    area = grid.dy[:,None]*grid.dx[None,:]
    rxy2 = grid.y[:,None]**2+grid.x[None,:]**2
    ix = np.arange(len(grid.x))[None,:]; iy = np.arange(len(grid.y))[:,None]
    for iz,z in enumerate(grid.z):
        now = native._state(current,iz,current=True)
        before = native._state(initial,iz,current=False)
        radius = np.sqrt(rxy2+z*z)
        volume = area*grid.dz[iz]
        potential = environment.potential_at_radius(radius*native.UNIT_LENGTH_CM)
        mass0 = before["rho"]*volume*MASS_UNIT_G
        mass1 = now["rho"]*volume*MASS_UNIT_G
        mass_delta = (now["rho"]-before["rho"])*volume*MASS_UNIT_G
        thermal = (now["prs"]-before["prs"])*volume*native.UNIT_ENERGY_ERG/(native.GAMMA_GAS-1.)
        kinetic = .5*(now["rho"]*sum(now[n]**2 for n in ("vx1","vx2","vx3"))-before["rho"]*sum(before[n]**2 for n in ("vx1","vx2","vx3")))*volume*native.UNIT_ENERGY_ERG
        gravitational = mass_delta*potential
        energy = {"thermal":thermal,"kinetic":kinetic,"gravitational":gravitational,
                  "gravitational_shifted":mass_delta*(potential+potential_zero_shift_cm2_s2)}
        cocoon = now["tr1"] > native.TRACER_THRESHOLD
        inside = selected_axes[1][:,None]&selected_axes[0][None,:]&bool(selected_axes[2][iz])
        inset_boundary = (ix==bounds[0][0])|(ix==bounds[0][1])|(iy==bounds[1][0])|(iy==bounds[1][1])|(iz==bounds[2][0])|(iz==bounds[2][1])
        masks = {"whole_grid":np.ones_like(cocoon),"fixed_inset_box":inside,"outside_fixed_inset_box":~inside,
                 **{n:radius<=np.nextafter(r,math.inf) for n,r in radius_limits.items() if r is not None}}
        for name,mask in masks.items():
            for part,part_mask in (("all",mask),("cocoon",mask&cocoon),("ambient",mask&~cocoon)):
                _add(budgets[name][part],part_mask,volume,mass0,mass1,mass_delta,energy)
        thermodynamic = (np.abs(now["prs"]/before["prs"]-1.)>=.01)|(np.abs(now["rho"]/before["rho"]-1.)>=.01)
        speed = native._speed_km_s(now)
        diagnostic_masks = {"thermodynamic_ge_1pct":thermodynamic,
                            **{f"speed_ge_{cut}_km_s":speed>=cut for cut in (30,100,300)},
                            "thermodynamic_ge_1pct_or_speed_ge_30_km_s":thermodynamic|(speed>=30.),
                            "current_cocoon":cocoon}
        for name,mask in diagnostic_masks.items():
            _extent(flags[name]["extent"],mask,inside,inset_boundary,grid,iz,radius)
            _add(flags[name]["inside"],mask&inside,volume,mass0,mass1,mass_delta,energy)
            _add(flags[name]["outside"],mask&~inside,volume,mass0,mass1,mass_delta,energy)
    result = {name:_finish_partition(acc,labelled_input_erg,potential_zero_shift_cm2_s2) for name,acc in budgets.items()}
    residuals = {}
    for part in REGIONS:
        for key in budgets["whole_grid"][part]:
            value = result["fixed_inset_box"]["partitions"][part][key]+result["outside_fixed_inset_box"]["partitions"][part][key]-result["whole_grid"]["partitions"][part][key]
            scale = max(abs(result[name]["partitions"][part][key]) for name in ("whole_grid","fixed_inset_box","outside_fixed_inset_box"))
            if abs(value) > (0. if key=="cell_count" else 1.e-9*max(scale,1.)):
                raise ValueError(f"fixed box partition identity failed: {part}/{key}")
            residuals[f"{part}/{key}"] = value
    diagnostics = {}
    for name,acc in flags.items():
        within = _finish(acc["inside"],labelled_input_erg,potential_zero_shift_cm2_s2)
        outside = _finish(acc["outside"],labelled_input_erg,potential_zero_shift_cm2_s2)
        extent = acc["extent"]
        diagnostics[name] = {"extent":extent,"inside_fixed_inset_box":within,"outside_fixed_inset_box":outside,
                             "all_selected_cells_inside_fixed_inset_box":outside["cell_count"]==0,
                             "contacts_inset_boundary":extent["inside_inset_boundary_cell_count"]>0,
                             "contacts_domain_face":extent["minimum_domain_face_margin_kpc"]==0.}
    box_faces = {axis:[float(edges[low]),float(edges[high+1])] for axis,edges,(low,high) in zip("xyz",(grid.x_edges,grid.y_edges,grid.z_edges),bounds,strict=True)}
    retained_radius = min(value for lower,upper in box_faces.values() for value in (-lower,upper))
    return {"regions":result,"fixed_box_partition_identity":{"pass":True,"residuals":residuals},
            "operational_coverage":diagnostics,"fixed_box_cell_faces_kpc":box_faces,
            "fixed_box_nominal_inscribed_radius_kpc":native._box_radius_limit((grid.x_edges,grid.y_edges,grid.z_edges),inset_kpc),
            "fixed_box_retained_cell_inscribed_radius_kpc":retained_radius if retained_radius>0. else None,
            "speed_apertures":{name:{"raw_radius_kpc":radius,"available":radius is not None,
               "geometrically_complete_in_domain_box":radius<=native._box_radius_limit((grid.x_edges,grid.y_edges,grid.z_edges),0.) if radius is not None else None,
               "geometrically_complete_in_fixed_inset_box":radius<=retained_radius if radius is not None else None} for name,radius in radius_limits.items()}}


def extract_snapshot(*, case: str, snapshot_index: int, current_h5: Path, initial_h5: Path,
                     environment_path: Path, output: Path, input_receipt: Path | None = None,
                     grid_file: Path | None = None, current_timestep: str | None = None,
                     initial_timestep: str | None = None, inset_kpc: float = DEFAULT_INSET_KPC,
                     potential_zero_shift_cm2_s2: float = 0.) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    if case not in native.CASES or snapshot_index<0:
        raise ValueError("invalid case or snapshot index")
    if case=="G-HI" and snapshot_index>=native.G_HI_FIRST_BOUNDARY_CONTAMINATED_INDEX:
        raise ValueError("G-HI snapshots 48-50 are boundary-contaminated and scientifically excluded")
    if not math.isfinite(inset_kpc) or inset_kpc<0 or not math.isfinite(potential_zero_shift_cm2_s2):
        raise ValueError("inset and potential shift must be finite; inset must be non-negative")
    native._validate_snapshot_index(current_h5,snapshot_index)
    native._validate_snapshot_index(initial_h5,0)
    paths = {"current_h5":current_h5,"initial_h5":initial_h5,"environment":environment_path}
    if grid_file is not None:
        paths["grid_file"] = grid_file
    identities,receipt_identity,mode,claims = native.bind_inputs(paths,input_receipt)
    if claims is not None and (claims.get("status")!="bound_spherical_budget_inputs" or claims.get("case")!=case or claims.get("snapshot_index")!=snapshot_index):
        raise ValueError("bound input receipt status/case/index differs")
    source_identities = [{**native._stat_identity(Path(__file__).parent/name),"sha256":native._sha256(Path(__file__).parent/name)} for name in SOURCE_FILES]
    environment = native.load_environment(environment_path)
    with h5py.File(initial_h5,"r") as f0,h5py.File(current_h5,"r") as f1:
        t0,time0,shape0 = native._single_timestep(f0,initial_timestep,context=str(initial_h5))
        t1,time1,shape1 = native._single_timestep(f1,current_timestep,context=str(current_h5))
        if shape0!=shape1:
            raise ValueError("current and initial native grid shapes differ")
        if abs(time0/native.CODE_TIME_PER_MYR)>1.e-6 or time1<0:
            raise ValueError("initial must be t=0 and current age non-negative")
        if claims is not None:
            for state,timestep,time in (("initial",t0,time0),("current",t1,time1)):
                if claims[state].get("timestep")!=timestep or not math.isclose(float(claims[state].get("time_code",math.nan)),time,rel_tol=0.,abs_tol=1.e-10):
                    raise ValueError("native timestep/time differs from receipt")
        g0 = native.read_grid(f0,shape0,grid_file=grid_file)
        grid = native.read_grid(f1,shape1,grid_file=grid_file)
        native._validate_grid(g0)
        native._validate_grid(grid,g0)
        native._box_radius_limit((grid.x_edges,grid.y_edges,grid.z_edges),inset_kpc)
        current = f1[f"/{t1}/vars"]; initial = f0[f"/{t0}/vars"]
        discovery = native.discover_apertures(current,grid,safe_buffer_kpc=inset_kpc)
        age = time1/native.CODE_TIME_PER_MYR
        labelled_input = native.CASE_BIPOLAR_POWER_ERG_S[case]*min(age,50.)*native.SECONDS_PER_MYR
        integrated = integrate(current=current,initial=initial,grid=grid,environment=environment,inset_kpc=inset_kpc,
                               labelled_input_erg=labelled_input,discovery=discovery,potential_zero_shift_cm2_s2=potential_zero_shift_cm2_s2)
    native._stable(identities+source_identities+([receipt_identity] if receipt_identity else []))
    result = {"schema_version":1,"method_version":METHOD_VERSION,"execution_status":"completed_fixed_box_energy_and_mass_measurement",
              "case":case,"snapshot_index":snapshot_index,"actual_time_myr":age,"initial_time_myr":time0/native.CODE_TIME_PER_MYR,
              "current_timestep":t1,"initial_timestep":t0,"shape_nz_ny_nx":list(shape1),"labelled_input_erg":labelled_input,
              "input_definition":"labelled bipolar power times actual age, capped at 50 Myr; not realised delivery",
              "inset_kpc":inset_kpc,"inset_membership":"complete finite-volume cells inside all six domain faces shifted inward by inset_kpc",
              "partition_definition":"current full-cell tr1 > 1e-3 and exact complement, applied to initial and current same cells",
              "mass_delta_definition":"sum[(rho(t)-rho(0))*V] over each current region",
              "gravitational_definition":"sum[(rho(t)-rho(0))*V*Phi0(r)] in the fixed centre-zero initial potential",
              "potential_shift_identity":"DeltaUg(Phi0+c)=DeltaUg(Phi0)+c*DeltaM; thermal and kinetic terms are invariant",
              "diagnostic_definition":"thermodynamic: abs(p/p0-1)>=0.01 or abs(rho/rho0-1)>=0.01; speed: full current 3-vector; no causal jet classification",
              "tracer_diagnostics":discovery["tracer_diagnostics"],"native_lobe":discovery["cocoon"],**integrated,
              "scientific_qualification":{"qualified":False,"status":"unreviewed_existing_output_diagnostic","holds":[
                  "native semantic configuration/environment identity requires external validated contract",
                  "coarse no-jet inset bounds do not certify production-grid contamination",
                  "operational disturbance containment is not causal separation or boundary quietness",
                  "realised nozzle delivery, historical discrete fluxes and in-grid source/repair terms remain unmeasured"]},
              "provenance":{"mode":mode,"inputs":identities,"input_receipt":receipt_identity,"input_receipt_claims":claims,
                            "source_files":source_identities,"environment_sha256":environment.source_sha256,
                            "stability":"all bound input, receipt and source identities checked after extraction"}}
    native._atomic_publish(output,result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case",choices=native.CASES,required=True)
    parser.add_argument("--snapshot-index",type=int,required=True)
    parser.add_argument("--current-h5",type=Path,required=True)
    parser.add_argument("--initial-h5",type=Path,required=True)
    parser.add_argument("--environment",type=Path,required=True)
    parser.add_argument("--grid-file",type=Path)
    parser.add_argument("--current-timestep")
    parser.add_argument("--initial-timestep")
    parser.add_argument("--inset-kpc",type=float,default=DEFAULT_INSET_KPC)
    parser.add_argument("--potential-zero-shift-cm2-s2",type=float,default=0.)
    parser.add_argument("--input-receipt",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    extract_snapshot(case=args.case,snapshot_index=args.snapshot_index,current_h5=args.current_h5,
                     initial_h5=args.initial_h5,environment_path=args.environment,output=args.output,
                     input_receipt=args.input_receipt,grid_file=args.grid_file,
                     current_timestep=args.current_timestep,initial_timestep=args.initial_timestep,
                     inset_kpc=args.inset_kpc,potential_zero_shift_cm2_s2=args.potential_zero_shift_cm2_s2)


if __name__=="__main__":
    main()
