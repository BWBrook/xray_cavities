#!/usr/bin/env python3
"""Plot Stewart tabulated environment stability-gate diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import astropy.constants as const
import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import plutokore as pk

from plutokore.jet import UnitValues


UNIT_LENGTH = 1 * u.kpc
UNIT_DENSITY = (0.60364 * u.u / (u.cm**3)).to(u.g / u.cm**3)
UNIT_SPEED = const.c
UNIT_TIME = (UNIT_LENGTH / UNIT_SPEED).to(u.Myr)
UNIT_PRESSURE = (UNIT_DENSITY * (UNIT_SPEED**2)).to(u.Pa)
UNIT_MASS = (UNIT_DENSITY * (UNIT_LENGTH**3)).to(u.kg)
UNIT_ENERGY = (UNIT_MASS * (UNIT_LENGTH**2) / (UNIT_TIME**2)).to(u.J)

UV = UnitValues(
    density=UNIT_DENSITY,
    length=UNIT_LENGTH,
    time=UNIT_TIME,
    mass=UNIT_MASS,
    pressure=UNIT_PRESSURE,
    energy=UNIT_ENERGY,
    speed=UNIT_SPEED,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create plots for Stewart no-jet environment stability gates."
    )
    parser.add_argument("--cluster-dir", type=Path, required=True)
    parser.add_argument("--group-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/science/assets/stewart_environment_gate_2026-05-05"),
    )
    return parser.parse_args()


def load_outputs(sim_dir: Path) -> list:
    times = pk.simulations.get_times(sim_dir)
    return [pk.simulations.load_timestep_data(i, sim_dir) for i, _ in enumerate(times)]


def max_mach(output) -> tuple[float, float]:
    vel = (
        np.sqrt(output.vx1**2 + output.vx2**2 + output.vx3**2) * UV.speed
    ).to(u.km / u.s)
    sound_speed = np.sqrt(
        (3.0 / 5.0) * (output.prs * UV.pressure) / (output.rho * UV.density)
    ).to(u.km / u.s)
    return np.max((vel / sound_speed).si).value, np.max(vel).value


def summarize_case(case_id: str, sim_dir: Path) -> tuple[list[dict[str, float]], list]:
    outputs = load_outputs(sim_dir)
    initial = outputs[0]
    c = (initial.n1 // 2, initial.n2 // 2, initial.n3 // 2)
    rows: list[dict[str, float]] = []

    for output_number, output in enumerate(outputs):
        mach, velocity = max_mach(output)
        initial_density = initial.rho[c]
        current_density = output.rho[c]
        initial_pressure = initial.prs[c]
        current_pressure = output.prs[c]
        rows.append(
            {
                "case_id": case_id,
                "output": output_number,
                "time_myr": float(output.SimTime * UV.time.value),
                "central_density_pct_change": float(
                    (current_density - initial_density) / initial_density * 100.0
                ),
                "central_pressure_pct_change": float(
                    (current_pressure - initial_pressure) / initial_pressure * 100.0
                ),
                "max_mach": float(mach),
                "max_velocity_km_s": float(velocity),
            }
        )
    return rows, outputs


def write_metrics(path: Path, rows: list[dict[str, float]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_timeseries(path: Path, rows_by_case: dict[str, list[dict[str, float]]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    colors = {"cluster 002_003": "#1f77b4", "group 002_031": "#2ca02c"}

    for label, rows in rows_by_case.items():
        times = [row["time_myr"] for row in rows]
        density = [row["central_density_pct_change"] for row in rows]
        pressure = [row["central_pressure_pct_change"] for row in rows]
        mach = [row["max_mach"] for row in rows]
        axes[0].plot(times, density, marker="o", color=colors[label], label=f"{label} density")
        axes[0].plot(
            times,
            pressure,
            marker="s",
            color=colors[label],
            linestyle="--",
            label=f"{label} pressure",
        )
        axes[1].plot(times, mach, marker="o", color=colors[label], label=label)

    axes[0].axhline(1.0, color="0.7", linewidth=1, linestyle=":")
    axes[0].axhline(-1.0, color="0.7", linewidth=1, linestyle=":")
    axes[0].set_xlabel("Time (Myr)")
    axes[0].set_ylabel("Central change (%)")
    axes[0].set_title("Central density and pressure drift")
    axes[0].legend(fontsize=8)
    axes[1].axhline(0.1, color="0.7", linewidth=1, linestyle=":")
    axes[1].set_xlabel("Time (Myr)")
    axes[1].set_ylabel("Max Mach number")
    axes[1].set_title("Spurious flow amplitude")
    axes[1].legend(fontsize=8)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_profiles(path: Path, outputs_by_case: dict[str, list]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)

    for row, (label, outputs) in enumerate(outputs_by_case.items()):
        initial = outputs[0]
        final = outputs[-1]
        j = initial.n2 // 2
        k = initial.n3 // 2
        radius = initial.x1
        density_initial = initial.rho[:, j, k] * UNIT_DENSITY.value
        density_final = final.rho[:, j, k] * UNIT_DENSITY.value
        pressure_initial = initial.prs[:, j, k] * UNIT_PRESSURE.to(u.dyne / u.cm**2).value
        pressure_final = final.prs[:, j, k] * UNIT_PRESSURE.to(u.dyne / u.cm**2).value

        axes[row, 0].plot(radius, density_initial, label="0 Myr")
        axes[row, 0].plot(radius, density_final, linestyle="--", label="300 Myr")
        axes[row, 0].set_yscale("log")
        axes[row, 0].set_ylabel(f"{label}\ndensity (g cm^-3)")
        axes[row, 0].legend(fontsize=8)

        axes[row, 1].plot(radius, pressure_initial, label="0 Myr")
        axes[row, 1].plot(radius, pressure_final, linestyle="--", label="300 Myr")
        axes[row, 1].set_yscale("log")
        axes[row, 1].set_ylabel("pressure (barye)")
        axes[row, 1].legend(fontsize=8)

    for ax in axes[-1, :]:
        ax.set_xlabel("x-axis centreline (kpc)")

    fig.suptitle("Centreline profile stability, initial vs 300 Myr")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows_by_case: dict[str, list[dict[str, float]]] = {}
    outputs_by_case: dict[str, list] = {}
    for label, sim_dir in {
        "cluster 002_003": args.cluster_dir,
        "group 002_031": args.group_dir,
    }.items():
        rows, outputs = summarize_case(label, sim_dir)
        rows_by_case[label] = rows
        outputs_by_case[label] = outputs

    rows = [row for case_rows in rows_by_case.values() for row in case_rows]
    write_metrics(args.output_dir / "stewart_environment_gate_metrics.csv", rows)
    plot_timeseries(args.output_dir / "stewart_environment_gate_timeseries.png", rows_by_case)
    plot_profiles(args.output_dir / "stewart_environment_gate_profiles.png", outputs_by_case)

    print(f"Wrote Stewart gate plots and metrics to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
