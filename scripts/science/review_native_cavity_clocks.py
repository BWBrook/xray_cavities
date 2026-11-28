"""Independently check the 19 native cavity clock and power comparisons."""
import argparse
import csv
import gzip
import io
import json
import math
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
CLOCKS = ("sound_crossing", "buoyant_rise", "refill")
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
SIDES = ("negative_z", "positive_z")
KPC_CM = 3.085677581491367e21
MYR_S = 31_557_600_000_000


def csv_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def keyed(rows, column=None):
    result = {}
    for row in rows:
        key = (row["case"], int(row["snapshot_index"]))
        if column:
            key += (row[column],)
        if key in result:
            raise ValueError(f"Duplicate {key}")
        result[key] = row
    return result


def initial_profiles(path, axial_archive):
    fields = ("radius_kpc", "density_code", "pressure_code")
    raw = defaultdict(list)
    for row in csv_rows(path):
        raw[row["environment"]].append([float(row[k]) for k in fields])
    if set(raw) != {"C", "G"}:
        raise ValueError("Expected the cluster and group initial profiles")
    if axial_archive:
        verified = []
        with tarfile.open(axial_archive, "r|gz") as bundle:
            for member in bundle:
                if member.name.endswith("/snapshot_0000_axial_profile.csv"):
                    case = Path(member.name).parts[0]
                    rows = csv.DictReader(io.StringIO(bundle.extractfile(member).read().decode()))
                    original = [[float(r[k]) for k in ("z_kpc", "baseline_rho_code", "baseline_pressure_code")]
                                for r in rows if float(r["z_kpc"]) >= 1]
                    if case not in CASES or not np.array_equal(original, raw[case[0]]):
                        raise ValueError(f"Archived initial atmosphere differs from the public profile for {case}")
                    verified.append(case)
        if sorted(verified) != sorted(CASES):
            raise ValueError("Archive must contain one initial axial profile for each production case")
    profiles = {}
    for env, values in raw.items():
        z, density, pressure = np.array(values).T
        dz = np.diff(z)
        if not (len(z) >= 3 and np.all(dz > 0) and np.all(density > 0) and np.all(pressure > 0)):
            raise ValueError(f"Invalid radial atmosphere for {env}")
        # A quadratic through adjacent nonuniform nodes gives this weighted mean of the two secants.
        slope = np.diff(pressure) / dz
        gradient = (slope[:-1] * dz[1:] + slope[1:] * dz[:-1]) / (dz[:-1] + dz[1:])
        c = 2.99792458e10
        profiles[env] = (z[1:-1], c * np.sqrt((5 / 3) * pressure[1:-1] / density[1:-1]),
                         -c**2 * gradient / (KPC_CM * density[1:-1]))
    return profiles


def direct_receipts(path, cohort):
    if path is None:
        return {}
    names = {key: f"{key[0]}_{key[1]:04d}.json" for key in cohort}
    if path.is_dir():
        return {key: json.loads((path / name).read_bytes()) for key, name in names.items()}
    with zipfile.ZipFile(path) as bundle:
        if sorted(bundle.namelist()) != sorted(names.values()):
            raise ValueError("Native ZIP must contain one named receipt for each of the 19 case-ages")
        return {key: json.loads(bundle.read(name)) for key, name in names.items()}


def delivery_histories():
    histories = {}
    with zipfile.ZipFile(ASSETS / "production_injector_histories_2026-11-21/history_tables.zip") as bundle:
        for case in CASES:
            name = f"native/summary/{case}/injector_snapshot_rates.csv"
            rows = csv.DictReader(io.StringIO(bundle.read(name).decode()))
            samples = sorted((int(r["index"]), float(r["age_myr"]), float(r["gas_energy_over_label"]))
                             for r in rows if r["region"] == "net" and r["method"] == "linear_snapshot_flags")
            label = 2e45 if case.endswith("HI") else 2e43
            increments = []
            for (i, t0, q0), (j, t1, q1) in zip(samples, samples[1:]):
                if j != i + 1 or t1 <= t0:
                    raise ValueError(f"Incomplete delivery history for {case}")
                increments.append((q1 + q0) / 2 * (t1 - t0) * MYR_S * label)
                histories[case, j] = (t1, math.fsum(increments))
    return histories


def side_times(profile, radius, volume, section):
    z, cs, g = profile
    if not z[0] <= radius <= z[-1]:
        raise ValueError(f"Centroid outside atmosphere at {radius} kpc")
    cs, g = (float(np.interp(radius, z, values)) for values in (cs, g))
    r = radius * KPC_CM
    v = math.sqrt((8 / 3) * g * KPC_CM * volume / section)
    reff = KPC_CM * math.cbrt(volume / (4 * math.pi / 3))
    return (r / cs / MYR_S, r / v / MYR_S, math.sqrt(4 * reff / g) / MYR_S)


def eligibility(folder):
    with gzip.open(ASSETS / "heldout_xray_2026-11-24/scores.csv.gz", "rt") as stream:
        rows = [r for r in csv.DictReader(stream) if r["kind"] == "science" and r["primary"] == "True"]
    results = {}
    reported = csv_rows(folder / "xray_eligibility.csv")
    for mode, method in sorted({(r["mode"], r["method"]) for r in rows}):
        sample = [r for r in rows if (r["mode"], r["method"]) == (mode, method)]
        passing = defaultdict(set)
        for r in sample:
            if (float(r["completeness"]) >= .75 and float(r["purity"] or 0) >= .95
                    and r["aperture_contact"] == "False"):
                passing[r["unit_id"]].add(r["hemisphere"])
        counts = (len(sample), sum(map(len, passing.values())), sum(len(v) == 2 for v in passing.values()))
        matched = [r for r in reported if (r["mode"], r["method"]) == (mode, method) and r["cohort"] == "held_out"]
        if (len(matched) != 18 or counts[0] != 108 or counts != tuple(sum(int(r[k]) for r in matched)
                for k in ("heldout_science_sides", "passed_sides", "passed_bipolar_views"))):
            raise ValueError(f"Held-out eligibility differs for {mode}/{method}")
        results[f"{mode}/{method}"] = dict(zip(("tested_sides", "passing_sides", "bipolar_views"), counts))
    return results


def review(folder, direct, axial_archive=None, tables_folder=None):
    tables_folder = tables_folder or folder
    projections = keyed(csv_rows(folder / "ortho_geometry.csv"), "side")
    sides = keyed(csv_rows(tables_folder / "side_clocks.csv"), "side")
    pairs = keyed(csv_rows(tables_folder / "bipolar_powers.csv"), "clock")
    references = keyed(csv_rows(ASSETS / "native_delivery_restatement_2026-11-21/primary_selected_ages.csv"))
    cohort = {(c, i) for c in CASES for i in (10, 20, 30, 40, 50) if (c, i) != ("G-HI", 50)}
    side_keys = {(*k, s) for k in cohort for s in SIDES}
    if (set(sides) != side_keys or set(projections) != side_keys or set(references) != cohort
            or set(pairs) != {(*k, j) for k in cohort for j in CLOCKS}):
        raise ValueError("Case, age, clock or side coverage differs from the 19 selected snapshots")
    profiles = initial_profiles(folder / "initial_atmospheres.csv", axial_archive)
    receipts, deliveries = direct_receipts(direct, cohort), delivery_histories()
    with np.load(ASSETS / "ghi20_compressive_front_native_2026-11-23/native_axes.npz") as axes:
        widths = [np.diff(axes[k + "_edges"]) / np.gradient(axes[k]) for k in "xyz"]
    low_weight, high_weight = (math.prod(func(w) for w in widths) for func in (min, max))
    tables = {}
    for env, number in (("C", "002003"), ("G", "002031")):
        raw = np.loadtxt(ASSETS / f"q032_synthetic_harness_2026-10-31/inputs/tabulated_cosmo_{number}.csv")
        tables[env] = (raw[:, 0] / KPC_CM, np.sqrt((5 / 3) * raw[:, 2] / raw[:, 1]), abs(raw[:, 4]))
    errors, sensitivity, ratios = defaultdict(float), defaultdict(float), defaultdict(list)

    def check(name, actual, expected):
        relative = abs(float(actual) / expected - 1)
        if not relative <= 2e-9:
            raise ValueError(f"{name} at {case}/{index}: {actual} vs {expected}")
        errors[name] = max(errors[name], relative)

    for case, index in sorted(cohort):
        key = case, index
        age, energy = deliveries[key]
        reference = references[key]
        total = float(reference["native_enthalpy_2p5pv_erg"])
        check("age", reference["actual_age_myr"], age)
        check("net_gas_delivery", reference["cumulative_net_gas_delivery_erg"], energy)
        measured = receipts.get(key)
        if direct and (measured["case"], measured["index"], measured["actual_age_myr"]) != (case, index, age):
            raise ValueError(f"Native receipt identity differs at {key}")
        sources = [projections[*key, s] for s in SIDES]
        old = np.array([float(r["historical_q029_side_enthalpy_2p5pv_erg"]) for r in sources])
        # Each cell contributes a positive pV. Both side intervals have to fit the measured whole-lobe H.
        negative_limits = (max(low_weight * old[0], total - high_weight * old[1]),
                           min(high_weight * old[0], total - low_weight * old[1]))
        h = (np.array([measured["sides"][s]["enthalpy_2p5pV_erg"] for s in SIDES])
             if direct else old / sum(old) * total)
        if not negative_limits[0] <= h[0] <= negative_limits[1]:
            raise ValueError(f"Side split outside the exact cell-volume bounds at {key}")
        check("whole_lobe_enthalpy", sum(h), total)
        times, union_times = [], []
        for side, archive, hs in zip(SIDES, sources, h, strict=True):
            row = sides[*key, side]
            geom = measured["sides"][side] if direct else archive
            x, y, z = (float(geom[f"centroid_{a}_kpc"]) for a in "xyz")
            radius = math.hypot(x, y, z)
            volume, area = float(geom["volume_kpc3"]), float(geom["axial_max_section_kpc2"])
            profile = profiles[case[0]]
            t = np.array(side_times(profile, radius, volume, area))
            times.append(t)
            for clock, ts in zip(CLOCKS, t, strict=True):
                check("side_time", row[f"{clock}_myr"], ts)
                check("side_power", row[f"{clock}_power_2p5pv_erg_s"], hs / (ts * MYR_S))
            alternate = side_times(tables[case[0]], radius, volume, area)
            sensitivity["prescribed_vs_grid_side_age_max_fraction"] = max(
                sensitivity["prescribed_vs_grid_side_age_max_fraction"], max(abs(alternate / t - 1)))
            for field in ("centroid_radius_lower_kpc", "centroid_radius_upper_kpc"):
                geo_times = side_times(profile, float(archive[field]), volume, area)
                sensitivity["archived_centroid_endpoint_side_age_max_fraction"] = max(
                    sensitivity["archived_centroid_endpoint_side_age_max_fraction"], max(abs(geo_times / t - 1)))
            sensitivity["centroid_to_axis_max_deg"] = max(sensitivity["centroid_to_axis_max_deg"],
                                                          math.degrees(math.atan2(math.hypot(x, y), abs(z))))
            if direct:
                union_times.append(side_times(profile, radius, volume, geom["axial_union_area_kpc2"])[1])
        for j, clock in enumerate(CLOCKS):
            row = pairs[*key, clock]
            t = np.array(times)[:, j]
            harmonic = sum(h) / sum(h / t)
            Q = sum(h / (t * MYR_S))
            ratio = sum((h / energy) * (age / t))
            check("effective_age", row["effective_age_myr"], harmonic)
            check("power", row["power_2p5pv_erg_s"], Q)
            check("power_over_actual_mean", row["power_over_mean_delivery"], ratio)
            check("mean_actual_power", row["mean_delivered_power_erg_s"], energy / (age * MYR_S))
            check("powers_4pv", row["power_4pv_erg_s"], 1.6 * Q)
            check("factor_product", Q / (energy / (age * MYR_S)), (total / energy) * age / harmonic)
            ratios[clock].append((harmonic / age, ratio))
            sensitivity["legacy_enthalpy_power_max_fraction"] = max(sensitivity["legacy_enthalpy_power_max_fraction"],
                                                                    abs(sum(old / t) / (Q * MYR_S) - 1))
            for h_neg in negative_limits:
                ratio_limit = (h_neg / t[0] + (total - h_neg) / t[1]) * age / energy
                sensitivity["side_enthalpy_allocation_max_absolute_power_ratio_change"] = max(
                    sensitivity["side_enthalpy_allocation_max_absolute_power_ratio_change"], abs(ratio_limit - ratio))
            if direct and clock == "buoyant_rise":
                union_ratio = sum(h / union_times) * age / energy
                check("union_power", row["union_area_power_over_mean_delivery"], union_ratio)
                sensitivity["union_vs_max_section_power_max_fraction"] = max(
                    sensitivity["union_vs_max_section_power_max_fraction"], abs(union_ratio / ratio - 1))
    stats = {}
    for clock, rows in ratios.items():
        stats[clock] = {k: dict(min=min(v), median=median(v), max=max(v)) for k, v in
                        zip(("effective_age_over_true", "power_over_mean_delivery"), zip(*rows), strict=True)}
    return dict(case_ages=len(cohort), sides=len(sides), pairs=len(pairs), direct_native_receipts=bool(direct),
                maximum_relative_disagreement=dict(errors), sensitivities=dict(sensitivity), ranges=stats,
                heldout_eligibility=eligibility(tables_folder))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=ASSETS / "native_clocks_2026-11-28")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--direct", type=Path, help="Directory or ZIP of 19 direct native receipts (default: native_receipts.zip)")
    source.add_argument("--archive-only", action="store_true", help="Check the geometry and pressure split from the older projections")
    parser.add_argument("--axial-archive", type=Path, help="Check the public density and pressure profiles against the original axial tar")
    parser.add_argument("--tables", type=Path, help="Directory of the three clock result tables to check (defaults to --folder)")
    parser.add_argument("--output", type=Path, help="Write the aggregate report as JSON; defaults to stdout")
    options = parser.parse_args()
    direct = None if options.archive_only else options.direct or options.folder / "native_receipts.zip"
    result = review(options.folder, direct, options.axial_archive, options.tables)
    report = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if options.output:
        options.output.write_text(report)
    else:
        print(report, end="")
