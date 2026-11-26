"""Compare native 0-degree slab row integrals with the original 90-degree emission maps.

The two projections retain the same native z rows. The archived transverse
coordinate is u = -y. Its uniform detector bins contain mean brightness over
their full width, so applying a cut within a bin is a resampling check.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np


AXES = ("horizontal_axis_kpc", "horizontal_edges_kpc", "z_axis_kpc", "z_edges_kpc")
FIELDS = {
    "current": ("current", "brightness_current_retained_linear_whole"),
    "initial": ("initial", "brightness_initial_retained_linear_whole"),
    "current_lobe_cells": ("current_lobe", "brightness_current_retained_linear_C"),
    "initial_on_current_lobe_cells": ("initial_on_current_lobe", "brightness_initial_retained_linear_C"),
}
SENSITIVITIES = ("whole_intersecting_pixels", "widen_each_edge_one_pixel", "narrow_each_edge_one_pixel",
                 "shifted_plus_u_one_pixel", "shifted_minus_u_one_pixel")
UNITS = ("case", "snapshot_index", "field", "depth", "side_view_cut")
DETAIL_COLUMNS = (*UNITS, "z_row", "z_kpc", "z_min_kpc", "z_max_kpc", "slab_row", "side_row",
                  "slab_minus_side", "slab_over_side_minus_one")
SUMMARY_COLUMNS = (*UNITS, "status", "reason", "native_z_rows", "compared_z_rows", "nonzero_reference_rows",
                   "negative_reference_rows", "negative_slab_rows", "both_zero_rows", "nonzero_slab_zero_reference_rows",
                   "total_ratio_minus_one", "dz_weighted_total_ratio_minus_one", "largest_row_ratio_minus_one",
                   "largest_row_difference_over_largest_row", "max_abs_row_difference", "max_abs_reference_row",
                   "cut_width_kpc")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_file(path, record):
    if path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
        raise ValueError(f"Size or digest mismatch for {path.name}")


def read_archive(projection, receipt_path, side_path, initial):
    index = 0 if initial else projection["snapshot_index"]
    prefix = f"{projection['case']}_{index:04d}_"
    phase = "initial" if initial else "current"
    pin = projection["initial_previous_producer_sha256" if initial else "previous_producer_sha256"]
    if sha256(receipt_path) != pin:
        raise ValueError(f"{phase} historical producer digest mismatch")
    archive = json.loads(receipt_path.read_text())
    if (archive["case"] != projection["case"] or archive["snapshot_index"] != index
            or not np.isclose(archive["actual_time_myr"], 0 if initial else projection["actual_time_myr"], atol=1e-10, rtol=0)
            or not {"0", "90"} <= archive["projection"].keys()):
        raise ValueError(f"{phase} archived case, age or views differ")
    native = {item["role"]: item["sha256"] for item in archive["provenance"]["native_inputs"]}
    expected = dict(projection["native_inputs_sha256"])
    if initial:
        expected["current_h5"] = expected["initial_h5"]
    if native != expected:
        raise ValueError(f"{phase} archived native input digests differ")
    if side_path.name != prefix + "90deg.npz":
        raise ValueError(f"Expected {prefix}90deg.npz")
    for angle in (0, 90):
        name = f"{prefix}{angle}deg.npz"
        record = archive["files"][name]
        if "references" in projection:
            ref = projection["references"][f"{phase}_{angle}"]
            if (ref["filename"], ref["sha256"], ref["size_bytes"]) != (name, record["sha256"], record["size_bytes"]):
                raise ValueError(f"{phase} {angle}-degree projection and archive identities differ")
        if angle == 0 and not initial and record["sha256"] != projection["previous_map_sha256"]:
            raise ValueError("Archived 0-degree map differs from native full-depth cross-check")
    record = archive["files"][side_path.name]
    verify_file(side_path, record)
    with np.load(side_path, allow_pickle=False) as f:
        keys = set(AXES) | {name for _, name in FIELDS.values() if name in f}
        maps = {name: f[name] for name in keys}
    require_axes(maps)
    if FIELDS["current"][1] not in maps:
        raise ValueError(f"Required archived all-gas brightness missing from {side_path.name}")
    identity = {"producer_sha256": pin, "side_map": side_path.name, "side_map_sha256": record["sha256"],
                "zero_degree_map_sha256": archive["files"][prefix + "0deg.npz"]["sha256"],
                "present_fields": sorted(maps.keys() - set(AXES))}
    return maps, identity


def require_axes(maps):
    for center_name, edge_name in (AXES[:2], AXES[2:]):
        centers, edges = maps[center_name], maps[edge_name]
        if (centers.ndim != 1 or edges.shape != (centers.size + 1,) or not centers.size
                or not np.isfinite(edges).all() or not np.isfinite(centers).all() or not np.all(np.diff(edges) > 0)
                or not np.all((edges[:-1] < centers) & (centers < edges[1:]))):
            raise ValueError(f"Invalid axis {edge_name}")


def weights(edges, lower, upper, rule):
    widths = np.diff(edges)
    pixel = widths.mean()
    if not np.allclose(widths, pixel, rtol=1e-6, atol=1e-12):
        raise ValueError("90-degree archive requires uniform transverse detector pixels")
    if rule == "whole_intersecting_pixels":
        return np.where((edges[1:] > lower) & (edges[:-1] < upper), widths, 0)
    if rule in ("shifted_plus_u_one_pixel", "shifted_minus_u_one_pixel"):
        exact = weights(edges, lower, upper, "exact")
        shifted = np.zeros_like(exact)
        if rule == "shifted_plus_u_one_pixel":
            shifted[1:] = exact[:-1]
        else:
            shifted[:-1] = exact[1:]
        return shifted
    if rule == "widen_each_edge_one_pixel":
        lower, upper = lower - pixel, upper + pixel
    elif rule == "narrow_each_edge_one_pixel":
        lower, upper = lower + pixel, upper - pixel
    elif rule != "exact":
        raise ValueError(f"Unknown side-view cut {rule}")
    return np.maximum(0.0, np.minimum(edges[1:], upper) - np.maximum(edges[:-1], lower))


def integrated_rows(field, widths, n_z):
    if field.shape != (n_z, widths.size) or not np.isfinite(field).all():
        raise ValueError("Map shape or finite-value check failed")
    return np.sum(field * widths[None, :], axis=1, dtype=np.float64)


def compare_rows(slab, side, dz):
    nonzero = side != 0
    relative = np.full(side.size, np.nan)
    relative[nonzero] = slab[nonzero] / side[nonzero] - 1
    delta = slab - side
    max_delta = np.max(np.abs(delta))
    max_side = np.max(np.abs(side))
    def ratio(total, denominator):
        return float(total / denominator - 1) if denominator != 0 else None
    return relative, delta, {
        "compared_z_rows": side.size, "nonzero_reference_rows": int(nonzero.sum()),
        "negative_reference_rows": int((side < 0).sum()), "negative_slab_rows": int((slab < 0).sum()),
        "both_zero_rows": int(((slab == 0) & ~nonzero).sum()),
        "nonzero_slab_zero_reference_rows": int(((slab != 0) & ~nonzero).sum()),
        "total_ratio_minus_one": ratio(slab.sum(), side.sum()),
        "dz_weighted_total_ratio_minus_one": ratio(np.dot(slab, dz), np.dot(side, dz)),
        "largest_row_ratio_minus_one": float(np.max(np.abs(relative[nonzero]))) if nonzero.any() else None,
        "max_abs_row_difference": float(max_delta), "max_abs_reference_row": float(max_side),
        "largest_row_difference_over_largest_row": float(max_delta / max_side) if max_side else None,
    }


def tabulate(projection, maps, current, initial, detail):
    require_axes(maps)
    z, ze = maps["z_axis_kpc"], maps["z_edges_kpc"]
    dx = np.diff(maps["horizontal_edges_kpc"])
    nz, _, nx = projection["native_shape_zyx"]
    if (len(z), len(dx)) != (nz, nx):
        raise ValueError("Native slab axes differ from the source shape")
    for archived in (current, initial):
        if archived is not None and any(not np.array_equal(archived[key], maps[key]) for key in AXES[2:]):
            raise ValueError("Archived 90-degree and native 0-degree maps do not share the exact native z rows")
    if initial is not None and any(not np.array_equal(initial[key], current[key]) for key in AXES):
        raise ValueError("Case-matched initial and evolved side views have different axes")
    u = current["horizontal_edges_kpc"]
    if len(u) != nx + 1:
        raise ValueError("Side-view pixel count differs from the archive projection convention")
    ymin, ymax = projection["y_extent_kpc"]
    bounds = {"full": (ymin, ymax), "slab30": (-30.0, 30.0), "slab10": (-10.0, 10.0)}
    for name, (lo, hi) in bounds.items():
        rec = projection["depths"][name]
        if (rec["y_min_kpc"], rec["y_max_kpc"]) != (lo, hi) or not np.isclose(rec["integrated_width_kpc"], hi - lo):
            raise ValueError(f"Slab source bounds differ for {name}")
        if name != "full" and (u[0] > -hi or u[-1] < -lo):
            raise ValueError(f"90-degree raster does not span {name}")
    summaries = []
    for name, (template, source_field) in FIELDS.items():
        source = current
        if name == "initial" and initial is not None:
            source, source_field = initial, FIELDS["current"][1]
        for depth, (lo, hi) in bounds.items():
            base = {"case": projection["case"], "snapshot_index": projection["snapshot_index"],
                    "field": name, "depth": depth, "native_z_rows": nz}
            slab = integrated_rows(maps[f"{template}_{depth}"], dx, nz)
            if source_field not in source:
                summaries.append({**base, "side_view_cut": "exact", "status": "unchecked",
                                  "reason": f"{source_field} absent from archived 90-degree emission file",
                                  "compared_z_rows": 0})
                continue
            rules = ("exact", *SENSITIVITIES) if depth != "full" and name == "current" else ("exact",)
            for rule in rules:
                cut = weights(u, -hi, -lo, rule)
                other = integrated_rows(source[source_field], cut, nz)
                relative, delta, stats = compare_rows(slab, other, np.diff(ze))
                summaries.append({**base, "side_view_cut": rule, "status": "compared",
                                  "cut_width_kpc": float(cut.sum()), **stats})
                key = (base["case"], base["snapshot_index"], name, depth, rule)
                detail.writerows((*key, i, z[i], ze[i], ze[i+1], slab[i], other[i], delta[i],
                                  relative[i] if other[i] else "") for i in range(nz))
    return summaries


def run(projection_dir, archive_receipt, side_view, initial_receipt, initial_side_view, output_dir):
    if output_dir.exists():
        raise FileExistsError(output_dir)
    receipt_path = projection_dir / "completion.json"
    projection = json.loads(receipt_path.read_text())
    if projection["status"] != "complete" or projection["view_deg"] != 0:
        raise ValueError("Expected a completed native 0-degree projection")
    if bool(initial_receipt) != bool(initial_side_view) or bool(initial_receipt) != ("initial_previous_producer_sha256" in projection):
        raise ValueError("Supply the matching initial producer and side view for a two-producer projection")
    product = projection_dir / "projections.npz"
    verify_file(product, projection["files"][product.name])
    current, current_id = read_archive(projection, archive_receipt, side_view, False)
    initial, initial_id = read_archive(projection, initial_receipt, initial_side_view, True) if initial_receipt else (None, None)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir.parent, prefix=".slab-rows-") as tmp:
        stage = Path(tmp) / "result"
        stage.mkdir()
        rows_file, summary_file = stage / "row_totals.csv.gz", stage / "row_summary.csv"
        with rows_file.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
            with io.TextIOWrapper(zipped, newline="") as stream, np.load(product, allow_pickle=False) as maps:
                writer = csv.writer(stream)
                writer.writerow(DETAIL_COLUMNS)
                summaries = tabulate(projection, maps, current, initial, writer)
        with summary_file.open("w", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=SUMMARY_COLUMNS)
            writer.writeheader()
            writer.writerows(summaries)
        u = current["horizontal_edges_kpc"]
        receipt = {
            "case": projection["case"], "snapshot_index": projection["snapshot_index"],
            "actual_time_myr": projection["actual_time_myr"], "projection_completion_sha256": sha256(receipt_path),
            "projection_sha256": projection["files"][product.name]["sha256"], "current_archive": current_id,
            "initial_archive": initial_id or current_id, "initial_field_source": "case/0000 current whole" if initial else "evolved archive initial",
            "native_z_rows": projection["native_shape_zyx"][0], "detailed_rows": sum(r["compared_z_rows"] for r in summaries),
            "side_u_extent_kpc": [float(u[0]), float(u[-1])], "native_y_extent_kpc": projection["y_extent_kpc"],
            "side_pixel_width_kpc": float(np.diff(u).mean()),
            "scope": "Signed retained-linear brightness; independent projections share the emissivity calculation. Row sums leave within-row structure untested.",
            "cuts": "Archived u = -y. Exact uses partial detector-bin widths. whole_intersecting_pixels replays the pilot's one_pixel_wider. Widening and narrowing adjust each edge by one mean pixel width. Shifts translate the exact weights one detector column without wrapping. No outside field is extrapolated.",
            "denominators": "Each archived z-row integral is the signed denominator; a zero denominator leaves the ratio blank. Max normalized difference uses the largest absolute reference row and includes zero-reference rows. total_ratio_minus_one gives equal weight to each native row as in the pilot. dz_weighted_total_ratio_minus_one integrates over physical z width.",
            "files": {p.name: {"sha256": sha256(p), "size_bytes": p.stat().st_size} for p in (rows_file, summary_file)},
            "checker_sha256": sha256(Path(__file__)),
        }
        (stage / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stage.rename(output_dir)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("projection-dir", "archive-receipt", "side-view", "initial-receipt", "initial-side-view", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=not name.startswith("initial-"))
    result = run(**vars(parser.parse_args()))
    print(f"{result['case']}/{result['snapshot_index']}: {result['detailed_rows']} row comparisons")


if __name__ == "__main__":
    main()
