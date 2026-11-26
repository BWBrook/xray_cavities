import json
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/science"))
import project_four_case_midplane_slabs as worker


def receipt(path):
    return {"path": str(path), "sha256": worker.budget._sha256(path)}


def save_json(path, data):
    path.write_text(json.dumps(data))
    return receipt(path)


def historical_producers(tmp_path, monkeypatch):
    """Use the actual old map producer with small HDF5 stocks and a synthetic radiation law."""
    producer = worker.previous
    case = "C-LO"
    edges = np.array([-60., -35., -8., 0., 8., 35., 60.])
    shape = (6,) * 3
    hdf = {}
    for age in (0, 20):
        file = tmp_path / f"data.{age:04d}.flt.h5"
        z, y, x = np.indices(shape)
        with h5py.File(file, "w") as f:
            for axis in "XYZ":
                f[f"cell_coords/{axis}"] = (edges[:-1] + edges[1:]) / 2
                f[f"node_coords/{axis}"] = edges
            step = f.create_group("Timestep_0")
            step.attrs["Time"] = age * worker.budget.CODE_TIME_PER_MYR
            variables = step.create_group("vars")
            variables["rho"] = 2. + .05 * z + .01 * y + .11 * (age > 0) * x
            variables["prs"] = np.ones(shape)
            variables["tr1"] = np.asarray(((x >= 1) & (x < 4) & (y == 3) & (age > 0)), dtype=float)
            for name in ("vx1", "vx2", "vx3"):
                variables[name] = np.zeros(shape)
        hdf[age] = {**worker.budget._stat_identity(file), **receipt(file)}
    environment = tmp_path / "atmosphere"
    environment.write_text("test")
    environment_id = {**worker.budget._stat_identity(environment), **receipt(environment)}
    native_contract = save_json(tmp_path / "native_case.json", {
        "schema_version": 1, "case": case, "shape_nz_ny_nx": list(shape),
        "snapshots": [{"index": i, "path": str(tmp_path / f"data.{i:04d}.flt.h5")} for i in range(51)],
        "files": {"environment": environment_id}})
    runtime = {}
    for key in producer.RUNTIME_HASHES:
        file = tmp_path / key
        file.write_text(key)
        runtime[key] = receipt(file)
    monkeypatch.setattr(producer, "RUNTIME_HASHES", worker.digests(runtime))
    monkeypatch.setattr(producer.NATIVE.renderer, "load_module", lambda path: None)
    monkeypatch.setattr(producer.NATIVE, "load_tables", lambda *paths: None)

    def synthetic_law(*, rho_code, pressure_code, **kwargs):
        fields = {k: rho_code ** 2 * pressure_code for c in worker.emission.CONVENTIONS for k in (c, c + "_before")}
        return fields, np.ones_like(rho_code), {k: np.zeros_like(rho_code, dtype=bool) for k in ("raw_nonfinite", "any")}

    monkeypatch.setattr(producer.NATIVE, "cell_emissivity", synthetic_law)
    config = ROOT / "configs/background_refit_blind_2026-11-11.json"
    pins = {}
    for age in (0, 20):
        source = save_json(tmp_path / f"native_{age}.json", {
            "schema_version": 1, "status": "bound_spherical_budget_inputs", "case": case, "snapshot_index": age,
            "inputs": {"current_h5": hdf[age], "initial_h5": hdf[0], "environment": environment_id},
            "current": {"time_code": age * worker.budget.CODE_TIME_PER_MYR, "timestep": "Timestep_0"},
            "initial": {"time_code": 0., "timestep": "Timestep_0"},
            "native_preflight": {"contract": native_contract, "scientific_qualification": {"holds": []},
                                 "semantic_checks": dict.fromkeys(producer.SEMANTICS, "passed")}})
        contract = save_json(tmp_path / f"contract_{age}.json", {
            "schema_version": 1, "case": case, "snapshot_index": age, "kind": "science" if age else "initial_null",
            "frequency_hz": producer.FREQUENCY_HZ, "redshift": producer.REDSHIFT, "sky_axis_policy": producer.AXIS_POLICY,
            "views_side_on_azimuth_deg": list(worker.emission.VIEWS), "inputs": runtime,
            "native_input_receipt": source, "protocol_config": receipt(config)})
        directory = tmp_path / f"{case}_{age:04d}"
        producer.run(Path(contract["path"]), contract["sha256"], directory)
        pins[age] = receipt(directory / "completion.json")["sha256"]
    return (Path(contract["path"]), contract["sha256"], directory, pins[20], pins[0])


def test_native_worker_uses_separate_initial_producer_and_same_native_tracer(tmp_path, monkeypatch):
    args = historical_producers(tmp_path, monkeypatch)
    truth = tmp_path / "released"
    truth.mkdir()
    name = "C-LO_0020_0deg.truth.npz"
    (args[2] / name).rename(truth / name)
    output = tmp_path / "result"
    result = worker.run(*args, truth, output)
    assert json.loads((output / "completion.json").read_text()) == result
    assert result["case"] == "C-LO" and result["snapshot_index"] == 20
    assert result["previous_producer_sha256"] == args[3] and result["initial_previous_producer_sha256"] == args[4]
    assert result["references"]["initial_0"]["filename"] == "C-LO_0000_0deg.npz"
    assert result["references"]["truth_90"]["filename"] == "C-LO_0020_90deg.truth.npz"
    assert len(result["closure_against_previous"]) == 3
    assert all(r["bitwise_equal"] for r in result["closure_against_previous"].values())
    assert len(result["native_full_integral_checks"]) == 5
    assert result["native_tracer_volume_kpc3"]["full"]["both"] > 0
    assert result["files"]["projections.npz"]["sha256"] == receipt(output / "projections.npz")["sha256"]
    with np.load(output / "projections.npz", allow_pickle=False) as maps:
        assert set(maps.files) == set(worker.AXES) | {
            f"{field}_{depth}" for field in worker.pilot.FULL_REFERENCE for depth in worker.pilot.DEPTHS}
        assert not np.array_equal(maps["current_slab10"], maps["initial_slab10"])
    with pytest.raises(FileExistsError):
        worker.run(*args, truth, output)
    failed = tmp_path / "mismatched"
    with pytest.raises(ValueError, match="identity mismatch"):
        worker.run(*args[:-1], args[3], truth, failed)
    assert not failed.exists()


def test_full_depth_comparison_rejects_single_wrong_pixel_in_faint_tail():
    bright = np.array([[1., 1e-12]])
    maps = {"current_full": bright.copy(), "initial_full": bright.copy(), "tracer_path_full": np.zeros_like(bright)}
    datasets = {"current_0": {worker.BRIGHTNESS: bright.copy()}, "initial_0": {worker.BRIGHTNESS: bright.copy()},
                "truth_0": {"path_C_kpc": np.zeros_like(bright)}}
    datasets["initial_0"][worker.BRIGHTNESS][0, 1] *= 2
    with pytest.raises(ValueError, match="initial_full.*pixels differ"):
        worker.compare_pixels(maps, datasets)


def test_ghi_source_rechecks_the_retained_parent_chain(tmp_path):
    chain = [{"output_index": i} for i in range(51)]
    native = {"case": "G-HI", "snapshot_index": 10, "inputs": {}}
    for epoch, index in (("initial", 0), ("current", 10)):
        file = tmp_path / f"data.{index:04d}.flt.h5"
        file.write_bytes(bytes([index]))
        native["inputs"][epoch + "_h5"] = {**worker.budget._stat_identity(file), **receipt(file)}
        native[epoch] = {"timestep": f"Timestep_{index}", "time_code": index * worker.budget.CODE_TIME_PER_MYR}
        chain[index].update({**native["inputs"][epoch + "_h5"], **native[epoch]})
    ref = save_json(tmp_path / "lineage.json", {
        "schema_version": 1, "status": "passed",
        "lineage": "accepted failed-run parent build/source plus validated 10 Myr home continuation",
        "snapshots": {"analysis_chain": chain}})
    native["native_preflight"] = {"inherited_lineage": {"receipt": ref}}
    old = {"provenance": {"inherited_lineage_receipt": ref}}
    assert worker.bind_ghi_lineage(native, old, []) == ref["sha256"]
    native["current"]["timestep"] = "Timestep_42"
    with pytest.raises(ValueError, match="current: G-HI snapshot differs"):
        worker.bind_ghi_lineage(native, old, [])
