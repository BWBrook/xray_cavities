from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys

import numpy as np


SCRIPT = Path("scripts/science/cluster_background_energy_diagnostic.py")


def _module():
    science_dir = str(SCRIPT.parent.resolve())
    if science_dir not in sys.path:
        sys.path.insert(0, science_dir)
    spec = importlib.util.spec_from_file_location("cluster_background_energy_diagnostic", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_radial_shells_are_exhaustive_and_nonoverlapping() -> None:
    module = _module()
    radius = np.asarray([[0.0, 49.9, 50.0], [99.9, 100.0, 250.0]])
    shells = module.radial_shell_masks(radius)

    assert [label for label, _mask in shells] == [
        "r_000_050_kpc", "r_050_100_kpc", "r_100_150_kpc",
        "r_150_200_kpc", "r_200_inf_kpc",
    ]
    coverage = sum(mask.astype(int) for _label, mask in shells)
    assert np.all(coverage == 1)


def test_shell_labels_and_contract_are_locked() -> None:
    module = _module()

    assert module.SHELL_EDGES_KPC[:-1] == (0.0, 50.0, 100.0, 150.0, 200.0)
    assert math.isinf(module.SHELL_EDGES_KPC[-1])
    assert module.OUTER_CONTROL_MIN_KPC == 100.0
    assert module.shell_label(200.0, math.inf) == "r_200_inf_kpc"


def test_cli_requires_explicit_case_inputs_and_selected_snapshots() -> None:
    parser = _module().build_parser()
    args = parser.parse_args([
        "--case", "C-LO",
        "--outputs-dir", "/scratch/outputs",
        "--environment-table", "/scratch/environment.csv",
        "--reference-energy", "/scratch/energy.csv",
        "--output-root", "/scratch/result",
        "--jet-power-one-sided-erg-s", "1e43",
        "--snapshot-index", "0",
        "--snapshot-index", "20",
    ])

    assert args.case == "C-LO"
    assert args.snapshot_index == [0, 20]
    assert args.jet_power_one_sided_erg_s == 1.0e43


def test_baseline_reconstruction_is_not_expressed_as_relative_error() -> None:
    text = SCRIPT.read_text()

    assert 'if snapshot.output_index == 0:' in text
    assert 'relative_error = ""' in text
    assert '"reference_absolute_difference_erg": reference_difference' in text
    assert 'if relative_error != "" and relative_error > 1.0e-8:' in text
