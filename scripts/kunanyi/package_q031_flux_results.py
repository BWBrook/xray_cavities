#!/usr/bin/env python3
"""Validate and package immutable Q-031 science outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import stat
import tarfile
from pathlib import Path
from typing import Any


OUTPUT_NAMES = (
    "instantaneous_surface_fluxes.csv",
    "region_storage.csv",
    "integrated_control_balances.csv",
    "provenance.json",
)
DATA_NAMES = OUTPUT_NAMES[:3]
ANALYSIS_NAMES = (
    "measure_q031_fluxes.py",
    "snapshot_energy.py",
    "pluto_h5_level3_ambient_extract.py",
    "select_common_age_hdf5.py",
)
EXPECTED_CASES = {
    "smoke": ("G-LO",),
    "production": ("C-HI", "C-LO", "G-HI", "G-LO"),
}
EXPECTED_SNAPSHOTS = {"smoke": 2, "production": 51}
COMPLETION_PAYLOAD = "retained-output diagnostic; scientific interpretation pending"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_regular_file(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise ValueError(f"missing package input: {path}") from exc
    if not stat.S_ISREG(mode):
        raise ValueError(f"package input is not a regular file: {path}")


def read_json(path: Path) -> dict[str, Any]:
    require_regular_file(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def current_analysis_hashes(science_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in ANALYSIS_NAMES:
        path = science_dir / name
        require_regular_file(path)
        hashes[name] = sha256_file(path)
    return hashes


def validate_case(
    case_dir: Path,
    *,
    case: str,
    expected_snapshots: int,
    analysis_hashes: dict[str, str],
) -> dict[Path, dict[str, Any]]:
    manifest = case_dir / "manifest.sha256.csv"
    require_regular_file(manifest)
    with manifest.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or list(rows[0]) != ["sha256", "filename"]:
        raise ValueError(f"invalid case manifest schema: {manifest}")
    if tuple(row["filename"] for row in rows) != OUTPUT_NAMES:
        raise ValueError(f"case manifest does not contain the exact science outputs: {manifest}")
    if len({row["filename"] for row in rows}) != len(OUTPUT_NAMES):
        raise ValueError(f"duplicate case manifest filename: {manifest}")
    expected_output_hashes: dict[str, str] = {}
    for row in rows:
        expected = row["sha256"]
        if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise ValueError(f"invalid SHA-256 in {manifest}: {expected}")
        output = case_dir / row["filename"]
        require_regular_file(output)
        observed = sha256_file(output)
        if observed != expected:
            raise ValueError(f"manifest hash mismatch for {output}: expected {expected}, observed {observed}")
        expected_output_hashes[row["filename"]] = expected
    provenance = read_json(case_dir / "provenance.json")
    if provenance.get("case") != case:
        raise ValueError(f"provenance case mismatch in {case_dir}")
    snapshots = provenance.get("snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != expected_snapshots:
        raise ValueError(f"expected {expected_snapshots} snapshots in {case_dir}, found {type(snapshots).__name__}")
    indices = [snapshot.get("output_index") for snapshot in snapshots if isinstance(snapshot, dict)]
    if indices != list(range(expected_snapshots)):
        raise ValueError(f"non-canonical snapshot indices in {case_dir}: {indices}")
    if provenance.get("analysis_implementation_hashes") != analysis_hashes:
        raise ValueError(f"analysis implementation hashes differ from current staged science in {case_dir}")
    if provenance.get("outputs") != {name: expected_output_hashes[name] for name in DATA_NAMES}:
        raise ValueError(f"provenance output hashes disagree with the manifest in {case_dir}")
    validated = {
        case_dir / name: {
            "sha256": expected_output_hashes[name],
            "size_bytes": (case_dir / name).stat().st_size,
        }
        for name in OUTPUT_NAMES
    }
    validated[manifest] = {
        "sha256": sha256_file(manifest),
        "size_bytes": manifest.stat().st_size,
    }
    return validated


def validate_results(
    results_dir: Path, mode: str, science_dir: Path,
) -> tuple[dict[Path, dict[str, Any]], dict[str, str]]:
    if results_dir.name != f"results_{mode}":
        raise ValueError(f"results directory name does not match mode {mode}: {results_dir}")
    cases = EXPECTED_CASES[mode]
    completion = read_json(results_dir / "completion.json")
    expected_completion = {
        "cases": list(cases),
        "status": "complete",
        "payload": COMPLETION_PAYLOAD,
    }
    if completion != expected_completion:
        raise ValueError(f"invalid completion receipt in {results_dir}: {completion}")
    analysis_hashes = current_analysis_hashes(science_dir)
    completion_path = results_dir / "completion.json"
    validated = {
        completion_path: {
            "sha256": sha256_file(completion_path),
            "size_bytes": completion_path.stat().st_size,
        }
    }
    for case in cases:
        case_dir = results_dir / case
        if not case_dir.is_dir() or case_dir.is_symlink():
            raise ValueError(f"missing regular case directory: {case_dir}")
        validated.update(validate_case(
            case_dir,
            case=case,
            expected_snapshots=EXPECTED_SNAPSHOTS[mode],
            analysis_hashes=analysis_hashes,
        ))
    actual_case_dirs = sorted(path.name for path in results_dir.iterdir() if path.is_dir() and path.name in EXPECTED_CASES["production"])
    if actual_case_dirs != sorted(cases):
        raise ValueError(f"unexpected case directories in {results_dir}: {actual_case_dirs}")
    return validated, analysis_hashes


def archive_expected_files(
    results_dir: Path, validated: dict[Path, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected: dict[str, dict[str, Any]] = {}
    for path, accepted in validated.items():
        require_regular_file(path)
        member = str(Path(results_dir.name) / path.relative_to(results_dir))
        expected[member] = {
            "sha256": accepted["sha256"],
            "size_bytes": accepted["size_bytes"],
            "source": path,
        }
    return dict(sorted(expected.items()))


def create_archive(archive: Path, expected: dict[str, dict[str, Any]]) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with tarfile.open(archive, "x:gz", format=tarfile.PAX_FORMAT) as handle:
            created = True
            for member, metadata in expected.items():
                source = metadata["source"]
                info = handle.gettarinfo(str(source), arcname=member)
                if not info.isfile():
                    raise ValueError(f"refusing non-file archive member: {source}")
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mode = 0o600
                info.mtime = 0
                with source.open("rb") as payload:
                    handle.addfile(info, payload)
    except Exception:
        if created:
            archive.unlink()
        raise


def verify_archive(archive: Path, expected: dict[str, dict[str, Any]]) -> None:
    require_regular_file(archive)
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        names = [member.name for member in members]
        if names != list(expected):
            raise ValueError(f"archive members differ from immutable package list: {names}")
        for member in members:
            if not member.isfile():
                raise ValueError(f"archive contains non-file member: {member.name}")
            payload = handle.extractfile(member)
            if payload is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            digest = hashlib.sha256()
            size = 0
            for block in iter(lambda: payload.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
            metadata = expected[member.name]
            if digest.hexdigest() != metadata["sha256"] or size != metadata["size_bytes"]:
                raise ValueError(f"archive payload verification failed: {member.name}")


def package_results(
    *,
    results_dir: Path,
    mode: str,
    science_dir: Path,
    archive: Path,
    receipt: Path,
    recovered_existing_smoke: bool = False,
) -> dict[str, Any]:
    if mode not in EXPECTED_CASES:
        raise ValueError(f"unsupported mode: {mode}")
    if recovered_existing_smoke and mode != "smoke":
        raise ValueError("existing-result recovery is restricted to smoke mode")
    if os.path.lexists(archive) or os.path.lexists(receipt):
        raise FileExistsError(f"refusing to overwrite package output: {archive} or {receipt}")
    validated, analysis_hashes = validate_results(results_dir, mode, science_dir)
    expected = archive_expected_files(results_dir, validated)
    archive_created = False
    receipt_created = False
    try:
        create_archive(archive, expected)
        archive_created = True
        verify_archive(archive, expected)
        payload = {
            "schema_version": 1,
            "status": "verified",
            "mode": mode,
            "recovered_existing_smoke": recovered_existing_smoke,
            "source_results_dir": str(results_dir.resolve()),
            "archive": str(archive.resolve()),
            "archive_sha256": sha256_file(archive),
            "cases": list(EXPECTED_CASES[mode]),
            "snapshot_count_per_case": EXPECTED_SNAPSHOTS[mode],
            "analysis_implementation_hashes": analysis_hashes,
            "members": [
                {
                    "path": member,
                    "sha256": metadata["sha256"],
                    "size_bytes": metadata["size_bytes"],
                }
                for member, metadata in expected.items()
            ],
        }
        receipt.parent.mkdir(parents=True, exist_ok=True)
        with receipt.open("x") as handle:
            receipt_created = True
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        if read_json(receipt) != payload:
            raise ValueError(f"package receipt readback failed: {receipt}")
        return payload
    except Exception:
        if receipt_created:
            receipt.unlink()
        if archive_created:
            archive.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--results-dir", type=Path)
    source.add_argument("--validate-existing-smoke", type=Path, metavar="RESULTS_DIR")
    parser.add_argument("--mode", choices=tuple(EXPECTED_CASES))
    parser.add_argument("--science-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.validate_existing_smoke is not None:
        if args.mode not in (None, "smoke"):
            parser.error("--validate-existing-smoke only supports smoke mode")
        results_dir = args.validate_existing_smoke
        mode = "smoke"
        recovered = True
    else:
        if args.mode is None:
            parser.error("--mode is required with --results-dir")
        results_dir = args.results_dir
        mode = args.mode
        recovered = False
    payload = package_results(
        results_dir=results_dir,
        mode=mode,
        science_dir=args.science_dir,
        archive=args.archive,
        receipt=args.receipt,
        recovered_existing_smoke=recovered,
    )
    print(
        "Q031_FLUX_PACKAGE_VERIFIED",
        payload["mode"], payload["archive_sha256"], len(payload["members"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
