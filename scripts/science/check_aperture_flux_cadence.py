"""Compare 0.1-Myr and annual transport on four fixed C-LO spheres between 10 and 11 Myr."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

import h5py
import numpy as np

import check_native_aperture_flux as plane
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR, load_environment, write_json

CASE = "C-LO"
INDICES = tuple(range(10, 21))
ENDPOINTS = (10, 11)
APERTURES = ("R100", "R300")
COMPACT_SHA = "02df47c1c377a943883fb6a0211c4de5c38409c4aff334e638396ef7f763f9f7"
REGISTRATION_SHA = "2adb3221da4ed806f6d42f33be3d37dc2c2c7fc4039c785c68d3b4abf8a098b6"
RATES = (*plane.RATES, "gas_flux_outward_erg_s", "total_energy_flux_outward_erg_s")
INTEGRALS = ("mass_outward_g", "thermal_advective_outward_erg", "pressure_work_outward_erg",
             "kinetic_outward_erg", "gravitational_outward_erg", "gas_outward_erg", "total_energy_outward_erg")


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def registration(stage):
    path = stage / "registration.json"
    check(plane.sha(path) == REGISTRATION_SHA, "production aperture registration has changed")
    return json.loads(path.read_bytes())["cases"][CASE]


def surface_specs(frozen):
    return {f"{name}_at_{i}": frozen["snapshots"][i]["apertures"][name]
            for i in ENDPOINTS for name in APERTURES}


def read_restart(compact, frozen):
    check(plane.sha(compact) == COMPACT_SHA, "compact restart archive has changed")
    with ZipFile(compact) as bundle:
        seed = json.loads(bundle.read("verification.json"))["cases"][CASE]
        gate = json.loads(bundle.read("raw/C-LO/gate.json"))
        catalog = json.loads(bundle.read("raw/native-inventory.json"))["outputs"]
        selected = [r for r in catalog if r["case"] == CASE and r["arm"] == "ON" and r["index"] in INDICES]
        check([r["index"] for r in selected] == list(INDICES), "incomplete restart inventory")
        check(seed["seed_float_sha256"] == frozen["snapshots"][10]["native_sha256"] and
              gate["case"] == CASE and gate["passed"] and gate["control_output"] == 20 and
              gate["reference_sha256"] == frozen["snapshots"][11]["native_sha256"] and
              gate["reference_step"] == gate["control_step"] == selected[-1]["step"] and
              gate["reference_time"] == gate["control_time"] == selected[-1]["time_code"] and
              set(gate["unequal_cells_full_grid"]) == {*plane.FIELDS, "tr1"} and
              not any(gate["unequal_cells_full_grid"].values()), "restart differs from production control")

        records = []
        for entry in selected:
            i = entry["index"]
            raw = bundle.read(f"snapshots/C-LO/ON/grid_{i}.json")
            grid = json.loads(raw)
            source = grid["input"]
            check((grid["case"], grid["arm"], grid["index"], grid["step"], grid["time_code"]) ==
                  (CASE, "ON", i, entry["step"], entry["time_code"]), "grid and inventory identities differ")
            check((source["filename"], source["bytes"], source["mtime_ns"]) ==
                  (f"data.{i:04d}.flt.h5", entry["size"], entry["mtime_ns"]) and
                  source["atmosphere_sha256"] == frozen["static_sha256"]["atmosphere.csv"] and
                  grid["age_myr"] == entry["time_code"]/CODE_TIME_PER_MYR, "compact input identity or age differs")
            records.append({**entry, "age_myr": grid["age_myr"], "shape": tuple(source["shape_zyx"]),
                            "grid_receipt_sha256": hashlib.sha256(raw).hexdigest()})
    check(all(b["age_myr"] > a["age_myr"] for a, b in zip(records, records[1:])) and
          all(records[j]["age_myr"] == frozen["snapshots"][i]["age_myr"] for j,i in ((0,10),(-1,11))),
          "restart does not span the exact production interval")
    return records


def verify_stat(path, record):
    info = path.stat()
    check((info.st_size, info.st_ino, info.st_mtime_ns) == (record["size"], record["inode"], record["mtime_ns"]),
          f"native restart stat differs at index {record['index']}")


def geometry(surface, spec):
    check(surface["radius_kpc"] == spec["raw_radius_kpc"] and surface["cell_count"] == spec["cell_count"] and
          math.isclose(surface["volume_kpc3"], spec["volume_kpc3"], rel_tol=5e-11), "fixed aperture geometry differs")


def integrate(states):
    check([r["index"] for r in states] == list(INDICES), "cadence needs the two endpoints and nine interior states")
    ages = [r["age_myr"] for r in states]
    dt = [(b-a)*SECONDS_PER_MYR for a,b in zip(ages, ages[1:])]
    check(all(math.isfinite(v) and v > 0 for v in dt), "cadence ages must increase")
    total_time = (ages[-1] - ages[0]) * SECONDS_PER_MYR
    fixed = {}
    for name in APERTURES:
        for i in ENDPOINTS:
            key = f"{name}_at_{i}"
            fixed[key] = {}
            for rate, quantity in zip(RATES, INTEGRALS, strict=True):
                series = [s["surfaces"][key]["centred_flux"][rate] for s in states]
                check(all(math.isfinite(v) for v in series), "nonfinite endpoint flux")
                annual = total_time * (series[0]+series[-1]) / 2
                refined = math.fsum(step*(a+b)/2 for step,a,b in zip(dt, series[:-1], series[1:], strict=True))
                fixed[key][quantity] = {"annual":annual, "subinterval_trapezoids":refined, "refined_minus_annual":refined-annual}
    means = {}
    for name in APERTURES:
        mean = {}
        for quantity in INTEGRALS:
            rows = [fixed[f"{name}_at_{i}"][quantity] for i in ENDPOINTS]
            mean[quantity] = {k: math.fsum(r[k] for r in rows)/2 for k in rows[0]}
        means[name] = mean
    return {"fixed":fixed, "mean_of_two_fixed_surfaces":means}


def measure(stage, outputs, compact):
    frozen = registration(stage)
    records = read_restart(compact, frozen)
    specs = surface_specs(frozen)
    check(all(s["available"] and s["geometrically_complete_in_domain_box"] for s in specs.values()),
          "expected four complete apertures")
    radii = {k:s["raw_radius_kpc"] for k,s in specs.items()}
    directory = stage / "requests" / CASE
    for name in ("axes.npz", "atmosphere.csv"):
        check(plane.sha(directory/name) == frozen["static_sha256"][name], f"changed static {name}")
    environment = load_environment(directory / "atmosphere.csv")
    states = []
    with np.load(directory / "axes.npz", allow_pickle=False) as axes:
        centres = [axes[k] for k in "xyz"]
        edges = [axes[k+"_edges"] for k in "xyz"]
        for record in records:
            i = record["index"]
            input_file = outputs / f"data.{i:04d}.flt.h5"
            verify_stat(input_file, record)
            print(f"Scanning C-LO/ON restart index {i}", flush=True)
            with h5py.File(input_file, "r") as src:
                group = src[f"Timestep_{i}"]
                fields = group["vars"]
                check(float(group.attrs["Time"]) == record["time_code"] and all(
                    fields[k].shape == record["shape"] and fields[k].dtype == np.dtype("<f4")
                    for k in plane.FIELDS), f"native restart precision, shape or time differs at {i}")
                for j, label in enumerate("XYZ"):
                    for key, target in (("cell_coords",centres[j]), ("node_coords",edges[j])):
                        check(np.array_equal(plane.axis_from_native(src[key], label, j), target), f"changed {label} axis at {i}")
                surfaces = plane.scan(fields, centres, edges, radii, environment.potential_at_radius)
            verify_stat(input_file, record)
            for k,s in surfaces.items():
                geometry(s,specs[k])
            states.append({"index":i, "age_myr":record["age_myr"], "grid_receipt_sha256":record["grid_receipt_sha256"],
                           "surfaces":surfaces})
    return {"case":CASE, "arm":"ON", "registration_sha256":REGISTRATION_SHA, "restart_archive_sha256":COMPACT_SHA,
            "reader_sha256":plane.sha(Path(plane.__file__)), "script_sha256":plane.sha(Path(__file__)),
            "production_endpoint_check":"pending", "snapshots":states, "integrals":integrate(states)}


def gross_scale(measured, rate):
    absolute = measured["sum_absolute_face_contributions"]
    if rate in absolute:
        return absolute[rate]
    fields = plane.RATES[1:4] if rate == RATES[-2] else plane.RATES[1:]
    return math.fsum(absolute[k] for k in fields)


def compare_endpoint(frozen, i, measured, receipt):
    row = frozen["snapshots"][i]
    identity = receipt["identity"]
    check((identity["case"], identity["index"], identity["actual_age_myr"], identity["registration_sha256"],
           identity["native_sha256"], identity["fixed_sha256"]) ==
          (CASE, i, row["age_myr"], REGISTRATION_SHA, row["native_sha256"], row["fixed_sha256"]) and
          measured["age_myr"] == row["age_myr"], "production endpoint identity differs")
    comparisons = []
    for name in APERTURES:
        surfaces = receipt["measurement"]["apertures"][name]["surfaces"]
        for radius_epoch in ENDPOINTS:
            role = {0:"current", -1:"previous", 1:"next"}[radius_epoch-i]
            reference = surfaces[role]
            test = measured["surfaces"][f"{name}_at_{radius_epoch}"]
            spec = frozen["snapshots"][radius_epoch]["apertures"][name]
            geometry(test,spec)
            geometry(reference,spec)
            check(test["face_count"] == reference["geometry"]["total"]["face_count"] and
                  math.isclose(test["area_kpc2"],reference["geometry"]["total"]["area_kpc2"],rel_tol=5e-11),
                  "independent endpoint face count or area differs")
            for rate in RATES:
                target = reference["flux"]["centered_primitives"]["total"][rate]
                value = test["centred_flux"][rate]
                scale = max(abs(target),gross_scale(test,rate),1.)
                delta = abs(target-value) / scale
                check(math.isfinite(delta) and delta <= 2e-11, f"endpoint mismatch {i}/{name}/{radius_epoch}/{rate}")
                comparisons.append({"production_index":i, "radius_at_index":radius_epoch, "aperture":name,
                                    "rate":rate, "restart":value, "production":target, "scaled_absolute_difference":delta})
    return comparisons


def compare(stage, path, production):
    frozen = registration(stage)
    result = json.loads(path.read_bytes())
    check((result["case"], result["arm"], result["registration_sha256"], result["restart_archive_sha256"]) ==
          (CASE,"ON",REGISTRATION_SHA,COMPACT_SHA), "unexpected cadence receipt")
    states = result["snapshots"]
    check(result["integrals"] == integrate(states), "cadence receipt integrals differ from its rates")
    rows, hashes = [], {}
    for endpoint_index, measured in zip(ENDPOINTS, (states[0],states[-1]), strict=True):
        native_path = production / f"snapshot_{endpoint_index:04d}.json"
        hashes[str(endpoint_index)] = plane.sha(native_path)
        rows.extend(compare_endpoint(frozen, endpoint_index, measured, json.loads(native_path.read_bytes())))
    return {"case":CASE, "status":"both_production_endpoints_match", "cadence_receipt_sha256":plane.sha(path),
            "production_endpoint_sha256":hashes, "number_compared":len(rows),
            "maximum_scaled_absolute_difference":max(r["scaled_absolute_difference"] for r in rows),
            "comparisons":rows, "integrals":result["integrals"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--compact-inputs", type=Path)
    parser.add_argument("--compare", type=Path, metavar="CADENCE_RECEIPT")
    parser.add_argument("--production-receipts", type=Path, metavar="C_LO_DIRECTORY")
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    if a.compare and a.production_receipts and not (a.outputs or a.compact_inputs):
        contents = compare(a.stage,a.compare,a.production_receipts)
    elif a.outputs and a.compact_inputs and not (a.compare or a.production_receipts):
        contents = measure(a.stage,a.outputs,a.compact_inputs)
    else:
        parser.error("supply --outputs and --compact-inputs for extraction, or --compare and --production-receipts for endpoint verification")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(a.output, contents)
