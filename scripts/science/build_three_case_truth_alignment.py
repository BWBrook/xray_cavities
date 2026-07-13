#!/usr/bin/env python3
"""Package the accepted X-ray recovery products with Level 1/2 truth evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12"
REMOTE_PRODUCTS = DEFAULT_OUTPUT / "remote_products"
REMOTE_LOGS = DEFAULT_OUTPUT / "remote_logs"
CASES = ("C-HI", "C-LO", "G-LO")
VIEWS = ("0deg", "45deg", "90deg")
THRESHOLDS = ((1.0e-3, "1e-3"), (5.0e-3, "5e-3"), (1.0e-2, "1e-2"))
DEPTHS = ("minor", "geometric", "major")
KPC_CM = 3.0856775814913673e21
BASE_THRESHOLD = 5.0e-3
ARCHIVE_SHA256 = "474c06f81d09acdb616345bc56d7919738d894d317b0d98a1fee7f941b9d2e6b"
STDOUT_SHA256 = "e375354ab5a4d4c3d2f9e31065010fc7d3a48760886d8633a314078af5e5bd6f"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
JOB_ID = "756092.kunanyi-ohpc"


def _read_csv(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        header = reader.fieldnames
        if header is None:
            raise ValueError(f"empty CSV/TSV: {path}")
        if len(header) != len(set(header)):
            raise ValueError(f"duplicate header in {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"no data rows in {path}")
    return rows


def _float(value: Any, *, context: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric value for {context}: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"non-finite value for {context}: {value!r}")
    return result


def _numeric_row(row: dict[str, str], *, context: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if key in {"metric", "unit", "side", "threshold"}:
            result[key] = value
        else:
            try:
                result[key] = _float(value, context=f"{context}.{key}")
            except ValueError:
                result[key] = value
    return result


def parse_level1(path: Path) -> dict[str, float]:
    """Parse the Level 1 metric table, requiring the exact elapsed metric."""

    rows = _read_csv(path)
    selected = [row for row in rows if row.get("metric") == "injected_energy_bipolar_elapsed"]
    if len(selected) != 1:
        raise ValueError(f"expected exactly one elapsed bipolar Level 1 metric in {path}")
    result: dict[str, float] = {}
    for row in rows:
        if "metric" not in row or "value" not in row:
            raise ValueError(f"invalid Level 1 schema in {path}")
        result[row["metric"]] = _float(row["value"], context=f"{path}:{row['metric']}")
    return result


def _threshold_key(value: str | float) -> str:
    threshold = _float(value, context="tracer threshold")
    for numeric, label in THRESHOLDS:
        if threshold == numeric:
            return label
    raise ValueError(f"unexpected tracer threshold: {value!r}")


def parse_level2(path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """Parse all exact threshold/side Level 2 rows, including bipolar totals."""

    rows = _read_csv(path)
    parsed: dict[str, dict[str, dict[str, Any]]] = {label: {} for _, label in THRESHOLDS}
    for index, row in enumerate(rows, start=2):
        if row.get("side") not in {"negative_z", "positive_z", "bipolar_total"}:
            raise ValueError(f"invalid Level 2 side at {path}:{index}")
        threshold = _threshold_key(row.get("threshold", ""))
        side = row["side"]
        if side in parsed[threshold]:
            raise ValueError(f"duplicate Level 2 row for {threshold}/{side} in {path}")
        parsed[threshold][side] = _numeric_row(row, context=f"{path}:{index}")
    for _, label in THRESHOLDS:
        if set(parsed[label]) != {"negative_z", "positive_z", "bipolar_total"}:
            raise ValueError(f"incomplete Level 2 rows for threshold {label} in {path}")
    return parsed


def assign_component_sides(rows: Iterable[dict[str, Any]]) -> list[str]:
    """Map each X-ray component centroid to a unique physical z side."""

    sides: list[str] = []
    for row in rows:
        z = _float(row.get("centroid_z_kpc"), context="X-ray component centroid_z_kpc")
        if str(row.get("crosses_z_zero", "False")).strip().lower() in {"true", "1", "yes"}:
            raise ValueError("X-ray component crosses z=0")
        if z == 0.0:
            raise ValueError("X-ray component centroid is at zero")
        sides.append("negative_z" if z < 0.0 else "positive_z")
    if set(sides) != {"negative_z", "positive_z"} or len(sides) != 2:
        raise ValueError("each base view must have exactly one component per z side")
    return sides


def parse_cavity_shell(path: Path) -> list[dict[str, Any]]:
    """Parse and validate the two side-specific tracer-shell pressure rows."""

    rows = _read_csv(path)
    if len(rows) != 2 or {row.get("side") for row in rows} != {"negative_z", "positive_z"}:
        raise ValueError(f"cavity shell must have one row for each z side: {path}")
    parsed = [_numeric_row(row, context=f"{path}:{index}") for index, row in enumerate(rows, start=2)]
    for row in parsed:
        pressure = _float(row.get("ambient_pressure_dyn_cm2"), context=f"{path}:ambient pressure")
        if pressure <= 0.0:
            raise ValueError(f"ambient pressure must be positive in {path}")
    return parsed


def hybrid_pv(pressure_dyn_cm2: float, volume_kpc3: float) -> float:
    """Convert pressure times a kpc^3 volume to an erg pV proxy."""

    pressure = _float(pressure_dyn_cm2, context="hybrid pressure")
    volume = _float(volume_kpc3, context="hybrid volume")
    result = pressure * volume * KPC_CM**3
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError("hybrid pV is not finite and positive")
    return result


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    fields = list(rows[0])
    if len(fields) != len(set(fields)):
        raise ValueError(f"duplicate output header for {path}")
    if any(set(row) != set(fields) for row in rows):
        raise ValueError(f"inconsistent output schema for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(output_dir: Path) -> None:
    manifest = output_dir / "local_asset_manifest.sha256"
    lines = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path != manifest:
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output_dir).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n")


def verify_remote_inputs(remote_products: Path = REMOTE_PRODUCTS, remote_logs: Path = REMOTE_LOGS) -> dict[str, str]:
    """Verify the retrieved archive manifest and fixed remote completion evidence."""

    checksum_file = remote_products / "archive_checksums.sha256"
    for line in checksum_file.read_text().splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(None, 1)
        target = remote_products / relative.removeprefix("./")
        if not target.is_file():
            raise ValueError(f"archive checksum target is missing: {target}")
        observed = hashlib.sha256(target.read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"archive checksum mismatch for {target}")

    archive = remote_logs / "three_case_endpoint_truth_alignment_2026-07-12.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("retrieved archive SHA256 does not match the prescribed value")
    stdout = remote_logs / "three_case_endpoint_truth_alignment.out"
    stderr = remote_logs / "three_case_endpoint_truth_alignment.err"
    if hashlib.sha256(stdout.read_bytes()).hexdigest() != STDOUT_SHA256:
        raise ValueError("retrieved stdout SHA256 does not match the prescribed value")
    if stderr.read_bytes() != b"" or hashlib.sha256(stderr.read_bytes()).hexdigest() != EMPTY_SHA256:
        raise ValueError("retrieved stderr is not empty")
    log_text = stdout.read_text()
    markers = {
        "validation_marker_c_hi": "case_validation=passed case=C-HI level2_rows=9 cavity_rows=2",
        "validation_marker_c_lo": "case_validation=passed case=C-LO level2_rows=9 cavity_rows=2",
        "validation_marker_g_lo": "case_validation=passed case=G-LO level2_rows=9 cavity_rows=2",
        "validation_marker_all_cases": "three_case_truth_validation=passed",
    }
    if any(marker not in log_text for marker in markers.values()):
        raise ValueError("one or more remote validation markers are missing")
    return {
        "job_id": JOB_ID,
        "exit_status": "0",
        "stageout_status": "1",
        "walltime": "00:22:16",
        "archive_sha256": ARCHIVE_SHA256,
        "stdout_sha256": STDOUT_SHA256,
        "stderr_sha256": EMPTY_SHA256,
        **markers,
    }


def _source(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _case_paths(case: str) -> dict[str, Path]:
    base = REMOTE_PRODUCTS / "products" / case
    return {
        "level1": base / "truth/level1_injected_energy.csv",
        "level2": base / "truth/level2_tracer_lobe_truth.csv",
        "shell": base / "cavity/cavity_stub_summary.csv",
    }


def _load_base_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]], dict[str, list[dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    level1: dict[str, dict[str, Any]] = {}
    level2: dict[str, dict[str, dict[str, Any]]] = {}
    shells: dict[str, list[dict[str, Any]]] = {}
    for case in CASES:
        paths = _case_paths(case)
        level1[case] = parse_level1(paths["level1"])
        level2[case] = parse_level2(paths["level2"])
        shells[case] = parse_cavity_shell(paths["shell"])
    xray_dir = DEFAULT_OUTPUT
    xray_summary = [_numeric_row(row, context=f"{xray_dir}/xray_recovery_summary.csv") for row in _read_csv(xray_dir / "xray_recovery_summary.csv")]
    xray_components = [_numeric_row(row, context=f"{xray_dir}/xray_component_summary.csv") for row in _read_csv(xray_dir / "xray_component_summary.csv")]
    if len(xray_summary) != 9 or {(r["case"], r["view"]) for r in xray_summary} != {(c, v) for c in CASES for v in VIEWS}:
        raise ValueError("X-ray recovery summary must contain exactly the nine case/view rows")
    if len(xray_components) != 18:
        raise ValueError("X-ray component summary must contain exactly 18 rows")
    components_by_view: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in xray_components:
        components_by_view.setdefault((str(row["case"]), str(row["view"])), []).append(row)
    for key, rows in components_by_view.items():
        if len(rows) != 2:
            raise ValueError(f"wrong component count for {key}")
        sides = assign_component_sides(rows)
        for row, side in zip(rows, sides, strict=True):
            row["z_side"] = side
    if set(components_by_view) != {(c, v) for c in CASES for v in VIEWS}:
        raise ValueError("X-ray components do not cover all case/view combinations")
    return level1, level2, shells, xray_summary, xray_components


def _case_summary_rows(level1: dict[str, dict[str, Any]], level2: dict[str, dict[str, dict[str, Any]]], shells: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for case in CASES:
        base = level2[case]["5e-3"]["bipolar_total"]
        pressure = {row["side"]: _float(row["ambient_pressure_dyn_cm2"], context=f"{case}:{row['side']} pressure") for row in shells[case]}
        rows.append({
            "case": case,
            "base_tracer_threshold": BASE_THRESHOLD,
            "level1_injected_energy_bipolar_elapsed_erg": level1[case]["injected_energy_bipolar_elapsed"],
            "base_level2_volume_kpc3": base["volume_kpc3"],
            "base_level2_tracer_weighted_volume_kpc3": base["tracer_weighted_volume_kpc3"],
            "base_level2_total_energy_erg": base["total_energy_erg"],
            "base_level2_thermal_energy_erg": base["thermal_energy_erg"],
            "base_level2_kinetic_energy_erg": base["kinetic_energy_erg"],
            "negative_z_ambient_pressure_dyn_cm2": pressure["negative_z"],
            "positive_z_ambient_pressure_dyn_cm2": pressure["positive_z"],
            "case_mean_pressure_dyn_cm2": (pressure["negative_z"] + pressure["positive_z"]) / 2.0,
            "pressure_convention": "side_specific_tracer_shell_pressure_for_alignment",
            "energy_interpretation": "hybrid_tracer_pressure_xray_volume_proxy",
        })
    return rows


def _threshold_rows(level2: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for case in CASES:
        for numeric, label in THRESHOLDS:
            source = level2[case][label]["bipolar_total"]
            row: dict[str, Any] = {"case": case, "tracer_threshold": numeric, "tracer_threshold_label": label, "source_side": "bipolar_total"}
            for key, value in source.items():
                if key not in {"threshold", "side"}:
                    row[key] = value
            row["is_base_threshold"] = label == "5e-3"
            rows.append(row)
    return rows


def _shell_rows(shells: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for case in CASES:
        for source in shells[case]:
            row = {"case": case, "source_file": _source(_case_paths(case)["shell"]), "pressure_context_role": "tracer_shell_ambient_context", **source}
            rows.append(row)
    return rows


def _alignment_rows(level1: dict[str, dict[str, Any]], level2: dict[str, dict[str, dict[str, Any]]], shells: dict[str, list[dict[str, Any]]], xray_summary: list[dict[str, Any]], xray_components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_by_key = {(str(row["case"]), str(row["view"])): row for row in xray_summary}
    components_by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in xray_components:
        components_by_key.setdefault((str(row["case"]), str(row["view"])), {})[row["z_side"]] = row
    rows = []
    for case in CASES:
        pressure = {row["side"]: row["ambient_pressure_dyn_cm2"] for row in shells[case]}
        base = level2[case]["5e-3"]["bipolar_total"]
        for view in VIEWS:
            source = summary_by_key[(case, view)]
            components = components_by_key[(case, view)]
            row: dict[str, Any] = {
                "case": case,
                "view": view,
                "time_myr": source["time_myr"],
                "level1_injected_energy_bipolar_elapsed_erg": level1[case]["injected_energy_bipolar_elapsed"],
                "base_level2_volume_kpc3": base["volume_kpc3"],
                "base_level2_total_energy_erg": base["total_energy_erg"],
                "negative_z_pressure_dyn_cm2": pressure["negative_z"],
                "positive_z_pressure_dyn_cm2": pressure["positive_z"],
                "pressure_context": "side_specific_tracer_shell",
                "energy_interpretation": "hybrid_tracer_pressure_xray_volume_proxy",
            }
            for depth in DEPTHS:
                depth_key = f"{depth}_depth"
                volumes = {side: components[side][f"volume_{depth_key}_kpc3"] for side in ("negative_z", "positive_z")}
                total_volume = volumes["negative_z"] + volumes["positive_z"]
                row[f"xray_volume_{depth_key}_negative_z_kpc3"] = volumes["negative_z"]
                row[f"xray_volume_{depth_key}_positive_z_kpc3"] = volumes["positive_z"]
                row[f"xray_volume_{depth_key}_kpc3"] = total_volume
                row[f"xray_volume_{depth_key}_over_level2_volume"] = total_volume / base["volume_kpc3"]
                side_pv = {side: hybrid_pv(pressure[side], volumes[side]) for side in volumes}
                total_pv = side_pv["negative_z"] + side_pv["positive_z"]
                for factor, name in ((1.0, "pV"), (2.5, "2_5pV"), (4.0, "4pV")):
                    side_values = {side: factor * side_pv[side] for side in side_pv}
                    total = factor * total_pv
                    row[f"hybrid_{name}_{depth_key}_negative_z_erg"] = side_values["negative_z"]
                    row[f"hybrid_{name}_{depth_key}_positive_z_erg"] = side_values["positive_z"]
                    row[f"hybrid_{name}_{depth_key}_erg"] = total
                    row[f"hybrid_{name}_{depth_key}_over_level1"] = total / level1[case]["injected_energy_bipolar_elapsed"]
                    row[f"hybrid_{name}_{depth_key}_over_level2"] = total / base["total_energy_erg"]
            rows.append(row)
    return rows


def _method_rows(level1: dict[str, dict[str, Any]], level2: dict[str, dict[str, dict[str, Any]]], shells: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    source_rows = [_numeric_row(row, context="method_sensitivity.csv") for row in _read_csv(DEFAULT_OUTPUT / "method_sensitivity.csv")]
    if len(source_rows) != 135:
        raise ValueError("method sensitivity input must contain exactly 135 rows")
    rows = []
    for source in source_rows:
        case = str(source["case"])
        base = level2[case]["5e-3"]["bipolar_total"]
        pressure = sum(row["ambient_pressure_dyn_cm2"] for row in shells[case]) / 2.0
        volume = _float(source["volume_geometric_depth_kpc3"], context="method sensitivity geometric volume")
        pv = hybrid_pv(pressure, volume)
        row = {**source, "xray_volume_geometric_depth_over_level2_volume": volume / base["volume_kpc3"], "pressure_convention": "case_mean_pressure_sensitivity_only", "case_mean_pressure_dyn_cm2": pressure, "hybrid_pV_geometric_depth_erg": pv, "hybrid_2_5pV_geometric_depth_erg": 2.5 * pv, "hybrid_4pV_geometric_depth_erg": 4.0 * pv, "hybrid_pV_geometric_depth_over_level1": pv / level1[case]["injected_energy_bipolar_elapsed"], "hybrid_2_5pV_geometric_depth_over_level1": 2.5 * pv / level1[case]["injected_energy_bipolar_elapsed"], "hybrid_4pV_geometric_depth_over_level1": 4.0 * pv / level1[case]["injected_energy_bipolar_elapsed"], "hybrid_pV_geometric_depth_over_level2": pv / base["total_energy_erg"], "hybrid_2_5pV_geometric_depth_over_level2": 2.5 * pv / base["total_energy_erg"], "hybrid_4pV_geometric_depth_over_level2": 4.0 * pv / base["total_energy_erg"], "energy_interpretation": "hybrid_tracer_pressure_xray_volume_proxy"}
        rows.append(row)
    return rows


def _completion_row(completion: dict[str, str]) -> list[dict[str, str]]:
    return [{**completion, "completion_interpretation": "retrieved_remote_postprocessing_evidence"}]


def _write_figure(output_dir: Path, alignment_rows: list[dict[str, Any]]) -> None:
    labels = [f"{row['case']}\n{row['view']}" for row in alignment_rows]
    x = np.arange(len(labels))
    series = (
        ("xray_volume_geometric_depth_over_level2_volume", "geometric X-ray volume / Level 2 volume"),
        ("hybrid_2_5pV_geometric_depth_over_level1", "adopted 2.5pV / Level 1 energy"),
        ("hybrid_2_5pV_geometric_depth_over_level2", "adopted 2.5pV / Level 2 energy"),
    )
    fig, axes = plt.subplots(3, 1, figsize=(13.0, 11.0), sharex=True, constrained_layout=True)
    for axis, (field, title) in zip(axes, series, strict=True):
        values = np.asarray([_float(row[field], context=field) for row in alignment_rows])
        axis.bar(x, values, color="#4472c4")
        axis.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
        axis.set_yscale("log")
        axis.set_ylabel("ratio")
        axis.set_title(title)
        axis.grid(axis="y", which="both", alpha=0.25)
    axes[-1].set_xticks(x, labels)
    axes[-1].set_xlabel("case / view")
    fig.suptitle("Three-case X-ray recovery truth alignment (50 Myr)", fontsize=15)
    fig.savefig(output_dir / "three_case_truth_alignment.png", dpi=180, facecolor="white")
    plt.close(fig)


def build_assets(output_dir: Path = DEFAULT_OUTPUT) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    completion = verify_remote_inputs()
    level1, level2, shells, xray_summary, xray_components = _load_base_inputs()
    case_rows = _case_summary_rows(level1, level2, shells)
    threshold_rows = _threshold_rows(level2)
    shell_rows = _shell_rows(shells)
    alignment_rows = _alignment_rows(level1, level2, shells, xray_summary, xray_components)
    method_rows = _method_rows(level1, level2, shells)
    _write_rows(output_dir / "case_truth_summary.csv", case_rows)
    _write_rows(output_dir / "truth_threshold_sensitivity.csv", threshold_rows)
    _write_rows(output_dir / "tracer_shell_pressure_context.csv", shell_rows)
    _write_rows(output_dir / "xray_truth_alignment.csv", alignment_rows)
    _write_rows(output_dir / "xray_truth_method_sensitivity.csv", method_rows)
    _write_rows(output_dir / "remote_completion_summary.csv", _completion_row(completion))
    _write_figure(output_dir, alignment_rows)
    metadata = {
        "status": "complete_product",
        "decision_label": "THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE",
        "cases": list(CASES),
        "views": list(VIEWS),
        "base_tracer_threshold": BASE_THRESHOLD,
        "kpc_cm": KPC_CM,
        "final_observational_topology_frozen": False,
        "publication_ready": False,
        "evidence_layers": {
            "observer_side": "existing X-ray recovery products are treated as fixed inputs",
            "simulation_truth": "Level 1 injected energy and Level 2 tracer-lobe truth are independent retrieved evidence",
            "hybrid_context": "tracer-shell ambient pressure combined with X-ray-derived volumes after recovery",
        },
        "interpretation_boundaries": {
            "xray_volume": "X-ray volume is projection/method sensitive",
            "pressure": "pressure is tracer-shell context",
            "energy": "energy is a hybrid proxy",
            "proxy_label": "hybrid tracer-pressure/X-ray-volume proxies, not observer-only estimates",
        },
        "pressure_conventions": {
            "truth_alignment": "side-specific tracer-shell pressure",
            "method_sensitivity": "case_mean_pressure_sensitivity_only",
        },
        "row_counts": {
            "case_truth_summary": len(case_rows),
            "truth_threshold_sensitivity": len(threshold_rows),
            "tracer_shell_pressure_context": len(shell_rows),
            "xray_truth_alignment": len(alignment_rows),
            "xray_truth_method_sensitivity": len(method_rows),
            "remote_completion_summary": 1,
        },
        "remote_completion": completion,
        "input_provenance": {
            "recovery_summary": _source(DEFAULT_OUTPUT / "xray_recovery_summary.csv"),
            "component_summary": _source(DEFAULT_OUTPUT / "xray_component_summary.csv"),
            "method_sensitivity": _source(DEFAULT_OUTPUT / "method_sensitivity.csv"),
            "remote_products": _source(REMOTE_PRODUCTS),
            "remote_logs": _source(REMOTE_LOGS),
        },
    }
    (output_dir / "three_case_truth_alignment_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    write_manifest(output_dir)
    print("status=complete_product")
    print("decision_label=THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_assets(args.output_dir)


if __name__ == "__main__":
    main()
