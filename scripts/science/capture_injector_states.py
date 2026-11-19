"""Read native injector stencils or reduce whole-grid tracer and gravity on the existing dumps."""

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np

from measure_q031_fluxes import Grid, derive_control_box, parse_pluto_parameters, read_grid
from pluto_h5_level3_ambient_extract import REQUIRED_DATASETS, require_datasets
from snapshot_energy import write_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_identity(path, bound):
    stat = path.stat()
    actual = (str(path.resolve()), stat.st_size, stat.st_ino, stat.st_ctime_ns, stat.st_mtime_ns)
    expected = tuple(bound[name] for name in ("resolved_path", "size_bytes", "inode", "ctime_ns", "mtime_ns"))
    if actual != expected:
        raise ValueError(f"Native file identity changed: {path.name}")


def select_history(history, selection):
    if selection == "all":
        return history
    indices = [int(value) for value in selection.split(",")]
    if len(set(indices)) != len(indices) or any(i < 0 or i >= len(history) for i in indices):
        raise ValueError("Indices must be distinct members of the bound history")
    return [history[i] for i in indices]


def capture(request_dir, output, mode, selection):
    from measure_outer_tracer_gravity import measure_snapshot

    request_path = request_dir / "request.json"
    request = json.loads(request_path.read_text())
    request_sha = sha(request_path)
    for name, expected in request["static_sha256"].items():
        if sha(request_dir / name) != expected:
            raise ValueError(f"Changed analysis input: {name}")
    here = Path(__file__).resolve().parent
    modules = ("capture_injector_states.py", "measure_outer_tracer_gravity.py", "measure_q031_fluxes.py",
               "select_common_age_hdf5.py", "snapshot_energy.py", "pluto_h5_level3_ambient_extract.py")
    code_sha = {name: sha(here / name) for name in modules}
    parameters = parse_pluto_parameters(request_dir / "pluto.ini")
    centre = tuple(parameters[f"JET_X{k}O"] for k in (1, 2, 3))
    if centre != (0., 0., 0.) or parameters["JET_ROTATION_ANGLE"] != 0 or parameters["JET_INJECTION_HEIGHT"] != .75:
        raise ValueError("The fixed 0.75-kpc central sphere is required")
    case = request["case"]
    with np.load(request_dir / "axes.npz", allow_pickle=False) as arrays:
        centres = tuple(arrays[axis] for axis in "xyz")
        edges = tuple(arrays[axis + "_edges"] for axis in "xyz")
    grid = Grid(*centres, *(np.diff(axis) for axis in edges), *edges)
    boxes = {padding: derive_control_box(grid, injection_height_kpc=.75, centre_kpc=centre, padding_cells=padding)
             for padding in (1, 2, 4)}
    box = boxes[4]
    if box.source_cell_count != 14328:
        raise ValueError("Source grid differs from the audited production grid")
    out = output / case / mode
    out.mkdir(parents=True, exist_ok=True)
    bounds = [(box.i0, box.i1+1), (box.j0, box.j1+1), (box.k0, box.k1+1)]
    slices = tuple(slice(start, end) for start, end in reversed(bounds))
    for item in select_history(request["history"], selection):
        index = item["index"]
        dest = out / f"snapshot_{index:04d}.json"
        npz = out / f"patch_{index:04d}.npz"
        native = item["native"]
        path = Path(native["resolved_path"])
        identity = dict(case=case, index=index, mode=mode, time_code=item["time_code"], age_myr=item["age_myr"],
                        historical_native_sha256=native["sha256"], fixed_receipt_sha256=item["fixed_receipt_sha256"],
                        request_sha256=request_sha, analysis_sha256=code_sha)
        check_identity(path, native)
        if dest.exists():
            old = json.loads(dest.read_text())
            if (any(old.get(k) != v for k, v in identity.items())
                    or (mode == "patch" and sha(npz) != old["patch_sha256"])):
                raise ValueError(f"Existing result has a different identity: {dest}")
            continue
        with h5py.File(path, "r") as data:
            timestep = item["timestep"]
            shape = require_datasets(data, timestep)
            variables = data[timestep]["vars"]
            if (list(shape) != item["shape"] or shape != tuple(len(s) for s in reversed(centres))
                    or float(data[timestep].attrs["Time"]) != item["time_code"]
                    or any(variables[k].dtype != np.dtype("<f4") for k in REQUIRED_DATASETS)):
                raise ValueError(f"Shape, precision or time mismatch at {case}/{index}")
            if mode == "patch":
                arrays = {field: variables[field][slices] for field in REQUIRED_DATASETS}
                for d, (axis, (start, end)) in enumerate(zip("xyz", bounds, strict=True)):
                    for key, group, nodes, extra in (
                            (axis, "cell_coords", centres, 0), (axis+"_edges", "node_coords", edges, 1)):
                        cut = slice(start, end + extra)
                        line = list((shape[0]//2, shape[1]//2, shape[2]//2))
                        line[2-d] = cut
                        values = data[f"{group}/{axis.upper()}"][tuple(line)]
                        if not np.array_equal(values, nodes[d][cut]):
                            raise ValueError(f"Native patch coordinates changed on {axis}")
                        arrays[key] = values
                temp = npz.with_suffix(".tmp.npz")
                np.savez_compressed(temp, **arrays)
                temp.replace(npz)
                result = dict(patch_sha256=sha(npz), bounds_xyz=bounds)
            else:
                native_grid = read_grid(data, shape)
                for key in ("x", "y", "z", "x_edges", "y_edges", "z_edges"):
                    if not np.array_equal(getattr(grid, key), getattr(native_grid, key)):
                        raise ValueError(f"Native full grid changed on {key}")
                result = measure_snapshot(variables, native_grid, boxes, request_dir / "atmosphere.csv",
                                          labelled_power_erg_s=2*parameters["JET_PWR"])
        check_identity(path, native)
        write_json(dest, {**identity, **result})
        print(f"{case} {mode} {index} complete", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("mode", choices=("patch", "outer"))
    parser.add_argument("--indices", default="all", help="all, or comma-separated output indices")
    args = parser.parse_args()
    capture(args.request_dir, args.output, args.mode, args.indices)
