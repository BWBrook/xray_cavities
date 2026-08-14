#!/usr/bin/env python3
"""Build the matched four-case production and G-LO analysis contracts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


FLT_BYTES = 44_890_581_676
DBL_BYTES = 67_318_639_276
PARTICLE_HISTORY_BYTES = 65 * 1024**3
FLT_COUNT = 51
DBL_COUNT = 11
CODE_TIME_PER_MYR = 306.601393788
ENDPOINT_MYR = 50.0


class ReadinessError(RuntimeError):
    """Raised when the production/readiness contract is internally inconsistent."""


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ReadinessError(f"refusing to write empty table: {path.name}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def case_rows() -> list[dict[str, Any]]:
    return [
        {
            "case": "C-HI", "environment_family": "cluster", "environment_id": "002_003",
            "jet_power_erg_s_one_sided": "1e45", "jet_speed_c": 0.1,
            "production_action": "rerun_full_history_after_quota", "execution_order": 1,
            "reason": "existing particle retention cannot reconstruct complete radiative histories",
        },
        {
            "case": "C-LO", "environment_family": "cluster", "environment_id": "002_003",
            "jet_power_erg_s_one_sided": "1e43", "jet_speed_c": 0.1,
            "production_action": "rerun_full_history_after_quota", "execution_order": 2,
            "reason": "existing particle retention cannot reconstruct complete radiative histories",
        },
        {
            "case": "G-LO", "environment_family": "group", "environment_id": "002_031",
            "jet_power_erg_s_one_sided": "1e43", "jet_speed_c": 0.1,
            "production_action": "analyse_existing_conditional_rerun_only", "execution_order": 0,
            "reason": "complete retained particle-history evidence is adequate; fluid cadence is sparse",
        },
        {
            "case": "G-HI", "environment_family": "group", "environment_id": "002_031",
            "jet_power_erg_s_one_sided": "1e45", "jet_speed_c": 0.1,
            "production_action": "new_full_history_after_cluster_reruns", "execution_order": 3,
            "reason": "missing cell of the environment-by-power factorial design",
        },
    ]


def storage_rows() -> list[dict[str, Any]]:
    fluid_float = FLT_COUNT * FLT_BYTES
    fluid_double = DBL_COUNT * DBL_BYTES
    per_case = fluid_float + fluid_double + PARTICLE_HISTORY_BYTES
    rows: list[dict[str, Any]] = []
    for case in ("C-HI", "C-LO", "G-LO", "G-HI"):
        rows.append({
            "scope": case,
            "flt_h5_count": FLT_COUNT,
            "dbl_h5_count": DBL_COUNT,
            "particle_cadence_Myr": 0.01,
            "fluid_float_bytes": fluid_float,
            "fluid_double_bytes": fluid_double,
            "particle_history_bytes_conservative": PARTICLE_HISTORY_BYTES,
            "uncompressed_total_bytes": per_case,
            "uncompressed_total_TiB": per_case / 1024**4,
            "compression_ratio_assumption": "pending_live_reversible_pilot",
        })
    rows.append({
        "scope": "four_case_total",
        "flt_h5_count": 4 * FLT_COUNT,
        "dbl_h5_count": 4 * DBL_COUNT,
        "particle_cadence_Myr": 0.01,
        "fluid_float_bytes": 4 * fluid_float,
        "fluid_double_bytes": 4 * fluid_double,
        "particle_history_bytes_conservative": 4 * PARTICLE_HISTORY_BYTES,
        "uncompressed_total_bytes": 4 * per_case,
        "uncompressed_total_TiB": 4 * per_case / 1024**4,
        "compression_ratio_assumption": "pending_live_reversible_pilot",
    })
    return rows


def retention_rows() -> list[dict[str, Any]]:
    return [
        {"surface": "particles", "cadence": "0.01 Myr", "count_expectation": "0..5000 inclusive", "retention": "full_project", "gate": "never cull before compact radio cache and provenance are validated"},
        {"surface": "flt.h5", "cadence": "1 Myr", "count_expectation": "51 including t=0 and endpoint", "retention": "full_project", "gate": "reversible compression only after bitwise and analysis-readability validation"},
        {"surface": "dbl.h5", "cadence": "5 Myr", "count_expectation": "11 including t=0 and endpoint", "retention": "full_project", "gate": "keep active restart source uncompressed until a newer restart or completed-run gate exists"},
        {"surface": "catalogues_config_logs", "cadence": "complete", "count_expectation": "all", "retention": "full_project", "gate": "small provenance surface; retain without compaction"},
        {"surface": "compressed_fluid", "cadence": "post-run", "count_expectation": "all validated flt/dbl candidates", "retention": "preferred_archive", "gate": "no source deletion in the pilot; later deletion needs explicit lifecycle authorization"},
    ]


def snapshot_rows(contract_csv: Path) -> list[dict[str, Any]]:
    with Path(contract_csv).open(newline="") as handle:
        protected = list(csv.DictReader(handle))
    rows = []
    for item in protected:
        path = item["path"]
        if "/G-LO/" not in path or not path.endswith(".flt.h5"):
            continue
        timestep = item["expected_timestep"]
        time_code = item["expected_time_code"]
        if not timestep or not time_code:
            continue
        actual_myr = float(time_code) / CODE_TIME_PER_MYR
        rows.append({
            "case": "G-LO",
            "snapshot_index": int(timestep.split("_")[-1]),
            "actual_time_code": float(time_code),
            "actual_time_Myr": actual_myr,
            "fluid_hdf5": path,
            "timestep": timestep,
            "shape_nz_ny_nx": item["expected_shape"],
            "required_datasets": item["expected_datasets"],
            "radio_history_source": "/scratch/bwbrook/xray_cavities_analysis/2026-07-24-g-lo-radio-history-method-value-gate/cache/g_lo_history.h5",
            "particle_matching_rule": "latest_particle_not_later_than_fluid_time",
            "analysis_status": "ready_for_read_only_preflight",
        })
    rows.sort(key=lambda row: float(row["actual_time_Myr"]))
    if [row["snapshot_index"] for row in rows] != [0, 10, 20, 30, 40, 50]:
        raise ReadinessError("protected G-LO fluid surface is not the expected 0/10/20/30/40/50 set")
    return rows


def analysis_stage_rows() -> list[dict[str, Any]]:
    return [
        {"stage": 1, "name": "source_truth_manifest", "primary_inputs": "protected fluid HDF5; exact catalogue times; initial atmosphere", "primary_outputs": "snapshot identity and baseline contract", "current_gate": "ready", "stop_condition": "any path/timestep/time/dataset mismatch"},
        {"stage": 2, "name": "energy_gravity_shock", "primary_inputs": "rho;prs;tr1;vx1;vx2;vx3;Stewart g(r)", "primary_outputs": "ambient/lobe thermal kinetic gravitational energies; closure; shocks; Mach", "current_gate": "method_contract_available", "stop_condition": "gravity-column inconsistency or material closure failure"},
        {"stage": 3, "name": "xray_cavity", "primary_inputs": "fluid HDF5; accepted XRAiSE projection; initial atmosphere", "primary_outputs": "0/45/90 X-ray maps; observational cavity geometry; pV/2.5pV/4pV", "current_gate": "accepted_methods_reusable", "stop_condition": "topology remains threshold-ambiguous for scientific comparison"},
        {"stage": 4, "name": "radio_spectral_age", "primary_inputs": "matched particle histories; corrected PRAiSE2; five frequencies", "primary_outputs": "lossless/full-loss luminosities; spectra; spectral ages", "current_gate": "pending_coefficient_comparison", "stop_condition": "coefficient comparison hold or future-particle leakage"},
        {"stage": 5, "name": "inferred_power_synthesis", "primary_inputs": "stages 2-4; known bipolar power", "primary_outputs": "Q estimates; bias versus time and Mach; four-case-ready tables", "current_gate": "blocked_by_upstream_stages", "stop_condition": "missing decision-critical upstream quantity"},
    ]


def build(contract_csv: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise ReadinessError("refusing to overwrite output directory")
    output_dir.mkdir(parents=True)
    cases = case_rows()
    storage = storage_rows()
    retention = retention_rows()
    snapshots = snapshot_rows(contract_csv)
    stages = analysis_stage_rows()
    _write_csv(output_dir / "four_case_production_contract.csv", cases)
    _write_csv(output_dir / "uncompressed_storage_forecast.csv", storage)
    _write_csv(output_dir / "retention_and_compression_contract.csv", retention)
    _write_csv(output_dir / "g_lo_snapshot_manifest.csv", snapshots)
    _write_csv(output_dir / "g_lo_analysis_stage_contract.csv", stages)
    total_tib = float(storage[-1]["uncompressed_total_TiB"])
    result = {
        "status": "complete_preproduction_readiness_contract",
        "decision_label": "FOUR_CASE_CONTRACT_READY_QUOTA_AND_PILOT_GATES_PENDING",
        "case_count": len(cases),
        "g_lo_snapshot_count": len(snapshots),
        "uncompressed_four_case_TiB": total_tib,
        "quota_floor_TiB": 16,
        "quota_preferred_TiB": 20,
        "compression_forecast_status": "pending_live_reversible_pilot",
        "submission_hold": "C-HI/C-LO/G-HI production waits for confirmed quota increase",
        "gates": {
            "factorial_complete_on_plan": {row["case"] for row in cases} == {"C-HI", "C-LO", "G-LO", "G-HI"},
            "matched_cadence_declared": True,
            "uncompressed_ceiling_below_quota_floor": total_tib < 16,
            "protected_g_lo_snapshot_surface_explicit": len(snapshots) == 6,
            "g_lo_rerun_conditional_not_default": next(row for row in cases if row["case"] == "G-LO")["production_action"] == "analyse_existing_conditional_rerun_only",
        },
    }
    (output_dir / "four_case_preproduction_readiness_metadata.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protected-contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.protected_contract, args.output_dir)
    except (ReadinessError, OSError, ValueError) as exc:
        print(f"readiness_error={exc}")
        return 2
    print(f"decision_label={result['decision_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
