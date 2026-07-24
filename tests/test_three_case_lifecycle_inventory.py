from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path("scripts/science/inventory_three_case_lifecycle.py")


def load_module():
    spec = importlib.util.spec_from_file_location("inventory_three_case_lifecycle", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_contracts(tmp_path: Path, root: Path, protected: list[dict[str, str]] | None = None) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    roots = tmp_path / "roots.csv"
    with roots.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "root_id",
                "root_path",
                "root_kind",
                "purpose",
                "expected_presence",
                "source_evidence",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "C-HI",
                "root_id": "r1",
                "root_path": str(root),
                "root_kind": "run",
                "purpose": "test run",
                "expected_presence": "true",
                "source_evidence": "synthetic test contract",
            }
        )
    protected_path = tmp_path / "protected.csv"
    rows = protected or []
    with protected_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "protection_class", "dependency", "source_evidence", "existing_sha256", "expected_timestep", "expected_time_code", "expected_time_myr", "expected_shape", "expected_datasets"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "expected_timestep": "", "expected_time_code": "", "expected_time_myr": "",
                "expected_shape": "", "expected_datasets": "", **row,
            })
    return roots, protected_path


def test_inventory_is_nonmutating_and_classifies_particles_candidates_and_compact(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    (root / "particles").mkdir(parents=True)
    (root / "particles" / "particles.0001.dbl").write_bytes(b"particle")
    (root / "data.0001.flt.h5").write_bytes(b"hdf5 placeholder")
    (root / "notes.txt").write_text("compact")
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    roots, protected = write_contracts(tmp_path, root)
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output)
    rows = list(csv.DictReader((output / "payload_inventory.csv").open()))
    by_name = {Path(row["path"]).name: row for row in rows}
    assert by_name["particles.0001.dbl"]["data_class"] == "HOLD_RADIO_UNRESOLVED"
    assert by_name["particles.0001.dbl"]["sha256_status"] == "held_particle"
    assert by_name["data.0001.flt.h5"]["data_class"] == "CANDIDATE_REVIEW"
    assert by_name["data.0001.flt.h5"]["sha256_status"] == "hashed"
    assert by_name["notes.txt"]["sha256_status"] == "hashed"
    assert by_name["notes.txt"]["identity_status"] == "stable"
    assert {path: path.read_bytes() for path in root.rglob("*") if path.is_file()} == before


def test_particles_parent_directory_does_not_make_every_file_a_particle(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    output_dir = root / "C-HI" / "particles" / "problem" / "outputs"
    output_dir.mkdir(parents=True)
    (output_dir / "data.0001.flt.h5").write_bytes(b"hdf5 placeholder")
    (output_dir / "particles.0001.dbl").write_bytes(b"particle")
    roots, protected = write_contracts(tmp_path, root)
    report = tmp_path / "reports"
    module.run_inventory(roots, protected, report)
    rows = {Path(row["path"]).name: row for row in csv.DictReader((report / "payload_inventory.csv").open())}
    assert rows["data.0001.flt.h5"]["data_class"] == "CANDIDATE_REVIEW"
    assert rows["particles.0001.dbl"]["data_class"] == "HOLD_RADIO_UNRESOLVED"


def test_incomplete_large_protected_hdf5_contract_falls_back_to_full_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "endpoint.h5"
    source.write_bytes(b"protected source")
    roots, protected = write_contracts(
        tmp_path,
        root,
        [{"path": str(source), "protection_class": "KEEP", "dependency": "endpoint", "source_evidence": "manifest", "existing_sha256": "", "expected_timestep": "Timestep_2"}],
    )
    monkeypatch.setattr(module, "PROTECTED_HASH_MAX_BYTES", 1)

    report = tmp_path / "reports"
    module.run_inventory(roots, protected, report)
    row = next(csv.DictReader((report / "payload_inventory.csv").open()))
    assert row["hash_policy"] == "full_sha256"
    assert row["sha256_status"] == "hashed"
    assert row["sha256"]
    assert row["identity_status"] == "stable"


def test_complete_large_protected_hdf5_contract_uses_identity_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "endpoint.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_2")
        group.attrs["Time"] = 12.5
        for name in ("rho", "prs", "tr1", "vx1", "vx2", "vx3"):
            group.create_dataset(name, shape=(2, 3), dtype="f8")
    roots, protected = write_contracts(tmp_path, root, [{
        "path": str(source), "protection_class": "KEEP", "dependency": "endpoint",
        "source_evidence": "manifest", "existing_sha256": "",
        "expected_timestep": "Timestep_2", "expected_time_code": "12.5",
        "expected_shape": "2x3", "expected_datasets": "rho;prs;tr1;vx1;vx2;vx3",
    }])
    monkeypatch.setattr(module, "PROTECTED_HASH_MAX_BYTES", 1)
    monkeypatch.setattr(module, "_sha256_file", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("identity-only HDF5 must not be hashed")))
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output, read_hdf5_metadata=True)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["hash_policy"] == "protected_stable_identity"
    assert row["sha256_status"] == "protected_identity_only"
    assert row["hdf5_status"] == "read"


def test_protected_path_keeps_class_and_verifies_existing_hash(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "endpoint.h5"
    source.write_bytes(b"trusted")
    digest = hashlib.sha256(b"trusted").hexdigest()
    roots, protected = write_contracts(
        tmp_path,
        root,
        [{"path": str(source), "protection_class": "KEEP", "dependency": "endpoint", "source_evidence": "manifest", "existing_sha256": digest}],
    )
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["data_class"] == "KEEP"
    assert row["contract_protection"] == "PROTECTED"
    assert row["sha256_status"] == "verified"
    assert row["sha256"] == digest


def test_symlink_is_not_followed_and_is_held(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("outside")
    link = root / "link.txt"
    link.symlink_to(target)
    roots, protected = write_contracts(tmp_path, root)
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["file_type"] == "symlink"
    assert row["sha256"] == ""
    assert row["sha256_status"] == "held_symlink"
    assert row["link_target"] == str(target)
    assert row["symlink_target_status"] == "outside_allowlist"
    assert row["data_class"] == "HOLD_AMBIGUOUS"


def test_missing_protected_path_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    missing = root / "endpoint.h5"
    roots, protected = write_contracts(
        tmp_path,
        root,
        [{"path": str(missing), "protection_class": "KEEP", "dependency": "endpoint", "source_evidence": "manifest", "existing_sha256": ""}],
    )
    with pytest.raises(module.InventoryError, match="protected path missing"):
        module.run_inventory(roots, protected, tmp_path / "reports")


def test_protected_symlink_target_outside_allowlist_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    outside = tmp_path / "outside.h5"
    outside.write_bytes(b"outside")
    link = root / "endpoint.h5"
    link.symlink_to(outside)
    roots, protected = write_contracts(
        tmp_path,
        root,
        [{"path": str(link), "protection_class": "KEEP", "dependency": "endpoint", "source_evidence": "manifest", "existing_sha256": ""}],
    )
    with pytest.raises(module.InventoryError, match="protected symlink target"):
        module.run_inventory(roots, protected, tmp_path / "reports")


def test_nested_intermediate_symlink_escape_is_held(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "payload.txt").write_text("outside")
    nested = root / "nested"
    nested.symlink_to(outside, target_is_directory=True)
    roots, protected = write_contracts(tmp_path, root)
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["file_type"] == "symlink"
    assert row["symlink_target_status"] == "outside_allowlist"
    assert row["data_class"] == "HOLD_AMBIGUOUS"


def test_rejects_overlapping_roots_and_output_inside_root(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    nested = root / "nested"
    nested.mkdir(parents=True)
    roots = tmp_path / "roots.csv"
    roots.write_text(
        "case_id,root_id,root_path,root_kind,purpose,expected_presence,source_evidence\n"
        f"C-HI,r1,{root},run,test,true,synthetic test contract\n"
        f"C-HI,r2,{nested},run,test,true,synthetic test contract\n"
    )
    marker = root / "marker.txt"
    marker.write_text("marker")
    protected = tmp_path / "protected.csv"
    protected.write_text(
        "path,protection_class,dependency,source_evidence,existing_sha256\n"
        f"{marker},KEEP,test,test,\n"
    )
    with pytest.raises(module.InventoryError, match="overlapping"):
        module.run_inventory(roots, protected, tmp_path / "out")
    roots_single, protected_single = write_contracts(tmp_path / "single", root)
    with pytest.raises(module.InventoryError, match="inside inventoried root"):
        module.run_inventory(roots_single, protected_single, root / "reports")


def test_rejects_protected_path_outside_allowlist(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    roots, protected = write_contracts(
        tmp_path,
        root,
        [{"path": str(outside), "protection_class": "KEEP", "dependency": "x", "source_evidence": "x", "existing_sha256": ""}],
    )
    with pytest.raises(module.InventoryError, match="outside allowlisted"):
        module.run_inventory(roots, protected, tmp_path / "out")


def test_rejects_unexpected_special_file_type(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    fifo = root / "unexpected.fifo"
    try:
        fifo.mkfifo()
    except (AttributeError, OSError):
        pytest.skip("FIFO creation unavailable on this platform")
    roots, protected = write_contracts(tmp_path, root)
    with pytest.raises(module.InventoryError, match="unexpected path type"):
        module.run_inventory(roots, protected, tmp_path / "out")


def test_changed_file_during_hash_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "data.bin"
    source.write_bytes(b"before")
    roots, protected = write_contracts(tmp_path, root)
    original = module._sha256_file

    def mutate(path: Path, before=None):
        path.write_bytes(b"changed")
        return original(path, before=before)

    monkeypatch.setattr(module, "_sha256_file", mutate)
    with pytest.raises(module.InventoryError, match="changed during hash"):
        module.run_inventory(roots, protected, tmp_path / "out")


def test_deterministic_reports_and_manifest_digest(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    (root / "b.txt").write_text("b")
    (root / "a.txt").write_text("a")
    roots, protected = write_contracts(tmp_path, root)
    first = tmp_path / "first"
    second = tmp_path / "second"
    meta1 = module.run_inventory(roots, protected, first)
    meta2 = module.run_inventory(roots, protected, second)
    assert meta1["manifest_digest_sha256"] == meta2["manifest_digest_sha256"]
    assert (first / "payload_inventory.csv").read_bytes() == (second / "payload_inventory.csv").read_bytes()
    assert json.loads((first / "inventory_metadata.json").read_text())["read_only"] is True


def test_contract_metadata_binding_and_duplicate_output_reservation(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    (root / "a.txt").write_text("a")
    roots, protected = write_contracts(tmp_path, root)
    metadata = tmp_path / "contract_metadata.json"
    metadata.write_text(json.dumps({"contract_files": [roots.name, protected.name], "contract_digest_sha256": module._contract_digest(roots, protected)}))
    report = tmp_path / "reports"
    module.run_inventory(roots, protected, report, contract_metadata=metadata)
    with pytest.raises(module.InventoryError, match="reservation"):
        module.run_inventory(roots, protected, report, contract_metadata=metadata)
    metadata.write_text(json.dumps({"contract_files": [roots.name, protected.name], "contract_digest_sha256": "0" * 64}))
    with pytest.raises(module.InventoryError, match="contract digest mismatch"):
        module.run_inventory(roots, protected, tmp_path / "reports2", contract_metadata=metadata)


def test_inventory_wide_entry_drift_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    (root / "a.txt").write_text("a")
    roots, protected = write_contracts(tmp_path, root)
    original = module._walk_root

    def drift(*args, **kwargs):
        rows = original(*args, **kwargs)
        (root / "late.txt").write_text("drift")
        return rows

    monkeypatch.setattr(module, "_walk_root", drift)
    with pytest.raises(module.InventoryError, match="identity drift"):
        module.run_inventory(roots, protected, tmp_path / "reports")


def test_snapshot_signature_ignores_directory_size_but_retains_file_identity() -> None:
    module = load_module()
    common = {
        "st_dev": 63,
        "st_ino": 1001,
        "st_mtime_ns": 123456789,
    }
    directory_before = SimpleNamespace(
        **common, st_size=4096, st_mode=stat.S_IFDIR | 0o755
    )
    directory_after = SimpleNamespace(
        **common, st_size=36813, st_mode=stat.S_IFDIR | 0o755
    )
    file_before = SimpleNamespace(
        **common, st_size=4096, st_mode=stat.S_IFREG | 0o644
    )
    assert module._snapshot_signature(directory_before) == module._snapshot_signature(directory_after)
    file_variants = (
        SimpleNamespace(**common, st_size=36813, st_mode=stat.S_IFREG | 0o644),
        SimpleNamespace(**{**common, "st_ino": 1002}, st_size=4096, st_mode=stat.S_IFREG | 0o644),
        SimpleNamespace(**{**common, "st_mtime_ns": 123456790}, st_size=4096, st_mode=stat.S_IFREG | 0o644),
        SimpleNamespace(**common, st_size=4096, st_mode=stat.S_IFREG | 0o600),
        SimpleNamespace(**common, st_size=4096, st_mode=stat.S_IFLNK | 0o777),
    )
    for variant in file_variants:
        assert module._snapshot_signature(file_before) != module._snapshot_signature(variant)


def test_transient_directory_entry_mutation_with_mtime_change_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    root_path = tmp_path / "run"
    root_path.mkdir()
    (root_path / "stable.txt").write_text("stable")
    root = {"root_id": "r1", "root_path": str(root_path), "exists": True}
    before = module._tree_snapshot(root)
    transient = root_path / "transient.txt"
    transient.write_text("temporary")
    transient.unlink()
    after = module._tree_snapshot(root)

    with pytest.raises(module.InventoryError, match="identity drift"):
        module._assert_snapshot_stable(before, after, root)


def test_nested_rename_during_inventory_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    root = tmp_path / "run"
    nested = root / "nested"
    nested.mkdir(parents=True)
    source = nested / "before.txt"
    source.write_text("stable")
    roots, protected = write_contracts(tmp_path, root)
    original = module._walk_root

    def rename(*args, **kwargs):
        rows = original(*args, **kwargs)
        source.rename(nested / "after.txt")
        return rows

    monkeypatch.setattr(module, "_walk_root", rename)
    with pytest.raises(module.InventoryError, match="identity drift"):
        module.run_inventory(roots, protected, tmp_path / "reports")


def test_drift_diagnostic_records_before_and_after_signatures() -> None:
    module = load_module()
    root = {"root_id": "r1"}
    before = {"/tmp/example": (1, 2, 3, 4)}
    after = {"/tmp/example": (1, 2, 5, 4)}

    with pytest.raises(module.InventoryError, match=r"before=.*after="):
        module._assert_snapshot_stable(before, after, root)


def test_unhashed_particle_mutation_during_inspection_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    particle = root / "particles.0001.dbl"
    particle.write_bytes(b"before")
    roots, protected = write_contracts(tmp_path, root)
    original = module._is_particle

    def mutate(path: Path) -> bool:
        result = original(path)
        if result:
            path.write_bytes(b"changed")
        return result

    monkeypatch.setattr(module, "_is_particle", mutate)
    with pytest.raises(module.InventoryError, match="path changed during inventory"):
        module.run_inventory(roots, protected, tmp_path / "reports")


def test_identity_only_hdf5_mutation_during_metadata_read_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "endpoint.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_2")
        group.attrs["Time"] = 12.5
        for name in ("rho", "prs", "tr1", "vx1", "vx2", "vx3"):
            group.create_dataset(name, shape=(2, 3), dtype="f8")
    roots, protected = write_contracts(tmp_path, root, [{
        "path": str(source), "protection_class": "KEEP", "dependency": "endpoint",
        "source_evidence": "manifest", "existing_sha256": "",
        "expected_timestep": "Timestep_2", "expected_time_code": "12.5",
        "expected_shape": "2x3", "expected_datasets": "rho;prs;tr1;vx1;vx2;vx3",
    }])
    monkeypatch.setattr(module, "PROTECTED_HASH_MAX_BYTES", 1)
    original = module._hdf5_metadata

    def mutate(path: Path, expected=None):
        fields = original(path, expected)
        path.touch()
        return fields

    monkeypatch.setattr(module, "_hdf5_metadata", mutate)
    with pytest.raises(module.InventoryError, match="path changed during inventory"):
        module.run_inventory(roots, protected, tmp_path / "reports", read_hdf5_metadata=True)


def test_optional_root_appearing_during_inventory_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    roots = tmp_path / "roots.csv"
    roots.write_text(
        "case_id,root_id,root_path,root_kind,purpose,expected_presence,source_evidence\n"
        f"C-HI,r1,{root},run,test,true,synthetic\n"
        f"C-HI,r2,{tmp_path / 'optional'},run,test,false,synthetic\n"
    )
    protected = tmp_path / "protected.csv"
    protected.write_text("path,protection_class,dependency,source_evidence,existing_sha256\n")
    original = module._walk_root
    appeared = False

    def appear(*args, **kwargs):
        nonlocal appeared
        rows = original(*args, **kwargs)
        optional = tmp_path / "optional"
        if not appeared:
            optional.mkdir()
            (optional / "late.txt").write_text("late")
            appeared = True
        return rows

    monkeypatch.setattr(module, "_walk_root", appear)
    with pytest.raises(module.InventoryError, match="identity drift"):
        module.run_inventory(roots, protected, tmp_path / "reports")


def test_protected_hdf5_metadata_contract_is_validated(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "data.0002.dbl.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_2")
        group.attrs["Time"] = 3065.934704693023
        for name in ("rho", "prs", "tr1", "vx1", "vx2", "vx3"):
            group.create_dataset(name, shape=(2, 3), dtype="f8")
    roots, protected = write_contracts(tmp_path, root, [{
        "path": str(source), "protection_class": "KEEP", "dependency": "restart",
        "source_evidence": "manifest", "existing_sha256": "",
        "expected_timestep": "Timestep_2", "expected_time_code": "3065.934704693023",
        "expected_time_myr": "", "expected_shape": "2x3",
        "expected_datasets": "rho;prs;tr1;vx1;vx2;vx3",
    }])
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output, read_hdf5_metadata=True)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["hdf5_timestep"] == "Timestep_2"
    assert row["hdf5_status"] == "read"


def test_protected_hdf5_metadata_contract_accepts_pluto_vars_layout(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "data.0002.dbl.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_2")
        group.attrs["Time"] = 3065.934704693023
        variables = group.create_group("vars")
        for name in ("rho", "prs", "tr1", "vx1", "vx2", "vx3"):
            variables.create_dataset(name, shape=(2, 3), dtype="f8")
    roots, protected = write_contracts(tmp_path, root, [{
        "path": str(source), "protection_class": "KEEP", "dependency": "restart",
        "source_evidence": "manifest", "existing_sha256": "",
        "expected_timestep": "Timestep_2", "expected_time_code": "3065.934704693023",
        "expected_time_myr": "", "expected_shape": "2x3",
        "expected_datasets": "rho;prs;tr1;vx1;vx2;vx3",
    }])
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output, read_hdf5_metadata=True)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["hdf5_status"] == "read"
    assert "Timestep_2/vars/rho" in row["hdf5_datasets"]


def test_protected_hdf5_metadata_contract_rejects_ambiguous_dataset_basename(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "data.0002.dbl.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_2")
        group.attrs["Time"] = 3065.934704693023
        group.create_dataset("rho", shape=(2, 3), dtype="f8")
        group.create_group("vars").create_dataset("rho", shape=(2, 3), dtype="f8")
    roots, protected = write_contracts(tmp_path, root, [{
        "path": str(source), "protection_class": "KEEP", "dependency": "restart",
        "source_evidence": "manifest", "existing_sha256": "",
        "expected_timestep": "Timestep_2", "expected_time_code": "3065.934704693023",
        "expected_time_myr": "", "expected_shape": "2x3", "expected_datasets": "rho",
    }])
    with pytest.raises(module.InventoryError, match="ambiguous HDF5 dataset basename"):
        module.run_inventory(roots, protected, tmp_path / "reports", read_hdf5_metadata=True)


def test_protected_hdf5_metadata_mismatch_fails_closed(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "data.0002.dbl.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_2")
        group.attrs["Time"] = 99.0
        group.create_dataset("rho", shape=(2, 3), dtype="f8")
    roots, protected = write_contracts(tmp_path, root, [{
        "path": str(source), "protection_class": "KEEP", "dependency": "restart",
        "source_evidence": "manifest", "existing_sha256": "",
        "expected_timestep": "Timestep_2", "expected_time_code": "3065.934704693023",
        "expected_time_myr": "", "expected_shape": "2x3", "expected_datasets": "rho",
    }])
    with pytest.raises(module.InventoryError, match="required HDF5 time mismatch"):
        module.run_inventory(roots, protected, tmp_path / "reports", read_hdf5_metadata=True)


def test_hdf5_metadata_is_read_when_requested(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    root = tmp_path / "run"
    root.mkdir()
    source = root / "data.0001.flt.h5"
    with h5py.File(source, "w") as handle:
        group = handle.create_group("Timestep_1")
        group.create_dataset("rho", data=[1, 2])
        handle.attrs["time_code"] = 12.5
    roots, protected = write_contracts(tmp_path, root)
    output = tmp_path / "reports"
    module.run_inventory(roots, protected, output, read_hdf5_metadata=True)
    row = next(csv.DictReader((output / "payload_inventory.csv").open()))
    assert row["hdf5_status"] == "read"
    assert row["hdf5_timestep"] == "Timestep_1"
    assert "Timestep_1/rho" in row["hdf5_datasets"]
