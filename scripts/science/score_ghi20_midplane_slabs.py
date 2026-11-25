"""Score the three matched G-HI/20 line-of-sight integrations on the native x–z grid."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import numpy as np

import compare_compressive_front as front
from fit_source_excluded_background import prepare_radial_fit
from render_compressive_front import outline
import xray_cavity_method_ladder as ladder


DEPTHS = ("full", "slab30", "slab10")
LABELS = ("Full depth", "−30 ≤ y ≤ 30 kpc", "−10 ≤ y ≤ 10 kpc")
HALVES = ("negative_z", "positive_z", "both")
FIELDS = ("current", "initial", "tracer_path", "current_lobe", "initial_on_current_lobe")
FULL_REFERENCE = dict(current="brightness_current_retained_linear_whole",
                      initial="brightness_initial_retained_linear_whole", tracer_path="path_C_kpc",
                      current_lobe="brightness_current_retained_linear_C",
                      initial_on_current_lobe="brightness_initial_retained_linear_C")
REFERENCE_MASK = "mask_retained_linear_v100_" + front.ORANGE + "_exact_projection_refit"
THRESHOLD = 0.05


def ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def fit_image(image, grid, depth, epoch):
    model = prepare_radial_fit(image, grid.u, grid.z, grid.ue, grid.ze)
    fit = model.fit(np.zeros(image.shape, dtype=bool))
    rows = []
    for row in fit.rows:
        rows.append({"depth": depth, "epoch": epoch, "r_inner_kpc": row["r_inner_kpc"],
                     "r_outer_kpc": row["r_outer_kpc"], "r_center_kpc": row["r_center_kpc"],
                     "valid_pixels": row["valid_pixels"], "valid_sectors_of_12": row["valid_sectors"],
                     "positive_area_kpc2": row["valid_area_kpc2"], "annular_area_kpc2": row["roi_area_kpc2"],
                     "support": row["support_class"], "median_mjy_sr": row["full_median"],
                     "smoothed_mjy_sr": row["baseline_profile"]})
    return model.baseline, rows


def sides(grid):
    return (grid.z < 0, grid.z > 0, np.ones(grid.z.size, dtype=bool))


def area_scores(grid, mask, full_mask, full_path, slab_path):
    area = grid.area
    _, aperture = ladder._rois(grid.u, grid.z)
    full, slab = full_path > 0, slab_path > 0
    rows = []
    for name, side in zip(HALVES, sides(grid), strict=True):
        half = side[:, None]
        selected = mask & half
        selected_area = area[selected].sum()
        full_area, slab_area = area[half & full].sum(), area[half & slab].sum()
        full_vol, slab_vol = ((area[side] * path[side]).sum() for path in (full_path, slab_path))
        contact = ladder.touches_aperture(selected, grid.u, grid.z)
        for target, truth, volume in (("full_lobe", full, full_vol), ("slab_lobe", slab, slab_vol)):
            lobe = truth & half
            target_area = area[lobe].sum()
            overlap = area[lobe & selected].sum()
            rows.append({"hemisphere": name, "target": target, "selected_kpc2": float(selected_area),
                         "lobe_kpc2": float(target_area), "overlap_kpc2": float(overlap),
                         "missed_kpc2": float(area[lobe & ~mask].sum()),
                         "false_kpc2": float(area[selected & ~truth].sum()),
                         "completeness": ratio(overlap, target_area), "purity": ratio(overlap, selected_area),
                         "native_lobe_kpc3": float(volume),
                         "slab_area_retained_fraction": ratio(slab_area, full_area),
                         "slab_volume_retained_fraction": ratio(slab_vol, full_vol),
                         "lobe_outside_aperture_kpc2": float(area[lobe & ~aperture].sum()),
                         "selection_touches_aperture": contact,
                         "lobe_touches_sky_edge": bool(lobe[[0, -1], :].any() or lobe[:, [0, -1]].any()),
                         "overlap_gained_vs_full_kpc2": float(area[lobe & mask & ~full_mask].sum()),
                         "overlap_lost_vs_full_kpc2": float(area[lobe & ~mask & full_mask].sum())})
    return rows


def filling_scores(grid, fields, background, fit_deficit, initial_deficit, full_path, full_mask, selected_mask):
    """Compare two fixed lobe regions and the exterior selected at this depth."""
    rows = []
    area = grid.area
    truth = full_path > 0
    for region, use in (("full_lobe", truth), ("missed_by_full_depth_detector", truth & ~full_mask),
                        ("selected_outside_full_lobe", selected_mask & ~truth)):
        for name, side in zip(HALVES, sides(grid), strict=True):
            cells = use & side[:, None]
            weights = area[cells]

            def integral(image):
                return float(np.sum(weights * image[cells]))

            current, initial, lobe_now, lobe_zero = (integral(fields[key]) for key in
                ("current", "initial", "current_lobe", "initial_on_current_lobe"))
            decrement = lobe_zero - lobe_now
            ambient_change = (current - lobe_now) - (initial - lobe_zero)
            bg_cells = cells & np.isfinite(background) & (background > 0)
            bg_area = area[bg_cells]
            bg_flux = float(np.sum(bg_area * background[bg_cells]))
            current_over_bg = float(np.sum(bg_area * fields["current"][bg_cells]))
            zero_over_bg = float(np.sum(bg_area * fields["initial"][bg_cells]))
            phys_on = initial_deficit[cells] > THRESHOLD
            fit_on = fit_deficit[cells] > THRESHOLD
            rows.append({"region": region, "hemisphere": name, "area_kpc2": float(weights.sum()),
                         "current_flux": current, "initial_flux": initial, "current_lobe_flux": lobe_now,
                         "initial_flux_on_current_lobe": lobe_zero,
                         "lobe_brightness_decrement": decrement, "ambient_brightness_change": ambient_change,
                         "ambient_offset_fraction": ratio(ambient_change, decrement) if decrement > 0 else None,
                         "physical_deficit_fraction": ratio(initial - current, initial),
                         "fit_valid_area_kpc2": float(bg_area.sum()), "fitted_background_flux": bg_flux,
                         "fitted_deficit_fraction": ratio(bg_flux - current_over_bg, bg_flux),
                         "fitted_background_over_initial": ratio(bg_flux, zero_over_bg),
                         "initial_valid_area_kpc2": float(weights[np.isfinite(initial_deficit[cells])].sum()),
                         "initial_dimmed_5pct_kpc2": float(weights[phys_on].sum()),
                         "fitted_dimmed_5pct_kpc2": float(weights[fit_on].sum()),
                         "initial_only_dimmed_kpc2": float(weights[phys_on & ~fit_on].sum()),
                         "fitted_only_dimmed_kpc2": float(weights[fit_on & ~phys_on].sum())})
    return rows


def read_projection(directory, reference):
    receipt = json.loads((directory / "completion.json").read_text())
    data_file = directory / "projections.npz"
    record = receipt["files"][data_file.name]
    if data_file.stat().st_size != record["size_bytes"] or front.HASH(data_file) != record["sha256"]:
        raise ValueError("Returned slab projection differs from its receipt")
    if (receipt["status"] != "complete" or receipt["case"] != "G-HI" or receipt["energy_kev"] != 1.0
            or receipt["snapshot_index"] != 20 or receipt["view_deg"] != 0
            or not np.isclose(receipt["actual_time_myr"], front.AGE, rtol=0, atol=1e-10)
            or receipt["previous_producer_sha256"] != front.PRODUCER_SHA
            or receipt["previous_map_sha256"] != front.SOURCE_HASHES[0]
            or front.HASH(reference) != front.SOURCE_HASHES[0]):
        raise ValueError("Wrong G-HI/20 snapshot, epoch or original 0-degree projection")
    with np.load(data_file, allow_pickle=False) as data, np.load(reference, allow_pickle=False) as original:
        fields = {depth: {name: data[f"{name}_{depth}"] for name in FIELDS} for depth in DEPTHS}
        dims = fields["full"]["current"].shape
        grid = front.Grid(*front.validate_axes(data, dims))
        if any(not np.array_equal(data[k], original[k]) for k in front.AXES):
            raise ValueError("Slabs and historical full-depth image differ in their physical sky axes")
        for name, old_name in FULL_REFERENCE.items():
            before = original[old_name]
            if not np.allclose(fields["full"][name], before, rtol=1e-10, atol=0):
                raise ValueError(f"Full-depth {name} differs from the published reference")
        archive_mask = original[REFERENCE_MASK]
    if not np.any(grid.ze == 0) or np.any(grid.z == 0):
        raise ValueError("The split between the two lobes must fall on a physical cell edge")
    for depth, maps in fields.items():
        if any(m.shape != dims or not np.isfinite(m).all() for m in maps.values()):
            raise ValueError(f"Invalid or nonfinite maps in {depth}")
    full, outer, inner = (fields[d]["tracer_path"] for d in DEPTHS)
    if any(np.any(path < 0) for path in (full, outer, inner)) or np.any(inner > outer + 1e-9) or np.any(outer > full + 1e-9):
        raise ValueError("Tracer depths fail their physical nesting")
    if np.any((inner > 0) & (outer <= 0)) or np.any((outer > 0) & (full <= 0)):
        raise ValueError("Slab tracer footprints are not nested")
    return receipt, grid, fields, archive_mask


def plot_maps(output, grid, fields, measured, age, full_depth):
    full_tracer = fields["full"]["tracer_path"] > 0
    extent = ladder.recovery.CANDIDATE_RADIUS_KPC + 5
    if full_tracer.any():
        iz, ix = np.nonzero(full_tracer)
        extent = max(extent, np.abs(grid.u[ix]).max() + 5, np.abs(grid.z[iz]).max() + 5)
    limits = (max(-extent, grid.ue[0]), min(extent, grid.ue[-1]),
              max(-extent, grid.ze[0]), min(extent, grid.ze[-1]))
    sample = []
    for lo, hi, edges in ((limits[0], limits[1], grid.ue), (limits[2], limits[3], grid.ze)):
        centres = lo + (np.arange(480) + 0.5) * (hi - lo) / 480
        sample.append(np.searchsorted(edges, centres, side="right") - 1)
    take = np.ix_(sample[1], sample[0])
    brightness = np.concatenate([fields[d][epoch][take].ravel() for d in DEPTHS for epoch in ("current", "initial")])
    bmin, bmax = np.percentile(brightness[brightness > 0], (0.5, 99.5))
    bmax = max(bmax, np.nextafter(bmin, np.inf))
    contrast = np.concatenate([measured[d][k][take].ravel() for d in DEPTHS for k in ("fit_deficit", "initial_deficit")])
    bound = float(max(10., 100 * np.nanpercentile(np.abs(contrast), 97)))
    bright_norm = LogNorm(bmin, bmax)
    deficit_norm = Normalize(-bound, bound)
    fig = plt.figure(figsize=(10.4, 12.4), layout="constrained")
    gs = fig.add_gridspec(5, 4, width_ratios=[1, 1, 1, .05], height_ratios=[1, 1, 1, 1, .12])
    axes = [[fig.add_subplot(gs[i, j]) for j in range(3)] for i in range(4)]
    initial_label = "Time-zero brightness"
    labels = ("Current brightness", initial_label, "Deficit against radial fit", "Deficit against time zero")
    colors = {"selected": "#e67d00", "full": "#098073", "slab": "#7b30b2"}
    try:
        fig.suptitle(f"G-HI · 1 keV · {age:.4f} Myr · looking along y", fontsize=13)
        full_title = f"Full ({full_depth['y_min_kpc']:g} to {full_depth['y_max_kpc']:g} kpc)"
        for j, (depth, depth_label) in enumerate(zip(DEPTHS, (full_title, *LABELS[1:]), strict=True)):
            maps, fitted = fields[depth], measured[depth]
            axes[0][j].set_title(depth_label, fontsize=11)
            for i, values in enumerate((maps["current"], maps["initial"], fitted["fit_deficit"], fitted["initial_deficit"])):
                ax = axes[i][j]
                data = values[take] if i < 2 else 100 * values[take]
                im = ax.imshow(data, origin="lower", extent=limits, aspect="equal", interpolation="nearest",
                               cmap="Greys" if i < 2 else "RdBu_r", norm=bright_norm if i < 2 else deficit_norm)
                if i == 0:
                    outline(ax, grid, full_tracer, colors["full"], .85)
                if i == 2:
                    outline(ax, grid, full_tracer, colors["full"], .7)
                    outline(ax, grid, fitted["mask"], colors["selected"], .95)
                    ax.add_patch(Circle((0, 0), ladder.recovery.CANDIDATE_RADIUS_KPC,
                                        facecolor="none", edgecolor="#363636", lw=.65, ls="--"))
                if i == 3:
                    outline(ax, grid, maps["tracer_path"] > 0, colors["slab"], .85)
                ax.set(xlim=limits[:2], ylim=limits[2:])
                ax.tick_params(labelsize=8, labelleft=j == 0, labelbottom=i == 3)
                if j == 0:
                    ax.set_ylabel(labels[i] + "\nz (kpc)", fontsize=9)
                if i == 3:
                    ax.set_xlabel("x (kpc)", fontsize=9)
                if j == 0 and i in (0, 2):
                    cax = fig.add_subplot(gs[i:i+2, 3])
                    fig.colorbar(im, cax=cax, extend="both",
                                 label="Brightness (mJy sr⁻¹)" if i == 0 else "Deficit (%) · positive is dimmer")
        legend = fig.add_subplot(gs[4, :3])
        legend.axis("off")
        handles = [Line2D([], [], color=colors["full"], label="Full lobe"),
                   Line2D([], [], color=colors["selected"], label="Detected cavity"),
                   Line2D([], [], color=colors["slab"], label="Lobe within emission depth"),
                   Line2D([], [], color="#363636", ls="--", label="120 kpc aperture")]
        legend.legend(handles=handles, loc="center", frameon=False, ncol=4, fontsize=8)
        fig.savefig(output, dpi=130)
    finally:
        plt.close(fig)
    return {"display_extent_xz_kpc": [float(v) for v in limits],
            "shared_log_brightness_limits_mjy_sr": [float(bmin), float(bmax)],
            "shared_deficit_limits_pct": [-bound, bound], "display_samples_per_axis": 480}


def plot_profiles(output, rows):
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6), layout="constrained")
    colors = ("#25272a", "#10756e", "#925286")
    try:
        for d, label, color in zip(DEPTHS, LABELS, colors, strict=True):
            current, initial = ([r for r in rows if r["depth"] == d and r["epoch"] == state]
                                for state in ("current", "initial"))
            r = np.array([x["r_center_kpc"] for x in current])
            curves = []
            for records, style in ((current, "-"), (initial, "--")):
                profile = np.array([x["smoothed_mjy_sr"] for x in records])
                curves.append(profile)
                axes[0].plot(r, profile, style, color=color, lw=1.5)
                missing = np.array([x["support"] != "direct" for x in records])
                axes[0].scatter(r[missing], profile[missing], facecolors="none", edgecolors=color, s=30)
            axes[1].plot(r, curves[0] / curves[1], color=color, label=label)
        axes[0].set(yscale="log", ylabel="Radial background (mJy sr⁻¹)", title="Fitted profiles")
        axes[0].legend(handles=[Line2D([], [], color="#555", label="Current"),
                                Line2D([], [], color="#555", ls="--", label="Time zero")],
                       frameon=False, fontsize=8)
        axes[1].axhline(1, ls="--", color="#999", lw=.8)
        axes[1].set(ylabel="Current / time-zero fit", title="Change within each emission depth")
        axes[1].legend(frameon=False, fontsize=8)
        for ax in axes:
            ax.set(xlabel="Annulus radius (kpc)", xlim=(0, ladder.recovery.BACKGROUND_RADIUS_KPC))
            ax.spines[["top", "right"]].set_visible(False)
        fig.savefig(output, dpi=135)
    finally:
        plt.close(fig)


def run(projection_dir, reference, output):
    if output.exists():
        raise FileExistsError(f"Output directory already exists: {output}")
    receipt, grid, fields, archived_mask = read_projection(projection_dir, reference)
    areas, filling, profiles = [], [], []
    measured, mask_hashes, support = {}, {}, {}
    for depth in DEPTHS:
        maps = fields[depth]
        background, profile_now = fit_image(maps["current"], grid, depth, "current")
        _, profile_zero = fit_image(maps["initial"], grid, depth, "initial")
        observer = ladder.deficit_threshold(maps["current"], grid.u, grid.z, background=background,
                                           background_label="observer_radial", threshold=THRESHOLD)
        mask = observer.mask
        if depth == "full" and not np.array_equal(mask, archived_mask):
            raise ValueError("Full-depth radial candidate does not reproduce the exact-edge archived mask")
        initial_deficit = ladder.recovery.compute_fractional_deficit(maps["current"], maps["initial"])
        measured[depth] = {"mask": mask, "fit_deficit": observer.deficit, "initial_deficit": initial_deficit}
        mask_hashes[depth] = hashlib.sha256(mask.tobytes(order="C")).hexdigest()
        full_mask = measured["full"]["mask"]
        full_path = fields["full"]["tracer_path"]
        depth_areas = area_scores(grid, mask, full_mask, full_path, maps["tracer_path"])
        for row in depth_areas:
            target_depth = "full" if row["target"] == "full_lobe" else depth
            native_volume = receipt["native_tracer_volume_kpc3"][target_depth][row["hemisphere"]]
            if not np.isclose(row["native_lobe_kpc3"], native_volume, rtol=4e-11, atol=0):
                raise ValueError(f"{depth}/{row['target']}/{row['hemisphere']} volume differs from the native cell sum")
        depth_filling = filling_scores(grid, maps, background, observer.deficit, initial_deficit, full_path, full_mask, mask)
        areas.extend({"depth": depth, **r} for r in depth_areas)
        filling.extend({"depth": depth, **r} for r in depth_filling)
        profiles.extend(profile_now + profile_zero)
        support[depth] = {r[0]["epoch"]: dict(Counter(x["support"] for x in r)) for r in (profile_now, profile_zero)}

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp) / "scores"
        work.mkdir()
        for name, rows in (("areas.csv", areas), ("filling.csv", filling), ("radial_profiles.csv", profiles)):
            front.write_rows(work / name, rows)
        display = plot_maps(work / "maps.png", grid, fields, measured, receipt["actual_time_myr"], receipt["depths"]["full"])
        plot_profiles(work / "profiles.png", profiles)
        result = {
            "case": receipt["case"], "snapshot_index": receipt["snapshot_index"], "view_deg": receipt["view_deg"],
            "actual_time_myr": receipt["actual_time_myr"], "frequency_hz": receipt["frequency_hz"],
            "redshift": receipt["redshift"], "projection_receipt_sha256": front.HASH(projection_dir / "completion.json"),
            "projection_file_sha256": receipt["files"]["projections.npz"]["sha256"],
            "reference_sha256": front.SOURCE_HASHES[0], "full_depth_candidate_matches_archive": True,
            "candidate_mask_sha256": mask_hashes, "native_tracer_boundary_face_cells": receipt["tracer_boundary_face_cells"],
            "support_by_5kpc_annulus": support, "flux_integral_units": "mJy sr^-1 kpc^2",
            "detector": {"fit_radius_kpc": ladder.recovery.BACKGROUND_RADIUS_KPC,
                         "candidate_radius_kpc": ladder.recovery.CANDIDATE_RADIUS_KPC,
                         "radial_bin_kpc": ladder.recovery.RADIAL_BIN_KPC,
                         "smoothing_sigma_kpc": ladder.recovery.RADIAL_SMOOTHING_KPC,
                         "strict_deficit_cut": THRESHOLD, "min_component_kpc2": ladder.recovery.MIN_COMPONENT_AREA_KPC2,
                         "connectivity": ladder.recovery.CONNECTIVITY},
            "figure": display, "scorer_sha256": front.HASH(Path(__file__)),
            "products": {p.name: front.HASH(p) for p in sorted(work.iterdir())},
        }
        (work / "score_receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        work.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.projection_dir, args.reference, args.out)
