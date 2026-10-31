#!/usr/bin/env python3
"""Bind Q-032 retained inputs and validate/package exploratory outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import stat
import tarfile
from pathlib import Path
from typing import Any

import numpy as np


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
VIEWS = ("0deg", "45deg", "90deg")
SIDES = ("negative_z", "positive_z")
RUNS = (
    "legacy_area_1pct",
    "seed_grow_goal045",
    "deficit_threshold_observer_radial_0.05",
    "deficit_threshold_observer_radial_0.10",
    "deficit_threshold_observer_radial_0.20",
)
CASE_ROOTS = {
    "C-HI": "xray_cavity/c_hi",
    "C-LO": "xray_cavity/c_lo",
    "G-HI": "xray_cavity_g_hi_r2/g_hi",
    "G-LO": "xray_cavity/g_lo",
}
XRAY = "xray_1kev_xraise_corrected_mjy_sr.tsv"
TRACER = "tracer_max_los.tsv"
VERTICAL = "z_kpc.tsv"
METADATA = "xraise_grid_smoke_metadata.json"
ROOT_OUTPUTS = ("method_ladder_rows.csv", "source_maps.csv", "method_ladder_metadata.json")
STAGED_CODE_PATHS = (
    "scripts/science/build_q032_selected_age_method_ladder.py",
    "scripts/science/xray_cavity_method_ladder.py",
    "scripts/science/xray_cavity_synthetic.py",
    "scripts/science/three_case_cavity_recovery.py",
    "scripts/science/build_three_case_cavity_recovery.py",
    "scripts/science/hemisphere_seed_grow_recovery.py",
    "scripts/kunanyi/validate_q032_retained_method_ladder.py",
    "scripts/kunanyi/q032_retained_method_ladder.pbs",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regular_stat(path: Path) -> os.stat_result:
    try:
        result = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"missing required file: {path}") from exc
    if not stat.S_ISREG(result.st_mode):
        raise ValueError(f"required file is not regular: {path}")
    return result


def read_json(path: Path) -> dict[str, Any]:
    regular_stat(path)
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with path.open("x") as handle:
            created = True
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except Exception:
        if created:
            path.unlink()
        raise


def view_directory(base: Path, case: str, age: int, view: str) -> Path:
    return base / CASE_ROOTS[case] / f"age_{age:02d}" / f"xraise_grid_{view}"


def input_binding(base: Path) -> dict[str, Any]:
    views: list[dict[str, Any]] = []
    for case in CASES:
        for age in AGES:
            for view in VIEWS:
                directory = view_directory(base, case, age, view)
                horizontal = "x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"
                names = (XRAY, TRACER, horizontal, VERTICAL, METADATA)
                files: list[dict[str, Any]] = []
                for name in names:
                    path = directory / name
                    before = regular_stat(path)
                    digest = sha256_file(path)
                    after = regular_stat(path)
                    identity_before = (
                        before.st_dev, before.st_ino, before.st_size,
                        before.st_mtime_ns, before.st_ctime_ns,
                    )
                    identity_after = (
                        after.st_dev, after.st_ino, after.st_size,
                        after.st_mtime_ns, after.st_ctime_ns,
                    )
                    if identity_after != identity_before:
                        raise ValueError(f"input changed while hashing: {path}")
                    files.append({
                        "name": name,
                        "path_relative_to_base": str(path.relative_to(base)),
                        "sha256": digest,
                        "size_bytes": after.st_size,
                        "device": after.st_dev,
                        "inode": after.st_ino,
                        "mtime_ns": after.st_mtime_ns,
                        "ctime_ns": after.st_ctime_ns,
                        "mode": stat.S_IMODE(after.st_mode),
                    })
                metadata = read_json(directory / METADATA)
                time_myr = float(metadata.get("time_myr", float("nan")))
                if not math.isfinite(time_myr) or abs(time_myr - age) > 0.05:
                    raise ValueError(f"metadata age mismatch: {directory}")
                projection = metadata.get("projection")
                if not isinstance(projection, dict) or float(projection.get("view_angle_deg", float("nan"))) != float(view.removesuffix("deg")):
                    raise ValueError(f"metadata view mismatch: {directory}")
                if metadata.get("grid_shape_nz_ny_nx") != [1014, 960, 960]:
                    raise ValueError(f"metadata native-grid mismatch: {directory}")
                views.append({"case": case, "age_myr": age, "view": view, "files": files})
    return {
        "schema_version": 1,
        "status": "complete_q032_retained_input_binding",
        "base": str(base.resolve()),
        "view_count": 60,
        "file_count": 300,
        "baselines": {},
        "full_hdf5_included": False,
        "views": views,
    }


def bind_inputs(base: Path, output: Path, compare: Path | None) -> dict[str, Any]:
    binding = input_binding(base)
    if compare is not None and read_json(compare) != binding:
        raise ValueError("retained Q-032 inputs changed between before and after bindings")
    write_json_exclusive(output, binding)
    return binding


def expected_view_keys() -> set[tuple[str, int, str]]:
    return {(case, age, view) for case in CASES for age in AGES for view in VIEWS}


def expected_row_keys() -> set[tuple[str, int, str, str, str]]:
    return {
        (case, age, view, run, side)
        for case, age, view in expected_view_keys()
        for run in RUNS
        for side in SIDES
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    regular_stat(path)
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def input_xray_lookup(binding: dict[str, Any]) -> dict[tuple[str, int, str], dict[str, Any]]:
    result: dict[tuple[str, int, str], dict[str, Any]] = {}
    for view in binding["views"]:
        files = {item["name"]: item for item in view["files"]}
        result[(view["case"], int(view["age_myr"]), view["view"])] = files[XRAY]
    return result


def parse_manifest(path: Path) -> dict[str, str]:
    regular_stat(path)
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        digest, separator, name = line.partition("  ")
        candidate = Path(name)
        if separator != "  " or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"invalid manifest line: {line}")
        if candidate.is_absolute() or ".." in candidate.parts or name in entries:
            raise ValueError(f"unsafe or duplicate manifest member: {name}")
        entries[name] = digest
    return entries


def validate_mask(path: Path) -> None:
    with np.load(path, allow_pickle=False) as packed:
        shape = tuple(int(value) for value in packed["shape"])
        if len(shape) != 2 or min(shape) < 2:
            raise ValueError(f"invalid packed-mask shape: {path}")
        expected_keys = {
            "horizontal_axis_kpc", "z_axis_kpc", "tracer", "shape",
            *(f"{run}__{side}" for run in RUNS for side in SIDES),
        }
        if set(packed.files) != expected_keys:
            raise ValueError(f"packed-mask keys differ from method contract: {path}")
        if packed["horizontal_axis_kpc"].size != shape[1] or packed["z_axis_kpc"].size != shape[0]:
            raise ValueError(f"packed-mask axes differ from shape: {path}")
        packed_size = (shape[0] * shape[1] + 7) // 8
        for key in expected_keys - {"horizontal_axis_kpc", "z_axis_kpc", "shape"}:
            if packed[key].size != packed_size:
                raise ValueError(f"packed-mask payload has wrong size: {path}:{key}")


def expected_result_paths() -> set[str]:
    stems = {f"{case}_age{age:02d}_{view}" for case, age, view in expected_view_keys()}
    return {
        *ROOT_OUTPUTS,
        *(f"masks/{stem}.npz" for stem in stems),
        *(f"stamps/{stem}.png" for stem in stems),
    }


def validate_result(result: Path, binding: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    metadata = read_json(result / "method_ladder_metadata.json")
    if metadata.get("status") != "complete_q032_selected_age_method_ladder":
        raise ValueError("Q-032 method-ladder metadata is not complete")
    if metadata.get("views_analysed") != 60 or metadata.get("baselines") != {}:
        raise ValueError("Q-032 view count or no-baseline contract failed")
    if set(metadata.get("runs", ())) != set(RUNS):
        raise ValueError("Q-032 run labels differ from the five-rung contract")
    rows = read_csv(result / "method_ladder_rows.csv")
    keys = [
        (row["case"], int(row["snapshot_index"]), row["view"], row["run"], row["side"])
        for row in rows
    ]
    if len(rows) != 600 or len(set(keys)) != 600 or set(keys) != expected_row_keys():
        raise ValueError("Q-032 rows do not cover the exact 60-view x 5-run x 2-side contract")
    if any(not row.get("topology_class") for row in rows):
        raise ValueError("Q-032 rows lost topology classifications")
    sources = read_csv(result / "source_maps.csv")
    source_keys = [(row["case"], int(row["snapshot_index"]), row["view"]) for row in sources]
    if len(sources) != 60 or len(set(source_keys)) != 60 or set(source_keys) != expected_view_keys():
        raise ValueError("Q-032 source map ledger does not cover exactly 60 views")
    input_maps = input_xray_lookup(binding)
    for row, key in zip(sources, source_keys, strict=True):
        expected = input_maps[key]
        if row["sha256"] != expected["sha256"] or int(row["size_bytes"]) != expected["size_bytes"]:
            raise ValueError(f"source map ledger differs from input binding: {key}")
        if Path(row["path"]).resolve() != (Path(binding["base"]) / expected["path_relative_to_base"]).resolve():
            raise ValueError(f"source map path differs from input binding: {key}")
    expected_paths = expected_result_paths()
    mask_paths = sorted(result.glob("masks/*.npz"))
    stamp_paths = sorted(result.glob("stamps/*.png"))
    if len(mask_paths) != 60 or len(stamp_paths) != 60:
        raise ValueError("Q-032 mask or stamp count differs from 60")
    for path in mask_paths:
        validate_mask(path)
    for path in stamp_paths:
        if path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"invalid PNG stamp: {path}")
    manifest_path = result / "manifest.sha256"
    manifest = parse_manifest(manifest_path)
    if set(manifest) != expected_paths:
        raise ValueError("Q-032 manifest membership differs from the fixed science-file list")
    actual_files = {
        str(path.relative_to(result)) for path in result.rglob("*") if path.is_file()
    }
    if actual_files != expected_paths | {"manifest.sha256"}:
        raise ValueError("Q-032 result directory contains unexpected or missing files")
    for name, expected in manifest.items():
        path = result / name
        regular_stat(path)
        observed = sha256_file(path)
        if observed != expected:
            raise ValueError(f"Q-032 manifest hash mismatch: {name}")
    validation = {
        "schema_version": 1,
        "status": "validated_q032_retained_method_ladder_exploratory",
        "views": 60,
        "rows": 600,
        "runs_per_view": 5,
        "sides_per_run": 2,
        "packed_masks": 60,
        "stamps": 60,
        "baselines": {},
        "topology_policy": "all method rows retained, including production-rejected topology",
        "production_adoption": False,
    }
    accepted = dict(manifest)
    accepted["manifest.sha256"] = sha256_file(manifest_path)
    return validation, accepted


def create_and_verify_archive(result: Path, archive: Path, accepted: dict[str, str]) -> list[dict[str, Any]]:
    if os.path.lexists(archive):
        raise FileExistsError(f"refusing to overwrite archive: {archive}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with tarfile.open(archive, "x:gz", format=tarfile.PAX_FORMAT) as handle:
            created = True
            for name in sorted(accepted):
                source = result / name
                regular_stat(source)
                info = handle.gettarinfo(str(source), arcname=str(Path(result.name) / name))
                if not info.isfile():
                    raise ValueError(f"non-file archive member: {source}")
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mode = 0o600
                info.mtime = 0
                with source.open("rb") as payload:
                    handle.addfile(info, payload)
        members: list[dict[str, Any]] = []
        with tarfile.open(archive, "r:gz") as handle:
            archived = handle.getmembers()
            expected_names = [str(Path(result.name) / name) for name in sorted(accepted)]
            if [member.name for member in archived] != expected_names:
                raise ValueError("archive members differ from fixed manifest-file list")
            for member, name in zip(archived, sorted(accepted), strict=True):
                if not member.isfile():
                    raise ValueError(f"non-file archive payload: {member.name}")
                payload = handle.extractfile(member)
                if payload is None:
                    raise ValueError(f"unreadable archive payload: {member.name}")
                digest = hashlib.sha256()
                size = 0
                for block in iter(lambda: payload.read(1024 * 1024), b""):
                    digest.update(block)
                    size += len(block)
                if digest.hexdigest() != accepted[name]:
                    raise ValueError(f"archive payload hash mismatch: {member.name}")
                members.append({"path": member.name, "sha256": digest.hexdigest(), "size_bytes": size})
        return members
    except Exception:
        if created:
            archive.unlink()
        raise


def validated_stage_code_hashes(stage_root: Path, checksum_path: Path) -> dict[str, str]:
    regular_stat(checksum_path)
    declared: dict[str, str] = {}
    for line in checksum_path.read_text().splitlines():
        digest, separator, name = line.partition("  ")
        if separator == "  ":
            declared[name.removeprefix("./")] = digest
    observed: dict[str, str] = {}
    for name in STAGED_CODE_PATHS:
        path = stage_root / name
        regular_stat(path)
        digest = sha256_file(path)
        if declared.get(name) != digest:
            raise ValueError(f"stage checksum does not bind current code: {name}")
        observed[name] = digest
    return observed


def validate_and_package(
    *, base: Path, result: Path, before: Path, after: Path,
    validation_path: Path, archive: Path, receipt: Path,
    stage_root: Path, stage_checksums: Path, source_commit: str,
) -> dict[str, Any]:
    if any(os.path.lexists(path) for path in (validation_path, archive, receipt)):
        raise FileExistsError("refusing to overwrite Q-032 validation, archive, or receipt")
    before_binding = read_json(before)
    after_binding = read_json(after)
    if before_binding != after_binding or before_binding.get("base") != str(base.resolve()):
        raise ValueError("before/after Q-032 input bindings differ")
    if source_commit != "7da6ed5":
        raise ValueError(f"unexpected Q-032 source commit: {source_commit}")
    staged_code_hashes = validated_stage_code_hashes(stage_root, stage_checksums)
    validation, accepted = validate_result(result, before_binding)
    write_json_exclusive(validation_path, validation)
    archive_created = False
    receipt_created = False
    try:
        members = create_and_verify_archive(result, archive, accepted)
        archive_created = True
        payload = {
            "schema_version": 1,
            "status": "complete_q032_retained_method_ladder_exploratory",
            "scientific_scope": "60-retained-view exploratory diagnostic",
            "production_adoption": False,
            "baseline": "absent",
            "topology_policy": validation["topology_policy"],
            "existing_scientific_exclusions": [{
                "case": "G-HI",
                "age_myr": 50,
                "evaluation_processing": "included in all method-ladder rows and artefacts",
                "scientific_interpretation": "excluded from existing production scientific inference",
            }],
            "source_commit": source_commit,
            "stage_checksums_sha256": sha256_file(stage_checksums),
            "staged_code_hashes": staged_code_hashes,
            "input_binding_before_sha256": sha256_file(before),
            "input_binding_after_sha256": sha256_file(after),
            "output_validation_sha256": sha256_file(validation_path),
            "result_manifest_sha256": accepted["manifest.sha256"],
            "archive": str(archive.resolve()),
            "archive_sha256": sha256_file(archive),
            "archive_members": members,
        }
        write_json_exclusive(receipt, payload)
        receipt_created = True
        if read_json(receipt) != payload:
            raise ValueError("Q-032 stage receipt readback failed")
        return payload
    except Exception:
        if receipt_created:
            receipt.unlink()
        if archive_created:
            archive.unlink()
        if validation_path.exists():
            validation_path.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    bind = subparsers.add_parser("bind-inputs")
    bind.add_argument("--base", type=Path, required=True)
    bind.add_argument("--output", type=Path, required=True)
    bind.add_argument("--compare", type=Path)
    package = subparsers.add_parser("validate-package")
    package.add_argument("--base", type=Path, required=True)
    package.add_argument("--result", type=Path, required=True)
    package.add_argument("--before", type=Path, required=True)
    package.add_argument("--after", type=Path, required=True)
    package.add_argument("--validation", type=Path, required=True)
    package.add_argument("--archive", type=Path, required=True)
    package.add_argument("--receipt", type=Path, required=True)
    package.add_argument("--stage-root", type=Path, required=True)
    package.add_argument("--stage-checksums", type=Path, required=True)
    package.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    if args.command == "bind-inputs":
        payload = bind_inputs(args.base, args.output, args.compare)
        print("Q032_INPUT_BINDING_COMPLETE", payload["view_count"], payload["file_count"], flush=True)
    else:
        payload = validate_and_package(
            base=args.base, result=args.result, before=args.before, after=args.after,
            validation_path=args.validation, archive=args.archive, receipt=args.receipt,
            stage_root=args.stage_root, stage_checksums=args.stage_checksums,
            source_commit=args.source_commit,
        )
        print(
            "Q032_RETAINED_METHOD_LADDER_COMPLETE",
            payload["archive_sha256"], len(payload["archive_members"]), flush=True,
        )


if __name__ == "__main__":
    main()
