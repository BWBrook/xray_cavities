from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_critical_stratum_census as diagnostic
from scripts.science import diagnose_g_lo_pressure_method_value as pressure_method


TARGET = (
    "affected=1|trim=0|length_q=1|injection_q=1|range_q=1|"
    "shock=post_injection_recent"
)


def _features() -> dict[str, np.ndarray]:
    count = 8
    return {
        "physical_id": np.arange(100, 100 + count, dtype=np.int64),
        "active": np.ones(count, dtype=bool),
        "trim": np.zeros(count, dtype=bool),
        "history_length": np.full(count, 8, dtype=np.int32),
        "injection_age": np.full(count, 10.0),
        "dynamic_range": np.full(count, 1.0),
        "shock_age": np.full(count, 1.0),
        "short": np.zeros(count, dtype=bool),
        "affected": np.ones(count, dtype=bool),
        "log_endpoint": np.arange(count, dtype=float),
        "min_log_ratio": np.arange(1, count + 1, dtype=float),
    }


def test_stratum_census_is_exact_sorted_and_unit_weighted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pressure_method,
        "_feature_table",
        lambda *_args, **_kwargs: _features(),
    )

    rows, records, metadata = pressure_method.construct_stratum_census(
        object(),
        {},
        {},
        target_stratum=TARGET,
        expected_count=8,
        expected_certainty_count=2,
        expected_ordinary_count=6,
        extreme_count_per_tail=1,
    )

    np.testing.assert_array_equal(rows, np.arange(8))
    assert [record["sample_index"] for record in records] == list(range(8))
    assert [record["physical_id"] for record in records] == list(range(100, 108))
    assert all(record["stratum"] == TARGET for record in records)
    assert all(record["inclusion_probability"] == 1.0 for record in records)
    assert all(record["analysis_weight"] == 1.0 for record in records)
    assert all(
        "critical_stratum_census" in record["selection_reason"]
        for record in records
    )
    assert metadata["census_count"] == 8
    assert metadata["certainty_count"] == 2
    assert metadata["ordinary_count"] == 6
    assert metadata["scope"] == "exact census of the declared stratum"


def test_hybrid_replacement_preserves_population_mass() -> None:
    original = [
        {
            "physical_id": 1,
            "stratum": "outside",
            "analysis_weight": 10.0,
        },
        {
            "physical_id": 2,
            "stratum": "target",
            "analysis_weight": 2.0,
        },
        {
            "physical_id": 3,
            "stratum": "target",
            "analysis_weight": 2.0,
        },
    ]
    census = [
        {"physical_id": value, "stratum": "target", "analysis_weight": 1.0}
        for value in (20, 21, 22, 23)
    ]

    hybrid, audit = diagnostic.replace_stratum_with_census(
        original,
        census,
        target_stratum="target",
    )

    assert [row["physical_id"] for row in hybrid] == [1, 20, 21, 22, 23]
    assert audit["original_total_represented_weight"] == 14.0
    assert audit["original_target_represented_weight"] == 4.0
    assert audit["census_target_represented_weight"] == 4.0
    assert audit["hybrid_total_represented_weight"] == 14.0


@pytest.mark.parametrize(
    ("hybrid_fraction", "census_fraction", "expected"),
    [
        (0.40, 0.90, "CENSUS_RESOLVES_SAMPLE_LEVERAGE"),
        (0.80, 0.40, "CENSUS_SUPPORTS_LOCALIZED_REGIME"),
        (0.80, 0.90, "CENSUS_FINDS_RARE_HISTORY_SENSITIVITY"),
        (0.50, 0.90, "CENSUS_RESOLVES_SAMPLE_LEVERAGE"),
        (0.80, 0.50, "CENSUS_SUPPORTS_LOCALIZED_REGIME"),
        (0.50, 0.50, "CENSUS_RESOLVES_SAMPLE_LEVERAGE"),
    ],
)
def test_census_outcome_uses_predeclared_concentration_gate(
    hybrid_fraction: float,
    census_fraction: float,
    expected: str,
) -> None:
    assert diagnostic.classify_census_outcome(
        hybrid_top_fraction=hybrid_fraction,
        census_top_fraction=census_fraction,
        cutoff_count=0,
        scientific_gates_passed=True,
        provenance_passed=True,
    ) == expected


def test_census_outcome_fails_closed_for_cutoff_or_invalid_evidence() -> None:
    assert diagnostic.classify_census_outcome(
        hybrid_top_fraction=0.2,
        census_top_fraction=0.2,
        cutoff_count=1,
        scientific_gates_passed=True,
        provenance_passed=True,
    ) == "HOLD_FOR_CUTOFF_REVIEW"
    assert diagnostic.classify_census_outcome(
        hybrid_top_fraction=0.2,
        census_top_fraction=0.2,
        cutoff_count=0,
        scientific_gates_passed=False,
        provenance_passed=True,
    ) == "FAIL_NUMERICAL_OR_PROVENANCE"


def test_original_selection_and_comparison_identity_is_exact() -> None:
    selection = [
        {"sample_index": 0, "cache_row": 4, "physical_id": 10},
        {"sample_index": 1, "cache_row": 8, "physical_id": 11},
    ]
    comparison = [dict(row) for row in selection]
    result = diagnostic._validate_original_row_identity(selection, comparison)
    assert result["row_count"] == 2
    comparison[1]["physical_id"] = 99
    with pytest.raises(
        diagnostic.CriticalStratumCensusError,
        match="identity mismatch",
    ):
        diagnostic._validate_original_row_identity(selection, comparison)


def test_stable_failure_is_propagated_with_partial_evidence(tmp_path: Path) -> None:
    core = tmp_path / "core"
    output = tmp_path / "output"
    core.mkdir()
    output.mkdir()
    (core / diagnostic.stable_method.SUMMARY_NAME).write_text(json.dumps({
        "status": "diagnostic_complete",
        "decision": "FAIL",
        "decision_label": "G_LO_STABLE_METHOD_VALUE_FAIL",
        "cutoff_count": 0,
        "scientific_failure": {
            "details": {"failed_gate": "stable_branch_reconstruction"},
        },
    }))
    (core / diagnostic.stable_method.CUTOFF_NAME).write_text(
        "pressure_mode,classification\n"
    )
    (core / diagnostic.stable_method.GATE_NAME).write_text(
        "scope,gate,passed,value\nscientific_reconstruction,stable_branch_reconstruction,False,failed\n"
    )
    result = diagnostic._propagate_stable_failure(
        core,
        output,
        selection_hash="a" * 64,
        observed_hashes={"cache": "b" * 64},
        cache_validation={"status": "passed"},
        pressure_treatment_identity_sha256="c" * 64,
        census_selection=[{"selection_reason": "ordinary"}],
        census_metadata={"census_count": 1},
        oracle_metadata={"oracle_count": 0},
        target_stratum=TARGET,
        expected_oracle_count=0,
        expected_certainty_count=0,
        expected_ordinary_count=1,
    )
    summary = json.loads((output / diagnostic.SUMMARY_NAME).read_text())
    assert result["decision"] == summary["decision"] == "FAIL_NUMERICAL_OR_PROVENANCE"
    assert (output / diagnostic.CUTOFF_NAME).is_file()
    assert (output / diagnostic.GATE_NAME).is_file()
    assert not (output / diagnostic.PARTICLE_NAME).exists()
    assert summary["stable_core_failure_evidence"]["failed_gate"] == "stable_branch_reconstruction"
