from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from astropy import units as u


SCRIPT = Path("scripts/science/praise2_method_validation.py")


def load_module():
    spec = importlib.util.spec_from_file_location("praise2_method_validation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cache_fixture(n: int = 3, nt: int = 6):
    return {
        "endpoint_ids": np.array([101, 407, 1503][:n], dtype=np.int64),
        # Starting at zero ensures praise2's uniform resampler can represent
        # the final requested endpoint rather than silently selecting t[-2].
        "times": np.arange(nt, dtype=float),
        "pressure": np.ones((n, nt), dtype=float) * 1.0,
        "density": np.ones((n, nt), dtype=float) * 1.0,
        "tracer": np.ones((n, nt), dtype=float) * 0.8,
        "last_shock_time": np.ones((n, nt), dtype=float) * 1.0,
    }


def test_loss_mapping_is_exact_and_rejects_ambiguous_switches():
    m = load_module()
    assert m.loss_code_mapping() == {0: "lossless", 1: "adiabatic", 4: "full"}
    with pytest.raises(ValueError, match="only PRAiSE2 codes"):
        m.loss_code_mapping([2])
    with pytest.raises(ValueError, match="duplicate"):
        m.loss_code_mapping([0, 0])


def test_singleton_last_shock_is_explicitly_mapped_and_rows_preserved():
    m = load_module()
    cache = cache_fixture()
    contract = m.build_praise2_particle_contract(
        cache,
        rows=[2, 0],
        unit_values=m.Praise2UnitValues(
            time=1 * u.Myr,
            density=1 * u.kg / u.m**3,
            pressure=1 * u.Pa,
        ),
    )
    assert contract["physical_ids"].tolist() == [1503, 101]
    assert contract["selected_rows"].tolist() == [2, 0]
    assert contract["part_data"]["last_shock_time"].shape == (2, 6, 3)
    np.testing.assert_array_equal(contract["part_data"]["last_shock_time"][:, :, 2], 1.0)
    assert np.isnan(contract["part_data"]["last_shock_time"][:, :, :2]).all()
    assert contract["last_shock_semantics"] == "singleton_source_mapped_to_component_2"


def test_pressure_treatment_is_pressure_only_and_forces_internal_smoothing_off():
    m = load_module()
    pressure = np.exp(np.linspace(0.0, 1.0, 6))[None, :]
    raw, raw_meta = m.prepare_pressure_for_praise2(pressure)
    smoothed, smooth_meta = m.prepare_pressure_for_praise2(pressure, pressure_mode="log_savgol")
    np.testing.assert_array_equal(raw, pressure)
    assert np.all(np.isfinite(smoothed)) and np.all(smoothed > 0)
    assert raw_meta["praise2_window_width"] == 0
    assert smooth_meta["praise2_window_width"] == 0
    prefixed = np.vstack([np.r_[np.nan, pressure[0, 1:]], pressure[0]])
    prepared, _ = m.prepare_pressure_for_praise2(prefixed, pressure_mode="log_savgol")
    assert np.isnan(prepared[0, 0])
    assert np.all(np.isfinite(prepared[0, 1:]))
    with pytest.raises(ValueError, match="linear-domain smoothing"):
        m.prepare_pressure_for_praise2(pressure, pressure_mode="linear_savgol")


def test_pinned_high_level_praise2_executes_on_minimal_cache_contract():
    m = load_module()
    cache = cache_fixture(n=2)
    contract = m.build_praise2_particle_contract(
        cache,
        unit_values=m.Praise2UnitValues(
            time=1 * u.Myr,
            density=1e-21 * u.kg / u.m**3,
            pressure=1e-9 * u.Pa,
        ),
    )
    source = Path("/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py")
    spec = importlib.util.spec_from_file_location("praise2_pinned", source)
    assert spec and spec.loader
    praise2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(praise2)
    kwargs = m.build_praise2_call_kwargs(contract, particle_spacing=0.01 * u.Myr)
    result = praise2.praise(**kwargs)
    audited = m.extract_praise2_outputs(result, expected_rows=2, expected_frequencies=2, expected_part_output=5)
    assert set(audited["branches"]) == {"lossless", "adiabatic", "full"}
    assert audited["raw_nonfinites_preserved"] is True
    assert all(branch["nonfinite_count"] == 0 for branch in audited["branches"].values())
    with pytest.raises(m.OutputAuditError, match="expected endpoint"):
        m.extract_praise2_outputs(result, expected_rows=2, expected_frequencies=2, expected_part_output=4)


def test_output_comparison_preserves_nonfinite_classes_and_state_is_fail_closed():
    m = load_module()
    left = np.array([1.0, np.nan, np.inf, -np.inf])
    right = np.array([1.0 + 1e-12, np.nan, np.inf, -np.inf])
    comparison = m.compare_numeric_arrays(left, right)
    assert comparison["equal"] is True
    assert m.state_trajectory_audit()["status"] == "not_observable"


def test_deterministic_repeat_handles_nested_array_audits():
    m = load_module()
    counter = {"n": 0}

    def run():
        counter["n"] += 1
        return np.array([1.0, np.nan, np.inf])

    def audit(value):
        return {"values": value, "nonfinite_classes": np.array([["finite", "nan"]], dtype="U8")}

    result = m.deterministic_repeat(run, audit, repeats=2)
    assert result["deterministic"] is True
    assert counter["n"] == 2


def test_provenance_resolver_has_pinned_identity():
    m = load_module()
    source = Path("/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py")
    provenance = m.resolve_praise2_provenance(source)
    assert provenance["commit"] == m.EXPECTED_PRAISE2_COMMIT
    assert provenance["source_sha256"] == m.EXPECTED_PRAISE2_SOURCE_SHA256
    assert provenance["callable"] == "plutokore.radio.praise2.praise"


def test_provenance_accepts_non_git_staged_source_with_exact_commit_proof(tmp_path):
    m = load_module()
    source = tmp_path / "praise2.py"
    source.write_text("def praise(*args, **kwargs):\n    return {}\n")
    proof = tmp_path / "plutokore_commit.txt"
    proof.write_text(m.EXPECTED_PRAISE2_COMMIT + "\n")
    provenance = m.resolve_praise2_provenance(
        source,
        expected_commit=m.EXPECTED_PRAISE2_COMMIT,
        expected_source_sha256=m._sha256(source),
        commit_proof_path=proof,
    )
    assert provenance["commit_verification"] == "staged_commit_proof"
