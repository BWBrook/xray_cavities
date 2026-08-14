#!/usr/bin/env python3
"""Isolate the published PRAiSE2 radiative-coefficient correction.

The diagnostic reuses the immutable Goal 056 cache and deterministic particle
sample.  It changes only the PRAiSE2 source module, then compares weighted
emissivity summaries, representative Lorentz histories, and endpoint maps.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np

from scripts.science import diagnose_g_lo_adiabatic_recovery as recovery
from scripts.science import diagnose_g_lo_stable_method_value as selection_tools
from scripts.science import diagnose_praise_last_shock_comparison as goal056
from scripts.science import run_g_lo_radio_history_value as workflow


FREQUENCIES_GHZ = np.asarray([0.15, 0.5, 1.4, 4.5, 15.0])
TIMEPOINTS_MYR = (10.0, 20.0, 30.0, 40.0, 50.0)
MATERIAL_RATIO = 1.05
MAP_BINS = 128
DECISION_LABEL = "PRAISE2_PUBLISHED_COEFFICIENT_VALIDATED_FOR_PRODUCTION"


class CoefficientDiagnosticError(RuntimeError):
    """Raised when the coefficient-only comparison cannot satisfy its contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_module(source: Path, label: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"praise2_coefficient_{label}", source)
    if spec is None or spec.loader is None:
        raise CoefficientDiagnosticError(f"cannot load PRAiSE2 source: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "praise", None)):
        raise CoefficientDiagnosticError(f"PRAiSE2 source lacks praise(): {source}")
    return module


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise CoefficientDiagnosticError(f"refusing to write empty table: {path.name}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _write_csv_gz(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise CoefficientDiagnosticError(f"refusing to write empty table: {path.name}")
    with gzip.open(path, "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def _value_class(value: float) -> str:
    if not math.isfinite(value):
        return "nonfinite"
    if value < 0:
        return "negative"
    if value == 0:
        return "zero"
    return "positive"


def summarise_weighted_change(
    baseline: np.ndarray,
    corrected: np.ndarray,
    weights: np.ndarray,
    frequencies: Sequence[float],
    *,
    time_myr: float,
) -> list[dict[str, Any]]:
    """Summarise a coefficient-only population comparison by frequency."""
    baseline = np.asarray(baseline, dtype=float)
    corrected = np.asarray(corrected, dtype=float)
    weights = np.asarray(weights, dtype=float)
    frequencies = np.asarray(frequencies, dtype=float)
    if baseline.shape != corrected.shape or baseline.shape != (weights.size, frequencies.size):
        raise CoefficientDiagnosticError("weighted comparison shapes do not align")
    if np.any(~np.isfinite(weights)) or np.any(weights < 0) or not np.any(weights > 0):
        raise CoefficientDiagnosticError("analysis weights must be finite, non-negative, and nonzero")
    rows: list[dict[str, Any]] = []
    for index, frequency in enumerate(frequencies):
        old = baseline[:, index]
        new = corrected[:, index]
        finite_positive = np.isfinite(old) & np.isfinite(new) & (old > 0) & (new > 0)
        ratio = np.divide(new, old, out=np.full_like(new, np.nan), where=finite_positive)
        material = finite_positive & ((ratio > MATERIAL_RATIO) | (ratio < 1 / MATERIAL_RATIO))
        class_change = np.asarray([
            _value_class(float(left)) != _value_class(float(right))
            for left, right in zip(old, new, strict=True)
        ])
        old_total = float(np.sum(weights * np.where(np.isfinite(old), old, 0.0)))
        new_total = float(np.sum(weights * np.where(np.isfinite(new), new, 0.0)))
        rows.append({
            "time_Myr": float(time_myr),
            "frequency_GHz": float(frequency),
            "particle_count": int(weights.size),
            "analysis_weight": float(np.sum(weights)),
            "uncorrected_weighted_emissivity": old_total,
            "corrected_weighted_emissivity": new_total,
            "corrected_over_uncorrected": new_total / old_total if old_total > 0 else None,
            "material_particle_count": int(np.count_nonzero(material)),
            "material_weight_fraction": float(np.sum(weights[material]) / np.sum(weights)),
            "class_change_count": int(np.count_nonzero(class_change)),
            "uncorrected_zero_count": int(np.count_nonzero(old == 0)),
            "corrected_zero_count": int(np.count_nonzero(new == 0)),
            "uncorrected_nonfinite_count": int(np.count_nonzero(~np.isfinite(old))),
            "corrected_nonfinite_count": int(np.count_nonzero(~np.isfinite(new))),
        })
    return rows


def _slice_raw(raw: Mapping[str, Any], rows: np.ndarray, endpoint: int) -> dict[str, np.ndarray]:
    n = np.asarray(raw["physical_ids"]).size
    nt = np.asarray(raw["time"]).size
    output: dict[str, np.ndarray] = {}
    for name, value in raw.items():
        array = np.asarray(value)
        if name == "time":
            output[name] = array[: endpoint + 1]
        elif array.ndim >= 2 and array.shape[:2] == (n, nt):
            output[name] = array[rows, : endpoint + 1, ...]
        elif array.ndim >= 1 and array.shape[0] == n:
            output[name] = array[rows, ...]
    return output


def _coefficient_probe(module: Any) -> float:
    return float(module.get_a2(1e-12, 1.0, 1.1, 0.2, 4 / 3, 0.03, 0.05, 4))


def build_endpoint_maps(
    positions: np.ndarray,
    weights: np.ndarray,
    baseline: np.ndarray,
    corrected: np.ndarray,
    frequencies: Sequence[float],
    *,
    bins: int = MAP_BINS,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    """Build matched x-z weighted-emissivity maps and pixel diagnostics."""
    positions = np.asarray(positions, dtype=float)
    weights = np.asarray(weights, dtype=float)
    baseline = np.asarray(baseline, dtype=float)
    corrected = np.asarray(corrected, dtype=float)
    frequencies = np.asarray(frequencies, dtype=float)
    if positions.shape != (weights.size, 3) or baseline.shape != corrected.shape:
        raise CoefficientDiagnosticError("endpoint map inputs do not align")
    extent = float(np.max(np.abs(positions[:, (0, 2)])))
    if not math.isfinite(extent) or extent <= 0:
        raise CoefficientDiagnosticError("endpoint positions do not define a finite map extent")
    edges = np.linspace(-extent, extent, bins + 1)
    arrays: dict[str, np.ndarray] = {"x_edges_kpc": edges, "z_edges_kpc": edges}
    rows: list[dict[str, Any]] = []
    for index, frequency in enumerate(frequencies):
        old = np.where(np.isfinite(baseline[:, index]), baseline[:, index], 0.0)
        new = np.where(np.isfinite(corrected[:, index]), corrected[:, index], 0.0)
        old_map, _, _ = np.histogram2d(
            positions[:, 0], positions[:, 2], bins=(edges, edges), weights=weights * old
        )
        new_map, _, _ = np.histogram2d(
            positions[:, 0], positions[:, 2], bins=(edges, edges), weights=weights * new
        )
        ratio = np.divide(new_map, old_map, out=np.full_like(new_map, np.nan), where=old_map > 0)
        label = str(frequency).replace(".", "p")
        arrays[f"uncorrected_{label}GHz"] = old_map
        arrays[f"corrected_{label}GHz"] = new_map
        arrays[f"ratio_{label}GHz"] = ratio
        finite = np.isfinite(ratio)
        finite_positive = finite & (ratio > 0)
        material = finite & ((ratio > MATERIAL_RATIO) | (ratio < 1 / MATERIAL_RATIO))
        rows.append({
            "frequency_GHz": float(frequency),
            "map_bins_per_axis": bins,
            "map_extent_kpc": extent,
            "populated_uncorrected_pixels": int(np.count_nonzero(old_map > 0)),
            "populated_corrected_pixels": int(np.count_nonzero(new_map > 0)),
            "finite_ratio_pixels": int(np.count_nonzero(finite)),
            "material_ratio_pixels": int(np.count_nonzero(material)),
            "median_corrected_over_uncorrected": float(np.median(ratio[finite])) if np.any(finite) else None,
            "max_abs_log10_ratio": (
                float(np.max(np.abs(np.log10(ratio[finite_positive]))))
                if np.any(finite_positive)
                else None
            ),
        })
    return arrays, rows


def _representative_histories(
    raw: Mapping[str, Any],
    selection: Sequence[Mapping[str, Any]],
    panel: Sequence[Mapping[str, Any]],
    baseline_module: Any,
    corrected_module: Any,
) -> list[dict[str, Any]]:
    by_pid = {int(row["physical_id"]): index for index, row in enumerate(selection)}
    output: list[dict[str, Any]] = []
    for selected in panel:
        pid = int(selected["physical_id"])
        row = by_pid[pid]
        old_series = goal056._prepare_praise2_series(raw, row, baseline_module, window_width=5)
        new_series = goal056._prepare_praise2_series(raw, row, corrected_module, window_width=5)
        endpoint = len(old_series["time"]) - 1
        old = goal056.replay_praise2(
            baseline_module, old_series, evaluation_index=endpoint,
            frequencies_ghz=FREQUENCIES_GHZ,
        )
        new = goal056.replay_praise2(
            corrected_module, new_series, evaluation_index=endpoint,
            frequencies_ghz=FREQUENCIES_GHZ,
        )
        shock = goal056.latest_shock_index(old_series["time"], old_series["last_shock"])
        for history_index in range(shock, endpoint + 1):
            for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                old_gamma = float(old["trajectory"][history_index, frequency_index])
                new_gamma = float(new["trajectory"][history_index, frequency_index])
                output.append({
                    "physical_id": pid,
                    "panel_index": int(selected["panel_index"]),
                    "panel_reason": selected["panel_reason"],
                    "time_Myr": float(old_series["time_absolute"][history_index]),
                    "latest_shock_Myr": float(old_series["last_shock_absolute"][-1]),
                    "frequency_GHz": float(frequency),
                    "uncorrected_lorentz_factor": old_gamma,
                    "corrected_lorentz_factor": new_gamma,
                    "corrected_over_uncorrected": new_gamma / old_gamma if old_gamma > 0 else None,
                    "uncorrected_classification": old["classification"],
                    "corrected_classification": new["classification"],
                })
    return output


def _make_figure(
    output: Path,
    time_rows: Sequence[Mapping[str, Any]],
    map_arrays: Mapping[str, np.ndarray],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, len(FREQUENCIES_GHZ), figsize=(18, 7))
    for column, frequency in enumerate(FREQUENCIES_GHZ):
        rows = [row for row in time_rows if math.isclose(float(row["frequency_GHz"]), frequency)]
        axes[0, column].plot(
            [float(row["time_Myr"]) for row in rows],
            [float(row["corrected_over_uncorrected"]) for row in rows],
            marker="o",
        )
        axes[0, column].axhline(1.0, color="black", linewidth=1)
        axes[0, column].set(title=f"{frequency:g} GHz", xlabel="Time (Myr)", ylabel="Weighted ratio")
        label = str(frequency).replace(".", "p")
        image = axes[1, column].imshow(
            map_arrays[f"ratio_{label}GHz"].T,
            origin="lower",
            vmin=0.8,
            vmax=1.2,
            cmap="coolwarm",
        )
        axes[1, column].set(title="Endpoint corrected / old", xlabel="x bin", ylabel="z bin")
        fig.colorbar(image, ax=axes[1, column], fraction=0.046)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def diagnose(
    cache: Path,
    selection_csv: Path,
    comparator_csv: Path,
    baseline_source: Path,
    corrected_source: Path,
    output_dir: Path,
) -> dict[str, Any]:
    paths = [cache, selection_csv, comparator_csv, baseline_source, corrected_source]
    cache, selection_csv, comparator_csv, baseline_source, corrected_source = map(Path, paths)
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise CoefficientDiagnosticError("refusing to overwrite output directory")
    if _sha256(cache) != goal056.EXPECTED_CACHE_SHA256:
        raise CoefficientDiagnosticError("immutable Goal 056 cache hash mismatch")
    if _sha256(selection_csv) != goal056.EXPECTED_SELECTION_SHA256:
        raise CoefficientDiagnosticError("immutable Goal 056 selection hash mismatch")

    baseline_module = _load_module(baseline_source, "uncorrected")
    corrected_module = _load_module(corrected_source, "corrected")
    probe_old = _coefficient_probe(baseline_module)
    probe_new = _coefficient_probe(corrected_module)
    coefficient_ratio = probe_new / probe_old
    if not math.isclose(coefficient_ratio, 4 / 3, rel_tol=1e-8, abs_tol=0.0):
        raise CoefficientDiagnosticError("PRAiSE2 source pair does not isolate the missing 4/3 coefficient")

    with h5py.File(cache, "r") as h5:
        workflow._validate_completed_cache(h5)
        selected_rows, selection = selection_tools.read_exact_selection(selection_csv, h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
            expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
            expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
            expected_trim_single_record_overlap_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_single_record_overlap_rows"],
        )
        raw = recovery._read_treated_sample(h5, selected_rows, plan)
    if len(selection) != goal056.EXPECTED_SELECTION_COUNT:
        raise CoefficientDiagnosticError("Goal 056 selection count changed")

    weights = np.asarray([float(row["analysis_weight"]) for row in selection])
    time_myr = np.asarray(raw["time"], dtype=float) * workflow.TIME_UNIT_S / goal056.TIME_MYR_S
    time_rows: list[dict[str, Any]] = []
    endpoint_old = endpoint_new = None
    endpoint_active = None
    for target in TIMEPOINTS_MYR:
        endpoint = int(np.argmin(np.abs(time_myr - target)))
        active = np.flatnonzero(np.isfinite(np.asarray(raw["pressure"])[:, endpoint]))
        sliced = _slice_raw(raw, active, endpoint)
        old, _ = goal056._run_praise2_endpoint(
            sliced, baseline_module, window_width=5, frequencies_ghz=FREQUENCIES_GHZ
        )
        new, _ = goal056._run_praise2_endpoint(
            sliced, corrected_module, window_width=5, frequencies_ghz=FREQUENCIES_GHZ
        )
        time_rows.extend(
            summarise_weighted_change(
                old, new, weights[active], FREQUENCIES_GHZ, time_myr=float(time_myr[endpoint])
            )
        )
        if endpoint == len(time_myr) - 1:
            endpoint_old, endpoint_new, endpoint_active = old, new, active
    if endpoint_old is None or endpoint_new is None or endpoint_active is None:
        raise CoefficientDiagnosticError("the requested timepoints did not include the cache endpoint")

    endpoint_particles: list[dict[str, Any]] = []
    for local, sample_index in enumerate(endpoint_active):
        selected = selection[int(sample_index)]
        for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
            old = float(endpoint_old[local, frequency_index])
            new = float(endpoint_new[local, frequency_index])
            endpoint_particles.append({
                "sample_index": int(selected["sample_index"]),
                "cache_row": int(selected["cache_row"]),
                "physical_id": int(selected["physical_id"]),
                "analysis_weight": float(selected["analysis_weight"]),
                "frequency_GHz": float(frequency),
                "uncorrected_emissivity": old,
                "corrected_emissivity": new,
                "corrected_over_uncorrected": new / old if old > 0 and math.isfinite(new) else None,
                "uncorrected_class": _value_class(old),
                "corrected_class": _value_class(new),
            })

    map_arrays, map_rows = build_endpoint_maps(
        np.asarray(raw["position"])[endpoint_active], weights[endpoint_active],
        endpoint_old, endpoint_new, FREQUENCIES_GHZ,
    )
    with comparator_csv.open(newline="") as handle:
        comparator = list(csv.DictReader(handle))
    panel = goal056.select_representative_particles(comparator)
    history_rows = _representative_histories(
        raw, selection, panel, baseline_module, corrected_module
    )

    output_dir.mkdir(parents=True)
    _write_csv(output_dir / "weighted_emissivity_timepoints.csv", time_rows)
    _write_csv_gz(output_dir / "endpoint_particle_comparison.csv.gz", endpoint_particles)
    _write_csv_gz(output_dir / "representative_lorentz_histories.csv.gz", history_rows)
    _write_csv(output_dir / "endpoint_map_summary.csv", map_rows)
    np.savez_compressed(output_dir / "endpoint_map_arrays.npz", **map_arrays)
    _make_figure(output_dir / "praise2_coefficient_correction.png", time_rows, map_arrays)

    corrected_nonfinite = sum(int(row["corrected_nonfinite_count"]) for row in time_rows)
    baseline_nonfinite = sum(int(row["uncorrected_nonfinite_count"]) for row in time_rows)
    result = {
        "status": "complete_diagnostic",
        "decision_label": DECISION_LABEL,
        "frequencies_GHz": FREQUENCIES_GHZ,
        "requested_timepoints_Myr": TIMEPOINTS_MYR,
        "selection_count": len(selection),
        "representative_count": len(panel),
        "baseline_source_sha256": _sha256(baseline_source),
        "corrected_source_sha256": _sha256(corrected_source),
        "coefficient_probe_uncorrected": probe_old,
        "coefficient_probe_corrected": probe_new,
        "coefficient_probe_ratio": coefficient_ratio,
        "corrected_nonfinite_count": corrected_nonfinite,
        "uncorrected_nonfinite_count": baseline_nonfinite,
        "gates": {
            "exact_missing_factor_isolated": True,
            "corrected_nonfinite_not_increased": corrected_nonfinite <= baseline_nonfinite,
            "five_frequency_population_comparison_complete": len(time_rows) == len(TIMEPOINTS_MYR) * len(FREQUENCIES_GHZ),
            "representative_histories_complete": bool(history_rows),
            "endpoint_maps_complete": len(map_rows) == len(FREQUENCIES_GHZ),
        },
    }
    if not all(result["gates"].values()):
        result["decision_label"] = "PRAISE2_COEFFICIENT_CORRECTION_HOLD"
    (output_dir / "praise2_coefficient_correction_metadata.json").write_text(
        json.dumps(_json_safe(result), indent=2, sort_keys=True) + "\n"
    )
    print(f"decision_label={result['decision_label']}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--selection-csv", type=Path, required=True)
    parser.add_argument("--comparator-csv", type=Path, required=True)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--corrected-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = diagnose(**vars(args))
    except (CoefficientDiagnosticError, OSError, ValueError) as exc:
        print(f"infrastructure_error={exc}")
        return 2
    return 0 if result["decision_label"] == DECISION_LABEL else 3


if __name__ == "__main__":
    raise SystemExit(main())
