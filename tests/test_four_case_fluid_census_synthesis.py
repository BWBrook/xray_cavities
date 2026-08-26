import csv
import importlib.util
import json
from pathlib import Path
import sys

INPUT = Path("docs/science/assets/four_case_fluid_snapshot_census_2026-08-25/review_products")
SCRIPT = Path("scripts/science/build_four_case_fluid_census_synthesis.py")


def _module():
    spec = importlib.util.spec_from_file_location("four_case_fluid_census_synthesis", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_builds_complete_primary_factorial_surface(tmp_path: Path) -> None:
    result = _module().build(INPUT, tmp_path)

    assert result["status"] == "complete_four_case_fluid_census_synthesis"
    assert result["snapshot_count"] == 204
    assert result["primary_shock_row_count"] == 408
    assert len(_rows(tmp_path / "endpoint_factorial_summary.csv")) == 4
    assert len(_rows(tmp_path / "endpoint_factorial_contrasts.csv")) == 32
    assert (tmp_path / "four_case_fluid_census.png").stat().st_size > 100_000


def test_exposes_material_c_lo_and_g_hi_limits(tmp_path: Path) -> None:
    _module().build(INPUT, tmp_path)
    endpoints = {row["case"]: row for row in _rows(tmp_path / "endpoint_factorial_summary.csv")}

    assert float(endpoints["C-LO"]["gas_total_fraction_of_injected"]) > 20.0
    assert endpoints["C-LO"]["absolute_residual_exceeds_injected"] == "True"
    assert float(endpoints["G-HI"]["minimum_domain_margin_kpc"]) < 2.0
    assert float(endpoints["G-LO"]["lobe_total_fraction_of_injected"]) < 0.2


def test_metadata_keeps_descriptive_scope_explicit(tmp_path: Path) -> None:
    _module().build(INPUT, tmp_path)
    metadata = json.loads((tmp_path / "four_case_fluid_census_synthesis_metadata.json").read_text())

    assert metadata["decision_label"].endswith("G_HI_BOUNDARY_GATES_EXPOSED")
    assert any("descriptive" in item for item in metadata["interpretation_limits"])
    assert any("not cocoon energy" in item for item in metadata["interpretation_limits"])
