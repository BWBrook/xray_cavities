"""Independent review of the paired high-power lobe readout (NAT-12).

Recomputes the paired lobe-enthalpy contrasts from the native lobe receipts in
snapshot_readout.json and from injector rates integrated here from
compact_inputs.zip, without reduce_entropy_lobes.py, verify_entropy_lobes.py
or their tables. It then asks three things the reduction does not: what the
contrast is per unit of energy delivered while the arms differed, how it grew
between 11 and 12 Myr, and how it compares with the solver's own entropy
counter in lobe cells and with the whole-grid energy components.

Independent down to the committed receipts, not to the native HDF5 files.

Run: uv run --no-project --with pandas python scripts/science/review_entropy_lobes.py
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
READOUT = SCI / "entropy_restart_lobes_2026-11-23/snapshot_readout.json"
ARCHIVE = SCI / "entropy_restart_result_2026-11-22/compact_inputs.zip"
SEED = SCI / "native_delivery_review_2026-11-21/recomputed_rows.csv"
PRODUCTION = SCI / "turn15_review_2026-11-11/budgets"
OUT = SCI / "entropy_lobe_review_2026-11-23"
MYR = 365.25 * 86400 * 1e6
POWER = 2e45
CASES = ("G-HI", "C-HI")
CUTS = (0.001, 0.005, 0.01)
LOBE_BINS = ("f_0.001_0.005", "f_0.005_0.5", "f_gt_0.5")
RAW = ["raw_entropy_gain_code", "raw_entropy_loss_code", "raw_entropy_with_p_floor_gain_code",
       "raw_entropy_with_p_floor_loss_code", "raw_p_energy_floor_gain_code", "raw_p_energy_floor_loss_code",
       "raw_E_floor_gain_code", "raw_E_floor_loss_code"]


def load():
    bundle = zipfile.ZipFile(ARCHIVE)
    snaps = {}
    for name in bundle.namelist():
        m = re.fullmatch(r"snapshots/([^/]+)/(ON|OFF)/(grid|injector)_(\d+)\.json", name)
        if m:
            snaps.setdefault((m[1], m[2]), {}).setdefault(int(m[4]), {})[m[3]] = json.loads(bundle.read(name))
    for case in CASES:
        snaps[case, "OFF"][10] = snaps[case, "ON"][10]
    unit = {k: v["energy_unit_erg"] for k, v in json.loads(bundle.read("stages/rk_verification.json")).items()}
    bins = pd.read_csv(io.BytesIO(bundle.read("stages/rk_interval_bins.csv.gz")), compression="gzip")
    bins["net_erg"] = bins.rk_weight * (bins.case + "/" + bins.arm).map(unit) * bins[RAW].sum(axis=1)
    native = {(r["case"], r["arm"], r["index"]): r for r in json.loads(READOUT.read_text())}
    return snaps, bins, native


def series(snaps, case, arm):
    s = dict(sorted(snaps[case, arm].items()))
    t = np.array([v["grid"]["age_myr"] for v in s.values()])
    gas = np.array([v["injector"]["rates"]["linear_snapshot_flags"]["net"]["gas_energy_erg_s"] for v in s.values()])
    delivered = np.concatenate([[0.0], np.cumsum(np.diff(t) * MYR * 0.5 * (gas[:-1] + gas[1:]))])
    comp = {k: np.array([v["grid"]["storage"][f"{k}_erg"] - v["injector"]["flagged_storage"][f"{k2}_erg"]
                         for v in s.values()])
            for k, k2 in (("thermal", "thermal"), ("kinetic", "kinetic"), ("gravitational", "potential"))}
    return list(s), t, gas, delivered, comp


def main():
    snaps, bins, native = load()
    seed_rows = pd.read_csv(SEED)
    rows, growth, grid_rows, summary = [], [], [], {}
    for case in CASES:
        seed = float(seed_rows[(seed_rows.case == case) & (seed_rows.snapshot_index == 10)
                               & (seed_rows.method == "linear_snapshot_flags") & (seed_rows.rule == "trapezoid")].net_gas_erg.iloc[0])
        idx_on, t_on, gas_on, d_on, c_on = series(snaps, case, "ON")
        idx_off, t_off, gas_off, d_off, c_off = series(snaps, case, "OFF")

        def delivered_at(t, d, gas, age):
            k = min(np.searchsorted(t, age, side="right") - 1, len(t) - 2)
            dt = (age - t[k]) * MYR
            rate = gas[k] + (gas[k + 1] - gas[k]) * (age - t[k]) / (t[k + 1] - t[k])
            return d[k] + dt * 0.5 * (gas[k] + rate)

        for nominal, i_on in ((11, 20), (12, 30)):
            on = native[case, "ON", i_on]
            age = on["age_myr"]
            lo = max(i for (c, a, i) in native if c == case and a == "OFF" and native[c, a, i]["age_myr"] <= age)
            hi = min(i for (c, a, i) in native if c == case and a == "OFF" and native[c, a, i]["age_myr"] >= age)
            a, b = native[case, "OFF", lo], native[case, "OFF", hi]
            w = 0.0 if hi == lo else (age - a["age_myr"]) / (b["age_myr"] - a["age_myr"])
            mix = lambda f: (1 - w) * f(a) + w * f(b)
            post_on = delivered_at(t_on, d_on, gas_on, age)
            post_off = delivered_at(t_off, d_off, gas_off, age)
            label = POWER * (age - t_on[0]) * MYR
            store = {k: mix(lambda r: r["r100_storage"][f"{k}_delta_erg"]) - on["r100_storage"][f"{k}_delta_erg"]
                     for k in ("thermal", "kinetic", "gravitational", "total")}
            grid = {k: np.interp(age, t_off, c_off[k]) - np.interp(age, t_on, c_on[k]) for k in c_on}
            for n, cut in enumerate(CUTS):
                assert on["lobes"][n]["tracer_cut"] == cut
                h_on, v_on = on["lobes"][n]["enthalpy_2p5pv_erg"], on["lobes"][n]["volume_kpc3"]
                h_off = mix(lambda r: r["lobes"][n]["enthalpy_2p5pv_erg"])
                v_off = mix(lambda r: r["lobes"][n]["volume_kpc3"])
                dh = h_off - h_on
                rows.append(dict(
                    case=case, nominal_myr=nominal, tracer_cut=cut, age_myr=age, off_weight_high=w,
                    ratio_on=h_on / (seed + post_on), ratio_off=h_off / (seed + post_off),
                    enthalpy_change_percent=100 * dh / h_on, volume_change_percent=100 * (v_off / v_on - 1),
                    mean_pressure_change_percent=100 * ((h_off / v_off) / (h_on / v_on) - 1),
                    net_delivery_over_label_on=post_on / label, net_delivery_over_label_off=post_off / label,
                    enthalpy_change_over_label=dh / label,
                    marginal_enthalpy_per_delivered=dh / post_off,
                    lobe_thermal_change_over_label=0.6 * dh / label,
                    r100_total_change_over_label=store["total"] / label,
                    r100_thermal_change_over_label=store["thermal"] / label,
                    r100_kinetic_change_over_label=store["kinetic"] / label,
                    grid_total_change_over_label=sum(grid.values()) / label,
                    grid_thermal_change_over_label=grid["thermal"] / label,
                    grid_kinetic_change_over_label=grid["kinetic"] / label,
                    grid_gravitational_change_over_label=grid["gravitational"] / label))
        r = pd.DataFrame(rows)
        r = r[(r.case == case) & (r.tracer_cut == 0.001)].set_index("nominal_myr")

        # Each arm's own enthalpy gain per unit of gas energy delivered since the shared seed.
        h10 = native[case, "ON", 10]["lobes"][0]["enthalpy_2p5pv_erg"]
        increment = {arm: (native[case, arm, 30]["lobes"][0]["enthalpy_2p5pv_erg"] - h10) / d[-1]
                     for arm, d in (("ON", d_on), ("OFF", d_off))}

        # Receipt bindings: the pressure field read for the lobe is the one the energy budget read,
        # and the two switch-on lobe values that exist in production match my NAT-01 recomputation.
        shared = [(arm, i) for (c, arm, i) in native if c == case and i in snaps[case, arm]]
        hashes_match = all(native[case, arm, i]["field_sha256"]["prs"]
                           == snaps[case, arm][i]["grid"]["input"]["field_sha256_c_order_float32_le"]["prs"]
                           for arm, i in shared)
        production = pd.read_csv(PRODUCTION / case / "measurements.csv")
        production = production[production.speed_threshold_km_s == 100].set_index("snapshot_index")
        production_match = max(
            max(abs(native[case, "ON", i]["lobes"][0]["enthalpy_2p5pv_erg"] / production.loc[j, "native_enthalpy_2.5_erg"] - 1),
                abs(native[case, "ON", i]["r100_storage"]["total_delta_erg"] / production.loc[j, "all_total_delta_erg"] - 1))
            for i, j in ((10, 10), (20, 11)))

        # How large is the between-arm difference in each whole-grid component next to the switch-on
        # arm's own 0.1-Myr departures from a smooth (quadratic) trend? No replicate pair exists, so this
        # is the only available scale for trajectory variability.
        variability = {}
        for comp in ("thermal", "kinetic"):
            x = t_on - t_on[0]
            smooth = np.polyval(np.polyfit(x, c_on[comp], 2), x)
            diff = np.array([np.interp(age, t_off, c_off[comp]) for age in t_on]) - c_on[comp]
            variability[comp] = dict(
                on_rms_about_quadratic_over_myr_label=float(np.sqrt(np.mean((c_on[comp] - smooth) ** 2)) / (POWER * MYR)),
                on_max_about_quadratic_over_myr_label=float(np.abs(c_on[comp] - smooth).max() / (POWER * MYR)),
                off_minus_on_at_11_over_myr_label=float(diff[10] / (POWER * MYR)),
                off_minus_on_at_12_over_myr_label=float(diff[20] / (POWER * MYR)),
                off_minus_on_min_over_myr_label=float(diff.min() / (POWER * MYR)),
                off_minus_on_max_over_myr_label=float(diff.max() / (POWER * MYR)),
                off_minus_on_at_12_over_on_stock=float(diff[20] / c_on[comp][20]))
        label_myr = POWER * MYR
        counter = bins[(bins.case == case) & (bins.arm == "ON") & (bins.radius_kpc != "injector_flag")]
        for window, (first, last) in (("10-11", (10, 19)), ("11-12", (20, 29)), ("10-12", (10, 29))):
            sel = counter[counter.start_index.between(first, last)]
            span = (t_on[last - 9] - t_on[first - 10]) * MYR * POWER
            lobe = sel[sel.tracer_fraction.isin(LOBE_BINS)]
            h0 = 0.0 if first == 10 else r.loc[11, "enthalpy_change_over_label"] * (r.loc[11, "age_myr"] - t_on[0]) * label_myr
            h1 = (r.loc[11 if last == 19 else 12, "enthalpy_change_over_label"]
                  * (r.loc[11 if last == 19 else 12, "age_myr"] - t_on[0]) * label_myr)
            growth.append(dict(
                case=case, window_myr=window,
                enthalpy_gain_off_minus_on_over_label=(h1 - h0) / span,
                lobe_thermal_gain_off_minus_on_over_label=0.6 * (h1 - h0) / span,
                switch_on_counter_all_exterior_over_label=sel.net_erg.sum() / span,
                switch_on_counter_lobe_cells_over_label=lobe.net_erg.sum() / span,
                switch_on_counter_tracer_gt_0p5_over_label=sel[sel.tracer_fraction == "f_gt_0.5"].net_erg.sum() / span,
                switch_on_counter_tracer_0p005_0p5_over_label=sel[sel.tracer_fraction == "f_0.005_0.5"].net_erg.sum() / span,
                switch_on_counter_tracer_0p001_0p005_over_label=sel[sel.tracer_fraction == "f_0.001_0.005"].net_erg.sum() / span,
                switch_on_counter_ambient_over_label=sel[sel.tracer_fraction == "f_le_0.001"].net_erg.sum() / span))
        for k, age in enumerate(t_on[1:], start=1):
            label = POWER * (age - t_on[0]) * MYR
            diff = {c: np.interp(age, t_off, c_off[c]) - c_on[c][k] for c in c_on}
            grid_rows.append(dict(case=case, on_index=idx_on[k], age_myr=age,
                                  **{f"{c}_off_minus_on_over_label": v / label for c, v in diff.items()},
                                  total_off_minus_on_over_label=sum(diff.values()) / label))
        summary[case] = dict(
            seed_cumulative_net_gas_erg=seed,
            ratio_on_12=r.loc[12, "ratio_on"], ratio_off_12=r.loc[12, "ratio_off"],
            enthalpy_change_percent_11=r.loc[11, "enthalpy_change_percent"],
            enthalpy_change_percent_12=r.loc[12, "enthalpy_change_percent"],
            volume_change_percent_12=r.loc[12, "volume_change_percent"],
            marginal_enthalpy_per_delivered_12=r.loc[12, "marginal_enthalpy_per_delivered"],
            enthalpy_gain_10_to_12_per_delivered_on=increment["ON"],
            enthalpy_gain_10_to_12_per_delivered_off=increment["OFF"],
            shared_pressure_hash_records=len(shared), shared_pressure_hashes_match=bool(hashes_match),
            switch_on_lobe_and_r100_max_relative_difference_from_production=float(production_match),
            whole_grid_component_variability=variability)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, growth, grid_rows = pd.DataFrame(rows), pd.DataFrame(growth), pd.DataFrame(grid_rows)
    rows.to_csv(OUT / "paired_rows.csv", index=False)
    growth.to_csv(OUT / "growth_and_counter.csv", index=False)
    grid_rows.to_csv(OUT / "grid_component_differences.csv", index=False)

    published = pd.read_csv(SCI / "entropy_restart_lobes_2026-11-23/paired_effects.csv")
    published = published[(published.timing == "off_interpolated_to_on") | (published.nominal_myr == 12)]
    merged = rows.merge(published, on=["case", "nominal_myr", "tracer_cut"])
    assert len(merged) == 12
    summary["max_abs_difference_from_published"] = dict(
        ratio_on=float((merged.ratio_on - merged.enthalpy_over_net_gas_on).abs().max()),
        ratio_off=float((merged.ratio_off - merged.enthalpy_over_net_gas_off).abs().max()),
        enthalpy_change_over_label=float((merged.enthalpy_change_over_label
                                          - merged.enthalpy_difference_over_post_seed_label).abs().max()),
        r100_total_change_over_label=float((merged.r100_total_change_over_label
                                            - merged.r100_storage_difference_over_post_seed_label).abs().max()))
    summary["published_timing_labels"] = sorted(published.timing.unique())
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.float_format", "{:.5f}".format)
    print(json.dumps(summary, indent=2))
    print(rows.drop(columns=["age_myr", "off_weight_high"]).T.to_string())
    print(growth.T.to_string())
    print(grid_rows.to_string(index=False))


if __name__ == "__main__":
    main()
