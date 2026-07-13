from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_three_case_truth_alignment.py")


def load_builder():
    spec = importlib.util.spec_from_file_location("truth_alignment_builder", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_level1_and_level2_are_selected_by_exact_metrics_and_thresholds(tmp_path: Path) -> None:
    builder = load_builder()
    level1 = tmp_path / "level1.csv"
    level1.write_text("metric,value,unit\nother,2,erg\ninjected_energy_bipolar_elapsed,42,erg\n")
    assert builder.parse_level1(level1)["injected_energy_bipolar_elapsed"] == 42.0

    level2 = tmp_path / "level2.csv"
    level2.write_text(
        "threshold,side,volume_kpc3,total_energy_erg\n"
        "1e-03,negative_z,1,10\n1e-03,positive_z,2,20\n1e-03,bipolar_total,3,30\n"
        "5e-03,negative_z,4,40\n5e-03,positive_z,5,50\n5e-03,bipolar_total,9,90\n"
        "1e-02,negative_z,7,70\n1e-02,positive_z,8,80\n1e-02,bipolar_total,15,150\n"
    )
    rows = builder.parse_level2(level2)
    assert rows["5e-3"]["bipolar_total"]["volume_kpc3"] == 9.0
    assert rows["1e-2"]["positive_z"]["total_energy_erg"] == 80.0


def test_side_assignment_rejects_invalid_component_topology() -> None:
    builder = load_builder()
    valid = [
        {"case": "C-HI", "view": "0deg", "centroid_z_kpc": "-1", "crosses_z_zero": "False"},
        {"case": "C-HI", "view": "0deg", "centroid_z_kpc": "1", "crosses_z_zero": "False"},
    ]
    assert set(builder.assign_component_sides(valid)) == {"negative_z", "positive_z"}

    invalid = [
        {"case": "C-HI", "view": "0deg", "centroid_z_kpc": "0", "crosses_z_zero": "False"},
        {"case": "C-HI", "view": "0deg", "centroid_z_kpc": "1", "crosses_z_zero": "False"},
    ]
    with pytest.raises(ValueError, match="zero"):
        builder.assign_component_sides(invalid)


def test_pv_conversion_uses_fixed_kpc_to_cm_constant() -> None:
    builder = load_builder()
    assert builder.hybrid_pv(2.0, 3.0) == pytest.approx(
        6.0 * builder.KPC_CM**3
    )


def test_real_compact_package_has_exact_derived_row_contracts(tmp_path: Path) -> None:
    builder = load_builder()
    builder.build_assets(tmp_path)
    expected = {
        "case_truth_summary.csv": 3,
        "truth_threshold_sensitivity.csv": 9,
        "tracer_shell_pressure_context.csv": 6,
        "xray_truth_alignment.csv": 9,
        "xray_truth_method_sensitivity.csv": 135,
        "remote_completion_summary.csv": 1,
    }
    for name, count in expected.items():
        with (tmp_path / name).open(newline="") as handle:
            rows = list(csv.reader(handle))
        assert len(rows) - 1 == count
        assert len(rows[0]) == len(set(rows[0]))
        if name == "xray_truth_method_sensitivity.csv":
            assert "xray_volume_geometric_depth_over_level2_volume" in rows[0]
    assert (tmp_path / "three_case_truth_alignment.png").stat().st_size > 0


def test_manifest_excludes_itself(tmp_path: Path) -> None:
    builder = load_builder()
    (tmp_path / "a.txt").write_text("a\n")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.txt").write_text("b\n")
    builder.write_manifest(tmp_path)
    manifest = (tmp_path / "local_asset_manifest.sha256").read_text()
    assert "local_asset_manifest.sha256" not in manifest
    assert "a.txt" in manifest
    assert "nested/b.txt" in manifest
