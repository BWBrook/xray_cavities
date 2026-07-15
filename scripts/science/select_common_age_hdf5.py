#!/usr/bin/env python3
"""Select common physical-age PLUTO float HDF5 surfaces.

Selection is based on each timestep group's ``Time`` attribute.  Output-file
indices are retained only as provenance; they are never used as an age proxy.
"""

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import h5py


CODE_TIME_PER_MYR = 306.6013937879523
TARGET_AGES_MYR = (10, 20, 30, 40, 50)
SELECTION_TOLERANCE_MYR = 0.05
BASELINE_ZERO_TOLERANCE_MYR = 1.0e-6
REQUIRED_DATASETS = ("rho", "prs", "tr1", "vx1", "vx2", "vx3")
FILE_PATTERN = re.compile(r"^data\.(?P<index>[0-9]+)\.flt\.h5$")
MANIFEST_FIELDS = (
    "case", "nominal_age_myr", "actual_time_myr", "time_code", "input_h5",
    "timestep", "output_index", "file_size_bytes", "grid_shape_nz_ny_nx",
    "jet_power_erg_s", "baseline_h5", "baseline_timestep", "baseline_time_code",
    "baseline_time_myr", "baseline_file_size_bytes", "baseline_grid_shape_nz_ny_nx", "action",
    "compute_xray", "compute_truth_cavity", "compute_level3", "endpoint_reuse_id",
    "selection_status",
)


@dataclass(frozen=True)
class Snapshot:
    input_h5: Path
    timestep: str
    output_index: int
    time_code: float
    shape: tuple[int, int, int]
    file_size_bytes: int

    @property
    def actual_time_myr(self) -> float:
        return self.time_code / CODE_TIME_PER_MYR


def _read_time(group: h5py.Group, *, context: str) -> float:
    if "Time" not in group.attrs:
        raise ValueError(f"missing Time attribute in {context}")
    value = float(group.attrs["Time"])
    if not math.isfinite(value):
        raise ValueError(f"non-finite Time attribute in {context}")
    return value


def inspect_file(path: Path, *, output_index: int | None = None) -> list[Snapshot]:
    """Inspect every timestep group in one HDF5 file."""

    if not path.is_file():
        raise ValueError(f"missing HDF5 file: {path}")
    if output_index is None:
        match = FILE_PATTERN.match(path.name)
        if match is None:
            raise ValueError(f"cannot derive output index from {path.name}")
        output_index = int(match.group("index"))
    snapshots: list[Snapshot] = []
    with h5py.File(path, "r") as h5:
        timestep_groups = [
            (name, obj) for name, obj in h5.items()
            if isinstance(obj, h5py.Group) and "vars" in obj
        ]
        if not timestep_groups:
            raise ValueError(f"no timestep groups with vars found in {path}")
        for timestep, group in sorted(timestep_groups):
            time_code = _read_time(group, context=f"{path}:{timestep}")
            variables = group["vars"]
            shapes: list[tuple[int, ...]] = []
            for dataset_name in REQUIRED_DATASETS:
                if dataset_name not in variables:
                    raise ValueError(f"missing dataset {timestep}/vars/{dataset_name} in {path}")
                shape = tuple(int(value) for value in variables[dataset_name].shape)
                if len(shape) != 3:
                    raise ValueError(f"dataset {timestep}/vars/{dataset_name} is not 3-D in {path}")
                shapes.append(shape)
            if len(set(shapes)) != 1:
                raise ValueError(f"dataset shape mismatch in {path}:{timestep}: {shapes}")
            snapshots.append(Snapshot(path, timestep, output_index, time_code, shapes[0], path.stat().st_size))
    return snapshots


def inspect_outputs(outputs_dir: Path) -> list[Snapshot]:
    """Inspect all deterministic ``data.*.flt.h5`` files in a directory."""

    if not outputs_dir.is_dir():
        raise ValueError(f"outputs directory does not exist: {outputs_dir}")
    paths: list[tuple[int, Path]] = []
    for path in outputs_dir.iterdir():
        match = FILE_PATTERN.match(path.name)
        if match:
            paths.append((int(match.group("index")), path))
    if not paths:
        raise ValueError(f"no data.*.flt.h5 files found in {outputs_dir}")
    snapshots: list[Snapshot] = []
    expected_shape: tuple[int, int, int] | None = None
    for output_index, path in sorted(paths, key=lambda item: (item[0], item[1].name)):
        file_snapshots = inspect_file(path, output_index=output_index)
        for snapshot in file_snapshots:
            if expected_shape is None:
                expected_shape = snapshot.shape
            elif snapshot.shape != expected_shape:
                raise ValueError(
                    f"inconsistent 3-D grid shape: {snapshot.shape} versus {expected_shape}"
                )
        snapshots.extend(file_snapshots)
    return snapshots


def inspect_output_dirs(outputs_dirs: list[Path] | tuple[Path, ...]) -> list[Snapshot]:
    """Inspect a promoted case chain split across one or more run segments."""

    if not outputs_dirs:
        raise ValueError("at least one outputs directory is required")
    snapshots: list[Snapshot] = []
    seen_paths: set[Path] = set()
    expected_shape: tuple[int, int, int] | None = None
    for outputs_dir in outputs_dirs:
        resolved = outputs_dir.resolve()
        if resolved in seen_paths:
            raise ValueError(f"duplicate outputs directory: {outputs_dir}")
        seen_paths.add(resolved)
        for snapshot in inspect_outputs(outputs_dir):
            if expected_shape is None:
                expected_shape = snapshot.shape
            elif snapshot.shape != expected_shape:
                raise ValueError(
                    f"inconsistent 3-D grid shape across promoted segments: "
                    f"{snapshot.shape} versus {expected_shape}"
                )
            snapshots.append(snapshot)
    return snapshots


def _validate_baseline(path: Path, timestep: str) -> Snapshot:
    snapshots = inspect_file(path, output_index=0)
    matches = [snapshot for snapshot in snapshots if snapshot.timestep == timestep]
    if len(matches) != 1:
        raise ValueError(f"baseline timestep {timestep!r} is not unique in {path}")
    return matches[0]


def select_snapshots(
    snapshots: list[Snapshot],
    *,
    target_ages_myr: tuple[int, ...] = TARGET_AGES_MYR,
    tolerance_myr: float = SELECTION_TOLERANCE_MYR,
) -> list[Snapshot]:
    """Select exactly one snapshot per target age, failing closed."""

    if tolerance_myr < 0.0 or not math.isfinite(tolerance_myr):
        raise ValueError("tolerance_myr must be finite and non-negative")
    selected: list[Snapshot] = []
    for target in target_ages_myr:
        matches = [
            snapshot for snapshot in snapshots
            if abs(snapshot.actual_time_myr - target) <= tolerance_myr
        ]
        if not matches:
            raise ValueError(f"missing target age {target} Myr")
        if len(matches) != 1:
            labels = ", ".join(f"{item.input_h5.name}:{item.timestep}" for item in matches)
            raise ValueError(f"ambiguous target age {target} Myr: {labels}")
        selected.append(matches[0])
    return selected


def select_manifest_rows(
    *,
    outputs_dir: Path | None = None,
    outputs_dirs: list[Path] | tuple[Path, ...] | None = None,
    case: str,
    jet_power_erg_s: float,
    baseline_h5: Path,
    baseline_timestep: str,
    tolerance_myr: float = SELECTION_TOLERANCE_MYR,
) -> list[dict[str, Any]]:
    """Build the deterministic five-age manifest for one case."""

    if not case or not math.isfinite(float(jet_power_erg_s)) or float(jet_power_erg_s) <= 0.0:
        raise ValueError("case and positive finite jet_power_erg_s are required")
    if outputs_dir is not None and outputs_dirs is not None:
        raise ValueError("use outputs_dir or outputs_dirs, not both")
    selected_dirs = list(outputs_dirs) if outputs_dirs is not None else ([outputs_dir] if outputs_dir is not None else [])
    snapshots = inspect_output_dirs(selected_dirs)
    baseline = _validate_baseline(baseline_h5, baseline_timestep)
    if abs(baseline.actual_time_myr) > BASELINE_ZERO_TOLERANCE_MYR:
        raise ValueError(
            "Level 3 baseline is not a zero-time surface: "
            f"{baseline.actual_time_myr:.16g} Myr"
        )
    selected = select_snapshots(snapshots, tolerance_myr=tolerance_myr)
    if any(snapshot.shape != baseline.shape for snapshot in selected):
        raise ValueError(
            f"baseline grid shape {baseline.shape} does not match all selected surfaces"
        )
    rows: list[dict[str, Any]] = []
    for nominal, snapshot in zip(TARGET_AGES_MYR, selected, strict=True):
        endpoint = nominal == 50
        rows.append({
            "case": case,
            "nominal_age_myr": nominal,
            "actual_time_myr": snapshot.actual_time_myr,
            "time_code": snapshot.time_code,
            "input_h5": str(snapshot.input_h5),
            "timestep": snapshot.timestep,
            "output_index": snapshot.output_index,
            "file_size_bytes": snapshot.file_size_bytes,
            "grid_shape_nz_ny_nx": "x".join(str(value) for value in snapshot.shape),
            "jet_power_erg_s": float(jet_power_erg_s),
            "baseline_h5": str(baseline_h5),
            "baseline_timestep": baseline_timestep,
            "baseline_time_code": baseline.time_code,
            "baseline_time_myr": baseline.actual_time_myr,
            "baseline_file_size_bytes": baseline.file_size_bytes,
            "baseline_grid_shape_nz_ny_nx": "x".join(str(value) for value in baseline.shape),
            "action": "reuse_endpoint_plus_level3" if endpoint else "compute_new",
            "compute_xray": "false" if endpoint else "true",
            "compute_truth_cavity": "false" if endpoint else "true",
            "compute_level3": "true",
            "endpoint_reuse_id": f"{case}:50myr",
            "selection_status": "selected",
        })
    return rows


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty source manifest")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MANIFEST_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs-dir", type=Path, action="append", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--jet-power-erg-s", type=float, required=True)
    parser.add_argument("--baseline-h5", type=Path, required=True)
    parser.add_argument("--baseline-timestep", default="Timestep_0")
    parser.add_argument("--tolerance-myr", type=float, default=SELECTION_TOLERANCE_MYR)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = select_manifest_rows(
        outputs_dirs=args.outputs_dir,
        case=args.case,
        jet_power_erg_s=args.jet_power_erg_s,
        baseline_h5=args.baseline_h5,
        baseline_timestep=args.baseline_timestep,
        tolerance_myr=args.tolerance_myr,
    )
    write_manifest(args.output, rows)
    print(f"source_time_manifest=written rows={len(rows)} path={args.output}")


if __name__ == "__main__":
    main()
