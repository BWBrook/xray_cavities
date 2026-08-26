from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest
from astropy import units as u

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import run_g_lo_radio_history_value as workflow


def test_primary_contract_is_explicitly_unsmoothed_and_blocks_linear_sg() -> None:
    assert workflow.PRIMARY_CONTRACT["pressure_mode"] == {
        "name": "unsmoothed",
        "transform": "identity",
        "smoothing": False,
        "linear_savgol_available": False,
    }
    assert "pressure_smoothing" not in workflow.PRIMARY_CONTRACT


def _write_cache(path: Path) -> None:
    ids = np.array([901, 17, 404, 33, 1201], dtype=np.int64)
    with h5py.File(path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=ids)
        h5.create_dataset("times", data=np.array([1.0, 2.0, 3.0]))
        h5.create_dataset("output_indices", data=np.array([0, 1, 2], dtype=np.int64))
        h5.create_dataset("pressure", data=np.arange(15, dtype=np.float64).reshape(5, 3) + 1.0)
        h5.create_dataset("density", data=np.ones((5, 3), dtype=np.float64) * 2.0)
        h5.create_dataset("tracer", data=np.ones((5, 3), dtype=np.float64) * 0.8)
        h5.create_dataset("last_shock_time", data=np.ones((5, 3), dtype=np.float64) * 0.5)
        h5.create_dataset("position", data=np.arange(15, dtype=np.float64).reshape(5, 3))
        h5.create_dataset("velocity", data=np.ones((5, 3), dtype=np.float64) * 1.0e-3)
        h5.create_dataset("tinj", data=np.zeros(5, dtype=np.float64))
        h5.create_dataset("presence", data=np.ones((5, 3), dtype=bool))
        h5.attrs["next_output"] = 3
        h5.attrs["shock_threshold"] = 5.0
        h5.attrs["shock_component"] = 2
        h5.attrs["source_identity_sha256"] = "a" * 64


def _write_treatment_cache(path: Path) -> None:
    ids = np.array([901, 17, 404, 33, 1201], dtype=np.int64)
    presence = np.array([
        [True, True, True, True],
        [True, True, True, True],
        [False, True, True, True],
        [False, True, True, True],
        [True, True, True, True],
    ])
    pressure = np.array([
        [1.0, 2.0, 3.0, 4.0],
        [0.0, 2.0, 3.0, 4.0],
        [np.nan, 0.0, 2.0, 3.0],
        [np.nan, 0.0, 0.0, 0.0],
        [1.0, 2.0, 3.0, 4.0],
    ])
    density = np.where(presence, 2.0, np.nan)
    tracer = np.where(presence, 0.8, np.nan)
    density[1, 0] = tracer[1, 0] = 0.0
    density[2, 1] = tracer[2, 1] = 0.0
    density[3, 1:] = tracer[3, 1:] = 0.0
    last = np.where(presence, np.arange(4)[None, :] * 0.5, np.nan)
    with h5py.File(path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=ids)
        h5.create_dataset("times", data=np.arange(4, dtype=float))
        h5.create_dataset("output_indices", data=np.arange(4, dtype=np.int64))
        h5.create_dataset("pressure", data=pressure)
        h5.create_dataset("density", data=density)
        h5.create_dataset("tracer", data=tracer)
        h5.create_dataset("last_shock_time", data=last)
        h5.create_dataset("position", data=np.arange(15, dtype=float).reshape(5, 3))
        h5.create_dataset("velocity", data=np.ones((5, 3)) * 1.0e-3)
        h5.create_dataset("tinj", data=np.array([-0.1, -0.1, 0.9, 0.9, -0.1]))
        h5.create_dataset("presence", data=presence)
        h5.attrs["next_output"] = 4
        h5.attrs["shock_threshold"] = 5.0
        h5.attrs["shock_component"] = 2
        h5.attrs["source_identity_sha256"] = "b" * 64


def test_code_to_physical_units_preserves_ids_and_float64() -> None:
    raw = {
        "physical_ids": np.array([901, 17], dtype=np.int64),
        "time": np.array([1.0, 2.0]),
        "pressure": np.ones((2, 2)),
        "density": np.ones((2, 2)),
        "tracer": np.ones((2, 2)) * 0.8,
        "last_shock_time": np.ones((2, 2)) * 0.5,
        "position": np.ones((2, 3)) * 2.0,
        "velocity": np.ones((2, 3)) * 0.01,
    }

    converted, provenance = workflow.convert_code_cache_to_physical(
        raw,
        shock_threshold=5.0,
        shock_component=2,
    )

    expected_density = (0.60364 * u.u / u.cm**3).to_value(u.kg / u.m**3)
    expected_pressure = expected_density * workflow.SPEED_OF_LIGHT_M_S**2
    expected_time = workflow.KPC_TO_M / workflow.SPEED_OF_LIGHT_M_S
    assert converted["physical_ids"].tolist() == [901, 17]
    assert converted["physical_ids"].dtype == np.dtype("int64")
    assert converted["time"].dtype == np.dtype("float64")
    assert converted["time"][0] == pytest.approx(expected_time)
    assert converted["density"][0, 0] == pytest.approx(expected_density)
    assert converted["pressure"][0, 0] == pytest.approx(expected_pressure)
    np.testing.assert_allclose(converted["position"], 2.0)
    np.testing.assert_allclose(converted["velocity"], 0.01)
    assert provenance["length_unit"] == "1 kpc"
    assert provenance["speed_unit"] == "c"
    assert provenance["density_unit"] == "0.60364 u cm^-3"
    assert provenance["pressure_unit"] == "density_unit * c^2"
    assert provenance["shock_threshold"] == 5.0
    assert provenance["shock_component"] == 2
    assert provenance["shock_component_semantics"] == "selected by g_lo_particle_history from PLUTO shk_thresh"


def test_code_to_physical_units_fails_closed_on_shock_or_beta() -> None:
    raw = {
        "physical_ids": np.array([1]),
        "time": np.array([1.0, 2.0]),
        "pressure": np.ones((1, 2)),
        "density": np.ones((1, 2)),
        "tracer": np.ones((1, 2)),
        "last_shock_time": np.ones((1, 2)),
        "position": np.zeros((1, 3)),
        "velocity": np.array([[1.0, 0.0, 0.0]]),
    }
    with pytest.raises(workflow.WorkflowError, match="shk_thresh=5"):
        workflow.convert_code_cache_to_physical(raw, shock_threshold=0.5, shock_component=1)
    with pytest.raises(workflow.WorkflowError, match="beta"):
        workflow.convert_code_cache_to_physical(raw, shock_threshold=5.0, shock_component=2)


def test_atomic_checkpoint_identity_detects_output_mutation(tmp_path: Path) -> None:
    output = tmp_path / "audit.json"
    output.write_text('{"passed": true}\n')
    marker = tmp_path / ".checkpoints" / "audit.json"
    workflow.write_stage_checkpoint(
        marker,
        stage="audit",
        input_contract={"source": "synthetic", "count": 3},
        outputs=[output],
    )
    assert workflow.validate_stage_checkpoint(
        marker,
        stage="audit",
        input_contract={"source": "synthetic", "count": 3},
    )["reused"] is True
    assert not list(marker.parent.glob("*.tmp"))

    output.write_text('{"passed": false}\n')
    with pytest.raises(workflow.WorkflowError, match="hash"):
        workflow.validate_stage_checkpoint(
            marker,
            stage="audit",
            input_contract={"source": "synthetic", "count": 3},
        )


def test_emissivity_chunks_resume_and_preserve_physical_id_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "history.h5"
    _write_cache(cache)
    calls: list[list[int]] = []

    def fake_praise(chunk, **kwargs):
        ids = np.asarray(chunk["physical_ids"])
        calls.append(ids.tolist())
        values = np.column_stack((ids, ids + 0.5)).astype(float)
        return {
            "ids": ids,
            "full": values * (u.W / (u.Hz * u.m**3 * u.sr)),
            "none": (values + 1.0) * (u.W / (u.Hz * u.m**3 * u.sr)),
            "metadata": {
                "actual_function": "fake.actual.praise",
                "single_record_instantaneous_count": 0,
                "single_record_instantaneous_ids": [],
            },
        }

    monkeypatch.setattr(workflow, "calculate_praise_pair", fake_praise)
    first = workflow.run_emissivity_stage(
        cache,
        tmp_path / "work",
        id_chunk_size=2,
        expected_trim_rows=0,
        expected_no_positive_rows=0,
        expected_single_record_rows=0,
    )
    assert calls == [[901, 17], [404, 33], [1201]]
    with np.load(first["emissivity_path"]) as data:
        assert data["physical_ids"].tolist() == [901, 17, 404, 33, 1201]
        assert data["full"][:, 0].tolist() == [901, 17, 404, 33, 1201]
        assert data["primary_active_mask"].tolist() == [True] * 5
        assert data["conservative_active_mask"].tolist() == [True] * 5
    treatment = json.loads(Path(first["pressure_treatment_path"]).read_text())
    assert treatment["trim_row_count"] == 0
    assert treatment["excluded_no_positive_row_count"] == 0
    assert treatment["source_exact_match"] == "not claimed; external wrapper preflight required"

    monkeypatch.setattr(
        workflow,
        "calculate_praise_pair",
        lambda *_args, **_kwargs: pytest.fail("completed chunks must be reused"),
    )
    second = workflow.run_emissivity_stage(
        cache,
        tmp_path / "work",
        id_chunk_size=2,
        expected_trim_rows=0,
        expected_no_positive_rows=0,
        expected_single_record_rows=0,
    )
    assert second["restart_identity_sha256"] == first["restart_identity_sha256"]
    assert second["reused_chunks"] == 3


def test_pressure_treatment_gate_and_two_row_exclusion(tmp_path: Path) -> None:
    cache = tmp_path / "treatment.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=2,
            expected_no_positive_rows=1,
            expected_single_record_rows=0,
            row_chunk=2,
        )
        assert plan["trim_rows"].tolist() == [1, 2]
        assert plan["excluded_rows"].tolist() == [3]
        assert plan["active_mask"].tolist() == [True, True, True, False, True]
        assert plan["trim_affected_active_mask"].tolist() == [False, True, True, False]
        assert plan["conservative_active_mask"].tolist() == [True, False, False, False, True]
        exceptional = plan["records"]
        assert [row["endpoint_id"] for row in exceptional] == [17, 404, 33]
        excluded = exceptional[-1]
        assert excluded["reason"] == "no_positive_pressure"
        assert excluded["effective_start_column"] is None
        assert excluded["tinj"] == pytest.approx(0.9)

        raw = workflow._raw_cache_chunk(h5, 0, 5)
        treated, metadata = workflow.apply_pressure_treatment(
            raw,
            row_offset=0,
            plan=plan,
        )
    assert treated["physical_ids"].tolist() == [901, 17, 404, 1201]
    assert np.isnan(treated["pressure"][1, 0])
    assert np.isnan(treated["density"][1, 0])
    assert np.isnan(treated["tracer"][1, 0])
    assert np.isnan(treated["last_shock_time"][1, 0])
    assert np.isnan(treated["pressure"][2, 1])
    assert treated["tinj"].tolist() == [-0.1, -0.1, 0.9, -0.1]
    assert metadata["active_cache_rows"] == [0, 1, 2, 4]
    assert metadata["trim_affected"] == [False, True, True, False]


def test_emissivity_stage_applies_trim_and_exclusion_before_praise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "treatment.h5"
    _write_treatment_cache(cache)
    calls: list[dict[str, object]] = []

    def fake_praise(chunk, **kwargs):
        calls.append({
            "chunk": {key: np.asarray(value).copy() for key, value in chunk.items()},
            "kwargs": dict(kwargs),
        })
        ids = np.asarray(chunk["physical_ids"])
        values = np.ones((len(ids), 2), dtype=float)
        return {
            "ids": ids,
            "full": values * (u.W / (u.Hz * u.m**3 * u.sr)),
            "none": values * 2 * (u.W / (u.Hz * u.m**3 * u.sr)),
            "metadata": {
                "single_record_instantaneous_count": 0,
                "single_record_instantaneous_ids": [],
            },
        }

    monkeypatch.setattr(workflow, "calculate_praise_pair", fake_praise)
    result = workflow.run_emissivity_stage(
        cache,
        tmp_path / "work",
        id_chunk_size=5,
        expected_trim_rows=2,
        expected_no_positive_rows=1,
        expected_single_record_rows=0,
    )
    assert len(calls) == 1
    chunk = calls[0]["chunk"]
    assert isinstance(chunk, dict)
    assert chunk["physical_ids"].tolist() == [901, 17, 404, 1201]
    assert np.isnan(chunk["pressure"][1, 0])
    assert np.isnan(chunk["pressure"][2, 1])
    np.testing.assert_allclose(
        chunk["tinj"] / workflow.TIME_UNIT_S,
        [-0.1, -0.1, 0.9, -0.1],
    )
    assert calls[0]["kwargs"]["pressure_mode"] == "unsmoothed"
    assert calls[0]["kwargs"]["singleton_policy"] == "instantaneous_recent_shock"
    with np.load(result["emissivity_path"]) as data:
        assert data["physical_ids"].tolist() == [901, 17, 404, 1201]
        assert data["cache_row_indices"].tolist() == [0, 1, 2, 4]
        assert data["trim_affected"].tolist() == [False, True, True, False]
        assert data["instantaneous_history"].tolist() == [False, False, False, False]
        assert data["primary_active_mask"].tolist() == [True, True, True, False, True]
        assert data["conservative_active_mask"].tolist() == [True, False, False, False, True]


def test_emissivity_stage_carries_singleton_provenance_and_comparator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "singleton_treatment.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r+") as h5:
        h5["presence"][2, :] = [False, False, True, True]
        h5["pressure"][2, :] = [np.nan, np.nan, 0.0, 3.0]
        h5["density"][2, :] = [np.nan, np.nan, 0.0, 2.0]
        h5["tracer"][2, :] = [np.nan, np.nan, 0.0, 0.8]
        h5["last_shock_time"][2, :] = [np.nan, np.nan, 2.0, 3.0]
        h5["tinj"][2] = 1.9
        h5["presence"][4, :] = [False, False, False, True]
        h5["pressure"][4, :] = [np.nan, np.nan, np.nan, 4.0]
        h5["density"][4, :] = [np.nan, np.nan, np.nan, 2.0]
        h5["tracer"][4, :] = [np.nan, np.nan, np.nan, 0.8]
        h5["last_shock_time"][4, :] = [np.nan, np.nan, np.nan, 3.0]
        h5["tinj"][4] = 2.9

    calls: list[dict[str, object]] = []

    def fake_praise(chunk, **kwargs):
        calls.append({"ids": np.asarray(chunk["physical_ids"]).copy(), **kwargs})
        values = np.ones((len(chunk["physical_ids"]), 2), dtype=float)
        return {
            "ids": np.asarray(chunk["physical_ids"]),
            "full": values * (u.W / (u.Hz * u.m**3 * u.sr)),
            "none": values * (u.W / (u.Hz * u.m**3 * u.sr)),
            "metadata": {
                "single_record_instantaneous_count": 2,
                "single_record_instantaneous_ids": [404, 1201],
            },
        }

    monkeypatch.setattr(workflow, "calculate_praise_pair", fake_praise)
    result = workflow.run_emissivity_stage(
        cache,
        tmp_path / "work",
        id_chunk_size=5,
        expected_trim_rows=2,
        expected_no_positive_rows=1,
        expected_single_record_rows=2,
        expected_trim_single_record_overlap_rows=1,
    )
    assert calls[0]["singleton_policy"] == "instantaneous_recent_shock"
    with np.load(result["emissivity_path"]) as data:
        assert data["physical_ids"].tolist() == [901, 17, 404, 1201]
        assert data["instantaneous_history"].tolist() == [False, False, True, True]
        assert data["conservative_active_mask"].tolist() == [
            True, False, False, False, False
        ]
    assert result["single_record_instantaneous_count"] == 2


@pytest.mark.parametrize(
    ("field", "row", "column", "value", "message"),
    [
        ("pressure", 0, 2, -1.0, "negative"),
        ("pressure", 0, 2, 0.0, "internal"),
        ("pressure", 0, 2, np.nan, "non-finite"),
        ("density", 1, 0, 1.0, "joint"),
        ("tracer", 1, 0, 0.1, "joint"),
        ("last_shock_time", 1, 0, 2.0, "future"),
    ],
)
def test_pressure_treatment_gate_rejects_prohibited_patterns(
    tmp_path: Path,
    field: str,
    row: int,
    column: int,
    value: float,
    message: str,
) -> None:
    cache = tmp_path / f"{field}.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r+") as h5:
        h5[field][row, column] = value
    with h5py.File(cache, "r") as h5:
        with pytest.raises(workflow.WorkflowError, match=message):
            workflow.build_pressure_treatment_plan(
                h5,
                expected_trim_rows=2,
                expected_no_positive_rows=1,
                expected_single_record_rows=0,
                row_chunk=2,
            )


def test_pressure_treatment_gate_rejects_wrong_aggregate_and_late_tinj(tmp_path: Path) -> None:
    cache = tmp_path / "wrong.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r") as h5:
        with pytest.raises(workflow.WorkflowError, match="aggregate"):
            workflow.build_pressure_treatment_plan(
                h5,
                expected_trim_rows=10_030,
                expected_no_positive_rows=2,
                expected_single_record_rows=0,
            )
    with h5py.File(cache, "r+") as h5:
        h5["tinj"][1] = 1.5
    with h5py.File(cache, "r") as h5:
        with pytest.raises(workflow.WorkflowError, match="tinj"):
            workflow.build_pressure_treatment_plan(
                h5,
                expected_trim_rows=2,
                expected_no_positive_rows=1,
                expected_single_record_rows=0,
            )


def test_pressure_treatment_accepts_case_specific_aggregate_counts(tmp_path: Path) -> None:
    cache = tmp_path / "case_specific.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=99,
            expected_no_positive_rows=99,
            expected_single_record_rows=99,
            enforce_expected_counts=False,
        )

    assert plan["trim_rows"].tolist() == [1, 2]
    assert plan["excluded_rows"].tolist() == [3]
    assert plan["contract"]["expected_trim_rows"] is None
    assert plan["contract"]["expected_no_positive_rows"] is None
    assert plan["contract"]["expected_single_record_rows"] is None
    assert (
        plan["contract"]["aggregate_count_gate"]
        == "case_specific_counts_recorded_after_structural_validation"
    )


def test_pressure_treatment_excludes_exactly_two_no_positive_rows(tmp_path: Path) -> None:
    cache = tmp_path / "two_excluded.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r+") as h5:
        h5["pressure"][4, :] = 0.0
        h5["density"][4, :] = 0.0
        h5["tracer"][4, :] = 0.0
    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=2,
            expected_no_positive_rows=2,
            expected_single_record_rows=0,
        )
    assert plan["excluded_rows"].tolist() == [3, 4]
    excluded = [row for row in plan["records"] if row["reason"] == "no_positive_pressure"]
    assert [row["endpoint_id"] for row in excluded] == [33, 1201]
    assert all(row["effective_start_time"] is None for row in excluded)


def test_pressure_treatment_excludes_one_record_endpoint_history(tmp_path: Path) -> None:
    cache = tmp_path / "endpoint_no_positive.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r+") as h5:
        h5["presence"][4, :] = [False, False, False, True]
        h5["pressure"][4, :] = [np.nan, np.nan, np.nan, 0.0]
        h5["density"][4, :] = [np.nan, np.nan, np.nan, 0.0]
        h5["tracer"][4, :] = [np.nan, np.nan, np.nan, 0.0]
        h5["last_shock_time"][4, :] = [np.nan, np.nan, np.nan, 3.0]
        h5["tinj"][4] = 2.9
    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=2,
            expected_no_positive_rows=2,
            expected_single_record_rows=0,
        )
    assert plan["trim_rows"].tolist() == [1, 2]
    assert plan["excluded_rows"].tolist() == [3, 4]
    endpoint = plan["records"][-1]
    assert endpoint["endpoint_id"] == 1201
    assert endpoint["reason"] == "no_positive_pressure"
    assert endpoint["first_present_column"] == 3
    assert endpoint["present_count"] == 1
    assert endpoint["effective_start_column"] is None


def test_pressure_treatment_marks_positive_one_record_history_as_instantaneous(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "endpoint_positive_only.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r+") as h5:
        h5["presence"][4, :] = [False, False, False, True]
        h5["pressure"][4, :] = [np.nan, np.nan, np.nan, 4.0]
        h5["density"][4, :] = [np.nan, np.nan, np.nan, 2.0]
        h5["tracer"][4, :] = [np.nan, np.nan, np.nan, 0.8]
        h5["last_shock_time"][4, :] = [np.nan, np.nan, np.nan, 3.0]
        h5["tinj"][4] = 2.9
    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=2,
            expected_no_positive_rows=1,
            expected_single_record_rows=1,
        )
        raw = workflow._raw_cache_chunk(h5, 0, 5)
        treated, metadata = workflow.apply_pressure_treatment(
            raw,
            row_offset=0,
            plan=plan,
        )
    assert plan["single_record_rows"].tolist() == [4]
    assert plan["excluded_rows"].tolist() == [3]
    assert plan["active_mask"].tolist() == [True, True, True, False, True]
    assert plan["conservative_active_mask"].tolist() == [True, False, False, False, False]
    instantaneous = plan["records"][-1]
    assert instantaneous["endpoint_id"] == 1201
    assert instantaneous["reason"] == "single_record_instantaneous_convention"
    assert instantaneous["present_count"] == 1
    assert instantaneous["minimum_history_records"] == 2
    assert treated["physical_ids"].tolist() == [901, 17, 404, 1201]
    assert metadata["instantaneous_history"] == [False, False, False, True]


def test_effective_singleton_mask_includes_trimmed_to_one_record_history(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "effective_singleton_treatment.h5"
    _write_treatment_cache(cache)
    with h5py.File(cache, "r+") as h5:
        # Row 2 has one joint-zero initialization record followed by one
        # positive endpoint record. Row 4 is already a one-record history.
        h5["presence"][2, :] = [False, False, True, True]
        h5["pressure"][2, :] = [np.nan, np.nan, 0.0, 3.0]
        h5["density"][2, :] = [np.nan, np.nan, 0.0, 2.0]
        h5["tracer"][2, :] = [np.nan, np.nan, 0.0, 0.8]
        h5["last_shock_time"][2, :] = [np.nan, np.nan, 2.0, 3.0]
        h5["tinj"][2] = 1.9
        h5["presence"][4, :] = [False, False, False, True]
        h5["pressure"][4, :] = [np.nan, np.nan, np.nan, 4.0]
        h5["density"][4, :] = [np.nan, np.nan, np.nan, 2.0]
        h5["tracer"][4, :] = [np.nan, np.nan, np.nan, 0.8]
        h5["last_shock_time"][4, :] = [np.nan, np.nan, np.nan, 3.0]
        h5["tinj"][4] = 2.9

    with h5py.File(cache, "r") as h5:
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=2,
            expected_no_positive_rows=1,
            expected_single_record_rows=2,
            expected_trim_single_record_overlap_rows=1,
        )
        raw = workflow._raw_cache_chunk(h5, 0, 5)
        treated, metadata = workflow.apply_pressure_treatment(
            raw,
            row_offset=0,
            plan=plan,
        )

    assert plan["trim_rows"].tolist() == [1, 2]
    assert plan["single_record_rows"].tolist() == [2, 4]
    assert plan["trim_single_record_overlap_rows"].tolist() == [2]
    assert plan["trim_single_record_overlap_row_count"] == 1
    assert len(plan["single_record_effective_mask_sha256"]) == 64
    assert np.intersect1d(
        plan["trim_rows"], plan["single_record_rows"]
    ).tolist() == [2]
    assert plan["single_record_active_mask"].tolist() == [
        False, False, True, True
    ]
    assert metadata["trim_affected"] == [False, True, True, False]
    assert metadata["instantaneous_history"] == [False, False, True, True]
    trimmed_singleton = next(
        row for row in plan["records"] if row["endpoint_id"] == 404
    )
    assert trimmed_singleton["reason"] == "joint_initialization_zero_trim"
    assert trimmed_singleton["instantaneous_after_treatment"] is True
    assert treated["physical_ids"].tolist() == [901, 17, 404, 1201]

    with h5py.File(cache, "r") as h5:
        with pytest.raises(workflow.WorkflowError, match="trim_single_record_overlap=1"):
            workflow.build_pressure_treatment_plan(
                h5,
                expected_trim_rows=2,
                expected_no_positive_rows=1,
                expected_single_record_rows=2,
                expected_trim_single_record_overlap_rows=0,
            )


def test_treatment_support_alignment_and_comparator_construction(tmp_path: Path) -> None:
    cache = tmp_path / "treatment.h5"
    _write_treatment_cache(cache)
    emissivity = tmp_path / "emissivity.npz"
    np.savez(
        emissivity,
        physical_ids=np.array([901, 17, 404, 1201]),
        cache_row_indices=np.array([0, 1, 2, 4]),
        trim_affected=np.array([False, True, True, False]),
        instantaneous_history=np.array([False, False, False, False]),
        primary_active_mask=np.array([True, True, True, False, True]),
        conservative_active_mask=np.array([True, False, False, False, True]),
        full=np.ones((4, 2)),
        none=np.ones((4, 2)) * 2,
    )
    with h5py.File(cache, "r") as h5, np.load(emissivity) as emis:
        support = workflow._load_treatment_aligned_support(h5, emis)
    assert support["primary_ids"].tolist() == [901, 17, 404, 1201]
    assert support["comparator_ids"].tolist() == [901, 1201]
    assert support["comparator_select"].tolist() == [True, False, False, True]

    with h5py.File(cache, "r+") as h5:
        h5["endpoint_ids"][2] = 999
    with h5py.File(cache, "r") as h5, np.load(emissivity) as emis:
        with pytest.raises(workflow.WorkflowError, match="alignment"):
            workflow._load_treatment_aligned_support(h5, emis)


def test_treatment_decision_stability_is_explicit() -> None:
    stable = workflow.assess_treatment_decision_stability(
        {"decision_label": workflow.DECISION_LABELS["low"]},
        {"decision_label": workflow.DECISION_LABELS["low"]},
    )
    assert stable["stable"] is True
    unstable = workflow.assess_treatment_decision_stability(
        {"decision_label": workflow.DECISION_LABELS["green"]},
        {"decision_label": workflow.DECISION_LABELS["low"]},
    )
    assert unstable["stable"] is False
    assert unstable["primary_decision_label"] == workflow.DECISION_LABELS["green"]


def test_pressure_treatment_map_comparison_records_lossless_metrics() -> None:
    primary = np.ones((2, 2, 2))
    primary[:, :, 1] = 0.5
    conservative = primary.copy()
    conservative[0, 0, :] = 0.0
    result = workflow._compare_pressure_treatment_maps(primary, conservative)
    assert result["primary"]["integrated_luminosity_W_Hz"][0] > result[
        "conservative"
    ]["integrated_luminosity_W_Hz"][0]
    assert result["primary"]["integrated_spectral_index"] == pytest.approx(
        result["conservative"]["integrated_spectral_index"]
    )
    assert result["per_frequency"]["0.15"]["normalised_l1_map_difference"] == pytest.approx(
        0.25
    )
    assert result["per_frequency"]["1.4"]["support_dice"] < 1.0


def test_intensity_observables_apply_one_dimming_and_one_four_pi() -> None:
    intensity = np.ones((9, 9, 1)) * (u.W / (u.Hz * u.m**2 * u.sr))
    result = workflow.derive_observables(
        intensity,
        pixel_size_kpc=1.8,
        redshift=0.05,
        beam_fwhm_kpc=5.0,
        angular_diameter_distance_m=1.0e24,
    )
    pixel_area = (1.8 * workflow.KPC_TO_M) ** 2
    expected_luminosity = 4.0 * np.pi * 81 * pixel_area
    expected_omega = np.pi / (4.0 * np.log(2.0)) * (5.0 * workflow.KPC_TO_M / 1.0e24) ** 2
    assert result["luminosity_W_Hz"][0] == pytest.approx(expected_luminosity)
    assert result["beam_solid_angle_sr"] == pytest.approx(expected_omega)
    assert result["dimming_factor"] == pytest.approx((1.0 + 0.05) ** -3)
    assert result["mjy_per_beam"].shape == intensity.shape
    assert np.all(np.isfinite(result["mjy_per_beam"]))


def _metric(value: float) -> dict[str, float | int]:
    return {
        "log10_luminosity_ratio": value,
        "area_fraction_change": 0.0,
        "extent_fraction_change": 0.0,
        "spectral_index_change": 0.0,
        "dice_change": 0.0,
        "component_change": 0,
    }


def test_decision_labels_and_persistent_materiality_contract() -> None:
    gates = {"history": True, "method": True, "compute": True}
    primary = [_metric(-0.12), _metric(-0.11), _metric(-0.02)]
    adjacent = {
        "beam_2.5_kpc": [_metric(-0.13), _metric(-0.10), _metric(-0.01)],
        "threshold_x3": [_metric(-0.02), _metric(-0.01), _metric(0.0)],
    }
    positive = workflow.decide_value_gate(
        gates=gates,
        primary_view_metrics=primary,
        adjacent_sensitivity_metrics=adjacent,
        numerical_error=0.02,
        stress_envelope_nonmaterial=False,
    )
    assert positive["decision_label"] == "G_LO_FULL_HISTORY_VALUE_GREEN_REGENERATION_REVIEW_JUSTIFIED"
    assert positive["same_direction_views"] == 2
    assert positive["persistent_adjacent_sensitivity"] == "beam_2.5_kpc"

    unstable = workflow.decide_value_gate(
        gates=gates,
        primary_view_metrics=primary,
        adjacent_sensitivity_metrics=adjacent,
        numerical_error=0.031,
        stress_envelope_nonmaterial=False,
    )
    assert unstable["decision_label"] == "G_LO_RADIO_METHOD_BLOCKED"

    low = workflow.decide_value_gate(
        gates=gates,
        primary_view_metrics=[_metric(-0.02)] * 3,
        adjacent_sensitivity_metrics=adjacent,
        numerical_error=0.0,
        stress_envelope_nonmaterial=False,
    )
    assert low["decision_label"] == "G_LO_FULL_HISTORY_VALUE_LOW_MATCHED_LOSSLESS_SCOPE_PREFERRED"
    assert low["history_regeneration_scope"] == "INSUFFICIENT_BY_ITSELF_TO_RULE_OUT_C_HI_C_LO_HISTORIES"

    assert workflow.decide_value_gate(
        gates={"history": False, "method": True, "compute": True},
        primary_view_metrics=[],
        adjacent_sensitivity_metrics={},
    )["decision_label"] == "G_LO_HISTORY_BLOCKED"
    assert workflow.decide_value_gate(
        gates={"history": True, "method": False, "compute": True},
        primary_view_metrics=[],
        adjacent_sensitivity_metrics={},
    )["decision_label"] == "G_LO_RADIO_METHOD_BLOCKED"
    assert workflow.decide_value_gate(
        gates={"history": True, "method": True, "compute": False},
        primary_view_metrics=[],
        adjacent_sensitivity_metrics={},
    )["decision_label"] == "G_LO_RADIO_COMPUTE_BLOCKED"


def test_compact_package_has_stable_file_list_and_excludes_cache(tmp_path: Path) -> None:
    products = tmp_path / "products"
    products.mkdir()
    (products / "decision.json").write_text('{"decision": "low"}\n')
    (products / "metrics.csv").write_text("metric,value\nx,1\n")
    cache = products / "history.h5"
    cache.write_bytes(b"must not be archived")
    raw = products / "particles.5000.dbl"
    raw.write_bytes(b"must not be archived")

    archive = tmp_path / "compact.tar.gz"
    result = workflow.create_compact_package(products, archive)
    listed = (products / "archive_file_list.txt").read_text().splitlines()
    assert listed == sorted(listed)
    assert "decision.json" in listed
    assert "metrics.csv" in listed
    assert "history.h5" not in listed
    assert "particles.5000.dbl" not in listed
    first_hash = hashlib.sha256(archive.read_bytes()).hexdigest()

    archive.unlink()
    result2 = workflow.create_compact_package(products, archive)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == first_hash
    assert result2["archive_sha256"] == result["archive_sha256"]
    manifest = json.loads((products / "package_manifest.json").read_text())
    assert manifest["contains_history_cache"] is False
    assert manifest["contains_raw_particles"] is False


def test_plutokore_verification_uses_exported_commit_only_when_git_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "plutokore"
    radio = source / "src" / "plutokore" / "radio"
    radio.mkdir(parents=True)
    (radio / "praise.py").write_text("# pinned praise\n")
    (radio / "raytracing.py").write_text("# pinned raytracing\n")
    monkeypatch.setenv("GOAL049_VERIFIED_PLUTOKORE_COMMIT", workflow.EXPECTED_PLUTOKORE_COMMIT)

    def missing_git(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(workflow.subprocess, "run", missing_git)
    result = workflow.verify_plutokore_source(source)
    assert result["commit"] == workflow.EXPECTED_PLUTOKORE_COMMIT
    assert result["commit_verification"] == "exported_pre_purge_commit_git_unavailable"
    assert set(result["implementation_sha256"]) == {"praise.py", "raytracing.py"}


def test_run_all_records_source_and_storage_preflight_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    method_root = tmp_path / "method"
    method_args = SimpleNamespace(
        work_root=method_root,
        plutokore_source=tmp_path / "missing-plutokore",
    )
    monkeypatch.setattr(
        workflow,
        "verify_plutokore_source",
        lambda _source: (_ for _ in ()).throw(workflow.WorkflowError("wrong source")),
    )
    with pytest.raises(workflow.WorkflowError, match="wrong source"):
        workflow.run_all(method_args)
    assert json.loads(
        (method_root / "compact" / "metrics" / "decision.json").read_text()
    )["decision_label"] == "G_LO_RADIO_METHOD_BLOCKED"

    compute_root = tmp_path / "compute"
    compute_args = SimpleNamespace(
        work_root=compute_root,
        plutokore_source=tmp_path / "plutokore",
        expected_endpoint_count=197_568,
        minimum_free_reserve_gb=130.0,
        max_projected_free_fraction=0.70,
    )
    monkeypatch.setattr(
        workflow,
        "verify_plutokore_source",
        lambda _source: {"commit": workflow.EXPECTED_PLUTOKORE_COMMIT},
    )
    monkeypatch.setattr(
        workflow,
        "storage_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            workflow.WorkflowError("insufficient storage")
        ),
    )
    with pytest.raises(workflow.WorkflowError, match="insufficient storage"):
        workflow.run_all(compute_args)
    assert json.loads(
        (compute_root / "compact" / "metrics" / "decision.json").read_text()
    )["decision_label"] == "G_LO_RADIO_COMPUTE_BLOCKED"
