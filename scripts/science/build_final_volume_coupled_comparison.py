#!/usr/bin/env python3
"""Build the final volume-coupled sparse-radio comparison package."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


SIDES = ("negative_z", "positive_z", "bipolar_total")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_metric_csv(path: Path) -> dict[str, dict[str, str]]:
    return {row["metric"]: row for row in read_rows(path)}


def parse_float(value: Any, *, context: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be numeric") from exc
    return out


def finite_positive(value: float, *, context: str) -> float:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{context} must be finite and positive")
    return value


def threshold_label(threshold: float) -> str:
    return f"{threshold:.0e}"


def normalize_truth_row(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    for key in (
        "threshold",
        "time_myr",
        "cell_count",
        "volume_kpc3",
        "tracer_weighted_volume_kpc3",
        "mass_g",
        "thermal_energy_erg",
        "kinetic_energy_erg",
        "total_energy_erg",
        "z_min_kpc",
        "z_max_kpc",
    ):
        if key in row and row[key] != "":
            out[key] = parse_float(row[key], context=f"Level 2 {key}")
    return out


def find_level2_row(rows: list[dict[str, str]], *, threshold: float, side: str) -> dict[str, str]:
    for row in rows:
        if row.get("side") != side:
            continue
        row_threshold = parse_float(row.get("threshold"), context="Level 2 threshold")
        if math.isclose(row_threshold, threshold, rel_tol=0.0, abs_tol=threshold * 1.0e-8):
            return row
    raise ValueError(f"missing Level 2 truth row for threshold={threshold_label(threshold)} side={side}")


def select_declared_volumes(
    rows: list[dict[str, str]],
    *,
    threshold: float = 5.0e-3,
    tolerance: float = 1.0e-6,
) -> dict[str, dict[str, Any]]:
    selected = {side: normalize_truth_row(find_level2_row(rows, threshold=threshold, side=side)) for side in SIDES}

    for side in ("negative_z", "positive_z"):
        finite_positive(
            parse_float(selected[side]["volume_kpc3"], context=f"{side} volume_kpc3"),
            context=f"{side} volume_kpc3",
        )
    bipolar_volume = finite_positive(
        parse_float(selected["bipolar_total"]["volume_kpc3"], context="bipolar_total volume_kpc3"),
        context="bipolar_total volume_kpc3",
    )
    side_sum = float(selected["negative_z"]["volume_kpc3"]) + float(selected["positive_z"]["volume_kpc3"])
    if not math.isclose(side_sum, bipolar_volume, rel_tol=tolerance, abs_tol=tolerance):
        raise ValueError(
            "selected negative_z + positive_z volumes do not match bipolar_total "
            f"({side_sum} vs {bipolar_volume})"
        )
    return selected


def rows_by_side(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out = {row["side"]: row for row in rows}
    missing = sorted(set(SIDES) - set(out))
    if missing:
        raise ValueError(f"missing lobe summary sides: {', '.join(missing)}")
    return out


def validate_volume_coupled_bridge(
    truth: dict[str, dict[str, Any]],
    lobe_rows: list[dict[str, str]],
    metadata: dict[str, Any],
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, Any]:
    if metadata.get("loss_model_key") != "external_praise_compatible":
        raise ValueError("bridge metadata loss_model_key must be external_praise_compatible")
    volume_assignment = str(metadata.get("volume_assignment", ""))
    if "declared side volumes" not in volume_assignment:
        raise ValueError("bridge metadata must report declared side volumes")
    loss_table = metadata.get("loss_table") or {}
    if int(loss_table.get("extra_ids", 0)) != 0:
        raise ValueError("bridge metadata reports extra loss-table IDs")

    by_side = rows_by_side(lobe_rows)
    checked: dict[str, float] = {}
    for side in SIDES:
        observed = parse_float(by_side[side]["volume_kpc3"], context=f"{side} bridge volume_kpc3")
        expected = parse_float(truth[side]["volume_kpc3"], context=f"{side} truth volume_kpc3")
        if not math.isclose(observed, expected, rel_tol=tolerance, abs_tol=tolerance):
            raise ValueError(f"{side} bridge volume_kpc3 {observed} does not match truth {expected}")
        checked[side] = observed
    return {
        "loss_model_key": metadata["loss_model_key"],
        "volume_assignment": volume_assignment,
        "checked_volumes_kpc3": checked,
        "loss_table": loss_table,
    }


def lobe_value(row: dict[str, str], key: str) -> float:
    return parse_float(row[key], context=f"{row.get('side', 'lobe')} {key}")


def compare_lobes(
    old_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    old_by_side = rows_by_side(old_rows)
    new_by_side = rows_by_side(new_rows)
    out: list[dict[str, Any]] = []
    for side in SIDES:
        old = old_by_side[side]
        new = new_by_side[side]
        old_volume = lobe_value(old, "volume_kpc3")
        new_volume = lobe_value(new, "volume_kpc3")
        old_luminosity = lobe_value(old, "lossy_luminosity_doppler_w_hz")
        new_luminosity = lobe_value(new, "lossy_luminosity_doppler_w_hz")
        out.append(
            {
                "side": side,
                "old_volume_kpc3": old_volume,
                "new_volume_kpc3": new_volume,
                "volume_scale_factor": new_volume / old_volume if old_volume else math.nan,
                "old_lossy_luminosity_doppler_w_hz": old_luminosity,
                "new_lossy_luminosity_doppler_w_hz": new_luminosity,
                "luminosity_scale_factor": new_luminosity / old_luminosity if old_luminosity else math.nan,
                "old_particle_count": int(parse_float(old["particle_count"], context=f"{side} old particle_count")),
                "new_particle_count": int(parse_float(new["particle_count"], context=f"{side} new particle_count")),
            }
        )
    return out


def write_dict_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def metric_value(metrics: dict[str, dict[str, str]], key: str) -> float | None:
    if key not in metrics:
        return None
    return parse_float(metrics[key]["value"], context=f"metric {key}")


def build_summary_markdown(
    *,
    threshold: str,
    declared: dict[str, dict[str, Any]],
    comparison: list[dict[str, Any]],
    level1: dict[str, dict[str, str]],
) -> str:
    lines = [
        "# Final Volume-coupled Sparse Radio Comparison",
        "",
        f"Truth volume threshold: `{threshold}`.",
        "",
        "## Declared Volumes",
        "",
        "| Side | Volume (kpc^3) | Total energy (erg) |",
        "| --- | ---: | ---: |",
    ]
    for side in SIDES:
        row = declared[side]
        lines.append(
            f"| `{side}` | `{float(row['volume_kpc3']):.17g}` | "
            f"`{float(row.get('total_energy_erg', math.nan)):.17g}` |"
        )

    injected = metric_value(level1, "injected_energy_bipolar_elapsed")
    if injected is not None:
        lines.extend(["", f"Bipolar injected energy elapsed: `{injected:.6e} erg`."])

    lines.extend(
        [
            "",
            "## Scale Change",
            "",
            "| Side | Old volume | New volume | Volume scale | Old luminosity | New luminosity | Luminosity scale |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in comparison:
        lines.append(
            f"| `{row['side']}` | `{row['old_volume_kpc3']:.6g}` | `{row['new_volume_kpc3']:.6g}` | "
            f"`{row['volume_scale_factor']:.6g}` | `{row['old_lossy_luminosity_doppler_w_hz']:.6e}` | "
            f"`{row['new_lossy_luminosity_doppler_w_hz']:.6e}` | `{row['luminosity_scale_factor']:.6g}` |"
        )

    lines.extend(
        [
            "",
            "This package is a final-endpoint volume-coupling comparison product, not a publication-ready observable.",
            "",
        ]
    )
    return "\n".join(lines)


def build_package(
    *,
    truth_dir: Path,
    old_bridge_dir: Path,
    volume_coupled_bridge_dir: Path,
    output_dir: Path,
    threshold: float = 5.0e-3,
) -> dict[str, Any]:
    level1 = read_metric_csv(truth_dir / "level1_injected_energy.csv")
    level2_rows = read_rows(truth_dir / "level2_tracer_lobe_truth.csv")
    declared = select_declared_volumes(level2_rows, threshold=threshold)
    old_lobes = read_rows(old_bridge_dir / "sparse_particle_radio_lobe_summary.csv")
    new_lobes = read_rows(volume_coupled_bridge_dir / "sparse_particle_radio_lobe_summary.csv")
    new_metadata = json.loads((volume_coupled_bridge_dir / "sparse_particle_radio_metadata.json").read_text())
    bridge_validation = validate_volume_coupled_bridge(declared, new_lobes, new_metadata)
    comparison = compare_lobes(old_lobes, new_lobes)

    output_dir.mkdir(parents=True, exist_ok=True)
    declared_rows = [
        {
            "threshold": threshold_label(threshold),
            "side": side,
            "volume_kpc3": declared[side]["volume_kpc3"],
            "cell_count": declared[side].get("cell_count", ""),
            "total_energy_erg": declared[side].get("total_energy_erg", ""),
            "z_min_kpc": declared[side].get("z_min_kpc", ""),
            "z_max_kpc": declared[side].get("z_max_kpc", ""),
        }
        for side in SIDES
    ]
    write_dict_rows(output_dir / "declared_volume_truth.csv", declared_rows)
    write_dict_rows(output_dir / "lobe_volume_coupling_comparison.csv", comparison)

    metadata = {
        "threshold": threshold_label(threshold),
        "truth_dir": str(truth_dir),
        "old_bridge_dir": str(old_bridge_dir),
        "volume_coupled_bridge_dir": str(volume_coupled_bridge_dir),
        "declared_volumes_kpc3": {side: float(declared[side]["volume_kpc3"]) for side in SIDES},
        "bridge_validation": bridge_validation,
        "level1": level1,
    }
    (output_dir / "comparison_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (output_dir / "comparison_summary.md").write_text(
        build_summary_markdown(
            threshold=threshold_label(threshold),
            declared=declared,
            comparison=comparison,
            level1=level1,
        )
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth-dir", type=Path, required=True)
    parser.add_argument("--old-bridge-dir", type=Path, required=True)
    parser.add_argument("--volume-coupled-bridge-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=5.0e-3)
    args = parser.parse_args()
    metadata = build_package(
        truth_dir=args.truth_dir,
        old_bridge_dir=args.old_bridge_dir,
        volume_coupled_bridge_dir=args.volume_coupled_bridge_dir,
        output_dir=args.output_dir,
        threshold=args.threshold,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
