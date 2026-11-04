#!/usr/bin/env python3
"""Prepare an immutable flux wrapper with the normalized migration gate."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat


WRAPPER_PATH = Path("scripts/kunanyi/q031_flux_measurements.pbs")
VALIDATOR_PATH = Path("scripts/kunanyi/validate_q031_native_dependencies.py")
EXPECTED_WRAPPER_SHA256 = "858fb2db1641ff288e194828aab4a99d77ae5a15ccb0b177003906e8005b7a6a"
OUTPUT_WRAPPER = "q031_flux_release.pbs"
OUTPUT_VALIDATOR = "validate_q031_native_dependencies.py"
GATE_START = b'  python - "$MIGRATION" <<\'PY\'\n'
GATE_END = b"\nPY\n"
GUARD_ANCHOR = b"umask 077\n"
NEW_GATE = b'''  python - "$MIGRATION" "$RELEASE_OVERLAY" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from validate_q031_native_dependencies import validate_migration_dependencies
validate_migration_dependencies(Path(sys.argv[1]))
print('MIGRATION_COMPLETE_GATE_OK', flush=True)
PY
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("source must be a regular file: {}".format(path))
    with os.fdopen(os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW), "rb") as handle:
        opened = os.fstat(handle.fileno())
        data = handle.read()
        after = os.fstat(handle.fileno())
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if identity(before) != identity(opened) or identity(opened) != identity(after) or identity(after) != identity(path.lstat()):
        raise ValueError("source changed during capture: {}".format(path))
    return data


def require_directory(path):
    if not stat.S_ISDIR(path.lstat().st_mode):
        raise ValueError("stage must be a directory, not a symlink: {}".format(path))


def prepare_overlay(flux_stage, native_stage, overlay):
    flux_stage = Path(os.path.abspath(str(flux_stage)))
    native_stage = Path(os.path.abspath(str(native_stage)))
    overlay = Path(os.path.abspath(str(overlay)))
    if os.path.lexists(str(overlay)):
        raise FileExistsError("refusing existing overlay: {}".format(overlay))
    require_directory(flux_stage)
    require_directory(native_stage)
    flux_stage = flux_stage.resolve()
    native_stage = native_stage.resolve()
    overlay = overlay.parent.resolve() / overlay.name
    for source_stage in (flux_stage, native_stage):
        if source_stage == overlay or source_stage in overlay.parents:
            raise ValueError("overlay must be outside frozen stages")

    original_path = flux_stage / WRAPPER_PATH
    validator_path = native_stage / VALIDATOR_PATH
    original = read_regular(original_path)
    if digest(original) != EXPECTED_WRAPPER_SHA256:
        raise ValueError("frozen flux wrapper hash mismatch")
    validator = read_regular(validator_path)
    if original.count(GATE_START) != 1 or original.count(GUARD_ANCHOR) != 1:
        raise ValueError("frozen wrapper anchors are not unique")
    start = original.index(GATE_START)
    end = original.index(GATE_END, start) + len(GATE_END)
    guard = (
        "readonly RELEASE_OVERLAY={}\n"
        "(\n"
        "  cd \"$RELEASE_OVERLAY\"\n"
        "  sha256sum --check overlay_checksums.sha256\n"
        ")\n"
    ).format(shlex.quote(str(overlay))).encode("utf-8")
    wrapper = (original[:start] + NEW_GATE + original[end:]).replace(
        GUARD_ANCHOR, GUARD_ANCHOR + guard, 1
    )
    files = {OUTPUT_WRAPPER: wrapper, OUTPUT_VALIDATOR: validator}
    checksums = "".join("{}  {}\n".format(digest(files[name]), name) for name in sorted(files)).encode("ascii")
    manifest = {
        "schema_version": 1,
        "scope": "migration-gate replacement; frozen flux science and result paths unchanged",
        "flux_stage": str(flux_stage),
        "native_stage": str(native_stage),
        "overlay": str(overlay),
        "sources": {
            str(original_path): digest(original),
            str(validator_path): digest(validator),
        },
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "overlay_checksums_sha256": digest(checksums),
    }
    overlay.mkdir(mode=0o700)
    for name, data in files.items():
        with (overlay / name).open("xb") as handle:
            handle.write(data)
        (overlay / name).chmod(0o600)
    with (overlay / "overlay_checksums.sha256").open("xb") as handle:
        handle.write(checksums)
    with (overlay / "manifest.json").open("x") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flux-stage", type=Path, required=True)
    parser.add_argument("--native-stage", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    args = parser.parse_args()
    prepare_overlay(args.flux_stage, args.native_stage, args.overlay)
    print("FLUX_RELEASE_OVERLAY", args.overlay.resolve())
    print("MANIFEST_SHA256", digest((args.overlay / "manifest.json").read_bytes()))


if __name__ == "__main__":
    main()
