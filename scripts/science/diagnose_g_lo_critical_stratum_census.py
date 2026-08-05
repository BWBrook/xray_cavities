#!/usr/bin/env python3
"""Exact census of the Goal 051 high-leverage G-LO pressure stratum.

The diagnostic reconstructs the declared Goal 049 stratum from the immutable
history cache, evaluates every member with the stable Goal 051 branches, and
replaces the original weighted stratum estimate with the census in a hybrid
population comparison. It does not generate new simulation or raytracing data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import numpy as np

from scripts.science import diagnose_g_lo_pressure_method_value as pressure_method
from scripts.science import diagnose_g_lo_stable_method_value as stable_method
from scripts.science import run_g_lo_radio_history_value as workflow


TARGET_STRATUM = (
    "affected=1|trim=0|length_q=0|injection_q=0|range_q=1|"
    "shock=post_injection_recent"
)
EXPECTED_CENSUS_COUNT = 262
EXPECTED_ORACLE_COUNT = 17
EXPECTED_CERTAINTY_COUNT = 13
EXPECTED_ORDINARY_COUNT = 249
HIGH_LEVERAGE_IDS = (197253, 197269)
SUCCESS_DECISIONS = {
    "CENSUS_RESOLVES_SAMPLE_LEVERAGE",
    "CENSUS_SUPPORTS_LOCALIZED_REGIME",
    "CENSUS_FINDS_RARE_HISTORY_SENSITIVITY",
}

SELECTION_NAME = "critical_stratum_census_selection.csv"
MEMBERSHIP_NAME = "critical_stratum_membership_summary.csv"
AUDIT_NAME = "sampling_extrapolation_audit.csv"
CONCENTRATION_NAME = "census_concentration_summary.csv"
HYBRID_GATE_NAME = "hybrid_population_gate_summary.csv"
PARTICLE_NAME = "critical_stratum_particle_comparison.csv"
ORDERING_NAME = "critical_stratum_ordering.csv"
CUTOFF_NAME = "census_cutoff_records.csv"
GATE_NAME = "census_gate_summary.csv"
SUMMARY_NAME = "critical_stratum_census_summary.json"
MODE_NPZ_NAMES = {
    "unsmoothed": "critical_stratum_unsmoothed_branches.npz",
    "log_savgol": "critical_stratum_log_savgol_branches.npz",
}

ORACLE_VALUE_FIELDS = tuple(
    f"{mode}_{branch}_{frequency:g}GHz"
    for mode in ("unsmoothed", "log_savgol")
    for branch in ("full", "adiabatic", "none")
    for frequency in stable_method.FREQUENCIES_GHZ
)


class CriticalStratumCensusError(RuntimeError):
    """Raised when census provenance or output contracts fail."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_json_safe(value), indent=2, sort_keys=True) + "\n"
    )


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise CriticalStratumCensusError(f"CSV has no header: {path}")
        rows = list(reader)
    if not rows:
        raise CriticalStratumCensusError(f"CSV has no data rows: {path}")
    return list(reader.fieldnames), rows


def _prepare_output_dir(path: Path) -> Path:
    output = Path(path).resolve()
    if output.exists() or output.is_symlink():
        raise CriticalStratumCensusError(
            f"refusing to overwrite census output: {output}"
        )
    output.mkdir(parents=True)
    return output


def replace_stratum_with_census(
    original_rows: Sequence[Mapping[str, Any]],
    census_rows: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Replace one weighted sample stratum with its exact unit-weight census."""
    original = [dict(row) for row in original_rows]
    census = [dict(row) for row in census_rows]
    target = [
        row for row in original if str(row.get("stratum")) == target_stratum
    ]
    outside = [
        row for row in original if str(row.get("stratum")) != target_stratum
    ]
    if not target or not census:
        raise CriticalStratumCensusError(
            "hybrid replacement requires non-empty sample and census strata"
        )
    if any(str(row.get("stratum")) != target_stratum for row in census):
        raise CriticalStratumCensusError(
            "census rows include a record outside the target stratum"
        )

    def total_weight(rows: Sequence[Mapping[str, Any]]) -> float:
        try:
            values = np.asarray(
                [float(row["analysis_weight"]) for row in rows],
                dtype=np.float64,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CriticalStratumCensusError(
                "hybrid rows contain malformed analysis weights"
            ) from exc
        if (
            values.size == 0
            or not np.all(np.isfinite(values))
            or np.any(values <= 0)
        ):
            raise CriticalStratumCensusError(
                "hybrid analysis weights must be finite and positive"
            )
        return float(np.sum(values))

    original_total = total_weight(original)
    original_target = total_weight(target)
    census_target = total_weight(census)
    if not math.isclose(
        original_target,
        census_target,
        rel_tol=1e-12,
        abs_tol=1e-9,
    ):
        raise CriticalStratumCensusError(
            "census represented mass does not match the sampled stratum"
        )
    hybrid = outside + census
    ids = [int(row["physical_id"]) for row in hybrid]
    if len(ids) != len(set(ids)):
        raise CriticalStratumCensusError(
            "hybrid population evidence contains duplicate physical IDs"
        )
    hybrid_total = total_weight(hybrid)
    if not math.isclose(
        original_total,
        hybrid_total,
        rel_tol=1e-12,
        abs_tol=1e-9,
    ):
        raise CriticalStratumCensusError(
            "hybrid replacement changed represented population mass"
        )
    return hybrid, {
        "original_row_count": len(original),
        "original_target_row_count": len(target),
        "census_target_row_count": len(census),
        "hybrid_row_count": len(hybrid),
        "original_total_represented_weight": original_total,
        "original_target_represented_weight": original_target,
        "census_target_represented_weight": census_target,
        "hybrid_total_represented_weight": hybrid_total,
    }


def classify_census_outcome(
    *,
    hybrid_top_fraction: float,
    census_top_fraction: float,
    cutoff_count: int,
    scientific_gates_passed: bool,
    provenance_passed: bool,
) -> str:
    """Classify the census without changing Goal 051's 0.50 threshold."""
    values = np.asarray(
        [hybrid_top_fraction, census_top_fraction],
        dtype=np.float64,
    )
    if (
        cutoff_count < 0
        or not np.all(np.isfinite(values))
        or np.any(values < 0)
        or np.any(values > 1)
    ):
        raise CriticalStratumCensusError(
            "census classification inputs are invalid"
        )
    if not provenance_passed or not scientific_gates_passed:
        return "FAIL_NUMERICAL_OR_PROVENANCE"
    if cutoff_count:
        return "HOLD_FOR_CUTOFF_REVIEW"
    threshold = pressure_method.GATES[
        "max_top_one_percent_discrepancy_fraction"
    ]
    if hybrid_top_fraction <= threshold:
        return "CENSUS_RESOLVES_SAMPLE_LEVERAGE"
    if census_top_fraction <= threshold:
        return "CENSUS_SUPPORTS_LOCALIZED_REGIME"
    return "CENSUS_FINDS_RARE_HISTORY_SENSITIVITY"


def _normalise_selection_rows(
    rows: Sequence[Mapping[str, str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for expected_index, raw in enumerate(rows):
        try:
            sample_index = int(raw["sample_index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CriticalStratumCensusError(
                "original selection sample_index values are malformed"
            ) from exc
        if sample_index != expected_index:
            raise CriticalStratumCensusError(
                "original selection sample_index order must be exactly 0..n-1"
            )
        result.append({
            **raw,
            "sample_index": sample_index,
            "cache_row": int(raw["cache_row"]),
            "physical_id": int(raw["physical_id"]),
            "analysis_weight": float(raw["analysis_weight"]),
        })
    return result


def _validate_original_row_identity(
    selection: Sequence[Mapping[str, Any]],
    comparison: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Require the original selection and comparison rows to be aligned."""
    if len(selection) != len(comparison):
        raise CriticalStratumCensusError(
            "original selection and comparison row counts differ"
        )
    seen_selection: set[tuple[int, int, int]] = set()
    seen_comparison: set[tuple[int, int, int]] = set()
    for expected_index, (selected, compared) in enumerate(
        zip(selection, comparison, strict=True)
    ):
        try:
            selected_identity = tuple(
                int(selected[field])
                for field in ("sample_index", "cache_row", "physical_id")
            )
            comparison_identity = tuple(
                int(compared[field])
                for field in ("sample_index", "cache_row", "physical_id")
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CriticalStratumCensusError(
                "original selection/comparison identity fields are malformed"
            ) from exc
        if selected_identity[0] != expected_index:
            raise CriticalStratumCensusError(
                "original selection sample_index order is not contiguous"
            )
        if comparison_identity[0] != expected_index:
            raise CriticalStratumCensusError(
                "original comparison sample_index order is not contiguous"
            )
        if selected_identity != comparison_identity:
            raise CriticalStratumCensusError(
                "original selection/comparison row identity mismatch at "
                f"row {expected_index}"
            )
        seen_selection.add(selected_identity)
        seen_comparison.add(comparison_identity)
    if len(seen_selection) != len(selection) or len(seen_comparison) != len(
        comparison
    ):
        raise CriticalStratumCensusError(
            "original selection/comparison rows contain duplicate identities"
        )
    return {
        "row_count": len(selection),
        "identity_fields": ["sample_index", "cache_row", "physical_id"],
        "identity_order": "selection and comparison rows are exactly aligned",
    }


def _validate_oracle_and_annotate(
    census: list[dict[str, Any]],
    original_selection: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
    expected_oracle_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    oracle = [
        row
        for row in original_selection
        if str(row.get("stratum")) == target_stratum
    ]
    if len(oracle) != expected_oracle_count:
        raise CriticalStratumCensusError(
            f"original selection has {len(oracle)} target rows, expected "
            f"{expected_oracle_count}"
        )
    by_cache = {int(row["cache_row"]): row for row in census}
    numeric_fields = (
        "history_length",
        "injection_age",
        "pressure_dynamic_range_log10",
        "shock_age",
        "log_endpoint_relative_difference",
        "min_log_to_raw_ratio",
    )
    for row in oracle:
        cache_row = int(row["cache_row"])
        current = by_cache.get(cache_row)
        if current is None:
            raise CriticalStratumCensusError(
                f"original target cache row {cache_row} is absent from census"
            )
        if (
            int(row["physical_id"]) != int(current["physical_id"])
            or str(row["stratum"]) != str(current["stratum"])
        ):
            raise CriticalStratumCensusError(
                f"original target identity mismatch at cache row {cache_row}"
            )
        for field in numeric_fields:
            if not math.isclose(
                float(row[field]),
                float(current[field]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise CriticalStratumCensusError(
                    f"original target feature mismatch: {cache_row}:{field}"
                )
    oracle_by_cache = {int(row["cache_row"]): row for row in oracle}
    annotated: list[dict[str, Any]] = []
    for row in census:
        original = oracle_by_cache.get(int(row["cache_row"]))
        annotated.append({
            **row,
            "goal051_selected": original is not None,
            "goal051_selection_reason": (
                "" if original is None else original["selection_reason"]
            ),
            "goal051_analysis_weight": (
                "" if original is None else float(original["analysis_weight"])
            ),
        })
    represented_weight = float(
        sum(float(row["analysis_weight"]) for row in oracle)
    )
    if not math.isclose(
        represented_weight,
        float(len(census)),
        rel_tol=1e-12,
        abs_tol=1e-9,
    ):
        raise CriticalStratumCensusError(
            "original target rows do not represent the census population mass"
        )
    return annotated, {
        "oracle_count": len(oracle),
        "oracle_represented_weight": represented_weight,
        "oracle_cache_rows": sorted(int(row["cache_row"]) for row in oracle),
    }


def _branch_inputs_from_particle_rows(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, np.ndarray]]]:
    selection = [dict(row) for row in rows]
    ids = np.asarray(
        [int(row["physical_id"]) for row in selection],
        dtype=np.int64,
    )
    modes: dict[str, dict[str, np.ndarray]] = {}
    for mode in ("unsmoothed", "log_savgol"):
        mode_data: dict[str, np.ndarray] = {"ids": ids}
        for branch in ("full", "adiabatic", "none"):
            mode_data[branch] = np.asarray([
                [
                    float(row[f"{mode}_{branch}_{frequency:g}GHz"])
                    for frequency in stable_method.FREQUENCIES_GHZ
                ]
                for row in selection
            ], dtype=np.float64)
        modes[mode] = mode_data
    return selection, modes


def _per_row_discrepancy(rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([
        sum(
            abs(
                float(row[f"log_savgol_full_{frequency:g}GHz"])
                - float(row[f"unsmoothed_full_{frequency:g}GHz"])
            )
            for frequency in stable_method.FREQUENCIES_GHZ
        )
        for row in rows
    ], dtype=np.float64)


def oracle_replay_tolerance_audit(
    original_rows: Sequence[Mapping[str, Any]],
    census_rows: Sequence[Mapping[str, Any]],
    *,
    target_stratum: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compare preserved Goal 051 oracle cells under the project tolerance.

    The original value is the reference in the established ordering contract:
    ``abs(diff) <= abs(original) * ORDERING_RTOL +
    ORDERING_ULP_MULTIPLIER * max(abs(spacing(original)),
    abs(spacing(census)))``.  Exact replay is retained as an audit statistic,
    but is no longer a gate.
    """
    original_target = [
        dict(row) for row in original_rows
        if str(row.get("stratum")) == target_stratum
    ]
    census_by_id = {int(row["physical_id"]): row for row in census_rows}
    if len(census_by_id) != len(census_rows):
        raise CriticalStratumCensusError("census particle rows contain duplicate IDs")
    audit_rows: list[dict[str, Any]] = []
    mismatch_count = 0
    cell_count = 0
    maximum_abs = 0.0
    maximum_relative = 0.0
    maximum_fraction = 0.0
    within = True
    for original in original_target:
        physical_id = int(original["physical_id"])
        census = census_by_id.get(physical_id)
        if census is None:
            raise CriticalStratumCensusError(
                f"original target physical ID {physical_id} is absent from census"
            )
        row_abs = 0.0
        row_relative = 0.0
        row_fraction = 0.0
        row_mismatches = 0
        row_within = True
        for field in ORACLE_VALUE_FIELDS:
            try:
                reference = float(original[field])
                candidate = float(census[field])
            except (KeyError, TypeError, ValueError) as exc:
                raise CriticalStratumCensusError(
                    f"oracle branch value is malformed for {physical_id}:{field}"
                ) from exc
            if not (math.isfinite(reference) and math.isfinite(candidate)):
                raise CriticalStratumCensusError(
                    f"oracle branch value is non-finite for {physical_id}:{field}"
                )
            difference = abs(candidate - reference)
            ulp = max(abs(float(np.spacing(reference))), abs(float(np.spacing(candidate))))
            tolerance = abs(reference) * pressure_method.ORDERING_RTOL + (
                pressure_method.ORDERING_ULP_MULTIPLIER * ulp
            )
            relative = difference / abs(reference) if reference != 0.0 else (
                0.0 if difference == 0.0 else math.inf
            )
            fraction = difference / tolerance if tolerance > 0.0 else (
                0.0 if difference == 0.0 else math.inf
            )
            exact = difference == 0.0
            passed = difference <= tolerance
            cell_count += 1
            mismatch_count += int(not exact)
            row_mismatches += int(not exact)
            row_abs = max(row_abs, difference)
            row_relative = max(row_relative, relative)
            row_fraction = max(row_fraction, fraction)
            maximum_abs = max(maximum_abs, difference)
            maximum_relative = max(maximum_relative, relative)
            maximum_fraction = max(maximum_fraction, fraction)
            row_within = row_within and passed
            within = within and passed
        audit_rows.append({
            "cache_row": int(original["cache_row"]),
            "physical_id": physical_id,
            "goal051_selection_reason": original.get("selection_reason", ""),
            "goal051_analysis_weight": float(original["analysis_weight"]),
            "census_analysis_weight": 1.0,
            "stable_branch_replay_exact_mismatch_count": row_mismatches,
            "stable_branch_replay_within_tolerance": row_within,
            "stable_branch_replay_max_abs_difference": row_abs,
            "stable_branch_replay_max_relative_difference": row_relative,
            "stable_branch_replay_max_tolerance_fraction": row_fraction,
            "high_leverage_goal051_id": physical_id in HIGH_LEVERAGE_IDS,
        })
    metadata = {
        "oracle_count": len(original_target),
        "oracle_cell_count": cell_count,
        "stable_branch_replay_exact_mismatch_count": mismatch_count,
        "stable_branch_replay_within_tolerance": within,
        "stable_branch_replay_max_abs_difference": maximum_abs,
        "stable_branch_replay_max_relative_difference": maximum_relative,
        "stable_branch_replay_max_tolerance_fraction": maximum_fraction,
        "stable_branch_replay_tolerance": {
            "relative_tolerance": pressure_method.ORDERING_RTOL,
            "ulp_multiplier": pressure_method.ORDERING_ULP_MULTIPLIER,
            "formula": (
                "abs(diff) <= abs(original) * relative_tolerance + "
                "ulp_multiplier * max(abs(spacing(original)), abs(spacing(census)))"
            ),
        },
    }
    if not within:
        raise CriticalStratumCensusError(
            "Goal 051 oracle stable branches exceed the project equivalence tolerance"
        )
    return audit_rows, metadata


def _copy_stable_outputs(
    core_dir: Path,
    output_dir: Path,
    *,
    selection_hash: str,
) -> dict[str, Any]:
    source_names = {
        stable_method.PARTICLE_NAME: PARTICLE_NAME,
        stable_method.ORDERING_NAME: ORDERING_NAME,
        stable_method.CUTOFF_NAME: CUTOFF_NAME,
        stable_method.GATE_NAME: GATE_NAME,
    }
    for source, target in source_names.items():
        source_path = core_dir / source
        if not source_path.is_file():
            raise CriticalStratumCensusError(
                f"stable core omitted required output: {source}"
            )
        shutil.copyfile(source_path, output_dir / target)
    fingerprint = hashlib.sha256(
        f"goal053:{selection_hash}".encode()
    ).hexdigest()
    for mode, target_name in MODE_NPZ_NAMES.items():
        source = core_dir / f"stable_method_value_{mode}_branches.npz"
        if not source.is_file():
            raise CriticalStratumCensusError(
                f"stable core omitted branch checkpoint: {source.name}"
            )
        with np.load(source, allow_pickle=False) as arrays:
            payload = {
                "physical_ids": np.asarray(
                    arrays["physical_ids"],
                    dtype=np.int64,
                ),
                "frequencies": np.asarray(
                    arrays["frequencies_GHz"],
                    dtype=np.float64,
                ),
                "full": np.asarray(arrays["full"], dtype=np.float64),
                "adiabatic": np.asarray(
                    arrays["adiabatic"],
                    dtype=np.float64,
                ),
                "none": np.asarray(arrays["none"], dtype=np.float64),
                "input_fingerprint": np.asarray(fingerprint),
            }
        stable_method._write_deterministic_npz(
            output_dir / target_name,
            payload,
        )
    return {
        "stable_core_summary": json.loads(
            (core_dir / stable_method.SUMMARY_NAME).read_text()
        ),
        "input_fingerprint": fingerprint,
    }


def _propagate_stable_failure(
    core_dir: Path,
    output_dir: Path,
    *,
    selection_hash: str,
    observed_hashes: Mapping[str, str],
    cache_validation: Mapping[str, Any],
    pressure_treatment_identity_sha256: str,
    census_selection: Sequence[Mapping[str, Any]],
    census_metadata: Mapping[str, Any],
    oracle_metadata: Mapping[str, Any],
    target_stratum: str,
    expected_oracle_count: int,
    expected_certainty_count: int,
    expected_ordinary_count: int,
) -> dict[str, Any]:
    """Carry a stable-core scientific FAIL forward without inventing outputs."""
    core_summary_path = core_dir / stable_method.SUMMARY_NAME
    core_cutoff_path = core_dir / stable_method.CUTOFF_NAME
    core_gate_path = core_dir / stable_method.GATE_NAME
    if not all(path.is_file() for path in (
        core_summary_path,
        core_cutoff_path,
        core_gate_path,
    )):
        raise CriticalStratumCensusError(
            "stable core scientific failure omitted cutoff/gate evidence"
        )
    stable_summary = json.loads(core_summary_path.read_text())
    if stable_summary.get("decision") != "FAIL":
        raise CriticalStratumCensusError(
            "stable failure propagation requires a structured FAIL summary"
        )
    shutil.copyfile(core_cutoff_path, output_dir / CUTOFF_NAME)
    shutil.copyfile(core_gate_path, output_dir / GATE_NAME)
    certainty_count = sum(
        any(
            reason in str(row.get("selection_reason", ""))
            for reason in (
                "all_short_histories",
                "extreme_abs_log_endpoint_perturbation",
                "extreme_min_log_raw_ratio",
            )
        )
        for row in census_selection
    )
    summary = {
        "status": "diagnostic_complete",
        "decision": "FAIL_NUMERICAL_OR_PROVENANCE",
        "decision_label": "FAIL_NUMERICAL_OR_PROVENANCE",
        "target_stratum": target_stratum,
        "census_count": len(census_selection),
        "oracle_count": expected_oracle_count,
        "certainty_count": certainty_count,
        "ordinary_count": len(census_selection) - certainty_count,
        "immutable_input_sha256": dict(observed_hashes),
        "cache_validation": dict(cache_validation),
        "pressure_treatment_identity_sha256": pressure_treatment_identity_sha256,
        "selection_sha256": selection_hash,
        "census_metadata": dict(census_metadata),
        "oracle_metadata": dict(oracle_metadata),
        "stable_core_decision": stable_summary.get("decision"),
        "stable_core_decision_label": stable_summary.get("decision_label"),
        "stable_core_summary": stable_summary,
        "stable_core_failure_evidence": {
            "cutoff_records_path": CUTOFF_NAME,
            "gate_summary_path": GATE_NAME,
            "cutoff_count": int(stable_summary.get("cutoff_count", 0)),
            "failed_gate": stable_summary.get(
                "scientific_failure", {}
            ).get("details", {}).get("failed_gate"),
        },
        "expected_contract": {
            "expected_census_count": expected_certainty_count + expected_ordinary_count,
            "expected_oracle_count": expected_oracle_count,
            "expected_certainty_count": expected_certainty_count,
            "expected_ordinary_count": expected_ordinary_count,
        },
        "failure_semantics": (
            "stable-core scientific failure is propagated as a Goal 053 "
            "numerical/provenance FAIL; branch arrays and downstream census "
            "comparison outputs are intentionally absent"
        ),
    }
    _write_json(output_dir / SUMMARY_NAME, summary)
    return {
        "status": "diagnostic_complete",
        "decision": "FAIL_NUMERICAL_OR_PROVENANCE",
        "decision_label": "FAIL_NUMERICAL_OR_PROVENANCE",
        "summary_json": str(output_dir / SUMMARY_NAME),
        "cutoff_records_path": str(output_dir / CUTOFF_NAME),
        "summary_csv": str(output_dir / GATE_NAME),
    }


def diagnose_critical_stratum_census(
    cache: Path,
    affected_rows_csv: Path,
    original_selection_csv: Path,
    original_comparison_csv: Path,
    output_dir: Path,
    *,
    expected_cache_sha256: str,
    expected_affected_rows_sha256: str,
    expected_original_selection_sha256: str,
    expected_original_comparison_sha256: str,
    expected_census_count: int = EXPECTED_CENSUS_COUNT,
    expected_oracle_count: int = EXPECTED_ORACLE_COUNT,
    expected_certainty_count: int = EXPECTED_CERTAINTY_COUNT,
    expected_ordinary_count: int = EXPECTED_ORDINARY_COUNT,
    target_stratum: str = TARGET_STRATUM,
) -> dict[str, Any]:
    """Run the exact stratum census and hybrid population replacement."""
    paths = [
        Path(value)
        for value in (
            cache,
            affected_rows_csv,
            original_selection_csv,
            original_comparison_csv,
        )
    ]
    if any(path.is_symlink() for path in paths):
        raise CriticalStratumCensusError(
            "Goal 053 inputs must not be symlinks"
        )
    if any(not path.is_file() for path in paths):
        raise CriticalStratumCensusError(
            "all Goal 053 inputs must be regular files"
        )
    cache, affected_rows_csv, original_selection_csv, original_comparison_csv = (
        path.resolve() for path in paths
    )
    observed_hashes = {
        "cache": _sha256_file(cache),
        "affected_rows": _sha256_file(affected_rows_csv),
        "original_selection": _sha256_file(original_selection_csv),
        "original_comparison": _sha256_file(original_comparison_csv),
    }
    expected_hashes = {
        "cache": expected_cache_sha256,
        "affected_rows": expected_affected_rows_sha256,
        "original_selection": expected_original_selection_sha256,
        "original_comparison": expected_original_comparison_sha256,
    }
    if observed_hashes != expected_hashes:
        mismatches = sorted(
            key
            for key in expected_hashes
            if observed_hashes[key] != expected_hashes[key]
        )
        raise CriticalStratumCensusError(
            f"immutable input SHA-256 mismatch: {mismatches}"
        )
    output_dir = _prepare_output_dir(output_dir)
    affected = pressure_method._read_affected_rows(affected_rows_csv)
    with h5py.File(cache, "r") as h5:
        cache_validation = workflow._validate_completed_cache(h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                "expected_trim_rows"
            ],
            expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                "expected_no_positive_rows"
            ],
            expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                "expected_single_record_rows"
            ],
            expected_trim_single_record_overlap_rows=(
                workflow.PRESSURE_TREATMENT_CONTRACT[
                    "expected_trim_single_record_overlap_rows"
                ]
            ),
        )
        _selected, census_selection, census_metadata = (
            pressure_method.construct_stratum_census(
                h5,
                plan,
                affected,
                target_stratum=target_stratum,
                expected_count=expected_census_count,
                expected_certainty_count=expected_certainty_count,
                expected_ordinary_count=expected_ordinary_count,
            )
        )
    _selection_fields, original_selection_raw = _read_csv(
        original_selection_csv
    )
    original_selection = _normalise_selection_rows(original_selection_raw)
    census_selection, oracle_metadata = _validate_oracle_and_annotate(
        census_selection,
        original_selection,
        target_stratum=target_stratum,
        expected_oracle_count=expected_oracle_count,
    )
    selection_fields = [
        *pressure_method.SELECTION_FIELDS,
        "goal051_selected",
        "goal051_selection_reason",
        "goal051_analysis_weight",
    ]
    selection_path = output_dir / SELECTION_NAME
    _write_csv(selection_path, selection_fields, census_selection)
    selection_hash = _sha256_file(selection_path)

    _original_fields, original_particle_raw = _read_csv(
        original_comparison_csv
    )
    original_particle = [dict(row) for row in original_particle_raw]
    original_identity = _validate_original_row_identity(
        original_selection,
        original_particle,
    )

    with tempfile.TemporaryDirectory(
        prefix="goal053_stable_core_",
        dir=output_dir.parent,
    ) as temporary:
        core_dir = Path(temporary) / "stable"
        stable_result = stable_method.diagnose_stable_method_value(
            cache,
            selection_path,
            core_dir,
            expected_cache_sha256=expected_cache_sha256,
            expected_selection_sha256=selection_hash,
            expected_selection_count=expected_census_count,
        )
        if stable_result.get("decision") == "FAIL":
            return _propagate_stable_failure(
                core_dir,
                output_dir,
                selection_hash=selection_hash,
                observed_hashes=observed_hashes,
                cache_validation=cache_validation,
                pressure_treatment_identity_sha256=plan["identity_sha256"],
                census_selection=census_selection,
                census_metadata=census_metadata,
                oracle_metadata={
                    **oracle_metadata,
                    "original_row_identity": original_identity,
                },
                target_stratum=target_stratum,
                expected_oracle_count=expected_oracle_count,
                expected_certainty_count=expected_certainty_count,
                expected_ordinary_count=expected_ordinary_count,
            )
        stable_evidence = _copy_stable_outputs(
            core_dir,
            output_dir,
            selection_hash=selection_hash,
        )

    _census_fields, census_particle_raw = _read_csv(
        output_dir / PARTICLE_NAME
    )
    census_particle = [dict(row) for row in census_particle_raw]
    hybrid_rows, replacement_audit = replace_stratum_with_census(
        original_particle,
        census_particle,
        target_stratum=target_stratum,
    )
    hybrid_selection, hybrid_modes = _branch_inputs_from_particle_rows(
        hybrid_rows
    )
    _hybrid_particle_rows, hybrid_comparison = (
        pressure_method.summarise_method_comparison(
            hybrid_selection,
            hybrid_modes["unsmoothed"],
            hybrid_modes["log_savgol"],
        )
    )
    census_selection_for_summary, census_modes = (
        _branch_inputs_from_particle_rows(census_particle)
    )
    _census_rows_check, census_comparison = (
        pressure_method.summarise_method_comparison(
            census_selection_for_summary,
            census_modes["unsmoothed"],
            census_modes["log_savgol"],
        )
    )

    census_by_id = {
        int(row["physical_id"]): row for row in census_particle
    }
    census_discrepancy = _per_row_discrepancy(census_particle)
    rank_order = np.lexsort(
        (np.arange(len(census_particle)), -census_discrepancy)
    )
    ranks = {
        int(census_particle[index]["physical_id"]): rank + 1
        for rank, index in enumerate(rank_order)
    }
    original_target = [
        row
        for row in original_particle
        if str(row["stratum"]) == target_stratum
    ]
    audit_rows, oracle_replay_metadata = oracle_replay_tolerance_audit(
        original_particle,
        census_particle,
        target_stratum=target_stratum,
    )
    for row in audit_rows:
        physical_id = int(row["physical_id"])
        row["census_discrepancy_rank"] = ranks[physical_id]
        row["census_per_particle_discrepancy"] = float(
            census_discrepancy[
                next(
                    index
                    for index, candidate in enumerate(census_particle)
                    if int(candidate["physical_id"]) == physical_id
                )
            ]
        )

    concentration_rows: list[dict[str, Any]] = []
    for scope, rows in (
        ("critical_stratum_census", census_particle),
        ("hybrid_population", hybrid_rows),
    ):
        discrepancy = _per_row_discrepancy(rows)
        weights = np.asarray(
            [float(row["analysis_weight"]) for row in rows],
            dtype=np.float64,
        )
        for fraction in (0.001, 0.01, 0.05, 0.10):
            value = (
                pressure_method.represented_population_discrepancy_concentration(
                    discrepancy,
                    weights,
                    population_fraction=fraction,
                )
            )
            concentration_rows.append({
                "scope": scope,
                "population_fraction": fraction,
                "discrepancy_fraction": value["fraction"],
                "represented_population_weight": value[
                    "represented_population_weight"
                ],
                "target_population_weight": value[
                    "target_population_weight"
                ],
                "fully_included_rows": value["fully_included_rows"],
                "fractional_boundary_row_index": value[
                    "fractional_boundary_row_index"
                ],
                "fractional_boundary_row_weight_fraction": value[
                    "fractional_boundary_row_weight_fraction"
                ],
            })
    census_top = float(
        census_comparison[
            "top_one_percent_absolute_discrepancy_fraction"
        ]
    )
    hybrid_top = float(
        hybrid_comparison[
            "top_one_percent_absolute_discrepancy_fraction"
        ]
    )
    stable_summary = stable_evidence["stable_core_summary"]
    stable_nonconcentration_gates = {
        key: bool(value)
        for key, value in stable_summary.get("stable_gates", {}).items()
        if key != "comparison_discrepancy_concentration"
    }
    hybrid_nonconcentration_gates = {
        key: bool(value)
        for key, value in hybrid_comparison["gate_results"].items()
        if key != "discrepancy_concentration"
    }
    scientific_gates_passed = all(stable_nonconcentration_gates.values()) and all(
        hybrid_nonconcentration_gates.values()
    )
    cutoff_count = int(stable_summary.get("cutoff_count", 0))
    decision = classify_census_outcome(
        hybrid_top_fraction=hybrid_top,
        census_top_fraction=census_top,
        cutoff_count=cutoff_count,
        scientific_gates_passed=scientific_gates_passed,
        provenance_passed=True,
    )

    certainty_count = sum(
        any(
            reason in str(row["selection_reason"])
            for reason in (
                "all_short_histories",
                "extreme_abs_log_endpoint_perturbation",
                "extreme_min_log_raw_ratio",
            )
        )
        for row in census_selection
    )
    membership_rows = [
        {"metric": "census_count", "value": expected_census_count},
        {"metric": "oracle_count", "value": expected_oracle_count},
        {"metric": "certainty_count", "value": certainty_count},
        {
            "metric": "ordinary_count",
            "value": expected_census_count - certainty_count,
        },
        {
            "metric": "minimum_history_length",
            "value": min(int(row["history_length"]) for row in census_selection),
        },
        {
            "metric": "maximum_history_length",
            "value": max(int(row["history_length"]) for row in census_selection),
        },
        {
            "metric": "target_stratum",
            "value": target_stratum,
        },
    ]
    hybrid_gate_rows = [
        {
            "gate": gate,
            "passed": bool(passed),
            "value": json.dumps(_json_safe(passed), sort_keys=True),
        }
        for gate, passed in hybrid_comparison["gate_results"].items()
    ]
    hybrid_gate_rows.append({
        "gate": "top_one_percent_absolute_discrepancy_fraction",
        "passed": hybrid_top <= pressure_method.GATES[
            "max_top_one_percent_discrepancy_fraction"
        ],
        "value": hybrid_top,
    })
    gate_rows = [
        {
            "scope": "provenance",
            "gate": "immutable_input_hashes",
            "passed": True,
            "value": json.dumps(observed_hashes, sort_keys=True),
        },
        {
            "scope": "membership",
            "gate": "exact_census_contract",
            "passed": (
                len(census_selection) == expected_census_count
                and len(original_target) == expected_oracle_count
                and certainty_count == expected_certainty_count
            ),
            "value": (
                f"{len(census_selection)}/{len(original_target)}/"
                f"{certainty_count}"
            ),
        },
        {
            "scope": "oracle",
            "gate": "goal051_branch_replay",
            "passed": oracle_replay_metadata[
                "stable_branch_replay_within_tolerance"
            ],
            "value": json.dumps(oracle_replay_metadata, sort_keys=True),
        },
    ]
    gate_rows.extend({
            "scope": "stable_core",
            "gate": gate,
            "passed": passed,
            "value": json.dumps(passed),
        }
        for gate, passed in stable_nonconcentration_gates.items()
    )
    gate_rows.extend({
        "scope": "hybrid_population",
        "gate": gate,
        "passed": passed,
        "value": json.dumps(passed),
    } for gate, passed in hybrid_nonconcentration_gates.items())
    gate_rows.append({
        "scope": "decision",
        "gate": "census_classification_complete",
        "passed": decision in SUCCESS_DECISIONS,
        "value": decision,
    })
    _write_csv(
        output_dir / MEMBERSHIP_NAME,
        ("metric", "value"),
        membership_rows,
    )
    _write_csv(
        output_dir / AUDIT_NAME,
        (
            "cache_row",
            "physical_id",
            "goal051_selection_reason",
            "goal051_analysis_weight",
            "census_analysis_weight",
            "census_discrepancy_rank",
            "census_per_particle_discrepancy",
            "stable_branch_replay_exact_mismatch_count",
            "stable_branch_replay_within_tolerance",
            "stable_branch_replay_max_abs_difference",
            "stable_branch_replay_max_relative_difference",
            "stable_branch_replay_max_tolerance_fraction",
            "high_leverage_goal051_id",
        ),
        audit_rows,
    )
    _write_csv(
        output_dir / CONCENTRATION_NAME,
        (
            "scope",
            "population_fraction",
            "discrepancy_fraction",
            "represented_population_weight",
            "target_population_weight",
            "fully_included_rows",
            "fractional_boundary_row_index",
            "fractional_boundary_row_weight_fraction",
        ),
        concentration_rows,
    )
    _write_csv(
        output_dir / HYBRID_GATE_NAME,
        ("gate", "passed", "value"),
        hybrid_gate_rows,
    )
    _write_csv(
        output_dir / GATE_NAME,
        ("scope", "gate", "passed", "value"),
        gate_rows,
    )
    summary = {
        "status": "diagnostic_complete",
        "decision": decision,
        "decision_label": decision,
        "target_stratum": target_stratum,
        "census_count": len(census_selection),
        "oracle_count": len(original_target),
        "certainty_count": certainty_count,
        "ordinary_count": len(census_selection) - certainty_count,
        "inference_scope": (
            "exact census of the declared 262-history stratum plus a hybrid "
            "population estimate retaining Goal 051 samples outside that stratum"
        ),
        "goal051_historical_status": (
            "formal predeclared discrepancy-concentration gate remains FAIL"
        ),
        "immutable_input_sha256": observed_hashes,
        "cache_validation": cache_validation,
        "pressure_treatment_identity_sha256": plan["identity_sha256"],
        "selection_sha256": selection_hash,
        "census_metadata": census_metadata,
        "oracle_metadata": oracle_metadata,
        "oracle_replay_tolerance": oracle_replay_metadata,
        "original_row_identity": original_identity,
        "replacement_audit": replacement_audit,
        "census_top_one_percent_discrepancy_fraction": census_top,
        "hybrid_top_one_percent_discrepancy_fraction": hybrid_top,
        "predeclared_threshold": pressure_method.GATES[
            "max_top_one_percent_discrepancy_fraction"
        ],
        "stable_nonconcentration_gates": stable_nonconcentration_gates,
        "hybrid_nonconcentration_gates": hybrid_nonconcentration_gates,
        "cutoff_count": cutoff_count,
        "high_leverage_goal051_ids": list(HIGH_LEVERAGE_IDS),
        "high_leverage_census_ranks": {
            str(value): ranks.get(value) for value in HIGH_LEVERAGE_IDS
        },
        "stable_core_decision": stable_result.get("decision"),
        "stable_core_decision_label": stable_result.get("decision_label"),
        "stable_core_input_fingerprint": stable_evidence["input_fingerprint"],
        "decision_semantics": {
            "CENSUS_RESOLVES_SAMPLE_LEVERAGE": (
                "hybrid population concentration is at or below 0.50"
            ),
            "CENSUS_SUPPORTS_LOCALIZED_REGIME": (
                "hybrid remains above 0.50 but census-stratum concentration "
                "is at or below 0.50; this is evidence consistent with a "
                "distributed localized sensitivity, not proof that the "
                "target stratum causes the hybrid discrepancy"
            ),
            "CENSUS_FINDS_RARE_HISTORY_SENSITIVITY": (
                "hybrid and census-stratum concentration both remain above 0.50"
            ),
            "HOLD_FOR_CUTOFF_REVIEW": "verified stable recurrence cutoff present",
            "FAIL_NUMERICAL_OR_PROVENANCE": (
                "an inherited numerical, scientific, or provenance gate failed"
            ),
        },
    }
    _write_json(output_dir / SUMMARY_NAME, summary)
    return {
        "status": "diagnostic_complete",
        "decision": decision,
        "summary_json": str(output_dir / SUMMARY_NAME),
        "selection_path": str(selection_path),
        "census_count": len(census_selection),
        "hybrid_top_one_percent_discrepancy_fraction": hybrid_top,
        "census_top_one_percent_discrepancy_fraction": census_top,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--affected-rows-csv", type=Path, required=True)
    parser.add_argument("--original-selection-csv", type=Path, required=True)
    parser.add_argument("--original-comparison-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-cache-sha256", required=True)
    parser.add_argument("--expected-affected-rows-sha256", required=True)
    parser.add_argument("--expected-original-selection-sha256", required=True)
    parser.add_argument("--expected-original-comparison-sha256", required=True)
    parser.add_argument(
        "--expected-census-count",
        type=int,
        default=EXPECTED_CENSUS_COUNT,
    )
    parser.add_argument(
        "--expected-oracle-count",
        type=int,
        default=EXPECTED_ORACLE_COUNT,
    )
    parser.add_argument(
        "--expected-certainty-count",
        type=int,
        default=EXPECTED_CERTAINTY_COUNT,
    )
    parser.add_argument(
        "--expected-ordinary-count",
        type=int,
        default=EXPECTED_ORDINARY_COUNT,
    )
    parser.add_argument("--target-stratum", default=TARGET_STRATUM)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = diagnose_critical_stratum_census(
            args.cache,
            args.affected_rows_csv,
            args.original_selection_csv,
            args.original_comparison_csv,
            args.output_dir,
            expected_cache_sha256=args.expected_cache_sha256,
            expected_affected_rows_sha256=(
                args.expected_affected_rows_sha256
            ),
            expected_original_selection_sha256=(
                args.expected_original_selection_sha256
            ),
            expected_original_comparison_sha256=(
                args.expected_original_comparison_sha256
            ),
            expected_census_count=args.expected_census_count,
            expected_oracle_count=args.expected_oracle_count,
            expected_certainty_count=args.expected_certainty_count,
            expected_ordinary_count=args.expected_ordinary_count,
            target_stratum=args.target_stratum,
        )
    except (
        OSError,
        TypeError,
        ValueError,
        workflow.WorkflowError,
        pressure_method.PressureMethodDiagnosticError,
        stable_method.StableMethodDiagnosticError,
        CriticalStratumCensusError,
    ) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(_json_safe(result), indent=2, sort_keys=True))
    return 0 if result["decision"] in SUCCESS_DECISIONS else 3


if __name__ == "__main__":
    raise SystemExit(main())
