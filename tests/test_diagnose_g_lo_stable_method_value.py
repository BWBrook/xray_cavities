from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pytest
from astropy import units as u

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_adiabatic_recovery as adiabatic
from scripts.science import diagnose_g_lo_full_loss_recurrence as full_loss
from scripts.science import diagnose_g_lo_stable_method_value as diagnostic


UNIT = u.W / (u.Hz * u.m**3 * u.sr)


def _selection(*physical_ids: int) -> list[dict[str, Any]]:
    return [
        {
            "sample_index": index,
            "cache_row": 10 + index,
            "physical_id": physical_id,
            "analysis_weight": 1.0,
        }
        for index, physical_id in enumerate(physical_ids)
    ]


def _group(
    rows: list[int],
    *,
    times: np.ndarray | None = None,
    pressure: np.ndarray | None = None,
    endpoint: np.ndarray | None = None,
    shock_index: np.ndarray | None = None,
    singleton: bool = False,
) -> dict[str, Any]:
    rows_array = np.asarray(rows, dtype=np.int64)
    times_array = np.asarray(
        [3.0e13] if times is None and singleton else (
            [1.0e13, 2.0e13, 3.0e13] if times is None else times
        ),
        dtype=np.float64,
    )
    width = times_array.size
    count = rows_array.size
    pressure_array = np.asarray(
        np.full((count, width), 1.0e-12) if pressure is None else pressure,
        dtype=np.float64,
    )
    endpoint_array = np.asarray(
        np.column_stack((
            1000.0 + 100.0 * np.arange(count),
            2000.0 + 100.0 * np.arange(count),
        ))
        if endpoint is None else endpoint,
        dtype=np.float64,
    )
    shocks = np.asarray(
        np.zeros(count, dtype=np.int64) if shock_index is None else shock_index,
        dtype=np.int64,
    )
    info = {
        "particle_times": times_array,
        "current_lorentz": endpoint_array,
        "injection_lorentz": np.full_like(endpoint_array, np.nan),
        "ap_arr": np.zeros((count, max(0, width - 1)), dtype=np.float64),
        # The pinned full-loss coefficient is deliberately not used by Goal 051.
        "a2_arr": np.full((count, max(0, width - 1)), np.nan),
        "particle_pressure": pressure_array,
    }
    if singleton:
        info["singleton_convention"] = "instantaneous_recent_shock"
    return {
        "start_index": 0,
        "rows": rows_array,
        "shock_index": shocks,
        "injection_pressure": pressure_array[np.arange(count), shocks],
        "adiabatic_eff": np.full((count, width), 5.0 / 3.0),
        "info": info,
    }


def _result(
    ids: list[int],
    groups: list[dict[str, Any]],
    *,
    none: np.ndarray | None = None,
) -> dict[str, Any]:
    ids_array = np.asarray(ids, dtype=np.int64)
    none_array = np.asarray(
        np.full((len(ids), 2), 1.0e-38) if none is None else none,
        dtype=np.float64,
    )
    return {
        "ids": ids_array,
        # These pinned values must never enter the stable comparison.
        "full": np.full_like(none_array, np.nan) * UNIT,
        "none": none_array * UNIT,
        "full_info": groups,
        "none_info": [
            {
                "rows": np.asarray(group["rows"], dtype=np.int64),
                "info": group["info"],
            }
            for group in groups
        ],
        "metadata": {
            "pressure_mode": "unsmoothed",
            "singleton_policy": "instantaneous_recent_shock",
        },
    }


def test_singleton_reconstruction_uses_the_explicit_instantaneous_policy() -> None:
    selection = _selection(101)
    group = _group([0], singleton=True)
    endpoint = group["info"]["current_lorentz"][0]
    pressure = group["info"]["particle_pressure"][0]
    gamma_c = group["adiabatic_eff"][0]
    expected_none = full_loss.reconstruct_full_loss_injection_emissivity(
        endpoint,
        endpoint,
        gamma_c,
        pressure,
        0,
        0.8,
    )
    result = _result([101], [group], none=expected_none[None, :])
    physical = {"tracer": np.asarray([[0.8]])}

    branches, summary, cutoff_records = diagnostic.reconstruct_stable_mode(
        result,
        physical,
        selection,
        pressure_mode="unsmoothed",
    )

    assert cutoff_records == []
    assert summary["singleton_particle_count"] == 1
    assert summary["stable_full"]["state_counts"]["finite"] == 2
    assert summary["stable_adiabatic"]["gate_passed"] is True
    np.testing.assert_allclose(branches["full"], branches["adiabatic"])
    np.testing.assert_allclose(branches["full"], branches["none"])


def test_grouped_reconstruction_covers_dense_rows_and_ignores_pinned_full() -> None:
    selection = _selection(101, 202)
    # Deliberately reverse group order: group rows index the selected sample.
    later = _group(
        [1],
        endpoint=np.asarray([[1200.0, 2200.0]]),
    )
    earlier = _group(
        [0],
        endpoint=np.asarray([[1000.0, 2000.0]]),
    )
    result = _result([101, 202], [later, earlier])
    physical = {"tracer": np.full((2, 3), 0.8)}

    branches, summary, cutoff_records = diagnostic.reconstruct_stable_mode(
        result,
        physical,
        selection,
        pressure_mode="unsmoothed",
    )
    repeat, repeat_summary, _ = diagnostic.reconstruct_stable_mode(
        result,
        physical,
        selection,
        pressure_mode="unsmoothed",
    )

    assert cutoff_records == []
    assert summary["grouped_provenance_complete"] is True
    assert summary["stable_full"]["silent_fallback_count"] == 0
    assert summary["stable_full"]["deterministic_repeat"] is True
    assert summary["stable_full"]["conditioning"]["instability_count"] == 0
    assert summary["branch_fingerprint_sha256"] == repeat_summary[
        "branch_fingerprint_sha256"
    ]
    assert not np.array_equal(branches["full"][0], branches["full"][1])
    for branch in ("full", "adiabatic", "none"):
        assert branches[branch].shape == (2, 2)
        assert np.all(np.isfinite(branches[branch]))
        assert np.all(branches[branch] >= 0)
        np.testing.assert_array_equal(branches[branch], repeat[branch])


def test_audited_physical_cutoff_is_zero_and_requires_review() -> None:
    selection = _selection(101)
    group = _group(
        [0],
        pressure=np.full((1, 3), 1.0e-8),
        endpoint=np.asarray([[1000.0, 2000.0]]),
    )
    result = _result([101], [group])
    physical = {"tracer": np.full((1, 3), 0.8)}

    branches, summary, records = diagnostic.reconstruct_stable_mode(
        result,
        physical,
        selection,
        pressure_mode="unsmoothed",
    )

    assert summary["cutoff_review_required"] is True
    assert summary["stable_full"]["state_counts"]["physical_cutoff"] == 2
    assert summary["stable_full"]["state_counts"]["gamma_inf_cutoff"] == 0
    assert len(records) == 2
    assert all(record["classification"] == "physical_cutoff" for record in records)
    assert all(record["reference_classification_match"] for record in records)
    assert all(record["ulp_classification_stable"] for record in records)
    assert all(record["explicit_zero_emissivity"] for record in records)
    np.testing.assert_array_equal(branches["full"], np.zeros((1, 2)))


@pytest.mark.parametrize("audit_failure", ["reference_state", "ulp_instability"])
def test_cutoff_audit_failure_is_a_scientific_fail_not_a_hold(
    monkeypatch: pytest.MonkeyPatch,
    audit_failure: str,
) -> None:
    selection = _selection(101)
    group = _group(
        [0],
        pressure=np.full((1, 3), 1.0e-8),
        endpoint=np.asarray([[1000.0, 2000.0]]),
    )
    if audit_failure == "reference_state":
        monkeypatch.setattr(
            diagnostic.full_loss,
            "high_precision_full_loss_interval",
            lambda **_kwargs: {
                "classification": full_loss.STATE_GAMMA_INF_CUTOFF,
            },
        )
    else:
        monkeypatch.setattr(
            diagnostic.full_loss,
            "interval_boundary_stability",
            lambda **_kwargs: {"stable": False},
        )

    with pytest.raises(
        diagnostic.StableMethodScientificFailure,
        match="cutoff audit|classification instability",
    ):
        diagnostic.reconstruct_stable_mode(
            _result([101], [group]),
            {"tracer": np.full((1, 3), 0.8)},
            selection,
            pressure_mode="unsmoothed",
        )


def test_subrelativistic_state_fails_scientifically() -> None:
    selection = _selection(101)
    group = _group(
        [0],
        times=np.asarray([1.0e13, 2.0e13]),
        pressure=np.asarray([[1.0e-15, 1.0e-12]]),
        endpoint=np.asarray([[2.0, 2.0]]),
    )

    with pytest.raises(
        diagnostic.StableMethodScientificFailure,
        match="subrelativistic",
    ):
        diagnostic.reconstruct_stable_mode(
            _result([101], [group]),
            {"tracer": np.full((1, 2), 0.8)},
            selection,
            pressure_mode="unsmoothed",
        )


def test_adiabatic_relevant_fallback_fails_scientifically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection(101)
    group = _group([0])
    original = adiabatic.stable_adiabatic_trajectory

    def fallback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        value = original(*args, **kwargs)
        value["relevant_fallback_count"] = 1
        value["endpoint_gate_passed"] = False
        return value

    monkeypatch.setattr(
        diagnostic.adiabatic,
        "stable_adiabatic_trajectory",
        fallback,
    )
    with pytest.raises(
        diagnostic.StableMethodScientificFailure,
        match="adiabatic",
    ):
        diagnostic.reconstruct_stable_mode(
            _result([101], [group]),
            {"tracer": np.full((1, 3), 0.8)},
            selection,
            pressure_mode="unsmoothed",
        )


def test_adiabatic_algebraic_disagreement_is_diagnostic_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _selection(101)
    group = _group([0])
    original = adiabatic.stable_adiabatic_trajectory

    def disagreement(*args: Any, **kwargs: Any) -> dict[str, Any]:
        value = original(*args, **kwargs)
        value["relevant_algebraic_disagreement_count"] = 1
        return value

    monkeypatch.setattr(
        diagnostic.adiabatic,
        "stable_adiabatic_trajectory",
        disagreement,
    )

    _branches, summary, _records = diagnostic.reconstruct_stable_mode(
        _result([101], [group]),
        {"tracer": np.full((1, 3), 0.8)},
        selection,
        pressure_mode="unsmoothed",
    )

    assert summary["stable_adiabatic"][
        "relevant_algebraic_disagreement_count"
    ] == 1
    assert summary["stable_adiabatic"]["gate_passed"] is True


@pytest.mark.parametrize(
    ("result_ids", "group_rows", "message"),
    [
        ([202, 101], [[0, 1]], "IDs"),
        ([101, 202], [[0]], "cover"),
        ([101, 202], [[0], [0]], "overlap"),
    ],
)
def test_ids_and_grouped_coverage_are_exact(
    result_ids: list[int],
    group_rows: list[list[int]],
    message: str,
) -> None:
    selection = _selection(101, 202)
    groups = [_group(rows) for rows in group_rows]
    with pytest.raises(diagnostic.StableMethodDiagnosticError, match=message):
        diagnostic.reconstruct_stable_mode(
            _result(result_ids, groups),
            {"tracer": np.full((2, 3), 0.8)},
            selection,
            pressure_mode="unsmoothed",
        )


@pytest.mark.parametrize("none", [None, np.asarray([1.0, 2.0])])
def test_actual_none_missing_or_wrong_shape_is_a_domain_error(
    none: np.ndarray | None,
) -> None:
    selection = _selection(101)
    result = _result([101], [_group([0])])
    if none is None:
        del result["none"]
    else:
        result["none"] = none
    with pytest.raises(
        diagnostic.StableMethodDiagnosticError,
        match="none.*shape",
    ):
        diagnostic.reconstruct_stable_mode(
            result,
            {"tracer": np.full((1, 3), 0.8)},
            selection,
            pressure_mode="unsmoothed",
        )


def test_actual_none_value_anomalies_are_evidence_bearing_scientific_failures() -> None:
    selection = _selection(101, 202)
    result = _result(
        [101, 202],
        [_group([0, 1])],
        none=np.asarray([
            [np.nan, np.inf],
            [-np.inf, -1.25],
        ]),
    )

    with pytest.raises(
        diagnostic.StableMethodScientificFailure,
        match="actual none",
    ) as caught:
        diagnostic.reconstruct_stable_mode(
            result,
            {"tracer": np.full((2, 3), 0.8)},
            selection,
            pressure_mode="unsmoothed",
        )

    assert caught.value.details["failed_gate"] == "actual_none_finite_nonnegative"
    assert caught.value.details["anomaly_count"] == 4
    assert caught.value.details["actual_none_anomalies"] == [
        {
            "pressure_mode": "unsmoothed",
            "sample_index": 0,
            "cache_row": 10,
            "physical_id": 101,
            "frequency_GHz": 0.15,
            "value_class": "nan",
            "raw_value": "nan",
        },
        {
            "pressure_mode": "unsmoothed",
            "sample_index": 0,
            "cache_row": 10,
            "physical_id": 101,
            "frequency_GHz": 1.4,
            "value_class": "+inf",
            "raw_value": "+inf",
        },
        {
            "pressure_mode": "unsmoothed",
            "sample_index": 1,
            "cache_row": 11,
            "physical_id": 202,
            "frequency_GHz": 0.15,
            "value_class": "-inf",
            "raw_value": "-inf",
        },
        {
            "pressure_mode": "unsmoothed",
            "sample_index": 1,
            "cache_row": 11,
            "physical_id": 202,
            "frequency_GHz": 1.4,
            "value_class": "negative",
            "raw_value": "-1.25",
        },
    ]


def test_comparison_uses_adiabatic_for_radiative_direction_and_none_descriptively() -> None:
    selection = _selection(101, 202)
    full = np.asarray([[2.0, 1.0], [2.0, 1.0]])
    adiabatic_values = full * 1.1
    none = full * 0.8  # Full above none is scientifically allowed.
    mode = {
        "ids": np.asarray([101, 202]),
        "full": full,
        "adiabatic": adiabatic_values,
        "none": none,
    }

    rows, comparison = diagnostic.summarise_stable_comparison(
        selection,
        {"unsmoothed": mode, "log_savgol": mode},
    )

    assert len(rows) == 2
    assert comparison["decision"] == "PASS"
    assert comparison["gate_results"]["radiative_suppression"] is True
    assert comparison["comparison_semantics"]["none_branch_is_upper_bound"] is False
    assert any(
        record["aggregate_direction"] == "full_above_none"
        for record in comparison["full_vs_none_ordering"]["unsmoothed"]
    )

    bad = {**mode, "full": adiabatic_values * 1.01}
    _, failed = diagnostic.summarise_stable_comparison(
        selection,
        {"unsmoothed": bad, "log_savgol": bad},
    )
    assert failed["decision"] == "FAIL"
    assert failed["gate_results"]["radiative_suppression"] is False


@pytest.mark.parametrize(
    ("comparison_decision", "cutoff_count", "expected_decision", "expected_label"),
    [
        ("PASS", 0, "PASS", diagnostic.PASS_LABEL),
        (
            "PASS",
            1,
            "HOLD_FOR_CUTOFF_REVIEW",
            diagnostic.HOLD_LABEL,
        ),
        ("FAIL", 0, "FAIL", diagnostic.FAIL_LABEL),
        ("FAIL", 1, "FAIL", diagnostic.FAIL_LABEL),
    ],
)
def test_tri_state_decision_gives_failed_gates_precedence_over_cutoff_hold(
    comparison_decision: str,
    cutoff_count: int,
    expected_decision: str,
    expected_label: str,
) -> None:
    assert diagnostic.classify_stable_decision(
        comparison_decision,
        cutoff_count=cutoff_count,
    ) == (expected_decision, expected_label)


def _write_minimal_cache(path: Path) -> None:
    with h5py.File(path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=np.asarray([101], dtype=np.int64))
        h5.create_dataset("pressure", data=np.ones((1, 3), dtype=np.float64))
        h5.create_dataset(
            "times",
            data=np.asarray([1.0e13, 2.0e13, 3.0e13], dtype=np.float64),
        )
        h5.attrs["shock_threshold"] = 5.0
        h5.attrs["shock_component"] = 2
        h5.attrs["source_identity_sha256"] = "a" * 64


def _write_selection(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_index",
                "cache_row",
                "physical_id",
                "analysis_weight",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "sample_index": 0,
            "cache_row": 0,
            "physical_id": 101,
            "analysis_weight": 1.0,
        })


def test_exact_selection_rejects_id_and_file_order_mismatch(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    selection_path = tmp_path / "selection.csv"
    _write_minimal_cache(cache)
    _write_selection(selection_path)
    with h5py.File(cache, "r") as h5:
        rows, selection = diagnostic.read_exact_selection(
            selection_path,
            h5,
            expected_count=1,
        )
        np.testing.assert_array_equal(rows, np.asarray([0]))
        assert [row["physical_id"] for row in selection] == [101]

    selection_path.write_text(
        "sample_index,cache_row,physical_id,analysis_weight\n"
        "1,0,101,1\n"
    )
    with h5py.File(cache, "r") as h5:
        with pytest.raises(
            diagnostic.StableMethodDiagnosticError,
            match="sample_index order",
        ):
            diagnostic.read_exact_selection(
                selection_path,
                h5,
                expected_count=1,
            )

    selection_path.write_text(
        "sample_index,cache_row,physical_id,analysis_weight\n"
        "0,0,999,1\n"
    )
    with h5py.File(cache, "r") as h5:
        with pytest.raises(
            diagnostic.StableMethodDiagnosticError,
            match="ID mismatch",
        ):
            diagnostic.read_exact_selection(
                selection_path,
                h5,
                expected_count=1,
            )


def test_orchestration_is_deterministic_and_uses_only_stable_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache.h5"
    selection_path = tmp_path / "selection.csv"
    _write_minimal_cache(cache)
    _write_selection(selection_path)
    physical = {
        "physical_ids": np.asarray([101]),
        "tracer": np.full((1, 3), 0.8),
    }
    group = _group([0])
    calls: list[tuple[str, bool, bool, str]] = []

    monkeypatch.setattr(
        diagnostic.workflow,
        "_validate_completed_cache",
        lambda _h5: {"endpoint_count": 1, "output_count": 3},
    )
    monkeypatch.setattr(
        diagnostic.workflow,
        "build_pressure_treatment_plan",
        lambda _h5, **_kwargs: {
            "identity_sha256": "b" * 64,
            "trim_rows": np.asarray([], dtype=np.int64),
            "excluded_rows": np.asarray([], dtype=np.int64),
            "single_record_rows": np.asarray([], dtype=np.int64),
            "trim_single_record_overlap_rows": np.asarray([], dtype=np.int64),
        },
    )
    monkeypatch.setattr(
        diagnostic.adiabatic,
        "_read_treated_sample",
        lambda _h5, _rows, _plan: {"physical_ids": np.asarray([101])},
    )
    monkeypatch.setattr(
        diagnostic.workflow,
        "convert_code_cache_to_physical",
        lambda _raw, **_kwargs: (
            physical,
            {"pressure_unit": "Pa", "time_unit": "s"},
        ),
    )

    def fake_praise(
        _physical: dict[str, np.ndarray],
        *,
        pressure_mode: str,
        diagnostic: bool,
        include_adiabatic: bool,
        singleton_policy: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        calls.append((
            pressure_mode,
            diagnostic,
            include_adiabatic,
            singleton_policy,
        ))
        value = _result([101], [group])
        value["metadata"]["pressure_mode"] = pressure_mode
        return value

    monkeypatch.setattr(diagnostic, "calculate_praise_pair", fake_praise)
    cache_hash = hashlib.sha256(cache.read_bytes()).hexdigest()
    selection_hash = hashlib.sha256(selection_path.read_bytes()).hexdigest()

    first = diagnostic.diagnose_stable_method_value(
        cache,
        selection_path,
        tmp_path / "first",
        expected_cache_sha256=cache_hash,
        expected_selection_sha256=selection_hash,
        expected_selection_count=1,
    )
    second = diagnostic.diagnose_stable_method_value(
        cache,
        selection_path,
        tmp_path / "second",
        expected_cache_sha256=cache_hash,
        expected_selection_sha256=selection_hash,
        expected_selection_count=1,
    )

    assert first["decision"] == second["decision"] == "PASS"
    assert calls == [
        ("unsmoothed", True, False, "instantaneous_recent_shock"),
        ("log_savgol", True, False, "instantaneous_recent_shock"),
        ("unsmoothed", True, False, "instantaneous_recent_shock"),
        ("log_savgol", True, False, "instantaneous_recent_shock"),
    ]
    expected_names = {
        "stable_method_value_selection.csv",
        "stable_method_value_unsmoothed_branches.npz",
        "stable_method_value_log_savgol_branches.npz",
        "stable_method_value_particle_comparison.csv",
        "stable_method_value_ordering.csv",
        "stable_method_value_cutoff_records.csv",
        "stable_method_value_gate_summary.csv",
        "stable_method_value_summary.json",
    }
    assert {path.name for path in (tmp_path / "first").iterdir()} == expected_names
    for name in expected_names:
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes()
    assert (
        tmp_path / "first" / "stable_method_value_selection.csv"
    ).read_bytes() == selection_path.read_bytes()
    summary = json.loads(
        (tmp_path / "first" / "stable_method_value_summary.json").read_text()
    )
    assert summary["selection_sha256"] == selection_hash
    assert summary["cache_sha256"] == cache_hash
    assert summary["comparison"]["comparison_semantics"][
        "none_branch_is_upper_bound"
    ] is False
    assert summary["branch_output_fingerprint_sha256"] == first[
        "branch_output_fingerprint_sha256"
    ]
    assert summary["infrastructure_gates"]
    assert summary["stable_gates"]
    assert all(
        isinstance(value, bool)
        for value in summary["infrastructure_gates"].values()
    )
    assert all(
        isinstance(value, bool)
        for value in summary["stable_gates"].values()
    )
    assert all(summary["infrastructure_gates"].values())
    assert all(summary["stable_gates"].values())


def test_actual_none_anomaly_is_archived_and_main_returns_scientific_exit_three(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache.h5"
    selection_path = tmp_path / "selection.csv"
    output_dir = tmp_path / "scientific-fail"
    _write_minimal_cache(cache)
    _write_selection(selection_path)
    group = _group([0])
    physical = {
        "physical_ids": np.asarray([101]),
        "tracer": np.full((1, 3), 0.8),
    }
    original_selection_reader = diagnostic.read_exact_selection

    monkeypatch.setattr(
        diagnostic.workflow,
        "_validate_completed_cache",
        lambda _h5: {"endpoint_count": 1, "output_count": 3},
    )
    monkeypatch.setattr(
        diagnostic.workflow,
        "build_pressure_treatment_plan",
        lambda _h5, **_kwargs: {
            "identity_sha256": "b" * 64,
            "trim_rows": np.asarray([], dtype=np.int64),
            "excluded_rows": np.asarray([], dtype=np.int64),
            "single_record_rows": np.asarray([], dtype=np.int64),
            "trim_single_record_overlap_rows": np.asarray([], dtype=np.int64),
        },
    )
    monkeypatch.setattr(
        diagnostic,
        "read_exact_selection",
        lambda path, h5, **_kwargs: original_selection_reader(
            path,
            h5,
            expected_count=1,
        ),
    )
    monkeypatch.setattr(
        diagnostic.adiabatic,
        "_read_treated_sample",
        lambda _h5, _rows, _plan: {"physical_ids": np.asarray([101])},
    )
    monkeypatch.setattr(
        diagnostic.workflow,
        "convert_code_cache_to_physical",
        lambda _raw, **_kwargs: (
            physical,
            {"pressure_unit": "Pa", "time_unit": "s"},
        ),
    )
    monkeypatch.setattr(
        diagnostic,
        "calculate_praise_pair",
        lambda *_args, **_kwargs: _result(
            [101],
            [group],
            none=np.asarray([[np.nan, 1.0e-38]]),
        ),
    )

    assert diagnostic.main([
        "--cache",
        str(cache),
        "--selection-csv",
        str(selection_path),
        "--output-dir",
        str(output_dir),
    ]) == 3

    assert {path.name for path in output_dir.iterdir()} == {
        diagnostic.SELECTION_NAME,
        diagnostic.CUTOFF_NAME,
        diagnostic.GATE_NAME,
        diagnostic.SUMMARY_NAME,
    }
    summary = json.loads((output_dir / diagnostic.SUMMARY_NAME).read_text())
    assert summary["decision"] == "FAIL"
    assert summary["stable_gates"] == {
        "actual_none_finite_nonnegative": False,
    }
    assert all(
        isinstance(value, bool)
        for value in summary["infrastructure_gates"].values()
    )
    assert summary["scientific_failure"]["details"][
        "actual_none_anomalies"
    ] == [{
        "pressure_mode": "unsmoothed",
        "sample_index": 0,
        "cache_row": 0,
        "physical_id": 101,
        "frequency_GHz": 0.15,
        "value_class": "nan",
        "raw_value": "nan",
    }]
    with (output_dir / diagnostic.GATE_NAME).open(newline="") as handle:
        gate_rows = list(csv.DictReader(handle))
    assert gate_rows == [{
        "scope": "scientific_reconstruction",
        "gate": "actual_none_finite_nonnegative",
        "passed": "False",
        "value": "actual none branch contains non-finite or negative values",
    }]
    with (output_dir / diagnostic.CUTOFF_NAME).open(newline="") as handle:
        assert list(csv.DictReader(handle)) == []


def test_scientific_failure_summary_has_wrapper_compatible_gate_mappings(
    tmp_path: Path,
) -> None:
    result = diagnostic._write_scientific_failure(
        tmp_path,
        {
            "infrastructure_gates": {
                "immutable_inputs": True,
                "completed_cache": True,
            },
        },
        diagnostic.StableMethodScientificFailure("subrelativistic state"),
    )
    summary = json.loads((tmp_path / diagnostic.SUMMARY_NAME).read_text())

    assert result["decision"] == summary["decision"] == "FAIL"
    assert summary["infrastructure_gates"] == {
        "completed_cache": True,
        "immutable_inputs": True,
    }
    assert summary["stable_gates"] == {
        "stable_branch_reconstruction": False,
    }
    assert all(
        isinstance(value, bool)
        for mapping in (
            summary["infrastructure_gates"],
            summary["stable_gates"],
        )
        for value in mapping.values()
    )


def test_hash_mismatch_and_nonempty_output_fail_before_calculation(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache.h5"
    selection_path = tmp_path / "selection.csv"
    _write_minimal_cache(cache)
    _write_selection(selection_path)
    with pytest.raises(
        diagnostic.StableMethodDiagnosticError,
        match="cache SHA-256",
    ):
        diagnostic.diagnose_stable_method_value(
            cache,
            selection_path,
            tmp_path / "hash-fail",
            expected_cache_sha256="0" * 64,
            expected_selection_count=1,
        )

    with pytest.raises(
        diagnostic.StableMethodDiagnosticError,
        match="selection SHA-256",
    ):
        diagnostic.diagnose_stable_method_value(
            cache,
            selection_path,
            tmp_path / "selection-hash-fail",
            expected_selection_sha256="0" * 64,
            expected_selection_count=1,
        )

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("do not overwrite\n")
    with pytest.raises(
        diagnostic.StableMethodDiagnosticError,
        match="non-empty",
    ):
        diagnostic.diagnose_stable_method_value(
            cache,
            selection_path,
            occupied,
            expected_selection_count=1,
        )


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        ("PASS", 0),
        ("HOLD_FOR_CUTOFF_REVIEW", 3),
        ("FAIL", 3),
    ],
)
def test_main_maps_scientific_decisions_to_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    expected: int,
) -> None:
    monkeypatch.setattr(
        diagnostic,
        "diagnose_stable_method_value",
        lambda *_args, **_kwargs: {"decision": decision},
    )
    assert diagnostic.main([
        "--cache",
        str(tmp_path / "cache.h5"),
        "--selection-csv",
        str(tmp_path / "selection.csv"),
        "--output-dir",
        str(tmp_path / "out"),
    ]) == expected


def test_main_maps_domain_errors_to_exit_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise diagnostic.StableMethodDiagnosticError("bad domain")

    monkeypatch.setattr(diagnostic, "diagnose_stable_method_value", fail)
    assert diagnostic.main([
        "--cache",
        str(tmp_path / "cache.h5"),
        "--selection-csv",
        str(tmp_path / "selection.csv"),
        "--output-dir",
        str(tmp_path / "out"),
    ]) == 2
