#!/usr/bin/env python3
"""Validate and lock the accepted Goal 040 endpoint reuse surface."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


CASES = ("C-HI", "C-LO", "G-LO")
VIEWS = ("0deg", "45deg", "90deg")
ENDPOINT_TIME_MYR = 50.0
REQUIRED_FILES = (
    "xray_recovery_summary.csv",
    "xray_component_summary.csv",
    "method_sensitivity.csv",
    "case_truth_summary.csv",
    "truth_threshold_sensitivity.csv",
    "tracer_shell_pressure_context.csv",
    "xray_truth_alignment.csv",
    "three_case_endpoint_cavity_recovery_metadata.json",
    "three_case_truth_alignment_metadata.json",
)


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"missing accepted endpoint asset: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"invalid or duplicate CSV header: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty accepted endpoint asset: {path}")
    return rows


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid accepted endpoint JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"accepted endpoint JSON is not an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _locked_hashes(endpoint_root: Path) -> dict[str, str]:
    manifest = endpoint_root / "local_asset_manifest.sha256"
    if not manifest.is_file():
        raise ValueError("missing accepted Goal 040 hash manifest")
    expected: dict[str, str] = {}
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(maxsplit=1)
        expected[relative.strip()] = digest
    locked: dict[str, str] = {}
    for relative in REQUIRED_FILES:
        if relative not in expected:
            raise ValueError(f"accepted hash manifest omits {relative}")
        observed = _sha256(endpoint_root / relative)
        if observed != expected[relative]:
            raise ValueError(f"hash mismatch for accepted endpoint asset {relative}")
        locked[relative] = observed
    return locked


def _finite_time(row: dict[str, str], field: str, context: str) -> None:
    try:
        value = float(row[field])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid time binding for {context}") from exc
    if not math.isfinite(value) or abs(value - ENDPOINT_TIME_MYR) > 1.0e-9:
        raise ValueError(f"endpoint time mismatch for {context}: {value}")


def _require_case_view_grid(rows: list[dict[str, str]], label: str) -> None:
    observed = [(row.get("case", ""), row.get("view", "")) for row in rows]
    expected = [(case, view) for case in CASES for view in VIEWS]
    if sorted(observed) != sorted(expected):
        raise ValueError(f"{label} does not cover the exact three-case/view grid")


def build_endpoint_contract(*, endpoint_root: Path, output_csv: Path, output_json: Path) -> dict[str, Any]:
    locked = _locked_hashes(endpoint_root)
    recovery_meta = _json(endpoint_root / "three_case_endpoint_cavity_recovery_metadata.json")
    truth_meta = _json(endpoint_root / "three_case_truth_alignment_metadata.json")
    for label, metadata in (("recovery", recovery_meta), ("truth", truth_meta)):
        if metadata.get("status") != "complete_product":
            raise ValueError(f"Goal 040 {label} metadata is not complete")
        if metadata.get("decision_label") != "THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE":
            raise ValueError(f"Goal 040 {label} decision label drift")
        if metadata.get("cases") != list(CASES) or metadata.get("views") != list(VIEWS):
            raise ValueError(f"Goal 040 {label} case/view contract drift")
        if metadata.get("final_observational_topology_frozen") is not False or metadata.get("publication_ready") is not False:
            raise ValueError(f"Goal 040 {label} interpretation boundary drift")
    protocol = recovery_meta.get("base_protocol", {})
    expected_protocol = {
        "radial_bin_kpc": 5.0,
        "radial_smoothing_kpc": 10.0,
        "candidate_fraction_percent": 1.0,
        "is_base": True,
    }
    if protocol != expected_protocol or recovery_meta.get("candidate_selection_basis") != "projected_physical_area_fraction":
        raise ValueError("Goal 040 physical-area base protocol drift")

    recovery_rows = _rows(endpoint_root / "xray_recovery_summary.csv")
    _require_case_view_grid(recovery_rows, "recovery summary")
    for row in recovery_rows:
        _finite_time(row, "time_myr", f"recovery {row.get('case')}/{row.get('view')}")
        if any(
            abs(float(row[field]) - expected_protocol[field]) > 1.0e-12
            for field in ("radial_bin_kpc", "radial_smoothing_kpc", "candidate_fraction_percent")
        ) or row.get("candidate_selection_basis") != "projected_physical_area_fraction":
            raise ValueError("Goal 040 recovery row is not the accepted physical-area base protocol")

    sensitivity = _rows(endpoint_root / "method_sensitivity.csv")
    expected_sensitivity = {
        (radial, smoothing, fraction)
        for radial, smoothing in ((4.0, 8.0), (5.0, 10.0), (8.0, 15.0))
        for fraction in (0.5, 1.0, 2.0, 3.0, 5.0)
    }
    if len(sensitivity) != 135:
        raise ValueError("Goal 040 method sensitivity does not contain 135 rows")
    for case in CASES:
        for view in VIEWS:
            selected = [row for row in sensitivity if row.get("case") == case and row.get("view") == view]
            observed = {
                (float(row["radial_bin_kpc"]), float(row["radial_smoothing_kpc"]), float(row["candidate_fraction_percent"]))
                for row in selected
            }
            if observed != expected_sensitivity or sum(row.get("is_base", "").lower() == "true" for row in selected) != 1:
                raise ValueError(f"Goal 040 method sensitivity grid drift for {case}/{view}")

    case_truth = _rows(endpoint_root / "case_truth_summary.csv")
    if sorted(row.get("case", "") for row in case_truth) != sorted(CASES):
        raise ValueError("Goal 040 case truth summary coverage drift")
    truth_threshold = _rows(endpoint_root / "truth_threshold_sensitivity.csv")
    if len(truth_threshold) != 9:
        raise ValueError("Goal 040 truth threshold coverage drift")
    for row in truth_threshold:
        _finite_time(row, "time_myr", f"truth threshold {row.get('case')}/{row.get('tracer_threshold')}")
    shell_rows = _rows(endpoint_root / "tracer_shell_pressure_context.csv")
    if len(shell_rows) != 6:
        raise ValueError("Goal 040 shell context coverage drift")
    for case in CASES:
        selected = [row for row in shell_rows if row.get("case") == case]
        if {row.get("side") for row in selected} != {"negative_z", "positive_z"}:
            raise ValueError(f"Goal 040 shell side coverage drift for {case}")
        for row in selected:
            _finite_time(row, "time_myr", f"shell {case}/{row.get('side')}")
    alignment = _rows(endpoint_root / "xray_truth_alignment.csv")
    _require_case_view_grid(alignment, "truth alignment")
    for row in alignment:
        _finite_time(row, "time_myr", f"truth alignment {row.get('case')}/{row.get('view')}")

    locked_digest = hashlib.sha256(
        "\n".join(f"{relative}:{locked[relative]}" for relative in sorted(locked)).encode()
    ).hexdigest()
    rows: list[dict[str, Any]] = []
    by_key = {(row["case"], row["view"]): row for row in recovery_rows}
    for case in CASES:
        for view in VIEWS:
            row = by_key[(case, view)]
            rows.append({
                "case": case,
                "view": view,
                "nominal_age_myr": 50,
                "endpoint_time_myr": float(row["time_myr"]),
                "endpoint_reuse_id": f"{case}:50myr",
                "endpoint_source_goal": "040",
                "endpoint_reuse_status": "accepted_goal040",
                "candidate_selection_basis": row["candidate_selection_basis"],
                "radial_bin_kpc": row["radial_bin_kpc"],
                "radial_smoothing_kpc": row["radial_smoothing_kpc"],
                "candidate_fraction_percent": row["candidate_fraction_percent"],
                "projection_accumulator": "direct_y_axis_sum" if view == "0deg" else "edge_overlap_uniform_cell_projection",
                "truth_time_binding": "validated_50myr",
                "sensitivity_protocol_count": 15,
                "locked_assets_digest_sha256": locked_digest,
                "topology_interpretation": "conditional_not_final",
            })
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "status": "endpoint_reuse_contract_green",
        "source_goal": "040",
        "source_root": str(endpoint_root),
        "row_count": len(rows),
        "cases": list(CASES),
        "views": list(VIEWS),
        "endpoint_time_myr": ENDPOINT_TIME_MYR,
        "candidate_selection_basis": "projected_physical_area_fraction",
        "sensitivity_protocols_per_case_view": 15,
        "locked_assets": locked,
        "locked_assets_digest_sha256": locked_digest,
        "final_observational_topology_frozen": False,
        "publication_ready": False,
    }
    output_json.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-root", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    metadata = build_endpoint_contract(
        endpoint_root=args.endpoint_root,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(f"endpoint_reuse_contract={metadata['status']} rows={metadata['row_count']}")


if __name__ == "__main__":
    main()

