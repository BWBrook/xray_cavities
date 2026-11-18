from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pytest


SCIENCE = Path(__file__).resolve().parents[1] / "scripts" / "science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))
import measure_ghi_final_flux as final
import measure_q031_fluxes as flux
from select_common_age_hdf5 import Snapshot


class QuadraticPotential:
    def potential_at_radius(self, radius):
        return 0.01 * (np.asarray(radius) / flux.UNIT_LENGTH_CM)**2 * flux.UNIT_VELOCITY_CMS**2


def grid():
    centres = np.arange(13, dtype=float) - 6
    widths = np.ones(13)
    edges = np.arange(14, dtype=float) - 6.5
    return flux.Grid(centres, centres.copy(), centres.copy(), widths, widths.copy(),
                     widths.copy(), edges, edges.copy(), edges.copy())


def primitives():
    shape = (13, 13, 13)
    return {name: np.full(shape, value) for name, value in
            zip(flux.PRIMITIVE_FIELDS, (1.0, 1.0, 0.2, -0.1, 0.3), strict=True)}


def cached(values):
    cache = flux.DomainPlaneCache.create(values["rho"].shape)
    for k in range(values["rho"].shape[0]):
        cache.capture_z_slab(k, {name: value[k] for name, value in values.items()})
    return cache


def snapshot_file(path, values):
    with h5py.File(path, "w") as h5:
        timestep = h5.create_group("Timestep_47")
        timestep.attrs["Time"] = 470.0
        variables = timestep.create_group("vars")
        for name, data in values.items():
            variables.create_dataset(name, data=data)
        variables.create_dataset("tr1", data=np.zeros(values["rho"].shape))
    return Snapshot(path, "Timestep_47", 47, 470.0, values["rho"].shape, path.stat().st_size)


def controls(mesh):
    return {padding: flux.derive_control_box(mesh, injection_height_kpc=0.1,
            centre_kpc=(0.0, 0.0, 0.0), padding_cells=padding) for padding in (1, 2, 4)}


def test_valid_endpoint_matches_original_all_rows(tmp_path):
    snapshot = snapshot_file(tmp_path / "data.0047.flt.h5", primitives())
    mesh = grid()
    kwargs = {"grid": mesh, "environment": QuadraticPotential(),
              "boxes": controls(mesh), "shell_layers": (1, 2, 4, 8)}
    result = final.measure_final_snapshot(snapshot, **kwargs)
    expected_flux, expected_storage = flux.analyze_snapshot(snapshot, **kwargs)
    assert result["flux_rows"] == expected_flux
    assert result["storage_rows"] == expected_storage
    assert len(result["flux_rows"]) == 56
    assert len(result["storage_rows"]) == 16
    assert result["linear_diagnostics"]["all_faces_linear_valid"]
    assert result["linear_diagnostics"]["native_primitives_valid"]
    assert result["linear_diagnostics"]["linear_invalid_cell_count_sum_over_faces"] == 0
    assert result["surface_availability"]["domain_boundary"]["linear_to_boundary_face"]["available"]
    assert result["snapshot"] == flux._snapshot_metadata(snapshot)
    assert not result["scientific_qualification"]["qualified"]
    json.dumps(result, allow_nan=False)


def test_multiple_invalid_faces_keep_all_valid_unchanged_rows(tmp_path):
    values = primitives()
    values["prs"][4, 6, 1] = 10.0
    values["rho"][11, 6, 7] = 10.0
    snapshot = snapshot_file(tmp_path / "data.0047.flt.h5", values)
    mesh = grid()
    boxes = controls(mesh)
    environment = QuadraticPotential()
    result = final.measure_final_snapshot(snapshot, grid=mesh, environment=environment, boxes=boxes)
    diagnostic = result["linear_diagnostics"]
    assert diagnostic["native_primitives_valid"]
    assert diagnostic["invalid_faces"] == ["x_negative", "z_positive"]
    assert diagnostic["linear_invalid_cell_count_sum_over_faces"] == 2
    assert len(diagnostic["faces"]) == 6
    assert len(result["flux_rows"]) == 49
    assert len(result["storage_rows"]) == 16
    assert all(row["reconstruction"] != "linear_to_boundary_face" for row in result["flux_rows"])
    availability = result["surface_availability"]["domain_boundary"]["linear_to_boundary_face"]
    assert availability == {"available": False, "reason": "invalid_linear_primitive_faces",
                            "invalid_faces": ["x_negative", "z_positive"]}
    with h5py.File(snapshot.input_h5, "r") as h5:
        variables = h5["/Timestep_47/vars"]
        expected = [{"surface": "domain_boundary", "reconstruction": "outer_active_cell", **row}
                    for row in flux.measure_domain_surface(variables, mesh, environment, "outer_active_cell")]
        for padding, box in boxes.items():
            for method in flux.CONTROL_RECONSTRUCTIONS:
                expected.extend({"surface": f"nozzle_control_p{padding}", "reconstruction": method, **row}
                                for row in flux.measure_control_surface(variables, mesh, environment, box, method))
        expected_storage = flux.measure_storage(variables, mesh, environment, boxes, (1, 2, 4, 8))
    prefix = {name: result["flux_rows"][0][name] for name in
              ("snapshot_index", "actual_time_code", "actual_time_myr", "input_h5", "timestep")}
    assert result["flux_rows"] == [{**prefix, **row} for row in expected]
    assert result["storage_rows"] == [{**prefix, **row} for row in expected_storage]
    with pytest.raises(ValueError, match="linear boundary-face reconstruction"):
        flux.analyze_snapshot(snapshot, grid=mesh, environment=environment,
                              boxes=boxes, shell_layers=(1, 2, 4, 8))
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("face,active,inner,coordinate", [
    ("x_negative", (4, 6, 0), (4, 6, 1), [-6.5, 0.0, -2.0]),
    ("x_positive", (4, 6, 12), (4, 6, 11), [6.5, 0.0, -2.0]),
    ("y_negative", (4, 0, 7), (4, 1, 7), [1.0, -6.5, -2.0]),
    ("y_positive", (4, 12, 7), (4, 11, 7), [1.0, 6.5, -2.0]),
    ("z_negative", (0, 6, 7), (1, 6, 7), [1.0, 0.0, -6.5]),
    ("z_positive", (12, 6, 7), (11, 6, 7), [1.0, 0.0, 6.5]),
])
def test_all_face_orientations_report_every_invalid_value(face, active, inner, coordinate):
    values = primitives()
    values["prs"][inner] = 10.0
    values["rho"][inner] = 12.0
    result = final.diagnose_linear_boundaries(cached(values), grid())
    assert result["native_primitives_valid"]
    assert result["invalid_faces"] == [face]
    assert result["linear_invalid_cell_count_sum_over_faces"] == 1
    record = next(r for r in result["faces"] if r["face"] == face)
    assert record["linear"]["invalid_cell_count"] == 1
    for name, expected in (("prs", -3.5), ("rho", -4.5)):
        field = record["linear"]["fields"][name]
        assert field["nonpositive_count"] == field["invalid_count"] == 1
        assert field["nonfinite_count"] == 0
        assert len(field["invalid_cells"]) == 1
        cell = field["invalid_cells"][0]
        assert cell["value"] == cell["linear_value"] == expected
        assert cell["active_value"] == 1.0
        assert cell["inner_value"] == values[name][inner]
        assert cell["active_cell_index_zyx"] == list(active)
        assert cell["inner_cell_index_zyx"] == list(inner)
        assert cell["face_xyz_kpc"] == coordinate
    assert not record["original_linear_gate_passed"]
    assert record["original_linear_gate_error"] == "linear boundary-face reconstruction produced a non-physical primitive state"


def test_native_nonfinite_values_are_distinct_and_storage_still_fails_closed(tmp_path):
    values = primitives()
    values["prs"][4, 6, 0] = -1.0
    values["vx2"][12, 6, 7] = np.nan
    result = final.diagnose_linear_boundaries(cached(values), grid())
    assert not result["native_primitives_valid"]
    assert result["invalid_faces"] == ["x_negative", "z_positive"]
    xface, zface = result["faces"][0], result["faces"][-1]
    assert xface["active"]["fields"]["prs"]["invalid_cells"][0]["value"] == -1.0
    assert xface["original_linear_gate_error"] == "non-positive density or pressure on a measured surface"
    assert zface["active"]["fields"]["vx2"]["invalid_cells"][0]["value"] == "nan"
    assert zface["linear"]["fields"]["vx2"]["invalid_cells"][0]["linear_value"] == "nan"
    json.dumps(result, allow_nan=False)
    snapshot = snapshot_file(tmp_path / "data.0047.flt.h5", values)
    with pytest.raises(ValueError, match="non-positive density or pressure"):
        final.measure_final_snapshot(snapshot, grid=grid(), environment=QuadraticPotential(), boxes={})


def test_invalid_inventory_is_not_truncated_at_first_cell_or_field():
    values = primitives()
    positions = [(3, 5, 1), (4, 6, 1), (5, 7, 1)]
    for position in positions:
        values["prs"][position] = 10.0
        values["rho"][position] = 12.0
    result = final.diagnose_linear_boundaries(cached(values), grid())
    assert result["invalid_faces"] == ["x_negative"]
    assert result["linear_invalid_cell_count_sum_over_faces"] == 3
    linear = result["faces"][0]["linear"]
    assert linear["invalid_cell_count"] == 3
    for field in ("rho", "prs"):
        report = linear["fields"][field]
        assert report["invalid_count"] == len(report["invalid_cells"]) == 3
        assert [cell["inner_cell_index_zyx"] for cell in report["invalid_cells"]] == [list(p) for p in positions]


def test_nonuniform_boundary_fraction_uses_original_geometry():
    mesh = grid()
    edges = np.array([-7.0, -6.0, -4.7, -3.2, -2.1, -0.8, 0.0,
                      0.9, 2.0, 3.2, 4.0, 5.3, 6.0, 8.0])
    mesh = replace(mesh, y=0.5*(edges[:-1]+edges[1:]), dy=np.diff(edges), y_edges=edges)
    values = primitives()
    values["prs"][4, 11, 7] = 10.0
    result = final.diagnose_linear_boundaries(cached(values), mesh)
    record = next(r for r in result["faces"] if r["face"] == "y_positive")
    expected_fraction = 1.0 / (7.0 - 5.65)
    assert record["face_fraction"] == pytest.approx(expected_fraction)
    assert record["face_fraction"] != 0.5
    cell = record["linear"]["fields"]["prs"]["invalid_cells"][0]
    assert cell["value"] == pytest.approx(1.0 - 9.0 * expected_fraction)
    assert cell["face_xyz_kpc"] == [1.0, 8.0, -2.0]


def test_addendum_refuses_other_snapshot_indices(tmp_path):
    snapshot = snapshot_file(tmp_path / "data.0047.flt.h5", primitives())
    with pytest.raises(ValueError, match="restricted to snapshot index 47"):
        final.measure_final_snapshot(replace(snapshot, output_index=46), grid=grid(),
                                     environment=QuadraticPotential(), boxes={})
