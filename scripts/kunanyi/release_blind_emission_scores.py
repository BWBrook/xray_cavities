"""Verify board 3731's release commitments, then run the frozen scorer on site."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import sys
import tarfile
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "science"))
import rescore_xray_blind as review


@contextmanager
def owner_readable(path):
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or stat.S_IMODE(mode) != 0:
        raise ValueError(f"{path.name}: expected a closed regular file")
    try:
        path.chmod(0o400)
        yield
    finally:
        path.chmod(0)


def add_file(archive, source, name):
    with source.open("rb") as handle:
        member = tarfile.TarInfo(name)
        member.size = os.fstat(handle.fileno()).st_size
        member.mode = 0o400
        archive.addfile(member, handle)


def release(blind, config_path, seal_dir, output):
    if output.exists():
        raise FileExistsError(f"choose a new release directory: {output}")
    seal_path = seal_dir / "seal.json"
    lock = seal_dir.parent / ('.' + seal_dir.name + '.scoring-release.lock')
    lock_fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'r+b') as anchor, tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        fcntl.flock(anchor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if blind.digest(seal_path) != review.SEAL:
            raise ValueError("seal differs from the independently reviewed commitment")
        sealed = blind.read_json(seal_path)
        config = blind.load_config(config_path)
        predictions = seal_dir / "predictions"
        if (blind.digest(config_path) != sealed["protocol_config_sha256"]
                or blind.digest(predictions / "prediction_receipt.json") != sealed["prediction_receipt_sha256"]
                or sealed["scoring_manifest_commitment_sha256"] != review.COMMITMENT):
            raise ValueError("configuration, prediction receipt or scoring commitment differs")
        blind.validate_units(config, sealed["units"])
        blind.validate_labels(config, sealed["label_definitions"])
        for unit in sealed["units"]:
            path = predictions / unit["file"]
            if (unit["file"] != unit["unit_id"] + ".npz" or path.is_symlink()
                    or blind.digest(path) != unit["prediction_sha256"]):
                raise ValueError(f"{unit['unit_id']}: sealed prediction differs")

        staging = Path(temporary)
        product = staging / "release"
        product.mkdir(mode=0o700)
        manifest = staging / "scoring_truth_manifest.json"
        original_manifest = seal_dir / "manifests" / manifest.name
        with owner_readable(original_manifest):
            shutil.copyfile(original_manifest, manifest)
        if blind.digest(manifest) != review.COMMITMENT:
            raise ValueError("scoring manifest differs from its pre-prediction commitment")
        units = blind.read_json(manifest)["units"]
        blind.validate_units(config, units)
        lookup = {unit["unit_id"]: unit for unit in units}
        source_paths = []
        expected = {manifest.name: review.COMMITMENT}
        archive_path = product / "scoring_evidence.tar"
        with tarfile.open(archive_path, "x") as archive:
            add_file(archive, manifest, manifest.name)
            for registered in sealed["units"]:
                uid = registered["unit_id"]
                unit = lookup[uid]
                refs = unit["provenance"]
                if (blind.unit_key(unit) != blind.unit_key(registered)
                        or refs["native_input_receipt"]["sha256"] != registered["source_receipt_sha256"]
                        or refs["producer_receipt"]["sha256"] != registered["producer_receipt_sha256"]):
                    raise ValueError(f"{uid}: case or provenance differs from the seal")
                blind.bind_provenance(unit)
                producer_path = Path(refs["producer_receipt"]["path"])
                producer = blind.read_json(producer_path)
                name = uid + ".truth.npz"
                path = producer_path.parent / name
                info = producer["files"][name]
                if (unit["truth"]["path"] != str(path) or unit["truth"]["sha256"] != info["sha256"]
                        or path.lstat().st_size != info["size_bytes"]):
                    raise ValueError(f"{uid}: scoring location, hash or size differs from the producer")
                with owner_readable(path):
                    add_file(archive, path, "truth/" + name)
                source_paths.append(path)
                expected["truth/" + name] = info["sha256"]
        archive_path.chmod(0o400)
        with tarfile.open(archive_path, "r:") as archive:
            if sorted(archive.getnames()) != sorted(expected):
                raise ValueError("private scoring archive inventory differs")
            for item in archive:
                with archive.extractfile(item) as handle:
                    if hashlib.file_digest(handle, "sha256").hexdigest() != expected[item.name]:
                        raise ValueError(f"{item.name}: archived bytes differ from the commitment")
        # The frozen manifest contains the original absolute paths. The frozen
        # scorer rehashes each original before and after scoring its view.
        with ExitStack() as readable:
            for path in source_paths:
                readable.enter_context(owner_readable(path))
                if blind.digest(path) != expected["truth/" + path.name]:
                    raise ValueError(f"{path.name}: original changed since archive verification")
            verified = datetime.now(timezone.utc).isoformat()
            evaluation = blind.score(config_path, predictions, manifest, product / "scores")
        if any(stat.S_IMODE(path.lstat().st_mode) for path in [original_manifest, *source_paths]):
            raise ValueError("original scoring permissions were not restored")
        if (evaluation["truth_manifest_sha256"] != review.COMMITMENT
                or evaluation["prediction_receipt_sha256"] != sealed["prediction_receipt_sha256"]):
            raise ValueError("frozen evaluation does not bind the original manifest and predictions")
        result = {
            "seal_sha256": review.SEAL, "scoring_manifest_sha256": review.COMMITMENT,
            "all_commitments_verified_before_scorer_utc": verified,
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "scoring_files_reclosed": len(source_paths) + 1, "scoring_rasters_verified": len(source_paths),
            "prediction_files_verified": len(sealed["units"]), "archive_member_count": len(expected),
            "archive_sha256": blind.digest(archive_path), "archive_size_bytes": archive_path.stat().st_size,
            "prediction_receipt_sha256": sealed["prediction_receipt_sha256"],
            "scores_sha256": evaluation["scores_sha256"],
            "evaluation_receipt_sha256": blind.digest(product / "scores/evaluation_receipt.json"),
        }
        blind.write_json(product / "release_receipt.json", result)
        (product / "scores").chmod(0o700)
        for artifact in (product / "release_receipt.json", *sorted((product / "scores").iterdir())):
            artifact.chmod(0o400)
        product.rename(output)
    return result


def terminate(signum, _frame):
    raise SystemExit(128 + signum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    for signum in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(signum, terminate)
    seal_dir = args.seal_dir.absolute()
    stage = seal_dir.parent
    sys.path.insert(0, str(stage / "scripts/science"))
    import run_background_refit_blind as frozen
    if Path(frozen.__file__).resolve() != (stage / review.RUNNER).resolve():
        raise ValueError("expected the original staged scorer")
    report = release(frozen, stage / review.CONFIG, seal_dir, args.output_dir.absolute())
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
