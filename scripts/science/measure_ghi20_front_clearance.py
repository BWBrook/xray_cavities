"""Measure the physical gap between the plotted tracer and compression-front edges."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

import compare_compressive_front as front
from measure_ghi20_front_constraint import OUTPUT, array_hash
from source_excluded_inputs import verify_archive


def edge_gaps(tracer, inside, grid):
    if np.any(tracer & ~inside):
        raise ValueError("A tracer pixel lies outside the supplied front")
    rim = front.segments(inside, grid)
    corners = np.unique(np.vstack((rim.lo[rim.exterior], rim.hi[rim.exterior])), axis=0)
    tree = cKDTree(corners)
    lobe = front.segments(tracer, grid)
    for side, half in zip(front.SIDES, (grid.z[lobe.row] < 0, grid.z[lobe.row] > 0), strict=True):
        edges = lobe.exterior & half
        vertices = np.unique(np.vstack((lobe.lo[edges], lobe.hi[edges])), axis=0)
        # Both contours follow elementary edges of the same rectilinear grid.
        # Even for parallel edges, a closest pair occurs at two vertices.
        distance, nearest = tree.query(vertices)
        i = distance.argmin()
        u, z = vertices[i]
        uf, zf = corners[nearest[i]]
        yield {"hemisphere": side, "contour_gap_kpc": distance[i],
               "tracer_u_kpc": u, "tracer_z_kpc": z, "front_u_kpc": uf, "front_z_kpc": zf}


def measure(exposed_dir, front_dir):
    receipt_path = OUTPUT / "receipt.json"
    verify_archive(receipt_path, "44862deed262a31551df261b96242c6676d7dbc6b20a77ecc3856151d633b489")
    receipt = json.loads(receipt_path.read_text())
    geometry = OUTPUT / "front_geometry.csv"
    verify_archive(geometry, receipt["products"][geometry.name])
    with geometry.open(newline="") as f:
        bounds = {(int(r["view_deg"]), r["front"]): r for r in csv.DictReader(f)}
    rows = []
    for angle in front.ANGLES:
        unit = f"G-HI_0020_{angle}deg"
        obs_path, native_path = (d / f"{unit}.npz" for d in (exposed_dir, front_dir))
        binding = receipt["bindings"][unit]
        verify_archive(obs_path, binding["observer_sha256"])
        verify_archive(native_path, binding["native_front_sha256"])
        with np.load(obs_path, allow_pickle=False) as obs, np.load(native_path, allow_pickle=False) as native:
            tracer = obs["path_C_kpc"] > 0
            grid = front.Grid(*front.validate_axes(obs, tracer.shape))
            if (array_hash(tracer) != binding["tracer_footprint_sha256"]
                    or any(not np.array_equal(obs[k], native[k]) for k in front.AXES)):
                raise ValueError(f"{unit}: tracer footprint or projection axes differ")
            for name, field in front.ARMS.items():
                inside = native[field] > 0
                reference = bounds[angle, name]
                if reference["status"] != "closed" or array_hash(inside) != reference["inside_sha256"]:
                    raise ValueError(f"{unit}/{name}: contour differs from the scored enclosure")
                rows.extend({"view_deg": angle, "front": name, **r} for r in edge_gaps(tracer, inside, grid))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exposed-dir", type=Path, required=True)
    parser.add_argument("--front-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT / "tracer_front_clearance.csv")
    args = parser.parse_args()
    front.write_rows(args.output, measure(args.exposed_dir, args.front_dir))
