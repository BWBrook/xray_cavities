import csv

import pytest

from scripts.science.build_four_case_boundary_spectral_field_review import run


def read_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_boundary_and_spectral_field_review(tmp_path):
    output = tmp_path / "review"
    metadata = run(output)

    assert metadata["row_counts"] == {
        "boundary_audit": 20,
        "annual_axial_boundary_audit": 204,
        "spectral_break_frequencies": 57,
        "spectral_age_field_comparison": 114,
    }
    assert metadata["boundary_contaminated_case_ages"] == [["G-HI", 50]]
    assert metadata["maximum_relative_difference_from_accepted_break_surface"] < 5e-7
    assert metadata["first_annual_axial_boundary_contact_snapshot"] == {
        "C-HI": None,
        "C-LO": None,
        "G-HI": 48,
        "G-LO": None,
    }
    assert metadata["selected_science_ages_by_case"]["G-HI"] == [10, 20, 30, 40]

    boundary = read_rows(output / "boundary_audit.csv")
    contaminated = [row for row in boundary if row["boundary_contact"] == "True"]
    assert [(row["case"], int(row["snapshot_index"])) for row in contaminated] == [
        ("G-HI", 50)
    ]
    assert float(contaminated[0]["negative_z_edge_pressure_ratio"]) > 300.0
    assert float(contaminated[0]["positive_z_edge_pressure_ratio"]) > 180.0

    annual = read_rows(output / "annual_axial_boundary_audit.csv")
    annual_contaminated = [
        row for row in annual if row["axial_boundary_contact"] == "True"
    ]
    assert [(row["case"], int(row["snapshot_index"])) for row in annual_contaminated] == [
        ("G-HI", 48),
        ("G-HI", 49),
        ("G-HI", 50),
    ]

    ages = read_rows(output / "spectral_age_field_comparison.csv")
    g_hi_mean = [
        row
        for row in ages
        if row["case"] == "G-HI"
        and row["view"] == "0deg"
        and row["field_treatment"] == "tracer_lobe_mean_pressure"
    ]
    mean_fields = [float(row["magnetic_field_ug"]) for row in g_hi_mean]
    assert mean_fields == sorted(mean_fields, reverse=True)
    assert mean_fields[-1] == pytest.approx(2.839, rel=2e-4)
    assert not any(
        row["case"] == "G-HI" and row["snapshot_index"] == "50" for row in ages
    )

    paired_breaks = {}
    for row in ages:
        key = (row["case"], row["snapshot_index"], row["view"])
        paired_breaks.setdefault(key, set()).add(float(row["fitted_break_ghz"]))
    assert all(len(values) == 1 for values in paired_breaks.values())

    for name in (
        "magnetic_field_comparison.png",
        "spectral_age_comparison.png",
        "spectral_break_frequency_evolution.png",
        "annual_axial_boundary_pressure.png",
        "review_metadata.json",
        "local_asset_manifest.sha256",
    ):
        assert (output / name).is_file()
