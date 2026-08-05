from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science import build_g_lo_pressure_method_synthesis as synthesis


def _row(
    physical_id: int,
    *,
    stratum: str,
    weight: float,
    unsmoothed: float,
    log_savgol: float,
    branch_scale: float = 1.0,
) -> dict[str, object]:
    row: dict[str, object] = {
        "sample_index": physical_id,
        "cache_row": physical_id,
        "physical_id": physical_id,
        "stratum": stratum,
        "analysis_weight": weight,
        "inclusion_probability": 1.0 / weight,
    }
    for mode, value in (("unsmoothed", unsmoothed), ("log_savgol", log_savgol)):
        for branch, factor in (("full", 1.0), ("adiabatic", 1.1), ("none", 1.4)):
            for frequency, frequency_factor in ((0.15, 1.0), (1.4, 0.5)):
                row[f"{mode}_{branch}_{frequency:g}GHz"] = (
                    value * factor * frequency_factor * branch_scale
                )
    return row


def _fixture() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    target = "target"
    secondary = "secondary"
    original = [
        _row(1, stratum="outside", weight=2.0, unsmoothed=1.0, log_savgol=1.2),
        _row(2, stratum=target, weight=3.0, unsmoothed=2.0, log_savgol=2.4),
        _row(3, stratum=secondary, weight=1.0, unsmoothed=1.0, log_savgol=1.8),
    ]
    census = [
        _row(20, stratum=target, weight=1.5, unsmoothed=2.0, log_savgol=2.2),
        _row(21, stratum=target, weight=1.5, unsmoothed=2.0, log_savgol=2.2),
    ]
    return original, census


def test_weighted_branch_rows_and_concentration_are_deterministic() -> None:
    original, census = _fixture()
    scopes = synthesis.build_scopes(original, census, target_stratum="target")
    rows = synthesis.branch_frequency_rows(scopes)
    row = next(
        r for r in rows
        if r["scope"] == "original_sample"
        and r["branch"] == "full"
        and r["frequency_GHz"] == 0.15
    )
    assert row["unsmoothed_weighted_sum"] == pytest.approx(9.0)
    assert row["log_savgol_weighted_sum"] == pytest.approx(11.4)
    assert row["percent_delta"] == pytest.approx((11.4 / 9.0 - 1) * 100)
    assert row["log10_ratio_dex"] == pytest.approx(np.log10(11.4 / 9.0))
    curves = synthesis.discrepancy_concentration_rows(scopes)
    assert len(curves) == 32
    assert curves == synthesis.discrepancy_concentration_rows(scopes)


def test_attribution_and_ablation_report_diagnostic_only() -> None:
    original, census = _fixture()
    scopes = synthesis.build_scopes(original, census, target_stratum="target")
    attribution = synthesis.stratum_attribution(scopes, exact_census_stratum="target")
    assert {row["stratum"] for row in attribution} == {"outside", "target", "secondary"}
    target = next(
        row for row in attribution
        if row["stratum"] == "target" and row["scope"] == "hybrid_population"
    )
    assert target["scope"] == "hybrid_population"
    assert target["row_set_status"] == "exact_census"
    assert 0 <= target["top_one_percent_numerator_fraction"] <= 1
    assert target["effective_sample_size"] > 0
    sensitivity = synthesis.influential_history_sensitivity(
        scopes["hybrid_population"],
        target_stratum="target",
        secondary_stratum="secondary",
        influential_id=1,
    )
    assert len(sensitivity) == 5
    assert all(row["is_alternative_estimate"] == "false" for row in sensitivity)
    assert next(row for row in sensitivity if row["scenario"] == "zero_id_1")["zeroed_row_count"] == 1
    assert next(row for row in sensitivity if row["scenario"] == "baseline_hybrid")["total_discrepancy"] > 0
    by_stratum = synthesis.stratum_zeroing_sensitivity(
        scopes["hybrid_population"], target_stratum="target"
    )
    assert {row["stratum"] for row in by_stratum} == {
        "outside",
        "secondary",
        "target",
    }
    assert all(row["is_alternative_estimate"] == "false" for row in by_stratum)


def test_builder_writes_fresh_outputs_and_nonempty_figure(tmp_path: Path) -> None:
    original, census = _fixture()
    original_csv = tmp_path / "original.csv"
    census_csv = tmp_path / "census.csv"
    summary_json = tmp_path / "summary.json"
    synthesis.write_rows(original_csv, original)
    synthesis.write_rows(census_csv, census)
    summary_json.write_text(json.dumps({"census_count": 2, "target_stratum": "target"}))
    output = tmp_path / "out"
    result = synthesis.build_synthesis(
        original_csv=original_csv,
        census_csv=census_csv,
        summary_json=summary_json,
        output_dir=output,
        target_stratum="target",
        secondary_stratum="secondary",
        influential_id=1,
    )
    assert result["status"] == "complete_local_synthesis"
    assert result["metadata"]["decision_label"] in {
        synthesis.DECISION_NO_FURTHER_CENSUS,
        synthesis.DECISION_CONDITIONAL,
    }
    figure = output / "g_lo_pressure_method_synthesis.png"
    assert figure.stat().st_size > 0
    assert (output / "branch_frequency_comparison.csv").is_file()
    with (output / "branch_frequency_comparison.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 24
    with pytest.raises(synthesis.SynthesisError, match="refusing to overwrite"):
        synthesis.build_synthesis(
            original_csv=original_csv,
            census_csv=census_csv,
            summary_json=summary_json,
            output_dir=output,
            target_stratum="target",
            secondary_stratum="secondary",
            influential_id=1,
        )


def test_malformed_duplicate_ids_and_mass_mismatch_fail_closed() -> None:
    original, census = _fixture()
    with pytest.raises(synthesis.SynthesisError, match="duplicate"):
        synthesis.build_scopes(original + [dict(original[0])], census, target_stratum="target")
    bad_census = [dict(row) for row in census]
    bad_census[0]["analysis_weight"] = 1.0
    with pytest.raises(synthesis.SynthesisError, match="represented mass"):
        synthesis.build_scopes(original, bad_census, target_stratum="target")
