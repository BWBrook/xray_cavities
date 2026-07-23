from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/validate_xray_cavity_recovery_refinement.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "validate_xray_cavity_recovery_refinement", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_common_grid_is_third_symmetric_intersection_grid() -> None:
    module = load_module()
    first = np.array([-4.0, -1.0, 0.5, 4.0])
    second = np.array([-3.5, -2.0, 0.0, 2.0, 3.5])

    common = module.common_symmetric_axis(first, second, cell_count=6)

    assert common.size == 6
    np.testing.assert_allclose(common, -common[::-1])
    assert not np.array_equal(common, first)
    assert not np.array_equal(common, second)


def test_regridded_identical_physical_map_has_exact_recovery_surface() -> None:
    module = load_module()
    source_axis = np.array([-3.0, -1.0, 0.5, 3.0])
    target_axis = module.common_symmetric_axis(source_axis, source_axis, cell_count=8)
    vertical = np.array([-1.0, 0.0, 1.0])
    corrected = np.vstack(
        (source_axis + 5.0, source_axis + 6.0, source_axis + 7.0)
    )
    product = module.goal044.MapProduct(
        corrected, corrected, np.ones_like(corrected), source_axis, vertical
    )

    first = module.regrid_product(product, target_axis)
    second = module.regrid_product(product, target_axis)

    assert module.normalized_l1(
        first.corrected, second.corrected, target_axis, vertical
    ) == pytest.approx(0.0)
    mask = first.corrected > 0.0
    assert module.area_weighted_mask_iou(mask, mask, target_axis, vertical) == 1.0


def test_unresolved_energy_is_not_estimable_not_zero() -> None:
    module = load_module()

    rows = module.energy_rows(
        "synthetic", "direct0", "negative_z", None, False, 1.0e-11
    )

    assert {row["estimation_status"] for row in rows} == {"not_estimable"}
    assert {row["energy_erg"] for row in rows} == {""}
    assert not module.energy_gate_result(rows)[0]


def test_resolved_energy_uses_exact_convention_multipliers() -> None:
    module = load_module()
    horizontal = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    vertical = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    mask = np.zeros((5, 5), dtype=bool)
    mask[1:4, 1:4] = True
    summary = module.summarize_mask(mask, horizontal, vertical)
    assert summary is not None

    rows = module.energy_rows(
        "synthetic", "direct0", "negative_z", summary, True, 1.0e-11
    )

    assert module.energy_gate_result(rows)[0]
    values = {row["convention"]: float(row["energy_erg"]) for row in rows}
    assert values["2.5pV"] == pytest.approx(2.5 * values["pV"])
    assert values["4pV"] == pytest.approx(4.0 * values["pV"])


def test_contract_keeps_detection_geometry_and_energy_separate() -> None:
    module = load_module()
    criteria = {row["gate"]: row for row in module.acceptance_criteria()}

    assert set(criteria) == {
        "background_stability",
        "synthetic_recovery",
        "negative_controls",
        "common_grid_recovery_equivalence",
        "geometry_resolution",
        "energy_convention",
        "input_provenance",
    }
    assert "area-weighted" in criteria["synthetic_recovery"]["tolerance"]
    assert "third symmetric grid" in criteria["common_grid_recovery_equivalence"][
        "comparison"
    ]


def test_contract_records_frozen_background_and_independent_controls(
    tmp_path: Path,
) -> None:
    module = load_module()
    output_dir = tmp_path / "contract"
    output_dir.mkdir()

    old_argv = sys.argv
    try:
        sys.argv = [
            str(SCRIPT),
            "write-contract",
            "--output-dir",
            str(output_dir),
        ]
        module.main()
    finally:
        sys.argv = old_argv

    metadata = __import__("json").loads(
        (output_dir / "goal045_contract_metadata.json").read_text()
    )
    assert metadata["background_degree"] == 6
    assert "Chebyshev" in metadata["background_fit"]
    assert "independent radial background" in metadata[
        "negative_control_background"
    ]
