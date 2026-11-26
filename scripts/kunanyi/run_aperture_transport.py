"""Measure one or more registered endpoints, retaining a separately verifiable receipt for each."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import time

import h5py
import numpy as np

from aperture_surface_transport import measure_snapshot
from capture_injector_states import check_identity
from measure_q031_fluxes import read_grid
from pluto_h5_level3_ambient_extract import REQUIRED_DATASETS, require_datasets
from snapshot_energy import load_environment


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state(file, record, axes):
    step = record["timestep"]
    shape = require_datasets(file, step)
    variables = file[step]["vars"]
    if (list(shape) != record["shape"] or float(file[step].attrs["Time"]) != record["time_code"]
            or any(variables[k].dtype != np.dtype("<f4") for k in REQUIRED_DATASETS)):
        raise ValueError("Native fields, precision or time disagree with the archived input")
    grid = read_grid(file, shape)
    if any(not np.array_equal(getattr(grid, k), axes[k]) for k in axes):
        raise ValueError("Native grid differs from the signed stock measurement")
    return variables, grid


def validate_measured_geometry(result, windows, index):
    for name, records in windows.items():
        measured = result["apertures"][name]
        for role, r in records.items():
            geometry = measured["surfaces"][role]
            if (geometry["radius_kpc"] != r["raw_radius_kpc"] or geometry["cell_count"] != r["cell_count"]
                    or not math.isclose(geometry["volume_kpc3"], r["volume_kpc3"], rel_tol=5e-11, abs_tol=1e-12)
                    or geometry["sphere_fully_inside_domain"] != r["geometrically_complete_in_domain_box"]):
                raise ValueError(f"{name}/{index}/{role}: reconstructed aperture differs from native stock")
        for left, right in (("previous", "current"), ("current", "next")):
            if left not in records or right not in records:
                continue
            sweep = measured["sweeps"][f"{left}_to_{right}"]
            expected_count = records[right]["cell_count"] - records[left]["cell_count"]
            expected_volume = records[right]["volume_kpc3"] - records[left]["volume_kpc3"]
            volume_scale = max(records[left]["volume_kpc3"], records[right]["volume_kpc3"])
            if (sweep["cell_count_delta"] != expected_count
                    or abs(sweep["volume_delta_kpc3"] - expected_volume) > 5e-11 * volume_scale):
                raise ValueError(f"{name}/{index}/{left}_to_{right}: swept membership differs from stock")
            if index == 0 and any(sweep[k] != 0 for k in ("mass_g", "thermal_erg", "kinetic_erg", "gravitational_erg")):
                raise ValueError("A time-zero perturbation stock must vanish on every swept cell")


def run(registration, root, output, case, indices):
    frozen = json.loads(registration.read_bytes())["cases"][case]
    case_dir = root / "requests" / case
    request_path = case_dir / "request.json"
    if digest(request_path) != frozen["input_request_sha256"]:
        raise ValueError("Native request differs from the registered history")
    request = json.loads(request_path.read_bytes())
    if request["case"] != case or any(digest(case_dir / k) != v for k, v in frozen["static_sha256"].items()):
        raise ValueError("Case, grid or initial atmosphere changed")
    count = len(frozen["snapshots"])
    if not indices or len(set(indices)) != len(indices) or any(i not in range(count) for i in indices):
        raise ValueError("Indices must be distinct members of the registered case")
    zero = request["history"][0]
    zero_path = Path(zero["native"]["resolved_path"])
    check_identity(zero_path, zero["native"])
    with np.load(case_dir / "axes.npz", allow_pickle=False) as file:
        axes = {k: file[k] for k in ("x", "y", "z", "x_edges", "y_edges", "z_edges")}
    env = load_environment(case_dir / "atmosphere.csv")
    out = output / case
    out.mkdir(parents=True, exist_ok=True)
    shared = {"case": case, "registration_sha256": digest(registration),
              "stage_sha256": digest(root / "stage.sha256"), "initial_sha256": zero["native"]["sha256"]}
    with h5py.File(zero_path, "r") as init:
        baseline, _ = state(init, zero, axes)
        for i in indices:
            started = time.monotonic()
            frozen_row = frozen["snapshots"][i]
            record = request["history"][i]
            input_path = Path(record["native"]["resolved_path"])
            check_identity(input_path, record["native"])
            if (frozen_row["index"] != i or record["native"]["sha256"] != frozen_row["native_sha256"]
                    or record["fixed_receipt_sha256"] != frozen_row["fixed_sha256"]):
                raise ValueError(f"{case}/{i}: archived input and stock disagree")
            identity = {**shared, "index": i, "actual_age_myr": frozen_row["age_myr"],
                        "native_sha256": frozen_row["native_sha256"], "fixed_sha256": frozen_row["fixed_sha256"]}
            roles = {label: j for label, j in (("previous", i-1), ("current", i), ("next", i+1)) if 0 <= j < count}
            windows = {n: {role: frozen["snapshots"][j]["apertures"][n] for role, j in roles.items()}
                       for n in ("R100", "R300")}
            dest = out / f"snapshot_{i:04d}.json"
            if dest.exists():
                old = json.loads(dest.read_bytes())
                if old["identity"] != identity:
                    raise ValueError(f"Existing receipt belongs to another input or calculation: {dest}")
                validate_measured_geometry(old["measurement"], windows, i)
                continue
            radii = {n: {role: r["raw_radius_kpc"] for role, r in window.items()} for n, window in windows.items()}
            print(f"Measuring {case}/{i} on {len(roles)} endpoint aperture pairs", flush=True)
            with h5py.File(input_path, "r") as current:
                variables, grid = state(current, record, axes)
                measured = measure_snapshot(current=variables, initial=baseline, grid=grid, environment=env, radii=radii)
            check_identity(input_path, record["native"])
            check_identity(zero_path, zero["native"])
            validate_measured_geometry(measured, windows, i)
            payload = {"identity": identity, "measurement": measured}
            with NamedTemporaryFile(mode="w", dir=out, prefix=".partial-", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                try:
                    json.dump(payload, tmp, allow_nan=False, separators=(",", ":"))
                    tmp.write("\n")
                    tmp.flush()
                    os.link(tmp_path, dest)
                finally:
                    tmp_path.unlink(missing_ok=True)
            print(f"Completed {case}/{i} in {time.monotonic()-started:.1f} s", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("case", choices=("C-HI", "C-LO", "G-HI", "G-LO"))
    parser.add_argument("indices", nargs="+", type=int)
    args = parser.parse_args()
    run(args.stage/"registration.json", args.stage, args.stage/"results", args.case, args.indices)
