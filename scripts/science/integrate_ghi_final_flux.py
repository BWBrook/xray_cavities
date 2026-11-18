#!/usr/bin/env python3
"""Append a qualified G-HI/47 diagnostic without completing the failed request."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

import measure_q031_fluxes as flux
import summarize_q031_source_accounting as source
from select_common_age_hdf5 import CODE_TIME_PER_MYR

QUADRATURES = source.QUADRATURES
UNAVAILABLE = "invalid_linear_primitive_faces_at_index_47"
TRANSPORT_SOURCE_FIELDS = tuple(
    prefix+field for prefix in ("", "cumulative_")
    for field in ("integrated_mass_flux_outward_g", "inferred_internal_mass_source_g",
                  "integrated_energy_flux_outward_erg", "inferred_internal_energy_source_erg")
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_csv(raw):
    return list(csv.DictReader(io.StringIO(raw.decode())))


def write_csv(path, rows):
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def balance_key(row):
    return (float(row["interval_start_myr"]), float(row["interval_end_myr"]),
            row["surface"], row["reconstruction"], row["temporal_quadrature"])


def outside_key(row):
    return (float(row["interval_start_myr"]), float(row["interval_end_myr"]),
            row["domain_reconstruction"], row["nozzle_reconstruction"],
            int(row["nozzle_padding_cells"]), row["temporal_quadrature"])


def verify_overlap(actual, prior, key):
    indexed = {key(row): row for row in actual}
    require(len(indexed) == len(actual) == len(prior), "overlap has missing or duplicate rows")
    checks = 0
    for row in prior:
        current = indexed.get(key(row))
        require(current is not None, "overlap key differs from prior recovered balance")
        for field, expected in row.items():
            value = current[field]
            if isinstance(value, (float, int)):
                require(math.isfinite(value) and value == float(expected),
                        f"overlap changed: {key(row)}/{field}")
            else:
                require(value == expected, f"overlap changed: {key(row)}/{field}")
            checks += 1
    return checks


def validate_snapshot(record, index, paddings, endpoint=False):
    snapshot = record["snapshot"]
    require(snapshot["output_index"] == index, "snapshot index mismatch")
    expected = {("domain_boundary", "outer_active_cell"),
                *((f"nozzle_control_p{p}", method) for p in paddings
                  for method in source.NOZZLE_RECONSTRUCTIONS)}
    if not endpoint:
        expected.add(("domain_boundary", "linear_to_boundary_face"))
    if endpoint:
        require(record.get("schema_version") == 1
                and record.get("status") == "measured_ghi_final_snapshot_addendum"
                and record.get("case") == "G-HI", "unsupported endpoint product")
        availability = record["surface_availability"]
        for surface, method in expected:
            require(availability[surface][method]["available"] is True,
                    f"endpoint surface not available: {surface}/{method}")
        linear = availability["domain_boundary"]["linear_to_boundary_face"]
        require(linear["available"] is False and linear["reason"] == "invalid_linear_primitive_faces"
                and bool(linear["invalid_faces"]), "original invalid linear face must remain unavailable")
    groups = {}
    age = snapshot["time_code"] / CODE_TIME_PER_MYR
    for row in record["flux_rows"]:
        require(row["snapshot_index"] == index and row["actual_time_myr"] == age,
                "flux row time/index mismatch")
        group = groups.setdefault((row["surface"], row["reconstruction"]), {})
        require(row["face"] not in group, "duplicate endpoint/checkpoint face")
        group[row["face"]] = row
    require(set(groups) == expected, "missing or unexpected surface series")
    for faces in groups.values():
        require(set(faces) == {*flux.FACE_NAMES, "closed_surface_total"}, "incomplete closed surface")
        for field in flux.FLUX_FIELDS:
            values = [float(faces[face][field]) for face in flux.FACE_NAMES]
            total = float(faces["closed_surface_total"][field])
            require(all(math.isfinite(v) for v in (*values, total)), "nonfinite surface flux")
            require(abs(math.fsum(values)-total) <= 1e-12*max(math.fsum(abs(v) for v in values), abs(total), 1),
                    "closed surface differs from six faces")
    storage_keys = set()
    for row in record["storage_rows"]:
        require(row["snapshot_index"] == index and row["actual_time_myr"] == age,
                "storage row time/index mismatch")
        key = row["volume_geometry"], row["region"]
        require(key not in storage_keys, "duplicate storage region")
        storage_keys.add(key)
        require(all(math.isfinite(float(row[field])) for field in flux.STORAGE_FIELDS), "nonfinite storage")
    expected_regions = {"whole_grid", *(f"nozzle_control_p{p}" for p in paddings),
                        *(f"boundary_layer_{p}" for p in (1, 2, 4, 8))}
    require(storage_keys == {(geometry, region) for geometry in ("exact_fv_nodes", "legacy_midpoint_centres")
                             for region in expected_regions}, "incomplete storage geometry/regions")
    return age


def label(age, parameters):
    return (2*parameters["JET_PWR"] * min(max(age-parameters["JET_START_TIME"], 0),
                                        parameters["JET_ACTIVE_TIME"]) * flux.SECONDS_PER_MYR)


def add_outside_row(domain, nozzle, padding):
    available = domain["balance_available"]
    row = {"case": "G-HI", "domain_reconstruction": domain["reconstruction"],
           "nozzle_reconstruction": nozzle["reconstruction"], "nozzle_padding_cells": padding,
           "temporal_quadrature": domain["temporal_quadrature"],
           **{field: domain[field] for field in ("interval_start_myr", "interval_end_myr", "interval_duration_myr",
                                                "nominal_configured_bipolar_energy_erg")}}
    for field in source.NUMERIC_FIELDS:
        d, n = domain[field], nozzle[field]
        row.update({"domain_"+field: d, "nozzle_"+field: n,
                    "outside_nozzle_"+field: d-n if d != "" else ""})
    for prefix in ("", "cumulative_"):
        row[prefix+"energy_gauge_response_mass_g"] = row["outside_nozzle_"+prefix+"inferred_internal_mass_source_g"]
    value = row["outside_nozzle_cumulative_inferred_internal_energy_source_erg"]
    row["cumulative_outside_nozzle_source_to_nominal_ratio"] = value/domain["nominal_configured_bipolar_energy_erg"] if available else ""
    row.update(measurement_status=domain["measurement_status"], unavailable_reason=domain["unavailable_reason"],
               balance_available=available, right_endpoint_flux_available=domain["right_endpoint_flux_available"],
               labelled_interval_energy_erg=domain["labelled_interval_energy_erg"])
    return row


def build_tables(checkpoints, endpoint, context, prior_balances, prior_outside):
    paddings = context["original_full_signature_payload"]["control_padding_cells"]
    parameters = context["pluto_parameters"]
    require(paddings == [1, 2, 4], "unexpected nozzle padding contract")
    require(parameters == {"JET_PWR": 1e45, "JET_START_TIME": 0., "JET_ACTIVE_TIME": 50.}, "unexpected G-HI labelled input")
    require(len(checkpoints) == 47, "expected complete 0–46 checkpoints")
    ages = [validate_snapshot(record, i, paddings) for i, record in enumerate(checkpoints)]
    end = validate_snapshot(endpoint, 47, paddings, endpoint=True)
    require(ages[0] == 0 and all(b > a for a, b in zip(ages, ages[1:])) and end > ages[-1], "invalid snapshot chronology")
    records = [*checkpoints, endpoint]
    flux_rows = [{"case": "G-HI", **row} for record in records for row in record["flux_rows"]]
    storage_rows = [{"case": "G-HI", **row} for record in records for row in record["storage_rows"]]
    balances = [{"case": "G-HI", **row} for row in flux.integrate_flux_series(
        flux_rows, storage_rows, one_sided_power_erg_s=parameters["JET_PWR"],
        jet_start_myr=parameters["JET_START_TIME"], jet_active_myr=parameters["JET_ACTIVE_TIME"])]
    prefix = [row for row in balances if row["interval_end_myr"] <= ages[-1]]
    overlap_checks = verify_overlap(prefix, prior_balances, balance_key)
    overlap_checks += verify_overlap(source.summarize_rows(prefix, paddings), prior_outside, outside_key)
    final = [row for row in balances if row["interval_end_myr"] == end]
    require(len(final) == 21, "incomplete final valid controls")
    for row in final:
        row.update(measurement_status="measured", unavailable_reason="",
                   balance_available=True, right_endpoint_flux_available=True,
                   labelled_interval_energy_erg=label(end, parameters)-label(ages[-1], parameters))
    for quadrature in QUADRATURES:
        outer = next(row for row in final if row["surface"] == "domain_boundary" and row["temporal_quadrature"] == quadrature)
        linear = {**outer, "reconstruction": "linear_to_boundary_face",
                       "measurement_status": "unavailable", "unavailable_reason": UNAVAILABLE,
                       "balance_available": False, "right_endpoint_flux_available": False}
        if quadrature == "left_rectangle":
            previous = next(row for row in prefix if row["surface"] == "domain_boundary"
                            and row["reconstruction"] == "linear_to_boundary_face"
                            and row["temporal_quadrature"] == quadrature and row["interval_end_myr"] == ages[-1])
            left_flux = next(row for row in checkpoints[-1]["flux_rows"]
                             if row["surface"] == "domain_boundary" and row["reconstruction"] == "linear_to_boundary_face"
                             and row["face"] == "closed_surface_total")
            dt_seconds = (end-ages[-1])*flux.SECONDS_PER_MYR
            for quantity, unit, field in (("mass", "g", "mass_flux_outward_g_s"),
                                          ("energy", "erg", "total_energy_flux_outward_erg_s")):
                transport = float(left_flux[field])*dt_seconds
                cumulative_transport = previous[f"cumulative_integrated_{quantity}_flux_outward_{unit}"]+transport
                for prefix_name, value in (("", transport), ("cumulative_", cumulative_transport)):
                    linear[f"{prefix_name}integrated_{quantity}_flux_outward_{unit}"] = value
                    linear[f"{prefix_name}inferred_internal_{quantity}_source_{unit}"] = linear[f"{prefix_name}storage_{quantity}_change_{unit}"]+value
            linear.update(measurement_status="available_left_endpoint_quadrature", unavailable_reason="",
                               balance_available=True)
            linear["cumulative_source_to_nominal_energy_ratio"] = linear["cumulative_inferred_internal_energy_source_erg"]/linear["nominal_configured_bipolar_energy_erg"]
        else:
            linear.update({field: "" for field in (*TRANSPORT_SOURCE_FIELDS, "cumulative_source_to_nominal_energy_ratio")})
        final.append(linear)
    final_outside = []
    for domain in (row for row in final if row["surface"] == "domain_boundary"):
        for padding in paddings:
            for method in source.NOZZLE_RECONSTRUCTIONS:
                nozzle = next(row for row in final if row["surface"] == f"nozzle_control_p{padding}"
                              and row["reconstruction"] == method and row["temporal_quadrature"] == domain["temporal_quadrature"])
                final_outside.append(add_outside_row(domain, nozzle, padding))
    complete_balances = []
    for original in prior_balances:
        row = dict(original)
        row.update(measurement_status="measured", unavailable_reason="",
                   balance_available=True, right_endpoint_flux_available=True,
                   labelled_interval_energy_erg=label(float(row["interval_end_myr"]), parameters)-label(float(row["interval_start_myr"]), parameters))
        complete_balances.append(row)
    complete_outside = []
    for original in prior_outside:
        row = dict(original)
        row.update(measurement_status="measured", unavailable_reason="",
                   balance_available=True, right_endpoint_flux_available=True,
                   labelled_interval_energy_erg=label(float(row["interval_end_myr"]), parameters)-label(float(row["interval_start_myr"]), parameters))
        complete_outside.append(row)
    complete_balances.extend(final)
    complete_outside.extend(final_outside)
    cumulative, interval = [], []
    for index, age in enumerate([*ages[1:], end], 1):
        selected = [row for row in complete_outside if float(row["interval_end_myr"]) == age]
        for outer in source.DOMAIN_RECONSTRUCTIONS:
            for quadrature in QUADRATURES:
                group = [row for row in selected if row["domain_reconstruction"] == outer and row["temporal_quadrature"] == quadrature]
                require(len(group) == 6, "missing outside-nozzle scenario")
                valid = group[0]["balance_available"]
                shared = dict(case="G-HI", snapshot_index=index, domain_reconstruction=outer,
                              temporal_quadrature=quadrature, measurement_status=group[0]["measurement_status"],
                              balance_available=valid, right_endpoint_flux_available=group[0]["right_endpoint_flux_available"],
                              unavailable_reason=group[0]["unavailable_reason"])
                for table, prefix_name, scale in ((cumulative, "cumulative_", label(age, parameters)),
                                                   (interval, "", group[0]["labelled_interval_energy_erg"])):
                    row = {**shared, "interval_start_myr": float(group[0]["interval_start_myr"]), "interval_end_myr": age,
                           "balance_start_myr": 0.0 if prefix_name else float(group[0]["interval_start_myr"]),
                           "balance_end_myr": age,
                           "normalization_scope": "cumulative_0_to_end" if prefix_name else "saved_interval",
                           "labelled_energy_erg": scale}
                    row["whole_grid_inferred_source_over_label"] = float(group[0]["domain_"+prefix_name+"inferred_internal_energy_source_erg"])/scale if valid else ""
                    for region in ("nozzle", "outside_nozzle"):
                        values = [float(r[region+"_"+prefix_name+"inferred_internal_energy_source_erg"])/scale for r in group] if valid or region == "nozzle" else []
                        row[region+"_inferred_source_over_label_min"] = min(values) if values else ""
                        row[region+"_inferred_source_over_label_max"] = max(values) if values else ""
                    table.append(row)
    return complete_balances, complete_outside, cumulative, interval, overlap_checks


def run(partial_dir, checkpoint_dir, endpoint_path, qualification_path, output_dir):
    require(not output_dir.exists(), f"output directory already exists: {output_dir}")
    inputs = {}

    def read(path):
        raw = path.read_bytes()
        inputs[path.resolve()] = digest(raw)
        return raw

    context = json.loads(read(partial_dir/"partial_context.json"))
    require(context["status"] == "derived_partial_checkpoint_reduction" and context["case"] == "G-HI"
            and context["original_request_status"] == "failed_at_index_47" and context["original_native_run_completed"] is False
            and context["kept_indices"] == list(range(47)), "unsupported or promoted partial history")
    products = {}
    for name, expected in context["products_sha256"].items():
        raw = read(partial_dir/"products"/name)
        require(digest(raw) == expected, f"partial product hash differs: {name}")
        products[name] = read_csv(raw)
    qualification = json.loads(read(qualification_path))
    require(qualification.get("schema_version") == 1 and qualification.get("status") == "qualified_ghi_index47_addendum"
            and qualification.get("case") == "G-HI" and qualification.get("snapshot_index") == 47
            and qualification.get("execution_qualified") is True and qualification.get("scientifically_qualified") is False,
            "endpoint is not separately provenance-qualified")
    original = qualification["original_request"]
    require(original["status"] == "failed_original_request" and original["analysis_signature"] == context["original_full_analysis_signature"],
            "qualification does not bind original failed analysis")
    source_hashes = context["original_full_signature_payload"]["analysis_implementation_hashes"]
    require(digest(json.dumps(context["original_full_signature_payload"], sort_keys=True, separators=(",", ":")).encode())
            == original["analysis_signature"], "original signature payload differs")
    require(qualification["sources"]["original_analysis_implementation_hashes"] == source_hashes,
            "original source hashes differ")
    for name, expected in {**source_hashes, **context["helper_sha256"]}.items():
        require(digest(read(Path(__file__).parent/name)) == expected, f"unchanged helper/source hash differs: {name}")
    inventory = qualification["prefix"]
    require(inventory["partial_context_sha256"] == inputs[(partial_dir/"partial_context.json").resolve()],
            "qualified partial context differs")
    require(inventory["count"] == len(inventory["checkpoints"]) == 47
            and inventory["indices"] == list(range(47)), "qualified prefix is incomplete")
    declared = {row["filename"]: row for row in inventory["checkpoints"]}
    expected_names = {f"{i:04d}-{i:04d}.json" for i in range(47)}
    require(set(declared) == {p.name for p in checkpoint_dir.glob("*.json")} == expected_names, "checkpoint index set differs")
    checkpoints = []
    for i in range(47):
        name = f"{i:04d}-{i:04d}.json"
        raw = read(checkpoint_dir/name)
        bound = declared[name]
        contextual = [sha for path, sha in context["checkpoint_sha256"].items() if Path(path).name == name]
        require(bound["index"] == i and bound["size_bytes"] == len(raw)
                and contextual == [digest(raw)] and bound["sha256"] == digest(raw), "checkpoint identity differs")
        checkpoint = json.loads(raw)
        require(checkpoint["analysis_signature"] == original["analysis_signature"], "checkpoint analysis signature differs")
        checkpoints.append(checkpoint)
    endpoint_raw = read(endpoint_path)
    require(qualification["endpoint_product"]["sha256"] == digest(endpoint_raw)
            and qualification["endpoint_product"]["size_bytes"] == len(endpoint_raw), "endpoint product hash/size differs")
    endpoint = json.loads(endpoint_raw)
    historical = context["original_full_signature_payload"]["snapshots"][47]
    for field in ("resolved_path", "output_index", "time_code", "timestep", "shape", "size_bytes", "inode", "mtime_ns", "ctime_ns"):
        require(endpoint["snapshot"][field] == historical[field], f"endpoint native identity differs: {field}")
    tables = build_tables(checkpoints, endpoint, context, products["flux/integrated_control_balances.csv"],
                          products["source_accounting/outside_nozzle_source_balances.csv"])
    for path, expected in inputs.items():
        require(digest(path.read_bytes()) == expected, f"input changed during integration: {path}")
    output_dir.mkdir(parents=True)
    for name, rows in zip(("integrated_control_balances.csv", "outside_nozzle_source_balances.csv", "cumulative_scenarios.csv", "interval_scenarios.csv"), tables[:4], strict=True):
        write_csv(output_dir/name, rows)
    receipt = {
        "schema_version": 1, "status": "completed_local_ghi_index47_flux_addendum", "case": "G-HI",
        "indices": list(range(48)), "original_request": original, "original_request_completed": False,
        "original_analysis_implementation_hashes": source_hashes, "original_helper_hashes": context["helper_sha256"],
        "qualified_source_identities": qualification["sources"],
        "input_sha256": {str(path): sha for path, sha in inputs.items()},
        "endpoint_qualification_sha256": inputs[qualification_path.resolve()],
        "integrator_sha256": digest(Path(__file__).read_bytes()), "exact_overlap_scalar_checks": tables[4],
        "row_counts": dict(zip(("integrated_controls", "outside_nozzle", "cumulative_scenarios", "interval_scenarios"), (len(t) for t in tables[:4]), strict=True)),
        "final_interval_availability": {
            "outside_nozzle_scenarios": 36,
            "available": sum(row["balance_available"] for row in tables[1][-36:]),
            "unavailable": sum(not row["balance_available"] for row in tables[1][-36:]),
            "linear_left_endpoint_only": sum(row["measurement_status"] == "available_left_endpoint_quadrature" for row in tables[1][-36:]),
            "instantaneous_linear_flux_at_47_available": False,
        },
        "products_sha256": {path.name: digest(path.read_bytes()) for path in sorted(output_dir.glob("*.csv"))},
        "scientific_qualification": {"qualified": False, "holds": [
            "saved-cell reconstructed fluxes and cadence scenarios are not solver-step delivery",
            "instantaneous linear boundary-face flux at index 47 and its trapezoid/right quadratures remain unavailable; left rectangle uses valid F46 only",
            "original failed request and its missing final checks are preserved",
            "native domain contact, potential-zero dependence and production-boundary qualifications remain",
        ]},
        "normalization": "interval ratios use label(end)-label(start); cumulative ratios use label(end), baseline at zero",
    }
    (output_dir/"integration_receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("partial-dir", "checkpoint-dir", "endpoint", "qualification", "output-dir"):
        parser.add_argument("--"+argument, type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.partial_dir, args.checkpoint_dir, args.endpoint, args.qualification, args.output_dir)
    print(json.dumps({key: receipt[key] for key in ("status", "row_counts", "exact_overlap_scalar_checks")}, indent=2))


if __name__ == "__main__":
    main()
