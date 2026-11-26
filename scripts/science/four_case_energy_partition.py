"""Partition signed native energy changes by current jet tracer and measured injector supply."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_tracer_mass_budget import FIXED
from compare_fixed_histories import RECEIPTS
from restate_native_delivery import CASES, PRIMARY, SECONDS

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs/science/assets"
SPHERES = ASSETS / "turn15_review_2026-11-11"
INJECTOR = ASSETS / "production_injector_histories_2026-11-21"
ENTHALPY = ASSETS / "native_delivery_restatement_2026-11-21"
PUBLISHED = ASSETS / "four_case_energy_partition_2026-11-26"
BASIS = "native_fixed_stocks.json.gz"
BASIS_SHA = "f9df74456fa22d0f321e44c3439ddae38671d2a190b200fc482c0a93072fdf20"
PINS = {
    SPHERES / "review_manifest.json": "20a782b396b1772ee48d0d346fde9715a42af57458cba9a8addaa981cf0e5726",
    INJECTOR / "verification.json": "9cdf21211f3f891ee5e805808412a4424e2a63e93848279ca4fca167676d0647",
    ENTHALPY / "verification.json": "76b4d15678936241ebf44a3c117c6cacdf8c5845e3dfeba527d533f600d53bef",
}
APERTURES = ("R100", "R300")
BOXES = ("whole_grid", "fixed_inset_box", "outside_fixed_inset_box")
REGIONS = ("all", "cocoon", "ambient")
ENERGY = ("thermal", "kinetic", "gravitational", "total")
ENERGY_KEYS = tuple(f"{component}_delta_erg" for component in ENERGY)
MASS_KEYS = ("initial_mass_g", "current_mass_g", "mass_delta_g")
STOCK_KEYS = ("cell_count", "volume_kpc3", *MASS_KEYS, *ENERGY_KEYS)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(path, expected):
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError(f"SHA-256 mismatch: {path.name}")
    return raw


def csv_rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode())))


def write_table(path, rows):
    with path.open("w", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def pack_fixed(private):
    """Copy only numerical fields and scientific input digests from the four accepted receipts."""
    basis = {}
    for case, last in CASES.items():
        directory = private / FIXED[case] / f"fixed_{case}_full"
        receipt = json.loads(checked(directory / "completion.json", RECEIPTS[case]))
        products = {Path(r["path"]).name: r["sha256"] for r in receipt["products"]}
        if (receipt["case"] != case or receipt["indices"] != list(range(last + 1))
                or set(products) != {f"snapshot_{i:04d}.json" for i in range(last + 1)}
                or len(receipt["products"]) != last + 1):
            raise ValueError(f"Fixed history inventory differs for {case}")
        snapshots = []
        for index in receipt["indices"]:
            name = f"snapshot_{index:04d}.json"
            snap = json.loads(checked(directory / name, products[name]))
            if (snap["case"], snap["snapshot_index"], snap["execution_status"]) != (
                    case, index, "completed_fixed_box_energy_and_mass_measurement"):
                raise ValueError(f"Wrong fixed snapshot: {case}/{index}")
            sources = {r["role"]: r["sha256"] for r in snap["provenance"]["inputs"]}
            if (set(sources) != {"current_h5", "initial_h5", "environment", "grid_file"}
                    or snap["shape_nz_ny_nx"] != [1014, 960, 960]
                    or snap["tracer_diagnostics"]["outside_unit_interval_cell_count"] != 0):
                raise ValueError(f"Unverified sources, tracer or mesh: {case}/{index}")
            stocks = {}
            for aperture in (*APERTURES, *BOXES):
                parts = snap["regions"][aperture]
                if not parts["partition_identity"]["pass"]:
                    raise ValueError(f"Source partition identity failed: {case}/{index}/{aperture}")
                stocks[aperture] = {}
                for region in REGIONS:
                    row = parts["partitions"][region]
                    if not (row["potential_zero_shift"]["identity_pass"] and row["mass_balance_identity"]["pass"]):
                        raise ValueError(f"Source mass or potential identity failed: {case}/{index}")
                    stocks[aperture][region] = [row[k] for k in STOCK_KEYS]
            cover = snap["operational_coverage"]["current_cocoon"]
            snapshots.append({
                "index": index, "age_myr": snap["actual_time_myr"], "label_erg": snap["labelled_input_erg"],
                "snapshot_sha256": products[name], "native_input_sha256": sources,
                "fixed_box_faces_kpc": snap["fixed_box_cell_faces_kpc"], "pi_erg": snap["native_lobe"]["pressure_volume_integral_erg"],
                "cocoon_contacts_domain": cover["contacts_domain_face"], "cocoon_clearance_kpc": cover["extent"]["minimum_domain_face_margin_kpc"],
                "speed_apertures": snap["speed_apertures"], "stocks": stocks,
            })
        basis[case] = {"completion_sha256": RECEIPTS[case], "snapshots": snapshots}
    return json.dumps({"stock_columns": STOCK_KEYS, "cases": basis}, ensure_ascii=True, allow_nan=False,
                      sort_keys=True, separators=(",", ":")).encode() + b"\n"


class Closure:
    def __init__(self):
        self.summary = {}

    def check(self, group, lhs, rhs, scale, context):
        relative = abs(lhs - rhs) / max(abs(lhs), abs(rhs), abs(scale), 1.)
        if not math.isfinite(relative) or relative > 2e-11:
            raise ValueError(f"{group} disagreement in {context}: {lhs} vs {rhs}")
        item = self.summary.setdefault(group, {"count": 0, "max_scaled_error": 0.0})
        item["count"] += 1
        item["max_scaled_error"] = max(item["max_scaled_error"], relative)


def deliveries(case, last, bundle, receipt, audit):
    def table(name):
        path = f"native/summary/{case}/{name}.csv"
        raw = bundle.read(path)
        if sha(raw) != receipt["public_member_sha256"][path]:
            raise ValueError(f"Wrong injector table digest: {path}")
        return csv_rows(raw)

    snapshot = [r for r in table("injector_snapshot_rates") if r["method"] == PRIMARY[0]]
    rates = {(int(r["index"]), r["region"]): r for r in snapshot}
    intervals = [r for r in table("injector_interval_balances") if (r["method"], r["rule"]) == PRIMARY]
    by_end = {int(r["end_index"]): r for r in intervals}
    if (set(rates) != {(i, r) for i in range(last + 1) for r in ("cap", "stationary", "net")}
            or len(rates) != len(snapshot) or len(intervals) != last or set(by_end) != set(range(1, last + 1))
            or any(r["case"] != case for r in snapshot + intervals)):
        raise ValueError(f"Primary injector history incomplete or mislabelled: {case}")
    power = 2e45 if case.endswith("HI") else 2e43
    supplied = []
    increments = {"cap": [], "stationary": [], "net": []}
    for i in range(last + 1):
        age = float(rates[i, "net"]["age_myr"])
        for region in increments:
            if float(rates[i, region]["age_myr"]) != age:
                raise ValueError(f"Inconsistent injector ages for {case}/{i}")
        if i == 0:
            if age != 0:
                raise ValueError(f"Nonzero initial age: {case}")
        else:
            start = supplied[-1]["actual_age_myr"]
            if age <= start or int(by_end[i]["start_index"]) != i - 1:
                raise ValueError(f"Non-consecutive injector interval: {case}/{i}")
            label_interval = power * (min(age, 50.) - min(start, 50.)) * SECONDS
            for region, terms in increments.items():
                mean_rate = 0.5 * (float(rates[i-1, region]["gas_energy_over_label"])
                                   + float(rates[i, region]["gas_energy_over_label"]))
                change = mean_rate * power * (age - start) * SECONDS
                audit.check("instantaneous_vs_interval", change, float(by_end[i][f"{region}_gas"]) * label_interval,
                            label_interval, (case, i, region))
                terms.append(change)
        cap, still, net = (math.fsum(increments[k]) for k in ("cap", "stationary", "net"))
        audit.check("cumulative_signed_regions", cap + still, net, net, (case, i))
        if i and net <= 0:
            raise ValueError(f"Nonpositive cumulative delivery at {case}/{i}")
        supplied.append({"actual_age_myr": age, "labelled_input_erg": power * min(age, 50.) * SECONDS,
                         "cumulative_net_gas_delivery_erg": net, "cumulative_cone_gas_delivery_erg": cap,
                         "cumulative_stationary_gas_delivery_erg": still})
    return supplied


def partition_case(case, source, sphere, supply, historical, audit):
    last = CASES[case]
    if (source["completion_sha256"] != RECEIPTS[case]
            or [s["index"] for s in source["snapshots"]] != list(range(last + 1))):
        raise ValueError(f"Fixed source identity or ages differ: {case}")
    spherical = {(int(r["snapshot_index"]), "R" + r["speed_threshold_km_s"]): r for r in sphere}
    if (set(spherical) != {(i, a) for i in range(last+1) for a in APERTURES}
            or len(spherical) != len(sphere) or any(r["case"] != case for r in sphere)):
        raise ValueError(f"Wrong spherical cohort: {case}")
    snapshots, spheres, boxes = [], [], []
    for i, (snap, denom) in enumerate(zip(source["snapshots"], supply, strict=True)):
        gas = denom["cumulative_net_gas_delivery_erg"]
        label = denom["labelled_input_erg"]
        audit.check("actual_age", snap["age_myr"], denom["actual_age_myr"], 1., (case, i))
        audit.check("label", snap["label_erg"], label, label, (case, i))
        if snap["age_myr"] != denom["actual_age_myr"]:
            raise ValueError(f"Primary age mismatch in {case}/{i}")
        identity = {"case": case, "snapshot_index": i, "actual_age_myr": snap["age_myr"]}
        first = spherical[i, "R100"]
        enthalpy = float(first["native_enthalpy_2.5_erg"])
        audit.check("whole_lobe_pv", enthalpy, 2.5 * snap["pi_erg"], enthalpy, (case, i))
        snapshots.append({**identity, **denom, "native_lobe_2p5pV_erg": enthalpy, "native_lobe_4pV_erg": 1.6*enthalpy,
                          "native_lobe_2p5pV_over_delivery": enthalpy / gas if gas else None,
                          "native_lobe_4pV_over_delivery": 1.6*enthalpy / gas if gas else None,
                          "cocoon_contacts_domain": snap["cocoon_contacts_domain"], "cocoon_clearance_kpc": snap["cocoon_clearance_kpc"],
                          **{f"{k}_sha256": v for k, v in snap["native_input_sha256"].items()},
                          "fixed_snapshot_sha256": snap["snapshot_sha256"]})
        stored = {scope: {r: dict(zip(STOCK_KEYS, vals, strict=True)) for r, vals in parts.items()}
                  for scope, parts in snap["stocks"].items()}
        for scope in (*APERTURES, *BOXES):
            raw = stored[scope]
            geometry = {}
            if scope in APERTURES:
                older = spherical[i, scope]
                geo = snap["speed_apertures"][scope]
                audit.check("actual_age", float(older["actual_time_myr"]), snap["age_myr"], 1., (case, i, scope))
                audit.check("radius", float(older["raw_radius_kpc"]), geo["raw_radius_kpc"], 1., (case, i, scope))
                if (older["domain_geometry_status"] == "complete_sphere") != geo["geometrically_complete_in_domain_box"]:
                    raise ValueError(f"Domain geometry mismatch: {case}/{i}/{scope}")
                for r in REGIONS:
                    for key in ENERGY_KEYS:
                        audit.check("two_native_stock_reductions", float(older[f"{r}_{key}"]), raw[r][key], label, (case, i, scope, r, key))
                audit.check("whole_lobe_pv", float(older["native_enthalpy_4_erg"]), 1.6*enthalpy, enthalpy, (case, i, scope))
                geometry = {"raw_radius_kpc": geo["raw_radius_kpc"], "domain_geometry": older["domain_geometry_status"],
                            "inside_40kpc_inset": "boundary_safe_box_conflict" not in older["measurement_hold_codes"].split(";"),
                            "inside_50kpc_inset": geo["geometrically_complete_in_fixed_inset_box"],
                            "all_lobe_cells_enclosed": raw["cocoon"]["cell_count"] == stored["whole_grid"]["cocoon"]["cell_count"]}
            for key in STOCK_KEYS:
                audit.check("cocoon_plus_ambient", raw["cocoon"][key] + raw["ambient"][key], raw["all"][key],
                            abs(raw["cocoon"][key]) + abs(raw["ambient"][key]), (case, i, scope, key))
            for r in REGIONS:
                values = raw[r]
                audit.check("three_energy_components", math.fsum(values[k] for k in ENERGY_KEYS[:3]), values["total_delta_erg"],
                            label, (case, i, scope, r))
                audit.check("mass_delta", values["current_mass_g"] - values["initial_mass_g"], values["mass_delta_g"],
                            values["initial_mass_g"], (case, i, scope, r))
                if scope == "whole_grid":
                    for k in STOCK_KEYS:
                        pair = (stored["fixed_inset_box"][r][k], stored["outside_fixed_inset_box"][r][k])
                        audit.check("box_plus_shell", sum(pair), values[k], sum(abs(v) for v in pair), (case, i, r, k))
                if i == 0 and any(values[k] != 0 for k in (*ENERGY_KEYS, "mass_delta_g")):
                    raise ValueError(f"Nonzero initial regional change: {case}/{scope}/{r}")
                row = {**identity, "aperture": scope, "region": r, **geometry,
                       "cocoon_contacts_domain": snap["cocoon_contacts_domain"], "cocoon_clearance_kpc": snap["cocoon_clearance_kpc"],
                       "cumulative_net_gas_delivery_erg": gas, **values,
                       **{f"{key}_over_delivery": values[f"{key}_delta_erg"]/gas if gas else None for key in ENERGY}}
                (spheres if scope in APERTURES else boxes).append(row)
        if (case, i) in historical:
            old = historical[case, i]
            quantities = {"R100_stored_change_erg": stored["R100"]["all"]["total_delta_erg"],
                          "cumulative_net_gas_delivery_erg": gas, "native_2p5pv_over_cumulative_net_gas": enthalpy/gas,
                          "native_4pv_over_cumulative_net_gas": 1.6*enthalpy/gas}
            for key, actual in quantities.items():
                audit.check("published_selected_ages", actual, float(old[key]), 0., (case, i, key))
    return snapshots, spheres, boxes


def plot_aperture(rows, aperture, output):
    styles = (("thermal", "#26609a", "-"), ("kinetic", "#c26722", "-"), ("gravitational", "#318068", "-"),
              ("total", "#303030", "--"))
    fig, axes = plt.subplots(3, 4, figsize=(11.8, 7.3), sharex=True, sharey=True, layout="constrained")
    for col, case in enumerate(CASES):
        for row, region in enumerate(("cocoon", "ambient", "all")):
            ax = axes[row, col]
            selected = [r for r in rows if r["case"] == case and r["region"] == region and r["aperture"] == aperture and r["snapshot_index"]]
            ages = [r["actual_age_myr"] for r in selected]
            truncated = [r["actual_age_myr"] for r in selected if r["domain_geometry"] != "complete_sphere"]
            if truncated:
                ax.axvspan(truncated[0], ages[-1], color="#e9e6df", zorder=-2)
            ax.axhline(0, color="#9a9a9a", lw=.6)
            for name, colour, line in styles:
                ax.plot(ages, [r[f"{name}_over_delivery"] for r in selected], color=colour, ls=line,
                        lw=1.6, label=name.capitalize())
            ax.set(xlim=(0, 50), xticks=(0, 10, 20, 30, 40, 50), ylim=(-.26, 1.32),
                   yticks=(-.25, 0, .25, .5, .75, 1, 1.25))
            ax.spines[["top", "right"]].set_visible(False)
            if col == 0:
                label = "All gas" if region == "all" else region.capitalize()
                ax.set_ylabel(f"{label}\nΔE / delivered gas energy", fontsize=9)
            if row == 0:
                ax.set_title(case)
    axes[0, 0].legend(frameon=False, fontsize=8, loc="upper right", ncols=1)
    fig.supxlabel("Actual age (Myr)", fontsize=10)
    fig.suptitle(f"Signed energy changes within {aperture}", fontsize=14)
    fig.savefig(output, dpi=155)
    plt.close(fig)


def run(out, fixed_root=None):
    if out.exists():
        raise FileExistsError(f"Use a fresh output directory: {out}")
    receipts = {p: json.loads(checked(p, pin)) for p, pin in PINS.items()}
    basis = pack_fixed(fixed_root) if fixed_root else gzip.decompress((PUBLISHED / BASIS).read_bytes())
    if sha(basis) != BASIS_SHA:
        raise ValueError(f"Compact fixed-stock payload differs: {sha(basis)}")
    native = json.loads(basis)
    if tuple(native["stock_columns"]) != STOCK_KEYS or native["cases"].keys() != CASES.keys():
        raise ValueError("Incomplete compact source or changed stock columns")
    sh = receipts[SPHERES / "review_manifest.json"]["files"]
    inj = receipts[INJECTOR / "verification.json"]
    archive = checked(INJECTOR / "history_tables.zip", inj["public_zip_sha256"])
    hist = receipts[ENTHALPY / "verification.json"]["products_sha256"]["primary_selected_ages.csv"]
    hrows = csv_rows(checked(ENTHALPY / "primary_selected_ages.csv", hist))
    old = {(r["case"], int(r["snapshot_index"])): r for r in hrows}
    if set(old) != {(c, i) for c, last in CASES.items() for i in (10, 20, 30, 40, 50) if i <= last} or len(hrows) != len(old):
        raise ValueError("Incomplete published selected-age reference")
    audit = Closure()
    snapshots, sphere_rows, fixed_rows = [], [], []
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        for case, last in CASES.items():
            relative = f"budgets/{case}/measurements.csv"
            spherical = csv_rows(checked(SPHERES / relative, sh[relative]["sha256"]))
            delivered = deliveries(case, last, bundle, inj, audit)
            s, a, b = partition_case(case, native["cases"][case], spherical, delivered, old, audit)
            snapshots.extend(s)
            sphere_rows.extend(a)
            fixed_rows.extend(b)
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as tmp:
        work = Path(tmp) / "result"
        work.mkdir()
        with (work / BASIS).open("wb") as stream, gzip.GzipFile(fileobj=stream, filename="", mode="wb", mtime=0) as writer:
            writer.write(basis)
        write_table(work / "snapshots.csv", snapshots)
        write_table(work / "sphere_components.csv", sphere_rows)
        write_table(work / "box_components.csv", fixed_rows)
        selected = [r for r in sphere_rows if (r["case"], r["snapshot_index"]) in old or (r["case"], r["snapshot_index"]) == ("G-HI", 47)]
        write_table(work / "selected_age_components.csv", selected)
        for ap in APERTURES:
            plot_aperture(sphere_rows, ap, work / f"{ap}_components.png")
        verification = {"case_last_indices": CASES, "retained_snapshots": len(snapshots), "positive_age_intervals": sum(CASES.values()),
                        "sphere_rows": len(sphere_rows), "fixed_rows": len(fixed_rows), "published_selected_ages": len(old),
                        "primary_injector": list(PRIMARY), "fixed_completion_sha256": RECEIPTS,
                        "compact_source_uncompressed_sha256": sha(basis), "pinned_receipts": {str(p.relative_to(ROOT)): v for p, v in PINS.items()},
                        "checks": audit.summary, "source_sha256": sha(Path(__file__).read_bytes()),
                        "products_sha256": {p.name: sha(p.read_bytes()) for p in sorted(work.iterdir())}}
        (work / "verification.json").write_text(json.dumps(verification, indent=2, allow_nan=False) + "\n")
        work.rename(out)
    return verification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--fixed-root", type=Path, help="Re-extract the compact basis from the original private archive root")
    args = parser.parse_args()
    run(args.out, args.fixed_root)
