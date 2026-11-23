"""Audit the high-power lobe comparison from native receipts, cell centres and signed injector rates."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

import numpy as np


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
PUBLISHED = ASSETS / "entropy_restart_lobes_2026-11-23"
SECONDS_PER_MYR = 3.15576e13
POWER = 2e45
CASES = ("G-HI", "C-HI")
CUTS = (.001, .005, .01)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, context):
    if not condition:
        raise ValueError(context)


def close(a, b, context, *, absolute=0.):
    if not math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=absolute):
        raise ValueError(f"{context}: {a} versus {b}")


def csv_rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))


def geometry():
    path = ASSETS / "g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/remote_stage/completion_evidence/grid.out"
    lines = iter(s.strip() for s in path.read_text().splitlines() if s.strip() and not s.lstrip().startswith("#"))
    axes = []
    for count in (960, 960, 1014):
        require(int(next(lines)) == count, "native grid axis length")
        edges = np.asarray([next(lines).split()[1:] for _ in range(count)], dtype=float)
        axes.append(edges.mean(axis=1).astype("<f4").astype("<f8"))
    # All centres match the independent archived G-HI and C-HI HDF5 axes, including float32 quantisation.
    centres_sha = digest(b"".join(axis.tobytes() for axis in axes))
    require(centres_sha == "9ed6b14b9117795fec014a0b1729fe01f2edafdd9d4c8a72dfbecb83cbdd7462", "cell centres")
    x, y, z = axes
    xy2 = np.sort((x[None,:]**2 + y[:,None]**2).ravel())
    def count(radius):
        lo, hi = np.zeros(z.shape, dtype=int), np.full(z.shape, len(xy2))
        while (lo < hi).any():
            middle = (lo+hi)//2
            inside = np.sqrt(xy2[np.minimum(middle, len(xy2)-1)] + z*z) <= radius
            active = lo < hi
            lo, hi = np.where(active & inside, middle+1, lo), np.where(active & ~inside, middle, hi)
        return int(lo.sum())
    return axes, centres_sha, count


def gas_curve(case, arm, historical, snapshots):
    name = f"native/summary/{case}/injector_snapshot_rates.csv"
    parts = {r: {} for r in ("cap", "stationary")}
    for row in csv_rows(historical.read(name)):
        i = int(row["index"])
        if i <= 10 and row["method"] == "linear_snapshot_flags" and row["region"] in parts:
            parts[row["region"]][i] = (float(row["age_myr"]), POWER*float(row["gas_energy_over_label"]))
    times, rates = [], []
    for i in range(11):
        age, cone = parts["cap"][i]
        require(age == parts["stationary"][i][0], "historical rate times")
        times.append(age)
        rates.append(cone+parts["stationary"][i][1])
    for i in range(10, 31):
        a = "ON" if i == 10 else arm
        s = json.loads(snapshots.read(f"snapshots/{case}/{a}/injector_{i}.json"))
        flux = math.fsum(s["rates"]["linear_snapshot_flags"][k]["gas_energy_erg_s"] for k in parts)
        if i == 10:
            close(flux, rates[-1], "production and common seed gas flux")
            require(times[-1] == s["age_myr"], "common seed age")
        else:
            times.append(s["age_myr"])
            rates.append(flux)
    require(times[0] == 0 and times[-1] == 12 and all(b > a for a,b in zip(times,times[1:])), "delivery ages")
    def integral(age):
        stop = int(np.searchsorted(times, age))
        age_nodes = [*times[:stop], age]
        flux_nodes = [*rates[:stop], float(np.interp(age, times, rates))]
        return SECONDS_PER_MYR * math.fsum((b-a)*(p+q)/2 for a,b,p,q in
                                          zip(age_nodes,age_nodes[1:],flux_nodes,flux_nodes[1:]))
    return integral


def audit(source):
    raw = (json.loads(source.read_text()) if source.is_file() else
           [json.loads(f.read_text()) for f in sorted(source.glob("*/*/lobe_*.json"))])
    def index(rows):
        return {(r["case"],r["arm"],r["index"]): r for r in rows}
    records = index(raw)
    published = json.loads((PUBLISHED/"snapshot_readout.json").read_text())
    require(len(raw) == len(records) == len(published) == 12 and records == index(published),
            "native and published readout inventories")
    bindings = json.loads((PUBLISHED/"initial_source_bindings.json").read_text())["cases"]
    rates = ASSETS / "production_injector_histories_2026-11-21/history_tables.zip"
    compact = ASSETS / "entropy_restart_result_2026-11-22/compact_inputs.zip"
    digests = {p.name: digest(p.read_bytes()) for p in (rates, compact)}
    require(digests["history_tables.zip"] == "5b5d0b2c526c8340e8cbd89e11f66d23e721c310443bb3e66b6aa7b4489a7461"
            and digests["compact_inputs.zip"] == "3ba5fa77d79d9f43e125f04a1d026206ce2c5127c1ed1c9be671ea3f284d882b",
            "archived injector or restart inputs")
    axes, centres_sha, count = geometry()
    effects = csv_rows((PUBLISHED/"paired_effects.csv").read_bytes())
    require(len(effects) == 18, "published comparison coverage")
    result = dict(archive_sha256=digests, cell_centres_sha256=centres_sha, native_records=len(raw),
                  source_checks="Server inode, size and nanosecond modification time for each native file and baseline. "
                                "The current pressure field matches its earlier full-field SHA-256. The baseline full-file "
                                "digests come from the production archive.",
                  archived_control_rows=0, effect_rows=0, cases={})
    history_receipt = json.loads((ASSETS/"native_delivery_restatement_2026-11-21/verification.json").read_text())
    with ZipFile(rates) as hist, ZipFile(compact) as restart:
        for line in restart.read("SHA256SUMS").decode().splitlines():
            expected, name = line.split(maxsplit=1)
            require(digest(restart.read(name)) == expected, name)
        inventory = index(json.loads(restart.read("raw/native-inventory.json"))["outputs"])
        for case in CASES:
            old = ASSETS / "turn15_review_2026-11-11/budgets" / case / "measurements.csv"
            key = f"docs/science/assets/{old.relative_to(ASSETS)}"
            require(digest(old.read_bytes()) == history_receipt["input_sha256"][key], key)
            controls = {int(r["snapshot_index"]): r for r in csv_rows(old.read_bytes()) if r["speed_threshold_km_s"] == "100"}
            seed = records[case,"ON",10]["age_myr"]
            curves = {arm: gas_curve(case,arm,hist,restart) for arm in ("ON","OFF")}
            checked = {"gas_delivery_through_10_myr_erg": curves["ON"](seed), "aperture_counts": {}, "primary": []}
            for (c, arm, i), r in records.items():
                if c != case:
                    continue
                n = inventory[case,arm,i]
                g = json.loads(restart.read(f"snapshots/{case}/{arm}/grid_{i}.json"))
                require(all(r["source"][k] == n[k] for k in ("inode", "mtime_ns")) and r["source"]["bytes"] == n["size"]
                        and r["source"]["filename"] == g["input"]["filename"] and r["time_code"] == n["time_code"]
                        and r["step"] == g["step"] and r["age_myr"] == g["age_myr"], "native snapshot identity")
                require(all(r["initial"][k] == bindings[case][k] for k in ("filename","bytes","inode","mtime_ns"))
                        and r["field_sha256"]["prs"] == g["input"]["field_sha256_c_order_float32_le"]["prs"]
                        and r["atmosphere_sha256"] == g["input"]["atmosphere_sha256"]
                        and r["grid_out_sha256"] == g["input"]["grid_out_sha256"], "baseline, pressure, atmosphere or grid")
                R = r["r100_radius_kpc"]
                xyz = [ax[j] for ax,j in zip(axes, reversed(r["r100_defining_cell_zyx"]))]
                close(math.hypot(*xyz), R, "defining centre", absolute=math.ulp(R))
                cells = count(math.nextafter(R, math.inf))
                inclusive = count(R)
                shell = inclusive-count(math.nextafter(R, -math.inf))
                s = r["r100_storage"]
                require(cells == s["cells"] and shell > 0 and s["complete_sphere"] and R <= s["box_radius_limit_kpc"] == 200
                        and R >= r["lobe_outermost_centre_kpc"], "closed sphere and lobe containment")
                close(sum(s[k+"_delta_erg"] for k in ("kinetic","thermal","gravitational")),s["total_delta_erg"],"sphere energy")
                require([v["tracer_cut"] for v in r["lobes"]] == list(CUTS), "native tracer thresholds")
                checked["aperture_counts"][f"{arm}_{i}"] = dict(cells=cells, centres_at_radius=shell,
                                                                extra_centres_in_one_ulp_guard=cells-inclusive)
                if arm == "ON" and i in (10,20):
                    original = controls[10 if i == 10 else 11]
                    for k in ("thermal_delta_erg","kinetic_delta_erg","gravitational_delta_erg","total_delta_erg"):
                        close(s[k], original["all_"+k], "archived sphere component")
                    for actual, field in ((R,"raw_radius_kpc"), (r["lobes"][0]["volume_kpc3"],"cocoon_volume_kpc3"),
                                         (r["lobes"][0]["enthalpy_2p5pv_erg"],"native_enthalpy_2.5_erg")):
                        close(actual, original[field], "archived production control")
                    result["archived_control_rows"] += 1
            off = sorted((r for (c,a,_),r in records.items() if (c,a) == (case,"OFF")), key=lambda r:r["age_myr"])
            times = [r["age_myr"] for r in off]
            for i, mode in ((20,"native_outputs"), (20,"off_interpolated_to_on"), (30,"native_outputs")):
                on = records[case,"ON",i]
                t = on["age_myr"]
                t_off = t if mode == "off_interpolated_to_on" else records[case,"OFF",i]["age_myr"]
                require(times[0] <= t_off <= times[-1], "bracketing OFF times")
                d0,d1 = curves["ON"](t),curves["OFF"](t_off)
                s0 = on["r100_storage"]["total_delta_erg"]
                s1 = float(np.interp(t_off,times,[r["r100_storage"]["total_delta_erg"] for r in off]))
                for j,cut in enumerate(CUTS):
                    h0,v0 = (on["lobes"][j][k] for k in ("enthalpy_2p5pv_erg","volume_kpc3"))
                    h1,v1 = (float(np.interp(t_off,times,[r["lobes"][j][k] for r in off]))
                             for k in ("enthalpy_2p5pv_erg","volume_kpc3"))
                    age = 11 if i == 20 else 12
                    expected, = (r for r in effects if r["case"] == case and int(r["nominal_myr"]) == age and
                                 r["timing"] == mode and float(r["tracer_cut"]) == cut)
                    values = {"enthalpy_on_erg":h0, "enthalpy_off_erg":h1, "volume_on_kpc3":v0, "volume_off_kpc3":v1,
                              "net_gas_on_erg":d0, "net_gas_off_erg":d1, "r100_storage_on_erg":s0, "r100_storage_off_erg":s1,
                              "r100_radius_on_kpc":on["r100_radius_kpc"],
                              "r100_radius_off_kpc":float(np.interp(t_off,times,[r["r100_radius_kpc"] for r in off])),
                              "numerator_percentage_points":100*(h1-h0)/d0,
                              "denominator_percentage_points":100*h1*(1/d1-1/d0),
                              "ratio_difference_percentage_points":100*(h1/d1-h0/d0)}
                    for k,v in values.items():
                        close(v, expected[k], k, absolute=2e-12 if k.endswith("percentage_points") else 0.)
                    result["effect_rows"] += 1
                    if j == 0 and (i == 30 or mode == "off_interpolated_to_on"):
                        label = POWER*(t-seed)*SECONDS_PER_MYR
                        checked["primary"].append(dict(on_age_myr=t, off_age_myr=t_off, H_change_percent=100*(h1/h0-1),
                            volume_change_percent=100*(v1/v0-1), H_over_delivered_on=h0/d0, H_over_delivered_off=h1/d1,
                            H_over_storage_on=h0/s0, H_over_storage_off=h1/s1, H_change_over_post_seed_label=(h1-h0)/label,
                            R100_storage_change_over_post_seed_label=(s1-s0)/label))
            result["cases"][case] = checked
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=PUBLISHED/"snapshot_readout.json")
    args = parser.parse_args()
    print(json.dumps(audit(args.source), indent=2, allow_nan=False))
