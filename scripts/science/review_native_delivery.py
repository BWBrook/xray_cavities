"""Independent review of the delivery-normalised native enthalpy (NAT-01, NAT-07).

Recomputes every case/age/method/rule row from the pinned injector snapshot-rate
tables and the turn-15 native tables without using restate_native_delivery.py or
the archived interval tables, then measures what the estimand is sensitive to.
Independent down to those tables, not to the face-flux reconstruction or the
native HDF5 integrals behind them.

Run: uv run --no-project --with pandas python scripts/science/review_native_delivery.py
"""
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCI = ROOT / "docs/science/assets"
OUT = SCI / "native_delivery_review_2026-11-21"
ARCHIVE = SCI / "production_injector_histories_2026-11-21/history_tables.zip"
NATIVE = SCI / "turn15_review_2026-11-11/budgets"
Q029 = SCI / "q029_binary_native_refresh_2026-09-06/remote_analysis"
PUBLISHED = SCI / "native_delivery_restatement_2026-11-21/selected_age_scenarios.csv"
CASES = ["C-HI", "C-LO", "G-HI", "G-LO"]
MYR = 365.25 * 86400 * 1e6
PRIMARY = ("linear_snapshot_flags", "trapezoid")
RULES = {"left": 0.0, "trapezoid": 0.5, "right": 1.0}


def selected(case):
    return [10, 20, 30, 40] + ([] if case == "G-HI" else [50])


def main():
    bundle = zipfile.ZipFile(ARCHIVE)
    table = lambda name: pd.read_csv(io.BytesIO(bundle.read(name)))
    rows, limits, nat07 = [], [], []
    for case in CASES:
        power = 2e45 if case.endswith("HI") else 2e43
        rates = table(f"native/summary/{case}/injector_snapshot_rates.csv")
        native = pd.read_csv(NATIVE / case / "measurements.csv")
        native = native[native.speed_threshold_km_s == 100].set_index("snapshot_index")
        for method, group in rates.groupby("method"):
            rate = group.pivot(index="index", columns="region", values="gas_energy_over_label").sort_index()
            age = group[group.region == "net"].set_index("index").age_myr.sort_index()
            dt = np.diff(age.values) * MYR
            for rule, w in RULES.items():
                cum = {r: np.concatenate([[0], np.cumsum(power * dt * ((1 - w) * rate[r].values[:-1] + w * rate[r].values[1:]))])
                       for r in ("cap", "stationary")}
                for i in selected(case):
                    h = native.loc[i, "native_enthalpy_2.5_erg"]
                    label = power * min(age[i], 50) * MYR
                    cone, stat = cum["cap"][i], cum["stationary"][i]
                    rows.append(dict(case=case, snapshot_index=i, actual_age_myr=age[i], method=method, rule=rule,
                                     enthalpy_2p5pv_erg=h, cone_gas_erg=cone, stationary_gas_erg=stat,
                                     net_gas_erg=cone + stat, net_gas_over_label=(cone + stat) / label,
                                     stationary_over_label=stat / label, ratio_net=h / (cone + stat), ratio_cone_only=h / cone))
        balance = table(f"native/summary/{case}/injector_interval_balances.csv")
        balance = balance[balance.rule == "trapezoid"]
        last = balance.end_index.max()
        for method, b in balance.groupby("method"):
            c = b.set_index("end_index").tracer_closure_with_native_volume_and_outer_flux
            limits.append(dict(case=case, method=method, first_interval=c[1], sum_intervals_1_to_10=c.loc[1:10].sum(),
                               max_abs_intervals_20_to_47=c.loc[20:47].abs().max(),
                               terminal_interval=c[last] if last == 50 else np.nan))
        primary_d = {r["snapshot_index"]: r["net_gas_erg"] for r in rows
                     if r["case"] == case and (r["method"], r["rule"]) == PRIMARY}
        m = native.loc[30]
        m20 = native.loc[20]
        nat07.append(dict(case=case, enthalpy_over_net_gas=m["native_enthalpy_2.5_erg"] / primary_d[30],
                          r100_storage_over_net_gas=m["all_total_delta_erg"] / primary_d[30],
                          enthalpy_over_r100_storage=m["native_enthalpy_2.5_erg"] / m["all_total_delta_erg"],
                          ambient_share_thermal_kinetic_20myr=(m20.ambient_thermal_delta_erg + m20.ambient_kinetic_delta_erg)
                          / (m20.all_thermal_delta_erg + m20.all_kinetic_delta_erg)))
    rows = pd.DataFrame(rows)
    published = pd.read_csv(PUBLISHED).rename(columns={"quadrature": "rule"})
    joined = rows.merge(published, on=["case", "snapshot_index", "method", "rule"])
    pairs = {"ratio_net": "native_2p5pv_over_cumulative_net_gas", "net_gas_erg": "cumulative_net_gas_delivery_erg",
             "cone_gas_erg": "cumulative_cone_gas_erg", "stationary_gas_erg": "cumulative_stationary_gas_erg"}
    primary = rows[(rows.method == PRIMARY[0]) & (rows.rule == PRIMARY[1])].set_index(["case", "snapshot_index"])

    thresholds = []
    for case in CASES:
        q = pd.read_csv(Q029 / case / "native_energy_selected_age.csv")
        q = q[q.side == "bipolar_total"].set_index(["snapshot_index", "partition_method"])
        for i in selected(case):
            cut = {k: q.loc[(i, f"binary_threshold_{k}")] for k in ("1e-3", "5e-3", "1e-2")}
            d = primary.loc[(case, i), "net_gas_erg"]
            a, b = cut["1e-3"], cut["5e-3"]
            thresholds.append(dict(
                case=case, snapshot_index=i,
                **{f"enthalpy_over_net_gas_tr{k}": v.lobe_enthalpy_2p5pv_erg / d for k, v in cut.items()},
                lobe_density_over_initial_same_cells=a.lobe_mass_g / a.masked_initial_lobe_mass_g,
                skin_density_over_initial_tr1e3_to_5e3=(a.lobe_mass_g - b.lobe_mass_g)
                / (a.masked_initial_lobe_mass_g - b.masked_initial_lobe_mass_g),
                lobe_thermal_over_initial_same_cells=a.lobe_thermal_erg / a.masked_initial_lobe_thermal_erg))
    thresholds = pd.DataFrame(thresholds)

    increments = []
    for case in CASES:
        p = primary.loc[case].sort_index()
        t = thresholds[thresholds.case == case].set_index("snapshot_index").sort_index()
        dd = np.diff(p.net_gas_erg)
        for k, i in enumerate(p.index[1:]):
            increments.append(dict(case=case, from_index=p.index[k], to_index=i,
                                   d_enthalpy_over_d_net_gas=np.diff(p.enthalpy_2p5pv_erg)[k] / dd[k],
                                   **{f"same_at_tr{c}": np.diff(t[f"enthalpy_over_net_gas_tr{c}"] * p.net_gas_erg)[k] / dd[k]
                                      for c in ("5e-3", "1e-2")}))
    OUT.mkdir(parents=True, exist_ok=True)
    rows.to_csv(OUT / "recomputed_rows.csv", index=False)
    thresholds.to_csv(OUT / "threshold_and_lobe_state.csv", index=False)
    pd.DataFrame(increments).to_csv(OUT / "incremental_ratios.csv", index=False)
    pd.DataFrame(limits).to_csv(OUT / "tracer_closure_limits.csv", index=False)
    pd.DataFrame(nat07).to_csv(OUT / "nat07_matched_30myr.csv", index=False)
    clo = rows[rows.case == "C-LO"]
    summary = dict(rows_compared=len(joined), published_rows=len(published),
                   max_relative_difference={k: float((abs(joined[k] - joined[v]) / abs(joined[v])).max()) for k, v in pairs.items()},
                   c_lo_maximum_ratio=float(clo.ratio_net.max()),
                   c_lo_maximum_row=clo.loc[clo.ratio_net.idxmax(), ["snapshot_index", "method", "rule"]].astype(str).tolist())
    (OUT / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    pd.set_option("display.width", 220)
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")
    for name in ("nat07", "limits", "increments"):
        print(pd.DataFrame(locals()[name]).to_string(index=False))


if __name__ == "__main__":
    main()
