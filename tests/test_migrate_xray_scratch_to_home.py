from __future__ import annotations

import importlib.util
import errno
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "kunanyi" / "migrate_xray_scratch_to_home.py"
SPEC = importlib.util.spec_from_file_location("migrate_xray_scratch_to_home", SCRIPT)
assert SPEC and SPEC.loader
migrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migrate)


class MigrationTests(unittest.TestCase):
    def test_advertised_unsupported_nfs_acl_is_recorded_not_restored(self) -> None:
        with mock.patch.object(migrate.os, "listxattr", return_value=["system.nfs4_acl"], create=True), \
             mock.patch.object(migrate.os, "getxattr", side_effect=OSError(errno.EOPNOTSUPP, "unsupported"), create=True), \
             mock.patch.object(migrate.os, "removexattr", create=True), \
             mock.patch.object(migrate.os, "setxattr", create=True) as setter:
            observed = migrate._xattrs(Path("/unused"))
            self.assertEqual(observed, {"system.nfs4_acl": None})
            migrate._restore_xattrs(Path("/unused"), observed)
            setter.assert_not_called()

    def test_private_archive_policy_is_required_and_archive_is_private(self) -> None:
        source = self.root / "source"
        source.mkdir()
        plan_path = self.plan([(source, self.archive / "unit")])
        loaded = migrate._load_plan(plan_path)
        self.assertEqual(loaded["metadata_policy"], "private_archive")
        os.chmod(self.archive, 0o750)
        with self.assertRaises(migrate.MigrationError):
            migrate._load_plan(plan_path)

    def test_metadata_policy_key_is_required(self) -> None:
        source = self.root / "source"
        source.mkdir()
        value = {"archive_root": str(self.archive), "authority": "test",
                 "units": [{"source": str(source), "destination": str(self.archive / "unit")}]}
        path = self.root / "missing-policy.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(migrate.MigrationError, "metadata_policy"):
            migrate._load_plan(path)

    def test_source_policy_rejects_readable_acl_security_xattr(self) -> None:
        source = self.root / "source"
        source.mkdir()
        path = source / "data"
        path.write_bytes(b"data")
        entries = migrate._inventory(source)
        entries["data"]["xattrs"] = {"security.test": "cmVqZWN0"}
        with self.assertRaisesRegex(migrate.MigrationError, "ACL/security xattr"):
            migrate._validate_source_policy(entries, source)

    def test_source_policy_rejects_non_owner_readable_file(self) -> None:
        source = self.root / "source"
        source.mkdir()
        path = source / "data"
        path.write_bytes(b"data")
        os.chmod(path, 0o200)
        entries = migrate._inventory(source)
        with self.assertRaisesRegex(migrate.MigrationError, "owner-readable"):
            migrate._validate_source_policy(entries, source)

    def test_private_archive_normalizes_modes_gid_and_receipts(self) -> None:
        source = self.root / "source"
        nested = source / "nested"
        nested.mkdir(parents=True)
        os.chmod(nested, 0o2775)
        for name, mode in (("rw", 0o644), ("exec", 0o755), ("readonly", 0o444)):
            path = nested / name
            path.write_bytes(name.encode())
            os.chmod(path, mode)
        os.symlink("rw", nested / "relative")
        destination = self.archive / "unit"
        result = self.invoke(self.plan([(source, destination)]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((destination.stat().st_mode & 0o777), 0o700)
        self.assertEqual((destination / "nested").stat().st_mode & 0o777, 0o700)
        self.assertEqual((destination / "nested/rw").stat().st_mode & 0o777, 0o600)
        self.assertEqual((destination / "nested/exec").stat().st_mode & 0o777, 0o700)
        self.assertEqual((destination / "nested/readonly").stat().st_mode & 0o777, 0o400)
        link_stat = os.lstat(destination / "nested/relative")
        self.assertEqual(link_stat.st_uid, os.geteuid())
        self.assertEqual(link_stat.st_gid, os.getgid())
        receipt = next((self.state).glob("unit-*/policy-receipt.json"))
        policy = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(policy["metadata_policy"], "private_archive")
        self.assertEqual(policy["destination_gid"], os.getgid())

    def test_descriptor_chmod_path_is_portable_when_path_chmod_is_unavailable(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"data")
        plan = migrate._load_plan(self.plan([(source, self.archive / "unit")]))
        with mock.patch.object(migrate.os, "chmod", side_effect=NotImplementedError):
            migrate.Migration(plan, self.state).execute()
        self.assertEqual((self.archive / "unit").stat().st_mode & 0o777, 0o700)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "archive"
        self.archive.mkdir(mode=0o700)
        os.chmod(self.archive, 0o700)
        self.state = self.root / "state"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def plan(self, units: list[tuple[Path, Path]]) -> Path:
        value = {
            "archive_root": str(self.archive),
            "authority": "test-authority",
            "metadata_policy": "private_archive",
            "units": [{"source": str(source), "destination": str(destination)}
                       for source, destination in units],
        }
        path = self.root / "plan.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def invoke(self, plan: Path, *, execute: bool = True) -> subprocess.CompletedProcess[str]:
        command = ["python3", str(SCRIPT), "--plan", str(plan), "--state-dir", str(self.state)]
        if execute:
            command.append("--execute")
        return subprocess.run(command, text=True, capture_output=True)

    def test_success_maps_cross_unit_absolute_link_and_preserves_relative_link(self) -> None:
        source_one = self.root / "source-one"
        source_two = self.root / "source-two"
        source_one.mkdir()
        source_two.mkdir()
        (source_one / "payload").write_bytes(b"payload")
        (source_two / "inside").write_bytes(b"inside")
        os.symlink(source_one / "payload", source_two / "cross-unit")
        os.symlink("inside", source_two / "relative")
        destination_one = self.archive / "one"
        destination_two = self.archive / "two"
        result = self.invoke(self.plan([(source_one, destination_one), (source_two, destination_two)]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(source_one.is_symlink())
        self.assertTrue(source_two.is_symlink())
        self.assertEqual(os.readlink(destination_two / "cross-unit"), str(destination_one / "payload"))
        self.assertEqual(os.readlink(destination_two / "relative"), "inside")
        self.assertFalse((self.root / ".source-one.xray-migration-").exists())
        self.assertTrue((self.state / "verified-manifest.json").exists())

    def test_directory_recursive_accounting_change_is_not_payload_mutation(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"payload")
        plan = migrate._load_plan(self.plan([(source, self.archive / "unit")]))
        unit = migrate.Unit(migrate.Migration(plan, self.state), 0, plan["units"][0])
        entries = migrate._inventory(source)
        entries["."]["signature"]["size"] += 1024
        unit.check_source_unchanged(entries)
        entries["data"]["signature"]["size"] += 1
        with self.assertRaises(migrate.MigrationError):
            unit.check_source_unchanged(entries)

    def test_destination_collision_fails_before_copy(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_text("data", encoding="utf-8")
        destination = self.archive / "unit"
        destination.mkdir()
        (destination / "existing").write_text("keep", encoding="utf-8")
        result = self.invoke(self.plan([(source, destination)]))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(source.is_dir())
        self.assertEqual((destination / "existing").read_text(encoding="utf-8"), "keep")

    def test_destination_content_corruption_fails_closed(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"correct")
        destination = self.archive / "unit"
        plan = self.plan([(source, destination)])
        original_run = migrate.subprocess.run

        def corrupting_run(command, *args, **kwargs):
            result = original_run(command, *args, **kwargs)
            (destination / "data").write_bytes(b"corrupt")
            return result

        with mock.patch.object(migrate.subprocess, "run", side_effect=corrupting_run):
            with self.assertRaises(migrate.MigrationError):
                migrate.Migration(migrate._load_plan(plan), self.state).execute()
        self.assertTrue(source.is_dir())
        self.assertTrue(destination.exists())

    def test_source_mutation_fails_before_promotion(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"before")
        destination = self.archive / "unit"
        plan = self.plan([(source, destination)])
        original_run = migrate.subprocess.run

        def mutating_run(command, *args, **kwargs):
            result = original_run(command, *args, **kwargs)
            (source / "data").write_bytes(b"after")
            return result

        with mock.patch.object(migrate.subprocess, "run", side_effect=mutating_run):
            with self.assertRaises(migrate.MigrationError):
                migrate.Migration(migrate._load_plan(plan), self.state).execute()
        self.assertTrue(source.is_dir())
        self.assertFalse(source.is_symlink())

    def test_special_file_is_rejected(self) -> None:
        source = self.root / "source"
        source.mkdir()
        os.mkfifo(source / "named-pipe")
        plan = self.plan([(source, self.archive / "unit")])
        result = self.invoke(plan, execute=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("special file", result.stderr)

    def test_relative_link_escaping_planned_unit_fails_context_check(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (self.root / "outside").write_text("outside", encoding="utf-8")
        os.symlink("../outside", source / "escaping")
        plan = self.plan([(source, self.archive / "unit")])
        result = self.invoke(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink context", result.stderr)
        self.assertTrue(source.is_dir())

    def test_resume_after_rename_before_symlink(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"data")
        destination = self.archive / "unit"
        plan = self.plan([(source, destination)])
        original_symlink = migrate.os.symlink

        def fail_promotion(target, link_name, *args, **kwargs):
            if Path(link_name) == source:
                raise RuntimeError("simulated crash after rename")
            return original_symlink(target, link_name, *args, **kwargs)

        with mock.patch.object(migrate.os, "symlink", side_effect=fail_promotion):
            with self.assertRaises(RuntimeError):
                migrate.Migration(migrate._load_plan(plan), self.state).execute()
        self.assertFalse(source.exists())
        self.assertTrue(any(path.name.endswith(".tombstone") for path in source.parent.iterdir()))
        result = self.invoke(plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(source.is_symlink())

    def test_resume_partial_cleanup_uses_deleted_ledger(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"data")
        destination = self.archive / "unit"
        plan = self.plan([(source, destination)])
        original_unlink = migrate.os.unlink
        should_fail = {"value": True}

        def fail_first_cleanup(path, *args, **kwargs):
            if should_fail["value"] and ".xray-migration-" in str(path):
                should_fail["value"] = False
                original_unlink(path, *args, **kwargs)
                raise OSError("simulated interrupted cleanup")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(migrate.os, "unlink", side_effect=fail_first_cleanup):
            with self.assertRaises(migrate.MigrationError):
                migrate.Migration(migrate._load_plan(plan), self.state).execute()
        result = self.invoke(plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(source.is_symlink())
        self.assertFalse(any(path.name.endswith(".tombstone") for path in source.parent.iterdir()))

    def test_unknown_tombstone_file_stops_cleanup(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"data")
        destination = self.archive / "unit"
        plan = self.plan([(source, destination)])
        original_unlink = migrate.os.unlink
        should_fail = {"value": True}

        def stop_cleanup(path, *args, **kwargs):
            if should_fail["value"] and ".xray-migration-" in str(path):
                should_fail["value"] = False
                raise OSError("pause before cleanup")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(migrate.os, "unlink", side_effect=stop_cleanup):
            with self.assertRaises(migrate.MigrationError):
                migrate.Migration(migrate._load_plan(plan), self.state).execute()
        tombstone = next(path for path in source.parent.iterdir() if path.name.endswith(".tombstone"))
        (tombstone / "unknown").write_text("must stop", encoding="utf-8")
        result = self.invoke(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown tombstone", result.stderr)
        self.assertTrue(source.is_symlink())
        self.assertTrue((tombstone / "unknown").exists())


    def test_nested_mapped_link_preserves_parent_metadata(self) -> None:
        first = self.root / "first"
        second = self.root / "second"
        first.mkdir()
        (first / "data").write_bytes(b"payload")
        nested = second / "problem" / "outputs"
        nested.mkdir(parents=True)
        os.symlink(first / "data", nested / "linked")
        stamp = nested.stat().st_mtime_ns
        result = self.invoke(self.plan([(first, self.archive / "first"),
                                      (second, self.archive / "second")]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(nested.stat().st_mtime_ns, stamp)
        self.assertEqual((nested / "linked").read_bytes(), b"payload")

    def test_completed_unit_missing_payload_fails_resume(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"payload")
        destination = self.archive / "unit"
        plan = self.plan([(source, destination)])
        self.assertEqual(self.invoke(plan).returncode, 0)
        (destination / "data").unlink()
        result = self.invoke(plan)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("destination tree differs", result.stderr)

    def test_resume_after_root_rmdir_before_ledger(self) -> None:
        source = self.root / "source"
        source.mkdir()
        (source / "data").write_bytes(b"payload")
        plan = self.plan([(source, self.archive / "unit")])
        original_rmdir = migrate.os.rmdir

        def interrupt_after_rmdir(path, *args, **kwargs):
            original_rmdir(path, *args, **kwargs)
            if str(path).endswith(".tombstone"):
                raise OSError("simulated crash after root rmdir")

        with mock.patch.object(migrate.os, "rmdir", side_effect=interrupt_after_rmdir):
            with self.assertRaises(migrate.MigrationError):
                migrate.Migration(migrate._load_plan(plan), self.state).execute()
        result = self.invoke(plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((source / "data").read_bytes(), b"payload")


if __name__ == "__main__":
    unittest.main()
