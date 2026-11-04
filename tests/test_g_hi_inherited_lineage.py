from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT / "scripts/science"
sys.path.insert(0, str(SCIENCE))
SCRIPT = ROOT / "scripts/kunanyi/validate_g_hi_inherited_lineage.py"
SPEC = importlib.util.spec_from_file_location("validate_g_hi_inherited_lineage", SCRIPT)
assert SPEC and SPEC.loader
lineage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lineage
SPEC.loader.exec_module(lineage)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_snapshot(path: Path, index: int, *, extra_timestep: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as handle:
        names = [f"Timestep_{index}"] + (["Timestep_duplicate"] if extra_timestep else [])
        for name in names:
            group = handle.create_group(name)
            group.attrs["Time"] = index * lineage.CODE_TIME_PER_MYR
            variables = group.create_group("vars")
            for dataset in ("rho", "prs", "tr1", "vx1", "vx2", "vx3"):
                variables.create_dataset(dataset, data=np.zeros((1, 1, 1)))


def write_fixture(tmp_path: Path) -> dict:
    parent = tmp_path / "parent/problem"
    continuation = tmp_path / "continuation/problem"
    source = parent / "src"
    source.mkdir(parents=True)
    continuation.mkdir(parents=True)
    for index, name in enumerate(lineage.REQUIRED_SOURCE_FILES):
        (source / name).write_text(f"source-{name}-{index}\n")
    (source / "extra.c").write_text("extra-source\n")
    binary = b"synthetic-pluto-binary\n"
    for path in (source / "pluto", parent / "pluto", continuation / "pluto"):
        path.write_bytes(binary)
        path.chmod(0o700)

    config_contents = {
        "case_manifest.json": "{}\n",
        "definitions_overrides.json": "{}\n",
        "environment.ini": "environment\n",
        "pluto.ini": "pluto-config\n",
        "tabulated_cosmo_002031.csv": "0,1,2,3,4,5\n1,1,2,3,4,5\n",
    }
    config_hashes = {}
    for name, content in config_contents.items():
        for problem in (parent, continuation):
            (problem / name).write_text(content)
        config_hashes[name] = sha256(parent / name)
    (source / "pluto.ini").write_text(config_contents["pluto.ini"])

    parent_outputs = parent / "outputs"
    continuation_outputs = continuation / "outputs"
    parent_outputs.mkdir()
    continuation_outputs.mkdir()
    for index in range(12):
        write_snapshot(parent_outputs / f"data.{index:04d}.flt.h5", index)
    (continuation_outputs / "data.0010.flt.h5").symlink_to(
        parent_outputs / "data.0010.flt.h5"
    )
    for index in range(11, 13):
        write_snapshot(continuation_outputs / f"data.{index:04d}.flt.h5", index)
    (parent_outputs / "grid.out").write_text(
        "# PLUTO grid\n# Generated on old\n# DIMENSIONS: 3\n1 0 1\n"
    )
    (continuation_outputs / "grid.out").write_text(
        "# PLUTO grid\n# Generated on new\n# DIMENSIONS: 3\n1 0 1\n"
    )

    fluid = parent_outputs / "data.0002.dbl.h5"
    particle = parent_outputs / "particles.1000.dbl"
    fluid.write_bytes(b"fluid-restart\n")
    particle.write_bytes(b"particle-restart\n")
    (continuation_outputs / fluid.name).symlink_to(fluid)
    (continuation_outputs / particle.name).symlink_to(particle)
    catalogue = parent_outputs / "dbl.h5.out"
    restart_out = parent_outputs / "restart.out"
    catalogue.write_text("2 3065.7857363 0.1 10011\n")
    restart_out.write_text("restart\n")
    (continuation_outputs / "dbl.h5.out").write_text(catalogue.read_text() + "3 later\n")
    (continuation_outputs / "restart.out").write_text("post-continuation restart\n")
    restart_report = {
        "status": "ok",
        "restart_record_count": 3,
        "fluid_restart": {"index": 2, "nstep": 10011, "time": 3065.7857363005746},
        "particle_restart": {"index": 1000, "stepNumber": 10011, "time": 3065.785736301},
        "input_sha256": {
            "fluid_catalogue": sha256(catalogue),
            "fluid_hdf5": sha256(fluid),
            "particle_restart": sha256(particle),
            "restart_out": sha256(restart_out),
        },
    }

    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    common = "\n".join(lineage.RUN_ENVIRONMENT_LINES) + "\n"
    evidence_paths = {
        "parent_run_log": evidence_root / "parent.out",
        "parent_source_revisions": evidence_root / "parent-source-revisions.txt",
        "continuation_run_log": evidence_root / "continuation.out",
        "staging_manifest": evidence_root / "staging.txt",
        "restart_report": evidence_root / "restart.json",
        "canonical_sequence_report": evidence_root / "sequence.csv",
        "endpoint_report": evidence_root / "endpoint.json",
        "source_revisions": evidence_root / "source-revisions.txt",
        "done_marker": evidence_root / "DONE",
    }
    evidence_paths["parent_run_log"].write_text(
        common + "--- setup problem ---\n--- build ---\nRUN_KIND=fresh\nMPI_EXIT_CODE=124\n"
    )
    evidence_paths["parent_source_revisions"].write_text("parent source revisions\n")
    evidence_paths["continuation_run_log"].write_text(
        common
        + "[info] reusing existing built problem at continuation\n"
        + "restart_pair_validation=passed report=restart.json\n"
        + "RUN_KIND=h5_restart_2\nMPI_EXIT_CODE=0\n"
    )
    evidence_paths["staging_manifest"].write_text(
        "source_root=/parent\n"
        "f\t/continuation/problem/pluto\t22\t\n"
        "f\t/continuation/problem/pluto.ini\t13\t\n"
    )
    evidence_paths["restart_report"].write_text(json.dumps(restart_report) + "\n")
    evidence_paths["canonical_sequence_report"].write_text("surface,status\nfloat_hdf5,passed\n")
    evidence_paths["endpoint_report"].write_text(json.dumps({
        "status": "passed",
        "endpoint_hdf5": {"time_code": 12 * lineage.CODE_TIME_PER_MYR},
    }) + "\n")
    evidence_paths["source_revisions"].write_text("source revisions\n")
    evidence_paths["done_marker"].write_text("status=done\n")
    evidence_hashes = {name: sha256(path) for name, path in evidence_paths.items()}
    return {
        "parent": parent,
        "continuation": continuation,
        "evidence_paths": evidence_paths,
        "evidence_hashes": evidence_hashes,
        "config_hashes": config_hashes,
        "receipt": tmp_path / "lineage.json",
    }


def validate(fixture: dict) -> dict:
    source_hashes = lineage._source_hashes(fixture["parent"] / "src")
    return lineage.validate_lineage(
        parent_problem=fixture["parent"],
        continuation_problem=fixture["continuation"],
        evidence_paths=fixture["evidence_paths"],
        receipt=fixture["receipt"],
        config_hashes=fixture["config_hashes"],
        evidence_hashes=fixture["evidence_hashes"],
        expected_executable_sha256=sha256(fixture["parent"] / "pluto"),
        expected_build_config_sha256=sha256(fixture["parent"] / "src/pluto.ini"),
        expected_source_count=len(source_hashes),
        expected_source_manifest_sha256=lineage._mapping_sha256(source_hashes),
        expected_grid_hashes={
            "parent": sha256(fixture["parent"] / "outputs/grid.out"),
            "continuation": sha256(fixture["continuation"] / "outputs/grid.out"),
        },
        expected_last_index=12,
    )


def write_analysis_outputs(fixture: dict, receipt: dict) -> tuple[Path, Path]:
    case = fixture["receipt"].parent / "G-HI"
    case.mkdir()
    provenance = case / "provenance.json"
    manifest = case / "manifest.sha256.csv"
    snapshots = []
    for item in receipt["snapshots"]["analysis_chain"]:
        snapshots.append(lineage._provenance_snapshot_metadata(item))
    provenance.write_text(json.dumps({
        "case": "G-HI",
        "problem_source_dir": receipt["problem_source_dir"],
        "problem_source_hashes": receipt["source_hashes"],
        "pluto_ini_sha256": fixture["config_hashes"]["pluto.ini"],
        "environment_sha256": fixture["config_hashes"]["tabulated_cosmo_002031.csv"],
        "snapshots": snapshots,
    }) + "\n")
    for name in lineage.ANALYSIS_OUTPUT_NAMES[:-1]:
        (case / name).write_text(name + "\n")
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sha256", "filename"))
        writer.writeheader()
        for name in lineage.ANALYSIS_OUTPUT_NAMES:
            writer.writerow({"sha256": sha256(case / name), "filename": name})
    return provenance, manifest


def test_accepts_inherited_parent_source_and_binds_analysis(tmp_path: Path) -> None:
    fixture = write_fixture(tmp_path)
    receipt = validate(fixture)
    assert receipt["status"] == "passed"
    assert receipt["binary_sha256"] == hashlib.sha256(b"synthetic-pluto-binary\n").hexdigest()
    assert receipt["snapshots"]["excluded_parent_overlap_indices"] == [11]
    assert receipt["snapshots"]["accepted_chain"][10]["path"].startswith(str(fixture["parent"]))
    assert receipt["snapshots"]["analysis_chain"][10]["path"].startswith(str(fixture["continuation"]))
    assert set(receipt["restart"]["input_identity"]) == {
        "fluid_catalogue",
        "fluid_hdf5",
        "particle_restart",
        "restart_out",
    }
    for name, identity in receipt["restart"]["input_identity"].items():
        path = Path(receipt["restart"]["accepted_parent_restart_paths"][name])
        observed = path.stat()
        assert identity == {
            "path": str(path),
            "resolved_path": str(path.resolve()),
            "device": observed.st_dev,
            "inode": observed.st_ino,
            "size_bytes": observed.st_size,
            "mtime_ns": observed.st_mtime_ns,
            "ctime_ns": observed.st_ctime_ns,
        }
    provenance, manifest = write_analysis_outputs(fixture, receipt)
    bound = lineage.bind_analysis_provenance(
        receipt=fixture["receipt"], provenance=provenance, manifest=manifest
    )
    assert bound["g_hi_inherited_lineage"]["receipt"]["status"] == "passed"
    rows = list(csv.DictReader(manifest.open()))
    assert [row["filename"] for row in rows] == list(lineage.ANALYSIS_OUTPUT_NAMES)
    assert rows[-1] == {"sha256": sha256(provenance), "filename": "provenance.json"}


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("binary", "executable differ"),
        ("config", "pluto.ini differs"),
        ("environment", "environment.ini differs"),
        ("missing_source", "required parent source"),
        ("restart", "inherited symlink"),
        ("ambiguous_snapshot", "ambiguous continuation snapshot"),
        ("missing_snapshot", "continuation snapshot chain"),
    ],
)
def test_rejects_mismatched_or_ambiguous_lineage(
    tmp_path: Path, mutation: str, match: str
) -> None:
    fixture = write_fixture(tmp_path)
    parent = fixture["parent"]
    continuation = fixture["continuation"]
    if mutation == "binary":
        (continuation / "pluto").write_bytes(b"different executable\n")
        (continuation / "pluto").chmod(0o700)
    elif mutation == "config":
        (continuation / "pluto.ini").write_text("different config\n")
    elif mutation == "environment":
        (continuation / "environment.ini").write_text("different environment\n")
    elif mutation == "missing_source":
        (parent / "src/jet.c").unlink()
    elif mutation == "restart":
        path = continuation / "outputs/data.0002.dbl.h5"
        path.unlink()
        path.write_bytes(b"not the parent restart\n")
    elif mutation == "ambiguous_snapshot":
        write_snapshot(continuation / "outputs/data.0012.flt.h5", 12, extra_timestep=True)
    elif mutation == "missing_snapshot":
        (continuation / "outputs/data.0012.flt.h5").unlink()
    with pytest.raises(lineage.LineageError, match=match):
        validate(fixture)
    assert not fixture["receipt"].exists()


def test_rejects_changed_historical_evidence(tmp_path: Path) -> None:
    fixture = write_fixture(tmp_path)
    with fixture["evidence_paths"]["continuation_run_log"].open("a") as handle:
        handle.write("changed\n")
    with pytest.raises(lineage.LineageError, match="historical continuation_run_log hash mismatch"):
        validate(fixture)


def test_hash_rejects_input_mutated_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "restart.bin"
    path.write_bytes(b"restart-payload")
    real_sha256 = lineage.hashlib.sha256

    class MutatingDigest:
        def __init__(self) -> None:
            self.digest = real_sha256()
            self.mutated = False

        def update(self, data: bytes) -> None:
            self.digest.update(data)
            if not self.mutated:
                with path.open("ab") as handle:
                    handle.write(b"-changed")
                self.mutated = True

        def hexdigest(self) -> str:
            return self.digest.hexdigest()

    monkeypatch.setattr(lineage.hashlib, "sha256", MutatingDigest)
    with pytest.raises(lineage.LineageError, match="changed during hashing"):
        lineage.sha256_file_with_identity(path)


def test_binding_rejects_unverified_source_choice_without_mutation(tmp_path: Path) -> None:
    fixture = write_fixture(tmp_path)
    receipt = validate(fixture)
    provenance, manifest = write_analysis_outputs(fixture, receipt)
    original_provenance = provenance.read_bytes()
    original_manifest = manifest.read_bytes()
    payload = json.loads(provenance.read_text())
    payload["problem_source_dir"] = str(fixture["continuation"] / "src")
    provenance.write_text(json.dumps(payload) + "\n")
    changed = provenance.read_bytes()
    with pytest.raises(lineage.LineageError, match="verified parent source"):
        lineage.bind_analysis_provenance(
            receipt=fixture["receipt"], provenance=provenance, manifest=manifest
        )
    assert provenance.read_bytes() == changed
    assert manifest.read_bytes() == original_manifest
    assert provenance.read_bytes() != original_provenance


@pytest.mark.parametrize("mutation", ["missing_row", "stale_provenance_hash"])
def test_binding_validates_manifest_before_writing(
    tmp_path: Path, mutation: str
) -> None:
    fixture = write_fixture(tmp_path)
    receipt = validate(fixture)
    provenance, manifest = write_analysis_outputs(fixture, receipt)
    rows = list(csv.DictReader(manifest.open()))
    if mutation == "missing_row":
        rows = rows[:-1]
    else:
        rows[-1]["sha256"] = "0" * 64
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sha256", "filename"))
        writer.writeheader()
        writer.writerows(rows)
    original_provenance = provenance.read_bytes()
    original_manifest = manifest.read_bytes()
    with pytest.raises(lineage.LineageError, match="manifest"):
        lineage.bind_analysis_provenance(
            receipt=fixture["receipt"], provenance=provenance, manifest=manifest
        )
    assert provenance.read_bytes() == original_provenance
    assert manifest.read_bytes() == original_manifest


def test_production_constants_match_retained_historical_evidence() -> None:
    assets = ROOT / "docs/science/assets/g_hi_full_history_production_2026-08-20"
    failure = assets / "failure_786189/remote_logs"
    completion = assets / "home_continuation_786326/completion/remote_logs"
    paths = {
        "parent_run_log": failure / "g_hi_full_history_production.out",
        "continuation_run_log": completion / "g_hi_full_history_home_continuation.out",
        "staging_manifest": completion / "home_continuation_staging_manifest.txt",
        "restart_report": completion / "restart_pair_validation_job.json",
        "canonical_sequence_report": completion / "canonical_sequence_validation.csv",
        "endpoint_report": completion / "endpoint_validation.json",
        "source_revisions": completion / "source_revisions.txt",
        "done_marker": completion / "DONE",
    }
    observed = {name: sha256(path) for name, path in paths.items()}
    assert observed == {
        name: expected for name, expected in lineage.EXPECTED_EVIDENCE_HASHES.items()
        if name in observed
    }
    rendered = assets / "rendered_config/G-HI/particles"
    assert {
        name: sha256(rendered / name)
        for name in lineage.EXPECTED_CONFIG_HASHES
        if name != "tabulated_cosmo_002031.csv"
    } == {
        name: expected
        for name, expected in lineage.EXPECTED_CONFIG_HASHES.items()
        if name != "tabulated_cosmo_002031.csv"
    }
    assert (
        lineage.EXPECTED_CONFIG_HASHES["tabulated_cosmo_002031.csv"]
        + "  rendered_g_hi_config/G-HI/particles/tabulated_cosmo_002031.csv"
    ) in (assets / "staged_inputs.sha256").read_text()


def test_flux_wrapper_orders_unaffected_cases_before_inherited_g_hi_gate() -> None:
    wrapper = (ROOT / "scripts/kunanyi/q031_flux_measurements.pbs").read_text()
    assert "q031_flux_measurements_2026-11-05_r6" in wrapper
    assert "module.validate_migration_dependencies" in wrapper
    assert "source_hashes(early) == source_hashes(late)" not in wrapper
    c_lo = wrapper.index('measure C-LO "$C_LO"')
    c_hi = wrapper.index('measure C-HI "$C_HI"')
    g_lo = wrapper.index('measure G-LO "$G_LO"', c_hi)
    lineage_gate = wrapper.index('python "$G_HI_LINEAGE_VALIDATOR" validate')
    g_hi = wrapper.index('measure G-HI "$G_HI_LATE"')
    bind = wrapper.index('python "$G_HI_LINEAGE_VALIDATOR" bind')
    assert c_lo < c_hi < g_lo < lineage_gate < g_hi < bind
    assert 'measure G-HI "$G_HI_LATE" tabulated_cosmo_002031.csv "$G_HI_EARLY/src"' in wrapper
    assert "cp " not in wrapper[lineage_gate:g_hi]
    assert "make " not in wrapper[lineage_gate:g_hi]
