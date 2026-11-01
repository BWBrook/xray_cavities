#!/usr/bin/env python3
"""Check the numerical transport ledger independently of the simulation writer."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from validate_paired_nojet_outputs import _hash, _publish, _stable, _stat


FACES = tuple(f"x{axis}_{side}" for axis in (1, 2, 3) for side in ("beg", "end"))
QUANTITIES = {"mass": "g", "hydro": "erg", "potential": "erg"}
PARTS = ("net", "positive", "negative")
REPAIR_PARTS = ("net", "positive", "negative", "gross")
REPAIR_COLUMNS = tuple(f"conversion_energy_repair_{part}_{span}_erg"
                       for span in ("interval", "cumulative") for part in REPAIR_PARTS)
CONVERSION_COUNTERS = ("conversion_failure_flagged_cell_observations", "conversion_nonzero_return_call")
COUNTER_COLUMNS = tuple(f"{counter}_{span}_count"
                        for span in ("interval", "cumulative") for counter in CONVERSION_COUNTERS)
GLOBAL = ("mass_g", "hydro_total_erg", "thermal_erg", "kinetic_erg", "potential_erg",
          "conserved_minus_primitive_hydro_erg", "gravity_work_interval_erg", "gravity_work_cumulative_erg",
          *REPAIR_COLUMNS, *COUNTER_COLUMNS,
          "mass_closure_residual_g", "hydro_closure_residual_erg", "potential_closure_residual_erg", "total_closure_residual_erg")


def close(actual: float, expected: float, scale: float, message: str) -> None:
    if abs(actual - expected) > 1e-12 * abs(scale) + 1e-9 * max(abs(actual), abs(expected)):
        raise ValueError(message)


def check_rows(rows: list[dict[str, str]], boundary: str, mode: str) -> dict:
    expected_code = {"outflow": 1, "reflective": 2}[boundary]
    if not rows or len(rows) % 6:
        raise ValueError("ledger must contain six faces per state")
    blocks = []
    required = {"state_step", "completed_step", "time_code", "time_myr", "interval_dt_code", "face", "boundary_type_code", *GLOBAL}
    for quantity, unit in QUANTITIES.items():
        for prefix in ("actual", "cumulative"):
            required.update(f"{prefix}_{quantity}_{part}_{unit}" for part in PARTS)
        required.update({f"reconstructed_{quantity}_rate_{unit}_s", f"reconstructed_{quantity}_interval_{unit}"})
    required.update({"minimum_outward_normal_velocity_km_s", "maximum_outward_normal_velocity_km_s"})
    if set(rows[0]) != required:
        raise ValueError(f"unexpected ledger columns: {set(rows[0]) ^ required}")
    for row in rows:
        if set(row) != required:
            raise ValueError("ledger row schema differs from the required columns")
        for name, value in row.items():
            if name != "face" and not math.isfinite(float(value)):
                raise ValueError(f"non-finite ledger field {name}")
    for offset in range(0, len(rows), 6):
        six = rows[offset:offset + 6]
        if tuple(r["face"] for r in six) != FACES:
            raise ValueError("face set/order is incomplete or duplicated")
        block = [{k: v if k == "face" else float(v) for k, v in row.items()} for row in six]
        for row in block:
            if row["boundary_type_code"] != expected_code:
                raise ValueError("actual boundary dispatch does not match treatment")
            if row["state_step"] != offset // 6 or row["completed_step"] != offset // 6 - 1:
                raise ValueError("accepted-step history has a gap or duplicate")
            for key in (*GLOBAL, "time_code", "time_myr", "interval_dt_code"):
                if row[key] != block[0][key]:
                    raise ValueError(f"global diagnostic disagrees across faces: {key}")
            if row["minimum_outward_normal_velocity_km_s"] > row["maximum_outward_normal_velocity_km_s"]:
                raise ValueError("inverted boundary velocity range")
        blocks.append(block)
    first = blocks[0][0]
    if first["time_code"] != 0 or first["time_myr"] != 0 or first["interval_dt_code"] != 0:
        raise ValueError("ledger must begin at the untouched zero-time state")
    if any(first[name] != 0 for name in ("gravity_work_interval_erg", "gravity_work_cumulative_erg", *REPAIR_COLUMNS, *COUNTER_COLUMNS)):
        raise ValueError("zero-time state contains a source, conversion repair or failure counter")
    if len(blocks) < 11:
        raise ValueError("at least ten accepted updates are required")
    endpoint = {"smoke": 0.25, "full": 50.0}[mode]
    if abs(blocks[-1][0]["time_myr"] - endpoint) > 1e-6:
        raise ValueError("ledger does not reach the required physical endpoint")
    scales = {"mass": first["mass_g"], "hydro": first["hydro_total_erg"], "potential": first["potential_erg"]}
    if min(scales.values()) <= 0:
        raise ValueError("initial storage scales must be positive")
    sums = {(face, quantity, part): 0.0 for face in FACES for quantity in QUANTITIES for part in PARTS}
    gravity = 0.0
    gravity_sum_abs_interval_net = 0.0
    repair_sums = dict.fromkeys(REPAIR_PARTS, 0.0)
    counter_sums = dict.fromkeys(CONVERSION_COUNTERS, 0)
    maximum_fraction = {"mass": 0.0, "hydro": 0.0, "potential": 0.0, "total": 0.0}
    for index, block in enumerate(blocks):
        state = block[0]
        previous = blocks[index - 1][0] if index else state
        if index:
            if state["time_code"] <= previous["time_code"]:
                raise ValueError("physical times must increase")
            close(state["interval_dt_code"], state["time_code"] - previous["time_code"], state["time_code"], "wrong interval dt")
        close(state["time_code"] / 306.601393788, state["time_myr"], endpoint, "inconsistent time units")
        close(state["conserved_minus_primitive_hydro_erg"], state["hydro_total_erg"] - state["thermal_erg"] - state["kinetic_erg"], scales["hydro"], "wrong conserved/primitive energy difference")
        net = dict.fromkeys(QUANTITIES, 0.0)
        gross = dict.fromkeys(QUANTITIES, 0.0)
        for face_index, row in enumerate(block):
            for quantity, unit in QUANTITIES.items():
                values = {part: row[f"actual_{quantity}_{part}_{unit}"] for part in PARTS}
                if values["positive"] < 0 or values["negative"] > 0:
                    raise ValueError("ingress/egress signs are invalid")
                close(values["net"], values["positive"] + values["negative"], 0, "signed actual flux does not sum")
                if not index and any(values.values()):
                    raise ValueError("zero-time state contains already accumulated transport")
                for part in PARTS:
                    key = (row["face"], quantity, part)
                    sums[key] += values[part]
                    close(row[f"cumulative_{quantity}_{part}_{unit}"], sums[key], 0, "cumulative transport differs from accepted intervals")
                net[quantity] += values["net"]
                gross[quantity] += values["positive"] - values["negative"]
                old_rate = blocks[index - 1][face_index][f"reconstructed_{quantity}_rate_{unit}_s"] if index else 0.0
                seconds = (state["time_myr"] - previous["time_myr"]) * 31557600.0e6
                expected_trapezoid = 0.5 * (old_rate + row[f"reconstructed_{quantity}_rate_{unit}_s"]) * seconds if index else 0.0
                close(row[f"reconstructed_{quantity}_interval_{unit}"], expected_trapezoid, gross[quantity], "reconstructed trapezoid is inconsistent")
        gravity += state["gravity_work_interval_erg"]
        gravity_sum_abs_interval_net += abs(state["gravity_work_interval_erg"])
        close(state["gravity_work_cumulative_erg"], gravity, 0, "gravity-work accumulation differs")
        for span in ("interval", "cumulative"):
            repairs = {part: state[f"conversion_energy_repair_{part}_{span}_erg"] for part in REPAIR_PARTS}
            if repairs["positive"] < 0 or repairs["negative"] > 0 or repairs["gross"] < 0:
                raise ValueError("conversion-repair signs are invalid")
            close(repairs["net"], repairs["positive"] + repairs["negative"], repairs["gross"],
                  "signed conversion repair does not sum")
            close(repairs["gross"], repairs["positive"] - repairs["negative"], repairs["gross"],
                  "conversion repair gross differs from cellwise positive-minus-negative")
        for part in REPAIR_PARTS:
            repair_sums[part] += state[f"conversion_energy_repair_{part}_interval_erg"]
        for part in REPAIR_PARTS:
            close(state[f"conversion_energy_repair_{part}_cumulative_erg"], repair_sums[part], repair_sums["gross"],
                  "conversion-repair accumulation differs from accepted intervals")
        for counter in CONVERSION_COUNTERS:
            interval, cumulative = (state[f"{counter}_{span}_count"] for span in ("interval", "cumulative"))
            if interval < 0 or cumulative < 0 or not interval.is_integer() or not cumulative.is_integer():
                raise ValueError("conversion event counts must be nonnegative integers")
            if counter == "conversion_nonzero_return_call" and interval > 2:
                raise ValueError("RK2 conversion return-call count exceeds two per accepted update")
            counter_sums[counter] += int(interval)
            if cumulative != counter_sums[counter]:
                raise ValueError("conversion-event count accumulation differs from accepted intervals")
            if interval or cumulative:
                raise ValueError("positivity/floor or ConsToPrim failure event violates the zero-event gate")
        repair_net = state["conversion_energy_repair_net_interval_erg"]
        repair_gross = state["conversion_energy_repair_gross_interval_erg"]
        residual = {
            "mass": state["mass_g"] - previous["mass_g"] + net["mass"],
            "hydro": state["hydro_total_erg"] - previous["hydro_total_erg"] + net["hydro"] - state["gravity_work_interval_erg"] - repair_net,
            "potential": state["potential_erg"] - previous["potential_erg"] + net["potential"] + state["gravity_work_interval_erg"],
        }
        residual["total"] = residual["hydro"] + residual["potential"]
        for quantity, value in residual.items():
            unit = "g" if quantity == "mass" else "erg"
            scale = scales[quantity] if quantity != "total" else scales["hydro"] + scales["potential"]
            close(state[f"{quantity}_closure_residual_{unit}"], value, scale, "writer closure differs from independent algebra")
            maximum_fraction[quantity] = max(maximum_fraction[quantity], abs(value) / scale)
        for quantity in ("mass", "hydro"):
            work = abs(state["gravity_work_interval_erg"]) + repair_gross if quantity == "hydro" else 0.0
            tolerance = 1e-10 * scales[quantity] + 1e-6 * (gross[quantity] + work)
            if abs(residual[quantity]) > tolerance:
                raise ValueError(f"{quantity} numerical update fails predeclared closure at step {index}")
        if boundary == "reflective":
            for quantity in ("mass", "hydro"):
                if gross[quantity] > 1e-12 * scales[quantity]:
                    raise ValueError("reflective wall has nonzero numerical mass/energy transport")
    final = blocks[-1][0]
    cumulative_net = {q: sum(sums[face, q, "net"] for face in FACES) for q in QUANTITIES}
    cumulative_gross = {q: sum(sums[face, q, "positive"] - sums[face, q, "negative"] for face in FACES) for q in QUANTITIES}
    cumulative_residual = {
        "mass": final["mass_g"] - first["mass_g"] + cumulative_net["mass"],
        "hydro": final["hydro_total_erg"] - first["hydro_total_erg"] + cumulative_net["hydro"] - gravity - repair_sums["net"],
        "potential": final["potential_erg"] - first["potential_erg"] + cumulative_net["potential"] + gravity,
    }
    cumulative_residual["total"] = cumulative_residual["hydro"] + cumulative_residual["potential"]
    for q in ("mass", "hydro"):
        tolerance = 1e-10 * scales[q] + 1e-6 * (cumulative_gross[q] + (gravity_sum_abs_interval_net + repair_sums["gross"] if q == "hydro" else 0))
        if abs(cumulative_residual[q]) > tolerance:
            raise ValueError(f"cumulative {q} numerical update fails predeclared closure")
    return {"state_count": len(blocks), "accepted_updates": len(blocks) - 1, "first_state": first, "last_state": final,
            "maximum_interval_closure_over_initial": maximum_fraction, "cumulative_residual": cumulative_residual,
            "cumulative_net_transport": cumulative_net, "cumulative_gross_transport": cumulative_gross,
            "gravity_work_cumulative_erg": gravity, "gravity_work_sum_abs_interval_net_erg": gravity_sum_abs_interval_net,
            **{f"conversion_energy_repair_{part}_cumulative_erg": value for part, value in repair_sums.items()},
            "conversion_event_counts_cumulative": counter_sums,
            "conversion_counter_semantics": "flagged cell-call observations use MPI SUM; nonzero return calls use per-update MPI MAX across ranks (zero-event gate, not global failure multiplicity)",
            "conversion_repair_measure": "cellwise positive/negative/gross ENG mutations weighted by RK2 stage and exact cell volume; gross is positive minus signed negative",
            "gravity_absolute_sum_measure": "sum of absolute interval net gravity work; does not measure spatially gross gravity work",
            "conversion_event_gate": "zero positivity/floor failure-flag observations and zero nonzero ConsToPrim return calls at every state",
            "closure_gate": "mass/hydro: abs(residual) <= 1e-10 initial storage + 1e-6 gross transport/source, for every interval and cumulatively",
            "potential_closure_role": "reported discretisation residual, not an exact-conservation acceptance gate",
            "scientific_gate": "A boundary-transport claim also requires residual and true gross conversion-repair contributions materially smaller than the measured pair contrast."}


def validate(run_dir: Path, boundary: str, mode: str, output: Path) -> dict:
    ledger = run_dir / "paired_nojet_budget.csv"
    native = run_dir / "output_receipt.json"
    paths = (ledger, native, Path(__file__))
    identities = [{**_stat(p), "sha256": _hash(p)} for p in paths]
    with ledger.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    report = check_rows(rows, boundary, mode)
    inputs = json.loads(native.read_text())
    if inputs.get("status") != "validated_paired_control_run" or inputs["boundary"] != boundary or inputs["mode"] != mode:
        raise ValueError("native-field receipt does not match diagnostic treatment")
    _stable(list(inputs["input_files"].values()))
    states = [rows[index] for index in range(0, len(rows), 6)]
    matches = []
    for snapshot in inputs["snapshots"]:
        candidates = [r for r in states if abs(float(r["time_code"]) - snapshot["time_code"]) < 1e-8]
        if len(candidates) != 1:
            raise ValueError("saved native snapshot has no unique diagnostic state")
        state = candidates[0]
        for key, value in snapshot["integrated_storage"].items():
            if abs(float(state[key]) - value) > 1e-10 * max(abs(value), 1.0):
                raise ValueError(f"native-cell integration disagrees with diagnostic storage: {key}")
        matches.append({"time_code": snapshot["time_code"], "fields": sorted(snapshot["integrated_storage"])})
    _stable(identities)
    receipt = {"schema_version": 1, "status": "validated_paired_control_budget", "boundary": boundary, "mode": mode,
               "input_files": identities, "native_storage_matches": matches, **report}
    _publish(output, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--boundary", choices=("reflective", "outflow"), required=True)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate(args.run_dir, args.boundary, args.mode, args.output)


if __name__ == "__main__":
    main()
