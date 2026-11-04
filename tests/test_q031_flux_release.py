from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/kunanyi/prepare_q031_flux_release.py"
SPEC = importlib.util.spec_from_file_location("prepare_q031_flux_release", SCRIPT)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def sources(tmp_path):
    flux, native = tmp_path / "flux", tmp_path / "native"
    for stage, relative in (
        (flux, release.WRAPPER_PATH),
        (flux, release.LINEAGE_VALIDATOR_PATH),
        (native, release.VALIDATOR_PATH),
    ):
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return flux, native


def test_overlay_preserves_reviewed_wrapper_outside_integrity_guard(tmp_path):
    flux, native = sources(tmp_path)
    overlay = tmp_path / "release with ' quote"
    original = (flux / release.WRAPPER_PATH).read_bytes()
    native_bytes = (native / release.VALIDATOR_PATH).read_bytes()
    lineage_bytes = (flux / release.LINEAGE_VALIDATOR_PATH).read_bytes()
    manifest = release.prepare_overlay(flux, native, overlay)
    actual = (overlay / release.OUTPUT_WRAPPER).read_bytes()
    restored = actual
    guard_start = restored.index(b"readonly RELEASE_OVERLAY=")
    guard_end = restored.index(b"Q031_G_HI_LINEAGE_VALIDATOR", guard_start)
    guard_end = restored.index(b"\n", guard_end) + 1
    assert restored[:guard_start] + restored[guard_end:] == original
    assert (overlay / release.OUTPUT_VALIDATOR).read_bytes() == native_bytes
    assert (overlay / release.OUTPUT_LINEAGE_VALIDATOR).read_bytes() == lineage_bytes
    assert (flux / release.WRAPPER_PATH).read_bytes() == original
    assert (native / release.VALIDATOR_PATH).read_bytes() == native_bytes
    assert manifest["sources"][str(flux / release.WRAPPER_PATH)] == release.EXPECTED_WRAPPER_SHA256
    assert manifest["sources"][str(native / release.VALIDATOR_PATH)] == manifest["files"][release.OUTPUT_VALIDATOR]
    assert manifest["sources"][str(flux / release.LINEAGE_VALIDATOR_PATH)] == manifest["files"][release.OUTPUT_LINEAGE_VALIDATOR]
    assert json.loads((overlay / "manifest.json").read_text()) == manifest
    subprocess.run(["bash", "-n", str(overlay / release.OUTPUT_WRAPPER)], check=True)


def test_checksum_guard_detects_changed_validator_before_work(tmp_path):
    flux, native = sources(tmp_path)
    overlay = tmp_path / "release"
    manifest = release.prepare_overlay(flux, native, overlay)
    checksums = (overlay / "overlay_checksums.sha256").read_bytes()
    assert hashlib.sha256(checksums).hexdigest() == manifest["overlay_checksums_sha256"]
    for line in checksums.decode().splitlines():
        expected, name = line.split("  ", 1)
        assert hashlib.sha256((overlay / name).read_bytes()).hexdigest() == expected
    wrapper = (overlay / release.OUTPUT_WRAPPER).read_text()
    guard = wrapper[wrapper.index("set -euo pipefail"):wrapper.index("readonly STAGE=")]
    subprocess.run(["bash", "-c", guard], check=True, capture_output=True, text=True)
    with (overlay / release.OUTPUT_VALIDATOR).open("a") as handle:
        handle.write("\n# changed\n")
    result = subprocess.run(["bash", "-c", guard], capture_output=True, text=True)
    assert result.returncode != 0
    assert "FAILED" in result.stdout


@pytest.mark.parametrize("mutation", [
    "stale_wrapper", "wrapper_symlink", "validator_symlink", "lineage_symlink", "stage_symlink"
])
def test_refuses_unbound_or_nonregular_sources_without_overlay(tmp_path, mutation):
    flux, native = sources(tmp_path)
    overlay = tmp_path / "release"
    if mutation == "stale_wrapper":
        with (flux / release.WRAPPER_PATH).open("a") as handle:
            handle.write("\n")
    elif mutation == "stage_symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(native, target_is_directory=True)
        native = alias
    else:
        if mutation == "wrapper_symlink":
            path = flux / release.WRAPPER_PATH
        elif mutation == "lineage_symlink":
            path = flux / release.LINEAGE_VALIDATOR_PATH
        else:
            path = native / release.VALIDATOR_PATH
        content = path.read_bytes()
        path.unlink()
        target = tmp_path / "external"
        target.write_bytes(content)
        path.symlink_to(target)
    with pytest.raises(ValueError):
        release.prepare_overlay(flux, native, overlay)
    assert not overlay.exists()


def test_refuses_existing_or_inside_frozen_stage_overlay(tmp_path):
    flux, native = sources(tmp_path)
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "marker"
    marker.write_text("preserve")
    with pytest.raises(FileExistsError):
        release.prepare_overlay(flux, native, existing)
    assert marker.read_text() == "preserve"
    for stage in (flux, native):
        with pytest.raises(ValueError, match="outside frozen"):
            release.prepare_overlay(flux, native, stage / "overlay")
        assert not (stage / "overlay").exists()
    alias = tmp_path / "flux-alias"
    alias.symlink_to(flux, target_is_directory=True)
    with pytest.raises(ValueError, match="outside frozen"):
        release.prepare_overlay(flux, native, alias / "overlay")


def test_builder_uses_python36_syntax():
    ast.parse(SCRIPT.read_text(), feature_version=(3, 6))
