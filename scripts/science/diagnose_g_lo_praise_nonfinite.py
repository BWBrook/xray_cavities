#!/usr/bin/env python3
"""Forensic replay of non-finite endpoint emissivities from actual PRAiSE.

This diagnostic reuses Goal 049's immutable cache, pressure-treatment plan, and
deterministic 4096-row sample.  It records the upstream result for each
pressure mode without replacing, clipping, zeroing, or censoring any value.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from scripts.science import diagnose_g_lo_pressure_method_value as base
from scripts.science import run_g_lo_radio_history_value as workflow
from scripts.science.g_lo_radio_method_value import calculate_praise_pair


MODES = ("unsmoothed", "log_savgol")
DECISIONS = (
    "CUTOFF_ZERO_POLICY_ELIGIBLE",
    "PRAISE_NUMERICS_BLOCKED",
    "NO_NONFINITE_REPRODUCED",
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(base._json_safe(value), indent=2, sort_keys=True) + "\n")


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _record_fields(records: Sequence[Mapping[str, Any]]) -> list[str]:
    preferred = [
        "pressure_mode", "loss_branch", "start_index", "dense_row", "physical_id",
        "frequency_GHz", "output_class", "matched_lossless_output_class",
        "replay_verified", "finite_inputs_dynamics", "shock_assignment_valid",
        "shock_index", "no_emission_index", "no_emission", "endpoint_pressure_Pa",
        "injection_pressure_Pa", "endpoint_tracer", "current_lorentz",
        "injection_lorentz", "classification",
    ]
    extras = sorted({key for row in records for key in row} - set(preferred))
    return [key for key in preferred if any(key in row for row in records)] + extras


def classify_forensic_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply the fail-closed cutoff decision contract to replay records."""
    nonfinite = [row for row in records if row.get("output_class") != "finite"]
    lossless_nonfinite = [
        row for row in records
        if row.get("loss_branch") == "none" and row.get("output_class") != "finite"
    ]
    proven = [
        row for row in nonfinite
        if row.get("classification") == "proven_full_loss_cutoff"
    ]
    if not nonfinite:
        decision = "NO_NONFINITE_REPRODUCED"
    elif len(proven) == len(nonfinite) and not lossless_nonfinite:
        decision = "CUTOFF_ZERO_POLICY_ELIGIBLE"
    else:
        decision = "PRAISE_NUMERICS_BLOCKED"
    by_mode = {}
    for mode in MODES:
        mode_rows = [row for row in records if row.get("pressure_mode") == mode]
        mode_nonfinite = [row for row in mode_rows if row.get("output_class") != "finite"]
        by_mode[mode] = {
            "record_count": len(mode_rows),
            "nonfinite_count": len(mode_nonfinite),
            "full_loss_nonfinite_count": sum(
                row.get("loss_branch") == "full" for row in mode_nonfinite
            ),
            "lossless_nonfinite_count": sum(
                row.get("loss_branch") == "none" for row in mode_nonfinite
            ),
            "proven_full_loss_cutoff_count": sum(
                row.get("classification") == "proven_full_loss_cutoff"
                for row in mode_nonfinite
            ),
        }
    return {
        "decision": decision,
        "record_count": len(records),
        "nonfinite_count": len(nonfinite),
        "proven_full_loss_cutoff_count": len(proven),
        "unresolved_nonfinite_count": sum(
            row.get("classification") == "unresolved_nonfinite" for row in nonfinite
        ),
        "lossless_nonfinite_count": len(lossless_nonfinite),
        "all_lossless_cells_finite": not lossless_nonfinite,
        "replacement_policy": (
            "No emissivity is zeroed, clipped, censored, dropped, or otherwise "
            "replaced by this forensic diagnostic."
        ),
        "by_pressure_mode": by_mode,
    }


def diagnose_praise_nonfinite(
    cache: Path,
    affected_rows_csv: Path,
    output_dir: Path,
    *,
    sample_size: int = base.SAMPLE_SIZE,
    row_chunk: int = 512,
    expected_trim_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
    expected_no_positive_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
    expected_single_record_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
) -> dict[str, Any]:
    cache = Path(cache).resolve()
    affected_rows_csv = Path(affected_rows_csv).resolve()
    output_dir = Path(output_dir).resolve()
    if not cache.is_file() or cache.is_symlink():
        raise base.PressureMethodDiagnosticError(f"cache must be a regular file: {cache}")
    if not affected_rows_csv.is_file() or affected_rows_csv.is_symlink():
        raise base.PressureMethodDiagnosticError(
            f"affected-row evidence must be a regular file: {affected_rows_csv}"
        )
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise base.PressureMethodDiagnosticError(
                f"refusing to overwrite non-empty output directory: {output_dir}"
            )
    else:
        output_dir.mkdir(parents=True)

    affected = base._read_affected_rows(affected_rows_csv)
    with h5py.File(cache, "r") as h5:
        workflow._validate_completed_cache(h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=expected_trim_rows,
            expected_no_positive_rows=expected_no_positive_rows,
            expected_single_record_rows=expected_single_record_rows,
            row_chunk=row_chunk,
        )
        selected_rows, selection, selection_metadata = base.construct_deterministic_sample(
            h5, plan, affected, sample_size=sample_size, row_chunk=row_chunk
        )
        raw = base._read_treated_sample(h5, selected_rows, plan)
        physical, units = workflow.convert_code_cache_to_physical(
            raw,
            shock_threshold=float(h5.attrs["shock_threshold"]),
            shock_component=int(h5.attrs["shock_component"]),
        )
        cache_identity = workflow._cache_identity(cache)

    # This is intentionally the first output: selection is auditable even if a
    # later upstream PRAiSE call fails.
    selection_path = output_dir / "praise_forensic_selection.csv"
    _write_csv(selection_path, base.SELECTION_FIELDS, selection)
    _write_json(output_dir / "praise_forensic_selection_metadata.json", {
        "status": "selection_complete",
        "cache_identity": cache_identity,
        "affected_rows_csv_sha256": workflow._sha256_file(affected_rows_csv),
        "pressure_treatment_identity_sha256": plan["identity_sha256"],
        "pressure_treatment_counts": {
            "trim_rows": int(len(plan["trim_rows"])),
            "excluded_rows": int(len(plan["excluded_rows"])),
        },
        "selection": selection_metadata,
        "unit_provenance": units,
        "replacement_policy": "no values are replaced by this diagnostic",
    })

    kwargs = {
        "frequencies": base.FREQUENCIES_GHZ,
        "z": workflow.PRIMARY_CONTRACT["redshift"],
        "s": workflow.PRIMARY_CONTRACT["s"],
        "eta": workflow.PRIMARY_CONTRACT["eta"],
        "gmin": workflow.PRIMARY_CONTRACT["gmin"],
        "gmax": workflow.PRIMARY_CONTRACT["gmax"],
        "lst_index": 0,
        "diagnostic": True,
    }
    all_records: list[dict[str, Any]] = []
    mode_summaries: dict[str, Any] = {}
    for mode in MODES:
        checkpoint_path = output_dir / f"praise_forensic_{mode}_checkpoint.json"
        records_path = output_dir / f"praise_forensic_{mode}_records.csv"
        try:
            result = calculate_praise_pair(
                physical,
                pressure_mode=mode,
                singleton_policy="instantaneous_recent_shock",
                **kwargs,
            )
            diagnostics = result.get("nonfinite_diagnostics", {})
            records = [dict(row) for row in diagnostics.get("records", [])]
            expected_records = len(selection) * 2 * len(base.FREQUENCIES_GHZ)
            if len(records) != expected_records:
                raise base.PressureMethodDiagnosticError(
                    f"{mode} forensic record count {len(records)} != expected {expected_records}"
                )
            all_records.extend(records)
            mode_summary = {
                "status": "mode_complete",
                "pressure_mode": mode,
                "record_count": len(records),
                "nonfinite": bool(diagnostics.get("nonfinite", False)),
                "nonfinite_diagnostics": diagnostics,
                "metadata": result.get("metadata", {}),
            }
            mode_summaries[mode] = mode_summary
            _write_csv(records_path, _record_fields(records), records)
            _write_json(checkpoint_path, mode_summary)
        except Exception as exc:
            # Preserve a machine-readable checkpoint before propagating; no
            # scientific result is accepted from an incomplete mode.
            mode_summary = {
                "status": "mode_failed",
                "pressure_mode": mode,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "replacement_policy": "no values are replaced by this diagnostic",
            }
            _write_csv(records_path, ("pressure_mode", "status"), [{"pressure_mode": mode, "status": "mode_failed"}])
            _write_json(checkpoint_path, mode_summary)
            raise

    forensic_path = output_dir / "praise_forensic_records.csv"
    _write_csv(forensic_path, _record_fields(all_records), all_records)
    decision = classify_forensic_records(all_records)
    summary = {
        "status": "forensic_diagnostic_complete",
        "decision": decision["decision"],
        "cache_identity": cache_identity,
        "affected_rows_csv_sha256": workflow._sha256_file(affected_rows_csv),
        "selection": selection_metadata,
        "pressure_treatment_identity_sha256": plan["identity_sha256"],
        "pressure_treatment_counts": {
            "trim_rows": int(len(plan["trim_rows"])),
            "excluded_rows": int(len(plan["excluded_rows"])),
        },
        "pressure_modes": mode_summaries,
        "decision_summary": decision,
        "replacement_policy": (
            "Forensic classification only; no emissivity is zeroed, clipped, "
            "censored, dropped, or substituted."
        ),
    }
    summary_json = output_dir / "praise_forensic_summary.json"
    _write_json(summary_json, summary)
    decision_rows = [
        {"metric": key, "value": value}
        for key, value in (
            ("decision", decision["decision"]),
            ("record_count", decision["record_count"]),
            ("nonfinite_count", decision["nonfinite_count"]),
            ("proven_full_loss_cutoff_count", decision["proven_full_loss_cutoff_count"]),
            ("unresolved_nonfinite_count", decision["unresolved_nonfinite_count"]),
            ("lossless_nonfinite_count", decision["lossless_nonfinite_count"]),
            ("all_lossless_cells_finite", decision["all_lossless_cells_finite"]),
        )
    ]
    _write_csv(output_dir / "praise_forensic_decision.csv", ("metric", "value"), decision_rows)
    return {
        "status": summary["status"],
        "decision": summary["decision"],
        "selection_path": str(selection_path),
        "forensic_records_path": str(forensic_path),
        "summary_json": str(summary_json),
        "decision_csv": str(output_dir / "praise_forensic_decision.csv"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--affected-rows-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=base.SAMPLE_SIZE)
    parser.add_argument("--row-chunk", type=int, default=512)
    parser.add_argument("--expected-trim-rows", type=int, default=10_030)
    parser.add_argument("--expected-no-positive-rows", type=int, default=2)
    parser.add_argument("--expected-single-record-rows", type=int, default=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = diagnose_praise_nonfinite(
            args.cache, args.affected_rows_csv, args.output_dir,
            sample_size=args.sample_size, row_chunk=args.row_chunk,
            expected_trim_rows=args.expected_trim_rows,
            expected_no_positive_rows=args.expected_no_positive_rows,
            expected_single_record_rows=args.expected_single_record_rows,
        )
    except (OSError, ValueError, workflow.WorkflowError, base.PressureMethodDiagnosticError) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
