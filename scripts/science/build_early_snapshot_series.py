#!/usr/bin/env python3
"""Build compact early-time C-HI scalar series from aligned smoke outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def read_metric_csv(path: Path) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            out[row["metric"]] = (row["value"], row.get("unit", ""))
    return out


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def f(value: str | float | int) -> float:
    return float(value)


def metric(metrics: dict[str, tuple[str, str]], name: str) -> float:
    return f(metrics[name][0])


def select_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    raise KeyError(f"no row matching {criteria}")


def parse_snapshot_id(path: Path) -> int:
    return int(path.name.split("_", 1)[1])


def collect(input_dir: Path) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for snap_dir in sorted(input_dir.glob("snap_*"), key=parse_snapshot_id):
        output = parse_snapshot_id(snap_dir)
        level1 = read_metric_csv(snap_dir / "truth/level1_injected_energy.csv")
        level2_rows = read_rows(snap_dir / "truth/level2_tracer_lobe_truth.csv")
        cavity_rows = read_rows(snap_dir / "cavity/cavity_stub_summary.csv")
        xray = read_metric_csv(snap_dir / "xray/xraise_grid_smoke_summary.csv")
        radio = read_metric_csv(snap_dir / "radio/particle_radio_smoke_summary.csv")
        lobes = read_rows(snap_dir / "radio/particle_radio_lobe_summary.csv")

        level2 = select_row(level2_rows, threshold="5e-03", side="bipolar_total")
        neg_lobe = select_row(lobes, side="negative_z")
        pos_lobe = select_row(lobes, side="positive_z")
        p_v_total = sum(f(row["pV_erg"]) for row in cavity_rows)
        four_p_v_total = sum(f(row["four_pV_erg"]) for row in cavity_rows)
        sound_age_mean = sum(f(row["sound_age_myr"]) for row in cavity_rows) / len(cavity_rows)
        cavity_distance_mean = sum(f(row["cavity_distance_kpc"]) for row in cavity_rows) / len(cavity_rows)

        rows.append(
            {
                "grid_output": output,
                "grid_time_myr": metric(radio, "grid_time_myr"),
                "particle_output": int(metric(radio, "particle_output")),
                "particle_time_myr": metric(radio, "particle_time_myr"),
                "selected_particles": int(metric(radio, "selected_particles")),
                "injected_energy_bipolar_erg": metric(level1, "injected_energy_bipolar_elapsed"),
                "tracer_volume_bipolar_kpc3": f(level2["volume_kpc3"]),
                "tracer_total_energy_bipolar_erg": f(level2["total_energy_erg"]),
                "tracer_z_extent_kpc": max(abs(f(level2["z_min_kpc"])), abs(f(level2["z_max_kpc"]))),
                "cavity_pv_bipolar_erg": p_v_total,
                "cavity_4pv_bipolar_erg": four_p_v_total,
                "cavity_sound_age_mean_myr": sound_age_mean,
                "cavity_distance_mean_kpc": cavity_distance_mean,
                "xray_corrected_max_mjy_sr": metric(xray, "corrected_xray_max"),
                "xray_corrected_sum_mjy_sr_pixel": metric(xray, "corrected_xray_sum"),
                "radio_map_max_mjy_sr": metric(radio, "radio_map_max_mjy_sr"),
                "radio_luminosity_bipolar_w_hz": metric(radio, "bipolar_total_lossy_luminosity_doppler"),
                "radio_lobe_balance_pos_over_neg": f(pos_lobe["lossy_luminosity_doppler_w_hz"])
                / f(neg_lobe["lossy_luminosity_doppler_w_hz"]),
            }
        )
    return rows


def write_metrics(path: Path, rows: list[dict[str, float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with path.open("w", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot(rows: list[dict[str, float | int]], output_png: Path) -> None:
    t = np.array([float(row["grid_time_myr"]) for row in rows])
    injected = np.array([float(row["injected_energy_bipolar_erg"]) for row in rows]) / 1.0e59
    tracer_energy = np.array([float(row["tracer_total_energy_bipolar_erg"]) for row in rows]) / 1.0e59
    four_pv = np.array([float(row["cavity_4pv_bipolar_erg"]) for row in rows]) / 1.0e59
    volume = np.array([float(row["tracer_volume_bipolar_kpc3"]) for row in rows])
    z_extent = np.array([float(row["tracer_z_extent_kpc"]) for row in rows])
    xray_max = np.array([float(row["xray_corrected_max_mjy_sr"]) for row in rows])
    radio_max = np.array([float(row["radio_map_max_mjy_sr"]) for row in rows])
    radio_lum = np.array([float(row["radio_luminosity_bipolar_w_hz"]) for row in rows])
    lobe_balance = np.array([float(row["radio_lobe_balance_pos_over_neg"]) for row in rows])

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.2), constrained_layout=True)

    ax = axes[0, 0]
    ax.plot(t, injected, marker="o", label="injected")
    ax.plot(t, tracer_energy, marker="o", label="tracer lobe")
    ax.plot(t, four_pv, marker="o", label="4pV cavity")
    ax.set_xlabel("time (Myr)")
    ax.set_ylabel("energy (1e59 erg)")
    ax.set_title("Energy scale")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(t, volume, marker="o", color="#4baf4f", label="volume")
    ax.set_xlabel("time (Myr)")
    ax.set_ylabel("tracer volume (kpc$^3$)")
    ax2 = ax.twinx()
    ax2.plot(t, z_extent, marker="s", color="#cc503e", label="z extent")
    ax2.set_ylabel("z extent (kpc)")
    ax.set_title("Lobe growth")
    ax.grid(True, alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left")

    ax = axes[1, 0]
    ax.plot(t, xray_max / xray_max[0], marker="o", label="X-ray max")
    ax.plot(t, radio_max / radio_max[0], marker="o", label="radio max")
    ax.set_xlabel("time (Myr)")
    ax.set_ylabel("relative to 1 Myr")
    ax.set_title("Observable map peak trends")
    ax.grid(True, alpha=0.25)
    ax.legend()

    ax = axes[1, 1]
    ax.semilogy(t, radio_lum, marker="o", color="#3969ac", label="radio L150")
    ax.set_xlabel("time (Myr)")
    ax.set_ylabel("radio luminosity proxy (W Hz$^{-1}$)")
    ax2 = ax.twinx()
    ax2.plot(t, lobe_balance, marker="s", color="#cc503e", label="+z / -z")
    ax2.axhline(1.0, color="#999999", lw=0.8, ls="--")
    ax2.set_ylabel("radio lobe balance")
    ax.set_title("Radio evolution and symmetry")
    ax.grid(True, alpha=0.25, which="both")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="best")

    fig.suptitle("C-HI aligned early-snapshot scalar series", fontsize=14)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_early_snapshot_series_2026-05-10/compact",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs/science/assets/c_hi_early_snapshot_series_2026-05-10",
    )
    args = parser.parse_args()
    rows = collect(args.input_dir)
    if not rows:
        raise SystemExit(f"no snap_* directories found in {args.input_dir}")
    write_metrics(args.output_dir / "early_snapshot_series_metrics.csv", rows)
    plot(rows, args.output_dir / "c_hi_early_snapshot_series.png")
    print(f"wrote {args.output_dir}")


if __name__ == "__main__":
    main()
