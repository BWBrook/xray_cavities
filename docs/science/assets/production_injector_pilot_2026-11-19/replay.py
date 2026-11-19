"""Compare the archived production rates with the independent PLUTO C calculation."""

import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
EPOCHS = (19, 20, 29, 30)


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def check_rows(native, independent, keys, expected):
    primary = [row for row in native if row["method"] == "linear_snapshot_flags"]
    by_key = {tuple(row[k] for k in keys): row for row in primary}
    independent_keys = {tuple(row[k] for k in keys) for row in independent}
    if len(primary) != len(independent) or len(by_key) != expected or independent_keys != by_key.keys():
        raise ValueError(f"Incomplete comparison for {keys}")
    for row in independent:
        key = tuple(row[k] for k in keys)
        for field in row.keys() - set(keys):
            a, b = row[field], by_key[key][field]
            if a == b:
                continue
            if not a or not b or not math.isclose(float(a), float(b), abs_tol=2e-13, rel_tol=2e-12):
                raise ValueError(f"Disagreement at {key}/{field}")


def main():
    independent = json.loads((HERE / "public_comparison_receipt.json").read_text())
    for name, expected in independent["products_sha256"].items():
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"C comparison digest differs for {name}")
    scheduler = json.loads((HERE / "scheduler_pilot_replay.json").read_text())
    tables = {}
    with zipfile.ZipFile(HERE / "pilot_tables.zip") as data:
        for name, item in scheduler["comparisons"].items():
            content = data.read(name)
            if hashlib.sha256(content).hexdigest() != item["remote_sha256"]:
                raise ValueError(f"Pilot table digest differs for {name}")
            tables[name] = list(csv.DictReader(io.StringIO(content.decode())))
            if len(tables[name]) != item["rows"]:
                raise ValueError(f"Pilot row count differs for {name}")
    snapshots = read_csv(HERE / "signed_rates.csv")
    intervals = read_csv(HERE / "signed_intervals.csv")
    check_rows(tables["injector_snapshot_rates.csv"], snapshots, ("case", "index", "region"), 48)
    check_rows(tables["injector_interval_balances.csv"], intervals, ("case", "start_index", "end_index", "rule"), 24)

    directions = {(row["case"], int(row["index"])): row for row in read_csv(HERE / "cap_direction_and_waves.csv")}
    if set(directions) != {(case, i) for case in CASES for i in EPOCHS}:
        raise ValueError("Incomplete face-direction table")
    cap_rates = {(row["case"], int(row["index"])): row for row in snapshots if row["region"] == "cap"}
    for key, row in directions.items():
        axial, lateral = (float(row[d + "_tagged_mass_over_label"]) for d in ("axial", "lateral"))
        cap = float(cap_rates[key]["tracer_over_label"])
        if not math.isclose(axial + lateral, cap, rel_tol=2e-12):
            raise ValueError(f"Axial and lateral contributions differ from cap rate at {key}")
        if not math.isclose(lateral / (cap - 1), float(row["lateral_flux_divided_by_cap_excess_over_label"]), rel_tol=2e-12):
            raise ValueError(f"Side-face share differs at {key}")
        if (int(row["cap_outward_upwind_faces"]) != int(row["axial_faces"]) + int(row["lateral_faces"])
                or float(row["cap_min_outward_Davis_lower_speed_c"]) <= 0):
            raise ValueError(f"Cap contains an inward characteristic at {key}")
    print("case  interval      cap gas    stationary       net gas    net tracer    census")
    for row in intervals:
        if row["rule"] == "trapezoid":
            values = (float(row[k]) for k in ("cap_gas", "stationary_gas", "net_gas", "net_tracer", "observed_tracer"))
            print(f"{row['case']:4}  {row['start_index']}–{row['end_index']}   " + "".join(f"{v:12.5f}" for v in values))


if __name__ == "__main__":
    main()
