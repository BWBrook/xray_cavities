from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/validate_common_age_endpoint_reuse.py")
ACCEPTED = Path("docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12")


def load_module():
    spec = importlib.util.spec_from_file_location("validate_common_age_endpoint_reuse", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_goal040_surface_builds_strict_endpoint_contract(tmp_path: Path) -> None:
    module = load_module()
    output_csv = tmp_path / "endpoint_reuse_contract.csv"
    output_json = tmp_path / "endpoint_reuse_contract.json"

    metadata = module.build_endpoint_contract(
        endpoint_root=ACCEPTED,
        output_csv=output_csv,
        output_json=output_json,
    )

    rows = list(csv.DictReader(output_csv.open(newline="")))
    assert len(rows) == 9
    assert {(row["case"], row["view"]) for row in rows} == {
        (case, view)
        for case in ("C-HI", "C-LO", "G-LO")
        for view in ("0deg", "45deg", "90deg")
    }
    assert all(float(row["endpoint_time_myr"]) == pytest.approx(50.0) for row in rows)
    assert all(row["candidate_selection_basis"] == "projected_physical_area_fraction" for row in rows)
    assert all(row["endpoint_reuse_status"] == "accepted_goal040" for row in rows)
    assert {row["projection_accumulator"] for row in rows if row["view"] == "0deg"} == {"direct_y_axis_sum"}
    assert {row["projection_accumulator"] for row in rows if row["view"] != "0deg"} == {"edge_overlap_uniform_cell_projection"}
    assert metadata["status"] == "endpoint_reuse_contract_green"
    assert json.loads(output_json.read_text())["row_count"] == 9


def test_endpoint_contract_rejects_hash_or_time_drift(tmp_path: Path) -> None:
    module = load_module()
    copied = tmp_path / "goal040"
    shutil.copytree(ACCEPTED, copied)
    recovery = copied / "xray_recovery_summary.csv"
    text = recovery.read_text().replace("C-HI,0deg,50.0", "C-HI,0deg,49.0", 1)
    recovery.write_text(text)

    with pytest.raises(ValueError, match="hash mismatch"):
        module.build_endpoint_contract(
            endpoint_root=copied,
            output_csv=tmp_path / "contract.csv",
            output_json=tmp_path / "contract.json",
        )

