from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import h5py
import numpy as np
import pytest


SCRIPT = Path("scripts/science/reversible_hdf5_compression.py")


def load_module():
    spec = importlib.util.spec_from_file_location("reversible_hdf5_compression", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_fixture(path: Path) -> None:
    with h5py.File(path, "w") as handle:
        handle.attrs["title"] = "synthetic PLUTO"
        timestep = handle.create_group("Timestep_1")
        timestep.attrs["time"] = 1.25
        coords = handle.create_group("cell_coords")
        coords.create_dataset("X", data=np.linspace(-1, 1, 9))
        node_coords = handle.create_group("node_coords")
        node_coords.create_dataset("X", data=np.linspace(-1.125, 1.125, 10))
        variables = timestep.create_group("vars")
        rho = variables.create_dataset(
            "rho", data=np.arange(4 * 5 * 6, dtype=np.float32).reshape(4, 5, 6)
        )
        rho.attrs["units"] = "code_density"
        variables.create_dataset("index", data=np.arange(6, dtype=np.int32))
        variables.create_dataset("scalar", data=np.float64(3.5))


def test_reversible_copy_preserves_schema_metadata_and_values(tmp_path: Path) -> None:
    module = load_module()
    source = tmp_path / "source.h5"
    output = tmp_path / "compressed.h5"
    report = tmp_path / "report.json"
    make_fixture(source)
    result = module.compress_reversibly(source, output, report)
    assert result["gates"]["bitwise_values_preserved"] is True
    assert result["dataset_count"] == 5
    assert json.loads(report.read_text())["status"] == "complete_reversible_copy"
    with h5py.File(source, "r") as left, h5py.File(output, "r") as right:
        np.testing.assert_array_equal(left["Timestep_1/vars/rho"], right["Timestep_1/vars/rho"])
        assert right["cell_coords/X"].compression == "gzip"
        assert right["node_coords/X"].compression == "gzip"
        assert right["Timestep_1/vars/index"].compression == "gzip"
        assert "32013" in right["Timestep_1/vars/rho"]._filters


def test_reversible_copy_refuses_overwrite(tmp_path: Path) -> None:
    module = load_module()
    source = tmp_path / "source.h5"
    output = tmp_path / "compressed.h5"
    report = tmp_path / "report.json"
    make_fixture(source)
    output.write_text("occupied")
    with pytest.raises(module.CompressionError, match="refusing to overwrite"):
        module.compress_reversibly(source, output, report)


def test_chunk_shape_is_bounded() -> None:
    module = load_module()
    chunks = module.choose_chunk_shape((1014, 960, 960), np.dtype("float64"))
    assert chunks is not None
    assert np.prod(chunks) * 8 <= module.TARGET_CHUNK_BYTES
