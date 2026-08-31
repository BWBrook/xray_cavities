from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_selected_age_dual_space_energetics.py")
NATIVE = Path("docs/science/assets/four_case_scientific_synthesis_2026-08-26/case_age_physics.csv")


def load_module():
    spec = importlib.util.spec_from_file_location("build_selected_age_dual_space_energetics", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_native_selected_surface_derives_pressure_volume_enthalpy_without_observer_input() -> None:
    module = load_module()

    rows = module.native_selected_rows(NATIVE)

    assert len(rows) == 19
    assert {(row["case"], row["snapshot_index"]) for row in rows if row["case"] == "G-HI"} == {
        ("G-HI", 10),
        ("G-HI", 20),
        ("G-HI", 30),
        ("G-HI", 40),
    }
    for row in rows:
        assert row["lobe_pressure_volume_erg"] == pytest.approx(
            (module.GAMMA - 1.0) * row["lobe_thermal_erg"]
        )
        assert row["lobe_enthalpy_2p5pv_erg"] == pytest.approx(
            2.5 * row["lobe_pressure_volume_erg"]
        )


def test_full_join_factorizes_volume_and_pressure_bias(tmp_path: Path) -> None:
    module = load_module()
    observer_root = tmp_path / "observer"
    native = module.native_selected_rows(NATIVE)
    for case in module.CASES:
        case_rows = [row for row in native if row["case"] == case]
        topology = []
        enthalpy = []
        profiles = []
        for native_row in case_rows:
            for view in ("0deg", "45deg", "90deg"):
                topology.append(
                    {
                        "case": case,
                        "snapshot_index": native_row["snapshot_index"],
                        "actual_time_myr": native_row["actual_time_myr"],
                        "view": view,
                        "topology_class": "two_separate_components",
                        "component_count": 2,
                        "quantitative_cavity_valid": True,
                    }
                )
                profiles.append(
                    {
                        "case": case,
                        "snapshot_index": native_row["snapshot_index"],
                        "view": view,
                        "pressure_dyn_cm2": 2.0e-11,
                    }
                )
                for depth in ("minor_depth", "geometric_depth", "major_depth"):
                    for pressure_method in ("midpoint", "ellipsoid_volume_average"):
                        for energy_model, alpha in (("2.5pV", 2.5), ("4pV", 4.0)):
                            for side in ("negative_z", "positive_z"):
                                volume = 100.0
                                pressure = 2.0e-11
                                enthalpy.append(
                                    {
                                        "case": case,
                                        "snapshot_index": native_row["snapshot_index"],
                                        "actual_time_myr": native_row["actual_time_myr"],
                                        "view": view,
                                        "side": side,
                                        "topology_class": "two_separate_components",
                                        "quantitative_cavity_valid": True,
                                        "volume_depth_assumption": depth,
                                        "pressure_method": pressure_method,
                                        "energy_model": energy_model,
                                        "alpha": alpha,
                                        "pressure_dyn_cm2": pressure,
                                        "volume_kpc3": volume,
                                        "enthalpy_erg": alpha * pressure * volume * module.KPC_CM**3,
                                    }
                                )
        write_rows(observer_root / case / "xray_topology_summary.csv", topology)
        write_rows(observer_root / case / "xray_cavity_enthalpy_selected_age.csv", enthalpy)
        write_rows(observer_root / case / "xray_pressure_profiles.csv", profiles)

    metadata = module.build_product(
        native_case_age_path=NATIVE,
        observer_root=observer_root,
        output_root=tmp_path / "output",
    )

    assert metadata["accepted_case_age_count"] == 19
    with (tmp_path / "output" / "matched_native_xray_energetics.csv").open(newline="") as handle:
        matched = list(csv.DictReader(handle))
    assert len(matched) == 57 * 12
    assert max(float(row["factorization_relative_error"]) for row in matched) < 1.0e-10
