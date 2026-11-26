import copy
import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import summarise_four_case_midplane_slabs as panel


def registered_manifest():
    registration = json.loads(panel.REGISTRATION.read_text())
    return registration, {"units": [panel.selected(r, ("case", "snapshot_index")) for r in registration["science"]],
                          "pilot": {"case": "G-HI", "snapshot_index": 20}}


def test_registration_rejects_duplicate_or_pilot_in_place_of_a_prospective_age():
    registration, manifest = registered_manifest()
    assert len(panel.check_manifest(manifest, registration)) == 18
    for replacement in (manifest["pilot"], manifest["units"][1]):
        wrong = copy.deepcopy(manifest)
        wrong["units"][0] = replacement
        with pytest.raises(ValueError, match="omitted, duplicated or unexpected"):
            panel.check_manifest(wrong, registration)


def test_time_zero_control_with_same_area_but_different_raster_cannot_be_deduplicated():
    base = {"case": "G-LO", "depth": "slab10", "hemisphere": "both", "time_zero_selected_kpc2": 8,
            "initial_image_sha256": "abc", "sky_axes_sha256": "uvw", "null_mask_sha256": "xyz"}
    assert panel.distinct_controls([base, dict(base)]) == [base]
    for field in ("initial_image_sha256", "sky_axes_sha256", "null_mask_sha256"):
        with pytest.raises(ValueError, match="varies among ages"):
            panel.distinct_controls([base, {**base, field: "different"}])


def test_atmosphere_count_requires_matching_detector_outcomes_across_powers():
    high = {"case": "G-HI", "depth": "slab10", "sky_axes_sha256": "axes", "null_mask_sha256": "mask",
            "time_zero_status": "failed_nonempty", "first_clean_status": "found", "first_clean_cut": 0.08}
    low = {**high, "case": "G-LO"}
    assert panel.atmosphere_control_counts([high, low]) == {"failed_nonempty": 1}
    for field, value in (("null_mask_sha256", "other mask"), ("first_clean_cut", 0.07)):
        with pytest.raises(ValueError, match="different control"):
            panel.atmosphere_control_counts([high, {**low, field: value}])


def test_authenticated_score_and_perpendicular_receipts_must_bind_the_same_projection(tmp_path):
    unit = {"case": "G-HI", "snapshot_index": 20}
    common = {**unit, "actual_time_myr": 19.99}
    score = {**common, "status": "complete", "view_deg": 0, "full_depth_candidate_matches_archive": True,
             "projection_receipt_sha256": panel.PILOT_COMPLETION_SHA, "projection_file_sha256": "scored"}
    side = {**common, "projection_completion_sha256": panel.PILOT_COMPLETION_SHA, "projection_sha256": "other"}
    for key, data in (("score_receipt", score), ("row_receipt", side)):
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps(data))
        unit[key] = {"path": path.name, "sha256": panel.front.HASH(path)}
    with pytest.raises(ValueError, match="differs between score and row"):
        panel.unit_tables(tmp_path, unit, None)
    (tmp_path / "row_receipt.json").write_text("{}")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        panel.unit_tables(tmp_path, unit, None)


def test_aggregation_keeps_exposed_pilot_separate_and_counts_repeated_ages_by_case(tmp_path, monkeypatch):
    _, manifest = registered_manifest()
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))

    def synthetic_tables(directory, entry, frozen):
        case, age = panel.case_key(entry)
        base = {"case": case, "snapshot_index": age, "actual_time_myr": age}
        pooled = [{**base, "depth": d, "matched_deficit": str(v), "lobe_kpc2": 10,
                   "dimmed_on_lobe_kpc2": 10 * v, "dilution_by_initial_outer_light": v - 0.2,
                   "change_due_to_outer_brightening": 0.0} for d, v in zip(panel.DEPTHS, (0.2, 0.4, 0.3))]
        targets = [{**base, "depth": "full", "target": "full_lobe"}]
        controls = []
        for d in panel.DEPTHS:
            group_slab = case.startswith("G-") and d != "full"
            for h in panel.HALVES:
                controls.append({"case": case, "depth": d, "hemisphere": h, "sky_axes_sha256": "axes",
                                 "null_mask_sha256": d if group_slab else "empty", "first_clean_status": "found",
                                 "first_clean_cut": 0.08 if group_slab else 0.05,
                                 "time_zero_status": "failed_nonempty" if group_slab else "empty"})
        side = [{**base, "side_view_cut": "exact", "status": "compared"}]
        return pooled, targets, controls, side

    monkeypatch.setattr(panel, "unit_tables", synthetic_tables)
    out = tmp_path / "summary"
    result = panel.run(path, out)
    assert result["case_ages"] == 18 and result["prospective_images"] == 54
    assert result["case_depth_controls"] == 12
    assert result["case_depth_control_status"] == {"empty": 8, "failed_nonempty": 4}
    assert result["atmosphere_depth_controls"] == 6
    assert result["atmosphere_depth_control_status"] == {"empty": 4, "failed_nonempty": 2}
    assert result["matched_flux_by_case"]["G-HI"] == {
        "case_ages": 3, "evaluable_at_all_depths": 3, "larger_deficit_at_slab10_than_full": 3,
        "deficit_increases_at_both_depth_cuts": 0}
    with (out / "pilot_case_age_depth.csv").open() as stream:
        assert [(r["case"], r["depth"]) for r in csv.DictReader(stream)] == [("G-HI", d) for d in panel.DEPTHS]
    with (out / "case_age_depth.csv").open() as stream:
        assert all(panel.case_key(r) != ("G-HI", 20) for r in csv.DictReader(stream))
    assert result["products"]["physical_deficit.png"] == panel.front.HASH(out / "physical_deficit.png")


def test_physical_summary_keeps_signed_outer_change_and_skips_zero_denominators():
    rows = [{"case": "G-HI", "snapshot_index": 40, "depth": d, "lobe_kpc2": 10,
             "dimmed_on_lobe_kpc2": a, "matched_deficit": f,
             "dilution_by_initial_outer_light": 0.55, "change_due_to_outer_brightening": -0.05}
            for d, a, f in zip(panel.DEPTHS, (1, 4, 8), (0.1, 0.3, 0.6), strict=True)]
    empty = [dict(r, snapshot_index=10, lobe_kpc2=0, dimmed_on_lobe_kpc2=0, matched_deficit="") for r in rows]
    summary = panel.physical_summary(rows + empty)
    assert summary["evaluable_area_case_ages"] == summary["dimmed_area_increases_at_both_cuts"] == 1
    assert summary["median_dimmed_area_fraction"] == dict(full=0.1, slab30=0.4, slab10=0.8)
    assert summary["defined_initial_light_fractions_full_to_slab10"] == 1
    assert summary["initial_light_fraction_full_to_slab10_median"] == pytest.approx(1.1)
