#!/usr/bin/env python3
"""Read migration receipts and selected-age map metadata without changing payloads."""

import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess


def inspect_path(path, hash_contents=False):
    result = {"path": str(path), "exists": path.exists(), "is_symlink": path.is_symlink()}
    if path.is_symlink():
        result["link_target"] = os.readlink(str(path))
    if path.exists():
        stat = path.stat()
        result.update(resolved_path=str(path.resolve()), size_bytes=stat.st_size,
                      mtime_ns=stat.st_mtime_ns, is_file=path.is_file(), is_dir=path.is_dir())
        if hash_contents and path.is_file():
            result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def inspect(stage):
    plan_path = stage / "migration_plan.json"
    plan = json.loads(plan_path.read_text())
    statuses = {}
    for path in sorted((stage / "state").glob("unit-*/status.json")):
        record = json.loads(path.read_text())
        statuses[record["source"]] = (path, record)
    units = []
    for unit in plan["units"]:
        item = {"source": inspect_path(Path(unit["source"])),
                "destination": inspect_path(Path(unit["destination"]))}
        if unit["source"] in statuses:
            path, record = statuses[unit["source"]]
            item.update(status=record, status_file=inspect_path(path, True),
                        tombstone=inspect_path(Path(record["tombstone"])),
                        policy_receipt=inspect_path(path.parent / "policy-receipt.json", True))
        else:
            item["status"] = None
        units.append(item)
    result = subprocess.run(["qstat", "-xf", "820961.kunanyi-ohpc"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    job_keys = ("Job Id:", "job_state =", "Exit_status =", "resources_used.walltime =",
                "Resource_List.walltime =", "stime =", "mtime =", "run_count =")
    job = {"returncode": result.returncode, "stderr": result.stderr,
           "selected_fields": [line.strip() for line in result.stdout.splitlines()
                               if any(key in line for key in job_keys)]}
    base = Path("/u/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables")
    cases = []
    for case in ("C-HI", "C-LO", "G-HI", "G-LO"):
        root = base / ("xray_cavity_g_hi_r2" if case == "G-HI" else "xray_cavity") / case.lower().replace("-", "_")
        maps = []
        for age in (10, 20, 30, 40, 50):
            for view in (0, 45, 90):
                directory = root / ("age_%02d" % age) / ("xraise_grid_%ddeg" % view)
                names = ("xray_1kev_xraise_corrected_mjy_sr.tsv", "tracer_max_los.tsv",
                         "x_kpc.tsv" if view == 0 else "u_kpc.tsv", "z_kpc.tsv",
                         "xraise_grid_smoke_metadata.json", "xraise_grid_smoke_summary.csv")
                files = [inspect_path(directory / name, name not in names[:2]) for name in names]
                maps.append({"age_myr": age, "view_deg": view, "files": files})
        manifest = root / "source_manifest.csv"
        native = []
        if manifest.is_file():
            with manifest.open() as handle:
                for row in csv.DictReader(handle):
                    native.append({"manifest_row": row, "input": inspect_path(Path(row["input_h5"]))})
        cases.append({"case": case, "root": inspect_path(root), "maps": maps,
                      "age_00_directory": inspect_path(root / "age_00"),
                      "source_manifest": inspect_path(manifest, True), "native_inputs": native})
    return {"observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "inspection_scope": "metadata, small coordinate/metadata hashes and existing migration receipts; no large payload rehash, numerical map validation or quota measurement",
            "migration_plan": inspect_path(plan_path, True),
            "plan_binding": inspect_path(stage / "state/plan-binding.json", True),
            "frozen_stage_checksums": inspect_path(stage / "stage_checksums.sha256", True),
            "job": job, "migration_units": units, "selected_age_maps": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=Path("/u/bwbrook/codex_kunanyi/scratch_home_migration_2026-10-16"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(inspect(args.stage), indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x") as handle:
            handle.write(payload)
        print(str(args.output), len(payload.encode()), hashlib.sha256(payload.encode()).hexdigest())
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
