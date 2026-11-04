from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCIENCE = Path(__file__).resolve().parents[1] / "scripts/science"
sys.path.insert(0, str(SCIENCE))
import extract_spherical_energy_budget as budget


def _axes(n: int = 5) -> tuple[np.ndarray, np.ndarray]:
    edges = np.arange(n + 1, dtype=float) - n / 2
    return 0.5 * (edges[:-1] + edges[1:]), edges


def _base_state(shape=(5, 5, 5)) -> dict[str, np.ndarray]:
    state = {
        "rho": np.full(shape, 2.0),
        "prs": np.full(shape, 3.0),
        "tr1": np.zeros(shape),
        "vx1": np.zeros(shape),
        "vx2": np.zeros(shape),
        "vx3": np.zeros(shape),
    }
    return state


def _write_h5(path: Path, state: dict[str, np.ndarray], *, timestep: str, time_code: float) -> None:
    z, y, x = state["rho"].shape
    x_values, x_edges = _axes(x)
    y_values, y_edges = _axes(y)
    z_values, z_edges = _axes(z)
    with h5py.File(path, "w") as h5:
        cells = h5.create_group("cell_coords")
        nodes = h5.create_group("node_coords")
        for name, values, edges in (
            ("X", x_values, x_edges), ("Y", y_values, y_edges), ("Z", z_values, z_edges)
        ):
            cells.create_dataset(name, data=values)
            nodes.create_dataset(name, data=edges)
        group = h5.create_group(timestep)
        group.attrs["Time"] = time_code
        variables = group.create_group("vars")
        for name, values in state.items():
            variables.create_dataset(name, data=values)


def _write_environment(path: Path) -> None:
    maximum = 20.0 * budget.UNIT_LENGTH_CM
    np.savetxt(
        path,
        np.array([
            [0.0, 1.0e-25, 1.0e-10, 0.0, 1.0e-8, 1.0e-8],
            [maximum, 1.0e-25, 1.0e-10, 0.0, 1.0e-8, 1.0e-8],
        ]),
    )


def _inputs(tmp_path: Path, current: dict[str, np.ndarray] | None = None,
            initial: dict[str, np.ndarray] | None = None, *, index: int = 1):
    tmp_path.mkdir(parents=True, exist_ok=True)
    initial = _base_state() if initial is None else initial
    current = {name: values.copy() for name, values in initial.items()} if current is None else current
    initial_path = tmp_path / "data.0000.flt.h5"
    current_path = tmp_path / f"data.{index:04d}.flt.h5"
    environment = tmp_path / "environment.csv"
    _write_h5(initial_path, initial, timestep="Timestep_0", time_code=0.0)
    _write_h5(
        current_path, current, timestep=f"Timestep_{index}",
        time_code=2.0 * budget.CODE_TIME_PER_MYR,
    )
    _write_environment(environment)
    return initial_path, current_path, environment


def _run(tmp_path: Path, current: dict[str, np.ndarray], initial: dict[str, np.ndarray] | None = None,
         *, case="C-HI", index=1, safe_buffer=1.0, receipt=None, output_name="budget.json"):
    initial_path, current_path, environment = _inputs(tmp_path, current, initial, index=index)
    output = tmp_path / output_name
    result = budget.extract_snapshot(
        case=case,
        snapshot_index=index,
        current_h5=current_path,
        initial_h5=initial_path,
        environment_path=environment,
        safe_buffer_kpc=safe_buffer,
        input_receipt=receipt,
        output=output,
    )
    return result, output, (initial_path, current_path, environment)


def _velocity_code(km_s: float) -> float:
    return km_s * 1.0e5 / budget.UNIT_VELOCITY_CMS


def _hold_codes(payload: dict) -> set[str]:
    return {item["code"] for item in payload["scientific_qualification"]["holds"]}


def test_radius_uses_full_speed_and_absent_threshold_is_unavailable(tmp_path: Path) -> None:
    current = _base_state()
    # x=2, y=z=0: neither component reaches 100 km/s, but the full speed does.
    current["vx1"][2, 2, 4] = _velocity_code(60.0)
    current["vx2"][2, 2, 4] = _velocity_code(81.0)
    current["prs"] += 0.25
    result, _, _ = _run(tmp_path, current)

    r100 = result["thresholds"]["100"]
    assert r100["measurement_status"] == "measured"
    assert r100["raw_radius_kpc"] == pytest.approx(2.0)
    assert r100["radius_defining_velocity_km_s"][:2] == pytest.approx([60.0, 81.0])
    assert r100["qualifying_cell_count"] == 1
    assert r100["isolated_radius_defining_fast_cell"] is True
    assert result["thresholds"]["300"] == {
        "speed_threshold_km_s": 300.0,
        "measurement_status": "unavailable_no_cells_meet_speed_threshold",
        "scientific_qualification": budget._qualification([]),
        "raw_radius_kpc": None,
        "budget": None,
    }
    assert result["threshold_comparison"]["measurement_status"] == "unavailable_unless_both_thresholds_exist"


def test_current_binary_membership_weights_actual_initial_subtraction(tmp_path: Path) -> None:
    initial = _base_state()
    current = {name: values.copy() for name, values in initial.items()}
    cocoon_index = (2, 2, 3)  # radius 1 kpc
    equality_index = (2, 3, 2)  # strict equality remains ambient
    current["vx1"][cocoon_index] = _velocity_code(120.0)
    initial["vx1"][cocoon_index] = _velocity_code(20.0)
    current["prs"][cocoon_index] += 2.0
    current["rho"][cocoon_index] += 0.5
    current["tr1"][cocoon_index] = 0.01
    current["prs"][equality_index] += 1.0
    current["tr1"][equality_index] = 1.0e-3

    result, _, _ = _run(tmp_path, current, initial)
    sphere = result["thresholds"]["100"]["sphere_budget"]
    partition = sphere["current_binary_partition"]
    expected_cocoon_thermal = 2.0 * budget.UNIT_ENERGY_ERG / (budget.GAMMA_GAS - 1.0)
    expected_ambient_thermal = 1.0 * budget.UNIT_ENERGY_ERG / (budget.GAMMA_GAS - 1.0)
    assert partition["cocoon"]["thermal_delta_erg"] == pytest.approx(expected_cocoon_thermal)
    assert partition["ambient"]["thermal_delta_erg"] == pytest.approx(expected_ambient_thermal)
    assert partition["cocoon"]["kinetic_delta_erg"] == pytest.approx(
        0.5 * (
            current["rho"][cocoon_index] * current["vx1"][cocoon_index] ** 2
            - initial["rho"][cocoon_index] * initial["vx1"][cocoon_index] ** 2
        ) * budget.UNIT_ENERGY_ERG
    )
    assert partition["identity_pass"] is True
    assert sphere["delta_erg"]["total_delta_erg"] == pytest.approx(
        partition["cocoon"]["total_delta_erg"] + partition["ambient"]["total_delta_erg"]
    )


def test_both_thresholds_partition_exactly_and_normalize_to_bipolar_injection(tmp_path: Path) -> None:
    current = _base_state()
    current["vx1"][2, 2, 4] = _velocity_code(110.0)  # R100=2
    current["vx3"][2, 2, 3] = _velocity_code(310.0)  # R300=1
    current["tr1"][2, 2, 3] = 0.1
    current["prs"][2, 2, 2] += 1.0
    current["prs"][2, 2, 3] += 2.0
    current["prs"][2, 2, 4] += 4.0
    result, _, _ = _run(tmp_path, current, case="C-LO")

    assert result["injected_energy_erg"] == pytest.approx(2.0e43 * 2.0 * budget.SECONDS_PER_MYR)
    assert "boundary_safe_box_conflict" in _hold_codes(result["thresholds"]["100"])
    assert "boundary_safe_box_conflict" not in _hold_codes(result["thresholds"]["300"])
    assert "boundary_safe_box_conflict" not in _hold_codes(result["native_lobe_enthalpy"])
    for threshold in ("100", "300"):
        record = result["thresholds"][threshold]
        assert record["sphere_budget"]["current_binary_partition"]["identity_pass"] is True
        total = record["sphere_budget"]["delta_erg"]["total_delta_erg"]
        assert record["sphere_budget"]["delta_erg"]["total_over_injected"] == pytest.approx(
            total / result["injected_energy_erg"]
        )
    comparison = result["threshold_comparison"]
    assert comparison["measurement_status"] == "measured_conditional_diagnostic"
    assert comparison["scientific_qualification"]["status"] == "held"
    assert any(
        item["code"] == "boundary_safe_box_conflict"
        for item in comparison["scientific_qualification"]["holds"]
    )
    assert comparison["radius_difference_kpc"] == pytest.approx(1.0)
    assert comparison["delta_difference_erg"]["thermal_delta_erg"] == pytest.approx(
        4.0 * budget.UNIT_ENERGY_ERG / (budget.GAMMA_GAS - 1.0)
    )


def test_safe_box_conflict_and_clipped_cocoon_loss_are_explicit(tmp_path: Path) -> None:
    current = _base_state()
    current["vx1"][2, 2, 4] = _velocity_code(120.0)  # radius 2; safe inscribed radius 1.5
    current["tr1"][2, 2, 4] = 0.5
    current["prs"][2, 2, 4] += 3.0
    result, _, _ = _run(tmp_path, current, safe_buffer=1.0)
    record = result["thresholds"]["100"]

    assert record["sphere_geometrically_complete_in_domain_box"] is True
    assert record["sphere_geometrically_complete_in_boundary_safe_box"] is False
    assert record["boundary_safe_conflict"] is True
    assert "boundary_safe_box_conflict" in _hold_codes(record)
    assert record["sphere_cells_outside_boundary_safe_box"]["cocoon_cell_count"] == 1
    assert record["sphere_cells_outside_boundary_safe_box"]["delta_erg"]["thermal_delta_erg"] > 0.0
    assert record["coverage"]["cocoon_cell_coverage_fraction"] == 1.0
    assert "conditional clipping" in result["interpretation_limits"][2]


def test_domain_truncation_and_outside_aperture_disturbance_are_flagged(tmp_path: Path) -> None:
    current = _base_state()
    # Corner radius sqrt(12) exceeds the box's 2.5-kpc inscribed radius.
    current["vx1"][4, 4, 4] = _velocity_code(120.0)
    # A pressure disturbance inside the safe box but outside a smaller R300 aperture.
    current["vx3"][2, 2, 3] = _velocity_code(320.0)
    current["prs"][2, 2, 4] *= 1.02
    result, _, _ = _run(tmp_path, current, safe_buffer=0.0)

    r100 = result["thresholds"]["100"]
    assert r100["domain_geometry_status"] == "domain_truncated_spherical_cell_selection"
    assert "domain_truncated_raw_spherical_selection" in _hold_codes(r100)
    r300_disturbance = result["thresholds"]["300"]["coverage"][
        "outside_aperture_within_safe_box_disturbance"
    ]
    assert r300_disturbance["flagged_cell_count"] >= 1
    assert r300_disturbance["maximum_abs_pressure_fractional_change"] >= 0.02 - 1e-12


@pytest.mark.parametrize("density_delta", [0.5, -0.5])
def test_fixed_centre_zero_potential_gravitational_sign_and_scale(
    tmp_path: Path, density_delta: float
) -> None:
    initial = _base_state()
    current = {name: values.copy() for name, values in initial.items()}
    index = (2, 2, 3)  # one kpc from the centre
    current["vx1"][index] = _velocity_code(120.0)
    current["rho"][index] += density_delta
    result, _, _ = _run(tmp_path, current, initial)

    potential = 1.0e-8 * budget.UNIT_LENGTH_CM
    expected = (
        density_delta
        * budget.UNIT_DENSITY_CGS
        * budget.UNIT_LENGTH_CM**3
        * potential
    )
    observed = result["thresholds"]["100"]["sphere_budget"]["delta_erg"][
        "gravitational_delta_erg"
    ]
    assert observed == pytest.approx(expected, rel=1.0e-12)
    assert np.sign(observed) == np.sign(density_delta)


def test_out_of_range_tracer_is_retained_but_places_science_on_hold(tmp_path: Path) -> None:
    current = _base_state()
    current["vx1"][2, 2, 3] = _velocity_code(120.0)
    current["tr1"][2, 2, 3] = 1.2
    current["tr1"][2, 2, 2] = -0.1
    result, _, _ = _run(tmp_path, current)

    assert result["tracer_diagnostics"]["outside_unit_interval_cell_count"] == 2
    assert "tracer_values_outside_unit_interval_unreviewed" in _hold_codes(result)
    r100 = result["thresholds"]["100"]
    assert "tracer_values_outside_unit_interval_unreviewed" in _hold_codes(r100)
    assert r100["sphere_budget"]["cocoon_cell_count"] == 1
    assert "without clipping" in result["tracer_diagnostics"]["handling"]


def _make_receipt(path: Path, roles: dict[str, Path], *, case="G-LO", index=1) -> None:
    records = {}
    for role, source in roles.items():
        records[role] = budget._stat_identity(source) | {"sha256": budget._sha256(source)}
    path.write_text(json.dumps({
        "schema_version": 1,
        "status": "bound_spherical_budget_inputs",
        "case": case,
        "snapshot_index": index,
        "current": {"timestep": f"Timestep_{index}", "time_code": 2.0 * budget.CODE_TIME_PER_MYR},
        "initial": {"timestep": "Timestep_0", "time_code": 0.0},
        "inputs": records,
    }) + "\n")


def test_bound_receipt_is_retained_and_mutation_fails_closed(tmp_path: Path) -> None:
    current = _base_state()
    current["vx1"][2, 2, 3] = _velocity_code(120.0)
    initial_path, current_path, environment = _inputs(tmp_path, current)
    receipt = tmp_path / "input_receipt.json"
    _make_receipt(receipt, {
        "current_h5": current_path,
        "initial_h5": initial_path,
        "environment": environment,
    })
    output = tmp_path / "first.json"
    result = budget.extract_snapshot(
        case="G-LO", snapshot_index=1, current_h5=current_path, initial_h5=initial_path,
        environment_path=environment, input_receipt=receipt, safe_buffer_kpc=1.0,
        output=output,
    )
    assert result["provenance"]["mode"] == "bound_input_receipt"
    assert result["provenance"]["input_receipt"]["sha256"] == budget._sha256(receipt)

    wrong_receipt = tmp_path / "wrong_case_receipt.json"
    _make_receipt(wrong_receipt, {
        "current_h5": current_path,
        "initial_h5": initial_path,
        "environment": environment,
    }, case="C-HI")
    with pytest.raises(ValueError, match="differs from input receipt"):
        budget.extract_snapshot(
            case="G-LO", snapshot_index=1, current_h5=current_path, initial_h5=initial_path,
            environment_path=environment, input_receipt=wrong_receipt, safe_buffer_kpc=1.0,
            output=tmp_path / "wrong_case.json",
        )

    with h5py.File(current_path, "r+") as h5:
        h5["Timestep_1/vars/prs"][2, 2, 2] += 1.0
    with pytest.raises(ValueError, match="metadata differs from receipt"):
        budget.extract_snapshot(
            case="G-LO", snapshot_index=1, current_h5=current_path, initial_h5=initial_path,
            environment_path=environment, input_receipt=receipt, safe_buffer_kpc=1.0,
            output=tmp_path / "mutated.json",
        )


def test_one_snapshot_cli_runs_with_required_receipt(tmp_path: Path) -> None:
    current = _base_state()
    current["vx1"][2, 2, 3] = _velocity_code(120.0)
    initial_path, current_path, environment = _inputs(tmp_path, current)
    receipt = tmp_path / "input_receipt.json"
    _make_receipt(receipt, {
        "current_h5": current_path,
        "initial_h5": initial_path,
        "environment": environment,
    })
    output = tmp_path / "cli.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCIENCE / "extract_spherical_energy_budget.py"),
            "--case", "G-LO",
            "--snapshot-index", "1",
            "--current-h5", str(current_path),
            "--initial-h5", str(initial_path),
            "--environment", str(environment),
            "--safe-buffer-kpc", "1",
            "--input-receipt", str(receipt),
            "--output", str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output.read_text())
    assert payload["execution_status"] == "completed_spherical_energy_budget_measurement"
    assert payload["scientific_qualification"]["status"] == "held"
    assert "external_native_case_configuration_environment_identity_unverified" in _hold_codes(payload)
    assert payload["provenance"]["native_semantic_identity_gate"]["status"] == "external_validation_required"


def test_refuses_overwrite_invalid_primitives_and_scientifically_excluded_g_hi(tmp_path: Path) -> None:
    current = _base_state()
    current["vx1"][2, 2, 3] = _velocity_code(120.0)
    result, output, paths = _run(tmp_path, current)
    assert result["execution_status"] == "completed_spherical_energy_budget_measurement"
    with pytest.raises(ValueError, match="refusing to overwrite"):
        budget.extract_snapshot(
            case="C-HI", snapshot_index=1, current_h5=paths[1], initial_h5=paths[0],
            environment_path=paths[2], safe_buffer_kpc=1.0, output=output,
        )

    bad = _base_state()
    bad["vx1"][2, 2, 3] = _velocity_code(120.0)
    bad["prs"][0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite primitive"):
        _run(tmp_path / "bad", bad)

    with pytest.raises(ValueError, match="boundary-contaminated"):
        budget.extract_snapshot(
            case="G-HI", snapshot_index=48,
            current_h5=Path("unused"), initial_h5=Path("unused"),
            environment_path=Path("unused"), output=tmp_path / "g_hi_48.json",
        )


def test_native_enthalpy_keeps_slow_lobe_outside_aperture_and_current_pressure(tmp_path: Path) -> None:
    current = _base_state()
    current['vx1'][2, 2, 3] = _velocity_code(310.0)
    current['tr1'][2, 2, 3] = 0.1
    current['prs'][2, 2, 3] = 5.0
    current['tr1'][0, 0, 0] = 0.1
    current['prs'][0, 0, 0] = 7.0
    current['tr1'][0, 0, 1] = 1e-3
    current['prs'][0, 0, 1] = 100.0
    result, _, _ = _run(tmp_path, current)
    expected_pv = 12.0 * budget.UNIT_ENERGY_ERG
    assert result['cocoon_global']['pressure_volume_integral_erg'] == pytest.approx(expected_pv)
    assert result['thresholds']['100']['coverage']['cocoon_outside_aperture_cell_count'] == 1
    for alpha in (2.5, 4.0):
        proxy = result['native_lobe_enthalpy']['conventions'][f'{alpha:g}']
        assert proxy['enthalpy_erg'] == pytest.approx(alpha * expected_pv)
        assert proxy['enthalpy_over_injected'] == pytest.approx(alpha * expected_pv / result['injected_energy_erg'])
