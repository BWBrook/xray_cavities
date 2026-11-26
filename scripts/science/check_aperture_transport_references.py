"""Compare native aperture fluxes with the separate C-LO/30 plane scan and registered injector faces."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

from restate_native_delivery import CASES, INJECTOR, PRIMARY, SECONDS
from check_aperture_flux_cadence import COMPACT_SHA, integrate


ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "docs/science/assets/aperture_transport_2026-11-26"


def endpoint_raw(root, case, i):
    name = f"snapshot_{i:04d}.json"
    local = root / case / name
    if local.is_file():
        return local.read_bytes()
    with ZipFile(root / f"endpoints_{case}.zip") as archive:
        return archive.read(name)


def endpoint(root, case, i):
    return json.loads(endpoint_raw(root, case, i))


def independent_check(root, plane_file, reg_sha):
    reference = json.loads(plane_file.read_bytes())
    candidate = endpoint(root, "C-LO", 30)
    identity = candidate["identity"]
    registered = json.loads((ASSET / "registration.json").read_bytes())["cases"]["C-LO"]
    if (reference["case"] != identity["case"] or reference["index"] != identity["index"]
            or reference["registration_sha256"] != identity["registration_sha256"] or reg_sha != identity["registration_sha256"]
            or reference["native_sha256"] != identity["native_sha256"] or reference["age_myr"] != identity["actual_age_myr"]
            or reference["request_sha256"] != registered["input_request_sha256"]
            or reference["axes_sha256"] != registered["static_sha256"]["axes.npz"]
            or reference["atmosphere_sha256"] != registered["static_sha256"]["atmosphere.csv"]
            or reference["script_sha256"] != hashlib.sha256(Path(__file__).with_name("check_native_aperture_flux.py").read_bytes()).hexdigest()):
        raise ValueError("Plane check and primary endpoint refer to different inputs")
    data = []
    for name in ("R100", "R300"):
        ref = reference["apertures"][name]
        surf = candidate["measurement"]["apertures"][name]["surfaces"]["current"]
        geo = surf["geometry"]["total"]
        if (surf["radius_kpc"] != ref["radius_kpc"] or surf["cell_count"] != ref["cell_count"]
                or geo["face_count"] != ref["face_count"] or surf["domain_contact"]
                or not math.isclose(ref["area_kpc2"], geo["area_kpc2"], rel_tol=2e-12)
                or not math.isclose(ref["volume_kpc3"], surf["volume_kpc3"], rel_tol=2e-12)):
            raise ValueError("Independent native face geometry disagrees")
        scales = ref["sum_absolute_face_contributions"].copy()
        scales["gas_flux_outward_erg_s"] = math.fsum(scales[k] for k in
                    ("thermal_advective_flux_outward_erg_s", "pressure_work_outward_erg_s", "kinetic_flux_outward_erg_s"))
        scales["total_energy_flux_outward_erg_s"] = scales["gas_flux_outward_erg_s"] + scales["gravitational_flux_outward_erg_s"]
        for field, value in ref["centred_flux"].items():
            primary = surf["flux"]["centered_primitives"]["total"][field]
            error = abs(primary - value) / max(scales[field], 1.)
            if error > 2e-12:
                raise ValueError(f"{name} {field} differs in independent native re-extraction")
            data.append(dict(aperture=name, field=field, cell_count=surf["cell_count"], face_count=geo["face_count"],
                             area_kpc2=geo["area_kpc2"], primary=primary, independent=value,
                             difference_over_sum_absolute_face_terms=error))
    return data


def injector_rates():
    archive_path = INJECTOR / "history_tables.zip"
    receipt = json.loads((INJECTOR / "verification.json").read_bytes())
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != receipt["public_zip_sha256"]:
        raise ValueError("The injector history archive changed")
    result = {}
    with ZipFile(archive_path) as archive:
        for case, last in CASES.items():
            name = f"native/summary/{case}/injector_snapshot_rates.csv"
            raw = archive.read(name)
            if hashlib.sha256(raw).hexdigest() != receipt["public_member_sha256"][name]:
                raise ValueError("The injector rates changed")
            rows = [r for r in csv.DictReader(io.StringIO(raw.decode())) if r["method"] == PRIMARY[0] and r["region"] == "net"]
            if len(rows) != last + 1 or {int(r["index"]) for r in rows} != set(range(last+1)):
                raise ValueError("The net injector rate history is incomplete")
            result[case] = {int(r["index"]): r for r in rows}
    return result


def instantaneous(root, rates, reg_sha):
    result = []
    for case, history in rates.items():
        power = 2e45 if case.endswith("HI") else 2e43
        for i, source in history.items():
            payload = endpoint(root, case, i)
            identity = payload["identity"]
            if (identity["registration_sha256"] != reg_sha or identity["actual_age_myr"] != float(source["age_myr"])
                    or identity["index"] != i or identity["case"] != case):
                raise ValueError("Instantaneous aperture and source rates use different endpoints")
            delivered = float(source["gas_energy_over_label"]) * power
            for name, aperture in payload["measurement"]["apertures"].items():
                surf = aperture["surfaces"]["current"]
                for method, flow in surf["flux"].items():
                    net = flow["total"]["total_energy_flux_outward_erg_s"]
                    result.append(dict(case=case, index=i, actual_age_myr=identity["actual_age_myr"], aperture=name,
                                       radius_kpc=surf["radius_kpc"], sphere_complete=surf["sphere_fully_inside_domain"],
                                       domain_contact=surf["domain_contact"], method=method, labelled_power_erg_s=power,
                                       delivered_gas_power_erg_s=delivered, **flow["total"],
                                       energy_on_box_faces_outward_erg_s=flow["domain"]["total_energy_flux_outward_erg_s"],
                                       total_energy_outward_over_delivered_gas_power=net/delivered))
    return result


def startup(root, registration, reg_sha, rates):
    rows = []
    for case, selected in rates.items():
        power = 2e45 if case.endswith("HI") else 2e43
        endpoints = [endpoint(root, case, i) for i in (0, 1)]
        delta_t = (endpoints[1]["identity"]["actual_age_myr"] - endpoints[0]["identity"]["actual_age_myr"]) * SECONDS
        output = []
        for i, (payload, role) in enumerate(zip(endpoints, ("current", "previous"), strict=True)):
            static = registration["cases"][case]
            if (payload["identity"]["case"] != case or payload["identity"]["index"] != i
                    or payload["identity"]["registration_sha256"] != reg_sha
                    or payload["identity"]["native_sha256"] != static["snapshots"][i]["native_sha256"]):
                raise ValueError("Startup reference has a different native input")
            a = payload["measurement"]["apertures"]["R100"]["surfaces"][role]
            if (a != payload["measurement"]["apertures"]["R300"]["surfaces"][role]
                    or a["cell_count"] != static["maintained_cells"] or a["radius_kpc"] != static["max_maintained_radius_kpc"]
                    or a["geometry"]["internal"]["face_count"] != int(selected[i]["face_count"])
                    or a["domain_contact"]):
                raise ValueError("The old surface is not the maintained region's boundary")
            ref = selected[i]
            if float(ref["age_myr"]) != payload["identity"]["actual_age_myr"]:
                raise ValueError("Injector reference uses a different endpoint")
            rates = {"saved_flag_injector": float(ref["total_energy_over_label"])}
            entry = dict(case=case, index=i, actual_age_myr=float(ref["age_myr"]),
                         old_radius_kpc=a["radius_kpc"], face_count=int(ref["face_count"]),
                         injector_gas_over_labelled_power=float(ref["gas_energy_over_label"]),
                         injector_total_over_labelled_power=rates["saved_flag_injector"])
            for method, parts in a["flux"].items():
                rate = parts["total"]
                entry[method+"_gas_over_labelled_power"] = rate["gas_flux_outward_erg_s"]/power
                rates[method] = rate["total_energy_flux_outward_erg_s"]/power
                entry[method+"_total_over_labelled_power"] = rates[method]
            output.append((entry, rates))
        for entry, _ in output:
            for method in ("centered_primitives", "donor_cell_primitives"):
                correction = 0.25 * math.fsum(r["saved_flag_injector"] - r[method] for _, r in output)
                entry[method+"_first_interval_correction_erg"] = correction * power * delta_t
                entry[method+"_first_interval_correction_over_label"] = correction
            rows.append(entry)
    return rows


def cadence_budget(root, registration):
    archive = ASSET.parent / "low_power_entropy_result_2026-11-23/compact_inputs.zip"
    raw = (ASSET / "cadence_CLO_10_11.json").read_bytes()
    cadence = json.loads(raw)
    checked = json.loads((ASSET / "cadence_comparison.json").read_bytes())
    if (hashlib.sha256(archive.read_bytes()).hexdigest() != COMPACT_SHA or cadence["restart_archive_sha256"] != COMPACT_SHA
            or checked["cadence_receipt_sha256"] != hashlib.sha256(raw).hexdigest()
            or checked["status"] != "both_production_endpoints_match" or checked["number_compared"] != 56
            or cadence["integrals"] != integrate(cadence["snapshots"])):
        raise ValueError("Fine-cadence control is not bound to its two verified production endpoints")
    with ZipFile(archive) as bundle:
        series = [json.loads(bundle.read(f"snapshots/C-LO/ON/injector_{i}.json")) for i in range(10, 21)]
    if [s["age_myr"] for s in series] != [s["age_myr"] for s in cadence["snapshots"]]:
        raise ValueError("Injector and aperture samples have different times")
    duration = SECONDS * (series[-1]["age_myr"] - series[0]["age_myr"])
    label_mass = series[0]["labelled_mass_rate_g_s"] * duration
    snaps = registration["cases"]["C-LO"]["snapshots"]
    endpoints = []
    for i in (10, 11):
        data = endpoint_raw(root, "C-LO", i)
        if hashlib.sha256(data).hexdigest() != checked["production_endpoint_sha256"][str(i)]:
            raise ValueError("The cadence check used a different production endpoint")
        endpoints.append(json.loads(data)["measurement"]["apertures"])
    result = []
    for rule, samples in (("annual", [series[0], series[-1]]), ("subinterval_trapezoids", series)):
        def source(field):
            return math.fsum(SECONDS * (b["age_myr"] - a["age_myr"]) * 0.5 *
                             (a["rates"][PRIMARY[0]]["net"][field] + b["rates"][PRIMARY[0]]["net"][field])
                             for a, b in zip(samples, samples[1:]))
        gas, total, mass = (source(k) for k in ("gas_energy_erg_s", "total_energy_erg_s", "mass_g_s"))
        for name in ("R100", "R300"):
            fixed = cadence["integrals"]["mean_of_two_fixed_surfaces"][name]
            row = dict(case="C-LO", aperture=name, time_rule=rule, start_age_myr=series[0]["age_myr"],
                       end_age_myr=series[-1]["age_myr"], subintervals=len(samples)-1, delivered_gas_erg=gas,
                       labelled_mass_g=label_mass, net_mass_from_injector_g=mass)
            for stock, sweep, flux, source_value, maintenance in (
                    ("total_delta_erg", "total_energy_erg", "total_energy_outward_erg", total, "total_erg"),
                    ("mass_delta_g", "mass_g", "mass_outward_g", mass, "mass_g")):
                membership = 0.5 * (endpoints[0][name]["sweeps"]["current_to_next"][sweep] +
                                    endpoints[1][name]["sweeps"]["previous_to_current"][sweep])
                change = snaps[11]["apertures"][name]["stock"][stock] - snaps[10]["apertures"][name]["stock"][stock]
                maintained = series[-1]["flagged_storage"][maintenance] - series[0]["flagged_storage"][maintenance]
                transport = fixed[flux][rule]
                residual = math.fsum((change, -membership, transport, -source_value, -maintained))
                row[flux] = transport
                if maintenance == "mass_g":
                    row["mass_residual_g"] = residual
                    row["mass_residual_over_labelled_mass"] = residual / label_mass
                else:
                    row["outward_over_delivered_gas"] = transport / gas
                    row["energy_residual_over_delivered_gas"] = residual / gas
            result.append(row)
    return result


def write(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoints", type=Path, default=ASSET)
    parser.add_argument("--independent", type=Path, default=ASSET / "independent_CLO30.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    blob = (ASSET / "registration.json").read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    checked = independent_check(args.endpoints, args.independent, sha)
    rates = injector_rates()
    first = startup(args.endpoints, json.loads(blob), sha, rates)
    current = instantaneous(args.endpoints, rates, sha)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "independent_flux_check.csv", checked)
    write(args.output / "startup_injector_comparison.csv", first)
    write(args.output / "instantaneous_rates.csv", current)
    write(args.output / "cadence_budget.csv", cadence_budget(args.endpoints, json.loads(blob)))


if __name__ == "__main__":
    main()
