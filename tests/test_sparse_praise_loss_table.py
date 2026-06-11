from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path("scripts/science/sparse_praise_loss_table.py")

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


def load_script_module():
    spec = importlib.util.spec_from_file_location("sparse_praise_loss_table", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def particle_row(
    particle_id: int,
    *,
    density: float,
    pressure: float,
    tracer: float = 0.8,
    last_shock_time: float = 0.5,
) -> list[float]:
    return [
        float(particle_id),
        0.1 * particle_id,
        0.0,
        0.2 * particle_id,
        0.01,
        0.0,
        0.02,
        0.0,
        0.0,
        tracer,
        last_shock_time - 0.2,
        last_shock_time - 0.1,
        last_shock_time,
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


def build_particle_fixture(tmp_path: Path) -> tuple[Path, Path]:
    particle_dir = tmp_path / "particles"
    particle_dir.mkdir()
    write_particle_file(
        particle_dir / "particles.0000.dbl",
        output_index=0,
        time_code=0.0,
        rows=[
            particle_row(2, density=1.0e-3, pressure=2.0e-8),
            particle_row(4, density=2.0e-3, pressure=4.0e-8),
        ],
    )
    write_particle_file(
        particle_dir / "particles.0001.dbl",
        output_index=1,
        time_code=10.0,
        rows=[
            particle_row(2, density=1.5e-3, pressure=3.0e-8),
        ],
    )
    write_particle_file(
        particle_dir / "particles.0002.dbl",
        output_index=2,
        time_code=20.0,
        rows=[
            particle_row(2, density=2.0e-3, pressure=4.0e-8),
            particle_row(4, density=4.0e-3, pressure=8.0e-8),
            particle_row(6, density=6.0e-3, pressure=1.2e-7),
        ],
    )

    sparse_dir = tmp_path / "sparse"
    sparse_dir.mkdir()
    (sparse_dir / "particle_sparse_window_metadata.json").write_text(
        json.dumps(
            {
                "target_index": 2,
                "window_indices": [0, 1, 2],
                "selected_ids": [2, 4],
                "selected_id_count": 2,
                "code_time_per_myr": 10.0,
            },
            indent=2,
        )
        + "\n"
    )
    return particle_dir, sparse_dir


def write_fake_xraise(path: Path) -> None:
    path.write_text(
        """
import numpy as np

class FakeQuantity:
    def __init__(self, values):
        self.values = values

    def to_value(self, unit):
        return self.values

def praise(**kwargs):
    part_data = kwargs["part_data"]
    density = np.nan_to_num(part_data["density"][:, -1], nan=0.0)
    loss = density.reshape((-1, 1, 1)) * 1000.0
    return {"full": [{"emis": FakeQuantity(loss), "part_output": part_data["density"].shape[1] - 1}]}
""".lstrip()
    )


def test_sparse_praise_shaper_reads_selected_id_particle_matrices(tmp_path: Path) -> None:
    module = load_script_module()
    particle_dir, sparse_dir = build_particle_fixture(tmp_path)

    shaped = module.build_sparse_particle_data(
        particle_dir=particle_dir,
        sparse_window_dir=sparse_dir,
        max_selected_ids=0,
    )

    assert shaped.selected_ids == [2, 4]
    assert shaped.output_indices == [0, 1, 2]
    assert shaped.part_times.tolist() == [0.0, 10.0, 20.0]
    assert shaped.part_data["density"].shape == (2, 3)
    assert shaped.part_data["last_shock_time"].shape == (2, 3, 3)
    assert np.isnan(shaped.part_data["density"][1, 1])
    assert shaped.present_counts == [2, 1, 2]
    assert shaped.missing_counts == [0, 1, 0]


def test_sparse_praise_shaper_rejects_selected_id_missing_at_target(tmp_path: Path) -> None:
    module = load_script_module()
    particle_dir, sparse_dir = build_particle_fixture(tmp_path)
    metadata_path = sparse_dir / "particle_sparse_window_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["selected_ids"] = [2, 4, 8]
    metadata["selected_id_count"] = 3
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    with np.testing.assert_raises_regex(ValueError, "1 selected IDs are missing at target output 2"):
        module.build_sparse_particle_data(
            particle_dir=particle_dir,
            sparse_window_dir=sparse_dir,
            max_selected_ids=0,
        )


def test_validate_loss_factors_rejects_nonfinite_values() -> None:
    module = load_script_module()

    with np.testing.assert_raises_regex(ValueError, "particle ID 4 must be finite"):
        module.validate_loss_factors([2, 4], np.array([1.0, np.nan]))


def test_validate_loss_factors_rejects_negative_values() -> None:
    module = load_script_module()

    with np.testing.assert_raises_regex(ValueError, "particle ID 2 must be non-negative"):
        module.validate_loss_factors([2, 4], np.array([-0.1, 1.0]))


def test_validate_loss_factors_rejects_count_mismatch() -> None:
    module = load_script_module()

    with np.testing.assert_raises_regex(ValueError, "loss factor count 1 does not match selected ID count 2"):
        module.validate_loss_factors([2, 4], np.array([1.0]))


def test_deterministic_subset_returns_stable_bounded_ids() -> None:
    module = load_script_module()

    ids = [10, 20, 30, 40, 50]
    assert module.deterministic_subset(ids, 0) == ids
    assert module.deterministic_subset(ids, 10) == ids
    assert module.deterministic_subset(ids, 1) == [10]
    assert module.deterministic_subset(ids, 3) == [10, 30, 50]


def test_sparse_praise_loss_table_cli_writes_id_keyed_table_with_fake_xraise(tmp_path: Path) -> None:
    particle_dir, sparse_dir = build_particle_fixture(tmp_path)
    fake_xraise = tmp_path / "fake_xraise.py"
    write_fake_xraise(fake_xraise)
    output_dir = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--particle-dir",
            str(particle_dir),
            "--sparse-window-dir",
            str(sparse_dir),
            "--xraise-py",
            str(fake_xraise),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    with (output_dir / "sparse_praise_loss_table.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert [int(row["id"]) for row in rows] == [2, 4]
    assert [float(row["loss_factor"]) for row in rows] == [2.0, 4.0]

    metadata = json.loads((output_dir / "sparse_praise_loss_metadata.json").read_text())
    assert metadata["selected_id_count"] == 2
    assert metadata["loss_factor_stats"]["finite_count"] == 2
    assert metadata["loss_factor_stats"]["min"] == 2.0
    assert metadata["coverage"]["missing_at_target"] == 0
