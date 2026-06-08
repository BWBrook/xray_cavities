from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


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


def run_bridge(tmp_path: Path) -> Path:
    sparse_dir = write_sparse_fixture(tmp_path)
    output_dir = tmp_path / "radio"
    subprocess.run(
        [
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
        ],
        check=True,
    )
    return output_dir


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
