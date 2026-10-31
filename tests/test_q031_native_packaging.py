from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/kunanyi"))
SPEC = importlib.util.spec_from_file_location("native_package", ROOT / "scripts/kunanyi/package_q031_native_pilot.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


@pytest.mark.parametrize("exit_code", [0, 7])
def test_measured_child_exit_and_memory(tmp_path, exit_code):
    output = tmp_path / "resources.txt"
    command = [sys.executable, str(ROOT / "scripts/kunanyi/run_q031_measured.py"),
               str(output), sys.executable, "-c",
               f"import sys; payload=bytearray(8*1024*1024); sys.exit({exit_code})"]
    result = subprocess.run(command, check=False)
    assert result.returncode == exit_code
    if exit_code == 0:
        assert package.measured_peak_kib(output) > 0
    else:
        with pytest.raises(ValueError, match="Missing successful"):
            package.measured_peak_kib(output)
    original = output.read_bytes()
    assert subprocess.run(command, check=False, capture_output=True).returncode != 0
    assert output.read_bytes() == original


@pytest.fixture(autouse=True)
def fixed_test_runtime(monkeypatch):
    monkeypatch.setattr(package, "runtime_identity", lambda: {"test_runtime": "fixed"})


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value))


def smoke_fixture(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    source = stage / "source.py"
    source.write_text("test source\n")
    write_json(stage / "stage_origin.json", {"repository_head": "synthetic"})
    (stage / "stage_checksums.sha256").write_text(
        f"{digest(source)}  source.py\n{digest(stage / 'stage_origin.json')}  stage_origin.json\n")
    runtime = tmp_path / "runtime.py"
    runtime.write_text("runtime source\n")
    (stage / "runtime_checksums.sha256").write_text(f"{digest(runtime)}  {runtime}\n")
    run = stage / "run_smoke"
    run.mkdir()
    (run / "tests.xml").write_text('<testsuites><testsuite><testcase name="test_real_kernel_cli_smoke"/></testsuite></testsuites>')
    (run / "resources.txt").write_text("Maximum resident set size (kbytes): 123456\nExit status: 0\n")
    return stage


def complete_fixture(tmp_path):
    stage = smoke_fixture(tmp_path)
    package.smoke_receipt(stage)
    dependencies = {"status": "verified", "flux": {"source_manifests": [], "native_input_identities": {}}}
    for case in package.CASES:
        root = stage / "results" / case
        root.mkdir(parents=True)
        for name in package.PRODUCTS:
            (root / name).write_text(f"{case} {name}\n")
        identity = {"device": 1, "inode": 2, "size_bytes": 3, "mtime_ns": 4, "ctime_ns": 5}
        current_path, baseline_path = f"/{case}/data.0040.h5", f"/{case}/data.0000.h5"
        manifest_path = f"/inputs/{case}/source_manifest.csv"
        source_row = {"case": case, "input_h5": current_path, "baseline_h5": baseline_path}
        dependencies["flux"]["source_manifests"].append({
            "case": case, "selected_row": source_row, "manifest": manifest_path, "sha256": "f"*64,
        })
        dependencies["flux"]["native_input_identities"][case] = {
            "target": dict(identity, resolved_path=current_path),
            "baseline": dict(identity, resolved_path=baseline_path),
        }
        write_json(root / "provenance.json", {
            "status": "validated", "case": case, "snapshot_index": 40,
            "views": [0, 45, 90], "conventions": package.CONVENTIONS,
            "source_manifest_row": source_row,
            "compact_input_sha256": {manifest_path: "f"*64},
            "source_resolution": {"current_resolved": current_path, "baseline_resolved": baseline_path},
            "native_hdf5": {phase: {"current": identity, "baseline": identity}
                            for phase in ("pre_read_identities", "post_read_identities")},
        })
        (root / "manifest.sha256").write_text("".join(
            f"{digest(root / name)}  {name}\n" for name in package.PRODUCTS))
    (stage / "run_pilot").mkdir()
    for side in ("before", "after"):
        write_json(stage / "run_pilot" / f"dependencies_{side}.json", dependencies)
    for case in package.CASES:
        (stage / "run_pilot" / f"{case}.resources.txt").write_text(
            "Maximum resident set size (kbytes): 43210000\nExit status: 0\n")
    return stage


@pytest.mark.parametrize("change", ["skip", "missing", "failure", "memory", "exit"])
def test_smoke_rejects_unexercised_kernel_failures_and_resource_overrun(tmp_path, change):
    stage = smoke_fixture(tmp_path)
    run = stage / "run_smoke"
    if change in {"skip", "missing", "failure"}:
        content = '<testcase name="test_real_kernel_cli_smoke"/>'
        if change == "skip":
            content = '<testcase name="test_real_kernel_cli_smoke"><skipped/></testcase>'
        elif change == "missing":
            content = '<testcase name="a_different_test"/>'
        else:
            content = '<testcase name="test_real_kernel_cli_smoke"><failure/></testcase>'
        (run / "tests.xml").write_text(f"<testsuites><testsuite>{content}</testsuite></testsuites>")
    else:
        (run / "resources.txt").write_text(
            f"Maximum resident set size (kbytes): {8 * 1024**2 if change == 'memory' else 123456}\n"
            f"Exit status: {1 if change == 'exit' else 0}\n")
    with pytest.raises(ValueError):
        package.smoke_receipt(stage)
    assert not (run / "completion.json").exists()


@pytest.mark.parametrize("changed", ["source.py", "run_smoke/tests.xml", "run_smoke/resources.txt"])
def test_smoke_binding_rejects_source_and_evidence_drift(tmp_path, changed):
    stage = smoke_fixture(tmp_path)
    package.smoke_receipt(stage)
    with (stage / changed).open("a") as handle:
        handle.write("changed\n")
    with pytest.raises(ValueError):
        package.check_smoke(stage)


def test_package_exact_validated_products_and_refuse_overwrite(tmp_path):
    stage = complete_fixture(tmp_path)
    (stage / "native_cache").mkdir()
    (stage / "native_cache/huge.memmap").write_text("not included")
    receipt = package.package(stage)
    assert receipt["status"] == "verified"
    with tarfile.open(stage / "q031_native_pilot.tar.gz") as archive:
        names = archive.getnames()
    assert names == [row["path"] for row in receipt["members"]]
    assert len(names) == 24
    assert receipt["maximum_resident_set_kib"] == {case: 43210000 for case in package.CASES}
    assert all("cache" not in name for name in names)
    with pytest.raises(FileExistsError):
        package.package(stage)


@pytest.mark.parametrize("problem", ["changed", "missing", "unvalidated", "native_identity", "extra", "dependencies", "traversal"])
def test_package_rejects_incomplete_unvalidated_or_changed_evidence(tmp_path, problem):
    stage = complete_fixture(tmp_path)
    root = stage / "results/C-HI"
    if problem == "changed":
        (root / "summary.csv").write_text("changed")
    elif problem == "missing":
        (root / "native_emission_90deg.npz").unlink()
    elif problem in {"unvalidated", "native_identity"}:
        obj = json.loads((root / "provenance.json").read_text())
        if problem == "unvalidated":
            obj["status"] = "partial"
        else:
            obj["native_hdf5"]["post_read_identities"]["current"]["inode"] += 1
        write_json(root / "provenance.json", obj)
        (root / "manifest.sha256").write_text("".join(
            f"{digest(root / name)}  {name}\n" for name in package.PRODUCTS))
    elif problem == "extra":
        (root / "unexpected.txt").write_text("unexpected")
    elif problem == "dependencies":
        write_json(stage / "run_pilot/dependencies_after.json", {"status": "changed"})
    else:
        with (root / "manifest.sha256").open("a") as handle:
            handle.write(f"{'0'*64}  ../outside\n")
    with pytest.raises((ValueError, FileNotFoundError)):
        package.package(stage)
    assert not (stage / "q031_native_pilot.receipt.json").exists()


def test_smoke_rejects_changed_python_environment(tmp_path, monkeypatch):
    stage = smoke_fixture(tmp_path)
    package.smoke_receipt(stage)
    monkeypatch.setattr(package, "runtime_identity", lambda: {"test_runtime": "changed"})
    with pytest.raises(ValueError, match="Smoke completion"):
        package.check_smoke(stage)


def test_archive_verification_failure_leaves_no_blocking_package(tmp_path, monkeypatch):
    stage = complete_fixture(tmp_path)
    verify = package.verify_archive

    def fail(*args):
        raise ValueError("forced verification failure")

    monkeypatch.setattr(package, "verify_archive", fail)
    with pytest.raises(ValueError, match="forced"):
        package.package(stage)
    assert not (stage / "q031_native_pilot.tar.gz").exists()
    assert not (stage / "q031_native_pilot.receipt.json").exists()
    monkeypatch.setattr(package, "verify_archive", verify)
    assert package.package(stage)["status"] == "verified"
