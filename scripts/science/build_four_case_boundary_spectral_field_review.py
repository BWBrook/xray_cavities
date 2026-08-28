#!/usr/bin/env python3
"""Audit selected-age boundaries and compare two spectral-age field choices."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import shutil
import tarfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts.science.snapshot_inference import spectral_age_myr
from scripts.science.snapshot_synthesis import fit_spectral_surface


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
FLUID_ROOT = ASSET_ROOT / "four_case_fluid_snapshot_census_2026-08-25"
XRAY_ROOT = (
    ASSET_ROOT
    / "four_case_selected_age_observables_2026-08-26"
    / "four_case_xray_complete/review_products/products"
)
RADIO_ROOT = ASSET_ROOT / "four_case_selected_age_observables_2026-08-26"
ACCEPTED_SYNTHESIS_ROOT = ASSET_ROOT / "four_case_scientific_synthesis_2026-08-26"
DEFAULT_OUTPUT_ROOT = (
    ASSET_ROOT / "four_case_boundary_spectral_field_review_2026-08-28"
)

CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
ANNUAL_AGES = tuple(range(51))
VIEWS = ("0deg", "45deg", "90deg")
DOMAIN_HALF_KPC = {"x": 200.0, "y": 200.0, "z": 250.0}
RADIO_PATHS = {
    "C-HI": RADIO_ROOT / "completed_radio_pair_1/C-HI/radio_view_luminosity.csv",
    "C-LO": RADIO_ROOT / "completed_radio_final/C-LO/radio_view_luminosity.csv",
    "G-HI": RADIO_ROOT / "completed_radio_pair_1/G-HI/radio_view_luminosity.csv",
    "G-LO": RADIO_ROOT / "completed_pair_2/G-LO-radio/radio_view_luminosity.csv",
}

GAMMA_GAS = 5.0 / 3.0
ETA = 0.03
MU0_SI = 1.25663706212e-6
KPC_TO_M = 3.085677581491367e19
TRACER_BOUNDARY_THRESHOLD = 1.0e-3
EDGE_PRESSURE_CONTAMINATION_RATIO = 2.0
EXCLUDED_SCIENCE_CASE_AGES = {
    ("G-HI", 50): "z_boundary_contact_pressure_contaminated",
}


class ReviewError(RuntimeError):
    """Raised when an accepted compact input violates the review contract."""


def read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ReviewError(f"refusing to write an empty table: {path.name}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_radio_rows(case: str) -> list[dict[str, Any]]:
    rows = read_rows(RADIO_PATHS[case])
    parsed: list[dict[str, Any]] = []
    for row in rows:
        parsed.append(
            {
                **row,
                "snapshot_index": int(row["snapshot_index"]),
                "fluid_time_myr": float(row["fluid_time_myr"]),
                "frequency_ghz": float(row["frequency_ghz"]),
                "luminosity_w_hz": float(row["luminosity_w_hz"]),
                "effective_magnetic_field_ug": float(
                    row["effective_magnetic_field_ug"]
                ),
            }
        )
    return parsed


def recalculate_breaks() -> tuple[list[dict[str, Any]], float]:
    all_rows: list[dict[str, Any]] = []
    for case in CASES:
        radio = load_radio_rows(case)
        for view in VIEWS:
            fits = fit_spectral_surface([row for row in radio if row["view"] == view])
            all_rows.extend({**fit, "view": view} for fit in fits)

    accepted = {
        (row["case"], int(row["snapshot_index"]), row["view"]): row
        for row in read_rows(ACCEPTED_SYNTHESIS_ROOT / "spectral_fits.csv")
    }
    maximum_relative_difference = 0.0
    for row in all_rows:
        key = (row["case"], int(row["snapshot_index"]), row["view"])
        reference = accepted.get(key)
        if reference is None:
            raise ReviewError(f"accepted spectral surface lacks {key}")
        for field in ("fitted_break_ghz", "reported_break_ghz"):
            value = float(row[field])
            expected = float(reference[field])
            difference = abs(value - expected) / expected
            maximum_relative_difference = max(maximum_relative_difference, difference)
            # Bounded optimiser stopping points vary slightly across SciPy
            # builds while leaving every fit and censoring decision unchanged.
            if difference > 5.0e-7:
                raise ReviewError(f"refitted break frequency drifted for {key}")
    if len(all_rows) != len(CASES) * len(AGES) * len(VIEWS):
        raise ReviewError("refitted spectral surface has incomplete coverage")
    rows_out = [
        row
        for row in all_rows
        if (str(row["case"]), int(row["snapshot_index"]))
        not in EXCLUDED_SCIENCE_CASE_AGES
    ]
    return rows_out, maximum_relative_difference


def mean_pressure_fields() -> dict[tuple[str, int], dict[str, float]]:
    result: dict[tuple[str, int], dict[str, float]] = {}
    for case in CASES:
        path = FLUID_ROOT / f"review_products/{case}/energy_partition_timeseries.csv"
        for row in read_rows(path):
            age = int(row["snapshot_index"])
            if (
                age not in AGES
                or row["side"] != "bipolar_total"
                or row["partition_method"] != "fractional"
            ):
                continue
            volume_kpc3 = float(row["lobe_volume_kpc3"])
            thermal_energy_j = float(row["lobe_thermal_erg"]) * 1.0e-7
            pressure_pa = (
                (GAMMA_GAS - 1.0)
                * thermal_energy_j
                / (volume_kpc3 * KPC_TO_M**3)
            )
            magnetic_energy_density = (
                ETA * pressure_pa / ((GAMMA_GAS - 1.0) * (ETA + 1.0))
            )
            field_ug = math.sqrt(2.0 * MU0_SI * magnetic_energy_density) * 1.0e10
            result[(case, age)] = {
                "mean_pressure_pa": pressure_pa,
                "mean_pressure_field_ug": field_ug,
                "tracer_weighted_volume_kpc3": volume_kpc3,
                "tracer_weighted_thermal_energy_erg": float(row["lobe_thermal_erg"]),
            }
    expected = {(case, age) for case in CASES for age in AGES}
    if set(result) != expected:
        raise ReviewError("mean-pressure field surface has incomplete coverage")
    return result


def _archive_profile(
    archive: tarfile.TarFile, case: str, age: int
) -> list[dict[str, str]]:
    member = f"./{case}/per_snapshot/snapshot_{age:04d}_axial_profile.csv"
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ReviewError(f"fluid archive lacks {member}")
    return list(csv.DictReader(io.TextIOWrapper(extracted)))


def _tracer_bounds(case: str, age: int) -> dict[str, float]:
    rows = [
        row
        for row in read_rows(XRAY_ROOT / case / "level2_truth.csv")
        if int(row["nominal_age_myr"]) == age
        and row["side"] in ("negative_z", "positive_z")
        and math.isclose(
            float(row["threshold"]), TRACER_BOUNDARY_THRESHOLD, rel_tol=0.0, abs_tol=1e-12
        )
    ]
    if len(rows) != 2:
        raise ReviewError(f"expected two tracer components for {case} age {age}")
    return {
        "x_min_kpc": min(float(row["x_min_kpc"]) for row in rows),
        "x_max_kpc": max(float(row["x_max_kpc"]) for row in rows),
        "y_min_kpc": min(float(row["y_min_kpc"]) for row in rows),
        "y_max_kpc": max(float(row["y_max_kpc"]) for row in rows),
        "z_min_kpc": min(float(row["z_min_kpc"]) for row in rows),
        "z_max_kpc": max(float(row["z_max_kpc"]) for row in rows),
    }


def build_boundary_audit() -> list[dict[str, Any]]:
    shock_rows = {
        case: read_rows(FLUID_ROOT / f"review_products/{case}/shock_dynamics.csv")
        for case in CASES
    }
    archive_path = (
        FLUID_ROOT
        / "remote_logs/four_case_fluid_snapshot_census_2026-08-25.tar.gz"
    )
    output: list[dict[str, Any]] = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for case in CASES:
            for age in AGES:
                bounds = _tracer_bounds(case, age)
                x_margin = min(
                    bounds["x_min_kpc"] + DOMAIN_HALF_KPC["x"],
                    DOMAIN_HALF_KPC["x"] - bounds["x_max_kpc"],
                )
                y_margin = min(
                    bounds["y_min_kpc"] + DOMAIN_HALF_KPC["y"],
                    DOMAIN_HALF_KPC["y"] - bounds["y_max_kpc"],
                )
                z_margin = min(
                    bounds["z_min_kpc"] + DOMAIN_HALF_KPC["z"],
                    DOMAIN_HALF_KPC["z"] - bounds["z_max_kpc"],
                )
                selected_shocks = [
                    row
                    for row in shock_rows[case]
                    if int(row["snapshot_index"]) == age and row["status"] == "detected"
                ]
                if not selected_shocks:
                    raise ReviewError(f"no detected shock for {case} age {age}")
                maximum_shock = max(
                    float(row["shock_distance_kpc"]) for row in selected_shocks
                )
                shock_margin = DOMAIN_HALF_KPC["z"] - maximum_shock

                profile = _archive_profile(archive, case, age)
                negative_edge, positive_edge = profile[0], profile[-1]
                negative_ratio = float(negative_edge["pressure_code"]) / float(
                    negative_edge["baseline_pressure_code"]
                )
                positive_ratio = float(positive_edge["pressure_code"]) / float(
                    positive_edge["baseline_pressure_code"]
                )
                outer_cell_width = max(
                    float(negative_edge["dz_kpc"]), float(positive_edge["dz_kpc"])
                )
                occupies_outer_z_cell = min(z_margin, shock_margin) <= 0.51 * outer_cell_width
                pressure_contaminated = max(negative_ratio, positive_ratio) >= (
                    EDGE_PRESSURE_CONTAMINATION_RATIO
                )
                transverse_contact = min(x_margin, y_margin) <= 0.0
                boundary_contact = bool(
                    occupies_outer_z_cell or pressure_contaminated or transverse_contact
                )
                status = (
                    "z_boundary_contact_pressure_contaminated"
                    if boundary_contact
                    else "no_boundary_contact_detected"
                )
                output.append(
                    {
                        "case": case,
                        "snapshot_index": age,
                        "actual_time_myr": float(profile[0]["actual_time_myr"]),
                        "tracer_threshold": TRACER_BOUNDARY_THRESHOLD,
                        **bounds,
                        "x_face_margin_kpc": x_margin,
                        "y_face_margin_kpc": y_margin,
                        "z_face_margin_kpc": z_margin,
                        "maximum_axial_shock_distance_kpc": maximum_shock,
                        "axial_shock_face_margin_kpc": shock_margin,
                        "outer_z_cell_width_kpc": outer_cell_width,
                        "negative_z_edge_pressure_ratio": negative_ratio,
                        "positive_z_edge_pressure_ratio": positive_ratio,
                        "negative_z_edge_vz_over_c": float(negative_edge["vz_code"]),
                        "positive_z_edge_vz_over_c": float(positive_edge["vz_code"]),
                        "occupies_outer_z_cell": occupies_outer_z_cell,
                        "transverse_tracer_contact": transverse_contact,
                        "edge_pressure_contaminated": pressure_contaminated,
                        "boundary_contact": boundary_contact,
                        "boundary_status": status,
                        "integrated_radio_use": (
                            "exclude_boundary_contaminated"
                            if boundary_contact
                            else "retain"
                        ),
                    }
                )
    if len(output) != len(CASES) * len(AGES):
        raise ReviewError("boundary audit has incomplete coverage")
    return output


def build_annual_axial_boundary_audit() -> list[dict[str, Any]]:
    shock_rows = {
        case: read_rows(FLUID_ROOT / f"review_products/{case}/shock_dynamics.csv")
        for case in CASES
    }
    archive_path = (
        FLUID_ROOT
        / "remote_logs/four_case_fluid_snapshot_census_2026-08-25.tar.gz"
    )
    output: list[dict[str, Any]] = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for case in CASES:
            for age in ANNUAL_AGES:
                profile = _archive_profile(archive, case, age)
                negative_edge, positive_edge = profile[0], profile[-1]
                negative_ratio = float(negative_edge["pressure_code"]) / float(
                    negative_edge["baseline_pressure_code"]
                )
                positive_ratio = float(positive_edge["pressure_code"]) / float(
                    positive_edge["baseline_pressure_code"]
                )
                outer_cell_width = max(
                    float(negative_edge["dz_kpc"]), float(positive_edge["dz_kpc"])
                )
                selected_shocks = [
                    row
                    for row in shock_rows[case]
                    if int(row["snapshot_index"]) == age and row["status"] == "detected"
                ]
                maximum_shock = (
                    max(float(row["shock_distance_kpc"]) for row in selected_shocks)
                    if selected_shocks
                    else None
                )
                shock_margin = (
                    DOMAIN_HALF_KPC["z"] - maximum_shock
                    if maximum_shock is not None
                    else None
                )
                occupies_outer_z_cell = bool(
                    shock_margin is not None
                    and shock_margin <= 0.51 * outer_cell_width
                )
                pressure_contaminated = max(negative_ratio, positive_ratio) >= (
                    EDGE_PRESSURE_CONTAMINATION_RATIO
                )
                boundary_contact = occupies_outer_z_cell or pressure_contaminated
                output.append(
                    {
                        "case": case,
                        "snapshot_index": age,
                        "actual_time_myr": float(profile[0]["actual_time_myr"]),
                        "maximum_axial_shock_distance_kpc": (
                            maximum_shock if maximum_shock is not None else ""
                        ),
                        "axial_shock_face_margin_kpc": (
                            shock_margin if shock_margin is not None else ""
                        ),
                        "outer_z_cell_width_kpc": outer_cell_width,
                        "negative_z_edge_pressure_ratio": negative_ratio,
                        "positive_z_edge_pressure_ratio": positive_ratio,
                        "maximum_z_edge_pressure_ratio": max(
                            negative_ratio, positive_ratio
                        ),
                        "negative_z_edge_vz_over_c": float(negative_edge["vz_code"]),
                        "positive_z_edge_vz_over_c": float(positive_edge["vz_code"]),
                        "occupies_outer_z_cell": occupies_outer_z_cell,
                        "edge_pressure_contaminated": pressure_contaminated,
                        "axial_boundary_contact": boundary_contact,
                        "axial_boundary_status": (
                            "boundary_affected"
                            if boundary_contact
                            else "no_axial_boundary_contact_detected"
                        ),
                    }
                )
    if len(output) != len(CASES) * len(ANNUAL_AGES):
        raise ReviewError("annual axial boundary audit has incomplete coverage")
    return output


def build_spectral_age_comparison(
    breaks: Sequence[Mapping[str, Any]],
    fields: Mapping[tuple[str, int], Mapping[str, float]],
    boundary_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    boundary = {
        (row["case"], int(row["snapshot_index"])): row for row in boundary_rows
    }
    radio = {case: load_radio_rows(case) for case in CASES}
    emissivity_fields: dict[tuple[str, int, str], float] = {}
    for case in CASES:
        for row in radio[case]:
            if row["loss_model"] == "full_loss" and math.isclose(
                row["frequency_ghz"], 1.4
            ):
                emissivity_fields[(case, row["snapshot_index"], row["view"])] = row[
                    "effective_magnetic_field_ug"
                ]

    output: list[dict[str, Any]] = []
    for fit in breaks:
        case = str(fit["case"])
        age = int(fit["snapshot_index"])
        view = str(fit["view"])
        boundary_row = boundary[(case, age)]
        choices = (
            (
                "tracer_lobe_mean_pressure",
                float(fields[(case, age)]["mean_pressure_field_ug"]),
                float(fields[(case, age)]["mean_pressure_pa"]),
                True,
            ),
            (
                "emissivity_weighted_1p4ghz",
                emissivity_fields[(case, age, view)],
                "",
                False,
            ),
        )
        for treatment, field_ug, pressure_pa, global_cocoon in choices:
            spectral_age = spectral_age_myr(
                float(fit["reported_break_ghz"]), field_ug, redshift=0.05
            )
            if bool(boundary_row["boundary_contact"]):
                interpretation = "exclude_boundary_contaminated"
            elif fit["spectral_age_limit_direction"] != "none":
                interpretation = fit["spectral_age_limit_direction"]
            else:
                interpretation = "quantitative_in_band_break"
            output.append(
                {
                    "case": case,
                    "snapshot_index": age,
                    "actual_time_myr": fit["actual_time_myr"],
                    "view": view,
                    "spectral_model": fit["spectral_model"],
                    "alpha_injection": fit["alpha_injection"],
                    "fitted_break_ghz": fit["fitted_break_ghz"],
                    "reported_break_ghz": fit["reported_break_ghz"],
                    "break_status": fit["break_status"],
                    "spectral_age_limit_direction": fit[
                        "spectral_age_limit_direction"
                    ],
                    "break_frequency_field_dependence": "independent_of_field_treatment",
                    "field_treatment": treatment,
                    "magnetic_field_ug": field_ug,
                    "mean_pressure_pa": pressure_pa,
                    "global_cocoon_field": global_cocoon,
                    "spectral_age_myr": spectral_age,
                    "spectral_to_true_age_ratio": spectral_age
                    / float(fit["actual_time_myr"]),
                    "boundary_status": boundary_row["boundary_status"],
                    "science_interpretation": interpretation,
                }
            )
    expected_rows = (
        len(CASES) * len(AGES) - len(EXCLUDED_SCIENCE_CASE_AGES)
    ) * len(VIEWS) * 2
    if len(output) != expected_rows:
        raise ReviewError("spectral-age comparison has incomplete coverage")
    return output


def _rows_for(
    rows: Iterable[Mapping[str, Any]], **conditions: Any
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in rows
        if all(row.get(field) == value for field, value in conditions.items())
    ]


def plot_field_comparison(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    colors = {"0deg": "#0072B2", "45deg": "#D55E00", "90deg": "#009E73"}
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), sharex=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        mean_rows = _rows_for(
            rows,
            case=case,
            view="45deg",
            field_treatment="tracer_lobe_mean_pressure",
        )
        valid_mean_rows = [
            row
            for row in mean_rows
            if row["science_interpretation"] != "exclude_boundary_contaminated"
        ]
        axis.plot(
            [row["actual_time_myr"] for row in valid_mean_rows],
            [row["magnetic_field_ug"] for row in valid_mean_rows],
            color="black",
            marker="o",
            linewidth=2.2,
            label="Mean-pressure cocoon",
        )
        for view in VIEWS:
            selected = _rows_for(
                rows,
                case=case,
                view=view,
                field_treatment="emissivity_weighted_1p4ghz",
            )
            valid_selected = [
                row
                for row in selected
                if row["science_interpretation"] != "exclude_boundary_contaminated"
            ]
            axis.plot(
                [row["actual_time_myr"] for row in valid_selected],
                [row["magnetic_field_ug"] for row in valid_selected],
                color=colors[view],
                marker="s",
                linewidth=1.2,
                label=f"Emissivity weighted {view}",
            )
        invalid = [
            row
            for row in rows
            if row["case"] == case
            and (
                row["field_treatment"] == "emissivity_weighted_1p4ghz"
                or row["view"] == "45deg"
            )
            if row["science_interpretation"] == "exclude_boundary_contaminated"
        ]
        if invalid:
            axis.scatter(
                [row["actual_time_myr"] for row in invalid],
                [row["magnetic_field_ug"] for row in invalid],
                marker="x",
                s=90,
                linewidths=2.5,
                color="#CC0000",
                zorder=5,
                label="Boundary contaminated",
            )
        axis.set_title(case)
        axis.set_yscale("log")
        axis.grid(alpha=0.25)
    for axis in axes[-1, :]:
        axis.set_xlabel("Simulation age [Myr]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Magnetic field [microG]")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    boundary_handle, boundary_label = axes[1, 0].get_legend_handles_labels()
    if "Boundary contaminated" in boundary_label:
        index = boundary_label.index("Boundary contaminated")
        handles.append(boundary_handle[index])
        labels.append(boundary_label[index])
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle("Cocoon mean-pressure and radio-emissivity-weighted fields")
    fig.tight_layout(rect=(0, 0.10, 1, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_spectral_ages(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    colors = {"0deg": "#0072B2", "45deg": "#D55E00", "90deg": "#009E73"}
    styles = {
        "tracer_lobe_mean_pressure": "-",
        "emissivity_weighted_1p4ghz": "--",
    }
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), sharex=True, sharey=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        case_rows = [row for row in rows if row["case"] == case]
        maximum = max(
            max(float(row["actual_time_myr"]), float(row["spectral_age_myr"]))
            for row in case_rows
            if row["science_interpretation"] != "exclude_boundary_contaminated"
        )
        axis.plot([0, maximum * 1.05], [0, maximum * 1.05], color="0.55", linewidth=1)
        for treatment in styles:
            for view in VIEWS:
                selected = _rows_for(
                    rows, case=case, view=view, field_treatment=treatment
                )
                valid_selected = [
                    row
                    for row in selected
                    if row["science_interpretation"] != "exclude_boundary_contaminated"
                ]
                axis.plot(
                    [row["actual_time_myr"] for row in valid_selected],
                    [row["spectral_age_myr"] for row in valid_selected],
                    color=colors[view],
                    linestyle=styles[treatment],
                    marker="o" if treatment == "tracer_lobe_mean_pressure" else "s",
                    markersize=4,
                    linewidth=1.3,
                    label=f"{view} {'mean p' if treatment.startswith('tracer') else 'emiss. wtd.'}",
                )
        invalid = [
            row
            for row in case_rows
            if row["science_interpretation"] == "exclude_boundary_contaminated"
        ]
        if invalid:
            axis.scatter(
                [row["actual_time_myr"] for row in invalid],
                [row["spectral_age_myr"] for row in invalid],
                marker="x",
                s=60,
                linewidths=2,
                color="#CC0000",
                zorder=5,
            )
        axis.set_title(case)
        axis.grid(alpha=0.25)
    for axis in axes[-1, :]:
        axis.set_xlabel("True simulation age [Myr]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Inferred spectral age [Myr]")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle("Spectral ages under two magnetic-field treatments")
    fig.tight_layout(rect=(0, 0.11, 1, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_breaks(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    boundary_rows: Sequence[Mapping[str, Any]],
) -> None:
    colors = {"0deg": "#0072B2", "45deg": "#D55E00", "90deg": "#009E73"}
    invalid_keys = {
        (row["case"], int(row["snapshot_index"]))
        for row in boundary_rows
        if row["boundary_contact"]
    }
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5), sharex=True, sharey=True)
    for axis, case in zip(axes.flat, CASES, strict=True):
        for view in VIEWS:
            selected = _rows_for(rows, case=case, view=view)
            valid_selected = [
                row
                for row in selected
                if (case, int(row["snapshot_index"])) not in invalid_keys
            ]
            axis.plot(
                [row["actual_time_myr"] for row in valid_selected],
                [row["fitted_break_ghz"] for row in valid_selected],
                color=colors[view],
                marker="o",
                linewidth=1.4,
                label=view,
            )
            invalid = [
                row
                for row in selected
                if (case, int(row["snapshot_index"])) in invalid_keys
            ]
            if invalid:
                axis.scatter(
                    [row["actual_time_myr"] for row in invalid],
                    [row["fitted_break_ghz"] for row in invalid],
                    marker="x",
                    s=70,
                    linewidths=2,
                    color="#CC0000",
                    zorder=5,
                )
        axis.axhspan(0.15, 15.0, color="#BBBBBB", alpha=0.18)
        axis.axhline(15.0, color="0.45", linewidth=0.8)
        axis.set_title(case)
        axis.set_yscale("log")
        axis.grid(alpha=0.25)
    for axis in axes[-1, :]:
        axis.set_xlabel("Simulation age [Myr]")
    for axis in axes[:, 0]:
        axis.set_ylabel("Fitted break frequency [GHz]")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False)
    fig.suptitle("Radio SED break frequencies (shaded: observed 0.15-15 GHz band)")
    fig.tight_layout(rect=(0, 0.08, 1, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_axial_boundary_pressure(
    path: Path, rows: Sequence[Mapping[str, Any]]
) -> None:
    colors = {
        "C-HI": "#0072B2",
        "C-LO": "#56B4E9",
        "G-HI": "#D55E00",
        "G-LO": "#009E73",
    }
    fig, axis = plt.subplots(figsize=(8.8, 5.2))
    for case in CASES:
        selected = [row for row in rows if row["case"] == case]
        valid = [row for row in selected if not row["axial_boundary_contact"]]
        invalid = [row for row in selected if row["axial_boundary_contact"]]
        axis.plot(
            [row["actual_time_myr"] for row in valid],
            [row["maximum_z_edge_pressure_ratio"] for row in valid],
            color=colors[case],
            linewidth=1.8,
            label=case,
        )
        if invalid:
            axis.scatter(
                [row["actual_time_myr"] for row in invalid],
                [row["maximum_z_edge_pressure_ratio"] for row in invalid],
                marker="x",
                s=75,
                linewidths=2,
                color="#CC0000",
                zorder=5,
            )
    axis.axhline(
        EDGE_PRESSURE_CONTAMINATION_RATIO,
        color="0.45",
        linestyle="--",
        linewidth=1,
        label="Contamination gate",
    )
    axis.set_yscale("log")
    axis.set_xlabel("Simulation age [Myr]")
    axis.set_ylabel("Maximum axial-edge pressure / initial pressure")
    axis.set_title("Annual axial boundary-pressure audit")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_manifest(output_root: Path) -> None:
    rows = []
    for path in sorted(output_root.iterdir()):
        if path.name == "local_asset_manifest.sha256" or not path.is_file():
            continue
        rows.append(f"{sha256_file(path)}  {path.name}")
    (output_root / "local_asset_manifest.sha256").write_text("\n".join(rows) + "\n")


def run(output_root: Path, *, force: bool = False) -> dict[str, Any]:
    output_root = Path(output_root)
    if output_root.exists():
        if not force:
            raise ReviewError(f"output root already exists: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    boundary_rows = build_boundary_audit()
    annual_boundary_rows = build_annual_axial_boundary_audit()
    breaks, maximum_refit_difference = recalculate_breaks()
    fields = mean_pressure_fields()
    age_rows = build_spectral_age_comparison(breaks, fields, boundary_rows)

    write_rows(output_root / "boundary_audit.csv", boundary_rows)
    write_rows(
        output_root / "annual_axial_boundary_audit.csv", annual_boundary_rows
    )
    write_rows(output_root / "spectral_break_frequencies.csv", breaks)
    write_rows(output_root / "spectral_age_field_comparison.csv", age_rows)
    plot_field_comparison(output_root / "magnetic_field_comparison.png", age_rows)
    plot_spectral_ages(output_root / "spectral_age_comparison.png", age_rows)
    plot_breaks(
        output_root / "spectral_break_frequency_evolution.png",
        breaks,
        boundary_rows,
    )
    plot_axial_boundary_pressure(
        output_root / "annual_axial_boundary_pressure.png", annual_boundary_rows
    )

    contaminated = [
        row
        for row in boundary_rows
        if row["boundary_contact"]
    ]
    first_annual_contact = {}
    for case in CASES:
        affected = [
            row
            for row in annual_boundary_rows
            if row["case"] == case and row["axial_boundary_contact"]
        ]
        first_annual_contact[case] = (
            affected[0]["snapshot_index"] if affected else None
        )
    metadata = {
        "status": "complete_boundary_and_spectral_field_review",
        "cases": list(CASES),
        "selected_ages_myr": list(AGES),
        "views": list(VIEWS),
        "boundary_contract": {
            "domain_half_widths_kpc": DOMAIN_HALF_KPC,
            "tracer_threshold": TRACER_BOUNDARY_THRESHOLD,
            "edge_pressure_contamination_ratio": EDGE_PRESSURE_CONTAMINATION_RATIO,
            "evidence": "3D tracer extents, axial shock positions, and axial edge pressure/velocity profiles",
        },
        "field_contract": {
            "eta": ETA,
            "gamma_gas": GAMMA_GAS,
            "mean_pressure": "fractional-tracer thermal energy divided by fractional-tracer volume",
            "emissivity_weighted": "existing ray-traced 1.4 GHz full-loss effective field",
        },
        "break_frequency_contract": "refitted from the five-frequency full-loss SED; independent of magnetic-field treatment",
        "maximum_relative_difference_from_accepted_break_surface": maximum_refit_difference,
        "boundary_contaminated_case_ages": [
            [row["case"], row["snapshot_index"]] for row in contaminated
        ],
        "excluded_science_case_ages": [
            {
                "case": case,
                "snapshot_index": age,
                "reason": reason,
            }
            for (case, age), reason in EXCLUDED_SCIENCE_CASE_AGES.items()
        ],
        "selected_science_ages_by_case": {
            case: [
                age
                for age in AGES
                if (case, age) not in EXCLUDED_SCIENCE_CASE_AGES
            ]
            for case in CASES
        },
        "first_annual_axial_boundary_contact_snapshot": first_annual_contact,
        "row_counts": {
            "boundary_audit": len(boundary_rows),
            "annual_axial_boundary_audit": len(annual_boundary_rows),
            "spectral_break_frequencies": len(breaks),
            "spectral_age_field_comparison": len(age_rows),
        },
    }
    write_json(output_root / "review_metadata.json", metadata)
    write_manifest(output_root)
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args.output_root, force=args.force)
    except (OSError, ValueError, ReviewError) as exc:
        print(f"review_error={exc}")
        return 2
    print(f"status={result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
