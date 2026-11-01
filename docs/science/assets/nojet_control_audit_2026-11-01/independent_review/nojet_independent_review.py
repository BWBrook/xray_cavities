#!/usr/bin/env python3
"""Independent output-only review of retained no-jet control audit products.

This checker deliberately does not read or hash the raw HDF5 snapshots.  It
binds the audit metadata to completed-migration hashes and live stat signatures,
then independently checks all relationships recoverable from the published
CSV, JSON and NPZ products.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


CASES = {
    "cluster_002003": {
        "job_id": "690366.kunanyi-ohpc",
        "environment": "tabulated_cosmo_002003.csv",
        "environment_sha256": "30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa",
        "shape": (500, 400, 400),
        "half_widths": (200.0, 200.0, 250.0),
        "migration_prefix": "2026-05-08/cluster_002003/690366.kunanyi-ohpc/problem",
    },
    "group_002031": {
        "job_id": "690371.kunanyi-ohpc",
        "environment": "tabulated_cosmo_002031.csv",
        "environment_sha256": "1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a",
        "shape": (500, 400, 400),
        "half_widths": (200.0, 200.0, 250.0),
        "migration_prefix": "2026-05-08/group_002031/690371.kunanyi-ohpc/problem/outputs",
    },
}

EXPECTED_UNIT_ID = "fc40cdd22f95cd549194"
EXPECTED_PLAN_HASH = "698d01634ade85df5fac6d42716c5463af56118230b085021ba7b205739c8900"
EXPECTED_REGIONS = (
    "whole_grid",
    "r_gt_100_kpc",
    "r_lt_10_kpc",
    "r_lt_30_kpc",
    "r_lt_80_kpc",
    "r_lt_100_kpc",
    "boundary_layer_1",
    "boundary_layer_2",
    "boundary_layer_4",
    "boundary_layer_8",
)
RADII = (10.0, 30.0, 80.0, 100.0)
BOUNDARY_LAYERS = (1, 2, 4, 8)
STORAGE = ("mass_g", "thermal_erg", "kinetic_erg", "gravitational_erg", "total_energy_erg")
COMPONENTS = ("thermal_erg", "kinetic_erg", "gravitational_erg")
ENERGIES = (*COMPONENTS, "total_energy_erg")
COMPARISON_ENERGY_ERG = 3.15576e58
UNIT_VELOCITY_CMS = 2.99792458e10
GAMMA_GAS = 5.0 / 3.0
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SNAPSHOT_RE = re.compile(r"^data\.(\d+)\.dbl\.h5$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or ())
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"invalid CSV header: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return fields, rows


def finite_float(row: Mapping[str, str], name: str) -> float:
    try:
        value = float(row[name])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid float {name}={row.get(name)!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite float {name}={value}")
    return value


def optional_float(row: Mapping[str, str], name: str) -> float | None:
    raw = row.get(name, "")
    return None if raw == "" else finite_float(row, name)


def exact_int(row: Mapping[str, str], name: str) -> int:
    raw = row.get(name, "")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid integer {name}={raw!r}") from exc
    return value


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


class Review:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.check_count = 0
        self.error_metrics: dict[str, dict[str, Any]] = {}

    def require(self, condition: bool, message: str) -> None:
        self.check_count += 1
        if not condition:
            self.failures.append(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)

    def residual(
        self,
        name: str,
        lhs: float,
        rhs: float,
        context: str,
        *,
        rel_limit: float = 2.0e-12,
        abs_limit: float = 0.0,
        scale_override: float | None = None,
    ) -> None:
        self.check_count += 1
        residual = lhs - rhs
        native_scale = max(abs(lhs), abs(rhs), np.finfo(float).tiny)
        scale = max(abs(scale_override), np.finfo(float).tiny) if scale_override is not None else native_scale
        normalized = abs(residual) / scale
        target_scale = max(abs(lhs), np.finfo(float).tiny)
        relative_to_lhs = abs(residual) / target_scale
        tolerance = abs_limit + rel_limit * scale
        candidate = {
            "absolute_residual": abs(residual),
            "scale": scale,
            "native_lhs_rhs_scale": native_scale,
            "residual_over_scale": normalized,
            "residual_over_native_lhs_rhs_scale": abs(residual) / native_scale,
            "residual_over_lhs": relative_to_lhs,
            "rel_limit": rel_limit,
            "abs_limit": abs_limit,
            "context": context,
            "lhs": lhs,
            "rhs": rhs,
        }
        previous = self.error_metrics.get(name)
        if previous is None or candidate["residual_over_scale"] > previous["residual_over_scale"]:
            self.error_metrics[name] = candidate
        if abs(residual) > tolerance:
            self.failures.append(
                f"{name} exceeds scale-aware tolerance at {context}: "
                f"lhs={lhs:.17g}, rhs={rhs:.17g}, residual={residual:.17g}, "
                f"residual/scale={normalized:.3e}, limit={rel_limit:.3e}"
            )

    def array_residual(
        self,
        name: str,
        lhs: np.ndarray,
        rhs: np.ndarray,
        context: str,
        *,
        rel_limit: float = 2.0e-12,
        abs_limit: float = 1.0e-12,
    ) -> None:
        self.require(lhs.shape == rhs.shape, f"{name} shape mismatch at {context}: {lhs.shape} != {rhs.shape}")
        if lhs.shape != rhs.shape:
            return
        finite = np.isfinite(lhs) & np.isfinite(rhs)
        self.require(bool(np.all(finite)), f"{name} contains non-finite values at {context}")
        if not np.all(finite):
            return
        diff = np.abs(lhs - rhs)
        scale_array = np.maximum(np.maximum(np.abs(lhs), np.abs(rhs)), np.finfo(float).tiny)
        normalized_array = diff / scale_array
        flat = int(np.argmax(normalized_array))
        index = np.unravel_index(flat, lhs.shape)
        candidate = {
            "absolute_residual": float(diff[index]),
            "scale": float(scale_array[index]),
            "residual_over_scale": float(normalized_array[index]),
            "residual_over_lhs": float(diff[index] / max(abs(float(lhs[index])), np.finfo(float).tiny)),
            "rel_limit": rel_limit,
            "abs_limit": abs_limit,
            "context": f"{context}; index={index}",
            "lhs": float(lhs[index]),
            "rhs": float(rhs[index]),
        }
        previous = self.error_metrics.get(name)
        if previous is None or candidate["residual_over_scale"] > previous["residual_over_scale"]:
            self.error_metrics[name] = candidate
        failures = diff > abs_limit + rel_limit * scale_array
        self.require(not bool(np.any(failures)), f"{name} exceeds array tolerance at {candidate['context']}")


def infer_case_dirs(results_root: Path | None, supplied: Iterable[str], *, allow_partial: bool) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for item in supplied:
        if "=" not in item:
            raise ValueError(f"--case-dir must be CASE=PATH, got {item!r}")
        case, raw_path = item.split("=", 1)
        if case not in CASES or case in result:
            raise ValueError(f"invalid or duplicate case directory: {case}")
        result[case] = Path(raw_path)
    if results_root is not None:
        for case in CASES:
            candidate = results_root / case
            if case not in result and candidate.is_dir():
                result[case] = candidate
    missing = sorted(set(CASES) - set(result))
    if missing and not allow_partial:
        raise ValueError(f"missing case directories: {missing}")
    if not result:
        raise ValueError("no case result directories were found")
    return result


def verify_manifest(review: Review, case: str, case_dir: Path) -> dict[str, str]:
    path = case_dir / "output_manifest.json"
    manifest = load_json(path)
    review.require(isinstance(manifest, dict), f"{case}: output manifest is not a mapping")
    expected = {
        "energy_mass_budgets.csv",
        "density_pressure_drift.csv",
        "motion_extrema.csv",
        "final_motion_slice.npz",
        "final_motion_slice.png",
        "audit_metadata.json",
    }
    review.require(set(manifest) == expected, f"{case}: output manifest members differ: {sorted(manifest)}")
    disk_files = {entry.name for entry in case_dir.iterdir() if entry.is_file()}
    review.require(disk_files == expected | {"output_manifest.json"}, f"{case}: unexpected/missing output files: {sorted(disk_files)}")
    for name in sorted(expected & set(manifest)):
        digest = manifest[name]
        review.require(isinstance(digest, str) and SHA256_RE.fullmatch(digest) is not None,
                       f"{case}: invalid digest for {name}: {digest!r}")
        if (case_dir / name).is_file():
            review.require(sha256_file(case_dir / name) == digest, f"{case}: hash mismatch for {name}")
    return manifest


def geometric_region_contract(case: str, metadata: Mapping[str, Any], review: Review) -> dict[str, dict[str, float | int]]:
    contract = CASES[case]
    nz, ny, nx = contract["shape"]
    half_x, half_y, half_z = contract["half_widths"]
    edges_meta = metadata.get("domain_edges_kpc", {})
    for axis, half in (("x", half_x), ("y", half_y), ("z", half_z)):
        review.require(edges_meta.get(axis) == [-half, half], f"{case}: metadata {axis} domain is not [-{half},{half}]")
    dx, dy, dz = 2 * half_x / nx, 2 * half_y / ny, 2 * half_z / nz
    review.residual(f"{case}.uniform_cell_width_x", dx, 1.0, case, rel_limit=1e-15)
    review.residual(f"{case}.uniform_cell_width_y", dy, 1.0, case, rel_limit=1e-15)
    review.residual(f"{case}.uniform_cell_width_z", dz, 1.0, case, rel_limit=1e-15)
    x = np.linspace(-half_x + dx / 2, half_x - dx / 2, nx)
    y = np.linspace(-half_y + dy / 2, half_y - dy / 2, ny)
    z = np.linspace(-half_z + dz / 2, half_z - dz / 2, nz)
    xy2 = y[:, None] ** 2 + x[None, :] ** 2
    counts = {radius: 0 for radius in RADII}
    equality_100 = 0
    for z_value in z:
        r2 = xy2 + z_value**2
        for radius in RADII:
            counts[radius] += int(np.count_nonzero(r2 < radius**2))
        equality_100 += int(np.count_nonzero(r2 == 100.0**2))
    review.require(equality_100 == 0, f"{case}: a cell centre lies exactly on r=100 kpc")
    total = nz * ny * nx
    volume = dx * dy * dz
    regions: dict[str, dict[str, float | int]] = {
        "whole_grid": {"cell_count": total, "volume_kpc3": total * volume},
        "r_gt_100_kpc": {"cell_count": total - counts[100.0], "volume_kpc3": (total - counts[100.0]) * volume},
    }
    for radius in RADII:
        regions[f"r_lt_{radius:g}_kpc"] = {"cell_count": counts[radius], "volume_kpc3": counts[radius] * volume}
    for layers in BOUNDARY_LAYERS:
        count = total - (nz - 2 * layers) * (ny - 2 * layers) * (nx - 2 * layers)
        regions[f"boundary_layer_{layers}"] = {"cell_count": count, "volume_kpc3": count * volume}
    return regions


def validate_metadata(case: str, metadata: Mapping[str, Any], review: Review) -> None:
    contract = CASES[case]
    review.require(metadata.get("status") == "complete_existing_control_storage_and_motion_audit", f"{case}: incomplete audit status")
    review.require(metadata.get("method_version") == 2, f"{case}: unexpected method version")
    review.require(metadata.get("case") == case, f"{case}: metadata case mismatch")
    review.require(metadata.get("job_id") == contract["job_id"], f"{case}: job ID mismatch")
    review.require(metadata.get("snapshot_count") == 6, f"{case}: snapshot count is not six")
    review.require(metadata.get("shape_nz_ny_nx") == list(contract["shape"]), f"{case}: shape mismatch")
    review.require(abs(float(metadata.get("first_age_myr", math.nan))) <= 1e-6, f"{case}: first age is not zero")
    review.require(abs(float(metadata.get("last_age_myr", math.nan)) - 50.0) <= 1e-6, f"{case}: final age is not 50 Myr")
    verified = metadata.get("verified_control_contract", {})
    review.require(verified.get("case") == case and verified.get("job_id") == contract["job_id"], f"{case}: verified contract mismatch")
    review.require(verified.get("environment_sha256") == contract["environment_sha256"], f"{case}: environment hash mismatch")
    review.require(verified.get("expected_output_indices") == list(range(6)), f"{case}: output-index contract mismatch")
    boundaries = metadata.get("configuration", {}).get("Boundary", {})
    expected_boundaries = {f"X{axis}-{side}": "reflective" for axis in (1, 2, 3) for side in ("beg", "end")}
    review.require(all(boundaries.get(key) == value for key, value in expected_boundaries.items()), f"{case}: not all boundaries are reflective")
    parameters = metadata.get("configuration", {}).get("Parameters", {})
    for name in ("JET_START_TIME", "JET_END_TIME", "JET_ACTIVE_TIME"):
        try:
            value = float(parameters.get(name, "nan"))
        except ValueError:
            value = math.nan
        review.require(value == 0.0, f"{case}: {name} is not zero")
    review.require(metadata.get("comparison_energy_erg") == COMPARISON_ENERGY_ERG, f"{case}: comparison energy mismatch")
    review.require(metadata.get("boundary_layers") == list(BOUNDARY_LAYERS), f"{case}: boundary layer contract mismatch")
    review.require("full-cell centre" in metadata.get("radial_membership", ""), f"{case}: radial membership is not explicit")
    for source in metadata.get("analysis_sources", []):
        review.require(SHA256_RE.fullmatch(str(source.get("sha256", ""))) is not None,
                       f"{case}: invalid analysis-source hash for {source.get('path')}")


def check_local_analysis_sources(
    case: str,
    metadata: Mapping[str, Any],
    source_root: Path | None,
    review: Review,
) -> dict[str, Any]:
    if source_root is None:
        return {"checked_against_local_repository": False}
    records = []
    for source in metadata.get("analysis_sources", []):
        basename = Path(str(source.get("path", ""))).name
        local = source_root / "scripts" / "science" / basename
        review.require(local.is_file(), f"{case}: local analysis source is missing: {local}")
        if not local.is_file():
            continue
        digest = sha256_file(local)
        review.require(digest == source.get("sha256"), f"{case}: local/staged analysis source hash differs: {basename}")
        review.require(local.stat().st_size == source.get("size_bytes"), f"{case}: local/staged source size differs: {basename}")
        records.append({"basename": basename, "sha256": digest, "size_bytes": local.stat().st_size})
    return {"checked_against_local_repository": True, "sources": records}


def keyed(rows: Iterable[dict[str, str]], case: str, label: str, review: Review) -> dict[tuple[int, str], dict[str, str]]:
    result: dict[tuple[int, str], dict[str, str]] = {}
    for row in rows:
        review.require(row.get("case") == case, f"{case}: {label} row has wrong case")
        index = exact_int(row, "snapshot_index")
        region = row.get("region", "")
        key = (index, region)
        review.require(key not in result, f"{case}: duplicate {label} row {key}")
        result[key] = row
    return result


def check_budget_and_drift(
    case: str,
    case_dir: Path,
    metadata: Mapping[str, Any],
    geometric: Mapping[str, Mapping[str, float | int]],
    review: Review,
) -> tuple[dict[tuple[int, str], dict[str, str]], dict[str, Any]]:
    _, budget_rows = load_csv(case_dir / "energy_mass_budgets.csv")
    _, drift_rows = load_csv(case_dir / "density_pressure_drift.csv")
    budgets = keyed(budget_rows, case, "budget", review)
    drifts = keyed(drift_rows, case, "drift", review)
    expected_keys = {(index, region) for index in range(6) for region in EXPECTED_REGIONS}
    review.require(set(budgets) == expected_keys, f"{case}: budget key set mismatch")
    review.require(set(drifts) == expected_keys, f"{case}: drift key set mismatch")

    times: dict[int, float] = {}
    baseline_values: dict[tuple[str, str], float] = {}
    tracer_rows_checked = 0
    for key in sorted(expected_keys & set(budgets) & set(drifts)):
        index, region = key
        budget, drift = budgets[key], drifts[key]
        context = f"{case}/snapshot={index}/region={region}"
        time_budget = finite_float(budget, "time_myr")
        time_drift = finite_float(drift, "time_myr")
        review.residual(f"{case}.budget_drift_time", time_budget, time_drift, context, rel_limit=1e-14, abs_limit=1e-12)
        if index in times:
            review.residual(f"{case}.within_snapshot_time", time_budget, times[index], context, rel_limit=1e-14, abs_limit=1e-12)
        else:
            times[index] = time_budget
        expected_geometry = geometric[region]
        for row_name, row in (("budget", budget), ("drift", drift)):
            review.require(exact_int(row, "cell_count") == expected_geometry["cell_count"],
                           f"{context}: {row_name} cell count disagrees with independent geometry")
            review.residual(f"{case}.region_volume", finite_float(row, "volume_kpc3"),
                            float(expected_geometry["volume_kpc3"]), f"{context}/{row_name}", rel_limit=1e-14)
        for field in STORAGE:
            initial = finite_float(budget, f"initial_{field}")
            current = finite_float(budget, f"current_{field}")
            delta = finite_float(budget, f"delta_{field}")
            review.residual(f"{case}.delta_equals_current_minus_initial.{field}", delta, current - initial,
                            context, rel_limit=3e-12, scale_override=max(abs(initial), abs(current)))
            baseline_key = (region, field)
            if baseline_key in baseline_values:
                review.residual(f"{case}.baseline_repeated.{field}", initial, baseline_values[baseline_key],
                                context, rel_limit=2e-15)
            else:
                baseline_values[baseline_key] = initial
            ratio = optional_float(budget, f"delta_{field}_over_initial")
            if initial == 0.0:
                review.require(ratio is None, f"{context}: zero-initial {field} has a ratio")
            else:
                review.require(ratio is not None, f"{context}: missing initial ratio for {field}")
                if ratio is not None:
                    review.residual(f"{case}.delta_over_initial.{field}", ratio, delta / initial,
                                    context, rel_limit=3e-12, abs_limit=1e-15)
            if field in ENERGIES:
                comparison = finite_float(budget, f"delta_{field}_over_low_power_comparison")
                review.residual(f"{case}.delta_over_comparison.{field}", comparison,
                                delta / COMPARISON_ENERGY_ERG, context, rel_limit=3e-12, abs_limit=1e-15)
        for state in ("initial", "current", "delta"):
            total = finite_float(budget, f"{state}_total_energy_erg")
            components = sum(finite_float(budget, f"{state}_{field}") for field in COMPONENTS)
            storage_scale = None
            if state == "delta":
                storage_scale = max(abs(finite_float(budget, "initial_total_energy_erg")),
                                    abs(finite_float(budget, "current_total_energy_erg")))
            review.residual(f"{case}.component_total.{state}", total, components, context, rel_limit=3e-12,
                            scale_override=storage_scale)
        if index == 0:
            for field in STORAGE:
                review.residual(f"{case}.baseline_zero_delta.{field}", finite_float(budget, f"delta_{field}"),
                                0.0, context, rel_limit=0.0, abs_limit=0.0)
        for name in ("rho", "prs"):
            initial_mean = finite_float(drift, f"{name}_initial_volume_mean_code")
            current_mean = finite_float(drift, f"{name}_current_volume_mean_code")
            mean_fractional = finite_float(drift, f"{name}_volume_mean_fractional_change")
            minimum = finite_float(drift, f"{name}_min_fractional_change")
            maximum = finite_float(drift, f"{name}_max_fractional_change")
            review.require(initial_mean > 0 and current_mean > 0, f"{context}: non-positive {name} mean")
            review.require(minimum > -1.0, f"{context}: {name} fractional minimum implies non-positive state")
            review.require(minimum <= mean_fractional <= maximum, f"{context}: {name} mean fractional drift outside extrema")
            if index == 0:
                review.residual(f"{case}.baseline_drift_mean.{name}", mean_fractional, 0.0, context, rel_limit=0.0, abs_limit=0.0)
                review.residual(f"{case}.baseline_drift_min.{name}", minimum, 0.0, context, rel_limit=0.0, abs_limit=0.0)
                review.residual(f"{case}.baseline_drift_max.{name}", maximum, 0.0, context, rel_limit=0.0, abs_limit=0.0)
        review.residual(f"{case}.tracer_min", finite_float(drift, "tracer_min"), 0.0, context, rel_limit=0.0, abs_limit=0.0)
        review.residual(f"{case}.tracer_max", finite_float(drift, "tracer_max"), 0.0, context, rel_limit=0.0, abs_limit=0.0)
        review.require(exact_int(drift, "nonzero_tracer_cells") == 0, f"{context}: nonzero tracer cells reported")
        tracer_rows_checked += 1

    review.require(sorted(times) == list(range(6)), f"{case}: missing snapshot times")
    if sorted(times) == list(range(6)):
        ordered = [times[index] for index in range(6)]
        review.require(abs(ordered[0]) <= 1e-6, f"{case}: first CSV time is not zero")
        review.require(all(b > a for a, b in zip(ordered, ordered[1:])), f"{case}: CSV times not strictly increasing")
        review.require(abs(ordered[-1] - 50.0) <= 1e-6, f"{case}: final CSV time is not 50 Myr")
        review.residual(f"{case}.metadata_first_time", ordered[0], float(metadata["first_age_myr"]), case,
                        rel_limit=1e-14, abs_limit=1e-12)
        review.residual(f"{case}.metadata_last_time", ordered[-1], float(metadata["last_age_myr"]), case,
                        rel_limit=1e-14, abs_limit=1e-12)

    # r<100 and r>100 are an exhaustive partition because the independent
    # geometry check established that no cell centre lies at exactly 100 kpc.
    for index in range(6):
        if not all((index, region) in budgets for region in ("whole_grid", "r_lt_100_kpc", "r_gt_100_kpc")):
            continue
        whole = budgets[(index, "whole_grid")]
        inner = budgets[(index, "r_lt_100_kpc")]
        outer = budgets[(index, "r_gt_100_kpc")]
        context = f"{case}/snapshot={index}/r100_partition"
        review.require(exact_int(whole, "cell_count") == exact_int(inner, "cell_count") + exact_int(outer, "cell_count"),
                       f"{context}: cell counts do not partition")
        review.residual(f"{case}.r100_partition.volume", finite_float(whole, "volume_kpc3"),
                        finite_float(inner, "volume_kpc3") + finite_float(outer, "volume_kpc3"), context,
                        rel_limit=1e-14)
        for state in ("initial", "current", "delta"):
            for field in STORAGE:
                storage_scale = None
                if state == "delta":
                    storage_scale = max(abs(finite_float(whole, f"initial_{field}")),
                                        abs(finite_float(whole, f"current_{field}")))
                review.residual(f"{case}.r100_partition.{state}.{field}", finite_float(whole, f"{state}_{field}"),
                                finite_float(inner, f"{state}_{field}") + finite_float(outer, f"{state}_{field}"),
                                context, rel_limit=4e-12, scale_override=storage_scale)
        for name in ("rho", "prs"):
            for suffix in ("initial_volume_mean_code", "current_volume_mean_code", "volume_mean_fractional_change"):
                whole_sum = finite_float(drifts[(index, "whole_grid")], f"{name}_{suffix}") * finite_float(whole, "volume_kpc3")
                inner_sum = finite_float(drifts[(index, "r_lt_100_kpc")], f"{name}_{suffix}") * finite_float(inner, "volume_kpc3")
                outer_sum = finite_float(drifts[(index, "r_gt_100_kpc")], f"{name}_{suffix}") * finite_float(outer, "volume_kpc3")
                review.residual(f"{case}.r100_partition.drift.{name}.{suffix}", whole_sum, inner_sum + outer_sum,
                                context, rel_limit=4e-12)

    # Positive stored quantities must grow monotonically with nested radial
    # apertures and boundary-layer thickness. Signed changes need not.
    radial_regions = [f"r_lt_{radius:g}_kpc" for radius in RADII]
    boundary_regions = [f"boundary_layer_{layers}" for layers in BOUNDARY_LAYERS]
    for index in range(6):
        for family, regions in (("radial", radial_regions), ("boundary", boundary_regions)):
            rows = [budgets[(index, region)] for region in regions if (index, region) in budgets]
            if len(rows) != len(regions):
                continue
            counts = [exact_int(row, "cell_count") for row in rows]
            volumes = [finite_float(row, "volume_kpc3") for row in rows]
            review.require(all(b > a for a, b in zip(counts, counts[1:])), f"{case}/snapshot={index}: {family} counts not nested")
            review.require(all(b > a for a, b in zip(volumes, volumes[1:])), f"{case}/snapshot={index}: {family} volumes not nested")
            for state in ("initial", "current"):
                for field in STORAGE:
                    values = [finite_float(row, f"{state}_{field}") for row in rows]
                    slack = 5e-14 * max(max(map(abs, values)), np.finfo(float).tiny)
                    review.require(all(b + slack >= a for a, b in zip(values, values[1:])),
                                   f"{case}/snapshot={index}: {family} {state} {field} not nested")

    final = budgets.get((5, "whole_grid"), {})
    radial_final = {}
    for region in (*radial_regions, "r_gt_100_kpc"):
        row = budgets.get((5, region), {})
        radial_final[region] = {f"delta_{field}": finite_float(row, f"delta_{field}") for field in STORAGE} if row else {}
    final_local_drift = {}
    for region in (*radial_regions, "r_gt_100_kpc", *(f"boundary_layer_{layers}" for layers in BOUNDARY_LAYERS)):
        row = drifts.get((5, region))
        if row is None:
            continue
        final_local_drift[region] = {
            f"{name}_{suffix}": finite_float(row, f"{name}_{suffix}")
            for name in ("rho", "prs")
            for suffix in ("volume_mean_fractional_change", "min_fractional_change", "max_fractional_change")
        }
    summary = {
        "snapshot_times_myr": [times[index] for index in sorted(times)],
        "tracer_rows_checked_zero": tracer_rows_checked,
        "final_whole_grid": {f"delta_{field}": finite_float(final, f"delta_{field}") for field in STORAGE} if final else {},
        "final_whole_grid_energy_over_comparison": {
            field: finite_float(final, f"delta_{field}_over_low_power_comparison") for field in ENERGIES
        } if final else {},
        "final_radial_partitions": radial_final,
        "final_local_density_pressure_drift": final_local_drift,
    }
    return budgets, summary


def expected_coordinate(index: int, cells: int, half_width: float) -> float:
    width = 2.0 * half_width / cells
    return -half_width + (index + 0.5) * width


def row_in_region(row: Mapping[str, str], region: str, shape: tuple[int, int, int]) -> bool:
    iz, iy, ix = (exact_int(row, name) for name in ("iz", "iy", "ix"))
    radius = finite_float(row, "radius_kpc")
    if region == "whole_grid":
        return True
    if region == "r_gt_100_kpc":
        return radius > 100.0
    match = re.fullmatch(r"r_lt_(\d+)_kpc", region)
    if match:
        return radius < float(match.group(1))
    match = re.fullmatch(r"boundary_layer_(\d+)", region)
    if match:
        layers = int(match.group(1))
        nz, ny, nx = shape
        return iz < layers or iz >= nz - layers or iy < layers or iy >= ny - layers or ix < layers or ix >= nx - layers
    return False


def check_extrema(
    case: str,
    case_dir: Path,
    budgets: Mapping[tuple[int, str], Mapping[str, str]],
    review: Review,
) -> tuple[dict[tuple[int, str, str], dict[str, str]], dict[str, Any]]:
    _, rows = load_csv(case_dir / "motion_extrema.csv")
    contract = CASES[case]
    shape = contract["shape"]
    half_x, half_y, half_z = contract["half_widths"]
    extrema: dict[tuple[int, str, str], dict[str, str]] = {}
    for row in rows:
        review.require(row.get("case") == case, f"{case}: extrema row has wrong case")
        index = exact_int(row, "snapshot_index")
        region = row.get("region", "")
        extremum = row.get("extremum", "")
        key = (index, region, extremum)
        review.require(key not in extrema, f"{case}: duplicate extrema row {key}")
        extrema[key] = row
        context = f"{case}/snapshot={index}/region={region}/{extremum}"
        review.require(extremum in ("maximum_speed", "maximum_mach"), f"{context}: unknown extremum")
        review.require((index, region) in budgets, f"{context}: no corresponding budget row")
        if (index, region) in budgets:
            budget = budgets[(index, region)]
            review.require(exact_int(row, "cell_count") == exact_int(budget, "cell_count"), f"{context}: cell count mismatch")
            review.residual(f"{case}.extrema_budget_volume", finite_float(row, "volume_kpc3"),
                            finite_float(budget, "volume_kpc3"), context, rel_limit=1e-14)
            review.residual(f"{case}.extrema_budget_time", finite_float(row, "time_myr"),
                            finite_float(budget, "time_myr"), context, rel_limit=1e-14, abs_limit=1e-12)
        iz, iy, ix = (exact_int(row, name) for name in ("iz", "iy", "ix"))
        nz, ny, nx = shape
        review.require(0 <= iz < nz and 0 <= iy < ny and 0 <= ix < nx, f"{context}: index outside grid")
        x = finite_float(row, "x_kpc")
        y = finite_float(row, "y_kpc")
        z = finite_float(row, "z_kpc")
        review.residual(f"{case}.extrema_coordinate_x", x, expected_coordinate(ix, nx, half_x), context,
                        rel_limit=1e-14, abs_limit=1e-12)
        review.residual(f"{case}.extrema_coordinate_y", y, expected_coordinate(iy, ny, half_y), context,
                        rel_limit=1e-14, abs_limit=1e-12)
        review.residual(f"{case}.extrema_coordinate_z", z, expected_coordinate(iz, nz, half_z), context,
                        rel_limit=1e-14, abs_limit=1e-12)
        radius = math.sqrt(x * x + y * y + z * z)
        review.residual(f"{case}.extrema_radius", finite_float(row, "radius_kpc"), radius, context,
                        rel_limit=2e-14, abs_limit=1e-12)
        distances = (x + half_x, half_x - x, y + half_y, half_y - y, z + half_z, half_z - z)
        faces = ("x_negative", "x_positive", "y_negative", "y_positive", "z_negative", "z_positive")
        nearest_index = int(np.argmin(distances))
        review.require(row.get("nearest_boundary") == faces[nearest_index], f"{context}: nearest boundary mismatch")
        review.residual(f"{case}.extrema_boundary_distance", finite_float(row, "boundary_distance_kpc"),
                        distances[nearest_index], context, rel_limit=1e-14, abs_limit=1e-12)
        vx, vy, vz = (finite_float(row, name) for name in ("vx_km_s", "vy_km_s", "vz_km_s"))
        speed = math.sqrt(vx * vx + vy * vy + vz * vz)
        reported_speed = finite_float(row, "speed_km_s")
        review.residual(f"{case}.extrema_speed_vector", reported_speed, speed, context, rel_limit=3e-12, abs_limit=1e-12)
        sound = finite_float(row, "sound_speed_km_s")
        review.require(sound > 0.0, f"{context}: non-positive sound speed")
        rho, prs = finite_float(row, "rho_code"), finite_float(row, "prs_code")
        review.require(rho > 0.0 and prs > 0.0, f"{context}: non-positive primitive")
        derived_sound = math.sqrt(GAMMA_GAS * prs / rho) * UNIT_VELOCITY_CMS / 1e5
        review.residual(f"{case}.extrema_sound_speed", sound, derived_sound, context, rel_limit=3e-12)
        mach = finite_float(row, "mach")
        review.residual(f"{case}.extrema_mach", mach, reported_speed / sound, context, rel_limit=3e-12, abs_limit=1e-15)
        radial = (vx * x + vy * y + vz * z) / radius if radius else 0.0
        review.residual(f"{case}.extrema_radial_velocity", finite_float(row, "radial_velocity_km_s"), radial,
                        context, rel_limit=3e-12, abs_limit=1e-12)
        expected_extremum = reported_speed if extremum == "maximum_speed" else mach
        review.residual(f"{case}.extremum_value", finite_float(row, "extremum_value"), expected_extremum,
                        context, rel_limit=3e-12, abs_limit=1e-15)
        review.require(row_in_region(row, region, shape), f"{context}: extremum location is outside its region")
        review.residual(f"{case}.extrema_tracer", finite_float(row, "tracer"), 0.0, context,
                        rel_limit=0.0, abs_limit=0.0)

    expected_keys = {(index, region, extremum) for index in range(6) for region in EXPECTED_REGIONS
                     for extremum in ("maximum_speed", "maximum_mach")}
    review.require(set(extrema) == expected_keys, f"{case}: extrema key set mismatch")

    timecourse = []
    for index in range(6):
        for extremum_name in ("maximum_speed", "maximum_mach"):
            whole = extrema.get((index, "whole_grid", extremum_name))
            inner = extrema.get((index, "r_lt_100_kpc", extremum_name))
            outer = extrema.get((index, "r_gt_100_kpc", extremum_name))
            if not (whole and inner and outer):
                continue
            whole_value = finite_float(whole, "extremum_value")
            partition_value = max(finite_float(inner, "extremum_value"), finite_float(outer, "extremum_value"))
            review.residual(f"{case}.r100_extremum_partition.{extremum_name}", whole_value, partition_value,
                            f"{case}/snapshot={index}", rel_limit=3e-12, abs_limit=1e-15)
            for region in EXPECTED_REGIONS[1:]:
                candidate = extrema.get((index, region, extremum_name))
                if candidate:
                    tolerance = 3e-12 * max(abs(whole_value), 1.0)
                    review.require(finite_float(candidate, "extremum_value") <= whole_value + tolerance,
                                   f"{case}/snapshot={index}: {region} {extremum_name} exceeds whole-grid maximum")
        speed_row = extrema.get((index, "whole_grid", "maximum_speed"))
        mach_row = extrema.get((index, "whole_grid", "maximum_mach"))
        outer_speed = extrema.get((index, "r_gt_100_kpc", "maximum_speed"))
        outer_mach = extrema.get((index, "r_gt_100_kpc", "maximum_mach"))
        if not all((speed_row, mach_row, outer_speed, outer_mach)):
            continue
        speed_layers = [layers for layers in BOUNDARY_LAYERS if row_in_region(speed_row, f"boundary_layer_{layers}", shape)]
        mach_layers = [layers for layers in BOUNDARY_LAYERS if row_in_region(mach_row, f"boundary_layer_{layers}", shape)]
        for extremum_name, row, layers_hit in (("maximum_speed", speed_row, speed_layers),
                                               ("maximum_mach", mach_row, mach_layers)):
            for layers in layers_hit:
                boundary = extrema.get((index, f"boundary_layer_{layers}", extremum_name))
                if boundary:
                    review.residual(f"{case}.boundary_contains_global.{extremum_name}.L{layers}",
                                    finite_float(boundary, "extremum_value"), finite_float(row, "extremum_value"),
                                    f"{case}/snapshot={index}", rel_limit=3e-12, abs_limit=1e-15)
        timecourse.append({
            "snapshot_index": index,
            "time_myr": finite_float(speed_row, "time_myr"),
            "whole_max_speed_km_s": finite_float(speed_row, "speed_km_s"),
            "whole_max_speed_mach": finite_float(speed_row, "mach"),
            "whole_max_speed_location_zyx": [exact_int(speed_row, name) for name in ("iz", "iy", "ix")],
            "whole_max_speed_radius_kpc": finite_float(speed_row, "radius_kpc"),
            "whole_max_speed_nearest_boundary": speed_row["nearest_boundary"],
            "whole_max_speed_boundary_distance_kpc": finite_float(speed_row, "boundary_distance_kpc"),
            "whole_max_speed_boundary_layers": speed_layers,
            "whole_max_mach": finite_float(mach_row, "mach"),
            "whole_max_mach_speed_km_s": finite_float(mach_row, "speed_km_s"),
            "whole_max_mach_location_zyx": [exact_int(mach_row, name) for name in ("iz", "iy", "ix")],
            "whole_max_mach_nearest_boundary": mach_row["nearest_boundary"],
            "whole_max_mach_boundary_distance_kpc": finite_float(mach_row, "boundary_distance_kpc"),
            "whole_max_mach_boundary_layers": mach_layers,
            "outer_max_speed_km_s": finite_float(outer_speed, "speed_km_s"),
            "outer_max_mach": finite_float(outer_mach, "mach"),
        })
    return extrema, {"motion_timecourse": timecourse}


def check_slice(
    case: str,
    case_dir: Path,
    metadata: Mapping[str, Any],
    extrema: Mapping[tuple[int, str, str], Mapping[str, str]],
    review: Review,
) -> dict[str, Any]:
    path = case_dir / "final_motion_slice.npz"
    required = {
        "x_kpc", "z_kpc", "y_kpc", "x_edges_kpc", "z_edges_kpc", "selected_y_index",
        "maximum_indices_zyx", "time_myr", "array_axis_order", "initial_rho_code", "initial_prs_code",
        "initial_vx1_code", "initial_vx2_code", "initial_vx3_code", "current_rho_code", "current_prs_code",
        "current_vx1_code", "current_vx2_code", "current_vx3_code", "speed_km_s", "mach",
        "rho_fractional_change", "prs_fractional_change",
    }
    with np.load(path, allow_pickle=False) as payload:
        review.require(set(payload.files) == required, f"{case}: NPZ member set mismatch: {sorted(payload.files)}")
        if not required.issubset(payload.files):
            return {}
        contract = CASES[case]
        nz, ny, nx = contract["shape"]
        half_x, _, half_z = contract["half_widths"]
        x = np.asarray(payload["x_kpc"], dtype=float)
        z = np.asarray(payload["z_kpc"], dtype=float)
        x_edges = np.asarray(payload["x_edges_kpc"], dtype=float)
        z_edges = np.asarray(payload["z_edges_kpc"], dtype=float)
        review.array_residual(f"{case}.slice_x", x, np.linspace(-half_x + 0.5, half_x - 0.5, nx), case,
                              rel_limit=1e-14, abs_limit=1e-12)
        review.array_residual(f"{case}.slice_z", z, np.linspace(-half_z + 0.5, half_z - 0.5, nz), case,
                              rel_limit=1e-14, abs_limit=1e-12)
        review.array_residual(f"{case}.slice_x_edges", x_edges, np.linspace(-half_x, half_x, nx + 1), case,
                              rel_limit=1e-14, abs_limit=1e-12)
        review.array_residual(f"{case}.slice_z_edges", z_edges, np.linspace(-half_z, half_z, nz + 1), case,
                              rel_limit=1e-14, abs_limit=1e-12)
        review.require(str(np.asarray(payload["array_axis_order"]).item()) == "z,x", f"{case}: slice axis order mismatch")
        indices = tuple(int(value) for value in np.asarray(payload["maximum_indices_zyx"]).tolist())
        review.require(len(indices) == 3, f"{case}: invalid maximum index tuple")
        selected_y = int(np.asarray(payload["selected_y_index"]).item())
        if len(indices) == 3:
            review.require(selected_y == indices[1], f"{case}: selected slice does not contain maximum-speed y index")
        final_row = extrema.get((5, "whole_grid", "maximum_speed"))
        if final_row and len(indices) == 3:
            expected_indices = tuple(exact_int(final_row, name) for name in ("iz", "iy", "ix"))
            review.require(indices == expected_indices, f"{case}: NPZ maximum indices {indices} != extrema {expected_indices}")
            review.residual(f"{case}.slice_y_coordinate", float(np.asarray(payload["y_kpc"]).item()),
                            finite_float(final_row, "y_kpc"), case, rel_limit=1e-14, abs_limit=1e-12)
            review.residual(f"{case}.slice_time", float(np.asarray(payload["time_myr"]).item()),
                            finite_float(final_row, "time_myr"), case, rel_limit=1e-14, abs_limit=1e-12)
        array_names = required - {
            "x_kpc", "z_kpc", "y_kpc", "x_edges_kpc", "z_edges_kpc", "selected_y_index",
            "maximum_indices_zyx", "time_myr", "array_axis_order",
        }
        arrays = {name: np.asarray(payload[name], dtype=float) for name in array_names}
        for name, values in arrays.items():
            review.require(values.shape == (nz, nx), f"{case}: slice {name} has shape {values.shape}")
            review.require(bool(np.all(np.isfinite(values))), f"{case}: slice {name} has non-finite values")
        if not all(values.shape == (nz, nx) for values in arrays.values()):
            return {}
        review.require(bool(np.all(arrays["initial_rho_code"] > 0) and np.all(arrays["current_rho_code"] > 0)),
                       f"{case}: slice has non-positive density")
        review.require(bool(np.all(arrays["initial_prs_code"] > 0) and np.all(arrays["current_prs_code"] > 0)),
                       f"{case}: slice has non-positive pressure")
        speed_code = np.sqrt(sum(arrays[f"current_vx{axis}_code"] ** 2 for axis in (1, 2, 3)))
        expected_speed = speed_code * UNIT_VELOCITY_CMS / 1e5
        expected_mach = speed_code / np.sqrt(GAMMA_GAS * arrays["current_prs_code"] / arrays["current_rho_code"])
        expected_rho_fractional = (arrays["current_rho_code"] - arrays["initial_rho_code"]) / arrays["initial_rho_code"]
        expected_prs_fractional = (arrays["current_prs_code"] - arrays["initial_prs_code"]) / arrays["initial_prs_code"]
        review.array_residual(f"{case}.slice_speed", arrays["speed_km_s"], expected_speed, case,
                              rel_limit=3e-12, abs_limit=1e-12)
        review.array_residual(f"{case}.slice_mach", arrays["mach"], expected_mach, case,
                              rel_limit=3e-12, abs_limit=1e-15)
        review.array_residual(f"{case}.slice_rho_fractional", arrays["rho_fractional_change"],
                              expected_rho_fractional, case, rel_limit=3e-12, abs_limit=1e-15)
        review.array_residual(f"{case}.slice_prs_fractional", arrays["prs_fractional_change"],
                              expected_prs_fractional, case, rel_limit=3e-12, abs_limit=1e-15)
        slice_max = float(np.max(arrays["speed_km_s"]))
        if final_row and len(indices) == 3:
            iz, _, ix = indices
            review.residual(f"{case}.slice_marked_speed", float(arrays["speed_km_s"][iz, ix]),
                            finite_float(final_row, "speed_km_s"), case, rel_limit=3e-12, abs_limit=1e-12)
            review.residual(f"{case}.slice_global_speed", slice_max, finite_float(final_row, "speed_km_s"),
                            case, rel_limit=3e-12, abs_limit=1e-12)
            review.residual(f"{case}.slice_marked_rho", float(arrays["current_rho_code"][iz, ix]),
                            finite_float(final_row, "rho_code"), case, rel_limit=3e-12)
            review.residual(f"{case}.slice_marked_prs", float(arrays["current_prs_code"][iz, ix]),
                            finite_float(final_row, "prs_code"), case, rel_limit=3e-12)
        motion_meta = metadata.get("motion_slice", {})
        review.require(motion_meta.get("selected_y_index") == selected_y, f"{case}: metadata slice y index mismatch")
        review.require(tuple(motion_meta.get("maximum_indices_zyx", ())) == indices, f"{case}: metadata maximum indices mismatch")
        return {
            "selected_y_index": selected_y,
            "maximum_indices_zyx": list(indices),
            "slice_max_speed_km_s": slice_max,
            "slice_max_mach": float(np.max(arrays["mach"])),
        }


def check_receipts(
    case_metadata: Mapping[str, Mapping[str, Any]],
    receipt_path: Path,
    review: Review,
    *,
    allow_partial: bool,
) -> dict[str, Any]:
    receipt = load_json(receipt_path)
    review.require(receipt.get("unit_id") == EXPECTED_UNIT_ID, "migration receipt unit ID mismatch")
    review.require(receipt.get("payload_rehashed") is False, "checker input claims an unexpected payload rehash")
    inputs = receipt.get("inputs", [])
    review.require(isinstance(inputs, list) and len(inputs) == 12, "migration receipt must contain 12 HDF5 inputs")
    by_path: dict[str, Mapping[str, Any]] = {}
    relative_paths: set[str] = set()
    for item in inputs if isinstance(inputs, list) else []:
        path = str(item.get("archive_path", ""))
        relative = str(item.get("migration_relative_path", ""))
        review.require(path not in by_path, f"duplicate migration archive path: {path}")
        by_path[path] = item
        review.require(relative not in relative_paths, f"duplicate migration relative path: {relative}")
        relative_paths.add(relative)
        review.require(SHA256_RE.fullmatch(str(item.get("sha256_from_completed_migration", ""))) is not None,
                       f"invalid completed-migration SHA-256 for {path}")
        stat = item.get("live_stat_checked", {})
        review.require(set(stat) == {"size", "mtime_ns", "ctime_ns", "ino"}, f"invalid live stat signature for {path}")

    matched = 0
    case_hashes: dict[str, list[dict[str, Any]]] = {}
    for case, metadata in case_metadata.items():
        contract = CASES[case]
        snapshots = metadata.get("snapshot_files", [])
        review.require(isinstance(snapshots, list) and len(snapshots) == 6, f"{case}: metadata must list six snapshot files")
        seen_indices = set()
        case_hashes[case] = []
        for snapshot in snapshots if isinstance(snapshots, list) else []:
            path = str(snapshot.get("path", ""))
            item = by_path.get(path)
            review.require(item is not None, f"{case}: snapshot path is absent from migration receipt: {path}")
            if item is None:
                continue
            matched += 1
            relative = str(item["migration_relative_path"])
            review.require(relative.startswith(contract["migration_prefix"] + "/"),
                           f"{case}: migration path has wrong prefix: {relative}")
            match = SNAPSHOT_RE.fullmatch(Path(relative).name)
            review.require(match is not None, f"{case}: invalid snapshot basename in migration receipt: {relative}")
            if match:
                seen_indices.add(int(match.group(1)))
            stat = item["live_stat_checked"]
            comparisons = {
                "size_bytes": stat["size"],
                "mtime_ns": stat["mtime_ns"],
                "ctime_ns": stat["ctime_ns"],
                "inode": stat["ino"],
            }
            for metadata_name, receipt_value in comparisons.items():
                review.require(snapshot.get(metadata_name) == receipt_value,
                               f"{case}: {metadata_name} differs from completed-migration live signature for {path}")
            review.require(snapshot.get("sha256") is None, f"{case}: metadata unexpectedly claims a fresh raw hash")
            review.require("not_read" in str(snapshot.get("hash_status", "")), f"{case}: metadata does not disclose no fresh raw hash")
            case_hashes[case].append({
                "path": path,
                "migration_relative_path": relative,
                "sha256_from_completed_migration": item["sha256_from_completed_migration"],
                "live_stat_checked": stat,
            })
        review.require(seen_indices == set(range(6)), f"{case}: receipt-linked snapshot indices differ: {sorted(seen_indices)}")
    metadata_paths = {
        str(snapshot.get("path", "")) for metadata in case_metadata.values() for snapshot in metadata.get("snapshot_files", [])
    }
    expected_matched = 6 * len(case_metadata)
    review.require(matched == expected_matched, "not every available metadata snapshot matched a migration receipt")
    if allow_partial:
        review.require(metadata_paths.issubset(set(by_path)), "available metadata snapshot files are not a subset of migration receipts")
    else:
        review.require(matched == 12 and set(by_path) == metadata_paths,
                       "migration receipt inputs and metadata snapshot files are not a bijection")

    gate_path = receipt_path.with_name("migration_gate.json")
    gate_summary: dict[str, Any] = {"present": gate_path.is_file()}
    if gate_path.is_file():
        gate = load_json(gate_path)
        gate_summary.update({
            "stage": gate.get("stage"),
            "plan_hash": gate.get("plan_hash"),
            "unit_id": gate.get("unit_id"),
            "source": gate.get("source"),
            "destination": gate.get("destination"),
            "tombstone": gate.get("tombstone"),
        })
        review.require(gate.get("stage") == "complete", "migration gate stage is not complete")
        review.require(gate.get("plan_hash") == EXPECTED_PLAN_HASH, "migration gate plan hash mismatch")
        review.require(gate.get("unit_id") == EXPECTED_UNIT_ID, "migration gate unit ID mismatch")
    else:
        review.warnings.append("migration_gate.json absent; completion/plan state is inherited from the wrapper-created receipt package")
    return {
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "raw_payload_rehashed_by_checker": False,
        "linked_snapshot_count": matched,
        "migration_gate": gate_summary,
        "case_inputs": case_hashes,
    }


def boundary_energy_timecourse(
    case: str,
    budgets: Mapping[tuple[int, str], Mapping[str, str]],
) -> list[dict[str, Any]]:
    rows = []
    for index in range(6):
        whole = budgets.get((index, "whole_grid"))
        if whole is None:
            continue
        record: dict[str, Any] = {
            "snapshot_index": index,
            "time_myr": finite_float(whole, "time_myr"),
            "whole_delta_mass_g": finite_float(whole, "delta_mass_g"),
            "whole_delta_total_energy_erg": finite_float(whole, "delta_total_energy_erg"),
            "layers": {},
        }
        for layers in BOUNDARY_LAYERS:
            row = budgets.get((index, f"boundary_layer_{layers}"))
            if row is None:
                continue
            delta_mass = finite_float(row, "delta_mass_g")
            delta_energy = finite_float(row, "delta_total_energy_erg")
            record["layers"][str(layers)] = {
                "delta_mass_g": delta_mass,
                "delta_total_energy_erg": delta_energy,
                "delta_mass_over_initial_layer_mass": delta_mass / finite_float(row, "initial_mass_g"),
                "delta_energy_over_low_power_comparison": delta_energy / COMPARISON_ENERGY_ERG,
            }
        rows.append(record)
    return rows


def run(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    review = Review()
    case_dirs = infer_case_dirs(args.results_root, args.case_dir, allow_partial=args.allow_partial)
    metadata: dict[str, Mapping[str, Any]] = {}
    case_reports: dict[str, Any] = {}
    budget_maps: dict[str, Mapping[tuple[int, str], Mapping[str, str]]] = {}

    for case, case_dir in case_dirs.items():
        review.require(case_dir.is_dir(), f"{case}: result directory missing: {case_dir}")
        if not case_dir.is_dir():
            continue
        verify_manifest(review, case, case_dir)
        metadata_path = case_dir / "audit_metadata.json"
        if not metadata_path.is_file():
            review.failures.append(f"{case}: audit_metadata.json missing")
            continue
        case_metadata = load_json(metadata_path)
        metadata[case] = case_metadata
        validate_metadata(case, case_metadata, review)
        local_source_check = check_local_analysis_sources(case, case_metadata, args.source_root, review)
        geometric = geometric_region_contract(case, case_metadata, review)
        budgets, budget_summary = check_budget_and_drift(case, case_dir, case_metadata, geometric, review)
        budget_maps[case] = budgets
        extrema, extrema_summary = check_extrema(case, case_dir, budgets, review)
        slice_summary = check_slice(case, case_dir, case_metadata, extrema, review)
        case_reports[case] = {
            "result_directory": str(case_dir),
            "output_manifest_sha256": sha256_file(case_dir / "output_manifest.json"),
            "analysis_source_check": local_source_check,
            **budget_summary,
            **extrema_summary,
            "boundary_storage_timecourse": boundary_energy_timecourse(case, budgets),
            "final_slice": slice_summary,
        }

    expected_metadata = set(case_dirs)
    if set(metadata) == expected_metadata:
        provenance = check_receipts(metadata, args.receipts, review, allow_partial=args.allow_partial)
    else:
        provenance = {"raw_payload_rehashed_by_checker": False, "linked_snapshot_count": 0}
        review.failures.append("could not check migration receipts because case metadata was incomplete")

    report = {
        "status": "pass" if not review.failures else "fail",
        "audit_scope": "independent output-only check; raw HDF5 payloads neither read nor freshly hashed",
        "checks_evaluated": review.check_count,
        "failures": review.failures,
        "warnings": review.warnings,
        "scale_aware_floating_error": review.error_metrics,
        "provenance": provenance,
        "cases": case_reports,
        "scientific_limits": [
            "The checker validates internal consistency and migration identity, not an independent raw-cell re-integration.",
            "The controls use a uniform 400x400x500 grid and six reflective faces; production uses a stretched 960x960x1014 grid and outflow faces.",
            "Storage changes do not identify numerical, boundary, body-force or internal-source causation without corresponding flux/source diagnostics.",
            "The final NPZ slice independently checks the reported global maximum-speed cell, but cannot independently recover all 3-D extrema from raw fields.",
            "Each atmosphere is represented by one deterministic run; no replicate-run uncertainty is estimated.",
        ],
    }
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(json_ready(report), indent=2, sort_keys=True) + "\n")
    return (0 if not review.failures else 1), report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, help="Directory containing cluster_002003/ and group_002031/")
    parser.add_argument("--case-dir", action="append", default=[], metavar="CASE=PATH",
                        help="Explicit case result directory; may be repeated")
    parser.add_argument("--receipts", type=Path, required=True,
                        help="Downloaded run/control_migration_receipts.json")
    parser.add_argument("--allow-partial", action="store_true",
                        help="Review whichever case directories are present while a job is still running")
    parser.add_argument("--report", type=Path, help="Optional JSON report destination")
    parser.add_argument("--source-root", type=Path,
                        help="Optional repository root for cross-checking staged analysis-source hashes")
    args = parser.parse_args()
    try:
        code, report = run(args)
    except Exception as exc:
        print(f"independent_review_error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    print(json.dumps({
        "status": report["status"],
        "checks_evaluated": report["checks_evaluated"],
        "failure_count": len(report["failures"]),
        "warning_count": len(report["warnings"]),
        "report": str(args.report) if args.report else None,
    }, sort_keys=True))
    if report["failures"]:
        for failure in report["failures"][:20]:
            print(f"FAIL: {failure}", file=sys.stderr)
        if len(report["failures"]) > 20:
            print(f"FAIL: ... {len(report['failures']) - 20} additional failures", file=sys.stderr)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
