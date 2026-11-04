#!/usr/bin/env python3
"""Validate and bind the inherited-source lineage of the G-HI continuation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
from typing import Any, Mapping, Sequence

from select_common_age_hdf5 import CODE_TIME_PER_MYR, Snapshot, inspect_outputs


EXPECTED_CONFIG_HASHES = {
    "case_manifest.json": "ca519eda5e29c38af1c82276ff8e486e4dd8d25b30bfa6f872ee26cf55bd878c",
    "definitions_overrides.json": "a65fbd272dd4d4f49d02efc7b54b8cf26f2356e6dd5bcfcaf402cf00cc48660c",
    "environment.ini": "b222f3a4ec1b4a78fa3b99d4db0c66c44b63146b00424e9ff451bdf3c141fce5",
    "pluto.ini": "71fc6f195966fc8e954ee2446d583e34676b140aace13e9ebd52747630f6c96d",
    "tabulated_cosmo_002031.csv": "1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a",
}
EXPECTED_EXECUTABLE_SHA256 = "46755d88e8f70d311a82cd4da7769daef392807b1b3a5bcb1663d40a30a87727"
EXPECTED_BUILD_CONFIG_SHA256 = "790bc7726fa63d2fd51ce5f5700527e66822f730222aaa93a3376ac561633ea3"
EXPECTED_SOURCE_COUNT = 50
EXPECTED_SOURCE_MANIFEST_SHA256 = "3fd16323c1fc484327eddacdd8667fc2d1ebaa36330ce45c010dd412272e6e73"
EXPECTED_GRID_HASHES = {
    "parent": "f3aee2aebdc98d4036e061f24b8823b7bf5e5620b99f0e855f205069ae55623b",
    "continuation": "77d10309df9fbe4366cd540bc966a6f06736109141a2e7931f28eebfdb88196d",
}
EXPECTED_EVIDENCE_HASHES = {
    "parent_run_log": "444f10ac356b71960b768459616aee49b34ce0a08a615954fd9f9c23e76a32fc",
    "parent_source_revisions": "f32530704d99305e01b31c32369d0ede9be64952297337f53688b631bfebc728",
    "continuation_run_log": "40759e7b45edf4d2be0992db68eb2387117306951d5652c8712e1eb7fb2a8546",
    "staging_manifest": "8394f7baf3516b25b95983bc1c43853c50a2310a53f921c05cf124fea9cadd86",
    "restart_report": "f2ca7b23d1f311bd5037a2c6ded89ae3bcb02c0eded940f246862862a1b99f82",
    "canonical_sequence_report": "344acb1cce5d287885793a7ca7006ad546fd39aada574072cd4479b21f19c389",
    "endpoint_report": "7c4473ada24bac495077e53896eff595ce8028681555bd6183333374f8942a9a",
    "source_revisions": "e6af312a19300cdbe55c6d0b826aa665cbed70c201a931605a12c51e3864e314",
    "done_marker": "93eb49ae178325ba0688667a8eac705d2af75d1b0ce1236456b31716eae18fb0",
}
REQUIRED_SOURCE_FILES = (
    "definitions.h",
    "definitions_usr.h",
    "init.c",
    "jet.c",
    "pluto_usr.h",
)
RUN_ENVIRONMENT_LINES = (
    "KUNANYI_MODULE_STACK=agn_intel_impi",
    "MPI_FLAVOR=intelmpi",
    "MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5",
    "HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi",
    "HDF5_USE_FILE_LOCKING=FALSE",
)
ANALYSIS_OUTPUT_NAMES = (
    "instantaneous_surface_fluxes.csv",
    "region_storage.csv",
    "integrated_control_balances.csv",
    "provenance.json",
)


class LineageError(ValueError):
    """Raised when the accepted parent/continuation lineage is not proved."""


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _require_regular(path: Path, label: str) -> None:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise LineageError(f"missing {label}: {path}") from exc
    if not stat.S_ISREG(observed.st_mode) or path.is_symlink():
        raise LineageError(f"{label} must be a regular file: {path}")


def _require_directory(path: Path, label: str) -> None:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise LineageError(f"missing {label}: {path}") from exc
    if not stat.S_ISDIR(observed.st_mode) or path.is_symlink():
        raise LineageError(f"{label} must be a live directory: {path}")


def sha256_file(path: Path, *, require_regular: bool = True) -> str:
    return sha256_file_with_identity(path, require_regular=require_regular)[0]


def sha256_file_with_identity(
    path: Path, *, require_regular: bool = True
) -> tuple[str, dict[str, Any]]:
    if require_regular:
        _require_regular(path, "hash input")
    before = path.stat()
    resolved_before = str(path.resolve(strict=True))
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if _identity(before) != _identity(opened):
                raise LineageError(f"file changed before hashing: {path}")
            input_identity = {
                "path": str(path),
                "resolved_path": resolved_before,
                "device": opened.st_dev,
                "inode": opened.st_ino,
                "size_bytes": opened.st_size,
                "mtime_ns": opened.st_mtime_ns,
                "ctime_ns": opened.st_ctime_ns,
            }
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(block)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise LineageError(f"cannot hash {path}: {exc}") from exc
    resolved_after = str(path.resolve(strict=True))
    if (
        _identity(opened) != _identity(after)
        or _identity(after) != _identity(path.stat())
        or resolved_after != resolved_before
    ):
        raise LineageError(f"file changed during hashing: {path}")
    return digest.hexdigest(), input_identity


def _read_object(path: Path, label: str) -> dict[str, Any]:
    _require_regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LineageError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise LineageError(f"{label} must be a JSON object: {path}")
    return value


def _same_file(first: Path, second: Path, label: str) -> None:
    try:
        same = os.path.samefile(first, second)
    except OSError as exc:
        raise LineageError(f"cannot resolve {label}: {first} and {second}") from exc
    if not same:
        raise LineageError(f"{label} do not identify the same payload: {first} and {second}")


def _grid_geometry_bytes(path: Path) -> bytes:
    _require_regular(path, "grid geometry")
    lines = path.read_bytes().splitlines(keepends=True)
    return b"".join(line for line in lines if not line.startswith(b"# Generated on"))


def _source_hashes(source_dir: Path) -> dict[str, str]:
    _require_directory(source_dir, "accepted parent source directory")
    for name in REQUIRED_SOURCE_FILES:
        _require_regular(source_dir / name, f"required parent source {name}")
    paths = [
        path for path in sorted(source_dir.rglob("*"))
        if path.is_file() and not path.is_symlink() and path.suffix in {".c", ".h"}
    ]
    if not paths:
        raise LineageError(f"no C/header source evidence in {source_dir}")
    return {str(path.relative_to(source_dir)): sha256_file(path) for path in paths}


def _mapping_sha256(value: Mapping[str, str]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot_metadata(snapshot: Snapshot) -> dict[str, Any]:
    observed = snapshot.input_h5.stat()
    return {
        "path": str(snapshot.input_h5),
        "resolved_path": str(snapshot.input_h5.resolve()),
        "timestep": snapshot.timestep,
        "output_index": snapshot.output_index,
        "time_code": snapshot.time_code,
        "time_myr": snapshot.actual_time_myr,
        "shape": list(snapshot.shape),
        "size_bytes": observed.st_size,
        "device": observed.st_dev,
        "inode": observed.st_ino,
        "mtime_ns": observed.st_mtime_ns,
        "ctime_ns": observed.st_ctime_ns,
    }


def _one_snapshot_per_index(outputs: Path, label: str) -> dict[int, Snapshot]:
    snapshots = inspect_outputs(outputs)
    by_index: dict[int, Snapshot] = {}
    for snapshot in snapshots:
        if snapshot.output_index in by_index:
            raise LineageError(f"ambiguous {label} snapshot index {snapshot.output_index}")
        by_index[snapshot.output_index] = snapshot
    return by_index


def _validate_snapshot_chain(
    parent_outputs: Path,
    continuation_outputs: Path,
    *,
    expected_last_index: int,
    time_tolerance_myr: float,
) -> dict[str, Any]:
    parent = _one_snapshot_per_index(parent_outputs, "parent")
    continuation = _one_snapshot_per_index(continuation_outputs, "continuation")
    required_parent = set(range(0, 11))
    required_continuation = set(range(10, expected_last_index + 1))
    if not required_parent.issubset(parent):
        raise LineageError(f"parent snapshot chain is incomplete: {sorted(required_parent - set(parent))}")
    if set(continuation) != required_continuation:
        raise LineageError(
            "continuation snapshot chain must be exactly restart index 10 through endpoint: "
            f"missing={sorted(required_continuation - set(continuation))}, "
            f"unexpected={sorted(set(continuation) - required_continuation)}"
        )
    _same_file(parent[10].input_h5, continuation[10].input_h5, "10 Myr float restart anchors")
    if parent[10].shape != continuation[10].shape or not math.isclose(
        parent[10].time_code, continuation[10].time_code, rel_tol=0.0, abs_tol=1.0e-6
    ):
        raise LineageError("10 Myr float restart anchors disagree in time or shape")
    accepted = [parent[index] for index in range(0, 11)] + [
        continuation[index] for index in range(11, expected_last_index + 1)
    ]
    analysis = [parent[index] for index in range(0, 10)] + [
        continuation[index] for index in range(10, expected_last_index + 1)
    ]
    shapes = {snapshot.shape for snapshot in accepted}
    if len(shapes) != 1:
        raise LineageError(f"canonical chain contains multiple shapes: {sorted(shapes)}")
    for index, snapshot in enumerate(accepted):
        if abs(snapshot.actual_time_myr - index) >= time_tolerance_myr:
            raise LineageError(
                f"snapshot {index} age differs from cadence: {snapshot.actual_time_myr:.12g} Myr"
            )
    return {
        "accepted_chain_rule": "parent indices 0..10; continuation indices 11..endpoint",
        "analysis_chain_rule": (
            "parent indices 0..9; continuation index 10 symlink to the identical parent payload, "
            "then continuation indices 11..endpoint (later-segment selection used by measure_q031_fluxes)"
        ),
        "accepted_chain": [_snapshot_metadata(snapshot) for snapshot in accepted],
        "analysis_chain": [_snapshot_metadata(snapshot) for snapshot in analysis],
        "excluded_parent_overlap_indices": sorted(index for index in parent if index > 10),
        "native_payload_rehashed": False,
    }


def _validate_restart(
    parent_problem: Path,
    continuation_problem: Path,
    restart_report_path: Path,
    *,
    rehash_restart_hdf5: bool,
) -> dict[str, Any]:
    report = _read_object(restart_report_path, "restart report")
    if report.get("status") != "ok" or report.get("restart_record_count") != 3:
        raise LineageError("restart report is not the accepted three-record ok report")
    fluid = report.get("fluid_restart")
    particle = report.get("particle_restart")
    if not isinstance(fluid, dict) or not isinstance(particle, dict):
        raise LineageError("restart report lacks fluid/particle records")
    if fluid.get("index") != 2 or fluid.get("nstep") != 10011:
        raise LineageError("fluid restart is not index 2 at step 10011")
    if particle.get("index") != 1000 or particle.get("stepNumber") != 10011:
        raise LineageError("particle restart is not index 1000 at step 10011")
    if abs(float(fluid.get("time", math.inf)) - float(particle.get("time", -math.inf))) > 0.005:
        raise LineageError("fluid and particle restart times disagree")
    parent_outputs = parent_problem / "outputs"
    continuation_outputs = continuation_problem / "outputs"
    restart_sources = {
        "fluid_catalogue": parent_outputs / "dbl.h5.out",
        "fluid_hdf5": parent_outputs / "data.0002.dbl.h5",
        "particle_restart": parent_outputs / "particles.1000.dbl",
        "restart_out": parent_outputs / "restart.out",
    }
    for name in ("fluid_hdf5", "particle_restart"):
        path = continuation_outputs / restart_sources[name].name
        if not path.is_symlink():
            raise LineageError(f"continuation {name} must remain an inherited symlink: {path}")
        _same_file(path, restart_sources[name], f"{name} restart files")
    expected_hashes = report.get("input_sha256")
    if not isinstance(expected_hashes, dict):
        raise LineageError("restart report lacks input SHA-256 values")
    observed_hashes: dict[str, str] = {}
    input_identity: dict[str, dict[str, Any]] = {}
    for name, path in restart_sources.items():
        expected = expected_hashes.get(name)
        if not isinstance(expected, str) or len(expected) != 64:
            raise LineageError(f"restart report lacks a valid hash for {name}")
        if name == "fluid_hdf5" and not rehash_restart_hdf5:
            observed_hashes[name] = expected
            observed = path.stat()
            input_identity[name] = {
                "path": str(path),
                "resolved_path": str(path.resolve(strict=True)),
                "device": observed.st_dev,
                "inode": observed.st_ino,
                "size_bytes": observed.st_size,
                "mtime_ns": observed.st_mtime_ns,
                "ctime_ns": observed.st_ctime_ns,
            }
            continue
        observed, identity = sha256_file_with_identity(path, require_regular=False)
        if observed != expected:
            raise LineageError(f"restart hash mismatch for {name}: expected {expected}, observed {observed}")
        observed_hashes[name] = observed
        input_identity[name] = identity
    return {
        "report": report,
        "accepted_parent_restart_paths": {name: str(path) for name, path in restart_sources.items()},
        "continuation_inherited_links": {
            name: str(continuation_outputs / restart_sources[name].name)
            for name in ("fluid_hdf5", "particle_restart")
        },
        "verified_sha256": observed_hashes,
        "input_identity": input_identity,
        "fluid_hdf5_rehashed": rehash_restart_hdf5,
    }


def _require_lines(path: Path, required: Sequence[str], label: str) -> None:
    _require_regular(path, label)
    lines = set(path.read_text(encoding="utf-8", errors="strict").splitlines())
    missing = [line for line in required if line not in lines]
    if missing:
        raise LineageError(f"{label} lacks required records: {missing}")


def _validate_evidence(
    paths: Mapping[str, Path], expected_hashes: Mapping[str, str]
) -> dict[str, dict[str, str]]:
    if set(paths) != set(expected_hashes):
        raise LineageError("historical evidence path/hash labels differ")
    result: dict[str, dict[str, str]] = {}
    for label, path in paths.items():
        observed = sha256_file(path)
        expected = expected_hashes[label]
        if observed != expected:
            raise LineageError(f"historical {label} hash mismatch: expected {expected}, observed {observed}")
        result[label] = {"path": str(path), "sha256": observed}
    _require_lines(
        paths["parent_run_log"],
        (*RUN_ENVIRONMENT_LINES, "--- setup problem ---", "--- build ---", "RUN_KIND=fresh", "MPI_EXIT_CODE=124"),
        "parent run log",
    )
    _require_lines(
        paths["continuation_run_log"],
        (*RUN_ENVIRONMENT_LINES, "RUN_KIND=h5_restart_2", "MPI_EXIT_CODE=0"),
        "continuation run log",
    )
    continuation_text = paths["continuation_run_log"].read_text(encoding="utf-8")
    if "restart_pair_validation=passed" not in continuation_text or "reusing existing built problem" not in continuation_text:
        raise LineageError("continuation log does not prove validated restart and binary reuse")
    staging_text = paths["staging_manifest"].read_text(encoding="utf-8")
    if "/src" in staging_text or "/problem/pluto\t" not in staging_text:
        raise LineageError("staging manifest must show reused binary without a duplicate source tree")
    return result


def validate_lineage(
    *,
    parent_problem: Path,
    continuation_problem: Path,
    evidence_paths: Mapping[str, Path],
    receipt: Path,
    config_hashes: Mapping[str, str] = EXPECTED_CONFIG_HASHES,
    evidence_hashes: Mapping[str, str] = EXPECTED_EVIDENCE_HASHES,
    expected_executable_sha256: str = EXPECTED_EXECUTABLE_SHA256,
    expected_build_config_sha256: str = EXPECTED_BUILD_CONFIG_SHA256,
    expected_source_count: int = EXPECTED_SOURCE_COUNT,
    expected_source_manifest_sha256: str = EXPECTED_SOURCE_MANIFEST_SHA256,
    expected_grid_hashes: Mapping[str, str] = EXPECTED_GRID_HASHES,
    expected_last_index: int = 50,
    time_tolerance_myr: float = 0.05,
    rehash_restart_hdf5: bool = True,
) -> dict[str, Any]:
    parent_problem = Path(parent_problem)
    continuation_problem = Path(continuation_problem)
    _require_directory(parent_problem, "accepted parent problem")
    _require_directory(continuation_problem, "continuation problem")
    if (continuation_problem / "src").exists() or (continuation_problem / "src").is_symlink():
        raise LineageError("continuation must inherit source explicitly, not select a duplicate src tree")
    source_dir = parent_problem / "src"
    source_hashes = _source_hashes(source_dir)
    source_manifest_sha256 = _mapping_sha256(source_hashes)
    if len(source_hashes) != expected_source_count or source_manifest_sha256 != expected_source_manifest_sha256:
        raise LineageError(
            "parent C/header source manifest differs from the reviewed live capture: "
            f"count={len(source_hashes)}, sha256={source_manifest_sha256}"
        )
    parent_source_binary = source_dir / "pluto"
    parent_binary = parent_problem / "pluto"
    continuation_binary = continuation_problem / "pluto"
    for path, label in (
        (parent_source_binary, "parent build product"),
        (parent_binary, "parent executable"),
        (continuation_binary, "continuation executable"),
    ):
        _require_regular(path, label)
        if not os.access(path, os.X_OK):
            raise LineageError(f"{label} is not executable: {path}")
    binary_hashes = {str(path): sha256_file(path) for path in (parent_source_binary, parent_binary, continuation_binary)}
    if len(set(binary_hashes.values())) != 1 or next(iter(binary_hashes.values())) != expected_executable_sha256:
        raise LineageError("parent build product, parent executable and continuation executable differ")
    source_ini = source_dir / "pluto.ini"
    _require_regular(source_ini, "parent build configuration")

    inputs: dict[str, dict[str, str]] = {}
    for name, expected in config_hashes.items():
        parent_path = parent_problem / name
        continuation_path = continuation_problem / name
        parent_hash = sha256_file(parent_path)
        continuation_hash = sha256_file(continuation_path)
        if parent_hash != expected or continuation_hash != expected:
            raise LineageError(
                f"{name} differs from the accepted rendered input: expected {expected}, "
                f"parent {parent_hash}, continuation {continuation_hash}"
            )
        inputs[name] = {
            "parent_path": str(parent_path),
            "continuation_path": str(continuation_path),
            "sha256": expected,
        }
    observed_build_config = sha256_file(source_ini)
    if observed_build_config != expected_build_config_sha256:
        raise LineageError("parent source build configuration differs from the reviewed build capture")
    parent_grid = parent_problem / "outputs/grid.out"
    continuation_grid = continuation_problem / "outputs/grid.out"
    grid_hashes = {"parent": sha256_file(parent_grid), "continuation": sha256_file(continuation_grid)}
    if grid_hashes != dict(expected_grid_hashes):
        raise LineageError(f"parent/continuation grid files differ from reviewed hashes: {grid_hashes}")
    if _grid_geometry_bytes(parent_grid) != _grid_geometry_bytes(continuation_grid):
        raise LineageError("parent and continuation grid geometry differ beyond generation metadata")

    evidence = _validate_evidence(evidence_paths, evidence_hashes)
    restart = _validate_restart(
        parent_problem,
        continuation_problem,
        evidence_paths["restart_report"],
        rehash_restart_hdf5=rehash_restart_hdf5,
    )
    snapshots = _validate_snapshot_chain(
        parent_problem / "outputs",
        continuation_problem / "outputs",
        expected_last_index=expected_last_index,
        time_tolerance_myr=time_tolerance_myr,
    )
    endpoint = _read_object(evidence_paths["endpoint_report"], "endpoint report")
    if endpoint.get("status") != "passed":
        raise LineageError("endpoint report did not pass")
    endpoint_hdf5 = endpoint.get("endpoint_hdf5")
    if not isinstance(endpoint_hdf5, dict) or not math.isclose(
        float(endpoint_hdf5.get("time_code", math.inf)), expected_last_index * CODE_TIME_PER_MYR,
        rel_tol=0.0, abs_tol=1.0e-3,
    ):
        raise LineageError("endpoint report does not identify the configured endpoint")

    payload = {
        "schema_version": 1,
        "status": "passed",
        "lineage": "accepted failed-run parent build/source plus validated 10 Myr home continuation",
        "parent_problem": str(parent_problem),
        "continuation_problem": str(continuation_problem),
        "problem_source_dir": str(source_dir),
        "source_hashes": source_hashes,
        "source_manifest_sha256": source_manifest_sha256,
        "source_file_count": len(source_hashes),
        "binary_sha256": next(iter(binary_hashes.values())),
        "binary_paths": list(binary_hashes),
        "build_pluto_ini_sha256": observed_build_config,
        "rendered_inputs": inputs,
        "grid_out": grid_hashes,
        "historical_evidence": evidence,
        "restart": restart,
        "snapshots": snapshots,
        "limitations": {
            "snapshot_payloads_rehashed": False,
            "historical_source_tree_hash_manifest_available": False,
            "source_build_binding": (
                "current retained parent C/header hashes plus equality of parent src/pluto, parent pluto, "
                "continuation pluto and immutable run/staging evidence"
            ),
        },
    }
    if os.path.lexists(receipt):
        raise FileExistsError(f"refusing existing lineage receipt: {receipt}")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_suffix(receipt.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(receipt)
    return payload


def _provenance_snapshot_metadata(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": item.get("path"),
        "resolved_path": item.get("resolved_path"),
        "timestep": item.get("timestep"),
        "output_index": item.get("output_index"),
        "time_code": item.get("time_code"),
        "shape": item.get("shape"),
        "size_bytes": item.get("size_bytes"),
        "device": item.get("device"),
        "inode": item.get("inode"),
        "mtime_ns": item.get("mtime_ns"),
        "ctime_ns": item.get("ctime_ns"),
    }


def bind_analysis_provenance(*, receipt: Path, provenance: Path, manifest: Path) -> dict[str, Any]:
    lineage = _read_object(receipt, "G-HI lineage receipt")
    if lineage.get("status") != "passed":
        raise LineageError("cannot bind a non-passing lineage receipt")
    for path_value in lineage.get("binary_paths", []):
        if sha256_file(Path(path_value)) != lineage.get("binary_sha256"):
            raise LineageError(f"lineage executable changed before binding: {path_value}")
    rendered_inputs = lineage.get("rendered_inputs")
    if not isinstance(rendered_inputs, dict):
        raise LineageError("lineage receipt lacks rendered inputs")
    for name, record in rendered_inputs.items():
        if not isinstance(record, dict):
            raise LineageError(f"invalid rendered-input receipt for {name}")
        for path_name in ("parent_path", "continuation_path"):
            if sha256_file(Path(str(record.get(path_name)))) != record.get("sha256"):
                raise LineageError(f"lineage rendered input changed before binding: {name} {path_name}")
    for label, record in lineage.get("historical_evidence", {}).items():
        if not isinstance(record, dict) or sha256_file(Path(str(record.get("path")))) != record.get("sha256"):
            raise LineageError(f"lineage historical evidence changed before binding: {label}")
    payload = _read_object(provenance, "G-HI analysis provenance")
    if payload.get("case") != "G-HI":
        raise LineageError("analysis provenance is not G-HI")
    if Path(str(payload.get("problem_source_dir"))).resolve() != Path(str(lineage["problem_source_dir"])).resolve():
        raise LineageError("analysis did not use the verified parent source directory")
    if payload.get("problem_source_hashes") != lineage.get("source_hashes"):
        raise LineageError("analysis parent-source hashes differ from the lineage receipt")
    inputs = rendered_inputs
    if payload.get("pluto_ini_sha256") != inputs["pluto.ini"]["sha256"]:
        raise LineageError("analysis pluto.ini differs from the lineage receipt")
    if payload.get("environment_sha256") != inputs["tabulated_cosmo_002031.csv"]["sha256"]:
        raise LineageError("analysis environment table differs from the lineage receipt")
    expected_snapshots = [
        _provenance_snapshot_metadata(item) for item in lineage["snapshots"]["analysis_chain"]
    ]
    if payload.get("snapshots") != expected_snapshots:
        raise LineageError("analysis snapshot chain differs from the verified inherited lineage")
    if "g_hi_inherited_lineage" in payload:
        raise LineageError("analysis provenance already contains a lineage binding")

    prebind_provenance_sha256 = sha256_file(provenance)
    _require_regular(manifest, "G-HI output manifest")
    with manifest.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if reader.fieldnames != ["sha256", "filename"]:
        raise LineageError("invalid G-HI output manifest schema")
    if tuple(row.get("filename") for row in rows) != ANALYSIS_OUTPUT_NAMES:
        raise LineageError("G-HI output manifest does not contain the exact analysis outputs")
    matches = [row for row in rows if row["filename"] == provenance.name]
    if len(matches) != 1:
        raise LineageError("G-HI output manifest must contain provenance.json exactly once")
    if matches[0].get("sha256") != prebind_provenance_sha256:
        raise LineageError("G-HI output manifest does not bind the pre-bind provenance bytes")

    lineage_bytes = receipt.read_bytes()
    payload["g_hi_inherited_lineage"] = {
        "receipt_sha256": hashlib.sha256(lineage_bytes).hexdigest(),
        "receipt": lineage,
    }
    provenance_bytes = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    matches[0]["sha256"] = hashlib.sha256(provenance_bytes).hexdigest()
    manifest_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(manifest_buffer, fieldnames=("sha256", "filename"))
    writer.writeheader()
    writer.writerows(rows)
    manifest_bytes = manifest_buffer.getvalue().encode("utf-8")

    temporary = provenance.with_suffix(provenance.suffix + ".tmp")
    temporary_manifest = manifest.with_suffix(manifest.suffix + ".tmp")
    if os.path.lexists(temporary) or os.path.lexists(temporary_manifest):
        raise LineageError("stale temporary lineage-binding output exists")
    try:
        with temporary.open("xb") as handle:
            handle.write(provenance_bytes)
        with temporary_manifest.open("xb") as handle:
            handle.write(manifest_bytes)
        temporary.replace(provenance)
        temporary_manifest.replace(manifest)
    except Exception:
        temporary.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
        raise
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--parent-problem", type=Path, required=True)
    validate.add_argument("--continuation-problem", type=Path, required=True)
    for label in EXPECTED_EVIDENCE_HASHES:
        validate.add_argument("--" + label.replace("_", "-"), type=Path, required=True)
    validate.add_argument("--receipt", type=Path, required=True)
    bind = subparsers.add_parser("bind")
    bind.add_argument("--receipt", type=Path, required=True)
    bind.add_argument("--provenance", type=Path, required=True)
    bind.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate":
        paths = {label: getattr(args, label) for label in EXPECTED_EVIDENCE_HASHES}
        result = validate_lineage(
            parent_problem=args.parent_problem,
            continuation_problem=args.continuation_problem,
            evidence_paths=paths,
            receipt=args.receipt,
            rehash_restart_hdf5=True,
        )
        print("G_HI_INHERITED_LINEAGE_OK", hashlib.sha256(args.receipt.read_bytes()).hexdigest())
        print("G_HI_PARENT_SOURCE", result["problem_source_dir"])
    else:
        bind_analysis_provenance(receipt=args.receipt, provenance=args.provenance, manifest=args.manifest)
        print("G_HI_ANALYSIS_LINEAGE_BOUND", sha256_file(args.provenance))


if __name__ == "__main__":
    main()
