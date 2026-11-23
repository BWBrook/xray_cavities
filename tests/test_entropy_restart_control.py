import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import check_entropy_restart_control as gate


class Potential:
    def potential_at_radius(self, radius):
        return np.zeros_like(radius)


def test_opposite_pressure_errors_cannot_cancel_in_the_control(tmp_path):
    with h5py.File(tmp_path / "ref.h5", "w") as f:
        nodes = np.arange(8) - 3.5
        for group, values in (("node_coords", nodes), ("cell_coords", nodes[:-1]+0.5)):
            z, y, x = np.meshgrid(values, values, values, indexing="ij")
            for name, coord in zip("XYZ", (x, y, z)):
                f.create_dataset(f"{group}/{name}", data=coord)
        for name in gate.REQUIRED_DATASETS:
            f.create_dataset(f"Timestep_11/vars/{name}", data=np.ones((7, 7, 7), dtype=np.float32))
    shutil.copyfile(tmp_path / "ref.h5", tmp_path / "on.h5")
    with h5py.File(tmp_path / "ref.h5") as ref, h5py.File(tmp_path / "on.h5", "r+") as on:
        arguments = (ref, on, None, None, Potential(), gate.UNIT_ENERGY_ERG)
        result = gate.compare_fields(*arguments)
        assert all(e == 0 for e in result["relative_L1_in_affected_gas"].values())
        on["Timestep_11/vars/prs"][3, 3, 3:5] = [0.9, 1.1]
        result = gate.compare_fields(*arguments)
        assert result["unequal_cells_full_grid"]["prs"] == 2
        assert result["component_L1_per_labelled_interval"]["thermal"] == pytest.approx(0.3)
        assert result["component_L1_per_labelled_interval"]["thermal"] > gate.MAX_COMPONENT_L1_PER_INTERVAL
        on["Timestep_11/vars/prs"][2, 2, 2] = np.nan
        with pytest.raises(ValueError, match="nonfinite"):
            gate.compare_fields(*arguments)


@pytest.mark.parametrize("case,power,passes", [("C-LO", 1e43, False), ("C-HI", 1e45, True)])
def test_gate_divides_the_same_thermal_error_by_its_own_label(tmp_path, monkeypatch, case, power, passes):
    production = tmp_path / "original"
    arm = tmp_path / case / "ON"
    time = gate.TIME_11[case]
    _, step = gate.KNOWN_11[case]
    nodes = np.arange(8)-3.5
    axes = "7\n" + "".join(f"{i+1} {lo} {hi}\n" for i,(lo,hi) in enumerate(zip(nodes,nodes[1:])))
    for path, index in ((production, 11), (arm, 20)):
        out = path / "outputs"
        out.mkdir(parents=True)
        (out / "flt.h5.out").write_text(f"{index} {time:.6e} 0.31 {step} single_file little\n")
        (out / "grid.out").write_text(axes*3)
        with h5py.File(out / f"data.{index:04d}.flt.h5", "w") as h5:
            for group, values in (("node_coords", nodes), ("cell_coords", nodes[:-1]+.5)):
                z, y, x = np.meshgrid(values, values, values, indexing="ij")
                for name, coord in zip("XYZ", (x,y,z)):
                    h5.create_dataset(f"{group}/{name}", data=coord)
            g = h5.create_group(f"Timestep_{index}")
            g.attrs["Time"] = time
            for f in gate.REQUIRED_DATASETS:
                g.create_dataset(f"vars/{f}", data=np.ones((7,7,7), dtype=np.float32))
            if path == arm:
                g["vars/prs"][0,0,0] += 2**-21
    ref = production / "outputs/data.0011.flt.h5"
    monkeypatch.setitem(gate.KNOWN_11, case, (gate.sha256_file(ref), step))
    monkeypatch.setattr(gate, "parse_particle_header", lambda p: SimpleNamespace(nparticles=17))
    monkeypatch.setattr(gate, "load_environment", lambda p: Potential())
    particles = arm / "outputs/particles.1000.dbl"
    particles.write_bytes(b"manufactured particle identity")
    (arm.parent / "seed-validation.json").write_text(json.dumps({
        "input_sha256": {"particle_restart": gate.sha256_file(particles)}, "particle_restart": {"nparticles": 17}}))
    logs = arm / "outputs/logs"
    logs.mkdir()
    (logs / "pluto.0.log").write_text("Restarting from Particle File particles.1000.dbl\nbuilding linked list of 17 particles\n")
    (arm.parent / "restart.json").write_text(json.dumps({"case": case, "atmosphere": "unused",
        "restart_time_code": time-gate.CODE_TIME_PER_MYR, "label_power_erg_s": 2*power}))
    ini = ("[Parameters]\nJET_SPD 0.1\nJET_INJECTION_HEIGHT 0.75\nJET_INITIAL_RADIUS 0.1\nJET_X1O 0\n"
           "JET_X2O 0\nJET_X3O 0\nJET_ROTATION_ANGLE 0\nJET_START_TIME 0\nJET_END_TIME 50\n"
           "JET_ACTIVE_TIME 50\nJET_EPISODES 1\n")
    (arm / "pluto.ini").write_text(ini + f"JET_PWR {power}\n")
    result = gate.check(case, production, arm)
    assert result["passed"] is passes
    assert result["unequal_cells_full_grid"]["prs"] == 1
    assert result["labelled_control_interval_erg"] == pytest.approx(2*power*gate.SECONDS_PER_MYR)
    (arm / "pluto.ini").write_text(ini + f"JET_PWR {10*power}\n")
    with pytest.raises(ValueError, match="bipolar jet power"):
        gate.check(case, production, arm)
