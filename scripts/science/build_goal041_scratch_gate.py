#!/usr/bin/env python3
"""Build a fail-closed scratch-capacity gate for Goal 041."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


CASES = ("C-HI", "C-LO", "G-LO")
SAFETY_FACTOR = 1.20
MINIMUM_HEADROOM_RATIO = 1.50
FORECAST_FIELDS = (
    "xray_products_bytes",
    "transient_working_bytes",
    "archive_duplication_bytes",
    "particle_outputs_bytes",
)


def _nonnegative_integer(value: str, context: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"invalid byte forecast for {context}: {value!r}") from exc
    if number < 0:
        raise ValueError(f"negative byte forecast for {context}")
    return number


def build_gate(
    *, forecast_csv: Path, available_bytes: int, write_probe_status: str,
    analysis_parent: str, output_csv: Path, output_json: Path,
) -> dict[str, Any]:
    if available_bytes <= 0:
        raise ValueError("available scratch bytes must be positive")
    if not analysis_parent:
        raise ValueError("analysis parent is required")
    with forecast_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("forecast CSV has an invalid header")
        rows = list(reader)
    if sorted(row.get("case", "") for row in rows) != sorted(CASES):
        raise ValueError("forecast case coverage must be exactly C-HI, C-LO, and G-LO")
    per_case: dict[str, int] = {}
    particle_outputs = 0
    for row in rows:
        case = row["case"]
        values = {field: _nonnegative_integer(row.get(field, ""), f"{case}/{field}") for field in FORECAST_FIELDS}
        if not row.get("forecast_basis"):
            raise ValueError(f"missing forecast basis for {case}")
        particle_outputs += values["particle_outputs_bytes"]
        per_case[case] = sum(values.values())
    if particle_outputs != 0:
        raise ValueError("Goal 041 scratch forecast must contain zero particle outputs")
    if write_probe_status != "passed":
        raise ValueError("scratch write probe did not pass")
    forecast_total = sum(per_case.values())
    if forecast_total <= 0:
        raise ValueError("scratch forecast total must be positive")
    required_with_safety = math.ceil(forecast_total * SAFETY_FACTOR)
    headroom_ratio = available_bytes / required_with_safety
    if headroom_ratio < MINIMUM_HEADROOM_RATIO:
        raise ValueError(
            f"scratch headroom ratio {headroom_ratio:.6g} is below {MINIMUM_HEADROOM_RATIO}"
        )
    row: dict[str, Any] = {
        "gate_status": "GREEN",
        "analysis_parent": analysis_parent,
        "write_probe_status": write_probe_status,
        "available_bytes": available_bytes,
        "forecast_total_bytes": forecast_total,
        "safety_factor": SAFETY_FACTOR,
        "required_with_safety_bytes": required_with_safety,
        "headroom_ratio": f"{headroom_ratio:.16g}",
        "minimum_headroom_ratio": MINIMUM_HEADROOM_RATIO,
        "c_hi_forecast_bytes": per_case["C-HI"],
        "c_lo_forecast_bytes": per_case["C-LO"],
        "g_lo_forecast_bytes": per_case["G-LO"],
        "particle_outputs_bytes": particle_outputs,
        "deletion_authority": "barry_only_after_goal041_synthesis_acceptance",
    }
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    metadata = {
        **row,
        "status": "scratch_capacity_gate_green",
        "forecast_cases": per_case,
        "forecast_source": str(forecast_csv),
    }
    output_json.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast-csv", type=Path, required=True)
    parser.add_argument("--available-bytes", type=int, required=True)
    parser.add_argument("--write-probe-status", choices=("passed", "failed"), required=True)
    parser.add_argument("--analysis-parent", required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    metadata = build_gate(
        forecast_csv=args.forecast_csv,
        available_bytes=args.available_bytes,
        write_probe_status=args.write_probe_status,
        analysis_parent=args.analysis_parent,
        output_csv=args.output_csv,
        output_json=args.output_json,
    )
    print(
        "scratch_gate=GREEN "
        f"headroom_ratio={metadata['headroom_ratio']} available_bytes={metadata['available_bytes']}"
    )


if __name__ == "__main__":
    main()
