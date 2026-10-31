#!/usr/bin/env python3
"""Bind the Q-031 native smoke and package only validated pilot products."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from package_q031_flux_results import (
    create_archive, read_json, require_regular_file, sha256_file, verify_archive,
)

CASES = ("C-HI", "G-HI")
PRODUCTS = (
    "native_emission_0deg.npz", "native_emission_45deg.npz", "native_emission_90deg.npz",
    "summary.csv", "summary.json", "provenance.json",
)
CONVENTIONS = ["retained_linear", "clamp_each_coordinate"]


def write_exclusive(path: Path, payload: dict) -> None:
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def verify_manifest(path: Path, *, relative: bool) -> dict[str, str]:
    require_regular_file(path)
    result = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValueError(f"Malformed checksum line in {path}")
        digest, name = match.groups()
        item = Path(name)
        if name in result or ".." in item.parts or (relative and item.is_absolute()):
            raise ValueError(f"Unsafe or duplicate checksum path: {name}")
        target = path.parent / item if relative else item
        if not relative and not item.is_absolute():
            raise ValueError(f"Runtime path must be absolute: {name}")
        require_regular_file(target)
        if sha256_file(target) != digest:
            raise ValueError(f"Checksum mismatch: {target}")
        result[name] = digest
    if not result:
        raise ValueError(f"Empty checksum manifest: {path}")
    return result


def measured_peak_kib(path: Path) -> int:
    require_regular_file(path)
    resource_text = path.read_text()
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", resource_text)
    exit_match = re.search(r"Exit status:\s*(\d+)", resource_text)
    if not match or not exit_match or exit_match[1] != "0" or int(match[1]) <= 0:
        raise ValueError(f"Missing successful measured-resource record: {path}")
    return int(match[1])


def runtime_identity() -> dict:
    modules = {}
    for name in ("numpy", "scipy", "h5py", "numba", "astropy",
                 "numpy.core._multiarray_umath", "scipy.special._ufuncs",
                 "scipy.ndimage._nd_image", "scipy.sparse._sparsetools", "h5py.h5"):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        modules[name] = {"path": str(path), "sha256": sha256_file(path),
                         "version": getattr(module, "__version__", None)}
    executable = Path(sys.executable).resolve()
    return {
        "python_version": sys.version, "python_executable": str(executable),
        "python_executable_sha256": sha256_file(executable), "modules": modules,
        "user_site_disabled": bool(sys.flags.no_user_site),
    }


def smoke_receipt(stage: Path) -> dict:
    run = stage / "run_smoke"
    verify_manifest(stage / "stage_checksums.sha256", relative=True)
    runtime = verify_manifest(stage / "runtime_checksums.sha256", relative=False)
    require_regular_file(run / "tests.xml")
    root = ET.parse(run / "tests.xml").getroot()
    tests = root.findall(".//testcase")
    if not tests or any(case.find(tag) is not None for case in tests for tag in ("failure", "error")):
        raise ValueError("Synthetic smoke has no tests or failed tests")
    real = [case for case in tests if case.attrib.get("name") == "test_real_kernel_cli_smoke"]
    if len(real) != 1 or real[0].find("skipped") is not None:
        raise ValueError("The real-kernel end-to-end smoke did not pass")
    peak_kib = measured_peak_kib(run / "resources.txt")
    if not 0 < peak_kib < 7 * 1024**2:
        raise ValueError("Synthetic smoke exceeded its measured memory gate")
    payload = {
        "status": "passed", "native_payload_read": False,
        "real_kernel_cli_smoke": "passed", "test_count": len(tests),
        "skipped_test_count": sum(case.find("skipped") is not None for case in tests),
        "maximum_resident_set_kib": peak_kib,
        "stage_checksums_sha256": sha256_file(stage / "stage_checksums.sha256"),
        "runtime_checksums_sha256": sha256_file(stage / "runtime_checksums.sha256"),
        "runtime_hashes": runtime,
        "tests_xml_sha256": sha256_file(run / "tests.xml"),
        "resources_sha256": sha256_file(run / "resources.txt"),
        "python_environment": runtime_identity(),
    }
    write_exclusive(run / "completion.json", payload)
    return payload


def check_smoke(stage: Path) -> dict:
    run = stage / "run_smoke"
    receipt = read_json(run / "completion.json")
    verify_manifest(stage / "stage_checksums.sha256", relative=True)
    runtime = verify_manifest(stage / "runtime_checksums.sha256", relative=False)
    expected = {
        "status": "passed", "native_payload_read": False,
        "real_kernel_cli_smoke": "passed", "runtime_hashes": runtime,
        "stage_checksums_sha256": sha256_file(stage / "stage_checksums.sha256"),
        "runtime_checksums_sha256": sha256_file(stage / "runtime_checksums.sha256"),
        "tests_xml_sha256": sha256_file(run / "tests.xml"),
        "resources_sha256": sha256_file(run / "resources.txt"),
        "python_environment": runtime_identity(),
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Smoke completion no longer binds the staged pilot")
    if not 0 < receipt.get("maximum_resident_set_kib", math.inf) < 7 * 1024**2:
        raise ValueError("Invalid smoke memory record")
    return receipt


def validate_native_binding(case: str, provenance: dict, dependencies: dict) -> None:
    flux = dependencies.get("flux", {})
    sources = [row for row in flux.get("source_manifests", []) if row.get("case") == case]
    if len(sources) != 1:
        raise ValueError(f"Missing dependency source binding for {case}")
    binding = sources[0]
    if provenance.get("source_manifest_row") != binding["selected_row"]:
        raise ValueError(f"Extractor source row differs from dependencies for {case}")
    if provenance.get("compact_input_sha256", {}).get(binding["manifest"]) != binding["sha256"]:
        raise ValueError(f"Extractor source-manifest hash differs from dependencies for {case}")
    identities = flux.get("native_input_identities", {}).get(case, {})
    for extracted, dependency in (("current", "target"), ("baseline", "baseline")):
        identity = identities.get(dependency, {})
        if provenance.get("source_resolution", {}).get(f"{extracted}_resolved") != identity.get("resolved_path"):
            raise ValueError(f"Extractor resolved {extracted} differs from dependencies for {case}")
        fields = ("device", "inode", "size_bytes", "mtime_ns", "ctime_ns")
        if any(field not in identity for field in fields):
            raise ValueError(f"Incomplete dependency native identity for {case}")
        expected = {field: identity[field] for field in fields}
        for phase in ("pre_read_identities", "post_read_identities"):
            if provenance.get("native_hdf5", {}).get(phase, {}).get(extracted) != expected:
                raise ValueError(f"Extractor {extracted} identity differs from dependencies for {case}/{phase}")


def package(stage: Path) -> dict:
    smoke = check_smoke(stage)
    before = read_json(stage / "run_pilot/dependencies_before.json")
    after = read_json(stage / "run_pilot/dependencies_after.json")
    if before.get("status") != "verified" or before != after:
        raise ValueError("Dependency evidence changed during the pilot")
    results = stage / "results"
    if sorted(path.name for path in results.iterdir()) != sorted(CASES):
        raise ValueError("Native pilot must contain exactly C-HI and G-HI")
    expected = {}
    for case in CASES:
        root = results / case
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f"Invalid case directory: {case}")
        if sorted(path.name for path in root.iterdir()) != sorted((*PRODUCTS, "manifest.sha256")):
            raise ValueError(f"Unexpected case products: {case}")
        manifest = verify_manifest(root / "manifest.sha256", relative=True)
        if set(manifest) != set(PRODUCTS):
            raise ValueError(f"Incomplete native product manifest: {case}")
        provenance = read_json(root / "provenance.json")
        required = {"status": "validated", "case": case, "snapshot_index": 40,
                    "views": [0, 45, 90], "conventions": CONVENTIONS}
        if any(provenance.get(key) != value for key, value in required.items()):
            raise ValueError(f"Native quantitative validation failed: {case}")
        validate_native_binding(case, provenance, before)
        for name in (*PRODUCTS, "manifest.sha256"):
            source = root / name
            expected[f"results/{case}/{name}"] = {
                "source": source, "sha256": sha256_file(source),
                "size_bytes": source.stat().st_size,
            }
    peaks = {case: measured_peak_kib(stage / "run_pilot" / f"{case}.resources.txt") for case in CASES}
    for name in ("dependencies_before.json", "dependencies_after.json", "C-HI.resources.txt", "G-HI.resources.txt"):
        source = stage / "run_pilot" / name
        expected[f"provenance/{name}"] = {
            "source": source, "sha256": sha256_file(source), "size_bytes": source.stat().st_size,
        }
    for name in ("completion.json", "tests.xml", "resources.txt"):
        source = stage / "run_smoke" / name
        expected[f"provenance/smoke/{name}"] = {
            "source": source, "sha256": sha256_file(source), "size_bytes": source.stat().st_size,
        }
    for name in ("stage_checksums.sha256", "runtime_checksums.sha256", "stage_origin.json"):
        source = stage / name
        require_regular_file(source)
        expected[f"provenance/{name}"] = {
            "source": source, "sha256": sha256_file(source), "size_bytes": source.stat().st_size,
        }
    expected = dict(sorted(expected.items()))
    archive = stage / "q031_native_pilot.tar.gz"
    receipt_path = stage / "q031_native_pilot.receipt.json"
    if os.path.lexists(archive) or os.path.lexists(receipt_path):
        raise FileExistsError("Refusing to overwrite native pilot archive/receipt")
    payload = {
        "status": "verified", "cases": list(CASES), "snapshot_index": 40,
        "conventions": CONVENTIONS, "archive": str(archive),
        "stage_checksums_sha256": smoke["stage_checksums_sha256"],
        "runtime_hashes": smoke["runtime_hashes"],
        "python_environment": smoke["python_environment"],
        "source_revision": read_json(stage / "stage_origin.json"),
        "native_payload_rehashed": False,
        "maximum_resident_set_kib": peaks,
        "scientific_interpretation": "pending independent native-product review",
        "members": [{"path": name, "sha256": data["sha256"], "size_bytes": data["size_bytes"]}
                    for name, data in expected.items()],
    }
    archive_created = False
    receipt_created = False
    try:
        create_archive(archive, expected)
        archive_created = True
        verify_archive(archive, expected)
        payload["archive_sha256"] = sha256_file(archive)
        with receipt_path.open("x") as handle:
            receipt_created = True
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        if read_json(receipt_path) != payload:
            raise ValueError("Native package receipt readback mismatch")
    except Exception:
        if receipt_created:
            receipt_path.unlink()
        if archive_created:
            archive.unlink()
        raise
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("smoke-receipt", "check-smoke", "package"))
    parser.add_argument("--stage-root", type=Path, required=True)
    args = parser.parse_args()
    result = {"smoke-receipt": smoke_receipt, "check-smoke": check_smoke, "package": package}[args.action](args.stage_root)
    print("Q031_NATIVE", args.action, result["status"], flush=True)


if __name__ == "__main__":
    main()
