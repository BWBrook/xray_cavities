from __future__ import annotations

from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_adiabatic_recovery as diagnostic


def test_treated_sample_preserves_unsorted_and_repeated_requested_row_order(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache.h5"
    with h5py.File(cache, "w") as h5:
        h5.create_dataset("endpoint_ids", data=np.array([100, 101, 102, 103]))
        h5.create_dataset("times", data=np.array([0.0, 1.0, 2.0]))
        base = np.arange(12, dtype=float).reshape(4, 3)
        for offset, field in enumerate(("pressure", "density", "tracer")):
            h5.create_dataset(field, data=base + 100.0 * offset)
        h5.create_dataset(
            "last_shock_time",
            data=np.stack((base + 300.0, base + 400.0), axis=-1),
        )
        h5.create_dataset("position", data=base + 500.0)
        h5.create_dataset("velocity", data=base + 600.0)
        h5.create_dataset("tinj", data=np.array([10.0, 11.0, 12.0, 13.0]))

    requested = np.array([3, 1, 3, 2], dtype=np.int64)
    plan = {"trim_columns": np.array([-1, 1, -1, -1], dtype=np.int64)}
    with h5py.File(cache, "r") as h5:
        sample = diagnostic._read_treated_sample(h5, requested, plan)

    assert sample["physical_ids"].tolist() == [103, 101, 103, 102]
    assert sample["tinj"].tolist() == [13.0, 11.0, 13.0, 12.0]
    assert sample["time"].tolist() == [0.0, 1.0, 2.0]
    for offset, field in enumerate(("pressure", "density", "tracer")):
        expected = (base + 100.0 * offset)[requested]
        expected[1, 1] = np.nan
        np.testing.assert_allclose(sample[field], expected, equal_nan=True)
    np.testing.assert_array_equal(sample["position"], (base + 500.0)[requested])
    np.testing.assert_array_equal(sample["velocity"], (base + 600.0)[requested])
    expected_shock = np.stack((base + 300.0, base + 400.0), axis=-1)[requested]
    expected_shock[1, 1, :] = np.nan
    np.testing.assert_allclose(
        sample["last_shock_time"],
        expected_shock,
        equal_nan=True,
    )


def test_separate_absolute_powers_can_fail_while_ratio_is_finite() -> None:
    # Both absolute powers overflow, so the pinned expression is inf/inf.  The
    # ratio itself is exactly one and remains finite in log space.
    upstream = diagnostic.separate_power_ratio(2.0, 1.0e200, 1.0e200, 2.0)
    stable = diagnostic.stable_ratio_power(2.0, 1.0e200, 1.0e200, 2.0)
    assert not np.isfinite(upstream)
    assert stable == pytest.approx(2.0)


def test_pressure_and_time_stable_forms_agree_on_positive_well_conditioned_interval() -> None:
    gamma = np.array([[1.0e4]])
    times = np.array([2.0, 4.0])
    pressure = np.array([[3.0, 6.0]])
    gamma_c = np.array([[5.0 / 3.0]])
    q = np.log(pressure[:, 0] / pressure[:, 1]) / np.log(times[0] / times[1]) / (3.0 * gamma_c)
    time_form = diagnostic.stable_ratio_power(gamma, times[0], times[1], q)
    pressure_form = diagnostic.stable_pressure_ratio(
        gamma, pressure[:, 0, None], pressure[:, 1, None], gamma_c[:, 0, None]
    )
    np.testing.assert_allclose(time_form, pressure_form, rtol=1e-12, atol=0.0)


def test_high_precision_recurrence_agrees_with_stable_trajectory() -> None:
    endpoint = np.array([[1.0e4, 2.0e4]])
    times = np.array([1.0, 2.0, 4.0])
    pressure = np.array([[1.0, 2.0, 4.0]])
    ap = diagnostic.get_ap_numba(pressure[:, :-1], pressure[:, 1:], times[:-1], times[1:])
    gamma_c = np.full((1, 3), 5.0 / 3.0)
    stable = diagnostic.stable_adiabatic_trajectory(
        endpoint, times, ap, gamma_c, np.array([0]), pressure=pressure
    )
    reference = diagnostic.high_precision_adiabatic_trajectory(
        endpoint, times, ap, gamma_c, np.array([0])
    )
    check = diagnostic.compare_recovery_to_high_precision(
        stable["trajectory"], reference, stable["relevant_mask"]
    )
    assert check["passed"]
    assert stable["endpoint_gate_passed"]


def test_finite_pressure_primary_trajectory_keeps_algebraic_roundoff_diagnostic_only() -> None:
    endpoint = np.array([[1.0e4]])
    times = np.array([1.0, 2.0])
    pressure = np.array([[1.0, 2.0]])
    gamma_c = np.full((1, 2), 5.0 / 3.0)
    stable = diagnostic.stable_adiabatic_trajectory(
        endpoint,
        times,
        np.zeros((1, 1)),
        gamma_c,
        np.array([0]),
        pressure=pressure,
    )
    assert stable["relevant_algebraic_disagreement_count"] == 1
    assert stable["endpoint_gate_passed"]


def test_recovery_decision_is_separate_from_full_method_blocker() -> None:
    gates = {
        "archived_failure_reproduction": True,
        "finite_injection_gamma_emissivity": True,
        "high_precision_agreement": True,
        "stable_endpoint_trajectory": True,
        "zero_relevant_full_dynamics_nonfinite": False,
        "zero_relevant_silent_gamma_fallbacks": False,
        "upstream_stable_finite_overlap_agreement": False,
    }
    decisions = diagnostic.classify_recovery_decisions(gates)
    assert decisions["decision"] == "FAIL"
    assert decisions["decision_scope"] == "full_loss_method_readiness"
    assert decisions["adiabatic_recovery_decision"] == "PASS"
    assert decisions["full_method_decision"] == "BLOCKED"


def test_high_precision_recurrence_declares_80_digit_context(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    original = diagnostic.mpmath.workdps

    def wrapped(dps: int):
        seen.append(int(dps))
        return original(dps)

    monkeypatch.setattr(diagnostic.mpmath, "workdps", wrapped)
    diagnostic.high_precision_adiabatic_trajectory(
        np.array([[1.0e4]]), np.array([1.0, 1.0000001]),
        np.array([[1.0e-9]]), np.array([[5.0 / 3.0, 5.0 / 3.0]]), np.array([0]),
    )
    assert diagnostic.HP_DPS in seen


def test_relevant_window_classification_preserves_preshock_evidence() -> None:
    values = np.array([[1.0, np.nan, np.nan, 2.0]])
    counts = diagnostic.classify_relevant_windows(values, np.array([2]))
    assert counts["relevant_nonfinite_count"] == 1
    assert counts["preshock_nonfinite_count"] == 1
    assert counts["relevant_cell_count"] == 2
    assert counts["preshock_cell_count"] == 2


def test_zero_or_nonpositive_time_fails_closed() -> None:
    endpoint = np.array([[1.0e4]])
    times = np.array([0.0, 1.0])
    ap = np.array([[0.0]])
    gamma_c = np.array([[5.0 / 3.0, 5.0 / 3.0]])
    stable = diagnostic.stable_adiabatic_trajectory(
        endpoint, times, ap, gamma_c, np.array([0]), pressure=np.array([[1.0, 1.0]])
    )
    assert stable["relevant_nonpositive_time_count"] == 1
    assert not stable["endpoint_gate_passed"]


def test_fail_closed_on_nonpositive_pressure() -> None:
    with pytest.raises(diagnostic.RecoveryDiagnosticError, match="finite positive"):
        diagnostic.stable_pressure_ratio(1.0, 0.0, 1.0, 5.0 / 3.0)


def test_relevant_nonfinite_dynamics_fail_closed_but_preshock_is_reported() -> None:
    endpoint = np.array([[1.0e4]])
    times = np.array([1.0, 2.0, 4.0])
    ap = np.array([[0.0, np.nan]])
    gamma_c = np.full((1, 3), 5.0 / 3.0)
    result = diagnostic.stable_adiabatic_trajectory(
        endpoint, times, ap, gamma_c, np.array([0]),
        pressure=np.ones((1, 3)),
    )
    assert result["relevant_nonfinite_count"] > 0
    assert not result["endpoint_gate_passed"]


def test_relevance_uses_current_interval_for_multiple_nonzero_shocks() -> None:
    endpoint = np.array([[1.0e4], [2.0e4]])
    times = np.array([1.0, 2.0, 4.0, 8.0])
    ap = np.zeros((2, 3))
    gamma_c = np.full((2, 4), 5.0 / 3.0)
    # Row 0 is relevant from interval 1; row 1 only from interval 2.
    result = diagnostic.stable_adiabatic_trajectory(
        endpoint, times, ap, gamma_c, np.array([1, 2]),
        pressure=np.ones((2, 4)),
    )
    assert result["relevant_mask"].tolist() == [
        [False, True, True, True],
        [False, False, True, True],
    ]
    full = np.zeros((2, 3))
    full[0, 0] = np.nan  # pre-shock for row 0
    full[1, 1] = np.nan  # pre-shock for row 1
    counts = diagnostic.classify_relevant_windows(full, np.array([1, 2]))
    assert counts["relevant_nonfinite_count"] == 0
    assert counts["preshock_nonfinite_count"] == 2


def test_gamma_fallback_relevance_uses_interval_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        diagnostic,
        "get_gamma_numba",
        lambda *, g_nm1, **_kwargs: np.full_like(g_nm1, np.nan),
    )
    result = diagnostic.classify_gamma_fallbacks(
        np.ones((2, 1)) * 1e4,
        np.array([1.0, 2.0, 4.0, 8.0]),
        np.full((2, 4), 5.0 / 3.0),
        np.zeros((2, 3)),
        np.zeros((2, 3)),
        np.array([1, 2]),
    )
    assert result["relevant_fallback_count"] == 3
    assert result["preshock_fallback_count"] == 3


def test_stable_emissivity_uses_endpoint_gamma_c(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, float] = {}

    def fake_k(_s, gamma_c, _gmin, _gmax):
        seen["K_gamma_c"] = float(gamma_c)
        return 1.0

    def fake_emissivity(*, gamma_c, **_kwargs):
        seen["emissivity_gamma_c"] = float(np.asarray(gamma_c)[0])
        return np.ones((1, 2))

    monkeypatch.setattr(diagnostic, "get_K", fake_k)
    monkeypatch.setattr(diagnostic, "get_emissivity_numba", fake_emissivity)
    out = diagnostic.reconstruct_stable_injection_emissivity(
        np.array([10.0, 20.0]), np.array([8.0, 16.0]),
        np.array([1.4, 1.5, 1.6]), np.array([2.0, 3.0, 4.0]), 0, 0.8,
    )
    assert out.shape == (1, 2)
    assert seen == {"K_gamma_c": 1.6, "emissivity_gamma_c": 1.6}


def test_trace_selection_covers_both_modes_and_labels_controls() -> None:
    selection = [
        {"sample_index": 0, "cache_row": 0, "physical_id": 10, "selection_reason": "extreme"},
        {"sample_index": 1, "cache_row": 1, "physical_id": 11, "selection_reason": "ordinary"},
    ]
    records = [
        {"pressure_mode": mode, "physical_id": 10, "frequency_GHz": frequency}
        for mode in ("unsmoothed", "log_savgol")
        for frequency in (0.15, 1.4)
    ]
    chosen = diagnostic.choose_trace_selection(selection, records, trace_limit=2)
    assert chosen[0]["trace_class"] == "archived_nonfinite"
    assert len(chosen[0]["trace_strata"]) == 4
    assert chosen[1]["trace_class"] == "finite_control"


def test_archived_failure_reproduction_gate_passes_when_all_strata_match() -> None:
    selected = [{
        "physical_id": 10,
        "trace_class": "archived_nonfinite",
        "trace_strata": ["unsmoothed/0.15", "log_savgol/1.4"],
    }]
    values = {
        "unsmoothed": np.array([[np.nan, 1.0]]),
        "unsmoothed_ids": np.array([10]),
        "log_savgol": np.array([[1.0, np.nan]]),
        "log_savgol_ids": np.array([10]),
    }
    result = diagnostic.assess_archived_failure_reproduction(selected, values)
    assert result["gate_passed"]
    assert result["expected_count"] == result["reproduced_count"] == 2
    assert result["missing_count"] == 0


def test_archived_failure_reproduction_gate_fails_on_missing_stratum() -> None:
    selected = [{
        "physical_id": 10,
        "trace_class": "archived_nonfinite",
        "trace_strata": ["unsmoothed/0.15", "log_savgol/1.4"],
    }]
    values = {
        "unsmoothed": np.array([[1.0, 1.0]]),
        "unsmoothed_ids": np.array([10]),
        "log_savgol": np.array([[1.0, np.nan]]),
        "log_savgol_ids": np.array([10]),
    }
    result = diagnostic.assess_archived_failure_reproduction(selected, values)
    assert not result["gate_passed"]
    assert result["missing_count"] == 1
    assert result["by_pressure_mode"]["unsmoothed"]["missing_count"] == 1
