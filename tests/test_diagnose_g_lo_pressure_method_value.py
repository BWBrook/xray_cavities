from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest
from astropy import units as u

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_pressure_method_value as diagnostic
from scripts.science import run_g_lo_radio_history_value as workflow


UNIT = u.W / (u.Hz * u.m**3 * u.sr)


def _write_cache(path: Path, *, rows: int = 24, columns: int = 8) -> None:
    ids = np.arange(10_000, 10_000 + rows, dtype=np.int64)
    times = np.arange(columns, dtype=float)
    presence = np.ones((rows, columns), dtype=bool)
    presence[4, :5] = False
    presence[5, :6] = False
    pressure = np.empty((rows, columns), dtype=float)
    for row in range(rows):
        pressure[row] = (1.0 + row / 10) * np.exp(np.linspace(0, 0.2 + row / 30, columns))
    # A large log-SG endpoint perturbation outside the linear-affected CSV.
    pressure[12] = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 100.0])
    pressure[~presence] = np.nan
    density = np.where(presence, 2.0, np.nan)
    tracer = np.where(presence, 0.8, np.nan)
    last = np.where(presence, np.minimum(times[None, :], 0.5 + np.arange(rows)[:, None] / 10), np.nan)
    # Two approved joint initialization trims and one no-positive exclusion.
    for row, column in ((1, 0), (2, 0)):
        pressure[row, column] = density[row, column] = tracer[row, column] = 0.0
    pressure[3] = density[3] = tracer[3] = 0.0
    tinj = np.zeros(rows)
    tinj[4] = 4.0
    tinj[5] = 5.0
    with h5py.File(path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=ids)
        h5.create_dataset("times", data=times)
        h5.create_dataset("output_indices", data=np.arange(columns, dtype=np.int64))
        h5.create_dataset("pressure", data=pressure)
        h5.create_dataset("density", data=density)
        h5.create_dataset("tracer", data=tracer)
        h5.create_dataset("last_shock_time", data=last)
        h5.create_dataset("position", data=np.arange(rows * 3, dtype=float).reshape(rows, 3))
        h5.create_dataset("velocity", data=np.ones((rows, 3)) * 1e-4)
        h5.create_dataset("tinj", data=tinj)
        h5.create_dataset("presence", data=presence)
        h5.attrs["next_output"] = columns
        h5.attrs["shock_threshold"] = 5.0
        h5.attrs["shock_component"] = 2
        h5.attrs["source_identity_sha256"] = "a" * 64


def _write_affected(path: Path) -> None:
    rows = [
        (6, 10006, 0.01, 0.8),
        (7, 10007, -0.55, 0.7),
        (8, 10008, 0.03, 0.05),
        (9, 10009, 0.04, 0.6),
        (10, 10010, 0.02, 0.9),
        (11, 10011, -0.10, 0.4),
    ]
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "cache_row", "physical_id", "log_endpoint_relative_difference",
            "min_log_to_raw_ratio",
        ])
        writer.writerows(rows)


def _plan(cache: Path):
    handle = h5py.File(cache, "r")
    return handle, workflow.build_pressure_treatment_plan(
        handle,
        expected_trim_rows=2,
        expected_no_positive_rows=1,
        expected_single_record_rows=0,
    )


def test_sample_is_deterministic_and_includes_short_and_extreme_rows(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    affected_path = tmp_path / "affected.csv"
    _write_cache(cache)
    _write_affected(affected_path)
    affected = diagnostic._read_affected_rows(affected_path)
    handle, plan = _plan(cache)
    try:
        first = diagnostic.construct_deterministic_sample(
            handle, plan, affected, sample_size=12, extreme_count_per_tail=1
        )
        second = diagnostic.construct_deterministic_sample(
            handle, plan, affected, sample_size=12, extreme_count_per_tail=1
        )
    finally:
        handle.close()
    np.testing.assert_array_equal(first[0], second[0])
    assert first[1] == second[1]
    selected = set(first[0].tolist())
    assert {4, 5}.issubset(selected)
    assert 12 in selected  # global log-SG extreme outside linear-affected CSV
    assert len(selected) == 12
    assert any(row["affected_linear_sg"] for row in first[1])
    assert any(not row["affected_linear_sg"] for row in first[1])
    assert any(row["trim_affected"] for row in first[1])
    assert all(float(row["analysis_weight"]) > 0 for row in first[1])
    assert first[2]["scope"].startswith("sample evidence")
    outside = next(row for row in first[1] if row["cache_row"] == 12)
    assert outside["affected_linear_sg"] is False
    assert "extreme_abs_log_endpoint_perturbation" in outside["selection_reason"]
    assert first[2]["log_savgol_extrema_universe"] == "all active treated cache rows"


def test_sample_uses_exact_4096_rows_when_population_is_sufficient(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Exercise the exact-size contract without constructing a huge HDF5 fixture.
    n = 5000
    features = {
        "physical_id": np.arange(n, dtype=np.int64),
        "active": np.ones(n, dtype=bool),
        "trim": np.zeros(n, dtype=bool),
        "history_length": np.full(n, 10, dtype=np.int32),
        "injection_age": np.linspace(1, 10, n),
        "dynamic_range": np.linspace(0, 2, n),
        "shock_age": np.linspace(0, 5, n),
        "short": np.zeros(n, dtype=bool),
        "affected": np.zeros(n, dtype=bool),
        "log_endpoint": np.full(n, np.nan),
        "min_log_ratio": np.full(n, np.nan),
    }
    features["affected"][:100] = True
    features["log_endpoint"][:100] = np.linspace(-1, 1, 100)
    features["min_log_ratio"][:100] = np.linspace(0.01, 0.9, 100)
    monkeypatch.setattr(diagnostic, "_feature_table", lambda *_args, **_kwargs: features)
    rows, records, metadata = diagnostic.construct_deterministic_sample(
        object(),
        {"active_mask": np.ones(n, bool)},
        {row: {} for row in range(100)},
    )
    assert len(rows) == len(records) == 4096
    assert metadata["sample_size_selected"] == 4096


def test_weighted_method_metrics_and_gates() -> None:
    selection = [
        {"physical_id": 1, "analysis_weight": 1.0},
        {"physical_id": 2, "analysis_weight": 1.0},
        {"physical_id": 3, "analysis_weight": 1.0},
    ]
    full = np.array([[10.0, 5.0], [10.0, 5.0], [10.0, 5.0]])
    none = full * 2
    unsmoothed = {
        "ids": np.array([1, 2, 3]),
        "full": full * UNIT,
        "adiabatic": full * 1.1 * UNIT,
        "none": none * UNIT,
    }
    log = {
        "ids": np.array([1, 2, 3]),
        "full": full * 1.05 * UNIT,
        "adiabatic": full * 1.15 * UNIT,
        "none": none * 1.05 * UNIT,
    }
    rows, summary = diagnostic.summarise_method_comparison(selection, unsmoothed, log)
    assert len(rows) == 3
    assert summary["decision"] == "PASS"
    assert summary["gate_results"] == {
        "aggregate_difference": True,
        "spectral_index_difference": True,
        "full_vs_lossless_direction": True,
        "radiative_suppression": True,
        "discrepancy_concentration": True,
    }
    assert summary["aggregate_log_savgol_minus_unsmoothed_dex"][0] == pytest.approx(
        np.log10(1.05)
    )


def test_diagnostic_calls_both_actual_modes_and_is_repeatable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache.h5"
    affected = tmp_path / "affected.csv"
    _write_cache(cache)
    _write_affected(affected)
    calls: list[str] = []

    def fake_praise(data, *, pressure_mode, **_kwargs):
        calls.append(pressure_mode)
        ids = np.asarray(data["physical_ids"], dtype=np.int64)
        particle_count = len(ids)
        base = np.column_stack((np.arange(1, len(ids) + 1), np.arange(1, len(ids) + 1) / 2))
        multiplier = 1.02 if pressure_mode == "log_savgol" else 1.0
        grouped_info = {
            "particle_times": np.array([1.0, 2.0, 3.0]),
            "current_lorentz": np.full((particle_count, 2), 10.0),
            "injection_lorentz": np.full((particle_count, 2), 10.0),
            "ap_arr": np.zeros((particle_count, 2)),
            "a2_arr": np.zeros((particle_count, 2)),
            "particle_pressure": np.ones((particle_count, 3)),
        }
        grouped_provenance = {
            "start_index": 0,
            "rows": np.arange(particle_count, dtype=np.int64),
            "shock_index": np.zeros(particle_count, dtype=np.int64),
            "injection_pressure": np.ones(particle_count),
            "adiabatic_eff": np.full((particle_count, 3), 5.0 / 3.0),
        }
        forensic_records = [
            {
                "loss_branch": branch,
                "physical_id": int(ids[row]),
                "frequency_GHz": float(frequency),
                "output_class": "finite",
            }
            for branch in ("full", "adiabatic", "none")
            for row in range(particle_count)
            for frequency in diagnostic.FREQUENCIES_GHZ
        ]
        return {
            "ids": ids,
            "full": base * multiplier * UNIT,
            "adiabatic": base * multiplier * 1.1 * UNIT,
            "none": base * multiplier * 2 * UNIT,
            "metadata": {"pressure_mode": pressure_mode},
            "full_info": [{**grouped_provenance, "info": grouped_info}],
            "adiabatic_info": [{**grouped_provenance, "info": grouped_info}],
            "none_info": [{**grouped_provenance, "info": grouped_info}],
            "nonfinite_diagnostics": {"records": forensic_records},
        }

    monkeypatch.setattr(diagnostic, "calculate_praise_pair", fake_praise)
    first = diagnostic.diagnose_pressure_method_value(
        cache,
        affected,
        tmp_path / "first",
        sample_size=23,
        expected_trim_rows=2,
        expected_no_positive_rows=1,
        expected_single_record_rows=0,
    )
    second = diagnostic.diagnose_pressure_method_value(
        cache,
        affected,
        tmp_path / "second",
        sample_size=23,
        expected_trim_rows=2,
        expected_no_positive_rows=1,
        expected_single_record_rows=0,
    )
    assert calls == ["unsmoothed", "log_savgol", "unsmoothed", "log_savgol"]
    assert first["decision"] == second["decision"] == "PASS"
    for name in (
        "pressure_method_selection.csv",
        "pressure_method_unsmoothed_emissivity_checkpoint.npz",
        "pressure_method_log_savgol_emissivity_checkpoint.npz",
        "pressure_method_particle_comparison.csv",
        "pressure_method_full_reference_ordering.csv",
        "pressure_method_gamma_fallback_summary.csv",
        "pressure_method_gamma_fallback_records.csv",
        "pressure_method_summary.csv",
    ):
        assert (tmp_path / "first" / name).read_bytes() == (tmp_path / "second" / name).read_bytes()
    summary = json.loads((tmp_path / "first" / "pressure_method_summary.json").read_text())
    assert summary["pressure_modes"]["primary"]["pressure_mode"] == "unsmoothed"
    assert summary["pressure_modes"]["comparator"]["pressure_mode"] == "log_savgol"
    assert summary["pressure_modes"]["primary"]["actual_praise_dynamics"]["ap_arr"][
        "finite_count"
    ] == 46
    assert summary["comparison"]["gamma_fallback"]["gate_passed"] is True
    assert summary["comparison"]["gamma_fallback"]["record_count"] == 0
    assert summary["comparison"]["inference_scope"].startswith("deterministic weighted sample")


def test_raw_checkpoint_round_trip_preserves_nonfinite_branch_values(tmp_path: Path) -> None:
    result = {
        "ids": np.array([101], dtype=np.int64),
        "full": np.array([[np.nan, np.inf]]) * UNIT,
        "adiabatic": np.array([[-np.inf, 2.0]]) * UNIT,
        "none": np.array([[3.0, 4.0]]) * UNIT,
    }
    path = tmp_path / "checkpoint.npz"
    diagnostic._write_emissivity_checkpoint(path, result)
    with np.load(path) as loaded:
        assert np.isnan(loaded["full"][0, 0])
        assert np.isposinf(loaded["full"][0, 1])
        assert np.isneginf(loaded["adiabatic"][0, 0])
        np.testing.assert_array_equal(loaded["none"], [[3.0, 4.0]])


def test_nonfinite_diagnostic_writes_fail_evidence_without_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache.h5"
    affected = tmp_path / "affected.csv"
    _write_cache(cache)
    _write_affected(affected)
    calls: list[tuple[str, bool]] = []

    def fake_praise(data, *, pressure_mode, diagnostic=False, **_kwargs):
        calls.append((pressure_mode, diagnostic))
        ids = np.asarray(data["physical_ids"], dtype=np.int64)
        n = len(ids)
        base = np.ones((n, 2))
        info = {
            "particle_times": np.array([1.0, 2.0, 3.0]),
            "current_lorentz": np.full((n, 2), 10.0),
            "injection_lorentz": np.full((n, 2), 10.0),
            "ap_arr": np.zeros((n, 2)),
            "a2_arr": np.zeros((n, 2)),
            "particle_pressure": np.ones((n, 3)),
        }
        provenance = {
            "start_index": 0,
            "rows": np.arange(n, dtype=np.int64),
            "shock_index": np.zeros(n, dtype=np.int64),
            "injection_pressure": np.ones(n),
            "adiabatic_eff": np.full((n, 3), 5.0 / 3.0),
        }
        return {
            "ids": ids,
            "full": base * UNIT,
            "adiabatic": np.full((n, 2), np.nan) * UNIT,
            "none": base * 2 * UNIT,
            "metadata": {"pressure_mode": pressure_mode},
            "full_info": [{**provenance, "info": info}],
            "adiabatic_info": [{**provenance, "info": info}],
            "none_info": [{**provenance, "info": info}],
            "nonfinite_diagnostics": {"records": []},
        }

    monkeypatch.setattr(diagnostic, "calculate_praise_pair", fake_praise)
    monkeypatch.setattr(
        diagnostic,
        "summarise_gamma_fallbacks",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            diagnostic.PressureMethodDiagnosticError("synthetic gamma audit failure")
        ),
    )
    monkeypatch.setattr(
        diagnostic,
        "summarise_actual_praise_dynamics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            diagnostic.PressureMethodDiagnosticError("synthetic dynamics audit failure")
        ),
    )
    result = diagnostic.diagnose_pressure_method_value(
        cache, affected, tmp_path / "out", sample_size=23,
        expected_trim_rows=2, expected_no_positive_rows=1,
        expected_single_record_rows=0,
    )
    assert calls == [("unsmoothed", True), ("log_savgol", True)]
    assert result["decision"] == "FAIL"
    out = tmp_path / "out"
    for name in (
        "pressure_method_nonfinite_emissivity_summary.csv",
        "pressure_method_nonfinite_emissivity_records.csv",
        "pressure_method_unsmoothed_emissivity_checkpoint.npz",
        "pressure_method_log_savgol_emissivity_checkpoint.npz",
    ):
        assert (out / name).is_file()
    summary = json.loads((out / "pressure_method_summary.json").read_text())
    assert summary["status"] == "diagnostic_complete"
    assert summary["nonfinite_evidence"]["nonfinite_branch_count"] == 2
    assert summary["nonfinite_evidence"]["coverage_valid"] is False
    assert summary["nonfinite_evidence"]["coverage_error_count"] > 0
    assert summary["comparison"]["comparison_semantics"][
        "finite_only_comparison_suppressed"
    ] is True
    fallback_text = (out / "pressure_method_gamma_fallback_summary.csv").read_text()
    assert "synthetic gamma audit failure" in fallback_text
    assert "synthetic dynamics audit failure" in summary["pressure_modes"][
        "primary"
    ]["actual_praise_dynamics"]["audit_error"]


def test_gamma_fallback_replay_is_detected_and_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = [{
        "sample_index": 0,
        "cache_row": 12,
        "physical_id": 1012,
        "analysis_weight": 1.0,
        "trim_affected": False,
        "short_history": False,
        "selection_reason": "unit-test",
        "stratum": "unit-test",
    }]
    info = {
        "particle_times": np.array([1.0, 2.0]),
        "current_lorentz": np.full((1, 2), 10.0),
        "injection_lorentz": np.full((1, 2), 10.0),
        "ap_arr": np.zeros((1, 1)),
        "a2_arr": np.zeros((1, 1)),
    }
    result = {
        "ids": np.array([1012]),
        **{
            f"{branch}_info": [{
                "rows": np.array([0], dtype=np.int64),
                "shock_index": np.array([0], dtype=np.int64),
                "adiabatic_eff": np.full((1, 2), 5.0 / 3.0),
                "info": info,
            }]
            for branch in ("full", "adiabatic", "none")
        },
    }
    monkeypatch.setattr(
        diagnostic,
        "get_gamma_numba",
        lambda **kwargs: np.full_like(kwargs["g_nm1"], np.nan),
    )
    summaries, records = diagnostic.summarise_gamma_fallbacks(
        result, selection, pressure_mode="unsmoothed"
    )
    assert len(summaries) == 3
    assert all(row["fallback_event_count"] == 2 for row in summaries)
    assert all(row["gate_passed"] is False for row in summaries)
    assert len(records) == 6
    assert {row["loss_branch"] for row in records} == {"full", "adiabatic", "none"}
    assert {row["frequency_GHz"] for row in records} == {0.15, 1.4}


def test_comparison_reports_full_above_no_evolution_without_rejecting() -> None:
    selection = [{"physical_id": 1, "analysis_weight": 1.0}]
    bad = {
        "ids": np.array([1]),
        "full": np.array([[2.0, 2.0]]),
        "adiabatic": np.array([[2.1, 2.1]]),
        "none": np.array([[1.0, 1.0]]),
    }
    rows, summary = diagnostic.summarise_method_comparison(selection, bad, bad)
    assert rows[0]["unsmoothed_full_vs_none_0.15GHz"] == "full_above_none"
    assert rows[0]["unsmoothed_full_over_none_0.15GHz"] == pytest.approx(2.0)
    ordering = summary["full_vs_none_ordering"]["unsmoothed"][0]
    assert ordering["full_above_none_count"] == 1
    assert ordering["aggregate_direction"] == "full_above_none"
    assert ordering["aggregate_full_over_none_ratio"] == pytest.approx(2.0)
    assert summary["comparison_semantics"]["none_branch_is_upper_bound"] is False


def test_full_vs_none_ordering_tolerance_is_relative_at_tiny_emissivity_scale() -> None:
    selection = [{"physical_id": 1, "analysis_weight": 1.0}]
    bad = {
        "ids": np.array([1]),
        "full": np.array([[2e-200, 2e-200]]),
        "adiabatic": np.array([[3e-200, 3e-200]]),
        "none": np.array([[1e-200, 1e-200]]),
    }
    _, summary = diagnostic.summarise_method_comparison(selection, bad, bad)
    assert all(
        row["full_above_none_count"] == 1
        for row in summary["full_vs_none_ordering"]["unsmoothed"]
    )


def test_ordering_tolerance_does_not_hide_faint_relative_violation() -> None:
    selection = [
        {"physical_id": 1, "analysis_weight": 1.0},
        {"physical_id": 2, "analysis_weight": 1.0},
    ]
    result = {
        "ids": np.array([1, 2]),
        "full": np.array([[1.0, 1.0], [2e-20, 2e-20]]),
        "adiabatic": np.array([[1.0, 1.0], [1e-20, 1e-20]]),
        "none": np.array([[2.0, 2.0], [2e-20, 2e-20]]),
    }
    _, summary = diagnostic.summarise_method_comparison(selection, result, result)
    assert summary["full_vs_adiabatic_ordering"]["unsmoothed"][0][
        "full_above_adiabatic_count"
    ] == 1
    assert summary["gate_results"]["radiative_suppression"] is False


def test_comparison_fails_closed_when_full_exceeds_adiabatic() -> None:
    selection = [{"physical_id": 1, "analysis_weight": 1.0}]
    result = {
        "ids": np.array([1]),
        "full": np.array([[2.0, 2.0]]),
        "adiabatic": np.array([[1.0, 1.0]]),
        "none": np.array([[3.0, 3.0]]),
    }
    _, summary = diagnostic.summarise_method_comparison(selection, result, result)
    assert summary["decision"] == "FAIL"
    assert summary["gate_results"]["radiative_suppression"] is False
    assert summary["full_vs_adiabatic_ordering"]["unsmoothed"][0][
        "full_above_adiabatic_count"
    ] == 1


def test_actual_dynamics_summary_rejects_nonfinite_and_reports_quantiles() -> None:
    good = {
        "full_info": [{
            "info": {
                "ap_arr": np.arange(10, dtype=float),
                "a2_arr": np.arange(10, dtype=float) / 10,
            }
        }]
    }
    summary = diagnostic.summarise_actual_praise_dynamics(good)
    assert summary["ap_arr"]["finite_count"] == 10
    assert summary["ap_arr"]["minimum"] == 0
    assert summary["ap_arr"]["q50"] == pytest.approx(4.5)
    good["full_info"][0]["info"]["a2_arr"][3] = np.nan
    with pytest.raises(diagnostic.PressureMethodDiagnosticError, match="non-finite"):
        diagnostic.summarise_actual_praise_dynamics(good)


def test_discrepancy_concentration_ranks_particles_then_uses_population_weight() -> None:
    # The old implementation ranked weight*discrepancy and selected one sampled
    # row, yielding 100/110 ~= 0.909.  The represented-population definition
    # ranks the genuinely high-discrepancy row first and takes a fractional
    # boundary row: (1*10 + 0.99*1)/110 ~= 0.0999.
    discrepancy = np.r_[1.0, 10.0, np.zeros(98)]
    weights = np.r_[100.0, np.ones(99)]
    result = diagnostic.represented_population_discrepancy_concentration(
        discrepancy,
        weights,
    )
    assert result["represented_population_weight"] == pytest.approx(199)
    assert result["target_population_weight"] == pytest.approx(1.99)
    assert result["fraction"] == pytest.approx(10.99 / 110)
    assert result["fractional_boundary_row_weight_fraction"] == pytest.approx(0.0099)
    assert result["fraction"] < 0.5
