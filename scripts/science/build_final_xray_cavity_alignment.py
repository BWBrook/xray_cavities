#!/usr/bin/env python3
"""Build the final C-HI endpoint X-ray/cavity alignment package."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSET_ROOT = ROOT / "docs/science/assets"
DEFAULT_GOAL003 = DEFAULT_ASSET_ROOT / "c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11"
SIDES = ("negative_z", "positive_z", "bipolar_total")
LOBE_SIDES = ("negative_z", "positive_z")
FINAL_INPUT_H5 = (
    "/scratch/bwbrook/xray_cavities_runs/"
    "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5"
)
FINAL_TIMESTEP = "Timestep_51"
TRACER_THRESHOLD = 5.0e-3


def read_rows(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def read_metric_csv(path: Path) -> dict[str, dict[str, str]]:
    return {row["metric"]: row for row in read_rows(path)}


def parse_float(value: Any, *, context: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be numeric") from exc
    if not math.isfinite(out):
        raise ValueError(f"{context} must be finite")
    return out


def finite_positive(value: Any, *, context: str) -> float:
    out = parse_float(value, context=context)
    if out <= 0.0:
        raise ValueError(f"{context} must be positive")
    return out


def rows_by_side(rows: list[dict[str, str]], *, required: tuple[str, ...] = SIDES) -> dict[str, dict[str, str]]:
    out = {row["side"]: row for row in rows}
    missing = sorted(set(required) - set(out))
    if missing:
        raise ValueError(f"missing side rows: {', '.join(missing)}")
    return out


def threshold_label(threshold: float) -> str:
    return f"{threshold:.0e}"


def find_level2_rows(rows: list[dict[str, str]], *, threshold: float = TRACER_THRESHOLD) -> dict[str, dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        if "side" not in row or "threshold" not in row:
            continue
        row_threshold = parse_float(row["threshold"], context="Level 2 threshold")
        if math.isclose(row_threshold, threshold, rel_tol=0.0, abs_tol=threshold * 1.0e-8):
            selected[row["side"]] = row
    return rows_by_side(list(selected.values()))


def metric_value(metrics: dict[str, dict[str, str]], key: str, *, positive: bool = False) -> float:
    if key not in metrics:
        raise ValueError(f"missing metric: {key}")
    if positive:
        return finite_positive(metrics[key]["value"], context=f"metric {key}")
    return parse_float(metrics[key]["value"], context=f"metric {key}")


def load_xraise_metadata(path: Path) -> dict[str, Any]:
    metadata = json.loads(path.read_text())
    input_h5 = str(metadata.get("input_h5", ""))
    timestep = str(metadata.get("timestep", ""))
    if input_h5 != FINAL_INPUT_H5:
        raise ValueError(f"X-ray metadata input_h5 mismatch: {input_h5}")
    if timestep != FINAL_TIMESTEP:
        raise ValueError(f"X-ray metadata timestep mismatch: {timestep}")
    finite_positive(metadata.get("time_myr"), context="X-ray metadata time_myr")
    if abs(float(metadata["time_myr"]) - 50.0) > 1.0e-4:
        raise ValueError(f"X-ray metadata time_myr is not final endpoint: {metadata['time_myr']}")
    return metadata


def load_cavity_metadata(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key] = value
    input_h5 = out.get("input_h5", "")
    timestep = out.get("timestep", "")
    if input_h5 != FINAL_INPUT_H5:
        raise ValueError(f"cavity metadata input_h5 mismatch: {input_h5}")
    if timestep != FINAL_TIMESTEP:
        raise ValueError(f"cavity metadata timestep mismatch: {timestep}")
    time_myr = finite_positive(out.get("time_myr"), context="cavity metadata time_myr")
    if abs(time_myr - 50.0) > 1.0e-4:
        raise ValueError(f"cavity metadata time_myr is not final endpoint: {time_myr}")
    return out


def validate_xray_summary(metrics: dict[str, dict[str, str]]) -> dict[str, float]:
    out = {
        "time_myr": metric_value(metrics, "time_myr", positive=True),
        "raw_xray_max": metric_value(metrics, "raw_xray_max", positive=True),
        "corrected_xray_max": metric_value(metrics, "corrected_xray_max", positive=True),
        "raw_xray_sum": metric_value(metrics, "raw_xray_sum", positive=True),
        "corrected_xray_sum": metric_value(metrics, "corrected_xray_sum", positive=True),
        "correction_ratio_positive_max": metric_value(metrics, "correction_ratio_positive_max", positive=True),
        "correction_ratio_positive_sum": metric_value(metrics, "correction_ratio_positive_sum", positive=True),
    }
    if abs(out["time_myr"] - 50.0) > 1.0e-4:
        raise ValueError(f"X-ray summary time_myr is not final endpoint: {out['time_myr']}")
    return out


def validate_cavity_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_side = rows_by_side(rows, required=LOBE_SIDES)
    for side in LOBE_SIDES:
        row = by_side[side]
        for key in (
            "tracer_extent_volume_kpc3",
            "ambient_pressure_dyn_cm2",
            "ambient_density_g_cm3",
            "pV_erg",
            "four_pV_erg",
            "cavity_distance_kpc",
            "sound_speed_km_s",
            "sound_age_myr",
            "buoyancy_age_myr",
            "refill_age_myr",
            "semi_x_kpc",
            "semi_y_kpc",
            "semi_z_kpc",
        ):
            finite_positive(row[key], context=f"{side} cavity {key}")
    return by_side


def build_lobe_rows(
    *,
    cavity_by_side: dict[str, dict[str, str]],
    truth_by_side: dict[str, dict[str, str]],
    radio_by_side: dict[str, dict[str, str]],
    level1: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    injected_one_side = finite_positive(
        level1["injected_energy_one_sided_elapsed"]["value"],
        context="Level 1 one-sided injected energy",
    )
    injected_bipolar = finite_positive(
        level1["injected_energy_bipolar_elapsed"]["value"],
        context="Level 1 bipolar injected energy",
    )

    rows: list[dict[str, Any]] = []
    for side in LOBE_SIDES:
        cavity = cavity_by_side[side]
        truth = truth_by_side[side]
        radio = radio_by_side[side]
        cavity_volume = finite_positive(cavity["tracer_extent_volume_kpc3"], context=f"{side} cavity volume")
        truth_volume = finite_positive(truth["volume_kpc3"], context=f"{side} truth volume")
        truth_energy = finite_positive(truth["total_energy_erg"], context=f"{side} truth energy")
        four_pv = finite_positive(cavity["four_pV_erg"], context=f"{side} four_pV")
        rows.append(
            {
                "side": side,
                "cavity_tracer_extent_volume_kpc3": cavity_volume,
                "level2_volume_kpc3": truth_volume,
                "cavity_to_level2_volume_ratio": cavity_volume / truth_volume,
                "level2_total_energy_erg": truth_energy,
                "cavity_pV_erg": finite_positive(cavity["pV_erg"], context=f"{side} pV"),
                "cavity_four_pV_erg": four_pv,
                "four_pV_over_level2_energy": four_pv / truth_energy,
                "four_pV_over_injected_energy_reference": four_pv / injected_one_side,
                "sound_age_myr": finite_positive(cavity["sound_age_myr"], context=f"{side} sound age"),
                "buoyancy_age_myr": finite_positive(cavity["buoyancy_age_myr"], context=f"{side} buoyancy age"),
                "refill_age_myr": finite_positive(cavity["refill_age_myr"], context=f"{side} refill age"),
                "radio_lossy_luminosity_doppler_w_hz": finite_positive(
                    radio["lossy_luminosity_doppler_w_hz"],
                    context=f"{side} radio lossy luminosity",
                ),
                "radio_volume_kpc3": finite_positive(radio["volume_kpc3"], context=f"{side} radio volume"),
                "radio_particle_count": int(parse_float(radio["particle_count"], context=f"{side} particle count")),
            }
        )

    bipolar_cavity_volume = sum(row["cavity_tracer_extent_volume_kpc3"] for row in rows)
    bipolar_four_pv = sum(row["cavity_four_pV_erg"] for row in rows)
    bipolar_pv = sum(row["cavity_pV_erg"] for row in rows)
    truth = truth_by_side["bipolar_total"]
    radio = radio_by_side["bipolar_total"]
    truth_volume = finite_positive(truth["volume_kpc3"], context="bipolar truth volume")
    truth_energy = finite_positive(truth["total_energy_erg"], context="bipolar truth energy")
    rows.append(
        {
            "side": "bipolar_total",
            "cavity_tracer_extent_volume_kpc3": bipolar_cavity_volume,
            "level2_volume_kpc3": truth_volume,
            "cavity_to_level2_volume_ratio": bipolar_cavity_volume / truth_volume,
            "level2_total_energy_erg": truth_energy,
            "cavity_pV_erg": bipolar_pv,
            "cavity_four_pV_erg": bipolar_four_pv,
            "four_pV_over_level2_energy": bipolar_four_pv / truth_energy,
            "four_pV_over_injected_energy_reference": bipolar_four_pv / injected_bipolar,
            "sound_age_myr": sum(row["sound_age_myr"] for row in rows) / len(rows),
            "buoyancy_age_myr": sum(row["buoyancy_age_myr"] for row in rows) / len(rows),
            "refill_age_myr": sum(row["refill_age_myr"] for row in rows) / len(rows),
            "radio_lossy_luminosity_doppler_w_hz": finite_positive(
                radio["lossy_luminosity_doppler_w_hz"],
                context="bipolar radio lossy luminosity",
            ),
            "radio_volume_kpc3": finite_positive(radio["volume_kpc3"], context="bipolar radio volume"),
            "radio_particle_count": int(parse_float(radio["particle_count"], context="bipolar particle count")),
        }
    )
    return rows


def gate_status(lobe_rows: list[dict[str, Any]], *, volume_tolerance: float = 0.05) -> str:
    for row in lobe_rows:
        ratio = float(row["cavity_to_level2_volume_ratio"])
        if abs(ratio - 1.0) > volume_tolerance:
            return "review"
    return "green"


def write_dict_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_metric_rows(
    *,
    xray: dict[str, float],
    lobe_rows: list[dict[str, Any]],
    level1: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    bipolar = next(row for row in lobe_rows if row["side"] == "bipolar_total")
    return [
        {"category": "xray", "metric": key, "value": value, "unit": unit, "source": "xraise_grid_smoke_summary.csv"}
        for key, value, unit in (
            ("time_myr", xray["time_myr"], "Myr"),
            ("raw_xray_max", xray["raw_xray_max"], "mJy sr^-1"),
            ("corrected_xray_max", xray["corrected_xray_max"], "mJy sr^-1"),
            ("raw_xray_sum", xray["raw_xray_sum"], "mJy sr^-1 pixels"),
            ("corrected_xray_sum", xray["corrected_xray_sum"], "mJy sr^-1 pixels"),
            ("correction_ratio_positive_max", xray["correction_ratio_positive_max"], "dimensionless"),
        )
    ] + [
        {
            "category": "truth_level1",
            "metric": "injected_energy_one_sided_elapsed",
            "value": finite_positive(
                level1["injected_energy_one_sided_elapsed"]["value"],
                context="Level 1 one-sided injected energy",
            ),
            "unit": "erg",
            "source": "level1_injected_energy.csv",
        },
        {
            "category": "truth_level1",
            "metric": "injected_energy_bipolar_elapsed",
            "value": finite_positive(
                level1["injected_energy_bipolar_elapsed"]["value"],
                context="Level 1 bipolar injected energy",
            ),
            "unit": "erg",
            "source": "level1_injected_energy.csv",
        },
        {
            "category": "cavity",
            "metric": "pV_bipolar",
            "value": bipolar["cavity_pV_erg"],
            "unit": "erg",
            "source": "cavity_stub_summary.csv",
        },
        {
            "category": "cavity",
            "metric": "four_pV_bipolar",
            "value": bipolar["cavity_four_pV_erg"],
            "unit": "erg",
            "source": "cavity_stub_summary.csv",
        },
        {
            "category": "cavity",
            "metric": "four_pV_over_level2_energy_bipolar",
            "value": bipolar["four_pV_over_level2_energy"],
            "unit": "ratio",
            "source": "final_xray_cavity_alignment_lobes.csv",
        },
        {
            "category": "radio",
            "metric": "radio_luminosity_bipolar",
            "value": bipolar["radio_lossy_luminosity_doppler_w_hz"],
            "unit": "W Hz^-1",
            "source": "sparse_particle_radio_lobe_summary.csv",
        },
    ]


def centres_to_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2:
        raise ValueError("need at least two coordinate centres")
    mids = 0.5 * (values[:-1] + values[1:])
    first = values[0] - (mids[0] - values[0])
    last = values[-1] + (values[-1] - mids[-1])
    return np.concatenate([[first], mids, [last]])


def log10_positive(values: np.ndarray) -> np.ndarray:
    out = np.full_like(values, np.nan, dtype=float)
    mask = np.isfinite(values) & (values > 0.0)
    out[mask] = np.log10(values[mask])
    return out


def cmap_with_background(name: str):
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad("#f2f2f2")
    return cmap


def add_cavity_boundaries(ax: plt.Axes, cavity_boundary: Path) -> None:
    by_side: dict[str, list[tuple[float, float]]] = {}
    with cavity_boundary.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            by_side.setdefault(row["side"], []).append(
                (
                    parse_float(row["x_kpc"], context="cavity boundary x_kpc"),
                    parse_float(row["z_kpc"], context="cavity boundary z_kpc"),
                )
            )
    colours = {"negative_z": "#1f78b4", "positive_z": "#e31a1c"}
    for side, points in by_side.items():
        xy = np.asarray(points)
        ax.plot(xy[:, 0], xy[:, 1], color=colours.get(side, "black"), lw=1.1, alpha=0.95)


def plot_package(
    *,
    output_png: Path,
    xraise_dir: Path,
    cavity_dir: Path,
    radio_dir: Path,
    lobe_rows: list[dict[str, Any]],
    xlim_kpc: float,
    zlim_kpc: float,
) -> None:
    x_xray = np.loadtxt(xraise_dir / "x_kpc.tsv")
    z_xray = np.loadtxt(xraise_dir / "z_kpc.tsv")
    x_radio = np.loadtxt(radio_dir / "x_kpc.tsv")
    z_radio = np.loadtxt(radio_dir / "z_kpc.tsv")
    xray = np.loadtxt(xraise_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv", delimiter="\t")
    tracer = np.loadtxt(xraise_dir / "tracer_max_los.tsv", delimiter="\t")
    radio = np.loadtxt(radio_dir / "radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv", delimiter="\t")

    fig = plt.figure(figsize=(10.6, 8.2), constrained_layout=True)
    layout_engine = fig.get_layout_engine()
    if layout_engine is not None:
        layout_engine.set(w_pad=0.035, h_pad=0.035, hspace=0.04, wspace=0.035)
    grid = fig.add_gridspec(2, 3, height_ratios=[1.35, 1.0])
    xray_ax = fig.add_subplot(grid[0, 0])
    tracer_ax = fig.add_subplot(grid[0, 1])
    radio_ax = fig.add_subplot(grid[0, 2])
    metric_ax = fig.add_subplot(grid[1, :])
    panels = [
        (
            xray_ax,
            x_xray,
            z_xray,
            log10_positive(xray),
            "1 keV XRAiSE X-ray",
            "log10 mJy sr$^{-1}$",
            "magma",
        ),
        (
            tracer_ax,
            x_xray,
            z_xray,
            np.where(tracer > 0.0, tracer, np.nan),
            "Tracer max along LOS",
            "max tracer",
            "viridis",
        ),
        (
            radio_ax,
            x_radio,
            z_radio,
            log10_positive(radio),
            "150 MHz radio",
            "log10 mJy sr$^{-1}$",
            "magma",
        ),
    ]
    for ax, x, z, values, title, label, cmap in panels:
        mesh = ax.pcolormesh(
            centres_to_edges(x),
            centres_to_edges(z),
            values,
            shading="auto",
            cmap=cmap_with_background(cmap),
        )
        add_cavity_boundaries(ax, cavity_dir / "cavity_ellipse_boundary_0deg.tsv")
        fig.colorbar(mesh, ax=ax, shrink=0.8, pad=0.035, aspect=24, label=label)
        ax.set_title(title, fontsize=10.5, pad=6)
        ax.set_xlabel("x (kpc)")
        ax.set_ylabel("z (kpc)")
        ax.set_xlim(-xlim_kpc, xlim_kpc)
        ax.set_ylim(-zlim_kpc, zlim_kpc)
        ax.set_aspect("equal", adjustable="box")

    metric_ax.set_title("Cavity and truth energy scale", fontsize=11, pad=8)
    bipolar = next(row for row in lobe_rows if row["side"] == "bipolar_total")
    energy_rows = [
        ("Injected", bipolar["cavity_four_pV_erg"] / bipolar["four_pV_over_injected_energy_reference"]),
        ("Tracer lobe", bipolar["level2_total_energy_erg"]),
        ("Cavity 4pV", bipolar["cavity_four_pV_erg"]),
    ]
    values = [value / 1.0e59 for _label, value in energy_rows]
    labels = [label for label, _value in energy_rows]
    y = np.arange(len(values))
    metric_ax.barh(y, values, color=["#4c78a8", "#54a24b", "#f58518"])
    metric_ax.set_yticks(y, labels)
    metric_ax.invert_yaxis()
    metric_ax.set_xlabel("energy (1e59 erg)")
    metric_ax.grid(axis="x", color="#dddddd", lw=0.7)
    metric_ax.set_xlim(0.0, max(values) * 1.22)
    for idx, value in enumerate(values):
        metric_ax.text(value + max(values) * 0.02, idx, f"{value:.2f}", va="center", fontsize=9)
    metric_ax.text(
        0.04,
        0.05,
        f"4pV/tracer energy: {bipolar['four_pV_over_level2_energy']:.4f}\n"
        f"Radio L_150: {bipolar['radio_lossy_luminosity_doppler_w_hz']:.3e} W Hz$^{{-1}}$",
        transform=metric_ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.82, "edgecolor": "#cccccc"},
    )

    fig.suptitle("C-HI final endpoint X-ray/cavity alignment gate", fontsize=13)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def build_summary_markdown(*, lobe_rows: list[dict[str, Any]], status: str, xray: dict[str, float]) -> str:
    lines = [
        "# C-HI Final Endpoint X-ray/Cavity Alignment Gate",
        "",
        f"Gate status: `{status}`.",
        "",
        "Target: final 50 Myr `C-HI`, `0 deg`, 1 keV XRAiSE/GRAiLE grid X-ray plus the existing ellipsoid/ambient-shell cavity protocol.",
        "",
        "## X-ray",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| corrected max | `{xray['corrected_xray_max']:.6e} mJy sr^-1` |",
        f"| corrected sum | `{xray['corrected_xray_sum']:.6e} mJy sr^-1 pixels` |",
        f"| correction-ratio positive max | `{xray['correction_ratio_positive_max']:.6g}` |",
        "",
        "## Lobe Alignment",
        "",
        "| Side | Cavity volume / Level 2 volume | 4pV / Level 2 energy | 4pV / injected-energy reference | Radio L150 (W Hz^-1) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in lobe_rows:
        lines.append(
            f"| `{row['side']}` | `{row['cavity_to_level2_volume_ratio']:.6g}` | "
            f"`{row['four_pV_over_level2_energy']:.6g}` | "
            f"`{row['four_pV_over_injected_energy_reference']:.6g}` | "
            f"`{row['radio_lossy_luminosity_doppler_w_hz']:.6e}` |"
        )
    lines.extend(
        [
            "",
            "Caveats: cavity ages use the current hydrostatic-proxy ambient-shell method; Level 3 ambient energy remains out of scope; no beam, detector, exposure, source-age sampling, or multi-angle treatment is included.",
            "",
        ]
    )
    return "\n".join(lines)


def build_package(
    *,
    xraise_dir: Path,
    cavity_dir: Path,
    truth_dir: Path,
    radio_dir: Path,
    output_dir: Path,
    xlim_kpc: float = 45.0,
    zlim_kpc: float = 230.0,
) -> dict[str, Any]:
    xraise_metadata = load_xraise_metadata(xraise_dir / "xraise_grid_smoke_metadata.json")
    cavity_metadata = load_cavity_metadata(cavity_dir / "cavity_stub_metadata.txt")
    xray = validate_xray_summary(read_metric_csv(xraise_dir / "xraise_grid_smoke_summary.csv"))
    cavity_by_side = validate_cavity_rows(read_rows(cavity_dir / "cavity_stub_summary.csv"))
    level1 = read_metric_csv(truth_dir / "level1_injected_energy.csv")
    truth_by_side = find_level2_rows(read_rows(truth_dir / "level2_tracer_lobe_truth.csv"))
    radio_by_side = rows_by_side(read_rows(radio_dir / "sparse_particle_radio_lobe_summary.csv"))
    lobe_rows = build_lobe_rows(
        cavity_by_side=cavity_by_side,
        truth_by_side=truth_by_side,
        radio_by_side=radio_by_side,
        level1=level1,
    )
    status = gate_status(lobe_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_dict_rows(output_dir / "final_xray_cavity_alignment_lobes.csv", lobe_rows)
    write_dict_rows(
        output_dir / "final_xray_cavity_alignment_metrics.csv",
        build_metric_rows(xray=xray, lobe_rows=lobe_rows, level1=level1),
    )
    plot_package(
        output_png=output_dir / "c_hi_final_endpoint_xray_cavity_alignment.png",
        xraise_dir=xraise_dir,
        cavity_dir=cavity_dir,
        radio_dir=radio_dir,
        lobe_rows=lobe_rows,
        xlim_kpc=xlim_kpc,
        zlim_kpc=zlim_kpc,
    )

    metadata = {
        "gate_status": status,
        "input_h5": FINAL_INPUT_H5,
        "timestep": FINAL_TIMESTEP,
        "view": "0 deg, projected along simulation y axis",
        "tracer_threshold": threshold_label(TRACER_THRESHOLD),
        "xray_energy": "1 keV",
        "xraise_dir": str(xraise_dir),
        "cavity_dir": str(cavity_dir),
        "truth_dir": str(truth_dir),
        "radio_dir": str(radio_dir),
        "xraise_metadata": xraise_metadata,
        "cavity_metadata": cavity_metadata,
        "caveats": [
            "cavity ages are hydrostatic-proxy ambient-shell estimates",
            "Level 3 ambient thermal/kinetic/gravitational energy is not included",
            "no beam, detector, exposure, source-age sampling, or multi-angle treatment is included",
        ],
    }
    (output_dir / "final_xray_cavity_alignment_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "final_xray_cavity_alignment_summary.md").write_text(
        build_summary_markdown(lobe_rows=lobe_rows, status=status, xray=xray)
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xraise-dir", type=Path, required=True)
    parser.add_argument("--cavity-dir", type=Path, required=True)
    parser.add_argument("--truth-dir", type=Path, default=DEFAULT_GOAL003 / "final_truth")
    parser.add_argument("--radio-dir", type=Path, default=DEFAULT_GOAL003 / "bridge_external_loss_volume_coupled")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--xlim-kpc", type=float, default=45.0)
    parser.add_argument("--zlim-kpc", type=float, default=230.0)
    args = parser.parse_args()
    metadata = build_package(
        xraise_dir=args.xraise_dir,
        cavity_dir=args.cavity_dir,
        truth_dir=args.truth_dir,
        radio_dir=args.radio_dir,
        output_dir=args.output_dir,
        xlim_kpc=args.xlim_kpc,
        zlim_kpc=args.zlim_kpc,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
