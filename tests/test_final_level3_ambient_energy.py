from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_final_level3_ambient_energy.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_final_level3_ambient_energy", SCRIPT)
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def comparator_fixture(tmp_path: Path) -> tuple[Path, Path]:
    level1 = tmp_path / "level1_injected_energy.csv"
    level2 = tmp_path / "level2_tracer_lobe_truth.csv"
    write_csv(
        level1,
        [{"metric": "injected_energy_bipolar_elapsed", "value": 100.0, "unit": "erg"}],
        ["metric", "value", "unit"],
    )
    write_csv(
        level2,
        [
            {
                "threshold": "5e-03",
                "side": "bipolar_total",
                "time_myr": 50.0,
                "cell_count": 20,
                "volume_kpc3": 300.0,
                "total_energy_erg": 40.0,
            }
        ],
        ["threshold", "side", "time_myr", "cell_count", "volume_kpc3", "total_energy_erg"],
    )
    return level1, level2


def test_validate_grid_preflight_rejects_shape_mismatch() -> None:
    module = load_script_module()

    with pytest.raises(ValueError, match="grid shapes differ"):
        module.validate_grid_preflight(
            {
                "baseline_shape_nz_ny_nx": [10, 20, 30],
                "final_shape_nz_ny_nx": [10, 20, 31],
                "required_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
                "baseline_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
                "final_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
            }
        )


def test_validate_grid_preflight_rejects_missing_required_dataset() -> None:
    module = load_script_module()

    with pytest.raises(ValueError, match="missing final datasets"):
        module.validate_grid_preflight(
            {
                "baseline_shape_nz_ny_nx": [10, 20, 30],
                "final_shape_nz_ny_nx": [10, 20, 30],
                "required_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
                "baseline_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
                "final_datasets": ["rho", "prs", "tr1", "vx1", "vx2"],
            }
        )


def test_computed_component_rows_include_all_comparator_ratios(tmp_path: Path) -> None:
    module = load_script_module()
    level1, level2 = comparator_fixture(tmp_path)
    comparators = module.load_comparators(
        level1_path=level1,
        level2_path=level2,
        pV_erg=10.0,
        two_point_five_pV_erg=25.0,
        four_pV_erg=40.0,
    )
    extractor_rows = [
        {
            "side": "bipolar_total",
            "ambient_cell_count": "100",
            "ambient_volume_kpc3": "500",
            "thermal_delta_erg": "50",
            "kinetic_delta_erg": "5",
        }
    ]

    rows = module.build_energy_rows(
        extractor_rows=extractor_rows,
        comparators=comparators,
        gravitational_status="blocked_missing_potential",
        gravitational_note="No potential profile was available.",
    )

    thermal = next(row for row in rows if row["component"] == "ambient_thermal_delta")
    assert thermal["status"] == "computed"
    assert thermal["ratio_to_level1_bipolar_injected"] == pytest.approx(0.5)
    assert thermal["ratio_to_level2_bipolar_lobe"] == pytest.approx(1.25)
    assert thermal["ratio_to_pV_bipolar"] == pytest.approx(5.0)
    assert thermal["ratio_to_2.5pV_bipolar"] == pytest.approx(2.0)
    assert thermal["ratio_to_4pV_bipolar"] == pytest.approx(1.25)

    total = next(row for row in rows if row["component"] == "ambient_thermal_plus_kinetic_delta")
    assert total["value_erg"] == pytest.approx(55.0)

    gravity = next(row for row in rows if row["component"] == "ambient_gravitational_delta")
    assert gravity["status"] == "blocked_missing_potential"
    assert gravity["value_erg"] == ""


def test_blocked_package_writes_status_tables_without_extractor_output(tmp_path: Path) -> None:
    module = load_script_module()
    level1, level2 = comparator_fixture(tmp_path)
    output_dir = tmp_path / "level3"

    metadata = module.build_package(
        output_dir=output_dir,
        level1_path=level1,
        level2_path=level2,
        pV_erg=10.0,
        two_point_five_pV_erg=25.0,
        four_pV_erg=40.0,
        extractor_csv=None,
        remote_preflight={
            "baseline_h5": "/scratch/example/data.0000.flt.h5",
            "baseline_timestep": "Timestep_0",
            "final_h5": "/scratch/example/data.0051.flt.h5",
            "final_timestep": "Timestep_51",
            "baseline_shape_nz_ny_nx": [1014, 960, 960],
            "final_shape_nz_ny_nx": [1014, 960, 960],
            "required_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
            "baseline_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
            "final_datasets": ["rho", "prs", "tr1", "vx1", "vx2", "vx3"],
        },
        thermal_kinetic_blocker="blocked_remote_postprocessing_access",
        gravitational_status="blocked_missing_potential",
        gravitational_note="No potential profile or convention is in the accepted HDF5 outputs.",
    )

    assert metadata["result_status"] == "blocked_remote_postprocessing_access"
    energy_rows = read_csv(output_dir / "level3_ambient_energy.csv")
    by_component = {row["component"]: row for row in energy_rows}
    assert by_component["ambient_thermal_delta"]["status"] == "blocked_remote_postprocessing_access"
    assert by_component["ambient_kinetic_delta"]["status"] == "blocked_remote_postprocessing_access"
    assert by_component["ambient_gravitational_delta"]["status"] == "blocked_missing_potential"

    method_rows = read_csv(output_dir / "level3_method_decisions.csv")
    assert {row["decision"] for row in method_rows} >= {
        "baseline_reference",
        "ambient_tracer_exclusion",
        "coordinate_compatibility",
        "gravitational_component",
    }
    coordinate_row = next(row for row in method_rows if row["decision"] == "coordinate_compatibility")
    assert coordinate_row["status"] == "enforced_by_extractor_not_remote_preflight"

    written_metadata = json.loads((output_dir / "level3_metadata.json").read_text())
    assert written_metadata["remote_preflight"]["baseline_timestep"] == "Timestep_0"
    assert written_metadata["coordinate_compatibility_contract"] == "enforced_by_extractor_not_remote_preflight"
