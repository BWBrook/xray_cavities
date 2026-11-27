import csv
import json
import math
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import measure_ambient_tracer_sensitivity as reader
from measure_q031_fluxes import Grid
from pluto_h5_level3_ambient_extract import GAMMA_GAS, UNIT_ENERGY_ERG


def native_fixture():
    edges = [np.array(axis) for axis in (
        [-3., -1.8, -.9, -.3, .3, .9, 1.8, 3.], [-2.8, -1.4, -.6, .1, .8, 1.7, 2.8],
        [-4., -3.2, -2.2, -1.5, -1., -.6, -.3, -.1, .1, .3, .6, 1., 1.5, 2.2, 3.2, 4.])]
    grid = Grid(*[.5*(e[:-1]+e[1:]) for e in edges], *[np.diff(e) for e in edges], *edges)
    z, y, x = np.meshgrid(grid.z, grid.y, grid.x, indexing="ij")
    baseline = np.asarray(3. + .07*y*y + .053 * z, dtype="f4")
    pressure = np.asarray(baseline + .2 * x - .1*y + .16 * z*z, dtype="f4")
    low, high = np.float32(1e-4), np.float32(1e-3)
    values = [0, 1e-9, low, np.nextafter(low, np.float32(np.inf)), np.nextafter(high, np.float32(0)), high, .14, .8, 1]
    tracer = np.asarray(values, dtype="f4")[np.arange(z.size).reshape(z.shape) % len(values)]
    # Include cells exactly at the one-ulp extension of the registered radius.
    limit = math.sqrt(grid.y[2]**2 + grid.x[1]**2 + grid.z[12]**2)
    return grid, pressure, baseline, tracer, {"R100": np.nextafter(limit, -math.inf), "R300": 1.1}


def cell_oracle(grid, pressure, baseline, tracer, radii):
    cells = {key: [] for key in (*radii, "R100_minus_R300")}
    for iz, iy, ix in np.ndindex(pressure.shape):
        radius = math.sqrt((grid.y[iy]**2 + grid.x[ix]**2) + grid.z[iz]**2)
        if radius > math.nextafter(radii["R100"], math.inf):
            continue
        volume = float(grid.dx[ix] * grid.dy[iy] * grid.dz[iz])
        difference = float(pressure[iz, iy, ix]) - float(baseline[iz, iy, ix])
        thermal = difference * volume * UNIT_ENERGY_ERG / (GAMMA_GAS - 1.)
        cell = float(tracer[iz, iy, ix]), volume, thermal
        cells["R100"].append(cell)
        cells["R300" if radius <= math.nextafter(radii["R300"], math.inf) else "R100_minus_R300"].append(cell)
    return cells


def test_bound_native_reader_controls_thresholds_signed_weighting_and_shell(tmp_path, monkeypatch):
    grid, pressure, baseline, tracer, radii = native_fixture()
    cells = cell_oracle(grid, pressure, baseline, tracer, radii)
    case_dir = tmp_path / "requests" / "C-LO"
    case_dir.mkdir(parents=True)
    axes = {k: getattr(grid, k) for k in reader.AXES}
    np.savez(case_dir / "axes.npz", **axes)
    records, snapshots = [{} for _ in range(51)], [{} for _ in range(51)]
    for i, p in [(0, baseline), (50, pressure)]:
        path = tmp_path / f"data.{i:04}.flt.h5"
        step = f"Timestep_{i}"
        with h5py.File(path, "w") as h5:
            for axis in "xyz":
                h5[f"cell_coords/{axis.upper()}"] = axes[axis]
                h5[f"node_coords/{axis.upper()}"] = axes[axis + "_edges"]
            h5.create_group(step).attrs["Time"] = i * 1.27
            for k, value in {"rho": np.ones_like(p), "prs": p, "tr1": tracer,
                             **{k: np.zeros_like(p) for k in ("vx1", "vx2", "vx3")}}.items():
                h5[f"{step}/vars/{k}"] = value
        st = path.stat()
        native = dict(sha256=reader.sha(path), resolved_path=str(path.resolve()), size_bytes=st.st_size,
                      inode=st.st_ino, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)
        records[i] = dict(index=i, native=native, fixed_receipt_sha256="a"*64, age_myr=float(i), time_code=i*1.27, timestep=step, shape=list(p.shape))
        snapshots[i] = dict(index=i, native_sha256=native["sha256"], fixed_sha256="a"*64, age_myr=float(i),
                            apertures={k: {"raw_radius_kpc": v} for k, v in radii.items()})
    request_file = case_dir / "request.json"
    request_file.write_text(json.dumps({"case": "C-LO", "history": records}))
    binding = {"input_request_sha256": reader.sha(request_file), "static_sha256": {"axes.npz": reader.sha(case_dir / "axes.npz")},
               "snapshots": snapshots}
    reg = tmp_path / "registration.json"
    reg.write_text(json.dumps({"cases": {"C-LO": binding}}))
    monkeypatch.setattr(reader, "REGISTRATION_SHA", reader.sha(reg))
    rows = []
    for name in radii:
        for region, cut in (("all", 1.), ("ambient", 1e-3)):
            chosen = [(v, e) for tr, v, e in cells[name] if tr <= cut]
            rows.append(dict(case="C-LO", snapshot_index=50, aperture=name, region=region, actual_age_myr=50.,
                             raw_radius_kpc=radii[name], cumulative_net_gas_delivery_erg=1e63, cell_count=len(chosen),
                             volume_kpc3=math.fsum(v for v, _ in chosen), thermal_delta_erg=math.fsum(e for _, e in chosen)))
    stocks = tmp_path / "stocks.csv"
    with stocks.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    monkeypatch.setattr(reader, "STOCK_SHA", reader.sha(stocks))
    result = reader.extract(tmp_path, "C-LO", 50, stocks)
    for name, selected in cells.items():
        figures = result["apertures"][name]
        for label, cut in (("all", 1.), ("ambient_le_1e-3", 1e-3), ("ambient_le_1e-4", 1e-4)):
            data = [(t, v, e) for t, v, e in selected if t <= cut]
            assert any(e < 0 for _, _, e in data) and any(e > 0 for _, _, e in data)
            assert figures[label]["cell_count"] == len(data)
            assert math.isclose(figures[label]["thermal_change_erg"], math.fsum(e for _, _, e in data), rel_tol=1e-13)
            assert math.isclose(figures[label]["one_minus_tr1_thermal_change_over_delivery"],
                                math.fsum((1-t)*e for t, _, e in data)/1e63, rel_tol=1e-13)
        assert [b["cell_count"] for b in figures["bands"].values()] == [
            sum(lo < t <= hi for t, _, _ in selected) for lo, hi in [(-1., 0.), (0., 1e-4), (1e-4, 1e-3), (1e-3, 1.)]]
    out = tmp_path / "result.json"
    reader.publish(out, result)
    reader.publish(out, result)
    with pytest.raises(ValueError, match="Existing receipt differs"):
        reader.publish(out, {})
    with h5py.File(tmp_path / "data.0050.flt.h5", "r+") as live:
        live["Timestep_50/vars/tr1"][7, 2, 3] = 0.77
    with pytest.raises(ValueError, match="identity changed"):
        reader.extract(tmp_path, "C-LO", 50, stocks)


@pytest.mark.parametrize("bad", [-1e-4, 1.2, float("nan")])
def test_invalid_native_tracer_inside_the_aperture(bad):
    grid, pressure, baseline, tracer, radii = native_fixture()
    tracer[7, 2, 3] = bad
    with pytest.raises(ValueError, match="Invalid tracer fraction"):
        reader.measure({"prs": pressure, "tr1": tracer}, {"prs": baseline}, grid, radii, 1e63)


def test_single_r100_across_short_stripes():
    grid, pressure, baseline, tracer, radii = native_fixture()
    fields = {"prs": pressure, "tr1": tracer}
    found = reader.measure(fields, {"prs": baseline}, grid, {"R100": radii["R100"]}, 1e63, slab_planes=2)
    selected = cell_oracle(grid, pressure, baseline, tracer, radii)["R100"]
    assert set(found["apertures"]) == {"R100"}
    assert found["tracer_range_in_R100"] == [0., 1.]
    assert found["apertures"]["R100"]["all"]["cell_count"] == len(selected)
    assert math.isclose(found["apertures"]["R100"]["all"]["one_minus_tr1_thermal_change_erg"],
                        math.fsum((1-t)*e for t, _, e in selected), rel_tol=1e-13)
