from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path


HELPER = Path("scripts/kunanyi/archive_file_list_payload.sh")


def test_archive_helper_builds_manifest_and_refuses_overwrite(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot"
    payload = snapshot / "products"
    payload.mkdir(parents=True)
    (payload / "summary.csv").write_text("metric,value\nanswer,1\n")
    logs = payload / "remote_logs"
    logs.mkdir()
    (logs / "job.out").write_text("finished\n")
    file_list = snapshot / "archive_file_list.txt"
    archive = tmp_path / "products.tar.gz"

    result = subprocess.run(
        ["bash", str(HELPER), str(snapshot), str(payload), str(file_list), str(archive)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert archive.is_file()
    assert file_list.is_file()
    assert (payload / "archive_manifest.tsv").is_file()
    assert (payload / "archive_checksums.sha256").is_file()
    with tarfile.open(archive, "r:gz") as handle:
        names = set(handle.getnames())
    assert "./products/summary.csv" in names
    assert "./products/remote_logs/job.out" in names
    assert "./products/archive_manifest.tsv" in names

    retry = subprocess.run(
        ["bash", str(HELPER), str(snapshot), str(payload), str(file_list), str(archive)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert retry.returncode == 3
