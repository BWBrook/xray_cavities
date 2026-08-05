from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest
from astropy import units as u

sys.path.insert(0, str(Path(__file__).parents[1]))


SCRIPT = Path("scripts/science/diagnose_praise2_method_validation.py")


def load_module():
    spec = importlib.util.spec_from_file_location("diagnose_praise2_method_validation", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selection_and_driver_schema_hold_on_state_gate(tmp_path, monkeypatch):
    m = load_module()
    cache_path = tmp_path / "cache.h5"
    selection_path = tmp_path / "selection.csv"
    output = tmp_path / "out"
    with h5py.File(cache_path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=np.array([10, 20], dtype=np.int64))
        h5.create_dataset("times", data=np.array([0.0, 1.0]))
        h5.attrs["shock_threshold"] = 5.0
        h5.attrs["shock_component"] = 0
    selection_path.write_text(
        "sample_index,cache_row,physical_id,analysis_weight\n"
        "0,1,20,1.0\n"
        "1,0,10,1.0\n"
    )
    cache_hash = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    selection_hash = hashlib.sha256(selection_path.read_bytes()).hexdigest()
    rows = np.array([1, 0], dtype=np.int64)
    selection = [
        {"sample_index": 0, "cache_row": 1, "physical_id": 20, "analysis_weight": 1.0},
        {"sample_index": 1, "cache_row": 0, "physical_id": 10, "analysis_weight": 1.0},
    ]
    raw = {
        "physical_ids": np.array([20, 10]),
        "time": np.array([0.0, 10.0]),
        "pressure": np.array([[np.nan, 1.0], [1.0, 1.1]]),
        "density": np.ones((2, 2)),
        "tracer": np.ones((2, 2)),
        # Goal cache stores singleton last-shock histories as a true 2-D array.
        "last_shock_time": np.ones((2, 2)),
        "position": np.zeros((2, 3)),
        "velocity": np.zeros((2, 3)),
        "tinj": np.zeros(2),
    }
    monkeypatch.setattr(m.stable, "read_exact_selection", lambda *args, **kwargs: (rows, selection))
    monkeypatch.setattr(m.adiabatic, "_read_treated_sample", lambda *args: raw)
    monkeypatch.setattr(m.workflow, "build_pressure_treatment_plan", lambda *args, **kwargs: {})
    monkeypatch.setattr(m.workflow, "convert_code_cache_to_physical", lambda value, **kwargs: (value, {"unit": "synthetic"}))
    monkeypatch.setattr(m, "resolve_praise2_provenance", lambda *args, **kwargs: {"commit": "synthetic", "source_sha256": "synthetic", "callable": "plutokore.radio.praise2.praise"})

    class FakePraise2:
        @staticmethod
        def praise(**kwargs):
            n = kwargs["part_data"]["pressure"].shape[0]
            width = kwargs["part_data"]["pressure"].shape[1]
            values = np.ones((n, 2, 1)) * (1.0 + width)
            quantity = values * (u.W / (u.Hz * u.m**3 * u.sr))
            result = {"lossless": [{"emis": quantity, "part_output": width - 1}]}
            for code, name in ((1, "adiabatic"), (4, "full")):
                if code in kwargs["losses"]:
                    result[name] = [{"emis": quantity, "part_output": width - 1}]
            return result

    monkeypatch.setattr(m, "_load_praise2", lambda *_args: FakePraise2)
    monkeypatch.setattr(
        m,
        "calculate_praise_pair",
        lambda *args, **kwargs: {
            "ids": np.array([20, 10]),
            "none": np.ones((2, 2)) * (u.W / (u.Hz * u.m**3 * u.sr)),
            "adiabatic": np.ones((2, 2)) * (u.W / (u.Hz * u.m**3 * u.sr)),
            "full": np.ones((2, 2)) * (u.W / (u.Hz * u.m**3 * u.sr)),
            "nonfinite_diagnostics": {"records": []},
        },
    )
    result = m.diagnose_praise2_method_validation(
        cache_path,
        selection_path,
        output,
        expected_cache_sha256=cache_hash,
        expected_selection_sha256=selection_hash,
        expected_selection_count=2,
        praise2_source=tmp_path / "praise2.py",
    )
    assert result["decision"] == "HOLD"
    assert result["decision_label"] == "PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION"
    assert result["state_observability"]["status"] == "not_observable"
    assert (output / "praise2_vs_goal049_raw_lower_endpoint.csv").is_file()
    assert (output / "goal049_raw_lower_forensics.csv").is_file()
    assert (output / "praise2_unsmoothed_endpoint.npz").is_file()
    with (output / "praise2_vs_goal049_raw_lower_endpoint.csv").open(newline="") as handle:
        rows_out = list(csv.DictReader(handle))
    assert len(rows_out) == 2 * 2 * 3 * 2
    assert {row["loss_branch"] for row in rows_out} == {"lossless", "adiabatic", "full"}
    assert result["modes"]["unsmoothed"]["group_provenance"]["singleton_rows"] == [0]
    assert all(group["state_validation_scope"] == "none" for group in result["modes"]["unsmoothed"]["group_provenance"]["groups"])
    assert result["goal051_stable_comparison"]["implemented"] is False


def test_hash_gate_fails_closed(tmp_path):
    m = load_module()
    cache = tmp_path / "cache.h5"
    selection = tmp_path / "selection.csv"
    with h5py.File(cache, "w"):
        pass
    selection.write_text("sample_index,cache_row,physical_id,analysis_weight\n")
    with pytest.raises(m.Praise2DiagnosticError, match="cache SHA-256"):
        m.diagnose_praise2_method_validation(
            cache,
            selection,
            tmp_path / "out",
            expected_cache_sha256="0" * 64,
            expected_selection_sha256=hashlib.sha256(selection.read_bytes()).hexdigest(),
            expected_selection_count=0,
            praise2_source=tmp_path / "praise2.py",
        )


def test_praise2_time_facade_is_myr_scaled_for_uniform_resampler():
    m = load_module()
    raw = {
        "physical_ids": np.array([1]),
        "time": np.array([0.0, 1.0]),
        "pressure": np.ones((1, 2)),
        "density": np.ones((1, 2)),
        "tracer": np.ones((1, 2)),
        "last_shock_time": np.ones((1, 2, 1)),
    }
    contract = m._cache_to_contract(raw, "unsmoothed")
    kwargs = m.build_praise2_call_kwargs(contract, particle_spacing=0.01 * u.Myr)
    time_myr = kwargs["sim"].unit_values.time.to_value(u.Myr)
    assert 0 < time_myr < 1e-2
    assert kwargs["particle_spacing"].unit.is_equivalent(u.Myr)


def test_uniform_index_gate_is_exact_and_rejects_omitted_indices(tmp_path, monkeypatch):
    m = load_module()
    raw = {
        "physical_ids": np.array([1]),
        "time": np.array([0.0, 10.0]),
        "pressure": np.ones((1, 2)),
        "density": np.ones((1, 2)),
        "tracer": np.ones((1, 2)),
        "last_shock_time": np.ones((1, 2)),
    }
    contract = m._cache_to_contract(raw, "unsmoothed")
    exact = m._praise2_uniform_indices(contract, 0.01 * u.Myr)
    assert exact.tolist() == [0, 1]
    original = m._praise2_uniform_indices
    monkeypatch.setattr(m, "_praise2_uniform_indices", lambda *_args: np.array([0], dtype=np.int64))
    with pytest.raises(m.Praise2DiagnosticError, match="omitted"):
        m._group_high_level_outputs(raw, mode="unsmoothed", praise2=SimpleNamespace())
    monkeypatch.setattr(m, "_praise2_uniform_indices", original)
