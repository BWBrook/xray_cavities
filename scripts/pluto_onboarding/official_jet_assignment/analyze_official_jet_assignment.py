#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plutokore as pk

BASE = Path(
    os.environ.get(
        "OFFICIAL_JET_ASSIGNMENT_BASE",
        str(Path.home() / "work/pluto-onboarding/official_jet_assignment"),
    )
)
RESULTS = BASE / "results"
PLOTS = BASE / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

GAMMA = 5.0 / 3.0
ETA = 10.0
RHO_JET = 1.0
RHO_AMBIENT = ETA
PRS_AMBIENT = 1.0 / GAMMA
EXTERNAL_MACH = 20.0
BEAM_RADIUS = 1.0

CASES = [
    ("r10", "10 cells per beam radius"),
    ("r20", "20 cells per beam radius"),
]


@dataclass
class SnapshotMetrics:
    case: str
    output_index: int
    time: float
    bow_position: float
    bow_speed_from_origin: float
    postshock_density_ratio: float
    min_backflow_speed: float
    shear_velocity_estimate: float
    kh_growth_rate_lambda_2r: float


def load_output(case: str, output_index: int):
    return pk.simulations.load_timestep_data(
        output_index,
        str(RESULTS / case),
        suppress_output=True,
        mmap=True,
        datatype="double",
    )


def output_indices(case: str) -> list[int]:
    return list(range(pk.simulations.get_output_count(str(RESULTS / case)) + 1))


def as_2d(field) -> np.ndarray:
    arr = np.asarray(field)
    if arr.ndim != 2:
        raise ValueError(f"expected 2D field, got shape {arr.shape}")
    return arr


def get_field(sim, *names: str) -> np.ndarray:
    for name in names:
        if hasattr(sim, name):
            return as_2d(getattr(sim, name))
    raise AttributeError(f"none of these fields exist: {names}")


def orient_rz(sim, field: np.ndarray) -> np.ndarray:
    """Return a 2D field as (radius, axial-distance)."""
    nr = len(sim.x1)
    nz = len(sim.x2)
    if field.shape == (nr, nz):
        return field
    if field.shape == (nz, nr):
        return field.T
    raise ValueError(f"field shape {field.shape} does not match grid {(nr, nz)}")


def bow_position(sim, prs: np.ndarray) -> float:
    radius = np.asarray(sim.x1)
    z = np.asarray(sim.x2)
    prs_rz = orient_rz(sim, prs)
    axis_band = radius <= 0.5 * BEAM_RADIUS
    pressure_axis = np.nanmax(prs_rz[axis_band, :], axis=0)
    shocked = np.where(pressure_axis > 1.10 * PRS_AMBIENT)[0]
    if shocked.size == 0:
        return 0.0
    return float(z[shocked[-1]])


def postshock_density_ratio(sim, rho: np.ndarray, bow_z: float) -> float:
    radius = np.asarray(sim.x1)
    z = np.asarray(sim.x2)
    rho_rz = orient_rz(sim, rho)
    axis_band = radius <= 0.75 * BEAM_RADIUS
    shell = (z >= max(0.0, bow_z - 1.5)) & (z <= bow_z + 0.5)
    if not np.any(shell):
        return float("nan")
    return float(np.nanmax(rho_rz[np.ix_(axis_band, shell)]) / RHO_AMBIENT)


def backflow_speed(sim, vx2: np.ndarray, bow_z: float) -> float:
    radius = np.asarray(sim.x1)
    z = np.asarray(sim.x2)
    vx2_rz = orient_rz(sim, vx2)
    cocoon = (
        (radius[:, None] >= BEAM_RADIUS)
        & (radius[:, None] <= 5.0 * BEAM_RADIUS)
        & (z[None, :] >= 0.5)
        & (z[None, :] <= max(0.5, bow_z - 0.5))
    )
    values = vx2_rz[cocoon]
    negative = values[np.isfinite(values) & (values < 0.0)]
    if negative.size == 0:
        return 0.0
    return float(np.nanmin(negative))


def shear_and_kh(sim, rho: np.ndarray, vx2: np.ndarray, bow_z: float) -> tuple[float, float]:
    z = np.asarray(sim.x2)
    rho_rz = orient_rz(sim, rho)
    vx2_rz = orient_rz(sim, vx2)
    col = int(np.nanargmin(np.abs(z - max(1.0, 0.5 * bow_z))))
    speed_profile = vx2_rz[:, col]
    rho_profile = rho_rz[:, col]
    if speed_profile.size < 3:
        return 0.0, 0.0
    shear = float(np.nanmax(speed_profile) - np.nanmin(speed_profile))
    left_rho = max(RHO_JET, float(np.nanmin(rho_profile)))
    right_rho = RHO_AMBIENT
    k = 2.0 * math.pi / (2.0 * BEAM_RADIUS)
    growth = k * abs(shear) * math.sqrt(left_rho * right_rho) / (left_rho + right_rho)
    return shear, float(growth)


def calculate_metrics(case: str, index: int) -> SnapshotMetrics:
    sim = load_output(case, index)
    rho = get_field(sim, "rho")
    prs = get_field(sim, "prs")
    vx2 = get_field(sim, "vx2", "v2")
    bow_z = bow_position(sim, prs)
    time = float(sim.SimTime)
    return SnapshotMetrics(
        case=case,
        output_index=index,
        time=time,
        bow_position=bow_z,
        bow_speed_from_origin=(bow_z / time if time > 0 else 0.0),
        postshock_density_ratio=postshock_density_ratio(sim, rho, bow_z),
        min_backflow_speed=backflow_speed(sim, vx2, bow_z),
        shear_velocity_estimate=shear_and_kh(sim, rho, vx2, bow_z)[0],
        kh_growth_rate_lambda_2r=shear_and_kh(sim, rho, vx2, bow_z)[1],
    )


def plot_density_snapshots(case: str, label: str, indices: list[int]) -> None:
    nonzero = [i for i in indices if i > 0]
    chosen = nonzero[-4:] if len(nonzero) >= 4 else indices[-4:]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), constrained_layout=True)
    axes = axes.ravel()
    all_logs = []
    sims = []
    for index in chosen:
        sim = load_output(case, index)
        rho = get_field(sim, "rho")
        sims.append((index, sim, rho))
        all_logs.append(np.log10(rho))
    vmin = min(float(np.nanmin(item)) for item in all_logs)
    vmax = max(float(np.nanmax(item)) for item in all_logs)
    for ax, (index, sim, rho) in zip(axes, sims):
        mesh = ax.pcolormesh(
            sim.x2r,
            sim.x1r,
            np.log10(orient_rz(sim, rho)),
            shading="auto",
            cmap="magma",
            vmin=vmin,
            vmax=vmax,
        )
        ax.set_title(f"output {index}, t={float(sim.SimTime):.2f}")
        ax.set_xlabel("Axial distance z")
        ax.set_ylabel("Cylindrical radius r")
        ax.set_xlim(0, 32)
        ax.set_ylim(0, 8)
    fig.colorbar(mesh, ax=axes, pad=0.02, label="log10 density")
    fig.suptitle(f"Official jet assignment: {label}", y=1.02)
    fig.savefig(PLOTS / f"official_jet_density_{case}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_timeseries(rows: list[SnapshotMetrics]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), constrained_layout=True)
    for case, label in CASES:
        case_rows = [row for row in rows if row.case == case]
        axes[0].plot([r.time for r in case_rows], [r.bow_position for r in case_rows], marker="o", label=label)
        axes[1].plot([r.time for r in case_rows], [r.bow_speed_from_origin for r in case_rows], marker="o", label=label)
        axes[2].plot([r.time for r in case_rows], [r.min_backflow_speed for r in case_rows], marker="o", label=label)
    axes[0].set_ylabel("Bow-shock position")
    axes[1].set_ylabel("Mean bow-shock speed")
    axes[2].set_ylabel("Most negative backflow speed")
    for ax in axes:
        ax.set_xlabel("Simulation time")
        ax.grid(alpha=0.25)
    axes[0].legend(frameon=False)
    fig.suptitle("Official jet assignment diagnostics", y=1.04)
    fig.savefig(PLOTS / "official_jet_diagnostics_timeseries.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def write_summary(rows: list[SnapshotMetrics]) -> None:
    lines = [
        "# Official PLUTO HD/Jet Assignment Summary",
        "",
        "This smoke report follows Patrick's supplied Martin Krause jet assignment using",
        "PLUTO `Test_Problems/HD/Jet` in 2D cylindrical coordinates.",
        "",
        "Run setup:",
        "",
        f"- Ambient-to-jet density ratio: `{ETA:g}`",
        f"- External Mach number: `{EXTERNAL_MACH:g}`",
        "- Pressure matched jet and uniform environment.",
        "- Two resolutions: `10` and `20` cells per beam radius.",
        "- Domain: `0 <= r <= 8`, `0 <= z <= 32`, beam radius `1`.",
        "",
        "Artifacts:",
        "",
        "- `official_jet_density_r10.png`",
        "- `official_jet_density_r20.png`",
        "- `official_jet_diagnostics_timeseries.png`",
        "- `official_jet_metrics.csv`",
        "",
        "Diagnostic notes:",
        "",
        "- The bow-shock position is estimated from the furthest on-axis pressure",
        "  enhancement above `1.10` times ambient pressure.",
        "- The KH growth-rate estimate uses the incompressible sheet formula with",
        "  characteristic wavelength `2 R_beam`; it is a scale check, not a full",
        "  compressible stability analysis.",
        "- Rankine-Hugoniot checking is summarized by the measured bow-shell density",
        "  compression relative to the strong-shock ideal-gas limit of `4`.",
        "",
    ]
    for case, label in CASES:
        case_rows = [row for row in rows if row.case == case]
        final = case_rows[-1]
        lines.extend(
            [
                f"## {label}",
                "",
                f"- Final bow position: `{final.bow_position:.3f}`",
                f"- Mean bow speed from origin: `{final.bow_speed_from_origin:.3f}`",
                f"- Strong-shock density-ratio limit: `4.000`",
                f"- Measured bow-shell density ratio: `{final.postshock_density_ratio:.3f}`",
                f"- Most negative backflow speed: `{final.min_backflow_speed:.3f}`",
                f"- Characteristic shear velocity estimate: `{final.shear_velocity_estimate:.3f}`",
                f"- KH growth-rate scale for lambda=2R: `{final.kh_growth_rate_lambda_2r:.3f}`",
                "",
            ]
        )
    (PLOTS / "official_jet_assignment_summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    rows: list[SnapshotMetrics] = []
    for case, label in CASES:
        indices = output_indices(case)
        plot_density_snapshots(case, label, indices)
        for index in indices:
            rows.append(calculate_metrics(case, index))

    metrics_path = PLOTS / "official_jet_metrics.csv"
    with metrics_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SnapshotMetrics.__annotations__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

    plot_timeseries(rows)
    write_summary(rows)

    print("[done] official jet assignment analysis complete")
    for path in sorted(PLOTS.iterdir()):
        print(f"saved {path}")


if __name__ == "__main__":
    main()
