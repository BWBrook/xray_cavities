import json
from pathlib import Path
import sys

import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from aperture_slab_reader import slab_fields
from aperture_surface_transport import measure_snapshot
from measure_q031_fluxes import PRIMITIVE_FIELDS
from test_aperture_surface_transport import Potential, grid_from


def native_file(path, grid, epoch):
    x, y = grid.x[None, :], grid.y[:, None]
    shape = (len(grid.z), len(grid.y), len(grid.x))
    with h5py.File(path, "w") as h5:
        timestep = h5.create_group(f"Timestep_{epoch}")
        timestep.attrs["Time"] = float(epoch)
        variables = timestep.create_group("vars")
        data = {k: variables.create_dataset(k, shape, dtype="<f4") for k in (*PRIMITIVE_FIELDS, "tr1")}
        for iz, z in enumerate(grid.z):
            data["rho"][iz] = 2 + .007*x - .012*y + epoch*(.02*z + .01*x*x)
            data["prs"][iz] = .08 + .002*x + .0003*z*z + epoch*(.001*y*y - .002*x)
            data["vx1"][iz] = .0009*(2*x - .2*y + 1 + epoch)
            data["vx2"][iz] = .001*(-y + .1*z*z + epoch) + .00001*x
            data["vx3"][iz] = .0002*(z*z - 3*x + epoch*y)


def layout(shape):
    nz, ny, nx = shape
    return grid_from(*(np.sinh(np.linspace(-1.5, 1.5, n + 1)) * scale
                       for n, scale in ((nx, 4), (ny, 4.5), (nz, 2.5))))


def profile(tmp, shape, tile):
    grid = layout(shape)
    for t in (0, 1):
        native_file(tmp / f"{t}.h5", grid, t)
    args = dict(grid=grid, environment=Potential(), tile_shape=tile,
                radii={"R100": {"previous": 4.97, "current": 7.9, "next": 6.31},
                       "R300": {"previous": 3.6, "current": 4.09, "next": 5.23}})
    counts = {}
    with h5py.File(tmp / "0.h5", "r") as f0, h5py.File(tmp / "1.h5", "r") as f1:
        initial, current = f0["Timestep_0/vars"], f1["Timestep_1/vars"]
        assert all(d.chunks is None and d.dtype == np.dtype("<f4") for d in current.values())
        for epoch, group in ((0, initial), (1, current)):
            direct = measure_snapshot(initial=initial, current=group, **args)
            baseline = slab_fields(initial)
            now = baseline if epoch == 0 else slab_fields(group)
            cached = measure_snapshot(initial=baseline, current=now, **args)
            assert json.dumps(cached, sort_keys=True, allow_nan=False) == json.dumps(direct, sort_keys=True, allow_nan=False)
            fields = list(now.values()) if epoch == 0 else [*now.values(), *baseline.values()]
            requests = sum(d.tile_requests for d in fields)
            assert requests == len(PRIMITIVE_FIELDS)*sum(direct["primitive_tiles_read"].values())
            reads = sum(d.hdf5_reads for d in fields)
            counts[epoch] = {"direct_reads": requests, "slab_reads": reads,
                             "slab_bytes": sum(d.read_bytes for d in fields)}
    return counts


def test_hdf5_estimator_identical_for_shared_and_distinct_endpoints(tmp_path):
    counts = profile(tmp_path, (25, 65, 77), (8, 9, 11))
    for row in counts.values():
        assert row["direct_reads"] > 6*row["slab_reads"]
    assert counts[0]["slab_reads"] < counts[1]["slab_reads"]


def test_overlapping_native_halos_and_independent_returned_tiles(tmp_path):
    grid = layout((19, 24, 32))
    path = tmp_path / "field.h5"
    native_file(path, grid, 0)
    with h5py.File(path, "r") as f:
        group = f["Timestep_0/vars"]
        fields = slab_fields(group)
        field = fields["rho"]
        raw = group["rho"]
        for z, y, x in ((slice(0, 8), slice(2, 12), slice(3, 18)),
                        (slice(0, 9), slice(3, 13), slice(4, 19)),
                        (slice(0, 8), slice(8, 24), slice(5, 25)),
                        (slice(8, 17), slice(16, 24), slice(6, 29)),
                        (slice(16, 19), slice(-4, None), slice(13, 31))):
            actual = field[z, y, x]
            assert actual.dtype == raw.dtype and actual.flags.c_contiguous
            assert actual.tobytes() == raw[z, y, x].tobytes()
            actual[:] = -1
        assert field.tile_requests == 5 and field.hdf5_reads == 4
        assert field.read_bytes == np.prod(raw.shape)*raw.dtype.itemsize
        assert field.buffer.shape == (9, 24, 32)
        assert all(d.buffer is None for k, d in fields.items() if k != "rho")
        for key in ((5, slice(2, 19, 3), slice(3, 7)), (Ellipsis, 6), np.s_[2:17, 2:5, 1:4]):
            assert np.array_equal(field[key], raw[key])
