from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ROOT/"scripts/science"
if str(SCIENCE) not in sys.path:
    sys.path.insert(0, str(SCIENCE))
SPEC = importlib.util.spec_from_file_location("integrate_ghi_final_flux", SCIENCE/"integrate_ghi_final_flux.py")
integration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(integration)


def snapshot(index, endpoint=False):
    code = index*integration.CODE_TIME_PER_MYR
    age = code/integration.CODE_TIME_PER_MYR
    metadata = dict(output_index=index, time_code=code, timestep=f"Timestep_{index}",
                    resolved_path=f"/synthetic/data.{index:04d}.h5", shape=[4, 4, 4],
                    size_bytes=1024, inode=index+1, mtime_ns=7, ctime_ns=8)
    series = [("domain_boundary", "outer_active_cell")]
    if not endpoint:
        series.append(("domain_boundary", "linear_to_boundary_face"))
    series.extend((f"nozzle_control_p{padding}", method) for padding in (1, 2, 4)
                  for method in integration.source.NOZZLE_RECONSTRUCTIONS)
    flux_rows = []
    availability = {}
    for surface, method in series:
        base = 1 if surface == "domain_boundary" else 2
        energy = (index+2)*base*1e43
        for face in (*integration.flux.FACE_NAMES, "closed_surface_total"):
            factor = 1 if face == "closed_surface_total" else 1/6
            row = dict(snapshot_index=index, actual_time_myr=age,
                       surface=surface, reconstruction=method, face=face)
            row.update({field: factor*(energy if "energy" in field or "enthalpy" in field else index+1)
                        for field in integration.flux.FLUX_FIELDS})
            flux_rows.append(row)
        availability.setdefault(surface, {})[method] = dict(available=True, reason="measured")
    storage_rows = []
    for geometry in ("exact_fv_nodes", "legacy_midpoint_centres"):
        for region in ("whole_grid", "nozzle_control_p1", "nozzle_control_p2", "nozzle_control_p4",
                       "boundary_layer_1", "boundary_layer_2", "boundary_layer_4", "boundary_layer_8"):
            factor = 1 if region == "whole_grid" else 0.1
            energy = factor*(1000+10*index+0.1*index**2)*1e58
            storage_rows.append(dict(snapshot_index=index, actual_time_myr=age,
                volume_geometry=geometry, region=region, mass_g=factor*(100+index**2)*1e40,
                thermal_erg=0.7*energy, kinetic_erg=0.2*energy, gravitational_erg=0.1*energy,
                total_energy_erg=energy))
    record = dict(snapshot=metadata, flux_rows=flux_rows, storage_rows=storage_rows)
    if endpoint:
        availability["domain_boundary"]["linear_to_boundary_face"] = dict(
            available=False, reason="invalid_linear_primitive_faces", invalid_faces=["z_negative"])
        record.update(schema_version=1, status="measured_ghi_final_snapshot_addendum", case="G-HI",
                      surface_availability=availability, linear_diagnostics={})
    return record


@pytest.fixture
def bundle(tmp_path):
    partial, checkpoints = tmp_path/"partial", tmp_path/"checkpoints"
    partial.mkdir(); checkpoints.mkdir()
    records = [snapshot(i) for i in range(47)]
    endpoint = snapshot(47, endpoint=True)
    original_hashes = {name: integration.digest((SCIENCE/name).read_bytes()) for name in (
        "measure_q031_fluxes.py", "pluto_h5_level3_ambient_extract.py", "select_common_age_hdf5.py", "snapshot_energy.py")}
    payload = dict(analysis_implementation_hashes=original_hashes, control_padding_cells=[1, 2, 4],
                   snapshots=[r["snapshot"] for r in [*records, endpoint]])
    signature = integration.digest(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    checkpoint_sha, inventory = {}, []
    for i, record in enumerate(records):
        record["analysis_signature"] = signature
        path = checkpoints/f"{i:04d}-{i:04d}.json"
        raw = json.dumps(record).encode(); path.write_bytes(raw)
        checkpoint_sha[path.name] = integration.digest(raw)
        inventory.append(dict(index=i, filename=path.name, size_bytes=len(raw), sha256=integration.digest(raw)))
    context = dict(status="derived_partial_checkpoint_reduction", case="G-HI",
                   original_request_status="failed_at_index_47", original_native_run_completed=False,
                   kept_indices=list(range(47)), original_full_analysis_signature=signature,
                   original_full_signature_payload=payload, checkpoint_sha256=checkpoint_sha,
                   helper_sha256={name: integration.digest((SCIENCE/name).read_bytes()) for name in (
                       "measure_q031_fluxes.py", "summarize_q031_source_accounting.py")},
                   pluto_parameters={"JET_PWR": 1e45, "JET_START_TIME": 0., "JET_ACTIVE_TIME": 50.})
    f = [{"case": "G-HI", **row} for r in records for row in r["flux_rows"]]
    s = [{"case": "G-HI", **row} for r in records for row in r["storage_rows"]]
    balances = [{"case": "G-HI", **row} for row in integration.flux.integrate_flux_series(
        f, s, one_sided_power_erg_s=1e45, jet_start_myr=0, jet_active_myr=50)]
    outside = integration.source.summarize_rows(balances, [1, 2, 4])
    context["products_sha256"] = {}
    for name, rows in (("flux/integrated_control_balances.csv", balances),
                       ("source_accounting/outside_nozzle_source_balances.csv", outside)):
        path = partial/"products"/name; path.parent.mkdir(parents=True, exist_ok=True)
        integration.write_csv(path, rows)
        context["products_sha256"][name] = integration.digest(path.read_bytes())
    context_path = partial/"partial_context.json"
    context_path.write_text(json.dumps(context))
    endpoint_path = tmp_path/"endpoint.json"; endpoint_path.write_text(json.dumps(endpoint))
    qualification = dict(schema_version=1, status="qualified_ghi_index47_addendum", case="G-HI",
        snapshot_index=47, execution_qualified=True, scientifically_qualified=False,
        original_request=dict(status="failed_original_request", analysis_signature=signature),
        sources=dict(original_analysis_implementation_hashes=original_hashes),
        prefix=dict(count=47, indices=list(range(47)), checkpoints=inventory,
                    partial_context_sha256=integration.digest(context_path.read_bytes())),
        endpoint_product=dict(sha256=integration.digest(endpoint_path.read_bytes()), size_bytes=endpoint_path.stat().st_size))
    qualification_path = tmp_path/"qualification.json"; qualification_path.write_text(json.dumps(qualification))
    return dict(partial=partial, checkpoints=checkpoints, endpoint=endpoint_path,
                qualification=qualification_path, output=tmp_path/"output")


def run(bundle):
    return integration.run(bundle["partial"], bundle["checkpoints"], bundle["endpoint"],
                           bundle["qualification"], bundle["output"])


def test_final_interval_and_cumulative_have_distinct_correct_normalizations(bundle):
    receipt = run(bundle)
    assert receipt["row_counts"] == dict(integrated_controls=1128, outside_nozzle=1692,
                                        cumulative_scenarios=282, interval_scenarios=282)
    assert receipt["exact_overlap_scalar_checks"] > 100_000
    assert receipt["original_request_completed"] is False
    assert receipt["scientific_qualification"]["qualified"] is False
    assert receipt["final_interval_availability"] == dict(outside_nozzle_scenarios=36,
        available=24, unavailable=12, linear_left_endpoint_only=6,
        instantaneous_linear_flux_at_47_available=False)
    cumulative = integration.read_csv((bundle["output"]/"cumulative_scenarios.csv").read_bytes())
    intervals = integration.read_csv((bundle["output"]/"interval_scenarios.csv").read_bytes())
    choose = lambda rows: next(r for r in rows if r["snapshot_index"] == "47"
        and r["domain_reconstruction"] == "outer_active_cell" and r["temporal_quadrature"] == "trapezoid")
    interval, cum = choose(intervals), choose(cumulative)
    duration = float(interval["interval_end_myr"])-float(interval["interval_start_myr"])
    dt = duration*integration.flux.SECONDS_PER_MYR
    storage_interval = ((1000+10*47+0.1*47**2)-(1000+10*46+0.1*46**2))*1e58
    expected_interval_source = storage_interval+48.5e43*dt
    assert float(interval["labelled_energy_erg"]) == pytest.approx(2e45*dt)
    assert float(interval["whole_grid_inferred_source_over_label"]) == pytest.approx(expected_interval_source/(2e45*dt))
    assert float(cum["labelled_energy_erg"]) == pytest.approx(47*2e45*integration.flux.SECONDS_PER_MYR)
    assert float(cum["balance_start_myr"]) == 0
    assert float(interval["balance_start_myr"]) == 46
    assert float(interval["whole_grid_inferred_source_over_label"]) != pytest.approx(float(cum["whole_grid_inferred_source_over_label"]))


def test_invalid_linear_endpoint_leaves_only_trapezoid_and_right_unavailable(bundle):
    run(bundle)
    records = integration.read_csv((bundle["output"]/"outside_nozzle_source_balances.csv").read_bytes())
    last = [r for r in records if float(r["interval_end_myr"]) > 46]
    assert len(last) == 36
    unavailable = [r for r in last if r["measurement_status"] == "unavailable"]
    assert len(unavailable) == 12
    for row in unavailable:
        assert row["domain_reconstruction"] == "linear_to_boundary_face"
        assert row["temporal_quadrature"] in ("trapezoid", "right_rectangle")
        assert row["unavailable_reason"] == integration.UNAVAILABLE
        assert row["outside_nozzle_inferred_internal_energy_source_erg"] == ""
        assert row["outside_nozzle_cumulative_inferred_internal_energy_source_erg"] == ""
        assert row["nozzle_cumulative_inferred_internal_energy_source_erg"] != ""
    left = [r for r in last if r["measurement_status"] == "available_left_endpoint_quadrature"]
    assert len(left) == 6
    assert all(r["temporal_quadrature"] == "left_rectangle" and r["right_endpoint_flux_available"] == "False" for r in left)
    with pytest.raises(ValueError, match="already exists"):
        run(bundle)


@pytest.mark.parametrize("change,match", [
    ("unqualified", "not separately provenance-qualified"),
    ("endpoint_bytes", "endpoint product hash"),
    ("checkpoint_bytes", "checkpoint identity"),
    ("missing_checkpoint", "checkpoint index set"),
    ("partial_product", "partial product hash"),
    ("promoted_original", "unsupported or promoted partial"),
])
def test_fail_closed_inputs_publish_no_result(bundle, change, match):
    if change == "unqualified":
        p=bundle["qualification"];d=json.loads(p.read_text());d["execution_qualified"]=False;p.write_text(json.dumps(d))
    elif change == "endpoint_bytes":
        with bundle["endpoint"].open("a") as stream:stream.write("\n")
    elif change == "checkpoint_bytes":
        p=bundle["checkpoints"]/"0001-0001.json";p.write_text(p.read_text()+"\n")
    elif change == "missing_checkpoint":
        (bundle["checkpoints"]/"0001-0001.json").unlink()
    elif change == "partial_product":
        p=bundle["partial"]/"products/flux/integrated_control_balances.csv";p.write_text(p.read_text()+"\n")
    else:
        p=bundle["partial"]/"partial_context.json";d=json.loads(p.read_text());d["original_native_run_completed"]=True;p.write_text(json.dumps(d))
    with pytest.raises(ValueError, match=match):run(bundle)
    assert not bundle["output"].exists()


def test_rejects_missing_face_and_changed_prior_balance(bundle):
    context = json.loads((bundle["partial"]/"partial_context.json").read_text())
    records = [json.loads(p.read_text()) for p in sorted(bundle["checkpoints"].glob("*.json"))]
    endpoint = json.loads(bundle["endpoint"].read_text())
    balances=integration.read_csv((bundle["partial"]/"products/flux/integrated_control_balances.csv").read_bytes())
    outside=integration.read_csv((bundle["partial"]/"products/source_accounting/outside_nozzle_source_balances.csv").read_bytes())
    removed=endpoint["flux_rows"].pop()
    with pytest.raises(ValueError, match="incomplete closed surface"):
        integration.build_tables(records,endpoint,context,balances,outside)
    endpoint["flux_rows"].append(removed)
    balances[0]["storage_energy_change_erg"]=str(float(balances[0]["storage_energy_change_erg"])*1.001)
    with pytest.raises(ValueError, match="overlap changed"):
        integration.build_tables(records,endpoint,context,balances,outside)


def test_linear_left_matches_valid_reference_independently_of_right_endpoint(bundle):
    run(bundle)
    published=integration.read_csv((bundle["output"]/"integrated_control_balances.csv").read_bytes())
    left=next(r for r in published if float(r["interval_end_myr"])>46 and r["surface"]=="domain_boundary"
              and r["reconstruction"]=="linear_to_boundary_face" and r["temporal_quadrature"]=="left_rectangle")
    records=[json.loads(p.read_text()) for p in sorted(bundle["checkpoints"].glob("*.json"))]
    published_outside=integration.read_csv((bundle["output"]/"outside_nozzle_source_balances.csv").read_bytes())
    actual_outside={(int(r["nozzle_padding_cells"]),r["nozzle_reconstruction"]):r for r in published_outside
                    if float(r["interval_end_myr"])>46 and r["domain_reconstruction"]=="linear_to_boundary_face"
                    and r["temporal_quadrature"]=="left_rectangle"}
    assert len(actual_outside)==6
    reference_endpoint=snapshot(47)
    references=[]; trapezoids=[]
    for right_multiplier in (0.125, 1234.):
        reference=json.loads(json.dumps(reference_endpoint))
        for row in reference["flux_rows"]:
            if row["surface"]=="domain_boundary" and row["reconstruction"]=="linear_to_boundary_face":
                for field in integration.flux.FLUX_FIELDS:
                    row[field]*=right_multiplier
        all_records=[*records,reference]
        f=[row for record in all_records for row in record["flux_rows"]]
        s=[row for record in all_records for row in record["storage_rows"]]
        balances=integration.flux.integrate_flux_series(f,s,one_sided_power_erg_s=1e45,jet_start_myr=0,jet_active_myr=50)
        selected=next(r for r in balances if r["interval_end_myr"]>46 and r["surface"]=="domain_boundary"
                      and r["reconstruction"]=="linear_to_boundary_face" and r["temporal_quadrature"]=="left_rectangle")
        references.append(selected)
        for field in (*integration.source.NUMERIC_FIELDS,"nominal_configured_bipolar_energy_erg","cumulative_source_to_nominal_energy_ratio"):
            assert float(left[field])==selected[field]
        assert left["right_endpoint_flux_available"]=="False"
        trapezoids.append(next(r["inferred_internal_energy_source_erg"] for r in balances
            if r["interval_end_myr"]>46 and r["surface"]=="domain_boundary"
            and r["reconstruction"]=="linear_to_boundary_face" and r["temporal_quadrature"]=="trapezoid"))
        expected_outside=integration.source.summarize_rows([{"case":"G-HI",**r} for r in balances],[1,2,4])
        for row in expected_outside:
            if row["interval_end_myr"]<=46 or row["domain_reconstruction"]!="linear_to_boundary_face" or row["temporal_quadrature"]!="left_rectangle":
                continue
            actual=actual_outside[row["nozzle_padding_cells"],row["nozzle_reconstruction"]]
            for region in ("domain","nozzle","outside_nozzle"):
                for field in integration.source.NUMERIC_FIELDS:
                    assert float(actual[region+"_"+field])==row[region+"_"+field]
    assert references[0]==references[1]
    assert trapezoids[0]!=trapezoids[1]
    assert not any(row["reconstruction"]=="linear_to_boundary_face"
                   for row in json.loads(bundle["endpoint"].read_text())["flux_rows"])
