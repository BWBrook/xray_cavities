"""Measure the tracer sensitivity of same-cell thermal changes in the registered native apertures."""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import h5py
import numpy as np

from capture_injector_states import check_identity, sha
from measure_q031_fluxes import read_grid
from pluto_h5_level3_ambient_extract import GAMMA_GAS, UNIT_ENERGY_ERG, require_datasets


REGISTRATION_SHA = "2adb3221da4ed806f6d42f33be3d37dc2c2c7fc4039c785c68d3b4abf8a098b6"
STOCK_SHA = "b4684a7dbe097fe0bf26a276243067fe1fd0203230db4ab200f6241075f28d9d"
BANDS = ("unmarked", "positive_le_1e-4", "gt_1e-4_le_1e-3", "gt_1e-3")
CUTS = (0.0, 1e-4, 1e-3)
AXES = ("x", "y", "z", "x_edges", "y_edges", "z_edges")


def checked_bytes(path, expected_hash):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError(f"Input digest differs for {path.name}")
    return data


def summarize(bands, delivery):
    def row(values):
        count, volume, thermal, weighted = values
        return {"cell_count": int(count), "volume_kpc3": float(volume),
                "thermal_change_erg": float(thermal), "thermal_change_over_delivery": float(thermal / delivery),
                "one_minus_tr1_thermal_change_erg": float(weighted),
                "one_minus_tr1_thermal_change_over_delivery": float(weighted / delivery)}

    return {"all": row(bands.sum(axis=0)), "ambient_le_1e-4": row(bands[:2].sum(axis=0)),
            "ambient_le_1e-3": row(bands[:3].sum(axis=0)),
            "bands": {name: row(values) for name, values in zip(BANDS, bands, strict=True)}}


def measure(current, initial, grid, radii, delivery, slab_planes=8):
    """Read only current pressure/tracer and initial pressure, in contiguous z stripes."""
    outer = np.nextafter(radii["R100"], math.inf)
    inner = np.nextafter(radii["R300"], math.inf) if "R300" in radii else None
    if not (math.isfinite(outer) and outer >= 0 and math.isfinite(delivery) and delivery > 0
            and (inner is None or 0 <= inner <= outer) and slab_planes > 0):
        raise ValueError("Invalid registered radius, delivery or stripe size")
    area = grid.dy[:, None] * grid.dx[None, :]
    xy2 = grid.y[:, None]**2 + grid.x[None, :]**2
    slices = np.flatnonzero(np.sqrt(xy2.min() + grid.z**2) <= outer)
    if not len(slices):
        raise ValueError("Registered aperture contains no cells")
    # With two radii the first four bins are R300 and the second four the shell.
    bins = len(BANDS) * (1 if inner is None else 2)
    sums = np.zeros((bins, 4), dtype=np.longdouble)
    tracer_min, tracer_max = math.inf, -math.inf
    for first in range(int(slices[0]), int(slices[-1]) + 1, slab_planes):
        last = min(first + slab_planes, int(slices[-1]) + 1)
        pressure = current["prs"][first:last]
        baseline = initial["prs"][first:last]
        tracer = current["tr1"][first:last]
        for k, iz in enumerate(range(first, last)):
            radius = np.sqrt(xy2 + grid.z[iz]**2)
            inside = radius <= outer
            tr = np.asarray(tracer[k][inside], dtype=np.float64)
            p = np.asarray(pressure[k][inside], dtype=np.float64)
            p0 = np.asarray(baseline[k][inside], dtype=np.float64)
            if (not np.isfinite(tr).all() or np.any((tr < 0) | (tr > 1))
                    or not np.isfinite(p).all() or not np.isfinite(p0).all() or np.any(p <= 0) or np.any(p0 <= 0)):
                raise ValueError(f"Invalid tracer fraction or pressure inside R100 at z index {iz}")
            tracer_min = min(tracer_min, float(tr.min()))
            tracer_max = max(tracer_max, float(tr.max()))
            # Classify the stored value promoted to float64, as in the registered partition.
            category = np.searchsorted(CUTS, tr, side="left")
            if inner is not None:
                category += len(BANDS) * (radius[inside] > inner)
            volume = area[inside] * grid.dz[iz]
            thermal = (p - p0) * volume * UNIT_ENERGY_ERG / (GAMMA_GAS - 1)
            for col, weights in enumerate((None, volume, thermal, (1 - tr) * thermal)):
                sums[:, col] += np.bincount(category, weights=weights, minlength=bins)

    partitions = sums.reshape(-1, len(BANDS), sums.shape[1])
    result = {"R100": summarize(partitions.sum(axis=0), delivery)}
    if inner is not None:
        result["R300"] = summarize(partitions[0], delivery)
        result["R100_minus_R300"] = summarize(partitions[1], delivery)
    return {"apertures": result, "radii_kpc": radii, "tracer_range_in_R100": [tracer_min, tracer_max]}


def fields(h5, record, axes):
    step = record["timestep"]
    shape = require_datasets(h5, step)
    grid = read_grid(h5, shape)
    variables = h5[step]["vars"]
    if (list(shape) != record["shape"] or float(h5[step].attrs["Time"]) != record["time_code"]
            or any(variables[k].dtype != np.dtype("<f4") for k in ("prs", "tr1"))
            or any(not np.array_equal(getattr(grid, key), axes[key]) for key in AXES)):
        raise ValueError("Native shape, time, precision or axes differ from the registered snapshot")
    return variables, grid


def extract(stage, case, index, stock_file):
    if index != 30 and (case, index) != ("C-LO", 50):
        raise ValueError("Expected one of the four 30-Myr snapshots or C-LO at 50 Myr")
    registration = stage / "registration.json"
    frozen = json.loads(checked_bytes(registration, REGISTRATION_SHA))["cases"][case]
    request_dir = stage / "requests" / case
    request_file, axes_file = request_dir / "request.json", request_dir / "axes.npz"
    request = json.loads(checked_bytes(request_file, frozen["input_request_sha256"]))
    bound_axes = checked_bytes(axes_file, frozen["static_sha256"]["axes.npz"])
    if request["case"] != case:
        raise ValueError("Incorrect case in native request")
    records = [request["history"][i] for i in (0, index)]
    paths = [Path(r["native"]["resolved_path"]) for r in records]
    for i, path, record in zip((0, index), paths, records, strict=True):
        registered = frozen["snapshots"][i]
        if (record["index"] != i or registered["index"] != i or record["native"]["sha256"] != registered["native_sha256"]
                or record["fixed_receipt_sha256"] != registered["fixed_sha256"] or record["age_myr"] != registered["age_myr"]):
            raise ValueError("Native history and registered stock identity differ")
        check_identity(path, record["native"])
    snapshot = frozen["snapshots"][index]
    names = ("R100", "R300") if index == 50 else ("R100",)
    radii = {name: snapshot["apertures"][name]["raw_radius_kpc"] for name in names}
    stock_rows = csv.DictReader(io.StringIO(checked_bytes(stock_file, STOCK_SHA).decode()))
    published = {(r["aperture"], r["region"]): r for r in stock_rows if (r["case"], int(r["snapshot_index"])) == (case, index)}
    delivery = float(published["R100", "all"]["cumulative_net_gas_delivery_erg"])
    with np.load(io.BytesIO(bound_axes), allow_pickle=False) as axes, h5py.File(paths[0], "r") as zero, h5py.File(paths[1], "r") as now:
        baseline, _ = fields(zero, records[0], axes)
        current, grid = fields(now, records[1], axes)
        answer = measure(current, baseline, grid, radii, delivery)
    for path, record in zip(paths, records, strict=True):
        check_identity(path, record["native"])
    for name in names:
        for result_key, region in (("all", "all"), ("ambient_le_1e-3", "ambient")):
            found, expected = answer["apertures"][name][result_key], published[name, region]
            if (float(expected["actual_age_myr"]) != snapshot["age_myr"] or float(expected["raw_radius_kpc"]) != radii[name]
                    or float(expected["cumulative_net_gas_delivery_erg"]) != delivery
                    or found["cell_count"] != int(expected["cell_count"])
                    or not math.isclose(found["volume_kpc3"], float(expected["volume_kpc3"]), rel_tol=5e-11)
                    or abs(found["thermal_change_erg"] - float(expected["thermal_delta_erg"])) > 5e-11 * delivery):
                raise ValueError(f"Native result does not reproduce published {case}/{index}/{name}/{region}")
    return {"case": case, "index": index, "actual_age_myr": snapshot["age_myr"], "cumulative_net_gas_delivery_erg": delivery,
            "weighting": "Current tr1 applied to same-cell thermal change; one_minus_tr1 is evaluated over the indicated region.",
            "initial_sha256": records[0]["native"]["sha256"], "native_sha256": snapshot["native_sha256"],
            "fixed_receipt_sha256": snapshot["fixed_sha256"], "axes_sha256": frozen["static_sha256"]["axes.npz"],
            "registration_sha256": REGISTRATION_SHA, "published_stocks_sha256": STOCK_SHA, "reader_sha256": sha(Path(__file__)),
            **answer}


def publish(path, answer):
    payload = (json.dumps(answer, allow_nan=False, indent=2) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent) as tmp:
        tmp.write(payload)
        tmp.flush()
        try:
            os.link(tmp.name, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError(f"Existing receipt differs at {path}") from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True, help="Registered 26 November transport stage")
    parser.add_argument("--stocks", type=Path, required=True, help="Published sphere_components.csv")
    parser.add_argument("--case", required=True, choices=("C-HI", "C-LO", "G-HI", "G-LO"))
    parser.add_argument("--index", type=int, required=True, choices=(30, 50))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    publish(args.output, extract(args.stage, args.case, args.index, args.stocks))
