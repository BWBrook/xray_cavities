#!/usr/bin/env python3
"""Run the Q-032 method ladder on retained selected-age XRAiSE maps.

Designed to run beside the maps (raw maps stay remote) and to return only
compact products: per-side recovery rows with tracer comparison, packed
per-view masks, and one postage stamp per view showing the corrected map,
the tracer outline, every method's mask, the aperture and the topology
status, including views that production rejects.

Map directories follow the retained layout
``<root>/age_<AA>/xraise_grid_<view>/``. Tracer data are used only after
recovery, as an evaluation reference.

Optional ``--baseline ENVIRONMENT:VIEW:DIRECTORY`` supplies a t=0 render of
the initial atmosphere on the same axes. It adds a t0-baseline rung and a
threshold calibrated on that map. A t0 map is the initial-state reference,
not the evolved no-jet counterfactual, and rows label it so.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCIENCE_DIR = Path(__file__).resolve().parent
if str(SCIENCE_DIR) not in sys.path:
    sys.path.insert(0, str(SCIENCE_DIR))

import three_case_cavity_recovery as recovery
import xray_cavity_method_ladder as ladder

AGES = (10, 20, 30, 40, 50)
VIEWS = ("0deg", "45deg", "90deg")
OBSERVER_THRESHOLDS = (0.05, 0.10, 0.20)
TRACER_THRESHOLD = 1.0e-3
CASE_ENVIRONMENT = {"C-HI": "cluster", "C-LO": "cluster", "G-HI": "group", "G-LO": "group"}
BASELINE_THRESHOLDS = (0.05, 0.10)
CASE_ROOTS = {
    "C-HI": "xray_cavity/c_hi",
    "C-LO": "xray_cavity/c_lo",
    "G-HI": "xray_cavity_g_hi_r2/g_hi",
    "G-LO": "xray_cavity/g_lo",
}


def load_view(directory: Path, case: str, view: str) -> recovery.LoadedMap:
    horizontal = directory / ("x_kpc.tsv" if view == "0deg" else "u_kpc.tsv")
    if not horizontal.is_file():
        horizontal = directory / "x_kpc.tsv"
    spec = recovery.MapSpec(
        case=case, view=view,
        corrected_xray=str(directory / recovery.CORRECTED_XRAY_NAME),
        tracer_max_los=str(directory / recovery.TRACER_NAME),
        horizontal_axis=str(horizontal), z_axis=str(directory / recovery.VERTICAL_AXIS_NAME),
        source_type="retained_selected_age",
    )
    return recovery.load_accepted_map(spec)


def load_baseline(directory: Path, view: str, loaded: recovery.LoadedMap) -> np.ndarray:
    image = np.loadtxt(directory / recovery.CORRECTED_XRAY_NAME)
    horizontal = np.loadtxt(directory / ("x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"))
    vertical = np.loadtxt(directory / recovery.VERTICAL_AXIS_NAME)
    if not (np.allclose(horizontal, loaded.horizontal_axis) and np.allclose(vertical, loaded.z_axis)):
        raise ValueError(f"baseline axes in {directory} do not match the analysed view")
    return image


def ladder_runs(loaded: recovery.LoadedMap, baseline: np.ndarray | None = None) -> list[ladder.Recovery]:
    image, h, z = loaded.corrected_xray, loaded.horizontal_axis, loaded.z_axis
    radial = ladder.observer_radial_background(image, h, z)
    runs = [ladder.legacy_area_fraction(image, h, z), ladder.seed_grow(image, h, z)]
    runs += [
        ladder.deficit_threshold(image, h, z, background=radial, background_label="observer_radial", threshold=t)
        for t in OBSERVER_THRESHOLDS
    ]
    if baseline is not None:
        runs.append(ladder.seed_grow(image, h, z, background=baseline, background_label="t0_baseline"))
        runs += [
            ladder.deficit_threshold(image, h, z, background=baseline, background_label="t0_baseline", threshold=t)
            for t in BASELINE_THRESHOLDS
        ]
        runs.append(ladder.deficit_threshold(
            image, h, z, background=radial, background_label="observer_radial_t0_calibrated",
            threshold=ladder.null_calibrated_threshold(baseline, h, z),
        ))
    return runs


def run_label(result: ladder.Recovery) -> str:
    label = result.method if result.background == ladder.OBSERVER else f"{result.method}_{result.background}"
    if result.method == ladder.THRESHOLD and result.background != "observer_radial_t0_calibrated":
        return f"{label}_{result.threshold:.2f}"
    return label


def analyse_view(
    loaded: recovery.LoadedMap, *, case: str, age: int, output: Path, baseline: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    h, z = loaded.horizontal_axis, loaded.z_axis
    area = recovery._cell_area_grid(h, z)
    _, aperture = ladder._rois(h, z)
    tracer = loaded.tracer_max_los > TRACER_THRESHOLD
    halves = ladder._split(tracer, z)
    results = ladder_runs(loaded, baseline)
    rows: list[dict[str, Any]] = []
    for result in results:
        for row in ladder.score_rows(result, h, z):
            truth = halves[row["side"]]
            mask = result.side_masks[row["side"]]
            tracer_area = float(area[truth].sum())
            tracer_volumes = ladder.side_volumes(truth, h, z)
            rows.append({
                "case": case, "snapshot_index": age, "view": loaded.spec.view,
                "run": run_label(result), **row,
                "tracer_projected_area_kpc2": tracer_area,
                "tracer_area_inside_aperture_fraction": (
                    float(area[truth & aperture].sum()) / tracer_area if tracer_area else float("nan")
                ),
                "tracer_revolution_volume_kpc3": tracer_volumes["revolution"],
                "tracer_completeness": float(area[mask & truth].sum()) / tracer_area if tracer_area else float("nan"),
                "tracer_purity": (
                    float(area[mask & truth].sum()) / row["recovered_area_kpc2"]
                    if row["recovered_area_kpc2"] else float("nan")
                ),
            })
    stem = f"{case}_age{age:02d}_{loaded.spec.view}"
    np.savez_compressed(
        output / "masks" / f"{stem}.npz",
        horizontal_axis_kpc=h, z_axis_kpc=z,
        tracer=np.packbits(tracer),
        **{f"{run_label(r)}__{side}": np.packbits(r.side_masks[side]) for r in results for side in ladder.SIDES},
        shape=np.array(tracer.shape),
    )
    stamp(loaded, results, tracer, output / "stamps" / f"{stem}.png", title=f"{case} {age} Myr {loaded.spec.view}")
    return rows


STAMP_COLOURS = ("#d62728", "#1f77b4", "#ff7f0e", "#9467bd", "#8c564b", "#17becf", "#e377c2", "#bcbd22", "#2ca02c")


def stamp(loaded, results, tracer, path: Path, *, title: str) -> None:
    h, z = loaded.horizontal_axis, loaded.z_axis
    image = loaded.corrected_xray
    positive = image[(image > 0.0) & (np.abs(h)[None, :] < 190.0)]
    figure, axis = plt.subplots(figsize=(5.2, 6.2))
    axis.pcolormesh(
        h, z, np.log10(np.clip(image, positive.min(), None)), cmap="Greys_r", shading="nearest",
        rasterized=True, vmin=np.log10(np.percentile(positive, 1.0)), vmax=np.log10(positive.max()),
    )
    if np.any(tracer):
        axis.contour(h, z, tracer.astype(float), levels=[0.5], colors="white", linewidths=1.0, linestyles="--")
    for result, colour in zip(results, STAMP_COLOURS[: len(results)], strict=True):
        if np.any(result.mask):
            axis.contour(h, z, result.mask.astype(float), levels=[0.5], colors=colour, linewidths=0.9)
    circle = np.linspace(0, 2 * np.pi, 200)
    axis.plot(120 * np.cos(circle), 120 * np.sin(circle), color="yellow", lw=0.7, ls=":")
    axis.set_xlim(-190, 190)
    axis.set_ylim(-240, 240)
    axis.set_aspect("equal")
    axis.set_title(f"{title}\nproduction topology: {results[0].topology_class}", fontsize=8)
    handles = [plt.Line2D([], [], color="white", ls="--", label=f"tracer >= {TRACER_THRESHOLD:g} (evaluation only)")]
    handles += [plt.Line2D([], [], color=c, label=run_label(r)) for r, c in zip(results, STAMP_COLOURS[: len(results)], strict=True)]
    axis.legend(handles=handles, loc="lower left", fontsize=6, facecolor="0.85")
    figure.tight_layout()
    figure.savefig(path, dpi=110)
    plt.close(figure)


def run(
    view_dirs: Sequence[tuple[str, int, str, Path]],
    output: Path,
    baselines: dict[tuple[str, str], Path] | None = None,
) -> dict[str, Any]:
    baselines = baselines or {}
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    (output / "masks").mkdir(parents=True)
    (output / "stamps").mkdir()
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for case, age, view, directory in view_dirs:
        loaded = load_view(directory, case, view)
        baseline_dir = baselines.get((CASE_ENVIRONMENT[case], view))
        baseline = load_baseline(baseline_dir, view, loaded) if baseline_dir else None
        rows.extend(analyse_view(loaded, case=case, age=age, output=output, baseline=baseline))
        source = directory / recovery.CORRECTED_XRAY_NAME
        sources.append({
            "case": case, "snapshot_index": age, "view": view, "path": str(source),
            "size_bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        })
        print(f"{case} {age} {view}", flush=True)
    for name, table in (("method_ladder_rows.csv", rows), ("source_maps.csv", sources)):
        with (output / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(table[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
    metadata = {
        "status": "complete_q032_selected_age_method_ladder",
        "views_analysed": len(view_dirs),
        "runs": sorted({row["run"] for row in rows}),
        "observer_thresholds": list(OBSERVER_THRESHOLDS),
        "baselines": {f"{env}:{view}": str(path) for (env, view), path in sorted(baselines.items())},
        "baseline_role": "t=0 initial-atmosphere reference, not an evolved no-jet counterfactual",
        "tracer_role": f"evaluation only, tr1 max along line of sight > {TRACER_THRESHOLD:g}",
        "mask_encoding": "numpy packbits of row-major boolean arrays; unpack with np.unpackbits(...)[:prod(shape)].reshape(shape)",
    }
    (output / "method_ladder_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output)}"
        for path in sorted(output.rglob("*"))
        if path.is_file()
    ]
    (output / "manifest.sha256").write_text("\n".join(lines) + "\n")
    return metadata


def retained_view_dirs(base: Path) -> list[tuple[str, int, str, Path]]:
    return [
        (case, age, view, base / root / f"age_{age:02d}" / f"xraise_grid_{view}")
        for case, root in CASE_ROOTS.items()
        for age in AGES
        for view in VIEWS
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=Path, help="retained selected-age analysis root")
    parser.add_argument(
        "--view-dir", action="append", default=[],
        help="CASE:AGE:VIEW:DIRECTORY, repeatable; overrides --base",
    )
    parser.add_argument(
        "--baseline", action="append", default=[],
        help="ENVIRONMENT:VIEW:DIRECTORY t=0 map for cluster or group, repeatable",
    )
    args = parser.parse_args(argv)
    baselines = {}
    for item in args.baseline:
        environment, view, directory = item.split(":", 2)
        baselines[(environment, view)] = Path(directory)
    if args.view_dir:
        view_dirs = []
        for item in args.view_dir:
            case, age, view, directory = item.split(":", 3)
            view_dirs.append((case, int(age), view, Path(directory)))
    elif args.base:
        view_dirs = retained_view_dirs(args.base)
    else:
        parser.error("give --base or --view-dir")
    print(json.dumps(run(view_dirs, args.output, baselines), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
