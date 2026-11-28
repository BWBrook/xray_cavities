"""Recover native clock geometry from two perpendicular archived tracer projections."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs/science/assets"
RELEASE = ROOT / "private_archive/turn28_scoring_2026-11-24/released"
PILOT = ROOT / ("private_archive/turn15_review_2026-11-11/inputs/stages/"
                "turn15_ghi_first20_r3/results_emission/G-HI_0020")
SEALED_TRUTH = "7ad2cc4b8d46209931aded1ec206e884963fdf7cc30d024d044fa458f8ed170a"
PILOT_RECEIPT = "4ca1a4f445ae1d65d6a7aa7619ccea7745d545266656875ddfb469487affd31e"
SIDES = ("negative_z", "positive_z")
GEOMETRY = ASSETS / "native_clocks_2026-11-28"
DELIVERY = ASSETS / "native_delivery_restatement_2026-11-21/primary_selected_ages.csv"
HISTORICAL = ASSETS / "q029_binary_native_refresh_2026-09-06/remote_analysis"
BUDGET = ASSETS / "turn15_review_2026-11-11/budgets"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verified(path, expected):
    if sha256(path) != expected:
        raise ValueError(f"Input digest mismatch at {path.name}")
    return path


def csv_rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def profile(path):
    with np.load(path, allow_pickle=False) as data:
        u_edges = data["horizontal_edges_kpc"]
        z_edges = data["z_edges_kpc"]
        length = data["path_C_kpc"]
    du = np.diff(u_edges)
    if (length.shape != (len(z_edges) - 1, len(du)) or not np.all(np.isfinite(length))
            or np.any(length < 0) or not np.all(du > 0) or not np.all(np.diff(z_edges) > 0)
            or np.count_nonzero(z_edges == 0) != 1):
        raise ValueError(f"Invalid lengths or physical edges in {path.name}")
    if np.any(length[:, [0, -1]]) or np.any(length[[0, -1], :]):
        raise ValueError(f"Tracer touches the projected frame in {path.name}")
    cell_area = length * du
    area = cell_area.sum(axis=1)
    # With no sub-bin information the true transverse centroid must lie
    # between volume-weighted bin edges.  The projected 90° axis is u=-y.
    first_moment = (cell_area * ((u_edges[1:] + u_edges[:-1]) / 2)).sum(axis=1)
    half_bin_moment = (cell_area * (du / 2)).sum(axis=1)
    return z_edges, area, first_moment, half_bin_moment


def geometry(z_edges, x_area, x_moment, y_area, u_moment, u_half_bin, side):
    dz = np.diff(z_edges)
    z = (z_edges[1:] + z_edges[:-1]) / 2
    use = z < 0 if side == "negative_z" else z > 0
    area = x_area[use]
    dz = dz[use]
    z = z[use]
    volume = np.dot(area, dz)
    other = np.dot(y_area[use], dz)
    x = np.dot(x_moment[use], dz) / volume
    y = -np.dot(u_moment[use], dz) / other
    cz = np.dot(area * z, dz) / volume
    dy = np.dot(u_half_bin[use], dz) / other
    residual = np.max(np.abs(y_area[use] - area)) / area.max()
    if (not np.all(np.isfinite([x, y, cz, dy, residual]))
            or residual > 1e-10 or abs(other / volume - 1) > 1e-10):
        raise ValueError(f"Orthogonal integrals disagree for {side}")
    xy0 = math.hypot(x, cz)
    return {
        "volume_kpc3": volume, "centroid_x_kpc": x, "centroid_y_kpc": y,
        "centroid_z_kpc": cz, "centroid_radius_kpc": math.hypot(xy0, y),
        "axial_max_section_kpc2": area.max(),
        "centroid_y_bin_bound_kpc": dy,
        "centroid_radius_lower_kpc": math.hypot(xy0, max(0, abs(y) - dy)),
        "centroid_radius_upper_kpc": math.hypot(xy0, abs(y) + dy),
        "max_section_z_kpc": z[np.argmax(area)],
        "volume_90deg_kpc3": other, "max_section_90deg_kpc2": y_area[use].max(),
        "max_row_area_difference_over_peak": residual,
    }


def run(release, pilot, output):
    seal = json.loads(verified(release / "scoring_truth_manifest.json", SEALED_TRUTH).read_text())
    exposed = json.loads(verified(pilot / "completion.json", PILOT_RECEIPT).read_text())
    binding = {u["unit_id"]: u for u in seal["units"] if u["kind"] == "science"}
    selected = {(r["case"], int(r["snapshot_index"])): r for r in csv_rows(DELIVERY)}
    if (len(selected) != 19 or len(binding) != 54
            or (exposed["case"], exposed["snapshot_index"]) != ("G-HI", 20)):
        raise ValueError("Unexpected coverage of the selected ages")
    tables = {str(DELIVERY.relative_to(ROOT)): sha256(DELIVERY)}
    inputs, results = [], []
    for case in sorted({key[0] for key in selected}):
        old_path = HISTORICAL / case / "native_energy_selected_age.csv"
        native_path = BUDGET / case / "measurements.csv"
        old = {(int(r["snapshot_index"]), r["side"]): r for r in csv_rows(old_path)
               if r["partition_method"] == "binary_threshold_1e-3"}
        native = {int(r["snapshot_index"]): r for r in csv_rows(native_path)
                  if r["speed_threshold_km_s"] == "100"}
        for file in (old_path, native_path):
            tables[str(file.relative_to(ROOT))] = sha256(file)
        for _, idx in sorted(k for k in selected if k[0] == case):
            pair = []
            for angle in (0, 90):
                uid = f"{case}_{idx:04d}_{angle}deg"
                if (case, idx) == ("G-HI", 20):
                    name = uid + ".npz"
                    path = pilot / name
                    digest = exposed["files"][name]["sha256"]
                    source = PILOT_RECEIPT
                else:
                    unit = binding[uid]
                    if (unit["case"], unit["snapshot_index"], unit["view_deg"]) != (case, idx, angle):
                        raise ValueError(f"Invalid binding at {uid}")
                    path = release / "truth" / (uid + ".truth.npz")
                    digest = unit["truth"]["sha256"]
                    source = unit["provenance"]["producer_receipt"]["sha256"]
                pair.append(profile(verified(path, digest)))
                inputs.append({"view": uid, "projection_sha256": digest,
                               "producer_receipt_sha256": source})
            (ze, a0, mx, _), (ze90, a90, mu, err) = pair
            if not np.array_equal(ze, ze90):
                raise ValueError("Perpendicular angles use different native z rows")
            sides = []
            for side in SIDES:
                measured = geometry(ze, a0, mx, a90, mu, err, side)
                historical = old[idx, side]
                age = float(selected[case, idx]["actual_age_myr"])
                if not math.isclose(float(historical["actual_time_myr"]), age, rel_tol=1e-12):
                    raise ValueError(f"Historical native age differs at {case}/{idx}/{side}")
                sides.append({"case": case, "snapshot_index": idx, "side": side, **measured,
                              "historical_q029_side_volume_kpc3": float(historical["lobe_volume_kpc3"]),
                              "historical_q029_side_enthalpy_2p5pv_erg":
                              float(historical["lobe_enthalpy_2p5pv_erg"])})
            whole = sum(row["volume_kpc3"] for row in sides)
            if not math.isclose(whole, float(native[idx]["cocoon_volume_kpc3"]), rel_tol=1e-10):
                raise ValueError(f"Native whole volume differs at {case}/{idx}")
            exact_h = float(selected[case, idx]["native_enthalpy_2p5pv_erg"])
            old_h = sum(row["historical_q029_side_enthalpy_2p5pv_erg"] for row in sides)
            if not math.isclose(old_h, float(selected[case, idx]["historical_Q029_enthalpy_2p5pv_erg"]),
                                rel_tol=1e-12):
                raise ValueError(f"Historical side enthalpies fail to close at {case}/{idx}")
            for row in sides:
                row["summed_q029_enthalpy_minus_exact_whole_fraction"] = old_h / exact_h - 1
                row["two_sides_volume_minus_exact_whole_fraction"] = (
                    whole / float(native[idx]["cocoon_volume_kpc3"]) - 1)
            results.extend(sides)
    output.mkdir(parents=True, exist_ok=True)
    table = output / "ortho_geometry.csv"
    with table.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    manifest = {
        "cases_ages": len(selected), "hemispheres": len(results),
        "binary_selection": "tr1 > 0.001 on current native cells; full line of sight and both signs of z",
        "volume_section": "A(z)=sum(path*du), V=sum(A*dz); S is maximum native axial-normal A(z) on that side",
        "centroid": "0-degree native edge midpoints for x,z; 90-degree u=-y with volume-weighted bin centres and a rigorous half-bin error bound",
        "pressure_check": "Historical Q029 side pressure integrals use their original quadrature. The signed historical summed enthalpy difference is relative to the current exact whole-lobe turn-15 integral.",
        "frame_check": "All bounding image rows and columns contain zero tracer for both views in each case-age",
        "sha256": {"released_truth_manifest": SEALED_TRUTH, "exposed_ghi20_receipt": PILOT_RECEIPT,
                   "ortho_geometry_csv": sha256(table), "source_tables": tables},
        "inputs": inputs,
    }
    (output / "ortho_geometry_sources.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=RELEASE)
    parser.add_argument("--pilot", type=Path, default=PILOT)
    parser.add_argument("--output", type=Path, default=GEOMETRY)
    args = parser.parse_args()
    print(f"{len(run(args.release, args.pilot, args.output))} native hemispheres")
