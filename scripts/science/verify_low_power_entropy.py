"""Independently score board forecast 3665 from raw injector/grid snapshots and unweighted native RK bins."""

import argparse
from bisect import bisect_right
from collections import defaultdict
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile


POWER = 2e43
SECONDS_PER_CODE = 3.15576e13 / 306.6013937879523
UNIT_ERG = .60364 * 1.66053886e-24 * (2.99792458e10)**2 * (3.0856775807e21)**3
CELLS = 960 * 960 * 1014
FORECASTS = {"C-LO": (.030, .047), "G-LO": (-.017, -.022)}
CONTROLS = {
    "C-LO": (12729, 46060, "fc03993609b51ac4cb208ade551d2113fd1ddce24b32af3d55c151b0392097b6"),
    "G-LO": (11526, 42032, "fa7d48233007223f29b274fbba07847579cb563654d42e397e06a25337ecaf8c"),
}
METHOD = "linear_snapshot_flags"
COMPONENTS = (("thermal_erg","thermal_erg"), ("kinetic_erg","kinetic_erg"), ("gravitational_erg","potential_erg"))
OPERATIONS = ("entropy", "entropy_with_p_floor", "E_floor", "p_energy_floor", "cell")
VISITS = ("entropy_visits", "density_floors", "gas_energy_floors", "p_entropy_floors", "p_energy_floors")


def require(condition, context):
    if not condition:
        raise ValueError(context)


def close(a, b, context, absolute=1e-12):
    require(math.isclose(a, b, rel_tol=2e-11, abs_tol=absolute), f"{context}: {a} versus {b}")


def ledger(rows, arm, steps, *, native):
    totals = {i: defaultdict(float) for i in range(11,31)}
    cells = defaultdict(int)
    for row in rows:
        if native:
            index = 10 + bisect_right(steps, int(row["step"]))
            require(steps[0] <= int(row["step"]) < steps[-1] and
                    row["entropy_switch"] == ("selective" if arm == "ON" else "off"), "native step and switch")
            close(float(row["energy_unit_erg"]), UNIT_ERG, "native gas energy unit")
        else:
            index = int(row["end_index"])
            require((int(row["start_index"]), int(row["start_step"]), int(row["end_step_exclusive"])) ==
                    (index-1, steps[index-11], steps[index-10]), "compact step coverage")
        stage = int(row["stage"])
        weight = {1: .5, 2: 1.}[stage]
        require(float(row["rk_weight"]) == weight, "RK2 stage weight")
        count = int(row["cell_visits"])
        cells[index, stage] += count
        if row["radius_kpc"] == "injector_flag":
            continue
        require(row["radius_kpc"] != "r_lt_0.75" or count == 0, "unflagged cells inside the maintained sphere")
        require(int(row["nonfinite_energy_visits"]) == 0, "nonfinite energy in native exterior")
        out = totals[index]
        for key in VISITS:
            out[key] += int(row[key])
        for op in OPERATIONS:
            for sign in ("gain","loss"):
                key = f"{op}_{sign}"
                v = float(row["raw_"+key+("" if native else "_code")])
                require(math.isfinite(v) and (v >= 0 if sign == "gain" else v <= 0), "signed raw change")
                out[key] += v*weight*UNIT_ERG
    for index,data in totals.items():
        for stage in (1,2):
            require(cells[index,stage] == (steps[index-10]-steps[index-11])*CELLS, "incomplete native stage")
        gross = data["cell_gain"]-data["cell_loss"]
        op_net = math.fsum(data[f"{op}_{sign}"] for op in OPERATIONS[:-1] for sign in ("gain","loss"))
        close(op_net, data["cell_gain"]+data["cell_loss"], "signed raw cell and branch changes", absolute=1e-12*gross)
    return totals


def snapshots(get, case, arm):
    result = []
    for i in range(10,31):
        source = "ON" if i == 10 else arm
        g,j = (get(f"snapshots/{case}/{source}/{kind}_{i}.json") for kind in ("grid", "injector"))
        require(all(g[k] == j[k] for k in ("case","arm","index","time_code","age_myr","step")) and
                (g["case"],g["arm"],g["index"]) == (case,source,i) and j["labelled_power_erg_s"] == POWER,
                "native snapshot metadata and bipolar label")
        faces = g["boundary"]["outer_active_cell"]
        require(faces["valid"] and len(faces["faces"]) == 6, "six outward domain faces")
        boundary = math.fsum(f["total_energy_flux_outward_erg_s"] for f in faces["faces"].values())
        close(boundary/POWER, faces["total_energy_flux_outward_erg_s"]/POWER, "six faces versus net energy flux")
        rates = j["rates"][METHOD]
        def source_rate(k):
            return math.fsum(rates[region][k] for region in ("cap","stationary"))
        gas, potential = (source_rate(k) for k in ("gas_energy_erg_s", "potential_energy_erg_s"))
        close((gas+potential)/POWER, rates["net"]["total_energy_erg_s"]/POWER, "cone and stationary delivery")
        result.append(dict(time=g["time_code"], step=g["step"], grid=g["storage"], flag=j["flagged_storage"],
                           boundary=boundary, delivery=gas+potential, gas=gas,
                           tagged=source_rate("tracer_mass_g_s")/j["labelled_mass_rate_g_s"],
                           net_mass=source_rate("mass_g_s")/j["labelled_mass_rate_g_s"]))
    require(all(b["step"] > a["step"] and b["time"] > a["time"] for a,b in zip(result,result[1:])), "snapshot ordering")
    return result


def period(samples, first, last, rk):
    s = samples[first-10:last-9]
    widths = [(b["time"]-a["time"])*SECONDS_PER_CODE for a,b in zip(s,s[1:])]
    duration = math.fsum(widths)
    label = POWER*duration
    # Integrate node observations with their time support, including half weights at the two endpoints.
    weights = [(a+b)/(2*duration) for a,b in zip([0.,*widths], [*widths,0.])]
    def mean(field):
        return math.fsum(w*x[field] for w,x in zip(weights,s))
    grid = {k.removesuffix("_erg"): (s[-1]["grid"][k]-s[0]["grid"][k])/label for k,_ in COMPONENTS}
    flag = math.fsum(s[-1]["flag"][k]-s[0]["flag"][k] for _,k in COMPONENTS)/label
    boundary = mean("boundary")/POWER
    injector = mean("delivery")/POWER
    exterior = math.fsum([*grid.values(), -flag, boundary, -injector])
    selected = [rk[i] for i in range(first+1,last+1)]
    def operation(keys):
        return math.fsum(d[k] for d in selected for k in keys)/label
    gain = operation(("entropy_gain","entropy_with_p_floor_gain"))
    loss = operation(("entropy_loss","entropy_with_p_floor_loss"))
    mapper = operation(("cell_gain","cell_loss"))
    return dict(start_index=first, end_index=last, label_erg=label, entropy_gain=gain, entropy_loss=loss,
                entropy_net=gain+loss, mapper_net=mapper, exterior=exterior, exterior_minus_mapper=exterior-mapper,
                grid_change=grid, flagged_change=flag, outer_outward=boundary, injector_total=injector,
                injector_gas=mean("gas")/POWER, tagged_mass=mean("tagged"), signed_total_mass=mean("net_mass"),
                visits={k: int(sum(d[k] for d in selected)) for k in VISITS})


def check_scored_tables(directory, primary, result):
    errors = {}
    def compare(expected, recorded, key):
        value = float(recorded)
        close(expected, value, f"public-scoring comparison {key}", absolute=1e-11)
        errors[key] = max(errors.get(key, 0.), abs(expected-value))

    def rows(filename):
        with (directory/filename).open(newline="") as file:
            return list(csv.DictReader(file))

    mapping = {"exterior":"exterior", "net_injector":"injector_total", "boundary_outward":"outer_outward",
               "flagged_storage":"flagged_change", "tagged_mass":"tagged_mass", "native_stage":"mapper_net",
               "unexplained":"exterior_minus_mapper"}
    intervals_path = Path("primary_intervals.csv")
    if not (directory/intervals_path).is_file():
        intervals_path = Path("budget")/intervals_path
    seen = set()
    for row in rows(intervals_path):
        key = row["case"], row["arm"], int(row["start_index"])
        expected = primary[key]
        require(key not in seen and expected["end_index"] == int(row["end_index"]), "scored interval selection")
        seen.add(key)
        for column, name in mapping.items():
            compare(expected[name], row[column], column)
        compare(math.fsum(expected["grid_change"].values()), row["grid_storage"], "grid_storage")
    require(seen == set(primary), "coverage of all 80 primary intervals")
    windows = {(case, w["start_index"], w["end_index"]):w for case,c in result["cases"].items()
               for w in c["arms"]["ON"]["windows"]}
    on = rows("on_counter_windows.csv")
    require(len(on) == len(windows), "six ON window scores")
    for row in on:
        case, first, last = row["case"], int(row["start_index"]), int(row["end_index"])
        w = windows.pop((case,first,last))
        compare(w["entropy_net"], row["entropy_net_over_label"], "annual_or_full_native_entropy")
        compare(w["exterior"], row["exterior_residual_over_label"], "annual_or_full_exterior")
        compare(w["mapper_net"], row["all_mapper_net_over_label"], "annual_or_full_native_mapper")
        if last-first == 10:
            passed = abs(w["entropy_net"]-FORECASTS[case][(first-10)//10]) <= .005
            require(passed == (row["score"] == "pass"), "annual registered score")
    off = rows("off_interval_scores.csv")
    remaining = {key for key in primary if key[1] == "OFF"}
    for row in off:
        key = row["case"], "OFF", int(row["start_index"])
        remaining.remove(key)
        r = primary[key]["exterior"]
        compare(r, row["exterior_residual_over_label"], "short_OFF_scored_exterior")
        expected_score = "excluded_startup" if key[-1] == 10 else ("pass" if abs(r) <= .002 else "miss")
        require(row["score"] == expected_score, "OFF scored bound")
    require(not remaining, "coverage of all 40 OFF interval scores")
    return {"primary_intervals":len(seen), "ON_windows":len(on), "OFF_intervals":len(off),
            "maximum_absolute_fractional_difference_by_quantity":errors}


def audit(read_bytes, raw_root=None, score_dir=None):
    def get(name):
        return json.loads(read_bytes(name))
    try:
        manifest = read_bytes("SHA256SUMS").decode()
    except (KeyError, FileNotFoundError):
        manifest = ""
    for line in manifest.splitlines():
        digest,name = line.split(maxsplit=1)
        require(hashlib.sha256(read_bytes(name)).hexdigest() == digest, name)
    compressed = read_bytes("stages/rk_interval_bins.csv.gz")
    contents = gzip.decompress(compressed).decode()
    bins = defaultdict(list)
    for row in csv.DictReader(io.StringIO(contents)):
        bins[row["case"],row["arm"]].append(row)
    verification = get("stages/rk_verification.json")
    result = {"forecast_board_message": 3665, "bipolar_power_erg_s": POWER,
              "compact_rk_bins_sha256": hashlib.sha256(compressed).hexdigest(), "cases": {}}
    primary = {}
    raw_checks = {}
    for case,predictions in FORECASTS.items():
        ref_step, particles, ref_hash = CONTROLS[case]
        g = get(f"raw/{case}/gate.json")
        require(g["case"] == case and g["passed"] and g["reference_sha256"] == ref_hash and
                g["labelled_power_erg_s"] == POWER and
                g["reference_step"] == ref_step and abs(g["control_step"]-ref_step) <= 1 and
                g["particle_count_at_restart"] == particles and max(g["relative_L1_in_affected_gas"].values()) <= .01
                and max(g["component_L1_per_labelled_interval"].values()) <= .005, "production control")
        out = {"differing_control_values": sum(g["unequal_cells_full_grid"].values()),
               "control_step_minus_production": g["control_step"]-ref_step,
               "control_time_minus_production": g["control_time"]-g["reference_time"], "arms": {}}
        for arm in ("ON","OFF"):
            samples = snapshots(get,case,arm)
            steps = [s["step"] for s in samples]
            if arm == "ON":
                require((steps[10], samples[10]["time"]) == (g["control_step"], g["control_time"]),
                        "matching the 11-Myr budget stock to the production control")
            v = verification[f"{case}/{arm}"]
            close(v["energy_unit_erg"], UNIT_ERG, "native physical unit")
            rk = ledger(bins[case,arm],arm,steps,native=False)
            if raw_root is not None:
                directory = raw_root / case / arm / "outputs"
                path, = sorted(directory.glob("entropy_rk_*.csv")) + sorted(directory.glob("entropy_rk_*.csv.gz"))
                payload = path.read_bytes()
                if path.suffix == ".gz":
                    payload = gzip.decompress(payload)
                require(hashlib.sha256(payload).hexdigest() == v["raw_csv_sha256"], "native stage file SHA-256")
                reader = csv.DictReader(io.StringIO(payload.decode()))
                native = ledger(reader,arm,steps,native=True)
                native_rows = reader.line_num-1
                require(native_rows == v["native_ledger_rows"], "original native CSV data-row count")
                max_delta = 0.
                for i in rk:
                    label = (samples[i-10]["time"]-samples[i-11]["time"])*SECONDS_PER_CODE*POWER
                    for k,num in native[i].items():
                        if k in VISITS:
                            require(num == rk[i][k], "native visit count")
                        else:
                            close(num/label, rk[i][k]/label, "step ledger versus compact unweighted bins")
                            max_delta = max(max_delta, abs(num/label-rk[i][k]/label))
                raw_checks[f"{case}/{arm}"] = {
                    "raw_csv_sha256":v["raw_csv_sha256"], "stage_csv_data_rows":native_rows,
                    "raw_and_compact_exterior_visit_counts_agree":True,
                    "largest_absolute_raw_minus_compact_operation_over_interval_label":max_delta,
                    "raw_entropy_net_over_label":[period(samples,a,b,native)["entropy_net"]
                                                  for a,b in ((10,20),(20,30),(10,30))]}
            intervals = [period(samples,i,i+1,rk) for i in range(10,30)]
            primary.update({(case,arm,i["start_index"]):i for i in intervals})
            windows = [period(samples,a,b,rk) for a,b in ((10,20),(20,30),(10,30))]
            for window in windows:
                members = intervals[window["start_index"]-10:window["end_index"]-10]
                for name in ("exterior","entropy_net","mapper_net","injector_total"):
                    other = math.fsum(x[name]*x["label_erg"] for x in members)/window["label_erg"]
                    close(window[name], other, "annual versus duration-weighted short intervals", absolute=1e-11)
            arm_result = dict(windows=windows, native_ledger_sha256=v["raw_csv_sha256"])
            out["arms"][arm] = arm_result
            if arm == "ON":
                out["annual_forecasts"] = [dict(prediction=p, actual=w["entropy_net"], difference=w["entropy_net"]-p,
                    passed=abs(w["entropy_net"]-p) <= .005) for p,w in zip(predictions,windows[:2])]
                if case == "C-LO":
                    out["below_refutation_plus_0p01"] = [w["entropy_net"] < .01 for w in windows]
            else:
                off = [x["exterior"] for x in intervals]
                out["off_exterior_by_end_index_11_to_30"] = off
                out["off_post_first"] = dict(passed=sum(abs(r) <= .002 for r in off[1:]), tested=19,
                    violating_end_indices=[i for i,r in enumerate(off[1:],12) if abs(r) > .002],
                    maximum_absolute=max(map(abs,off[1:])))
        result["cases"][case] = out
    cases = result["cases"]
    result["registered_tests"] = {
        "annual_forecasts_within_plus_or_minus_0p005":
            sum(f["passed"] for c in cases.values() for f in c["annual_forecasts"]),
        "annual_forecasts_tested": 4,
        "OFF_post_first_intervals_within_plus_or_minus_0p002":
            sum(c["off_post_first"]["passed"] for c in cases.values()),
        "OFF_post_first_intervals_tested": 38,
        "C_LO_annual_or_full_counter_below_plus_0p01": any(cases["C-LO"]["below_refutation_plus_0p01"]),
        "opposite_ON_entropy_signs_in_each_registered_year":
            all(wc["actual"] > 0 > wg["actual"]
                for wc,wg in zip(cases["C-LO"]["annual_forecasts"],cases["G-LO"]["annual_forecasts"])),
    }
    if raw_checks:
        result["raw_stage_csv_crosscheck"] = raw_checks
    if score_dir is not None:
        result["scored_table_crosscheck"] = check_scored_tables(score_dir, primary, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="compact budget inputs ZIP or extracted directory")
    parser.add_argument("--raw-native", type=Path, help="also verify against the original per-step CSV ledgers")
    parser.add_argument("--compare-scored", type=Path, help="also compare against the completed scorer's three tables")
    args = parser.parse_args()
    if args.source.is_dir():
        result = audit(lambda n: (args.source/n).read_bytes(), args.raw_native, args.compare_scored)
    else:
        with ZipFile(args.source) as archive:
            result = audit(archive.read, args.raw_native, args.compare_scored)
    print(json.dumps(result, indent=2, allow_nan=False))
