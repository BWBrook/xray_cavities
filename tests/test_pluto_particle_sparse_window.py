from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path("scripts/science/pluto_particle_sparse_window.py")


FIELD_NAMES = [
    "id",
    "x1",
    "x2",
    "x3",
    "vx1",
    "vx2",
    "vx3",
    "tinj",
    "color",
    "tracer",
    "last_shock_time",
    "density",
    "pressure",
]
FIELD_DIMS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1]


def row(
    particle_id: int,
    *,
    x: float,
    y: float,
    z: float,
    tinj: float,
    tracer: float,
    density: float = 1.0e-3,
    pressure: float = 1.0e-8,
) -> list[float]:
    return [
        float(particle_id),
        x,
        y,
        z,
        0.01 * particle_id,
        0.02 * particle_id,
        0.03 * particle_id,
        tinj,
        0.0,
        tracer,
        tinj,
        tinj + 0.5,
        tinj + 1.0,
        density,
        pressure,
    ]


def write_particle_file(path: Path, *, output_index: int, time_code: float, rows: list[list[float]]) -> None:
    header = "".join(
        [
            f"# field_names {' '.join(FIELD_NAMES)}\n",
            "# field_dim " + " ".join(str(value) for value in FIELD_DIMS) + "\n",
            f"# nparticles {len(rows)}\n",
            f"# time {time_code}\n",
            f"# stepNumber {1000 + output_index}\n",
            "# endianity little\n",
        ]
    ).encode("ascii")
    matrix = np.asarray(rows, dtype="<f8")
    path.write_bytes(header + matrix.tobytes())


def build_window(tmp_path: Path) -> Path:
    particle_dir = tmp_path / "particles"
    particle_dir.mkdir()
    write_particle_file(
        particle_dir / "particles.0000.dbl",
        output_index=0,
        time_code=0.0,
        rows=[
            row(1, x=-1.0, y=0.0, z=-1.0, tinj=0.0, tracer=0.1),
            row(2, x=-2.0, y=0.0, z=-2.0, tinj=0.0, tracer=0.6),
            row(3, x=3.0, y=0.0, z=3.0, tinj=0.0, tracer=0.8),
            row(4, x=4.0, y=0.0, z=4.0, tinj=0.0, tracer=0.7),
        ],
    )
    write_particle_file(
        particle_dir / "particles.0001.dbl",
        output_index=1,
        time_code=10.0,
        rows=[
            row(1, x=-1.5, y=0.0, z=-1.5, tinj=0.0, tracer=0.1),
            row(2, x=-2.5, y=0.0, z=-2.5, tinj=0.0, tracer=0.6),
            row(3, x=3.5, y=0.0, z=3.5, tinj=0.0, tracer=0.8),
        ],
    )
    write_particle_file(
        particle_dir / "particles.0002.dbl",
        output_index=2,
        time_code=20.0,
        rows=[
            row(1, x=-2.0, y=0.0, z=-2.0, tinj=0.0, tracer=0.1),
            row(2, x=-3.0, y=0.0, z=-3.0, tinj=0.0, tracer=0.6),
            row(3, x=4.0, y=0.0, z=4.0, tinj=0.0, tracer=0.8),
            row(4, x=5.0, y=0.0, z=5.0, tinj=0.0, tracer=0.7),
        ],
    )
    return particle_dir


def run_sparse_window(tmp_path: Path) -> Path:
    particle_dir = build_window(tmp_path)
    output_dir = tmp_path / "out"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--particle-dir",
            str(particle_dir),
            "--output-dir",
            str(output_dir),
            "--start-index",
            "0",
            "--end-index",
            "2",
            "--target-index",
            "2",
            "--stride",
            "1",
            "--tracer-threshold",
            "0.5",
            "--max-selected-ids",
            "2",
            "--code-time-per-myr",
            "10",
        ],
        check=True,
    )
    return output_dir


def test_sparse_window_selects_target_ids_and_writes_trajectory(tmp_path: Path) -> None:
    output_dir = run_sparse_window(tmp_path)
    metadata = json.loads((output_dir / "particle_sparse_window_metadata.json").read_text())
    assert metadata["window_indices"] == [0, 1, 2]
    assert metadata["target_candidate_count"] == 3
    assert metadata["selected_id_count"] == 2
    assert metadata["selected_ids"] == [2, 4]
    assert metadata["trajectory_rows"] == 5

    with (output_dir / "particle_sparse_window_trajectory.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [(int(row["output_index"]), int(row["id"])) for row in rows] == [
        (0, 2),
        (0, 4),
        (1, 2),
        (2, 2),
        (2, 4),
    ]
    assert rows[-1]["time_myr"] == "2.0"
    assert rows[-1]["age_myr"] == "2.0"
    assert rows[-1]["z_kpc"] == "5.0"


def test_sparse_window_reports_lifecycle_and_side_counts(tmp_path: Path) -> None:
    output_dir = run_sparse_window(tmp_path)
    with (output_dir / "particle_sparse_window_lifecycle.csv").open() as handle:
        lifecycle = {int(row["id"]): row for row in csv.DictReader(handle)}
    assert lifecycle[2]["output_count"] == "3"
    assert lifecycle[2]["present_fraction"] == "1.0"
    assert lifecycle[4]["output_count"] == "2"
    assert lifecycle[4]["present_fraction"] == "0.6666666666666666"
    assert lifecycle[4]["first_output"] == "0"
    assert lifecycle[4]["last_output"] == "2"

    with (output_dir / "particle_sparse_window_summary.csv").open() as handle:
        summary = {int(row["output_index"]): row for row in csv.DictReader(handle)}
    assert summary[1]["selected_present_count"] == "1"
    assert summary[1]["selected_missing_count"] == "1"
    assert summary[2]["target_candidate_count"] == "3"

    with (output_dir / "particle_sparse_window_side_summary.csv").open() as handle:
        side_rows = {
            (int(row["output_index"]), row["side"]): row
            for row in csv.DictReader(handle)
        }
    assert side_rows[(0, "negative_z")]["particle_count"] == "2"
    assert side_rows[(0, "positive_z")]["particle_count"] == "2"
    assert side_rows[(1, "positive_z")]["selected_present_count"] == "0"
