"""Rebuild the primary histories from native face components and the reviewed injector table."""
import argparse
import csv
import json
import math
from pathlib import Path
from zipfile import ZipFile


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
TRANSPORT = ASSETS / "aperture_transport_2026-11-26"
ANNUAL = ASSETS / "production_entropy_review_2026-11-23/annual_balances.csv"
SECONDS_PER_MYR = 31557600e6
COMPONENTS = ("thermal_advective_flux_outward_erg_s", "pressure_work_outward_erg_s",
              "kinetic_flux_outward_erg_s", "gravitational_flux_outward_erg_s")


def rows(path):
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def outward(surface):
    flux = surface["flux"]["centered_primitives"]
    return math.fsum(flux[part][key] for part in ("internal", "domain") for key in COMPONENTS)


def rebuild(case, snapshots, archive, annual):
    delivery = supply = grid = 0.0
    carried = dict.fromkeys(("R100", "R300"), 0.0)
    motion = carried.copy()
    for i, snapshot in enumerate(snapshots):
        endpoint = json.loads(archive.read(f"snapshot_{i:04d}.json"))
        identity = endpoint["identity"]
        if (identity["case"], identity["index"], identity["native_sha256"]) != (case, i, snapshot["native_sha256"]):
            raise ValueError(f"Native identity differs at {case}/{i}")
        current = endpoint["measurement"]["apertures"]
        if i == 0:
            previous = current
            continue
        source = annual[case, i]
        dt = SECONDS_PER_MYR * (float(source["end_age_myr"]) - float(source["start_age_myr"]))
        label = float(source["labelled_energy_erg"])
        gas = float(source["delivered_gas_erg"])
        delivery += gas
        supply += gas + label * (float(source["injector_potential_over_label"]) + float(source["maintained_stock_over_label"]))
        grid += label * float(source["exterior_residual_over_label"])
        for name in carried:
            a, b = previous[name], current[name]
            surfaces = (a["surfaces"]["current"], a["surfaces"]["next"],
                        b["surfaces"]["previous"], b["surfaces"]["current"])
            carried[name] += dt * math.fsum(outward(s) for s in surfaces) / 4
            sweeps = (a["sweeps"]["current_to_next"], b["sweeps"]["previous_to_current"])
            motion[name] += 0.5 * math.fsum(s[k] for s in sweeps for k in ("thermal_erg", "kinetic_erg", "gravitational_erg"))
            stock = snapshot["apertures"][name]["stock"]["total_delta_erg"]
            residual = stock - motion[name] + carried[name] - supply
            yield (case, i, name), delivery, {
                "total_energy_outward": carried[name], "membership_correction": motion[name],
                "stock_change": stock, "aperture_residual": residual, "aperture_minus_grid_residual": residual - grid,
            }
        previous = current


def check(directory, tables):
    registry = json.loads((directory / "registration.json").read_bytes())["cases"]
    annual = {(r["case"], int(r["end_index"])): r for r in rows(ANNUAL) if r["scope"] == "annual"}
    primary = rows(tables / "primary_balances.csv")
    published = {(r["case"], int(r["end_index"]), r["aperture"]): r for r in primary}
    seen = set()
    worst = 0.0
    comparisons = 0
    for case, binding in registry.items():
        with ZipFile(directory / f"endpoints_{case}.zip") as archive:
            for key, delivery, quantities in rebuild(case, binding["snapshots"], archive, annual):
                row = published[key]
                pub_delivery = float(row["cumulative_delivered_gas_erg"])
                seen.add(key)
                for quantity, value in quantities.items():
                    difference = abs(value / delivery - float(row[f"cumulative_{quantity}_erg"]) / pub_delivery)
                    if not math.isfinite(difference) or difference > 1e-11:
                        raise ValueError(f"{key} {quantity} differs by {difference} of delivery")
                    worst = max(worst, difference)
                    comparisons += 1
    if len(primary) != 394 or len(seen) != 394 or seen != published.keys():
        raise ValueError("Expected 394 distinct sphere intervals")
    return {"checks": comparisons, "max_difference_over_delivery": worst}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoints", type=Path, default=TRANSPORT)
    parser.add_argument("--tables", type=Path, default=TRANSPORT / "tables")
    args = parser.parse_args()
    print(json.dumps(check(args.endpoints, args.tables), indent=2))
