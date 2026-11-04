#!/usr/bin/env python3
"""Prepare an immutable flux wrapper and its provenance validators."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat


WRAPPER_PATH = Path("scripts/kunanyi/q031_flux_measurements.pbs")
VALIDATOR_PATH = Path("scripts/kunanyi/validate_q031_native_dependencies.py")
LINEAGE_VALIDATOR_PATH = Path("scripts/kunanyi/validate_g_hi_inherited_lineage.py")
EXPECTED_WRAPPER_SHA256 = "d53ae9f97e22175df3b470136e7829316190046ed09c9f7a9e30c9e792d95f4d"
OUTPUT_WRAPPER = "q031_flux_release.pbs"
OUTPUT_VALIDATOR = "validate_q031_native_dependencies.py"
OUTPUT_LINEAGE_VALIDATOR = "validate_g_hi_inherited_lineage.py"
GUARD_ANCHOR = b"umask 077\n"


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
    lineage_validator_path = flux_stage / LINEAGE_VALIDATOR_PATH
    original = read_regular(original_path)
    if digest(original) != EXPECTED_WRAPPER_SHA256:
        raise ValueError("frozen flux wrapper hash mismatch")
    validator = read_regular(validator_path)
    lineage_validator = read_regular(lineage_validator_path)
    if original.count(GUARD_ANCHOR) != 1:
        raise ValueError("frozen wrapper anchors are not unique")
    guard = (
        "readonly RELEASE_OVERLAY={}\n"
        "(\n"
        "  cd \"$RELEASE_OVERLAY\"\n"
        "  sha256sum --check overlay_checksums.sha256\n"
        ")\n"
        "export Q031_DEPENDENCY_VALIDATOR=\"$RELEASE_OVERLAY/{}\"\n"
        "export Q031_G_HI_LINEAGE_VALIDATOR=\"$RELEASE_OVERLAY/{}\"\n"
    ).format(
        shlex.quote(str(overlay)), OUTPUT_VALIDATOR, OUTPUT_LINEAGE_VALIDATOR
    ).encode("utf-8")
    wrapper = original.replace(GUARD_ANCHOR, GUARD_ANCHOR + guard, 1)
    files = {
        OUTPUT_WRAPPER: wrapper,
        OUTPUT_VALIDATOR: validator,
        OUTPUT_LINEAGE_VALIDATOR: lineage_validator,
    }
    checksums = "".join("{}  {}\n".format(digest(files[name]), name) for name in sorted(files)).encode("ascii")
    manifest = {
        "schema_version": 1,
        "scope": (
            "immutable r6 flux wrapper with normalized migration validation and "
            "G-HI inherited-source lineage validation"
        ),
        "flux_stage": str(flux_stage),
        "native_stage": str(native_stage),
        "overlay": str(overlay),
        "sources": {
            str(original_path): digest(original),
            str(validator_path): digest(validator),
            str(lineage_validator_path): digest(lineage_validator),
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
