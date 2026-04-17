#!/usr/bin/env python3
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plutokore as pk

BASE = Path("/home/bwbrook/work/pluto-onboarding/krause_jets_assignment")
RESULTS = BASE / "results"
PLOTS = BASE / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

TRACER_THRESHOLD = 0.005
CASES = [
    ("baseline", "Baseline"),
    ("higher_power", "Higher power"),
]


@dataclass
class FinalSnapshot:
    label: str
    density: np.ndarray
    tracer: np.ndarray
    rcyl_edges: np.ndarray
    z_edges: np.ndarray


def get_case_geometry(sim_data, *, edges: bool = False):
    radial = sim_data.x1r if edges else sim_data.x1
    polar = sim_data.x2r if edges else sim_data.x2
    rr, tt = np.meshgrid(radial, polar, indexing="ij")
    rcyl = rr * np.sin(tt)
    z = rr * np.cos(tt)
    return rcyl, z


def get_lobe_metrics(sim_data):
    tracer_count = pk.simulations.get_tracer_count_data(sim_data)
    _, clamped_tracers, combined_tracers = pk.simulations.clamp_tracers(
        sim_data,
        tracer_count,
        tracer_threshold=TRACER_THRESHOLD,
    )
    lobe_mask = clamped_tracers > TRACER_THRESHOLD
    rcyl, z = get_case_geometry(sim_data)
    cell_volume = pk.simulations.calculate_cell_volume(sim_data)

    if not np.any(lobe_mask):
        return {
            "combined_tracer": combined_tracers,
            "lobe_length_kpc": 0.0,
            "lobe_width_kpc": 0.0,
            "lobe_volume": 0.0,
            "rcyl": rcyl,
            "z": z,
        }

    return {
        "combined_tracer": combined_tracers,
        "lobe_length_kpc": float(np.nanmax(np.abs(z[lobe_mask]))),
        "lobe_width_kpc": float(np.nanmax(rcyl[lobe_mask])),
        "lobe_volume": float(np.nansum(cell_volume[lobe_mask])),
        "rcyl": rcyl,
        "z": z,
    }


def load_case(case_name: str, label: str):
    case_dir = RESULTS / case_name
    nlast = pk.simulations.get_output_count(str(case_dir))
    rows = []
    final_snapshot = None

    for output_index in range(nlast + 1):
        sim_data = pk.simulations.load_timestep_data(
            output_index,
            str(case_dir),
            mmap=True,
        )
        metrics = get_lobe_metrics(sim_data)
        rows.append(
            {
                "case": case_name,
                "output_index": output_index,
                "time_code": float(sim_data.SimTime),
                "lobe_length_kpc": metrics["lobe_length_kpc"],
                "lobe_width_kpc": metrics["lobe_width_kpc"],
                "lobe_volume": metrics["lobe_volume"],
                "tracer_threshold": TRACER_THRESHOLD,
            }
        )
        if output_index == nlast:
            final_snapshot = FinalSnapshot(
                label=label,
                density=np.array(sim_data.rho),
                tracer=np.array(metrics["combined_tracer"]),
                rcyl_edges=np.array(get_case_geometry(sim_data, edges=True)[0]),
                z_edges=np.array(get_case_geometry(sim_data, edges=True)[1]),
            )

    assert final_snapshot is not None
    return rows, final_snapshot


all_rows = []
snapshots = {}
for case_name, label in CASES:
    case_rows, snapshot = load_case(case_name, label)
    all_rows.extend(case_rows)
    snapshots[case_name] = snapshot

metrics_path = PLOTS / "krause_jet_metrics.csv"
with open(metrics_path, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "case",
            "output_index",
            "time_code",
            "lobe_length_kpc",
            "lobe_width_kpc",
            "lobe_volume",
            "tracer_threshold",
        ],
    )
    writer.writeheader()
    writer.writerows(all_rows)

density_vmin = min(np.nanmin(np.log10(s.density)) for s in snapshots.values())
density_vmax = max(np.nanmax(np.log10(s.density)) for s in snapshots.values())

fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), constrained_layout=True)
for ax, (case_name, _) in zip(axes, CASES):
    snapshot = snapshots[case_name]
    mesh = ax.pcolormesh(
        snapshot.rcyl_edges,
        snapshot.z_edges,
        np.log10(snapshot.density),
        shading="auto",
        cmap="magma",
        vmin=density_vmin,
        vmax=density_vmax,
    )
    ax.set_title(snapshot.label)
    ax.set_xlabel("Cylindrical radius (kpc)")
    ax.set_xlim(0, 60)
    ax.set_ylim(-60, 60)
    if ax is axes[0]:
        ax.set_ylabel("Axial distance (kpc)")
fig.colorbar(mesh, ax=axes, pad=0.02, label="log10 density (code units)")
fig.suptitle("Krause-style jet assignment: final density comparison", y=1.02)
fig.savefig(PLOTS / "krause_jet_density.png", dpi=200, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), constrained_layout=True)
for ax, (case_name, _) in zip(axes, CASES):
    snapshot = snapshots[case_name]
    mesh = ax.pcolormesh(
        snapshot.rcyl_edges,
        snapshot.z_edges,
        snapshot.tracer,
        shading="auto",
        cmap="Blues",
        vmin=0.0,
        vmax=1.0,
    )
    ax.set_title(snapshot.label)
    ax.set_xlabel("Cylindrical radius (kpc)")
    ax.set_xlim(0, 60)
    ax.set_ylim(-60, 60)
    if ax is axes[0]:
        ax.set_ylabel("Axial distance (kpc)")
fig.colorbar(mesh, ax=axes, pad=0.02, label="Combined tracer")
fig.suptitle("Krause-style jet assignment: final tracer comparison", y=1.02)
fig.savefig(PLOTS / "krause_jet_tracer.png", dpi=200, bbox_inches="tight")
plt.close(fig)

case_groups = {case_name: [] for case_name, _ in CASES}
for row in all_rows:
    case_groups[row["case"]].append(row)

fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
metrics = [
    ("lobe_length_kpc", "Lobe length (kpc)"),
    ("lobe_width_kpc", "Lobe width (kpc)"),
    ("lobe_volume", "Lobe volume (code units)"),
]
for ax, (metric_key, metric_label) in zip(axes, metrics):
    for case_name, label in CASES:
        rows = sorted(case_groups[case_name], key=lambda item: item["output_index"])
        ax.plot(
            [row["time_code"] for row in rows],
            [row[metric_key] for row in rows],
            marker="o",
            lw=2,
            label=label,
        )
    ax.set_xlabel("Simulation time (code units)")
    ax.set_ylabel(metric_label)
    ax.set_title(metric_label)
axes[0].legend(frameon=False)
fig.suptitle("Krause-style jet assignment: tracer-based lobe diagnostics", y=1.03)
fig.savefig(PLOTS / "krause_jet_timeseries.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("[done] analysis complete")
print(f"saved {metrics_path}")
print(f"saved {PLOTS / 'krause_jet_density.png'}")
print(f"saved {PLOTS / 'krause_jet_tracer.png'}")
print(f"saved {PLOTS / 'krause_jet_timeseries.png'}")
