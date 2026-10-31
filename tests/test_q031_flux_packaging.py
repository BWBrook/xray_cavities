from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "kunanyi" / "package_q031_flux_results.py"
SPEC = importlib.util.spec_from_file_location("package_q031_flux_results", SCRIPT)
assert SPEC and SPEC.loader
package = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = package
SPEC.loader.exec_module(package)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_smoke_fixture(tmp_path: Path) -> tuple[Path, Path]:
    science = tmp_path / "science"
    science.mkdir()
    for index, name in enumerate(package.ANALYSIS_NAMES):
        (science / name).write_text(f"science-{index}\n")
    analysis_hashes = {name: sha256(science / name) for name in package.ANALYSIS_NAMES}
    results = tmp_path / "results_smoke"
    case = results / "G-LO"
    case.mkdir(parents=True)
    for index, name in enumerate(package.DATA_NAMES):
        (case / name).write_text(f"column\n{index}\n")
    provenance = {
        "case": "G-LO",
        "snapshots": [{"output_index": 0}, {"output_index": 1}],
        "analysis_implementation_hashes": analysis_hashes,
        "outputs": {name: sha256(case / name) for name in package.DATA_NAMES},
    }
    (case / "provenance.json").write_text(json.dumps(provenance, sort_keys=True) + "\n")
    with (case / "manifest.sha256.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sha256", "filename"))
        writer.writeheader()
        for name in package.OUTPUT_NAMES:
            writer.writerow({"sha256": sha256(case / name), "filename": name})
    (results / "completion.json").write_text(json.dumps({
        "cases": ["G-LO"],
        "status": "complete",
        "payload": package.COMPLETION_PAYLOAD,
    }) + "\n")
    (results / "run.out").write_text("live log before packaging\n")
    (results / "run.err").write_text("")
    (results / "synthetic_checks").mkdir()
    (results / "synthetic_checks" / "pytest.log").write_text("mutable\n")
    (results / "smoke_inputs").mkdir()
    (results / "smoke_inputs" / "data.0000.flt.h5").symlink_to("/not/packaged/input.h5")
    (case / "checkpoints").mkdir()
    (case / "checkpoints" / "0000.json").write_text("{}\n")
    return results, science


def test_recovery_cli_packages_only_manifest_bound_science_and_ignores_live_logs(tmp_path: Path) -> None:
    results, science = write_smoke_fixture(tmp_path)
    archive = tmp_path / "compact_smoke.tar.gz"
    receipt = tmp_path / "compact_smoke.receipt.json"
    completed = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--validate-existing-smoke", str(results),
            "--science-dir", str(science),
            "--archive", str(archive),
            "--receipt", str(receipt),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Q031_FLUX_PACKAGE_VERIFIED smoke" in completed.stdout
    first_receipt = json.loads(receipt.read_text())
    assert first_receipt["recovered_existing_smoke"] is True
    assert first_receipt["archive_sha256"] == sha256(archive)
    with tarfile.open(archive, "r:gz") as handle:
        names = handle.getnames()
    assert len(names) == 6
    assert names == [item["path"] for item in first_receipt["members"]]
    assert all("run." not in name and "checkpoints" not in name and "smoke_inputs" not in name for name in names)
    (results / "run.out").write_text("live log changed after successful science\n")
    (results / "synthetic_checks" / "pytest.log").write_text("also changed\n")
    second_receipt = package.package_results(
        results_dir=results,
        mode="smoke",
        science_dir=science,
        archive=tmp_path / "compact_smoke_second.tar.gz",
        receipt=tmp_path / "compact_smoke_second.receipt.json",
        recovered_existing_smoke=True,
    )
    assert second_receipt["members"] == first_receipt["members"]
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        package.package_results(
            results_dir=results,
            mode="smoke",
            science_dir=science,
            archive=archive,
            receipt=receipt,
            recovered_existing_smoke=True,
        )


def test_packaging_fails_closed_on_manifested_output_hash_change(tmp_path: Path) -> None:
    results, science = write_smoke_fixture(tmp_path)
    (results / "G-LO" / "region_storage.csv").write_text("tampered\n")
    archive = tmp_path / "compact_smoke.tar.gz"
    receipt = tmp_path / "compact_smoke.receipt.json"
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        package.package_results(
            results_dir=results,
            mode="smoke",
            science_dir=science,
            archive=archive,
            receipt=receipt,
            recovered_existing_smoke=True,
        )
    assert not archive.exists()
    assert not receipt.exists()


def test_packaging_rejects_same_size_mutation_after_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    results, science = write_smoke_fixture(tmp_path)
    output = results / "G-LO" / "region_storage.csv"
    original_archive_expected_files = package.archive_expected_files

    def mutate_after_validation(results_dir: Path, validated: dict) -> dict:
        original = output.read_bytes()
        output.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        assert output.stat().st_size == len(original)
        return original_archive_expected_files(results_dir, validated)

    monkeypatch.setattr(package, "archive_expected_files", mutate_after_validation)
    archive = tmp_path / "compact_smoke.tar.gz"
    receipt = tmp_path / "compact_smoke.receipt.json"
    with pytest.raises(ValueError, match="archive payload verification failed"):
        package.package_results(
            results_dir=results,
            mode="smoke",
            science_dir=science,
            archive=archive,
            receipt=receipt,
            recovered_existing_smoke=True,
        )
    assert not archive.exists()
    assert not receipt.exists()
