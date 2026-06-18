#!/usr/bin/env python3
"""Package the C-HI Level 3 remote extraction closeout."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any


def load_level3_base():
    path = Path(__file__).with_name("build_final_level3_ambient_energy.py")
    spec = importlib.util.spec_from_file_location("build_final_level3_ambient_energy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_level3_base()

PRODUCT = "c_hi_final_level3_remote_extraction_closeout"
DATE = "2026-06-18"
JOB_ID = "699326.kunanyi-ohpc"
REMOTE_STAGE_DIR = "/u/bwbrook/codex_kunanyi/goal009_final_level3_ambient_energy"
REMOTE_ANALYSIS_ROOT = "/scratch/bwbrook/xray_cavities_analysis/2026-06-18-c-hi-final-level3-ambient-energy"
ARCHIVE_SHA256 = "77d01152913072afcfcf4a0ebffdb9d50a50afea8a25ddb9c311e04cb8cd1d96"
EXTRACTOR_SHA256 = "00d4f10b729cd74982514f4dde52c8ef7f5ee7a2b1074305d479c99aa6cd26de"
WRAPPER_SHA256 = "3e84ff8a27571d1dac66b958390a97d924d17b9694262788380b98b66c8fdc97"

REMOTE_JOB_STATUS = {
    "job_id": JOB_ID,
    "job_name": "c_hi_l3amb",
    "state": "F",
    "exit_status": 0,
    "queue": "normal",
    "resources_used": {
        "cpupercent": 30,
        "cput": "00:01:12",
        "mem": "150096kb",
        "ncpus": 1,
        "vmem": "423060kb",
        "walltime": "00:02:39",
    },
    "resource_request": {
        "select": "1:ncpus=1:mpiprocs=1:mem=64gb",
        "walltime": "04:00:00",
    },
    "ctime": "Thu Jun 18 13:06:14 2026",
    "mtime": "Thu Jun 18 13:08:53 2026",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_remote_logs(stdout_path: Path, stderr_path: Path) -> None:
    stdout = stdout_path.read_text()
    if "level3_extractor_validation=passed" not in stdout:
        raise ValueError("remote stdout does not contain level3_extractor_validation=passed")
    if stderr_path.stat().st_size != 0:
        raise ValueError(f"remote stderr is not empty: {stderr_path}")


def validate_extractor_rows(rows: list[dict[str, str]]) -> None:
    by_side = {row["side"]: row for row in rows}
    expected = {"negative_z", "positive_z", "bipolar_total"}
    missing = expected - set(by_side)
    if missing:
        raise ValueError(f"missing extractor sides: {sorted(missing)}")

    for side, row in by_side.items():
        count = int(row["ambient_cell_count"])
        if count <= 0:
            raise ValueError(f"{side} ambient_cell_count must be positive")
        thermal = BASE.parse_float(row["thermal_delta_erg"], context=f"{side} thermal_delta_erg")
        kinetic = BASE.parse_float(row["kinetic_delta_erg"], context=f"{side} kinetic_delta_erg")
        total = BASE.parse_float(
            row["thermal_plus_kinetic_delta_erg"],
            context=f"{side} thermal_plus_kinetic_delta_erg",
        )
        volume = BASE.parse_float(row["ambient_volume_kpc3"], context=f"{side} ambient_volume_kpc3")
        if volume <= 0.0:
            raise ValueError(f"{side} ambient_volume_kpc3 must be positive")
        if not math.isclose(total, thermal + kinetic, rel_tol=1.0e-12, abs_tol=0.0):
            raise ValueError(f"{side} thermal+kinetic mismatch")


def method_decision_rows(*, remote_preflight: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "decision": "baseline_reference",
            "status": "identified",
            "choice": f"{remote_preflight['baseline_h5']}::{remote_preflight['baseline_timestep']}",
            "rationale": "Earliest full-grid initial output from the same C-HI production chain.",
        },
        {
            "decision": "final_endpoint",
            "status": "identified",
            "choice": f"{remote_preflight['final_h5']}::{remote_preflight['final_timestep']}",
            "rationale": "Accepted final 50 Myr C-HI endpoint used by Goals 003, 005, 007, and 008.",
        },
        {
            "decision": "grid_compatibility",
            "status": "remote_preflight_passed",
            "choice": f"shape {remote_preflight['final_shape_nz_ny_nx']}",
            "rationale": "Remote job preflight confirmed required datasets and matching field shapes.",
        },
        {
            "decision": "coordinate_compatibility",
            "status": "executed_by_remote_extractor_success",
            "choice": "compare baseline/final X, Y, and Z coordinate axes with rtol=0 and atol=1e-10 kpc",
            "rationale": (
                "The SHA-matched extractor unconditionally validates coordinates before streaming "
                "subtraction; the remote job reached extractor validation and Exit_status=0."
            ),
        },
        {
            "decision": "ambient_tracer_exclusion",
            "status": "selected",
            "choice": "final cells with tr1 <= 5e-3 are ambient; tr1 > 5e-3 remains Level 2 lobe truth",
            "rationale": "Keeps Level 3 compatible with the accepted Level 2 tracer-lobe threshold.",
        },
        {
            "decision": "spatial_mask",
            "status": "selected",
            "choice": "whole-grid side-aware mask, split by z < 0 and z >= 0 plus bipolar total",
            "rationale": "Captures shocked ambient gas outside tracer-defined lobes without adding a new cavity geometry.",
        },
        {
            "decision": "thermal_formula",
            "status": "computed",
            "choice": "sum((prs_final - prs_baseline) * dV / (gamma - 1)) * unit_energy",
            "rationale": "Matches the pressure-volume unit convention in pluto_h5_truth_extract.c.",
        },
        {
            "decision": "kinetic_formula",
            "status": "computed",
            "choice": "sum(0.5 * (rho_final*v_final^2 - rho_baseline*v_baseline^2) * dV) * unit_energy",
            "rationale": "Uses the same PLUTO code-unit energy conversion as Level 2 truth.",
        },
        {
            "decision": "remote_postprocessing_access",
            "status": "completed",
            "choice": f"{JOB_ID}, Exit_status=0",
            "rationale": "Bounded one-node PBS post-processing job completed and compact outputs were retrieved.",
        },
        {
            "decision": "gravitational_component",
            "status": "blocked_missing_potential",
            "choice": "not computed in Goal 009",
            "rationale": "No reviewed potential/profile zero-point convention is available inside authorized evidence.",
        },
    ]


def build_closeout_package(
    *,
    output_dir: Path,
    extractor_csv: Path,
    stdout_path: Path,
    stderr_path: Path,
    archive_path: Path,
    level1_path: Path,
    level2_path: Path,
    remote_preflight: dict[str, Any],
) -> dict[str, Any]:
    BASE.validate_grid_preflight(remote_preflight)
    validate_remote_logs(stdout_path, stderr_path)
    extractor_rows = read_rows(extractor_csv)
    validate_extractor_rows(extractor_rows)

    comparators = BASE.load_comparators(
        level1_path=level1_path,
        level2_path=level2_path,
        pV_erg=BASE.DEFAULT_PV_ERG,
        two_point_five_pV_erg=BASE.DEFAULT_TWO_POINT_FIVE_PV_ERG,
        four_pV_erg=BASE.DEFAULT_FOUR_PV_ERG,
    )
    gravitational_note = (
        "The accepted HDF5 outputs do not expose gravitational potential, and this repo does not "
        "contain a reviewed potential/profile zero-point convention for Level 3 gravitational energy."
    )
    energy_rows = BASE.build_energy_rows(
        extractor_rows=extractor_rows,
        comparators=comparators,
        gravitational_status="blocked_missing_potential",
        gravitational_note=gravitational_note,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    BASE.write_dict_rows(output_dir / "level3_ambient_energy.csv", energy_rows)
    BASE.write_dict_rows(
        output_dir / "level3_method_decisions.csv",
        method_decision_rows(remote_preflight=remote_preflight),
    )

    metadata = {
        "product": PRODUCT,
        "date": DATE,
        "result_status": BASE.result_status(energy_rows),
        "thermal_kinetic_status": "green_level3_thermal_kinetic_closeout",
        "gravitational_status": "blocked_missing_potential",
        "gravitational_note": gravitational_note,
        "coordinate_compatibility_contract": "executed_by_remote_extractor_success",
        "remote_job": REMOTE_JOB_STATUS,
        "remote_stage_dir": REMOTE_STAGE_DIR,
        "remote_analysis_root": REMOTE_ANALYSIS_ROOT,
        "remote_preflight": remote_preflight,
        "comparators_erg": comparators,
        "retrieved_files": {
            "extractor_csv": str(extractor_csv),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "archive": str(archive_path),
        },
        "checksums_sha256": {
            "extractor_csv": sha256(extractor_csv),
            "remote_archive": sha256(archive_path),
            "remote_archive_expected": ARCHIVE_SHA256,
            "staged_extractor": EXTRACTOR_SHA256,
            "staged_pbs_wrapper": WRAPPER_SHA256,
        },
        "tracer_threshold": f"{BASE.DEFAULT_TRACER_THRESHOLD:.0e}",
    }
    if metadata["checksums_sha256"]["remote_archive"] != ARCHIVE_SHA256:
        raise ValueError("retrieved archive checksum does not match remote evidence")
    (output_dir / "level3_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def default_paths(repo_root: Path) -> dict[str, Path]:
    asset_dir = repo_root / "docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18"
    return {
        "level1": repo_root
        / "docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/final_truth/level1_injected_energy.csv",
        "level2": repo_root
        / "docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/final_truth/level2_tracer_lobe_truth.csv",
        "output": asset_dir,
        "extractor_csv": asset_dir / "level3_extractor_output.csv",
        "stdout": asset_dir / "remote_logs/c_hi_final_level3_ambient_energy.out",
        "stderr": asset_dir / "remote_logs/c_hi_final_level3_ambient_energy.err",
        "archive": asset_dir / "remote_logs/final_level3_ambient_energy_2026-06-18.tar.gz",
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    defaults = default_paths(repo_root)
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=defaults["output"])
    parser.add_argument("--extractor-csv", type=Path, default=defaults["extractor_csv"])
    parser.add_argument("--stdout", type=Path, default=defaults["stdout"])
    parser.add_argument("--stderr", type=Path, default=defaults["stderr"])
    parser.add_argument("--archive", type=Path, default=defaults["archive"])
    parser.add_argument("--level1-path", type=Path, default=defaults["level1"])
    parser.add_argument("--level2-path", type=Path, default=defaults["level2"])
    args = parser.parse_args()

    metadata = build_closeout_package(
        output_dir=args.output_dir,
        extractor_csv=args.extractor_csv,
        stdout_path=args.stdout,
        stderr_path=args.stderr,
        archive_path=args.archive,
        level1_path=args.level1_path,
        level2_path=args.level2_path,
        remote_preflight=BASE.DEFAULT_REMOTE_PREFLIGHT,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
