#!/usr/bin/env python3
"""Assemble one scientifically locked case-level snapshot-science product."""

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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.science.snapshot_inference import continuous_injection_delta_shape
from scripts.science.snapshot_synthesis import (
    CAVITY_ENERGY_MODELS,
    RADIO_FREQUENCIES_GHZ,
    RADIO_SNAPSHOT_INDICES,
    SNAPSHOT_INDICES,
    XRAY_VIEWS,
    build_radio_power_surface,
    build_spectral_cavity_power_surface,
    fit_spectral_surface,
    method_contract,
    select_cavity_surface,
    validate_radio_surface,
    validate_radio_view_surface,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAVITY_CSV = (
    ROOT
    / "docs/science/assets/three_case_common_age_evolution_2026-07-13"
    / "synthesis/hybrid_cavity_evolution.csv"
)
DEFAULT_XRAY_FIGURE = (
    ROOT
    / "docs/science/assets/three_case_common_age_evolution_2026-07-13"
    / "synthesis/observer_hybrid_evolution.png"
)
CASE_CONTRACTS = {
    "C-HI": {"environment": "cluster 002_003", "one_sided_power_erg_s": 1.0e45},
    "C-LO": {"environment": "cluster 002_003", "one_sided_power_erg_s": 1.0e43},
    "G-LO": {"environment": "group 002_031", "one_sided_power_erg_s": 1.0e43},
    "G-HI": {"environment": "group 002_031", "one_sided_power_erg_s": 1.0e45},
}
KPC_CM = 3.085_677_581_491_3673e21
ALL_CAVITY_ENERGY_MODELS = ("pV", "2.5pV", "4pV")


class ProductError(ValueError):
    """Raised when an input surface cannot support the locked analysis."""


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
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def number(row: Mapping[str, Any], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductError(f"missing or invalid {field}") from exc
    if not math.isfinite(value):
        raise ProductError(f"non-finite {field}")
    return value


def integer(row: Mapping[str, Any], field: str) -> int:
    value = number(row, field)
    result = int(value)
    if value != result:
        raise ProductError(f"non-integer {field}")
    return result


def boolean(row: Mapping[str, Any], field: str) -> bool:
    value = str(row.get(field, "")).strip().lower()
    if value not in {"true", "false"}:
        raise ProductError(f"invalid Boolean {field}")
    return value == "true"


def ratio(numerator: float, denominator: float) -> float | str:
    return numerator / denominator if denominator > 0.0 else ""


def validate_fluid_surface(
    *,
    case: str,
    expected_bipolar_power_erg_s: float,
    manifest_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    energy_rows: Sequence[Mapping[str, Any]],
    shock_rows: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Validate the six retained snapshots and select primary fluid rows."""
    expected = set(SNAPSHOT_INDICES)
    for name, rows in (
        ("manifest", manifest_rows),
        ("source truth", source_rows),
        ("energy", energy_rows),
        ("shock", shock_rows),
    ):
        if any(row.get("case") != case for row in rows):
            raise ProductError(f"{name} contains a non-{case} row")

    manifest = {integer(row, "snapshot_index"): dict(row) for row in manifest_rows}
    source = {integer(row, "snapshot_index"): dict(row) for row in source_rows}
    if set(manifest) != expected or set(source) != expected:
        raise ProductError("fluid manifest/source truth does not contain exactly 0/10/20/30/40/50")

    primary_energy = [
        dict(row)
        for row in energy_rows
        if row.get("side") == "bipolar_total" and row.get("partition_method") == "fractional"
    ]
    energy = {integer(row, "snapshot_index"): row for row in primary_energy}
    if len(primary_energy) != len(expected) or set(energy) != expected:
        raise ProductError("primary fractional bipolar energy surface is incomplete or duplicated")

    primary_shocks = [
        dict(row)
        for row in shock_rows
        if math.isclose(number(row, "velocity_threshold_factor"), 1.0, rel_tol=0.0, abs_tol=1.0e-12)
    ]
    shock_keys = [(integer(row, "snapshot_index"), str(row.get("side", ""))) for row in primary_shocks]
    expected_shocks = {(index, side) for index in SNAPSHOT_INDICES for side in ("negative_z", "positive_z")}
    if len(shock_keys) != len(expected_shocks) or set(shock_keys) != expected_shocks:
        raise ProductError("primary two-sided shock surface is incomplete or duplicated")

    for index in SNAPSHOT_INDICES:
        manifest_time = number(manifest[index], "actual_time_myr")
        for row in (source[index], energy[index]):
            if not math.isclose(number(row, "actual_time_myr"), manifest_time, rel_tol=0.0, abs_tol=1.0e-8):
                raise ProductError(f"fluid time mismatch at snapshot {index}")
        if not math.isclose(
            number(source[index], "jet_power_bipolar_erg_s"),
            expected_bipolar_power_erg_s,
            rel_tol=1.0e-12,
        ):
            raise ProductError("source truth does not use the locked bipolar power")
        if not math.isclose(
            number(energy[index], "injected_energy_erg"),
            number(source[index], "injected_energy_bipolar_erg"),
            rel_tol=1.0e-12,
            abs_tol=0.0,
        ):
            raise ProductError(f"injected-energy mismatch at snapshot {index}")

    return {
        "manifest": [manifest[index] for index in SNAPSHOT_INDICES],
        "source": [source[index] for index in SNAPSHOT_INDICES],
        "energy": [energy[index] for index in SNAPSHOT_INDICES],
        "shock": sorted(primary_shocks, key=lambda row: (integer(row, "snapshot_index"), str(row["side"]))),
    }


def select_cavity_recovery_surface(
    rows: Sequence[Mapping[str, Any]], *, case: str
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    for row in rows:
        if (
            row.get("case") != case
            or row.get("side") != "bipolar_total"
            or row.get("volume_depth_assumption") != "geometric_depth"
            or row.get("view") not in XRAY_VIEWS
            or row.get("energy_model") not in ALL_CAVITY_ENERGY_MODELS
        ):
            continue
        index = integer(row, "nominal_age_myr")
        key = (index, str(row["view"]), str(row["energy_model"]))
        if key in seen:
            raise ProductError(f"duplicate cavity recovery row: {key}")
        seen.add(key)
        selected.append(
            dict(row)
            | {
                "nominal_age_myr": index,
                "actual_time_myr": number(row, "actual_time_myr"),
                "pressure_dyn_cm2": number(row, "pressure_dyn_cm2"),
                "volume_kpc3": number(row, "volume_kpc3"),
                "energy_erg": number(row, "energy_erg"),
                "quantitative_energy_valid": boolean(row, "quantitative_energy_valid"),
            }
        )
    expected = {
        (index, view, model)
        for index in RADIO_SNAPSHOT_INDICES
        for view in XRAY_VIEWS
        for model in ALL_CAVITY_ENERGY_MODELS
    }
    if seen != expected:
        raise ProductError(f"cavity recovery surface mismatch: missing={sorted(expected - seen)}")
    return sorted(selected, key=lambda row: (row["nominal_age_myr"], row["view"], row["energy_model"]))


def build_energy_recovery_rows(
    *,
    energy_rows: Sequence[Mapping[str, Any]],
    cavity_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    energy = {integer(row, "snapshot_index"): row for row in energy_rows}
    output: list[dict[str, Any]] = []
    for cavity in cavity_rows:
        index = int(cavity["nominal_age_myr"])
        fluid = energy[index]
        injected = number(fluid, "injected_energy_erg")
        gas_total = number(fluid, "gas_total_delta_erg")
        lobe_thermal = number(fluid, "lobe_thermal_erg")
        lobe_total = number(fluid, "lobe_total_erg")
        lobe_volume = number(fluid, "lobe_volume_kpc3")
        pressure_volume = float(cavity["pressure_dyn_cm2"]) * lobe_volume * KPC_CM**3
        direct_enthalpy = lobe_thermal + pressure_volume
        residual_if_zero_boundary = injected - gas_total
        closure_if_zero_boundary = number(fluid, "unattributed_residual_erg")
        valid = bool(cavity["quantitative_energy_valid"])
        cavity_energy = float(cavity["energy_erg"])
        output.append(
            {
                "case": cavity["case"],
                "snapshot_index": index,
                "actual_time_myr": cavity["actual_time_myr"],
                "view": cavity["view"],
                "topology_status": cavity["topology_status"],
                "cavity_energy_model": cavity["energy_model"],
                "quantitative_energy_valid": valid,
                "cavity_energy_erg": cavity_energy,
                "ambient_pressure_dyn_cm2": cavity["pressure_dyn_cm2"],
                "cavity_volume_kpc3": cavity["volume_kpc3"],
                "injected_energy_erg": injected,
                "ambient_gas_total_delta_erg": gas_total,
                "direct_lobe_thermal_erg": lobe_thermal,
                "direct_lobe_kinetic_erg": number(fluid, "lobe_kinetic_erg"),
                "direct_lobe_gravitational_erg": number(fluid, "lobe_gravitational_erg"),
                "direct_lobe_total_erg": lobe_total,
                "direct_lobe_volume_kpc3": lobe_volume,
                "direct_lobe_nonrel_enthalpy_erg": direct_enthalpy,
                "residual_lobe_if_zero_boundary_erg": residual_if_zero_boundary,
                "closure_residual_if_zero_boundary_erg": closure_if_zero_boundary,
                "closure_fraction_of_injected": fluid.get("closure_fraction_of_injected", ""),
                "boundary_status": fluid["boundary_status"],
                "residual_cocoon_status": "not_usable_as_cocoon_boundary_unmeasured",
                "cavity_to_injected_ratio": ratio(cavity_energy, injected) if valid else "",
                "cavity_to_direct_lobe_total_ratio": ratio(cavity_energy, lobe_total) if valid else "",
                "cavity_to_direct_lobe_enthalpy_ratio": ratio(cavity_energy, direct_enthalpy) if valid else "",
                "cavity_to_residual_cocoon_ratio": "",
                "recovery_status": "quantitative" if valid else "excluded_by_xray_topology_gate",
            }
        )
    return output


def build_shock_recovery_rows(
    recovery_rows: Sequence[Mapping[str, Any]],
    shock_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    shocks = {
        (integer(row, "snapshot_index"), str(row["side"])): row
        for row in shock_rows
    }
    output: list[dict[str, Any]] = []
    for recovery in recovery_rows:
        for side in ("negative_z", "positive_z"):
            shock = shocks[(int(recovery["snapshot_index"]), side)]
            detected = shock.get("status") == "detected"
            mach = shock.get("mach_kinematic", "") if detected else ""
            output.append(
                {
                    "case": recovery["case"],
                    "snapshot_index": recovery["snapshot_index"],
                    "actual_time_myr": recovery["actual_time_myr"],
                    "view": recovery["view"],
                    "cavity_energy_model": recovery["cavity_energy_model"],
                    "quantitative_energy_valid": recovery["quantitative_energy_valid"],
                    "side": side,
                    "shock_status": shock["status"],
                    "shock_distance_kpc": shock.get("shock_distance_kpc", ""),
                    "shock_speed_km_s": shock.get("shock_speed_km_s", ""),
                    "ambient_sound_speed_km_s": shock.get("ambient_sound_speed_km_s", ""),
                    "mach_kinematic": mach,
                    "mach_rh_pressure": shock.get("mach_rh_pressure", ""),
                    "mach_rh_density": shock.get("mach_rh_density", ""),
                    "cavity_to_injected_ratio": recovery["cavity_to_injected_ratio"],
                    "cavity_to_direct_lobe_total_ratio": recovery["cavity_to_direct_lobe_total_ratio"],
                    "cavity_to_direct_lobe_enthalpy_ratio": recovery["cavity_to_direct_lobe_enthalpy_ratio"],
                    "status": "quantitative" if mach != "" and recovery["recovery_status"] == "quantitative" else "nonquantitative",
                }
            )
    return output


def simulation_setup_rows(
    manifest_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    *,
    case: str,
) -> list[dict[str, str]]:
    contract = CASE_CONTRACTS[case]
    source = source_rows[0]
    source_times = ";".join(
        f"{integer(row, 'snapshot_index')}:{number(row, 'actual_time_myr'):.12g}"
        for row in manifest_rows
    )
    source_paths = ";".join(str(row["input_h5"]) for row in manifest_rows)
    entries = (
        ("case", "case_id", case, "", "locked simulation identity"),
        ("environment", "Stewart atmosphere", str(contract["environment"]), "", "tabulated initial static environment"),
        ("grid", "geometry", "3D Cartesian; stewart_stretched_250; 960x960x1014", "", "accepted production grid"),
        ("grid", "jet-axis extent", "-250 to 250", "kpc", "accepted production grid"),
        ("time", "retained fluid snapshots index:time", source_times, "Myr", "actual HDF5 times"),
        ("time", "fluid source paths", source_paths, "", "six retained immutable HDF5 sources"),
        ("jet", "power one-sided", f"{number(source, 'jet_power_one_sided_erg_s'):.12g}", "erg s^-1", "JET_PWR convention"),
        ("jet", "power bipolar", f"{number(source, 'jet_power_bipolar_erg_s'):.12g}", "erg s^-1", "two jets"),
        ("jet", "speed", "0.1", "c", "accepted production configuration"),
        ("jet", "opening angles primary/secondary", "15/15", "deg", "accepted production configuration"),
        ("jet", "initial radius", "0.1", "kpc", "accepted production configuration"),
        ("jet", "injection height", "0.75", "kpc", "accepted production configuration"),
        (
            "jet",
            "start/active/end",
            f"{number(source, 'jet_start_myr'):.12g}/{number(source, 'jet_active_myr'):.12g}/{number(source, 'jet_start_myr') + number(source, 'jet_active_myr'):.12g}",
            "Myr",
            "active integrated source",
        ),
        ("particles", "output and injection cadence", "0.01", "Myr", "retained 0..5000 histories"),
        ("particles", "particles per injection", "32", "", "accepted production configuration"),
        ("energy", "primary tracer partition", "clip(tr1,0,1)", "", "fractional operational partition"),
        ("energy", "binary tracer sensitivities", "1e-3;5e-3;1e-2", "", "secondary only"),
        ("energy", "gravitational potential", "centre-zero integral of matched group gravity columns", "", "fixed initial atmosphere"),
        ("shock", "method", "2 kpc axial tube; 5% p/rho disturbance; 3-snapshot fit", "", "baseline-noise velocity cut"),
        ("radio", "frequencies", "0.15;0.5;1.4;4.5;15", "GHz", "lossless and full-loss"),
        ("radio", "PRAiSE2 source", "73210e15d4c60e77ffb317b3ee2b9209c049edd4", "git commit", "corrected implementation"),
        ("radio", "assumptions", "z=0.05;eta=0.03;s=2.2;gmin=500;gmax=1e5", "", "locked radio contract"),
        ("xray", "diagnostic", "1 keV XRAiSE-corrected surface brightness", "", "supplied APEC and Gaunt tables"),
        ("xray", "views", "0;45;90", "deg", "edge-overlap projection for nonzero views"),
        ("cavity", "energy conventions", "pV;2.5pV;4pV", "erg", "2.5pV adopted; 4pV literature comparator"),
    )
    return [
        {"section": section, "item": item, "value": value, "unit": unit, "provenance": provenance}
        for section, item, value, unit, provenance in entries
    ]


def _numeric(rows: Sequence[Mapping[str, Any]], field: str) -> np.ndarray:
    return np.asarray([number(row, field) for row in rows], dtype=float)


def plot_energy(rows: Sequence[Mapping[str, Any]], output: Path) -> None:
    ordered = sorted(rows, key=lambda row: integer(row, "snapshot_index"))
    time = _numeric(ordered, "actual_time_myr")
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    for field, label in (
        ("injected_energy_erg", "Injected"),
        ("gas_thermal_delta_erg", "Ambient thermal"),
        ("gas_kinetic_delta_erg", "Ambient kinetic"),
        ("gas_gravitational_delta_erg", "Ambient gravity"),
        ("lobe_total_erg", "Direct lobe total"),
        ("unattributed_residual_erg", "Closure residual (zero-boundary assumption)"),
    ):
        ax.plot(time, _numeric(ordered, field), marker="o", label=label)
    ax.set_yscale("symlog", linthresh=1.0e55)
    ax.set(xlabel="Actual source age (Myr)", ylabel="Energy (erg)", title="Single-case energy budget")
    ax.legend(fontsize=8, ncol=2)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_radio(rows: Sequence[Mapping[str, Any]], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    colors = plt.cm.viridis(np.linspace(0.05, 0.95, len(RADIO_FREQUENCIES_GHZ)))
    for color, frequency in zip(colors, RADIO_FREQUENCIES_GHZ, strict=True):
        for loss_model, linestyle in (("lossless", "--"), ("full_loss", "-")):
            selected = sorted(
                [row for row in rows if float(row["frequency_ghz"]) == frequency and row["loss_model"] == loss_model],
                key=lambda row: int(row["snapshot_index"]),
            )
            ax.plot(
                _numeric(selected, "fluid_time_myr"),
                _numeric(selected, "luminosity_w_hz"),
                color=color,
                linestyle=linestyle,
                marker="o",
                label=f"{frequency:g} GHz {loss_model}",
            )
    ax.set_yscale("log")
    ax.set(xlabel="Actual source age (Myr)", ylabel="Luminosity (W Hz$^{-1}$)", title="Corrected PRAiSE2 integrated luminosity (45 deg)")
    ax.legend(fontsize=7, ncol=2)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_cavity_energy(rows: Sequence[Mapping[str, Any]], output: Path) -> None:
    valid = [row for row in rows if row["recovery_status"] == "quantitative" and row["view"] == "45deg"]
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    for model, marker in (("2.5pV", "s"), ("4pV", "^")):
        selected = sorted([row for row in valid if row["cavity_energy_model"] == model], key=lambda row: int(row["snapshot_index"]))
        if selected:
            ax.plot(_numeric(selected, "actual_time_myr"), _numeric(selected, "cavity_energy_erg"), marker=marker, label=f"X-ray {model} (45 deg)")
    primary = sorted({int(row["snapshot_index"]): row for row in rows}.values(), key=lambda row: int(row["snapshot_index"]))
    ax.plot(_numeric(primary, "actual_time_myr"), _numeric(primary, "injected_energy_erg"), color="black", marker="o", label="Injected")
    ax.plot(_numeric(primary, "actual_time_myr"), _numeric(primary, "direct_lobe_total_erg"), color="#0072B2", marker="o", label="Direct lobe total")
    ax.plot(_numeric(primary, "actual_time_myr"), _numeric(primary, "direct_lobe_nonrel_enthalpy_erg"), color="#D55E00", marker="o", label="Direct lobe enthalpy")
    ax.set_yscale("log")
    ax.set(xlabel="Actual source age (Myr)", ylabel="Energy (erg)", title="X-ray cavity energy recovery")
    ax.legend(fontsize=8)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_shock_recovery(rows: Sequence[Mapping[str, Any]], output: Path) -> None:
    valid = [
        row for row in rows
        if row["status"] == "quantitative" and row["cavity_energy_model"] in CAVITY_ENERGY_MODELS
    ]
    fig, ax = plt.subplots(figsize=(8.0, 5.2), constrained_layout=True)
    for side, marker in (("negative_z", "v"), ("positive_z", "^")):
        for model, color in (("2.5pV", "#0072B2"), ("4pV", "#D55E00")):
            selected = [row for row in valid if row["side"] == side and row["cavity_energy_model"] == model]
            if selected:
                ax.scatter(_numeric(selected, "mach_kinematic"), _numeric(selected, "cavity_to_injected_ratio"), marker=marker, color=color, alpha=0.75, label=f"{model} {side}")
    ax.axhline(1.0, color="black", linewidth=1, linestyle=":")
    ax.set(xlabel="Kinematic shock Mach number", ylabel="Cavity energy / injected energy", title="Cavity recovery versus shock strength")
    ax.legend(fontsize=8, ncol=2)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_power(
    radio_power: Sequence[Mapping[str, Any]],
    spectral_power: Sequence[Mapping[str, Any]],
    known_bipolar_power_erg_s: float,
    output: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    ax.axhline(known_bipolar_power_erg_s, color="black", linewidth=1.5, label="Known bipolar power")
    for relation, color in (("kokotanekov_2017_150mhz_approx", "#009E73"), ("cavagnolo_2010_1p4ghz", "#CC79A7")):
        selected = sorted([row for row in radio_power if row["relation"] == relation and row["loss_model"] == "full_loss"], key=lambda row: int(row["snapshot_index"]))
        ax.plot(_numeric(selected, "actual_time_myr"), _numeric(selected, "inferred_power_erg_s"), marker="o", color=color, label=relation)
    for model, linestyle in (("2.5pV", "--"), ("4pV", "-.")):
        selected = sorted(
            [row for row in spectral_power if row["view"] == "45deg" and row["cavity_energy_model"] == model and row["field_treatment"] == "matched_praise_effective" and row["status"] != "cavity_energy_not_quantitatively_valid"],
            key=lambda row: int(row["snapshot_index"]),
        )
        if selected:
            ax.plot(_numeric(selected, "actual_time_myr"), _numeric(selected, "inferred_cavity_power_erg_s"), marker="s", linestyle=linestyle, label=f"{model} / PRAiSE-effective spectral age")
    ax.set_yscale("log")
    ax.set(xlabel="Actual source age (Myr)", ylabel="Jet power (erg s$^{-1}$)", title="Known and inferred jet power")
    ax.legend(fontsize=7)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_spectral_age(rows: Sequence[Mapping[str, Any]], output: Path) -> None:
    selected = [row for row in rows if row["view"] == "45deg" and row["cavity_energy_model"] == "2.5pV" and row["status"] != "cavity_energy_not_quantitatively_valid"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), constrained_layout=True)
    for treatment in sorted({str(row["field_treatment"]) for row in selected}):
        subset = sorted([row for row in selected if row["field_treatment"] == treatment], key=lambda row: int(row["snapshot_index"]))
        axes[0].plot(_numeric(subset, "actual_time_myr"), _numeric(subset, "spectral_to_true_age_ratio"), marker="o", label=treatment)
        axes[1].plot(_numeric(subset, "actual_time_myr"), _numeric(subset, "inferred_to_known_ratio"), marker="o", label=treatment)
    for ax in axes:
        ax.axhline(1.0, color="black", linestyle=":", linewidth=1)
        ax.set_xlabel("Actual source age (Myr)")
    axes[0].set_ylabel("Spectral age / true age")
    axes[1].set_ylabel("2.5pV / spectral-age power / known power")
    axes[0].set_title("Spectral-age recovery")
    axes[1].set_title("Cavity-power recovery")
    axes[0].legend(fontsize=7)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_spectra(
    radio_rows: Sequence[Mapping[str, Any]],
    spectral_rows: Sequence[Mapping[str, Any]],
    output: Path,
) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(11.2, 7.2), constrained_layout=True)
    frequencies = np.asarray(RADIO_FREQUENCIES_GHZ, dtype=float)
    fine = np.geomspace(frequencies.min(), frequencies.max(), 200)
    spectral = {int(row["snapshot_index"]): row for row in spectral_rows}
    for ax, index in zip(axes.flat, RADIO_SNAPSHOT_INDICES, strict=False):
        for loss_model, marker in (("lossless", "s"), ("full_loss", "o")):
            rows = sorted([row for row in radio_rows if int(row["snapshot_index"]) == index and row["loss_model"] == loss_model], key=lambda row: float(row["frequency_ghz"]))
            ax.scatter(_numeric(rows, "frequency_ghz"), _numeric(rows, "luminosity_w_hz"), marker=marker, label=loss_model)
        fit = spectral[index]
        curve = float(fit["amplitude"]) * continuous_injection_delta_shape(fine, alpha_injection=float(fit["alpha_injection"]), break_ghz=float(fit["fitted_break_ghz"]))
        ax.plot(fine, curve, color="black", linewidth=1, label=f"CI fit ({fit['break_status']})")
        ax.set(xscale="log", yscale="log", title=f"{index} Myr", xlabel="GHz", ylabel="W Hz$^{-1}$")
        ax.legend(fontsize=6)
    axes.flat[-1].axis("off")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def build_product(
    *,
    case: str,
    fluid_root: Path,
    radio_root: Path,
    cavity_csv: Path,
    xray_figure: Path,
    output_root: Path,
) -> dict[str, Any]:
    if case not in CASE_CONTRACTS:
        raise ProductError(f"unsupported case: {case}")
    case_contract = CASE_CONTRACTS[case]
    known_bipolar_power_erg_s = 2.0 * float(case_contract["one_sided_power_erg_s"])
    if output_root.exists():
        raise ProductError(f"refusing to overwrite output root: {output_root}")
    output_root.mkdir(parents=True)
    inputs = {
        "fluid_manifest": fluid_root / "snapshot_manifest.csv",
        "source_truth": fluid_root / "source_truth.csv",
        "energy": fluid_root / "energy_partition_timeseries.csv",
        "shock": fluid_root / "shock_dynamics.csv",
        "radio_primary": radio_root / "radio_luminosity_timeseries.csv",
        "radio_views": radio_root / "radio_view_luminosity.csv",
        "cavity": cavity_csv,
        "xray_figure": xray_figure,
    }
    for path in inputs.values():
        if not Path(path).is_file():
            raise ProductError(f"required input missing: {path}")

    fluid = validate_fluid_surface(
        case=case,
        expected_bipolar_power_erg_s=known_bipolar_power_erg_s,
        manifest_rows=read_rows(inputs["fluid_manifest"]),
        source_rows=read_rows(inputs["source_truth"]),
        energy_rows=read_rows(inputs["energy"]),
        shock_rows=read_rows(inputs["shock"]),
    )
    radio = validate_radio_surface(read_rows(inputs["radio_primary"]), case=case)
    radio_views = validate_radio_view_surface(read_rows(inputs["radio_views"]), case=case)
    primary_lookup = {
        (int(row["snapshot_index"]), str(row["loss_model"]), float(row["frequency_ghz"])): row
        for row in radio
    }
    for row in radio_views:
        if row["view"] != "45deg":
            continue
        key = (int(row["snapshot_index"]), str(row["loss_model"]), float(row["frequency_ghz"]))
        primary = primary_lookup[key]
        for field in (
            "fluid_time_myr",
            "particle_time_myr",
            "particle_time_offset_myr",
            "luminosity_w_hz",
            "effective_magnetic_field_ug",
        ):
            if not math.isclose(float(row[field]), float(primary[field]), rel_tol=1.0e-12, abs_tol=0.0):
                raise ProductError(f"45deg primary radio mismatch for {key}: {field}")
    cavity_source = read_rows(inputs["cavity"])
    cavity_recovery = select_cavity_recovery_surface(cavity_source, case=case)
    cavity_inference = select_cavity_surface(cavity_source, case=case)
    recovery = build_energy_recovery_rows(energy_rows=fluid["energy"], cavity_rows=cavity_recovery)
    shock_recovery = build_shock_recovery_rows(recovery, fluid["shock"])
    radio_power = build_radio_power_surface(
        radio,
        known_bipolar_power_erg_s=known_bipolar_power_erg_s,
    )
    spectral = fit_spectral_surface(radio)
    spectral_power = build_spectral_cavity_power_surface(
        radio_rows=radio,
        cavity_rows=cavity_inference,
        spectral_rows=spectral,
        known_bipolar_power_erg_s=known_bipolar_power_erg_s,
    )

    tables = {
        "simulation_setup.csv": simulation_setup_rows(
            fluid["manifest"], fluid["source"], case=case
        ),
        "snapshot_manifest.csv": fluid["manifest"],
        "source_truth.csv": fluid["source"],
        "energy_partition_primary.csv": fluid["energy"],
        "shock_dynamics_primary.csv": fluid["shock"],
        "radio_luminosity_timeseries.csv": radio,
        "radio_view_luminosity.csv": radio_views,
        "xray_cavity_surface.csv": cavity_recovery,
        "cavity_energy_recovery.csv": recovery,
        "cavity_recovery_vs_shock.csv": shock_recovery,
        "radio_power_inference.csv": radio_power,
        "spectral_fits.csv": spectral,
        "spectral_cavity_power.csv": spectral_power,
    }
    for name, rows in tables.items():
        write_rows(output_root / name, rows)

    figures = {
        "energy_budget.png": lambda path: plot_energy(fluid["energy"], path),
        "radio_luminosity_evolution.png": lambda path: plot_radio(radio, path),
        "cavity_energy_recovery.png": lambda path: plot_cavity_energy(recovery, path),
        "cavity_recovery_vs_shock.png": lambda path: plot_shock_recovery(shock_recovery, path),
        "jet_power_recovery.png": lambda path: plot_power(
            radio_power, spectral_power, known_bipolar_power_erg_s, path
        ),
        "spectral_age_recovery.png": lambda path: plot_spectral_age(spectral_power, path),
        "radio_spectra_ci_fits.png": lambda path: plot_spectra(radio, spectral, path),
    }
    for name, plotter in figures.items():
        plotter(output_root / name)

    figure_register = [
        {
            "figure": name,
            "role": "generated_goal058_single_case_diagnostic",
            "status": "complete",
            "source": str(output_root / name),
            "note": f"{case} only; no cross-case claim",
        }
        for name in figures
    ]
    figure_register.append(
        {
            "figure": xray_figure.name,
            "role": "accepted_xray_cavity_and_truth_map_context",
            "status": "referenced_not_duplicated",
            "source": str(xray_figure),
            "note": "Accepted Goal 041/three-case synthesis figure; quantitative topology gates remain active",
        }
    )
    write_rows(output_root / "figure_register.csv", figure_register)

    provenance = [
        {
            "input_id": key,
            "path": str(path),
            "sha256": sha256_file(path),
            "role": "immutable_input" if key != "xray_figure" else "accepted_external_figure",
        }
        for key, path in inputs.items()
    ]
    write_rows(output_root / "input_provenance.csv", provenance)
    validation = [
        {"surface": name, "row_count": len(rows), "status": "passed"}
        for name, rows in tables.items()
    ] + [
        {"surface": "generated_figures", "row_count": len(figures), "status": "passed"},
        {"surface": "cross_case_claims", "row_count": 0, "status": "prohibited_and_absent"},
    ]
    write_rows(output_root / "product_validation.csv", validation)

    metadata = {
        "status": "complete_single_case_snapshot_science_product",
        "case": case,
        "decision_scope": "single-case method and recovery surface; no cross-case claims",
        "snapshot_indices": list(SNAPSHOT_INDICES),
        "radio_snapshot_indices": list(RADIO_SNAPSHOT_INDICES),
        "method_contract": method_contract(
            known_bipolar_power_erg_s=known_bipolar_power_erg_s
        ),
        "boundary_flux": "unmeasured_from_retained_snapshots",
        "residual_cocoon_interpretation": "not promoted because closure cannot exclude boundary flux",
        "xray_map_policy": "reuse accepted map context; do not duplicate bulky arrays",
        "table_row_counts": {name: len(rows) for name, rows in tables.items()},
        "generated_figures": list(figures),
        "cross_case_claims": False,
    }
    write_json(output_root / "snapshot_science_metadata.json", metadata)
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=tuple(CASE_CONTRACTS))
    parser.add_argument("--fluid-root", required=True, type=Path)
    parser.add_argument("--radio-root", required=True, type=Path)
    parser.add_argument("--cavity-csv", type=Path, default=DEFAULT_CAVITY_CSV)
    parser.add_argument("--xray-figure", type=Path, default=DEFAULT_XRAY_FIGURE)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = build_product(
        case=args.case,
        fluid_root=args.fluid_root,
        radio_root=args.radio_root,
        cavity_csv=args.cavity_csv,
        xray_figure=args.xray_figure,
        output_root=args.output_root,
    )
    print(f"status={metadata['status']} case={metadata['case']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
