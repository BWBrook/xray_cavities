#!/usr/bin/env python3
"""Finalize Goal 053 from preserved partial arrays without recomputation.

This is deliberately an evidence-only post-processing step.  It never opens
the immutable cache and never invokes the stable-method diagnostic.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from scripts.science import diagnose_g_lo_critical_stratum_census as diagnostic
from scripts.science import diagnose_g_lo_pressure_method_value as pressure_method
from scripts.science import diagnose_g_lo_stable_method_value as stable_method


class Goal053FinalizationError(RuntimeError):
    """Raised when preserved Goal 053 evidence cannot be finalized safely."""


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise Goal053FinalizationError(f"CSV has no header: {path}")
        rows = list(reader)
    if not rows:
        raise Goal053FinalizationError(f"CSV has no data rows: {path}")
    return list(reader.fieldnames), rows


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _regular(path: Path) -> Path:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise Goal053FinalizationError(
            f"required evidence is not a regular file: {source}"
        )
    return source.resolve()


def _validate_particle_and_arrays(
    selection: Sequence[Mapping[str, Any]],
    particle: Sequence[Mapping[str, Any]],
    partial_dir: Path,
) -> None:
    if len(selection) != len(particle):
        raise Goal053FinalizationError("census selection and particle row counts differ")
    numeric_fields = {
        "inclusion_probability", "analysis_weight", "injection_age",
        "pressure_dynamic_range_log10", "shock_age",
        "log_endpoint_relative_difference", "min_log_to_raw_ratio",
    }
    for index, (selected, compared) in enumerate(zip(selection, particle, strict=True)):
        for field in ("sample_index", "cache_row", "physical_id"):
            if int(selected[field]) != int(compared[field]):
                raise Goal053FinalizationError(f"census identity mismatch at row {index}:{field}")
        if int(selected["sample_index"]) != index:
            raise Goal053FinalizationError("census sample_index order is not 0..n-1")
        for field in diagnostic.pressure_method.SELECTION_FIELDS:
            if field in {"sample_index", "cache_row", "physical_id"}:
                continue
            if field in numeric_fields:
                if not np.isclose(float(selected[field]), float(compared[field]), rtol=1e-12, atol=1e-12):
                    raise Goal053FinalizationError(f"census feature mismatch at row {index}:{field}")
            elif str(selected[field]) != str(compared[field]):
                raise Goal053FinalizationError(f"census feature mismatch at row {index}:{field}")
        if not np.isclose(float(selected["analysis_weight"]), 1.0, rtol=0.0, atol=0.0):
            raise Goal053FinalizationError("census analysis weights must be exactly one")
        if not np.isclose(float(selected["inclusion_probability"]), 1.0, rtol=0.0, atol=0.0):
            raise Goal053FinalizationError("census inclusion probabilities must be exactly one")

    ids = np.asarray([int(row["physical_id"]) for row in particle], dtype=np.int64)
    if len(np.unique(ids)) != len(ids):
        raise Goal053FinalizationError("census particle IDs are not unique")
    for mode, filename in diagnostic.MODE_NPZ_NAMES.items():
        path = _regular(partial_dir / filename)
        with np.load(path, allow_pickle=False) as arrays:
            required = {"physical_ids", "frequencies", "full", "adiabatic", "none"}
            if not required.issubset(arrays.files):
                raise Goal053FinalizationError(f"{filename} omits required branch arrays")
            if not np.array_equal(np.asarray(arrays["physical_ids"], dtype=np.int64), ids):
                raise Goal053FinalizationError(f"{filename} IDs/order differ from CSV")
            if not np.array_equal(np.asarray(arrays["frequencies"], dtype=np.float64), np.asarray(stable_method.FREQUENCIES_GHZ, dtype=np.float64)):
                raise Goal053FinalizationError(f"{filename} frequencies differ from contract")
            for branch in ("full", "adiabatic", "none"):
                values = np.asarray(arrays[branch], dtype=np.float64)
                if values.shape != (len(ids), len(stable_method.FREQUENCIES_GHZ)) or not np.all(np.isfinite(values)) or np.any(values < 0):
                    raise Goal053FinalizationError(f"{filename} has malformed {branch} array")
                for row_index, row in enumerate(particle):
                    expected = np.asarray([
                        float(row[f"{mode}_{branch}_{frequency:g}GHz"])
                        for frequency in stable_method.FREQUENCIES_GHZ
                    ])
                    if not np.array_equal(values[row_index], expected):
                        raise Goal053FinalizationError(f"{filename} does not reproduce CSV at row {row_index}")


def _concentration(rows: Sequence[Mapping[str, Any]], scope: str) -> list[dict[str, Any]]:
    discrepancy = diagnostic._per_row_discrepancy(rows)
    weights = np.asarray([float(row["analysis_weight"]) for row in rows], dtype=np.float64)
    output = []
    for fraction in (0.001, 0.01, 0.05, 0.10):
        value = pressure_method.represented_population_discrepancy_concentration(
            discrepancy, weights, population_fraction=fraction
        )
        output.append({
            "scope": scope,
            "population_fraction": fraction,
            "discrepancy_fraction": value["fraction"],
            "represented_population_weight": value["represented_population_weight"],
            "target_population_weight": value["target_population_weight"],
            "fully_included_rows": value["fully_included_rows"],
            "fractional_boundary_row_index": value["fractional_boundary_row_index"],
            "fractional_boundary_row_weight_fraction": value["fractional_boundary_row_weight_fraction"],
        })
    return output


def finalize_g_lo_critical_stratum_census(
    partial_dir: Path,
    original_selection_csv: Path | None,
    original_comparison_csv: Path | None,
    output_dir: Path,
    *,
    expected_original_selection_sha256: str | None = None,
    expected_original_comparison_sha256: str | None = None,
    expected_census_count: int = diagnostic.EXPECTED_CENSUS_COUNT,
    expected_oracle_count: int = diagnostic.EXPECTED_ORACLE_COUNT,
    target_stratum: str = diagnostic.TARGET_STRATUM,
) -> dict[str, Any]:
    """Generate Goal 053 downstream products from a retrieved partial run."""
    partial_dir_source = Path(partial_dir)
    if partial_dir_source.is_symlink() or not partial_dir_source.is_dir():
        raise Goal053FinalizationError(
            f"partial evidence directory is invalid: {partial_dir_source}"
        )
    partial_dir = partial_dir_source.resolve()
    original_selection_csv = _regular(original_selection_csv or partial_dir / "original_selection.csv")
    original_comparison_csv = _regular(original_comparison_csv or partial_dir / "original_particle_comparison.csv")
    if expected_original_selection_sha256 and _sha256(original_selection_csv) != expected_original_selection_sha256:
        raise Goal053FinalizationError("original selection SHA-256 mismatch")
    if expected_original_comparison_sha256 and _sha256(original_comparison_csv) != expected_original_comparison_sha256:
        raise Goal053FinalizationError("original comparison SHA-256 mismatch")

    required = [diagnostic.SELECTION_NAME, diagnostic.PARTICLE_NAME, *diagnostic.MODE_NPZ_NAMES.values()]
    for name in required:
        _regular(partial_dir / name)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() or output_dir.is_symlink():
        raise Goal053FinalizationError(f"refusing to overwrite finalization output: {output_dir}")
    output_dir.mkdir(parents=True)

    _selection_fields, selection_raw = _read_csv(partial_dir / diagnostic.SELECTION_NAME)
    selection = diagnostic._normalise_selection_rows(selection_raw)
    _particle_fields, particle_raw = _read_csv(partial_dir / diagnostic.PARTICLE_NAME)
    particle = [dict(row) for row in particle_raw]
    if len(selection) != expected_census_count:
        raise Goal053FinalizationError(f"census count {len(selection)} != expected {expected_census_count}")
    _validate_particle_and_arrays(selection, particle, partial_dir)

    _, original_selection_raw = _read_csv(original_selection_csv)
    original_selection = diagnostic._normalise_selection_rows(original_selection_raw)
    _, original_particle_raw = _read_csv(original_comparison_csv)
    original_particle = [dict(row) for row in original_particle_raw]
    identity = diagnostic._validate_original_row_identity(original_selection, original_particle)
    _, oracle_metadata = diagnostic._validate_oracle_and_annotate(
        selection, original_selection, target_stratum=target_stratum,
        expected_oracle_count=expected_oracle_count,
    )
    audit_rows, oracle_replay = diagnostic.oracle_replay_tolerance_audit(
        original_particle, particle, target_stratum=target_stratum
    )
    census_by_id = {int(row["physical_id"]): row for row in particle}
    original_target = [row for row in original_particle if str(row["stratum"]) == target_stratum]
    if len(original_target) != expected_oracle_count:
        raise Goal053FinalizationError("original comparison oracle count differs from contract")
    hybrid_rows, replacement = diagnostic.replace_stratum_with_census(
        original_particle, particle, target_stratum=target_stratum
    )
    _, hybrid_modes = diagnostic._branch_inputs_from_particle_rows(hybrid_rows)
    _, census_modes = diagnostic._branch_inputs_from_particle_rows(particle)
    _, hybrid_comparison = pressure_method.summarise_method_comparison(
        hybrid_rows, hybrid_modes["unsmoothed"], hybrid_modes["log_savgol"]
    )
    _, census_comparison = pressure_method.summarise_method_comparison(
        particle, census_modes["unsmoothed"], census_modes["log_savgol"]
    )

    discrepancy = diagnostic._per_row_discrepancy(particle)
    rank_order = np.lexsort((np.arange(len(particle)), -discrepancy))
    ranks = {int(particle[index]["physical_id"]): rank + 1 for rank, index in enumerate(rank_order)}
    by_id_index = {int(row["physical_id"]): i for i, row in enumerate(particle)}
    for row in audit_rows:
        row["census_discrepancy_rank"] = ranks[int(row["physical_id"])]
        row["census_per_particle_discrepancy"] = float(discrepancy[by_id_index[int(row["physical_id"])]])

    concentration_rows = _concentration(particle, "critical_stratum_census") + _concentration(hybrid_rows, "hybrid_population")
    hybrid_gates = [{"gate": gate, "passed": bool(value), "value": json.dumps(bool(value))} for gate, value in hybrid_comparison["gate_results"].items()]
    hybrid_top = float(hybrid_comparison["top_one_percent_absolute_discrepancy_fraction"])
    census_top = float(census_comparison["top_one_percent_absolute_discrepancy_fraction"])
    hybrid_gates.append({"gate": "top_one_percent_absolute_discrepancy_fraction", "passed": hybrid_top <= pressure_method.GATES["max_top_one_percent_discrepancy_fraction"], "value": hybrid_top})
    source_gate_rows: list[dict[str, str]] = []
    gate_path = partial_dir / diagnostic.GATE_NAME
    if gate_path.is_file():
        _, source_gate_rows = _read_csv(gate_path)
    inherited_fail = any(str(row.get("passed", "")).strip().lower() in {"false", "0", "no"} for row in source_gate_rows)
    cutoff_count = 0
    cutoff_path = partial_dir / diagnostic.CUTOFF_NAME
    if cutoff_path.is_file():
        try:
            with cutoff_path.open(newline="") as handle:
                cutoff_count = max(0, sum(1 for _ in csv.DictReader(handle)))
        except (OSError, csv.Error) as exc:
            raise Goal053FinalizationError("malformed cutoff evidence") from exc
    decision = diagnostic.classify_census_outcome(
        hybrid_top_fraction=hybrid_top, census_top_fraction=census_top,
        cutoff_count=cutoff_count, scientific_gates_passed=not inherited_fail,
        provenance_passed=oracle_replay["stable_branch_replay_within_tolerance"],
    )

    # Copy preserved source evidence first; generated files below are fresh.
    generated = {diagnostic.MEMBERSHIP_NAME, diagnostic.AUDIT_NAME, diagnostic.CONCENTRATION_NAME, diagnostic.HYBRID_GATE_NAME, diagnostic.GATE_NAME, diagnostic.SUMMARY_NAME}
    for source in partial_dir.iterdir():
        if source.is_file() and source.name not in generated:
            shutil.copyfile(source, output_dir / source.name)
    shutil.copyfile(original_selection_csv, output_dir / "original_selection.csv")
    shutil.copyfile(original_comparison_csv, output_dir / "original_particle_comparison.csv")
    membership = [
        {"metric": "census_count", "value": len(selection)},
        {"metric": "oracle_count", "value": len(original_target)},
        {"metric": "target_stratum", "value": target_stratum},
    ]
    _write_csv(output_dir / diagnostic.MEMBERSHIP_NAME, ("metric", "value"), membership)
    _write_csv(output_dir / diagnostic.AUDIT_NAME, tuple(audit_rows[0].keys()) if audit_rows else ("physical_id",), audit_rows)
    _write_csv(output_dir / diagnostic.CONCENTRATION_NAME, ("scope", "population_fraction", "discrepancy_fraction", "represented_population_weight", "target_population_weight", "fully_included_rows", "fractional_boundary_row_index", "fractional_boundary_row_weight_fraction"), concentration_rows)
    _write_csv(output_dir / diagnostic.HYBRID_GATE_NAME, ("gate", "passed", "value"), hybrid_gates)
    gate_rows = list(source_gate_rows)
    gate_rows.extend([
        {"scope": "oracle", "gate": "goal051_branch_replay", "passed": str(oracle_replay["stable_branch_replay_within_tolerance"]), "value": json.dumps(oracle_replay, sort_keys=True)},
        {"scope": "decision", "gate": "census_classification_complete", "passed": str(decision in diagnostic.SUCCESS_DECISIONS), "value": decision},
    ])
    _write_csv(output_dir / diagnostic.GATE_NAME, ("scope", "gate", "passed", "value"), gate_rows)
    summary = {
        "status": "diagnostic_complete",
        "decision": decision,
        "decision_label": decision,
        "target_stratum": target_stratum,
        "census_count": len(selection),
        "oracle_count": len(original_target),
        "census_top_one_percent_discrepancy_fraction": census_top,
        "hybrid_top_one_percent_discrepancy_fraction": hybrid_top,
        "predeclared_threshold": pressure_method.GATES["max_top_one_percent_discrepancy_fraction"],
        "original_row_identity": identity,
        "oracle_metadata": oracle_metadata,
        "oracle_replay_tolerance": oracle_replay,
        "replacement_audit": replacement,
        "finalization": {
            "mode": "no_recompute_from_preserved_arrays",
            "cache_recomputed": False,
            "stable_branch_recomputed": False,
            "source_partial_directory": str(partial_dir_source),
        },
        "pbs_failure_evidence": {"job_id": "780326.kunanyi-ohpc", "exit_status": 2, "cause": "obsolete exact oracle replay gate", "preserved": True},
    }
    (output_dir / diagnostic.SUMMARY_NAME).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return {"status": "diagnostic_complete", "decision": decision, "summary_json": str(output_dir / diagnostic.SUMMARY_NAME), "output_dir": str(output_dir)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial-dir", type=Path, required=True)
    parser.add_argument("--original-selection-csv", type=Path)
    parser.add_argument("--original-comparison-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-original-selection-sha256")
    parser.add_argument("--expected-original-comparison-sha256")
    parser.add_argument("--expected-census-count", type=int, default=diagnostic.EXPECTED_CENSUS_COUNT)
    parser.add_argument("--expected-oracle-count", type=int, default=diagnostic.EXPECTED_ORACLE_COUNT)
    parser.add_argument("--target-stratum", default=diagnostic.TARGET_STRATUM)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = finalize_g_lo_critical_stratum_census(
            args.partial_dir, args.original_selection_csv, args.original_comparison_csv, args.output_dir,
            expected_original_selection_sha256=args.expected_original_selection_sha256,
            expected_original_comparison_sha256=args.expected_original_comparison_sha256,
            expected_census_count=args.expected_census_count,
            expected_oracle_count=args.expected_oracle_count,
            target_stratum=args.target_stratum,
        )
    except (OSError, TypeError, ValueError, pressure_method.PressureMethodDiagnosticError, diagnostic.CriticalStratumCensusError, Goal053FinalizationError) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
