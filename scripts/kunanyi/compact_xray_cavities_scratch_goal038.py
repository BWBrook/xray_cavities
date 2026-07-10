#!/usr/bin/env python3
"""Execute the approved Goal 038 scratch-retention plan fail-closed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable


APPROVAL_TOKEN = "GOAL038_COMPACTION_APPROVED_2026-07-10"
PRODUCTION_RUNS_ROOT = Path("/scratch/bwbrook/xray_cavities_runs")
PRODUCTION_STAGE_ROOT = Path(
    "/u/bwbrook/codex_kunanyi/goal038_g_lo_hdf5_stall_guarded_continuation"
)
DEFAULT_FLOAT_HDF5_SIZE = 44_890_581_676

PURGE_ROOTS = (
    "2026-05-08-c-hi-segment",
    "2026-05-19-c-hi-fullgrid-startup",
    "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-08node",
    "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-16node",
    "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node",
    "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-48node",
    "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-64node",
    "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node",
)
C_LO_1 = "2026-07-03-c-lo-bounded-execution"
C_LO_2 = "2026-07-04-c-lo-bounded-continuation"
C_LO_3 = "2026-07-05-c-lo-bounded-continuation-2"
C_LO_FINAL = "2026-07-05-c-lo-endpoint-oriented-continuation"
C_LO_OLD_ROOTS = (C_LO_1, C_LO_2, C_LO_3)
C_HI_FRESH = "2026-06-01-c-hi-fullgrid-agn-impi-fresh"
C_HI_PROD = "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64"
G_LO_SOURCE = "2026-07-07-g-lo-endpoint-oriented-production"
GOAL038_PARTIAL = "2026-07-10-g-lo-hdf5-stall-guarded-continuation"


class CompactionError(Exception):
    """The retention plan failed a preflight or postcondition."""


def output_root(runs_root: Path, run_name: str, case_id: str) -> Path:
    return runs_root / run_name / case_id / "particles" / "problem" / "outputs"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CompactionError(message)


def require_regular(path: Path, *, expected_size: int | None = None) -> None:
    require(path.exists(), f"required file is missing: {path}")
    require(path.is_file() and not path.is_symlink(), f"required regular file: {path}")
    if expected_size is not None:
        require(
            path.stat().st_size == expected_size,
            f"size mismatch for {path}: expected {expected_size}, "
            f"found {path.stat().st_size}",
        )


def numeric_catalogue_indices(path: Path) -> list[int]:
    require_regular(path)
    indices: list[int] = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split()
        if not fields or not fields[0].isdigit():
            continue
        require(
            len(fields) >= 4,
            f"catalogue row {line_number} has fewer than four fields: {path}",
        )
        indices.append(int(fields[0]))
    return indices


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def tree_inventory(path: Path) -> dict[str, object]:
    total_bytes = 0
    regular_files = 0
    symlinks = 0
    if not path.exists() and not path.is_symlink():
        return {
            "path": str(path),
            "exists": False,
            "size_bytes": 0,
            "regular_files": 0,
            "symlinks": 0,
        }
    for root, directories, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in directories + files:
            item = root_path / name
            if item.is_symlink():
                symlinks += 1
                total_bytes += item.lstat().st_size
            elif item.is_file():
                regular_files += 1
                total_bytes += item.stat().st_size
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": total_bytes,
        "regular_files": regular_files,
        "symlinks": symlinks,
    }


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text)
    os.replace(temporary, path)


def write_inventory(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    fieldnames = ["path", "exists", "size_bytes", "regular_files", "symlinks"]
    temporary = path.with_name(f".{path.name}.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)
    digest = sha256_file(path)
    atomic_write_text(
        path.with_suffix(".sha256"), f"{digest}  {path.name}\n"
    )


def manifest_roots(runs_root: Path) -> list[Path]:
    names = list(PURGE_ROOTS) + [
        C_HI_FRESH,
        C_HI_PROD,
        C_LO_1,
        C_LO_2,
        C_LO_3,
        C_LO_FINAL,
        G_LO_SOURCE,
        GOAL038_PARTIAL,
    ]
    return [runs_root / name for name in names]


def validate_symlink(path: Path, expected_target: Path) -> None:
    require(path.is_symlink(), f"required symlink is missing: {path}")
    require(
        path.resolve() == expected_target.resolve(),
        f"symlink target mismatch for {path}: expected {expected_target}, "
        f"found {path.resolve()}",
    )


def preflight(
    runs_root: Path,
    *,
    expected_float_size: int | None,
) -> dict[str, object]:
    require(runs_root.is_dir(), f"runs root is missing: {runs_root}")
    purge_presence = [(runs_root / name).is_dir() for name in PURGE_ROOTS]
    require(
        all(purge_presence) or not any(purge_presence),
        "planned whole-root purge is in a partial state",
    )
    for name in (C_HI_FRESH, C_HI_PROD, C_LO_FINAL, G_LO_SOURCE):
        require((runs_root / name).is_dir(), f"required run root is missing: {name}")

    c_lo_1 = output_root(runs_root, C_LO_1, "C-LO")
    c_lo_2 = output_root(runs_root, C_LO_2, "C-LO")
    c_lo_3 = output_root(runs_root, C_LO_3, "C-LO")
    endpoint = output_root(runs_root, C_LO_FINAL, "C-LO")
    old_presence = [
        (runs_root / name).is_dir() for name in C_LO_OLD_ROOTS
    ]
    require(
        all(old_presence) or not any(old_presence),
        "C-LO segmented roots are in a partial promotion state",
    )
    c_lo_state = "segmented" if all(old_presence) else "promoted"
    float_sources = ((c_lo_1, 0, 6), (c_lo_2, 7, 12), (c_lo_3, 13, 19))
    if c_lo_state == "segmented":
        for source, first, last in float_sources:
            for index in range(first, last + 1):
                source_h5 = source / f"data.{index:04d}.flt.h5"
                source_xmf = source / f"data.{index:04d}.flt.xmf"
                require_regular(source_h5, expected_size=expected_float_size)
                require_regular(source_xmf)
                for destination in (
                    endpoint / source_h5.name,
                    endpoint / source_xmf.name,
                ):
                    require(
                        not destination.exists() and not destination.is_symlink(),
                        f"destination collision before C-LO promotion: {destination}",
                    )
    for index in range(0 if c_lo_state == "promoted" else 20, 54):
        require_regular(
            endpoint / f"data.{index:04d}.flt.h5",
            expected_size=expected_float_size,
        )
        require_regular(endpoint / f"data.{index:04d}.flt.xmf")

    require(
        numeric_catalogue_indices(endpoint / "flt.h5.out") == list(range(54)),
        "C-LO endpoint flt.h5.out must contain exactly indices 0 through 53",
    )
    require(
        numeric_catalogue_indices(endpoint / "dbl.h5.out") == list(range(14)),
        "C-LO endpoint dbl.h5.out must contain exactly indices 0 through 13",
    )

    endpoint_xmf_6 = endpoint / "data.0006.dbl.xmf"
    require_regular(endpoint_xmf_6)
    if c_lo_state == "segmented":
        source_double_6 = c_lo_3 / "data.0006.dbl.h5"
        source_particle_1611 = c_lo_3 / "particles.1611.dbl"
        require_regular(source_double_6)
        require_regular(source_particle_1611)
        validate_symlink(endpoint / "data.0006.dbl.h5", source_double_6)
        validate_symlink(endpoint / "particles.1611.dbl", source_particle_1611)
        source_xmf_6 = c_lo_3 / "data.0006.dbl.xmf"
        require_regular(source_xmf_6)
        require(
            sha256_file(source_xmf_6) == sha256_file(endpoint_xmf_6),
            "C-LO data.0006.dbl.xmf copies differ",
        )
    else:
        require_regular(endpoint / "data.0006.dbl.h5")
        require_regular(endpoint / "particles.1611.dbl")
    require_regular(endpoint / "data.0013.dbl.h5")
    require_regular(endpoint / "particles.5003.dbl")

    fresh = output_root(runs_root, C_HI_FRESH, "C-HI")
    prod = output_root(runs_root, C_HI_PROD, "C-HI")
    require_regular(fresh / "data.0009.dbl.h5")
    require_regular(fresh / "data.0009.dbl.xmf")
    require_regular(fresh / "particles.4277.dbl")
    require_regular(prod / "data.0011.dbl.h5")
    require_regular(prod / "data.0011.dbl.xmf")
    require_regular(prod / "particles.5000.dbl")
    validate_symlink(prod / "data.0009.dbl.h5", fresh / "data.0009.dbl.h5")
    validate_symlink(prod / "particles.4277.dbl", fresh / "particles.4277.dbl")

    g_lo = output_root(runs_root, G_LO_SOURCE, "G-LO")
    require_regular(g_lo / "data.0002.dbl.h5")
    invalid_partial = g_lo / "data.0003.dbl.h5"
    if invalid_partial.exists() or invalid_partial.is_symlink():
        require_regular(invalid_partial)
    return {
        "c_lo_endpoint": str(endpoint),
        "c_lo_state": c_lo_state,
        "g_lo_restart": str(g_lo / "data.0002.dbl.h5"),
        "planned_purge_roots": len(PURGE_ROOTS) + len(C_LO_OLD_ROOTS),
    }


def move_c_lo_surfaces(runs_root: Path) -> None:
    c_lo_1 = output_root(runs_root, C_LO_1, "C-LO")
    c_lo_2 = output_root(runs_root, C_LO_2, "C-LO")
    c_lo_3 = output_root(runs_root, C_LO_3, "C-LO")
    endpoint = output_root(runs_root, C_LO_FINAL, "C-LO")
    for source, first, last in ((c_lo_1, 0, 6), (c_lo_2, 7, 12), (c_lo_3, 13, 19)):
        for index in range(first, last + 1):
            for suffix in ("h5", "xmf"):
                name = f"data.{index:04d}.flt.{suffix}"
                os.replace(source / name, endpoint / name)
    os.replace(c_lo_3 / "data.0006.dbl.h5", endpoint / "data.0006.dbl.h5")
    os.replace(c_lo_3 / "particles.1611.dbl", endpoint / "particles.1611.dbl")


def remove_superseded_data(runs_root: Path) -> None:
    for name in PURGE_ROOTS + C_LO_OLD_ROOTS:
        path = runs_root / name
        if path.exists() or path.is_symlink():
            shutil.rmtree(path)

    endpoint = output_root(runs_root, C_LO_FINAL, "C-LO")
    keep_doubles = {"data.0006.dbl.h5", "data.0013.dbl.h5"}
    keep_double_xmf = {"data.0006.dbl.xmf", "data.0013.dbl.xmf"}
    for path in endpoint.glob("data.*.dbl.h5"):
        if path.name not in keep_doubles:
            path.unlink()
    for path in endpoint.glob("data.*.dbl.xmf"):
        if path.name not in keep_double_xmf:
            path.unlink()
    for path in endpoint.glob("particles.*.dbl"):
        if path.name not in {"particles.1611.dbl", "particles.5003.dbl"}:
            path.unlink()

    fresh = output_root(runs_root, C_HI_FRESH, "C-HI")
    for index in range(9):
        for suffix in ("h5", "xmf"):
            path = fresh / f"data.{index:04d}.dbl.{suffix}"
            if path.exists() or path.is_symlink():
                path.unlink()
    for path in fresh.glob("particles.*.dbl"):
        if path.name != "particles.4277.dbl":
            path.unlink()

    prod = output_root(runs_root, C_HI_PROD, "C-HI")
    for suffix in ("h5", "xmf"):
        path = prod / f"data.0010.dbl.{suffix}"
        if path.exists() or path.is_symlink():
            path.unlink()
    for path in prod.glob("particles.*.dbl"):
        if path.name != "particles.5000.dbl" and not path.is_symlink():
            path.unlink()

    g_lo = output_root(runs_root, G_LO_SOURCE, "G-LO")
    for suffix in ("h5", "xmf"):
        path = g_lo / f"data.0003.dbl.{suffix}"
        if path.exists() or path.is_symlink():
            path.unlink()
    partial = runs_root / GOAL038_PARTIAL
    if partial.exists() or partial.is_symlink():
        shutil.rmtree(partial)


def validate_postconditions(
    runs_root: Path,
    *,
    expected_float_size: int | None,
) -> None:
    endpoint = output_root(runs_root, C_LO_FINAL, "C-LO")
    for index in range(54):
        require_regular(
            endpoint / f"data.{index:04d}.flt.h5",
            expected_size=expected_float_size,
        )
        require_regular(endpoint / f"data.{index:04d}.flt.xmf")
    require_regular(endpoint / "data.0006.dbl.h5")
    require_regular(endpoint / "particles.1611.dbl")
    require_regular(endpoint / "data.0013.dbl.h5")
    require_regular(endpoint / "particles.5003.dbl")
    require(
        sorted(path.name for path in endpoint.glob("data.*.dbl.h5"))
        == ["data.0006.dbl.h5", "data.0013.dbl.h5"],
        "C-LO retained double-HDF5 set differs from indices 6 and 13",
    )
    require(
        sorted(path.name for path in endpoint.glob("particles.*.dbl"))
        == ["particles.1611.dbl", "particles.5003.dbl"],
        "C-LO retained particle set differs from indices 1611 and 5003",
    )
    for name in PURGE_ROOTS + C_LO_OLD_ROOTS + (GOAL038_PARTIAL,):
        require(not (runs_root / name).exists(), f"superseded root remains: {name}")

    fresh = output_root(runs_root, C_HI_FRESH, "C-HI")
    require_regular(fresh / "data.0009.dbl.h5")
    require_regular(fresh / "particles.4277.dbl")
    require(
        not any(
            fresh.glob("data.000[0-8].dbl.h5")
        ),
        "C-HI fresh intermediate double HDF5 remains",
    )
    require(
        [path.name for path in fresh.glob("particles.*.dbl")]
        == ["particles.4277.dbl"],
        "C-HI fresh particle retention set differs from particles.4277.dbl",
    )

    prod = output_root(runs_root, C_HI_PROD, "C-HI")
    require_regular(prod / "data.0011.dbl.h5")
    require_regular(prod / "particles.5000.dbl")
    require(not (prod / "data.0010.dbl.h5").exists(), "C-HI prod64 data.0010 remains")
    validate_symlink(prod / "data.0009.dbl.h5", fresh / "data.0009.dbl.h5")
    validate_symlink(prod / "particles.4277.dbl", fresh / "particles.4277.dbl")

    g_lo = output_root(runs_root, G_LO_SOURCE, "G-LO")
    require_regular(g_lo / "data.0002.dbl.h5")
    require(not (g_lo / "data.0003.dbl.h5").exists(), "invalid G-LO data.0003 remains")


def run_compaction(
    *,
    runs_root: Path,
    stage_root: Path,
    execute: bool,
    expected_float_size: int | None = DEFAULT_FLOAT_HDF5_SIZE,
) -> dict[str, object]:
    runs_root = runs_root.resolve()
    stage_root = stage_root.resolve()
    log_root = stage_root / "remote_logs"
    log_root.mkdir(parents=True, exist_ok=True)
    preflight_report = preflight(
        runs_root,
        expected_float_size=expected_float_size,
    )
    roots = manifest_roots(runs_root)
    pre_rows = [tree_inventory(path) for path in roots]
    pre_manifest = log_root / "goal038_compaction_pre_manifest.csv"
    write_inventory(pre_manifest, pre_rows)
    before_bytes = sum(int(row["size_bytes"]) for row in pre_rows)

    summary: dict[str, object] = {
        "before_manifest_bytes": before_bytes,
        "execute": execute,
        "preflight": preflight_report,
        "runs_root": str(runs_root),
        "status": "dry_run_ready",
    }
    if execute:
        if preflight_report["c_lo_state"] == "segmented":
            move_c_lo_surfaces(runs_root)
        remove_superseded_data(runs_root)
        validate_postconditions(
            runs_root,
            expected_float_size=expected_float_size,
        )
        post_rows = [tree_inventory(path) for path in roots]
        post_manifest = log_root / "goal038_compaction_post_manifest.csv"
        write_inventory(post_manifest, post_rows)
        after_bytes = sum(int(row["size_bytes"]) for row in post_rows)
        summary.update(
            {
                "after_manifest_bytes": after_bytes,
                "freed_manifest_bytes": before_bytes - after_bytes,
                "status": "compaction_complete",
            }
        )
    atomic_write_text(
        log_root / "goal038_compaction_summary.json",
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=PRODUCTION_RUNS_ROOT)
    parser.add_argument("--stage-root", type=Path, default=PRODUCTION_STAGE_ROOT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-token")
    parser.add_argument(
        "--expected-float-size", type=int, default=DEFAULT_FLOAT_HDF5_SIZE
    )
    parser.add_argument("--allow-nonstandard-root", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.allow_nonstandard_root:
        require(
            args.runs_root.resolve() == PRODUCTION_RUNS_ROOT,
            f"refusing non-production runs root: {args.runs_root}",
        )
        require(
            args.stage_root.resolve() == PRODUCTION_STAGE_ROOT,
            f"refusing non-production stage root: {args.stage_root}",
        )
    if args.execute:
        require(
            args.approval_token == APPROVAL_TOKEN,
            "--execute requires the exact Goal 038 approval token",
        )
    summary = run_compaction(
        runs_root=args.runs_root,
        stage_root=args.stage_root,
        execute=args.execute,
        expected_float_size=args.expected_float_size,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompactionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
