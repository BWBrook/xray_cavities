#!/usr/bin/env python3
"""Native-grid shock-mask calibration, topology, and energy primitives."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from scipy import ndimage

from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS,
    UNIT_DENSITY_CGS,
    UNIT_ENERGY_ERG,
    UNIT_LENGTH_CM,
)


THRESHOLD_FACTORS = (0.5, 1.0, 2.0)
CONTROL_QUANTILE = 0.9999
CONTROL_MULTIPLIER = 5.0
PRESSURE_EXCESS_FLOOR = 0.05
DENSITY_EXCESS_FLOOR = 0.03
ENTROPY_EXCESS_FLOOR = 0.02
AMBIENT_TRACER_MAX = 0.001
MIN_SELECTED_CELLS = 100


@dataclass(frozen=True)
class ShockThresholds:
    pressure_excess: float
    density_excess: float
    entropy_excess: float
    control_sample_count: int
    control_joint_exceedance_fraction: float
    pressure_control_quantile: float
    density_control_quantile: float
    entropy_control_quantile: float
    pressure_control_max: float
    density_control_max: float
    entropy_control_max: float

    def scaled(self, factor: float) -> tuple[float, float, float]:
        if not math.isfinite(factor) or factor <= 0.0:
            raise ValueError("shock threshold factor must be finite and positive")
        return (
            factor * self.pressure_excess,
            factor * self.density_excess,
            factor * self.entropy_excess,
        )

    def as_row(self, *, environment: str, source: str) -> dict[str, Any]:
        return {
            "environment": environment,
            "control_source": source,
            "control_role": "dimensionless_noise_calibration_not_cellwise_subtraction",
            "control_quantile": CONTROL_QUANTILE,
            "control_multiplier": CONTROL_MULTIPLIER,
            "control_sample_count": self.control_sample_count,
            "pressure_control_quantile": self.pressure_control_quantile,
            "density_control_quantile": self.density_control_quantile,
            "entropy_control_quantile": self.entropy_control_quantile,
            "pressure_control_max": self.pressure_control_max,
            "density_control_max": self.density_control_max,
            "entropy_control_max": self.entropy_control_max,
            "pressure_excess_floor": PRESSURE_EXCESS_FLOOR,
            "density_excess_floor": DENSITY_EXCESS_FLOOR,
            "entropy_excess_floor": ENTROPY_EXCESS_FLOOR,
            "adopted_pressure_excess": self.pressure_excess,
            "adopted_density_excess": self.density_excess,
            "adopted_entropy_excess": self.entropy_excess,
            "control_joint_exceedance_fraction": self.control_joint_exceedance_fraction,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ShockThresholds":
        return cls(
            pressure_excess=float(row["adopted_pressure_excess"]),
            density_excess=float(row["adopted_density_excess"]),
            entropy_excess=float(row["adopted_entropy_excess"]),
            control_sample_count=int(row["control_sample_count"]),
            control_joint_exceedance_fraction=float(row["control_joint_exceedance_fraction"]),
            pressure_control_quantile=float(row["pressure_control_quantile"]),
            density_control_quantile=float(row["density_control_quantile"]),
            entropy_control_quantile=float(row["entropy_control_quantile"]),
            pressure_control_max=float(row["pressure_control_max"]),
            density_control_max=float(row["density_control_max"]),
            entropy_control_max=float(row["entropy_control_max"]),
        )


def entropy_excess(pressure_ratio: np.ndarray, density_ratio: np.ndarray) -> np.ndarray:
    pressure = np.asarray(pressure_ratio, dtype=np.float64)
    density = np.asarray(density_ratio, dtype=np.float64)
    if pressure.shape != density.shape or np.any(pressure <= 0.0) or np.any(density <= 0.0):
        raise ValueError("pressure and density ratios must be aligned and positive")
    return np.log(pressure) - GAMMA_GAS * np.log(density)


def derive_control_thresholds(
    *,
    pressure_excess_samples: np.ndarray,
    density_excess_samples: np.ndarray,
    entropy_excess_samples: np.ndarray,
    maximum_primary_joint_fraction: float = 1.0e-6,
) -> ShockThresholds:
    samples = [
        np.asarray(values, dtype=np.float64).reshape(-1)
        for values in (pressure_excess_samples, density_excess_samples, entropy_excess_samples)
    ]
    if not samples[0].size or len({values.size for values in samples}) != 1:
        raise ValueError("control samples must be non-empty and aligned")
    if any(np.any(~np.isfinite(values)) or np.any(values < 0.0) for values in samples):
        raise ValueError("control excess samples must be finite and non-negative")
    quantiles = [float(np.quantile(values, CONTROL_QUANTILE)) for values in samples]
    thresholds = (
        max(PRESSURE_EXCESS_FLOOR, CONTROL_MULTIPLIER * quantiles[0]),
        max(DENSITY_EXCESS_FLOOR, CONTROL_MULTIPLIER * quantiles[1]),
        max(ENTROPY_EXCESS_FLOOR, CONTROL_MULTIPLIER * quantiles[2]),
    )
    joint = (samples[0] >= thresholds[0]) & (samples[1] >= thresholds[1]) & (
        samples[2] >= thresholds[2]
    )
    joint_fraction = float(np.mean(joint))
    if joint_fraction > maximum_primary_joint_fraction:
        raise ValueError(
            "no-jet primary front thresholds exceed the allowed false-positive rate: "
            f"{joint_fraction:.8g}"
        )
    return ShockThresholds(
        pressure_excess=thresholds[0],
        density_excess=thresholds[1],
        entropy_excess=thresholds[2],
        control_sample_count=samples[0].size,
        control_joint_exceedance_fraction=joint_fraction,
        pressure_control_quantile=quantiles[0],
        density_control_quantile=quantiles[1],
        entropy_control_quantile=quantiles[2],
        pressure_control_max=float(np.max(samples[0])),
        density_control_max=float(np.max(samples[1])),
        entropy_control_max=float(np.max(samples[2])),
    )


def build_processed_and_front_masks(
    *,
    pressure_ratio: np.ndarray,
    density_ratio: np.ndarray,
    entropy_delta: np.ndarray,
    ambient_mask: np.ndarray,
    thresholds: ShockThresholds,
    factor: float,
) -> tuple[np.ndarray, np.ndarray]:
    pressure = np.asarray(pressure_ratio)
    density = np.asarray(density_ratio)
    entropy = np.asarray(entropy_delta)
    ambient = np.asarray(ambient_mask, dtype=bool)
    if len({pressure.shape, density.shape, entropy.shape, ambient.shape}) != 1:
        raise ValueError("shock-mask inputs must have the same shape")
    p_cut, rho_cut, entropy_cut = thresholds.scaled(factor)
    processed = ambient & (entropy >= entropy_cut)
    front = processed & ((pressure - 1.0) >= p_cut) & ((density - 1.0) >= rho_cut)
    return processed, front


def select_seeded_components(
    candidate: np.ndarray,
    seed: np.ndarray,
    *,
    labels: np.ndarray | None = None,
    minimum_cells: int = MIN_SELECTED_CELLS,
) -> tuple[np.ndarray, dict[str, Any]]:
    candidate_mask = np.asarray(candidate, dtype=bool)
    seed_mask = np.asarray(seed, dtype=bool)
    if candidate_mask.shape != seed_mask.shape:
        raise ValueError("candidate and seed masks must be aligned")
    if labels is None:
        labels = np.empty(candidate_mask.shape, dtype=np.int32)
    if labels.shape != candidate_mask.shape or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("label workspace must be an aligned integer array")
    component_count = int(
        ndimage.label(candidate_mask, structure=np.ones((3, 3, 3), dtype=bool), output=labels)
    )
    selected_ids = np.unique(labels[seed_mask & candidate_mask])
    selected_ids = selected_ids[selected_ids != 0]
    if selected_ids.size == 0:
        return np.zeros(candidate_mask.shape, dtype=bool), {
            "component_count": component_count,
            "selected_component_count": 0,
            "selected_cell_count": 0,
            "status": "unresolved_no_seeded_component",
        }
    selected = np.isin(labels, selected_ids)
    selected_cells = int(np.count_nonzero(selected))
    status = "quantitative_seeded_component" if selected_cells >= minimum_cells else "unresolved_too_small"
    if status != "quantitative_seeded_component":
        selected[:] = False
    return selected, {
        "component_count": component_count,
        "selected_component_count": int(selected_ids.size),
        "selected_cell_count": selected_cells,
        "status": status,
    }


def shock_energy_slice(
    *,
    rho: np.ndarray,
    pressure: np.ndarray,
    velocity_squared: np.ndarray,
    tracer: np.ndarray,
    baseline_rho: np.ndarray,
    baseline_pressure: np.ndarray,
    baseline_velocity_squared: np.ndarray,
    volume_kpc3: np.ndarray,
    potential_cm2_s2: np.ndarray,
    mask: np.ndarray,
) -> dict[str, float]:
    arrays = [
        np.asarray(values, dtype=np.float64)
        for values in (
            rho,
            pressure,
            velocity_squared,
            tracer,
            baseline_rho,
            baseline_pressure,
            baseline_velocity_squared,
            volume_kpc3,
            potential_cm2_s2,
        )
    ]
    selected = np.asarray(mask, dtype=bool)
    if len({values.shape for values in arrays} | {selected.shape}) != 1:
        raise ValueError("shock-energy arrays must have the same shape")
    rho_now, pressure_now, v2_now, tracer_now, rho0, pressure0, v20, volume, potential = arrays
    if np.any(rho_now <= 0.0) or np.any(rho0 <= 0.0) or np.any(pressure_now <= 0.0) or np.any(pressure0 <= 0.0):
        raise ValueError("shock-energy density and pressure must be positive")
    if np.any(~np.isfinite(tracer_now)):
        raise ValueError("shock-energy tracer must be finite")
    ambient_mask = np.clip(tracer_now, 0.0, 1.0) <= AMBIENT_TRACER_MAX
    if np.any(selected & ~ambient_mask):
        raise ValueError("shock mask overlaps the strict native cocoon")
    # Membership is binary: selected ambient cells contribute their full
    # current and initial energies, with no residual (1-tr1) weighting.
    selected_float = selected.astype(np.float64)
    thermal_delta = np.sum(
        selected_float * (pressure_now - pressure0) * volume
    ) / (GAMMA_GAS - 1.0) * UNIT_ENERGY_ERG
    kinetic_delta = np.sum(
        0.5 * selected_float * (rho_now * v2_now - rho0 * v20) * volume
    ) * UNIT_ENERGY_ERG
    mass_delta_g = (
        selected_float
        * (rho_now - rho0)
        * volume
        * UNIT_DENSITY_CGS
        * UNIT_LENGTH_CM**3
    )
    gravitational_delta = np.sum(mass_delta_g * potential)
    irreversible = np.sum(
        selected_float
        * (pressure_now - pressure0 * (rho_now / rho0) ** GAMMA_GAS)
        * volume
    ) / (GAMMA_GAS - 1.0) * UNIT_ENERGY_ERG
    return {
        "thermal_delta_erg": float(thermal_delta),
        "kinetic_delta_erg": float(kinetic_delta),
        "gravitational_delta_erg": float(gravitational_delta),
        "total_delta_erg": float(thermal_delta + kinetic_delta + gravitational_delta),
        "irreversible_heating_erg": float(irreversible),
        "mask_volume_kpc3": float(np.sum(selected_float * volume)),
        "ambient_weighted_volume_kpc3": float(np.sum(selected_float * volume)),
        "ambient_weighted_mass_g": float(
            np.sum(selected_float * rho_now * volume)
            * UNIT_DENSITY_CGS
            * UNIT_LENGTH_CM**3
        ),
        "selected_cell_count": float(np.count_nonzero(selected)),
    }


def empty_shock_energy() -> dict[str, float]:
    return {
        "thermal_delta_erg": 0.0,
        "kinetic_delta_erg": 0.0,
        "gravitational_delta_erg": 0.0,
        "total_delta_erg": 0.0,
        "irreversible_heating_erg": 0.0,
        "mask_volume_kpc3": 0.0,
        "ambient_weighted_volume_kpc3": 0.0,
        "ambient_weighted_mass_g": 0.0,
        "selected_cell_count": 0.0,
    }


def add_shock_energy(target: dict[str, float], source: Mapping[str, float]) -> None:
    if set(target) != set(source):
        raise ValueError("shock-energy accumulator schema mismatch")
    for key in target:
        target[key] += float(source[key])
