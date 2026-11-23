"""Reconstruct the production exterior energy residual and test its 10–12 Myr calibration."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
OUTPUT = ASSETS / "production_entropy_review_2026-11-23"
CASES = {"C-HI": 50, "C-LO": 50, "G-HI": 47, "G-LO": 50}
MYR = 3.15576e13
INJECTOR = "linear_snapshot_flags"
FACE = "outer_active_cell"
HISTORY = ASSETS / "production_injector_histories_2026-11-21/history_tables.zip"
DOMAIN = ASSETS / "outer_tracer_gravity_2026-11-19/compact_inputs.zip"
FIXED = ASSETS / "four_case_fixed_2026-11-18/histories.csv"
RESTART = {
    "HI": ASSETS / "entropy_restart_result_2026-11-22",
    "LO": ASSETS / "low_power_entropy_result_2026-11-23",
}


def csv_rows(data):
    return list(csv.DictReader(io.StringIO(data.decode())))


def write_rows(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def index_rows(rows, field="index"):
    indexed = {int(row[field]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"Duplicate {field} in selected inputs")
    return indexed


def close(a, b, description, tolerance=5e-11):
    if not math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance):
        raise ValueError(f"{description}: {a} differs from {b}")


def f(row, field):
    return float(row[field])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table(archive, name):
    return csv_rows(archive.read(name))


def trapezoid(rate_a, rate_b, elapsed_seconds):
    return (rate_a + rate_b) * (0.5 * elapsed_seconds)


def fixed_stock(row, name):
    return 0.0 if row["index"] == "0" else f(row, name) * f(row, "labelled_input_erg")


def production_case(case, last, history, domain, fixed_rows):
    power = 2e45 if case.endswith("HI") else 2e43
    fixed = index_rows([r for r in fixed_rows if r["case"] == case])
    grid = index_rows([r for r in table(domain, "stock.csv") if r["case"] == case and r["surface"] == "domain_boundary"])
    faces = [r for r in table(domain, "rates.csv") if r["case"] == case and r["surface"] == "domain_boundary"]
    faces = index_rows([r for r in faces if r["method"] == FACE])
    inj = index_rows([r for r in table(history, f"native/summary/{case}/injector_snapshot_rates.csv")
                      if r["region"] == "net" and r["method"] == INJECTOR])
    intervals = index_rows([r for r in table(history, f"native/summary/{case}/injector_interval_balances.csv")
                            if r["method"] == INJECTOR and r["rule"] == "trapezoid"], "end_index")
    if any(set(t) != set(range(last + 1)) for t in (fixed, grid, faces, inj)) or set(intervals) != set(range(1, last + 1)):
        raise ValueError(f"Incomplete primary history in {case}")
    raw = []
    errors = {"exterior": [], "fixed_vs_domain_whole_change": [], "shell_equation": []}
    for i in range(1, last + 1):
        a, b = i - 1, i
        ages = [f(grid[j], "age_myr") for j in (a, b)]
        for j, age in zip((a, b), ages):
            for t in (fixed, inj, faces):
                close(f(t[j], "age_myr"), age, f"{case}/{j} age")
        elapsed = (ages[1] - ages[0]) * MYR
        label = (min(50., ages[1]) - min(50., ages[0])) * MYR * power
        close(label, f(fixed[b], "labelled_input_erg") - f(fixed[a], "labelled_input_erg"), "interval label")
        gas = trapezoid(f(inj[a], "gas_energy_over_label"), f(inj[b], "gas_energy_over_label"), elapsed * power)
        phi = trapezoid(f(inj[a], "potential_energy_over_label"), f(inj[b], "potential_energy_over_label"), elapsed * power)
        outer = trapezoid(f(faces[a], "total_energy_flux_outward_erg_s"), f(faces[b], "total_energy_flux_outward_erg_s"), elapsed)
        whole = f(grid[b], "total_energy_erg") - f(grid[a], "total_energy_erg")
        flagged = f(intervals[b], "flagged_total_energy_change") * label
        exterior = math.fsum([whole, outer, -gas, -phi, -flagged])
        box = fixed_stock(fixed[b], "fixed_box_over_label") - fixed_stock(fixed[a], "fixed_box_over_label")
        sphere = fixed_stock(fixed[b], "R100_over_label") - fixed_stock(fixed[a], "R100_over_label")
        shell = f(fixed[b], "exterior_total_delta_erg") - f(fixed[a], "exterior_total_delta_erg")
        published = f(intervals[b], "outside_flagged_sphere_outer_active_cell")
        close(exterior / label, published, f"{case}/{i} archived exterior")
        close(gas / label, f(intervals[b], "net_gas"), "gas delivery")
        close((gas + phi) / label, f(intervals[b], "net_gas_plus_potential"), "total delivery")
        errors["exterior"].append(abs(exterior / label - published))
        # The whole grid was summed independently in the fixed-region reader.
        errors["fixed_vs_domain_whole_change"].append(abs(
            (f(grid[b], "total_energy_erg") - f(grid[0], "total_energy_erg")) / f(fixed[b], "labelled_input_erg")
            - f(fixed[b], "whole_grid_over_label")))
        errors["shell_equation"].append(abs((exterior - (box - gas) - (shell + outer - phi - flagged)) / label))
        alt = intervals[b]["outside_flagged_sphere_linear_to_boundary_face"]
        raw.append(dict(label=label, gas=gas, phi=phi, flagged=flagged, outer=outer, whole=whole,
                        box=box, sphere=sphere, shell=shell, exterior=exterior, alternate=float(alt)*label if alt else None))

    def window(kind, start, end):
        chosen = raw[start:end]
        def amount(key):
            return math.fsum(row[key] for row in chosen)

        label, gas = amount("label"), amount("gas")
        result = dict(case=case, scope=kind, start_index=start, end_index=end,
                      start_age_myr=f(grid[start], "age_myr"), end_age_myr=f(grid[end], "age_myr"),
                      labelled_energy_erg=label, delivered_gas_erg=gas,
                      domain_storage_over_label=amount("whole")/label, boundary_outward_over_label=amount("outer")/label,
                      injector_potential_over_label=amount("phi")/label, maintained_stock_over_label=amount("flagged")/label)
        amounts = {
            "exterior_residual": amount("exterior"), "box_minus_gas": amount("box") - gas,
            "r100_minus_gas": amount("sphere") - gas, "shell_plus_outer_flux": amount("shell") + amount("outer"),
            "box_minus_r100": amount("box") - amount("sphere"),
        }
        for key, value in amounts.items():
            result[key + "_over_label"] = value / label
            result[key + "_over_delivered_gas"] = value / gas
        result["alternative_face_exterior_over_label"] = (amount("alternate")/label
                                                          if all(r["alternate"] is not None for r in chosen) else None)
        result["lobe_inside_box_at_end"] = fixed[end]["cocoon_inside_box"]
        result["r100_inside_box_at_end"] = fixed[end]["R100_inside_box"]
        return result

    ages = [10, 20, 30, 40, last]
    annual = []
    for i in range(1, last + 1):
        row = window("annual", i - 1, i)
        accumulated = math.fsum(r["exterior"] for r in raw[:i])
        row["cumulative_exterior_over_label"] = accumulated / math.fsum(r["label"] for r in raw[:i])
        row["cumulative_exterior_over_delivered_gas"] = accumulated / math.fsum(r["gas"] for r in raw[:i])
        annual.append(row)
    cumulative = [window("cumulative", 0, end) for end in ages]
    decades = [window("decade", start, end) for start, end in zip([0] + ages[:-1], ages, strict=True)]
    return annual, cumulative + decades, {key: max(vals) for key, vals in errors.items()}


def restart_interval(start, end, power):
    (grid_a, inj_a), (grid_b, inj_b) = start, end
    dt = (f(grid_b, "age_myr") - f(grid_a, "age_myr")) * MYR
    def stock(a, b, fields):
        return math.fsum(f(b, k) - f(a, k) for k in fields)

    whole = stock(grid_a["storage"], grid_b["storage"], ("thermal_erg", "kinetic_erg", "gravitational_erg"))
    flagged = stock(inj_a["flagged_storage"], inj_b["flagged_storage"], ("thermal_erg", "kinetic_erg", "potential_erg"))
    outer = trapezoid(*(f(g["boundary"][FACE], "total_energy_flux_outward_erg_s") for g in (grid_a, grid_b)), dt)
    total = trapezoid(*(f(j["rates"][INJECTOR]["net"], "total_energy_erg_s") for j in (inj_a, inj_b)), dt)
    return dt * power, math.fsum([whole, outer, -flagged, -total])


def calibration(annual, sources):
    result = []
    for level, folder in RESTART.items():
        path = folder / "compact_inputs.zip"
        sources[path] = sha(path.read_bytes())
        with ZipFile(path) as z:
            steps = [r for r in table(z, "stages/rk_interval_regions.csv") if r["region"] == "exterior"]
            for case in (c for c in CASES if c.endswith(level)):
                for arm in ("ON", "OFF"):
                    sequence = []
                    for i in range(10, 31):
                        directory = f"snapshots/{case}/{'ON' if i == 10 else arm}"
                        g, j = (json.loads(z.read(f"{directory}/{kind}_{i}.json")) for kind in ("grid", "injector"))
                        if (g["age_myr"], g["step"], g["index"]) != (j["age_myr"], j["step"], j["index"]) or j["index"] != i:
                            raise ValueError("Restart grid and injector are not coeval")
                        sequence.append((g, j))
                    power = j["labelled_power_erg_s"]
                    for start, end in ((0, 10), (10, 20), (0, 20)):
                        window = sequence[start:end + 1]
                        fine = [restart_interval(a, b, power) for a, b in zip(window, window[1:])]
                        yearly = window[::10]
                        coarse = [restart_interval(a, b, power) for a, b in zip(yearly, yearly[1:])]
                        label = math.fsum(v for v, _ in fine)
                        counter = [r for r in steps if r["case"] == case and r["arm"] == arm
                                   and start + 10 < int(r["end_index"]) <= end + 10]
                        close(label, math.fsum(f(r, "labelled_energy_erg") for r in counter), "restart counter labels")
                        if len(counter) != end - start:
                            raise ValueError("Incomplete restart counter")
                        native = math.fsum(f(r, "effective_net_erg") for r in counter) / label
                        fast = math.fsum(v for _, v in fine) / label
                        slow = math.fsum(v for _, v in coarse) / label
                        first, last = 10 + start // 10, 10 + end // 10
                        prod = [r for r in annual if r["case"] == case and first < r["end_index"] <= last]
                        prod_res = math.fsum(r["exterior_residual_over_label"] * r["labelled_energy_erg"] for r in prod)
                        result.append(dict(case=case, arm=arm, start_index=first, end_index=last,
                                           restart_start_age_myr=window[0][0]["age_myr"], restart_end_age_myr=window[-1][0]["age_myr"],
                                           production_end_age_myr=prod[-1]["end_age_myr"], native_adjustment_over_label=native,
                                           fine_exterior_over_label=fast, annual_exterior_over_label=slow,
                                           fine_minus_native_over_label=fast - native, annual_minus_native_over_label=slow - native,
                                           production_exterior_over_label=prod_res/math.fsum(r["labelled_energy_erg"] for r in prod) if arm=="ON" else None))
    return result


def run(output):
    sources = {p: sha(p.read_bytes()) for p in (HISTORY, DOMAIN, FIXED)}
    annual, windows, checks = [], [], {}
    fixed = csv_rows(FIXED.read_bytes())
    with ZipFile(HISTORY) as history, ZipFile(DOMAIN) as domain:
        for case, last in CASES.items():
            rows, chosen, errors = production_case(case, last, history, domain, fixed)
            annual.extend(rows)
            windows.extend(chosen)
            checks[case] = errors
    if max(r["shell_equation"] for r in checks.values()) > 1e-8:
        raise ValueError("The independent shell stock does not close the exterior/box difference")
    controls = calibration(annual, sources)
    output.mkdir(parents=True, exist_ok=True)
    write_rows(output / "annual_balances.csv", annual)
    write_rows(output / "milestone_and_decade_balances.csv", windows)
    write_rows(output / "restart_calibration.csv", controls)
    evidence = dict(source_sha256={str(p.relative_to(ASSETS)): h for p, h in sources.items()},
                    max_abs_differences_over_label=checks, production_intervals=len(annual))
    (output / "input_and_crosscheck.json").write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    run(parser.parse_args().output)
