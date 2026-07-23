#!/usr/bin/env python3
"""Build and evaluate the Goal 044 X-ray cavity production validation.

The production XRAiSE CLI is invoked by the PBS wrapper. This helper creates
small PLUTO-schema fixtures before those invocations and evaluates their
products, plus one accepted real endpoint, through the existing tracer-blind
cavity-recovery code.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, SymLogNorm

import build_three_case_cavity_recovery as recovery_builder
import three_case_cavity_recovery as recovery


CODE_TIME = 15330.0696894
TRACER_THRESHOLD = 5.0e-3
KPC_CM = 3.0856775814913673e21
UNIT_DENSITY_SI = 1.0023678e-21
UNIT_PRESSURE_SI = UNIT_DENSITY_SI * 2.99792458e8**2
UNIT_PRESSURE_DYN_CM2 = UNIT_PRESSURE_SI * 10.0
OUTPUT_FILES = (
    "x_kpc.tsv",
    "z_kpc.tsv",
    "xray_1kev_raw_mjy_sr.tsv",
    "xray_1kev_xraise_corrected_mjy_sr.tsv",
    "xray_1kev_correction_ratio.tsv",
    "tracer_max_los.tsv",
    "xraise_grid_smoke_metadata.json",
    "xraise_grid_smoke_summary.csv",
)
SYNTHETIC_PRODUCTS = (
    "direct0",
    "edge0",
    "edge45",
    "edge89p9",
    "edge90",
    "direct90",
)
REAL_PRODUCTS = ("direct0", "direct90", "edge90")


@dataclass(frozen=True)
class MapProduct:
    corrected: np.ndarray
    raw: np.ndarray
    tracer: np.ndarray
    horizontal: np.ndarray
    vertical: np.ndarray


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stretched_axis(count: int, half_extent: float, exponent: float) -> np.ndarray:
    if count < 3 or count % 2 == 0:
        raise ValueError("synthetic axes require an odd count of at least three")
    unit = np.linspace(-1.0, 1.0, count)
    return half_extent * np.sign(unit) * np.abs(unit) ** exponent


def centres_to_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2 or np.any(np.diff(values) <= 0.0):
        raise ValueError("coordinate centres must be a strictly increasing vector")
    mids = 0.5 * (values[:-1] + values[1:])
    return np.concatenate(
        [[values[0] - (mids[0] - values[0])], mids, [values[-1] + (values[-1] - mids[-1])]]
    )


def conservative_regrid_columns(
    values: np.ndarray,
    source_centres: np.ndarray,
    target_centres: np.ndarray,
) -> np.ndarray:
    """Area-average source columns onto target cells without changing flux."""

    source = np.asarray(values, dtype=float)
    source_edges = centres_to_edges(source_centres)
    target_edges = centres_to_edges(target_centres)
    if source.ndim != 2 or source.shape[1] != len(source_centres):
        raise ValueError("values must have one column per source centre")
    target = np.zeros((source.shape[0], len(target_centres)), dtype=float)
    for target_index, (left, right) in enumerate(
        zip(target_edges[:-1], target_edges[1:], strict=True)
    ):
        width = right - left
        first = max(0, int(np.searchsorted(source_edges, left, side="right") - 1))
        last = min(len(source_centres) - 1, int(np.searchsorted(source_edges, right, side="left")))
        for source_index in range(first, last + 1):
            overlap = min(right, source_edges[source_index + 1]) - max(
                left, source_edges[source_index]
            )
            if overlap > 0.0:
                target[:, target_index] += source[:, source_index] * overlap / width
    return target


def physical_integral(values: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray) -> float:
    area = np.outer(np.diff(centres_to_edges(vertical)), np.diff(centres_to_edges(horizontal)))
    return float(np.sum(np.asarray(values, dtype=float) * area))


def _cavity_masks(
    case: str, xx: np.ndarray, yy: np.ndarray, zz: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    if case == "axisymmetric":
        specs = ((0.0, 0.0, -58.0, 29.0, 29.0, 34.0), (0.0, 0.0, 58.0, 29.0, 29.0, 34.0))
    elif case == "nonaxisymmetric":
        specs = ((-23.0, 14.0, -60.0, 25.0, 34.0, 31.0), (19.0, -17.0, 61.0, 35.0, 23.0, 29.0))
    else:
        raise ValueError(f"unknown synthetic case: {case}")
    masks = []
    for cx, cy, cz, ax, ay, az in specs:
        masks.append(((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2 + ((zz - cz) / az) ** 2 <= 1.0)
    return masks[0], masks[1]


def create_fixture(path: Path, case: str) -> dict[str, Any]:
    x = stretched_axis(49, 200.0, 1.32)
    y = stretched_axis(45, 200.0, 1.18)
    z = stretched_axis(61, 200.0, 1.25)
    zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")
    radius = np.sqrt(xx**2 + yy**2 + zz**2)
    rho = 0.012 / (1.0 + (radius / 175.0) ** 1.4)
    prs = 4.0e-8 / (1.0 + (radius / 280.0) ** 1.2)
    negative, positive = _cavity_masks(case, xx, yy, zz)
    cavity = negative | positive
    rho[cavity] *= 0.24
    tracer = np.zeros_like(rho)
    tracer[cavity] = 1.0e-2
    zeros = np.zeros_like(rho)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as h5:
        coords = h5.create_group("cell_coords")
        coords.create_dataset("X", data=np.broadcast_to(x, rho.shape))
        coords.create_dataset("Y", data=np.broadcast_to(y[np.newaxis, :, np.newaxis], rho.shape))
        coords.create_dataset("Z", data=np.broadcast_to(z[:, np.newaxis, np.newaxis], rho.shape))
        timestep = h5.create_group("Timestep_0")
        timestep.attrs["Time"] = CODE_TIME
        variables = timestep.create_group("vars")
        for name, values in (
            ("rho", rho),
            ("prs", prs),
            ("tr1", tracer),
            ("vx1", zeros),
            ("vx2", zeros),
            ("vx3", zeros),
        ):
            variables.create_dataset(name, data=values.astype(np.float64))
    return {
        "case": case,
        "path": str(path),
        "sha256": sha256_path(path),
        "shape_nz_ny_nx": "x".join(str(value) for value in rho.shape),
        "x_nonuniform": not np.allclose(np.diff(x), np.diff(x)[0]),
        "y_nonuniform": not np.allclose(np.diff(y), np.diff(y)[0]),
        "z_nonuniform": not np.allclose(np.diff(z), np.diff(z)[0]),
        "negative_cavity_cells": int(np.count_nonzero(negative)),
        "positive_cavity_cells": int(np.count_nonzero(positive)),
        "ambient_pressure_code_median": float(np.median(prs[~cavity & (radius <= 120.0)])),
    }


def acceptance_criteria() -> list[dict[str, Any]]:
    return [
        {"gate": "fixture_schema", "comparison": "required datasets and nonuniform axes", "tolerance": "all pass"},
        {"gate": "physical_flux_conservation", "comparison": "direct versus edge and 89.9 versus 90", "tolerance": "relative_error<=1e-9"},
        {"gate": "native_axis_equivalence", "comparison": "direct versus edge on common grid", "tolerance": "normalized_l1<=1e-9"},
        {"gate": "near_90_continuity", "comparison": "edge 89.9 versus edge 90 on common grid", "tolerance": "normalized_l1<=0.05"},
        {"gate": "projected_occupancy", "comparison": "raw/corrected/ratio positive support", "tolerance": "zero empty columns"},
        {"gate": "synthetic_cavity_recovery", "comparison": "all synthetic products", "tolerance": "two opposite-side components and xray_precision>=0.95"},
        {"gate": "real_endpoint_recovery", "comparison": "direct 90 versus edge 90", "tolerance": "same topology, area and volume relative_error<=1e-9"},
        {"gate": "energy_convention", "comparison": "hybrid pV, 2.5pV, 4pV", "tolerance": "finite positive and exact multipliers"},
        {"gate": "determinism", "comparison": "repeated synthetic products and real edge 90", "tolerance": "byte-identical output files"},
        {"gate": "provenance", "comparison": "raw/staged/runtime dependencies", "tolerance": "complete SHA-256 manifest"},
    ]


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_fixtures(run_root: Path) -> None:
    contracts = run_root / "contracts"
    fixtures = run_root / "fixtures"
    contracts.mkdir(parents=True, exist_ok=True)
    rows = [create_fixture(fixtures / f"{case}.h5", case) for case in ("axisymmetric", "nonaxisymmetric")]
    _write_rows(contracts / "synthetic_fixture_contract.csv", rows)
    _write_rows(contracts / "acceptance_criteria.csv", acceptance_criteria())
    print("synthetic_fixtures=created acceptance_criteria=predeclared")


def load_product(path: Path) -> MapProduct:
    corrected = np.loadtxt(path / "xray_1kev_xraise_corrected_mjy_sr.tsv", delimiter="\t")
    raw = np.loadtxt(path / "xray_1kev_raw_mjy_sr.tsv", delimiter="\t")
    tracer = np.loadtxt(path / "tracer_max_los.tsv", delimiter="\t")
    horizontal = np.loadtxt(path / "x_kpc.tsv")
    vertical = np.loadtxt(path / "z_kpc.tsv")
    recovery.validate_map_and_axes(corrected, horizontal, vertical)
    if raw.shape != corrected.shape or tracer.shape != corrected.shape:
        raise ValueError(f"product arrays do not share shape: {path}")
    return MapProduct(corrected, raw, tracer, horizontal, vertical)


def compare_products(
    label: str,
    reference: MapProduct,
    candidate: MapProduct,
    comparison_kind: str,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    if not np.allclose(reference.vertical, candidate.vertical, rtol=0.0, atol=1.0e-10):
        raise ValueError(f"vertical axes differ for {label}")
    reference_common = conservative_regrid_columns(
        reference.corrected, reference.horizontal, candidate.horizontal
    )
    residual = candidate.corrected - reference_common
    scale = max(float(np.max(np.abs(reference_common))), np.finfo(float).tiny)
    area = np.outer(
        np.diff(centres_to_edges(candidate.vertical)),
        np.diff(centres_to_edges(candidate.horizontal)),
    )
    normalized_l1 = float(np.sum(np.abs(residual) * area) / np.sum(np.abs(reference_common) * area))
    row: dict[str, Any] = {
        "comparison": label,
        "comparison_kind": comparison_kind,
        "reference_flux": physical_integral(reference.corrected, reference.horizontal, reference.vertical),
        "candidate_flux": physical_integral(candidate.corrected, candidate.horizontal, candidate.vertical),
        "flux_relative_error": 0.0,
        "normalized_l1_residual": normalized_l1,
        "max_absolute_residual": float(np.max(np.abs(residual))),
        "max_residual_over_reference_peak": float(np.max(np.abs(residual)) / scale),
    }
    row["flux_relative_error"] = abs(row["candidate_flux"] - row["reference_flux"]) / abs(row["reference_flux"])
    return row, reference_common, residual


def empty_column_rows(case: str, product_name: str, product: MapProduct) -> list[dict[str, Any]]:
    rows = []
    ratio = np.divide(product.corrected, product.raw, out=np.zeros_like(product.raw), where=product.raw > 0.0)
    for layer, values in (("raw", product.raw), ("corrected", product.corrected), ("ratio", ratio)):
        positive = np.isfinite(values) & (values > 0.0)
        empty = int(np.count_nonzero(np.count_nonzero(positive, axis=0) == 0))
        rows.append({"case": case, "product": product_name, "layer": layer, "empty_columns": empty, "column_count": values.shape[1]})
    return rows


def analyse_recovery(case: str, product_name: str, product: MapProduct) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    spec = recovery.MapSpec(case, product_name, "", "", "", "", "validation_memory")
    loaded = recovery.LoadedMap(spec, product.corrected, product.tracer, product.horizontal, product.vertical)
    analysis = recovery_builder.analyse_loaded_map(loaded, time_myr=50.0)
    summary = dict(analysis.summary_row)
    summary["xray_precision_at_5e_3"] = next(
        row["xray_precision"] for row in analysis.tracer_rows if math.isclose(float(row["tracer_threshold"]), TRACER_THRESHOLD)
    )
    summary["tracer_recall_at_5e_3"] = next(
        row["tracer_recall"] for row in analysis.tracer_rows if math.isclose(float(row["tracer_threshold"]), TRACER_THRESHOLD)
    )
    return summary, analysis.component_rows


def synthetic_pressures(fixture_contract: dict[str, dict[str, str]], case: str) -> dict[str, float]:
    pressure = float(fixture_contract[case]["ambient_pressure_code_median"]) * UNIT_PRESSURE_DYN_CM2
    return {"negative_z": pressure, "positive_z": pressure}


def real_pressures(path: Path) -> dict[str, float]:
    rows = [row for row in csv.DictReader(path.open(newline="")) if row["case"] == "C-HI"]
    if {row["side"] for row in rows} != {"negative_z", "positive_z"}:
        raise ValueError("real pressure context must contain both C-HI sides")
    return {row["side"]: float(row["ambient_pressure_dyn_cm2"]) for row in rows}


def energy_rows(
    case: str,
    product_name: str,
    components: list[dict[str, Any]],
    pressures: dict[str, float],
) -> list[dict[str, Any]]:
    rows = []
    for component_index, component in enumerate(components, start=1):
        side = "negative_z" if float(component["centroid_z_kpc"]) < 0.0 else "positive_z"
        volume = float(component["volume_geometric_depth_kpc3"])
        p_v = pressures[side] * volume * KPC_CM**3
        for convention, multiplier in (("pV", 1.0), ("2.5pV", 2.5), ("4pV", 4.0)):
            rows.append({
                "case": case,
                "product": product_name,
                "component_index": component_index,
                "side": side,
                "pressure_dyn_cm2": pressures[side],
                "volume_geometric_depth_kpc3": volume,
                "convention": convention,
                "multiplier": multiplier,
                "energy_erg": p_v * multiplier,
                "interpretation": "hybrid_tracer_pressure_xray_volume_proxy",
            })
    return rows


def energy_gate_result(rows: list[dict[str, Any]]) -> tuple[bool, str]:
    """Validate positivity and exact pV multiplier propagation per component."""

    groups: dict[tuple[str, str, int], dict[str, float]] = {}
    positive_count = 0
    for row in rows:
        energy = float(row["energy_erg"])
        if math.isfinite(energy) and energy > 0.0:
            positive_count += 1
        key = (str(row["case"]), str(row["product"]), int(row["component_index"]))
        groups.setdefault(key, {})[str(row["convention"])] = energy

    multiplier_ok = 0
    for values in groups.values():
        if set(values) != {"pV", "2.5pV", "4pV"}:
            continue
        p_v = values["pV"]
        if (
            math.isfinite(p_v)
            and p_v > 0.0
            and math.isclose(values["2.5pV"], 2.5 * p_v, rel_tol=1.0e-12, abs_tol=0.0)
            and math.isclose(values["4pV"], 4.0 * p_v, rel_tol=1.0e-12, abs_tol=0.0)
        ):
            multiplier_ok += 1

    passed = positive_count == len(rows) and multiplier_ok == len(groups)
    observed = (
        f"{positive_count}/{len(rows)} finite positive rows; "
        f"{multiplier_ok}/{len(groups)} component groups have exact 1/2.5/4 multipliers"
    )
    return passed, observed


def determinism_rows(run_root: Path) -> list[dict[str, Any]]:
    pairs = []
    for case in ("axisymmetric", "nonaxisymmetric"):
        for product in SYNTHETIC_PRODUCTS:
            pairs.append((f"synthetic/{case}/{product}", run_root / "synthetic" / case / product, run_root / "synthetic_repeat" / case / product))
    pairs.append(("real_c_hi/edge90", run_root / "real_c_hi" / "edge90", run_root / "real_c_hi" / "edge90_repeat"))
    rows = []
    for label, first, second in pairs:
        first_files = {path.name for path in first.iterdir() if path.is_file()}
        second_files = {path.name for path in second.iterdir() if path.is_file()}
        if first_files != second_files or not set(OUTPUT_FILES) <= first_files:
            raise ValueError(f"determinism file surface differs for {label}")
        for filename in sorted(first_files):
            left, right = first / filename, second / filename
            first_hash, second_hash = sha256_path(left), sha256_path(right)
            rows.append({"product": label, "file": filename, "first_sha256": first_hash, "repeat_sha256": second_hash, "byte_identical": first_hash == second_hash})
    return rows


def _write_figure(
    path: Path,
    comparisons: list[tuple[str, MapProduct, MapProduct, np.ndarray, np.ndarray]],
) -> None:
    fig, axes = plt.subplots(len(comparisons), 4, figsize=(14, 3.5 * len(comparisons)), constrained_layout=True)
    if len(comparisons) == 1:
        axes = axes[np.newaxis, :]
    for row_index, (label, reference, candidate, reference_common, residual) in enumerate(comparisons):
        extent = [candidate.horizontal[0], candidate.horizontal[-1], candidate.vertical[0], candidate.vertical[-1]]
        positive = np.concatenate([reference_common[reference_common > 0.0], candidate.corrected[candidate.corrected > 0.0]])
        vmin = float(np.percentile(positive, 1.0))
        vmax = float(np.percentile(positive, 99.9))
        norm = LogNorm(vmin=max(vmin, np.finfo(float).tiny), vmax=max(vmax, vmin * 1.01))
        axes[row_index, 0].imshow(reference_common, origin="lower", extent=extent, aspect="auto", norm=norm, cmap="magma")
        axes[row_index, 1].imshow(candidate.corrected, origin="lower", extent=extent, aspect="auto", norm=norm, cmap="magma")
        absolute = np.abs(residual)
        axes[row_index, 2].imshow(absolute, origin="lower", extent=extent, aspect="auto", cmap="viridis")
        fractional = np.divide(residual, reference_common, out=np.zeros_like(residual), where=reference_common > 0.0)
        limit = max(float(np.percentile(np.abs(fractional), 99.5)), 1.0e-12)
        axes[row_index, 3].imshow(fractional, origin="lower", extent=extent, aspect="auto", cmap="coolwarm", norm=SymLogNorm(linthresh=limit / 100.0, vmin=-limit, vmax=limit))
        axes[row_index, 0].set_ylabel(f"{label}\nz (kpc)")
    for axis, title in zip(axes[0], ("Direct native axis", "Edge-overlap", "Absolute residual", "Fractional residual"), strict=True):
        axis.set_title(title)
    for axis in axes[-1]:
        axis.set_xlabel("common projected coordinate (kpc)")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def evaluate(run_root: Path, output_dir: Path, pressure_context: Path, provenance: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    criteria_path = run_root / "contracts" / "acceptance_criteria.csv"
    fixture_path = run_root / "contracts" / "synthetic_fixture_contract.csv"
    criteria = list(csv.DictReader(criteria_path.open(newline="")))
    fixtures = {row["case"]: row for row in csv.DictReader(fixture_path.open(newline=""))}
    products: dict[tuple[str, str], MapProduct] = {}
    for case in ("axisymmetric", "nonaxisymmetric"):
        for product_name in SYNTHETIC_PRODUCTS:
            products[(case, product_name)] = load_product(run_root / "synthetic" / case / product_name)
    for product_name in REAL_PRODUCTS:
        products[("C-HI", product_name)] = load_product(run_root / "real_c_hi" / product_name)

    comparison_rows: list[dict[str, Any]] = []
    figure_rows = []
    for case in ("axisymmetric", "nonaxisymmetric"):
        for ref_name, candidate_name, kind in (
            ("direct0", "edge0", "native_axis_equivalence"),
            ("direct90", "edge90", "native_axis_equivalence"),
            ("edge90", "edge89p9", "near_90_continuity"),
        ):
            row, common, residual = compare_products(
                f"{case}:{ref_name}_vs_{candidate_name}", products[(case, ref_name)], products[(case, candidate_name)], kind
            )
            comparison_rows.append(row)
            if ref_name == "direct90":
                figure_rows.append((case, products[(case, ref_name)], products[(case, candidate_name)], common, residual))
    row, common, residual = compare_products(
        "C-HI:direct90_vs_edge90", products[("C-HI", "direct90")], products[("C-HI", "edge90")], "native_axis_equivalence"
    )
    comparison_rows.append(row)
    figure_rows.append(("C-HI endpoint", products[("C-HI", "direct90")], products[("C-HI", "edge90")], common, residual))

    occupancy_rows: list[dict[str, Any]] = []
    recovery_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    all_energy_rows: list[dict[str, Any]] = []
    for (case, product_name), product in products.items():
        occupancy_rows.extend(empty_column_rows(case, product_name, product))
        summary, components = analyse_recovery(case, product_name, product)
        recovery_rows.append(summary)
        component_rows.extend(components)
        pressures = synthetic_pressures(fixtures, case) if case != "C-HI" else real_pressures(pressure_context)
        all_energy_rows.extend(energy_rows(case, product_name, components, pressures))

    deterministic = determinism_rows(run_root)
    provenance_rows = list(csv.DictReader(provenance.open(newline="")))
    required_roles = {"real_endpoint_hdf5", "xraise_cli", "xraise_runtime", "apec_table", "gaunt_lut", "cavity_recovery", "validation_helper"}
    gates = []
    gates.append({"gate": "fixture_schema", "status": "pass" if len(fixtures) == 2 and all(row[axis] == "True" for row in fixtures.values() for axis in ("x_nonuniform", "y_nonuniform", "z_nonuniform")) else "fail", "observed": "two production-schema fixtures with nonuniform x/y/z", "tolerance": "all pass"})
    flux_ok = all(float(row["flux_relative_error"]) <= 1.0e-9 for row in comparison_rows)
    gates.append({"gate": "physical_flux_conservation", "status": "pass" if flux_ok else "fail", "observed": max(float(row["flux_relative_error"]) for row in comparison_rows), "tolerance": "<=1e-9"})
    equivalence = [row for row in comparison_rows if row["comparison_kind"] == "native_axis_equivalence"]
    gates.append({"gate": "native_axis_equivalence", "status": "pass" if all(float(row["normalized_l1_residual"]) <= 1.0e-9 for row in equivalence) else "fail", "observed": max(float(row["normalized_l1_residual"]) for row in equivalence), "tolerance": "<=1e-9"})
    continuity = [row for row in comparison_rows if row["comparison_kind"] == "near_90_continuity"]
    gates.append({"gate": "near_90_continuity", "status": "pass" if all(float(row["normalized_l1_residual"]) <= 0.05 for row in continuity) else "fail", "observed": max(float(row["normalized_l1_residual"]) for row in continuity), "tolerance": "<=0.05"})
    gates.append({"gate": "projected_occupancy", "status": "pass" if all(int(row["empty_columns"]) == 0 for row in occupancy_rows) else "fail", "observed": max(int(row["empty_columns"]) for row in occupancy_rows), "tolerance": "0"})
    synthetic_recovery = [row for row in recovery_rows if row["case"] != "C-HI"]
    synthetic_ok = all(row["topology_class"] == "two_separate_components" and float(row["xray_precision_at_5e_3"]) >= 0.95 for row in synthetic_recovery)
    gates.append({"gate": "synthetic_cavity_recovery", "status": "pass" if synthetic_ok else "fail", "observed": f"{sum(row['topology_class'] == 'two_separate_components' for row in synthetic_recovery)}/{len(synthetic_recovery)} two-component; min precision={min(float(row['xray_precision_at_5e_3']) for row in synthetic_recovery):.6g}", "tolerance": "all two-component and precision>=0.95"})
    real = {row["view"]: row for row in recovery_rows if row["case"] == "C-HI"}
    area_error = abs(float(real["direct90"]["retained_area_kpc2"]) - float(real["edge90"]["retained_area_kpc2"])) / float(real["direct90"]["retained_area_kpc2"])
    volume_error = abs(float(real["direct90"]["volume_geometric_depth_kpc3"]) - float(real["edge90"]["volume_geometric_depth_kpc3"])) / float(real["direct90"]["volume_geometric_depth_kpc3"])
    real_ok = real["direct90"]["topology_class"] == real["edge90"]["topology_class"] and area_error <= 1.0e-9 and volume_error <= 1.0e-9
    gates.append({"gate": "real_endpoint_recovery", "status": "pass" if real_ok else "fail", "observed": f"topology={real['direct90']['topology_class']}/{real['edge90']['topology_class']}; area_error={area_error:.6g}; volume_error={volume_error:.6g}", "tolerance": "same topology; errors<=1e-9"})
    energy_ok, energy_observed = energy_gate_result(all_energy_rows)
    gates.append({"gate": "energy_convention", "status": "pass" if energy_ok else "fail", "observed": energy_observed, "tolerance": "all finite positive; multipliers 1/2.5/4"})
    gates.append({"gate": "determinism", "status": "pass" if all(str(row["byte_identical"]) == "True" for row in deterministic) else "fail", "observed": f"{sum(str(row['byte_identical']) == 'True' for row in deterministic)}/{len(deterministic)} byte-identical", "tolerance": "all byte-identical"})
    observed_roles = {row["role"] for row in provenance_rows if len(row.get("sha256", "")) == 64}
    gates.append({"gate": "provenance", "status": "pass" if required_roles <= observed_roles else "fail", "observed": ",".join(sorted(observed_roles)), "tolerance": ",".join(sorted(required_roles))})

    _write_rows(output_dir / "acceptance_criteria.csv", criteria)
    _write_rows(output_dir / "projection_comparison.csv", comparison_rows)
    _write_rows(output_dir / "projection_occupancy.csv", occupancy_rows)
    _write_rows(output_dir / "cavity_recovery_summary.csv", recovery_rows)
    _write_rows(output_dir / "cavity_component_summary.csv", component_rows)
    _write_rows(output_dir / "hybrid_energy_summary.csv", all_energy_rows)
    _write_rows(output_dir / "determinism.csv", deterministic)
    _write_rows(output_dir / "provenance.csv", provenance_rows)
    _write_rows(output_dir / "validation_pass_fail.csv", gates)
    _write_figure(output_dir / "xray_cavity_production_validation.png", figure_rows)
    status = "pass" if all(row["status"] == "pass" for row in gates) else "fail"
    metadata = {
        "status": status,
        "decision_label": "XRAY_CAVITY_PRODUCTION_VALIDATION_GREEN" if status == "pass" else "XRAY_CAVITY_PRODUCTION_VALIDATION_FAILED_CLOSED",
        "predeclared_acceptance_criteria": str(criteria_path),
        "synthetic_cases": ["axisymmetric", "nonaxisymmetric"],
        "real_endpoint": "C-HI Timestep_51",
        "gate_count": len(gates),
        "passed_gate_count": sum(row["status"] == "pass" for row in gates),
    }
    (output_dir / "xray_cavity_production_validation_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    manifest = output_dir / "local_asset_manifest.sha256"
    manifest.write_text("\n".join(f"{sha256_path(path)}  {path.relative_to(output_dir)}" for path in sorted(output_dir.rglob("*")) if path.is_file() and path != manifest) + "\n")
    print(f"validation_status={status} passed_gates={metadata['passed_gate_count']}/{metadata['gate_count']}")
    if status != "pass":
        raise SystemExit("X-ray cavity production validation failed closed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    fixtures = subparsers.add_parser("make-fixtures")
    fixtures.add_argument("--run-root", type=Path, required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--run-root", type=Path, required=True)
    evaluate_parser.add_argument("--output-dir", type=Path, required=True)
    evaluate_parser.add_argument("--pressure-context", type=Path, required=True)
    evaluate_parser.add_argument("--provenance", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "make-fixtures":
        make_fixtures(args.run_root)
    else:
        evaluate(args.run_root, args.output_dir, args.pressure_context, args.provenance)


if __name__ == "__main__":
    main()
