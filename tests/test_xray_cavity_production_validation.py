from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCRIPT = Path("scripts/science/validate_xray_cavity_production.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("validate_xray_cavity_production", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_conservative_column_regrid_preserves_physical_integral() -> None:
    module = load_module()
    source_axis = np.array([-2.0, -0.5, 1.5, 3.0])
    source_edges = module.centres_to_edges(source_axis)
    target_edges = np.linspace(source_edges[0], source_edges[-1], 8)
    target_axis = 0.5 * (target_edges[:-1] + target_edges[1:])
    vertical = np.array([-1.0, 0.0, 1.0])
    values = np.vstack((source_axis + 4.0, 2.0 * source_axis + 8.0, source_axis**2 + 2.0))

    target = module.conservative_regrid_columns(values, source_axis, target_axis)

    assert module.physical_integral(target, target_axis, vertical) == pytest.approx(
        module.physical_integral(values, source_axis, vertical), rel=1.0e-12
    )


def test_fixture_builder_writes_production_schema_and_predeclared_criteria(tmp_path: Path) -> None:
    run_root = tmp_path / "validation"

    subprocess.run(
        [sys.executable, str(SCRIPT), "make-fixtures", "--run-root", str(run_root)],
        check=True,
    )

    contract = list(csv.DictReader((run_root / "contracts/synthetic_fixture_contract.csv").open()))
    criteria = list(csv.DictReader((run_root / "contracts/acceptance_criteria.csv").open()))
    assert {row["case"] for row in contract} == {"axisymmetric", "nonaxisymmetric"}
    assert {row["gate"] for row in criteria} == {
        "fixture_schema",
        "physical_flux_conservation",
        "native_axis_equivalence",
        "near_90_continuity",
        "projected_occupancy",
        "synthetic_cavity_recovery",
        "real_endpoint_recovery",
        "energy_convention",
        "determinism",
        "provenance",
    }
    for row in contract:
        path = Path(row["path"])
        with h5py.File(path, "r") as h5:
            assert h5["Timestep_0"].attrs["Time"] == pytest.approx(15330.0696894)
            assert set(h5["Timestep_0/vars"]) == {"rho", "prs", "tr1", "vx1", "vx2", "vx3"}
            shapes = {h5[f"Timestep_0/vars/{name}"].shape for name in h5["Timestep_0/vars"]}
            assert len(shapes) == 1
            assert h5["cell_coords/X"].shape in shapes
            assert h5["cell_coords/Y"].shape in shapes
            assert h5["cell_coords/Z"].shape in shapes
            assert np.any(h5["Timestep_0/vars/tr1"][:] >= 5.0e-3)
        assert row["x_nonuniform"] == "True"
        assert row["y_nonuniform"] == "True"
        assert row["z_nonuniform"] == "True"
        assert len(row["sha256"]) == 64


def test_comparison_is_exact_after_conservative_common_grid_rebin() -> None:
    module = load_module()
    source_axis = np.array([-3.0, -1.0, 0.5, 3.0])
    source_edges = module.centres_to_edges(source_axis)
    target_edges = np.linspace(source_edges[0], source_edges[-1], 9)
    target_axis = 0.5 * (target_edges[:-1] + target_edges[1:])
    vertical = np.array([-1.0, 0.0, 1.0])
    direct = np.vstack((source_axis + 5.0, source_axis + 6.0, source_axis + 7.0))
    edge = module.conservative_regrid_columns(direct, source_axis, target_axis)
    reference = module.MapProduct(direct, direct, np.ones_like(direct), source_axis, vertical)
    candidate = module.MapProduct(edge, edge, np.ones_like(edge), target_axis, vertical)

    row, common, residual = module.compare_products(
        "synthetic", reference, candidate, "native_axis_equivalence"
    )

    np.testing.assert_allclose(common, edge)
    np.testing.assert_allclose(residual, 0.0, atol=1.0e-15)
    assert row["flux_relative_error"] == pytest.approx(0.0, abs=1.0e-15)
    assert row["normalized_l1_residual"] == pytest.approx(0.0, abs=1.0e-15)


def test_metadata_decision_labels_fail_closed() -> None:
    module = load_module()
    criteria = module.acceptance_criteria()

    assert len(criteria) == 10
    assert all("tolerance" in row for row in criteria)
    assert json.loads(json.dumps(criteria))[0]["gate"] == "fixture_schema"


def test_energy_gate_checks_positive_values_and_exact_multipliers() -> None:
    module = load_module()
    rows = [
        {
            "case": "synthetic",
            "product": "direct0",
            "component_index": 1,
            "convention": convention,
            "energy_erg": energy,
        }
        for convention, energy in (("pV", 2.0), ("2.5pV", 5.0), ("4pV", 8.0))
    ]

    passed, observed = module.energy_gate_result(rows)

    assert passed
    assert "3/3 finite positive" in observed
    rows[-1]["energy_erg"] = 7.5
    assert not module.energy_gate_result(rows)[0]
    rows[-1]["energy_erg"] = 0.0
    assert not module.energy_gate_result(rows)[0]
