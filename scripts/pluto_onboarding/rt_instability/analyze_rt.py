from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
import array as _array

sys.path.insert(0, "/home/bwbrook/git/utas-agn/pluto/Tools/pyPLUTO")
import pyPLUTO.pload as pp


class CompatArray(_array.array):
    def fromstring(self, payload):
        return self.frombytes(payload)


pp.array.array = CompatArray

BASE = Path("/home/bwbrook/work/pluto-onboarding/rt_instability")
RUNS = BASE / "runs"
PLOTS = BASE / "plots"
PLOTS.mkdir(exist_ok=True)
RESULTS = BASE / "results"
RESULTS.mkdir(exist_ok=True)
SCHEMES = ["flat_euler", "linear_hancock", "parabolic_rk3"]
TIMES = [5.0, 10.0, 15.0]
COLORS = {
    "flat_euler": "#d62828",
    "linear_hancock": "#1d3557",
    "parabolic_rk3": "#2a9d8f",
}
LABELS = {
    "flat_euler": "flat + euler",
    "linear_hancock": "linear + hancock",
    "parabolic_rk3": "parabolic + rk3",
}
LOWER_THRESH = 1.1
UPPER_THRESH = 1.9
TIME_TOL = 0.01


def load_time_map(case_dir: Path):
    mapping = {}
    for line in (case_dir / "dbl.out").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            mapping[float(parts[1])] = int(parts[0])
    return mapping


def nearest_output(case_dir: Path, requested_time: float):
    mapping = load_time_map(case_dir)
    available = np.array(sorted(mapping))
    idx = int(np.argmin(np.abs(available - requested_time)))
    actual_time = float(available[idx])
    if abs(actual_time - requested_time) > TIME_TOL:
        raise ValueError(
            f"No output within {TIME_TOL} of requested time {requested_time} in {case_dir}; nearest is {actual_time}"
        )
    return actual_time, mapping[actual_time]


def load_snapshot(case_dir: Path, t: float):
    actual_time, idx = nearest_output(case_dir, t)
    D = pp.pload(idx, w_dir=str(case_dir) + "/")
    rho = np.asarray(D.rho)
    x = np.asarray(D.x1)
    y = np.asarray(D.x2)
    if rho.shape == (len(x), len(y)):
        rho = rho.T
    if rho.shape != (len(y), len(x)):
        raise ValueError(f"Unexpected rho shape {rho.shape}")
    return actual_time, x, y, rho


def profile_metrics(y, rho_xavg):
    bubble_candidates = y[rho_xavg <= LOWER_THRESH]
    spike_candidates = y[rho_xavg >= UPPER_THRESH]
    bubble_height = float(np.max(bubble_candidates)) if bubble_candidates.size else float("nan")
    spike_depth = float(np.min(spike_candidates)) if spike_candidates.size else float("nan")
    mixed_layer_thickness = spike_depth - bubble_height if np.isfinite(bubble_height) and np.isfinite(spike_depth) else float("nan")
    return bubble_height, spike_depth, mixed_layer_thickness


records = []
cache = {}
for scheme in SCHEMES:
    for t in TIMES:
        actual_time, x, y, rho = load_snapshot(RUNS / scheme, t)
        rho_xavg = rho.mean(axis=1)
        bubble_height, spike_depth, mixed_layer_thickness = profile_metrics(y, rho_xavg)
        cache[(scheme, t)] = (actual_time, x, y, rho, rho_xavg)
        records.append({
            "scheme": scheme,
            "requested_time": t,
            "actual_time": actual_time,
            "bubble_height": bubble_height,
            "spike_depth": spike_depth,
            "mixed_layer_thickness": mixed_layer_thickness,
        })

csv_path = RESULTS / "rt_metrics.csv"
with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "scheme",
            "requested_time",
            "actual_time",
            "bubble_height",
            "spike_depth",
            "mixed_layer_thickness",
        ],
    )
    writer.writeheader()
    writer.writerows(records)

fig, axes = plt.subplots(len(SCHEMES), len(TIMES), figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
for i, scheme in enumerate(SCHEMES):
    for j, t in enumerate(TIMES):
        actual_time, x, y, rho, _ = cache[(scheme, t)]
        ax = axes[i, j]
        im = ax.imshow(rho, origin="lower", aspect="auto", extent=[x.min(), x.max(), y.min(), y.max()], vmin=1.0, vmax=2.0, cmap="viridis")
        if i == 0:
            ax.set_title(f"t ~= {actual_time:.2f}")
        if j == 0:
            ax.set_ylabel(LABELS[scheme])
        if i == len(SCHEMES) - 1:
            ax.set_xlabel("x")
fig.suptitle("RT density snapshots by scheme and time", y=1.02)
fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85, label="Density")
fig.savefig(PLOTS / "rt_density_snapshots.png", dpi=180, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(1, len(TIMES), figsize=(12, 4), sharey=True)
for ax, t in zip(axes, TIMES):
    for scheme in SCHEMES:
        _, y, _, rho_xavg = cache[(scheme, t)][1:]
        ax.plot(rho_xavg, y, lw=2, color=COLORS[scheme], label=LABELS[scheme])
    actual_time = cache[(SCHEMES[0], t)][0]
    ax.set_title(f"t ~= {actual_time:.2f}")
    ax.set_xlabel("x-avg density")
    ax.grid(alpha=0.25)
axes[0].set_ylabel("y")
axes[-1].legend(frameon=False, loc="lower right")
fig.suptitle("RT x-averaged density profiles", y=1.03)
fig.tight_layout()
fig.savefig(PLOTS / "rt_xavg_profiles.png", dpi=180, bbox_inches="tight")
plt.close(fig)

summary = RESULTS / "rt_metrics_summary.md"
with summary.open("w") as f:
    f.write("# RT metrics summary\n\n")
    f.write("| scheme | requested_time | actual_time | bubble_height | spike_depth | mixed_layer_thickness |\n")
    f.write("|---|---:|---:|---:|---:|---:|\n")
    for r in records:
        f.write(
            f"| {r['scheme']} | {r['requested_time']:.1f} | {r['actual_time']:.6f} | {r['bubble_height']:.6f} | {r['spike_depth']:.6f} | {r['mixed_layer_thickness']:.6f} |\n"
        )

print("wrote", csv_path)
print("wrote", PLOTS / "rt_density_snapshots.png")
print("wrote", PLOTS / "rt_xavg_profiles.png")
print("wrote", summary)
