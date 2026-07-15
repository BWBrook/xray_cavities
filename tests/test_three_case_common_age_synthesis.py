from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/science/build_three_case_common_age_synthesis.py"


def load_module():
    spec = importlib.util.spec_from_file_location("three_case_common_age_synthesis", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_authoritative_power_contract_matches_frozen_three_case_design() -> None:
    module = load_module()

    assert module.AUTHORITATIVE_JET_POWER_ERG_S == {
        "C-HI": 1.0e45,
        "C-LO": 1.0e43,
        "G-LO": 1.0e43,
    }


def test_build_synthesis_merges_endpoint_and_repairs_only_derived_c_hi_power_surface(
    tmp_path: Path,
) -> None:
    module = load_module()
    module.build_synthesis(tmp_path)

    provenance = read_rows(tmp_path / "case_age_provenance.csv")
    truth = read_rows(tmp_path / "truth_energy_evolution.csv")
    observer = read_rows(tmp_path / "observer_recovery_evolution.csv")
    hybrid = read_rows(tmp_path / "hybrid_cavity_evolution.csv")
    sensitivity = read_rows(tmp_path / "method_sensitivity_summary.csv")
    corrections = read_rows(tmp_path / "correction_register.csv")
    contrasts = read_rows(tmp_path / "descriptive_contrasts.csv")
    validation = read_rows(tmp_path / "validation_report.csv")
    metadata = json.loads((tmp_path / "three_case_common_age_synthesis_metadata.json").read_text())

    assert len(provenance) == 15
    assert len(truth) == 15
    assert len(observer) == 45
    assert len(sensitivity) == 45
    assert len(hybrid) == 963
    assert len(contrasts) == 20
    assert len(corrections) == 1
    assert all(row["status"] == "passed" for row in validation)
    assert metadata["status"] == "complete_local_synthesis"
    assert metadata["decision_label"] == "THREE_CASE_COMMON_AGE_SYNTHESIS_COMPLETE"

    correction = corrections[0]
    assert correction["case"] == "C-HI"
    assert correction["reported_one_sided_power_erg_s"] == "1e+44"
    assert correction["authoritative_one_sided_power_erg_s"] == "1e+45"
    assert correction["source_manifest_affected_nominal_ages_myr"] == "10;20;30;40;50"
    assert correction["derived_outputs_corrected_nominal_ages_myr"] == "10;20;30;40"
    assert correction["correction_scope"] == "derived_level1_and_dependent_ratios_only"

    c_hi_truth = sorted(
        (row for row in truth if row["case"] == "C-HI"),
        key=lambda row: int(row["nominal_age_myr"]),
    )
    assert [int(row["nominal_age_myr"]) for row in c_hi_truth] == [10, 20, 30, 40, 50]
    assert math.isclose(float(c_hi_truth[0]["injected_energy_bipolar_elapsed_erg"]), 6.311450322900221e59)
    assert math.isclose(float(c_hi_truth[-1]["injected_energy_bipolar_elapsed_erg"]), 3.15576e60)
    assert all(row["power_binding_status"] == "corrected_from_authoritative_contract" for row in c_hi_truth[:4])
    assert c_hi_truth[-1]["power_binding_status"] == "accepted_goal040_authoritative"

    endpoint_rows = [row for row in observer if row["nominal_age_myr"] == "50"]
    assert len(endpoint_rows) == 9
    assert {row["source_goal"] for row in endpoint_rows} == {"Goal 040"}
    assert all(row["quantitative_volume_valid"] == "true" for row in endpoint_rows)

    invalid = {
        (row["case"], row["nominal_age_myr"], row["view"])
        for row in observer
        if row["quantitative_volume_valid"] == "false"
    }
    assert ("C-LO", "10", "0deg") in invalid
    assert ("C-LO", "10", "90deg") in invalid
    assert ("G-LO", "10", "0deg") in invalid
    assert ("G-LO", "10", "90deg") in invalid

    for name in (
        "energy_response_evolution.png",
        "observer_hybrid_evolution.png",
        "local_asset_manifest.sha256",
    ):
        assert (tmp_path / name).stat().st_size > 0


def test_goal041_case_builder_rejects_non_authoritative_case_power() -> None:
    module = load_module()

    module.validate_authoritative_power("C-HI", 1.0e45)
    try:
        module.validate_authoritative_power("C-HI", 1.0e44)
    except ValueError as exc:
        assert "authoritative jet power" in str(exc)
    else:
        raise AssertionError("non-authoritative C-HI power was accepted")
