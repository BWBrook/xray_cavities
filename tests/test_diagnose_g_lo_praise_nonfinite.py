from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_praise_nonfinite as forensic


def _record(mode: str, loss: str, output: str, classification: str = "finite") -> dict:
    return {
        "pressure_mode": mode,
        "loss_branch": loss,
        "start_index": 0,
        "dense_row": 0,
        "physical_id": 100,
        "frequency_GHz": 0.15,
        "output_class": output,
        "matched_lossless_output_class": "finite",
        "classification": classification,
    }


def test_decision_contract_is_fail_closed() -> None:
    assert forensic.classify_forensic_records([])["decision"] == "NO_NONFINITE_REPRODUCED"
    cutoff = [_record("unsmoothed", "full", "nan", "proven_full_loss_cutoff"), _record("unsmoothed", "none", "finite")]
    assert forensic.classify_forensic_records(cutoff)["decision"] == "CUTOFF_ZERO_POLICY_ELIGIBLE"
    unresolved = [_record("unsmoothed", "full", "nan", "unresolved_nonfinite"), _record("unsmoothed", "none", "finite")]
    assert forensic.classify_forensic_records(unresolved)["decision"] == "PRAISE_NUMERICS_BLOCKED"
    lossless = [_record("unsmoothed", "full", "nan", "proven_full_loss_cutoff"), _record("unsmoothed", "none", "nan")]
    assert forensic.classify_forensic_records(lossless)["decision"] == "PRAISE_NUMERICS_BLOCKED"


def test_diagnostic_writes_selection_then_mode_checkpoints_and_no_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = tmp_path / "cache.h5"
    affected = tmp_path / "affected.csv"
    cache.write_bytes(b"cache")
    affected.write_text("cache_row,physical_id,log_endpoint_relative_difference,min_log_to_raw_ratio\n0,100,0,1\n")
    output = tmp_path / "out"

    class FakeH5:
        attrs = {"shock_threshold": 5.0, "shock_component": 2}
        def __enter__(self): return self
        def __exit__(self, *_): return False

    monkeypatch.setattr(forensic.h5py, "File", lambda *_args, **_kwargs: FakeH5())
    monkeypatch.setattr(forensic.workflow, "_validate_completed_cache", lambda _h5: None)
    monkeypatch.setattr(forensic.workflow, "build_pressure_treatment_plan", lambda *_args, **_kwargs: {
        "trim_rows": [], "excluded_rows": [], "identity_sha256": "a" * 64,
    })
    monkeypatch.setattr(forensic.base, "construct_deterministic_sample", lambda *_args, **_kwargs: (
        [0], [{"sample_index": 0, "cache_row": 0, "physical_id": 100, "analysis_weight": 1.0}],
        {"sample_size_selected": 1},
    ))
    monkeypatch.setattr(forensic.base, "_read_treated_sample", lambda *_args: {})
    monkeypatch.setattr(forensic.workflow, "convert_code_cache_to_physical", lambda *_args, **_kwargs: ({}, {"units": "test"}))
    monkeypatch.setattr(forensic.workflow, "_cache_identity", lambda _path: {"sha256": "b" * 64})
    monkeypatch.setattr(forensic.workflow, "_sha256_file", lambda _path: "c" * 64)
    calls: list[str] = []

    def fake_pair(_physical, *, pressure_mode, **_kwargs):
        calls.append(pressure_mode)
        records = [
            _record(pressure_mode, "full", "nan", "proven_full_loss_cutoff"),
            _record(pressure_mode, "full", "nan", "proven_full_loss_cutoff"),
            _record(pressure_mode, "none", "finite"),
            _record(pressure_mode, "none", "finite"),
        ]
        return {
            "nonfinite_diagnostics": {"records": records, "nonfinite": True},
            "metadata": {"pressure_mode": pressure_mode},
        }

    monkeypatch.setattr(forensic, "calculate_praise_pair", fake_pair)
    result = forensic.diagnose_praise_nonfinite(cache, affected, output, sample_size=1, expected_trim_rows=0, expected_no_positive_rows=0, expected_single_record_rows=0)
    assert calls == ["unsmoothed", "log_savgol"]
    assert result["decision"] == "CUTOFF_ZERO_POLICY_ELIGIBLE"
    assert (output / "praise_forensic_selection.csv").is_file()
    for mode in forensic.MODES:
        assert (output / f"praise_forensic_{mode}_checkpoint.json").is_file()
        assert (output / f"praise_forensic_{mode}_records.csv").is_file()
    summary = json.loads((output / "praise_forensic_summary.json").read_text())
    assert "no emissivity is zeroed" in summary["replacement_policy"]
    assert not (output / "pressure_method_particle_comparison.csv").exists()
    with (output / "praise_forensic_selection.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 1


def test_mode_failure_checkpoint_is_written_and_propagated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache.h5"; cache.write_bytes(b"cache")
    affected = tmp_path / "affected.csv"; affected.write_text("cache_row,physical_id,log_endpoint_relative_difference,min_log_to_raw_ratio\n0,100,0,1\n")
    class FakeH5:
        attrs = {"shock_threshold": 5.0, "shock_component": 2}
        def __enter__(self): return self
        def __exit__(self, *_): return False
    monkeypatch.setattr(forensic.h5py, "File", lambda *_args, **_kwargs: FakeH5())
    monkeypatch.setattr(forensic.workflow, "_validate_completed_cache", lambda _h5: None)
    monkeypatch.setattr(forensic.workflow, "build_pressure_treatment_plan", lambda *_args, **_kwargs: {"trim_rows": [], "excluded_rows": [], "identity_sha256": "a" * 64})
    monkeypatch.setattr(forensic.base, "construct_deterministic_sample", lambda *_args, **_kwargs: ([0], [{"sample_index": 0, "cache_row": 0, "physical_id": 100, "analysis_weight": 1.0}], {"sample_size_selected": 1}))
    monkeypatch.setattr(forensic.base, "_read_treated_sample", lambda *_args: {})
    monkeypatch.setattr(forensic.workflow, "convert_code_cache_to_physical", lambda *_args, **_kwargs: ({}, {}))
    monkeypatch.setattr(forensic.workflow, "_cache_identity", lambda _path: {})
    monkeypatch.setattr(forensic.workflow, "_sha256_file", lambda _path: "c" * 64)
    def fail_pair(*_args, **_kwargs): raise ValueError("upstream nonfinite")
    monkeypatch.setattr(forensic, "calculate_praise_pair", fail_pair)
    with pytest.raises(ValueError, match="upstream nonfinite"):
        forensic.diagnose_praise_nonfinite(cache, affected, tmp_path / "out", sample_size=1, expected_trim_rows=0, expected_no_positive_rows=0, expected_single_record_rows=0)
    checkpoint = json.loads((tmp_path / "out" / "praise_forensic_unsmoothed_checkpoint.json").read_text())
    assert checkpoint["status"] == "mode_failed"
