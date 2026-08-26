from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_selected_age_xray_cavity.py")


def load_module():
    spec = importlib.util.spec_from_file_location("build_selected_age_xray_cavity", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def components(*, crossing: bool = False) -> list[dict[str, object]]:
    return [
        {
            "centroid_z_kpc": -25.0,
            "crosses_z_zero": crossing,
            "volume_minor_depth_kpc3": 100.0,
            "volume_geometric_depth_kpc3": 200.0,
            "volume_major_depth_kpc3": 300.0,
        },
        {
            "centroid_z_kpc": 30.0,
            "crosses_z_zero": False,
            "volume_minor_depth_kpc3": 120.0,
            "volume_geometric_depth_kpc3": 240.0,
            "volume_major_depth_kpc3": 360.0,
        },
    ]


def cavity_context() -> list[dict[str, object]]:
    return [
        {"side": "negative_z", "ambient_pressure_dyn_cm2": 1.0e-10},
        {"side": "positive_z", "ambient_pressure_dyn_cm2": 2.0e-10},
    ]


def test_energy_is_quantitative_only_for_two_opposite_xray_components() -> None:
    module = load_module()

    rows = module.build_energy_rows(
        case="G-LO",
        snapshot_index=20,
        actual_time_myr=20.0,
        view="45deg",
        topology_class="two_separate_components",
        components=components(),
        cavity_context=cavity_context(),
    )

    assert len(rows) == 27
    assert all(row["quantitative_energy_valid"] is True for row in rows)
    bipolar = next(
        row
        for row in rows
        if row["side"] == "bipolar_total"
        and row["volume_depth_assumption"] == "geometric_depth"
        and row["energy_model"] == "pV"
    )
    expected = (1.0e-10 * 200.0 + 2.0e-10 * 240.0) * module.KPC_CM**3
    assert bipolar["energy_erg"] == pytest.approx(expected)
    assert bipolar["pressure_role"] == "sum_of_side_specific_energy_estimates"


@pytest.mark.parametrize(
    ("topology", "case_components"),
    [
        ("connected_cross_midplane_component", components(crossing=True)),
        ("multiple_or_one_sided_components", components()[:1]),
    ],
)
def test_ambiguous_topology_is_retained_as_nonquantitative_proxy(
    topology: str,
    case_components: list[dict[str, object]],
) -> None:
    module = load_module()

    rows = module.build_energy_rows(
        case="C-HI",
        snapshot_index=50,
        actual_time_myr=50.0,
        view="90deg",
        topology_class=topology,
        components=case_components,
        cavity_context=cavity_context(),
    )

    assert len(rows) == 9
    assert {row["side"] for row in rows} == {"bipolar_total"}
    assert all(row["quantitative_energy_valid"] is False for row in rows)
    assert all(row["pressure_role"] == "nonquantitative_bipolar_mean_shell_proxy" for row in rows)


def test_manifest_requires_exact_common_age_surface(tmp_path: Path) -> None:
    module = load_module()
    manifest = tmp_path / "manifest.csv"
    rows = [
        {
            "case": "G-HI",
            "snapshot_index": age,
            "actual_time_myr": age + 0.001,
            "timestep": f"Timestep_{age}",
        }
        for age in (10, 20, 30, 40, 50)
    ]
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    selected = module.manifest_rows(manifest, "G-HI")

    assert [int(row["snapshot_index"]) for row in selected] == [10, 20, 30, 40, 50]


def test_g_hi_shock_cap_is_not_confused_with_nonshock_observable_age() -> None:
    module = load_module()
    assert module.AGES == (10, 20, 30, 40, 50)
    assert module.VIEWS == ("0deg", "45deg", "90deg")
