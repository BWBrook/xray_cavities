"""Independent 10–12 Myr balance from native RK records, snapshot receipts and production controls."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile


REPO = Path(__file__).resolve().parents[2]
ASSETS = REPO / "docs/science/assets"
CASES = ("G-HI", "C-HI")
ARMS = ("ON", "OFF")
PRIMARY = "linear_snapshot_flags"
BOUNDARY = "outer_active_cell"
POWER = 2e45
SECONDS_PER_MYR = 3.15576e13
CODE_TIME_PER_MYR = 306.6013937879523
CONTROL = {
    "G-HI": (10990, "5e427ae7ad1efdc7141ee5b03063157f7e6eb144f58fd8e36ce8e0317e564c01"),
    "C-HI": (11159, "198578a32ff2b7c48a45fff7bea768584dd286bdf5c88545654e0e236bcc3c05"),
}
COMPONENTS = (("thermal_erg", "thermal_erg"), ("kinetic_erg", "kinetic_erg"),
              ("gravitational_erg", "potential_erg"))


def read(path):
    return json.loads(path.read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, context, *, absolute=0., relative=4e-12):
    actual, expected = float(actual), float(expected)
    if not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute):
        raise ValueError(f"{context}: measured {actual:.17g}, expected {expected:.17g}")


def sha(data, digest, context):
    require(hashlib.sha256(data).hexdigest() == digest, f"SHA-256 mismatch: {context}")
    return data


def rows(data):
    return csv.DictReader(io.StringIO(data.decode()))


def production():
    result = {}
    base = ASSETS / "production_injector_histories_2026-11-21"
    receipt = read(base / "verification.json")
    archive = sha((base / "history_tables.zip").read_bytes(), receipt["public_zip_sha256"], "history_tables.zip")
    with ZipFile(io.BytesIO(archive)) as z:
        for case in CASES:
            for table in ("injector_snapshot_rates", "injector_interval_balances"):
                name = f"native/summary/{case}/{table}.csv"
                data = sha(z.read(name), receipt["public_member_sha256"][name], name)
                for row in rows(data):
                    i = int(row.get("index", row.get("start_index")))
                    if i in (10, 11) and row["method"] == PRIMARY:
                        result[case, table, i, row.get("region", row.get("rule"))] = row
            name = "comparison/flagged_sphere_gravity_snapshots.csv"
            for row in rows(sha(z.read(name), receipt["public_member_sha256"][name], name)):
                if row["case"] == case and int(row["index"]) in (10, 11):
                    result[case, "flagged", int(row["index"])] = row
    base = ASSETS / "outer_tracer_gravity_2026-11-19"
    with ZipFile(base / "compact_inputs.zip") as z:
        provenance = json.loads(z.read("provenance.json"))
        for name in ("stock.csv", "rates.csv"):
            data = sha(z.read(name), provenance["compact_csv_sha256"][name], name)
            for row in rows(data):
                i, case = int(row["index"]), row["case"]
                if case in CASES and i in (10, 11, 12) and row["surface"] == "domain_boundary":
                    result[case, name, i, row.get("method")] = row
    # The public stock table has total and gravitational energy. The retained source additionally has thermal and kinetic.
    retained = REPO / "private_archive/turn18_high_review_2026-11-18"
    for case, path, member in (
        ("G-HI", "flux_audit/G-HI_partial", "products/flux/region_storage.csv"),
        ("C-HI", "stage/results/flux_C-HI_full", "flux/region_storage.csv"),
    ):
        path = retained / path / member
        if path.exists():
            data = sha(path.read_bytes(), provenance["retained_products_sha256"][case][member], member)
            for row in rows(data):
                if (row["region"] == "whole_grid" and row["volume_geometry"] == "exact_fv_nodes"
                        and row["snapshot_index"] in ("10", "11")):
                    result[case, "components", int(row["snapshot_index"])] = row
    return result


def gate(raw, case):
    control = read(raw / case / "gate.json")
    seed = read(raw / case / "seed-validation.json")
    fields = {"rho", "prs", "vx1", "vx2", "vx3", "tr1"}
    step, digest = CONTROL[case]
    require(control["case"] == case and control["passed"] and control["control_output"] == 20
            and control["control_step"] == control["reference_step"] == step
            and control["reference_time"] == control["control_time"] and control["reference_sha256"] == digest
            and control["unequal_cells_full_grid"] == dict.fromkeys(fields, 0), f"{case} 11-Myr gate")
    require(seed["status"] == "ok" and set(seed["production_float_check"]) == fields and
            all(x["cells_checked"] == 934502400 for x in seed["production_float_check"].values()),
            f"{case} 10-Myr native-float seed")
    return control, seed


def native_stages(root, case, arm, catalogue, ages):
    raw = root / "raw" / case / arm / "outputs"
    path, = raw.glob("entropy_rk_*.csv")
    # Sum the two signed cell changes directly in each stage, independently of the reducer's effective column.
    changes = {1: [], 2: []}
    native_effective = []
    units, seen = set(), {1: set(), 2: set()}
    with path.open(newline="") as stream:
        for r in csv.DictReader(stream):
            stage, step = int(r["stage"]), int(r["step"])
            require(stage in changes and float(r["rk_weight"]) == (0.5 if stage == 1 else 1.0)
                    and r["entropy_switch"] == ("selective" if arm == "ON" else "off"), f"{path.name} stage or switch")
            seen[stage].add(step)
            units.add(float(r["energy_unit_erg"]))
            if r["radius_kpc"] == "injector_flag":
                continue
            require(r["radius_kpc"] != "r_lt_0.75" or int(r["cell_visits"]) == 0, "unflagged visits inside sphere")
            changes[stage].extend((float(r["raw_cell_gain"]), float(r["raw_cell_loss"])))
            native_effective.append(float(r["effective_net_code"]))
    unit, = units
    require(seen[1] == seen[2] == set(range(catalogue[10], catalogue[30])), "RK hydro-step coverage")
    stage_sums = [w * math.fsum(changes[i]) for i, w in ((1, .5), (2, 1.))]
    label = POWER * SECONDS_PER_MYR * (ages[-1]-ages[0])
    net = math.fsum(stage_sums) * unit / label
    close(net, math.fsum(native_effective)*unit/label, "weighted raw vs stored effective RK", absolute=1e-13)
    with (root/"stages/rk_window_regions.csv").open() as stream:
        row, = (r for r in csv.DictReader(stream) if (r["case"],r["arm"],r["region"]) == (case,arm,"exterior"))
    close(label, row["labelled_energy_erg"], "RK input-energy denominator")
    close(net, row["effective_net_over_label"], "raw native RK vs independently reduced exterior", absolute=1e-13)
    return {"stage_1_over_label": stage_sums[0]*unit/label, "stage_2_over_label": stage_sums[1]*unit/label,
            "net_over_label": net}


def history(root, case, arm, seed):
    series = read(root/"raw"/case/arm/"series.json")
    cat_path = root/"raw"/case/arm/"outputs/flt.h5.out"
    cat = {int(cols[0]): int(cols[3]) for line in cat_path.read_text().splitlines() if (cols := line.split())}
    start = seed["fluid_restart"]
    require(series["case"] == case and series["arm"] == arm and cat[10] == start["nstep"] and
            series["new_indices"] == list(range(11,31)) and len(series["ages_myr"]) == 20, "arm history")
    ages = [start["time"]/CODE_TIME_PER_MYR, *series["ages_myr"]]
    require(all(b > a for a, b in zip(ages, ages[1:])) and ages[-1] == 12., "unequal or missing time intervals")
    return cat, ages


def snapshots(root, case, arm, catalogue, ages, inventory):
    result = []
    for index, age in enumerate(ages, 10):
        source_arm = "ON" if index == 10 else arm
        path = root/"snapshots"/case/source_arm
        g, j = (read(path/f"{kind}_{index}.json") for kind in ("grid", "injector"))
        key = (case, source_arm, index, age, catalogue[index])
        for obj in (g,j):
            require(tuple(obj[k] for k in ("case","arm","index","age_myr","step")) == key, f"wrong snapshot {key}")
            close(obj["time_code"]/CODE_TIME_PER_MYR, age, "snapshot age", absolute=1e-14)
        entry = inventory[case, arm, index]
        require(g["time_code"] == j["time_code"] == entry["time_code"] and
                g["input"]["bytes"] == j["file_size_bytes"] == entry["size"] and
                g["input"]["mtime_ns"] == entry["mtime_ns"] and
                g["input"]["atmosphere_sha256"] == j["atmosphere_sha256"] and j["primary_method"] == PRIMARY and
                j["labelled_power_erg_s"] == POWER and g["boundary"][BOUNDARY]["valid"], f"snapshot convention {key}")
        result.append((g,j))
    return result


def balance(states, boundary=BOUNDARY):
    """Change in exterior stock plus energy crossing the box faces minus energy entering from the injector."""
    times = [g["age_myr"] for g,_ in states]
    durations = [r-l for l,r in zip(times, times[1:])]
    width = times[-1]-times[0]
    label = width*SECONDS_PER_MYR*POWER
    weights = [0.5*(a+b)/width for a,b in zip([0., *durations], [*durations, 0.])]
    close(math.fsum(weights), 1., "nodal time weights")
    first, last = states[0], states[-1]
    grid_components = {g.removesuffix("_erg"): (last[0]["storage"][g]-first[0]["storage"][g])/label
                       for g,_ in COMPONENTS}
    grid_delta = math.fsum(grid_components.values())
    flag_delta = math.fsum(last[1]["flagged_storage"][j]-first[1]["flagged_storage"][j] for _,j in COMPONENTS) / label
    outer = [g["boundary"][boundary]["total_energy_flux_outward_erg_s"]/POWER for g,_ in states]
    net = [j["rates"][PRIMARY]["net"]["total_energy_erg_s"]/POWER for _,j in states]
    difference = [o-i for o,i in zip(outer, net)]
    def average(values):
        return math.fsum(w*v for w,v in zip(weights, values))
    result = {"grid_storage_change": grid_delta, "grid_components": grid_components, "flagged_storage_change": flag_delta,
              "outer_flux": average(outer), "injector_total": average(net),
              "first_interval_injector_trapezoid_minus_right": .5*(net[0]-net[1])*durations[0]/width}
    for region in ("cap", "stationary", "net"):
        result[f"{region}_gas"] = average([j["rates"][PRIMARY][region]["gas_energy_erg_s"]/POWER for _,j in states])
    result["tagged_mass"] = average([j["rates"][PRIMARY]["net"]["tracer_mass_g_s"]/j["labelled_mass_rate_g_s"]
                                     for _,j in states])
    close(result["cap_gas"]+result["stationary_gas"], result["net_gas"], "integrated cone plus stationary gas", absolute=2e-12)
    result["exterior"] = grid_delta-flag_delta + average(difference)
    for name, sample in (("left",difference[:-1]), ("right",difference[1:])):
        result[name+"_exterior"] = grid_delta-flag_delta + math.fsum(t*v/width for t,v in zip(durations,sample))
    close(result["exterior"], (result["left_exterior"]+result["right_exterior"])/2, "left/right trapezoid", absolute=2e-13)
    # Calculate per-interval changes from separately recorded total stocks, expanding the trapezoids at their endpoints.
    intervals = []
    for k, d in enumerate(durations):
        a,b = states[k:k+2]
        change = (b[0]["storage"]["total_energy_erg"]-a[0]["storage"]["total_energy_erg"]
                  - (b[1]["flagged_storage"]["total_erg"]-a[1]["flagged_storage"]["total_erg"]))
        intervals.append(change/(d*SECONDS_PER_MYR*POWER) + .5*(difference[k]+difference[k+1]))
    weighted = math.fsum(d*v/width for d,v in zip(durations,intervals))
    close(result["exterior"], weighted, "endpoint components vs duration-weighted interval residuals", absolute=1e-11)
    result["interval_weighted_exterior"] = weighted
    return result


def compare_controls(case, states, archive, gate_receipt):
    require(states[10][0]["time_code"] == gate_receipt["reference_time"] and
            states[10][0]["step"] == gate_receipt["reference_step"], "11-Myr control step and time")
    for k,i in ((0,10),(10,11)):
        grid, injector = states[k]
        old = archive[case,"stock.csv",i,None]
        close(grid["age_myr"], old["age_myr"], f"{case} production age {i}", relative=0.)
        for key in ("mass_g","gravitational_erg","total_energy_erg"):
            close(grid["storage"][key], old[key], f"{case}/{i} stock {key}")
        if (case,"components",i) in archive:
            for key,_ in COMPONENTS:
                close(grid["storage"][key], archive[case,"components",i][key], f"{case}/{i} stock {key}")
        close(injector["flagged_storage"]["potential_erg"], archive[case,"flagged",i]["flagged_potential_erg"],
              f"{case}/{i} flagged potential")
        for method, current in grid["boundary"].items():
            old = archive[case,"rates.csv",i,method]
            require(current["valid"], f"{case}/{i} archival boundary {method} valid")
            for key in ("total_energy_flux_outward_erg_s","potential_flux_outward_erg_s","mass_flux_outward_g_s"):
                close(current[key], old[key], f"{case}/{i} {method} {key}")
        for region, rates in injector["rates"][PRIMARY].items():
            old = archive[case,"injector_snapshot_rates",i,region]
            for key in ("gas_energy","potential_energy","total_energy","tracer_mass","mass"):
                is_mass = "mass" in key
                suffix, unit = ("_g_s",injector["labelled_mass_rate_g_s"]) if is_mass else ("_erg_s",POWER)
                name = "tracer" if key == "tracer_mass" else key
                close(rates[key+suffix]/unit, old[name+"_over_label"], f"{case}/{i} {region} {name}", absolute=1e-13)
            require(rates["face_count"] == int(old["face_count"]), f"{case}/{i} {region} face count")
    old = archive[case,"injector_interval_balances",10,"trapezoid"]
    coarse = [states[0], states[10]]
    for method in (BOUNDARY,"linear_to_boundary_face"):
        replay = balance(coarse, method)
        for key, old_key in (("exterior","outside_flagged_sphere_"+method), ("injector_total","net_gas_plus_potential"),
                             ("flagged_storage_change","flagged_total_energy_change")):
            close(replay[key], old[old_key], f"{case} 10–11 coarse {method} {key}", absolute=5e-11)
    residuals = [float(archive[case,"injector_interval_balances",i,"trapezoid"]["outside_flagged_sphere_"+BOUNDARY])
                 for i in (10,11)]
    ages = [float(archive[case,"stock.csv",i,None]["age_myr"]) for i in (10,11,12)]
    weighted = math.fsum((b-a)*v for a,b,v in zip(ages,ages[1:],residuals))/(ages[-1]-ages[0])
    return {"production_control_step": gate_receipt["reference_step"], "production_control_age_myr": states[10][0]["age_myr"],
            "production_control_sha256": gate_receipt["reference_sha256"],
            "differing_primitive_values": sum(gate_receipt["unequal_cells_full_grid"].values()),
            "archived_10_11": residuals[0], "coarse_replay_10_11": balance(coarse)["exterior"],
            "archived_11_12": residuals[1], "archived_10_12_weighted": weighted,
            "production_final_age_myr": ages[-1], "thermal_kinetic_sources_checked": (case,"components",11) in archive}


def audit(root, native_only=False):
    raw = root/"raw"
    for name, digest in read(raw/"raw-sha256.json").items():
        sha((raw/name).read_bytes(), digest, name)
    archive = production()
    inventory = {(r["case"],r["arm"],r["index"]): r for r in read(raw/"native-inventory.json")["outputs"]}
    result = {}
    for case in CASES:
        control, seed = gate(raw, case)
        shared = ("device", "inode", "size", "mtime_ns", "time_code")
        require(all(inventory[case,"ON",10][k] == inventory[case,"OFF",10][k] for k in shared),
                f"{case} shared native seed")
        arms = {}
        for arm in ARMS:
            cat, ages = history(root, case, arm, seed)
            rk = native_stages(root, case, arm, cat, ages)
            arms[arm] = {"rk_exterior": rk, "intervals": len(ages)-1}
            if native_only:
                continue
            states = snapshots(root, case, arm, cat, ages, inventory)
            budget = balance(states)
            arms[arm]["budget_over_label"] = budget
            arms[arm]["exterior_minus_rk"] = budget["exterior"]-rk["net_over_label"]
            if arm == "ON":
                arms["production_control"] = compare_controls(case, states, archive, control)
        if not native_only:
            on, off = (arms[arm]["budget_over_label"]["exterior"] for arm in ARMS)
            arms["off_minus_on"] = off-on
            arms["fraction_of_on_deficit_removed"] = (off-on)/-on
        result[case] = arms
    return result


def verify_primary_table(result, path):
    mapping = {"grid_storage_change": "grid_storage", "flagged_storage_change": "flagged_storage",
               "outer_flux": "boundary_outward", "injector_total": "net_injector", "cap_gas": "cone_gas",
               "stationary_gas": "stationary_gas", "tagged_mass": "tagged_mass", "exterior": "exterior"}
    with path.open() as stream:
        records = list(csv.DictReader(stream))
    require(len(records) == 4 and {(r["case"],r["arm"]) for r in records} == {(c,a) for c in CASES for a in ARMS},
            "primary window table must contain the four arms")
    for row in records:
        require((row["injector_method"],row["outer_boundary"],row["time_rule"]) == (PRIMARY,BOUNDARY,"trapezoid") and
                int(row["intervals"]) == int(row["valid_exterior_intervals"]) == 20, "primary window convention")
        arm = result[row["case"]][row["arm"]]
        for source, target in mapping.items():
            close(arm["budget_over_label"][source], row[target], target, absolute=1e-11)
        close(arm["rk_exterior"]["net_over_label"], row["native_stage"], "native exterior RK", absolute=1e-13)
        arm["primary_table_verified"] = True


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("receipt_directory", type=Path)
    cli.add_argument("--native-only", action="store_true", help="audit the native ledgers and controls before snapshot reductions arrive")
    cli.add_argument("--primary-windows", type=Path, help="also compare an independently produced primary_windows.csv")
    args = cli.parse_args()
    if args.native_only and args.primary_windows:
        cli.error("--primary-windows requires the snapshot reductions")
    audited = audit(args.receipt_directory, args.native_only)
    if args.primary_windows:
        verify_primary_table(audited, args.primary_windows)
    print(json.dumps(audited, indent=2, allow_nan=False))
