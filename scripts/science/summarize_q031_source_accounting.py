#!/usr/bin/env python3
"""Difference whole-grid and nozzle-control snapshot balances without source attribution."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Mapping, Sequence


DOMAIN_RECONSTRUCTIONS = ("outer_active_cell", "linear_to_boundary_face")
NOZZLE_RECONSTRUCTIONS = ("centered_primitives", "donor_cell_primitives")
QUADRATURES = ("left_rectangle", "trapezoid", "right_rectangle")
ENERGY_DEFINITION = "internal + kinetic + fixed centre-zero gravitational potential"
BALANCE_FIELDS = (
    "storage_mass_change_g", "integrated_mass_flux_outward_g",
    "inferred_internal_mass_source_g", "storage_energy_change_erg",
    "integrated_energy_flux_outward_erg", "inferred_internal_energy_source_erg",
)
NUMERIC_FIELDS = (*BALANCE_FIELDS, *("cumulative_" + name for name in BALANCE_FIELDS))


def _number(value, name):
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f"invalid numeric field {name}") from error
    if not math.isfinite(result):
        raise ValueError(f"nonfinite numeric field {name}")
    return result


def _identity(actual, expected, scale, label):
    if abs(actual - expected) > 1e-11 * max(abs(actual), abs(expected), scale, 1.0):
        raise ValueError(f"inconsistent balance identity: {label}")


def summarize_rows(rows: Sequence[Mapping], padding_cells: Sequence[int]) -> list[dict]:
    """Keep every outer/inner reconstruction combination at exactly matching times."""
    paddings = tuple(sorted(padding_cells))
    if not paddings or len(set(paddings)) != len(paddings) or any(type(p) is not int or p < 0 for p in paddings):
        raise ValueError("padding cells must be unique nonnegative integers")
    expected = {(surface, reconstruction, quadrature)
                for surface, reconstructions in (
                    ("domain_boundary", DOMAIN_RECONSTRUCTIONS),
                    *((f"nozzle_control_p{padding}", NOZZLE_RECONSTRUCTIONS) for padding in paddings),
                )
                for reconstruction in reconstructions for quadrature in QUADRATURES}
    series = {}
    cases = set()
    for row in rows:
        try:
            case = str(row["case"])
            surface = str(row["surface"])
            reconstruction = str(row["reconstruction"])
            quadrature = str(row["temporal_quadrature"])
            region = str(row["storage_region"])
        except KeyError as error:
            raise ValueError(f"missing required field {error.args[0]}") from error
        if not case:
            raise ValueError("empty case")
        cases.add(case)
        key = (surface, reconstruction, quadrature)
        if key not in expected:
            raise ValueError(f"unexpected surface/reconstruction/quadrature: {key}")
        if region != ("whole_grid" if surface == "domain_boundary" else surface):
            raise ValueError("storage region does not match surface")
        fields = (*NUMERIC_FIELDS, "interval_start_myr", "interval_end_myr",
                  "interval_duration_myr", "nominal_configured_bipolar_energy_erg")
        try:
            record = {name: _number(row[name], name) for name in fields}
        except KeyError as error:
            raise ValueError(f"missing required field {error.args[0]}") from error
        start, end = record["interval_start_myr"], record["interval_end_myr"]
        if start < 0 or end <= start or record["nominal_configured_bipolar_energy_erg"] < 0:
            raise ValueError("invalid time interval or nominal energy")
        _identity(record["interval_duration_myr"], end-start, end-start, "interval duration")
        interval = (start, end)
        records = series.setdefault(key, {})
        if interval in records:
            raise ValueError(f"duplicate balance row: {key}, {interval}")
        for prefix in ("", "cumulative_"):
            for unit, quantity in (("g", "mass"), ("erg", "energy")):
                storage = record[f"{prefix}storage_{quantity}_change_{unit}"]
                flux = record[f"{prefix}integrated_{quantity}_flux_outward_{unit}"]
                source = record[f"{prefix}inferred_internal_{quantity}_source_{unit}"]
                _identity(source, storage+flux, abs(storage)+abs(flux), prefix+quantity)
        records[interval] = record
    if len(cases) != 1 or set(series) != expected:
        raise ValueError("missing series or mixed/empty cases")
    intervals = sorted(next(iter(series.values())))
    if not intervals:
        raise ValueError("no intervals")
    for key, records in series.items():
        if set(records) != set(intervals):
            raise ValueError(f"time/reconstruction interval mismatch: {key}")
    for previous, current in zip(intervals, intervals[1:]):
        if previous[1] != current[0]:
            raise ValueError("time intervals have a gap or overlap")
    for key, records in series.items():
        previous = {field: 0.0 for field in BALANCE_FIELDS}
        for interval in intervals:
            row = records[interval]
            for field in BALANCE_FIELDS:
                cumulative = row["cumulative_"+field]
                _identity(cumulative, previous[field]+row[field], abs(previous[field])+abs(row[field]),
                          "cumulative progression "+field)
                previous[field] = cumulative
    output = []
    case = next(iter(cases))
    for interval in intervals:
        for quadrature in QUADRATURES:
            for outer in DOMAIN_RECONSTRUCTIONS:
                domain = series[("domain_boundary", outer, quadrature)][interval]
                for padding in paddings:
                    for inner in NOZZLE_RECONSTRUCTIONS:
                        nozzle = series[(f"nozzle_control_p{padding}", inner, quadrature)][interval]
                        nominal = domain["nominal_configured_bipolar_energy_erg"]
                        if nozzle["nominal_configured_bipolar_energy_erg"] != nominal:
                            raise ValueError("nominal energy differs across matching series")
                        row = {"case": case, "domain_reconstruction": outer,
                               "nozzle_reconstruction": inner, "nozzle_padding_cells": padding,
                               "temporal_quadrature": quadrature,
                               "interval_start_myr": interval[0], "interval_end_myr": interval[1],
                               "interval_duration_myr": domain["interval_duration_myr"],
                               "nominal_configured_bipolar_energy_erg": nominal}
                        for field in NUMERIC_FIELDS:
                            row["domain_"+field] = domain[field]
                            row["nozzle_"+field] = nozzle[field]
                            row["outside_nozzle_"+field] = domain[field]-nozzle[field]
                        for prefix in ("", "cumulative_"):
                            row[prefix+"energy_gauge_response_mass_g"] = row[
                                "outside_nozzle_"+prefix+"inferred_internal_mass_source_g"]
                        value = row["outside_nozzle_cumulative_inferred_internal_energy_source_erg"]
                        row["cumulative_outside_nozzle_source_to_nominal_ratio"] = value/nominal if nominal > 0 else ""
                        output.append(row)
    return output


def run(input_dir: Path, output_dir: Path) -> dict:
    balances_path, provenance_path = input_dir/"integrated_control_balances.csv", input_dir/"provenance.json"
    balances_bytes, provenance_bytes = balances_path.read_bytes(), provenance_path.read_bytes()
    digest = hashlib.sha256(balances_bytes).hexdigest()
    provenance = json.loads(provenance_bytes)
    if provenance.get("outputs", {}).get(balances_path.name) != digest:
        raise ValueError("input balance hash does not match producer provenance")
    if provenance.get("energy_definition") != ENERGY_DEFINITION:
        raise ValueError("unsupported or missing potential/energy convention")
    try:
        padding = [int(name) for name in provenance["control_box_edges_kpc"]]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("missing or invalid producer padding declaration") from error
    rows = list(csv.DictReader(io.StringIO(balances_bytes.decode("utf-8"))))
    output = summarize_rows(rows, padding)
    intervals = {(row["interval_start_myr"], row["interval_end_myr"]) for row in output}
    if output[0]["case"] != provenance.get("case"):
        raise ValueError("balance case differs from producer provenance")
    if len(provenance.get("snapshots", [])) != len(intervals)+1:
        raise ValueError("balance interval count differs from producer snapshot count")
    if set(padding) != set(provenance.get("control_padding_cells", [])):
        raise ValueError("producer padding declarations disagree")
    output_dir.mkdir(parents=True, exist_ok=False)
    product = output_dir/"outside_nozzle_source_balances.csv"
    with product.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    receipt = {
        "schema_version": 1, "status": "completed_snapshot_source_balance_summary",
        "input_balances_sha256": digest,
        "input_provenance_sha256": hashlib.sha256(provenance_bytes).hexdigest(),
        "summarizer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "producer_analysis_signature": provenance.get("analysis_signature"),
        "case": output[0]["case"], "row_count": len(output), "interval_count": len(intervals),
        "nozzle_padding_cells": sorted(padding),
        "energy_definition": ENERGY_DEFINITION,
        "source_identity": "inferred source = storage change + outward integrated flux",
        "outside_nozzle_identity": "whole-grid inferred source minus nozzle-control inferred source",
        "potential_shift_response": "For Phi -> Phi + C, every energy storage/flux/source changes by C times its matching mass storage/flux/source; outside-source coefficient is energy_gauge_response_mass_g.",
        "sensitivity": "Explicit cross-product of outer and nozzle reconstructions at identical intervals and quadratures; padding, cadence and reconstruction scenarios are not confidence bounds.",
        "limits": [
            "The outside-nozzle quantity is an unresolved source/balance residual, not a measured volumetric-source decomposition.",
            "Snapshot-reconstructed flux is not solver Riemann flux or measured per-step nozzle delivery.",
            "Gravity integration error, floors, conversion repairs and cadence/reconstruction errors are not individually measured.",
            "The potential convention is inherited jointly from one producer; storage-only comparisons are gauge-dependent wherever mass changes.",
            "The baseline excludes the original t=0 nozzle overwrite as specified by the producer.",
        ],
        "products_sha256": {product.name: hashlib.sha256(product.read_bytes()).hexdigest()},
    }
    with (output_dir/"receipt.json").open("x") as handle:
        handle.write(json.dumps(receipt, indent=2, allow_nan=False)+"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input_dir, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
