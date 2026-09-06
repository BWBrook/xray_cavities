"""The proof fixtures here are synthetic assertions, not scientific source-dtype evidence."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

CENSUS = Path("docs/science/assets/four_case_fluid_snapshot_census_2026-08-25/review_products")
CONTEXT = Path("docs/science/assets/four_case_scientific_synthesis_2026-08-26/case_age_physics.csv")
OBSERVER = Path("docs/science/assets/four_case_selected_age_dual_space_energetics_2026-08-31/audit_products")


def load_module():
    script = Path("scripts/science/build_binary_native_refresh.py")
    sys.path.insert(0, str(script.parent.resolve()))
    try:
        spec = importlib.util.spec_from_file_location("build_binary_native_refresh", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def synthetic_proof(module, path):
    covered = []
    for case in module.CASES:
        for row in module.read_rows(CENSUS / case / "snapshot_manifest.csv"):
            key = (row["case"], int(row["snapshot_index"]))
            if key in module.EXPECTED:
                covered.append({"case": key[0], "snapshot_index": key[1], "input_h5": row["input_h5"],
                                "timestep": row["timestep"], "tracer_dtype": "<f4",
                                "tracer_shape": [int(v) for v in row["shape_nz_ny_nx"].split("x")]})
    proof = {"primary_threshold": 0.001, "strict_equivalent": True, "comparison_dtype": "float64",
             "proof_method": "float32_threshold_not_representable_after_float64_promotion",
             "covered_case_ages": covered}
    path.write_text(json.dumps(proof))
    return proof


@pytest.mark.parametrize("mutation", ["dtype", "source", "threshold", "coverage"])
def test_rejects_unsupported_or_unbound_strict_proof(tmp_path, mutation):
    module = load_module()
    path = tmp_path / "synthetic_proof.json"
    proof = synthetic_proof(module, path)
    if mutation == "dtype":
        proof["covered_case_ages"][0]["tracer_dtype"] = "<f8"
    elif mutation == "source":
        proof["covered_case_ages"][0]["input_h5"] = "/unrelated/file.h5"
    elif mutation == "threshold":
        proof["primary_threshold"] = 0.005
    else:
        proof["covered_case_ages"].pop()
    path.write_text(json.dumps(proof))
    with pytest.raises(module.ProductError):
        module.validate_equivalence(path, CENSUS)


def test_rejects_noncomplementary_partition(tmp_path):
    module = load_module()
    shutil.copytree(CENSUS, tmp_path / "census")
    path = tmp_path / "census/C-HI/energy_partition_timeseries.csv"
    rows = module.read_rows(path)
    changed = next(r for r in rows if r["snapshot_index"] == "10" and r["side"] == "bipolar_total"
                   and r["partition_method"] == "binary_threshold_1e-3")
    changed["gas_total_delta_erg"] = str(float(changed["gas_total_delta_erg"]) + 1e59)
    module.write_rows(path, rows)
    with pytest.raises(module.ProductError, match="does not close"):
        module.selected_inputs(tmp_path / "census", CONTEXT)


def test_refresh_changes_only_native_denominators_and_preserves_censoring(tmp_path):
    module = load_module()
    proof = tmp_path / "synthetic_proof.json"
    synthetic_proof(module, proof)
    output = tmp_path / "refresh"
    metadata = module.build_refresh(census_root=CENSUS, reference_native_case_age_path=CONTEXT,
                                    strict_equivalence_proof=proof, observer_root=OBSERVER, output_root=output)
    assert metadata["sensitivity_native_row_count"] == 76
    assert metadata["observer_recovery_row_count"] == 228
    for filename in ("xray_topology_summary.csv", "xray_pressure_profiles.csv", "xray_cavity_enthalpy_selected_age.csv"):
        assert module.read_rows(output / "primary_join" / filename) == module.read_rows(OBSERVER / filename)
    matched = module.read_rows(output / "primary_join/matched_native_xray_energetics.csv")
    assert len(matched) == 464
    censored = [r for r in matched if r["matched_status"] == "unresolved_observer_topology"]
    assert len(censored) == 20
    assert all(r["ratio_to_native_lobe_enthalpy"] == "" for r in censored)
    valid = [r for r in matched if r not in censored]
    assert max(float(r["factorization_relative_error"]) for r in valid) < 1e-10
    native = module.read_rows(output / "native_partition_sensitivity.csv")
    primary = next(r for r in native if r["case"] == "C-HI" and r["snapshot_index"] == "10"
                   and r["role"] == "primary")
    assert float(primary["lobe_volume_kpc3"]) == pytest.approx(40186.27008723593)
    assert float(primary["lobe_mass_g"]) == pytest.approx(2.9854909884011534e42)
    assert float(primary["lobe_enthalpy_2p5pv_erg"]) == pytest.approx(2.0949680261126814e59 * (5/3 - 1) * 2.5)
    assert float(primary["lobe_volume_kpc3_relative_change_from_fractional"]) > 4.0
    assert abs(float(primary["retained_energy_erg_relative_change_from_fractional"])) < 1e-10
    fractional_recoveries = [r for r in module.read_rows(output / "observer_recovery_sensitivity.csv")
                            if r["source_partition_method"] == "fractional"]
    original = module.read_rows(OBSERVER / "matched_native_xray_energetics.csv")
    for row in fractional_recoveries:
        if row["matched_status"] == "unresolved_observer_topology":
            continue
        old = next(r for r in original if all(r[k] == row[k] for k in ("case", "snapshot_index", "view"))
                   and r["energy_model"] == "2.5pV" and r["pressure_method"] == "ellipsoid_volume_average"
                   and r["volume_depth_assumption"] == "geometric_depth")
        assert float(row["ratio_to_native_lobe_enthalpy"]) == pytest.approx(float(old["ratio_to_native_lobe_enthalpy"]), rel=1e-12)
