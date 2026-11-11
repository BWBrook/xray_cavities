from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1]/"scripts/science/summarize_q031_source_accounting.py"
SPEC = importlib.util.spec_from_file_location("q031_source_accounting", SCRIPT)
assert SPEC and SPEC.loader
accounting = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(accounting)


def rows(outer_energy=0.0, outer_mass=0.0, sensitivity=False):
    result = []
    for surface, reconstructions in (
        ("domain_boundary", accounting.DOMAIN_RECONSTRUCTIONS),
        ("nozzle_control_p1", accounting.NOZZLE_RECONSTRUCTIONS),
        ("nozzle_control_p2", accounting.NOZZLE_RECONSTRUCTIONS),
    ):
        for method_index, method in enumerate(reconstructions):
            for quadrature_index, quadrature in enumerate(accounting.QUADRATURES):
                domain = surface == "domain_boundary"
                shift = (method_index+quadrature_index) if sensitivity else 0.0
                for end in (1.0, 2.0):
                    row = {
                        "case": "SYNTHETIC", "surface": surface,
                        "storage_region": "whole_grid" if domain else surface,
                        "reconstruction": method, "temporal_quadrature": quadrature,
                        "interval_start_myr": end-1, "interval_end_myr": end,
                        "interval_duration_myr": 1.0,
                        "nominal_configured_bipolar_energy_erg": 50.0*end,
                    }
                    for quantity, unit, storage, flux in (
                        ("energy", "erg", 80.0+outer_energy if domain else 20.0,
                         -30.0+shift if domain else 30.0+2*shift),
                        ("mass", "g", 8.0+outer_mass if domain else 2.0,
                         -3.0 if domain else 3.0),
                    ):
                        values = {
                            f"storage_{quantity}_change_{unit}": storage,
                            f"integrated_{quantity}_flux_outward_{unit}": flux,
                            f"inferred_internal_{quantity}_source_{unit}": storage+flux,
                        }
                        row.update(values)
                        row.update({"cumulative_"+name: value*end for name, value in values.items()})
                    result.append(row)
    return result


def write_inputs(path, records):
    path.mkdir()
    balances = path/"integrated_control_balances.csv"
    with balances.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    provenance = {
        "analysis_signature": "synthetic_only",
        "case": "SYNTHETIC", "snapshots": [{"output_index": i} for i in range(3)],
        "energy_definition": accounting.ENERGY_DEFINITION,
        "control_box_edges_kpc": {"1": {}, "2": {}},
        "control_padding_cells": [1, 2],
        "outputs": {balances.name: hashlib.sha256(balances.read_bytes()).hexdigest()},
    }
    (path/"provenance.json").write_text(json.dumps(provenance))


def test_nozzle_only_source_cancels_with_traceable_storage_and_flux():
    result = accounting.summarize_rows(rows(), (1, 2))
    assert len(result) == 48
    for row in result:
        assert row["outside_nozzle_storage_energy_change_erg"] == 60
        assert row["outside_nozzle_integrated_energy_flux_outward_erg"] == -60
        assert row["outside_nozzle_inferred_internal_energy_source_erg"] == 0
        assert row["outside_nozzle_inferred_internal_mass_source_g"] == 0
        assert row["outside_nozzle_cumulative_inferred_internal_energy_source_erg"] == 0


def test_added_outside_source_and_mass_gauge_response():
    original = rows(outer_energy=7.0, outer_mass=0.7)
    result = accounting.summarize_rows(original, (1, 2))
    shifted = [row.copy() for row in original]
    potential_shift = 11.0
    for row in shifted:
        for prefix in ("", "cumulative_"):
            for energy, mass in (
                ("storage_energy_change_erg", "storage_mass_change_g"),
                ("integrated_energy_flux_outward_erg", "integrated_mass_flux_outward_g"),
                ("inferred_internal_energy_source_erg", "inferred_internal_mass_source_g"),
            ):
                row[prefix+energy] += potential_shift*row[prefix+mass]
    shifted_result = accounting.summarize_rows(shifted, (1, 2))
    for row, other in zip(result, shifted_result, strict=True):
        assert row["outside_nozzle_inferred_internal_energy_source_erg"] == 7
        assert row["energy_gauge_response_mass_g"] == pytest.approx(0.7)
        assert other["outside_nozzle_inferred_internal_energy_source_erg"] == pytest.approx(
            7+potential_shift*row["energy_gauge_response_mass_g"])
        assert other["outside_nozzle_cumulative_inferred_internal_energy_source_erg"] == pytest.approx(
            row["outside_nozzle_cumulative_inferred_internal_energy_source_erg"]
            +potential_shift*row["cumulative_energy_gauge_response_mass_g"])


def test_reconstruction_cross_product_and_cadence_scenarios_are_not_averaged():
    result = accounting.summarize_rows(rows(sensitivity=True), (1, 2))
    selected = [r for r in result if r["interval_end_myr"] == 1 and r["nozzle_padding_cells"] == 1]
    assert len(selected) == 12
    assert {r["outside_nozzle_inferred_internal_energy_source_erg"] for r in selected} == {-4, -3, -2, -1, 0, 1}
    assert {r["temporal_quadrature"] for r in result} == set(accounting.QUADRATURES)


@pytest.mark.parametrize("change,match", [
    ("duplicate", "duplicate balance row"),
    ("missing_row", "interval mismatch"),
    ("missing_series", "missing series"),
    ("wrong_reconstruction", "unexpected surface/reconstruction"),
    ("time_mismatch", "interval mismatch"),
    ("mixed_case", "mixed/empty cases"),
    ("bad_source", "balance identity"),
    ("bad_cumulative", "cumulative progression"),
    ("nonfinite", "nonfinite numeric"),
])
def test_rejects_unmatched_or_inconsistent_inputs(change, match):
    records = rows()
    if change == "duplicate":
        records.append(records[0].copy())
    elif change == "missing_row":
        records.pop(0)
    elif change == "missing_series":
        records = [r for r in records if r["surface"] != "nozzle_control_p2"]
    elif change == "wrong_reconstruction":
        records[0]["reconstruction"] = "donor_cell_primitives"
    elif change == "time_mismatch":
        records[0].update(interval_start_myr=0.5, interval_end_myr=1.5)
    elif change == "mixed_case":
        records[0]["case"] = "OTHER"
    elif change == "bad_source":
        records[0]["inferred_internal_energy_source_erg"] += 5
    elif change == "bad_cumulative":
        records[0]["cumulative_storage_energy_change_erg"] += 5
        records[0]["cumulative_inferred_internal_energy_source_erg"] += 5
    elif change == "nonfinite":
        records[0]["storage_mass_change_g"] = float("nan")
    with pytest.raises(ValueError, match=match):
        accounting.summarize_rows(records, (1, 2))


def test_bound_input_and_no_overwrite(tmp_path):
    source, output = tmp_path/"input", tmp_path/"output"
    write_inputs(source, rows(outer_energy=7))
    receipt = accounting.run(source, output)
    assert receipt["row_count"] == 48
    assert "unresolved" in receipt["limits"][0]
    product = output/"outside_nozzle_source_balances.csv"
    assert receipt["products_sha256"][product.name] == hashlib.sha256(product.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        accounting.run(source, output)
    with (source/"integrated_control_balances.csv").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="balance hash"):
        accounting.run(source, tmp_path/"other")
    assert not (tmp_path/"other").exists()


def test_rejects_wrong_potential_convention(tmp_path):
    source = tmp_path/"input"
    write_inputs(source, rows())
    path = source/"provenance.json"
    provenance = json.loads(path.read_text())
    provenance["energy_definition"] = "unidentified potential"
    path.write_text(json.dumps(provenance))
    with pytest.raises(ValueError, match="potential/energy convention"):
        accounting.run(source, tmp_path/"output")


def test_rejects_entire_missing_interval_and_case_mismatch(tmp_path):
    source = tmp_path/"input"
    write_inputs(source, [r for r in rows() if r["interval_end_myr"] == 1])
    with pytest.raises(ValueError, match="producer snapshot count"):
        accounting.run(source, tmp_path/"output")
    path = source/"provenance.json"
    provenance = json.loads(path.read_text())
    provenance["case"] = "OTHER"
    path.write_text(json.dumps(provenance))
    with pytest.raises(ValueError, match="balance case"):
        accounting.run(source, tmp_path/"output")
