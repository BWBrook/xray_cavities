import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/science/build_g_lo_three_case_endpoint_comparison.py"


def load_module():
    spec = importlib.util.spec_from_file_location("three_case_figure", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builds_nine_panel_comparison_with_explicit_scaling_boundary(tmp_path):
    module = load_module()
    module.build_comparison(tmp_path)

    figure = tmp_path / "g_lo_three_case_endpoint_comparison.png"
    metadata = json.loads(
        (tmp_path / "g_lo_three_case_endpoint_comparison_metadata.json").read_text()
    )
    assert figure.stat().st_size > 100_000
    assert metadata["status"] == "complete_product"
    assert metadata["case_order"] == ["C-HI", "C-LO", "G-LO"]
    assert metadata["views"] == ["0deg", "45deg", "90deg"]
    assert metadata["map_scaling"] == "independent_per_panel_log_percentile"
    assert metadata["quantitative_authority"] == "three_case_endpoint_comparison.csv"
    assert len(metadata["panels"]) == 9
    assert (tmp_path / "local_asset_manifest.sha256").stat().st_size > 0


def test_real_product_bundle_records_all_deliberate_large_files():
    module = load_module()
    output = ROOT / "docs/science/assets/g_lo_endpoint_first_products_and_three_case_comparison_2026-07-12"
    module.write_bundle_inventory(output)

    rows = (output / "large_file_inventory.csv").read_text().splitlines()
    assert len(rows) == 14
    assert all(int(row.split(",", 1)[0]) < 100 * 1024 * 1024 for row in rows[1:])
