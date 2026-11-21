"""Compare gravitational work, spatial storage and the near-injector energy balance."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np

from compare_injector_gravity import patch_terms
from measure_injector_faces import FIELDS, METHODS, _face_flux, _frame, _shock_mask, _slope
from measure_outer_tracer_gravity import SOLVER_LENGTH_CM
from measure_q031_fluxes import parse_pluto_parameters
from pluto_h5_level3_ambient_extract import UNIT_DENSITY_CGS as D, UNIT_LENGTH_CM as L, UNIT_VELOCITY_CMS as V
from snapshot_energy import SECONDS_PER_MYR, load_environment, sha256_file, write_rows


ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "docs/science/assets/production_injector_histories_2026-11-21"
PRIVATE = ROOT / "private_archive"
CASES = {"C-HI": 50, "G-HI": 47}
PRIMARY = "linear_snapshot_flags"
RULES = {"left": 0.0, "trapezoid": 0.5, "right": 1.0}
BOUNDARIES = ("outer_active_cell", "linear_to_boundary_face")
TRACER_CLASSES = ("ambient_at_both", "intermediate_at_both", "jet_rich_at_both", "changed_class")


def published():
    receipt = json.loads((PUBLIC / "verification.json").read_text())
    path = PUBLIC / "history_tables.zip"
    if sha256_file(path) != receipt["public_zip_sha256"]:
        raise ValueError("unexpected source archive")
    gravity = "comparison/flagged_sphere_gravity_intervals.csv"
    names = [gravity, *[f"native/summary/{case}/injector_snapshot_rates.csv" for case in CASES]]
    tables = {}
    with zipfile.ZipFile(path) as archive:
        for name in names:
            binary = archive.read(name)
            if hashlib.sha256(binary).hexdigest() != receipt["public_member_sha256"][name]:
                raise ValueError(f"archived input mismatch: {name}")
            tables[name] = list(csv.DictReader(io.StringIO(binary.decode())))
    intervals = {
        (r["case"], int(r["end_index"]), r["injector_method"], r["boundary_method"], r["rule"]): r
        for r in tables[gravity]
        if r["case"] in CASES
    }
    rates = {
        (case, int(r["index"]), r["method"]): r
        for case in CASES
        for r in tables[f"native/summary/{case}/injector_snapshot_rates.csv"]
        if r["region"] == "net"
    }
    if len(intervals) != (50 + 47) * 24 - 8 or len(rates) != (51 + 48) * 4:
        raise ValueError("incomplete high-power histories")
    return intervals, rates


def windows(last):
    return [(i - 1, i) for i in range(1, last + 1)] + [(10, 12)]


def work_ratios(intervals):
    rows = []
    for case, last in CASES.items():
        for a, b in windows(last):
            points = {}
            for method in METHODS:
                for face in BOUNDARIES:
                    for rule in RULES:
                        keys = [(case, i, method, face, rule) for i in range(a + 1, b + 1)]
                        if not all(k in intervals for k in keys):
                            continue
                        rates = [intervals[k] for k in keys]
                        label = math.fsum(float(r["labelled_energy_erg"]) for r in rates)

                        def integrate(field):
                            return (
                                math.fsum(float(r[field]) * float(r["labelled_energy_erg"]) for r in rates)
                                / label
                            )

                        direct = integrate("direct_net_work_over_label")
                        gross = integrate("direct_inward_motion_work_over_label") - integrate(
                            "direct_outward_motion_work_over_label"
                        )
                        work_gap = integrate("direct_minus_continuity_work_over_label")
                        deficit = integrate("outside_total_residual_over_label")
                        points[method, face, rule] = (
                            label,
                            direct,
                            gross,
                            deficit,
                            abs(direct / deficit),
                            gross / abs(deficit),
                            work_gap,
                        )
            label, direct, gross, residual, ratio, grossratio, gap = points[
                PRIMARY, "outer_active_cell", "trapezoid"
            ]
            rows.append(
                dict(
                    case=case,
                    start_index=a,
                    end_index=b,
                    n_matched_methods=len(points),
                    labelled_energy_erg=label,
                    signed_direct_work_over_label=direct,
                    gross_absolute_work_over_label=gross,
                    exterior_residual_over_label=residual,
                    abs_direct_over_abs_residual=ratio,
                    method_min_abs_direct_over_abs_residual=min(v[4] for v in points.values()),
                    method_max_abs_direct_over_abs_residual=max(v[4] for v in points.values()),
                    gross_absolute_work_over_abs_residual=grossratio,
                    method_max_gross_absolute_work_over_abs_residual=max(v[5] for v in points.values()),
                    direct_minus_continuity_work_over_label=gap,
                    abs_direct_minus_continuity_over_abs_residual=abs(gap / residual),
                )
            )
    return rows


def storage_partitions(record):
    regions = record["regions"]
    walls = record["speed_apertures"]
    if not all(walls[key]["available"] for key in ("R300", "R100")):
        return []
    r300, r100 = (walls[key]["raw_radius_kpc"] for key in ("R300", "R100"))
    if r300 > r100:
        raise ValueError("transposed speed apertures")
    columns = (
        "cell_count",
        "mass_delta_g",
        "thermal_delta_erg",
        "kinetic_delta_erg",
        "gravitational_delta_erg",
        "total_delta_erg",
    )
    out = []
    for name, outer, inner in (
        ("within_R300", "R300", None),
        ("R300_to_R100", "R100", "R300"),
        ("grid_outside_R100", "whole_grid", "R100"),
    ):
        for region in ("cocoon", "ambient"):
            src = regions[outer]["partitions"][region]
            sub = regions[inner]["partitions"][region] if inner else None
            vals = {f: src[f] - (sub[f] if sub else 0) for f in columns}
            if vals["cell_count"] < 0:
                raise ValueError("nested tracer partitions inconsistent")
            out.append(
                dict(
                    case=record["case"],
                    index=record["snapshot_index"],
                    age_myr=record["actual_time_myr"],
                    zone=name,
                    tracer_class=region,
                    r300_kpc=r300,
                    r100_kpc=r100,
                    complete_R100=walls["R100"]["geometrically_complete_in_domain_box"],
                    initial_to_current_storage_over_label=vals["total_delta_erg"]
                    / record["labelled_input_erg"],
                    **vals,
                )
            )
    for f in columns:
        total = regions["whole_grid"]["partitions"]["all"][f]
        scale = max(math.fsum(abs(r[f]) for r in out), abs(total), 1.0)
        if not math.isclose(math.fsum(r[f] for r in out), total, rel_tol=0.0, abs_tol=2.0e-11 * scale):
            raise ValueError(f"partition closure differs for {f}")
    return out


def patch_geometry(arrays, environment):
    xyz = [arrays[d].astype(float) for d in "xyz"]
    nodes = [arrays[d + "_edges"].astype(float) for d in "xyz"]
    widths = [np.diff(e) for e in nodes]
    if any(not np.allclose(w, 0.05, rtol=2.0e-6, atol=0.0) for w in widths):
        raise ValueError("near-injector stencil requires the uniform 0.05-kpc core")
    z, y, x = np.ix_(*xyz[::-1])
    r2 = x * x + y * y + z * z
    shells = np.full(r2.shape, -1, dtype=np.int8)
    shells[r2 <= 0.85**2] = 2
    shells[r2 <= 0.80**2] = 1
    shells[r2 <= 0.75**2] = 0
    valid = shells >= 0
    if np.sum(shells == 0) != 14328:
        raise ValueError("native flagged mask differs")
    cell_phi = environment.potential_at_radius(np.sqrt(r2) * L) / V**2
    volume = widths[2][:, None, None] * widths[1][None, :, None] * widths[0][None, None, :]
    interfaces = []
    for d in range(3):
        dim = 2 - d
        left, right = [slice(None)] * 3, [slice(None)] * 3
        left[dim], right[dim] = slice(None, -1), slice(1, None)
        i = np.column_stack(np.where(valid[tuple(left)] | valid[tuple(right)]))
        step = np.zeros(3, dtype=int)
        step[dim] = 1
        j = i + step
        if i[:, dim].min() < 1 or j[:, dim].max() + 1 >= valid.shape[dim]:
            raise ValueError("a measured face lacks its slope stencil")
        face_r2 = nodes[d][j[:, dim]] ** 2
        area = np.ones(len(i))
        for tang in set(range(3)) - {d}:
            k = i[:, 2 - tang]
            face_r2 += ((nodes[tang][k] + nodes[tang][k + 1]) * 0.5) ** 2
            area *= widths[tang][k]
        phi = environment.potential_at_radius(np.sqrt(face_r2) * L) / V**2
        interfaces.append((tuple((i - step).T), tuple(i.T), tuple(j.T), tuple((j + step).T), area, phi))
    return widths, shells, cell_phi, volume, interfaces


def cell_budgets(arrays, geom):
    widths, shells, phi, volume, interfaces = geom
    state = np.stack([arrays[f].astype(float) for f in FIELDS], axis=-1)
    shock = _shock_mask(state, widths)
    divergence = {m: np.zeros(shells.shape) for m in METHODS}
    for d, (im, i, j, jp, area, face_phi) in enumerate(interfaces):
        l, r = state[i], state[j]
        pl = _frame(l + 0.5 * _slope(state[im], l, r), d, 1.0)
        pr = _frame(r - 0.5 * _slope(l, r, state[jp]), d, 1.0)
        flag = shock[i] | shock[j]
        for m in METHODS:
            left, right = (
                (_frame(l, d, 1.0), _frame(r, d, 1.0)) if m == "first_order_snapshot_flags" else (pl, pr)
            )
            switch = (
                np.ones_like(flag)
                if m == "linear_hll"
                else np.zeros_like(flag)
                if m == "linear_hllc"
                else flag
            )
            flux, _, _ = _face_flux(left, right, switch)
            face = (flux["gas_energy"] + face_phi * flux["mass"]) * area * (D * L**2 * V**3)
            divergence[m][i] += face
            divergence[m][j] -= face
    rho = state[..., 0]
    energy = (
        (1.5 * state[..., 1] + rho * (0.5 * np.sum(state[..., 2:5] ** 2, axis=-1) + phi))
        * volume
        * (D * L**3 * V**2)
    )
    return energy, divergence, state[..., 5]


def case_budgets(case, native, requests, fixed_root, intervals, source_rates):
    last = CASES[case]
    local, classes, wide = [], [], []
    req_dir = requests / case
    request = json.loads((req_dir / "request.json").read_text())
    environment = load_environment(req_dir / "atmosphere.csv")
    if environment.source_sha256 != request["static_sha256"]["atmosphere.csv"]:
        raise ValueError("unmatched atmosphere")
    radial_force = np.loadtxt(req_dir / "atmosphere.csv", usecols=(0, 5))
    radial_force[:, 0] /= SOLVER_LENGTH_CM
    ini = req_dir / "pluto.ini"
    if sha256_file(ini) != request["static_sha256"]["pluto.ini"]:
        raise ValueError("unmatched injector configuration")
    power = 2 * parse_pluto_parameters(ini)["JET_PWR"]
    geom = axes = previous = None
    geometry_error = 0.0
    for idx in range(last + 1):
        item = request["history"][idx]
        current_time = item["age_myr"]
        path = native / case / "patch" / f"patch_{idx:04d}.npz"
        source = source_rates[case, idx, PRIMARY]
        if source["patch_sha256"] != sha256_file(path) or float(source["age_myr"]) != current_time:
            raise ValueError(f"patch identity or time differs: {case}/{idx}")
        if idx in (10, 11, 12, 29, 30):
            fixed = fixed_root / f"fixed_{case}_full" / f"snapshot_{idx:04d}.json"
            if sha256_file(fixed) != item["fixed_receipt_sha256"]:
                raise ValueError(f"fixed budget identity differs: {case}/{idx}")
            record = json.loads(fixed.read_text())
            if (
                record["actual_time_myr"] != current_time
                or record["case"] != case
                or record["snapshot_index"] != idx
            ):
                raise ValueError("misaligned regional stock")
            wide.extend(storage_partitions(record))
        with np.load(path, allow_pickle=False) as arrays:
            coords = [arrays[d + suffix] for d in "xyz" for suffix in ("", "_edges")]
            if geom is None:
                geom = patch_geometry(arrays, environment)
                axes = coords
            elif not all(np.array_equal(a, b) for a, b in zip(axes, coords, strict=True)):
                raise ValueError(f"grid changed at {case}/{idx}")
            stock, flux, tracer = cell_budgets(arrays, geom)
            core_work, mid_work, outer_work = (
                np.asarray(patch_terms(arrays, environment, radial_force, radius)[2])
                for radius in (0.75, 0.80, 0.85)
            )
            gravity = {
                "0.75_to_0.80": mid_work - core_work,
                "0.80_to_0.85": outer_work - mid_work,
                "0.75_to_0.85": outer_work - core_work,
            }
        shells = geom[1]
        for m in METHODS:
            emitted = float(np.sum(flux[m], where=shells == 0)) / power
            expected = float(source_rates[case, idx, m]["total_energy_over_label"])
            geometry_error = max(geometry_error, abs(emitted - expected))
            if not math.isclose(emitted, expected, rel_tol=2.0e-12, abs_tol=2.0e-12):
                raise ValueError(
                    f"cell-by-cell inner transport differs from calibrated injector: {case}/{idx}/{m}"
                )
        if previous is not None:
            t0, old_stock, old_flux, old_tracer, old_gravity = previous
            dt = (current_time - t0) * SECONDS_PER_MYR
            label = float(
                intervals[case, idx, PRIMARY, "outer_active_cell", "trapezoid"]["labelled_energy_erg"]
            )
            change = (stock - old_stock) / label
            old_class, new_class = (
                np.where(t <= 0.001, 0, np.where(t >= 0.999, 2, 1)) for t in (old_tracer, tracer)
            )
            classes_at_endpoints = np.where(old_class == new_class, new_class, 3)
            strong_mixture = (old_tracer > 0.1) & (old_tracer < 0.9) & (tracer > 0.1) & (tracer < 0.9)
            masks = {"0.75_to_0.80": shells == 1, "0.80_to_0.85": shells == 2, "0.75_to_0.85": shells > 0}
            subsets = {
                (zone, kind): mask & (classes_at_endpoints == code)
                for zone, mask in masks.items()
                for code, kind in enumerate(TRACER_CLASSES)
            }
            estimates = {key: [] for key in subsets}
            primary_classes = {}
            for m in METHODS:
                for rule, w in RULES.items():
                    transport = ((1.0 - w) * old_flux[m] + w * flux[m]) * (dt / label)
                    inner_sum = 0.0
                    for zone, mask in masks.items():
                        ds = float(np.sum(change, where=mask))
                        ft = float(np.sum(transport, where=mask))
                        residual = ds + ft
                        grav = ((1.0 - w) * old_gravity[zone] + w * gravity[zone]) * (dt / label)
                        if zone == "0.75_to_0.85":
                            if not math.isclose(residual, inner_sum, rel_tol=1.0e-12, abs_tol=1.0e-12):
                                raise ValueError("adjacent fixed annuli do not close")
                        else:
                            inner_sum += residual
                        local.append(
                            dict(
                                case=case,
                                start_index=idx - 1,
                                end_index=idx,
                                zone=zone,
                                method=m,
                                rule=rule,
                                label=label,
                                storage=ds,
                                transport=ft,
                                residual=residual,
                                gravity_net=grav[2],
                                gravity_gross=grav[0] - grav[1],
                            )
                        )
                        subtotal = 0.0
                        for name in TRACER_CLASSES:
                            cells = subsets[zone, name]
                            dsub = float(np.sum(change, where=cells))
                            fsub = float(np.sum(transport, where=cells))
                            part = dsub + fsub
                            subtotal += part
                            estimates[zone, name].append((part, part / residual))
                            if m == PRIMARY and rule == "trapezoid":
                                strong_cells = cells & strong_mixture
                                strong_part = float(
                                    np.sum(change, where=strong_cells) + np.sum(transport, where=strong_cells)
                                )
                                primary_classes[zone, name] = dict(
                                    case=case,
                                    start_index=idx - 1,
                                    end_index=idx,
                                    zone_kpc=zone,
                                    tracer_at_saved_endpoints=name,
                                    cell_count=int(cells.sum()),
                                    labelled_energy_erg=label,
                                    fixed_cell_storage_change_over_label=dsub,
                                    integrated_outward_flux_over_label=fsub,
                                    reconstructed_residual_over_label=part,
                                    share_of_zone_signed_residual=part / residual,
                                    tr1_0p1_to_0p9_at_both_cell_count=int(strong_cells.sum()),
                                    tr1_0p1_to_0p9_at_both_share_of_zone_residual=strong_part / residual,
                                )
                        if not math.isclose(subtotal, residual, abs_tol=1.0e-12, rel_tol=1.0e-12):
                            raise ValueError("endpoint tracer classes do not close")
            for key, values in estimates.items():
                primary_classes[key].update(
                    method_min_residual_over_label=min(v[0] for v in values),
                    method_max_residual_over_label=max(v[0] for v in values),
                    method_min_share_of_zone_signed_residual=min(v[1] for v in values),
                    method_max_share_of_zone_signed_residual=max(v[1] for v in values),
                )
                classes.append(primary_classes[key])
        previous = (current_time, stock, flux, tracer, gravity)
    return local, classes, wide, geometry_error


def radial_windows(local, intervals):
    keyed = {(q["case"], q["end_index"], q["zone"], q["method"], q["rule"]): q for q in local}
    reports = []
    for case, last in CASES.items():
        for a, b in windows(last):
            whole = {}
            for m in METHODS:
                for boundary in BOUNDARIES:
                    for rule in RULES:
                        keys = [(case, i, m, boundary, rule) for i in range(a + 1, b + 1)]
                        if not all(k in intervals for k in keys):
                            continue
                        points = [intervals[k] for k in keys]
                        label = math.fsum(float(q["labelled_energy_erg"]) for q in points)
                        whole[m, boundary, rule] = (
                            math.fsum(
                                float(q["labelled_energy_erg"])
                                * float(q["outside_total_residual_over_label"])
                                for q in points
                            )
                            / label
                        )
            for zone in ("0.75_to_0.80", "0.80_to_0.85", "0.75_to_0.85"):
                estimates = {}
                for m in METHODS:
                    for rule in RULES:
                        points = [keyed[case, i, zone, m, rule] for i in range(a + 1, b + 1)]
                        label = math.fsum(q["label"] for q in points)
                        estimates[m, rule] = [
                            math.fsum(q["label"] * q[k] for q in points) / label
                            for k in ("storage", "transport", "residual", "gravity_net", "gravity_gross")
                        ]
                storage, transport, residual, gravity_net, gravity_gross = estimates[PRIMARY, "trapezoid"]
                exterior = whole[PRIMARY, "outer_active_cell", "trapezoid"]
                beyond = [val - estimates[m, rule][2] for (m, boundary, rule), val in whole.items()]
                reports.append(
                    dict(
                        case=case,
                        start_index=a,
                        end_index=b,
                        zone_kpc=zone,
                        primary_storage_change_over_label=storage,
                        primary_net_outward_flux_over_label=transport,
                        primary_residual_over_label=residual,
                        primary_shell_direct_net_work_over_label=gravity_net,
                        primary_shell_direct_gross_work_over_label=gravity_gross,
                        method_min_residual_over_label=min(v[2] for v in estimates.values()),
                        method_max_residual_over_label=max(v[2] for v in estimates.values()),
                        primary_total_exterior_residual_over_label=exterior,
                        n_available_domain_combinations=len(whole),
                        primary_beyond_0p85_residual_over_label=exterior - residual
                        if zone == "0.75_to_0.85"
                        else None,
                        method_min_beyond_0p85_residual_over_label=min(beyond)
                        if zone == "0.75_to_0.85"
                        else None,
                        method_max_beyond_0p85_residual_over_label=max(beyond)
                        if zone == "0.75_to_0.85"
                        else None,
                    )
                )
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--native", type=Path, default=PRIVATE / "turn21_injector/full_review/native/results")
    parser.add_argument(
        "--requests", type=Path, default=PRIVATE / "turn21_injector/native_stage_repair/requests"
    )
    parser.add_argument("--fixed", type=Path, default=PRIVATE / "turn18_high_review_2026-11-18/stage/results")
    parser.add_argument("--gravity-only", action="store_true", help="use only the public packaged histories")
    args = parser.parse_args()
    intervals, rates = published()
    write_rows(args.output / "entropy_localisation_gravity_ratio.csv", work_ratios(intervals))
    if args.gravity_only:
        return
    local, tracer, wide = [], [], []
    differences = {}
    for case in CASES:
        sub, classes, storage, difference = case_budgets(
            case, args.native, args.requests, args.fixed, intervals, rates
        )
        local.extend(sub)
        tracer.extend(classes)
        wide.extend(storage)
        differences[case] = difference
    write_rows(args.output / "entropy_localisation_near_spheres.csv", radial_windows(local, intervals))
    write_rows(args.output / "entropy_localisation_near_tracer.csv", tracer)
    write_rows(args.output / "entropy_localisation_large_spheres.csv", wide)
    print("Maximum difference from archived injector rates as a fraction of labelled power", differences)


if __name__ == "__main__":
    main()
