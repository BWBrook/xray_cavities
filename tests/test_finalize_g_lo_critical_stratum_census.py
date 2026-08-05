from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import diagnose_g_lo_critical_stratum_census as diagnostic
from scripts.science import diagnose_g_lo_stable_method_value as stable_method
from scripts.science.finalize_g_lo_critical_stratum_census import (
    Goal053FinalizationError,
    finalize_g_lo_critical_stratum_census,
)


TARGET = "target"


def _base_row(index: int, physical_id: int, weight: float, *, target: bool) -> dict[str, object]:
    row: dict[str, object] = {
        "sample_index": index,
        "cache_row": index,
        "physical_id": physical_id,
        "selection_reason": "critical_stratum_census" if target else "outside",
        "stratum": TARGET if target else "outside",
        "inclusion_probability": 1.0 if target else 0.5,
        "analysis_weight": weight,
        "affected_linear_sg": "True",
        "trim_affected": "False",
        "short_history": "False",
        "history_length": 10,
        "injection_age": 2.0,
        "pressure_dynamic_range_log10": 3.0,
        "shock_age": 1.0,
        "shock_relative_state": "post_injection_recent",
        "log_endpoint_relative_difference": 0.01,
        "min_log_to_raw_ratio": 0.8,
        "goal051_selected": "True" if target else "False",
        "goal051_selection_reason": "sample" if target else "",
        "goal051_analysis_weight": weight if target else "",
    }
    for mode in ("unsmoothed", "log_savgol"):
        for branch, value in (("full", 1.0), ("adiabatic", 2.0), ("none", 3.0)):
            for frequency in stable_method.FREQUENCIES_GHZ:
                row[f"{mode}_{branch}_{frequency:g}GHz"] = value + index * 0.1
    return row


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(root: Path) -> Path:
    partial = root / "partial"
    partial.mkdir()
    census = [_base_row(0, 10, 1.0, target=True), _base_row(1, 11, 1.0, target=True)]
    original = [_base_row(0, 10, 2.0, target=True), _base_row(1, 20, 3.0, target=False)]
    # The oracle target is represented by the two-row census mass.
    original[0]["cache_row"] = 0
    original[0]["goal051_analysis_weight"] = 2.0
    _write_rows(partial / diagnostic.SELECTION_NAME, census)
    _write_rows(partial / diagnostic.PARTICLE_NAME, census)
    _write_rows(partial / "original_selection.csv", original)
    _write_rows(partial / "original_particle_comparison.csv", original)
    ids = np.array([10, 11], dtype=np.int64)
    for mode, name in diagnostic.MODE_NPZ_NAMES.items():
        payload = {"physical_ids": ids, "frequencies": np.array(stable_method.FREQUENCIES_GHZ)}
        for branch, value in (("full", 1.0), ("adiabatic", 2.0), ("none", 3.0)):
            payload[branch] = np.array([[value, value], [value + 0.1, value + 0.1]])
        np.savez(partial / name, **payload)
    return partial


def test_oracle_exact_and_within_tolerance_are_accepted() -> None:
    original = [_base_row(0, 10, 1.0, target=True)]
    census = [dict(original[0])]
    rows, metadata = diagnostic.oracle_replay_tolerance_audit(original, census, target_stratum=TARGET)
    assert metadata["stable_branch_replay_exact_mismatch_count"] == 0
    assert metadata["stable_branch_replay_within_tolerance"] is True
    census[0]["unsmoothed_full_0.15GHz"] = 1.0 + 5e-11
    _rows, metadata = diagnostic.oracle_replay_tolerance_audit(original, census, target_stratum=TARGET)
    assert metadata["stable_branch_replay_exact_mismatch_count"] == 1
    assert metadata["stable_branch_replay_within_tolerance"] is True


def test_oracle_above_tolerance_rejects() -> None:
    original = [_base_row(0, 10, 1.0, target=True)]
    census = [dict(original[0])]
    census[0]["unsmoothed_full_0.15GHz"] = 1.0 + 2e-9
    with pytest.raises(diagnostic.CriticalStratumCensusError, match="tolerance"):
        diagnostic.oracle_replay_tolerance_audit(original, census, target_stratum=TARGET)


def test_finalization_is_deterministic_and_no_overwrite(tmp_path: Path) -> None:
    partial = _fixture(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    kwargs = {"expected_census_count": 2, "expected_oracle_count": 1, "target_stratum": TARGET}
    result1 = finalize_g_lo_critical_stratum_census(partial, None, None, first, **kwargs)
    result2 = finalize_g_lo_critical_stratum_census(partial, None, None, second, **kwargs)
    assert result1["decision"] == result2["decision"]
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
    with pytest.raises(Goal053FinalizationError, match="overwrite"):
        finalize_g_lo_critical_stratum_census(partial, None, None, first, **kwargs)


def test_missing_partial_array_fails_closed(tmp_path: Path) -> None:
    partial = _fixture(tmp_path)
    (partial / diagnostic.MODE_NPZ_NAMES["unsmoothed"]).unlink()
    with pytest.raises(Goal053FinalizationError, match="required evidence"):
        finalize_g_lo_critical_stratum_census(partial, None, None, tmp_path / "out", expected_census_count=2, expected_oracle_count=1, target_stratum=TARGET)


def test_symlinked_partial_directory_fails_closed(tmp_path: Path) -> None:
    partial = _fixture(tmp_path)
    linked = tmp_path / "linked_partial"
    linked.symlink_to(partial, target_is_directory=True)
    with pytest.raises(Goal053FinalizationError, match="directory is invalid"):
        finalize_g_lo_critical_stratum_census(
            linked,
            None,
            None,
            tmp_path / "out",
            expected_census_count=2,
            expected_oracle_count=1,
            target_stratum=TARGET,
        )


def test_npz_csv_identity_is_exact(tmp_path: Path) -> None:
    partial = _fixture(tmp_path)
    path = partial / diagnostic.MODE_NPZ_NAMES["unsmoothed"]
    with np.load(path, allow_pickle=False) as arrays:
        payload = {name: np.asarray(arrays[name]).copy() for name in arrays.files}
    payload["full"][0, 0] += 5e-13
    np.savez(path, **payload)
    with pytest.raises(Goal053FinalizationError, match="does not reproduce CSV"):
        finalize_g_lo_critical_stratum_census(
            partial,
            None,
            None,
            tmp_path / "out",
            expected_census_count=2,
            expected_oracle_count=1,
            target_stratum=TARGET,
        )
