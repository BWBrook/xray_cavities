from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/science/build_four_case_scientific_synthesis.py"


def load_module():
    spec = importlib.util.spec_from_file_location("four_case_scientific_synthesis", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert len(reader.fieldnames) == len(set(reader.fieldnames))
        return list(reader)


@pytest.fixture(scope="module")
def synthesis(tmp_path_factory: pytest.TempPathFactory) -> tuple[object, Path]:
    module = load_module()
    output = tmp_path_factory.mktemp("four_case_synthesis") / "product"
    module.build_synthesis(output)
    return module, output


def test_synthesis_has_exact_joined_surfaces_and_validity_gates(
    synthesis: tuple[object, Path],
) -> None:
    _module, output = synthesis
    metadata = json.loads((output / "four_case_scientific_synthesis_metadata.json").read_text())
    physics = read_rows(output / "case_age_physics.csv")
    cavity = read_rows(output / "cavity_energy_recovery.csv")

    assert metadata["status"] == "complete_corrected_local_scientific_synthesis"
    assert metadata["decision_label"] == "FOUR_CASE_SYNTHESIS_CORRECTED_DUAL_SPACE_AUDIT_NEXT"
    assert metadata["row_counts"] == {
        "age_method_comparison.csv": 259,
        "age_power_method_summary.csv": 56,
        "case_age_physics.csv": 19,
        "cavity_energy_recovery.csv": 171,
        "cavity_power_method_comparison.csv": 518,
        "factorial_effects.csv": 150,
        "radio_power_inference.csv": 228,
        "radio_power_recovery_summary.csv": 16,
        "scientific_decision_summary.csv": 3,
        "shock_cavity_test_summary.csv": 12,
        "spectral_fits.csv": 57,
        "xray_cavity_age_geometry.csv": 74,
    }
    assert {(row["case"], int(row["snapshot_index"])) for row in physics} == {
        (case, age)
        for case in ("C-HI", "C-LO", "G-HI", "G-LO")
        for age in (10, 20, 30, 40, 50)
        if not (case == "G-HI" and age == 50)
    }

    endpoints = {row["case"]: row for row in physics if row["snapshot_index"] == "50"}
    assert set(endpoints) == {"C-HI", "C-LO", "G-LO"}
    assert all(endpoints[case]["shock_kinematics_valid"] == "true" for case in endpoints)
    assert endpoints["C-LO"]["ambient_energy_interpretation"] == "whole_domain_background_dominated_inside100_upper_bound_only"
    assert float(endpoints["C-LO"]["c_lo_far_field_fraction_of_injected"]) > 20.0

    assert len(cavity) == (4 * 5 - 1) * 3 * 3
    assert sum(row["quantitative_energy_valid"] == "True" for row in cavity) == 37 * 3
    invalid = [row for row in cavity if row["quantitative_energy_valid"] == "False"]
    assert invalid
    assert all(row["cavity_to_injected_ratio"] == "" for row in invalid)
    assert not [row for row in cavity if row["case"] == "G-HI" and row["snapshot_index"] == "50"]

    for name in (
        "radio_power_inference.csv",
        "spectral_fits.csv",
        "xray_cavity_age_geometry.csv",
        "age_method_comparison.csv",
        "cavity_power_method_comparison.csv",
    ):
        assert not [
            row
            for row in read_rows(output / name)
            if row["case"] == "G-HI" and row["snapshot_index"] == "50"
        ], name


def test_primary_science_decisions_distinguish_pattern_from_identification(
    synthesis: tuple[object, Path],
) -> None:
    _module, output = synthesis
    shock = read_rows(output / "shock_cavity_test_summary.csv")
    decisions = {row["test_id"]: row for row in read_rows(output / "scientific_decision_summary.csv")}

    raw = [
        row
        for row in shock
        if row["analysis_scope"] == "within_view_pooled_cases"
        and row["response"] == "cavity_to_injected_ratio"
    ]
    assert len(raw) == 3
    assert all(float(row["spearman_rho"]) < -0.85 for row in raw)
    adjusted = next(
        row
        for row in shock
        if row["analysis_scope"] == "case_and_view_fixed_effect_descriptive"
        and row["response"] == "cavity_to_injected_ratio"
    )
    assert float(adjusted["mach_slope_dex_per_unit"]) < 0.0
    assert float(adjusted["incremental_mach_r2"]) < 0.01
    leave_one_out = [
        float(row["mach_slope_dex_per_unit"])
        for row in shock
        if row["analysis_scope"] == "leave_one_case_out_fixed_effect_sensitivity"
    ]
    assert min(leave_one_out) < 0.0 < max(leave_one_out)
    assert all(row["inference_scope"].endswith("no_p_value") or "no_replicate" in row["inference_scope"] for row in shock)

    assert decisions["T1"]["decision"] == "strong_pooled_negative_pattern_not_case_robust"
    assert decisions["T2"]["decision"] == "age_method_bias_modulates_not_explains_cavity_energy_deficit"
    assert decisions["T3"]["decision"] == "radio_scalings_power_and_environment_dependent"


def test_radio_power_results_and_local_manifest_are_reproducible(
    synthesis: tuple[object, Path],
) -> None:
    _module, output = synthesis
    summary = read_rows(output / "radio_power_recovery_summary.csv")
    spectral = read_rows(output / "spectral_fits.csv")
    age_summary = read_rows(output / "age_power_method_summary.csv")

    radio150 = {
        row["case"]: float(row["median_inferred_to_known"])
        for row in summary
        if row["method"] == "kokotanekov_2017_150mhz_approx"
        and row["comparator"] == "full_loss"
    }
    assert 0.8 < radio150["C-HI"] < 1.2
    assert radio150["C-LO"] > 7.0
    assert radio150["G-HI"] < 0.6
    assert radio150["G-LO"] > 4.0
    assert sum(row["spectral_age_limit_direction"] != "none" for row in spectral) == 37

    assert {row["age_method"] for row in age_summary} == {
        "true_source_age",
        "sound_crossing_age",
        "buoyant_rise_age",
        "refill_age",
        "shock_kinematic_age",
        "spectral_age_mean_pressure",
        "spectral_age_emissivity_weighted",
    }
    primary_spectral = [
        row
        for row in age_summary
        if row["cavity_energy_model"] == "2.5pV"
        and row["age_method"] == "spectral_age_mean_pressure"
    ]
    assert sum(int(row["power_lower_limit_rows"]) for row in primary_spectral) == 20
    assert all(
        row["median_exact_inferred_to_known_power_ratio"] == ""
        and row["median_lower_limit_inferred_to_known_power_ratio"] != ""
        for row in primary_spectral
        if row["case"] in {"G-HI", "G-LO"}
    )

    manifest = output / "local_asset_manifest.sha256"
    for line in manifest.read_text().splitlines():
        expected, name = line.split(None, 1)
        path = output / name.strip()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    assert (output / "four_case_scientific_synthesis.png").stat().st_size > 100_000
