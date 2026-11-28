"""Reduce each native tracer lobe to the geometry and pressure integrals used for cavity clocks."""
import argparse
import io
import json
import math
from pathlib import Path

import h5py
import numpy as np

from capture_injector_states import check_identity, sha
from measure_ambient_tracer_sensitivity import REGISTRATION_SHA, checked_bytes, fields, publish
from pluto_h5_level3_ambient_extract import UNIT_ENERGY_ERG


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
INDICES = (10, 20, 30, 40, 50)
TRACER_CUT = 1e-3


def measure(variables, grid, slab_planes=8):
    """Integrate full finite-volume cells; count each projected column only once per side."""
    shape = (len(grid.z), len(grid.y), len(grid.x))
    if slab_planes < 1 or any(variables[name].shape != shape for name in ("prs", "tr1")):
        raise ValueError("Invalid native field shape or stripe size")
    area = grid.dy[:, None] * grid.dx[None, :]
    sections = {side: [] for side in ("negative_z", "positive_z")}
    columns = {side: np.zeros(area.shape, dtype=bool) for side in sections}
    for first in range(0, shape[0], slab_planes):
        last = min(first + slab_planes, shape[0])
        tracer = variables["tr1"][first:last]
        if not (tracer.min() >= 0 and tracer.max() <= 1):
            raise ValueError(f"Nonfinite or out-of-range tracer in z planes {first}–{last-1}")
        selected = np.asarray(tracer, dtype=np.float64) > TRACER_CUT
        if not selected.any():
            continue
        pressure = variables["prs"][first:last]
        for k, inside in enumerate(selected):
            iy, ix = np.nonzero(inside)
            if not len(ix):
                continue
            iz = first + k
            side = "negative_z" if grid.z[iz] < 0 else "positive_z"
            columns[side] |= inside
            p = np.asarray(pressure[k, iy, ix], dtype=np.float64)
            if not np.isfinite(p).all() or np.any(p <= 0):
                raise ValueError(f"Invalid lobe pressure at z index {iz}")
            dA = area[iy, ix]
            S = float(np.sum(dA))
            dV = dA * grid.dz[iz]
            sections[side].append((iz, len(ix), S, S * grid.dz[iz],
                                   np.dot(grid.x[ix], dV), np.dot(grid.y[iy], dV),
                                   np.dot(p, dV)))

    sides = {}
    for side, planes in sections.items():
        if not planes:
            raise ValueError(f"No tracer-selected cells in the {side} hemisphere")
        iz, counts, areas, volumes, mx, my, pv = zip(*planes, strict=True)
        volume = math.fsum(volumes)
        z = [float(grid.z[i]) for i in iz]
        cx = math.fsum(mx) / volume
        cy = math.fsum(my) / volume
        cz = math.fsum(h * v for h, v in zip(z, volumes, strict=True)) / volume
        pv_erg = math.fsum(pv) * UNIT_ENERGY_ERG
        union = columns[side]
        walls = (("x_min", union[:, 0].any()), ("x_max", union[:, -1].any()),
                 ("y_min", union[0, :].any()), ("y_max", union[-1, :].any()),
                 ("z_min", iz[0] == 0), ("z_max", iz[-1] == shape[0] - 1))
        sides[side] = {
            "cell_count": sum(counts), "volume_kpc3": volume,
            "centroid_x_kpc": cx, "centroid_y_kpc": cy, "centroid_z_kpc": cz,
            "centroid_radius_kpc": math.hypot(cx, cy, cz),
            "centroid_angle_to_outward_axis_deg": math.degrees(math.atan2(math.hypot(cx, cy), abs(cz))),
            "pv_erg": pv_erg, "enthalpy_2p5pV_erg": 2.5 * pv_erg, "enthalpy_4pV_erg": 4 * pv_erg,
            "axial_max_section_kpc2": max(areas), "axial_union_area_kpc2": float(np.sum(area[union])),
            "wall_faces": [face for face, hit in walls if hit],
            "sections": {"z_index": list(iz), "z_kpc": z, "dz_kpc": [float(grid.dz[i]) for i in iz],
                         "area_kpc2": list(areas)},
        }
    return sides


def extract(stage, case, index):
    if case not in CASES or index not in INDICES or (case, index) == ("G-HI", 50):
        raise ValueError("Expected one of the 19 registered native clock case-ages")
    frozen = json.loads(checked_bytes(stage / "registration.json", REGISTRATION_SHA))["cases"][case]
    request_dir = stage / "requests" / case
    request = json.loads(checked_bytes(request_dir / "request.json", frozen["input_request_sha256"]))
    axes_sha = frozen["static_sha256"]["axes.npz"]
    bound_axes = checked_bytes(request_dir / "axes.npz", axes_sha)
    record, snapshot = request["history"][index], frozen["snapshots"][index]
    if (request["case"] != case or record["index"] != index or snapshot["index"] != index
            or record["age_myr"] != snapshot["age_myr"]
            or record["native"]["sha256"] != snapshot["native_sha256"]
            or record["fixed_receipt_sha256"] != snapshot["fixed_sha256"]):
        raise ValueError("Native input and registered history differ")
    native = record["native"]
    path = Path(native["resolved_path"])
    check_identity(path, native)
    with np.load(io.BytesIO(bound_axes), allow_pickle=False) as axes, h5py.File(path, "r") as h5:
        variables, grid = fields(h5, record, axes)
        sides = measure(variables, grid)
    check_identity(path, native)
    return {
        "case": case, "index": index, "actual_age_myr": record["age_myr"], "time_code": record["time_code"],
        "shape_zyx": record["shape"], "timestep": record["timestep"],
        "native_sha256": native["sha256"], "fixed_receipt_sha256": snapshot["fixed_sha256"],
        "registration_sha256": REGISTRATION_SHA, "input_request_sha256": frozen["input_request_sha256"],
        "axes_sha256": axes_sha, "reader_sha256": sha(Path(__file__)),
        "quadrature": {
            "selection": "Full-domain cells with stored tr1 promoted to float64 > 0.001, split by z centre (<0 or >=0).",
            "volume": "Full native node-coordinate dx dy dz; volume centroid uses native cell centres.",
            "pressure": "Sum of native cell pressure times cell volume, converted to erg.",
            "axial_sections": "Cross-sections are normal to z. The union counts each selected xy column once per side.",
            "edge_source": grid.edge_source, "max_center_edge_residual_kpc": grid.max_center_edge_residual_kpc,
            "unit_energy_erg": UNIT_ENERGY_ERG,
        },
        "sides": sides,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True, help="Registered 26 November transport stage")
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--index", type=int, choices=INDICES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    publish(args.output, extract(args.stage, args.case, args.index))
