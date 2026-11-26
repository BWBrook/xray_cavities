"""Measure maintained gas mass and test signed interval and cumulative aperture mass conservation.

Residual = change of perturbed aperture stock - membership change + outward mass
transport - signed injector delivery - maintained-region mass change. For the
absolute transport scale, add the magnitudes of the interval's net aperture,
cone and stationary injector terms. Face-level inflow and outflow can cancel
within each term. Cumulative ratios sum their gram numerators and denominators
from time zero before division.
"""
import argparse
import gzip
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import tarfile
from zipfile import ZipFile

import numpy as np

from four_case_energy_partition import ASSETS, PUBLISHED, checked, csv_rows
from pluto_h5_level3_ambient_extract import UNIT_DENSITY_CGS, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS
from restate_native_delivery import CASES, PRIMARY, ROOT, SECONDS
from summarise_aperture_transport import APERTURES, HISTORY, METHODS, PINS, REGISTRATION, VERIFICATION, WEIGHTS
from summarise_aperture_transport import write_table as write_product


DIRECTORY = ASSETS / "aperture_transport_2026-11-26"
MAINTAINED = DIRECTORY / "maintained_masses.csv"
MAINTAINED_SHA = "f1d509d24617998227bdd34c7681a9f8ca1e7d713441c6ec40d064a54b05e993"
PATCHES = ROOT / "private_archive/incoming/injector_full_2026-11-21/production_injector_201.tar.gz"
SECTORS = ("cap", "stationary", "net")
TERMS = ("mass_change_g", "mass_membership_correction_g", "mass_outward_g", "delivered_mass_g",
         "maintained_mass_change_g", "labelled_mass_g", "abs_net_aperture_and_injector_sectors_g", "abs_net_injector_sectors_g")


def public_rates(review):
    result = {}
    with ZipFile(io.BytesIO(checked(HISTORY, review["public_zip_sha256"]))) as archive:
        for case, last in CASES.items():
            name = f"native/summary/{case}/injector_snapshot_rates.csv"
            raw = archive.read(name)
            if hashlib.sha256(raw).hexdigest() != review["public_member_sha256"][name]:
                raise ValueError(f"Public rate table hash differs for {case}")
            for row in csv_rows(raw):
                key = (row["case"], int(row["index"]))
                if key[0] != case or not 0 <= key[1] <= last:
                    raise ValueError(f"Unexpected injector endpoint {key}")
                info = result.setdefault(key, {"patch_sha256": row["patch_sha256"], "age_myr": float(row["age_myr"])})
                if info["patch_sha256"] != row["patch_sha256"] or info["age_myr"] != float(row["age_myr"]):
                    raise ValueError(f"Public rates do not identify one patch at {key}")
                if row["method"] == PRIMARY[0]:
                    sector = row["region"]
                    if sector not in SECTORS or sector in info:
                        raise ValueError(f"Duplicated or unknown primary sector at {key}")
                    info[sector] = float(row["mass_over_label"])
    if (set(result) != {(c, i) for c, last in CASES.items() for i in range(last + 1)}
            or any(set(SECTORS).difference(r) for r in result.values())):
        raise ValueError("Incomplete source-bound injector rates")
    return result


def maintained_masses(path):
    review = json.loads(checked(VERIFICATION, PINS["injector_verification"]))
    with path.open("rb") as stream:
        archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    prefixes = {review["archive"]["archive_sha256"]: "native/results", review["raw_histories_archive_sha256"]: "results"}
    if archive_hash not in prefixes:
        raise ValueError("Unrecognised injector patch archive")
    prefix = prefixes[archive_hash]
    rates = public_rates(review)
    registration = json.loads(checked(REGISTRATION, PINS["registration"]))["cases"]
    rows = {}
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            hit = re.fullmatch(rf"{prefix}/([CG]-(?:HI|LO))/patch/patch_(\d{{4}})\.npz", member.name)
            if not hit:
                continue
            key = case, index = hit[1], int(hit[2])
            if not member.isfile() or key not in rates or key in rows:
                raise ValueError(f"Unexpected or duplicated injector patch {key}")
            data = archive.extractfile(member).read()
            info, case_reg = rates[key], registration[case]
            if hashlib.sha256(data).hexdigest() != info["patch_sha256"]:
                raise ValueError(f"Injector patch differs from the public rate tables at {key}")
            with np.load(io.BytesIO(data), allow_pickle=False) as patch:
                z, y, x = np.ix_(*(patch[a].astype(float) for a in "zyx"))
                dz, dy, dx = np.ix_(*(np.diff(patch[a + "_edges"].astype(float)) for a in "zyx"))
                r2 = x*x + y*y + z*z
                mask = r2 <= .75**2
                rho = patch["rho"][mask]
                volumes = (dx*dy*dz)[mask]
            if (rho.dtype != np.dtype("<f4") or rho.size != case_reg["maintained_cells"] or rho.size != 14328
                    or not np.all(np.isfinite(rho) & (rho > 0)) or not np.all(np.isfinite(volumes) & (volumes > 0))
                    or math.sqrt(r2[mask].max()) != case_reg["max_maintained_radius_kpc"]
                    or info["age_myr"] != case_reg["snapshots"][index]["age_myr"]):
                raise ValueError(f"Invalid grid, age or maintained cell census at {key}")
            mass = math.fsum(rho.astype(float) * volumes) * UNIT_DENSITY_CGS * UNIT_LENGTH_CM**3
            rows[key] = {"case": case, "snapshot_index": index, "actual_age_myr": info["age_myr"],
                         "maintained_cell_count": rho.size, "maintained_mass_g": mass,
                         "maintained_volume_kpc3": math.fsum(volumes),
                         "selected_native_rho_sha256": hashlib.sha256(rho.tobytes()).hexdigest(),
                         "patch_sha256": info["patch_sha256"]}
    if rows.keys() != rates.keys():
        raise ValueError("Archive did not yield all 201 injector patches")
    selected = checked(PUBLISHED / "sphere_components.csv", "b4684a7dbe097fe0bf26a276243067fe1fd0203230db4ab200f6241075f28d9d")
    for r in csv_rows(selected):
        if r["snapshot_index"] == "0" and r["region"] == "all":
            if not math.isclose(rows[r["case"], 0]["maintained_mass_g"], float(r["current_mass_g"]), rel_tol=1e-13):
                raise ValueError(f"Maintained mass differs from the native {r['aperture']} stock at time zero")
    ordered = []
    for (case, i), row in sorted(rows.items()):
        row["mass_change_from_initial_g"] = row["maintained_mass_g"] - rows[case, 0]["maintained_mass_g"]
        row["mass_change_from_previous_g"] = row["maintained_mass_g"] - rows[case, i-1]["maintained_mass_g"] if i else None
        ordered.append(row)
    return ordered


def quantities(row, sources, case):
    start, end = (int(row[k]) for k in ("start_index", "end_index"))
    a, b = sources[case, start], sources[case, end]
    if (end != start + 1 or float(row["start_age_myr"]) != a["age_myr"]
            or float(row["end_age_myr"]) != b["age_myr"]):
        raise ValueError(f"Mass-budget endpoint mismatch at {case}/{start}–{end}")
    elapsed = (b["age_myr"] - a["age_myr"]) * SECONDS
    active = (min(b["age_myr"], 50.) - min(a["age_myr"], 50.)) * SECONDS
    power = 2e45 if case.endswith("HI") else 2e43
    mass_rate = 2*power / (.1*UNIT_VELOCITY_CMS)**2
    delivered = {s: .5*(a[s]+b[s])*mass_rate*elapsed for s in SECTORS}
    terms = {k: float(row[k]) for k in TERMS[:4]}
    absolute_sectors = abs(delivered["cap"]) + abs(delivered["stationary"])
    terms.update(maintained_mass_change_g=b["maintained_mass_g"] - a["maintained_mass_g"],
                 labelled_mass_g=float(row["labelled_mass_g"]),
                 abs_net_aperture_and_injector_sectors_g=abs(terms["mass_outward_g"]) + absolute_sectors,
                 abs_net_injector_sectors_g=absolute_sectors)
    label = terms["labelled_mass_g"]
    for left, right in ((label, mass_rate*active), (terms["delivered_mass_g"], delivered["net"]),
                        (delivered["net"], delivered["cap"] + delivered["stationary"]),
                        (float(row["mass_change_minus_membership_plus_outward_g"]),
                         math.fsum((terms["mass_change_g"], -terms["mass_membership_correction_g"], terms["mass_outward_g"])))):
        scale = max(abs(left), abs(right), label)
        if not all(map(math.isfinite, (left, right))) or abs(left-right) > 2e-11*scale:
            raise ValueError(f"Independent source, label or aperture subtotal disagrees at {case}/{end}")
    if label <= 0 or not all(map(math.isfinite, terms.values())):
        raise ValueError(f"Nonfinite budget or nonpositive labelled mass at {case}/{end}")
    return terms


def residual(terms):
    change, motion, outward, injected, maintained, label, absolute, sector_sum = (terms[k] for k in TERMS)
    value = math.fsum((change, -motion, outward, -injected, -maintained))
    # The signed ratio loses arithmetic resolution when net delivery cancels to roundoff.
    return {"mass_residual_g": value, "mass_residual_over_label": value / label,
            "mass_residual_over_signed_delivery": value/injected if abs(injected) > 64*math.ulp(max(label, sector_sum)) else None,
            "mass_residual_over_abs_aperture_and_injector_sectors": value/absolute if absolute else None,
            "signed_delivery_over_label": injected/label,
            "signed_delivery_over_abs_injector_sectors": injected/sector_sum if sector_sum else None}


def case_balances(case, last, rows, sources):
    series = {}
    for row in rows:
        key = row["aperture"], row["face_method"], row["integration_rule"]
        i = int(row["end_index"])
        segment = series.setdefault(key, {})
        if row["case"] != case or i in segment:
            raise ValueError(f"Incorrect or duplicate mass balance at {case}/{i}/{key}")
        segment[i] = row
    if set(series) != set(itertools.product(APERTURES, METHODS, WEIGHTS)):
        raise ValueError(f"Missing registered aperture or sensitivity for {case}")
    result = []
    for (aperture, method, rule), segment in sorted(series.items()):
        if set(segment) != set(range(1, last+1)):
            raise ValueError(f"Incomplete cumulative mass history for {case}/{aperture}/{method}/{rule}")
        running = {k: [] for k in TERMS}
        for i, row in sorted(segment.items()):
            terms = quantities(row, sources, case)
            for k in TERMS:
                running[k].append(terms[k])
            cumulative = {k: math.fsum(seq) for k, seq in running.items()}
            for k in (*TERMS[:4], "labelled_mass_g"):
                expected = float(row[f"cumulative_{k}"])
                if not math.isfinite(expected) or abs(cumulative[k]-expected) > 2e-11*max(cumulative["labelled_mass_g"], math.fsum(map(abs, running[k]))):
                    raise ValueError(f"Independent cumulative {k} differs at {case}/{i}")
            base = {k: row[k] for k in ("case", "start_index", "end_index", "start_age_myr", "end_age_myr",
                                         "aperture", "face_method", "integration_rule", "end_geometry_complete", "end_cocoon_contacts_domain")}
            result.append({**base, **terms, **residual(terms),
                           **{f"cumulative_{k}": v for k, v in {**cumulative, **residual(cumulative)}.items()}})
    return result


def balances(directory, maintained_file):
    review = json.loads(checked(VERIFICATION, PINS["injector_verification"]))
    sources = public_rates(review)
    stored = csv_rows(checked(maintained_file, MAINTAINED_SHA))
    matched = {(r["case"], int(r["snapshot_index"])): r for r in stored}
    if len(matched) != len(stored) or matched.keys() != sources.keys():
        raise ValueError("Wrong maintained-mass inventory")
    for key, s in sources.items():
        row = matched[key]
        if row["patch_sha256"] != s["patch_sha256"] or float(row["actual_age_myr"]) != s["age_myr"]:
            raise ValueError(f"Wrong maintained-mass source at {key}")
        s["maintained_mass_g"] = float(row["maintained_mass_g"])
    manifest = json.loads((directory/"verification.json").read_bytes())
    if manifest["source_sha256"]["registration"] != PINS["registration"] or manifest["last_indices"] != CASES:
        raise ValueError("Aperture balances have a different source cohort")
    result = []
    for case, last in CASES.items():
        name = f"balances_{case}.csv.gz"
        product = manifest["products"][name]
        raw = gzip.decompress(checked(directory/name, product["sha256"]))
        if hashlib.sha256(raw).hexdigest() != product["expanded_csv_sha256"]:
            raise ValueError(f"Expanded mass-balance table digest differs for {case}")
        result.extend(case_balances(case, last, csv_rows(raw), sources))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    inventory = sub.add_parser("maintained", help="Recover total gas mass from either verified 201-patch archive")
    inventory.add_argument("--archive", type=Path, default=PATCHES)
    inventory.add_argument("--out", type=Path, default=MAINTAINED)
    budget = sub.add_parser("balances", help="Signed residuals for all 197 intervals, both apertures and all eight surface rules")
    budget.add_argument("--tables", type=Path, default=DIRECTORY / "tables")
    budget.add_argument("--maintained", type=Path, default=MAINTAINED)
    budget.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = maintained_masses(args.archive) if args.mode == "maintained" else balances(args.tables, args.maintained)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_product(args.out, result)
