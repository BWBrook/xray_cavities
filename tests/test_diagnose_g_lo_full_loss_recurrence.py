from __future__ import annotations

from pathlib import Path
import sys
import csv
import json

import h5py

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_full_loss_recurrence as diagnostic


def test_log_exprel_has_exact_zero_limit_and_extreme_finite_branches() -> None:
    values = np.array([-1000.0, -1.0e-12, 0.0, 1.0e-12, 1000.0])
    result = diagnostic.log_exprel(values)
    assert np.all(np.isfinite(result))
    assert result[2] == 0.0
    assert result[1] == pytest.approx(-5.0e-13, abs=1.0e-20)
    assert result[3] == pytest.approx(5.0e-13, abs=1.0e-20)
    assert result[0] == pytest.approx(-np.log(1000.0))
    assert result[4] == pytest.approx(1000.0 - np.log(1000.0))


def test_constant_pressure_scaled_loss_matches_closed_form() -> None:
    t0, t1 = 2.0e15, 2.1e15
    pressure = 3.0e-12
    gamma_c = 5.0 / 3.0
    result = diagnostic.stable_scaled_loss(
        t0=t0,
        t1=t1,
        p0=pressure,
        p1=pressure,
        gamma_c=gamma_c,
        eta=0.03,
        z=0.05,
    )
    ub = diagnostic.magnetic_energy_density(0.03, pressure, gamma_c)
    uc = diagnostic.cmb_energy_density(0.05)
    expected = diagnostic.C1 * (t1 - t0) * (ub + uc)
    assert np.exp(result["log_lambda"]) == pytest.approx(expected, rel=2.0e-14)


@pytest.mark.parametrize(
    ("gamma_c", "ap", "limit_name"),
    [
        (5.0 / 3.0, -5.0 / 6.0, "a3"),
        (5.0 / 3.0, -5.0, "a4"),
    ],
)
def test_removable_a3_a4_limits_match_80_digit_reference(
    gamma_c: float,
    ap: float,
    limit_name: str,
) -> None:
    t0, t1 = 1.0e15, 1.1e15
    p0 = 2.0e-12
    p1 = p0 * (t1 / t0) ** ap
    stable = diagnostic.stable_scaled_loss(
        t0=t0, t1=t1, p0=p0, p1=p1, gamma_c=gamma_c, eta=0.03, z=0.05
    )
    reference = diagnostic.high_precision_scaled_loss(
        t0=t0, t1=t1, p0=p0, p1=p1, gamma_c=gamma_c, eta=0.03, z=0.05
    )
    assert stable[f"{limit_name}_argument"] == pytest.approx(0.0, abs=2.0e-15)
    assert np.exp(stable["log_lambda"]) == pytest.approx(
        float(reference["lambda"]), rel=2.0e-12
    )


def test_extreme_raw_a2_can_overflow_while_scaled_loss_is_finite() -> None:
    result = diagnostic.stable_scaled_loss(
        t0=1.0e15,
        t1=1.01e15,
        p0=1.0e-12,
        p1=1.0e-12 * (1.01 ** 36000.0),
        gamma_c=5.0 / 3.0,
        eta=0.03,
        z=0.05,
    )
    assert np.isfinite(result["log_lambda"])
    assert result["log_raw_a2"] > np.log(np.finfo(float).max)
    assert np.exp(result["log_lambda"]) > 0.0


def test_finite_interval_update_matches_independent_reference() -> None:
    kwargs = dict(
        gamma_later=8.0e3,
        t0=1.0e15,
        t1=1.02e15,
        p0=2.0e-12,
        p1=1.9e-12,
        gamma_c=5.0 / 3.0,
        eta=0.03,
        z=0.05,
    )
    stable = diagnostic.stable_full_loss_interval(**kwargs)
    reference = diagnostic.high_precision_full_loss_interval(**kwargs)
    assert stable["classification"] == reference["classification"] == "finite"
    assert stable["gamma_earlier"] == pytest.approx(
        float(reference["gamma_earlier"]), rel=1.0e-11
    )


def test_gamma_inf_cutoff_is_explicit_and_never_reconstructed() -> None:
    kwargs = dict(
        gamma_later=8.0e3,
        t0=1.0e15,
        t1=1.02e15,
        p0=2.0e-12,
        p1=1.9e-12,
        gamma_c=5.0 / 3.0,
        eta=0.03,
        z=0.05,
        gamma_inf=1.0e3,
    )
    result = diagnostic.stable_full_loss_interval(**kwargs)
    assert result["classification"] == diagnostic.STATE_GAMMA_INF_CUTOFF
    assert np.isnan(result["gamma_earlier"])


def test_subrelativistic_state_is_rejected_by_emissivity_policy() -> None:
    result = diagnostic.stable_full_loss_interval(
        gamma_later=0.1,
        t0=1.0e15,
        t1=1.02e15,
        p0=2.0e-12,
        p1=1.9e-12,
        gamma_c=5.0 / 3.0,
        eta=0.03,
        z=0.05,
    )
    assert result["classification"] == diagnostic.STATE_SUBRELATIVISTIC
    assert 0.0 < result["gamma_earlier"] < 1.0
    with pytest.raises(
        diagnostic.FullLossDiagnosticError,
        match="subrelativistic",
    ):
        diagnostic.reconstruct_full_loss_injection_emissivity(
            endpoint_gamma=np.array([0.1]),
            injection_gamma=np.array([result["gamma_earlier"]]),
            gamma_c=np.full(2, 5.0 / 3.0),
            pressure=np.full(2, 2.0e-12),
            shock_index=0,
            tracer_endpoint=0.05,
            classification=diagnostic.STATE_SUBRELATIVISTIC,
            frequencies=(0.15,),
        )


def test_runtime_analytic_self_checks_execute_and_pass() -> None:
    result = diagnostic.run_analytic_self_checks()
    assert result["passed"] is True
    assert {row["check"] for row in result["checks"]} == {
        "constant_pressure_closed_form",
        "a3_zero_limit",
        "a4_zero_limit",
        "overflow_scaled_loss",
    }
    assert all(row["passed"] for row in result["checks"])


def test_pole_is_explicit_and_never_retains_previous_gamma() -> None:
    base = dict(
        t0=1.0,
        t1=2.0,
        p0=1.0,
        p1=1.0,
        gamma_c=5.0 / 3.0,
        eta=0.03,
        z=0.05,
    )
    loss = diagnostic.stable_scaled_loss(**base)
    gamma_at_pole = 1.0 / np.exp(loss["log_lambda"])
    result = diagnostic.stable_full_loss_interval(
        gamma_later=gamma_at_pole * (1.0 + 1.0e-12),
        **base,
    )
    assert result["classification"] == "physical_cutoff"
    assert np.isnan(result["gamma_earlier"])
    assert result["gamma_earlier"] != gamma_at_pole


def test_trajectory_propagates_cutoff_without_silent_fallback() -> None:
    times = np.array([1.0, 2.0, 3.0])
    pressure = np.ones((1, 3))
    gamma_c = np.full((1, 3), 5.0 / 3.0)
    interval = diagnostic.stable_scaled_loss(
        t0=2.0, t1=3.0, p0=1.0, p1=1.0,
        gamma_c=5.0 / 3.0, eta=0.03, z=0.05,
    )
    endpoint = np.array([[1.01 / np.exp(interval["log_lambda"])]])
    result = diagnostic.stable_full_loss_trajectory(
        endpoint,
        times,
        pressure,
        gamma_c,
        np.array([0]),
        eta=0.03,
        z=0.05,
    )
    assert result["physical_cutoff_count"] == 1
    assert result["silent_fallback_count"] == 0
    assert result["state"][0, 1, 0] == diagnostic.STATE_PHYSICAL_CUTOFF
    assert result["state"][0, 0, 0] == diagnostic.STATE_POST_CUTOFF
    assert np.isnan(result["trajectory"][0, 1, 0])


def test_boundary_conditioning_detects_classification_flip() -> None:
    loss = diagnostic.stable_scaled_loss(
        t0=1.0, t1=2.0, p0=1.0, p1=1.0,
        gamma_c=5.0 / 3.0, eta=0.03, z=0.05,
    )
    gamma_at_pole = 1.0 / np.exp(loss["log_lambda"])
    check = diagnostic.interval_boundary_stability(
        gamma_later=gamma_at_pole,
        t0=1.0,
        t1=2.0,
        p0=1.0,
        p1=1.0,
        gamma_c=5.0 / 3.0,
        eta=0.03,
        z=0.05,
    )
    assert not check["stable"]
    assert set(check["classifications"]) >= {"finite", "physical_cutoff"}


def test_decision_requires_reference_and_conditioning_gates() -> None:
    gates = {
        "analytic_limits": True,
        "finite_scaled_loss": True,
        "high_precision_scaled_loss": True,
        "high_precision_gamma": True,
        "exact_state_classification": True,
        "boundary_conditioning": False,
        "zero_silent_fallbacks": True,
        "no_subrelativistic_states": True,
        "finite_or_explicit_cutoff_emissivity": True,
        "deterministic_repeat": True,
        "pinned_failure_reproduction": True,
    }
    result = diagnostic.classify_full_loss_gate(gates)
    assert result["decision"] == "FAIL"
    assert result["decision_label"] == (
        "G_LO_RADIO_METHOD_BLOCKED_STABLE_FULL_LOSS_GATE_FAILED"
    )


def test_decision_fails_when_subrelativistic_states_are_present() -> None:
    gates = {name: True for name in diagnostic.FULL_LOSS_GATE_NAMES}
    gates["no_subrelativistic_states"] = False
    result = diagnostic.classify_full_loss_gate(gates)
    assert result["decision"] == "FAIL"


def test_trajectory_comparison_uses_scale_appropriate_relative_tolerance() -> None:
    stable = {
        "trajectory": np.array([[[1.0e12 + 10.0]]]),
        "state": np.array([[[diagnostic.STATE_FINITE]]]),
    }
    reference = {
        "trajectory": np.array([[[1.0e12]]]),
        "state": np.array([[[diagnostic.STATE_FINITE]]]),
    }
    comparison = diagnostic.compare_full_loss_trajectories(
        stable, reference, np.array([0])
    )
    assert comparison["max_abs_difference"] == pytest.approx(10.0)
    assert comparison["passed"]


def test_mocked_full_loss_orchestration_writes_deterministic_evidence_and_exit_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A one-trace fixture exercises the cache gate without reading the 115 GB cache."""
    cache = tmp_path / "cache.h5"
    with h5py.File(cache, "w") as handle:
        handle.create_dataset("endpoint_ids", data=np.array([42], dtype=np.int64))
        handle.create_dataset("pressure", data=np.ones((1, 3), dtype=float))
        handle.attrs["shock_threshold"] = 0.0
        handle.attrs["shock_component"] = 0
    selection = tmp_path / "selection.csv"
    selection.write_text("cache_row,physical_id\n0,42\n")
    records = tmp_path / "records.csv"
    records.write_text("pressure_mode,physical_id,frequency_GHz\nunsmoothed,42,0.15\n")

    times = np.array([1.0, 2.0, 3.0])
    endpoint = np.array([[100.0, 120.0]])
    pressure = np.ones((1, 3))
    gamma_c = np.full((1, 3), 5.0 / 3.0)
    group = {
        "rows": np.array([0]),
        "shock_index": np.array([0]),
        "adiabatic_eff": gamma_c,
        "info": {
            "particle_times": times,
            "current_lorentz": endpoint,
            "particle_pressure": pressure,
            "ap_arr": np.zeros((1, 2)),
            "a2_arr": np.full((1, 2), np.nan),
        },
    }

    monkeypatch.setattr(diagnostic.workflow, "_validate_completed_cache", lambda h5: None)
    monkeypatch.setattr(
        diagnostic.workflow,
        "build_pressure_treatment_plan",
        lambda h5, **kwargs: {},
    )
    monkeypatch.setattr(
        diagnostic.recovery, "_read_treated_sample",
        lambda h5, rows, plan: {"time": times, "pressure": pressure},
    )
    physical = {"tracer": np.full((1, 3), 0.05)}
    monkeypatch.setattr(diagnostic.workflow, "convert_code_cache_to_physical", lambda raw, **kwargs: (physical, {}))
    monkeypatch.setattr(
        diagnostic.workflow, "calculate_praise_pair",
        lambda physical, **kwargs: {
            "ids": np.array([42]),
            "full": np.array([[1.0, 2.0]]),
            "full_info": [group],
        },
    )

    out = tmp_path / "out"
    summary = diagnostic.diagnose_full_loss(cache, selection, records, out, trace_limit=1)
    assert summary["decision"] == "PASS", [
        key for key, passed in summary["gates"].items() if not passed
    ]
    assert summary["stable_silent_fallback_count"] == 0
    assert summary["original_relevant_nonfinite_a2_count"] == 4
    assert summary["pinned_relevant_gamma_fallback_count"] == 8
    assert summary["gates"]["zero_silent_fallbacks"] is True
    assert summary["gates"]["pinned_failure_reproduction"] is True
    expected = {
        "full_loss_panel_selection.csv",
        "full_loss_interval_summary.csv",
        "full_loss_gamma_summary.csv",
        "full_loss_emissivity_summary.csv",
        "full_loss_gate_summary.csv",
        "full_loss_gate_summary.json",
    }
    assert {path.name for path in out.iterdir()} == expected
    with (out / "full_loss_gate_summary.json").open() as handle:
        assert json.load(handle)["decision"] == "PASS"
    with (out / "full_loss_gamma_summary.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and all(row["classification_match"] == "True" for row in rows)
    with (out / "full_loss_interval_summary.csv").open(newline="") as handle:
        interval_rows = list(csv.DictReader(handle))
    assert {row["a2_class"] for row in interval_rows} == {"nan"}

    # Main's scientific and infrastructure failure contracts are fail-closed.
    monkeypatch.setattr(diagnostic, "diagnose_full_loss", lambda *args, **kwargs: {"decision": "FAIL"})
    assert diagnostic.main([
        "--cache", str(cache), "--selection-csv", str(selection),
        "--nonfinite-records-csv", str(records), "--output-dir", str(tmp_path / "fail"),
    ]) == 3
    monkeypatch.setattr(diagnostic, "diagnose_full_loss", lambda *args, **kwargs: (_ for _ in ()).throw(diagnostic.FullLossDiagnosticError("bad domain")))
    assert diagnostic.main([
        "--cache", str(cache), "--selection-csv", str(selection),
        "--nonfinite-records-csv", str(records), "--output-dir", str(tmp_path / "error"),
    ]) == 2
