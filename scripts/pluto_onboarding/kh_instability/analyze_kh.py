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

BASE = Path("/home/bwbrook/work/pluto-onboarding/kh_instability")
RUNS = BASE / "runs"
PLOTS = BASE / "plots"
PLOTS.mkdir(exist_ok=True)
RESULTS = BASE / "results"
RESULTS.mkdir(exist_ok=True)
SCHEMES = ["flat_euler", "linear_rk2", "parabolic_rk3"]
TIMES = [1.0, 2.5, 5.0]
COLORS = {
    "flat_euler": "#d62828",
    "linear_rk2": "#1d3557",
    "parabolic_rk3": "#2a9d8f",
}
LABELS = {
    "flat_euler": "flat + euler",
    "linear_rk2": "linear + rk2",
    "parabolic_rk3": "parabolic + rk3",
}
TIME_TOL = 0.05


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
    vy = np.asarray(D.vx2)
    tracer_attr = "trc" if hasattr(D, "trc") else "tr1"
    trc = np.asarray(getattr(D, tracer_attr))
    x = np.asarray(D.x1)
    y = np.asarray(D.x2)
    arrays = []
    for arr in (rho, vy, trc):
        if arr.shape == (len(x), len(y)):
            arr = arr.T
        if arr.shape != (len(y), len(x)):
            raise ValueError(f"Unexpected array shape {arr.shape}")
        arrays.append(arr)
    return actual_time, x, y, arrays[0], arrays[1], arrays[2]


def mixing_thickness(y, trc_xavg):
    high = y[trc_xavg >= 0.9]
    low = y[trc_xavg <= 0.1]
    y09 = float(np.max(high)) if high.size else float("nan")
    y01 = float(np.min(low)) if low.size else float("nan")
    return y01 - y09 if np.isfinite(y01) and np.isfinite(y09) else float("nan")


records = []
cache = {}
for scheme in SCHEMES:
    for t in TIMES:
        actual_time, x, y, rho, vy, trc = load_snapshot(RUNS / scheme, t)
        trc_xavg = trc.mean(axis=1)
        cache[(scheme, t)] = (actual_time, x, y, rho, vy, trc, trc_xavg)
        records.append({
            "scheme": scheme,
            "requested_time": t,
            "actual_time": actual_time,
            "vy2_mean": float(np.mean(vy**2)),
            "max_abs_vy": float(np.max(np.abs(vy))),
            "mixing_layer_thickness": mixing_thickness(y, trc_xavg),
        })

csv_path = RESULTS / "kh_metrics.csv"
with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "scheme",
            "requested_time",
            "actual_time",
            "vy2_mean",
            "max_abs_vy",
            "mixing_layer_thickness",
        ],
    )
    writer.writeheader()
    writer.writerows(records)

fig, axes = plt.subplots(len(SCHEMES), len(TIMES), figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
for i, scheme in enumerate(SCHEMES):
    for j, t in enumerate(TIMES):
        actual_time, x, y, rho, _, _, _ = cache[(scheme, t)]
        ax = axes[i, j]
        im = ax.imshow(rho, origin="lower", aspect="auto", extent=[x.min(), x.max(), y.min(), y.max()], vmin=0.98, vmax=1.02, cmap="viridis")
        if i == 0:
            ax.set_title(f"t ~= {actual_time:.2f}")
        if j == 0:
            ax.set_ylabel(LABELS[scheme])
        if i == len(SCHEMES) - 1:
            ax.set_xlabel("x")
fig.suptitle("KH density snapshots", y=1.02)
fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85, label="Density")
fig.savefig(PLOTS / "kh_density_snapshots.png", dpi=180, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(len(SCHEMES), len(TIMES), figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
for i, scheme in enumerate(SCHEMES):
    for j, t in enumerate(TIMES):
        actual_time, x, y, _, _, trc, _ = cache[(scheme, t)]
        ax = axes[i, j]
        im = ax.imshow(trc, origin="lower", aspect="auto", extent=[x.min(), x.max(), y.min(), y.max()], vmin=0.0, vmax=1.0, cmap="magma")
        if i == 0:
            ax.set_title(f"t ~= {actual_time:.2f}")
        if j == 0:
            ax.set_ylabel(LABELS[scheme])
        if i == len(SCHEMES) - 1:
            ax.set_xlabel("x")
fig.suptitle("KH tracer snapshots", y=1.02)
fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85, label="Tracer")
fig.savefig(PLOTS / "kh_tracer_snapshots.png", dpi=180, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(1, len(TIMES), figsize=(12, 4), sharey=True)
for ax, t in zip(axes, TIMES):
    for scheme in SCHEMES:
        _, y, _, _, _, trc_xavg = cache[(scheme, t)][1:]
        ax.plot(trc_xavg, y, lw=2, color=COLORS[scheme], label=LABELS[scheme])
    actual_time = cache[(SCHEMES[0], t)][0]
    ax.set_title(f"t ~= {actual_time:.2f}")
    ax.set_xlabel("x-avg tracer")
    ax.grid(alpha=0.25)
axes[0].set_ylabel("y")
axes[-1].legend(frameon=False, loc="lower right")
fig.suptitle("KH x-averaged tracer profiles", y=1.03)
fig.tight_layout()
fig.savefig(PLOTS / "kh_tracer_profiles.png", dpi=180, bbox_inches="tight")
plt.close(fig)

summary = RESULTS / "kh_metrics_summary.md"
with summary.open("w") as f:
    f.write("# KH metrics summary\n\n")
    f.write("| scheme | requested_time | actual_time | vy2_mean | max_abs_vy | mixing_layer_thickness |\n")
    f.write("|---|---:|---:|---:|---:|---:|\n")
    for r in records:
        f.write(
            f"| {r['scheme']} | {r['requested_time']:.1f} | {r['actual_time']:.6f} | {r['vy2_mean']:.6e} | {r['max_abs_vy']:.6e} | {r['mixing_layer_thickness']:.6f} |\n"
        )

print("wrote", csv_path)
print("wrote", PLOTS / "kh_density_snapshots.png")
print("wrote", PLOTS / "kh_tracer_snapshots.png")
print("wrote", PLOTS / "kh_tracer_profiles.png")
print("wrote", summary)
