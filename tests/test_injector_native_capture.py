import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from capture_injector_states import capture, sha
from reduce_injector_patches import read_domain_balances, read_tracer_intervals, reduce_case
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR
from pluto_h5_level3_ambient_extract import UNIT_VELOCITY_CMS


def test_tracer_reference_distinguishes_three_intervals_ending_at_30():
    source = Path(__file__).resolve().parents[1] / "docs/science/assets/tracer_mass_budget_2026-11-19/tagged_mass_intervals.csv"
    with source.open() as stream:
        references = read_tracer_intervals(csv.DictReader(stream))
    assert len(references) == 197 + 8
    for case in ("C-HI", "C-LO", "G-HI", "G-LO"):
        annual, decade, two_decades = [float(references[case, start, 30]["labelled_mass_g"]) for start in (29, 20, 10)]
        assert decade / annual == pytest.approx(10, rel=.001)
        assert two_decades / annual == pytest.approx(20, rel=.001)
    row = references["G-HI", 29, 30]
    with pytest.raises(ValueError, match="Duplicate tracer interval"):
        read_tracer_intervals([row, row])


def test_archived_domain_endpoint_keeps_two_unknown_balances():
    archive = Path(__file__).resolve().parents[1] / "docs/science/assets/outer_tracer_gravity_2026-11-19/compact_inputs.zip"
    with zipfile.ZipFile(archive) as source, source.open("source_check.csv") as data:
        records = list(csv.DictReader(io.TextIOWrapper(data)))
    values = read_domain_balances(records)
    assert len(values) == 197 * 6
    assert {k for k, v in values.items() if v is None} == {
        ("G-HI", 47, "linear_to_boundary_face", rule) for rule in ("right", "trapezoid")}
    assert values["G-HI", 47, "linear_to_boundary_face", "left"] > 0
    good = next(r for r in records if r["surface"] == "domain_boundary" and r["inferred_energy_source_erg"])
    with pytest.raises(ValueError, match="coverage"):
        read_domain_balances([{**good, "inferred_energy_source_erg": ""}])


def test_bound_patch_and_outer_read_then_replay(tmp_path):
    req, out = tmp_path / "input", tmp_path / "output"
    req.mkdir()
    edges = (np.arange(-21, 22)/20).astype("f4")
    centres = ((np.arange(-21, 21)+.5)/20).astype("f4")
    np.savez(req / "axes.npz", **{d: centres.astype(float) for d in "xyz"},
             **{d+"_edges": edges.astype(float) for d in "xyz"})
    (req / "atmosphere.csv").write_text("0 1 1 0 0 0\n1e23 1 1 0 0 0\n")
    (req / "pluto.ini").write_text(
        "[Parameters]\nJET_PWR 1e45\nJET_SPD 0.1\nJET_INJECTION_HEIGHT .75\nJET_INITIAL_RADIUS .1\n"
        "JET_X1O 0\nJET_X2O 0\nJET_X3O 0\nJET_ROTATION_ANGLE 0\nJET_START_TIME 0\nJET_END_TIME 50\n"
        "JET_ACTIVE_TIME 50\nJET_EPISODES 1\n")
    history = []
    for i in range(2):
        path = req / f"data.{i:04d}.flt.h5"
        group = f"Timestep_{i}"
        with h5py.File(path, "w") as h5:
            for label, coords in (("cell_coords", centres), ("node_coords", edges)):
                vectors = np.meshgrid(coords, coords, coords, indexing="ij")
                for d, field in zip("XYZ", vectors[::-1], strict=True):
                    h5[f"{label}/{d}"] = field
            z, y, x = np.meshgrid(centres, centres, centres, indexing="ij")
            r = np.sqrt(x*x + y*y + z*z)
            cap = (x*x + y*y <= (z * np.tan(np.pi/12))**2) & (r <= .75)
            state = {"rho": np.ones_like(r), "prs": np.full_like(r, .002), "tr1": cap.astype("f4")}
            state.update({f"vx{d}": (.1 * coord/r * cap).astype("f4") for d, coord in enumerate((x, y, z), 1)})
            for key, field in state.items():
                h5[f"{group}/vars/{key}"] = field
            h5[group].attrs["Time"] = i*CODE_TIME_PER_MYR
        stat = path.stat()
        native = dict(resolved_path=str(path.resolve()), size_bytes=stat.st_size, inode=stat.st_ino,
                      ctime_ns=stat.st_ctime_ns, mtime_ns=stat.st_mtime_ns, sha256=sha(path))
        history.append(dict(index=i, shape=list(r.shape), time_code=i*CODE_TIME_PER_MYR, age_myr=i,
                            fixed_receipt_sha256=str(i), native=native, timestep=group))
    request = dict(case="test", history=history, static_sha256={k: sha(req / k) for k in
                   ("axes.npz", "atmosphere.csv", "pluto.ini")})
    (req / "request.json").write_text(json.dumps(request))
    capture(req, out, "patch", "all")
    capture(req, out, "patch", "all")
    capture(req, out, "outer", "all")
    outer = json.loads((out / "test/outer/snapshot_0000.json").read_text())
    assert outer["gravity"]["outside_p2"]["net_erg_s"] == 0
    assert outer["tracer"]["min_margin_above_threshold_kpc"] > 0
    label = 4e45 * SECONDS_PER_MYR / (.1*UNIT_VELOCITY_CMS)**2
    ref = {("test", 0, 1): {"labelled_mass_g": label, "delta_over_label": 0}}
    domain = {("test", 1, boundary, rule): 2e45 * SECONDS_PER_MYR for boundary in
              ("outer_active_cell", "linear_to_boundary_face") for rule in ("left", "right", "trapezoid")}
    rates, intervals = reduce_case(req, out, ref, domain, require_outer=True)
    assert len(rates) == 24 and len(intervals) == 12
    assert all(row["flagged_tagged_storage_change"] == 0 for row in intervals)
    assert all(row["native_volume_observed_tracer"] == row["outer_face_net_tracer"] == 0 for row in intervals)
    assert all(row["outside_flagged_sphere_outer_active_cell"] == pytest.approx(1-row["net_gas_plus_potential"])
               for row in intervals)
    assert all(row["net_tracer"] == pytest.approx(row["cap_tracer"] + row["stationary_tracer"])
               for row in intervals)
    (out / "test/patch/patch_0001.npz").write_bytes(b"broken")
    with pytest.raises(ValueError, match="identity"):
        capture(req, out, "patch", "1")
    with pytest.raises(ValueError, match="receipt"):
        reduce_case(req, out, ref)
