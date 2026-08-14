from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path("scripts/science/build_four_case_preproduction_readiness.py")
PROTECTED = Path("docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/completed_run/review_inventory/protected_path_contract.csv")


def load_module():
    spec = importlib.util.spec_from_file_location("build_four_case_preproduction_readiness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_four_case_contract_and_storage_ceiling() -> None:
    module = load_module()
    cases = module.case_rows()
    assert {row["case"] for row in cases} == {"C-HI", "C-LO", "G-LO", "G-HI"}
    assert next(row for row in cases if row["case"] == "G-LO")["execution_order"] == 0
    total = module.storage_rows()[-1]
    assert 11 < total["uncompressed_total_TiB"] < 12


def test_build_uses_actual_protected_g_lo_snapshot_surface(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "contract"
    result = module.build(PROTECTED, output)
    assert result["g_lo_snapshot_count"] == 6
    assert all(result["gates"].values())
    rows = list(csv.DictReader((output / "g_lo_snapshot_manifest.csv").open()))
    assert [int(row["snapshot_index"]) for row in rows] == [0, 10, 20, 30, 40, 50]
    assert float(rows[-1]["actual_time_Myr"]) == 50.0
    metadata = json.loads((output / "four_case_preproduction_readiness_metadata.json").read_text())
    assert metadata["submission_hold"].startswith("C-HI/C-LO/G-HI")
