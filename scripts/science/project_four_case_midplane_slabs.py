"""Integrate the 18 held-out native snapshots along y at the three registered depths."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import h5py
import numpy as np

import assemble_blind_emission_cohort as cohort
import prepare_blind_emission_maps as previous
import project_ghi20_midplane_slabs as pilot


emission = previous.emission
budget = previous.BUDGET
AXES = previous.blind.AXES
BRIGHTNESS = "brightness_current_retained_linear_whole"
PILOT_SHA256 = "86ff048c4fccad2bc41cc29390b43c15617e20d90747c732dd3e6a8a8380b470"
PIXEL_RTOL = 4e-11


def digests(records):
    return {key: record["sha256"] for key, record in records.items()}


def read_bound(path, sha256, identities):
    identity = emission.checked_compact({"path": str(path.absolute()), "sha256": sha256})
    identities.append(identity)
    return previous.blind.read_json(path)


def bind_production(case, index, kind, directory, sha256, config, config_sha256, identities):
    old = read_bound(directory / "completion.json", sha256, identities)
    if (old["case"], old["snapshot_index"], old["kind"]) != (case, index, kind):
        raise ValueError("archived map completion has the wrong case, age or kind")
    ref = old["provenance"]["native_input_receipt"]
    native = read_bound(Path(ref["path"]), ref["sha256"], identities)
    previous.validate_native_receipt(native, case, index)
    cohort.bind_producer_metadata(old, native, config, config_sha256)
    roles = {item["role"]: item["sha256"] for item in old["provenance"]["native_inputs"]}
    if digests(native["inputs"]) != roles:
        raise ValueError("archived map producer and native receipt disagree on input hashes")
    return old, native


def reference_files(old, zero):
    references = {}
    case, index = old["case"], old["snapshot_index"]
    for angle in (0, 90):
        for label, receipt, age, field, ending in (
            ("current", old, index, "maps_filename", ".npz"),
            ("truth", old, index, "truth_filename", ".truth.npz"),
            ("initial", zero, 0, "maps_filename", ".npz"),
        ):
            units = [u for u in receipt["units"] if u["view_deg"] == angle]
            name = f"{case}_{age:04d}_{angle}deg"
            if (len(units) != 1 or units[0]["case"] != case or units[0]["snapshot_index"] != age
                    or units[0]["kind"] != receipt["kind"] or units[0]["unit_id"] != name
                    or units[0][field] != name + ending):
                raise ValueError(f"{name}: archived producer unit does not bind its reference")
            filename = units[0][field]
            record = receipt["files"][filename]
            references[f"{label}_{angle}"] = {"filename": filename, "sha256": record["sha256"],
                                              "size_bytes": record["size_bytes"]}
    return references


def bind_sources(old, zero, identities):
    archive = old["provenance"]["analysis_sources"]
    if digests(archive) != digests(zero["provenance"]["analysis_sources"]):
        raise ValueError("archived current and initial map producers used different analysis sources")
    for filename, record in archive.items():
        module = sys.modules.get(Path(filename).stem)
        path = Path(module.__file__) if module else Path(previous.__file__).with_name(filename)
        identities.append(emission.checked_compact({"path": str(path.resolve()), "sha256": record["sha256"]}))
    identities.append(emission.checked_compact({"path": str(Path(pilot.__file__).resolve()),
                                                "sha256": PILOT_SHA256}))
    this_file = Path(__file__).resolve()
    own_identity = {**budget._stat_identity(this_file), "sha256": budget._sha256(this_file)}
    identities.append(own_identity)
    return own_identity["sha256"]


def bind_ghi_lineage(native, old, identities):
    archived = old["provenance"]["inherited_lineage_receipt"]
    if native["case"] != "G-HI":
        if archived is not None:
            raise ValueError("unexpected inherited G-HI lineage on another case")
        return None
    ref = native["native_preflight"]["inherited_lineage"]["receipt"]
    if ref["sha256"] != archived["sha256"]:
        raise ValueError("archived G-HI producer differs from the accepted native ancestry")
    lineage = read_bound(Path(ref["path"]), ref["sha256"], identities)
    chain = lineage["snapshots"]["analysis_chain"]
    if (lineage.get("schema_version") != 1 or lineage.get("status") != "passed"
            or lineage.get("lineage") != "accepted failed-run parent build/source plus validated 10 Myr home continuation"
            or [row.get("output_index") for row in chain] != list(range(51))):
        raise ValueError("incomplete or unaccepted G-HI native analysis chain")
    # Compare historical file identities to each other. bind_inputs verifies the
    # live copy, including its full hash if the NFS device has changed since then.
    for epoch, index in (("initial", 0), ("current", native["snapshot_index"])):
        record = native["inputs"][epoch + "_h5"]
        keys = ("path", "resolved_path", "size_bytes", "mtime_ns", "ctime_ns", "device", "inode")
        if (any(chain[index].get(k) != record[k] for k in keys)
                or any(chain[index].get(k) != native[epoch][k] for k in ("timestep", "time_code"))):
            raise ValueError(f"{epoch}: G-HI snapshot differs from the accepted native analysis chain")
    return ref["sha256"]


def matched_axes(grid, datasets):
    axes = {"horizontal_axis_kpc": grid.x, "horizontal_edges_kpc": grid.x_edges,
            "z_axis_kpc": grid.z, "z_edges_kpc": grid.z_edges}
    for label, archive in datasets.items():
        if any(not np.array_equal(archive[name], value) for name, value in axes.items()):
            raise ValueError(f"{label}: archived native-axis projection and xyz grid differ")
    return axes


def compare_pixels(maps, datasets):
    checks = {}
    for name, label, field in (("current_full", "current_0", BRIGHTNESS),
                               ("initial_full", "initial_0", BRIGHTNESS),
                               ("tracer_path_full", "truth_0", "path_C_kpc")):
        current, archived = maps[name], datasets[label][field]
        result = emission.closure(name, current, archived)
        exact = np.array_equal(current, archived)
        if ((name == "tracer_path_full" and not exact)
                or not np.allclose(current, archived, rtol=PIXEL_RTOL, atol=0)):
            raise ValueError(f"{name}: native and archived 0-degree pixels differ")
        checks[name] = {**result, "reference": label, "reference_key": field,
                        "reference_dtype": str(archived.dtype),
                        "bitwise_equal": bool(current.dtype == archived.dtype
                                              and current.tobytes() == archived.tobytes())}
    return checks


def check_integrals(maps, summary, grid, old):
    if summary["tracer_boundary_face_cells"] != old["diagnostics"]["native_component_boundary_cell_counts"]["C"]:
        raise ValueError("tracer face counts differ from archived native counts")
    flags = {"negative": "retained_linear_negative", "raw_nonfinite": "raw_nonfinite",
             "out_of_table": "any_out_of_table", "retained_nonfinite": "retained_linear_nonfinite"}
    for epoch, counts in summary["emissivity_cell_counts"]["full"].items():
        reference = old["diagnostics"]["correction_domain"][epoch]
        if any(counts[k] != reference[v] for k, v in flags.items()):
            raise ValueError(f"{epoch}: native emissivity-domain counts differ from archived counts")
    area = grid.dz[:, None] * grid.dx[None, :]
    archived = old["projection"]["0"]["native_integrals"]
    checks = {}
    for field, key in pilot.FULL_REFERENCE.items():
        name = field + "_full"
        actual = float(np.sum(maps[name] * area))
        checks[name] = {**emission.closure(name, actual, archived[key]),
                        "reference_key": key, "native_integral": archived[key], "projected_integral": actual}
    emission.closure("full 3D tracer volume", summary["native_tracer_volume_kpc3"]["full"]["both"],
                     archived["path_C_kpc"])
    return checks


def make_emissivity(runtime, contract):
    xraise = previous.NATIVE.renderer.load_module(Path(runtime["xraise_py"]["path"]))
    tables = previous.NATIVE.load_tables(Path(runtime["apec_table"]["path"]), Path(runtime["gaunt_lut"]["path"]))

    def evaluate(rho, prs):
        values, _, flags = previous.NATIVE.cell_emissivity(
            xraise=xraise, tables=tables, rho_code=rho[None], pressure_code=prs[None],
            frequency_hz=contract["frequency_hz"], redshift=contract["redshift"])
        before = values["retained_linear_before"][0]
        return values["retained_linear"][0], {
            "out_of_table": flags["any"][0], "negative": np.isfinite(before) & (before < 0),
            "retained_nonfinite": ~np.isfinite(before), "raw_nonfinite": flags["raw_nonfinite"][0]}

    return evaluate


def run(contract_path, contract_sha256, previous_dir, previous_sha256, initial_previous_sha256, truth_dir, output):
    if output.exists():
        raise FileExistsError(output)
    identities = []
    contract = read_bound(contract_path, contract_sha256, identities)
    config_ref = contract["protocol_config"]
    config = read_bound(Path(config_ref["path"]), config_ref["sha256"], identities)
    previous.validate_specification(contract, config)
    case, index = contract["case"], contract["snapshot_index"]
    if contract["kind"] != "science":
        raise ValueError("the held-out slab cohort requires an evolved science snapshot")
    zero_dir = previous_dir.parent / f"{case}_0000"
    old, native = bind_production(case, index, "science", previous_dir, previous_sha256,
                                  config, config_ref["sha256"], identities)
    zero, native_zero = bind_production(case, 0, "initial_null", zero_dir, initial_previous_sha256,
                                        config, config_ref["sha256"], identities)
    provenance = old["provenance"]
    if (contract_sha256 != provenance["contract"]["sha256"]
            or contract["native_input_receipt"] != {k: provenance["native_input_receipt"][k] for k in ("path", "sha256")}):
        raise ValueError("archived science producer and requested emission contract disagree")
    native_hashes, zero_hashes = digests(native["inputs"]), digests(native_zero["inputs"])
    if {**native_hashes, "current_h5": native_hashes["initial_h5"]} != zero_hashes:
        raise ValueError("time-zero map producer does not bind the science snapshot's initial conditions")
    preflight_ref = native["native_preflight"]["contract"]
    if preflight_ref["sha256"] != provenance["native_preflight_contract"]["sha256"]:
        raise ValueError("archived and native case preflight contract digests differ")
    native_contract = read_bound(Path(preflight_ref["path"]), preflight_ref["sha256"], identities)
    previous.validate_receipt_contract(native, native_contract)
    paths = {role: Path(record["path"]) for role, record in native["inputs"].items()}
    native_ids, _, binding, _ = budget.bind_inputs(paths, Path(contract["native_input_receipt"]["path"]))
    identities.extend(native_ids)
    lineage = bind_ghi_lineage(native, old, identities)
    runtime = {k: emission.checked_compact(r) for k, r in contract["inputs"].items()}
    identities.extend(runtime.values())
    projector_sha = bind_sources(old, zero, identities)
    refs = reference_files(old, zero)
    raster_paths = {}
    for label, location in (("current_0", previous_dir), ("truth_0", truth_dir), ("initial_0", zero_dir)):
        record = refs[label]
        fields = (*AXES, "path_C_kpc") if label == "truth_0" else previous.DETECTOR_FIELDS
        bound = cohort.payload(location.absolute(), record["filename"], record, fields)
        identities.append(bound)
        raster_paths[label] = Path(bound["path"])
    budget._stable(identities)
    evaluate = make_emissivity(runtime, contract)
    budget._validate_snapshot_index(paths["current_h5"], index)
    budget._validate_snapshot_index(paths["initial_h5"], 0)
    with (h5py.File(paths["current_h5"], "r") as current, h5py.File(paths["initial_h5"], "r") as initial,
          np.load(raster_paths["current_0"], allow_pickle=False) as current_map,
          np.load(raster_paths["truth_0"], allow_pickle=False) as truth_map,
          np.load(raster_paths["initial_0"], allow_pickle=False) as initial_map):
        data, grids = [], []
        for epoch, file in (("current", current), ("initial", initial)):
            step, time_code, shape = budget._single_timestep(file, native[epoch]["timestep"], context=epoch)
            if (list(shape) != native_contract["shape_nz_ny_nx"]
                    or not np.isclose(time_code, native[epoch]["time_code"], rtol=0, atol=1e-10)):
                raise ValueError(f"{epoch}: HDF5 time or shape differs from native receipt")
            grids.append(emission.read_grid(file, shape, grid_file=paths.get("grid_file")))
            data.append(file[step]["vars"])
        grid = grids[0]
        budget._validate_grid(grid, grids[1])
        datasets = {"current_0": current_map, "truth_0": truth_map, "initial_0": initial_map}
        axes = matched_axes(grid, datasets)
        print(f"Integrating native fields for {case}/{index} Myr", flush=True)
        maps, summary = pilot.project(*data, grid, evaluate, emission.BRIGHTNESS_FACTOR)
        pixel_checks = compare_pixels(maps, datasets)
    integral_checks = check_integrals(maps, summary, grid, old)
    actual_age = native["current"]["time_code"] / budget.CODE_TIME_PER_MYR
    if not np.isclose(actual_age, old["actual_time_myr"], rtol=0, atol=1e-10):
        raise ValueError("archived producer age differs from the native receipt")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".midplane-") as tmp:
        staged = Path(tmp) / "result"
        staged.mkdir()
        product = staged / "projections.npz"
        np.savez_compressed(product, **axes, **maps)
        completion = {
            "schema_version": 1, "status": "complete", "case": case, "snapshot_index": index,
            "actual_time_myr": actual_age, "view_deg": 0, "energy_kev": 1.0,
            "frequency_hz": contract["frequency_hz"], "redshift": contract["redshift"],
            "projection": "direct y integral onto native x-z, with exact overlap lengths in kpc",
            "emissivity": "retained_linear with original signed extrapolation",
            "emissivity_cell_count_domain": "native cells with positive y overlap; a partial cell counts once",
            "tracer": "binary current tr1 > 0.001 at both emission epochs",
            "brightness_factor": emission.BRIGHTNESS_FACTOR, "native_shape_zyx": list(shape),
            "axis_edges_source": grid.edge_source, "y_extent_kpc": [float(grid.y_edges[0]), float(grid.y_edges[-1])],
            "axes_sha256": {k: hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for k, a in axes.items()},
            "contract_sha256": contract_sha256, "previous_producer_sha256": previous_sha256,
            "initial_previous_producer_sha256": initial_previous_sha256, "previous_map_sha256": refs["current_0"]["sha256"],
            "protocol_config_sha256": config_ref["sha256"], "native_receipt_sha256": contract["native_input_receipt"]["sha256"],
            "native_preflight_contract_sha256": preflight_ref["sha256"], "inherited_lineage_receipt_sha256": lineage,
            "native_inputs_sha256": native_hashes, "native_input_binding": binding, "emission_inputs_sha256": digests(runtime),
            "historical_analysis_sources_sha256": digests(provenance["analysis_sources"]),
            "projector_sha256": projector_sha, "pilot_projector_sha256": PILOT_SHA256,
            "references": refs, "references_verified_in_this_job": list(raster_paths),
            "closure_against_previous": pixel_checks, "pixel_brightness_rtol": PIXEL_RTOL, "pixel_brightness_atol": 0,
            "native_full_integral_checks": integral_checks, **summary,
            "files": {product.name: {"sha256": budget._sha256(product), "size_bytes": product.stat().st_size}},
            "completed_utc": datetime.now(timezone.utc).isoformat(),
        }
        budget._stable(identities)
        (staged / "completion.json").write_text(json.dumps(completion, sort_keys=True, indent=2, allow_nan=False) + "\n")
        staged.rename(output)
    return completion


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--previous", type=Path, required=True, help="turn27 science producer directory")
    parser.add_argument("--previous-sha256", required=True, help="SHA-256 of science completion.json")
    parser.add_argument("--initial-previous-sha256", required=True, help="SHA-256 of case/0000 completion.json")
    parser.add_argument("--truth-dir", type=Path, required=True, help="Directory of privately released tracer rasters")
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory for this case and age")
    args = parser.parse_args()
    run(args.contract, args.contract_sha256, args.previous, args.previous_sha256,
        args.initial_previous_sha256, args.truth_dir, args.output)
