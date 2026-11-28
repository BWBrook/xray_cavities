"""Measure the three cavity clocks on the 19 selected native bipolar lobes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np

from build_four_case_cavity_age_method_comparison import (
    AGES, ASSET_ROOT, AXIAL_ARCHIVE, CASES, CASE_POWER_ERG_S, EXCLUDED_SCIENCE_CASE_AGES,
    GAMMA_AMBIENT, KPC_CM, SECONDS_PER_MYR, SIDES, atmosphere_at, buoyant_age_myr,
    load_initial_atmospheres, read_rows, refill_age_myr, sha256_file, sound_age_myr,
    write_json, write_rows,
)
from summarise_heldout_xray import CUSTODY, METHODS, MODES, primary_results, read_scores


ASSETS = ASSET_ROOT / "native_clocks_2026-11-28"
REFERENCE = ASSET_ROOT / "native_delivery_restatement_2026-11-21/primary_selected_ages.csv"
SELECTION = [(case, age) for case in CASES for age in AGES if (case, age) not in EXCLUDED_SCIENCE_CASE_AGES]
CLOCKS = ("sound_crossing", "buoyant_rise", "refill")
TABLES = {"C": "002003", "G": "002031"}
REGISTRATION = ASSET_ROOT / "aperture_transport_2026-11-26/registration.json"


def extract_profiles(destination):
    profiles = load_initial_atmospheres()
    rows = []
    for environment in TABLES:
        profile = profiles[environment + "-HI"]
        for radius, sound, gravity, density, pressure in zip(
                *(profile[k] for k in ("radius_kpc", "sound_speed_km_s", "gravity_cm_s2",
                                        "density_code", "pressure_code")), strict=True):
            rows.append(dict(environment=environment, radius_kpc=radius,
                             sound_speed_km_s=sound, gravity_cm_s2=gravity,
                             density_code=density, pressure_code=pressure))
    write_rows(destination, rows)
    return sha256_file(AXIAL_ARCHIVE)


def atmospheres(folder):
    rows = read_rows(folder / "initial_atmospheres.csv")
    profiles, prescribed = {}, {}
    for env, source in TABLES.items():
        selected = [r for r in rows if r["environment"] == env]
        fields = ("radius_kpc", "sound_speed_km_s", "gravity_cm_s2")
        profiles[env] = {k: np.array([float(r[k]) for r in selected]) for k in fields}
        raw = np.loadtxt(ASSET_ROOT / "q032_synthetic_harness_2026-10-31/inputs"
                         / f"tabulated_cosmo_{source}.csv")
        prescribed[env] = dict(radius_kpc=raw[:, 0] / KPC_CM,
                               sound_speed_km_s=np.sqrt(GAMMA_AMBIENT * raw[:, 2] / raw[:, 1]) / 1e5,
                               gravity_cm_s2=np.abs(raw[:, 4]))
        for profile in (profiles[env], prescribed[env]):
            if not np.all(np.diff(profile["radius_kpc"]) > 0):
                raise ValueError(f"Unordered {env} atmosphere")
    return profiles, prescribed


def by_key(rows, names):
    keyed = {tuple(str(row[k]) for k in names): row for row in rows}
    if len(keyed) != len(rows):
        raise ValueError(f"Duplicate {names}")
    return keyed


def observer_eligibility():
    seal = json.loads((CUSTODY / "seal.json").read_text())
    receipt = json.loads((CUSTODY / "private_scoring_custody.json").read_text())
    scores = read_scores(seal, receipt)
    primary_results(scores)
    science = [r for r in scores if r["kind"] == "science" and r["primary"] == "True"]
    result = []
    for case, index in SELECTION:
        for mode in MODES:
            for method in METHODS:
                subset = [r for r in science if (r["case"], int(r["snapshot_index"]), r["mode"], r["method"])
                          == (case, index, mode, method)]
                keys = {(r["view_deg"], r["hemisphere"]) for r in subset}
                pilot = (case, index) == ("G-HI", 20)
                expected = set() if pilot else {(v, s) for v in ("0", "45", "90") for s in SIDES}
                if keys != expected or len(subset) != len(keys):
                    raise ValueError(f"Unexpected DET-05 cohort for {case}/{index}")
                passed = {(r["view_deg"], r["hemisphere"]) for r in subset
                          if r["generalization_criterion_passed"] == "True"}
                both = sum(all((v, s) in passed for s in SIDES) for v in ("0", "45", "90"))
                result.append(dict(case=case, snapshot_index=index, mode=mode, method=method,
                                   cohort="development" if pilot else "held_out",
                                   heldout_science_sides=len(keys), passed_sides=len(passed) if keys else "",
                                   passed_bipolar_views=both if keys else "",
                                   nondetected_sides=sum(r["nondetection"] == "True" for r in subset) if keys else "",
                                   aperture_contact_sides=sum(r["aperture_contact"] == "True" for r in subset) if keys else "",
                                   observer_eligible_views=both if keys and mode == "observer_refit" else ""))
    return result


def archive_enthalpies(case, index, total):
    source = (ASSET_ROOT / "q029_binary_native_refresh_2026-09-06/remote_analysis" / case
              / "native_energy_selected_age.csv")
    selected = [r for r in read_rows(source) if int(r["snapshot_index"]) == index
                and r["partition_method"] == "binary_threshold_1e-3" and r["side"] in SIDES]
    old = {r["side"]: float(r["lobe_enthalpy_2p5pv_erg"]) for r in selected}
    if len(selected) != 2 or set(old) != set(SIDES) or min(old.values()) <= 0:
        raise ValueError(f"Incomplete side pressures for {case}/{index}")
    old_sum = sum(old.values())
    if abs(old_sum / total - 1) > 0.000071:
        raise ValueError(f"Archived native enthalpy outside its published agreement at {case}/{index}")
    # Conservative outward rounding of the measured native / centre-width cell volume extrema.
    lo, hi = 0.994327, 1.012619
    result = {}
    for side, other in (SIDES, SIDES[::-1]):
        result[side] = (old[side] * total / old_sum,
                        max(old[side] * lo, total - old[other] * hi),
                        min(old[side] * hi, total - old[other] * lo))
        h, low, high = result[side]
        if not 0 < low <= h <= high:
            raise ValueError("Incompatible exact total and legacy side quadrature")
    return result


def side_clocks(radius, volume, area, sound, gravity):
    effective_radius = (3 * volume / (4 * math.pi)) ** (1 / 3)
    buoyant_time, speed = buoyant_age_myr(radius, gravity, volume, area)
    return dict(sound_crossing=sound_age_myr(radius, sound), buoyant_rise=buoyant_time,
                refill=refill_age_myr(effective_radius, gravity)), effective_radius, speed


def calculate(inputs, direct):
    geo = by_key(read_rows(inputs / "ortho_geometry.csv"), ("case", "snapshot_index", "side"))
    references = by_key(read_rows(REFERENCE), ("case", "snapshot_index"))
    expected = {(c, str(i)) for c, i in SELECTION}
    if set(references) != expected or set(geo) != {(*key, s) for key in expected for s in SIDES}:
        raise ValueError("Expected exactly 19 selected case-ages and 38 native sides")
    profiles, prescribed = atmospheres(inputs)
    sides, powers = [], []
    if direct:
        run = json.loads((inputs / "native_run.json").read_text())
        if (sha256_file(REGISTRATION) != run["registration_sha256"] or
                sha256_file(inputs / "initial_atmospheres.csv") != run["compact_initial_atmospheres_sha256"]):
            raise ValueError("Native cohort registration or initial atmosphere differs")
        registered = json.loads(REGISTRATION.read_bytes())["cases"]
        jobs = {(r["case"], r["index"]): r for r in run["jobs"]}
        if set(jobs) != set(SELECTION) or len(run["jobs"]) != len(SELECTION):
            raise ValueError("Unexpected native job cohort")
    for case, index in SELECTION:
        key = case, str(index)
        ref = references[key]
        age = float(ref["actual_age_myr"])
        total = float(ref["native_enthalpy_2p5pv_erg"])
        delivery = float(ref["cumulative_net_gas_delivery_erg"])
        mean_delivery = delivery / (age * SECONDS_PER_MYR)
        archived_h = archive_enthalpies(case, index, total)
        receipt = None
        if direct:
            data = (direct / f"{case}_{index:04d}.json").read_bytes()
            receipt = json.loads(data)
            job, reg = jobs[case, index], registered[case]
            snap = reg["snapshots"][index]
            if (job["state"] != "F" or job["exit_status"] != 0
                    or hashlib.sha256(data).hexdigest() != job["sha256"]
                    or (receipt["case"], receipt["index"]) != (case, index)
                    or receipt["reader_sha256"] != run["reader_sha256"]
                    or receipt["registration_sha256"] != run["registration_sha256"]
                    or receipt["input_request_sha256"] != reg["input_request_sha256"]
                    or receipt["axes_sha256"] != reg["static_sha256"]["axes.npz"]
                    or receipt["native_sha256"] != snap["native_sha256"]
                    or receipt["fixed_receipt_sha256"] != snap["fixed_sha256"]
                    or receipt["actual_age_myr"] != snap["age_myr"]
                    or not math.isclose(receipt["actual_age_myr"], age, rel_tol=1e-12)):
                raise ValueError("Direct geometry receipt has wrong identity")
        pair = []
        for side in SIDES:
            archived = geo[(*key, side)]
            geometry = receipt["sides"][side] if receipt else archived
            radius, volume, area = (float(geometry[k]) for k in
                                     ("centroid_radius_kpc", "volume_kpc3", "axial_max_section_kpc2"))
            sound, gravity = atmosphere_at(profiles[case[0]], radius)
            cs_table, g_table = atmosphere_at(prescribed[case[0]], radius)
            h, low, high = archived_h[side]
            if receipt:
                h = float(geometry["enthalpy_2p5pV_erg"])
                if not low <= h <= high:
                    raise ValueError(f"Exact {case}/{index}/{side} enthalpy outside the archive bracket")
                low = high = h
                for k in ("volume_kpc3", "axial_max_section_kpc2"):
                    if not math.isclose(float(geometry[k]), float(archived[k]), rel_tol=2e-10):
                        raise ValueError(f"{case}/{index}/{side} orthogonal archive disagrees on {k}")
                if not float(archived["centroid_radius_lower_kpc"]) - 1e-9 <= radius <= float(
                        archived["centroid_radius_upper_kpc"]) + 1e-9:
                    raise ValueError(f"{case}/{index}/{side} native distance outside the projection bounds")
            ages, effective_radius, speed = side_clocks(radius, volume, area, sound, gravity)
            row = dict(case=case, snapshot_index=index, side=side, true_age_myr=age,
                       volume_kpc3=volume, centroid_radius_kpc=radius, axial_max_section_kpc2=area,
                       effective_radius_kpc=effective_radius, sound_speed_km_s=sound, gravity_cm_s2=gravity,
                       sound_vs_prescription_rel=sound / cs_table - 1, gravity_vs_prescription_rel=gravity / g_table - 1,
                       buoyant_speed_km_s=speed, enthalpy_2p5pv_erg=h, enthalpy_4pv_erg=1.6 * h,
                       side_enthalpy_lower_erg=low, side_enthalpy_upper_erg=high)
            for clock, t in ages.items():
                row[f"{clock}_myr"] = t
                row[f"{clock}_over_true_age"] = t / age
                row[f"{clock}_power_2p5pv_erg_s"] = h / (t * SECONDS_PER_MYR)
                row[f"{clock}_power_4pv_erg_s"] = 1.6 * row[f"{clock}_power_2p5pv_erg_s"]
            if receipt:
                row["cell_count"] = geometry["cell_count"]
                row["centroid_angle_to_outward_axis_deg"] = geometry["centroid_angle_to_outward_axis_deg"]
                row["wall_faces"] = "|".join(geometry["wall_faces"])
                row["axial_union_area_kpc2"] = geometry["axial_union_area_kpc2"]
                row["buoyant_union_myr"] = ages["buoyant_rise"] * math.sqrt(row["axial_union_area_kpc2"] / area)
            pair.append(row)
        sides.extend(pair)
        if not math.isclose(sum(s["enthalpy_2p5pv_erg"] for s in pair), total, rel_tol=2e-10):
            raise ValueError(f"Side enthalpies fail the whole-lobe native check for {key}")
        for clock in CLOCKS:
            times = [s[f"{clock}_myr"] for s in pair]
            power = sum(s[f"{clock}_power_2p5pv_erg_s"] for s in pair)
            effective_age = total / (power * SECONDS_PER_MYR)
            ratio = power / mean_delivery
            if not math.isclose(ratio, (total / delivery) * age / effective_age, rel_tol=2e-12):
                raise ValueError("Age and enthalpy factors fail the bipolar power identity")
            neg = pair[0]
            bounds = [(x / times[0] + (total - x) / times[1]) / (SECONDS_PER_MYR * mean_delivery)
                      for x in (neg["side_enthalpy_lower_erg"], neg["side_enthalpy_upper_erg"])]
            row = dict(case=case, snapshot_index=index, true_age_myr=age, clock=clock,
                       negative_age_myr=times[0], positive_age_myr=times[1], effective_age_myr=effective_age,
                       effective_age_over_true=effective_age / age, labelled_kinetic_power_erg_s=CASE_POWER_ERG_S[case],
                       cumulative_net_gas_delivery_erg=delivery, mean_delivered_power_erg_s=mean_delivery,
                       native_enthalpy_2p5pv_erg=total, true_age_power_2p5pv_erg_s=total / (age * SECONDS_PER_MYR),
                       true_age_power_over_delivery=total / delivery, power_2p5pv_erg_s=power,
                       power_over_mean_delivery=ratio, power_over_label=power / CASE_POWER_ERG_S[case],
                       clock_power_over_true_age_power=age / effective_age,
                       power_4pv_erg_s=1.6 * power, power_4pv_over_mean_delivery=1.6 * ratio,
                       pressure_split_ratio_lower=min(bounds), pressure_split_ratio_upper=max(bounds))
            if receipt:
                union = sum(s["enthalpy_2p5pv_erg"] / (s["buoyant_union_myr"] * SECONDS_PER_MYR) for s in pair)
                row["union_area_power_over_mean_delivery"] = union / mean_delivery if clock == "buoyant_rise" else ""
            powers.append(row)
    return sides, powers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, default=ASSETS)
    parser.add_argument("--output", type=Path, default=ASSETS)
    parser.add_argument("--direct", type=Path, help="nineteen native per-snapshot JSON receipts")
    parser.add_argument("--archive-only", action="store_true", help="use the independent projection and historical pressure reductions")
    parser.add_argument("--extract-atmospheres", action="store_true", help="extract the matched initial profiles and exit")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.extract_atmospheres:
        print("Time-zero axial archive SHA-256", extract_profiles(args.output / "initial_atmospheres.csv"))
        return
    if args.archive_only and args.direct:
        parser.error("--archive-only and --direct are mutually exclusive")
    if args.archive_only or args.direct:
        sides, powers = calculate(args.inputs, args.direct)
    else:
        with zipfile.ZipFile(args.inputs / "native_receipts.zip") as bundle:
            sides, powers = calculate(args.inputs, zipfile.Path(bundle))
    eligible = observer_eligibility()
    write_rows(args.output / "side_clocks.csv", sides)
    write_rows(args.output / "bipolar_powers.csv", powers)
    write_rows(args.output / "xray_eligibility.csv", eligible)
    by_clock = {}
    for clock in CLOCKS:
        selected = [r for r in powers if r["clock"] == clock]
        ranges = {}
        for k in ("effective_age_over_true", "power_over_mean_delivery"):
            values = [r[k] for r in selected]
            ranges[k] = dict(min=min(values), median=float(np.median(values)), max=max(values))
        by_clock[clock] = ranges
    summary = dict(case_ages=len(SELECTION), sides=len(sides),
               powers=len(powers), geometry="orthogonal_native_projections" if args.archive_only else "direct_native",
               primary_cross_section="maximum native section normal to the bipolar z axis",
               ranges=by_clock, max_pressure_split_ratio_width=max(
                   r["pressure_split_ratio_upper"] - r["pressure_split_ratio_lower"] for r in powers),
               maximum_sound_relative_difference=max(abs(s["sound_vs_prescription_rel"]) for s in sides),
               maximum_gravity_relative_difference=max(abs(s["gravity_vs_prescription_rel"]) for s in sides),
               side_clocks_above_true_age=sum(r[f"{c}_over_true_age"] > 1 for r in sides for c in CLOCKS),
               sides_with_formal_buoyant_speed_above_sound=sum(s["buoyant_speed_km_s"] > s["sound_speed_km_s"] for s in sides))
    if not args.archive_only:
        buoyant = [r for r in powers if r["clock"] == "buoyant_rise"]
        summary.update(sides_contacting_domain=sum(bool(s["wall_faces"]) for s in sides),
                       maximum_centroid_tilt_deg=max(s["centroid_angle_to_outward_axis_deg"] for s in sides),
                       median_silhouette_power_over_mean_delivery=float(np.median(
                           [r["union_area_power_over_mean_delivery"] for r in buoyant])),
                       maximum_relative_buoyant_power_reduction=max(
                           1 - r["union_area_power_over_mean_delivery"] / r["power_over_mean_delivery"] for r in buoyant))
    write_json(args.output / "summary.json", summary)


if __name__ == "__main__":
    main()
