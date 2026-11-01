#!/usr/bin/env python3
"""Fail-closed dependency gate for the Q-031 native HDF5 pilot.

This gate only inspects the migration and compact-flux provenance.  It never
opens native HDF5 payloads and never changes migration state.  The command is
intended to run immediately before a native extractor is started.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


KNOWN_PLAN_HASH = "698d01634ade85df5fac6d42716c5463af56118230b085021ba7b205739c8900"
EXPECTED_UNIT_COUNT = 10
EXPECTED_CASES = ["C-HI", "C-LO", "G-HI", "G-LO"]
EXPECTED_SNAPSHOT_COUNT = 51
PACKAGE_SCRIPT = Path(__file__).with_name("package_q031_flux_results.py")
NATIVE_CASES = ("C-HI", "G-HI")
NATIVE_TARGET_INDEX = 40
NATIVE_BASELINE_INDEX = 0
IDENTITY_FIELDS = ("device", "inode", "size_bytes", "mtime_ns", "ctime_ns")
COMPARE_IDENTITY_FIELDS = ("inode", "size_bytes", "mtime_ns", "ctime_ns")
DEVICE_COMPARISON = "recorded_not_compared_across_allocations"


class DependencyGateError(ValueError):
    """Raised when a dependency is absent, stale, or not receipt-bound."""


def canonical_json(value: Any) -> str:
    """Return the migration's exact canonical JSON representation."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a named small receipt/code file, never a migration payload."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise DependencyGateError(f"cannot hash dependency file {path}: {exc}") from exc
    return digest.hexdigest()


def _require_regular_file(path: Path, label: str) -> None:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise DependencyGateError(f"missing {label}: {path}") from exc
    if not stat.S_ISREG(observed.st_mode) or path.is_symlink():
        raise DependencyGateError(f"{label} is not a regular file: {path}")


def _require_directory(path: Path, label: str) -> None:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise DependencyGateError(f"missing {label}: {path}") from exc
    if not stat.S_ISDIR(observed.st_mode) or path.is_symlink():
        raise DependencyGateError(f"{label} is not a live directory: {path}")


def _read_object(path: Path, label: str) -> dict[str, Any]:
    _require_regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DependencyGateError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise DependencyGateError(f"{label} is not a JSON object: {path}")
    return value


def _unit_id(unit: dict[str, str]) -> str:
    """Match migrate_xray_scratch_to_home._unit_id exactly."""

    try:
        source, destination = unit["source"], unit["destination"]
    except KeyError as exc:
        raise DependencyGateError(f"migration unit lacks {exc.args[0]}") from exc
    return hashlib.sha256(f"{source}\0{destination}".encode()).hexdigest()[:20]


def _migration_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\0" in value:
        raise DependencyGateError(f"{label} must be a non-empty path string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise DependencyGateError(f"{label} must be absolute")
    return Path(os.path.normpath(str(path)))


def _normalize_migration_plan(raw: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the frozen migrator's schema-2 plan from its raw input."""

    if set(raw) != {"archive_root", "authority", "metadata_policy", "units"}:
        raise DependencyGateError("migration plan has an unexpected raw schema")
    if raw["metadata_policy"] != "private_archive":
        raise DependencyGateError("migration metadata_policy must be private_archive")
    if not isinstance(raw["authority"], str) or not raw["authority"].strip():
        raise DependencyGateError("migration authority must be a non-empty string")
    archive_root = _migration_path(raw["archive_root"], "archive_root")
    if not isinstance(raw["units"], list) or len(raw["units"]) != EXPECTED_UNIT_COUNT:
        raise DependencyGateError(f"migration plan must contain exactly {EXPECTED_UNIT_COUNT} units")
    units = []
    sources: list[Path] = []
    destinations: list[Path] = []
    for index, unit in enumerate(raw["units"]):
        if not isinstance(unit, dict) or set(unit) != {"source", "destination"}:
            raise DependencyGateError(f"migration unit {index} has an unexpected schema")
        source = _migration_path(unit["source"], f"unit {index} source")
        destination = _migration_path(unit["destination"], f"unit {index} destination")
        if destination == archive_root or archive_root not in destination.parents:
            raise DependencyGateError(f"migration destination {index} must be below archive_root")
        if source == destination or source in destination.parents or destination in source.parents:
            raise DependencyGateError(f"migration source and destination overlap in unit {index}")
        if any(source == other or source in other.parents or other in source.parents for other in sources):
            raise DependencyGateError(f"migration source units overlap at unit {index}")
        if any(destination == other or destination in other.parents or other in destination.parents for other in destinations):
            raise DependencyGateError(f"migration destination units overlap at unit {index}")
        sources.append(source)
        destinations.append(destination)
        units.append({"source": str(source), "destination": str(destination)})
    return {
        "schema": 2,
        "archive_root": str(archive_root),
        "authority": raw["authority"],
        "metadata_policy": "private_archive",
        "units": units,
    }


def _migration_small_file_hashes(root: Path, status_paths: list[Path]) -> dict[str, str]:
    paths = [
        root / "migration_plan.json",
        root / "state" / "plan-binding.json",
        root / "state" / "verified-manifest.json",
        root / "state" / "events.jsonl",
        *status_paths,
    ]
    return {str(path.relative_to(root)): sha256_file(path) for path in paths}


def validate_migration_dependencies(
    migration_root: Path,
    expected_plan_hash: str = KNOWN_PLAN_HASH,
) -> dict[str, Any]:
    """Validate migration 870323 state without hashing any payload tree.

    ``expected_plan_hash`` is injectable for synthetic unit tests.  The CLI
    retains the production constant above.
    """

    root = Path(migration_root)
    _require_directory(root, "migration root")
    plan_path = root / "migration_plan.json"
    plan = _normalize_migration_plan(_read_object(plan_path, "migration plan"))
    observed_hash = canonical_sha256(plan)
    if observed_hash != expected_plan_hash:
        raise DependencyGateError(
            f"migration plan hash mismatch: expected {expected_plan_hash}, observed {observed_hash}"
        )
    units = plan["units"]

    state = root / "state"
    _require_directory(state, "migration state directory")
    binding_path = state / "plan-binding.json"
    binding = _read_object(binding_path, "plan binding")
    expected_binding = {"schema": 2, "plan_hash": observed_hash, "plan": plan}
    if canonical_json(binding) != canonical_json(expected_binding):
        raise DependencyGateError("plan-binding.json does not match migration plan/hash")

    verified_path = state / "verified-manifest.json"
    verified = _read_object(verified_path, "verified manifest")
    verified_units = verified.get("units")
    if verified.get("plan_hash") != observed_hash or not isinstance(verified_units, list):
        raise DependencyGateError("verified manifest plan binding mismatch")
    if len(verified_units) != EXPECTED_UNIT_COUNT:
        raise DependencyGateError("verified manifest does not contain exactly ten units")

    expected_units: list[dict[str, str]] = []
    status_paths: list[Path] = []
    for index, raw_unit in enumerate(units):
        if set(raw_unit) != {"source", "destination"}:
            raise DependencyGateError(f"migration unit {index} has an unexpected schema")
        unit = {"source": raw_unit["source"], "destination": raw_unit["destination"]}
        if not all(isinstance(value, str) for value in unit.values()):
            raise DependencyGateError(f"migration unit {index} paths must be strings")
        unit_id = _unit_id(unit)
        expected = {
            "unit_id": unit_id,
            "source": unit["source"],
            "destination": unit["destination"],
            "stage": "complete",
        }
        expected_units.append(expected)
        if verified_units[index] != expected:
            raise DependencyGateError(f"verified manifest unit {index} is not plan-bound and complete")

        unit_dir = state / f"unit-{unit_id}"
        status_path = unit_dir / "status.json"
        status_paths.append(status_path)
        status = _read_object(status_path, f"status for unit {index}")
        status_expected = {
            "plan_hash": observed_hash,
            "unit_id": unit_id,
            "source": unit["source"],
            "destination": unit["destination"],
            "stage": "complete",
        }
        if any(status.get(key) != value for key, value in status_expected.items()):
            raise DependencyGateError(f"status for unit {index} is not plan-bound and complete")
        tombstone = Path(status.get("tombstone", ""))
        expected_tombstone = Path(unit["source"]).with_name(
            f".{Path(unit['source']).name}.xray-migration-{unit_id}.tombstone"
        )
        if tombstone != expected_tombstone:
            raise DependencyGateError(f"status tombstone identity mismatch for unit {index}")
        source = Path(unit["source"])
        destination = Path(unit["destination"])
        if not source.is_symlink() or os.readlink(source) != unit["destination"]:
            raise DependencyGateError(f"source symlink does not literally target destination for unit {index}")
        try:
            destination_stat = destination.lstat()
        except OSError as exc:
            raise DependencyGateError(f"destination is not live for unit {index}: {destination}") from exc
        if not stat.S_ISDIR(destination_stat.st_mode) or destination.is_symlink():
            raise DependencyGateError(f"destination is not a live directory for unit {index}: {destination}")
        if os.path.lexists(expected_tombstone):
            raise DependencyGateError(f"migration tombstone remains for unit {index}: {expected_tombstone}")

    events_path = state / "events.jsonl"
    _require_regular_file(events_path, "migration events")
    try:
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DependencyGateError(f"invalid migration events: {events_path}") from exc
    if not events or not isinstance(events[-1], dict):
        raise DependencyGateError("migration events have no final event")
    final = events[-1]
    if final.get("event") != "device-transition-execute-complete" or final.get("plan_hash") != observed_hash:
        raise DependencyGateError("migration final event is not device-transition-execute-complete for this plan")

    return {
        "plan_hash": observed_hash,
        "unit_count": EXPECTED_UNIT_COUNT,
        "units": expected_units,
        "input_small_file_hashes": _migration_small_file_hashes(root, status_paths),
    }


def _load_package_module() -> Any:
    spec = importlib.util.spec_from_file_location("q031_flux_package_for_gate", PACKAGE_SCRIPT)
    if spec is None or spec.loader is None:
        raise DependencyGateError(f"cannot import flux package validator: {PACKAGE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stat_identity(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    try:
        resolved = path.resolve(strict=True)
        observed = path.stat()
    except OSError as exc:
        raise DependencyGateError(f"native source is missing or cannot be stat-ed: {path}") from exc
    if not stat.S_ISREG(observed.st_mode):
        raise DependencyGateError(f"native source is not a regular file: {path}")
    return {
        "path": str(path),
        "resolved_path": str(resolved),
        "device": int(observed.st_dev),
        "inode": int(observed.st_ino),
        "size_bytes": int(observed.st_size),
        "mtime_ns": int(observed.st_mtime_ns),
        "ctime_ns": int(observed.st_ctime_ns),
    }


def _shape_from_manifest(row: dict[str, str], key: str) -> list[int]:
    value = row.get(key, "")
    try:
        shape = [int(part) for part in value.split("x")]
    except (AttributeError, ValueError) as exc:
        raise DependencyGateError(f"invalid native source shape in {key}: {value!r}") from exc
    if len(shape) != 3 or any(part <= 0 for part in shape):
        raise DependencyGateError(f"invalid native source shape in {key}: {value!r}")
    return shape


def _float_field(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise DependencyGateError(f"native source manifest lacks numeric {key}") from exc


def _metadata_for_index(provenance: dict[str, Any], index: int, case: str) -> dict[str, Any]:
    snapshots = provenance.get("snapshots")
    if not isinstance(snapshots, list):
        raise DependencyGateError(f"flux provenance snapshots missing for {case}")
    matches = [item for item in snapshots if isinstance(item, dict) and item.get("output_index") == index]
    if len(matches) != 1:
        raise DependencyGateError(f"flux provenance has {len(matches)} snapshots at index {index} for {case}")
    metadata = matches[0]
    required = {"path", "resolved_path", "timestep", "output_index", "time_code", "shape", "size_bytes", *IDENTITY_FIELDS}
    if not required.issubset(metadata):
        raise DependencyGateError(f"flux provenance snapshot metadata is incomplete for {case}/{index}")
    return metadata


def _validate_one_source_manifest(manifest_path: Path, results_dir: Path) -> dict[str, Any]:
    _require_regular_file(manifest_path, "native source manifest")
    try:
        with manifest_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error, UnicodeError) as exc:
        raise DependencyGateError(f"invalid native source manifest: {manifest_path}") from exc
    if not rows:
        raise DependencyGateError(f"native source manifest is empty: {manifest_path}")
    cases = {row.get("case") for row in rows}
    if len(cases) != 1 or next(iter(cases)) not in NATIVE_CASES:
        raise DependencyGateError(f"native source manifest has an unexpected case: {manifest_path}")
    case = next(iter(cases))
    selected = [row for row in rows if row.get("snapshot_index") == str(NATIVE_TARGET_INDEX)]
    if len(selected) != 1:
        raise DependencyGateError(f"native source manifest must select exactly snapshot 40: {manifest_path}")
    row = selected[0]
    required_row_fields = {"input_h5", "timestep", "actual_time_code", "shape_nz_ny_nx", "baseline_h5", "baseline_timestep"}
    if not required_row_fields.issubset(row):
        raise DependencyGateError(f"native source manifest lacks baseline/target binding fields: {manifest_path}")
    target_shape = _shape_from_manifest(row, "shape_nz_ny_nx")
    baseline_path = row["baseline_h5"]
    target_path = row["input_h5"]
    target_identity = _stat_identity(target_path)
    baseline_identity = _stat_identity(baseline_path)
    provenance = _read_object(results_dir / case / "provenance.json", f"{case} flux provenance")
    target_metadata = _metadata_for_index(provenance, NATIVE_TARGET_INDEX, case)
    baseline_metadata = _metadata_for_index(provenance, NATIVE_BASELINE_INDEX, case)
    if row["timestep"] != "Timestep_40" or row["baseline_timestep"] != "Timestep_0":
        raise DependencyGateError(f"native source manifest timestep binding mismatch for {case}")
    if target_identity["resolved_path"] != target_metadata["resolved_path"]:
        raise DependencyGateError(f"native target resolved path differs from flux identity for {case}")
    if baseline_identity["resolved_path"] != baseline_metadata["resolved_path"]:
        raise DependencyGateError(f"native baseline resolved path differs from flux identity for {case}")
    for label, identity, metadata in (
        ("target", target_identity, target_metadata), ("baseline", baseline_identity, baseline_metadata)
    ):
        for field in COMPARE_IDENTITY_FIELDS:
            if identity[field] != metadata[field]:
                raise DependencyGateError(f"native {label} stat identity differs from flux identity for {case}: {field}")
    if target_metadata["timestep"] != "Timestep_40" or baseline_metadata["timestep"] != "Timestep_0":
        raise DependencyGateError(f"flux provenance timestep binding mismatch for {case}")
    baseline_shape = (
        _shape_from_manifest(row, "baseline_grid_shape_nz_ny_nx")
        if row.get("baseline_grid_shape_nz_ny_nx") else baseline_metadata["shape"]
    )
    if target_metadata["shape"] != target_shape or baseline_metadata["shape"] != baseline_shape:
        raise DependencyGateError(f"native source shape differs from flux metadata for {case}")
    if target_metadata["time_code"] != _float_field(row, "actual_time_code"):
        raise DependencyGateError(f"native target time differs from flux metadata for {case}")
    if row.get("baseline_time_code") and baseline_metadata["time_code"] != _float_field(row, "baseline_time_code"):
        raise DependencyGateError(f"native baseline time differs from flux metadata for {case}")
    if row.get("file_size_bytes") and target_metadata["size_bytes"] != int(row["file_size_bytes"]):
        raise DependencyGateError(f"native target size differs from source manifest for {case}")
    if row.get("baseline_file_size_bytes") and baseline_metadata["size_bytes"] != int(row["baseline_file_size_bytes"]):
        raise DependencyGateError(f"native baseline size differs from source manifest for {case}")
    return {
        "manifest": str(manifest_path.resolve()),
        "sha256": sha256_file(manifest_path),
        "case": case,
        "selected_row": row,
        "target_identity": target_identity,
        "baseline_identity": baseline_identity,
        "target_flux_metadata": target_metadata,
        "baseline_flux_metadata": baseline_metadata,
        "device_comparison": DEVICE_COMPARISON,
    }


def validate_native_source_manifests(
    source_manifests: list[Path] | tuple[Path, ...], results_dir: Path,
) -> dict[str, Any]:
    if len(source_manifests) != len(NATIVE_CASES):
        raise DependencyGateError("exactly two native source manifests (C-HI and G-HI) are required")
    records = [_validate_one_source_manifest(Path(path), Path(results_dir)) for path in source_manifests]
    if {record["case"] for record in records} != set(NATIVE_CASES):
        raise DependencyGateError("native source manifests must cover exactly C-HI and G-HI")
    records.sort(key=lambda record: NATIVE_CASES.index(record["case"]))
    return {
        "source_manifests": records,
        "device_comparison": DEVICE_COMPARISON,
        "native_input_identities": {
            record["case"]: {
                "target": record["target_identity"],
                "baseline": record["baseline_identity"],
            }
            for record in records
        },
    }


def validate_flux_dependencies(
    flux_stage: Path, science_dir: Path, source_manifests: list[Path] | tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Reuse the established Q-031 production validator and archive gate."""

    package = _load_package_module()
    stage = Path(flux_stage)
    staged_science = stage / "scripts" / "science"
    results = stage / "results_production"
    archive = stage / "compact_production.tar.gz"
    receipt_path = stage / "compact_production.receipt.json"
    _require_directory(stage, "flux stage")
    _require_directory(staged_science, "staged flux science directory")
    _require_directory(Path(science_dir), "current science directory")

    validated, staged_hashes = package.validate_results(results, "production", staged_science)
    current_hashes = package.current_analysis_hashes(Path(science_dir))
    if staged_hashes != current_hashes:
        raise DependencyGateError("flux analysis hashes differ from current staged science")
    expected = package.archive_expected_files(results, validated)
    package.verify_archive(archive, expected)
    archive_hash = package.sha256_file(archive)
    receipt = package.read_json(receipt_path)
    expected_members = [
        {"path": member, "sha256": metadata["sha256"], "size_bytes": metadata["size_bytes"]}
        for member, metadata in expected.items()
    ]
    if (receipt.get("schema_version") != 1 or receipt.get("status") != "verified" or
            receipt.get("mode") != "production" or receipt.get("recovered_existing_smoke") is not False):
        raise DependencyGateError("compact production receipt is not verified production")
    if receipt.get("cases") != EXPECTED_CASES or receipt.get("snapshot_count_per_case") != EXPECTED_SNAPSHOT_COUNT:
        raise DependencyGateError("compact production receipt case/snapshot binding mismatch")
    if receipt.get("source_results_dir") != str(results.resolve()) or receipt.get("archive") != str(archive.resolve()):
        raise DependencyGateError("compact production receipt source/archive path binding mismatch")
    if receipt.get("analysis_implementation_hashes") != staged_hashes:
        raise DependencyGateError("compact production receipt analysis hash binding mismatch")
    if receipt.get("members") != expected_members:
        raise DependencyGateError("compact production receipt members/hash binding mismatch")
    if receipt.get("archive_sha256") != archive_hash:
        raise DependencyGateError("compact production receipt archive hash mismatch")
    native_sources = validate_native_source_manifests(source_manifests or [], results)

    input_hashes = {
        str(path.relative_to(stage)): metadata["sha256"]
        for path, metadata in validated.items()
    }
    input_hashes.update({f"scripts/science/{name}": digest for name, digest in staged_hashes.items()})
    input_hashes["compact_production.tar.gz"] = archive_hash
    input_hashes["compact_production.receipt.json"] = package.sha256_file(receipt_path)
    input_hashes.update({
        f"source_manifests/{record['case']}.csv": record["sha256"]
        for record in native_sources["source_manifests"]
    })
    return {
        "results_dir": str(results.resolve()),
        "archive": str(archive.resolve()),
        "archive_sha256": archive_hash,
        "cases": EXPECTED_CASES,
        "snapshot_count_per_case": EXPECTED_SNAPSHOT_COUNT,
        "analysis_implementation_hashes": current_hashes,
        "input_small_file_hashes": input_hashes,
        "source_manifests": native_sources["source_manifests"],
        "native_input_identities": native_sources["native_input_identities"],
        "device_comparison": native_sources["device_comparison"],
    }


def validate_dependencies(
    *,
    migration_root: Path,
    flux_stage: Path,
    science_dir: Path,
    source_manifests: list[Path] | tuple[Path, ...] | None = None,
    expected_plan_hash: str = KNOWN_PLAN_HASH,
) -> dict[str, Any]:
    migration = validate_migration_dependencies(migration_root, expected_plan_hash=expected_plan_hash)
    flux = validate_flux_dependencies(flux_stage, science_dir, source_manifests)
    return {
        "schema_version": 1,
        "status": "verified",
        "scope": "q031-native-ch-i-g-hi40-pilot",
        "authorisation": {"migration": "870323", "flux": "870374", "cases": ["C-HI", "G-HI"], "age_myr": 40},
        "migration": migration,
        "flux": flux,
        "checks": [
            "canonical migration plan hash",
            "plan binding",
            "ten ordered complete migration units",
            "unit status and literal source links",
            "live destinations and absent tombstones",
            "device-transition migration completion event",
            "Q-031 production flux result validation",
            "current analysis implementation hash binding",
            "compact production receipt and archive member/hash binding",
            "C-HI/G-HI snapshot-40 and baseline-0 source identity binding",
            "native device identities recorded without cross-allocation comparison",
        ],
        "native_payload_rehashed": False,
    }


def write_receipt(payload: dict[str, Any], output: Path) -> None:
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(f"refusing to overwrite dependency-gate receipt: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError:
        raise FileExistsError(f"refusing to overwrite dependency-gate receipt: {output}") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migration-root", type=Path, required=True)
    parser.add_argument("--flux-stage", type=Path, required=True)
    parser.add_argument("--science-dir", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        payload = validate_dependencies(
            migration_root=args.migration_root,
            flux_stage=args.flux_stage,
            science_dir=args.science_dir,
            source_manifests=args.source_manifest,
        )
        write_receipt(payload, args.output)
    except (DependencyGateError, FileExistsError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("Q031_NATIVE_DEPENDENCY_GATE_VERIFIED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
