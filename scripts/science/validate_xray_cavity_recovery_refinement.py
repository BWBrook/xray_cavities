#!/usr/bin/env python3
"""Evaluate the Goal 045 recovery refinement on existing Goal 044 maps.

Goal 044 remains an immutable failed-closed record. This evaluator does not
run XRAiSE: it separates high-purity seed detection from projected geometry,
uses area-weighted validation, and recomputes projector recovery equivalence
on a third symmetric common grid.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import hemisphere_seed_grow_recovery as seed_grow
import three_case_cavity_recovery as recovery
import validate_xray_cavity_production as goal044


TRACER_THRESHOLD = 5.0e-3
KPC_CM = goal044.KPC_CM
COMMON_GRID_NORMALIZED_L1_MAX = 1.0e-8
COMMON_GRID_MASK_IOU_MIN = 0.99
COMMON_GRID_AREA_RELATIVE_ERROR_MAX = 0.01
COMMON_GRID_CENTROID_ERROR_KPC_MAX = 1.0
COMMON_GRID_VOLUME_RELATIVE_ERROR_MAX = 0.05
SYNTHETIC_PRECISION_MIN = 0.90
SYNTHETIC_IOU_MIN = 0.50
SYNTHETIC_CENTROID_ERROR_KPC_MAX = 10.0
SYNTHETIC_AREA_RELATIVE_ERROR_MAX = 0.25
SYNTHETIC_VOLUME_RELATIVE_ERROR_MAX = 0.30
SECONDARY_AREA_FRACTION_MAX = 0.10
UNIQUE_SYNTHETIC_PRODUCTS = ("direct0", "edge45", "edge90")
COMMON_GRID_CASES = ("axisymmetric", "nonaxisymmetric", "C-HI")
SIDES = ("negative_z", "positive_z")


def acceptance_criteria() -> list[dict[str, Any]]:
    """Return the frozen Goal 045 gates before any evaluation is run."""

    return [
        {
            "gate": "background_stability",
            "comparison": "degree 5/6/7 fits on six unique synthetic maps",
            "tolerance": (
                "all converged; condition_number<1e6; finite blocked-CV RMSE; "
                "degree 6 not a numerical knife-edge"
            ),
        },
        {
            "gate": "synthetic_recovery",
            "comparison": "two fixtures x unique physical angles 0/45/90",
            "tolerance": (
                "both sides; no midplane-crossing primary; area-weighted "
                "precision>=0.90; IoU>=0.50; centroid_error<=10 kpc; "
                "area_error<=0.25; volume_error<=0.30; "
                "secondary_area/primary_area<=0.10"
            ),
        },
        {
            "gate": "negative_controls",
            "comparison": "smooth background and one-sided ablations",
            "tolerance": "smooth=zero sides; ablation=retained side only",
        },
        {
            "gate": "common_grid_recovery_equivalence",
            "comparison": "direct90 versus edge90 on third symmetric grid",
            "tolerance": (
                "map normalized_l1<=1e-8; same sides/topology; mask IoU>=0.99; "
                "area_error<=0.01; centroid_error<=1 kpc; volume_error<=0.05"
            ),
        },
        {
            "gate": "geometry_resolution",
            "comparison": "all expected primary validation components",
            "tolerance": (
                ">=3 distinct horizontal and vertical centres; full-rank "
                "covariance; minor semiaxis>one local cell width"
            ),
        },
        {
            "gate": "energy_convention",
            "comparison": "resolved hybrid pV, 2.5pV, and 4pV rows",
            "tolerance": "finite positive; exact multipliers at rel_tol=1e-12",
        },
        {
            "gate": "input_provenance",
            "comparison": "Goal 044 products and Goal 045 staged code",
            "tolerance": "complete SHA-256 manifest",
        },
    ]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def common_symmetric_axis(
    first_centres: np.ndarray,
    second_centres: np.ndarray,
    *,
    cell_count: int | None = None,
) -> np.ndarray:
    """Build a third symmetric grid over the intersection of two supports."""

    first = np.asarray(first_centres, dtype=float)
    second = np.asarray(second_centres, dtype=float)
    first_edges = goal044.centres_to_edges(first)
    second_edges = goal044.centres_to_edges(second)
    lower = max(float(first_edges[0]), float(second_edges[0]))
    upper = min(float(first_edges[-1]), float(second_edges[-1]))
    if not lower < 0.0 < upper:
        raise ValueError("common support must straddle zero")
    limit = min(abs(lower), abs(upper))
    count = min(first.size, second.size) if cell_count is None else int(cell_count)
    if count < 3:
        raise ValueError("common grid requires at least three cells")
    edges = np.linspace(-limit, limit, count + 1)
    return 0.5 * (edges[:-1] + edges[1:])


def regrid_product(
    product: goal044.MapProduct,
    target_horizontal: np.ndarray,
) -> goal044.MapProduct:
    """Conservatively map a product's columns onto a third grid."""

    return goal044.MapProduct(
        corrected=goal044.conservative_regrid_columns(
            product.corrected, product.horizontal, target_horizontal
        ),
        raw=goal044.conservative_regrid_columns(
            product.raw, product.horizontal, target_horizontal
        ),
        tracer=goal044.conservative_regrid_columns(
            product.tracer, product.horizontal, target_horizontal
        ),
        horizontal=np.asarray(target_horizontal, dtype=float),
        vertical=product.vertical.copy(),
    )


def area_weighted_mask_iou(
    first: np.ndarray,
    second: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
) -> float:
    first_mask = np.asarray(first, dtype=bool)
    second_mask = np.asarray(second, dtype=bool)
    if first_mask.shape != second_mask.shape:
        raise ValueError("mask shapes differ")
    area = recovery._cell_area_grid(horizontal, vertical)
    intersection = float(area[first_mask & second_mask].sum())
    union = float(area[first_mask | second_mask].sum())
    return 1.0 if union == 0.0 else intersection / union


def normalized_l1(
    first: np.ndarray,
    second: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
) -> float:
    left = np.asarray(first, dtype=float)
    right = np.asarray(second, dtype=float)
    if left.shape != right.shape:
        raise ValueError("map shapes differ")
    area = recovery._cell_area_grid(horizontal, vertical)
    denominator = float(np.sum(np.abs(left) * area))
    if denominator <= 0.0:
        return 0.0 if np.array_equal(left, right) else float("inf")
    return float(np.sum(np.abs(right - left) * area) / denominator)


def relative_error(first: float, second: float) -> float:
    denominator = abs(float(first))
    if denominator == 0.0:
        return 0.0 if float(second) == 0.0 else float("inf")
    return abs(float(second) - float(first)) / denominator


def summarize_mask(
    mask: np.ndarray,
    horizontal: np.ndarray,
    vertical: np.ndarray,
) -> recovery.ComponentSummary | None:
    values = np.asarray(mask, dtype=bool)
    if not np.any(values):
        return None
    area = float(recovery._cell_area_grid(horizontal, vertical)[values].sum())
    component = recovery.Component(1, values, area)
    return recovery.summarize_components((component,), horizontal, vertical)[0]


def energy_rows(
    case: str,
    product: str,
    side: str,
    summary: recovery.ComponentSummary | None,
    resolved: bool,
    pressure_dyn_cm2: float,
) -> list[dict[str, Any]]:
    """Return explicit estimated or not-estimable energy rows."""

    rows: list[dict[str, Any]] = []
    volume = (
        float(summary.volumes_kpc3["geometric_depth"])
        if resolved and summary is not None
        else None
    )
    p_v = pressure_dyn_cm2 * volume * KPC_CM**3 if volume is not None else None
    for convention, multiplier in (("pV", 1.0), ("2.5pV", 2.5), ("4pV", 4.0)):
        rows.append(
            {
                "case": case,
                "product": product,
                "side": side,
                "convention": convention,
                "multiplier": multiplier,
                "pressure_dyn_cm2": pressure_dyn_cm2,
                "volume_geometric_depth_kpc3": "" if volume is None else volume,
                "energy_erg": "" if p_v is None else p_v * multiplier,
                "estimation_status": "estimated" if p_v is not None else "not_estimable",
                "interpretation": "simulation_assisted_pressure_times_geometric_proxy_volume",
            }
        )
    return rows


def energy_gate_result(rows: list[dict[str, Any]]) -> tuple[bool, str]:
    groups: dict[tuple[str, str, str], dict[str, float]] = {}
    unresolved = 0
    positive = 0
    for row in rows:
        if row["estimation_status"] != "estimated":
            unresolved += 1
            continue
        energy = float(row["energy_erg"])
        if math.isfinite(energy) and energy > 0.0:
            positive += 1
        key = (str(row["case"]), str(row["product"]), str(row["side"]))
        groups.setdefault(key, {})[str(row["convention"])] = energy
    multiplier_ok = 0
    for values in groups.values():
        if set(values) != {"pV", "2.5pV", "4pV"}:
            continue
        p_v = values["pV"]
        if (
            math.isfinite(p_v)
            and p_v > 0.0
            and math.isclose(values["2.5pV"], 2.5 * p_v, rel_tol=1.0e-12)
            and math.isclose(values["4pV"], 4.0 * p_v, rel_tol=1.0e-12)
        ):
            multiplier_ok += 1
    passed = (
        bool(rows)
        and unresolved == 0
        and positive == len(rows)
        and multiplier_ok == len(groups)
    )
    return (
        passed,
        f"{unresolved} unresolved rows; {positive}/{len(rows)} finite positive; "
        f"{multiplier_ok}/{len(groups)} exact multiplier groups",
    )


def _side_mask(
    vertical: np.ndarray,
    horizontal: np.ndarray,
    side: str,
) -> np.ndarray:
    if side not in SIDES:
        raise ValueError(f"unknown side: {side}")
    _, zz = np.meshgrid(horizontal, vertical)
    return zz < 0.0 if side == "negative_z" else zz > 0.0


def _fragment_area_fraction(
    hemisphere: seed_grow.HemisphereRecovery,
) -> float:
    if hemisphere.primary is None:
        return float("inf")
    fragment_area = sum(
        fragment.area_kpc2 for fragment in hemisphere.secondary_fragments
    )
    return fragment_area / hemisphere.primary.area_kpc2


def _synthetic_recovery_rows(
    products: dict[tuple[str, str], goal044.MapProduct],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    recovery_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    stability_rows: list[dict[str, Any]] = []
    energy_inputs: list[dict[str, Any]] = []
    for case in ("axisymmetric", "nonaxisymmetric"):
        for product_name in UNIQUE_SYNTHETIC_PRODUCTS:
            product = products[(case, product_name)]
            result = seed_grow.recover_hemisphere_seed_grow(
                product.corrected, product.horizontal, product.vertical
            )
            stability = seed_grow.polynomial_background_stability(
                product.corrected, product.horizontal, product.vertical
            )
            for degree in stability.degrees:
                stability_rows.append(
                    {
                        "case": case,
                        "product": product_name,
                        "degree": degree.degree,
                        "converged": degree.converged,
                        "condition_number": degree.condition_number,
                        "retained_area_fraction": degree.retained_area_fraction,
                        "weighted_rmse_log_intensity": (
                            degree.weighted_rmse_log_intensity
                        ),
                        "blocked_cv_rmse_log_intensity": (
                            degree.blocked_cv_rmse_log_intensity
                        ),
                        "degree6_not_numerical_knife_edge": (
                            stability.degree6_not_numerical_knife_edge
                        ),
                    }
                )

            truth = product.tracer >= TRACER_THRESHOLD
            for side in SIDES:
                hemisphere_mask = _side_mask(
                    product.vertical, product.horizontal, side
                )
                truth_side = truth & hemisphere_mask
                hemisphere = result.hemispheres[side]
                predicted = (
                    hemisphere.primary.mask
                    if hemisphere.primary is not None
                    else np.zeros_like(truth_side)
                )
                metrics = seed_grow.area_weighted_truth_metrics(
                    predicted,
                    truth_side,
                    product.horizontal,
                    product.vertical,
                )
                truth_summary = summarize_mask(
                    truth_side, product.horizontal, product.vertical
                )
                predicted_summary = (
                    hemisphere.primary.summary
                    if hemisphere.primary is not None
                    else None
                )
                resolution = seed_grow.geometry_resolution(
                    predicted, product.horizontal, product.vertical
                )
                volume_error = (
                    relative_error(
                        truth_summary.volumes_kpc3["geometric_depth"],
                        predicted_summary.volumes_kpc3["geometric_depth"],
                    )
                    if truth_summary is not None and predicted_summary is not None
                    else float("inf")
                )
                fragment_fraction = _fragment_area_fraction(hemisphere)
                row_pass = (
                    hemisphere.primary is not None
                    and not hemisphere.primary.summary.crosses_z_zero
                    and metrics.precision >= SYNTHETIC_PRECISION_MIN
                    and metrics.intersection_over_union >= SYNTHETIC_IOU_MIN
                    and metrics.centroid_error_kpc
                    <= SYNTHETIC_CENTROID_ERROR_KPC_MAX
                    and metrics.area_absolute_relative_error
                    <= SYNTHETIC_AREA_RELATIVE_ERROR_MAX
                    and volume_error <= SYNTHETIC_VOLUME_RELATIVE_ERROR_MAX
                    and fragment_fraction <= SECONDARY_AREA_FRACTION_MAX
                    and resolution.resolved
                )
                recovery_rows.append(
                    {
                        "case": case,
                        "product": product_name,
                        "side": side,
                        "background_method": result.background_method,
                        "support_threshold": result.support_threshold,
                        "radial_outer_annulus_threshold": (
                            result.radial_outer_annulus_threshold
                        ),
                        "seed_threshold": hemisphere.seed_threshold,
                        "detected": hemisphere.primary is not None,
                        "crosses_z_zero": (
                            ""
                            if hemisphere.primary is None
                            else hemisphere.primary.summary.crosses_z_zero
                        ),
                        "area_weighted_precision": metrics.precision,
                        "area_weighted_recall": metrics.recall,
                        "area_weighted_iou": metrics.intersection_over_union,
                        "centroid_error_kpc": metrics.centroid_error_kpc,
                        "area_absolute_relative_error": (
                            metrics.area_absolute_relative_error
                        ),
                        "volume_geometric_relative_error": volume_error,
                        "secondary_area_fraction": fragment_fraction,
                        "geometry_resolved": resolution.resolved,
                        "gate_pass": row_pass,
                    }
                )
                geometry_rows.append(
                    {
                        "case": case,
                        "product": product_name,
                        "side": side,
                        "status": (
                            "resolved" if resolution.resolved else "not_estimable"
                        ),
                        "distinct_horizontal_centres": (
                            resolution.distinct_horizontal_centres
                        ),
                        "distinct_vertical_centres": (
                            resolution.distinct_vertical_centres
                        ),
                        "covariance_rank": resolution.covariance_rank,
                        "major_semiaxis_kpc": (
                            resolution.major_semiaxis_kpc
                            if resolution.resolved
                            else ""
                        ),
                        "minor_semiaxis_kpc": (
                            resolution.minor_semiaxis_kpc
                            if resolution.resolved
                            else ""
                        ),
                        "local_cell_width_kpc": (
                            resolution.local_cell_width_kpc
                        ),
                        "volume_geometric_depth_kpc3": (
                            predicted_summary.volumes_kpc3["geometric_depth"]
                            if resolution.resolved
                            and predicted_summary is not None
                            else ""
                        ),
                    }
                )
                energy_inputs.append(
                    {
                        "case": case,
                        "product": product_name,
                        "side": side,
                        "summary": predicted_summary,
                        "resolved": resolution.resolved,
                    }
                )

            smooth = seed_grow.make_smooth_background_control(
                product.corrected, product.horizontal, product.vertical
            )
            smooth_result = seed_grow.recover_hemisphere_seed_grow(
                smooth, product.horizontal, product.vertical
            )
            control_rows.append(
                {
                    "case": case,
                    "product": product_name,
                    "control": "independent_radial_smooth_null",
                    "retained_side": "none",
                    "detected_sides": "|".join(smooth_result.detected_sides),
                    "gate_pass": len(smooth_result.detected_sides) == 0,
                }
            )
            for retained_side in SIDES:
                ablated = seed_grow.make_one_sided_ablation_control(
                    product.corrected,
                    product.horizontal,
                    product.vertical,
                    retained_side=retained_side,
                )
                ablated_result = seed_grow.recover_hemisphere_seed_grow(
                    ablated, product.horizontal, product.vertical
                )
                control_rows.append(
                    {
                        "case": case,
                        "product": product_name,
                        "control": "independent_radial_one_sided_ablation",
                        "retained_side": retained_side,
                        "detected_sides": "|".join(
                            ablated_result.detected_sides
                        ),
                        "gate_pass": (
                            ablated_result.detected_sides == (retained_side,)
                        ),
                    }
                )
    return (
        recovery_rows,
        geometry_rows,
        control_rows,
        stability_rows,
        energy_inputs,
    )


def _common_grid_rows(
    products: dict[tuple[str, str], goal044.MapProduct],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    comparison_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    real_energy_inputs: list[dict[str, Any]] = []
    for case in COMMON_GRID_CASES:
        direct = products[(case, "direct90")]
        edge = products[(case, "edge90")]
        if not np.allclose(
            direct.vertical, edge.vertical, rtol=0.0, atol=1.0e-10
        ):
            raise ValueError(f"{case} direct/edge vertical axes differ")
        common = common_symmetric_axis(direct.horizontal, edge.horizontal)
        direct_common = regrid_product(direct, common)
        edge_common = regrid_product(edge, common)
        direct_result = seed_grow.recover_hemisphere_seed_grow(
            direct_common.corrected, common, direct_common.vertical
        )
        edge_result = seed_grow.recover_hemisphere_seed_grow(
            edge_common.corrected, common, edge_common.vertical
        )
        area = recovery._cell_area_grid(common, direct_common.vertical)
        direct_area = float(area[direct_result.observer_mask].sum())
        edge_area = float(area[edge_result.observer_mask].sum())
        centroid_errors: list[float] = []
        for side in SIDES:
            direct_primary = direct_result.hemispheres[side].primary
            edge_primary = edge_result.hemispheres[side].primary
            if direct_primary is None or edge_primary is None:
                centroid_errors.append(float("inf"))
                continue
            centroid_errors.append(
                float(
                    np.hypot(
                        direct_primary.summary.centroid_x_kpc
                        - edge_primary.summary.centroid_x_kpc,
                        direct_primary.summary.centroid_z_kpc
                        - edge_primary.summary.centroid_z_kpc,
                    )
                )
            )
        direct_volumes = [
            side.primary.summary.volumes_kpc3["geometric_depth"]
            for side in direct_result.hemispheres.values()
            if side.primary is not None
        ]
        edge_volumes = [
            side.primary.summary.volumes_kpc3["geometric_depth"]
            for side in edge_result.hemispheres.values()
            if side.primary is not None
        ]
        volume_error = (
            relative_error(sum(direct_volumes), sum(edge_volumes))
            if len(direct_volumes) == len(edge_volumes) == 2
            else float("inf")
        )
        map_l1 = normalized_l1(
            direct_common.corrected,
            edge_common.corrected,
            common,
            direct_common.vertical,
        )
        mask_iou = area_weighted_mask_iou(
            direct_result.observer_mask,
            edge_result.observer_mask,
            common,
            direct_common.vertical,
        )
        area_error = relative_error(direct_area, edge_area)
        centroid_error = max(centroid_errors)
        same_sides = direct_result.detected_sides == edge_result.detected_sides
        gate_pass = (
            map_l1 <= COMMON_GRID_NORMALIZED_L1_MAX
            and same_sides
            and mask_iou >= COMMON_GRID_MASK_IOU_MIN
            and area_error <= COMMON_GRID_AREA_RELATIVE_ERROR_MAX
            and centroid_error <= COMMON_GRID_CENTROID_ERROR_KPC_MAX
            and volume_error <= COMMON_GRID_VOLUME_RELATIVE_ERROR_MAX
        )
        comparison_rows.append(
            {
                "case": case,
                "common_cell_count": common.size,
                "common_min_kpc": common[0],
                "common_max_kpc": common[-1],
                "map_normalized_l1": map_l1,
                "direct_detected_sides": "|".join(
                    direct_result.detected_sides
                ),
                "edge_detected_sides": "|".join(edge_result.detected_sides),
                "same_side_topology": same_sides,
                "area_weighted_mask_iou": mask_iou,
                "total_area_relative_error": area_error,
                "max_primary_centroid_error_kpc": centroid_error,
                "total_geometric_volume_relative_error": volume_error,
                "gate_pass": gate_pass,
            }
        )
        for method, result in (
            ("direct90_common", direct_result),
            ("edge90_common", edge_result),
        ):
            for side in SIDES:
                hemisphere = result.hemispheres[side]
                primary = hemisphere.primary
                mask = (
                    primary.mask
                    if primary is not None
                    else np.zeros_like(result.observer_mask)
                )
                resolution = seed_grow.geometry_resolution(
                    mask, common, direct_common.vertical
                )
                geometry_rows.append(
                    {
                        "case": case,
                        "product": method,
                        "side": side,
                        "status": (
                            "resolved" if resolution.resolved else "not_estimable"
                        ),
                        "distinct_horizontal_centres": (
                            resolution.distinct_horizontal_centres
                        ),
                        "distinct_vertical_centres": (
                            resolution.distinct_vertical_centres
                        ),
                        "covariance_rank": resolution.covariance_rank,
                        "major_semiaxis_kpc": (
                            resolution.major_semiaxis_kpc
                            if resolution.resolved
                            else ""
                        ),
                        "minor_semiaxis_kpc": (
                            resolution.minor_semiaxis_kpc
                            if resolution.resolved
                            else ""
                        ),
                        "local_cell_width_kpc": (
                            resolution.local_cell_width_kpc
                        ),
                        "volume_geometric_depth_kpc3": (
                            primary.summary.volumes_kpc3["geometric_depth"]
                            if resolution.resolved and primary is not None
                            else ""
                        ),
                    }
                )
                if case == "C-HI" and method == "edge90_common":
                    real_energy_inputs.append(
                        {
                            "case": case,
                            "product": method,
                            "side": side,
                            "summary": (
                                primary.summary if primary is not None else None
                            ),
                            "resolved": resolution.resolved,
                        }
                    )
    return comparison_rows, geometry_rows, real_energy_inputs


def _selected_input_provenance(
    run_root: Path,
) -> list[dict[str, Any]]:
    paths: set[Path] = set()
    for case in ("axisymmetric", "nonaxisymmetric"):
        for product in set(UNIQUE_SYNTHETIC_PRODUCTS) | {"direct90", "edge90"}:
            directory = run_root / "synthetic" / case / product
            for name in (
                "xray_1kev_xraise_corrected_mjy_sr.tsv",
                "tracer_max_los.tsv",
                "x_kpc.tsv",
                "z_kpc.tsv",
            ):
                paths.add(directory / name)
    for product in ("direct90", "edge90"):
        directory = run_root / "real_c_hi" / product
        for name in (
            "xray_1kev_xraise_corrected_mjy_sr.tsv",
            "tracer_max_los.tsv",
            "x_kpc.tsv",
            "z_kpc.tsv",
        ):
            paths.add(directory / name)
    rows = []
    for path in sorted(paths):
        if not path.is_file():
            raise ValueError(f"missing selected Goal 044 input: {path}")
        rows.append(
            {
                "role": "goal044_existing_map_input",
                "path": str(path),
                "sha256": sha256_path(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def evaluate(
    run_root: Path,
    output_dir: Path,
    pressure_context: Path,
    provenance: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    contract_path = (
        output_dir.parent / "contracts" / "acceptance_criteria_goal045.csv"
    )
    frozen = list(csv.DictReader(contract_path.open(newline="")))
    if frozen != [
        {key: str(value) for key, value in row.items()}
        for row in acceptance_criteria()
    ]:
        raise ValueError("frozen Goal 045 contract differs from evaluator")

    fixture_rows = list(
        csv.DictReader(
            (run_root / "contracts" / "synthetic_fixture_contract.csv").open(
                newline=""
            )
        )
    )
    fixtures = {row["case"]: row for row in fixture_rows}
    products: dict[tuple[str, str], goal044.MapProduct] = {}
    for case in ("axisymmetric", "nonaxisymmetric"):
        for product in set(UNIQUE_SYNTHETIC_PRODUCTS) | {"direct90", "edge90"}:
            products[(case, product)] = goal044.load_product(
                run_root / "synthetic" / case / product
            )
    for product in ("direct90", "edge90"):
        products[("C-HI", product)] = goal044.load_product(
            run_root / "real_c_hi" / product
        )

    (
        synthetic_rows,
        synthetic_geometry,
        control_rows,
        stability_rows,
        synthetic_energy_inputs,
    ) = _synthetic_recovery_rows(products)
    (
        common_rows,
        common_geometry,
        real_energy_inputs,
    ) = _common_grid_rows(products)
    geometry_rows = synthetic_geometry + common_geometry

    synthetic_pressure = {
        case: goal044.synthetic_pressures(fixtures, case)
        for case in ("axisymmetric", "nonaxisymmetric")
    }
    real_pressure = goal044.real_pressures(pressure_context)
    all_energy_rows: list[dict[str, Any]] = []
    for item in synthetic_energy_inputs + real_energy_inputs:
        pressures = (
            real_pressure
            if item["case"] == "C-HI"
            else synthetic_pressure[item["case"]]
        )
        all_energy_rows.extend(
            energy_rows(
                item["case"],
                item["product"],
                item["side"],
                item["summary"],
                bool(item["resolved"]),
                pressures[item["side"]],
            )
        )

    code_provenance = list(csv.DictReader(provenance.open(newline="")))
    input_provenance = _selected_input_provenance(run_root)
    provenance_rows = code_provenance + input_provenance
    required_code_roles = {
        "goal045_validator",
        "goal045_wrapper",
        "goal044_validator",
        "seed_grow_recovery",
        "cavity_recovery",
        "cavity_recovery_builder",
        "pressure_context",
        "synthetic_fixture_contract",
        "goal044_provenance",
    }
    observed_code_roles = {
        row["role"]
        for row in code_provenance
        if len(row.get("sha256", "")) == 64
    }

    stability_ok = all(
        str(row["converged"]) == "True"
        and float(row["condition_number"]) < 1.0e6
        and math.isfinite(float(row["blocked_cv_rmse_log_intensity"]))
        and str(row["degree6_not_numerical_knife_edge"]) == "True"
        for row in stability_rows
    )
    synthetic_ok = all(str(row["gate_pass"]) == "True" for row in synthetic_rows)
    controls_ok = all(str(row["gate_pass"]) == "True" for row in control_rows)
    common_ok = all(str(row["gate_pass"]) == "True" for row in common_rows)
    geometry_ok = all(row["status"] == "resolved" for row in geometry_rows)
    energy_ok, energy_observed = energy_gate_result(all_energy_rows)
    provenance_ok = (
        required_code_roles <= observed_code_roles
        and bool(input_provenance)
        and all(len(row["sha256"]) == 64 for row in input_provenance)
    )
    gates = [
        {
            "gate": "background_stability",
            "status": "pass" if stability_ok else "fail",
            "observed": (
                f"{sum(str(row['converged']) == 'True' for row in stability_rows)}/"
                f"{len(stability_rows)} converged; "
                f"max_condition={max(float(row['condition_number']) for row in stability_rows):.6g}"
            ),
            "tolerance": acceptance_criteria()[0]["tolerance"],
        },
        {
            "gate": "synthetic_recovery",
            "status": "pass" if synthetic_ok else "fail",
            "observed": (
                f"{sum(str(row['gate_pass']) == 'True' for row in synthetic_rows)}/"
                f"{len(synthetic_rows)} side-angle rows pass"
            ),
            "tolerance": acceptance_criteria()[1]["tolerance"],
        },
        {
            "gate": "negative_controls",
            "status": "pass" if controls_ok else "fail",
            "observed": (
                f"{sum(str(row['gate_pass']) == 'True' for row in control_rows)}/"
                f"{len(control_rows)} controls pass"
            ),
            "tolerance": acceptance_criteria()[2]["tolerance"],
        },
        {
            "gate": "common_grid_recovery_equivalence",
            "status": "pass" if common_ok else "fail",
            "observed": (
                f"{sum(str(row['gate_pass']) == 'True' for row in common_rows)}/"
                f"{len(common_rows)} cases pass"
            ),
            "tolerance": acceptance_criteria()[3]["tolerance"],
        },
        {
            "gate": "geometry_resolution",
            "status": "pass" if geometry_ok else "fail",
            "observed": (
                f"{sum(row['status'] == 'resolved' for row in geometry_rows)}/"
                f"{len(geometry_rows)} expected components resolved"
            ),
            "tolerance": acceptance_criteria()[4]["tolerance"],
        },
        {
            "gate": "energy_convention",
            "status": "pass" if energy_ok else "fail",
            "observed": energy_observed,
            "tolerance": acceptance_criteria()[5]["tolerance"],
        },
        {
            "gate": "input_provenance",
            "status": "pass" if provenance_ok else "fail",
            "observed": (
                f"{len(input_provenance)} map inputs hashed; "
                f"{len(observed_code_roles & required_code_roles)}/"
                f"{len(required_code_roles)} code roles"
            ),
            "tolerance": acceptance_criteria()[6]["tolerance"],
        },
    ]

    _write_rows(output_dir / "acceptance_criteria_goal045.csv", frozen)
    _write_rows(output_dir / "background_stability.csv", stability_rows)
    _write_rows(output_dir / "synthetic_recovery.csv", synthetic_rows)
    _write_rows(output_dir / "negative_controls.csv", control_rows)
    _write_rows(output_dir / "common_grid_recovery_equivalence.csv", common_rows)
    _write_rows(output_dir / "geometry_resolution.csv", geometry_rows)
    _write_rows(output_dir / "hybrid_energy_summary.csv", all_energy_rows)
    _write_rows(output_dir / "input_provenance.csv", provenance_rows)
    _write_rows(output_dir / "validation_pass_fail.csv", gates)

    status = "pass" if all(row["status"] == "pass" for row in gates) else "fail"
    metadata = {
        "status": status,
        "decision_label": (
            "XRAY_CAVITY_RECOVERY_METHOD_REFINEMENT_GREEN"
            if status == "pass"
            else "XRAY_CAVITY_RECOVERY_METHOD_REFINEMENT_FAILED_CLOSED"
        ),
        "goal044_evidence_preserved": True,
        "xraise_or_pluto_rerun": False,
        "background_method": seed_grow.BACKGROUND_METHOD_LABEL,
        "background_degree": seed_grow.PRODUCTION_BACKGROUND_DEGREE,
        "unique_synthetic_products": list(UNIQUE_SYNTHETIC_PRODUCTS),
        "gate_count": len(gates),
        "passed_gate_count": sum(row["status"] == "pass" for row in gates),
        "scope_limit": (
            "fixture-informed production-pipeline validation; not general "
            "observational or publication-method certification"
        ),
    }
    (output_dir / "xray_cavity_recovery_method_refinement_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    manifest = output_dir / "local_asset_manifest.sha256"
    manifest.write_text(
        "\n".join(
            f"{sha256_path(path)}  {path.relative_to(output_dir)}"
            for path in sorted(output_dir.rglob("*"))
            if path.is_file() and path != manifest
        )
        + "\n"
    )
    print(
        f"validation_status={status} "
        f"passed_gates={metadata['passed_gate_count']}/{metadata['gate_count']}"
    )
    if status != "pass":
        raise SystemExit("X-ray cavity recovery method refinement failed closed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("write-contract")
    contract.add_argument("--output-dir", type=Path, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--run-root", type=Path, required=True)
    evaluate.add_argument("--output-dir", type=Path, required=True)
    evaluate.add_argument("--pressure-context", type=Path, required=True)
    evaluate.add_argument("--provenance", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "write-contract":
        _write_rows(args.output_dir / "acceptance_criteria_goal045.csv", acceptance_criteria())
        metadata = {
            "status": "predeclared_before_evaluation",
            "decision_label": "XRAY_CAVITY_RECOVERY_METHOD_REFINEMENT_CONTRACT_FROZEN",
            "seed_fraction_percent_per_hemisphere": 1.0,
            "background_method": seed_grow.BACKGROUND_METHOD_LABEL,
            "background_degree": seed_grow.PRODUCTION_BACKGROUND_DEGREE,
            "background_fit": (
                "normalized Chebyshev basis; SVD least squares; fixed robust "
                "lower-outlier clipping"
            ),
            "background_stability_check": (
                "degrees 5/6/7; convergence, condition number, blocked spatial "
                "cross-validation, and degree-6 knife-edge test"
            ),
            "support_threshold": (
                "max(0, outer_annulus_median + 3 * 1.4826 * MAD) on the "
                "polynomial-background fractional deficit"
            ),
            "negative_control_background": (
                "independent radial background, not the fitted polynomial"
            ),
            "scope_limit": (
                "fixture-informed production-pipeline validation; not general "
                "observational or publication-method certification"
            ),
        }
        (args.output_dir / "goal045_contract_metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )
        return
    evaluate(
        args.run_root,
        args.output_dir,
        args.pressure_context,
        args.provenance,
    )


if __name__ == "__main__":
    main()
