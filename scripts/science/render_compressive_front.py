"""Matched G-HI/20 compressive-front figures on the original sky coordinates."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from compare_compressive_front import ANGLES, BLUE, ORANGE, segments
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

COLORS = {"front": "#a90065", "lobe": "#188a46", "orange": "#e68000", "blue": "#0967c3"}


def shared_norms(inputs):
    flux = []
    deficit = []
    for angle in ANGLES:
        with np.load(
            Path(inputs) / f"G-HI_0020_{angle}deg.npz", allow_pickle=False
        ) as d:
            use = (
                d["horizontal_axis_kpc"][None, :] ** 2 + d["z_axis_kpc"][:, None] ** 2
                <= 125**2
            )
            raw = d["retained_image"]
            bg = d[f"original_background_{ORANGE}"]
            flux.append(raw[use])
            deficit.append(fraction(raw, bg)[use])
    lo, hi = np.nanpercentile(np.concatenate(flux), (0.5, 99.5))
    lim = np.nanpercentile(np.abs(np.concatenate(deficit)), 96)
    return LogNorm(lo, hi), TwoSlopeNorm(0, -lim, lim)


def fraction(brightness, background):
    return np.divide(
        background - brightness,
        background,
        out=np.full_like(brightness, np.nan),
        where=background > 0,
    )


def outline(ax, g, mask, color, width=1, style="solid"):
    if not np.any(mask):
        return
    walls = segments(mask, g)
    vertices = np.stack((walls.lo, walls.hi), axis=1)
    ax.add_collection(
        LineCollection(
            vertices, colors=color, linewidths=width, linestyles=style, alpha=0.92
        )
    )


def sky(ax, g, values, norm, cmap):
    iu = np.flatnonzero(np.abs(g.u) <= 128)
    iz = np.flatnonzero(np.abs(g.z) <= 128)
    us = slice(iu[0], iu[-1] + 1)
    zs = slice(iz[0], iz[-1] + 1)
    mesh = ax.pcolormesh(
        g.ue[iu[0] : iu[-1] + 2],
        g.ze[iz[0] : iz[-1] + 2],
        values[zs, us],
        cmap=cmap,
        norm=norm,
        shading="flat",
        rasterized=True,
    )
    ax.add_patch(
        Circle(
            (0, 0),
            120,
            edgecolor="#626262",
            linestyle="--",
            facecolor="none",
            linewidth=0.85,
        )
    )
    ax.set(
        aspect="equal",
        xlim=(-125, 125),
        ylim=(-125, 125),
        xlabel="Projected position u (kpc)",
    )
    return mesh


def overlay_figure(
    angle, g, raw, bg, masks, path, native, display, positions, norms, output
):
    font = {"fontsize": 10}
    columns = 3 if native is not None else 2
    fig, axs = plt.subplots(
        1, columns, figsize=(4.75 * columns, 5.35), layout="constrained", sharey=True
    )
    ims = [
        sky(axs[0], g, raw, norms[0], "Greys"),
        sky(axs[1], g, fraction(raw, bg[ORANGE]), norms[1], "RdBu_r"),
    ]
    for i, ax in enumerate(axs[:2]):
        if native is not None:
            outline(ax, g, native["front_path_kpc"] > 0, COLORS["front"], 0.9)
        outline(ax, g, path > 0, COLORS["lobe"], 0.75)
        outline(ax, g, masks[ORANGE], COLORS["orange"], 0.8)
        outline(ax, g, masks[BLUE], COLORS["blue"], 0.7)
        ax.set_title(
            (
                "Original 1-keV brightness",
                "Deficit against the original radial background",
            )[i],
            **font,
        )
        fig.colorbar(
            ims[i],
            ax=ax,
            location="bottom",
            shrink=0.84,
            pad=0.05,
            extend="both",
            label=(
                "Brightness (mJy sr⁻¹)",
                "Fractional deficit, (background − brightness) / background",
            )[i],
        )
    if native is not None:
        ax = axs[2]
        for key, color in [
            ("other_path_kpc", "#7770ac"),
            ("boundary_path_kpc", "#916224"),
            ("front_path_kpc", COLORS["front"]),
        ]:
            outline(ax, g, native[key] > 0, color, 0.65)
        ax.set(
            aspect="equal",
            xlim=(-125, 125),
            ylim=(-125, 125),
            xlabel="Projected position u (kpc)",
            title="Independent compression components",
        )
        ax.add_patch(
            Circle(
                (0, 0),
                120,
                edgecolor="#626262",
                linestyle="--",
                facecolor="none",
                linewidth=0.85,
            )
        )
        ax.legend(
            handles=[
                Line2D([], [], color=color, lw=1.3, label=label)
                for color, label in [
                    (COLORS["front"], "Dominant"),
                    ("#7770ac", "Other detached"),
                    ("#916224", "Boundary-associated"),
                ]
            ],
            frameon=False,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.19),
            ncol=2,
            fontsize=8,
        )
    axs[0].set_ylabel("Jet-axis position z (kpc)")
    lines = [
        (COLORS["lobe"], "Full lobe"),
        (COLORS["orange"], "5% deficit"),
        (COLORS["blue"], "Seed/grow"),
    ]
    if native is not None:
        lines.insert(0, (COLORS["front"], "Compressive front"))
    handles = [Line2D([], [], color=c, lw=1.7, label=l) for c, l in lines]
    handles.append(Line2D([], [], color="#626262", linestyle="--", label="120 kpc"))
    fig.legend(
        handles=handles,
        loc="outside lower center",
        ncol=len(handles),
        frameon=False,
        fontsize=9,
    )
    fig.suptitle(f"G-HI  •  20 Myr  •  side-on azimuth {angle}°", fontsize=13)
    fig.savefig(
        output
        / f"{angle:02d}deg_{'front_overlay' if native is not None else 'original_observer'}.png",
        dpi=142,
    )
    plt.close(fig)
    if native is not None and display is not None:
        replacement_figure(angle, g, bg, path, native, display, norms, output)


def replacement_figure(angle, g, bg, path, native, display, norms, output):
    image = display["image"]
    primary = native["front_path_kpc"] > 0
    fig, axs = plt.subplots(
        1, 3, figsize=(12.2, 4.75), sharex=True, sharey=True, layout="constrained"
    )
    names = (
        "Same-cell replacement brightness",
        "Original radial background",
        "Refitted radial background",
    )
    modes = (
        "replace_same_cells_original_background",
        "replace_same_cells_original_background",
        "replace_same_cells_refit_background",
    )
    backgrounds = (None, bg[ORANGE], display["radial_background_refit"])
    for i, (ax, title, mode, background) in enumerate(
        zip(axs, names, modes, backgrounds)
    ):
        values = image if background is None else fraction(image, background)
        im = sky(
            ax, g, values, norms[0 if i == 0 else 1], "Greys" if i == 0 else "RdBu_r"
        )
        for arr, c in [
            (primary, COLORS["front"]),
            (path > 0, COLORS["lobe"]),
            (display[ORANGE][mode], COLORS["orange"]),
            (display[BLUE][mode], COLORS["blue"]),
        ]:
            outline(ax, g, arr, c, 0.7)
        ax.set_title(title, fontsize=10)
        if i == 0:
            fig.colorbar(
                im,
                ax=ax,
                location="bottom",
                shrink=0.8,
                pad=0.06,
                extend="both",
                label="Brightness (mJy sr⁻¹)",
            )
    fig.colorbar(
        im,
        ax=axs[1:].tolist(),
        location="bottom",
        shrink=0.75,
        extend="both",
        label="Fractional deficit",
    )
    axs[0].set_ylabel("Jet-axis position z (kpc)")
    fig.suptitle(
        f"Front-associated ambient gas at its initial emissivity  •  G-HI/20, {angle}°",
        fontsize=13,
    )
    lines = [
        (COLORS["front"], "Compressive front"),
        (COLORS["lobe"], "Full lobe"),
        (COLORS["orange"], "5% deficit"),
        (COLORS["blue"], "Seed/grow"),
    ]
    fig.legend(
        handles=[Line2D([], [], color=c, lw=1.5, label=l) for c, l in lines],
        loc="outside lower center",
        ncol=4,
        frameon=False,
        fontsize=9,
    )
    fig.savefig(output / f"{angle:02d}deg_front_replacement.png", dpi=135)
    plt.close(fig)


def profile_figure(angle, g, positions, raw, bg, fields, path, native, display, output):
    fig, axs = plt.subplots(4, 2, figsize=(10, 8.6), layout="constrained", sharex=True)
    for k, (side, which, row) in enumerate(positions):
        left, right = axs[k]
        title = "Lateral orange arc" if which == "lateral_arc" else "Lobe"
        if row is None:
            left.set_title(f"{title}  •  {side}  •  no qualifying profile")
            right.set_axis_off()
            continue
        choose = np.abs(g.u) <= 123
        u = g.u[choose]
        for img, color, style, label in (
            (raw, "#222222", "-", "Original image"),
            (bg[ORANGE], "#da7e0a", "--", "Radial background"),
            (display["image"], "#3831a0", "-.", "After replacement"),
        ):
            left.plot(u, img[row, choose], color=color, ls=style, lw=1.1, label=label)
        left.set_yscale("symlog", linthresh=2)
        left.set_ylabel("mJy sr⁻¹")
        left.set_title(f"{title}  •  z = {g.z[row]:.2f} kpc", fontsize=9)
        right.plot(u, path[row, choose], lw=1, color=COLORS["lobe"], label="Lobe path")
        right.plot(
            u,
            native["front_path_kpc"][row, choose],
            color=COLORS["front"],
            lw=1.1,
            label="Front path",
        )
        right.set_ylabel("Path (kpc)")
        other = right.twinx()
        delta = (
            fields["current"]["front"][row, choose]
            - fields["initial"]["front"][row, choose]
        )
        other.plot(u, delta, color="#6a5429", ls=":", lw=1, label="Front brightening")
        other.set_ylabel("Front change (mJy sr⁻¹)", color="#6a5429", fontsize=8)
        right.set_title(f"{title}  •  z = {g.z[row]:.2f} kpc", fontsize=9)
        left.set_xlim(-120, 120)
        right.set_xlim(-120, 120)
        if k == 0:
            left.legend(loc="upper right", fontsize=7, frameon=False)
            right.legend(loc="upper left", fontsize=7, frameon=False)
    for ax in axs[-1]:
        ax.set_xlabel("Projected position u (kpc)")
    fig.suptitle(f"Transverse profiles  •  G-HI/20, {angle}°", fontsize=13)
    fig.savefig(output / f"{angle:02d}deg_transverse_profiles.png", dpi=142)
    plt.close(fig)
