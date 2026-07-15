from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_goal041_scratch_gate.py")


def load_module():
    spec = importlib.util.spec_from_file_location("build_goal041_scratch_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_forecast(path: Path, per_case: int = 100) -> None:
    rows = [
        {
            "case": case,
            "xray_products_bytes": per_case,
            "transient_working_bytes": per_case,
            "archive_duplication_bytes": per_case,
            "particle_outputs_bytes": 0,
            "forecast_basis": "accepted_endpoint_product_sizes_scaled_to_four_new_ages",
        }
        for case in ("C-HI", "C-LO", "G-LO")
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_scratch_gate_is_green_only_with_write_probe_and_headroom(tmp_path: Path) -> None:
    module = load_module()
    forecast = tmp_path / "forecast.csv"
    write_forecast(forecast)
    output_csv = tmp_path / "gate.csv"
    output_json = tmp_path / "gate.json"

    metadata = module.build_gate(
        forecast_csv=forecast,
        available_bytes=10_000,
        write_probe_status="passed",
        analysis_parent="/scratch/example",
        output_csv=output_csv,
        output_json=output_json,
    )

    row = next(csv.DictReader(output_csv.open(newline="")))
    assert row["gate_status"] == "GREEN"
    assert float(row["headroom_ratio"]) >= 1.5
    assert metadata["particle_outputs_bytes"] == 0
    assert json.loads(output_json.read_text())["gate_status"] == "GREEN"


@pytest.mark.parametrize(
    ("available", "probe", "message"),
    [(100, "passed", "headroom"), (10_000, "failed", "write probe")],
)
def test_scratch_gate_fails_closed(tmp_path: Path, available: int, probe: str, message: str) -> None:
    module = load_module()
    forecast = tmp_path / "forecast.csv"
    write_forecast(forecast)
    with pytest.raises(ValueError, match=message):
        module.build_gate(
            forecast_csv=forecast,
            available_bytes=available,
            write_probe_status=probe,
            analysis_parent="/scratch/example",
            output_csv=tmp_path / "gate.csv",
            output_json=tmp_path / "gate.json",
        )


def test_scratch_gate_rejects_particle_outputs_or_missing_cases(tmp_path: Path) -> None:
    module = load_module()
    forecast = tmp_path / "forecast.csv"
    write_forecast(forecast)
    rows = list(csv.DictReader(forecast.open(newline="")))[:2]
    rows[0]["particle_outputs_bytes"] = "1"
    with forecast.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="case coverage|particle"):
        module.build_gate(
            forecast_csv=forecast,
            available_bytes=10_000,
            write_probe_status="passed",
            analysis_parent="/scratch/example",
            output_csv=tmp_path / "gate.csv",
            output_json=tmp_path / "gate.json",
        )
