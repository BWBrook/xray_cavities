import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import measure_native_clock_geometry as reader
from measure_q031_fluxes import Grid
from pluto_h5_level3_ambient_extract import UNIT_ENERGY_ERG


def test_native_receipt_against_individual_stretched_cells(tmp_path, monkeypatch):
    edges = [np.array(axis) for axis in ([-5., -2., -1., 0., 3., 5.], [-4., -1., 1., 2.],
                                         [-6., -3., -1.5, -.3, .3, 2., 6.])]
    grid = Grid(*[(e[:-1] + e[1:]) / 2 for e in edges], *[np.diff(e) for e in edges], *edges)
    shape = (len(grid.z), len(grid.y), len(grid.x))
    pressure = np.arange(1, math.prod(shape) + 1, dtype=np.float32).reshape(shape)
    tracer = np.zeros(shape, dtype=np.float32)
    for cell in [(0, 0, 0), (0, 1, 1), (1, 0, 0), (2, 2, 3), (2, 1, 1),
                 (3, 1, 2), (3, 1, 3), (5, 1, 2), (5, 2, 4)]:
        tracer[cell] = .7
    tracer[3, 1, 1] = np.float32(1e-3)
    tracer[3, 0, 2] = np.nextafter(np.float32(1e-3), np.float32(0))
    assert float(tracer[3, 0, 2]) < 1e-3 < float(tracer[3, 1, 1])

    case_dir = tmp_path / "requests" / "G-LO"
    case_dir.mkdir(parents=True)
    axes = {k: getattr(grid, k) for k in ("x", "y", "z", "x_edges", "y_edges", "z_edges")}
    np.savez(case_dir / "axes.npz", **axes)
    native = tmp_path / "data.0010.flt.h5"
    step = "Timestep_12345"
    with h5py.File(native, "w") as h5:
        for axis in "xyz":
            h5[f"cell_coords/{axis.upper()}"] = axes[axis]
            h5[f"node_coords/{axis.upper()}"] = axes[axis + "_edges"]
        h5.create_group(step).attrs["Time"] = 3.246
        for name, values in {"prs": pressure, "tr1": tracer, "rho": np.ones_like(pressure),
                             **{k: np.zeros_like(pressure) for k in ("vx1", "vx2", "vx3")}}.items():
            h5[f"{step}/vars/{name}"] = values
    stat = native.stat()
    bound = dict(sha256=reader.sha(native), resolved_path=str(native.resolve()), size_bytes=stat.st_size,
                 inode=stat.st_ino, ctime_ns=stat.st_ctime_ns, mtime_ns=stat.st_mtime_ns)
    record = dict(index=10, native=bound, fixed_receipt_sha256="a"*64, age_myr=10.001,
                  time_code=3.246, timestep=step, shape=list(shape))
    snapshot = dict(index=10, native_sha256=bound["sha256"], fixed_sha256="a"*64, age_myr=10.001)
    request = case_dir / "request.json"
    request.write_text(json.dumps({"case": "G-LO", "history": [None]*10 + [record]}))
    frozen = dict(input_request_sha256=reader.sha(request), static_sha256={"axes.npz": reader.sha(case_dir / "axes.npz")},
                  snapshots=[None]*10 + [snapshot])
    registration = tmp_path / "registration.json"
    registration.write_text(json.dumps({"cases": {"G-LO": frozen}}))
    monkeypatch.setattr(reader, "REGISTRATION_SHA", reader.sha(registration))

    result = reader.extract(tmp_path, "G-LO", 10)
    assert result["actual_age_myr"] == 10.001 and result["native_sha256"] == reader.sha(native)
    assert result["sides"] == reader.measure({"prs": pressure, "tr1": tracer}, grid, slab_planes=1)
    for sign, side in [(-1, "negative_z"), (1, "positive_z")]:
        row = result["sides"][side]
        cells = [(k, j, i) for k, j, i in np.ndindex(shape)
                 if float(tracer[k, j, i]) > .001 and (grid.z[k] >= 0) == (sign == 1)]
        widths = [grid.dx[i] * grid.dy[j] * grid.dz[k] for k, j, i in cells]
        volume = sum(widths)
        pv = sum(float(pressure[cell]) * dv for cell, dv in zip(cells, widths, strict=True)) * UNIT_ENERGY_ERG
        assert row["cell_count"] == len(cells) and row["volume_kpc3"] == pytest.approx(volume)
        assert row["enthalpy_2p5pV_erg"] == pytest.approx(2.5 * pv) and row["pv_erg"] == pytest.approx(pv)
        assert row["enthalpy_4pV_erg"] == pytest.approx(4 * pv)
        centroid = np.average([(grid.x[i], grid.y[j], grid.z[k]) for k, j, i in cells], axis=0, weights=widths)
        np.testing.assert_allclose([row[f"centroid_{axis}_kpc"] for axis in "xyz"], centroid)
        assert row["centroid_radius_kpc"] == pytest.approx(math.hypot(*centroid))
        assert row["centroid_angle_to_outward_axis_deg"] == pytest.approx(
            math.degrees(math.acos(sign * centroid[2] / math.hypot(*centroid))))
        by_plane = {}
        for k, j, i in cells:
            by_plane[k] = by_plane.get(k, 0.) + grid.dx[i] * grid.dy[j]
        union = {(j, i) for k, j, i in cells}
        assert row["sections"]["z_index"] == list(by_plane)
        np.testing.assert_allclose(row["sections"]["dz_kpc"], grid.dz[list(by_plane)])
        np.testing.assert_allclose(row["sections"]["z_kpc"], grid.z[list(by_plane)])
        np.testing.assert_allclose(row["sections"]["area_kpc2"], list(by_plane.values()))
        assert row["axial_max_section_kpc2"] == max(by_plane.values())
        assert row["axial_union_area_kpc2"] == sum(grid.dx[i] * grid.dy[j] for j, i in union)
        assert row["axial_union_area_kpc2"] > row["axial_max_section_kpc2"]
        walls = ["x_min", "y_min", "y_max", "z_min"] if sign == -1 else ["x_max", "y_max", "z_max"]
        assert row["wall_faces"] == walls
    out = tmp_path / "result.json"
    reader.publish(out, result)
    assert json.loads(out.read_bytes()) == result
    with h5py.File(native, "r+") as h5:
        h5[f"{step}/vars/tr1"][0, 0, 0] = 0
    with pytest.raises(ValueError, match="identity changed"):
        reader.extract(tmp_path, "G-LO", 10)


def test_rejects_g_hi_50_before_opening_native_inputs(tmp_path):
    with pytest.raises(ValueError, match="19 registered"):
        reader.extract(tmp_path, "G-HI", 50)
