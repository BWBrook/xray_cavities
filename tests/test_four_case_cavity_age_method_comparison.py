import csv

import pytest

from scripts.science.build_four_case_cavity_age_method_comparison import (
    AGE_METHODS,
    run,
)


def read_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_four_case_cavity_age_method_comparison(tmp_path):
    output = tmp_path / "comparison"
    metadata = run(output)

    assert metadata["status"] == "complete_four_case_cavity_age_method_comparison"
    assert metadata["row_counts"] == {
        "quantitative_cavity_views": 37,
        "xray_cavity_age_geometry": 74,
        "age_method_comparison": 259,
        "cavity_power_method_comparison": 518,
        "age_power_method_summary": 56,
    }
    assert metadata["excluded_science_case_ages"] == [
        {"case": "G-HI", "snapshot_index": 50, "reason": "boundary_contaminated"}
    ]
    validation = metadata["atmosphere_contract"]["group_tabulated_profile_validation"]
    assert metadata["atmosphere_contract"]["minimum_profile_radius_kpc"] == 1.0
    assert validation["sound_speed_max_relative_difference"] < 5e-4
    assert validation["gravity_median_relative_difference"] < 0.01
    assert validation["gravity_max_relative_difference"] < 0.08
    assert len(metadata["input_provenance"]) == 12

    geometry = read_rows(output / "xray_cavity_age_geometry.csv")
    assert len(geometry) == 74
    assert not any(
        row["case"] == "G-HI" and row["snapshot_index"] == "50"
        for row in geometry
    )
    assert all(float(row["initial_atmosphere_gravity_cm_s2"]) > 0.0 for row in geometry)
    ratios = [float(row["buoyant_to_sound_age_ratio"]) for row in geometry]
    assert max(ratios) - min(ratios) > 0.5
    assert max(ratios) > 2.0
    assert any(abs(value - 2.0) > 0.5 for value in ratios)

    ages = read_rows(output / "age_method_comparison.csv")
    grouped = {}
    for row in ages:
        key = (row["case"], row["snapshot_index"], row["view"])
        grouped.setdefault(key, set()).add(row["age_method"])
    assert len(grouped) == 37
    assert all(methods == set(AGE_METHODS) for methods in grouped.values())
    assert not any(row["G_HI_50_excluded"] == "True" for row in ages)
    assert any(
        row["case"] == "C-LO"
        and row["age_method"] == "shock_kinematic_age"
        and row["combined_age_myr"] == ""
        for row in ages
    )
    assert any(row["age_limit_direction"] == "upper_limit" for row in ages)

    powers = read_rows(output / "cavity_power_method_comparison.csv")
    paired = {}
    for row in powers:
        key = (
            row["case"],
            row["snapshot_index"],
            row["view"],
            row["age_method"],
        )
        paired.setdefault(key, {})[row["cavity_energy_model"]] = row
    assert len(paired) == 37 * len(AGE_METHODS)
    for values in paired.values():
        assert set(values) == {"2.5pV", "4pV"}
        if values["2.5pV"]["inferred_cavity_power_erg_s"]:
            ratio = float(values["4pV"]["inferred_cavity_power_erg_s"]) / float(
                values["2.5pV"]["inferred_cavity_power_erg_s"]
            )
            assert ratio == pytest.approx(1.6)
    assert any(row["power_limit_direction"] == "lower_limit" for row in powers)

    summary = read_rows(output / "age_power_method_summary.csv")
    fully_censored = [
        row
        for row in summary
        if row["case"] in {"G-HI", "G-LO"}
        and row["age_method"].startswith("spectral_age_")
    ]
    assert len(fully_censored) == 8
    assert all(row["exact_age_rows"] == "0" for row in fully_censored)
    assert all(row["exact_power_rows"] == "0" for row in fully_censored)
    assert all(row["median_exact_age_to_true_ratio"] == "" for row in fully_censored)
    assert all(
        row["median_exact_inferred_to_known_power_ratio"] == ""
        for row in fully_censored
    )

    for name in (
        "age_estimator_comparison.png",
        "buoyancy_to_sound_ratio.png",
        "cavity_power_recovery_by_age_method.png",
        "age_power_method_summary.csv",
        "review_metadata.json",
        "local_asset_manifest.sha256",
    ):
        assert (output / name).is_file()
