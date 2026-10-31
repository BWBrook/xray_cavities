from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/kunanyi/resume_xray_migration_device_transition.py"
SPEC = importlib.util.spec_from_file_location("resume_xray_migration_device_transition", SCRIPT)
assert SPEC and SPEC.loader
transition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transition)
frozen = transition.frozen


class DeviceTransitionTests(unittest.TestCase):
    def test_findmnt_raw_parser_requires_one_four_field_record(self) -> None:
        observed = transition._parse_findmnt_output(
            "<private-ip>:/hpc-kunanyi/scratch/bwbrook /scratch/bwbrook nfs4 /\n",
            Path("/scratch/bwbrook/example"),
        )
        self.assertEqual(observed, transition.SCRATCH_MOUNT)
        for invalid in ("", "one two three\n", "one two three four\nfive six seven eight\n"):
            with self.subTest(output=invalid):
                with self.assertRaises(transition.TransitionError):
                    transition._parse_findmnt_output(invalid, Path("/invalid"))

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.destination = self.root / "archive/unit"
        self.source.mkdir()
        (self.source / "a.bin").write_bytes(b"alpha")
        (self.source / "b.bin").write_bytes(b"beta")
        os.symlink("a.bin", self.source / "relative-link")
        self.destination.parent.mkdir(mode=0o700)
        shutil.copytree(self.source, self.destination, symlinks=True)
        self.state = self.root / "state"
        self.inspection = self.root / "source-inspection.json"
        self.inspection.write_text('{"scope":"test"}\n', encoding="utf-8")
        self.evidence = self.root / "transition-evidence"

        plan_unit = {"source": str(self.source), "destination": str(self.destination)}
        units = [{"source": f"/unused/source-{index}", "destination": f"/unused/dest-{index}"}
                 for index in range(8)] + [plan_unit]
        self.plan = {
            "schema": frozen.SCHEMA,
            "archive_root": str(self.destination.parent),
            "authority": "test",
            "metadata_policy": frozen.METADATA_POLICY,
            "units": units,
        }
        self.manager = frozen.Migration(self.plan, self.state)
        self.unit_id = frozen._unit_id(plan_unit)
        current = frozen._inventory(self.source)
        devices = {entry["signature"]["dev"] for entry in current.values()}
        self.assertEqual(len(devices), 1)
        self.current_device = devices.pop()
        self.old_device = self.current_device + 1
        entries = copy.deepcopy(current)
        for entry in entries.values():
            entry["signature"]["dev"] = self.old_device
        manifest = frozen._manifest_value(plan_unit, entries)
        manifest.update({"plan_hash": self.manager.plan_hash, "unit_id": self.unit_id})
        unit_dir = self.state / f"unit-{self.unit_id}"
        frozen._atomic_json(unit_dir / "manifest.json", manifest)

        self.patches = [
            mock.patch.object(transition, "UNIT_ID", self.unit_id),
            mock.patch.object(transition, "OLD_DEVICE_FROM_MANIFEST", self.old_device),
            mock.patch.object(transition, "CURRENT_DEVICE", self.current_device),
            mock.patch.object(transition, "EXPECTED_ENTRIES", len(entries)),
            mock.patch.object(transition, "INSPECTION", self.inspection),
            mock.patch.object(transition, "EVIDENCE", self.evidence),
            mock.patch.object(transition, "RECEIPT", self.evidence / "transition-receipt.json"),
            mock.patch.object(
                transition,
                "_require_mounts",
                return_value={"scratch": transition.SCRATCH_MOUNT, "home": transition.HOME_MOUNT},
            ),
        ]
        for patch in self.patches:
            patch.start()
        self.unit = transition.ReboundDeviceUnit(self.manager, transition.UNIT_INDEX, plan_unit)
        self.unit.set_status("copied", entries=len(entries) - 1,
                             bytes=self.unit.bytes(entries))

    def tearDown(self) -> None:
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def prepared(self) -> dict:
        return self.unit.prepare_manifest(self.unit.status())

    def test_uniform_device_rebind_forces_hash_and_ignores_old_receipts(self) -> None:
        manifest = self.prepared()
        first_file = "a.bin"
        self.unit.ledger(
            "file_verified",
            path=first_file,
            source_signature=frozen._sig((self.source / first_file).lstat()),
            destination_signature=frozen._sig((self.destination / first_file).lstat()),
            sha256="old-receipt-must-not-be-used",
        )
        original = frozen._hash_regular
        with mock.patch.object(frozen, "_hash_regular", wraps=original) as hasher:
            self.unit.verify_complete(manifest)
        self.assertEqual(hasher.call_count, 4)
        records = frozen._read_ledger(self.unit.ledger_path)
        new_records = [record for record in records
                       if record.get("verification_epoch") == transition.VERIFICATION_EPOCH]
        self.assertEqual({record["path"] for record in new_records}, {"a.bin", "b.bin"})
        self.assertTrue(all(record["transition_receipt_sha256"] == self.unit.transition_receipt_sha256
                            for record in new_records))

    def test_new_epoch_receipts_resume_without_using_original_epoch(self) -> None:
        manifest = self.prepared()
        original = frozen._hash_regular
        calls = {"count": 0}

        def interrupt_on_second_file(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 3:
                raise RuntimeError("simulated walltime stop")
            return original(*args, **kwargs)

        with mock.patch.object(frozen, "_hash_regular", side_effect=interrupt_on_second_file):
            with self.assertRaisesRegex(RuntimeError, "walltime"):
                self.unit.verify_complete(manifest)
        resumed_manifest = self.prepared()
        with mock.patch.object(frozen, "_hash_regular", wraps=original) as resumed_hasher:
            self.unit.verify_complete(resumed_manifest)
        self.assertEqual(resumed_hasher.call_count, 2)

    def test_transition_rejects_every_non_device_change(self) -> None:
        manifest = self.unit.manifest()["entries"]
        actual = frozen._inventory(self.source)
        transition._validate_transition(manifest, actual)

        mutations = []
        changed_inode = copy.deepcopy(actual)
        changed_inode["a.bin"]["signature"]["ino"] += 1
        mutations.append(changed_inode)
        changed_time = copy.deepcopy(actual)
        changed_time["a.bin"]["signature"]["ctime_ns"] += 1
        mutations.append(changed_time)
        changed_mode = copy.deepcopy(actual)
        changed_mode["a.bin"]["signature"]["mode"] ^= 0o100
        mutations.append(changed_mode)
        changed_xattr = copy.deepcopy(actual)
        changed_xattr["a.bin"]["xattrs"] = {"security.test": "dGFtcGVy"}
        mutations.append(changed_xattr)
        changed_link = copy.deepcopy(actual)
        changed_link["relative-link"]["linktarget"] = "b.bin"
        mutations.append(changed_link)
        mixed_device = copy.deepcopy(actual)
        mixed_device["b.bin"]["signature"]["dev"] += 1
        mutations.append(mixed_device)
        missing = copy.deepcopy(actual)
        missing.pop("b.bin")
        mutations.append(missing)

        for index, mutated in enumerate(mutations):
            with self.subTest(mutation=index):
                with self.assertRaises(transition.TransitionError):
                    transition._validate_transition(manifest, mutated)

    def test_source_tampering_after_receipt_stops_before_hash(self) -> None:
        manifest = self.prepared()
        (self.source / "a.bin").write_bytes(b"changed")
        with mock.patch.object(frozen, "_hash_regular") as hasher:
            with self.assertRaises(frozen.MigrationError):
                self.unit.verify_complete(manifest)
        hasher.assert_not_called()

    def test_interrupted_cleanup_resumes_with_partial_tombstone(self) -> None:
        original_unlink = frozen.os.unlink
        stopped = {"value": False}

        def interrupt_after_delete(path, *args, **kwargs):
            if not stopped["value"] and ".xray-migration-" in str(path):
                stopped["value"] = True
                original_unlink(path, *args, **kwargs)
                raise OSError("simulated cleanup interruption")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(frozen.os, "unlink", side_effect=interrupt_after_delete):
            with self.assertRaises(frozen.MigrationError):
                self.unit.run()
        self.assertEqual(self.unit.status()["stage"], "cleaning")
        self.assertTrue(self.source.is_symlink())

        resumed = transition.ReboundDeviceUnit(
            self.manager, transition.UNIT_INDEX, self.manager.plan["units"][transition.UNIT_INDEX]
        )
        resumed.run()
        self.assertEqual(resumed.status()["stage"], "complete")
        self.assertTrue(self.source.is_symlink())
        self.assertFalse(os.path.lexists(resumed.tombstone))

    def test_interrupted_after_root_rename_revalidates_tombstone_and_resumes(self) -> None:
        original_symlink = frozen.os.symlink

        def stop_promotion(target, link_name, *args, **kwargs):
            if Path(link_name) == self.source:
                raise RuntimeError("simulated stop after source rename")
            return original_symlink(target, link_name, *args, **kwargs)

        with mock.patch.object(frozen.os, "symlink", side_effect=stop_promotion):
            with self.assertRaisesRegex(RuntimeError, "source rename"):
                self.unit.run()
        self.assertEqual(self.unit.status()["stage"], "renamed")
        self.assertFalse(os.path.lexists(self.source))
        self.assertTrue(os.path.lexists(self.unit.tombstone))

        resumed = transition.ReboundDeviceUnit(
            self.manager, transition.UNIT_INDEX, self.manager.plan["units"][transition.UNIT_INDEX]
        )
        resumed.run()
        self.assertEqual(resumed.status()["stage"], "complete")
        self.assertTrue(self.source.is_symlink())
        self.assertFalse(os.path.lexists(resumed.tombstone))

    def test_receipt_labels_old_device_as_manifest_evidence(self) -> None:
        self.prepared()
        receipt = json.loads(transition.RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["old_device_from_manifest"], self.old_device)
        self.assertNotIn("old_mount", receipt)

    def test_receipt_core_tampering_fails_closed(self) -> None:
        self.prepared()
        receipt = json.loads(transition.RECEIPT.read_text(encoding="utf-8"))
        receipt["stable_source_inventory_sha256"] = "0" * 64
        transition.RECEIPT.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(transition.TransitionError, "receipt"):
            self.prepared()

    def test_symlinked_inspection_and_evidence_directory_fail_closed(self) -> None:
        inspection_target = self.root / "inspection-target.json"
        inspection_target.write_text('{}\n', encoding="utf-8")
        self.inspection.unlink()
        os.symlink(inspection_target, self.inspection)
        with self.assertRaisesRegex(transition.TransitionError, "evidence file"):
            self.prepared()

        self.inspection.unlink()
        self.inspection.write_text('{}\n', encoding="utf-8")
        evidence_target = self.root / "evidence-target"
        evidence_target.mkdir()
        os.symlink(evidence_target, self.evidence)
        with self.assertRaisesRegex(transition.TransitionError, "evidence directory"):
            self.prepared()


if __name__ == "__main__":
    unittest.main()
