"""Project the native G-HI/20 emissivity along y through three finite depths."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import h5py
import numpy as np

import build_q032_source_emission as emission
from measure_q031_fluxes import read_grid


CONTRACT_SHA = "f2239f3ea557bb08be97beb128ae0f7898aaa744c3d32e51d17dfaae05e519e4"
PRODUCER_SHA = "4ca1a4f445ae1d65d6a7aa7619ccea7745d545266656875ddfb469487affd31e"
DEPTHS = {"full": None, "slab30": 30.0, "slab10": 10.0}
FULL_REFERENCE = {
    "current": "brightness_current_retained_linear_whole",
    "initial": "brightness_initial_retained_linear_whole",
    "tracer_path": "path_C_kpc",
    "current_lobe": "brightness_current_retained_linear_C",
    "initial_on_current_lobe": "brightness_initial_retained_linear_C",
}
FACES = ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max")


def slab_widths(edges):
    edges = np.asarray(edges, dtype=np.float64)
    if edges.ndim != 1 or edges.size < 2 or not np.isfinite(edges).all() or np.any(np.diff(edges) <= 0):
        raise ValueError("Invalid native y edges")
    left, right = edges[:-1], edges[1:]
    widths, records = {}, {}
    for name, half in DEPTHS.items():
        lo, hi = (edges[0], edges[-1]) if half is None else (-half, half)
        if lo < edges[0] or hi > edges[-1]:
            raise ValueError(f"{name}: slab extends outside the native y domain")
        weight = np.maximum(0.0, np.minimum(right, hi) - np.maximum(left, lo))
        if not np.isclose(weight.sum(), hi - lo, atol=1e-12, rtol=1e-13):
            raise ValueError(f"{name}: native cell overlaps do not span the requested depth")
        partial = np.flatnonzero((weight > 0) & (weight < right - left))
        widths[name] = weight
        records[name] = {
            "y_min_kpc": float(lo), "y_max_kpc": float(hi), "integrated_width_kpc": float(weight.sum()),
            "intersecting_y_cells": int(np.count_nonzero(weight)),
            "partial_cells": [{"index_y": int(i), "lower_kpc": float(left[i]), "upper_kpc": float(right[i]),
                               "included_width_kpc": float(weight[i])} for i in partial],
        }
    return widths, records


def project(current, initial, grid, emissivity, brightness_factor):
    widths, depths = slab_widths(grid.y_edges)
    shape = (len(grid.z), len(grid.x))
    maps = {f"{field}_{name}": np.empty(shape) for name in DEPTHS for field in FULL_REFERENCE}
    volumes = {name: np.zeros(len(grid.z)) for name in DEPTHS}
    diagnostics = {name: {"current": {}, "initial": {}} for name in DEPTHS}
    faces = dict.fromkeys(FACES, 0)
    area_xy = {name: weight[:, None] * grid.dx[None, :] for name, weight in widths.items()}
    for iz, dz in enumerate(grid.dz):
        tracer = np.asarray(current["tr1"][iz], dtype=np.float64)
        if tracer.shape != (len(grid.y), len(grid.x)) or not np.isfinite(tracer).all():
            raise ValueError(f"Invalid tracer plane at z index {iz}")
        lobe = tracer > 1e-3
        for face, boundary in zip(FACES[:4], (lobe[:, 0], lobe[:, -1], lobe[0], lobe[-1])):
            faces[face] += int(np.count_nonzero(boundary))
        if iz == 0:
            faces["z_min"] = int(np.count_nonzero(lobe))
        if iz == len(grid.z) - 1:
            faces["z_max"] = int(np.count_nonzero(lobe))
        for name, weight in widths.items():
            maps[f"tracer_path_{name}"][iz] = np.sum(lobe * weight[:, None], axis=0)
            volumes[name][iz] = float(np.sum(area_xy[name][lobe]) * dz)
        for epoch, variables, lobe_field in (("current", current, "current_lobe"),
                                             ("initial", initial, "initial_on_current_lobe")):
            rho, prs = (np.asarray(variables[key][iz], dtype=np.float64) for key in ("rho", "prs"))
            if any(a.shape != lobe.shape or not np.isfinite(a).all() or np.any(a <= 0) for a in (rho, prs)):
                raise ValueError(f"{epoch}: invalid native density/pressure at z index {iz}")
            values, flags = emissivity(rho, prs)
            if values.shape != lobe.shape or not np.isfinite(values).all():
                raise ValueError(f"{epoch}: invalid retained emissivity at z index {iz}")
            within_lobe = values * lobe
            for name, weight in widths.items():
                maps[f"{epoch}_{name}"][iz] = np.sum(values * weight[:, None], axis=0) * brightness_factor
                maps[f"{lobe_field}_{name}"][iz] = np.sum(within_lobe * weight[:, None], axis=0) * brightness_factor
                counts = diagnostics[name][epoch]
                for key, flag in flags.items():
                    counts[key] = counts.get(key, 0) + int(np.count_nonzero(flag[weight > 0]))
        if iz % 64 == 0:
            print(f"G-HI/20 y projections, z plane {iz}/{len(grid.z)}", flush=True)
    if np.any(grid.z == 0):
        raise ValueError("A z cell centre is on the dividing plane between the two lobes")
    sky_area = grid.dz[:, None] * grid.dx[None, :]
    volume_by_side = {}
    for name, vol in volumes.items():
        volume_by_side[name] = {}
        for side, half in (("negative_z", grid.z < 0), ("positive_z", grid.z > 0),
                           ("both", np.ones(len(grid.z), dtype=bool))):
            value = float(vol[half].sum())
            emission.closure(f"{name}/{side} tracer volume", (maps[f"tracer_path_{name}"] * sky_area)[half].sum(), value)
            volume_by_side[name][side] = value
    if np.any(maps["tracer_path_slab10"] > maps["tracer_path_slab30"]) or np.any(
            maps["tracer_path_slab30"] > maps["tracer_path_full"]):
        raise ValueError("Tracer path lengths are not nested with emitting depth")
    return maps, {"depths": depths, "native_tracer_volume_kpc3": volume_by_side,
                  "tracer_boundary_face_cells": faces, "emissivity_cell_counts": diagnostics}


def bind(previous):
    producer_dir = previous / "G-HI_0020"
    contract_path, producer_path = previous / "input_contract.json", producer_dir / "completion.json"
    stable = []

    def check(path, digest):
        record = emission.checked_compact({"path": str(Path(path).absolute()), "sha256": digest})
        stable.append(record)
        return record

    check(contract_path, CONTRACT_SHA)
    check(producer_path, PRODUCER_SHA)
    contract, old = (json.loads(p.read_text()) for p in (contract_path, producer_path))
    ref = contract["native_input_receipt"]
    check(ref["path"], ref["sha256"])
    source = json.loads(Path(ref["path"]).read_text())
    if ((old["case"], old["snapshot_index"], old["execution_status"]) !=
            ("G-HI", 20, "completed_GHI20_source_emission_diagnostic")
            or (source["case"], source["snapshot_index"], source["status"]) !=
            ("G-HI", 20, "bound_spherical_budget_inputs")
            or old["provenance"]["native_input_receipt"]["sha256"] != ref["sha256"]):
        raise ValueError("Prior producer and native receipts do not bind the G-HI/20 snapshot")
    lineage = source["native_preflight"]["inherited_lineage"]["receipt"]
    if (lineage["sha256"] != old["provenance"]["inherited_lineage_receipt"]["sha256"]
            or source["native_preflight"]["semantic_checks"]["inherited_parent_source_restart_and_chain"] != "passed"):
        raise ValueError("G-HI native ancestry differs from the accepted emission producer")
    check(lineage["path"], lineage["sha256"])
    historic = {r["role"]: r["sha256"] for r in old["provenance"]["native_inputs"]}
    if {k: r["sha256"] for k, r in source["inputs"].items()} != historic:
        raise ValueError("Previous and native source file digests differ")
    for record in source["inputs"].values():
        check(record["path"], record["sha256"])
    for record in contract["inputs"].values():
        check(record["path"], record["sha256"])
    module_dir = Path(emission.__file__).parent
    for name, record in old["provenance"]["analysis_sources"].items():
        check(module_dir / name, record["sha256"])
    reference = producer_dir / "G-HI_0020_0deg.npz"
    check(reference, old["files"][reference.name]["sha256"])
    return contract, source, old, reference, stable


def run(previous, output):
    if output.exists():
        raise FileExistsError(output)
    contract, source, old, reference, stable = bind(previous)
    inputs = source["inputs"]
    table_paths = {k: Path(r["path"]) for k, r in contract["inputs"].items()}
    xraise = emission.native.renderer.load_module(table_paths["xraise_py"])
    tables = emission.native.load_tables(table_paths["apec_table"], table_paths["gaunt_lut"])

    def emissivity(rho, prs):
        vals, _, flags = emission.native.cell_emissivity(
            xraise=xraise, tables=tables, rho_code=rho[None], pressure_code=prs[None],
            frequency_hz=contract["frequency_hz"], redshift=contract["redshift"])
        before = vals["retained_linear_before"][0]
        return vals["retained_linear"][0], {"out_of_table": flags["any"][0],
                                           "negative": np.isfinite(before) & (before < 0), "retained_nonfinite": ~np.isfinite(before),
                                           "raw_nonfinite": flags["raw_nonfinite"][0]}

    with (h5py.File(inputs["current_h5"]["path"], "r") as current,
          h5py.File(inputs["initial_h5"]["path"], "r") as initial,
          np.load(reference, allow_pickle=False) as archive):
        grids, data = [], []
        for file, epoch in ((current, "current"), (initial, "initial")):
            step, time, shape = emission.budget._single_timestep(file, source[epoch]["timestep"], context=epoch)
            if shape != (1014, 960, 960) or not np.isclose(time, source[epoch]["time_code"], atol=1e-10, rtol=0):
                raise ValueError(f"{epoch}: native shape or time differs")
            grids.append(read_grid(file, shape, grid_file=Path(inputs["grid_file"]["path"])))
            data.append(file[step]["vars"])
        grid = grids[0]
        emission.budget._validate_grid(grid, grids[1])
        axes = {key: archive[key] for key in ("horizontal_axis_kpc", "horizontal_edges_kpc", "z_axis_kpc", "z_edges_kpc")}
        if (not np.allclose(grid.x, axes["horizontal_axis_kpc"], rtol=emission.native.TEXT_RTOL, atol=1e-10)
                or any(not np.array_equal(a, axes[k]) for a, k in
                       ((grid.x_edges, "horizontal_edges_kpc"), (grid.z, "z_axis_kpc"), (grid.z_edges, "z_edges_kpc")))):
            raise ValueError("Native grid differs from the archived 0-degree x-z grid")
        maps, summary = project(data[0], data[1], grid, emissivity, emission.BRIGHTNESS_FACTOR)
        checks = {}
        for field, key in FULL_REFERENCE.items():
            new, prior = maps[field + "_full"], archive[key]
            checks[field + "_full"] = {**emission.closure(field, new, prior), "reference_key": key,
                                       "bitwise_equal": new.tobytes() == prior.tobytes()}
            if not np.allclose(new, prior, rtol=4e-11, atol=0) or (field == "tracer_path" and not np.array_equal(new, prior)):
                raise ValueError(f"Full-depth {field} differs from the archived projection at individual pixels")
    if summary["tracer_boundary_face_cells"] != old["diagnostics"]["native_component_boundary_cell_counts"]["C"]:
        raise ValueError("Native tracer face counts differ from the archived snapshot")
    original_keys = {"negative": "retained_linear_negative", "out_of_table": "any_out_of_table",
                     "retained_nonfinite": "retained_linear_nonfinite", "raw_nonfinite": "raw_nonfinite"}
    for epoch, counts in summary["emissivity_cell_counts"]["full"].items():
        previous_counts = old["diagnostics"]["correction_domain"][epoch]
        if any(counts[k] != previous_counts[historical] for k, historical in original_keys.items()):
            raise ValueError(f"{epoch}: full-depth emissivity-domain counts differ from the archived producer")
    emission.closure("archived native lobe volume", summary["native_tracer_volume_kpc3"]["full"]["both"],
                     old["projection"]["0"]["native_volume_integrals"]["path_C_kpc"])
    actual_age = source["current"]["time_code"] / emission.budget.CODE_TIME_PER_MYR
    if not np.isclose(actual_age, old["actual_time_myr"], rtol=0, atol=1e-10):
        raise ValueError("Snapshot age differs from the archived producer")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".midplane-") as tmp:
        staged = Path(tmp) / "result"
        staged.mkdir()
        product = staged / "projections.npz"
        np.savez_compressed(product, **axes, **maps)
        emission.budget._stable(stable)
        completion = {
            "case": "G-HI", "snapshot_index": 20, "actual_time_myr": actual_age, "view_deg": 0,
            "schema_version": 1, "status": "complete", "energy_kev": 1.0,
            "frequency_hz": contract["frequency_hz"], "redshift": contract["redshift"],
            "projection": "direct y integral onto x-z, with exact overlap lengths in kpc",
            "emissivity": "retained_linear with original signed extrapolation",
            "emissivity_cell_count_domain": "native cells with positive y overlap; a partial cell counts once",
            "tracer": "binary current tr1 > 0.001 at both emission epochs",
            "brightness_factor": emission.BRIGHTNESS_FACTOR, "native_shape_zyx": list(shape),
            "axis_edges_source": grid.edge_source, "y_extent_kpc": [float(grid.y_edges[0]), float(grid.y_edges[-1])],
            "contract_sha256": CONTRACT_SHA, "previous_producer_sha256": PRODUCER_SHA,
            "previous_map_sha256": old["files"][reference.name]["sha256"],
            "native_receipt_sha256": contract["native_input_receipt"]["sha256"],
            "inherited_lineage_receipt_sha256": old["provenance"]["inherited_lineage_receipt"]["sha256"],
            "native_inputs_sha256": {k: r["sha256"] for k, r in inputs.items()},
            "emission_inputs_sha256": {k: r["sha256"] for k, r in contract["inputs"].items()},
            "projector_sha256": emission.budget._sha256(Path(__file__)),
            "closure_against_previous": checks, **summary,
            "files": {product.name: {"sha256": emission.budget._sha256(product), "size_bytes": product.stat().st_size}},
            "completed_utc": datetime.now(timezone.utc).isoformat(),
        }
        (staged / "completion.json").write_text(json.dumps(completion, sort_keys=True, indent=2, allow_nan=False) + "\n")
        staged.rename(output)
    return completion


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, required=True, help="Historical G-HI results_emission directory")
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory")
    args = parser.parse_args()
    run(args.previous, args.output)
