import copy
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/science"))
spec = importlib.util.spec_from_file_location("paired_budget", ROOT / "scripts/science/validate_paired_nojet_budget.py")
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


def ledger(boundary="outflow", repair_per_step=0.0, cancelling_repair_per_step=0.0):
    result = []
    for index in range(11):
        incoming = 0.0 if boundary == "reflective" else 2.0
        state = {
            "state_step": index, "completed_step": index - 1,
            "time_code": index * .025 * 306.601393788, "time_myr": index * .025,
            "interval_dt_code": .025 * 306.601393788 if index else 0,
            "mass_g": 1000 + index * incoming,
            "hydro_total_erg": 2000 + index * (2 * incoming + repair_per_step),
            "thermal_erg": 2000 + index * (2 * incoming + repair_per_step),
            "kinetic_erg": 0.0, "potential_erg": 3000 + index * 3 * incoming,
            "conserved_minus_primitive_hydro_erg": 0.0,
            "gravity_work_interval_erg": 0.0, "gravity_work_cumulative_erg": 0.0,
            "mass_closure_residual_g": 0.0, "hydro_closure_residual_erg": 0.0,
            "potential_closure_residual_erg": 0.0, "total_closure_residual_erg": 0.0,
        }
        repairs = {"net": repair_per_step,
                   "positive": max(repair_per_step, 0.) + cancelling_repair_per_step,
                   "negative": min(repair_per_step, 0.) - cancelling_repair_per_step,
                   "gross": abs(repair_per_step) + 2 * cancelling_repair_per_step}
        for part, value in repairs.items():
            state[f"conversion_energy_repair_{part}_interval_erg"] = value if index else 0.
            state[f"conversion_energy_repair_{part}_cumulative_erg"] = value * index
        for counter in budget.CONVERSION_COUNTERS:
            state[f"{counter}_interval_count"] = 0
            state[f"{counter}_cumulative_count"] = 0
        for face in budget.FACES:
            row = {**state, "face": face, "boundary_type_code": 2 if boundary == "reflective" else 1,
                   "minimum_outward_normal_velocity_km_s": 0.0, "maximum_outward_normal_velocity_km_s": 0.0}
            for (quantity, unit), multiplier in zip(budget.QUANTITIES.items(), (1, 2, 3)):
                interval = -incoming * multiplier if face == budget.FACES[0] and index else 0.0
                cumulative = -incoming * multiplier * index if face == budget.FACES[0] else 0.0
                for part in budget.PARTS:
                    row[f"actual_{quantity}_{part}_{unit}"] = interval if part != "positive" else 0.0
                    row[f"cumulative_{quantity}_{part}_{unit}"] = cumulative if part != "positive" else 0.0
                row[f"reconstructed_{quantity}_rate_{unit}_s"] = 0.0
                row[f"reconstructed_{quantity}_interval_{unit}"] = 0.0
            result.append({k: str(v) for k, v in row.items()})
    return result


@pytest.mark.parametrize("boundary", ["reflective", "outflow"])
def test_exact_manufactured_storage_flux_and_separate_repair(boundary):
    report = budget.check_rows(ledger(boundary, repair_per_step=.5), boundary, "smoke")
    assert report["accepted_updates"] == 10
    assert report["cumulative_residual"]["hydro"] == 0
    assert report["conversion_energy_repair_net_cumulative_erg"] == 5
    assert report["conversion_energy_repair_gross_cumulative_erg"] == 5
    assert report["cumulative_net_transport"]["mass"] == (0 if boundary == "reflective" else -20)


def test_signed_gross_transport_exposes_reflective_cancellation():
    rows = ledger("reflective")
    for index in range(1, 11):
        row = rows[index * 6]
        row["actual_mass_positive_g"] = "1"
        row["actual_mass_negative_g"] = "-1"
        row["cumulative_mass_positive_g"] = str(index)
        row["cumulative_mass_negative_g"] = str(-index)
    with pytest.raises(ValueError, match="reflective wall"):
        budget.check_rows(rows, "reflective", "smoke")


@pytest.mark.parametrize("field,value,error", [
    ("boundary_type_code", "2", "dispatch"),
    ("mass_g", "nan", "non-finite"),
    ("state_step", "12", "gap or duplicate"),
    ("cumulative_hydro_negative_erg", "-999", "cumulative transport"),
    ("actual_mass_positive_g", "-1", "signs"),
])
def test_ledger_corruption_fails_closed(field, value, error):
    rows = ledger()
    rows[6][field] = value
    with pytest.raises(ValueError, match=error):
        budget.check_rows(rows, "outflow", "smoke")


def test_internally_consistent_writer_cannot_hide_failed_numerical_closure():
    rows = ledger()
    for row in rows[-6:]:
        row["mass_g"] = str(float(row["mass_g"]) + 1)
        row["mass_closure_residual_g"] = "1"
    with pytest.raises(ValueError, match="predeclared closure"):
        budget.check_rows(rows, "outflow", "smoke")


def test_potential_discretisation_error_is_reported_not_silently_forced_to_zero():
    rows = ledger()
    for row in rows[-6:]:
        row["potential_erg"] = str(float(row["potential_erg"]) + .2)
        row["potential_closure_residual_erg"] = ".2"
        row["total_closure_residual_erg"] = ".2"
    report = budget.check_rows(rows, "outflow", "smoke")
    assert report["cumulative_residual"]["total"] == pytest.approx(.2)


def test_incomplete_final_state_cannot_pass():
    with pytest.raises(ValueError, match="six faces"):
        budget.check_rows(ledger()[:-1], "outflow", "smoke")


def test_missing_or_altered_primitive_energy_difference_is_rejected():
    rows = copy.deepcopy(ledger())
    for row in rows[-6:]:
        row["conserved_minus_primitive_hydro_erg"] = "1"
    with pytest.raises(ValueError, match="conserved/primitive"):
        budget.check_rows(rows, "outflow", "smoke")


def test_cancelling_cellwise_repairs_retain_true_gross_despite_zero_net():
    report = budget.check_rows(ledger(cancelling_repair_per_step=100.), "outflow", "smoke")
    assert report["conversion_energy_repair_net_cumulative_erg"] == 0
    assert report["conversion_energy_repair_positive_cumulative_erg"] == 1000
    assert report["conversion_energy_repair_negative_cumulative_erg"] == -1000
    assert report["conversion_energy_repair_gross_cumulative_erg"] == 2000
    assert report["cumulative_residual"]["hydro"] == 0
    assert "gravity_work_gross_erg" not in report
    assert report["gravity_work_sum_abs_interval_net_erg"] == 0


def test_net_only_gross_cannot_hide_cancelling_repairs():
    rows = ledger(cancelling_repair_per_step=100.)
    for row in rows[6:]:
        row["conversion_energy_repair_gross_interval_erg"] = "0"
        row["conversion_energy_repair_gross_cumulative_erg"] = "0"
    with pytest.raises(ValueError, match="gross differs"):
        budget.check_rows(rows, "outflow", "smoke")


def test_signed_conversion_repair_and_cumulative_parts_are_independently_checked():
    rows = ledger(cancelling_repair_per_step=2.)
    for row in rows[-6:]:
        row["conversion_energy_repair_net_interval_erg"] = "1"
    with pytest.raises(ValueError, match="signed conversion repair"):
        budget.check_rows(rows, "outflow", "smoke")
    rows = ledger(cancelling_repair_per_step=2.)
    for row in rows[-6:]:
        row["conversion_energy_repair_positive_cumulative_erg"] = "21"
        row["conversion_energy_repair_negative_cumulative_erg"] = "-21"
        row["conversion_energy_repair_gross_cumulative_erg"] = "42"
    with pytest.raises(ValueError, match="accumulation differs"):
        budget.check_rows(rows, "outflow", "smoke")


@pytest.mark.parametrize("counter", budget.CONVERSION_COUNTERS)
def test_any_floor_or_conversion_failure_event_fails_even_with_exact_energy_closure(counter):
    rows = ledger()
    for index in range(1, 11):
        for row in rows[index * 6:(index + 1) * 6]:
            row[f"{counter}_interval_count"] = "1" if index == 1 else "0"
            row[f"{counter}_cumulative_count"] = "1"
    with pytest.raises(ValueError, match="zero-event gate"):
        budget.check_rows(rows, "outflow", "smoke")


@pytest.mark.parametrize("field", ["gravity_work_interval_erg", "gravity_work_cumulative_erg",
                                  *budget.REPAIR_COLUMNS, *budget.COUNTER_COLUMNS])
def test_zero_time_must_have_no_source_repair_or_failure_counts(field):
    rows = ledger()
    for row in rows[:6]:
        row[field] = "1"
    with pytest.raises(ValueError, match="zero-time state contains a source"):
        budget.check_rows(rows, "outflow", "smoke")


@pytest.mark.parametrize("value,pattern", [("-1", "nonnegative integers"), ("0.5", "nonnegative integers"),
                                         ("3", "exceeds two")])
def test_event_counts_are_valid_raw_rk2_counts(value, pattern):
    rows = ledger()
    for row in rows[6:12]:
        row["conversion_nonzero_return_call_interval_count"] = value
        row["conversion_nonzero_return_call_cumulative_count"] = value
    with pytest.raises(ValueError, match=pattern):
        budget.check_rows(rows, "outflow", "smoke")


def test_failure_count_cumulative_cannot_disagree_with_interval_counts():
    rows = ledger()
    for row in rows[-6:]:
        row["conversion_failure_flagged_cell_observations_cumulative_count"] = "1"
    with pytest.raises(ValueError, match="count accumulation"):
        budget.check_rows(rows, "outflow", "smoke")


def test_conversion_repair_signed_parts_have_required_signs():
    rows = ledger()
    for row in rows[-6:]:
        row["conversion_energy_repair_positive_interval_erg"] = "-1"
    with pytest.raises(ValueError, match="repair signs"):
        budget.check_rows(rows, "outflow", "smoke")
