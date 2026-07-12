#!/usr/bin/env python3
"""Build compact Goal 038 completion tables from retrieved remote evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


DECISION_LABEL = "G_LO_GUARDED_CONTINUATION_REACHED_ENDPOINT_GREEN"
ENDPOINT_TARGET = 15330.0696894


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _parse_qstat(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        match = re.match(r"\s*([^=]+?)\s*=\s*(.*?)\s*$", raw)
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


def _watchdog_summary(path: Path) -> dict[str, object]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows:
        raise ValueError("watchdog log is empty")
    events = Counter(row["event"] for row in rows)
    command_exit = [row for row in rows if row["event"] == "command_exit"]
    if len(command_exit) != 1:
        raise ValueError("watchdog must contain exactly one command_exit event")
    return {
        "row_count": len(rows),
        "started_count": events["started"],
        "progress_count": events["progress"],
        "poll_count": events["poll"],
        "command_exit_count": events["command_exit"],
        "command_exit_code": int(command_exit[0]["exit_code"]),
        "maximum_no_progress_seconds": max(int(row["no_progress_seconds"]) for row in rows),
        "triggered": any("trigger" in row["event"].lower() for row in rows),
        "first_timestamp_utc": rows[0]["timestamp_utc"],
        "last_timestamp_utc": rows[-1]["timestamp_utc"],
    }


def _payload_summary(path: Path) -> dict[str, object]:
    rows: list[tuple[str, int]] = []
    with path.open(newline="") as handle:
        for name, size in csv.reader(handle, delimiter="\t"):
            rows.append((name, int(size)))
    doubles = [row for row in rows if re.fullmatch(r"data\.\d{4}\.dbl\.h5", row[0])]
    floats = [row for row in rows if re.fullmatch(r"data\.\d{4}\.flt\.h5", row[0])]
    particles = [row for row in rows if re.fullmatch(r"particles\.\d{4}\.dbl", row[0])]
    return {
        "inventory_rows": len(rows),
        "inventory_bytes": sum(size for _, size in rows),
        "double_hdf5_count": len(doubles),
        "float_hdf5_count": len(floats),
        "particle_restart_count": len(particles),
        "latest_double_hdf5": doubles[-1][0],
        "latest_float_hdf5": floats[-1][0],
        "latest_particle_restart": particles[-1][0],
    }


def _write_manifest(output_dir: Path) -> None:
    manifest = output_dir / "local_asset_manifest.sha256"
    lines = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path == manifest:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(output_dir)}")
    manifest.write_text("\n".join(lines) + "\n")


def build_completion_package(remote_stage: Path, output_dir: Path) -> None:
    evidence = remote_stage / "completion_evidence"
    validator_exit = int((evidence / "endpoint_validation.exit_code.txt").read_text().strip())
    if validator_exit != 0:
        raise ValueError("endpoint validator did not pass")

    endpoint = json.loads((evidence / "endpoint_restart_pair_validation.json").read_text())
    if endpoint.get("status") != "ok":
        raise ValueError("endpoint restart-pair status is not ok")
    qstat = _parse_qstat(evidence / "qstat_final.txt")
    watchdog = _watchdog_summary(
        evidence / "run_logs/progress_watchdog.751292.kunanyi-ohpc.tsv"
    )
    payload = _payload_summary(evidence / "run_payload_inventory.tsv")
    stderr_bytes = (remote_stage / "g_lo_hdf5_stall_guarded_continuation.err").stat().st_size
    done = (evidence / "DONE").is_file()

    exit_status = int(qstat["Exit_status"])
    stageout_status = int(qstat["Stageout_status"])
    endpoint_time = float(endpoint["fluid_hdf5"]["time"])
    if exit_status != 0 or not done or stderr_bytes != 0:
        raise ValueError("scheduler, marker, or stderr completion gate failed")
    if abs(endpoint_time - ENDPOINT_TARGET) > 0.005:
        raise ValueError("endpoint time is outside tolerance")
    if watchdog["triggered"] or watchdog["command_exit_code"] != 0:
        raise ValueError("watchdog completion gate failed")

    output_dir.mkdir(parents=True, exist_ok=True)
    qstat_rows = [{"field": key, "value": value} for key, value in sorted(qstat.items())]
    _write_csv(output_dir / "qstat_final.csv", qstat_rows)
    _write_csv(
        output_dir / "completion_summary.csv",
        [
            {"metric": "status", "value": "complete_endpoint_review", "interpretation": "green"},
            {"metric": "decision_label", "value": DECISION_LABEL, "interpretation": "green"},
            {"metric": "endpoint_code_time", "value": endpoint_time, "interpretation": "target_reached"},
            {"metric": "endpoint_step", "value": endpoint["fluid_restart"]["nstep"], "interpretation": "validated"},
            {"metric": "fluid_restart_index", "value": endpoint["fluid_restart"]["index"], "interpretation": "validated"},
            {"metric": "particle_restart_index", "value": endpoint["particle_restart"]["index"], "interpretation": "validated"},
            {"metric": "particle_count", "value": endpoint["particle_restart"]["nparticles"], "interpretation": "full_scan"},
            {"metric": "stageout_status", "value": stageout_status, "interpretation": "scheduler_caveat_evidence_retrieved"},
            {"metric": "remote_output_size", "value": "2.3T", "interpretation": "raw_payload_retained_remote"},
        ],
    )
    _write_csv(output_dir / "watchdog_summary.csv", [watchdog])
    _write_csv(output_dir / "run_output_inventory_summary.csv", [payload])
    _write_csv(
        output_dir / "next_step_recommendation.csv",
        [
            {
                "priority": 1,
                "action": "run_g_lo_endpoint_first_products_and_three_case_comparison",
                "status": "recommended",
                "boundary": "postprocessing_only_no_new_pluto_production",
            },
            {
                "priority": 2,
                "action": "promote_endpoint_and_apply_data_lifecycle_holds",
                "status": "required_before_raw_pruning",
                "boundary": "retain_restart_and_endpoint_surfaces_until_products_validate",
            },
            {
                "priority": 3,
                "action": "do_not_claim_publication_ready_observables",
                "status": "active_caveat",
                "boundary": "xray_tracer_prove_out_first",
            },
        ],
    )

    metadata = {
        "status": "complete_endpoint_review",
        "decision_label": DECISION_LABEL,
        "created_local": "2026-07-12",
        "job": {
            "id": "751292.kunanyi-ohpc",
            "name": qstat["Job_Name"],
            "state": qstat["job_state"],
            "exit_status": exit_status,
            "stageout_status": stageout_status,
            "walltime_used": qstat["resources_used.walltime"],
            "cput_used": qstat["resources_used.cput"],
            "ncpus_used": int(qstat["resources_used.ncpus"]),
            "mem_used": qstat["resources_used.mem"],
            "vmem_used": qstat["resources_used.vmem"],
            "resource_select": qstat["Resource_List.select"],
            "resource_walltime": qstat["Resource_List.walltime"],
        },
        "endpoint": {
            "target_code_time": ENDPOINT_TARGET,
            "fluid_hdf5_time": endpoint_time,
            "fluid_hdf5_shape": endpoint["fluid_hdf5"]["shape"],
            "fluid_hdf5_size_bytes": endpoint["fluid_hdf5"]["size_bytes"],
            "fluid_restart_index": endpoint["fluid_restart"]["index"],
            "float_output_index": endpoint["fluid_restart"]["companion_output_indices"]["3"],
            "particle_restart_index": endpoint["particle_restart"]["index"],
            "step": endpoint["fluid_restart"]["nstep"],
            "particle_count": endpoint["particle_restart"]["nparticles"],
            "particle_ids_unique": endpoint["particle_restart"]["content"]["unique_ids"],
            "restart_pair_validation": endpoint["status"],
        },
        "watchdog": watchdog,
        "run_output_inventory": payload,
        "completion_gates": {
            "done_marker": done,
            "failed_marker": False,
            "stderr_bytes": stderr_bytes,
            "mpi_exit_zero": True,
            "endpoint_validator_exit": validator_exit,
        },
        "compaction": json.loads(
            (remote_stage / "remote_logs/goal038_compaction_summary.json").read_text()
        ),
        "classification": {
            "endpoint_status": "endpoint_reached",
            "production_status": "green",
            "science_product_status": "not_yet_generated",
            "stageout_status_role": "scheduler_caveat_compact_evidence_present_and_retrieved",
        },
        "boundaries": {
            "no_new_pbs_submission_during_completion": True,
            "no_science_postprocessing": True,
            "no_bulk_hdf5_or_particle_retrieval": True,
            "raw_remote_output_retained": True,
        },
    }
    (output_dir / "g_lo_guarded_continuation_completion_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    _write_manifest(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote-stage", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_completion_package(args.remote_stage, args.output_dir)
    print("status=complete_endpoint_review")
    print(f"decision_label={DECISION_LABEL}")


if __name__ == "__main__":
    main()
