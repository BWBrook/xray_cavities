#!/usr/bin/env python3
"""Build the local Goal 054 G-LO pressure-method synthesis.

This is a descriptive synthesis of preserved Goal 051/053 compact outputs.  It
does not open the history cache, invoke PRAiSE, or make a physical uncertainty
claim.  All outputs are written to a required fresh directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Permit direct ``python scripts/science/...`` execution from the repository
# root, matching the project command convention.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.science import diagnose_g_lo_critical_stratum_census as census_diagnostic
from scripts.science import diagnose_g_lo_pressure_method_value as pressure_method
from scripts.science import diagnose_g_lo_stable_method_value as stable_method


DEFAULT_INPUT_DIR = ROOT / "docs/science/assets/g_lo_critical_stratum_census_repair_2026-07-30"
DEFAULT_OUTPUT_DIR = ROOT / "docs/science/assets/g_lo_pressure_method_synthesis_2026-08-01"
BRANCHES = ("full", "adiabatic", "none")
MODES = ("unsmoothed", "log_savgol")
FREQUENCIES_GHZ = tuple(float(value) for value in stable_method.FREQUENCIES_GHZ)
CONCENTRATION_FRACTIONS = (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
DEFAULT_TARGET_STRATUM = census_diagnostic.TARGET_STRATUM
DEFAULT_SECONDARY_STRATUM = (
    "affected=1|trim=1|length_q=0|injection_q=0|range_q=3|"
    "shock=post_injection_recent"
)
INFLUENTIAL_ID = 196136
DECISION_NO_FURTHER_CENSUS = "LOCALIZED_REGIME_SYNTHESIZED_NO_FURTHER_CENSUS"
DECISION_CONDITIONAL = "LOCAL_SYNTHESIS_COMPLETE_TARGETED_COMPUTE_ONLY_IF_RESIDUAL_DRIVER_CONTROLS_DECISION"


class SynthesisError(RuntimeError):
    """Raised when the Goal 054 evidence contract cannot be satisfied."""


def _regular(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SynthesisError(f"required input is not a regular file: {path}")
    return path.resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_path(path: Path) -> str:
    """Prefer a repository-relative provenance path when one is available."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _number(value: Any, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise SynthesisError(f"malformed numeric field {field!r}") from exc
    if not math.isfinite(parsed):
        raise SynthesisError(f"non-finite numeric field {field!r}")
    return parsed


def read_rows(path: Path) -> list[dict[str, str]]:
    path = _regular(path)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        if not fields or len(fields) != len(set(fields)):
            raise SynthesisError(f"CSV has missing or duplicate header fields: {path}")
        rows = list(reader)
    if not rows:
        raise SynthesisError(f"CSV has no data rows: {path}")
    if any(None in row for row in rows):
        raise SynthesisError(f"CSV has malformed extra columns: {path}")
    return rows


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    if not rows:
        raise SynthesisError(f"refusing to write empty CSV: {path}")
    names = list(fieldnames or rows[0].keys())
    if len(names) != len(set(names)):
        raise SynthesisError(f"duplicate output fields: {path}")
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _required_branch_fields() -> list[str]:
    return [
        f"{mode}_{branch}_{frequency:g}GHz"
        for mode in MODES
        for branch in BRANCHES
        for frequency in FREQUENCIES_GHZ
    ]


def _validate_rows(rows: Sequence[Mapping[str, Any]], label: str) -> list[dict[str, Any]]:
    required = {"sample_index", "cache_row", "physical_id", "stratum", "analysis_weight"}
    required.update(_required_branch_fields())
    if not rows:
        raise SynthesisError(f"{label} rows are empty")
    ids: set[int] = set()
    parsed: list[dict[str, Any]] = []
    for index, source in enumerate(rows):
        missing = required - set(source)
        if missing:
            raise SynthesisError(f"{label} row {index} missing fields: {sorted(missing)}")
        row = dict(source)
        for field in ("sample_index", "cache_row", "physical_id"):
            try:
                row[field] = int(source[field])
            except (TypeError, ValueError) as exc:
                raise SynthesisError(f"{label} malformed identity field {field}") from exc
        if row["physical_id"] in ids:
            raise SynthesisError(f"{label} has duplicate physical ID {row['physical_id']}")
        ids.add(row["physical_id"])
        row["stratum"] = str(source["stratum"])
        row["analysis_weight"] = _number(source["analysis_weight"], "analysis_weight")
        if row["analysis_weight"] <= 0:
            raise SynthesisError(f"{label} analysis weights must be positive")
        for field in _required_branch_fields():
            row[field] = _number(source[field], field)
            if row[field] < 0:
                raise SynthesisError(f"{label} branch values must be nonnegative")
        parsed.append(row)
    return parsed


def build_scopes(
    original_rows: Sequence[Mapping[str, Any]],
    census_rows: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
) -> dict[str, list[dict[str, Any]]]:
    """Validate and reconstruct original, exact census, and hybrid populations."""
    original = _validate_rows(original_rows, "original sample")
    census = _validate_rows(census_rows, "census")
    if any(row["stratum"] != target_stratum for row in census):
        raise SynthesisError("census rows include a record outside target stratum")
    if not any(row["stratum"] == target_stratum for row in original):
        raise SynthesisError("original sample has no target stratum rows")
    try:
        hybrid, _ = census_diagnostic.replace_stratum_with_census(
            original, census, target_stratum=target_stratum
        )
    except Exception as exc:
        raise SynthesisError(str(exc)) from exc
    return {
        "original_sample": original,
        "original_weighted_target_stratum": [
            dict(row) for row in original if row["stratum"] == target_stratum
        ],
        "critical_stratum_census": census,
        "hybrid_population": [dict(row) for row in hybrid],
    }


def _weighted_sum(rows: Sequence[Mapping[str, Any]], mode: str, branch: str, frequency: float) -> float:
    return float(sum(float(row["analysis_weight"]) * float(row[f"{mode}_{branch}_{frequency:g}GHz"]) for row in rows))


def branch_frequency_rows(scopes: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scope in (
        "original_sample",
        "original_weighted_target_stratum",
        "hybrid_population",
        "critical_stratum_census",
    ):
        population = scopes[scope]
        total_weight = float(sum(float(row["analysis_weight"]) for row in population))
        for branch in BRANCHES:
            for frequency in FREQUENCIES_GHZ:
                unsmoothed = _weighted_sum(population, "unsmoothed", branch, frequency)
                log_savgol = _weighted_sum(population, "log_savgol", branch, frequency)
                ratio = log_savgol / unsmoothed if unsmoothed else float("nan")
                rows.append({
                    "scope": scope,
                    "branch": branch,
                    "frequency_GHz": frequency,
                    "row_count": len(population),
                    "represented_weight": total_weight,
                    "unsmoothed_weighted_sum": unsmoothed,
                    "log_savgol_weighted_sum": log_savgol,
                    "log_savgol_over_unsmoothed_ratio": ratio,
                    "log10_ratio_dex": math.log10(ratio) if ratio > 0 else float("nan"),
                    "percent_delta": (ratio - 1.0) * 100.0 if math.isfinite(ratio) else float("nan"),
                })
    return rows


def _per_row_discrepancy(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return census_diagnostic._per_row_discrepancy(rows)


def discrepancy_concentration_rows(scopes: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for scope in (
        "original_sample",
        "original_weighted_target_stratum",
        "hybrid_population",
        "critical_stratum_census",
    ):
        rows = scopes[scope]
        discrepancy = _per_row_discrepancy(rows)
        weights = np.asarray([float(row["analysis_weight"]) for row in rows], dtype=np.float64)
        for fraction in CONCENTRATION_FRACTIONS:
            result = pressure_method.represented_population_discrepancy_concentration(
                discrepancy, weights, population_fraction=fraction
            )
            output.append({
                "scope": scope,
                "population_fraction": fraction,
                "discrepancy_fraction": result["fraction"],
                "represented_population_weight": result["represented_population_weight"],
                "target_population_weight": result["target_population_weight"],
                "fully_included_rows": result["fully_included_rows"],
                "fractional_boundary_row_index": result["fractional_boundary_row_index"],
                "fractional_boundary_row_weight_fraction": result["fractional_boundary_row_weight_fraction"],
                "numerator": result["numerator"],
                "denominator": result["denominator"],
            })
    return output


def _top_population_numerator_by_row(
    rows: Sequence[Mapping[str, Any]],
    discrepancy: np.ndarray,
    *,
    population_fraction: float = 0.01,
) -> np.ndarray:
    """Allocate the exact fractional-boundary concentration numerator by row."""
    weights = np.asarray([float(row["analysis_weight"]) for row in rows], dtype=np.float64)
    remaining = float(population_fraction * np.sum(weights))
    contribution = np.zeros(len(rows), dtype=np.float64)
    order = np.lexsort((np.arange(len(rows)), -discrepancy))
    for index in order:
        if remaining <= 0:
            break
        used = min(float(weights[index]), remaining)
        contribution[index] = used * float(discrepancy[index])
        remaining -= used
    return contribution


def _stratum_attribution_scope(
    rows: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    exact_census_stratum: str,
) -> list[dict[str, Any]]:
    discrepancy = _per_row_discrepancy(rows)
    total_weight = float(sum(float(row["analysis_weight"]) for row in rows))
    weighted_discrepancy = np.asarray([float(row["analysis_weight"]) for row in rows]) * discrepancy
    total_discrepancy = float(np.sum(weighted_discrepancy))
    top_one_percent_by_row = _top_population_numerator_by_row(rows, discrepancy)
    top_one_percent_numerator = float(np.sum(top_one_percent_by_row))
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[str(row["stratum"])].append(index)
    output: list[dict[str, Any]] = []
    for stratum in sorted(grouped):
        indices = grouped[stratum]
        stratum_weight = float(sum(float(rows[i]["analysis_weight"]) for i in indices))
        stratum_weights = np.asarray(
            [float(rows[i]["analysis_weight"]) for i in indices], dtype=np.float64
        )
        stratum_discrepancy = float(np.sum(weighted_discrepancy[indices]))
        stratum_top_one_percent = float(np.sum(top_one_percent_by_row[indices]))
        max_index = min(indices, key=lambda i: (-float(weighted_discrepancy[i]), int(rows[i]["physical_id"])))
        max_contribution = float(weighted_discrepancy[max_index])
        output.append({
            "scope": scope,
            "stratum": stratum,
            "row_count": len(indices),
            "represented_weight": stratum_weight,
            "represented_weight_fraction": stratum_weight / total_weight,
            "effective_sample_size": stratum_weight**2 / float(np.sum(stratum_weights**2)),
            "weighted_discrepancy": stratum_discrepancy,
            "scope_discrepancy_fraction": stratum_discrepancy / total_discrepancy if total_discrepancy else 0.0,
            "top_one_percent_numerator": stratum_top_one_percent,
            "top_one_percent_numerator_fraction": (
                stratum_top_one_percent / top_one_percent_numerator
                if top_one_percent_numerator
                else 0.0
            ),
            "top_one_percent_total_discrepancy_fraction": (
                stratum_top_one_percent / total_discrepancy if total_discrepancy else 0.0
            ),
            "max_contributor_id": int(rows[max_index]["physical_id"]),
            "max_contributor_analysis_weight": float(rows[max_index]["analysis_weight"]),
            "max_contributor_weighted_discrepancy": max_contribution,
            "max_contributor_share_within_stratum": max_contribution / stratum_discrepancy if stratum_discrepancy else 0.0,
            "max_contributor_share_scope_total": max_contribution / total_discrepancy if total_discrepancy else 0.0,
            "row_set_status": "exact_census" if scope == "hybrid_population" and stratum == exact_census_stratum else "sampled_expansion",
        })
    return output


def stratum_attribution(
    scopes_or_rows: Mapping[str, Sequence[Mapping[str, Any]]] | Sequence[Mapping[str, Any]],
    *,
    exact_census_stratum: str = DEFAULT_TARGET_STRATUM,
) -> list[dict[str, Any]]:
    """Attribute discrepancy by stratum for the hybrid and original scopes."""
    if isinstance(scopes_or_rows, Mapping):
        scopes = scopes_or_rows
    else:
        scopes = {"hybrid_population": scopes_or_rows}
    output: list[dict[str, Any]] = []
    for scope in ("original_sample", "hybrid_population"):
        if scope in scopes:
            output.extend(
                _stratum_attribution_scope(
                    scopes[scope], scope=scope, exact_census_stratum=exact_census_stratum
                )
            )
    return output


def influential_history_sensitivity(
    hybrid_rows: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
    secondary_stratum: str,
    influential_id: int = INFLUENTIAL_ID,
) -> list[dict[str, Any]]:
    scenarios: list[tuple[str, set[int], str]] = [
        ("baseline_hybrid", set(), "reference hybrid population"),
        (f"zero_id_{influential_id}", {influential_id}, "diagnostic ablation only"),
        ("zero_secondary_stratum", {int(r["physical_id"]) for r in hybrid_rows if r["stratum"] == secondary_stratum}, "diagnostic ablation only"),
        ("zero_exact_target_stratum", {int(r["physical_id"]) for r in hybrid_rows if r["stratum"] == target_stratum}, "diagnostic ablation only"),
        ("zero_both_strata", {int(r["physical_id"]) for r in hybrid_rows if r["stratum"] in {target_stratum, secondary_stratum}}, "diagnostic ablation only"),
    ]
    baseline = float(np.sum(np.asarray([float(r["analysis_weight"]) for r in hybrid_rows]) * _per_row_discrepancy(hybrid_rows)))
    output: list[dict[str, Any]] = []
    threshold = float(pressure_method.GATES["max_top_one_percent_discrepancy_fraction"])
    for scenario, remove_indices, interpretation in scenarios:
        rows = list(hybrid_rows)
        if len(remove_indices) >= len(rows):
            raise SynthesisError(f"sensitivity scenario {scenario} zeroes all rows")
        discrepancy = _per_row_discrepancy(rows)
        zeroed = np.asarray(
            [int(row["physical_id"]) in remove_indices for row in rows], dtype=bool
        )
        discrepancy[zeroed] = 0.0
        weights = np.asarray([float(row["analysis_weight"]) for row in rows], dtype=np.float64)
        total = float(np.sum(weights * discrepancy))
        concentration = pressure_method.represented_population_discrepancy_concentration(discrepancy, weights, population_fraction=0.01)
        top = float(concentration["fraction"])
        output.append({
            "scenario": scenario,
            "zeroed_row_count": len(remove_indices),
            "remaining_row_count": len(rows),
            "total_discrepancy": total,
            "relative_to_baseline": total / baseline if baseline else float("nan"),
            "top_one_percent_concentration": top,
            "threshold": threshold,
            "threshold_status": "passes" if top <= threshold else "above_threshold",
            "is_alternative_estimate": "false",
            "interpretation_scope": interpretation,
        })
    return output


def stratum_zeroing_sensitivity(
    hybrid_rows: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
) -> list[dict[str, Any]]:
    """Zero each stratum in turn while retaining its represented population mass."""
    discrepancy = _per_row_discrepancy(hybrid_rows)
    weights = np.asarray(
        [float(row["analysis_weight"]) for row in hybrid_rows], dtype=np.float64
    )
    baseline = float(np.sum(weights * discrepancy))
    threshold = float(pressure_method.GATES["max_top_one_percent_discrepancy_fraction"])
    output: list[dict[str, Any]] = []
    for stratum in sorted({str(row["stratum"]) for row in hybrid_rows}):
        mask = np.asarray(
            [str(row["stratum"]) == stratum for row in hybrid_rows], dtype=bool
        )
        zeroed = discrepancy.copy()
        zeroed[mask] = 0.0
        total = float(np.sum(weights * zeroed))
        concentration = pressure_method.represented_population_discrepancy_concentration(
            zeroed, weights, population_fraction=0.01
        )
        output.append({
            "stratum": stratum,
            "row_set_status": "exact_census" if stratum == target_stratum else "sampled_expansion",
            "zeroed_row_count": int(np.sum(mask)),
            "zeroed_represented_weight": float(np.sum(weights[mask])),
            "removed_weighted_discrepancy": float(np.sum(weights[mask] * discrepancy[mask])),
            "remaining_total_discrepancy": total,
            "remaining_relative_to_baseline": total / baseline if baseline else float("nan"),
            "top_one_percent_concentration": float(concentration["fraction"]),
            "threshold": threshold,
            "threshold_status": "passes" if float(concentration["fraction"]) <= threshold else "above_threshold",
            "is_alternative_estimate": "false",
        })
    return output


def top_hybrid_contributors(hybrid_rows: Sequence[Mapping[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    discrepancy = _per_row_discrepancy(hybrid_rows)
    weighted = np.asarray([float(row["analysis_weight"]) for row in hybrid_rows]) * discrepancy
    total = float(np.sum(weighted))
    order = sorted(range(len(hybrid_rows)), key=lambda i: (-float(weighted[i]), int(hybrid_rows[i]["physical_id"])))
    return [{
        "rank": rank,
        "physical_id": int(hybrid_rows[i]["physical_id"]),
        "stratum": str(hybrid_rows[i]["stratum"]),
        "analysis_weight": float(hybrid_rows[i]["analysis_weight"]),
        "per_row_discrepancy": float(discrepancy[i]),
        "weighted_discrepancy": float(weighted[i]),
        "hybrid_total_share": float(weighted[i] / total) if total else 0.0,
    } for rank, i in enumerate(order[:limit], start=1)]


def classify_synthesis(
    concentration: Sequence[Mapping[str, Any]],
    attribution: Sequence[Mapping[str, Any]],
    sensitivity: Sequence[Mapping[str, Any]],
    stratum_zeroing: Sequence[Mapping[str, Any]],
    branch: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
    secondary_stratum: str,
) -> tuple[str, dict[str, Any]]:
    """Classify whether another targeted census can change the current decision."""
    c1 = {
        str(row["scope"]): float(row["discrepancy_fraction"])
        for row in concentration
        if math.isclose(float(row["population_fraction"]), 0.01)
    }
    scenarios = {str(row["scenario"]): row for row in sensitivity}
    hybrid_attr = {
        str(row["stratum"]): row
        for row in attribution
        if row["scope"] == "hybrid_population"
    }
    branch_hybrid_full = [
        row
        for row in branch
        if row["scope"] == "hybrid_population" and row["branch"] == "full"
    ]
    threshold = float(pressure_method.GATES["max_top_one_percent_discrepancy_fraction"])
    max_shift_dex = max(abs(float(row["log10_ratio_dex"])) for row in branch_hybrid_full)
    secondary_zero_c1 = float(
        scenarios["zero_secondary_stratum"]["top_one_percent_concentration"]
    )
    target_zero_c1 = float(
        scenarios["zero_exact_target_stratum"]["top_one_percent_concentration"]
    )
    both_zero_c1 = float(scenarios["zero_both_strata"]["top_one_percent_concentration"])
    most_favourable_uncensused = min(
        (row for row in stratum_zeroing if row["stratum"] != target_stratum),
        key=lambda row: (float(row["top_one_percent_concentration"]), str(row["stratum"])),
    )
    minimum_uncensused_c1 = float(
        most_favourable_uncensused["top_one_percent_concentration"]
    )
    no_further_census = bool(
        c1["hybrid_population"] > threshold
        and c1["critical_stratum_census"] <= threshold
        and minimum_uncensused_c1 > threshold
        and target_zero_c1 > threshold
        and both_zero_c1 <= threshold
        and max_shift_dex
        <= float(pressure_method.GATES["max_abs_aggregate_difference_dex"])
    )
    metrics: dict[str, Any] = {
        "hybrid_top_one_percent_concentration": c1["hybrid_population"],
        "census_top_one_percent_concentration": c1["critical_stratum_census"],
        "secondary_stratum_zeroed_top_one_percent_concentration": secondary_zero_c1,
        "minimum_uncensused_stratum_zeroed_top_one_percent_concentration": minimum_uncensused_c1,
        "most_decision_favourable_uncensused_stratum": str(
            most_favourable_uncensused["stratum"]
        ),
        "uncensused_strata_tested": sum(
            row["stratum"] != target_stratum for row in stratum_zeroing
        ),
        "target_stratum_zeroed_top_one_percent_concentration": target_zero_c1,
        "both_strata_zeroed_top_one_percent_concentration": both_zero_c1,
        "target_stratum_hybrid_discrepancy_fraction": float(
            hybrid_attr[target_stratum]["scope_discrepancy_fraction"]
        ),
        "secondary_stratum_hybrid_discrepancy_fraction": float(
            hybrid_attr[secondary_stratum]["scope_discrepancy_fraction"]
        ),
        "max_hybrid_full_branch_shift_dex": max_shift_dex,
        "additional_single_stratum_census_decision_relevant": not no_further_census,
    }
    return (
        DECISION_NO_FURTHER_CENSUS if no_further_census else DECISION_CONDITIONAL,
        metrics,
    )


def next_step_recommendation_rows(
    decision_label: str,
    metrics: Mapping[str, Any],
) -> list[dict[str, Any]]:
    no_further = decision_label == DECISION_NO_FURTHER_CENSUS
    return [
        {
            "option": "pressure_method_interpretation_review",
            "recommendation_rank": 1,
            "decision": "recommended",
            "action": "Review the localized-regime interpretation and production-default implications using the compact Goal 054 evidence.",
            "compute_timing": "local_docs_and_decision",
            "why": "The exact census reduced magnitude while confirming a distributed discrepancy inside a rare stratum.",
        },
        {
            "option": "targeted_followup_census",
            "recommendation_rank": 2,
            "decision": "not_recommended_now" if no_further else "conditional",
            "action": "Do not run another census unless a later production decision specifically requires a direct estimate for the secondary stratum.",
            "compute_timing": "none_now" if no_further else "Kunanyi_only_if_residual_driver_controls_decision",
            "why": (
                "The most decision-favourable single uncensused-stratum zeroing leaves "
                f"C(1%)={float(metrics['minimum_uncensused_stratum_zeroed_top_one_percent_concentration']):.6f}; "
                "no one stratum can clear the 0.50 gate."
                if no_further
                else "Residual attribution has not yet excluded a decision-changing stratum."
            ),
        },
        {
            "option": "production_default_change",
            "recommendation_rank": 3,
            "decision": "hold_not_authorized",
            "action": "Retain current scientific defaults pending explicit method interpretation and supervisor review.",
            "compute_timing": "not_authorized",
            "why": "This deterministic within-simulation synthesis is not causal evidence or physical-uncertainty inference.",
        },
    ]


def _short_stratum_label(stratum: str) -> str:
    fields = dict(
        part.split("=", 1) for part in stratum.split("|") if "=" in part
    )
    shock = fields.get("shock", "unknown").replace("post_injection_", "post_")
    return (
        f"A{fields.get('affected', '?')} T{fields.get('trim', '?')} "
        f"L{fields.get('length_q', '?')} I{fields.get('injection_q', '?')} "
        f"R{fields.get('range_q', '?')} {shock}"
    )


def _plot(output: Path, concentration: Sequence[Mapping[str, Any]], attribution: Sequence[Mapping[str, Any]], branch: Sequence[Mapping[str, Any]]) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11, 13), constrained_layout=True)
    for scope in ("original_sample", "hybrid_population", "critical_stratum_census"):
        subset = [r for r in concentration if r["scope"] == scope]
        axes[0].plot([float(r["population_fraction"]) * 100 for r in subset], [float(r["discrepancy_fraction"]) for r in subset], marker="o", label=scope)
    axes[0].set_xscale("log")
    axes[0].set_ylim(0, 1.02)
    axes[0].set_ylabel("Discrepancy fraction")
    axes[0].set_title("Cumulative discrepancy concentration")
    axes[0].legend()
    top = sorted(
        [r for r in attribution if r["scope"] == "hybrid_population"],
        key=lambda r: float(r["scope_discrepancy_fraction"]),
        reverse=True,
    )[:12]
    axes[1].barh(
        [_short_stratum_label(str(r["stratum"])) for r in top][::-1],
        [float(r["scope_discrepancy_fraction"]) for r in top][::-1],
    )
    axes[1].set_xlabel("Share of hybrid discrepancy")
    axes[1].set_title("Top hybrid stratum attribution")
    selected = [r for r in branch if r["branch"] == "full"]
    labels = [
        f"{r['scope']}\n{float(r['frequency_GHz']):g} GHz" for r in selected
    ]
    axes[2].bar(np.arange(len(selected)), [float(r["percent_delta"]) for r in selected])
    axes[2].set_xticks(np.arange(len(selected)), labels, rotation=35, ha="right")
    axes[2].set_ylabel("Log-SG vs unsmoothed (%)")
    axes[2].set_title("Full-branch pressure-method shifts")
    fig.savefig(output, dpi=150)
    plt.close(fig)


def build_synthesis(*, original_csv: Path, census_csv: Path, summary_json: Path, output_dir: Path, target_stratum: str = DEFAULT_TARGET_STRATUM, secondary_stratum: str = DEFAULT_SECONDARY_STRATUM, influential_id: int = INFLUENTIAL_ID) -> dict[str, Any]:
    original_path = _regular(original_csv)
    census_path = _regular(census_csv)
    summary_path = _regular(summary_json)
    try:
        summary = json.loads(summary_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SynthesisError("invalid census summary JSON") from exc
    original = read_rows(original_path)
    census = read_rows(census_path)
    scopes = build_scopes(original, census, target_stratum=target_stratum)
    if int(summary.get("census_count", len(census))) != len(census):
        raise SynthesisError("census summary count does not match CSV")
    if str(summary.get("target_stratum", target_stratum)) != target_stratum:
        raise SynthesisError("census summary target stratum does not match contract")
    output = Path(output_dir).resolve()
    if output.exists() or output.is_symlink():
        raise SynthesisError(f"refusing to overwrite synthesis output: {output}")
    output.mkdir(parents=True)
    branch_rows = branch_frequency_rows(scopes)
    concentration_rows = discrepancy_concentration_rows(scopes)
    attribution_rows = stratum_attribution(scopes, exact_census_stratum=target_stratum)
    sensitivity_rows = influential_history_sensitivity(scopes["hybrid_population"], target_stratum=target_stratum, secondary_stratum=secondary_stratum, influential_id=influential_id)
    stratum_zeroing_rows = stratum_zeroing_sensitivity(
        scopes["hybrid_population"], target_stratum=target_stratum
    )
    contributor_rows = top_hybrid_contributors(scopes["hybrid_population"])
    decision_label, decision_metrics = classify_synthesis(
        concentration_rows,
        attribution_rows,
        sensitivity_rows,
        stratum_zeroing_rows,
        branch_rows,
        target_stratum=target_stratum,
        secondary_stratum=secondary_stratum,
    )
    recommendation_rows = next_step_recommendation_rows(decision_label, decision_metrics)
    write_rows(output / "branch_frequency_comparison.csv", branch_rows)
    write_rows(output / "discrepancy_concentration_curve.csv", concentration_rows)
    write_rows(output / "stratum_attribution.csv", attribution_rows)
    write_rows(output / "influential_history_sensitivity.csv", sensitivity_rows)
    write_rows(output / "stratum_zeroing_sensitivity.csv", stratum_zeroing_rows)
    write_rows(output / "top_hybrid_contributors.csv", contributor_rows)
    write_rows(output / "next_step_recommendation.csv", recommendation_rows)
    _plot(output / "g_lo_pressure_method_synthesis.png", concentration_rows, attribution_rows, branch_rows)
    metadata = {
        "status": "complete_local_synthesis",
        "decision_label": decision_label,
        "decision_metrics": decision_metrics,
        "scientific_scope": "descriptive local synthesis; no physical-uncertainty inference",
        "input_paths": {
            "original_csv": _stable_path(original_path),
            "census_csv": _stable_path(census_path),
            "summary_json": _stable_path(summary_path),
        },
        "input_sha256": {"original_csv": _sha256(original_path), "census_csv": _sha256(census_path), "summary_json": _sha256(summary_path)},
        "scope_row_counts": {scope: len(rows) for scope, rows in scopes.items()},
        "scope_represented_weights": {scope: float(sum(float(row["analysis_weight"]) for row in rows)) for scope, rows in scopes.items()},
        "target_stratum": target_stratum,
        "secondary_stratum": secondary_stratum,
        "influential_id": influential_id,
        "branches": list(BRANCHES),
        "frequencies_GHz": list(FREQUENCIES_GHZ),
        "concentration_fractions": list(CONCENTRATION_FRACTIONS),
        "threshold": float(pressure_method.GATES["max_top_one_percent_discrepancy_fraction"]),
        "ablations_are_not_alternative_estimates": True,
        "remote_compute_performed": False,
        "generated_files": sorted([
            "branch_frequency_comparison.csv",
            "discrepancy_concentration_curve.csv",
            "stratum_attribution.csv",
            "influential_history_sensitivity.csv",
            "stratum_zeroing_sensitivity.csv",
            "top_hybrid_contributors.csv",
            "next_step_recommendation.csv",
            "g_lo_pressure_method_synthesis.png",
            "g_lo_pressure_method_synthesis_metadata.json",
        ]),
    }
    (output / "g_lo_pressure_method_synthesis_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return {"status": metadata["status"], "output_dir": str(output), "metadata": metadata}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-csv", type=Path, default=DEFAULT_INPUT_DIR / "original_particle_comparison.csv")
    parser.add_argument("--census-csv", type=Path, default=DEFAULT_INPUT_DIR / "critical_stratum_particle_comparison.csv")
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_INPUT_DIR / "critical_stratum_census_summary.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-stratum", default=DEFAULT_TARGET_STRATUM)
    parser.add_argument("--secondary-stratum", default=DEFAULT_SECONDARY_STRATUM)
    parser.add_argument("--influential-id", type=int, default=INFLUENTIAL_ID)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_synthesis(original_csv=args.original_csv, census_csv=args.census_csv, summary_json=args.summary_json, output_dir=args.output_dir, target_stratum=args.target_stratum, secondary_stratum=args.secondary_stratum, influential_id=args.influential_id)
    except SynthesisError as exc:
        print(f"Goal 054 synthesis failed: {exc}")
        return 2
    print(f"status={result['status']}")
    print(f"output_dir={result['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
