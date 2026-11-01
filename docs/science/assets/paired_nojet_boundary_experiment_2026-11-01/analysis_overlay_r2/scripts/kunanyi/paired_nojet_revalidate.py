#!/usr/bin/env python3
"""Revalidate completed paired no-jet smokes through a bound analysis overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


CASES = ("cluster_002003", "group_002031")
BOUNDARIES = ("reflective", "outflow")
ORIGINAL_PBS = Path("scripts/kunanyi/paired_nojet_control.pbs")
ORIGINAL_BUDGET_VALIDATOR = Path("scripts/science/validate_paired_nojet_budget.py")
ORIGINAL_OUTPUT_VALIDATOR = Path("scripts/science/validate_paired_nojet_outputs.py")
UPDATED_BUDGET_VALIDATOR = Path("scripts/science/validate_paired_nojet_budget.py")
UPDATED_OUTPUT_VALIDATOR = Path("scripts/science/validate_paired_nojet_outputs.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def manifest_records(path: Path) -> dict[Path, str]:
    pattern = re.compile(r"^([0-9a-f]{64})  ([^\n]+)$")
    records: dict[Path, str] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        match = pattern.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid checksum manifest line {line_number}: {path}")
        relative = Path(match[2])
        if relative.is_absolute() or ".." in relative.parts or relative in records:
            raise ValueError(f"unsafe or duplicate manifest path: {relative}")
        records[relative] = match[1]
    if not records:
        raise ValueError(f"empty checksum manifest: {path}")
    return records


def verify_manifest(root: Path, name: str, *, allow_revalidated: bool = False) -> dict[Path, str]:
    manifest = root / name
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError(f"missing regular checksum manifest: {manifest}")
    records = manifest_records(manifest)
    for relative, expected in records.items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            raise ValueError(f"checksum mismatch: {path}")
    if allow_revalidated:
        actual = {
            path.relative_to(root)
            for path in root.rglob("*")
            if path.is_file() and path != manifest and "revalidated" not in path.relative_to(root).parts
        }
        if actual != set(records):
            raise ValueError(f"unmanifested immutable overlay files: {sorted(map(str, actual ^ set(records)))}")
    return records


def verify_bindings(physics_stage: Path, overlay: Path) -> dict:
    physics_stage = physics_stage.resolve()
    overlay = overlay.resolve()
    contract = load_json(overlay / "overlay_contract.json")
    if contract.get("status") != "validator_only_analysis_overlay":
        raise ValueError("analysis overlay contract status is invalid")
    if Path(contract["remote_physics_stage"]) != physics_stage:
        raise ValueError("physics stage differs from the overlay's bound remote stage")
    if Path(contract["remote_analysis_overlay"]) != overlay:
        raise ValueError("analysis overlay path differs from its bound remote path")
    verify_manifest(overlay, "overlay_checksums.sha256", allow_revalidated=True)
    stage_manifest = physics_stage / "stage_checksums.sha256"
    stage_records = manifest_records(stage_manifest)
    checks = {
        "original_stage_manifest_sha256": sha256(stage_manifest),
        "original_pbs_sha256": sha256(physics_stage / ORIGINAL_PBS),
        "original_budget_validator_sha256": sha256(physics_stage / ORIGINAL_BUDGET_VALIDATOR),
        "original_output_validator_sha256": sha256(physics_stage / ORIGINAL_OUTPUT_VALIDATOR),
        "updated_budget_validator_sha256": sha256(overlay / UPDATED_BUDGET_VALIDATOR),
        "updated_output_validator_sha256": sha256(overlay / UPDATED_OUTPUT_VALIDATOR),
        "budget_test_sha256": sha256(overlay / "tests/test_paired_nojet_budget.py"),
        "output_test_sha256": sha256(overlay / "tests/test_paired_nojet_outputs.py"),
    }
    for key, actual in checks.items():
        if contract.get(key) != actual:
            raise ValueError(f"overlay binding mismatch: {key}")
    for relative, key in (
        (ORIGINAL_PBS, "original_pbs_sha256"),
        (ORIGINAL_BUDGET_VALIDATOR, "original_budget_validator_sha256"),
        (ORIGINAL_OUTPUT_VALIDATOR, "original_output_validator_sha256"),
    ):
        if stage_records.get(relative) != contract[key]:
            raise ValueError(f"original stage manifest binding mismatch: {relative}")
    if contract.get("physical_acceptance_gates_changed") is not False or contract.get("physics_stage_files_changed") != []:
        raise ValueError("overlay contract does not preserve the physics stage and gates")
    return contract


def child_environment(physics_stage: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update({
        "LC_ALL": "C",
        "LANG": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(physics_stage / "scripts/science"),
    })
    return environment


def require_junit(xml: Path, expected: int) -> None:
    root = ET.parse(xml).getroot()
    tests = int(root.attrib.get("tests", sum(int(node.attrib.get("tests", 0)) for node in root.findall("testsuite"))))
    failures = int(root.attrib.get("failures", sum(int(node.attrib.get("failures", 0)) for node in root.findall("testsuite"))))
    errors = int(root.attrib.get("errors", sum(int(node.attrib.get("errors", 0)) for node in root.findall("testsuite"))))
    skipped = int(root.attrib.get("skipped", sum(int(node.attrib.get("skipped", 0)) for node in root.findall("testsuite"))))
    if (tests, failures, errors, skipped) != (expected, 0, 0, 0):
        raise ValueError(f"test gate differs from {(expected, 0, 0, 0)}: {(tests, failures, errors, skipped)}")


def run_budget_tests(physics_stage: Path, overlay: Path, output: Path, expected: int) -> Path:
    xml = output / "budget_tests.xml"
    command = [
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp", str(output / "pytest_tmp"), "--junitxml", str(xml),
        str(overlay / "tests/test_paired_nojet_budget.py"),
    ]
    subprocess.run(command, cwd=overlay, env=child_environment(physics_stage), check=True)
    require_junit(xml, expected)
    return xml


def run_output_helper_tests(physics_stage: Path, overlay: Path, output: Path, expected: int) -> Path:
    xml = output / "output_helper_tests.xml"
    command = [
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp", str(output / "output_pytest_tmp"), "--junitxml", str(xml),
        "-k", "stability_", str(overlay / "tests/test_paired_nojet_outputs.py"),
    ]
    subprocess.run(command, cwd=overlay, env=child_environment(physics_stage), check=True)
    require_junit(xml, expected)
    return xml


def measured_exit(path: Path) -> int:
    matches = re.findall(r"(?m)^Exit status: ([0-9]+)$", path.read_text())
    if len(matches) != 1:
        raise ValueError(f"missing or ambiguous measured MPI exit status: {path}")
    return int(matches[0])


def verify_native_smokes(physics_stage: Path, contract: dict) -> tuple[list[Path], list[Path], str]:
    receipts: list[Path] = []
    resources: list[Path] = []
    binary_hashes = set()
    build = load_json(physics_stage / "build/build_receipt.json")
    if build.get("status") != "built_common_binary" or build.get("stage_manifest_sha256") != contract["original_stage_manifest_sha256"]:
        raise ValueError("common build receipt does not bind the original physics stage")
    built_binary = build.get("files", {}).get("pluto")
    if not re.fullmatch(r"[0-9a-f]{64}", str(built_binary)):
        raise ValueError("common build receipt has no valid binary hash")
    for case in CASES:
        for boundary in BOUNDARIES:
            run = physics_stage / "smoke" / f"{case}_{boundary}"
            receipt_path = run / "output_receipt.json"
            resource_path = run / "simulation.resources.txt"
            receipt = load_json(receipt_path)
            if (
                receipt.get("schema_version") != 1
                or receipt.get("status") != "validated_paired_control_run"
                or receipt.get("case") != case
                or receipt.get("boundary") != boundary
                or receipt.get("mode") != "smoke"
                or Path(receipt.get("run_dir", "")).resolve() != run.resolve()
            ):
                raise ValueError(f"native smoke receipt identity failed: {receipt_path}")
            inputs = receipt.get("input_files", {})
            binary = inputs.get("pluto", {}).get("sha256")
            output_validator = inputs.get("validator_source:validate_paired_nojet_outputs.py", {}).get("sha256")
            if binary != sha256(run / "pluto") or output_validator != contract["original_output_validator_sha256"]:
                raise ValueError(f"native smoke receipt source/binary binding failed: {receipt_path}")
            if measured_exit(resource_path) != 0:
                raise ValueError(f"measured MPI execution did not exit zero: {resource_path}")
            binary_hashes.add(binary)
            receipts.append(receipt_path)
            resources.append(resource_path)
    if binary_hashes != {built_binary}:
        raise ValueError("the four smokes do not bind the same common binary")
    return receipts, resources, built_binary


def verified_budget_ledger(receipt: dict, run: Path) -> Path:
    ledger = (run / "paired_nojet_budget.csv").resolve()
    matches = [
        identity
        for identity in receipt.get("input_files", [])
        if Path(identity.get("path", "")).resolve() == ledger
    ]
    if len(matches) != 1 or matches[0].get("sha256") != sha256(ledger):
        raise ValueError(f"budget receipt does not hash-bind its direct ledger evidence: {ledger}")
    return ledger


def run_revalidation(physics_stage: Path, overlay: Path) -> Path:
    contract = verify_bindings(physics_stage, overlay)
    destination = overlay / "revalidated"
    destination.mkdir(mode=0o700, exist_ok=False)
    tests_xml = run_budget_tests(
        physics_stage,
        overlay,
        destination,
        int(contract["expected_budget_test_count"]),
    )
    output_tests_xml = run_output_helper_tests(
        physics_stage,
        overlay,
        destination,
        int(contract["expected_output_helper_test_count"]),
    )
    native_receipts, resources, binary_hash = verify_native_smokes(physics_stage, contract)
    budgets = destination / "budgets"
    pairs = destination / "pairs"
    budgets.mkdir()
    pairs.mkdir()
    budget_receipts: list[Path] = []
    ledgers: list[Path] = []
    pair_receipts: list[Path] = []
    environment = child_environment(physics_stage)
    for case in CASES:
        for boundary in BOUNDARIES:
            run = physics_stage / "smoke" / f"{case}_{boundary}"
            output = budgets / f"{case}_{boundary}.json"
            subprocess.run([
                sys.executable,
                str(overlay / UPDATED_BUDGET_VALIDATOR),
                "--run-dir", str(run),
                "--boundary", boundary,
                "--mode", "smoke",
                "--output", str(output),
            ], cwd=physics_stage, env=environment, check=True)
            receipt = load_json(output)
            if receipt.get("status") != "validated_paired_control_budget" or receipt.get("boundary") != boundary:
                raise ValueError(f"revalidated budget receipt identity failed: {output}")
            budget_receipts.append(output)
            ledgers.append(verified_budget_ledger(receipt, run))
        output = pairs / f"{case}.json"
        subprocess.run([
            sys.executable,
            str(overlay / UPDATED_OUTPUT_VALIDATOR),
            "--pair-receipts",
            str(physics_stage / "smoke" / f"{case}_reflective/output_receipt.json"),
            str(physics_stage / "smoke" / f"{case}_outflow/output_receipt.json"),
            "--output", str(output),
        ], cwd=physics_stage, env=environment, check=True)
        pair = load_json(output)
        if pair.get("status") != "validated_paired_control_identity" or pair.get("case") != case or pair.get("binary_sha256") != binary_hash:
            raise ValueError(f"revalidated pair receipt identity failed: {output}")
        pair_receipts.append(output)
    evidence_paths = [
        physics_stage / "build/build_receipt.json",
        physics_stage / "stage_checksums.sha256",
        overlay / "overlay_contract.json",
        overlay / "overlay_checksums.sha256",
        tests_xml,
        output_tests_xml,
        *native_receipts,
        *resources,
        *ledgers,
        *budget_receipts,
        *pair_receipts,
    ]
    evidence = {str(path.resolve()): sha256(path) for path in evidence_paths}
    gate = {
        "schema_version": 1,
        "status": "all_four_smokes_and_both_pairs_passed",
        "job_id": os.environ.get("PBS_JOBID"),
        "original_stage_manifest_sha256": contract["original_stage_manifest_sha256"],
        "overlay_manifest_sha256": sha256(overlay / "overlay_checksums.sha256"),
        "original_budget_validator_sha256": contract["original_budget_validator_sha256"],
        "updated_budget_validator_sha256": contract["updated_budget_validator_sha256"],
        "updated_output_validator_sha256": contract["updated_output_validator_sha256"],
        "common_binary_sha256": binary_hash,
        "budget_tests_passed": contract["expected_budget_test_count"],
        "output_helper_tests_passed": contract["expected_output_helper_test_count"],
        "native_smoke_receipts_verified": len(native_receipts),
        "measured_mpi_exit_zero_verified": len(resources),
        "budgets_revalidated": len(budget_receipts),
        "pairs_revalidated": len(pair_receipts),
        "evidence": evidence,
    }
    gate_path = destination / "gate_receipt.json"
    encoded = json.dumps(gate, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=destination, prefix=".gate_receipt.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, gate_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(json.dumps({"gate_receipt": str(gate_path), "status": gate["status"]}, sort_keys=True))
    return gate_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physics-stage", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--verify-bindings", action="store_true")
    args = parser.parse_args()
    if args.verify_bindings:
        verify_bindings(args.physics_stage, args.overlay)
    else:
        run_revalidation(args.physics_stage.resolve(), args.overlay.resolve())


if __name__ == "__main__":
    main()
