from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_final_volume_coupled_comparison.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_final_volume_coupled_comparison", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metric_csv(path: Path) -> None:
    write_csv(
        path,
        [
            {"metric": "time_myr", "value": 50.0, "unit": "Myr"},
            {"metric": "injected_energy_bipolar_elapsed", "value": 3.15576e60, "unit": "erg"},
        ],
        ["metric", "value", "unit"],
    )


def truth_rows(*, negative_volume: float = 120.0, positive_volume: float = 180.0) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for threshold in ("1e-03", "5e-03", "1e-02"):
        scale = 1.0 if threshold == "5e-03" else 0.5
        neg = negative_volume * scale
        pos = positive_volume * scale
        rows.extend(
            [
                {
                    "threshold": threshold,
                    "side": "negative_z",
                    "time_myr": 50.0,
                    "cell_count": 10,
                    "volume_kpc3": neg,
                    "total_energy_erg": neg * 1.0e56,
                    "z_min_kpc": -215.0,
                    "z_max_kpc": -0.1,
                },
                {
                    "threshold": threshold,
                    "side": "positive_z",
                    "time_myr": 50.0,
                    "cell_count": 12,
                    "volume_kpc3": pos,
                    "total_energy_erg": pos * 1.0e56,
                    "z_min_kpc": 0.1,
                    "z_max_kpc": 216.0,
                },
                {
                    "threshold": threshold,
                    "side": "bipolar_total",
                    "time_myr": 50.0,
                    "cell_count": 22,
                    "volume_kpc3": neg + pos,
                    "total_energy_erg": (neg + pos) * 1.0e56,
                    "z_min_kpc": -215.0,
                    "z_max_kpc": 216.0,
                },
            ]
        )
    return rows


def write_level2(path: Path, rows: list[dict[str, object]]) -> None:
    write_csv(
        path,
        rows,
        [
            "threshold",
            "side",
            "time_myr",
            "cell_count",
            "volume_kpc3",
            "total_energy_erg",
            "z_min_kpc",
            "z_max_kpc",
        ],
    )


def bridge_rows(*, negative_volume: float, positive_volume: float, negative_lum: float, positive_lum: float):
    return [
        {
            "side": "negative_z",
            "particle_count": 4,
            "volume_kpc3": negative_volume,
            "lossy_luminosity_doppler_w_hz": negative_lum,
            "lossless_luminosity_doppler_w_hz": negative_lum * 1.1,
            "loss_factor_mean": 0.9,
        },
        {
            "side": "positive_z",
            "particle_count": 6,
            "volume_kpc3": positive_volume,
            "lossy_luminosity_doppler_w_hz": positive_lum,
            "lossless_luminosity_doppler_w_hz": positive_lum * 1.1,
            "loss_factor_mean": 1.1,
        },
        {
            "side": "bipolar_total",
            "particle_count": 10,
            "volume_kpc3": negative_volume + positive_volume,
            "lossy_luminosity_doppler_w_hz": negative_lum + positive_lum,
            "lossless_luminosity_doppler_w_hz": (negative_lum + positive_lum) * 1.1,
            "loss_factor_mean": 1.02,
        },
    ]


def write_bridge_dir(
    path: Path,
    *,
    negative_volume: float,
    positive_volume: float,
    negative_lum: float,
    positive_lum: float,
    volume_assignment: str,
) -> None:
    rows = bridge_rows(
        negative_volume=negative_volume,
        positive_volume=positive_volume,
        negative_lum=negative_lum,
        positive_lum=positive_lum,
    )
    write_csv(
        path / "sparse_particle_radio_lobe_summary.csv",
        rows,
        list(rows[0]),
    )
    write_csv(
        path / "sparse_particle_radio_summary.csv",
        [
            {"metric": "selected_particles", "value": 10, "unit": "count"},
            {"metric": "radio_map_sum_mjy_sr_pixel", "value": 12.5, "unit": "mJy/sr_pixel_sum"},
            {
                "metric": "bipolar_total_lossy_luminosity_doppler",
                "value": negative_lum + positive_lum,
                "unit": "W/Hz",
            },
        ],
        ["metric", "value", "unit"],
    )
    metadata = {
        "loss_model_key": "external_praise_compatible",
        "volume_assignment": volume_assignment,
        "loss_table": {"matched_selected_ids": 10, "extra_ids": 0, "table_rows": 10},
    }
    (path / "sparse_particle_radio_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


def build_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    truth_dir = tmp_path / "truth"
    old_dir = tmp_path / "old_bridge"
    new_dir = tmp_path / "new_bridge"
    write_metric_csv(truth_dir / "level1_injected_energy.csv")
    write_level2(truth_dir / "level2_tracer_lobe_truth.csv", truth_rows())
    write_bridge_dir(
        old_dir,
        negative_volume=4.0,
        positive_volume=6.0,
        negative_lum=2.0e27,
        positive_lum=3.0e27,
        volume_assignment="1.0 kpc^3 per selected particle",
    )
    write_bridge_dir(
        new_dir,
        negative_volume=120.0,
        positive_volume=180.0,
        negative_lum=6.0e28,
        positive_lum=9.0e28,
        volume_assignment="declared side volumes divided evenly across selected particles",
    )
    return truth_dir, old_dir, new_dir


def test_select_declared_volumes_uses_default_threshold_and_validates_bipolar_sum(tmp_path: Path) -> None:
    module = load_script_module()
    level2_path = tmp_path / "level2_tracer_lobe_truth.csv"
    write_level2(level2_path, truth_rows())

    selected = module.select_declared_volumes(module.read_rows(level2_path), threshold=5.0e-3)

    assert selected["negative_z"]["volume_kpc3"] == 120.0
    assert selected["positive_z"]["volume_kpc3"] == 180.0
    assert selected["bipolar_total"]["volume_kpc3"] == 300.0


def test_select_declared_volumes_rejects_missing_threshold_side_row(tmp_path: Path) -> None:
    module = load_script_module()
    rows = [row for row in truth_rows() if not (row["threshold"] == "5e-03" and row["side"] == "positive_z")]

    with pytest.raises(ValueError, match="missing Level 2 truth row"):
        module.select_declared_volumes(rows, threshold=5.0e-3)


def test_select_declared_volumes_rejects_nonpositive_side_volume() -> None:
    module = load_script_module()
    rows = truth_rows(negative_volume=0.0)

    with pytest.raises(ValueError, match="negative_z volume_kpc3 must be finite and positive"):
        module.select_declared_volumes(rows, threshold=5.0e-3)


def test_validate_bridge_lobe_volumes_match_declared_truth(tmp_path: Path) -> None:
    module = load_script_module()
    truth_dir, _old_dir, new_dir = build_fixture(tmp_path)
    truth = module.select_declared_volumes(
        module.read_rows(truth_dir / "level2_tracer_lobe_truth.csv"),
        threshold=5.0e-3,
    )
    lobe_rows = module.read_rows(new_dir / "sparse_particle_radio_lobe_summary.csv")
    metadata = json.loads((new_dir / "sparse_particle_radio_metadata.json").read_text())

    module.validate_volume_coupled_bridge(truth, lobe_rows, metadata)


def test_validate_bridge_lobe_volumes_rejects_proxy_assignment(tmp_path: Path) -> None:
    module = load_script_module()
    truth_dir, old_dir, _new_dir = build_fixture(tmp_path)
    truth = module.select_declared_volumes(
        module.read_rows(truth_dir / "level2_tracer_lobe_truth.csv"),
        threshold=5.0e-3,
    )
    lobe_rows = module.read_rows(old_dir / "sparse_particle_radio_lobe_summary.csv")
    metadata = json.loads((old_dir / "sparse_particle_radio_metadata.json").read_text())

    with pytest.raises(ValueError, match="declared side volumes"):
        module.validate_volume_coupled_bridge(truth, lobe_rows, metadata)


def test_lobe_comparison_reports_volume_and_luminosity_scale_factors(tmp_path: Path) -> None:
    module = load_script_module()
    _truth_dir, old_dir, new_dir = build_fixture(tmp_path)

    comparison = module.compare_lobes(
        module.read_rows(old_dir / "sparse_particle_radio_lobe_summary.csv"),
        module.read_rows(new_dir / "sparse_particle_radio_lobe_summary.csv"),
    )

    by_side = {row["side"]: row for row in comparison}
    assert by_side["negative_z"]["volume_scale_factor"] == 30.0
    assert by_side["positive_z"]["volume_scale_factor"] == 30.0
    assert by_side["bipolar_total"]["luminosity_scale_factor"] == 30.0


def test_comparison_cli_writes_machine_readable_outputs(tmp_path: Path) -> None:
    truth_dir, old_dir, new_dir = build_fixture(tmp_path)
    output_dir = tmp_path / "comparison"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--truth-dir",
            str(truth_dir),
            "--old-bridge-dir",
            str(old_dir),
            "--volume-coupled-bridge-dir",
            str(new_dir),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    comparison_rows = list(csv.DictReader((output_dir / "lobe_volume_coupling_comparison.csv").open()))
    assert {row["side"] for row in comparison_rows} == {"negative_z", "positive_z", "bipolar_total"}

    summary = json.loads((output_dir / "comparison_metadata.json").read_text())
    assert summary["threshold"] == "5e-03"
    assert summary["declared_volumes_kpc3"]["negative_z"] == 120.0
    assert summary["bridge_validation"]["loss_model_key"] == "external_praise_compatible"
    assert (output_dir / "comparison_summary.md").exists()
