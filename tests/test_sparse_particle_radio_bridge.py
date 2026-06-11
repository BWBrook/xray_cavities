from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/sparse_particle_radio_bridge.py")


def write_sparse_fixture(root: Path) -> Path:
    sparse_dir = root / "sparse"
    sparse_dir.mkdir()
    rows = [
        [0, 0.0, 0.0, 10, -1.0, 0.0, -2.0, 0.0, 0.01, 0.0, 0.0, 0.0, 0.80, 1.0e-3, 4.0e-8],
        [1, 1.0, 1.0, 10, -1.0, 0.0, -2.0, 0.0, 0.01, 0.0, 0.0, 1.0, 0.80, 1.0e-3, 3.0e-8],
        [2, 2.0, 2.0, 10, -1.0, 0.0, -2.0, 0.0, 0.01, 0.0, 0.0, 2.0, 0.80, 1.0e-3, 2.0e-8],
        [0, 0.0, 0.0, 20, 2.0, 0.0, 1.0, 0.0, -0.01, 0.0, 0.0, 0.0, 0.70, 2.0e-3, 3.0e-8],
        [1, 1.0, 1.0, 20, 2.0, 0.0, 1.0, 0.0, -0.01, 0.0, 0.0, 1.0, 0.70, 2.0e-3, 3.0e-8],
        [2, 2.0, 2.0, 20, 2.0, 0.0, 1.0, 0.0, -0.01, 0.0, 0.0, 2.0, 0.70, 2.0e-3, 3.0e-8],
        [2, 2.0, 2.0, 30, 0.0, 0.0, 0.0, 0.0, 0.00, 0.0, 0.0, 2.0, 0.10, 1.0e-3, 1.0e-8],
        [1, 1.0, 1.0, 40, 8.0, 0.0, 9.0, 0.0, 0.00, 0.0, 0.0, 1.0, 0.75, 1.0e-3, 8.0e-8],
        [2, 2.0, 2.0, 40, 8.0, 0.0, 9.0, 0.0, 0.00, 0.0, 0.0, 2.0, 0.75, 1.0e-3, 4.0e-8],
    ]
    with (sparse_dir / "particle_sparse_window_trajectory.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "output_index",
                "time_code",
                "time_myr",
                "id",
                "x_kpc",
                "y_kpc",
                "z_kpc",
                "vx1",
                "vx2",
                "vx3",
                "tinj_myr",
                "age_myr",
                "tracer",
                "density",
                "pressure",
            ]
        )
        writer.writerows(rows)

    (sparse_dir / "particle_sparse_window_metadata.json").write_text(
        json.dumps(
            {
                "target_index": 2,
                "window_indices": [0, 1, 2],
                "selected_id_count": 4,
                "trajectory_rows": len(rows),
            },
            indent=2,
        )
        + "\n"
    )
    return sparse_dir


def write_loss_table(
    path: Path,
    rows: list[list[object]],
    *,
    header: list[str] | None = None,
    delimiter: str = ",",
) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(header or ["id", "loss_factor"])
        writer.writerows(rows)


def bridge_command(sparse_dir: Path, output_dir: Path, extra_args: list[object] | None = None) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--sparse-window-dir",
        str(sparse_dir),
        "--output-dir",
        str(output_dir),
        "--target-index",
        "2",
        "--tracer-threshold",
        "0.5",
        "--xlim-kpc",
        "5",
        "--zlim-kpc",
        "5",
        "--pixel-kpc",
        "1",
        "--unit-volume-kpc3",
        "2",
    ]
    if extra_args:
        command.extend(str(arg) for arg in extra_args)
    return command


def run_bridge(tmp_path: Path, extra_args: list[object] | None = None) -> Path:
    sparse_dir = write_sparse_fixture(tmp_path)
    output_dir = tmp_path / "radio"
    subprocess.run(bridge_command(sparse_dir, output_dir, extra_args), check=True)
    return output_dir


def run_bridge_failure(tmp_path: Path, loss_rows: list[list[object]]) -> str:
    sparse_dir = write_sparse_fixture(tmp_path)
    loss_table = tmp_path / "loss_table.csv"
    write_loss_table(loss_table, loss_rows)
    output_dir = tmp_path / "radio"
    result = subprocess.run(
        bridge_command(sparse_dir, output_dir, ["--loss-table", loss_table]),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    return result.stdout + result.stderr


def test_sparse_radio_bridge_writes_proxy_maps_and_particle_rows(tmp_path: Path) -> None:
    output_dir = run_bridge(tmp_path)

    metadata = json.loads((output_dir / "sparse_particle_radio_metadata.json").read_text())
    assert metadata["target_index"] == 2
    assert metadata["selected_particles"] == 3
    assert metadata["in_frame_particles"] == 2
    assert metadata["loss_model"] == "pressure-history attenuation proxy"
    assert metadata["volume_assignment"] == "2.0 kpc^3 per selected particle"
    assert metadata["map_shape"] == [10, 10]

    lossy = np.loadtxt(output_dir / "radio_150mhz_sparse_loss_proxy_mjy_sr.tsv", delimiter="\t")
    lossless = np.loadtxt(output_dir / "radio_150mhz_sparse_lossless_mjy_sr.tsv", delimiter="\t")
    counts = np.loadtxt(output_dir / "radio_sparse_particle_count_map.tsv", delimiter="\t")
    mean_loss = np.loadtxt(output_dir / "radio_sparse_mean_loss_proxy.tsv", delimiter="\t")
    assert lossy.shape == (10, 10)
    assert lossless.shape == (10, 10)
    assert counts.sum() == 2
    assert np.count_nonzero(lossy > 0) == 2
    assert np.nanmax(mean_loss) == 1.0
    assert np.nanmin(mean_loss[mean_loss > 0]) == 0.5

    with (output_dir / "sparse_particle_radio_positions_0deg.tsv").open() as handle:
        rows = {int(row["id"]): row for row in csv.DictReader(handle, delimiter="\t")}
    assert sorted(rows) == [10, 20, 40]
    assert float(rows[10]["loss_proxy"]) == 0.5
    assert float(rows[20]["loss_proxy"]) == 1.0
    assert float(rows[40]["loss_proxy"]) == 0.5
    assert float(rows[10]["pressure_history_max"]) == 4.0e-8


def test_sparse_radio_bridge_uses_external_loss_table_by_particle_id(tmp_path: Path) -> None:
    sparse_dir = write_sparse_fixture(tmp_path)
    loss_table = tmp_path / "loss_table.csv"
    write_loss_table(
        loss_table,
        [
            [40, 2.0],
            [10, 1.5],
            [20, 0.25],
            [999, 8.0],
        ],
    )
    output_dir = tmp_path / "radio"
    subprocess.run(
        bridge_command(sparse_dir, output_dir, ["--loss-table", loss_table]),
        check=True,
    )

    metadata = json.loads((output_dir / "sparse_particle_radio_metadata.json").read_text())
    assert metadata["loss_model_key"] == "external_praise_compatible"
    assert metadata["loss_model"] == "external PRAiSE-compatible particle loss table"
    assert metadata["loss_table"]["matched_selected_ids"] == 3
    assert metadata["loss_table"]["extra_ids"] == 1
    assert metadata["loss_map_file"] == "radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv"
    assert metadata["mean_loss_map_file"] == "radio_sparse_mean_external_praise_loss.tsv"
    assert (output_dir / metadata["loss_map_file"]).exists()
    assert (output_dir / metadata["mean_loss_map_file"]).exists()

    mean_loss = np.loadtxt(output_dir / metadata["mean_loss_map_file"], delimiter="\t")
    assert np.nanmax(mean_loss) == 1.5
    assert np.nanmin(mean_loss[mean_loss > 0]) == 0.25

    with (output_dir / "sparse_particle_radio_positions_0deg.tsv").open() as handle:
        rows = {int(row["id"]): row for row in csv.DictReader(handle, delimiter="\t")}
    assert float(rows[10]["loss_factor"]) == 1.5
    assert float(rows[20]["loss_factor"]) == 0.25
    assert float(rows[40]["loss_factor"]) == 2.0

    with (output_dir / "sparse_particle_radio_lobe_summary.csv").open() as handle:
        lobe_rows = {row["side"]: row for row in csv.DictReader(handle)}
    assert float(lobe_rows["negative_z"]["loss_factor_mean"]) == 1.5
    assert float(lobe_rows["positive_z"]["loss_factor_min"]) == 0.25
    assert float(lobe_rows["positive_z"]["loss_factor_max"]) == 2.0


def test_sparse_radio_bridge_accepts_tsv_loss_table_with_custom_columns(tmp_path: Path) -> None:
    sparse_dir = write_sparse_fixture(tmp_path)
    loss_table = tmp_path / "loss_table.tsv"
    write_loss_table(
        loss_table,
        [
            [20, 0.4],
            [40, 1.2],
            [10, 0.8],
        ],
        header=["particle_id", "praise_loss"],
        delimiter="\t",
    )
    output_dir = tmp_path / "radio"
    subprocess.run(
        bridge_command(
            sparse_dir,
            output_dir,
            [
                "--loss-table",
                loss_table,
                "--loss-id-column",
                "particle_id",
                "--loss-factor-column",
                "praise_loss",
            ],
        ),
        check=True,
    )

    metadata = json.loads((output_dir / "sparse_particle_radio_metadata.json").read_text())
    assert metadata["loss_table"]["delimiter"] == "tab"
    assert metadata["loss_table"]["id_column"] == "particle_id"
    assert metadata["loss_table"]["loss_factor_column"] == "praise_loss"
    assert metadata["loss_table"]["matched_selected_ids"] == 3

    with (output_dir / "sparse_particle_radio_positions_0deg.tsv").open() as handle:
        rows = {int(row["id"]): row for row in csv.DictReader(handle, delimiter="\t")}
    assert float(rows[10]["loss_factor"]) == 0.8
    assert float(rows[20]["loss_factor"]) == 0.4
    assert float(rows[40]["loss_factor"]) == 1.2


@pytest.mark.parametrize(
    ("loss_rows", "expected_message"),
    [
        ([[10, 1.0], [40, 0.5]], "missing loss factors for selected particle IDs: 20"),
        ([[10, 1.0], [10, 0.9], [20, 0.5], [40, 0.5]], "duplicate loss-table particle ID: 10"),
        ([[10, 1.0], [20.5, 0.5], [40, 0.5]], "loss-table id value on row 2 must be an integer particle ID"),
        ([[10, 1.0], [20, "nan"], [40, 0.5]], "loss factor for particle ID 20 must be finite"),
        ([[10, 1.0], [20, -0.1], [40, 0.5]], "loss factor for particle ID 20 must be non-negative"),
    ],
)
def test_sparse_radio_bridge_rejects_unsafe_external_loss_tables(
    tmp_path: Path,
    loss_rows: list[list[object]],
    expected_message: str,
) -> None:
    message = run_bridge_failure(tmp_path, loss_rows)
    assert expected_message in message


def test_sparse_radio_bridge_reports_missing_configured_loss_table_columns(tmp_path: Path) -> None:
    sparse_dir = write_sparse_fixture(tmp_path)
    loss_table = tmp_path / "loss_table.csv"
    write_loss_table(loss_table, [[10, 1.0], [20, 0.5], [40, 0.5]])
    output_dir = tmp_path / "radio"
    result = subprocess.run(
        bridge_command(
            sparse_dir,
            output_dir,
            [
                "--loss-table",
                loss_table,
                "--loss-id-column",
                "particle_id",
                "--loss-factor-column",
                "praise_loss",
            ],
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "missing columns: particle_id, praise_loss" in result.stdout + result.stderr


def test_sparse_radio_bridge_reports_lobe_proxy_luminosities(tmp_path: Path) -> None:
    output_dir = run_bridge(tmp_path)
    with (output_dir / "sparse_particle_radio_lobe_summary.csv").open() as handle:
        rows = {row["side"]: row for row in csv.DictReader(handle)}

    assert rows["negative_z"]["particle_count"] == "1"
    assert rows["positive_z"]["particle_count"] == "2"
    assert rows["bipolar_total"]["particle_count"] == "3"
    assert float(rows["negative_z"]["loss_proxy_mean"]) == 0.5
    assert float(rows["positive_z"]["loss_proxy_min"]) == 0.5
    assert float(rows["positive_z"]["loss_proxy_max"]) == 1.0
    assert float(rows["bipolar_total"]["lossy_luminosity_doppler_w_hz"]) > 0

    with (output_dir / "sparse_particle_radio_summary.csv").open() as handle:
        summary_rows = list(csv.DictReader(handle))
    metrics = {row["metric"]: row for row in summary_rows}
    assert metrics["selected_particles"]["value"] == "3"
    assert metrics["in_frame_particles"]["value"] == "2"
    assert "positive_z_lossy_luminosity_doppler" in metrics
