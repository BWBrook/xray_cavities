"""Compare the final two saved energy budgets in the three runs that reach 50 Myr."""
import argparse
import csv
import json
import math
import re
from itertools import product
from pathlib import Path

from measure_q031_fluxes import CONTROL_RECONSTRUCTIONS, OUTER_RECONSTRUCTIONS, parse_pluto_parameters
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR, sha256_file


CASES = ("C-HI", "C-LO", "G-LO")
RULES = ("left_rectangle", "trapezoid", "right_rectangle")


def read_rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def require_hash(path, expected):
    if sha256_file(path) != expected:
        raise ValueError(f"Input hash differs for {path.name}")


def compare_case(bundle, case, reference):
    native = bundle / "inputs" / case
    production = bundle / "production" / case
    manifest = json.loads((bundle / "production/manifest.json").read_text())[case]
    receipt = production / "completion.json"
    require_hash(receipt, manifest["receipt_sha256"])
    products = {Path(r["path"]).name: r["sha256"] for r in json.loads(receipt.read_text())["products"]}
    balances = production / "integrated_control_balances.csv"
    require_hash(balances, products[balances.name])
    binding = json.loads((bundle / "inputs/bindings.json").read_text())[case]
    config = native / "pluto.ini"
    require_hash(config, binding["static"]["runtime_config"]["sha256"])
    for name in ("jet.c", "pluto_usr.h", "units.c"):
        require_hash(native / "src" / name, binding["source_helpers"][name])
    params = parse_pluto_parameters(config)
    if (params["JET_START_TIME"], params["JET_END_TIME"], params["JET_ACTIVE_TIME"], params["JET_EPISODES"]) != (0, 50, 50, 1):
        raise ValueError(f"Unexpected duty cycle in {case}")

    history, times = {}, {}
    for row in read_rows(balances):
        start, end = float(row["interval_start_myr"]), float(row["interval_end_myr"])
        index = round(end)
        if index < 39:
            continue
        if times.setdefault(index, (start, end)) != (start, end) or row["case"] != case:
            raise ValueError("Inconsistent interval identity")
        duration = min(params["JET_END_TIME"], end) - start
        label = 2 * params["JET_PWR"] * duration * SECONDS_PER_MYR
        key = index, row["surface"], row["reconstruction"], row["temporal_quadrature"]
        storage, transport, balance = (float(row[k]) / label for k in (
            "storage_energy_change_erg", "integrated_energy_flux_outward_erg", "inferred_internal_energy_source_erg"))
        if key in history or not math.isclose(balance, storage + transport, abs_tol=1e-12):
            raise ValueError(f"Duplicate or inconsistent energy balance for {key}")
        history[key] = (storage, transport, balance)
    if times[49][1] != times[50][0] or abs(times[50][1] - 50) > 1e-8:
        raise ValueError("Last two saved intervals do not meet at index 49 and end at 50 Myr")

    results = []
    for face, rule in product(OUTER_RECONSTRUCTIONS, RULES):
        domain = [history[i, "domain_boundary", face, rule] for i in range(39, 51)]
        previous, final = domain[-2:]
        changes = [b[2] - a[2] for a, b in zip(domain, domain[1:])]
        for pad, method in product((1, 2, 4), CONTROL_RECONSTRUCTIONS):
            nozzle_before, nozzle_final = (history[i, f"nozzle_control_p{pad}", method, rule][2] for i in (49, 50))
            outside_before, outside_final = previous[2] - nozzle_before, final[2] - nozzle_final
            results.append(dict(
                case=case, domain_reconstruction=face, temporal_quadrature=rule, nozzle_padding_cells=pad,
                nozzle_reconstruction=method, domain_source_48_49=previous[2], domain_source_49_50=final[2],
                domain_source_change=changes[-1], domain_storage_change=final[0] - previous[0],
                domain_transport_change=final[1] - previous[1], nozzle_source_48_49=nozzle_before,
                nozzle_source_49_50=nozzle_final, nozzle_source_change=nozzle_final - nozzle_before,
                outside_source_48_49=outside_before, outside_source_49_50=outside_final,
                outside_source_change=outside_final - outside_before, preceding_ten_domain_changes_min=min(changes[:-1]),
                preceding_ten_domain_changes_max=max(changes[:-1]),
                preceding_domain_drops_at_least_as_large=sum(d <= changes[-1] for d in changes[:-1])))

    source = (native / "src/jet.c").read_text()
    header = (native / "src/pluto_usr.h").read_text()
    width = float(re.search(r"jip->delta_t = ([\d.e+-]+) / \(SEC2MYR \* vn.time\)", source).group(1))
    sec2myr = float(re.search(r"#define SEC2MYR \(([\d.e+-]+)\)", header).group(1))
    units = json.loads((bundle / "inputs/units.json").read_text())["jet_prescription_cgs"]
    analysis_myr_per_source_myr = units["velocity"] / (units["length"] * sec2myr * CODE_TIME_PER_MYR)
    ramp_end = params["JET_END_TIME"] * analysis_myr_per_source_myr
    ramp_start = ramp_end - width * analysis_myr_per_source_myr
    if not times[50][0] < ramp_start < ramp_end < times[50][1]:
        raise ValueError("Velocity dip falls outside the final sampled interval")
    mean_speed_cubed = 2.5 - 22 / (3 * math.pi)
    nominal_duration = min(50., times[50][1]) - times[50][0]
    shortfall = (ramp_end - ramp_start) * (1 - mean_speed_cubed) * reference / nominal_duration
    observed = [abs(r["domain_source_change"]) for r in results]
    clock = dict(case=case, age_48_myr=times[49][0], age_49_myr=times[50][0], age_50_myr=times[50][1],
                 ramp_start_myr=ramp_start, ramp_end_myr=ramp_end, mean_speed_factor_cubed=mean_speed_cubed,
                 steady_kinetic_over_label=reference, ideal_kinetic_shortfall_over_final_interval_label=shortfall,
                 ratio_to_observed_domain_drop_min=shortfall / max(observed),
                 ratio_to_observed_domain_drop_max=shortfall / min(observed))
    return results, clock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", required=True, type=Path, help="restored 19 November calibration archive")
    parser.add_argument("--output", required=True, type=Path, help="new output directory")
    args = parser.parse_args()
    references = read_rows(args.calibration / "reference/continuum_reference.csv")
    rows, clocks = [], []
    for case in CASES:
        reference, = {float(r["kinetic_over_Q"]) for r in references if r["case"] == case}
        matched, clock = compare_case(args.calibration, case, reference)
        rows.extend(matched)
        clocks.append(clock)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, records in (("matched_final_intervals.csv", rows), ("source_clock.csv", clocks)):
        with (args.output / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, records[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)


if __name__ == "__main__":
    main()
