"""Combine authenticated midplane-slab scores and archived 90° row comparisons."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from score_four_case_midplane_slabs import ASSETS, DEPTHS, HALVES, PILOT_COMPLETION_SHA, front


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
REGISTRATION = ASSETS / "four_case_midplane_slabs_2026-11-26/registration.json"
CONTROL_KEYS = ("time_zero_status", "search_kpc2", "time_zero_selected_kpc2", "time_zero_share_of_search",
                "time_zero_invalid_fit_kpc2", "time_zero_touches_aperture")
SCORE_KEYS = ("selected_kpc2", "overlap_kpc2", "missed_kpc2", "false_kpc2", "completeness", "purity",
              "selection_touches_aperture")


def case_key(entry):
    return entry["case"], int(entry["snapshot_index"])


def checked_path(directory, record):
    path = directory / record["path"]
    if front.HASH(path) != record["sha256"]:
        raise ValueError(f"Receipt or table SHA-256 mismatch for {path.name}")
    return path


def check_manifest(manifest, registration):
    cases = {(case, age) for case in CASES for age in (10, 20, 30, 40, 50)}
    cases -= {("G-HI", 20), ("G-HI", 50)}
    expected = {case_key(row): row for row in registration["science"]}
    actual = [case_key(row) for row in manifest["units"]]
    if set(expected) != cases or len(registration["science"]) != len(cases):
        raise ValueError("Registration differs from the 18 agreed case-ages")
    if set(actual) != cases or len(actual) != len(cases):
        raise ValueError("Manifest has an omitted, duplicated or unexpected prospective case-age")
    if "pilot" in manifest and case_key(manifest["pilot"]) != ("G-HI", 20):
        raise ValueError("Only G-HI/20 belongs in the exposed pilot slot")
    return expected


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def keyed(rows, keys, expected):
    entries = {tuple(row[k] for k in keys): row for row in rows}
    if len(entries) != len(rows) or entries.keys() != expected:
        raise ValueError(f"Missing, duplicated or unexpected score rows for {keys}")
    return entries


def selected(row, keys):
    return {k: row[k] for k in keys}


def unit_tables(directory, entry, frozen):
    score_file = checked_path(directory, entry["score_receipt"])
    side_file = checked_path(directory, entry["row_receipt"])
    score, side = (json.loads(p.read_text()) for p in (score_file, side_file))
    unit = case_key(entry)
    if (case_key(score) != unit or case_key(side) != unit or score["status"] != "complete"
            or score["view_deg"] != 0 or not score["full_depth_candidate_matches_archive"]
            or score["projection_receipt_sha256"] != side["projection_completion_sha256"]
            or score["projection_file_sha256"] != side["projection_sha256"]
            or score["actual_time_myr"] != side["actual_time_myr"]):
        raise ValueError(f"Case-age, native projection or time differs between score and row receipts for {unit}")
    if frozen is None:
        if unit != ("G-HI", 20) or score["projection_receipt_sha256"] != PILOT_COMPLETION_SHA:
            raise ValueError("Wrong exposed pilot projection")
    elif (score["expected_full_depth_mask_sha256"] != frozen["sealed_radial_mask_sha256"]
          or score["candidate_mask_sha256"]["full"] != frozen["sealed_radial_mask_sha256"]
          or not np.isclose(score["actual_time_myr"], frozen["actual_age_myr"], rtol=0, atol=1e-10)
          or side["current_archive"]["producer_sha256"] != frozen["previous_producer_sha256"]
          or side["current_archive"]["side_map_sha256"] != frozen["archive_90_sha256"]
          or side["initial_archive"]["producer_sha256"] != frozen["initial_previous_producer_sha256"]):
        raise ValueError(f"Mask, native age or perpendicular producer differs from registration for {unit}")
    fields = {}
    for name in ("areas", "sensitivity", "time_zero_controls", "coverage_controls", "depth_flux", "filling"):
        filename = f"{name}.csv"
        product = checked_path(score_file.parent, {"path": filename, "sha256": score["products"][filename]})
        fields[name] = read_csv(product)
        if any(case_key(r) != unit or float(r["actual_time_myr"]) != score["actual_time_myr"]
               or int(r["view_deg"]) != 0 for r in fields[name]):
            raise ValueError(f"Label differs in {filename} for {unit}")
    perpendicular = read_csv(checked_path(side_file.parent, {"path": "row_summary.csv",
                                                            **side["files"]["row_summary.csv"]}))
    field_names = ("current", "initial", "current_lobe_cells", "initial_on_current_lobe_cells")
    exact = keyed([r for r in perpendicular if r["side_view_cut"] == "exact"], ("field", "depth"),
                  {(f, d) for f in field_names for d in DEPTHS})
    if any(case_key(r) != unit for r in perpendicular):
        raise ValueError("Perpendicular row labels differ from the native unit")
    for row in exact.values():
        if row["status"] == "compared":
            if int(row["compared_z_rows"]) != side["native_z_rows"]:
                raise ValueError("A perpendicular receipt covers only part of the native z axis")
        elif row["status"] != "unchecked" or not row["reason"]:
            raise ValueError("An unavailable perpendicular comparison needs its recorded reason")

    duos = {(d, h) for d in DEPTHS for h in HALVES}
    triples = {(d, h, t) for d, h in duos for t in ("full_lobe", "slab_lobe")}
    areas, sensitivity = (keyed(fields[n], ("depth", "hemisphere", "target"), triples) for n in ("areas", "sensitivity"))
    nulls, coverage = (keyed(fields[n], ("depth", "hemisphere"), duos) for n in ("time_zero_controls", "coverage_controls"))
    flux = keyed([r for r in fields["depth_flux"] if r["sightlines"] == "lobe"], ("depth", "hemisphere"), duos)
    filling = keyed([r for r in fields["filling"] if r["region"] == "full_lobe"], ("depth", "hemisphere"), duos)
    boundary = sum(score["native_tracer_boundary_face_cells"].values())
    pooled, targets, controls = [], [], []
    for d in DEPTHS:
        for h in HALVES:
            key = d, h
            null, cov, f = nulls[key], coverage[key], flux[key]
            controls.append({"case": unit[0], "depth": d, "hemisphere": h,
                             "initial_image_sha256": score["time_zero_image_sha256"][d],
                             "sky_axes_sha256": json.dumps(score["sky_axes_sha256"], sort_keys=True, separators=(",", ":")),
                             "null_mask_sha256": score["time_zero_mask_sha256"][d],
                             "initial_annular_support": json.dumps(score["support_by_5kpc_annulus"][d]["initial"],
                                                                   sort_keys=True, separators=(",", ":")),
                             **selected(null, CONTROL_KEYS), "first_clean_cut": cov["first_clean_cut"],
                             "first_clean_status": cov["first_clean_status"]})
            for target in ("full_lobe", "slab_lobe"):
                a, s = (table[d, h, target] for table in (areas, sensitivity))
                targets.append({**a, "native_tracer_face_contact": bool(boundary),
                                "side_time_zero_status": null["time_zero_status"],
                                **selected(s, ("primary_time_zero_status", "first_clean_status", "first_clean_cut")),
                                **{f"first_clean_{k}": s[k] for k in SCORE_KEYS}})
            if h != "both":
                continue
            a = areas[d, h, "full_lobe"]
            common = ("case", "snapshot_index", "actual_time_myr", "view_deg", "depth", "lobe_kpc2",
                      "native_lobe_kpc3", "slab_area_retained_fraction", "slab_volume_retained_fraction",
                      "lobe_outside_aperture_kpc2", "lobe_touches_sky_edge")
            pooled.append({
                **selected(a, common), "native_tracer_face_contact": bool(boundary),
                **{f"registered_{k}": a[k] for k in SCORE_KEYS},
                **selected(null, (*CONTROL_KEYS, "current_false_in_time_zero_outline_kpc2", "dimmed_on_lobe_kpc2",
                                  "brightened_on_lobe_kpc2", "dimmed_off_lobe_in_search_kpc2",
                                  "brightened_off_lobe_in_search_kpc2", "invalid_initial_on_lobe_kpc2",
                                  "invalid_initial_off_lobe_in_search_kpc2", "full_lobe_in_search_kpc2")),
                **selected(cov, ("control_coverage", "lobe_in_control_outline_kpc2", "overlap_in_control_outline_kpc2",
                                 "overlap_outside_control_outline_kpc2", "overlap_dimmed_kpc2", "overlap_not_dimmed_kpc2",
                                 "overlap_invalid_initial_kpc2", "dimmed_on_lobe_missed_kpc2", "first_clean_status",
                                 "first_clean_cut", "first_clean_coverage", "first_clean_purity", "first_clean_false_kpc2",
                                 "first_clean_touches_aperture")),
                **selected(f, ("initial_flux", "current_flux", "initial_lobe_flux", "current_lobe_flux",
                               "tracer_change_flux", "ambient_change_flux", "outer_initial_flux", "outer_current_flux",
                               "matched_deficit", "unchanged_outer_deficit", "full_deficit", "dilution_by_initial_outer_light",
                               "change_due_to_outer_brightening")),
                **selected(filling[key], ("fitted_deficit_fraction", "fitted_background_over_initial")),
            })
    return pooled, targets, controls, perpendicular


def distinct_controls(all_controls):
    controls = {}
    for entry in all_controls:
        key = tuple(entry[k] for k in ("case", "depth", "hemisphere"))
        if key in controls and entry != controls[key]:
            raise ValueError(f"Time-zero control or geometric identity varies among ages for {key}")
        controls[key] = entry
    return list(controls.values())


def physical_figure(output, rows):
    fig, axes = plt.subplots(2, 2, figsize=(8.1, 5.8), sharex=True, sharey=True, layout="constrained")
    styles = (("full", "Full depth", "#252830", "o"), ("slab30", "±30 kpc", "#156868", "s"),
              ("slab10", "±10 kpc", "#b34c12", "^"))
    for case, ax in zip(CASES, axes.flat, strict=True):
        for depth, label, color, marker in styles:
            data = sorted((r for r in rows if r["case"] == case and r["depth"] == depth),
                          key=lambda r: int(r["snapshot_index"]))
            by_index = {int(r["snapshot_index"]): r for r in data}
            x, y = [], []
            for i in (10, 20, 30, 40, 50):
                row = by_index.get(i)
                x.append(float(row["actual_time_myr"]) if row else i)
                y.append(float(row["matched_deficit"]) * 100 if row and row["matched_deficit"] != "" else np.nan)
            ax.plot(x, y, label=label, color=color, lw=1.35, marker=marker, markersize=5)
        ax.axhline(0, color=".6", ls=":", lw=.8)
        ax.spines[["right", "top"]].set_visible(False)
        ax.set(title=case, xticks=[10, 20, 30, 40, 50], xlim=(8, 52))
    axes[0, 0].legend(frameon=False, loc="best", fontsize=8)
    fig.supxlabel("Age (Myr)")
    fig.supylabel("Flux deficit over the full tracer footprint (%)")
    fig.savefig(output, dpi=160)
    plt.close(fig)


def depth_comparison(rows):
    values = {(int(r["snapshot_index"]), r["depth"]): r["matched_deficit"] for r in rows}
    ages = sorted({age for age, _ in values})
    evaluable = [tuple(float(values[i, d]) for d in DEPTHS) for i in ages if all(values[i, d] != "" for d in DEPTHS)]
    return {"case_ages": len(ages), "evaluable_at_all_depths": len(evaluable),
            "larger_deficit_at_slab10_than_full": sum(inner > full for full, _, inner in evaluable),
            "deficit_increases_at_both_depth_cuts": sum(full < middle < inner for full, middle, inner in evaluable)}


def run(manifest_path, output, registration_path=REGISTRATION):
    if output.exists():
        raise FileExistsError(f"Aggregate directory already exists: {output}")
    manifest, registration = (json.loads(p.read_text()) for p in (manifest_path, registration_path))
    expected = check_manifest(manifest, registration)
    combined = {"case_age_depth": [], "case_age_targets": [], "case_depth_controls": [], "perpendicular_rows": []}
    counts = Counter()
    for entry in sorted(manifest["units"], key=case_key):
        unit = case_key(entry)
        tables = unit_tables(manifest_path.parent, entry, expected[unit])
        counts[unit[0]] += 1
        for merged, per_unit in zip(combined.values(), tables, strict=True):
            merged.extend(per_unit)
    controls = distinct_controls(combined["case_depth_controls"])
    if len(controls) != len(CASES) * len(DEPTHS) * len(HALVES):
        raise ValueError("Time-zero controls do not cover all cases, depths and hemispheres")
    combined["case_depth_controls"] = [{**r, "number_of_case_ages": counts[r["case"]]} for r in controls]
    if "pilot" in manifest:
        combined["pilot_case_age_depth"] = unit_tables(manifest_path.parent, manifest["pilot"], None)[0]
    pooled = combined["case_age_depth"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp) / "cohort"
        work.mkdir()
        for name, rows in combined.items():
            front.write_rows(work / f"{name}.csv", rows)
        physical_figure(work / "physical_deficit.png", pooled)
        result = {
            "case_ages": len(expected), "prospective_images": len(pooled), "ordered_cases": list(CASES),
            "case_depth_controls": len(controls) // len(HALVES), "pilot_separate": True,
            "pilot_in_separate_table": "pilot" in manifest,
            "shared_control_status": dict(Counter(r["time_zero_status"] for r in controls if r["hemisphere"] == "both")),
            "matched_flux_by_case": {c: depth_comparison([r for r in pooled if r["case"] == c]) for c in CASES},
            "exact_perpendicular_field_depths": dict(Counter(r["status"] for r in combined["perpendicular_rows"]
                                                              if r["side_view_cut"] == "exact")),
            "denominator": "Matched flux is integrated over the full evolved tracer footprint at all depths.",
            "sampling": "Each case is one production run viewed along y at several ages.",
            "manifest_sha256": front.HASH(manifest_path), "registration_sha256": front.HASH(registration_path),
            "summariser_sha256": front.HASH(Path(__file__)),
            "products": {p.name: front.HASH(p) for p in sorted(work.iterdir())},
        }
        (work / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        work.rename(output)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.manifest, args.out)
