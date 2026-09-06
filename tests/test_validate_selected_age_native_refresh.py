"""Synthetic coverage expanded from one genuinely emitted tiny native product."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def load(path: Path, name: str):
    science = str(Path("scripts/science").resolve())
    if science not in sys.path:
        sys.path.insert(0, science)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def products(tmp_path):
    emitter_test = load(Path("tests/test_selected_age_native_shock.py"), "emitter_fixture_test")
    tiny = tmp_path / "tiny"
    tiny.mkdir()
    emitter_test.test_selected_age_native_shock_builds_bilateral_seeded_energy_product(tiny, True)
    module = load(Path("scripts/science/validate_selected_age_native_refresh.py"), "validate_native_fixture")
    analysis, census = tmp_path / "analysis", tmp_path / "census"
    emitter = emitter_test.load_module()
    native_template = emitter.read_rows(tiny / "output/native_energy_selected_age.csv")
    precision_template = emitter.read_rows(tiny / "output/tracer_threshold_precision.csv")[0]
    source_template = emitter.read_rows(tiny / "output/source_manifest.csv")[0]
    for case in module.CASES:
        (analysis / case).mkdir(parents=True)
        (census / case).mkdir(parents=True)
        native, precision, sources = [], [], []
        for _, age in sorted(key for key in module.EXPECTED if key[0] == case):
            identity = {"case": case, "snapshot_index": age, "actual_time_myr": float(age),
                        "actual_time_code": float(source_template["actual_time_code"]) * age / 10}
            source = {**source_template, **identity, "input_h5": f"/synthetic/{case}/data.{age:04d}.flt.h5",
                      "timestep": f"Timestep_{age}", "baseline_h5": f"/synthetic/{case}/data.0000.flt.h5"}
            sources.append(source)
            precision.append({**precision_template, **{field: source[field] for field in
                              ("case", "snapshot_index", "actual_time_myr", "input_h5", "timestep")}})
            for row in native_template:
                updated = {**row, **identity}
                injected = float(row["injected_energy_erg"]) * age / 10
                updated["injected_energy_erg"] = injected
                updated["unattributed_residual_erg"] = injected - float(row["retained_energy_erg"])
                updated["closure_fraction_of_injected"] = updated["unattributed_residual_erg"] / injected
                native.append(updated)
        for name, rows in (("source_manifest.csv", sources), ("native_energy_selected_age.csv", native),
                           ("tracer_threshold_precision.csv", precision)):
            emitter.write_rows(analysis / case / name, rows)
        baseline = {**sources[0], "snapshot_index": 0, "actual_time_myr": 0, "actual_time_code": 0,
                    "input_h5": sources[0]["baseline_h5"], "timestep": "Timestep_0"}
        emitter.write_rows(census / case / "snapshot_manifest.csv", [baseline, *sources])
        emitter.write_rows(census / case / "energy_partition_timeseries.csv", native)
    return module, emitter, analysis, census


def test_validates_emitted_ledgers_and_writes_compatible_nonoverwriting_proof(products, tmp_path):
    module, _, analysis, census = products
    output = tmp_path / "proof.json"
    proof = module.validate_refresh(analysis, census, output)
    assert len(proof["covered_case_ages"]) == 19
    assert len(proof["compact_source_sha256"]) == 20
    assert proof["quantized_threshold_materiality"] == "pending scientific review"
    assert all(row["raw_dtype_quantized_equality_cell_count"] == 1 for row in proof["covered_case_ages"])
    assert all(row["quantized_equality_volume_fraction_of_primary"] == pytest.approx(0.5)
               for row in proof["covered_case_ages"])
    from build_binary_native_refresh import validate_equivalence
    validate_equivalence(output, census)
    assert json.loads(output.read_text())["strict_equivalent"] is True
    with pytest.raises(module.ProductError, match="overwrite"):
        module.validate_refresh(analysis, census, output)


@pytest.mark.parametrize("mutation", ["coverage", "mass", "component", "closure", "nan", "dtype", "source", "census"])
def test_rejects_invalid_compact_evidence(products, mutation):
    module, emitter, analysis, census = products
    root = census if mutation == "census" else analysis
    name = ("tracer_threshold_precision.csv" if mutation in ("nan", "dtype") else
            "source_manifest.csv" if mutation == "source" else
            "energy_partition_timeseries.csv" if mutation == "census" else "native_energy_selected_age.csv")
    path = root / "C-HI" / name
    rows = emitter.read_rows(path)
    if mutation == "coverage":
        rows.pop()
    elif mutation == "mass":
        rows[0]["gas_mass_g"] = float(rows[0]["gas_mass_g"]) * 2
    elif mutation == "component":
        rows[0]["lobe_thermal_erg"] = float(rows[0]["lobe_thermal_erg"]) + float(rows[0]["injected_energy_erg"])
    elif mutation == "closure":
        rows[0]["closure_fraction_of_injected"] = 100
    elif mutation == "nan":
        rows[0]["tracer_max"] = "NaN"
    elif mutation == "dtype":
        rows[0]["raw_tracer_dtype"] = "float64"
    elif mutation == "source":
        rows[0]["baseline_h5"] = "/wrong/baseline"
    else:
        rows[0]["lobe_volume_kpc3"] = float(rows[0]["lobe_volume_kpc3"]) * 2
    emitter.write_rows(path, rows)
    with pytest.raises(module.ProductError):
        module.validate_refresh(analysis, census)
