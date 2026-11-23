"""Compare the energy components and nested lobe cuts in four paired restarts."""

import argparse
import csv
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

import numpy as np


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
OUT = ASSETS / "entropy_redistribution_review_2026-11-23"
MYR = 365.25 * 86400 * 1e6
CUTS = (0.001, 0.005, 0.01)
COMPONENTS = (("thermal", "thermal"), ("kinetic", "kinetic"), ("gravitational", "potential"))


def write_rows(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def receipt_series(archive, case, arm):
    rows = []
    for index in range(10, 31):
        saved_arm = "ON" if index == 10 else arm
        prefix = f"snapshots/{case}/{saved_arm}"
        grid = json.loads(archive.read(f"{prefix}/grid_{index}.json"))
        injector = json.loads(archive.read(f"{prefix}/injector_{index}.json"))
        if any(grid[k] != injector[k] for k in ("age_myr", "step", "time_code", "index", "case", "arm")):
            raise ValueError(f"unmatched grid and injector at {prefix} {index}")
        rows.append((grid, injector))
    time = np.array([g["age_myr"] for g, _ in rows])
    if not np.all(np.diff(time) > 0) or time[-1] != 12:
        raise ValueError("unexpected restart times")
    rates = [j["rates"]["linear_snapshot_flags"]["net"]["gas_energy_erg_s"] for _, j in rows]
    delivered = math.fsum(dt * MYR * (a + b) / 2 for dt, a, b in zip(np.diff(time), rates, rates[1:]))
    return rows, time, delivered


def component_series(case, on, off, scale):
    pairs, on_age, _ = on
    other_pairs, off_age, _ = off
    records = [dict(case=case, on_index=k, age_myr=t, elapsed_myr=t-on_age[0])
               for k, t in enumerate(on_age[1:], start=11)]
    for term, flagged in COMPONENTS:
        for region in ("whole_grid", "exterior"):
            def stocks(pairs):
                return np.array([g["storage"][term+"_erg"] - (j["flagged_storage"][flagged+"_erg"]
                                 if region == "exterior" else 0.) for g, j in pairs])
            a, b = stocks(pairs), stocks(other_pairs)
            # Interpolate changes from the common seed to limit cancellation of the large initial atmosphere.
            diff = np.interp(on_age[1:], off_age, b - b[0]) - (a[1:] - a[0])
            for row, value in zip(records, diff):
                row[f"{region}_{term}_difference_erg"] = value
                row[f"{region}_{term}_over_one_myr_label"] = value / scale
                row[f"{region}_{term}_over_elapsed_label"] = value / (scale * row["elapsed_myr"])
    return records


def lobe_contrasts(case, lookup, on, off, scale):
    lobes = {}
    for key, grid in [(("ON", 10), on[0][0][0]), (("ON", 30), on[0][-1][0]), (("OFF", 30), off[0][-1][0])]:
        r = lookup[case, *key]
        if (grid["input"]["field_sha256_c_order_float32_le"]["prs"] != r["field_sha256"]["prs"]
                or grid["time_code"] != r["time_code"] or grid["step"] != r["step"]):
            raise ValueError(f"grid and lobe sources differ for {case} {key}")
        lobes[key] = {v["tracer_cut"]: v for v in r["lobes"]}
    changes = []
    for cut in CUTS:
        a = lobes["ON", 30][cut]
        b = lobes["OFF", 30][cut]
        seed_h = lobes["ON", 10][cut]["enthalpy_2p5pv_erg"]
        h_on, h_off = (r["enthalpy_2p5pv_erg"] for r in (a, b))
        volume_ratio = b["volume_kpc3"] / a["volume_kpc3"]
        changes.append(dict(case=case, tracer_cut=cut, cell_count_change=b["cells"]-a["cells"],
                            volume_change_pct=100*(volume_ratio-1), enthalpy_change_pct=100*(h_off/h_on-1),
                            mean_pressure_change_pct=100*((h_off/h_on)/volume_ratio-1),
                            lobe_thermal_difference_over_one_myr_label=0.6*(h_off-h_on)/scale,
                            enthalpy_gain_per_delivered_on=(h_on-seed_h)/on[2],
                            enthalpy_gain_per_delivered_off=(h_off-seed_h)/off[2]))
    return changes


def counter_bins(archive, case):
    verification = json.loads(archive.read("stages/rk_verification.json"))
    unit = verification[case+"/ON"]["energy_unit_erg"]
    totals = {}
    with archive.open("stages/rk_window_bins.csv") as f:
        for row in csv.DictReader(io.TextIOWrapper(f)):
            if row["case"] != case or row["arm"] != "ON" or row["radius_kpc"] == "injector_flag":
                continue
            if (row["start_index"], row["end_index"]) != ("10", "30"):
                raise ValueError("unexpected entropy window")
            net = math.fsum(float(row[f"raw_{term}_{sign}_code"])
                            for term in ("entropy", "entropy_with_p_floor") for sign in ("gain", "loss"))
            weighted = net * float(row["rk_weight"]) * unit / float(row["labelled_energy_erg"])
            key = row["radius_kpc"], row["tracer_fraction"]
            totals[key] = totals.get(key, 0.) + weighted
    return [dict(case=case, radius_kpc=key[0], tracer_bin=key[1], net_entropy_over_interval_label=value)
            for key, value in sorted(totals.items())]


def plot_components(rows, path):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(7.3, 4.7), sharex=True, sharey=True, layout="constrained")
    for ax, case in zip(axes.flat, ("C-HI", "C-LO", "G-HI", "G-LO")):
        case_rows = [r for r in rows if r["case"] == case]
        times = [case_rows[0]["age_myr"] - case_rows[0]["elapsed_myr"]] + [r["age_myr"] for r in case_rows]
        ax.axhline(0, lw=0.7, color="0.57")
        for component, color, style in (("thermal", "#17566e", "-"), ("kinetic", "#bc5a26", "--")):
            values = [0.] + [100 * r[f"whole_grid_{component}_over_one_myr_label"] for r in case_rows]
            ax.plot(times, values, style, linewidth=2, color=color, label=component.capitalize())
        ax.set_title(case, loc="left", fontsize=11)
        ax.spines[["right", "top"]].set_visible(False)
        ax.set_xticks([10, 10.5, 11, 11.5, 12])
    axes[0, 1].legend(loc="upper left", frameon=False)
    fig.supxlabel("Simulation age (Myr)", fontsize=10)
    fig.supylabel("Switch off minus on (% of one Myr of labelled input)", fontsize=10)
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    out = parser.parse_args().output
    out.mkdir(exist_ok=True, parents=True)
    low = ASSETS / "low_power_entropy_result_2026-11-23"
    high = ASSETS / "entropy_restart_result_2026-11-22"
    groups = ((high, ASSETS/"entropy_restart_lobes_2026-11-23/snapshot_readout.json", "HI"),
              (low, low/"lobe_native_snapshots.json", "LO"))
    contrasts, components, bins = [], [], []
    for directory, lobe_file, power in groups:
        lookup = {(r["case"],r["arm"],r["index"]):r for r in json.loads(lobe_file.read_text())}
        with ZipFile(directory / "compact_inputs.zip") as archive:
            for case in ("C-"+power, "G-"+power):
                on, off = (receipt_series(archive, case, arm) for arm in ("ON", "OFF"))
                scale = on[0][0][1]["labelled_power_erg_s"] * MYR
                components.extend(component_series(case, on, off, scale))
                contrasts.extend(lobe_contrasts(case, lookup, on, off, scale))
                bins.extend(counter_bins(archive, case))
    original = {(r["case"], float(r["tracer_cut"])): r for r in csv.DictReader((low/"lobe_paired_effects.csv").read_text().splitlines())}
    difference = max(abs(r["enthalpy_gain_per_delivered_"+arm] -
                         float(original[r["case"], r["tracer_cut"]]["gain_over_post_seed_gas_"+arm]))
                     for r in contrasts if r["case"].endswith("LO") for arm in ("on", "off"))
    if difference > 1e-12:
        raise ValueError(f"low-power interval ratios disagree by {difference}")
    earlier = ASSETS / "entropy_lobe_review_2026-11-23/grid_component_differences.csv"
    common = {(r["case"], r["on_index"]): r for r in components}
    with earlier.open() as stream:
        high_errors = [
            abs(common[r["case"], int(r["on_index"])][f"exterior_{term}_over_elapsed_label"]
                - float(r[f"{term}_off_minus_on_over_label"]))
            for r in csv.DictReader(stream) for term, _ in COMPONENTS
        ]
    if len(high_errors) != 120 or max(high_errors) > 1e-10:
        raise ValueError("high-power components differ from the earlier elapsed-input calculation")
    write_rows(out / "paired_components.csv", components)
    write_rows(out / "lobe_contrasts.csv", contrasts)
    write_rows(out / "switch_on_bins.csv", bins)
    plot_components(components, out / "paired_components.png")
    print(f"{len(components)} age-matched states, {len(contrasts)} lobe comparisons. "
          f"Maximum differences: low-power ratios {difference:.3g}, "
          f"high-power elapsed-input components {max(high_errors):.3g}.")


if __name__ == "__main__":
    main()
