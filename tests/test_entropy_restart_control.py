import shutil
import sys
from pathlib import Path

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
