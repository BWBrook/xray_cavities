"""Integrate the registered four-case R100/R300 stocks and signed outward face rates."""
from __future__ import annotations

import argparse
import csv
from contextlib import ExitStack
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from review_production_entropy_history import ASSETS, CASES, FACE, HISTORY, INJECTOR, MYR


REGISTRATION = ASSETS / "aperture_transport_2026-11-26/registration.json"
VERIFICATION = HISTORY.with_name("verification.json")
ANNUAL = ASSETS / "production_entropy_review_2026-11-23/annual_balances.csv"
MASS = ASSETS / "tracer_mass_budget_2026-11-19/tagged_mass_intervals.csv"
FIXED_BASIS = ASSETS / "four_case_energy_partition_2026-11-26/native_fixed_stocks.json.gz"
PINS = {
    "registration": "2adb3221da4ed806f6d42f33be3d37dc2c2c7fc4039c785c68d3b4abf8a098b6",
    "injector_verification": "9cdf21211f3f891ee5e805808412a4424e2a63e93848279ca4fca167676d0647",
    "annual_review": "da769097af6e8b7e1d8884f085d8dd32eb62bcba202f399818dcc28fe3b5bdab",
    "labelled_mass": "cbf1fbfc4da6e641064a41969c6cd81984cc21d49ce3d7015f5318e77f608364",
    "fixed_stock_basis_uncompressed": "f9df74456fa22d0f321e44c3439ddae38671d2a190b200fc482c0a93072fdf20",
}
APERTURES = ("R100", "R300")
METHODS = ("centered_primitives", "donor_cell_primitives")
PARTS = ("internal", "domain", "total")
BOX_FACES = tuple(f"{axis}_{side}" for axis in "zyx" for side in ("negative", "positive"))
# Endpoint order is F_start(old), F_start(new), F_end(old), F_end(new).
WEIGHTS = {
    "symmetric_fixed": (0.25, 0.25, 0.25, 0.25),
    "old_fixed": (0.5, 0., 0.5, 0.),
    "new_fixed": (0., 0.5, 0., 0.5),
    "moving_endpoints": (0.5, 0., 0., 0.5),
}
# Public interval quantity -> native rate or pair of registered/swept stock names.
RATES = {
    "mass_outward_g": "mass_flux_outward_g_s",
    "thermal_advective_outward_erg": "thermal_advective_flux_outward_erg_s",
    "pressure_work_outward_erg": "pressure_work_outward_erg_s",
    "kinetic_outward_erg": "kinetic_flux_outward_erg_s",
    "gravitational_outward_erg": "gravitational_flux_outward_erg_s",
    "gas_outward_erg": "gas_flux_outward_erg_s",
    "total_energy_outward_erg": "total_energy_flux_outward_erg_s",
}
STOCK = {
    "mass_g": ("mass_delta_g", "mass_g"),
    "thermal_erg": ("thermal_delta_erg", "thermal_erg"),
    "kinetic_erg": ("kinetic_delta_erg", "kinetic_erg"),
    "gravitational_erg": ("gravitational_delta_erg", "gravitational_erg"),
    "total_energy_erg": ("total_delta_erg", "total_energy_erg"),
}
ENERGIES = ("thermal_erg", "kinetic_erg", "gravitational_erg")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(data, expected, name):
    if digest(data) != expected:
        raise ValueError(f"SHA-256 mismatch for {name}")
    return data


def csv_rows(data):
    return csv.DictReader(io.StringIO(data.decode()))


def index_rows(rows, key, expected, name):
    by_key = {}
    for row in rows:
        k = key(row)
        if k in by_key:
            raise ValueError(f"Duplicate {name}: {k}")
        by_key[k] = row
    if by_key.keys() != expected:
        raise ValueError(f"Wrong {name} cohort: missing {expected - by_key.keys()}, extra {by_key.keys() - expected}")
    return by_key


class Audit:
    def __init__(self):
        self.summary = {}

    def equal(self, check, actual, expected, scale=0.):
        size = max(abs(actual), abs(expected), abs(scale), 1e-300)
        error = abs(actual - expected) / size
        if not math.isfinite(error) or error > 5e-11:
            raise ValueError(f"{check}: {actual} differs from {expected} (scale {size})")
        row = self.summary.setdefault(check, {"checks": 0, "max_scaled_difference": 0.})
        row["checks"] += 1
        row["max_scaled_difference"] = max(row["max_scaled_difference"], error)

    def sum(self, check, actual, terms):
        terms = tuple(terms)
        self.equal(check, actual, math.fsum(terms), math.fsum(abs(t) for t in terms))


def source_intervals(cases, archive, verification, annual, masses, audit):
    """Bind the archived interval label to the actual ages, net injector rates and grid balance."""
    inventory = {(case, i - 1, i) for case, data in cases.items() for i in range(1, len(data["snapshots"]))}
    def interval(r):
        return r["case"], int(r["start_index"]), int(r["end_index"])

    def member(path):
        return csv_rows(checked(archive.read(path), verification["public_member_sha256"][path], path))

    review = index_rows(annual, interval, inventory, "reviewed annual balance")
    mass = index_rows((r for r in masses if int(r["end_index"]) == int(r["start_index"])+1),
                      interval, inventory, "mass label")
    grav = index_rows((r for r in member("comparison/flagged_sphere_gravity_intervals.csv")
                       if (r["injector_method"], r["boundary_method"], r["rule"]) == (INJECTOR, FACE, "trapezoid")),
                      interval, inventory, "injector potential")
    result = {}
    for case, source in cases.items():
        snaps = source["snapshots"]
        power = 2e45 if case.endswith("HI") else 2e43
        selected = (r for r in member(f"native/summary/{case}/injector_interval_balances.csv")
                    if (r["method"], r["rule"]) == (INJECTOR, "trapezoid"))
        intervals = index_rows(selected, interval, {k for k in inventory if k[0] == case}, "net injector")
        selected = (r for r in member(f"native/summary/{case}/injector_snapshot_rates.csv")
                    if (r["method"], r["region"]) == (INJECTOR, "net"))
        rates = index_rows(selected, lambda r: (r["case"], int(r["index"])),
                           {(case, i) for i in range(len(snaps))}, "net injector rate")
        for key, inj in intervals.items():
            _, a, b = key
            start, end = snaps[a]["age_myr"], snaps[b]["age_myr"]
            sa, sb = rates[case, a], rates[case, b]
            g, rev = grav[key], review[key]
            if (rev["scope"] != "annual" or
                any(float(r[k]) != t for r, k, t in ((sa, "age_myr", start), (sb, "age_myr", end),
                    (g, "start_myr", start), (g, "end_myr", end),
                    (rev, "start_age_myr", start), (rev, "end_age_myr", end)))):
                raise ValueError(f"Archived interval ages disagree at {key}")
            elapsed = (end-start)*MYR
            active = (min(end, 50.) - min(start, 50.))*MYR
            label, mass_label = float(g["labelled_energy_erg"]), float(mass[key]["labelled_mass_g"])
            if not (active > 0 and elapsed > 0 and label > 0 and mass_label > 0):
                raise ValueError(f"Invalid interval label or duration at {key}")
            audit.equal("energy label from active seconds and bipolar power", label, active*power)
            audit.equal("energy and mass labels at 0.1c", label, 0.5*(0.1*2.99792458e10)**2*mass_label)
            audit.equal("independent energy label", label, float(rev["labelled_energy_erg"]))
            gas = float(inj["net_gas"])*label
            phi = float(g["injector_potential_flux_integral_over_label"])*label
            maintained = float(inj["flagged_total_energy_change"])*label
            grid = float(inj["outside_flagged_sphere_outer_active_cell"])*label
            def trap(field):
                return 0.5*elapsed*(float(sa[field])+float(sb[field]))
            audit.equal("signed gas endpoint trapezoid", gas, trap("gas_energy_over_label")*power, label)
            audit.equal("potential endpoint trapezoid", phi, trap("potential_energy_over_label")*power, label)
            audit.equal("gas plus potential injector delivery", gas+phi, float(inj["net_gas_plus_potential"])*label, label)
            for name, value, other in (
                    ("net gas", gas, float(rev["delivered_gas_erg"])),
                    ("potential", phi, float(rev["injector_potential_over_label"])*label),
                    ("maintained stock", maintained, float(rev["maintained_stock_over_label"])*label),
                    ("whole grid review", grid, float(rev["exterior_residual_over_label"])*label),
                    ("whole grid gravity archive", grid, float(g["outside_total_residual_over_label"])*label)):
                audit.equal(name, value, other, label)
            if gas <= 0:
                raise ValueError(f"Nonpositive net gas-energy denominator at {key}")
            result[key] = {"labelled_energy_erg": label, "delivered_gas_erg": gas, "injector_potential_erg": phi,
                           "maintained_stock_change_erg": maintained, "archived_grid_residual_erg": grid,
                           "labelled_mass_g": mass_label, "delivered_mass_g": trap("mass_over_label")*(mass_label/active)}
    return result


def fixed_bindings(cases, basis):
    """Match the partition's copy of the native stocks and its cocoon contact flags."""
    contacts = {}
    if basis["cases"].keys() != cases.keys():
        raise ValueError("Fixed-stock and registration cases disagree")
    for case, source in cases.items():
        fixed = basis["cases"][case]
        if fixed["completion_sha256"] != source["fixed_completion_sha256"]:
            raise ValueError(f"Different stock completion at {case}")
        contacts[case] = []
        for a, b in zip(source["snapshots"], fixed["snapshots"], strict=True):
            native = b["native_input_sha256"]
            if (a["index"] != b["index"] or a["age_myr"] != b["age_myr"] or a["fixed_sha256"] != b["snapshot_sha256"]
                    or a["native_sha256"] != native["current_h5"] or source["snapshots"][0]["native_sha256"] != native["initial_h5"]
                    or source["static_sha256"]["atmosphere.csv"] != native["environment"]):
                raise ValueError(f"Different fixed or native source at {case}/{a['index']}")
            for key in APERTURES:
                r = a["apertures"][key]
                stock = dict(zip(basis["stock_columns"], b["stocks"][key]["all"], strict=True))
                if (any(r[k] != v for k, v in b["speed_apertures"][key].items()) or
                        any(r[k] != stock[k] for k in ("cell_count", "volume_kpc3")) or
                        any(v != stock[k] for k, v in r["stock"].items())):
                    raise ValueError(f"Registered radius or stock disagrees at {case}/{a['index']}/{key}")
            contacts[case].append((b["cocoon_contacts_domain"], b["cocoon_clearance_kpc"]))
    return contacts


def validate_surface(surface, registered, audit):
    geometric = surface["geometry"]
    if (surface["radius_kpc"] != registered["raw_radius_kpc"] or surface["cell_count"] != registered["cell_count"]
            or surface["sphere_fully_inside_domain"] is not registered["geometrically_complete_in_domain_box"]
            or set(surface["flux"]) != set(METHODS) or set(geometric) != set(PARTS)
            or set(surface["box_faces"]) != set(BOX_FACES)):
        raise ValueError("Surface identity differs from the registered aperture or reconstruction")
    audit.equal("registered volume", surface["volume_kpc3"], registered["volume_kpc3"])
    for patch in (*geometric.values(), *surface["box_faces"].values()):
        if (type(patch["face_count"]) is not int or patch["face_count"] < 0
                or not math.isfinite(patch["area_kpc2"]) or patch["area_kpc2"] < 0
                or (patch["face_count"] == 0) != (patch["area_kpc2"] == 0)):
            raise ValueError("Invalid face count or area")
    if surface["domain_contact"] is not bool(geometric["domain"]["face_count"]):
        raise ValueError("Box-contact flag disagrees with its measured faces")
    for field in ("face_count", "area_kpc2"):
        audit.sum("six box faces", geometric["domain"][field], (r[field] for r in surface["box_faces"].values()))
        audit.sum("internal and box geometry", geometric["total"][field], (geometric[p][field] for p in PARTS[:2]))
    for by_part in surface["flux"].values():
        if set(by_part) != set(PARTS):
            raise ValueError("Missing or extra boundary part")
        for part, rates in by_part.items():
            if set(rates) != set(RATES.values()) or not all(math.isfinite(v) for v in rates.values()):
                raise ValueError("Wrong native flux quantities, units or nonfinite rate")
            if not geometric[part]["face_count"] and any(rates.values()):
                raise ValueError("Nonzero transport on an empty face patch")
            gas_terms = [rates[RATES[k]] for k in ("thermal_advective_outward_erg", "pressure_work_outward_erg",
                                                   "kinetic_outward_erg")]
            audit.sum("gas flux components", rates[RATES["gas_outward_erg"]], gas_terms)
            audit.sum("total energy flux components", rates[RATES["total_energy_outward_erg"]],
                      (*gas_terms, rates[RATES["gravitational_outward_erg"]]))
        for key in RATES.values():
            audit.sum("internal plus box flux", by_part["total"][key], (by_part[p][key] for p in PARTS[:2]))
    if surface["flux"][METHODS[0]]["domain"] != surface["flux"][METHODS[1]]["domain"]:
        raise ValueError("Outer active-cell rates differ between internal reconstructions")


def validate_endpoint(data, case, index, source, registration_sha, stage, audit):
    snapshots = source["snapshots"]
    entry = snapshots[index]
    expected = dict(case=case, index=index, actual_age_myr=entry["age_myr"], stage_sha256=stage,
                    registration_sha256=registration_sha, initial_sha256=snapshots[0]["native_sha256"],
                    native_sha256=entry["native_sha256"], fixed_sha256=entry["fixed_sha256"])
    if data["identity"] != expected:
        raise ValueError(f"Endpoint identity or stage differs at {case}/{index}")
    measurement = data["measurement"]
    if (set(measurement["apertures"]) != set(APERTURES) or measurement["internal_face_methods"] != list(METHODS)
            or measurement["domain_face_method"] != FACE):
        raise ValueError(f"Aperture or flux methods differ at {case}/{index}")
    roles = {name: i for name, i in (("previous", index-1), ("current", index), ("next", index+1))
             if 0 <= i < len(snapshots)}
    directions = [(left, right) for left, right in (("previous", "current"), ("current", "next"))
                  if left in roles and right in roles]
    for name, measured in measurement["apertures"].items():
        if (set(measured["surfaces"]) != roles.keys() or
                set(measured["sweeps"]) != {f"{left}_to_{right}" for left, right in directions}):
            raise ValueError(f"Incomplete radius roles or swept stocks at {case}/{index}/{name}")
        for role, i in roles.items():
            validate_surface(measured["surfaces"][role], snapshots[i]["apertures"][name], audit)
        for left, right in directions:
            a, b = (snapshots[roles[role]]["apertures"][name] for role in (left, right))
            sweep = measured["sweeps"][f"{left}_to_{right}"]
            if (set(sweep) != {s for _, s in STOCK.values()} | {"cell_count_delta", "volume_delta_kpc3"} or
                    sweep["cell_count_delta"] != b["cell_count"]-a["cell_count"]):
                raise ValueError("Swept quantities, units or cell count disagree")
            audit.equal("swept volume", sweep["volume_delta_kpc3"], b["volume_kpc3"]-a["volume_kpc3"],
                        max(a["volume_kpc3"], b["volume_kpc3"]))
            fields = [sweep[s] for _, s in STOCK.values()]
            if not all(map(math.isfinite, fields)) or ((index == 0 or sweep["cell_count_delta"] == 0) and any(fields)):
                raise ValueError("Nonfinite sweep or nonzero change on zero perturbation or unchanged membership")
            audit.sum("swept energy components", sweep["total_energy_erg"], (sweep[k] for k in ENERGIES))
    return measurement["apertures"]


def stock_motion(old, new, left_sweep, right_sweep, audit):
    rows = {}
    for key, (stored, swept) in STOCK.items():
        initial, final = old[stored], new[stored]
        a, b = left_sweep[swept], right_sweep[swept]
        delta = final-initial
        mean = 0.5*math.fsum((a, b))
        old_fixed, new_fixed = math.fsum((final, -b, -initial)), math.fsum((final, -initial, -a))
        audit.equal("symmetric stock change equals mean fixed-radius changes", delta-mean,
                    0.5*math.fsum((old_fixed, new_fixed)), max(map(abs, (initial, final, a, b))))
        rows[key] = {"change": delta, "sweep_at_start": a, "sweep_at_end": b, "symmetric_sweep": mean,
                     "symmetric_fixed_change": delta-mean, "old_fixed_change": old_fixed, "new_fixed_change": new_fixed}
    for term in rows["total_energy_erg"]:
        # Differences of large endpoint stocks can nearly cancel even when the stock identities are exact.
        audit.equal("component stock differences and sweeps", rows["total_energy_erg"][term],
                    math.fsum(rows[k][term] for k in ENERGIES),
                    max(math.fsum(abs(r[STOCK[k][0]]) for k in ENERGIES) for r in (old, new)) +
                    math.fsum(abs(s[k]) for s in (left_sweep, right_sweep) for k in ENERGIES))
    return rows


def integrate_flux(samples, method, rule, seconds):
    weights = WEIGHTS[rule]
    return {part: {name: seconds*math.fsum(w*s["flux"][method][part][rate] for s, w in zip(samples, weights, strict=True))
                   for name, rate in RATES.items()} for part in PARTS}


def balance(motion, integrated, source, rule):
    correction = {"old_fixed": "sweep_at_end", "new_fixed": "sweep_at_start"}.get(rule, "symmetric_sweep")
    energy, mass = motion["total_energy_erg"], motion["mass_g"]
    total = integrated["total"]
    corrected = energy["change"] - energy[correction]
    residual = math.fsum((corrected, total["total_energy_outward_erg"], -source["delivered_gas_erg"],
                          -source["injector_potential_erg"], -source["maintained_stock_change_erg"]))
    return {
        **source, "stock_change_erg": energy["change"], "membership_correction_erg": energy[correction],
        "stock_change_minus_membership_erg": corrected, "total_energy_outward_erg": total["total_energy_outward_erg"],
        "internal_face_energy_outward_erg": integrated["internal"]["total_energy_outward_erg"],
        "box_energy_outward_erg": integrated["domain"]["total_energy_outward_erg"], "aperture_residual_erg": residual,
        "aperture_minus_grid_residual_erg": residual-source["archived_grid_residual_erg"],
        "mass_change_g": mass["change"], "mass_membership_correction_g": mass[correction],
        "mass_outward_g": total["mass_outward_g"], "box_mass_outward_g": integrated["domain"]["mass_outward_g"],
        "mass_change_minus_membership_plus_outward_g": math.fsum((mass["change"], -mass[correction], total["mass_outward_g"])),
    }


def with_cumulative(values, running):
    for k, v in values.items():
        running.setdefault(k, []).append(v)
    return {**values, **{f"cumulative_{k}": math.fsum(terms) for k, terms in running.items()}}


def normalized(row):
    ratios = {}
    for prefix in ("", "cumulative_"):
        for key in ("total_energy_outward", "aperture_residual", "archived_grid_residual", "aperture_minus_grid_residual"):
            for unit, amount in (("label", "labelled_energy"), ("delivered_gas", "delivered_gas")):
                ratios[f"{prefix}{key}_over_{unit}"] = row[f"{prefix}{key}_erg"]/row[f"{prefix}{amount}_erg"]
    return ratios


def geometry_row(surface):
    row = {k: surface[k] for k in ("radius_kpc", "cell_count", "volume_kpc3", "sphere_fully_inside_domain", "domain_contact")}
    for name, patch in {**surface["geometry"], **surface["box_faces"]}.items():
        row.update({f"{name}_{k}": v for k, v in patch.items()})
    return row


def reduce_case(case, snapshots, endpoints, sources, contacts, audit):
    motion_rows, flux_rows, balances, geometries = [], [], [], []
    running = {}
    for i, measured in enumerate(endpoints):
        for aperture, data in measured.items():
            geometric = geometry_row(data["surfaces"]["current"])
            geometries.append(dict(case=case, index=i, actual_age_myr=snapshots[i]["age_myr"], aperture=aperture,
                                   cocoon_contacts_domain=contacts[i][0], cocoon_clearance_kpc=contacts[i][1], **geometric))
        if i == 0:
            continue
        a, b = snapshots[i-1], snapshots[i]
        seconds = (b["age_myr"]-a["age_myr"])*MYR
        for name in APERTURES:
            start, end = endpoints[i-1][name], measured[name]
            samples = (start["surfaces"]["current"], start["surfaces"]["next"],
                       end["surfaces"]["previous"], end["surfaces"]["current"])
            for u, v in ((samples[0], samples[2]), (samples[1], samples[3])):
                for category in ("geometry", "box_faces"):
                    for part, patch in u[category].items():
                        if patch["face_count"] != v[category][part]["face_count"]:
                            raise ValueError(f"Fixed-surface faces differ across {case}/{i}/{name}")
                        audit.equal("same fixed face area across endpoint states", patch["area_kpc2"], v[category][part]["area_kpc2"])
            base = dict(case=case, start_index=i-1, end_index=i, start_age_myr=a["age_myr"], end_age_myr=b["age_myr"],
                        aperture=name, start_radius_kpc=samples[0]["radius_kpc"], end_radius_kpc=samples[3]["radius_kpc"],
                        start_domain_contact=samples[0]["domain_contact"], end_domain_contact=samples[3]["domain_contact"],
                        start_geometry_complete=samples[0]["sphere_fully_inside_domain"],
                        end_geometry_complete=samples[3]["sphere_fully_inside_domain"],
                        start_cocoon_contacts_domain=contacts[i-1][0], end_cocoon_contacts_domain=contacts[i][0])
            motion = stock_motion(a["apertures"][name]["stock"], b["apertures"][name]["stock"],
                                  start["sweeps"]["current_to_next"], end["sweeps"]["previous_to_current"], audit)
            fields = {f"{term}_{k}": v for k, terms in motion.items() for term, v in terms.items()}
            history = with_cumulative(fields, running.setdefault((name, "motion"), {}))
            motion_rows.append({**base, **history})
            for k, (stock_key, _) in STOCK.items():
                audit.equal("cumulative moving stock versus endpoint", history[f"cumulative_change_{k}"],
                            b["apertures"][name]["stock"][stock_key],
                            max(abs(s["apertures"][name]["stock"][stock_key]) for s in snapshots[:i+1]))
            for method in METHODS:
                estimates = {rule: integrate_flux(samples, method, rule, seconds) for rule in WEIGHTS}
                for part in PARTS:
                    for field, rate in RATES.items():
                        estimate = estimates["symmetric_fixed"][part][field]
                        mean = 0.5*(estimates["old_fixed"][part][field] + estimates["new_fixed"][part][field])
                        scale = 0.25*seconds*math.fsum(abs(s["flux"][method][part][rate]) for s in samples)
                        audit.equal("symmetric transport equals mean of fixed-surface transports", estimate, mean, scale)
                for rule, parts in estimates.items():
                    prefix = {**base, "face_method": method, "integration_rule": rule}
                    for field, rate in RATES.items():
                        scale = seconds*math.fsum(w*abs(s["flux"][method][part][rate]) for part in PARTS[:2]
                                                  for w, s in zip(WEIGHTS[rule], samples, strict=True))
                        audit.equal("integrated internal plus box flux", parts["total"][field],
                                    parts["internal"][field]+parts["domain"][field], scale)
                    for part, amounts in parts.items():
                        sums = with_cumulative(amounts, running.setdefault((name, method, rule, part), {}))
                        flux_rows.append({**prefix, "boundary_part": part, **sums})
                    amounts = balance(motion, parts, sources[case, i-1, i], rule)
                    sums = with_cumulative(amounts, running.setdefault((name, method, rule), {}))
                    for t in ("", "cumulative_"):
                        audit.sum("signed local energy balance", sums[t+"aperture_residual_erg"],
                                  (sums[t+"stock_change_erg"], -sums[t+"membership_correction_erg"],
                                   sums[t+"total_energy_outward_erg"], -sums[t+"delivered_gas_erg"],
                                   -sums[t+"injector_potential_erg"], -sums[t+"maintained_stock_change_erg"]))
                    balances.append({**prefix, **sums, **normalized(sums)})
    return motion_rows, flux_rows, balances, geometries


def write_table(path, rows):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    raw = buf.getvalue().encode()
    if path.suffix == ".gz":
        with path.open("wb") as handle, gzip.GzipFile(filename="", fileobj=handle, mode="wb", mtime=0) as out:
            out.write(raw)
    else:
        path.write_bytes(raw)
    return {"rows": len(rows), "sha256": digest(path.read_bytes()), "expanded_csv_sha256": digest(raw)}


def endpoint_inventory(root, cases, stack):
    expected = {Path(case, f"snapshot_{i:04d}.json") for case, last in cases.items() for i in range(last+1)}
    found = {p.relative_to(root) for p in root.glob("*/snapshot_*.json")}
    archives = {p.name: p for p in root.glob("endpoints_*.zip")}
    if archives:
        if found or archives.keys() != {f"endpoints_{case}.zip" for case in cases}:
            raise ValueError("Mixed or incomplete endpoint ZIP cohort")
        members, file_hashes = {}, {}
        for case, last in cases.items():
            path = archives[f"endpoints_{case}.zip"]
            raw = path.read_bytes()
            file_hashes[path.name] = digest(raw)
            bundle = stack.enter_context(ZipFile(io.BytesIO(raw)))
            names = [x.filename for x in bundle.infolist() if not x.is_dir()]
            bare = {f"snapshot_{i:04d}.json" for i in range(last+1)}
            if len(names) != len(bare) or (set(names) != bare and set(names) != {f"{case}/{f}" for f in bare}):
                raise ValueError(f"Missing, duplicated or unexpected ZIP member in {path.name}")
            members.update({Path(case, Path(f).name): (bundle, f) for f in names})
        return lambda rel: members[rel][0].read(members[rel][1]), file_hashes
    if found != expected:
        raise ValueError(f"Wrong endpoint cohort: missing {sorted(expected-found)}, extra {sorted(found-expected)}")
    return lambda rel: (root/rel).read_bytes(), {}


def run(endpoints, output, registration=REGISTRATION, history_archive=HISTORY,
        history_verification=VERIFICATION, stage_sha256=None):
    reg = json.loads(checked(registration.read_bytes(), PINS["registration"], registration.name))
    cases = reg["cases"]
    if set(cases) != set(CASES):
        raise ValueError("Four registered production cases required")
    contacts = fixed_bindings(cases, json.loads(checked(gzip.decompress(FIXED_BASIS.read_bytes()),
                                                        PINS["fixed_stock_basis_uncompressed"], FIXED_BASIS.name)))
    review = json.loads(checked(history_verification.read_bytes(), PINS["injector_verification"], history_verification.name))
    audit = Audit()
    with ZipFile(io.BytesIO(checked(history_archive.read_bytes(), review["public_zip_sha256"], history_archive.name))) as archive:
        sources = source_intervals(cases, archive, review, csv_rows(checked(ANNUAL.read_bytes(), PINS["annual_review"], ANNUAL.name)),
                                   csv_rows(checked(MASS.read_bytes(), PINS["labelled_mass"], MASS.name)), audit)
    stage_proof = "supplied digest" if stage_sha256 else "common endpoint digest"
    manifest = endpoints.parent / "stage.sha256"
    if manifest.is_file():
        local_digest = digest(manifest.read_bytes())
        if stage_sha256 is not None and local_digest != stage_sha256:
            raise ValueError("Supplied stage digest differs from the adjacent stage manifest")
        stage_sha256, stage_proof = local_digest, "adjacent stage manifest" + (" and supplied digest" if stage_sha256 else "")
    hashes, products = {}, {}
    all_motion, all_primary, all_geometry = [], [], []
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack, TemporaryDirectory(dir=output.parent) as work:
        read_endpoint, zip_hashes = endpoint_inventory(endpoints, CASES, stack)
        stage_dir = Path(work) / "tables"
        stage_dir.mkdir()
        for case, last in CASES.items():
            source = cases[case]
            snaps = source["snapshots"]
            if [s["index"] for s in snaps] != list(range(last+1)) or snaps[0]["age_myr"] != 0:
                raise ValueError(f"Wrong registered indices or initial time at {case}")
            measured = []
            hashes[case] = {}
            for i, snap in enumerate(snaps):
                rel = Path(case, f"snapshot_{i:04d}.json")
                data = read_endpoint(rel)
                hashes[case][rel.name] = digest(data)
                payload = json.loads(data)
                if stage_sha256 is None:
                    stage_sha256 = payload["identity"]["stage_sha256"]
                if not isinstance(stage_sha256, str) or not re.fullmatch("[0-9a-f]{64}", stage_sha256):
                    raise ValueError("Invalid stage SHA-256")
                measured.append(validate_endpoint(payload, case, i, source, PINS["registration"], stage_sha256, audit))
                for aperture in snap["apertures"].values():
                    stock = aperture["stock"]
                    if (not aperture["available"] or aperture["raw_radius_kpc"] < source["max_maintained_radius_kpc"]
                            or not all(math.isfinite(v) for v in stock.values()) or (i == 0 and any(stock.values()))):
                        raise ValueError(f"Unusable registered stock or incomplete injector at {case}/{i}")
                    audit.sum("registered stock energy components", stock["total_delta_erg"],
                              (stock[STOCK[k][0]] for k in ENERGIES))
            motion, flux, balances, geometry = reduce_case(case, snaps, measured, sources, contacts[case], audit)
            for name, rows in ((f"transport_{case}.csv.gz", flux), (f"balances_{case}.csv.gz", balances)):
                products[name] = write_table(stage_dir/name, rows)
            all_motion.extend(motion)
            all_geometry.extend(geometry)
            all_primary.extend(r for r in balances if (r["face_method"], r["integration_rule"]) == (METHODS[0], "symmetric_fixed"))
        for name, rows in (("primary_balances.csv", all_primary), ("stock_motion.csv.gz", all_motion), ("geometry.csv.gz", all_geometry)):
            products[name] = write_table(stage_dir/name, rows)
        verification = {
            "source_sha256": {**PINS, "history_archive": review["public_zip_sha256"], "reducer": digest(Path(__file__).read_bytes())},
            "stage_sha256": stage_sha256, "stage_provenance": stage_proof, "endpoint_sha256": hashes,
            "endpoint_zip_sha256": zip_hashes,
            "snapshots": sum(n+1 for n in CASES.values()), "intervals": len(sources), "last_indices": CASES,
            "primary": {"face_method": METHODS[0], "integration_rule": "symmetric_fixed"},
            "outward_sign": "Positive leaves the selected native cells. Domain is the part on the simulation box.",
            "elapsed_seconds_per_myr": MYR, "injector": {"method": INJECTOR, "integration": "trapezoid", "box_method": FACE},
            "integration_sample_order": ["start_old", "start_new", "end_old", "end_new"], "integration_weights": WEIGHTS,
            "membership_correction": {"symmetric_fixed": "mean of start and end sweeps", "moving_endpoints": "mean of start and end sweeps",
                                      "old_fixed": "sweep measured at end", "new_fixed": "sweep measured at start"},
            "energy_balance": "stock change minus membership plus outward transport minus net gas, injector potential and maintained stock change",
            "mass_diagnostic": "Stock change minus membership plus outward transport and archived signed net injector mass are reported separately.",
            "cumulative": "Sum signed intervals from snapshot zero to end_index, then divide by cumulative denominators.",
            "products": products, "numerical_checks": audit.summary,
        }
        (stage_dir/"verification.json").write_text(json.dumps(verification, indent=2, allow_nan=False)+"\n")
        stage_dir.rename(output)
    return verification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoints", type=Path, required=True, help="Case subdirectories or endpoints_CASE.zip files")
    parser.add_argument("--output", type=Path, required=True, help="New directory for verified tables")
    parser.add_argument("--registration", type=Path, default=REGISTRATION)
    parser.add_argument("--history-archive", type=Path, default=HISTORY)
    parser.add_argument("--history-verification", type=Path, default=VERIFICATION)
    parser.add_argument("--stage-sha256", help="SHA-256 of the stage.sha256 manifest used to submit the jobs")
    args = parser.parse_args()
    results = run(**vars(args))
    print(f"Reduced {results['snapshots']} endpoints and {results['intervals']} intervals into {args.output}")
