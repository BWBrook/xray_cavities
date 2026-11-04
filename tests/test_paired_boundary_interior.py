from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

SCIENCE = Path(__file__).resolve().parents[1] / "scripts/science"
sys.path.insert(0, str(SCIENCE))
import audit_paired_boundary_interior as audit
from measure_q031_fluxes import Grid
from test_paired_nojet_outputs import make_run
import validate_paired_nojet_outputs as validator


class Potential:
    def potential_at_radius(self, radius):
        return np.full_like(radius, 3e15)


def setup_arrays(n=12):
    edges = np.arange(n + 1, dtype=float) - n / 2
    centers, widths = (edges[:-1] + edges[1:]) / 2, np.diff(edges)
    grid = Grid(centers, centers, centers, widths, widths, widths, edges, edges, edges)
    state = {name: np.full((n, n, n), 2. if name in ("rho", "prs") else 0.)
             for name in audit.FIELDS}
    return grid, state


def measure(initial, reflective, outflow, grid, **kwargs):
    return audit.measure_pair(initial, initial, reflective, outflow, grid=grid,
                              environment=Potential(), time_myr=.25, **kwargs)


def test_identical_runs_zero_contrast_and_complete_cell_counts():
    grid, initial = setup_arrays()
    result = measure(initial, initial, initial, grid)
    assert [row["cell_count"] for row in result["regions"]] == [12**3, 10**3, 8**3, 4**3]
    for row in result["regions"]:
        assert all(value == 0 for value in row["contrast"].values())
        assert all(value == 0 for value in row["contrast_cell_l1"].values())
        assert row["absolute_total_contrast_over_whole_grid_contrast"] is None


def test_boundary_only_changes_disappear_after_one_cell_exclusion():
    grid, initial = setup_arrays()
    outflow = copy.deepcopy(initial)
    mask = np.zeros((12, 12, 12), dtype=bool)
    mask[[0, -1], :, :] = True
    mask[:, [0, -1], :] = True
    mask[:, :, [0, -1]] = True
    outflow["rho"][mask] += .25
    outflow["prs"][mask] += .5
    outflow["vx1"][mask] = .001
    result = measure(initial, initial, outflow, grid)
    whole = result["regions"][0]["contrast"]
    count = np.count_nonzero(mask)
    expected_mass = count * .25 * audit.UNIT_DENSITY_CGS * audit.UNIT_LENGTH_CM**3
    assert whole["mass_g"] == pytest.approx(expected_mass)
    assert whole["thermal_erg"] == pytest.approx(count * .5 * audit.UNIT_ENERGY_ERG / (5/3 - 1))
    assert whole["kinetic_erg"] == pytest.approx(count * .5 * 2.25 * .001**2 * audit.UNIT_ENERGY_ERG)
    assert whole["gravitational_erg"] == pytest.approx(expected_mass * 3e15)
    for row in result["regions"][1:]:
        assert all(value == 0 for value in row["contrast_cell_l1"].values())


def test_second_layer_is_not_hidden_by_one_kpc_cut():
    grid, initial = setup_arrays()
    outflow = copy.deepcopy(initial)
    outflow["prs"][1, 5, 5] += .25
    result = measure(initial, initial, outflow, grid)
    rows = result["regions"]
    assert rows[0]["contrast"] == rows[1]["contrast"]
    assert rows[2]["contrast"]["total_energy_erg"] == 0


def test_opposite_signed_cells_do_not_cancel_in_absolute_diagnostic():
    grid, initial = setup_arrays()
    outflow = copy.deepcopy(initial)
    outflow["prs"][5, 5, 5] += .25
    outflow["prs"][5, 5, 6] -= .25
    result = measure(initial, initial, outflow, grid)
    for row in result["regions"]:
        assert row["contrast"]["thermal_erg"] == 0
        assert row["contrast_cell_l1"]["thermal_erg"] > 0
        assert row["total_l1_over_low_power_comparison"] > 0


def test_same_cell_initial_subtraction_and_direct_contrast_agree():
    grid, initial = setup_arrays()
    reflective, outflow = copy.deepcopy(initial), copy.deepcopy(initial)
    reflective["prs"][5, 5, 5] += .125
    outflow["prs"][5, 5, 5] += .375
    for row in measure(initial, reflective, outflow, grid)["regions"]:
        for key in audit.COMPONENTS:
            assert row["contrast"][key] == pytest.approx(row["outflow_delta"][key] - row["reflective_delta"][key])


def test_complete_cell_containment_not_centre_selection():
    grid, _ = setup_arrays()
    assert audit.interior_mask(grid, 5, .25).sum() == 10**2
    assert not audit.interior_mask(grid, 0, .25).any()
    assert audit.interior_mask(grid, 1, 1.).sum() == 10**2


def test_shared_drift_is_reported_even_when_paired_contrast_is_zero():
    grid, initial = setup_arrays()
    changed = copy.deepcopy(initial)
    changed["prs"][5, 5, 5] += .25
    changed["prs"][5, 5, 6] -= .25
    changed["rho"][5, 5, 5] += .1
    changed["rho"][5, 5, 6] -= .1
    result = measure(initial, changed, changed, grid)
    for row in result["regions"]:
        assert row["boundary_all_components_pass"]
        for kind in ("reflective_delta", "outflow_delta"):
            assert row[kind]["thermal_erg"] == pytest.approx(0., abs=1e40)
            assert row[kind + "_cell_l1"]["thermal_erg"] == pytest.approx(
                .5 * audit.UNIT_ENERGY_ERG / (audit.GAMMA_GAS - 1))
            assert not row["background_drift_l1_pass"][kind]["thermal_erg"]
            assert row["mass_energy_equivalent_erg"][kind + "_cell_l1"] > 0
    assert result["smallest_tested_passing_width_kpc"] == 0
    assert result["smallest_tested_stable_width_kpc"] is None
    assert not any(row["combined_interior_pass"] for row in result["regions"])
    assert result["adopted_coarse_width_at_50_myr_kpc"] is None


def test_component_l1_failure_cannot_hide_in_signed_contrast():
    grid, initial = setup_arrays()
    changed = copy.deepcopy(initial)
    changed["prs"][0, 5, 5] += .25
    changed["prs"][0, 5, 6] -= .25
    result = measure(initial, initial, changed, grid)
    assert result["regions"][0]["contrast"]["thermal_erg"] == pytest.approx(0., abs=1e40)
    assert not result["regions"][0]["boundary_l1_pass"]["thermal_erg"]
    assert result["smallest_tested_passing_width_kpc"] == 1


@pytest.mark.parametrize("buffers", [(1.,), (0., -1.), (0., 2., 1.), (0., 1., 1.), (0., float("nan"))])
def test_invalid_buffers_rejected(buffers):
    grid, initial = setup_arrays()
    with pytest.raises(ValueError, match="buffers"):
        measure(initial, initial, initial, grid, buffers_kpc=buffers)


def test_empty_interior_rejected():
    grid, initial = setup_arrays()
    with pytest.raises(ValueError, match="no complete"):
        measure(initial, initial, initial, grid, buffers_kpc=(0., 7.))


def test_mismatched_initial_fields_rejected():
    grid, initial = setup_arrays()
    changed = copy.deepcopy(initial)
    changed["prs"][1, 1, 1] += .1
    with pytest.raises(ValueError, match="initial fields differ"):
        audit.measure_pair(initial, changed, initial, initial, grid=grid,
                           environment=Potential(), time_myr=.25)


@pytest.mark.parametrize("field,value", [("rho", 0.), ("prs", -1.), ("vx1", float("nan")), ("tr1", .1)])
def test_invalid_primitives_rejected(field, value):
    grid, initial = setup_arrays()
    outflow = copy.deepcopy(initial)
    outflow[field][0, 0, 0] = value
    with pytest.raises(ValueError):
        measure(initial, initial, outflow, grid)


def test_real_hdf5_caller_validates_receipts_and_does_not_overwrite(tmp_path):
    ref = make_run(tmp_path, "reflective")
    out = make_run(tmp_path, "outflow")
    with h5py.File(out["run_dir"] / "outputs/data.0001.dbl.h5", "r+") as h5:
        h5["Timestep_1/vars/prs"][0, 1, 2] += .25
    for options in (ref, out):
        options["output"] = options["run_dir"] / "output_receipt.json"
        validator.validate_run(**options)
    args = dict(reflective_run=ref["run_dir"], outflow_run=out["run_dir"],
                environment_path=ref["run_dir"] / "environment.csv", snapshot_index=1,
                buffers_kpc=(0., 1.), output=tmp_path / "audit.json")
    result = audit.run_audit(**args)
    assert result["status"] == "complete_paired_interior_audit"
    assert result["regions"][0]["contrast"]["thermal_erg"] > 0
    assert result["regions"][1]["contrast"]["thermal_erg"] == 0
    assert json.loads(args["output"].read_text()) == result
    with pytest.raises(ValueError, match="overwrite"):
        audit.run_audit(**args)


def test_changed_snapshot_rejected_against_receipt(tmp_path):
    ref = make_run(tmp_path, "reflective")
    out = make_run(tmp_path, "outflow")
    for options in (ref, out):
        options["output"] = options["run_dir"] / "output_receipt.json"
        validator.validate_run(**options)
    with h5py.File(out["run_dir"] / "outputs/data.0001.dbl.h5", "r+") as h5:
        h5["Timestep_1/vars/prs"][0, 1, 2] += .25
    with pytest.raises(ValueError, match="mutated"):
        audit.run_audit(reflective_run=ref["run_dir"], outflow_run=out["run_dir"],
                        environment_path=ref["run_dir"] / "environment.csv", snapshot_index=1,
                        buffers_kpc=(0., 1.), output=tmp_path / "audit.json")


@pytest.mark.parametrize("difference", ["binary", "solver"])
def test_nonboundary_pair_mismatch_rejected(tmp_path, difference):
    ref = make_run(tmp_path, "reflective")
    out = make_run(tmp_path, "outflow")
    for options in (ref, out):
        options["output"] = options["run_dir"] / "output_receipt.json"
        validator.validate_run(**options)
    receipt = json.loads(out["output"].read_text())
    if difference == "binary":
        receipt["input_files"]["pluto"]["sha256"] = "0" * 64
    else:
        receipt["configuration"]["pluto_ini"]["Time"]["CFL"] = "0.1"
    out["output"].write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="pair"):
        audit.run_audit(reflective_run=ref["run_dir"], outflow_run=out["run_dir"],
                        environment_path=ref["run_dir"] / "environment.csv", snapshot_index=1,
                        buffers_kpc=(0., 1.), output=tmp_path / "audit.json")
