import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import check_four_case_slab_rows as rows


def test_signed_rows_and_zero_reference():
    slab, side = np.array([0., 2., -2., 7.]), np.array([0., 0., -4., 5.])
    rel, delta, stats = rows.compare_rows(slab, side, np.array([1., 2., 3., 4.]))
    np.testing.assert_allclose(rel, [np.nan, np.nan, -.5, .4], equal_nan=True)
    np.testing.assert_equal(delta, [0, 2, 2, 2])
    assert stats["both_zero_rows"] == stats["nonzero_slab_zero_reference_rows"] == 1
    assert stats["negative_reference_rows"] == stats["negative_slab_rows"] == 1
    assert stats["total_ratio_minus_one"] == 6
    assert stats["dz_weighted_total_ratio_minus_one"] == 26 / 8 - 1
    assert stats["largest_row_difference_over_largest_row"] == .4
    zero = np.zeros(3)
    _, _, cancelled = rows.compare_rows(np.array([1., -1., 0]), zero, np.ones(3))
    assert all(cancelled[key] is None for key in ("total_ratio_minus_one", "largest_row_ratio_minus_one",
                                                 "largest_row_difference_over_largest_row"))
    _, _, cancelled = rows.compare_rows(np.array([1., 1.]), np.array([1., -1.]), np.ones(2))
    assert cancelled["total_ratio_minus_one"] is None
    assert cancelled["largest_row_ratio_minus_one"] == 2


def test_boundary_pixel_widths_and_directions():
    edges = np.arange(-4., 5.)
    cuts = {mode: rows.weights(edges, -1.25, 1.25, mode) for mode in ("exact", *rows.SENSITIVITIES)}
    np.testing.assert_equal(cuts["exact"], [0, 0, .25, 1, 1, .25, 0, 0])
    np.testing.assert_equal(cuts["whole_intersecting_pixels"], [0, 0, 1, 1, 1, 1, 0, 0])
    np.testing.assert_equal(cuts["shifted_plus_u_one_pixel"], [0, 0, 0, .25, 1, 1, .25, 0])
    np.testing.assert_equal(cuts["shifted_minus_u_one_pixel"], [0, .25, 1, 1, .25, 0, 0, 0])
    assert cuts["widen_each_edge_one_pixel"].sum() == 4.5
    assert cuts["narrow_each_edge_one_pixel"].sum() == .5
    np.testing.assert_equal(rows.weights(edges, 3, 4, "shifted_plus_u_one_pixel"), np.zeros(8))
    with pytest.raises(ValueError, match="uniform"):
        rows.weights(np.array([-3., -1., 2., 5.]), -1, 1, "exact")


def write_json(path, values):
    path.write_text(json.dumps(values))
    return rows.sha256(path)


def file_record(path):
    return {"size_bytes": path.stat().st_size, "sha256": rows.sha256(path)}


def make_pair(tmp_path, *, bad_initial_source=False, bad_z=False):
    xe = np.array([-4,-3,-2,-1,0,2,4,5,9,11,18], dtype=float)
    ye = np.arange(-50., 60, 10)
    ze = np.array([-3., -2., 0., 4., 8.])
    def axes(horizontal):
        return dict(zip(rows.AXES, ((horizontal[:-1] + horizontal[1:]) / 2, horizontal,
                                    (ze[:-1] + ze[1:]) / 2, ze)))
    z, y, x = np.indices((4, 10, 10))
    current = (2 + 3*z + 2*y - x) * (z != 0)
    initial = (17 + z - 2*y + 2*x) * (z != 0)
    tracer = (y > 4) & (x < 7) & (z < 3)
    maps = axes(xe)
    depths = {}
    for depth, half in (("full",50.), ("slab30",30.), ("slab10",10.)):
        depths[depth] = {"y_min_kpc": -half, "y_max_kpc": half, "integrated_width_kpc": 2*half}
        w = np.maximum(0, np.minimum(ye[1:], half) - np.maximum(ye[:-1], -half))
        for name, gas in (("current",current), ("initial",initial), ("current_lobe",current*tracer),
                          ("initial_on_current_lobe",initial*tracer)):
            maps[f"{name}_{depth}"] = np.sum(gas*w[None, :, None], axis=1)
    new = tmp_path / "projection"
    new.mkdir()
    product = new / "projections.npz"
    np.savez(product, **maps)
    native = {"current_h5": "a"*64, "initial_h5": "b"*64, "environment": "e"*64}
    refs, pins, pairs = {}, {}, {}
    for phase, age, gas in (("current", 10, current), ("initial", 0, initial)):
        name = f"C-LO_{age:04d}"
        path = tmp_path / f"{name}_90deg.npz"
        side_axis = axes(ye)
        if bad_z and age == 0:
            side_axis["z_axis_kpc"] = side_axis["z_axis_kpc"] + .1
        side = np.sum(gas*np.diff(xe)[None, None, :], axis=2)[:, ::-1]
        np.savez(path, **side_axis, brightness_current_retained_linear_whole=side)
        files = {f"{name}_0deg.npz": {"size_bytes": 100, "sha256": "f"*64}, path.name: file_record(path)}
        for angle in (0,90):
            filename = f"{name}_{angle}deg.npz"
            refs[f"{phase}_{angle}"] = {"filename": filename, **files[filename]}
        roles = dict(native)
        if not age:
            roles["current_h5"] = "c"*64 if bad_initial_source else native["initial_h5"]
        archive = tmp_path / f"{name}.json"
        pins[phase] = write_json(archive, {
            "case": "C-LO", "snapshot_index": age, "actual_time_myr": float(age), "files": files,
            "projection": {"0": {}, "90": {}},
            "provenance": {"native_inputs": [{"role": k, "sha256": v} for k, v in roles.items()]}})
        pairs[phase] = (archive, path)
    write_json(new / "completion.json", {
        "status": "complete", "case": "C-LO", "snapshot_index": 10, "actual_time_myr": 10., "view_deg": 0,
        "native_shape_zyx": [4, 10, 10], "y_extent_kpc": [-50., 50.], "depths": depths,
        "native_inputs_sha256": native, "previous_producer_sha256": pins["current"],
        "initial_previous_producer_sha256": pins["initial"], "previous_map_sha256": refs["current_0"]["sha256"],
        "references": refs, "files": {product.name: file_record(product)}})
    return (new, *pairs["current"], *pairs["initial"], tmp_path / "out")


def test_turn27_archive_pair_exact_rows_and_absent_components(tmp_path):
    inputs = make_pair(tmp_path)
    receipt = rows.run(*inputs)
    assert receipt["native_z_rows"] == 4 and receipt["initial_field_source"] == "case/0000 current whole"
    with (inputs[-1] / "row_summary.csv").open() as stream:
        summary = list(csv.DictReader(stream))
    assert len(summary) == 22
    assert all(r["status"] == "unchecked" and r["compared_z_rows"] == "0" for r in summary if "lobe" in r["field"])
    exact = [r for r in summary if r["side_view_cut"] == "exact" and r["field"] in ("current", "initial")]
    assert len(exact) == 6
    assert all(r["both_zero_rows"] == "1" and float(r["max_abs_row_difference"]) == 0 for r in exact)
    with gzip.open(inputs[-1] / "row_totals.csv.gz", "rt") as stream:
        detail = list(csv.DictReader(stream))
    assert len(detail) == receipt["detailed_rows"] == 64
    assert all(r["slab_over_side_minus_one"] == "" for r in detail if r["z_row"] == "0")
    with pytest.raises(FileExistsError):
        rows.run(*inputs)


@pytest.mark.parametrize(("kwargs", "message"), [({"bad_z": True}, "exact native z rows"),
                                                ({"bad_initial_source": True}, "native input digests")])
def test_mismatched_initial_identity_fails_before_publication(tmp_path, kwargs, message):
    inputs = make_pair(tmp_path, **kwargs)
    with pytest.raises(ValueError, match=message):
        rows.run(*inputs)
    assert not inputs[-1].exists()


def test_side_archive_bytes_bound_to_evolved_receipt(tmp_path):
    inputs = make_pair(tmp_path)
    with inputs[2].open("ab") as side:
        side.write(b"changed")
    with pytest.raises(ValueError, match="Size or digest"):
        rows.run(*inputs)
    assert not inputs[-1].exists()
