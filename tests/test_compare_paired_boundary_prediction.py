import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "scripts/science"
sys.path.insert(0, str(SCIENCE))
SMOKES = ROOT / "docs/science/assets/paired_nojet_boundary_experiment_2026-11-01/original_smokes/smoke"
spec = importlib.util.spec_from_file_location("compare", SCIENCE / "compare_paired_boundary_prediction.py")
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def complete_rows(case="cluster_002003"):
    pred = compare.PREDICTION[case]
    rows = []
    for time_myr in (5.0, 10.0, 20.0, 30.0, 40.0, 50.0):
        scale = (time_myr / 50.0) ** 2
        rows.append({
            "time_myr": time_myr,
            "contrast_mass_g": pred["mass_g"] * scale,
            "mass_over_t2_prediction": 1.0,
            "hp_over_t2_prediction": 1.0,
            "transport_explains_mass": 1.0,
            "transport_explains_h": 1.0,
            "transport_explains_hp": 1.0,
            "h_with_gravity_repair_explains": 1.0,
            "mass_transport_discrepancy_fraction": 0.0,
            "hp_transport_discrepancy_fraction": 0.0,
            "repair_residual_budget_fraction": 0.01,
        })
    return rows


def test_smoke_contrasts_reproduce_recorded_values_signs_and_source_accounting(tmp_path):
    cluster_rows, cluster_mode = compare.contrasts(SMOKES, "cluster_002003")
    for boundary in ("outflow", "reflective"):
        staged = tmp_path / f"group_002031_{boundary}"
        staged.mkdir()
        source = SMOKES / f"group_002031_{boundary}"
        shutil.copyfile(source / "paired_nojet_budget.csv", staged / "paired_nojet_budget.csv")
        shutil.copyfile(source / "output_receipt.json", staged / "output_receipt.json")
        receipt = source / "budget_receipt.json"
        if not receipt.exists():
            receipt = (ROOT / "docs/science/assets/paired_nojet_boundary_experiment_2026-11-01/"
                       "revalidation_capture/paired_nojet_analysis_overlay_2026-11-01_r2/"
                       "revalidated/budgets/group_002031_reflective.json")
        shutil.copyfile(receipt, staged / "budget_receipt.json")
    group_rows, group_mode = compare.contrasts(tmp_path, "group_002031")
    cluster, group = cluster_rows[-1], group_rows[-1]
    assert (cluster_mode, group_mode) == ("smoke", "smoke")
    assert cluster["contrast_mass_g"] == pytest.approx(1.628e39, rel=1e-3)
    assert cluster["contrast_h_erg"] == pytest.approx(1.137e55, rel=1e-3)
    assert group["contrast_h_erg"] == pytest.approx(1.348e53, rel=1e-3)
    for row in (cluster, group):
        assert row["transport_explains_mass"] == pytest.approx(1.0, abs=1e-4)
        assert row["transport_explains_h"] == pytest.approx(0.9998, abs=2e-4)
        assert row["transport_explains_hp"] == pytest.approx(1.0004, abs=2e-4)
        assert row["h_with_gravity_repair_explains"] == pytest.approx(1.0, abs=3e-8)
        assert row["inward_face_mass_contrast_g"] > 0
        assert row["inward_face_h_contrast_erg"] > 0
        assert row["inward_face_p_contrast_erg"] > 0
        assert row["paired_repair_gross_combined_erg"] >= abs(row["paired_repair_net_contrast_erg"])
        assert 1.25 < row["mass_over_t2_prediction"] < 1.4


def test_incomplete_precedes_all_scientific_or_transport_verdicts():
    rows = complete_rows()
    rows[-1].update({
        "time_myr": 0.25,
        "transport_explains_mass": 0.5,
        "transport_explains_h": 0.5,
        "mass_transport_discrepancy_fraction": 0.5,
        "hp_transport_discrepancy_fraction": 0.5,
        "repair_residual_budget_fraction": 0.5,
    })
    result = compare.verdict("cluster_002003", rows, "smoke")
    assert result["verdict"] == "incomplete"
    assert result["physical_refutations"] == []
    assert result["accounting_indeterminacies"] == []


def test_nonpositive_or_insufficient_growth_is_indeterminate_and_json_strict():
    rows = complete_rows()
    rows[2]["contrast_mass_g"] = 0.0
    result = compare.verdict("cluster_002003", rows, "full")
    assert result["verdict"] == "scientifically_indeterminate"
    assert result["growth_exponent_t_ge_5myr"] is None
    assert "nonpositive" in result["growth_information_issue"]
    json.dumps(result, allow_nan=False)
    one = complete_rows()[-1:]
    result = compare.verdict("cluster_002003", one, "full")
    assert result["verdict"] == "scientifically_indeterminate"
    assert "fewer than two" in result["growth_information_issue"]


def test_validated_full_endpoint_uses_validator_scale_tolerance():
    rows = complete_rows()
    rows[-1]["time_myr"] = 50.0 - 5e-7
    assert compare.verdict("cluster_002003", rows, "full")["complete_to_50_myr"]


def test_amended_transport_is_two_sided_and_h_face_only_is_diagnostic():
    rows = complete_rows()
    rows[-1]["transport_explains_h"] = 0.5
    assert compare.verdict("cluster_002003", rows, "full")["verdict"] == "supported"
    assert compare.verdict("cluster_002003", rows, "full")["original_one_sided_transport_flags"]
    rows[-1]["hp_transport_discrepancy_fraction"] = 0.1000001
    result = compare.verdict("cluster_002003", rows, "full")
    assert result["verdict"] == "refuted"
    assert any("hp face-transport" in reason for reason in result["physical_refutations"])


def test_large_repair_or_residual_budget_is_accounting_indeterminate_not_refuted():
    rows = complete_rows()
    rows[-1]["repair_residual_budget_fraction"] = 0.1000001
    rows[-1]["hp_transport_discrepancy_fraction"] = 0.5
    result = compare.verdict("cluster_002003", rows, "full")
    assert result["verdict"] == "accounting_indeterminate"
    assert result["physical_refutations"] == []


def test_receipt_binding_rejects_changed_ledger_bytes(tmp_path):
    source = SMOKES / "cluster_002003_outflow"
    run = tmp_path / "run"
    run.mkdir()
    for name in ("paired_nojet_budget.csv", "budget_receipt.json", "output_receipt.json"):
        shutil.copyfile(source / name, run / name)
    with (run / "paired_nojet_budget.csv").open("a") as handle:
        handle.write("\n")
    with pytest.raises(compare.EvidenceError, match="bytes do not match"):
        compare.load_bound_run(run, "cluster_002003", "outflow")


def test_revalidation_rejects_bad_face_coverage_even_if_receipt_hash_is_rebound(tmp_path):
    source = SMOKES / "cluster_002003_outflow"
    run = tmp_path / "run"
    run.mkdir()
    ledger = run / "paired_nojet_budget.csv"
    receipt_path = run / "budget_receipt.json"
    shutil.copyfile(source / "paired_nojet_budget.csv", ledger)
    shutil.copyfile(source / "budget_receipt.json", receipt_path)
    shutil.copyfile(source / "output_receipt.json", run / "output_receipt.json")
    lines = ledger.read_text().splitlines()
    ledger.write_text("\n".join([lines[0], lines[1], lines[1], *lines[2:]]) + "\n")
    receipt = json.loads(receipt_path.read_text())
    identity = next(entry for entry in receipt["input_files"] if Path(entry["path"]).name == ledger.name)
    identity["size_bytes"] = ledger.stat().st_size
    identity["sha256"] = hashlib.sha256(ledger.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(compare.EvidenceError, match="six faces"):
        compare.load_bound_run(run, "cluster_002003", "outflow")


def test_bound_output_receipts_must_establish_pair_identity():
    runs = {
        boundary: compare.load_bound_run(
            SMOKES / f"cluster_002003_{boundary}", "cluster_002003", boundary)
        for boundary in ("outflow", "reflective")
    }
    altered = copy.deepcopy(runs)
    altered["outflow"]["output_receipt"]["initial_field_hashes"]["rho"] = "wrong"
    with pytest.raises(compare.EvidenceError, match="initial_field_hashes"):
        compare._validate_pair_identity("cluster_002003", altered)


def test_physical_age_alignment_interpolates_brackets_and_forbids_extrapolation():
    states = [
        {"state_step": 0, "time_myr": 0.0, "in_mass": 0.0, "mass": 100.0},
        {"state_step": 7, "time_myr": 8.0, "in_mass": 16.0, "mass": 116.0},
        {"state_step": 11, "time_myr": 12.0, "in_mass": 24.0, "mass": 124.0},
    ]
    values, metadata = compare._interpolate_state(states, 10.0)
    assert values == {"time_myr": 10.0, "in_mass": 20.0, "mass": 120.0}
    assert metadata == {
        "lower_state_step": 7,
        "upper_state_step": 11,
        "lower_time_myr": 8.0,
        "upper_time_myr": 12.0,
        "interpolation_fraction": 0.5,
    }
    with pytest.raises(compare.EvidenceError, match="extrapolation is forbidden"):
        compare._interpolate_state(states, 20.0)


def test_output_directory_must_be_new(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        compare.write_outputs(output, complete_rows(), [])
