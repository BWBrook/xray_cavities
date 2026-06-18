from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path("scripts/science/build_final_level3_remote_extraction_closeout.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_final_level3_remote_extraction_closeout", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_remote_closeout_package_marks_thermal_kinetic_green_and_gravity_blocked(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_script_module()
    level1 = tmp_path / "level1.csv"
    level2 = tmp_path / "level2.csv"
    extractor_csv = tmp_path / "level3_extractor_output.csv"
    stdout = tmp_path / "remote.out"
    stderr = tmp_path / "remote.err"
    archive = tmp_path / "remote.tar.gz"
    output_dir = tmp_path / "package"

    write_csv(
        level1,
        [{"metric": "injected_energy_bipolar_elapsed", "value": 100.0, "unit": "erg"}],
        ["metric", "value", "unit"],
    )
    write_csv(
        level2,
        [
            {
                "threshold": "5e-03",
                "side": "bipolar_total",
                "time_myr": 50.0,
                "cell_count": 20,
                "volume_kpc3": 300.0,
                "total_energy_erg": 40.0,
            }
        ],
        ["threshold", "side", "time_myr", "cell_count", "volume_kpc3", "total_energy_erg"],
    )
    extractor_fields = [
        "side",
        "tracer_threshold",
        "ambient_cell_count",
        "ambient_volume_kpc3",
        "thermal_delta_code",
        "kinetic_delta_code",
        "thermal_delta_erg",
        "kinetic_delta_erg",
        "thermal_plus_kinetic_delta_erg",
    ]
    write_csv(
        extractor_csv,
        [
            {
                "side": "negative_z",
                "tracer_threshold": "5e-03",
                "ambient_cell_count": 10,
                "ambient_volume_kpc3": 100.0,
                "thermal_delta_code": 0.0,
                "kinetic_delta_code": 0.0,
                "thermal_delta_erg": 20.0,
                "kinetic_delta_erg": 2.0,
                "thermal_plus_kinetic_delta_erg": 22.0,
            },
            {
                "side": "positive_z",
                "tracer_threshold": "5e-03",
                "ambient_cell_count": 10,
                "ambient_volume_kpc3": 100.0,
                "thermal_delta_code": 0.0,
                "kinetic_delta_code": 0.0,
                "thermal_delta_erg": 30.0,
                "kinetic_delta_erg": 3.0,
                "thermal_plus_kinetic_delta_erg": 33.0,
            },
            {
                "side": "bipolar_total",
                "tracer_threshold": "5e-03",
                "ambient_cell_count": 20,
                "ambient_volume_kpc3": 200.0,
                "thermal_delta_code": 0.0,
                "kinetic_delta_code": 0.0,
                "thermal_delta_erg": 50.0,
                "kinetic_delta_erg": 5.0,
                "thermal_plus_kinetic_delta_erg": 55.0,
            },
        ],
        extractor_fields,
    )
    stdout.write_text("baseline_hdf5_preflight=passed\nlevel3_extractor_validation=passed\n")
    stderr.write_text("")
    archive.write_text("fake archive\n")
    monkeypatch.setattr(module, "ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())

    metadata = module.build_closeout_package(
        output_dir=output_dir,
        extractor_csv=extractor_csv,
        stdout_path=stdout,
        stderr_path=stderr,
        archive_path=archive,
        level1_path=level1,
        level2_path=level2,
        remote_preflight=module.BASE.DEFAULT_REMOTE_PREFLIGHT,
    )

    assert metadata["thermal_kinetic_status"] == "green_level3_thermal_kinetic_closeout"
    assert metadata["gravitational_status"] == "blocked_missing_potential"
    assert metadata["coordinate_compatibility_contract"] == "executed_by_remote_extractor_success"

    energy_rows = read_csv(output_dir / "level3_ambient_energy.csv")
    total = next(
        row
        for row in energy_rows
        if row["side"] == "bipolar_total" and row["component"] == "ambient_thermal_plus_kinetic_delta"
    )
    assert total["status"] == "computed"
    assert float(total["value_erg"]) == 55.0

    decisions = {row["decision"]: row for row in read_csv(output_dir / "level3_method_decisions.csv")}
    assert decisions["coordinate_compatibility"]["status"] == "executed_by_remote_extractor_success"
    written = json.loads((output_dir / "level3_metadata.json").read_text())
    assert written["remote_job"]["job_id"] == module.JOB_ID
