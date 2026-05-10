#!/usr/bin/env python3
"""Build a first particle-loss-aware radio smoke map from XRAiSE/PRAiSE."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import astropy.units as u
import numpy as np
import plutokore as pk

from xraise_particle_loss_smoke import load_module, stats


C_LIGHT = 2.99792458e8
KPC_M = 3.0856775814913673e19
MILLIJANSKY_SI = 1.0e-29


def adiabatic_index(pressure_si: np.ndarray, density_si: np.ndarray) -> np.ndarray:
    theta = pressure_si / (density_si * C_LIGHT**2)
    enthalpy = 2.5 * theta + np.sqrt(2.25 * theta**2 + 1.0)
    return (enthalpy - 1.0) / (enthalpy - 1.0 - theta)


def sync_lossless_emissivity(
    *,
    xraise: Any,
    pressure_si: np.ndarray,
    density_si: np.ndarray,
    tracer: np.ndarray,
    frequency_hz: float,
    redshift: float,
    eta: float,
    s: float,
    gmin: float,
    gmax: float,
) -> np.ndarray:
    gamma_c = adiabatic_index(pressure_si, density_si)
    kappa_s = xraise.get_kappa_nonumba(s)
    k_const = xraise.get_K(
        kappa_s,
        s,
        gamma_c.reshape(gamma_c.shape[0], 1, 1),
        gmin,
        gmax,
    ).reshape(gamma_c.shape[0])
    emitted_frequency = frequency_hz * (1.0 + redshift)
    return xraise.get_emissivity_lossless(
        pressure_si,
        eta,
        emitted_frequency,
        s,
        tracer,
        k_const,
    )


def doppler_term(vx: np.ndarray, vy: np.ndarray, vz: np.ndarray, s: float) -> np.ndarray:
    vel2 = vx * vx + vy * vy + vz * vz
    vel2 = np.clip(vel2, 0.0, 0.999999)
    gamma = 1.0 / np.sqrt(1.0 - vel2)
    doppler = 1.0 / (gamma * (1.0 - vy))
    return np.power(doppler, 2.0 + ((s - 1.0) / 2.0))


def make_edges(limit: float, pixel: float) -> np.ndarray:
    n_each_side = int(math.ceil(limit / pixel))
    return np.linspace(-n_each_side * pixel, n_each_side * pixel, 2 * n_each_side + 1)


def bin_surface_brightness(
    *,
    x: np.ndarray,
    z: np.ndarray,
    values: np.ndarray,
    particle_volume_m3: np.ndarray,
    x_edges: np.ndarray,
    z_edges: np.ndarray,
) -> np.ndarray:
    pixel_area_m2 = np.diff(x_edges)[0] * np.diff(z_edges)[0] * KPC_M**2
    weights = values * particle_volume_m3 / pixel_area_m2 / MILLIJANSKY_SI
    hist, _, _ = np.histogram2d(z, x, bins=[z_edges, x_edges], weights=weights)
    return hist


def write_matrix(path: Path, values: np.ndarray) -> None:
    np.savetxt(path, values, delimiter="\t", fmt="%.9e")


def write_vector(path: Path, values: np.ndarray) -> None:
    np.savetxt(path, values, fmt="%.17g")


def side_masks(z: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "negative_z": z < 0.0,
        "positive_z": z > 0.0,
        "bipolar_total": np.ones_like(z, dtype=bool),
    }


def finite_range(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return (float("nan"), float("nan"))
    return float(finite.min()), float(finite.max())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-dir", type=Path, required=True)
    parser.add_argument("--particle-hdf5", type=Path, required=True)
    parser.add_argument("--xraise-py", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--grid-output", type=int, default=8)
    parser.add_argument("--frequency-hz", type=float, default=1.5e8)
    parser.add_argument("--redshift", type=float, default=0.05)
    parser.add_argument("--losses", type=int, default=4)
    parser.add_argument("--particle-sampling-myr", type=float, default=0.01)
    parser.add_argument("--lst-index", type=int, default=2)
    parser.add_argument("--window-width", type=int, default=5)
    parser.add_argument("--smooth-order", type=int, default=3)
    parser.add_argument("--eta", type=float, default=0.03)
    parser.add_argument("--s", type=float, default=2.2)
    parser.add_argument("--gmin", type=float, default=500.0)
    parser.add_argument("--gmax", type=float, default=1.0e5)
    parser.add_argument("--tracer-threshold", type=float, default=5.0e-3)
    parser.add_argument("--xlim-kpc", type=float, default=45.0)
    parser.add_argument("--zlim-kpc", type=float, default=55.0)
    parser.add_argument("--pixel-kpc", type=float, default=0.5)
    parser.add_argument("--negative-volume-kpc3", type=float, default=5395.8850886719865)
    parser.add_argument("--positive-volume-kpc3", type=float, default=5395.8895827940314)
    parser.add_argument("--datatype", choices=["float", "double"], default="float")
    args = parser.parse_args()

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    xraise = load_module(args.xraise_py)
    sim = pk.PlutoSimulation(
        simulation_name="C-HI",
        simulation_directory=args.sim_dir,
        simulation_description="C-HI particle-loss radio smoke",
        datatype=args.datatype,
        dimensions=3,
        file_format="HDF5",
    )
    particle_data, particle_times = pk.particles.load_particle_data_hdf5(
        sim,
        args.particle_hdf5,
    )

    loss_dict = xraise.praise(
        sim=sim,
        part_data=particle_data,
        part_times=particle_times,
        max_output=args.grid_output,
        emit_outputs=[args.grid_output],
        redshift=[args.redshift],
        freqs=np.array([args.frequency_hz], dtype=float),
        eta=args.eta,
        s=args.s,
        gmin=args.gmin,
        gmax=args.gmax,
        lst_index=args.lst_index,
        losses=[args.losses],
        window_width=args.window_width,
        smooth_order=args.smooth_order,
        particle_spacing=args.particle_sampling_myr * u.Myr,
        time_execution=True,
        output_system="grid",
    )
    key = "full" if args.losses == 4 else next(iter(loss_dict))
    entry = loss_dict[key][0]
    part_output = int(entry["part_output"])
    loss_factor = np.asarray(entry["emis"].value[:, 0, 0], dtype=np.float64)

    ids = np.asarray(particle_data["id"][:, part_output], dtype=np.float64)
    x = np.asarray(particle_data["x1"][:, part_output], dtype=np.float64)
    y = np.asarray(particle_data["x2"][:, part_output], dtype=np.float64)
    z = np.asarray(particle_data["x3"][:, part_output], dtype=np.float64)
    vx = np.asarray(particle_data["vx1"][:, part_output], dtype=np.float64)
    vy = np.asarray(particle_data["vx2"][:, part_output], dtype=np.float64)
    vz = np.asarray(particle_data["vx3"][:, part_output], dtype=np.float64)
    tracer = np.asarray(particle_data["tracer"][:, part_output], dtype=np.float64)
    density = np.asarray(particle_data["density"][:, part_output], dtype=np.float64)
    pressure = np.asarray(particle_data["pressure"][:, part_output], dtype=np.float64)

    pressure_si = pressure * sim.unit_values.pressure.si.value
    density_si = density * sim.unit_values.density.si.value

    valid = (
        np.isfinite(ids)
        & np.isfinite(x)
        & np.isfinite(y)
        & np.isfinite(z)
        & np.isfinite(vx)
        & np.isfinite(vy)
        & np.isfinite(vz)
        & np.isfinite(tracer)
        & np.isfinite(pressure_si)
        & np.isfinite(density_si)
        & np.isfinite(loss_factor)
        & (tracer >= args.tracer_threshold)
        & (pressure_si > 0.0)
        & (density_si > 0.0)
    )

    lossless = np.zeros_like(loss_factor, dtype=np.float64)
    lossless[valid] = sync_lossless_emissivity(
        xraise=xraise,
        pressure_si=pressure_si[valid],
        density_si=density_si[valid],
        tracer=tracer[valid],
        frequency_hz=args.frequency_hz,
        redshift=args.redshift,
        eta=args.eta,
        s=args.s,
        gmin=args.gmin,
        gmax=args.gmax,
    )
    doppler = np.ones_like(loss_factor, dtype=np.float64)
    doppler[valid] = doppler_term(vx[valid], vy[valid], vz[valid], args.s)
    lossy_rest = lossless * loss_factor
    lossy_doppler = lossy_rest * doppler
    lossless_doppler = lossless * doppler

    particle_volume_m3 = np.zeros_like(loss_factor, dtype=np.float64)
    selected = valid
    selected_sides = side_masks(z[selected])
    volume_by_side = {
        "negative_z": args.negative_volume_kpc3,
        "positive_z": args.positive_volume_kpc3,
    }
    for side, volume_kpc3 in volume_by_side.items():
        mask_selected = selected_sides[side]
        count = int(mask_selected.sum())
        if count == 0:
            continue
        original_indices = np.flatnonzero(selected)[mask_selected]
        particle_volume_m3[original_indices] = (volume_kpc3 / count) * KPC_M**3

    x_edges = make_edges(args.xlim_kpc, args.pixel_kpc)
    z_edges = make_edges(args.zlim_kpc, args.pixel_kpc)
    x_centres = 0.5 * (x_edges[:-1] + x_edges[1:])
    z_centres = 0.5 * (z_edges[:-1] + z_edges[1:])

    in_frame = (
        selected
        & (x >= x_edges[0])
        & (x < x_edges[-1])
        & (z >= z_edges[0])
        & (z < z_edges[-1])
    )
    lossy_map = bin_surface_brightness(
        x=x[in_frame],
        z=z[in_frame],
        values=lossy_doppler[in_frame],
        particle_volume_m3=particle_volume_m3[in_frame],
        x_edges=x_edges,
        z_edges=z_edges,
    )
    lossless_map = bin_surface_brightness(
        x=x[in_frame],
        z=z[in_frame],
        values=lossless_doppler[in_frame],
        particle_volume_m3=particle_volume_m3[in_frame],
        x_edges=x_edges,
        z_edges=z_edges,
    )
    count_map, _, _ = np.histogram2d(z[in_frame], x[in_frame], bins=[z_edges, x_edges])
    loss_sum_map, _, _ = np.histogram2d(
        z[in_frame], x[in_frame], bins=[z_edges, x_edges], weights=loss_factor[in_frame]
    )
    mean_loss_map = np.divide(
        loss_sum_map,
        count_map,
        out=np.zeros_like(loss_sum_map),
        where=count_map > 0,
    )

    write_vector(out_dir / "x_kpc.tsv", x_centres)
    write_vector(out_dir / "z_kpc.tsv", z_centres)
    write_matrix(out_dir / "radio_150mhz_particle_loss_mjy_sr.tsv", lossy_map)
    write_matrix(out_dir / "radio_150mhz_particle_lossless_mjy_sr.tsv", lossless_map)
    write_matrix(out_dir / "radio_particle_count_map.tsv", count_map)
    write_matrix(out_dir / "radio_particle_mean_loss_factor.tsv", mean_loss_map)

    rows = []
    selected_indices = np.flatnonzero(selected)
    with (out_dir / "particle_radio_positions_0deg.tsv").open("w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(
            [
                "particle_index",
                "id",
                "x_kpc",
                "y_kpc",
                "z_kpc",
                "tracer",
                "loss_factor",
                "doppler_term",
                "lossless_emissivity_si",
                "lossy_emissivity_si",
            ]
        )
        for idx in selected_indices:
            writer.writerow(
                [
                    int(idx),
                    float(ids[idx]),
                    float(x[idx]),
                    float(y[idx]),
                    float(z[idx]),
                    float(tracer[idx]),
                    float(loss_factor[idx]),
                    float(doppler[idx]),
                    float(lossless[idx]),
                    float(lossy_doppler[idx]),
                ]
            )

    side_rows = []
    for side, mask in side_masks(z).items():
        side_mask = selected & mask
        side_count = int(side_mask.sum())
        volume_m3 = float(np.sum(particle_volume_m3[side_mask]))
        luminosity_rest = float(np.sum(lossy_rest[side_mask] * particle_volume_m3[side_mask]) * 4.0 * np.pi)
        luminosity_doppler = float(np.sum(lossy_doppler[side_mask] * particle_volume_m3[side_mask]) * 4.0 * np.pi)
        lossless_luminosity = float(np.sum(lossless_doppler[side_mask] * particle_volume_m3[side_mask]) * 4.0 * np.pi)
        xmin, xmax = finite_range(x[side_mask])
        ymin, ymax = finite_range(y[side_mask])
        zmin, zmax = finite_range(z[side_mask])
        lf_stats = stats(loss_factor[side_mask])
        side_rows.append(
            {
                "side": side,
                "particle_count": side_count,
                "volume_kpc3": volume_m3 / KPC_M**3,
                "lossy_luminosity_rest_w_hz": luminosity_rest,
                "lossy_luminosity_doppler_w_hz": luminosity_doppler,
                "lossless_luminosity_doppler_w_hz": lossless_luminosity,
                "x_min_kpc": xmin,
                "x_max_kpc": xmax,
                "y_min_kpc": ymin,
                "y_max_kpc": ymax,
                "z_min_kpc": zmin,
                "z_max_kpc": zmax,
                "loss_factor_min": lf_stats.get("min", float("nan")),
                "loss_factor_max": lf_stats.get("max", float("nan")),
                "loss_factor_mean": lf_stats.get("mean", float("nan")),
                "loss_factor_positive_count": lf_stats.get("positive_count", 0),
            }
        )

    with (out_dir / "particle_radio_lobe_summary.csv").open("w", newline="") as f:
        fieldnames = list(side_rows[0])
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(side_rows)

    map_positive = lossy_map[lossy_map > 0]
    summary = {
        "sim_dir": str(args.sim_dir),
        "particle_hdf5": str(args.particle_hdf5),
        "xraise_py": str(args.xraise_py),
        "grid_output": args.grid_output,
        "grid_time_myr": float(sim.times[args.grid_output].to(u.Myr).value),
        "particle_output": part_output,
        "particle_time_myr": float(particle_times[part_output] * sim.unit_values.time.to(u.Myr).value),
        "frequency_hz": args.frequency_hz,
        "redshift": args.redshift,
        "tracer_threshold": args.tracer_threshold,
        "selected_particles": int(selected.sum()),
        "in_frame_particles": int(in_frame.sum()),
        "map_shape": list(lossy_map.shape),
        "pixel_kpc": args.pixel_kpc,
        "radio_map_min_mjy_sr": float(lossy_map.min()),
        "radio_map_max_mjy_sr": float(lossy_map.max()),
        "radio_map_sum_mjy_sr_pixel": float(lossy_map.sum()),
        "radio_positive_pixels": int(map_positive.size),
        "loss_factor_stats": stats(loss_factor[selected]),
        "side_summary": side_rows,
        "volume_assignment": "Level 2 tracer > 5e-3 side volumes divided evenly across selected particles on each side",
        "projection": "0 deg, projected along simulation y onto x-z plane",
    }
    (out_dir / "particle_radio_smoke_metadata.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )

    with (out_dir / "particle_radio_smoke_summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value", "unit"])
        writer.writerow(["grid_output", args.grid_output, "index"])
        writer.writerow(["grid_time_myr", summary["grid_time_myr"], "Myr"])
        writer.writerow(["particle_output", part_output, "index"])
        writer.writerow(["particle_time_myr", summary["particle_time_myr"], "Myr"])
        writer.writerow(["frequency_hz", args.frequency_hz, "Hz"])
        writer.writerow(["selected_particles", summary["selected_particles"], "count"])
        writer.writerow(["in_frame_particles", summary["in_frame_particles"], "count"])
        writer.writerow(["radio_map_max_mjy_sr", summary["radio_map_max_mjy_sr"], "mJy/sr"])
        writer.writerow(["radio_map_sum_mjy_sr_pixel", summary["radio_map_sum_mjy_sr_pixel"], "mJy/sr_pixel_sum"])
        writer.writerow(["radio_positive_pixels", summary["radio_positive_pixels"], "pixels"])
        for side in side_rows:
            writer.writerow(
                [
                    f"{side['side']}_lossy_luminosity_doppler",
                    side["lossy_luminosity_doppler_w_hz"],
                    "W/Hz",
                ]
            )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
