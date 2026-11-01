#!/usr/bin/env python3
"""Build a hash-bound validator-only overlay for the paired no-jet stage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile


ORIGINAL_PBS = Path("scripts/kunanyi/paired_nojet_control.pbs")
ORIGINAL_BUDGET_VALIDATOR = Path("scripts/science/validate_paired_nojet_budget.py")
ORIGINAL_OUTPUT_VALIDATOR = Path("scripts/science/validate_paired_nojet_outputs.py")
UPDATED_BUDGET_VALIDATOR = Path("scripts/science/validate_paired_nojet_budget.py")
UPDATED_OUTPUT_VALIDATOR = Path("scripts/science/validate_paired_nojet_outputs.py")
BUDGET_TESTS = Path("tests/test_paired_nojet_budget.py")
OUTPUT_TESTS = Path("tests/test_paired_nojet_outputs.py")
OVERLAY_FILES = (
    Path("scripts/kunanyi/build_paired_nojet_analysis_overlay.py"),
    Path("scripts/kunanyi/paired_nojet_revalidate.py"),
    Path("scripts/kunanyi/paired_nojet_revalidate.pbs"),
    UPDATED_BUDGET_VALIDATOR,
    UPDATED_OUTPUT_VALIDATOR,
    BUDGET_TESTS,
    OUTPUT_TESTS,
)
EXPECTED_BUDGET_TEST_COUNT = 38
EXPECTED_OUTPUT_HELPER_TEST_COUNT = 7
OLD_SCALE = 'close(values["net"], values["positive"] + values["negative"], 0, "signed actual flux does not sum")'
NEW_SCALE = 'close(values["net"], values["positive"] + values["negative"], values["positive"] - values["negative"], "signed actual flux does not sum")'
OLD_STABLE = '''def _stable(identities: Sequence[Mapping[str, Any]]) -> None:
    for identity in identities:
        if any(identity[key] != value for key, value in _stat(Path(identity["path"])).items()):
            raise ValueError(f"input mutated during or after validation: {identity['path']}")
'''
NEW_STABLE = '''def _stable(identities: Sequence[Mapping[str, Any]]) -> None:
    for identity in identities:
        path = Path(identity["path"])
        before = _stat(path)
        mismatches = {key for key, value in before.items() if identity.get(key) != value}
        if not mismatches:
            continue
        expected_hash = identity.get("sha256")
        if mismatches != {"device"} or not isinstance(expected_hash, str) or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
            raise ValueError(f"input mutated during or after validation: {identity['path']}")
        actual_hash = _hash(path)
        after = _stat(path)
        if before != after or actual_hash != expected_hash:
            raise ValueError(f"input mutated during or after validation: {identity['path']}")
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_stage_manifest(stage: Path) -> tuple[Path, dict[Path, str]]:
    manifest = stage / "stage_checksums.sha256"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("physics stage has no regular stage_checksums.sha256")
    records: dict[Path, str] = {}
    pattern = re.compile(r"^([0-9a-f]{64})  ([^\n]+)$")
    for line_number, line in enumerate(manifest.read_text().splitlines(), 1):
        match = pattern.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid stage manifest line {line_number}")
        relative = Path(match[2])
        if relative.is_absolute() or ".." in relative.parts or relative in records:
            raise ValueError(f"unsafe or duplicate stage manifest path: {relative}")
        records[relative] = match[1]
    if not records:
        raise ValueError("empty stage manifest")
    for relative, expected in records.items():
        path = stage / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"stage manifest entry is not a regular file: {relative}")
        if sha256(path) != expected:
            raise ValueError(f"physics stage hash mismatch: {relative}")
    return manifest, records


def require_validator_only_change(old_path: Path, new_path: Path) -> None:
    old = old_path.read_text()
    new = new_path.read_text()
    if old.count(OLD_SCALE) != 1 or OLD_SCALE in new or new.count(NEW_SCALE) != 1:
        raise ValueError("budget validator does not contain the authorised scale replacement")
    if old.replace(OLD_SCALE, NEW_SCALE) != new:
        raise ValueError("budget validator differs from the frozen version beyond the authorised scale replacement")


def require_output_helper_only_change(old_path: Path, new_path: Path) -> None:
    old = old_path.read_text()
    new = new_path.read_text()
    if old.count(OLD_STABLE) != 1 or OLD_STABLE in new or new.count(NEW_STABLE) != 1:
        raise ValueError("output helper does not contain the authorised cross-device stability replacement")
    if old.replace(OLD_STABLE, NEW_STABLE) != new:
        raise ValueError("output helper differs from the frozen version beyond the authorised stability replacement")


def render_revalidation_pbs(template: str, remote_stage: PurePosixPath, remote_overlay: PurePosixPath) -> str:
    replacements = {
        "@PHYSICS_STAGE@": str(remote_stage),
        "@ANALYSIS_OVERLAY@": str(remote_overlay),
    }
    for token, replacement in replacements.items():
        if template.count(token) != 1:
            raise ValueError(f"revalidation PBS must contain exactly one {token}")
        template = template.replace(token, replacement)
    return template


def render_full_pbs(original: str, remote_overlay: PurePosixPath) -> str:
    overlay = str(remote_overlay)
    anchor = 'sha256sum --check stage_checksums.sha256 > "logs/checksums.${PBS_JOBID}.txt"\n'
    if original.count(anchor) != 1:
        raise ValueError("original PBS checksum preflight anchor changed")
    preflight = (
        anchor
        + f'readonly OVERLAY={json.dumps(overlay)}\n'
        + 'python3 "$OVERLAY/scripts/kunanyi/paired_nojet_revalidate.py" --physics-stage "$STAGE" '
          '--overlay "$OVERLAY" --verify-bindings\n'
    )
    rendered = original.replace(anchor, preflight)
    gate_old = "r=json.loads(Path('smoke_gate/receipt.json').read_text())"
    gate_new = f"r=json.loads(Path({str(remote_overlay / 'revalidated/gate_receipt.json')!r}).read_text())"
    if rendered.count(gate_old) != 1:
        raise ValueError("original PBS full-run gate path changed")
    rendered = rendered.replace(gate_old, gate_new)
    key_old = "assert r['stage_manifest_sha256']==hashlib.sha256(Path('stage_checksums.sha256').read_bytes()).hexdigest()"
    key_new = "assert r['original_stage_manifest_sha256']==hashlib.sha256(Path('stage_checksums.sha256').read_bytes()).hexdigest()"
    if rendered.count(key_old) != 1:
        raise ValueError("original PBS full-run manifest assertion changed")
    rendered = rendered.replace(key_old, key_new)
    budget_old = "python scripts/science/validate_paired_nojet_budget.py --run-dir \"$RUN\" \\\n"
    budget_new = "python \"$OVERLAY/scripts/science/validate_paired_nojet_budget.py\" --run-dir \"$RUN\" \\\n"
    if rendered.count(budget_old) != 1:
        raise ValueError("original PBS budget invocation changed")
    return rendered.replace(budget_old, budget_new)


def write_overlay_manifest(root: Path) -> Path:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"overlay contains a symlink: {path}")
        if path.is_file() and path.name != "overlay_checksums.sha256":
            records.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    manifest = root / "overlay_checksums.sha256"
    manifest.write_text("\n".join(records) + "\n")
    return manifest


def build(args: argparse.Namespace) -> dict[str, object]:
    repo = Path(__file__).resolve().parents[2]
    physics_stage = args.physics_stage.resolve()
    output = args.output.resolve()
    archive = output.with_suffix(output.suffix + ".tar.gz")
    if output.exists() or archive.exists():
        raise FileExistsError(f"refusing to overwrite overlay or archive: {output}")
    remote_stage = PurePosixPath(args.remote_physics_stage)
    if not remote_stage.is_absolute():
        raise ValueError("--remote-physics-stage must be an absolute POSIX path")
    remote_overlay = remote_stage.parent / output.name
    manifest, stage_records = load_stage_manifest(physics_stage)
    for required in (ORIGINAL_PBS, ORIGINAL_BUDGET_VALIDATOR, ORIGINAL_OUTPUT_VALIDATOR):
        if required not in stage_records:
            raise ValueError(f"physics stage manifest omits required file: {required}")
    require_validator_only_change(physics_stage / ORIGINAL_BUDGET_VALIDATOR, repo / UPDATED_BUDGET_VALIDATOR)
    require_output_helper_only_change(physics_stage / ORIGINAL_OUTPUT_VALIDATOR, repo / UPDATED_OUTPUT_VALIDATOR)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    temporary_archive = archive.with_name(f".{archive.name}.{os.getpid()}.tmp")
    try:
        for relative in OVERLAY_FILES:
            source = repo / relative
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        revalidation = temporary / "scripts/kunanyi/paired_nojet_revalidate.pbs"
        revalidation.write_text(render_revalidation_pbs(revalidation.read_text(), remote_stage, remote_overlay))
        full_pbs = temporary / "scripts/kunanyi/paired_nojet_control_full.pbs"
        full_pbs.write_text(render_full_pbs((physics_stage / ORIGINAL_PBS).read_text(), remote_overlay))
        contract = {
            "schema_version": 1,
            "status": "validator_only_analysis_overlay",
            "remote_physics_stage": str(remote_stage),
            "remote_analysis_overlay": str(remote_overlay),
            "original_stage_manifest_sha256": sha256(manifest),
            "original_pbs_sha256": stage_records[ORIGINAL_PBS],
            "original_budget_validator_sha256": stage_records[ORIGINAL_BUDGET_VALIDATOR],
            "original_output_validator_sha256": stage_records[ORIGINAL_OUTPUT_VALIDATOR],
            "updated_budget_validator_sha256": sha256(repo / UPDATED_BUDGET_VALIDATOR),
            "updated_output_validator_sha256": sha256(repo / UPDATED_OUTPUT_VALIDATOR),
            "budget_test_sha256": sha256(repo / BUDGET_TESTS),
            "output_test_sha256": sha256(repo / OUTPUT_TESTS),
            "expected_budget_test_count": EXPECTED_BUDGET_TEST_COUNT,
            "expected_output_helper_test_count": EXPECTED_OUTPUT_HELPER_TEST_COUNT,
            "validator_change": "signed actual-flux identity uses positive-minus-negative gross transport as the floating-point consistency scale",
            "physical_acceptance_gates_changed": False,
            "physics_stage_files_changed": [],
            "full_runtime_budget_validator": str(remote_overlay / UPDATED_BUDGET_VALIDATOR.as_posix()),
            "full_runtime_gate_receipt": str(remote_overlay / "revalidated/gate_receipt.json"),
        }
        (temporary / "overlay_contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
        overlay_manifest = write_overlay_manifest(temporary)
        with tarfile.open(temporary_archive, "x:gz") as handle:
            handle.add(temporary, arcname=output.name)
        os.rename(temporary, output)
        os.rename(temporary_archive, archive)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        temporary_archive.unlink(missing_ok=True)
        raise
    result = {
        "overlay": str(output),
        "archive": str(archive),
        "archive_sha256": sha256(archive),
        "overlay_manifest_sha256": sha256(output / overlay_manifest.name),
        "remote_overlay": str(remote_overlay),
    }
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physics-stage", type=Path, required=True)
    parser.add_argument("--remote-physics-stage", required=True)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
