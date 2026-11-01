#!/usr/bin/env python3
"""Freeze the authorised coarse reflective/outflow experiment for Kunanyi."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile


CASES = {"cluster_002003": "690366", "group_002031": "690371"}
BOUNDARIES = ("reflective", "outflow")
CODE_TIME_PER_MYR = 306.601393788


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_setting(text: str, key: str, value: str) -> str:
    pattern = rf"(?m)^{re.escape(key)}\s+[^\n]*$"
    if len(re.findall(pattern, text)) != 1:
        raise ValueError(f"expected exactly one setting: {key}")
    return re.sub(pattern, f"{key:<17}{value}", text)


def render_ini(template: str, boundary: str, smoke: bool) -> str:
    if boundary not in BOUNDARIES:
        raise ValueError(boundary)
    text = template.replace(
        "[Static Grid Output]\n", "[Static Grid Output]\n\nlog_dir          ./outputs/logs\noutput_dir       ./outputs\n"
    )
    for axis in (1, 2, 3):
        for side in ("beg", "end"):
            text = replace_setting(text, f"X{axis}-{side}", boundary)
    text = replace_setting(text, "analysis", "-1.0  1")
    text = replace_setting(text, "log", "1")
    if smoke:
        text = replace_setting(text, "tstop", f"{0.25 * CODE_TIME_PER_MYR:.12f}")
        text = replace_setting(text, "dbl.h5", f"{0.25 * CODE_TIME_PER_MYR:.12f}  -1")
    return text


def export_source(repo: Path, dest: Path, paths: list[str]) -> str:
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--", *paths], text=True)
    if dirty.strip():
        raise ValueError(f"source paths have uncommitted changes: {repo}: {dirty}")
    data = subprocess.check_output(["git", "-C", str(repo), "archive", "--format=tar", revision, *paths])
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(dest, filter="data")
    return revision


def build(args: argparse.Namespace) -> Path:
    repo = args.repo.resolve()
    dest = args.output.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    snapshots = {
        "pluto": export_source(args.pluto, dest / "source/pluto", ["Src", "Tools", "Config", "setup.py", "COPYING", "CHANGES"]),
        "jet_setup": export_source(args.jet_setup, dest / "source/jet-setup", ["src", "LICENSE"]),
    }
    files = [
        "docs/science/paired_nojet_boundary_experiment_2026-11-01.md",
        "scripts/kunanyi/build_paired_nojet_stage.py",
        "scripts/kunanyi/paired_nojet_control.pbs",
        "scripts/kunanyi/paired_nojet_diagnostics.c",
        "scripts/kunanyi/paired_nojet_diagnostics.h",
        "scripts/kunanyi/patch_paired_nojet_sources.py",
        "scripts/kunanyi/run_q031_measured.py",
        "scripts/science/validate_paired_nojet_outputs.py",
        "scripts/science/validate_paired_nojet_budget.py",
        "scripts/science/pluto_h5_level3_ambient_extract.py",
        "scripts/science/select_common_age_hdf5.py",
        "scripts/science/measure_q031_fluxes.py",
        "scripts/science/snapshot_energy.py",
        "tests/test_paired_nojet_source_patch.py",
        "tests/test_paired_nojet_outputs.py",
        "tests/test_paired_nojet_stage.py",
        "tests/test_paired_nojet_budget.py",
    ]
    for name in files:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / name, target)
    subprocess.run([
        args.python, str(dest / "scripts/kunanyi/patch_paired_nojet_sources.py"),
        "--pluto-dir", str(dest / "source/pluto"),
        "--jet-setup-dir", str(dest / "source/jet-setup"),
        "--diagnostics-dir", str(dest / "scripts/kunanyi"),
        "--receipt", str(dest / "source_patch_receipt.json"),
    ], check=True)
    historical = repo / "docs/science/assets/nojet_control_stocktake_2026-11-01/executed_controls"
    template = (historical / "cluster_002003/690366.kunanyi-ohpc/pluto.ini").read_text()
    inputs = {}
    for case, job in CASES.items():
        source = historical / case / (job + ".kunanyi-ohpc")
        metadata = json.loads((repo / "docs/science/assets/nojet_control_audit_2026-11-01/results_bundle/results" / case / "audit_metadata.json").read_text())
        table_name = f"tabulated_cosmo_{case.split('_')[1]}.csv"
        table_record = next(r for r in metadata["configuration_files"] if Path(r["path"]).name == table_name)
        table = table_record["text"].encode()
        if hashlib.sha256(table).hexdigest() != table_record["sha256"]:
            raise ValueError(f"retained atmosphere table hash mismatch: {case}")
        inputs[case] = {"table_sha256": table_record["sha256"], "historical_job": job}
        for smoke in (False, True):
            for boundary in BOUNDARIES:
                d = dest / ("smoke_inputs" if smoke else "inputs") / f"{case}_{boundary}"
                d.mkdir(parents=True)
                (d / "pluto.ini").write_text(render_ini(template, boundary, smoke))
                for name in ("environment.ini", "definitions.h", "definitions_usr.h"):
                    shutil.copy2(source / name, d / name)
                (d / table_name).write_bytes(table)
    contract = {
        "schema": 1,
        "status": "authorised_for_target_smoke_then_coarse_pair_runs",
        "authorisation": "Go ahead with the cheap paired reflective/outflow controls, keeping everything else identical. Hold off on a full production-matched run.",
        "source_revisions": snapshots,
        "project_revision": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "atmospheres": inputs,
        "boundaries": list(BOUNDARIES),
        "sole_within_pair_physics_difference": "all six Boundary values: reflective versus outflow",
        "grid_nx_ny_nz": [400, 400, 500],
        "grid_spacing_kpc": 1.0,
        "duration_myr": 50.0,
        "smoke_duration_myr": 0.25,
        "ranks": 28,
        "decomposition": [2, 2, 7],
        "source_disable": "zero start/end/active times plus explicit inactive-intermittency guard before fmod",
        "new_full_grid_production_matched_run": False,
        "outputs_per_full_run": 6,
        "estimated_full_raw_bytes_all_four": 4 * 6 * 5766745108,
        "notes": "One instrumented binary; fresh starts after smoke; no frozen production or migration input is modified.",
    }
    (dest / "experiment_contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    records = []
    for p in sorted(dest.rglob("*")):
        if p.is_symlink():
            raise ValueError(f"unexpected stage symlink: {p}")
        if p.is_file():
            records.append(f"{sha(p)}  {p.relative_to(dest).as_posix()}")
    (dest / "stage_checksums.sha256").write_text("\n".join(records) + "\n")
    archive = dest.with_suffix(".tar.gz")
    with tarfile.open(archive, "x:gz") as handle:
        handle.add(dest, arcname=dest.name)
    print(json.dumps({"stage": str(dest), "archive": str(archive), "sha256": sha(archive), "bytes": archive.stat().st_size}))
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--pluto", type=Path, default=Path("/Users/bwbrook/git/utas-agn/pluto"))
    parser.add_argument("--jet-setup", type=Path, default=Path("/Users/bwbrook/git/utas-agn/jet-setup"))
    parser.add_argument("--python", default="python3")
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
