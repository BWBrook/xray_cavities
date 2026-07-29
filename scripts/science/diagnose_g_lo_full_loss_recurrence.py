#!/usr/bin/env python3
"""Stable Goal 050 reference for the RAiSE II full-loss recurrence.

The pinned PRAiSE implementation materializes absolute-time powers in both
``a2`` and the gamma denominator.  This module keeps the same real-arithmetic
equations but evaluates the dimensionless scaled loss coefficient and gamma
denominator in log space.  It is diagnostic-only and does not alter
``plutokore`` defaults.
"""

from __future__ import annotations

import math
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import mpmath
import numpy as np

from plutokore.radio.praise import get_c1
from scripts.science import diagnose_g_lo_adiabatic_recovery as recovery
from scripts.science import run_g_lo_radio_history_value as workflow


HP_DPS = 80
C1 = float(get_c1())
GAMMA_INF = 1.0e50
STATE_FINITE = "finite"
STATE_PHYSICAL_CUTOFF = "physical_cutoff"
STATE_GAMMA_INF_CUTOFF = "gamma_inf_cutoff"
STATE_SUBRELATIVISTIC = "subrelativistic"
STATE_POST_CUTOFF = "post_cutoff"

PASS_LABEL = "G_LO_STABLE_FULL_LOSS_RECURRENCE_GREEN_4096_COMPARISON_JUSTIFIED"
FAIL_LABEL = "G_LO_RADIO_METHOD_BLOCKED_STABLE_FULL_LOSS_GATE_FAILED"

FULL_LOSS_GATE_NAMES = (
    "analytic_limits",
    "finite_scaled_loss",
    "high_precision_scaled_loss",
    "high_precision_gamma",
    "exact_state_classification",
    "boundary_conditioning",
    "zero_silent_fallbacks",
    "no_subrelativistic_states",
    "finite_or_explicit_cutoff_emissivity",
    "deterministic_repeat",
    "pinned_failure_reproduction",
)
FREQUENCIES_GHZ = (0.15, 1.4)
TRACE_LIMIT = 64
STABLE_RTOL = 1.0e-10
STABLE_ATOL = 1.0e-12
EXPECTED_RELEVANT_NONFINITE_A2 = 22737
EXPECTED_PINNED_GAMMA_FALLBACKS = 45474


class FullLossDiagnosticError(RuntimeError):
    """Raised when the stable full-loss contract cannot be evaluated."""


def _scalar_or_array(original: Any, value: np.ndarray) -> Any:
    return float(value) if np.ndim(original) == 0 else value


def log_exprel(value: Any) -> Any:
    """Return ``log(expm1(x) / x)`` with its removable zero limit."""
    original = value
    x = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(x)):
        raise FullLossDiagnosticError("log_exprel requires finite inputs")
    result = np.empty_like(x)
    near = np.abs(x) <= 1.0e-5
    positive = x > 50.0
    negative = x < -50.0
    ordinary = ~(near | positive | negative)
    xn = x[near]
    result[near] = xn / 2.0 + xn**2 / 24.0 - xn**4 / 2880.0
    xp = x[positive]
    result[positive] = xp + np.log1p(-np.exp(-xp)) - np.log(xp)
    xm = x[negative]
    result[negative] = np.log(-np.expm1(xm)) - np.log(-xm)
    xo = x[ordinary]
    result[ordinary] = np.log(np.expm1(xo) / xo)
    return _scalar_or_array(original, result)


def magnetic_energy_density(eta: float, pressure: float, gamma_c: float) -> float:
    """Pinned PRAiSE magnetic energy density in SI numeric units."""
    eta_f = float(eta)
    pressure_f = float(pressure)
    gamma_f = float(gamma_c)
    if (
        not np.isfinite(eta_f)
        or eta_f < 0
        or not np.isfinite(pressure_f)
        or pressure_f <= 0
        or not np.isfinite(gamma_f)
        or gamma_f <= 1
    ):
        raise FullLossDiagnosticError(
            "magnetic energy density requires eta >= 0, pressure > 0, and gamma_c > 1"
        )
    return eta_f * pressure_f / ((gamma_f - 1.0) * (eta_f + 1.0))


def cmb_energy_density(z: float) -> float:
    """Pinned PRAiSE CMB energy density in SI numeric units."""
    z_f = float(z)
    if not np.isfinite(z_f) or z_f <= -1:
        raise FullLossDiagnosticError("redshift must be finite and greater than -1")
    return 4.005e-14 * (1.0 + z_f) ** 4


def _interval_terms(
    *,
    t0: float,
    t1: float,
    p0: float,
    p1: float,
    gamma_c: float,
) -> dict[str, float]:
    values = np.asarray([t0, t1, p0, p1, gamma_c], dtype=float)
    if np.any(~np.isfinite(values)):
        raise FullLossDiagnosticError("full-loss interval inputs must be finite")
    if t0 <= 0 or t1 <= t0:
        raise FullLossDiagnosticError("full-loss interval requires t1 > t0 > 0")
    if p0 <= 0 or p1 <= 0:
        raise FullLossDiagnosticError("full-loss interval requires positive pressure")
    if gamma_c <= 1:
        raise FullLossDiagnosticError("full-loss interval requires gamma_c > 1")
    interval = (t1 - t0) / t0
    pressure_change = (p1 - p0) / p0
    log_time_ratio = float(np.log1p(interval))
    log_pressure_ratio = float(np.log1p(pressure_change))
    ap = log_pressure_ratio / log_time_ratio
    exponent = ap / (3.0 * gamma_c)
    exponent_interval = log_pressure_ratio / (3.0 * gamma_c)
    return {
        "log_time_ratio": log_time_ratio,
        "log_pressure_ratio": log_pressure_ratio,
        "ap": ap,
        "exponent": exponent,
        "exponent_interval": exponent_interval,
        "a3": 1.0 + ap + exponent,
        "a4": 1.0 + exponent,
        "a3_argument": log_time_ratio + log_pressure_ratio + exponent_interval,
        "a4_argument": log_time_ratio + exponent_interval,
    }


def stable_scaled_loss(
    *,
    t0: float,
    t1: float,
    p0: float,
    p1: float,
    gamma_c: float,
    eta: float,
    z: float,
) -> dict[str, float]:
    """Evaluate ``lambda = a2 / t1**b`` without absolute-time powers."""
    terms = _interval_terms(t0=t0, t1=t1, p0=p0, p1=p1, gamma_c=gamma_c)
    ub = magnetic_energy_density(eta, p0, gamma_c)
    uc = cmb_energy_density(z)
    log_ub_term = (
        -np.inf
        if ub == 0
        else math.log(ub) + float(log_exprel(terms["a3_argument"]))
    )
    log_uc_term = math.log(uc) + float(log_exprel(terms["a4_argument"]))
    log_lambda = (
        math.log(C1)
        + math.log(t0)
        - terms["exponent_interval"]
        + math.log(terms["log_time_ratio"])
        + float(np.logaddexp(log_ub_term, log_uc_term))
    )
    log_raw_a2 = log_lambda + terms["exponent"] * math.log(t1)
    if not np.isfinite(log_lambda) or not np.isfinite(log_raw_a2):
        raise FullLossDiagnosticError(
            "scaled full-loss representation is non-finite"
        )
    return {
        **terms,
        "magnetic_energy_density": ub,
        "cmb_energy_density": uc,
        "log_lambda": float(log_lambda),
        "log_raw_a2": float(log_raw_a2),
    }


def high_precision_scaled_loss(
    *,
    t0: float,
    t1: float,
    p0: float,
    p1: float,
    gamma_c: float,
    eta: float,
    z: float,
) -> dict[str, Any]:
    """Independent 80-digit evaluation of pinned equation A11."""
    _interval_terms(t0=t0, t1=t1, p0=p0, p1=p1, gamma_c=gamma_c)
    with mpmath.workdps(HP_DPS):
        mt0, mt1 = mpmath.mpf(str(t0)), mpmath.mpf(str(t1))
        mp0, mp1 = mpmath.mpf(str(p0)), mpmath.mpf(str(p1))
        mgc = mpmath.mpf(str(gamma_c))
        meta, mz = mpmath.mpf(str(eta)), mpmath.mpf(str(z))
        log_ratio = mpmath.log(mt1 / mt0)
        ap = mpmath.log(mp1 / mp0) / log_ratio
        exponent = ap / (3 * mgc)
        a3 = 1 + ap + exponent
        a4 = 1 + exponent
        ub = meta * mp0 / ((mgc - 1) * (meta + 1))
        uc = mpmath.mpf("4.005e-14") * (1 + mz) ** 4
        if a3 == 0:
            magnetic = ub * mt0 ** (-ap) * log_ratio
        else:
            magnetic = (
                ub / a3 * mt0 ** (-ap) * (mt1**a3 - mt0**a3)
            )
        if a4 == 0:
            cmb = uc * log_ratio
        else:
            cmb = uc / a4 * (mt1**a4 - mt0**a4)
        raw_a2 = mpmath.mpf(str(C1)) * (magnetic + cmb)
        scaled = raw_a2 / mt1**exponent
        return {
            "lambda": scaled,
            "log_lambda": mpmath.log(scaled),
            "raw_a2": raw_a2,
            "log_raw_a2": mpmath.log(raw_a2),
            "ap": ap,
            "exponent": exponent,
        }


def run_analytic_self_checks() -> dict[str, Any]:
    """Execute the analytic-limit checks used by the scientific gate."""
    checks: list[dict[str, Any]] = []

    t0, t1 = 2.0e15, 2.1e15
    pressure = 3.0e-12
    gamma_c = 5.0 / 3.0
    constant = stable_scaled_loss(
        t0=t0,
        t1=t1,
        p0=pressure,
        p1=pressure,
        gamma_c=gamma_c,
        eta=0.03,
        z=0.05,
    )
    constant_value = math.exp(constant["log_lambda"])
    constant_reference = C1 * (t1 - t0) * (
        magnetic_energy_density(0.03, pressure, gamma_c)
        + cmb_energy_density(0.05)
    )
    checks.append(
        {
            "check": "constant_pressure_closed_form",
            "passed": bool(
                math.isclose(
                    constant_value,
                    constant_reference,
                    rel_tol=2.0e-14,
                    abs_tol=0.0,
                )
            ),
            "log_value": constant["log_lambda"],
            "log_reference": math.log(constant_reference),
        }
    )

    for name, ap in (("a3_zero_limit", -5.0 / 6.0), ("a4_zero_limit", -5.0)):
        limit_t0, limit_t1 = 1.0e15, 1.1e15
        limit_p0 = 2.0e-12
        limit_p1 = limit_p0 * (limit_t1 / limit_t0) ** ap
        stable = stable_scaled_loss(
            t0=limit_t0,
            t1=limit_t1,
            p0=limit_p0,
            p1=limit_p1,
            gamma_c=gamma_c,
            eta=0.03,
            z=0.05,
        )
        reference = high_precision_scaled_loss(
            t0=limit_t0,
            t1=limit_t1,
            p0=limit_p0,
            p1=limit_p1,
            gamma_c=gamma_c,
            eta=0.03,
            z=0.05,
        )
        log_reference = float(reference["log_lambda"])
        checks.append(
            {
                "check": name,
                "passed": bool(
                    abs(stable["log_lambda"] - log_reference) <= 2.0e-12
                ),
                "log_value": stable["log_lambda"],
                "log_reference": log_reference,
            }
        )

    overflow = stable_scaled_loss(
        t0=1.0e15,
        t1=1.01e15,
        p0=1.0e-12,
        p1=1.0e-12 * (1.01**36000.0),
        gamma_c=gamma_c,
        eta=0.03,
        z=0.05,
    )
    checks.append(
        {
            "check": "overflow_scaled_loss",
            "passed": bool(
                np.isfinite(overflow["log_lambda"])
                and overflow["log_raw_a2"] > math.log(np.finfo(float).max)
            ),
            "log_value": overflow["log_lambda"],
            "log_raw_a2": overflow["log_raw_a2"],
        }
    )
    return {
        "passed": bool(checks and all(row["passed"] for row in checks)),
        "checks": checks,
    }


def stable_full_loss_interval(
    *,
    gamma_later: float,
    t0: float,
    t1: float,
    p0: float,
    p1: float,
    gamma_c: float,
    eta: float,
    z: float,
    gamma_inf: float = GAMMA_INF,
) -> dict[str, Any]:
    """Evaluate one backward full-loss update with explicit state semantics."""
    gamma = float(gamma_later)
    if not np.isfinite(gamma) or gamma <= 0:
        raise FullLossDiagnosticError("later gamma must be finite and positive")
    if not np.isfinite(gamma_inf) or gamma_inf <= 1:
        raise FullLossDiagnosticError("gamma_inf must be finite and greater than one")
    loss = stable_scaled_loss(
        t0=t0, t1=t1, p0=p0, p1=p1, gamma_c=gamma_c, eta=eta, z=z
    )
    log_gamma = math.log(gamma)
    log_y = math.fsum((log_gamma, loss["log_lambda"]))
    pole_tolerance = 8.0 * np.finfo(float).eps * max(
        1.0, abs(log_gamma), abs(loss["log_lambda"])
    )
    if abs(log_y) <= pole_tolerance:
        loss_fraction = gamma * math.exp(loss["log_lambda"])
        cutoff = loss_fraction >= 1.0
    else:
        loss_fraction = math.exp(log_y) if log_y > -745.0 else 0.0
        cutoff = log_y >= 0.0
    result = {
        **loss,
        "log_loss_fraction": log_y,
        "loss_fraction": loss_fraction,
        "pole_tolerance": pole_tolerance,
    }
    if cutoff:
        return {
            **result,
            "classification": STATE_PHYSICAL_CUTOFF,
            "gamma_earlier": math.nan,
            "log_denominator": -math.inf,
        }
    log_denominator = (
        math.log1p(-loss_fraction)
        if abs(log_y) <= pole_tolerance
        else math.log(-math.expm1(log_y))
    )
    log_gamma = (
        math.log(gamma)
        - loss["exponent_interval"]
        - log_denominator
    )
    if log_gamma >= math.log(gamma_inf):
        classification = STATE_GAMMA_INF_CUTOFF
        gamma_earlier = math.nan
    elif log_gamma < 0:
        classification = STATE_SUBRELATIVISTIC
        gamma_earlier = math.exp(log_gamma)
    else:
        classification = STATE_FINITE
        gamma_earlier = math.exp(log_gamma)
    return {
        **result,
        "classification": classification,
        "gamma_earlier": gamma_earlier,
        "log_gamma_earlier": log_gamma,
        "log_denominator": log_denominator,
    }


def high_precision_full_loss_interval(
    *,
    gamma_later: float,
    t0: float,
    t1: float,
    p0: float,
    p1: float,
    gamma_c: float,
    eta: float,
    z: float,
    gamma_inf: float = GAMMA_INF,
) -> dict[str, Any]:
    """Independent high-precision equation A10 update."""
    reference = high_precision_scaled_loss(
        t0=t0, t1=t1, p0=p0, p1=p1, gamma_c=gamma_c, eta=eta, z=z
    )
    with mpmath.workdps(HP_DPS):
        gamma = mpmath.mpf(str(gamma_later))
        exponent = reference["exponent"]
        time_ratio = mpmath.mpf(str(t1)) / mpmath.mpf(str(t0))
        loss_fraction = gamma * reference["lambda"]
        if loss_fraction >= 1:
            return {
                **reference,
                "classification": STATE_PHYSICAL_CUTOFF,
                "gamma_earlier": mpmath.nan,
            }
        earlier = gamma * time_ratio ** (-exponent) / (1 - loss_fraction)
        if earlier >= mpmath.mpf(str(gamma_inf)):
            classification = STATE_GAMMA_INF_CUTOFF
            earlier = mpmath.nan
        elif earlier < 1:
            classification = STATE_SUBRELATIVISTIC
        else:
            classification = STATE_FINITE
        return {
            **reference,
            "classification": classification,
            "gamma_earlier": earlier,
        }


def stable_full_loss_trajectory(
    endpoint_gamma: Any,
    times: Any,
    pressure: Any,
    gamma_c: Any,
    shock_index: Any,
    *,
    eta: float,
    z: float,
    gamma_inf: float = GAMMA_INF,
) -> dict[str, Any]:
    """Walk endpoint gamma back to each assigned shock without fallback."""
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    times_a = np.asarray(times, dtype=float)
    pressure_a = np.asarray(pressure, dtype=float)
    gamma_c_a = np.asarray(gamma_c, dtype=float)
    shocks = np.asarray(shock_index, dtype=int)
    if endpoint.ndim != 2 or times_a.ndim != 1:
        raise FullLossDiagnosticError("trajectory endpoint/time shapes are invalid")
    n, nf = endpoint.shape
    if (
        pressure_a.shape != (n, times_a.size)
        or gamma_c_a.shape != pressure_a.shape
        or shocks.shape != (n,)
    ):
        raise FullLossDiagnosticError("trajectory history shapes are incompatible")
    if np.any(shocks < 0) or np.any(shocks >= times_a.size):
        raise FullLossDiagnosticError("shock indices are outside the trajectory")
    trajectory = np.full((n, times_a.size, nf), np.nan, dtype=float)
    state = np.full(
        (n, times_a.size, nf), STATE_POST_CUTOFF, dtype="<U32"
    )
    trajectory[:, -1, :] = endpoint
    state[:, -1, :] = STATE_FINITE
    cutoff_count = 0
    subrelativistic_count = 0
    for row in range(n):
        for frequency in range(nf):
            for interval in range(times_a.size - 2, -1, -1):
                if interval < shocks[row]:
                    state[row, interval, frequency] = STATE_POST_CUTOFF
                    continue
                if state[row, interval + 1, frequency] != STATE_FINITE:
                    state[row, interval, frequency] = STATE_POST_CUTOFF
                    continue
                result = stable_full_loss_interval(
                    gamma_later=trajectory[row, interval + 1, frequency],
                    t0=times_a[interval],
                    t1=times_a[interval + 1],
                    p0=pressure_a[row, interval],
                    p1=pressure_a[row, interval + 1],
                    gamma_c=gamma_c_a[row, interval],
                    eta=eta,
                    z=z,
                    gamma_inf=gamma_inf,
                )
                classification = str(result["classification"])
                state[row, interval, frequency] = classification
                trajectory[row, interval, frequency] = float(
                    result["gamma_earlier"]
                )
                if interval >= shocks[row]:
                    cutoff_count += int(
                        classification
                        in (STATE_PHYSICAL_CUTOFF, STATE_GAMMA_INF_CUTOFF)
                    )
                    subrelativistic_count += int(
                        classification == STATE_SUBRELATIVISTIC
                    )
    return {
        "trajectory": trajectory,
        "state": state,
        "physical_cutoff_count": cutoff_count,
        "subrelativistic_count": subrelativistic_count,
        "silent_fallback_count": 0,
    }


def interval_boundary_stability(**kwargs: Any) -> dict[str, Any]:
    """Check one-ULP input perturbations for state-classification stability."""
    numeric_names = (
        "gamma_later", "t0", "t1", "p0", "p1", "gamma_c"
    )
    classifications: list[str] = []
    base = {key: float(value) if key in numeric_names else value for key, value in kwargs.items()}
    candidates = [base]
    for name in numeric_names:
        for direction in (-math.inf, math.inf):
            current = dict(base)
            current[name] = float(np.nextafter(current[name], direction))
            candidates.append(current)
    loss = stable_scaled_loss(
        t0=base["t0"],
        t1=base["t1"],
        p0=base["p0"],
        p1=base["p1"],
        gamma_c=base["gamma_c"],
        eta=base["eta"],
        z=base["z"],
    )
    pole_gamma = math.exp(-loss["log_lambda"])
    log_margin = math.log(base["gamma_later"]) + loss["log_lambda"]
    conditioning_tolerance = 8.0 * np.finfo(float).eps * max(
        1.0,
        abs(math.log(base["gamma_later"])),
        abs(loss["log_lambda"]),
    )
    near_pole = abs(log_margin) <= conditioning_tolerance
    if near_pole:
        for direction in (-math.inf, math.inf):
            current = dict(base)
            current["gamma_later"] = float(np.nextafter(pole_gamma, direction))
            candidates.append(current)
    for candidate in candidates:
        try:
            classifications.append(
                str(stable_full_loss_interval(**candidate)["classification"])
            )
        except FullLossDiagnosticError:
            classifications.append("invalid_domain")
    return {
        "stable": len(set(classifications)) == 1,
        "classifications": classifications,
        "near_pole": near_pole,
        "log_margin": log_margin,
        "conditioning_tolerance": conditioning_tolerance,
    }


def classify_full_loss_gate(gates: Mapping[str, bool]) -> dict[str, Any]:
    """Return the Goal 050 decision without changing pinned PRAiSE."""
    missing = sorted(set(FULL_LOSS_GATE_NAMES) - set(gates))
    if missing:
        raise FullLossDiagnosticError(
            f"full-loss decision is missing required gates: {missing}"
        )
    passed = all(bool(gates[name]) for name in FULL_LOSS_GATE_NAMES)
    return {
        "decision": "PASS" if passed else "FAIL",
        "decision_label": PASS_LABEL if passed else FAIL_LABEL,
        "gate_names": list(FULL_LOSS_GATE_NAMES),
    }


def high_precision_full_loss_trajectory(
    endpoint_gamma: Any, times: Any, pressure: Any, gamma_c: Any,
    shock_index: Any, *, eta: float, z: float,
    gamma_inf: float = GAMMA_INF,
) -> dict[str, Any]:
    """Independent mpmath replay of every backward full-loss update."""
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    times_a = np.asarray(times, dtype=float)
    pressure_a = np.asarray(pressure, dtype=float)
    gamma_c_a = np.asarray(gamma_c, dtype=float)
    shocks = np.asarray(shock_index, dtype=int)
    if endpoint.ndim != 2 or times_a.ndim != 1 or pressure_a.shape != (endpoint.shape[0], times_a.size):
        raise FullLossDiagnosticError("high-precision trajectory shapes are invalid")
    if gamma_c_a.shape != pressure_a.shape or shocks.shape != (endpoint.shape[0],):
        raise FullLossDiagnosticError("high-precision trajectory shapes are incompatible")
    trajectory = np.full((endpoint.shape[0], times_a.size, endpoint.shape[1]), np.nan)
    state = np.full(trajectory.shape, STATE_POST_CUTOFF, dtype="<U32")
    trajectory[:, -1, :] = endpoint
    state[:, -1, :] = STATE_FINITE
    for row in range(endpoint.shape[0]):
        for freq in range(endpoint.shape[1]):
            for interval in range(times_a.size - 2, -1, -1):
                if interval < shocks[row]:
                    state[row, interval, freq] = STATE_POST_CUTOFF
                    continue
                if state[row, interval + 1, freq] != STATE_FINITE:
                    continue
                result = high_precision_full_loss_interval(
                    gamma_later=float(trajectory[row, interval + 1, freq]),
                    t0=float(times_a[interval]), t1=float(times_a[interval + 1]),
                    p0=float(pressure_a[row, interval]), p1=float(pressure_a[row, interval + 1]),
                    gamma_c=float(gamma_c_a[row, interval]), eta=eta, z=z,
                    gamma_inf=gamma_inf,
                )
                state[row, interval, freq] = str(result["classification"])
                if result["classification"] == STATE_FINITE or result["classification"] == STATE_SUBRELATIVISTIC:
                    trajectory[row, interval, freq] = float(result["gamma_earlier"])
    return {"trajectory": trajectory, "state": state}


def compare_full_loss_trajectories(
    stable: Mapping[str, Any], reference: Mapping[str, Any],
    shock_index: Any,
) -> dict[str, Any]:
    """Compare stable and 80-digit trajectories, including state labels."""
    left = np.asarray(stable["trajectory"], dtype=float)
    right = np.asarray(reference["trajectory"], dtype=float)
    ls = np.asarray(stable["state"])
    rs = np.asarray(reference["state"])
    if left.shape != right.shape or ls.shape != rs.shape:
        raise FullLossDiagnosticError("trajectory comparison shapes differ")
    shocks = np.asarray(shock_index, dtype=int)
    relevant = np.zeros(ls.shape, dtype=bool)
    for row, shock in enumerate(shocks.tolist()):
        relevant[row, shock:, :] = True
    finite = relevant & np.isfinite(left) & np.isfinite(right)
    if np.any(finite):
        delta = np.abs(left[finite] - right[finite])
        denom = np.maximum(np.abs(right[finite]), np.finfo(float).tiny)
        max_abs = float(np.max(delta)); max_rel = float(np.max(delta / denom))
        finite_pass = bool(
            np.all(
                delta
                <= STABLE_ATOL + STABLE_RTOL * np.abs(right[finite])
            )
        )
    else:
        max_abs = max_rel = None
        finite_pass = True
    class_mismatch = int(np.count_nonzero(relevant & (ls != rs)))
    return {
        "relevant_cell_count": int(np.count_nonzero(relevant)),
        "finite_cell_count": int(np.count_nonzero(finite)),
        "max_abs_difference": max_abs,
        "max_relative_difference": max_rel,
        "classification_mismatch_count": class_mismatch,
        "passed": bool(finite_pass and class_mismatch == 0),
    }


def reconstruct_full_loss_injection_emissivity(
    endpoint_gamma: Any, injection_gamma: Any, gamma_c: Any,
    pressure: Any, shock_index: int, tracer_endpoint: float,
    *, eta: float = 0.03, z: float = 0.05, s: float = 2.2,
    gmin: float = 500.0, gmax: float = 1.0e5,
    classification: str = STATE_FINITE,
    frequencies: Any = FREQUENCIES_GHZ,
) -> np.ndarray:
    """Reconstruct finite emissivity; explicit cutoffs use a labelled zero policy."""
    if classification in (STATE_PHYSICAL_CUTOFF, STATE_GAMMA_INF_CUTOFF, STATE_POST_CUTOFF):
        return np.zeros(len(tuple(frequencies)), dtype=float)
    if classification == STATE_SUBRELATIVISTIC:
        raise FullLossDiagnosticError(
            "subrelativistic gamma is outside the emissivity model domain"
        )
    if classification != STATE_FINITE:
        raise FullLossDiagnosticError(f"cannot reconstruct emissivity for {classification}")
    from plutokore.radio.praise import get_emissivity_numba, get_K
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    injection = np.asarray(injection_gamma, dtype=float)
    gc = np.asarray(gamma_c, dtype=float)
    p = np.asarray(pressure, dtype=float)
    if endpoint.shape != injection.shape or endpoint.ndim != 1 or not np.all(np.isfinite(injection)):
        raise FullLossDiagnosticError("finite emissivity requires finite endpoint and injection gamma")
    if shock_index < 0 or shock_index >= p.size or not np.isfinite(tracer_endpoint):
        raise FullLossDiagnosticError("invalid emissivity reconstruction inputs")
    values = get_emissivity_numba(
        s=s, freq=np.asarray(tuple(frequencies)) * 1.0e9 * (1.0 + z), eta=eta,
        gamma_c=np.asarray([gc[-1]]), p=np.asarray([p[-1]]), p_inj=np.asarray([p[shock_index]]),
        gm=endpoint[None, :], gm_inj=injection[None, :], tracer=np.asarray([tracer_endpoint]),
        K=get_K(s, float(gc[-1]), gmin, gmax),
    )
    values = np.asarray(values, dtype=float).reshape(-1)
    if not np.all(np.isfinite(values)):
        raise FullLossDiagnosticError("finite trajectory produced non-finite emissivity")
    return values


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv(path: Path, fields: list[str], rows: list[Mapping[str, Any]]) -> None:
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _write_gzip_csv(path: Path, fields: list[str], rows: list[Mapping[str, Any]]) -> None:
    with gzip.open(path, "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def _read_selection(path: Path, h5: Any) -> list[dict[str, Any]]:
    return recovery._read_selection(path, h5)


def _read_nonfinite_records(path: Path) -> list[dict[str, Any]]:
    return recovery._read_nonfinite_records(path)


def diagnose_full_loss(
    cache: Path, selection_csv: Path, nonfinite_records_csv: Path, output_dir: Path, *,
    trace_limit: int = TRACE_LIMIT, expected_cache_sha256: str | None = None,
    expected_selection_sha256: str | None = None,
    expected_nonfinite_records_sha256: str | None = None,
) -> dict[str, Any]:
    """Run the bounded 64-trace full-loss gate and emit deterministic evidence."""
    if trace_limit <= 0:
        raise FullLossDiagnosticError("trace_limit must be positive")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    cache_hash, selection_hash, records_hash = _sha256(Path(cache)), _sha256(Path(selection_csv)), _sha256(Path(nonfinite_records_csv))
    if expected_cache_sha256 and cache_hash != expected_cache_sha256:
        raise FullLossDiagnosticError("cache SHA-256 does not match declared immutable input")
    if expected_selection_sha256 and selection_hash != expected_selection_sha256:
        raise FullLossDiagnosticError("selection SHA-256 does not match declared immutable input")
    if expected_nonfinite_records_sha256 and records_hash != expected_nonfinite_records_sha256:
        raise FullLossDiagnosticError("nonfinite-record SHA-256 does not match declared immutable input")
    interval_rows: list[dict[str, Any]] = []
    gamma_rows: list[dict[str, Any]] = []
    emissivity_rows: list[dict[str, Any]] = []
    panel_rows: list[dict[str, Any]] = []
    hp_checks: list[dict[str, Any]] = []
    boundary_checks: list[dict[str, Any]] = []
    stable_ok = emissivity_ok = reference_ok = boundary_ok = lambda_ok = repeat_ok = True
    window_relevant_a2_count = 0
    window_relevant_fallback_count = 0
    relevant_a2_keys: set[tuple[str, int, int]] = set()
    fallback_keys: set[tuple[str, int, int, int]] = set()
    stable_silent_fallback_count = 0
    selected: list[dict[str, Any]] = []
    source_identity_sha256: str | None = None
    with __import__("h5py").File(cache, "r") as h5:
        raw_source_identity = h5.attrs.get("source_identity_sha256")
        if raw_source_identity is not None:
            source_identity_sha256 = (
                raw_source_identity.decode()
                if isinstance(raw_source_identity, bytes)
                else str(raw_source_identity)
            )
        if hasattr(workflow, "_validate_completed_cache"):
            workflow._validate_completed_cache(h5)
        selections = _read_selection(Path(selection_csv), h5)
        records = _read_nonfinite_records(Path(nonfinite_records_csv))
        selected = recovery.choose_trace_selection(selections, records, trace_limit=trace_limit)
        selected_rows = np.asarray([int(row["cache_row"]) for row in selected], dtype=np.int64)
        if hasattr(workflow, "build_pressure_treatment_plan"):
            plan = workflow.build_pressure_treatment_plan(
                h5,
                expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                    "expected_trim_rows"
                ],
                expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                    "expected_no_positive_rows"
                ],
                expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                    "expected_single_record_rows"
                ],
                expected_trim_single_record_overlap_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                    "expected_trim_single_record_overlap_rows"
                ],
            )
            raw = recovery._read_treated_sample(h5, selected_rows, plan)
            physical, _units = workflow.convert_code_cache_to_physical(raw, shock_threshold=float(h5.attrs["shock_threshold"]), shock_component=int(h5.attrs["shock_component"]))
        else:
            physical = raw = selected_rows
        panel_rows = [{"sample_index": int(row["sample_index"]), "cache_row": int(row["cache_row"]), "physical_id": int(row["physical_id"]), "trace_class": str(row.get("trace_class", "selected")), "trace_mode": str(row.get("trace_mode", "both")), "trace_frequency_GHz": str(row.get("trace_frequency_GHz", "both")), "trace_selection_rule": str(row.get("trace_selection_rule", "deterministic"))} for row in selected]
        for mode in ("unsmoothed", "log_savgol"):
            result = workflow.calculate_praise_pair(physical, frequencies=FREQUENCIES_GHZ, z=0.05, s=2.2, eta=0.03, gmin=500.0, gmax=1.0e5, lst_index=0, pressure_mode=mode, singleton_policy="instantaneous_recent_shock", diagnostic=True, include_adiabatic=False)
            groups = result.get("full_info", [])
            id_to_selection = {int(row["physical_id"]): row for row in selected}
            ids = np.asarray(result.get("ids", []), dtype=np.int64)
            full_values = np.asarray(
                getattr(result.get("full"), "value", result.get("full")),
                dtype=float,
            )
            if full_values.shape != (len(selected), len(FREQUENCIES_GHZ)):
                raise FullLossDiagnosticError(
                    f"{mode} full emissivity shape does not match the selected panel"
                )
            mode_seen_rows: set[int] = set()
            for group in groups:
                info = group.get("info", {}); rows = np.asarray(group.get("rows", []), dtype=int)
                if not rows.size or not isinstance(info, Mapping):
                    raise FullLossDiagnosticError(
                        f"{mode} grouped full-loss provenance is malformed"
                    )
                if (
                    np.any(rows < 0)
                    or np.any(rows >= len(selected))
                    or mode_seen_rows.intersection(rows.tolist())
                ):
                    raise FullLossDiagnosticError(
                        f"{mode} grouped full-loss rows overlap or leave the panel"
                    )
                mode_seen_rows.update(int(row) for row in rows.tolist())
                times = np.asarray(info.get("particle_times"), dtype=float)
                endpoint = np.asarray(info.get("current_lorentz"), dtype=float)
                pressure = np.asarray(info.get("particle_pressure"), dtype=float)
                gc = np.asarray(group.get("adiabatic_eff"), dtype=float)
                shocks = np.asarray(group.get("shock_index"), dtype=int)
                if times.size < 2:
                    for local, global_row in enumerate(rows.tolist()):
                        pid = int(ids[global_row]) if global_row < ids.size else int(selected[global_row]["physical_id"])
                        for frequency_index, frequency in enumerate(
                            FREQUENCIES_GHZ
                        ):
                            value = float(
                                full_values[global_row, frequency_index]
                            )
                            emissivity_ok = emissivity_ok and math.isfinite(value)
                            emissivity_rows.append({
                                "pressure_mode": mode,
                                "physical_id": pid,
                                "frequency_GHz": float(frequency),
                                "classification": STATE_FINITE,
                                "emissivity": value,
                                "policy": "instantaneous_recent_shock",
                            })
                    continue
                try:
                    stable = stable_full_loss_trajectory(endpoint, times, pressure, gc, shocks, eta=0.03, z=0.05)
                    reference = high_precision_full_loss_trajectory(endpoint, times, pressure, gc, shocks, eta=0.03, z=0.05)
                    comparison = compare_full_loss_trajectories(stable, reference, shocks)
                    repeat = stable_full_loss_trajectory(endpoint, times, pressure, gc, shocks, eta=0.03, z=0.05)
                    repeat_ok = repeat_ok and bool(np.array_equal(stable["trajectory"], repeat["trajectory"], equal_nan=True) and np.array_equal(stable["state"], repeat["state"]))
                except (FullLossDiagnosticError, ValueError, OverflowError):
                    stable_ok = reference_ok = repeat_ok = False; continue
                hp_checks.append(comparison); stable_ok = stable_ok and bool(comparison["passed"]); reference_ok = reference_ok and bool(comparison["passed"])
                stable_silent_fallback_count += int(
                    stable["silent_fallback_count"]
                )
                a2 = np.asarray(info.get("a2_arr", np.empty((rows.size, times.size - 1))), dtype=float)
                ap_arr = np.asarray(info.get("ap_arr", np.zeros_like(a2)), dtype=float)
                try:
                    a2_window = recovery.classify_relevant_windows(a2, shocks)
                    window_relevant_a2_count += int(a2_window["relevant_nonfinite_count"])
                    for local_row, interval in np.argwhere(~np.isfinite(a2)):
                        if int(interval) >= int(shocks[int(local_row)]):
                            pid_key = int(ids[rows[int(local_row)]]) if rows[int(local_row)] < ids.size else int(selected[int(local_row)]["physical_id"])
                            relevant_a2_keys.add((mode, pid_key, int(interval)))
                    fallback = recovery.classify_gamma_fallbacks(endpoint, times, gc, ap_arr, a2, shocks)
                    window_relevant_fallback_count += int(
                        fallback["relevant_fallback_count"]
                    )
                    for rec in fallback["records"]:
                        if int(rec["relevant"]):
                            local_row = int(rec["row"]); pid_key = int(ids[rows[local_row]]) if rows[local_row] < ids.size else int(selected[local_row]["physical_id"])
                            fallback_keys.add((mode, pid_key, int(rec["interval_index"]), int(rec["frequency_index"])))
                except (ValueError, TypeError, IndexError, KeyError) as exc:
                    raise FullLossDiagnosticError(
                        f"{mode} pinned-failure reproduction could not be classified"
                    ) from exc
                for local, global_row in enumerate(rows.tolist()):
                    pid = int(ids[global_row]) if global_row < ids.size else int(selected[global_row]["physical_id"])
                    selection = id_to_selection.get(pid, selected[min(global_row, len(selected) - 1)])
                    for interval in range(times.size - 1):
                        if interval < int(shocks[local]):
                            continue
                        loss = stable_scaled_loss(t0=float(times[interval]), t1=float(times[interval + 1]), p0=float(pressure[local, interval]), p1=float(pressure[local, interval + 1]), gamma_c=float(gc[local, interval]), eta=0.03, z=0.05)
                        hp = high_precision_scaled_loss(t0=float(times[interval]), t1=float(times[interval + 1]), p0=float(pressure[local, interval]), p1=float(pressure[local, interval + 1]), gamma_c=float(gc[local, interval]), eta=0.03, z=0.05)
                        log_difference = abs(float(loss["log_lambda"]) - float(hp["log_lambda"]))
                        lambda_ok = lambda_ok and bool(log_difference <= STABLE_RTOL + STABLE_ATOL)
                        interval_rows.append({"pressure_mode": mode, "physical_id": pid, "cache_row": int(selection["cache_row"]), "interval_index": interval, "frequency_GHz": "both", "log_lambda": loss["log_lambda"], "high_precision_log_lambda": float(hp["log_lambda"]), "a2_class": recovery._value_class(float(a2[local, interval]))})
                        for fi, freq in enumerate(FREQUENCIES_GHZ):
                            value = float(stable["trajectory"][local, interval, fi]); ref = float(reference["trajectory"][local, interval, fi])
                            cls = str(stable["state"][local, interval, fi]); rcls = str(reference["state"][local, interval, fi])
                            gamma_rows.append({"pressure_mode": mode, "physical_id": pid, "cache_row": int(selection["cache_row"]), "interval_index": interval, "frequency_GHz": float(freq), "stable_gamma": value, "reference_gamma": ref, "classification": cls, "reference_classification": rcls, "classification_match": cls == rcls})
                        for fi, freq in enumerate(FREQUENCIES_GHZ):
                            if stable["state"][local, interval + 1, fi] != STATE_FINITE:
                                continue
                            check = interval_boundary_stability(gamma_later=float(stable["trajectory"][local, interval + 1, fi]), t0=float(times[interval]), t1=float(times[interval + 1]), p0=float(pressure[local, interval]), p1=float(pressure[local, interval + 1]), gamma_c=float(gc[local, interval]), eta=0.03, z=0.05)
                            boundary_checks.append(check); boundary_ok = boundary_ok and bool(check["stable"])
                    shock = int(shocks[local]); injections = stable["trajectory"][local, shock, :] if shock < times.size else np.full(len(FREQUENCIES_GHZ), np.nan)
                    classes = [str(stable["state"][local, shock, fi]) if shock < times.size - 1 else STATE_FINITE for fi in range(len(FREQUENCIES_GHZ))]
                    for fi, freq in enumerate(FREQUENCIES_GHZ):
                        cls = classes[fi]
                        try:
                            em = reconstruct_full_loss_injection_emissivity(endpoint[local, fi:fi + 1], injections[fi:fi + 1], gc[local], pressure[local], shock, float(physical["tracer"][global_row, -1]), classification=cls, frequencies=(freq,))
                            emissivity_ok = emissivity_ok and bool(np.all(np.isfinite(em))); value = float(em[0])
                        except Exception:
                            emissivity_ok = False; value = None
                        emissivity_rows.append({"pressure_mode": mode, "physical_id": pid, "frequency_GHz": float(freq), "classification": cls, "emissivity": value, "policy": "Turner/RAiSE explicit physical cutoff zero" if cls in (STATE_PHYSICAL_CUTOFF, STATE_GAMMA_INF_CUTOFF) else "finite trajectory reconstruction"})
            if mode_seen_rows != set(range(len(selected))):
                raise FullLossDiagnosticError(
                    f"{mode} grouped full-loss provenance does not cover the panel"
                )
    records_count = len(records)
    real_panel = bool(trace_limit == TRACE_LIMIT and len(selections) >= trace_limit)
    relevant_a2_count = len(relevant_a2_keys)
    fallback_count = len(fallback_keys)
    panel_count_gate = (not real_panel) or (
        relevant_a2_count == EXPECTED_RELEVANT_NONFINITE_A2
        and window_relevant_a2_count == EXPECTED_RELEVANT_NONFINITE_A2
        and fallback_count == EXPECTED_PINNED_GAMMA_FALLBACKS
        and window_relevant_fallback_count == EXPECTED_PINNED_GAMMA_FALLBACKS
    )
    analytic_self_checks = run_analytic_self_checks()
    relevant_subrelativistic_count = sum(
        1
        for row in gamma_rows
        if row["classification"] == STATE_SUBRELATIVISTIC
    )
    gates = {"analytic_limits": bool(analytic_self_checks["passed"]), "finite_scaled_loss": bool(stable_ok and (interval_rows or emissivity_rows)), "high_precision_scaled_loss": bool(reference_ok and lambda_ok and hp_checks), "high_precision_gamma": bool(reference_ok and hp_checks), "exact_state_classification": bool(gamma_rows and all(row["classification_match"] for row in gamma_rows)), "boundary_conditioning": bool(boundary_ok and boundary_checks), "zero_silent_fallbacks": bool(stable_silent_fallback_count == 0), "no_subrelativistic_states": bool(relevant_subrelativistic_count == 0), "finite_or_explicit_cutoff_emissivity": emissivity_ok, "deterministic_repeat": repeat_ok, "pinned_failure_reproduction": panel_count_gate}
    decision = classify_full_loss_gate({name: gates[name] for name in FULL_LOSS_GATE_NAMES})
    fingerprint_payload = {"interval": interval_rows, "gamma": gamma_rows, "emissivity": emissivity_rows, "gates": gates}
    fingerprint = hashlib.sha256(json.dumps(_json_safe(fingerprint_payload), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    summary = {"status": "diagnostic_complete", **decision, "cache_sha256": cache_hash, "selection_sha256": selection_hash, "nonfinite_records_sha256": records_hash, "source_identity_sha256": source_identity_sha256, "trace_count": len(selected), "selection_count": len(selections), "frequencies_GHz": list(FREQUENCIES_GHZ), "pressure_modes_checked": ["unsmoothed", "log_savgol"], "original_relevant_nonfinite_a2_count": relevant_a2_count, "window_classified_relevant_nonfinite_a2_count": window_relevant_a2_count, "expected_relevant_nonfinite_a2_count": EXPECTED_RELEVANT_NONFINITE_A2, "pinned_relevant_gamma_fallback_count": fallback_count, "window_classified_pinned_gamma_fallback_count": window_relevant_fallback_count, "stable_silent_fallback_count": stable_silent_fallback_count, "relevant_subrelativistic_state_count": relevant_subrelativistic_count, "expected_frequency_specific_pinned_gamma_fallback_count": EXPECTED_PINNED_GAMMA_FALLBACKS, "archived_nonfinite_record_count": records_count, "evidence_fingerprint_sha256": fingerprint, "gates": gates, "analytic_self_checks": analytic_self_checks, "high_precision": {"comparison_count": len(hp_checks), "max_relative_difference": max((x["max_relative_difference"] or 0 for x in hp_checks), default=None)}, "state_counts": {state: sum(1 for row in gamma_rows if row["classification"] == state) for state in (STATE_FINITE, STATE_PHYSICAL_CUTOFF, STATE_GAMMA_INF_CUTOFF, STATE_SUBRELATIVISTIC, STATE_POST_CUTOFF)}}
    _write_csv(output_dir / "full_loss_panel_selection.csv", list(panel_rows[0]) if panel_rows else ["sample_index", "cache_row", "physical_id", "trace_class", "trace_mode", "trace_frequency_GHz", "trace_selection_rule"], panel_rows)
    _write_csv(output_dir / "full_loss_interval_summary.csv", ["pressure_mode", "physical_id", "cache_row", "interval_index", "frequency_GHz", "log_lambda", "high_precision_log_lambda", "a2_class"], interval_rows)
    _write_csv(output_dir / "full_loss_gamma_summary.csv", ["pressure_mode", "physical_id", "cache_row", "interval_index", "frequency_GHz", "stable_gamma", "reference_gamma", "classification", "reference_classification", "classification_match"], gamma_rows)
    _write_csv(output_dir / "full_loss_emissivity_summary.csv", ["pressure_mode", "physical_id", "frequency_GHz", "classification", "emissivity", "policy"], emissivity_rows)
    _write_csv(output_dir / "full_loss_gate_summary.csv", ["gate", "passed", "value"], [{"gate": key, "passed": bool(value), "value": json.dumps(_json_safe(value), sort_keys=True)} for key, value in gates.items()])
    (output_dir / "full_loss_gate_summary.json").write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--selection-csv", type=Path, required=True)
    parser.add_argument("--nonfinite-records-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--trace-limit", type=int, default=TRACE_LIMIT)
    parser.add_argument("--expected-cache-sha256")
    parser.add_argument("--expected-selection-sha256")
    parser.add_argument("--expected-nonfinite-records-sha256")
    return parser


def main(argv: Any = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = diagnose_full_loss(args.cache, args.selection_csv, args.nonfinite_records_csv, args.output_dir, trace_limit=args.trace_limit, expected_cache_sha256=args.expected_cache_sha256, expected_selection_sha256=args.expected_selection_sha256, expected_nonfinite_records_sha256=args.expected_nonfinite_records_sha256)
    except (OSError, ValueError, FullLossDiagnosticError, KeyError, TypeError) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))
    return 0 if summary["decision"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
