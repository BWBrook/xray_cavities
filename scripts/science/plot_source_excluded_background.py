"""Render one private source-exclusion diagnostic on the native physical sky coordinates."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LogNorm, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import numpy as np

from three_case_cavity_recovery import BACKGROUND_RADIUS_KPC, CANDIDATE_RADIUS_KPC, compute_fractional_deficit


CASES = ("original", "tracer", "speed_100")
LABELS = {"original": "Whole image", "tracer": "Tracer excluded", "speed_100": "Speed excluded"}
COLORS = {"original": "#24232a", "tracer": "#087a68", "speed_100": "#89477d"}
NATIVE = "#142d2a"
OUTLINE = "#e39f13"
APERTURE = "#5d5865"


def _sample_axis(edges, count):
    """Take the cell containing each regular physical display centre, on either axis orientation."""
    edges = np.asarray(edges)
    lo, hi = min(edges[0], edges[-1]), max(edges[0], edges[-1])
    centres = lo + (np.arange(count) + .5) * (hi - lo) / count
    if edges[0] < edges[-1]:
        index = np.searchsorted(edges, centres, side="right") - 1
    else:
        index = len(edges) - 1 - np.searchsorted(edges[::-1], centres, side="right")
    return centres, index, (lo, hi)


def _outline(ax, u, z, mask, color, linestyle="solid"):
    if mask is None:
        return
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    if not rows.size or (len(rows) == len(z) and len(cols) == len(u) and mask.all()):
        return
    zs = slice(max(0, rows[0] - 1), min(len(z), rows[-1] + 2))
    us = slice(max(0, cols[0] - 1), min(len(u), cols[-1] + 2))
    ax.contour(u[us], z[zs], mask[zs, us], levels=[.5], colors=[color], linestyles=[linestyle], linewidths=.9)


def _note(ax, message):
    ax.text(.5, .5, message, transform=ax.transAxes, ha="center", va="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=.3", edgecolor="none", facecolor="white", alpha=.9))


def _profiles(profile_ax, area_ax, fits):
    gaps = []
    for case in CASES:
        fit = fits.get(case)
        label, color = LABELS[case], COLORS[case]
        if fit is None:
            gaps.append(f"{label}: unavailable")
            continue
        rows = fit.rows
        r = np.array([row["r_center_kpc"] for row in rows])
        area = np.array([row["retained_area_kpc2"] for row in rows])
        area_ax.plot(r, area, color=color, label=label, linewidth=1.65)
        if fit.backgrounds["flat"] is None:
            gaps.append(f"{label}: insufficient support")
            continue
        direct = np.array([row["support_class"] == "direct" for row in rows])
        profile = np.array([row["flat_profile"] for row in rows])
        profile_ax.plot(r, profile, color=color, label=label, linewidth=1.6)
        profile_ax.scatter(r[direct], profile[direct], s=6, color=color)
        inner = [row for row in rows if row["support_class"] == "inner_extrapolated"]
        if case != "original" and not inner:
            gaps.append(f"{label}: none")
        if inner:
            stop = inner[-1]["r_outer_kpc"]
            gaps.append(f"{label}: 0–{stop:g} kpc" +
                        (" (slope undefined)" if fit.backgrounds["log_slope"] is None else ""))
            if fit.backgrounds["log_slope"] is not None:
                alt = np.array([row["log_slope_profile"] for row in rows])
                profile_ax.plot(r, alt, color=color, linestyle="--", linewidth=1.25)

    for ax in (profile_ax, area_ax):
        ax.set_xlim(0, BACKGROUND_RADIUS_KPC)
        ax.set_xlabel("Projected radius (kpc)")
        ax.grid(axis="y", alpha=.2, linewidth=.6)
        ax.spines[["right", "top"]].set_visible(False)
    profile_ax.set_title("Radial background after smoothing", loc="left", fontsize=11)
    profile_ax.set_ylabel("B(R) (mJy sr⁻¹)")
    profile_ax.set_yscale("log")
    if profile_ax.lines:
        profile_ax.legend(fontsize=8, frameon=False, loc="best")
    area_ax.set_ylim(bottom=0)
    area_ax.set_title("Sky retained for each 5-kpc median", loc="left", fontsize=11)
    area_ax.set_ylabel("Positive-brightness area (kpc²)")
    return "Inner gap in fitting support   " + "  ·  ".join(gaps)


def plot_view(view, fits, exclusions, selected, output):
    """Save the full-field view. Maps sample the containing native cell on a regular display grid.

    The longest sky axis has 512 colour samples. Contours use the full-resolution native physical
    coordinates so sub-display-pixel structures remain visible. Brightness colours span the
    0.5th to 99.5th display percentiles. The input stays on the native grid for all fit and
    score calculations. Profile markers denote direct support before smoothing. Dashed
    profiles apply the log-slope central continuation. All deficit panels use the primary fit.
    Missing masks, missing fits, empty outlines and the time-zero evaluation target are distinct.
    """
    ue, ze = (view.axes[key] for key in ("horizontal_edges_kpc", "z_edges_kpc"))
    width, height = abs(ue[-1] - ue[0]), abs(ze[-1] - ze[0])
    step = max(width, height) / 512
    _, ui, urange = _sample_axis(ue, max(2, round(width / step)))
    _, zi, zrange = _sample_axis(ze, max(2, round(height / step)))
    u, z = (view.axes[key] for key in ("horizontal_axis_kpc", "z_axis_kpc"))
    take = np.ix_(zi, ui)
    extent = (*urange, *zrange)
    image = view.image[take]
    if view.kind == "initial_null":
        native = exclusions.get("tracer")
        target_note = "  ·  Initial scoring target empty by definition"
    else:
        native = view.target_path_kpc > 0
        target_note = ""
    fig = plt.figure(figsize=(12.2, 12.0), layout="constrained")
    try:
        outer = fig.add_gridspec(4, 1, height_ratios=[6.8, .46, 2.25, .48])
        maps = outer[0].subgridspec(2, 4, width_ratios=[1, 1, 1, .043], wspace=.07, hspace=.08)
        map_axes = [[fig.add_subplot(maps[i, j]) for j in range(3)] for i in range(2)]
        for row in map_axes:
            for j, ax in enumerate(row):
                ax.set_aspect("equal")
                ax.set_xlim(urange)
                ax.set_ylim(zrange)
                ax.set_facecolor("#e6e5e2")
                ax.tick_params(labelsize=8)
                if j == 0:
                    ax.set_ylabel("Jet axis z (kpc)")
                else:
                    ax.tick_params(labelleft=False)
                if row is map_axes[1]:
                    ax.set_xlabel("Sky coordinate u (kpc)")
                else:
                    ax.tick_params(labelbottom=False)

        bright = np.ma.masked_less_equal(image, 0)
        positive = bright.compressed()
        if len(positive):
            lo, hi = np.percentile(positive, [.5, 99.5])
            if hi <= lo:
                lo, hi = lo / 1.01, hi * 1.01
            brightness = map_axes[0][0].imshow(bright, origin="lower", extent=extent, interpolation="nearest",
                                              cmap="magma", norm=LogNorm(lo, hi))
            fig.colorbar(brightness, cax=fig.add_subplot(maps[0, 3]), extend="both", label="1-keV brightness (mJy sr⁻¹)")
        else:
            _note(map_axes[0][0], "No positive display pixels")
        map_axes[0][0].set_title("Whole 1-keV image", fontsize=11)

        for j, (key, title) in enumerate((("tracer", "Tracer >0.001 fit exclusion"), ("speed_100", "Speed ≥100 km/s fit exclusion")), start=1):
            ax = map_axes[0][j]
            ax.set_title(title, fontsize=11)
            mask = exclusions.get(key)
            if mask is None:
                _note(ax, "Native mask unavailable")
            else:
                ax.imshow(mask[take], origin="lower", extent=extent, interpolation="nearest", vmin=0, vmax=1,
                          cmap=ListedColormap(["#faf9f6", COLORS[key]]))
                _outline(ax, u, z, mask, COLORS[key])
                if not mask.any():
                    _note(ax, "Empty exclusion")
            ax.add_patch(Circle((0, 0), BACKGROUND_RADIUS_KPC, fill=False, linestyle=":", linewidth=.9, color=APERTURE))

        deficit_cmap = plt.get_cmap("RdBu_r").with_extremes(bad="#e6e5e2")
        dnorm = Normalize(-20, 20)
        for j, key in enumerate(CASES):
            ax, fit = map_axes[1][j], fits.get(key)
            ax.set_title(f"Deficit · {LABELS[key].lower()}", fontsize=11)
            if fit is None or fit.backgrounds["flat"] is None:
                _note(ax, "Fit unavailable" if fit is None else "Insufficient radial support")
            else:
                deficit = 100 * compute_fractional_deficit(image, fit.backgrounds["flat"][take])
                ax.imshow(deficit, origin="lower", extent=extent, interpolation="nearest", cmap=deficit_cmap, norm=dnorm)
                outline = selected.get(key)
                if outline is None:
                    _note(ax, "Outline unavailable")
                elif not np.any(outline):
                    ax.text(.025, .025, "No selected pixels", transform=ax.transAxes, fontsize=8)
                else:
                    _outline(ax, u, z, outline, OUTLINE)
            _outline(ax, u, z, native, NATIVE, "dashed")
            ax.add_patch(Circle((0, 0), CANDIDATE_RADIUS_KPC, color=APERTURE, fill=False, linestyle=":", linewidth=1.0))
        fig.colorbar(matplotlib.cm.ScalarMappable(norm=dnorm, cmap=deficit_cmap), cax=fig.add_subplot(maps[1, 3]),
                     extend="both", label="Deficit, 100 × (B − I) / B (%)")

        key_ax = fig.add_subplot(outer[1])
        key_ax.axis("off")
        tracer_label = "Native tracer outline" if native is not None else "Native tracer unavailable"
        keys = [(NATIVE, "--", tracer_label), (OUTLINE, "-", "Selected deficit >5%"),
                (APERTURE, ":", "120-kpc search / 180-kpc fit circles")]
        key_ax.legend(handles=[Line2D([], [], color=c, linestyle=s, linewidth=1.7, label=l) for c, s, l in keys],
                      loc="center", ncol=3, frameon=False, fontsize=9)
        profiles = outer[2].subgridspec(1, 2, wspace=.12)
        gap_note = _profiles(fig.add_subplot(profiles[0]), fig.add_subplot(profiles[1]), fits)
        foot = fig.add_subplot(outer[3])
        foot.axis("off")
        foot.text(0, .7, gap_note, fontsize=8.5, transform=foot.transAxes)
        foot.text(0, .15, "Solid and dashed lines give the flat and log-slope continuations. Dots mark direct support. "
                  "Map colours sample native cells on a regular grid. Outlines follow native coordinates.",
                  fontsize=8.5, transform=foot.transAxes)
        fig.suptitle(f"{view.case}   ·   {view.actual_age_myr:.3f} Myr   ·   {view.view_deg:g}° side-on azimuth{target_note}", fontsize=14)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=120)
    finally:
        plt.close(fig)
