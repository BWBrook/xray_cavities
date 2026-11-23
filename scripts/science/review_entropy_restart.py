"""Independent review of the paired entropy-switch restart budgets (BND-14).

Recomputes the exterior energy residual of each arm from the snapshot-level
stocks and rates in compact_inputs.zip, and the solver's entropy counter from
the raw stage codes, without entropy_restart_budget.py or its tables. It is
independent down to those receipts, not to the native HDF5 files or stage
ledgers behind them.

Run: uv run --no-project --with pandas python scripts/science/review_entropy_restart.py
Low power (BND-15): add --low-power
"""
import argparse
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCI = ROOT / "docs/science/assets"
MYR = 365.25 * 86400 * 1e6
ARMS = ("ON", "OFF")
PRIMARY = ("outer_active_cell", "linear_snapshot_flags", "trapezoid")
RAW = ["raw_entropy_gain_code", "raw_entropy_loss_code", "raw_entropy_with_p_floor_gain_code",
       "raw_entropy_with_p_floor_loss_code", "raw_p_energy_floor_gain_code", "raw_p_energy_floor_loss_code",
       "raw_E_floor_gain_code", "raw_E_floor_loss_code"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--low-power", action="store_true")
    low = parser.parse_args().low_power
    ARCHIVE = SCI / ("low_power_entropy_result_2026-11-23" if low else "entropy_restart_result_2026-11-22") / "compact_inputs.zip"
    OUT = SCI / ("low_power_entropy_review_2026-11-23" if low else "entropy_restart_review_2026-11-23")
    POWER = 2e43 if low else 2e45
    CASES = ("G-LO", "C-LO") if low else ("G-HI", "C-HI")
    bundle = zipfile.ZipFile(ARCHIVE)
    snaps = {}
    for name in bundle.namelist():
        m = re.fullmatch(r"snapshots/([^/]+)/(ON|OFF)/(grid|injector)_(\d+)\.json", name)
        if m:
            snaps.setdefault((m[1], m[2]), {}).setdefault(int(m[4]), {})[m[3]] = json.loads(bundle.read(name))
    for case in CASES:  # the two arms share the 10-Myr production seed
        snaps[case, "OFF"][10] = snaps[case, "ON"][10]
    energy_unit = {k: v["energy_unit_erg"] for k, v in json.loads(bundle.read("stages/rk_verification.json")).items()}
    bins = pd.read_csv(io.BytesIO(bundle.read("stages/rk_interval_bins.csv.gz")), compression="gzip")
    unit = (bins.case + "/" + bins.arm).map(energy_unit)
    bins["net_erg"] = bins.rk_weight * unit * bins[RAW].sum(axis=1)
    bins["gain_erg"] = bins.rk_weight * unit * (bins.raw_entropy_gain_code + bins.raw_entropy_with_p_floor_gain_code)
    bins["loss_erg"] = bins.rk_weight * unit * (bins.raw_entropy_loss_code + bins.raw_entropy_with_p_floor_loss_code)
    exterior = bins[bins.radius_kpc != "injector_flag"]

    budgets, intervals, summary = [], [], {}
    for case in CASES:
        for arm in ARMS:
            s = dict(sorted(snaps[case, arm].items()))
            idx = list(s)
            t = np.array([s[i]["grid"]["age_myr"] for i in idx]) * MYR
            dt = np.diff(t)
            label = POWER * dt
            grid = np.array([s[i]["grid"]["storage"]["total_energy_erg"] for i in idx])
            flag = np.array([s[i]["injector"]["flagged_storage"]["total_erg"] for i in idx])
            counter = exterior[(exterior.case == case) & (exterior.arm == arm)].groupby("start_index")
            counter = counter[["net_erg", "gain_erg", "loss_erg"]].sum().reindex(idx[:-1])
            for outer in ("outer_active_cell", "linear_to_boundary_face"):
                out = np.array([s[i]["grid"]["boundary"][outer]["total_energy_flux_outward_erg_s"] for i in idx])
                for method in s[idx[0]]["injector"]["rates"]:
                    inj = np.array([s[i]["injector"]["rates"][method]["net"]["total_energy_erg_s"] for i in idx])
                    for rule, w in (("left", 0.0), ("trapezoid", 0.5), ("right", 1.0)):
                        quad = lambda x: dt * ((1 - w) * x[:-1] + w * x[1:])
                        resid = np.diff(grid) - np.diff(flag) + quad(out) - quad(inj)
                        later = resid[1:] / label[1:]
                        budgets.append(dict(case=case, arm=arm, outer_boundary=outer, injector_method=method, time_rule=rule,
                                            window_residual=resid.sum() / label.sum(), first_interval_residual=resid[0] / label[0],
                                            later_interval_min=later.min(), later_interval_max=later.max(),
                                            net_delivery=quad(inj).sum() / label.sum(), outer_flux=quad(out).sum() / label.sum(),
                                            grid_source=(np.diff(grid) - np.diff(flag) + quad(out)).sum() / label.sum()))
                        if (outer, method, rule) == PRIMARY:
                            for k, i in enumerate(idx[:-1]):
                                intervals.append(dict(case=case, arm=arm, start_index=i, residual=resid[k] / label[k],
                                                      counter_net=counter.net_erg.iloc[k] / label[k],
                                                      residual_minus_counter=(resid[k] - counter.net_erg.iloc[k]) / label[k]))
                            summary[f"{case}/{arm}"] = dict(
                                window_residual=resid.sum() / label.sum(), counter_net=counter.net_erg.sum() / label.sum(),
                                counter_net_first_myr=counter.net_erg.values[:10].sum() / label[:10].sum(),
                                counter_net_second_myr=counter.net_erg.values[10:].sum() / label[10:].sum(),
                                residual_first_myr=resid[:10].sum() / label[:10].sum(),
                                residual_second_myr=resid[10:].sum() / label[10:].sum(),
                                max_abs_interval_residual_after_first=float(np.abs(resid[1:] / label[1:]).max()),
                                counter_gain=counter.gain_erg.sum() / label.sum(), counter_loss=counter.loss_erg.sum() / label.sum(),
                                max_abs_interval_residual_minus_counter=float(np.abs((resid - counter.net_erg.values) / label).max()),
                                max_abs_interval_residual_minus_counter_after_first=float(np.abs((resid - counter.net_erg.values) / label)[1:].max()))
    region = exterior[exterior.arm == "ON"].groupby(["case", "radius_kpc", "tracer_fraction"])[["net_erg", "gain_erg", "loss_erg"]].sum()
    window_label = {c: POWER * (snaps[c, "ON"][30]["grid"]["age_myr"] - snaps[c, "ON"][10]["grid"]["age_myr"]) * MYR for c in CASES}
    region = region.div(region.index.get_level_values("case").map(window_label), axis=0).reset_index()
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(budgets).to_csv(OUT / "budgets_by_method.csv", index=False)
    pd.DataFrame(intervals).to_csv(OUT / "primary_interval_closure.csv", index=False)
    region.to_csv(OUT / "switch_on_counter_by_region.csv", index=False)
    for case in CASES:
        on, off = summary[f"{case}/ON"]["window_residual"], summary[f"{case}/OFF"]["window_residual"]
        summary[f"{case}/deficit_removed"] = 1 - off / on
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    b = pd.DataFrame(budgets)
    pd.set_option("display.width", 220)
    print(b[(b.time_rule == "trapezoid") & (b.arm == "OFF")].drop(columns=["time_rule", "arm"]).to_string(index=False))


if __name__ == "__main__":
    main()
