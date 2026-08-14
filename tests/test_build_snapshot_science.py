from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science.build_snapshot_science import (
    ProductError,
    build_energy_recovery_rows,
    build_product,
    select_cavity_recovery_surface,
    validate_fluid_surface,
)
from scripts.science.snapshot_inference import continuous_injection_delta_shape
from scripts.science.snapshot_synthesis import (
    RADIO_FREQUENCIES_GHZ,
    RADIO_SNAPSHOT_INDICES,
    SNAPSHOT_INDICES,
    XRAY_VIEWS,
)


CASE = "G-LO"


def test_direct_cli_entry_point_is_runnable() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/science/build_snapshot_science.py", "--help"],
        cwd=Path(__file__).parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "--case" in result.stdout


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fluid_rows() -> dict[str, list[dict[str, object]]]:
    manifest: list[dict[str, object]] = []
    source: list[dict[str, object]] = []
    energy: list[dict[str, object]] = []
    shock: list[dict[str, object]] = []
    for index in SNAPSHOT_INDICES:
        time = float(index)
        injected = 2.0e43 * time * 3.15576e13
        manifest.append(
            {
                "case": CASE,
                "snapshot_index": index,
                "actual_time_myr": time,
                "actual_time_code": time * 306.6,
                "input_h5": f"/remote/data.{index:04d}.flt.h5",
                "timestep": f"Timestep_{index}",
                "file_size_bytes": 100,
                "shape_nz_ny_nx": "1014x960x960",
                "selection_rule": "test",
            }
        )
        source.append(
            {
                "case": CASE,
                "snapshot_index": index,
                "actual_time_myr": time,
                "jet_power_one_sided_erg_s": 1.0e43,
                "jet_power_bipolar_erg_s": 2.0e43,
                "jet_start_myr": 0.0,
                "jet_active_myr": 50.0,
                "injected_energy_one_sided_erg": injected / 2.0,
                "injected_energy_bipolar_erg": injected,
            }
        )
        energy.append(
            {
                "case": CASE,
                "snapshot_index": index,
                "actual_time_myr": time,
                "side": "bipolar_total",
                "partition_method": "fractional",
                "gas_thermal_delta_erg": 0.35 * injected,
                "gas_kinetic_delta_erg": 0.05 * injected,
                "gas_gravitational_delta_erg": 0.10 * injected,
                "gas_total_delta_erg": 0.50 * injected,
                "lobe_thermal_erg": 0.20 * injected,
                "lobe_kinetic_erg": 0.05 * injected,
                "lobe_gravitational_erg": 0.02 * injected,
                "lobe_total_erg": 0.27 * injected,
                "lobe_volume_kpc3": 5000.0 + index,
                "injected_energy_erg": injected,
                "boundary_status": "unmeasured_from_retained_snapshots",
                "unattributed_residual_erg": 0.23 * injected,
                "closure_fraction_of_injected": 0.23 if index else "",
            }
        )
        for side in ("negative_z", "positive_z"):
            shock.append(
                {
                    "case": CASE,
                    "snapshot_index": index,
                    "actual_time_myr": time,
                    "side": side,
                    "velocity_threshold_factor": 1.0,
                    "status": "detected" if index else "not_detected",
                    "shock_distance_kpc": index * 2.0 if index else "",
                    "shock_speed_km_s": 1500.0 if index else "",
                    "ambient_sound_speed_km_s": 500.0 if index else "",
                    "mach_kinematic": 3.0 if index else "",
                    "mach_rh_pressure": 2.8 if index else "",
                    "mach_rh_density": 2.6 if index else "",
                }
            )
    return {"manifest": manifest, "source": source, "energy": energy, "shock": shock}


def cavity_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    factors = {"pV": 1.0, "2.5pV": 2.5, "4pV": 4.0}
    for index in RADIO_SNAPSHOT_INDICES:
        for view in XRAY_VIEWS:
            for model, factor in factors.items():
                invalid = index == 10 and view == "0deg" and model == "2.5pV"
                rows.append(
                    {
                        "case": CASE,
                        "nominal_age_myr": index,
                        "actual_time_myr": float(index),
                        "view": view,
                        "side": "bipolar_total",
                        "volume_depth_assumption": "geometric_depth",
                        "energy_model": model,
                        "topology_status": "connected_cross_midplane_component" if invalid else "two_separate_components",
                        "pressure_dyn_cm2": 1.0e-11,
                        "volume_kpc3": 5000.0,
                        "energy_erg": factor * 1.0e58,
                        "quantitative_energy_valid": "false" if invalid else "true",
                    }
                )
    return rows


def radio_rows(*, views: bool) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    frequencies = np.asarray(RADIO_FREQUENCIES_GHZ)
    view_values = XRAY_VIEWS if views else ("45deg",)
    for index in RADIO_SNAPSHOT_INDICES:
        for view in view_values:
            for loss_model in ("lossless", "full_loss"):
                shape = frequencies**-0.6
                if loss_model == "full_loss":
                    shape = continuous_injection_delta_shape(
                        frequencies,
                        alpha_injection=0.6,
                        break_ghz=6.0 / (index / 10.0),
                    )
                for frequency, luminosity in zip(frequencies, 2.0e24 * shape, strict=True):
                    rows.append(
                        {
                            "case": CASE,
                            "snapshot_index": index,
                            "fluid_time_myr": float(index),
                            "particle_output_index": index * 100,
                            "particle_time_myr": index - 0.001,
                            "particle_time_offset_myr": 0.001,
                            "view": view,
                            "frequency_ghz": frequency,
                            "loss_model": loss_model,
                            "luminosity_w_hz": luminosity,
                            "effective_magnetic_field_ug": 4.5,
                            "method": "corrected_praise2",
                        }
                    )
    return rows


def test_fluid_contract_rejects_cross_case_rows() -> None:
    rows = fluid_rows()
    rows["source"][0]["case"] = "C-LO"
    with pytest.raises(ProductError, match="non-G-LO"):
        validate_fluid_surface(
            case=CASE,
            expected_bipolar_power_erg_s=2.0e43,
            manifest_rows=rows["manifest"],
            source_rows=rows["source"],
            energy_rows=rows["energy"],
            shock_rows=rows["shock"],
        )


def test_invalid_cavity_and_boundary_residual_remain_nonquantitative() -> None:
    fluid = fluid_rows()
    selected = select_cavity_recovery_surface(cavity_rows(), case=CASE)
    recovery = build_energy_recovery_rows(
        energy_rows=fluid["energy"],
        cavity_rows=selected,
    )
    invalid = [
        row
        for row in recovery
        if row["snapshot_index"] == 10
        and row["view"] == "0deg"
        and row["cavity_energy_model"] == "2.5pV"
    ][0]
    assert invalid["recovery_status"] == "excluded_by_xray_topology_gate"
    assert invalid["cavity_to_injected_ratio"] == ""
    assert invalid["cavity_to_direct_lobe_total_ratio"] == ""
    assert invalid["residual_cocoon_status"] == "not_usable_as_cocoon_boundary_unmeasured"
    assert all(row["cavity_to_residual_cocoon_ratio"] == "" for row in recovery)


def test_full_product_builds_single_case_tables_and_figures(tmp_path: Path) -> None:
    fluid_root = tmp_path / "fluid"
    radio_root = tmp_path / "radio"
    fluid = fluid_rows()
    write_rows(fluid_root / "snapshot_manifest.csv", fluid["manifest"])
    write_rows(fluid_root / "source_truth.csv", fluid["source"])
    write_rows(fluid_root / "energy_partition_timeseries.csv", fluid["energy"])
    write_rows(fluid_root / "shock_dynamics.csv", fluid["shock"])
    write_rows(radio_root / "radio_luminosity_timeseries.csv", radio_rows(views=False))
    write_rows(radio_root / "radio_view_luminosity.csv", radio_rows(views=True))
    cavity = tmp_path / "cavity.csv"
    write_rows(cavity, cavity_rows())
    xray = tmp_path / "xray.png"
    xray.write_bytes(b"accepted-xray-context")
    output = tmp_path / "product"

    metadata = build_product(
        case=CASE,
        fluid_root=fluid_root,
        radio_root=radio_root,
        cavity_csv=cavity,
        xray_figure=xray,
        output_root=output,
    )

    assert metadata["status"] == "complete_single_case_snapshot_science_product"
    assert metadata["cross_case_claims"] is False
    assert metadata["table_row_counts"]["cavity_energy_recovery.csv"] == 45
    assert metadata["table_row_counts"]["spectral_cavity_power.csv"] == 90
    parsed = json.loads((output / "snapshot_science_metadata.json").read_text())
    assert parsed["case"] == CASE
    assert len(list(csv.DictReader((output / "figure_register.csv").open()))) == 8
    for name in metadata["generated_figures"]:
        assert (output / name).stat().st_size > 1000


def test_product_rejects_primary_radio_that_differs_from_45deg_view(tmp_path: Path) -> None:
    fluid_root = tmp_path / "fluid"
    radio_root = tmp_path / "radio"
    fluid = fluid_rows()
    write_rows(fluid_root / "snapshot_manifest.csv", fluid["manifest"])
    write_rows(fluid_root / "source_truth.csv", fluid["source"])
    write_rows(fluid_root / "energy_partition_timeseries.csv", fluid["energy"])
    write_rows(fluid_root / "shock_dynamics.csv", fluid["shock"])
    primary = radio_rows(views=False)
    primary[0]["luminosity_w_hz"] = float(primary[0]["luminosity_w_hz"]) * 1.01
    write_rows(radio_root / "radio_luminosity_timeseries.csv", primary)
    write_rows(radio_root / "radio_view_luminosity.csv", radio_rows(views=True))
    cavity = tmp_path / "cavity.csv"
    write_rows(cavity, cavity_rows())
    xray = tmp_path / "xray.png"
    xray.write_bytes(b"accepted-xray-context")

    with pytest.raises(ProductError, match="45deg primary radio mismatch"):
        build_product(
            case=CASE,
            fluid_root=fluid_root,
            radio_root=radio_root,
            cavity_csv=cavity,
            xray_figure=xray,
            output_root=tmp_path / "product",
        )


def test_high_power_case_uses_its_locked_bipolar_power(tmp_path: Path) -> None:
    case = "C-HI"
    fluid_root = tmp_path / "fluid"
    radio_root = tmp_path / "radio"
    fluid = fluid_rows()
    for rows in fluid.values():
        for row in rows:
            row["case"] = case
    for row in fluid["source"]:
        row["jet_power_one_sided_erg_s"] = 1.0e45
        row["jet_power_bipolar_erg_s"] = 2.0e45
        row["injected_energy_one_sided_erg"] = float(row["injected_energy_one_sided_erg"]) * 100.0
        row["injected_energy_bipolar_erg"] = float(row["injected_energy_bipolar_erg"]) * 100.0
    for row in fluid["energy"]:
        for field in (
            "gas_thermal_delta_erg",
            "gas_kinetic_delta_erg",
            "gas_gravitational_delta_erg",
            "gas_total_delta_erg",
            "lobe_thermal_erg",
            "lobe_kinetic_erg",
            "lobe_gravitational_erg",
            "lobe_total_erg",
            "injected_energy_erg",
            "unattributed_residual_erg",
        ):
            row[field] = float(row[field]) * 100.0
    write_rows(fluid_root / "snapshot_manifest.csv", fluid["manifest"])
    write_rows(fluid_root / "source_truth.csv", fluid["source"])
    write_rows(fluid_root / "energy_partition_timeseries.csv", fluid["energy"])
    write_rows(fluid_root / "shock_dynamics.csv", fluid["shock"])
    primary = [dict(row) | {"case": case} for row in radio_rows(views=False)]
    views = [dict(row) | {"case": case} for row in radio_rows(views=True)]
    write_rows(radio_root / "radio_luminosity_timeseries.csv", primary)
    write_rows(radio_root / "radio_view_luminosity.csv", views)
    cavity = tmp_path / "cavity.csv"
    write_rows(cavity, [dict(row) | {"case": case} for row in cavity_rows()])
    xray = tmp_path / "xray.png"
    xray.write_bytes(b"accepted-xray-context")
    output = tmp_path / "product"

    metadata = build_product(
        case=case,
        fluid_root=fluid_root,
        radio_root=radio_root,
        cavity_csv=cavity,
        xray_figure=xray,
        output_root=output,
    )

    assert metadata["method_contract"]["known_power_convention"] == "bipolar 2e+45 erg/s"
    power_rows = list(csv.DictReader((output / "radio_power_inference.csv").open()))
    assert {float(row["known_bipolar_power_erg_s"]) for row in power_rows} == {2.0e45}
