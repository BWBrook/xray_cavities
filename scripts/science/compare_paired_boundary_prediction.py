#!/usr/bin/env python3
"""Compare validated paired no-jet ledgers with the frozen BND-02 prediction.

Each run directory must contain ``paired_nojet_budget.csv`` and its
``budget_receipt.json``. The receipt binds the ledger bytes to the prior
validator, and this script independently reruns the complete ledger validator
before comparing a pair. Numerical face transport is positive outward.

The original mass floor and mass-growth exponent criteria remain fixed. The
amended accounting criterion requires both mass and H+P inward face transport
to agree with the corresponding stored contrast to within 10% in either
direction. H alone is diagnostic because gravity transfers energy between H
and P. Gross conversion repair plus absolute numerical residual must also be
no more than 10% of the absolute H+P contrast; failure of that evidence-quality
gate is accounting-indeterminate, not a physical refutation.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from validate_paired_nojet_budget import check_rows
from validate_paired_nojet_outputs import FACES as CONFIG_FACES


PREDICTION = {
    "cluster_002003": {"mass_g": 4.86e43, "h_erg": 3.4e59, "hp_erg": 7.2e59, "floor_g": 1e43},
    "group_002031": {"mass_g": 2.38e42, "h_erg": 4.2e57, "hp_erg": 1.3e58, "floor_g": 5e41},
}
T_REF_MYR = 50.0
TRANSPORT_DISCREPANCY_MAX = 0.10
ACCOUNTING_BUDGET_MAX = 0.10
GROWTH_EXPONENT_RANGE = (1.6, 2.4)
COMPARISON_AGES_MYR = {
    "smoke": (0.0, 0.25),
    "full": (0.0, 10.0, 20.0, 30.0, 40.0, 50.0),
}
AGE_MATCH_ABS_TOL_MYR = 1e-6


class EvidenceError(ValueError):
    """The supplied files cannot support a BND-02 scientific verdict."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same(actual, recorded, label: str) -> None:
    if isinstance(actual, dict):
        if not isinstance(recorded, dict) or set(actual) != set(recorded):
            raise EvidenceError(f"receipt differs from revalidation: {label}")
        for key in actual:
            _same(actual[key], recorded[key], f"{label}.{key}")
    elif isinstance(actual, (int, float)) and isinstance(recorded, (int, float)):
        if not math.isclose(float(actual), float(recorded), rel_tol=1e-9, abs_tol=0.0):
            raise EvidenceError(f"receipt differs from revalidation: {label}")
    elif actual != recorded:
        raise EvidenceError(f"receipt differs from revalidation: {label}")


def _input_identity(receipt: dict, name: str, receipt_path: Path) -> dict:
    identities = [entry for entry in receipt.get("input_files", [])
                  if Path(entry.get("path", "")).name == name]
    if len(identities) != 1:
        raise EvidenceError(f"{receipt_path}: {name} identity is missing or ambiguous")
    return identities[0]


def load_bound_run(run_dir: Path, case: str, boundary: str) -> dict:
    ledger = run_dir / "paired_nojet_budget.csv"
    receipt_path = run_dir / "budget_receipt.json"
    output_receipt_path = run_dir / "output_receipt.json"
    if not ledger.is_file() or not receipt_path.is_file() or not output_receipt_path.is_file():
        raise EvidenceError(
            f"{run_dir}: paired_nojet_budget.csv, budget_receipt.json and output_receipt.json are required")
    try:
        receipt = json.loads(receipt_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{receipt_path}: unreadable receipt") from exc
    if receipt.get("schema_version") != 1 or receipt.get("status") != "validated_paired_control_budget":
        raise EvidenceError(f"{receipt_path}: not a validated schema-1 budget receipt")
    if receipt.get("boundary") != boundary or receipt.get("mode") not in ("smoke", "full"):
        raise EvidenceError(f"{receipt_path}: boundary or mode does not match the run")
    identity = _input_identity(receipt, ledger.name, receipt_path)
    if identity.get("size_bytes") != ledger.stat().st_size or identity.get("sha256") != _sha256(ledger):
        raise EvidenceError(f"{ledger}: bytes do not match budget_receipt.json")
    output_identity = _input_identity(receipt, output_receipt_path.name, receipt_path)
    if (output_identity.get("size_bytes") != output_receipt_path.stat().st_size
            or output_identity.get("sha256") != _sha256(output_receipt_path)):
        raise EvidenceError(f"{output_receipt_path}: bytes do not match budget_receipt.json")
    try:
        output_receipt = json.loads(output_receipt_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{output_receipt_path}: unreadable receipt") from exc
    if (output_receipt.get("schema_version") != 1
            or output_receipt.get("status") != "validated_paired_control_run"
            or output_receipt.get("case") != case
            or output_receipt.get("boundary") != boundary
            or output_receipt.get("mode") != receipt["mode"]):
        raise EvidenceError(f"{output_receipt_path}: run identity differs from the requested case")
    try:
        with ledger.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        report = check_rows(rows, boundary, receipt["mode"])
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise EvidenceError(f"{ledger}: independent ledger revalidation failed: {exc}") from exc
    for key in (
        "state_count", "accepted_updates", "cumulative_net_transport", "cumulative_gross_transport",
        "cumulative_residual", "gravity_work_cumulative_erg",
        "conversion_energy_repair_net_cumulative_erg", "conversion_energy_repair_gross_cumulative_erg",
    ):
        if key not in receipt:
            raise EvidenceError(f"{receipt_path}: missing validated accounting field {key}")
        _same(report[key], receipt[key], key)
    blocks = defaultdict(list)
    for row in rows:
        blocks[int(float(row["state_step"]))].append(row)
    return {
        "blocks": dict(blocks),
        "mode": receipt["mode"],
        "report": report,
        "output_receipt": output_receipt,
        "source_sha256": {
            "ledger": identity["sha256"],
            "budget_receipt": _sha256(receipt_path),
            "output_receipt": output_identity["sha256"],
        },
    }


def _validate_pair_identity(case: str, runs: dict) -> None:
    receipts = {boundary: run["output_receipt"] for boundary, run in runs.items()}
    reflective, outflow = (receipts[boundary] for boundary in ("reflective", "outflow"))
    try:
        for key in ("grid_geometry_hashes", "initial_field_hashes"):
            if reflective[key] != outflow[key]:
                raise EvidenceError(f"{case}: pair identity mismatch in {key}")
        for name in ("pluto", "definitions.h", "definitions_usr.h"):
            if reflective["input_files"][name]["sha256"] != outflow["input_files"][name]["sha256"]:
                raise EvidenceError(f"{case}: pair identity mismatch in {name}")
        for key in ("environment_ini", "definitions", "definitions_user"):
            if reflective["configuration"][key] != outflow["configuration"][key]:
                raise EvidenceError(f"{case}: pair configuration mismatch in {key}")
        tables = {}
        for boundary, receipt in receipts.items():
            table_name = Path(
                receipt["configuration"]["environment_ini"]["Tabulated Environment"]["TabulatedData"]
            ).name
            tables[boundary] = receipt["input_files"][table_name]["sha256"]
            if receipt["configuration"]["pluto_ini"]["Boundary"] != dict.fromkeys(CONFIG_FACES, boundary):
                raise EvidenceError(f"{case}: receipt boundary settings disagree with {boundary}")
        if tables["reflective"] != tables["outflow"]:
            raise EvidenceError(f"{case}: atmosphere table hashes differ")
        left = {key: value for key, value in reflective["configuration"]["pluto_ini"].items()
                if key != "Boundary"}
        right = {key: value for key, value in outflow["configuration"]["pluto_ini"].items()
                 if key != "Boundary"}
        if left != right:
            raise EvidenceError(f"{case}: pluto.ini differs outside the six boundary settings")
    except KeyError as exc:
        raise EvidenceError(f"{case}: output receipt lacks pair-identity field {exc}") from exc


def _state(rows: list[dict], initial: dict[str, float]) -> dict[str, float]:
    first = rows[0]
    current = {
        "state_step": int(float(first["state_step"])),
        "time_myr": float(first["time_myr"]),
        "mass": float(first["mass_g"]),
        "h": float(first["hydro_total_erg"]),
        "p": float(first["potential_erg"]),
        "in_mass": -sum(float(row["cumulative_mass_net_g"]) for row in rows),
        "in_h": -sum(float(row["cumulative_hydro_net_erg"]) for row in rows),
        "in_p": -sum(float(row["cumulative_potential_net_erg"]) for row in rows),
        "gravity": float(first["gravity_work_cumulative_erg"]),
        "repair_net": float(first["conversion_energy_repair_net_cumulative_erg"]),
        "repair_gross": float(first["conversion_energy_repair_gross_cumulative_erg"]),
    }
    current["change_mass"] = current["mass"] - initial["mass"]
    current["change_h"] = current["h"] - initial["h"]
    current["change_p"] = current["p"] - initial["p"]
    current["residual_mass"] = current["change_mass"] - current["in_mass"]
    current["residual_h"] = (current["change_h"] - current["in_h"]
                             - current["gravity"] - current["repair_net"])
    current["residual_p"] = current["change_p"] - current["in_p"] + current["gravity"]
    current["residual_hp"] = current["residual_h"] + current["residual_p"]
    return current


def _interpolate_state(states: list[dict[str, float]], target_myr: float) -> tuple[dict[str, float], dict]:
    times = [state["time_myr"] for state in states]
    for state in states:
        if math.isclose(state["time_myr"], target_myr, rel_tol=0.0, abs_tol=AGE_MATCH_ABS_TOL_MYR):
            values = {key: value for key, value in state.items() if key != "state_step"}
            values["time_myr"] = target_myr
            metadata = {
                "lower_state_step": state["state_step"],
                "upper_state_step": state["state_step"],
                "lower_time_myr": state["time_myr"],
                "upper_time_myr": state["time_myr"],
                "interpolation_fraction": 0.0,
            }
            return values, metadata
    upper_index = bisect.bisect_right(times, target_myr)
    if upper_index == 0 or upper_index == len(states):
        raise EvidenceError(f"comparison age {target_myr:g} Myr is not bracketed; extrapolation is forbidden")
    lower, upper = states[upper_index - 1], states[upper_index]
    fraction = (target_myr - lower["time_myr"]) / (upper["time_myr"] - lower["time_myr"])
    values = {
        key: lower[key] + fraction * (upper[key] - lower[key])
        for key in lower if key != "state_step"
    }
    values["time_myr"] = target_myr
    metadata = {
        "lower_state_step": lower["state_step"],
        "upper_state_step": upper["state_step"],
        "lower_time_myr": lower["time_myr"],
        "upper_time_myr": upper["time_myr"],
        "interpolation_fraction": fraction,
    }
    return values, metadata


def _ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator != 0 else None


def _relative_discrepancy(accounted: float, observed: float) -> float | None:
    if observed == 0:
        return 0.0 if accounted == 0 else None
    return abs(accounted - observed) / abs(observed)


def contrasts(root: Path, case: str) -> tuple[list[dict], str]:
    runs = {boundary: load_bound_run(root / f"{case}_{boundary}", case, boundary)
            for boundary in ("outflow", "reflective")}
    if runs["outflow"]["mode"] != runs["reflective"]["mode"]:
        raise EvidenceError(f"{case}: paired ledgers have different validation modes")
    _validate_pair_identity(case, runs)
    mode = runs["outflow"]["mode"]
    initial = {
        boundary: {key: float(runs[boundary]["blocks"][0][0][column])
                   for key, column in (("mass", "mass_g"), ("h", "hydro_total_erg"), ("p", "potential_erg"))}
        for boundary in runs
    }
    native = {
        boundary: [_state(run["blocks"][step], initial[boundary]) for step in run["blocks"]]
        for boundary, run in runs.items()
    }
    pred = PREDICTION[case]
    output = []
    for t in COMPARISON_AGES_MYR[mode][1:]:
        aligned = {boundary: _interpolate_state(native[boundary], t) for boundary in runs}
        now = {boundary: values for boundary, (values, _) in aligned.items()}
        delta = {key: now["outflow"][key] - now["reflective"][key]
                 for key in ("change_mass", "change_h", "change_p", "in_mass", "in_h", "in_p",
                             "gravity", "repair_net", "residual_mass", "residual_h", "residual_p", "residual_hp")}
        contrast_hp = delta["change_h"] + delta["change_p"]
        inward_hp = delta["in_h"] + delta["in_p"]
        combined_repair_gross = now["outflow"]["repair_gross"] + now["reflective"]["repair_gross"]
        combined_abs_total_residual = (abs(now["outflow"]["residual_hp"])
                                       + abs(now["reflective"]["residual_hp"]))
        scale = (t / T_REF_MYR) ** 2
        output.append({
            "case": case,
            "time_myr": t,
            **{f"{boundary}_{name}_sha256": digest
               for boundary, run in runs.items() for name, digest in run["source_sha256"].items()},
            **{f"{boundary}_{key}": value
               for boundary, (_, metadata) in aligned.items() for key, value in metadata.items()},
            "contrast_mass_g": delta["change_mass"],
            "contrast_h_erg": delta["change_h"],
            "contrast_p_erg": delta["change_p"],
            "contrast_hp_erg": contrast_hp,
            "inward_face_mass_contrast_g": delta["in_mass"],
            "inward_face_h_contrast_erg": delta["in_h"],
            "inward_face_p_contrast_erg": delta["in_p"],
            "inward_face_hp_contrast_erg": inward_hp,
            "paired_gravity_work_contrast_erg": delta["gravity"],
            "paired_repair_net_contrast_erg": delta["repair_net"],
            "paired_repair_gross_combined_erg": combined_repair_gross,
            "paired_total_residual_contrast_erg": delta["residual_hp"],
            "paired_total_residual_abs_combined_erg": combined_abs_total_residual,
            "transport_explains_mass": _ratio(delta["in_mass"], delta["change_mass"]),
            "transport_explains_h": _ratio(delta["in_h"], delta["change_h"]),
            "transport_explains_hp": _ratio(inward_hp, contrast_hp),
            "h_with_gravity_repair_explains": _ratio(
                delta["in_h"] + delta["gravity"] + delta["repair_net"], delta["change_h"]),
            "mass_transport_discrepancy_fraction": _relative_discrepancy(
                delta["in_mass"], delta["change_mass"]),
            "hp_transport_discrepancy_fraction": _relative_discrepancy(inward_hp, contrast_hp),
            "repair_residual_budget_fraction": _ratio(
                combined_repair_gross + combined_abs_total_residual, abs(contrast_hp)),
            "mass_over_t2_prediction": delta["change_mass"] / (pred["mass_g"] * scale),
            "h_over_t2_prediction": delta["change_h"] / (pred["h_erg"] * scale),
            "hp_over_t2_prediction": contrast_hp / (pred["hp_erg"] * scale),
        })
    return output, mode


def growth_exponent(rows: list[dict]) -> tuple[float | None, str | None]:
    eligible = [row for row in rows if row["time_myr"] >= 5.0]
    if any(row["contrast_mass_g"] <= 0 for row in eligible):
        return None, "nonpositive mass contrast at t >= 5 Myr"
    if len(eligible) < 2:
        return None, "fewer than two mass contrasts at t >= 5 Myr"
    points = [(math.log(row["time_myr"]), math.log(row["contrast_mass_g"])) for row in eligible]
    mean_x = sum(x for x, _ in points) / len(points)
    mean_y = sum(y for _, y in points) / len(points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        return None, "mass-growth times do not identify an exponent"
    exponent = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    return exponent, None


def verdict(case: str, rows: list[dict], mode: str) -> dict:
    if not rows:
        raise EvidenceError(f"{case}: no post-initial states")
    final = rows[-1]
    exponent, growth_issue = growth_exponent(rows)
    ratios = (final["mass_over_t2_prediction"], final["hp_over_t2_prediction"])
    result = {
        "case": case,
        "final_time_myr": final["time_myr"],
        "complete_to_50_myr": mode == "full" and math.isclose(
            final["time_myr"], T_REF_MYR, rel_tol=0.0, abs_tol=1e-6),
        "growth_exponent_t_ge_5myr": exponent,
        "growth_information_issue": growth_issue,
        "final_mass_ratio": ratios[0],
        "final_hp_ratio": ratios[1],
        "within_factor_2": all(0.5 <= ratio <= 2.0 for ratio in ratios),
        "within_30_percent": all(1 / 1.3 <= ratio <= 1.3 for ratio in ratios),
        "mass_transport_discrepancy_fraction": final["mass_transport_discrepancy_fraction"],
        "hp_transport_discrepancy_fraction": final["hp_transport_discrepancy_fraction"],
        "repair_residual_budget_fraction": final["repair_residual_budget_fraction"],
        "h_face_only_fraction_diagnostic": final["transport_explains_h"],
        "h_with_gravity_repair_fraction_diagnostic": final["h_with_gravity_repair_explains"],
        "physical_refutations": [],
        "accounting_indeterminacies": [],
        "original_one_sided_transport_flags": [],
    }
    if not result["complete_to_50_myr"]:
        result["verdict"] = "incomplete"
        return result
    for quantity in ("mass", "h"):
        ratio = final[f"transport_explains_{quantity}"]
        if ratio is None or ratio < 0.9:
            result["original_one_sided_transport_flags"].append(
                f"original {quantity} face-transport fraction below 0.9 or undefined")
    if growth_issue:
        result["verdict"] = "scientifically_indeterminate"
        return result
    if final["contrast_mass_g"] < PREDICTION[case]["floor_g"]:
        result["physical_refutations"].append("final mass contrast below frozen floor")
    lower, upper = GROWTH_EXPONENT_RANGE
    if not lower <= exponent <= upper:
        result["physical_refutations"].append(f"growth exponent {exponent:.2f} outside [{lower}, {upper}]")
    mass_discrepancy = final["mass_transport_discrepancy_fraction"]
    if mass_discrepancy is None:
        result["accounting_indeterminacies"].append("mass transport discrepancy is undefined")
    elif mass_discrepancy > TRANSPORT_DISCREPANCY_MAX:
        result["physical_refutations"].append(
            f"mass face-transport discrepancy exceeds {TRANSPORT_DISCREPANCY_MAX:.0%}")
    budget = final["repair_residual_budget_fraction"]
    if budget is None:
        result["accounting_indeterminacies"].append("repair/residual budget is undefined")
    elif budget > ACCOUNTING_BUDGET_MAX:
        result["accounting_indeterminacies"].append(
            f"gross repair plus numerical residual exceeds {ACCOUNTING_BUDGET_MAX:.0%} of |H+P contrast|")
    hp_discrepancy = final["hp_transport_discrepancy_fraction"]
    if hp_discrepancy is None:
        result["accounting_indeterminacies"].append("hp transport discrepancy is undefined")
    elif (budget is not None and budget <= ACCOUNTING_BUDGET_MAX
          and hp_discrepancy > TRANSPORT_DISCREPANCY_MAX):
        result["physical_refutations"].append(
            f"hp face-transport discrepancy exceeds {TRANSPORT_DISCREPANCY_MAX:.0%}")
    if result["accounting_indeterminacies"]:
        result["verdict"] = "accounting_indeterminate"
    elif result["physical_refutations"]:
        result["verdict"] = "refuted"
    else:
        result["verdict"] = "supported"
    return result


def write_outputs(output: Path, rows: list[dict], verdicts: list[dict]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    with (output / "paired_contrasts.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    payload = json.dumps(verdicts, indent=2, allow_nan=False) + "\n"
    (output / "verdict.json").write_text(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="directory holding the four validated paired run directories")
    parser.add_argument("output", type=Path, help="new output directory; existing paths are refused")
    args = parser.parse_args()
    all_rows, verdicts = [], []
    for case in PREDICTION:
        case_rows, mode = contrasts(args.root, case)
        all_rows.extend(case_rows)
        verdicts.append(verdict(case, case_rows, mode))
    write_outputs(args.output, all_rows, verdicts)
    print(json.dumps(verdicts, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
