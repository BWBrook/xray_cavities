from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "kunanyi" / "validate_q031_native_dependencies.py"
SPEC = importlib.util.spec_from_file_location("validate_q031_native_dependencies", SCRIPT)
assert SPEC and SPEC.loader
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_migration_fixture(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "migration"
    state = root / "state"
    state.mkdir(parents=True)
    units: list[dict[str, str]] = []
    for index in range(10):
        source = root / f"scratch-{index}"
        destination = root / "archive" / f"unit-{index}"
        destination.mkdir(parents=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        source_target = str(destination)
        source.symlink_to(source_target)
        units.append({"source": str(source), "destination": source_target})
    (root / "archive").chmod(0o700)
    raw_plan = {
        "archive_root": str(root / "archive"),
        "authority": "synthetic-test",
        "metadata_policy": "private_archive",
        "units": units,
    }
    plan = {"schema": 2, **raw_plan}
    plan_hash = gate.canonical_sha256(plan)
    (root / "migration_plan.json").write_text(json.dumps(raw_plan) + "\n", encoding="utf-8")
    (state / "plan-binding.json").write_text(
        json.dumps({"schema": 2, "plan_hash": plan_hash, "plan": plan}) + "\n", encoding="utf-8"
    )
    verified_units = []
    for unit in units:
        unit_id = gate._unit_id(unit)
        tombstone = str(Path(unit["source"]).with_name(f".{Path(unit['source']).name}.xray-migration-{unit_id}.tombstone"))
        unit_dir = state / f"unit-{unit_id}"
        unit_dir.mkdir()
        status = {
            "schema": 2,
            "plan_hash": plan_hash,
            "unit_id": unit_id,
            "source": unit["source"],
            "destination": unit["destination"],
            "tombstone": tombstone,
            "stage": "complete",
        }
        (unit_dir / "status.json").write_text(json.dumps(status) + "\n", encoding="utf-8")
        verified_units.append({**unit, "unit_id": unit_id, "stage": "complete"})
    (state / "verified-manifest.json").write_text(
        json.dumps({"schema": 2, "plan_hash": plan_hash, "units": verified_units}) + "\n", encoding="utf-8"
    )
    (state / "events.jsonl").write_text(
        json.dumps({"event": "device-transition-execute-start", "plan_hash": plan_hash})
        + "\n"
        + json.dumps({"event": "device-transition-execute-complete", "plan_hash": plan_hash})
        + "\n",
        encoding="utf-8",
    )
    return root, plan_hash


def write_flux_fixture(tmp_path: Path) -> tuple[Path, Path, list[Path]]:
    package_script = ROOT / "scripts" / "kunanyi" / "package_q031_flux_results.py"
    package_spec = importlib.util.spec_from_file_location("package_q031_flux_results_fixture", package_script)
    assert package_spec and package_spec.loader
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[package_spec.name] = package
    package_spec.loader.exec_module(package)

    stage = tmp_path / "flux"
    staged_science = stage / "scripts" / "science"
    current_science = tmp_path / "current-science"
    staged_science.mkdir(parents=True)
    current_science.mkdir()
    for index, name in enumerate(package.ANALYSIS_NAMES):
        for directory in (staged_science, current_science):
            (directory / name).write_text(f"implementation {index}\n", encoding="utf-8")
    results = stage / "results_production"
    manifests: list[Path] = []
    for case in package.EXPECTED_CASES["production"]:
        case_dir = results / case
        case_dir.mkdir(parents=True)
        raw_root = stage / "raw" / case
        raw_root.mkdir(parents=True)
        raw_paths = []
        for index in range(51):
            raw_path = raw_root / f"data.{index:04d}.flt.h5"
            raw_path.write_bytes(f"{case}-{index}\n".encode())
            raw_paths.append(raw_path)
        snapshots = []
        for index, raw_path in enumerate(raw_paths):
            observed = raw_path.stat()
            snapshots.append({
                "path": str(raw_path),
                "resolved_path": str(raw_path.resolve()),
                "timestep": f"Timestep_{index}",
                "output_index": index,
                "time_code": float(index),
                "shape": [4, 3, 2],
                "size_bytes": observed.st_size,
                "device": observed.st_dev,
                "inode": observed.st_ino,
                "mtime_ns": observed.st_mtime_ns,
                "ctime_ns": observed.st_ctime_ns,
            })
        for index, name in enumerate(package.DATA_NAMES):
            (case_dir / name).write_text(f"{case},{name},{index}\n", encoding="utf-8")
        provenance = {
            "case": case,
            "snapshots": snapshots,
            "analysis_implementation_hashes": {
                name: _sha256(staged_science / name) for name in package.ANALYSIS_NAMES
            },
            "outputs": {name: _sha256(case_dir / name) for name in package.DATA_NAMES},
        }
        (case_dir / "provenance.json").write_text(json.dumps(provenance) + "\n", encoding="utf-8")
        with (case_dir / "manifest.sha256.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("sha256", "filename"))
            writer.writeheader()
            for name in package.OUTPUT_NAMES:
                writer.writerow({"sha256": _sha256(case_dir / name), "filename": name})
        manifest = tmp_path / f"{case}.source_manifest.csv"
        with manifest.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=(
                "case", "snapshot_index", "actual_time_myr", "actual_time_code", "input_h5", "timestep",
                "baseline_h5", "baseline_timestep", "shape_nz_ny_nx", "baseline_grid_shape_nz_ny_nx",
                "baseline_time_code", "file_size_bytes", "baseline_file_size_bytes",
            ))
            writer.writeheader()
            writer.writerow({
                "case": case,
                "snapshot_index": 40,
                "actual_time_myr": 40.0,
                "actual_time_code": 40.0,
                "input_h5": str(raw_paths[40]),
                "timestep": "Timestep_40",
                "baseline_h5": str(raw_paths[0]),
                "baseline_timestep": "Timestep_0",
                "shape_nz_ny_nx": "4x3x2",
                "baseline_grid_shape_nz_ny_nx": "4x3x2",
                "baseline_time_code": 0.0,
                "file_size_bytes": raw_paths[40].stat().st_size,
                "baseline_file_size_bytes": raw_paths[0].stat().st_size,
            })
        if case in gate.NATIVE_CASES:
            manifests.append(manifest)
    (results / "completion.json").write_text(
        json.dumps({"cases": list(package.EXPECTED_CASES["production"]), "status": "complete", "payload": package.COMPLETION_PAYLOAD})
        + "\n",
        encoding="utf-8",
    )
    package.package_results(
        results_dir=results,
        mode="production",
        science_dir=staged_science,
        archive=stage / "compact_production.tar.gz",
        receipt=stage / "compact_production.receipt.json",
    )
    return stage, current_science, manifests


def test_valid_migration_gate_is_parameterized_for_synthetic_plan(tmp_path: Path) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    raw_plan = json.loads((root / "migration_plan.json").read_text())
    binding = json.loads((root / "state" / "plan-binding.json").read_text())
    assert "schema" not in raw_plan
    assert binding["plan"]["schema"] == 2
    assert gate.canonical_sha256(raw_plan) != plan_hash
    result = gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)
    assert result["plan_hash"] == plan_hash
    assert result["unit_count"] == 10
    assert result["input_small_file_hashes"]


def test_normalization_matches_frozen_migrator(tmp_path: Path) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    raw = json.loads((root / "migration_plan.json").read_text())
    spec = importlib.util.spec_from_file_location(
        "frozen_migration_for_dependency_test", ROOT / "scripts/kunanyi/migrate_xray_scratch_to_home.py"
    )
    assert spec and spec.loader
    frozen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = frozen
    spec.loader.exec_module(frozen)
    normalized = gate._normalize_migration_plan(raw)
    assert normalized == frozen._validate_plan(raw)
    assert gate.canonical_json(normalized) == frozen._canonical(normalized)
    assert gate.canonical_sha256(normalized) == frozen._plan_hash(normalized) == plan_hash


def test_frozen_production_raw_plan_reproduces_immutable_hash() -> None:
    path = ROOT / "docs/science/assets/scratch_home_migration_2026-10-16/migration_plan.json"
    raw = json.loads(path.read_text())
    assert "schema" not in raw
    assert gate.canonical_sha256(raw) != gate.KNOWN_PLAN_HASH
    assert gate.canonical_sha256(gate._normalize_migration_plan(raw)) == gate.KNOWN_PLAN_HASH


@pytest.mark.parametrize("mutation", [
    "schema", "extra_key", "missing_key", "policy", "authority", "unit_count", "unit_schema",
    "relative_source", "nonstring_source", "null_source", "relative_archive",
    "outside_destination", "overlapping_sources", "overlapping_destinations",
])
def test_migration_gate_rejects_malformed_raw_plan(tmp_path: Path, mutation: str) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    path = root / "migration_plan.json"
    raw = json.loads(path.read_text())
    if mutation == "schema":
        raw["schema"] = 2
    elif mutation == "extra_key":
        raw["unexpected"] = True
    elif mutation == "missing_key":
        raw.pop("authority")
    elif mutation == "policy":
        raw["metadata_policy"] = "public"
    elif mutation == "authority":
        raw["authority"] = " "
    elif mutation == "unit_count":
        raw["units"].pop()
    elif mutation == "unit_schema":
        raw["units"][0]["unexpected"] = True
    elif mutation == "relative_source":
        raw["units"][0]["source"] = "scratch"
    elif mutation == "nonstring_source":
        raw["units"][0]["source"] = None
    elif mutation == "null_source":
        raw["units"][0]["source"] += "\0"
    elif mutation == "relative_archive":
        raw["archive_root"] = "archive"
    elif mutation == "outside_destination":
        raw["units"][0]["destination"] = str(root / "elsewhere")
    elif mutation == "overlapping_sources":
        raw["units"][1]["source"] = raw["units"][0]["source"] + "/nested"
    elif mutation == "overlapping_destinations":
        raw["units"][1]["destination"] = raw["units"][0]["destination"]
    path.write_text(json.dumps(raw))
    with pytest.raises(gate.DependencyGateError):
        gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)


@pytest.mark.parametrize("mutation", ["missing_schema", "extra_key", "raw_plan", "hash", "schema_type", "plan_schema"])
def test_migration_gate_rejects_malformed_binding(tmp_path: Path, mutation: str) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    path = root / "state" / "plan-binding.json"
    binding = json.loads(path.read_text())
    if mutation == "missing_schema":
        binding.pop("schema")
    elif mutation == "extra_key":
        binding["unexpected"] = True
    elif mutation == "raw_plan":
        binding["plan"].pop("schema")
    elif mutation == "hash":
        binding["plan_hash"] = "0" * 64
    elif mutation == "schema_type":
        binding["schema"] = 2.0
    elif mutation == "plan_schema":
        binding["plan"]["schema"] = 2.0
    path.write_text(json.dumps(binding))
    with pytest.raises(gate.DependencyGateError, match="plan-binding"):
        gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)


def test_migration_gate_rejects_unfinished_unit(tmp_path: Path) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    status_path = next((root / "state").glob("unit-*/status.json"))
    status = json.loads(status_path.read_text())
    status["stage"] = "copied"
    status_path.write_text(json.dumps(status))
    with pytest.raises(gate.DependencyGateError, match="not plan-bound and complete"):
        gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)


def test_migration_gate_rejects_wrong_literal_link_and_tombstone(tmp_path: Path) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    status_path = next((root / "state").glob("unit-*/status.json"))
    status = json.loads(status_path.read_text())
    source = Path(status["source"])
    destination = Path(status["destination"])
    source.unlink()
    source.symlink_to(destination.parent / destination.name / "..")
    with pytest.raises(gate.DependencyGateError, match="literally target"):
        gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)

    source.unlink()
    source.symlink_to(destination)
    Path(status["tombstone"]).write_text("unexpected")
    with pytest.raises(gate.DependencyGateError, match="tombstone"):
        gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)


def test_migration_gate_rejects_plan_drift(tmp_path: Path) -> None:
    root, plan_hash = write_migration_fixture(tmp_path)
    plan_path = root / "migration_plan.json"
    plan = json.loads(plan_path.read_text())
    plan["authority"] = "drifted"
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(gate.DependencyGateError, match="plan hash mismatch"):
        gate.validate_migration_dependencies(root, expected_plan_hash=plan_hash)


def test_flux_gate_rejects_altered_receipt_and_archive(tmp_path: Path) -> None:
    stage, science, manifests = write_flux_fixture(tmp_path)
    receipt_path = stage / "compact_production.receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["snapshot_count_per_case"] = 50
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(gate.DependencyGateError, match="case/snapshot"):
        gate.validate_flux_dependencies(stage, science, manifests)

    stage, science, manifests = write_flux_fixture(tmp_path / "archive")
    archive = stage / "compact_production.tar.gz"
    with archive.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises((ValueError, tarfile.ReadError, gate.DependencyGateError)):
        gate.validate_flux_dependencies(stage, science, manifests)


def test_flux_gate_binds_native_source_rows_and_accepts_device_only_cross_allocation_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage, science, manifests = write_flux_fixture(tmp_path)
    result = gate.validate_flux_dependencies(stage, science, manifests)
    assert [record["case"] for record in result["source_manifests"]] == ["C-HI", "G-HI"]
    assert result["device_comparison"] == gate.DEVICE_COMPARISON
    assert result["input_small_file_hashes"]["source_manifests/C-HI.csv"] == result["source_manifests"][0]["sha256"]
    original_identity = gate._stat_identity

    def different_allocation_device(path: str) -> dict[str, object]:
        identity = original_identity(path)
        identity["device"] = int(identity["device"]) + 100
        return identity

    monkeypatch.setattr(gate, "_stat_identity", different_allocation_device)
    # NFS device numbers are allocation-local; the recorded values remain in the receipt.
    result = gate.validate_flux_dependencies(stage, science, manifests)
    assert result["native_input_identities"]["C-HI"]["target"]["device"] != result["source_manifests"][0]["target_flux_metadata"]["device"]


def test_flux_gate_rejects_replaced_native_input_or_swapped_source_row(tmp_path: Path) -> None:
    stage, science, manifests = write_flux_fixture(tmp_path)
    target = stage / "raw" / "C-HI" / "data.0040.flt.h5"
    target.write_bytes(b"replacement-with-different-size\n")
    with pytest.raises(gate.DependencyGateError, match="stat identity"):
        gate.validate_flux_dependencies(stage, science, manifests)

    stage, science, manifests = write_flux_fixture(tmp_path / "swap")
    rows = list(csv.DictReader(manifests[0].open(newline="")))
    rows[0]["input_h5"] = rows[0]["baseline_h5"]
    with manifests[0].open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(gate.DependencyGateError, match="resolved path differs"):
        gate.validate_flux_dependencies(stage, science, manifests)


def test_receipt_is_exclusive(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    output.write_text("existing\n")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        gate.write_receipt({"status": "verified"}, output)
