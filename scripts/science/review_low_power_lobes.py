"""Independent review of the low-power lobe contrasts (NAT-13) and the late
production balances (BND-16).

NAT-13: recomputes each arm's 10-12 Myr lobe-enthalpy gain per unit of gas
energy delivered from the native lobe receipts and from injector rates
integrated here from the low-power compact_inputs.zip, then sets the lobe
contrast beside the whole-grid thermal and kinetic differences. It also puts
all four cases on the same increment basis, using my high-power review.

BND-16: accumulates the archived primary interval residuals of the four
production histories and compares them with the published cumulative values
and with the solver counters of the restart window.

Independent down to the committed receipts and interval reductions, not to
the native HDF5 files.

Run: uv run --no-project --with pandas python scripts/science/review_low_power_lobes.py
"""
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCI = ROOT / "docs/science/assets"
LOW = SCI / "low_power_entropy_result_2026-11-23"
HISTORY = SCI / "production_injector_histories_2026-11-21/history_tables.zip"
OUT = SCI / "low_power_entropy_review_2026-11-23"
MYR = 365.25 * 86400 * 1e6
CUTS = (0.001, 0.005, 0.01)


def lobes():
    bundle = zipfile.ZipFile(LOW / "compact_inputs.zip")
    snaps = {}
    for name in bundle.namelist():
        m = re.fullmatch(r"snapshots/([^/]+)/(ON|OFF)/(grid|injector)_(\d+)\.json", name)
        if m:
            snaps.setdefault((m[1], m[2]), {}).setdefault(int(m[4]), {})[m[3]] = json.loads(bundle.read(name))
    native = {(r["case"], r["arm"], r["index"]): r for r in json.loads((LOW / "lobe_native_snapshots.json").read_text())}
    published = pd.read_csv(LOW / "lobe_paired_effects.csv").set_index(["case", "tracer_cut"])
    rows, components, worst = [], [], 0.0
    for case in ("G-LO", "C-LO"):
        snaps[case, "OFF"][10] = snaps[case, "ON"][10]
        series = {}
        for arm in ("ON", "OFF"):
            s = dict(sorted(snaps[case, arm].items()))
            t = np.array([v["grid"]["age_myr"] for v in s.values()])
            gas = np.array([v["injector"]["rates"]["linear_snapshot_flags"]["net"]["gas_energy_erg_s"] for v in s.values()])
            comp = {k: np.array([v["grid"]["storage"][f"{k}_erg"] - v["injector"]["flagged_storage"][f"{k2}_erg"]
                                 for v in s.values()]) for k, k2 in (("thermal", "thermal"), ("kinetic", "kinetic"))}
            series[arm] = (t, float(np.sum(np.diff(t) * MYR * 0.5 * (gas[:-1] + gas[1:]))), comp)
            assert all(native[case, a, i]["field_sha256"]["prs"]
                       == snaps[case, a][i]["grid"]["input"]["field_sha256_c_order_float32_le"]["prs"]
                       for (c, a, i) in native if c == case and a == arm)
        t_on, d_on, c_on = series["ON"]
        t_off, d_off, c_off = series["OFF"]
        label = 2e43 * (t_on[-1] - t_on[0]) * MYR
        for k, age in enumerate(t_on[1:], start=1):
            components.append(dict(case=case, age_myr=age, **{
                f"{c}_off_minus_on_over_myr_label": (np.interp(age, t_off, c_off[c]) - c_on[c][k]) / (2e43 * MYR)
                for c in c_on}))
        for n, cut in enumerate(CUTS):
            seed, on, off = (native[case, a, i]["lobes"][n] for a, i in (("ON", 10), ("ON", 30), ("OFF", 30)))
            assert seed["tracer_cut"] == on["tracer_cut"] == off["tracer_cut"] == cut
            h0, h_on, h_off = (x["enthalpy_2p5pv_erg"] for x in (seed, on, off))
            row = dict(case=case, tracer_cut=cut, gain_per_delivered_on=(h_on - h0) / d_on,
                       gain_per_delivered_off=(h_off - h0) / d_off,
                       enthalpy_change_percent=100 * (h_off / h_on - 1),
                       volume_change_percent=100 * (off["volume_kpc3"] / on["volume_kpc3"] - 1),
                       mean_pressure_change_percent=100 * ((h_off / off["volume_kpc3"]) / (h_on / on["volume_kpc3"]) - 1),
                       cells_off_minus_on=off["cells"] - on["cells"],
                       net_delivery_over_label_on=d_on / label, net_delivery_over_label_off=d_off / label,
                       lobe_thermal_off_minus_on_over_myr_label=0.6 * (h_off - h_on) / (2e43 * MYR),
                       grid_thermal_off_minus_on_over_myr_label=(c_off["thermal"][-1] - c_on["thermal"][-1]) / (2e43 * MYR),
                       grid_kinetic_off_minus_on_over_myr_label=(c_off["kinetic"][-1] - c_on["kinetic"][-1]) / (2e43 * MYR))
            row["gain_change_points"] = 100 * (row["gain_per_delivered_off"] - row["gain_per_delivered_on"])
            p = published.loc[(case, cut)]
            worst = max(worst, abs(row["gain_per_delivered_on"] - p.gain_over_post_seed_gas_on),
                        abs(row["gain_per_delivered_off"] - p.gain_over_post_seed_gas_off),
                        abs(row["enthalpy_change_percent"] - p.enthalpy_change_percent) / 100)
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(components), worst


def production():
    bundle = zipfile.ZipFile(HISTORY)
    published = pd.read_csv(SCI / "production_entropy_review_2026-11-23/annual_balances.csv")
    restart = {**json.loads((SCI / "entropy_restart_review_2026-11-23/summary.json").read_text()),
               **json.loads((OUT / "summary.json").read_text())}
    rows = []
    for case in ("C-HI", "C-LO", "G-HI", "G-LO"):
        power = 2e45 if case.endswith("HI") else 2e43
        b = pd.read_csv(io.BytesIO(bundle.read(f"native/summary/{case}/injector_interval_balances.csv")))
        b = b[(b.method == "linear_snapshot_flags") & (b.rule == "trapezoid")].sort_values("start_index")
        r = pd.read_csv(io.BytesIO(bundle.read(f"native/summary/{case}/injector_snapshot_rates.csv")))
        age = r[(r.method == "linear_snapshot_flags") & (r.region == "net")].sort_values("index").age_myr.values
        label = power * np.diff(age) * MYR
        residual = b.outside_flagged_sphere_outer_active_cell.values * label
        alternative = b.outside_flagged_sphere_linear_to_boundary_face.values * label
        delivered = b.net_gas.values * label
        pub = published[published.case == case].sort_values("start_index")
        for k in range(len(label)):
            rows.append(dict(
                case=case, end_index=k + 1, end_age_myr=age[k + 1],
                interval_residual_over_label=residual[k] / label[k],
                interval_alternative_face_over_label=alternative[k] / label[k],
                cumulative_residual_over_label=residual[:k + 1].sum() / label[:k + 1].sum(),
                cumulative_residual_over_delivered_gas=residual[:k + 1].sum() / delivered[:k + 1].sum(),
                cumulative_alternative_face_over_label=alternative[:k + 1].sum() / label[:k + 1].sum(),
                difference_from_published_cumulative=residual[:k + 1].sum() / label[:k + 1].sum()
                - pub.cumulative_exterior_over_label.values[k]))
        for k, key in ((10, "counter_net_first_myr"), (11, "counter_net_second_myr")):
            rows[-len(label) + k][f"restart_switch_on_counter_over_label"] = restart[f"{case}/ON"][key]
    return pd.DataFrame(rows)


def main():
    lobe_rows, components, worst = lobes()
    history = production()
    hi = json.loads((SCI / "entropy_lobe_review_2026-11-23/summary.json").read_text())
    increments = {c: (hi[c]["enthalpy_gain_10_to_12_per_delivered_on"], hi[c]["enthalpy_gain_10_to_12_per_delivered_off"])
                  for c in ("G-HI", "C-HI")}
    primary = lobe_rows[lobe_rows.tracer_cut == 0.001].set_index("case")
    for c in ("G-LO", "C-LO"):
        increments[c] = (primary.loc[c, "gain_per_delivered_on"], primary.loc[c, "gain_per_delivered_off"])
    contrast = {env: dict(low_minus_high_on=increments[f"{env}-LO"][0] - increments[f"{env}-HI"][0],
                          low_minus_high_off=increments[f"{env}-LO"][1] - increments[f"{env}-HI"][1]) for env in "CG"}
    at30 = history[history.end_index == 30].set_index("case")
    window = history[history.end_index.isin([11, 12])]
    summary = dict(
        nat13_max_abs_difference_from_published=worst,
        increments_10_to_12={c: dict(on=v[0], off=v[1]) for c, v in increments.items()},
        low_minus_high_increment_contrast=contrast,
        bnd16_cumulative_residual_over_delivered_gas_at_30={c: at30.loc[c, "cumulative_residual_over_delivered_gas"] for c in at30.index},
        bnd16_max_abs_difference_from_published_cumulative=float(history.difference_from_published_cumulative.abs().max()),
        bnd16_production_minus_restart_counter_10_to_12=float(
            (window.interval_residual_over_label - window.restart_switch_on_counter_over_label).abs().max()))
    lobe_rows.to_csv(OUT / "lobe_rows.csv", index=False)
    components.to_csv(OUT / "grid_component_differences.csv", index=False)
    history.to_csv(OUT / "production_cumulative_residuals.csv", index=False)
    (OUT / "lobe_and_history_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", "{:.5f}".format)
    print(json.dumps(summary, indent=2))
    print(lobe_rows.T.to_string())
    print(components[components.age_myr.round(1).isin([10.5, 11.0, 11.5, 11.8, 12.0])].to_string(index=False))
    show = history[history.end_index.isin([5, 10, 11, 12, 15, 17, 20, 30, 40, 47, 50])]
    print(show.drop(columns=["difference_from_published_cumulative"]).to_string(index=False))


if __name__ == "__main__":
    main()
