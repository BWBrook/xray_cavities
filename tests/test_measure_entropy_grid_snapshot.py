import hashlib
import json
from pathlib import Path
import subprocess
import sys

import h5py
import numpy as np
import pytest


SCIENCE = Path(__file__).resolve().parents[1] / "scripts/science"
sys.path.insert(0, str(SCIENCE))
import measure_entropy_grid_snapshot as reader


def test_native_entry_matches_reference_and_withholds_invalid_face(tmp_path):
    arm = tmp_path / "G-HI/ON"
    outputs = arm / "outputs"
    outputs.mkdir(parents=True)
    time = 11.0 * reader.CODE_TIME_PER_MYR
    (arm.parent / "restart.json").write_text(json.dumps({
        "case": "G-HI", "atmosphere": "atmosphere.csv", "restart_time_code": time * 10 / 11,
    }))
    (arm / "series.json").write_text(json.dumps({
        "case": "G-HI", "arm": "ON", "new_indices": [20], "ages_myr": [time / reader.CODE_TIME_PER_MYR],
    }))
    np.savetxt(arm / "atmosphere.csv", [[0, 1, 1, 0, 0, 0], [1e24, 1, 1, 0, -1e-7, -1e-7]])
    (outputs / "flt.h5.out").write_text(f"20 {time} 0.42 10990\n")
    edges = np.array([-3., -2., -0.8, 0., 0.8, 2., 3., 5.0])
    centres = (edges[1:] + edges[:-1]) / 2
    (outputs / "grid.out").write_text(3 * ("7\n" + "".join(
        f"{i + 1} {left} {right}\n" for i, (left, right) in enumerate(zip(edges[:-1], edges[1:]))
    )))
    z, y, x = np.indices((7, 7, 7))
    snapshot = outputs / "data.0020.flt.h5"
    with h5py.File(snapshot, "w") as h5:
        for axis in "XYZ":
            h5[f"node_coords/{axis}"] = edges
            h5[f"cell_coords/{axis}"] = centres
        group = h5.create_group("Timestep_20")
        group.attrs["Time"] = time
        for n, field in enumerate((*reader.flux.PRIMITIVE_FIELDS, "tr1")):
            group[f"vars/{field}"] = (n + 1 + .1*x - .05*y + .02*z).astype("<f4")

    result = tmp_path / "receipts/20.json"
    subprocess.run([sys.executable, str(SCIENCE / "measure_entropy_grid_snapshot.py"),
                    str(arm), "20", str(result)], check=True)
    row = json.loads(result.read_text())
    assert (row["index"], row["case"], row["step"]) == (20, "G-HI", 10990)
    with h5py.File(snapshot, "r+") as h5:
        vars_ = h5["Timestep_20/vars"]
        grid = reader.flux.read_grid(h5, x.shape, grid_file=outputs / "grid.out")
        atmosphere = reader.load_environment(arm / "atmosphere.csv")
        exact, _ = reader.flux.measure_storage(vars_, grid, atmosphere, {}, ())
        for field, value in row["storage"].items():
            assert value == pytest.approx(exact[field], rel=2e-15)
        for method in reader.flux.OUTER_RECONSTRUCTIONS:
            expected = reader.flux.measure_domain_surface(vars_, grid, atmosphere, method)
            assert row["boundary"][method]["valid"]
            assert row["boundary"][method]["total_energy_flux_outward_erg_s"] == expected[-1]["total_energy_flux_outward_erg_s"]
            assert set(row["boundary"][method]["faces"]) == set(reader.flux.FACE_NAMES)
        for field, digest in row["input"]["field_sha256_c_order_float32_le"].items():
            assert digest == hashlib.sha256(vars_[field][:]).hexdigest()
        vars_["prs"][:, :, 0] = .001
    failed_linear = reader.reduce_snapshot(arm, 20)["boundary"]
    assert failed_linear["outer_active_cell"]["valid"]
    assert not failed_linear["linear_to_boundary_face"]["valid"]
    assert failed_linear["linear_to_boundary_face"]["total_energy_flux_outward_erg_s"] is None
