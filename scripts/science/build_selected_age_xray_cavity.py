#!/usr/bin/env python3
"""Assemble one case's selected-age X-ray cavity recovery product."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SCIENCE_DIR = Path(__file__).resolve().parent
for import_root in (ROOT, SCIENCE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from scripts.science import build_three_case_cavity_recovery as recovery_builder
from scripts.science.analyse_common_age_case import (
    _cavity_rows,
    _load_map,
    _truth_rows,
    finite,
)


CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
VIEWS = ("0deg", "45deg", "90deg")
DEPTHS = ("minor", "geometric", "major")
ENERGY_MODELS = (("pV", 1.0), ("2.5pV", 2.5), ("4pV", 4.0))
KPC_CM = 3.085_677_581_491_3673e21


class ProductError(ValueError):
    """Raised when the selected-age X-ray surface violates its contract."""


def read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ProductError(f"duplicate or missing header in {path}")
        rows = list(reader)
    if not rows:
        raise ProductError(f"empty table: {path}")
    return rows


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ProductError(f"refusing to write empty table: {path}")
    fields = list(rows[0])
    if len(fields) != len(set(fields)) or any(set(row) != set(fields) for row in rows):
        raise ProductError(f"inconsistent output schema for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def manifest_rows(path: Path, case: str) -> list[dict[str, str]]:
    selected = [row for row in read_rows(path) if row.get("case") == case]
    if len(selected) != len(AGES):
        raise ProductError(f"source manifest must contain five rows for {case}")
    by_age: dict[int, dict[str, str]] = {}
    for row in selected:
        age = int(row["snapshot_index"])
        if age not in AGES or age in by_age:
            raise ProductError(f"invalid or duplicate selected age: {case}/{age}")
        actual = finite(row["actual_time_myr"], context=f"actual age {case}/{age}", positive=True)
        if abs(actual - age) > 0.05:
            raise ProductError(f"selected age exceeds tolerance: {case}/{age}")
        if row.get("timestep") != f"Timestep_{age}":
            raise ProductError(f"timestep binding drifted: {case}/{age}")
        by_age[age] = row
    return [by_age[age] for age in AGES]


def _component_side_rows(components: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    if len(components) != 2:
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for component in components:
        if str(component.get("crosses_z_zero", "")).lower() in {"true", "1", "yes"}:
            return {}
        z = finite(component["centroid_z_kpc"], context="component centroid")
        side = "negative_z" if z < 0 else "positive_z" if z > 0 else ""
        if not side or side in result:
            return {}
        result[side] = component
    return result if set(result) == {"negative_z", "positive_z"} else {}


def build_energy_rows(
    *,
    case: str,
    snapshot_index: int,
    actual_time_myr: float,
    view: str,
    topology_class: str,
    components: Sequence[Mapping[str, Any]],
    cavity_context: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply ambient-pressure and topology gates to X-ray-derived volumes."""

    context = {row["side"]: row for row in cavity_context}
    if set(context) != {"negative_z", "positive_z"}:
        raise ProductError("cavity context must contain both tracer-proxy sides")
    component_sides = _component_side_rows(components)
    quantitative = bool(component_sides) and topology_class == "two_separate_components"
    rows: list[dict[str, Any]] = []
    for depth in DEPTHS:
        for model, factor in ENERGY_MODELS:
            if quantitative:
                side_rows = []
                for side in ("negative_z", "positive_z"):
                    component = component_sides[side]
                    pressure = finite(
                        context[side]["ambient_pressure_dyn_cm2"],
                        context=f"ambient pressure {case}/{snapshot_index}/{side}",
                        positive=True,
                    )
                    volume = finite(
                        component[f"volume_{depth}_depth_kpc3"],
                        context=f"X-ray volume {case}/{snapshot_index}/{side}/{depth}",
                        positive=True,
                    )
                    energy = pressure * volume * KPC_CM**3 * factor
                    row = {
                        "case": case,
                        "snapshot_index": snapshot_index,
                        "actual_time_myr": actual_time_myr,
                        "view": view,
                        "side": side,
                        "topology_class": topology_class,
                        "quantitative_energy_valid": True,
                        "volume_depth_assumption": f"{depth}_depth",
                        "energy_model": model,
                        "pressure_dyn_cm2": pressure,
                        "volume_kpc3": volume,
                        "energy_erg": energy,
                        "pressure_role": "tracer_shell_proxy_at_side_midpoint",
                    }
                    rows.append(row)
                    side_rows.append(row)
                rows.append({
                    **side_rows[0],
                    "side": "bipolar_total",
                    "pressure_dyn_cm2": sum(float(row["pressure_dyn_cm2"]) for row in side_rows) / 2.0,
                    "volume_kpc3": sum(float(row["volume_kpc3"]) for row in side_rows),
                    "energy_erg": sum(float(row["energy_erg"]) for row in side_rows),
                    "pressure_role": "sum_of_side_specific_energy_estimates",
                })
            else:
                pressure = sum(
                    finite(row["ambient_pressure_dyn_cm2"], context="ambient pressure", positive=True)
                    for row in context.values()
                ) / 2.0
                volume = sum(
                    finite(component[f"volume_{depth}_depth_kpc3"], context="X-ray volume", positive=True)
                    for component in components
                )
                rows.append({
                    "case": case,
                    "snapshot_index": snapshot_index,
                    "actual_time_myr": actual_time_myr,
                    "view": view,
                    "side": "bipolar_total",
                    "topology_class": topology_class,
                    "quantitative_energy_valid": False,
                    "volume_depth_assumption": f"{depth}_depth",
                    "energy_model": model,
                    "pressure_dyn_cm2": pressure,
                    "volume_kpc3": volume,
                    "energy_erg": pressure * volume * KPC_CM**3 * factor,
                    "pressure_role": "nonquantitative_bipolar_mean_shell_proxy",
                })
    return rows


def _figure(
    panels: Sequence[tuple[Any, Any]],
    *,
    case: str,
    output: Path,
) -> None:
    fig, axes = plt.subplots(5, 3, figsize=(11.8, 16.0), constrained_layout=True)
    image = None
    for axis, (loaded, analysis) in zip(axes.flat, panels, strict=True):
        extent = [
            float(loaded.horizontal_axis.min()),
            float(loaded.horizontal_axis.max()),
            float(loaded.z_axis.min()),
            float(loaded.z_axis.max()),
        ]
        image = axis.imshow(
            analysis.deficit,
            origin="lower",
            extent=extent,
            cmap="coolwarm",
            vmin=-0.5,
            vmax=0.5,
            aspect="auto",
        )
        axis.contour(
            loaded.horizontal_axis,
            loaded.z_axis,
            analysis.observer_mask,
            levels=[0.5],
            colors="#00a651",
            linewidths=1.0,
        )
        axis.contour(
            loaded.horizontal_axis,
            loaded.z_axis,
            loaded.tracer_max_los >= 5.0e-3,
            levels=[0.5],
            colors="black",
            linewidths=0.6,
        )
        axis.set_xlim(-120, 120)
        axis.set_ylim(-120, 120)
        axis.set_title(
            f"{analysis.summary_row['time_myr']:.1f} Myr | {loaded.spec.view} | "
            f"n={analysis.summary_row['component_count']}",
            fontsize=9,
        )
        axis.set_xlabel("projected horizontal (kpc)")
        axis.set_ylabel("z (kpc)")
    if image is None:
        raise ProductError("no panels available for the X-ray figure")
    fig.colorbar(image, ax=axes.ravel().tolist(), label="fractional X-ray deficit")
    fig.suptitle(
        f"{case} selected-age X-ray cavity recovery\n"
        "green: X-ray-only mask; black: tracer >= 5e-3 truth comparator",
        fontsize=13,
    )
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


def build_product(
    *,
    case: str,
    source_manifest: Path,
    analysis_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    if case not in CASES:
        raise ProductError(f"unsupported case: {case}")
    manifests = manifest_rows(source_manifest, case)
    if output_root.exists():
        raise ProductError(f"refusing to overwrite compact output: {output_root}")
    output_root.mkdir(parents=True)
    summaries: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    tracer: list[dict[str, Any]] = []
    sensitivity: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []
    level1: list[dict[str, Any]] = []
    level2: list[dict[str, Any]] = []
    cavity: list[dict[str, Any]] = []
    energies: list[dict[str, Any]] = []
    panels: list[tuple[Any, Any]] = []
    for manifest in manifests:
        snapshot = int(manifest["snapshot_index"])
        actual = float(manifest["actual_time_myr"])
        age_dir = analysis_root / f"age_{snapshot:02d}"
        age_level1, age_level2 = _truth_rows(age_dir, case, snapshot, actual)
        age_cavity = _cavity_rows(age_dir, case, snapshot, actual)
        level1.extend(age_level1)
        level2.extend(age_level2)
        cavity.extend(age_cavity)
        for view in VIEWS:
            loaded, projection = _load_map(age_dir, case, view, actual)
            analysis = recovery_builder.analyse_loaded_map(loaded, time_myr=actual)
            summary = {
                **analysis.summary_row,
                "snapshot_index": snapshot,
                "actual_time_myr": actual,
            }
            age_components = [
                {**row, "snapshot_index": snapshot, "actual_time_myr": actual}
                for row in analysis.component_rows
            ]
            summaries.append(summary)
            components.extend(age_components)
            tracer.extend(
                {**row, "snapshot_index": snapshot, "actual_time_myr": actual}
                for row in analysis.tracer_rows
            )
            sensitivity.extend(
                {**row, "snapshot_index": snapshot, "actual_time_myr": actual}
                for row in recovery_builder._sensitivity_rows(loaded)
            )
            projections.append({**projection, "snapshot_index": snapshot})
            energies.extend(build_energy_rows(
                case=case,
                snapshot_index=snapshot,
                actual_time_myr=actual,
                view=view,
                topology_class=str(summary["topology_class"]),
                components=age_components,
                cavity_context=age_cavity,
            ))
            panels.append((loaded, analysis))
    if len(summaries) != 15 or len(projections) != 15 or len(sensitivity) != 225:
        raise ProductError("selected-age X-ray/view/sensitivity coverage is incomplete")
    if len(level2) != 45 or len(cavity) != 10:
        raise ProductError("selected-age truth/cavity context coverage is incomplete")
    tables = {
        "xray_recovery_summary.csv": summaries,
        "xray_component_summary.csv": components or [{"status": "no_components"}],
        "projected_tracer_alignment.csv": tracer,
        "xray_method_sensitivity.csv": sensitivity,
        "projection_validation.csv": projections,
        "level1_truth.csv": level1,
        "level2_truth.csv": level2,
        "cavity_shell_context.csv": cavity,
        "xray_cavity_energy.csv": energies,
        "source_manifest.csv": manifests,
    }
    for name, rows in tables.items():
        write_rows(output_root / name, rows)
    _figure(panels, case=case, output=output_root / "selected_age_xray_cavity.png")
    provenance = []
    for row in manifests:
        source = Path(row["input_h5"])
        provenance.append({
            "case": case,
            "snapshot_index": row["snapshot_index"],
            "actual_time_myr": row["actual_time_myr"],
            "source_h5": str(source),
            "source_size_bytes": row["file_size_bytes"],
            "source_hash_status": "canonical_goal061_059_060_not_rehashed",
        })
    write_rows(output_root / "input_provenance.csv", provenance)
    metadata = {
        "status": "complete_selected_age_xray_cavity_product",
        "case": case,
        "snapshot_indices": list(AGES),
        "views": list(VIEWS),
        "observer_mask": "X-ray-only 1 percent projected-physical-area deficit tail",
        "tracer_role": "post_hoc truth comparison only",
        "quantitative_energy_gate": "exactly two non-crossing opposite-side X-ray components",
        "pressure_caveat": "ambient pressure is the tracer-shell midpoint proxy, not X-ray-fitted pressure",
        "table_row_counts": {name: len(rows) for name, rows in tables.items()},
    }
    write_json(output_root / "selected_age_xray_cavity_metadata.json", metadata)
    manifest_path = output_root / "local_asset_manifest.sha256"
    lines = []
    for path in sorted(output_root.iterdir()):
        if path.is_file() and path != manifest_path:
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    manifest_path.write_text("\n".join(lines) + "\n")
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=CASES)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = build_product(
        case=args.case,
        source_manifest=args.source_manifest,
        analysis_root=args.analysis_root,
        output_root=args.output_root,
    )
    print(f"status={metadata['status']} case={metadata['case']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
