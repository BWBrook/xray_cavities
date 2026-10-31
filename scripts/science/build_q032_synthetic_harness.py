#!/usr/bin/env python3
"""Run the Q-032 method ladder on synthetic maps with known cavities.

Scenarios cover the cluster and group atmospheres, the 0 and 45 degree
production views (90 degrees is identical to 0 degrees for a spherical
atmosphere in the square production box), a null map, and bipolar cavity
pairs from compact to aperture-filling sizes. Cavities are evacuated, partly
filled, or evacuated inside a compressed rim. Rim arms separate the thermal
convention from the geometry: isobaric and isothermal density x2 rims of
width 0.15a, and Mach 1.5 Rankine-Hugoniot shells either 0.15a wide or wide
enough to hold the displaced cavity mass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCIENCE_DIR = Path(__file__).resolve().parent
if str(SCIENCE_DIR) not in sys.path:
    sys.path.insert(0, str(SCIENCE_DIR))

import xray_cavity_method_ladder as ladder
import xray_cavity_synthetic as synthetic

ROOT = SCIENCE_DIR.parents[1]
AXES_ROOT = ROOT / "docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products"
DEFAULT_OUTPUT = ROOT / "docs/science/assets/q032_synthetic_harness_2026-10-31/results_r2"
ENVIRONMENTS = ("cluster", "group")
VIEWS = ("0deg", "45deg")
ALONG_JET_KPC = (10.0, 20.0, 40.0, 60.0, 90.0)
ASPECT = 0.6
SHOCK_MACH = 1.5
SHOCK_DENSITY, SHOCK_TEMPERATURE = synthetic.rankine_hugoniot(SHOCK_MACH)
VARIANTS = {
    "evacuated": {"density_factor": 0.01},
    "partly_filled": {"density_factor": 0.3},
    "rim_isobaric_x2": {"density_factor": 0.01, "rim_fraction": 0.15, "rim_density_factor": 2.0},
    "rim_isothermal_x2": {
        "density_factor": 0.01, "rim_fraction": 0.15, "rim_density_factor": 2.0, "rim_temperature_factor": 1.0,
    },
    "rim_shock_m1p5": {
        "density_factor": 0.01, "rim_fraction": 0.15,
        "rim_density_factor": SHOCK_DENSITY, "rim_temperature_factor": SHOCK_TEMPERATURE,
    },
    "rim_shock_m1p5_mass_matched": {
        "density_factor": 0.01, "rim_fraction": "mass_matched",
        "rim_density_factor": SHOCK_DENSITY, "rim_temperature_factor": SHOCK_TEMPERATURE,
    },
}
RIM_VARIANTS = tuple(name for name in VARIANTS if name.startswith("rim_"))
ORACLE_THRESHOLDS = (0.05, 0.10, 0.20)
NULL_QUANTILE = 99.5
NULL_FLOOR = 0.05


def axes(view: str, stride: int) -> tuple[np.ndarray, np.ndarray]:
    horizontal_name = "x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"
    horizontal = np.loadtxt(AXES_ROOT / f"xraise_grid_{view}" / horizontal_name)[::stride]
    vertical = np.loadtxt(AXES_ROOT / f"xraise_grid_{view}" / "z_kpc.tsv")[::stride]
    return horizontal, vertical


def cavities(atmosphere: synthetic.Atmosphere, along: float, variant: str) -> tuple[synthetic.Spheroid, ...]:
    settings = VARIANTS[variant]
    pair = synthetic.bipolar_pair(
        semiaxis_along_jet_kpc=along,
        semiaxis_across_jet_kpc=ASPECT * along,
        density_factor=settings["density_factor"],
        rim_density_factor=settings.get("rim_density_factor", 1.0),
        rim_temperature_factor=settings.get("rim_temperature_factor"),
    )
    fraction = settings.get("rim_fraction", 0.0)
    width = (
        synthetic.mass_matched_rim_width(atmosphere, pair[1]) if fraction == "mass_matched" else fraction * along
    )
    return tuple(synthetic.Spheroid(**{**cavity.__dict__, "rim_width_kpc": width}) for cavity in pair)


def ladder_runs(image: np.ndarray, null: np.ndarray, horizontal: np.ndarray, vertical: np.ndarray, null_threshold: float):
    observer_radial = ladder.observer_radial_background(image, horizontal, vertical)
    yield ladder.legacy_area_fraction(image, horizontal, vertical)
    yield ladder.legacy_area_fraction(image, horizontal, vertical, background=null, background_label="oracle")
    yield ladder.seed_grow(image, horizontal, vertical)
    yield ladder.seed_grow(image, horizontal, vertical, background=null, background_label="oracle")
    for threshold in ORACLE_THRESHOLDS:
        yield ladder.deficit_threshold(
            image, horizontal, vertical, background=null, background_label="oracle", threshold=threshold,
        )
    yield ladder.deficit_threshold(
        image, horizontal, vertical, background=observer_radial,
        background_label="observer_radial_null_calibrated", threshold=null_threshold,
    )


def run(output: Path, stride: int) -> dict[str, Any]:
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    output.mkdir(parents=True)
    rows: list[dict[str, Any]] = []
    stamps: dict[tuple[str, str, float, str], tuple[synthetic.SyntheticMap, list[ladder.Recovery]]] = {}
    thresholds: list[dict[str, Any]] = []
    rim_budgets: list[dict[str, Any]] = []
    for environment in ENVIRONMENTS:
        atmosphere = synthetic.load_atmosphere(environment)
        for view in VIEWS:
            horizontal, vertical = axes(view, stride)
            view_deg = float(view.removesuffix("deg"))
            null_map = synthetic.render_map(atmosphere, horizontal, vertical, view_deg=view_deg)
            null = null_map.surface_brightness
            null_threshold = ladder.null_calibrated_threshold(
                null, horizontal, vertical, quantile=NULL_QUANTILE, floor=NULL_FLOOR,
            )
            thresholds.append({"environment": environment, "view": view, "null_calibrated_threshold": null_threshold})
            scenarios = [("null", 0.0, null_map)]
            for variant in VARIANTS:
                for along in ALONG_JET_KPC:
                    pair = cavities(atmosphere, along, variant)
                    scenarios.append((variant, along, synthetic.render_map(
                        atmosphere, horizontal, vertical, pair, view_deg=view_deg,
                    )))
                    if variant in RIM_VARIANTS and view == VIEWS[0]:
                        rim_budgets.append({
                            "environment": environment, "variant": variant, "semiaxis_along_jet_kpc": along,
                            "rim_width_kpc": pair[1].rim_width_kpc,
                            "rim_density_factor": pair[1].rim_density_factor,
                            "rim_temperature_factor": (
                                pair[1].rim_temperature_factor
                                if pair[1].rim_temperature_factor is not None
                                else 1.0 / pair[1].rim_density_factor
                            ),
                            **synthetic.rim_mass_budget(atmosphere, pair[1]),
                        })
            for variant, along, rendered in scenarios:
                truth_masks = {side: rendered.cavity_path_length_kpc.get(side, np.zeros(null.shape)) > 0.0 for side in ladder.SIDES}
                truth_volumes = {side: rendered.cavity_volume_kpc3.get(side, 0.0) for side in ladder.SIDES}
                results = list(ladder_runs(rendered.surface_brightness, null, horizontal, vertical, null_threshold))
                for result in results:
                    for row in ladder.score_rows(
                        result, horizontal, vertical, truth_masks=truth_masks, truth_volumes=truth_volumes,
                    ):
                        rows.append({
                            "environment": environment, "view": view, "variant": variant,
                            "semiaxis_along_jet_kpc": along, "semiaxis_across_jet_kpc": ASPECT * along,
                            **row,
                        })
                stamps[(environment, view, along, variant)] = (rendered, results)
                print(f"{environment} {view} {variant} {along:g}", flush=True)
    write_rows(output / "synthetic_recovery.csv", rows)
    write_rows(output / "null_calibrated_thresholds.csv", thresholds)
    write_rows(output / "rim_mass_budget.csv", rim_budgets)
    write_rows(output / "summary_by_size.csv", summarise(rows))
    volume_figure(rows, output / "synthetic_volume_recovery.png")
    stamp_figure(stamps, output / "synthetic_postage_stamps.png")
    metadata = {
        "status": "complete_q032_synthetic_harness",
        "stride": stride,
        "environments": list(ENVIRONMENTS),
        "views": list(VIEWS),
        "semiaxes_along_jet_kpc": list(ALONG_JET_KPC),
        "aspect_across_over_along": ASPECT,
        "variants": VARIANTS,
        "shock_mach": SHOCK_MACH,
        "oracle_thresholds": list(ORACLE_THRESHOLDS),
        "null_threshold_rule": f"max({NULL_FLOOR}, {NULL_QUANTILE}th percentile of |observer radial deficit| on the null map in the 120 kpc aperture)",
        "emissivity": (
            "n^2 T^-1/2 exp(-1 keV/kT); cavity fills pressure-matched (T = T_amb/density_factor); "
            "rim temperature = T_amb * rim_temperature_factor, isobaric when absent"
        ),
        "summary_rule": (
            "median over all sides of the 2 environments x 2 views, nondetections counted as zero; "
            "detected-only medians and detection counts reported separately"
        ),
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip(),
        "row_count": len(rows),
    }
    (output / "synthetic_harness_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(output.iterdir())
        if path.is_file()
    ]
    (output / "manifest.sha256").write_text("\n".join(lines) + "\n")
    return metadata


def run_label(row: dict[str, Any]) -> str:
    label = f"{row['method']}/{row['background']}"
    return f"{label}/{float(row['threshold']):.2f}" if row["background"] == "oracle" and row["method"] == ladder.THRESHOLD else label


def summarise(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, float], list[dict[str, Any]]] = {}
    for row in rows:
        if row["variant"] == "null":
            continue
        for scope in ("all", row["environment"]):
            groups.setdefault((run_label(row), row["variant"], scope, row["semiaxis_along_jet_kpc"]), []).append(row)
    summary = []
    for (label, variant, scope, along), members in groups.items():
        ratios = np.array([row["volume_ratio_revolution"] for row in members])
        detected = np.array([row["detected"] for row in members])
        topology = [row["topology_class"] for row in members]
        summary.append({
            "run": label, "variant": variant, "scope": scope, "semiaxis_along_jet_kpc": along,
            "sides": len(members), "sides_detected": int(detected.sum()),
            "median_revolution_ratio_all_sides": float(np.median(ratios)),
            "median_revolution_ratio_detected": float(np.median(ratios[detected])) if detected.any() else float("nan"),
            "median_true_area_inside_aperture_fraction": float(
                np.median([row["true_area_inside_aperture_fraction"] for row in members])
            ),
            "sides_in_two_separate_components": topology.count("two_separate_components"),
            "sides_in_connected_cross_midplane_component": topology.count("connected_cross_midplane_component"),
        })
    return summary


def write_rows(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


PANELS = (
    ("legacy_area_1pct", "observer", None, "Legacy 1% area (production)"),
    ("legacy_area_1pct", "oracle", None, "Legacy 1% area, oracle background"),
    ("seed_grow_goal045", "observer", None, "Seed-and-grow (Goal 045)"),
    ("seed_grow_goal045", "oracle", None, "Seed-and-grow, oracle background"),
    ("deficit_threshold", "oracle", 0.10, "Deficit > 0.10, oracle background"),
    ("deficit_threshold", "observer_radial_null_calibrated", None, "Deficit > null-calibrated, observer background"),
)
COLOURS = {
    "evacuated": "#1f77b4", "partly_filled": "#ff7f0e", "rim_isobaric_x2": "#2ca02c",
    "rim_isothermal_x2": "#d62728", "rim_shock_m1p5": "#9467bd", "rim_shock_m1p5_mass_matched": "#8c564b",
}
MARKERS = {("cluster", "0deg"): "o", ("cluster", "45deg"): "s", ("group", "0deg"): "^", ("group", "45deg"): "D"}


def volume_figure(rows: Sequence[dict[str, Any]], path: Path) -> None:
    figure, panels = plt.subplots(2, 3, figsize=(13, 8), sharex=True, sharey=True)
    for axis, (method, background, threshold, title) in zip(panels.ravel(), PANELS, strict=True):
        for row in rows:
            if row["method"] != method or row["background"] != background or row["variant"] == "null":
                continue
            if threshold is not None and not np.isclose(row["threshold"], threshold):
                continue
            ratio = row["volume_ratio_revolution"]
            axis.scatter(
                row["true_volume_kpc3"], max(ratio, 1.0e-3),
                color=COLOURS[row["variant"]], marker=MARKERS[(row["environment"], row["view"])],
                s=22, alpha=0.8, edgecolors="none",
            )
        axis.axhline(1.0, color="0.3", lw=0.8)
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_ylim(8.0e-4, 5.0)
        axis.set_title(title, fontsize=10)
    for axis in panels[1]:
        axis.set_xlabel("True cavity volume per side (kpc$^3$)")
    for axis in panels[:, 0]:
        axis.set_ylabel("Recovered / true volume (revolution)")
    handles = [plt.Line2D([], [], color=c, marker="o", ls="", label=v.replace("_", " ")) for v, c in COLOURS.items()]
    handles += [plt.Line2D([], [], color="0.4", marker=m, ls="", label=f"{e} {v}") for (e, v), m in MARKERS.items()]
    figure.legend(handles=handles, loc="lower center", ncol=5, fontsize=8, frameon=False)
    figure.suptitle("Q-032 synthetic recovery: undetected sides plotted at 1e-3", fontsize=11)
    figure.tight_layout(rect=(0, 0.08, 1, 0.97))
    figure.savefig(path, dpi=130)
    plt.close(figure)


STAMP_SCENARIOS = (
    ("cluster", "0deg", 0.0, "null"),
    ("cluster", "45deg", 0.0, "null"),
    ("cluster", "0deg", 20.0, "evacuated"),
    ("cluster", "0deg", 40.0, "evacuated"),
    ("cluster", "0deg", 90.0, "evacuated"),
    ("cluster", "0deg", 40.0, "rim_isothermal_x2"),
    ("cluster", "0deg", 40.0, "rim_shock_m1p5_mass_matched"),
    ("group", "0deg", 40.0, "rim_shock_m1p5_mass_matched"),
)
STAMP_METHODS = (
    (ladder.LEGACY, "observer", "#d62728"),
    (ladder.SEED_GROW, "observer", "#1f77b4"),
    (ladder.THRESHOLD, "observer_radial_null_calibrated", "#ff7f0e"),
)


def stamp_figure(stamps, path: Path) -> None:
    figure, panels = plt.subplots(2, 4, figsize=(15, 8.4))
    for axis, key in zip(panels.ravel(), STAMP_SCENARIOS, strict=True):
        rendered, results = stamps[key]
        h, z = rendered.horizontal_axis_kpc, rendered.z_axis_kpc
        shown = rendered.surface_brightness[:, np.abs(h) < 190.0]
        positive = shown[shown > 0.0]
        axis.pcolormesh(
            h, z, np.log10(np.clip(rendered.surface_brightness, positive.min(), None)),
            cmap="Greys_r", shading="nearest", rasterized=True,
            vmin=np.log10(np.percentile(positive, 1.0)), vmax=np.log10(positive.max()),
        )
        if np.any(rendered.cavity_mask):
            axis.contour(h, z, rendered.cavity_mask.astype(float), levels=[0.5], colors="white", linewidths=1.2, linestyles="--")
        for method, background, colour in STAMP_METHODS:
            match = next(r for r in results if r.method == method and r.background == background)
            if np.any(match.mask):
                axis.contour(h, z, match.mask.astype(float), levels=[0.5], colors=colour, linewidths=1.0)
        circle = np.linspace(0, 2 * np.pi, 200)
        axis.plot(120 * np.cos(circle), 120 * np.sin(circle), color="yellow", lw=0.7, ls=":")
        axis.set_xlim(-190, 190)
        axis.set_ylim(-240, 240)
        axis.set_aspect("equal")
        environment, view, along, variant = key
        axis.set_title(f"{environment} {view} {variant.replace('_', ' ')} a={along:g}", fontsize=9)
    handles = [plt.Line2D([], [], color="white", ls="--", label="true cavity")]
    handles += [plt.Line2D([], [], color=c, label=f"{m} / {b}") for m, b, c in STAMP_METHODS]
    handles += [plt.Line2D([], [], color="yellow", ls=":", label="120 kpc aperture")]
    figure.legend(handles=handles, loc="lower center", ncol=5, fontsize=8, facecolor="0.85")
    figure.tight_layout(rect=(0, 0.04, 1, 1))
    figure.savefig(path, dpi=120)
    plt.close(figure)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stride", type=int, default=2)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.output, args.stride), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
