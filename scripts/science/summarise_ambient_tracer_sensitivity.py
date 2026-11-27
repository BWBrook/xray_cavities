"""Compare the five native tracer receipts with the published stocks and the 30-Myr forecasts."""
import argparse
import json
import math
from pathlib import Path

from bound_ambient_tracer_partition import NATIVE, rows30
from four_case_energy_partition import ASSETS, CASES, PUBLISHED, checked, csv_rows, write_table


OUT = ASSETS / "aperture_partition_followup_2026-11-27"
# Board 3870, published before the five reads, gives percentages to one decimal.
FORECAST = {"C-HI": 58.2, "C-LO": 91.6, "G-HI": 47.7, "G-LO": 74.3}
BANDS = ("unmarked", "positive_le_1e-4", "gt_1e-4_le_1e-3", "gt_1e-3")


def summary():
    run = json.loads((OUT / "native_receipt.json").read_bytes())
    registration = json.loads(checked(ASSETS / "aperture_transport_2026-11-26/registration.json", run["registration_sha256"]))["cases"]
    stocks = {(r["case"], int(r["snapshot_index"]), r["aperture"], r["region"]): r
              for r in csv_rows(checked(PUBLISHED / "sphere_components.csv", run["published_stocks_sha256"]))}
    bounds = {r["case"]: r for r in csv_rows(checked(OUT / "thermal_tracer_30myr.csv", run["archived_bounds_sha256"]))}
    jobs = {(j["case"], j["index"]): j for j in run["jobs"]}
    targets = [(case, 30) for case in CASES] + [("C-LO", 50)]
    if set(jobs) != set(targets) or len(run["jobs"]) != len(targets):
        raise ValueError("Expected four 30-Myr receipts and C-LO at 50 Myr")
    rows = []
    for case, index in targets:
        job = jobs[case, index]
        raw = json.loads(checked(OUT / "native" / f"{case}_{index}.json", job["sha256"]))
        reg = registration[case]
        snap = reg["snapshots"][index]
        if (job["state"] != "F" or job["exit_status"] != 0 or (raw["case"], raw["index"]) != (case, index)
                or raw["reader_sha256"] != run["reader_sha256"] or raw["registration_sha256"] != run["registration_sha256"]
                or raw["published_stocks_sha256"] != run["published_stocks_sha256"] or raw["actual_age_myr"] != snap["age_myr"]
                or raw["native_sha256"] != snap["native_sha256"] or raw["initial_sha256"] != reg["snapshots"][0]["native_sha256"]
                or raw["fixed_receipt_sha256"] != snap["fixed_sha256"] or raw["axes_sha256"] != reg["static_sha256"]["axes.npz"]):
            raise ValueError(f"Source or completion receipt differs for {case}/{index}")
        names = ["R100"] if index == 30 else ["R100", "R300", "R100_minus_R300"]
        if set(names) != set(raw["apertures"]):
            raise ValueError(f"Aperture set differs for {case}/{index}")
        delivery = raw["cumulative_net_gas_delivery_erg"]
        for name in names:
            a = raw["apertures"][name]
            bands = [a["bands"][key] for key in BANDS]
            primary, tighter = a["ambient_le_1e-3"], a["ambient_le_1e-4"]
            if sum(b["cell_count"] for b in bands) != a["all"]["cell_count"]:
                raise ValueError(f"Band counts differ at {case}/{index}/{name}")
            # Subtract the inner archived stock only for the shell.
            outer = "R100" if name == "R100_minus_R300" else name
            for native, region in ((a["all"], "all"), (primary, "ambient")):
                stock = stocks[case, index, outer, region]
                count, energy = int(stock["cell_count"]), float(stock["thermal_delta_erg"])
                if name == "R100_minus_R300":
                    inner = stocks[case, index, "R300", region]
                    count -= int(inner["cell_count"])
                    energy -= float(inner["thermal_delta_erg"])
                if (native["cell_count"] != count or float(stock["cumulative_net_gas_delivery_erg"]) != delivery
                        or abs(native["thermal_change_erg"] - energy) > 5e-11 * delivery):
                    raise ValueError(f"Archived {region} stock differs at {case}/{index}/{name}")

            binary = 100 * primary["thermal_change_erg"] / delivery
            strict = 100 * tighter["thermal_change_erg"] / delivery
            weighted = 100 * math.fsum(b["one_minus_tr1_thermal_change_erg"] for b in bands) / delivery
            dilute = 100 * bands[2]["thermal_change_erg"] / delivery
            lobe = 100 * bands[3]["one_minus_tr1_thermal_change_erg"] / delivery
            subcut_jet = 100 * (primary["thermal_change_erg"] - primary["one_minus_tr1_thermal_change_erg"]) / delivery
            if max(abs(binary - strict - dilute), abs(weighted - binary - lobe + subcut_jet),
                   abs(weighted - 100 * a["all"]["one_minus_tr1_thermal_change_over_delivery"])) > 1e-9:
                raise ValueError(f"Thermal partition does not close at {case}/{index}/{name}")
            forecast = lower = upper = residual = tagged_mass_pct = archive_proxy = proxy_residual = None
            if index == 30:
                predicted = bounds[case]
                lower = 100 * float(predicted["r100_continuous_ambient_thermal_over_delivery_min"])
                upper = 100 * float(predicted["r100_continuous_ambient_thermal_over_delivery_max"])
                forecast, residual = FORECAST[case], weighted - FORECAST[case]
                moment, = (r for r in rows30(NATIVE / case / "native_energy_selected_age.csv")
                           if r["partition_method"] == "fractional" and r["side"] == "bipolar_total")
                if (float(moment["actual_time_myr"]) != raw["actual_age_myr"]
                        or moment["region_delta_reference"] != "same_t0_cells_under_current_partition_weights"):
                    raise ValueError("The archive forecast uses a different epoch or weighting")
                jet_change = float(moment["lobe_thermal_erg"]) - float(moment["masked_initial_lobe_thermal_erg"])
                archive_proxy = 100 * (float(predicted["r100_thermal_change_erg"]) - jet_change) / delivery
                proxy_residual = weighted - archive_proxy
                cocoon = stocks[case, index, "R100", "cocoon"]
                if cocoon["all_lobe_cells_enclosed"] != "True":
                    raise ValueError("Whole-grid tagged lobe mass cannot be assigned to R100")
                tagged_mass = float(predicted["grid_tracer_mass_g"]) - float(predicted["grid_tracer_mass_le_0p001_g"])
                tagged_mass_pct = 100 * tagged_mass / float(cocoon["current_mass_g"])
            rows.append(dict(case=case, snapshot_index=index, actual_age_myr=raw["actual_age_myr"], aperture=name,
                             delivery_erg=delivery, thermal_le_1e_3_pct=binary, thermal_le_1e_4_pct=strict,
                             thermal_in_removed_band_pct=dilute, removed_band_cells=bands[2]["cell_count"],
                             thermal_ambient_weighted_pct=weighted, weighted_minus_binary_pp=weighted-binary,
                             ambient_weighted_in_binary_lobe_pct=lobe, jet_weighted_in_binary_ambient_pct=subcut_jet,
                             forecast_pct=forecast, measured_minus_forecast_pp=residual,
                             archive_proxy_pct=archive_proxy, measured_minus_archive_proxy_pp=proxy_residual,
                             lower_bound_pct=lower, upper_bound_pct=upper,
                             within_archived_bounds=lower <= weighted <= upper if index == 30 else None,
                             jet_tagged_mass_pct_of_binary_lobe=tagged_mass_pct))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT / "native_thermal_partition.csv")
    write_table(parser.parse_args().out, summary())
