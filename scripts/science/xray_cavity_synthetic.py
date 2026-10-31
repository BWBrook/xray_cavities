#!/usr/bin/env python3
"""Synthetic X-ray maps with known cavities for Q-032 detector validation.

The atmosphere is the tabulated spherical cluster or group profile used by
the production runs. Maps follow the production XRAiSE view convention: the
line of sight rotates in the simulation x-y plane, so the jet (z) axis lies
in the sky plane for every view and the sky horizontal coordinate is
``u = x cos(theta) - y sin(theta)``. Emission is integrated across the
production box (|x|, |y| <= 200 kpc, |z| <= 250 kpc).

Cavities are spheroids symmetric about the jet axis, so their projected
chord at sky position (u, z) is independent of view angle. The cavity and
rim contributions are integrated over the analytic chords, which keeps thin
structures exact on the stretched production pixel grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

KPC_CM = 3.085_677_581_491_3673e21
BOLTZMANN_KEV_PER_K = 8.617_333_262e-8
BAND_ENERGY_KEV = 1.0
BOX_HALF_WIDTH_KPC = 200.0
BOX_HALF_HEIGHT_KPC = 250.0
ATMOSPHERE_SAMPLES = 768
CHORD_SAMPLES = 48
ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_TABLES = {
    "cluster": ROOT / "docs/science/assets/q032_synthetic_harness_2026-10-31/inputs/tabulated_cosmo_002003.csv",
    "group": ROOT / "docs/science/assets/q032_synthetic_harness_2026-10-31/inputs/tabulated_cosmo_002031.csv",
}


@dataclass(frozen=True)
class Atmosphere:
    radius_kpc: np.ndarray
    density_g_cm3: np.ndarray
    temperature_k: np.ndarray

    def emissivity(self, radius_kpc: np.ndarray, density_factor: float = 1.0) -> np.ndarray:
        """Narrow-band free-free emissivity at 1 keV, normalised to the centre.

        A region at ``density_factor`` times ambient density keeps ambient
        pressure, so its temperature scales by the inverse factor.
        """

        density = np.interp(radius_kpc, self.radius_kpc, self.density_g_cm3) / self.density_g_cm3[0] * density_factor
        temperature = np.interp(radius_kpc, self.radius_kpc, self.temperature_k) / density_factor
        kt = BOLTZMANN_KEV_PER_K * temperature
        return density**2 * kt**-0.5 * np.exp(-BAND_ENERGY_KEV / kt)


def load_atmosphere(environment: str) -> Atmosphere:
    values = np.loadtxt(ENVIRONMENT_TABLES[environment], ndmin=2)
    return Atmosphere(values[:, 0] / KPC_CM, values[:, 1], values[:, 3])


@dataclass(frozen=True)
class Spheroid:
    """Cavity spheroid on the jet axis with an optional compressed rim."""

    center_z_kpc: float
    semiaxis_along_jet_kpc: float
    semiaxis_across_jet_kpc: float
    density_factor: float = 0.01
    rim_width_kpc: float = 0.0
    rim_density_factor: float = 1.0

    @property
    def side(self) -> str:
        return "negative_z" if self.center_z_kpc < 0.0 else "positive_z"

    @property
    def volume_kpc3(self) -> float:
        return 4.0 / 3.0 * np.pi * self.semiaxis_along_jet_kpc * self.semiaxis_across_jet_kpc**2

    def half_chord(self, u: np.ndarray, z: np.ndarray, grow_kpc: float = 0.0) -> np.ndarray:
        a = self.semiaxis_along_jet_kpc + grow_kpc
        b = self.semiaxis_across_jet_kpc + grow_kpc
        radial_sq = b**2 * (1.0 - ((z - self.center_z_kpc) / a) ** 2) - u**2
        return np.sqrt(np.clip(radial_sq, 0.0, None))


@dataclass(frozen=True)
class SyntheticMap:
    surface_brightness: np.ndarray
    horizontal_axis_kpc: np.ndarray
    z_axis_kpc: np.ndarray
    cavity_path_length_kpc: dict[str, np.ndarray]
    cavity_volume_kpc3: dict[str, float]
    view_deg: float

    @property
    def cavity_mask(self) -> np.ndarray:
        mask = np.zeros(self.surface_brightness.shape, dtype=bool)
        for length in self.cavity_path_length_kpc.values():
            mask |= length > 0.0
        return mask


def _box_chord(u: np.ndarray, view_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Line-of-sight interval inside |x|, |y| <= box half width."""

    theta = np.deg2rad(view_deg)
    sin_t, cos_t = np.sin(theta), np.cos(theta)
    lower = np.full(u.shape, -np.inf)
    upper = np.full(u.shape, np.inf)
    # x = u cos + s sin, y = -u sin + s cos
    for offset, slope in ((u * cos_t, sin_t), (-u * sin_t, cos_t)):
        if abs(slope) < 1.0e-12:
            outside = np.abs(offset) > BOX_HALF_WIDTH_KPC
            lower = np.where(outside, np.inf, lower)
            continue
        first = (-BOX_HALF_WIDTH_KPC - offset) / slope
        second = (BOX_HALF_WIDTH_KPC - offset) / slope
        lower = np.maximum(lower, np.minimum(first, second))
        upper = np.minimum(upper, np.maximum(first, second))
    return lower, np.maximum(upper, lower)


def _segment_integral(
    atmosphere: Atmosphere,
    u: np.ndarray,
    z: np.ndarray,
    start: np.ndarray,
    stop: np.ndarray,
    density_factor: float,
    samples: int,
) -> np.ndarray:
    nodes, weights = np.polynomial.legendre.leggauss(samples)
    half = 0.5 * (stop - start)
    middle = 0.5 * (stop + start)
    s = middle[..., None] + half[..., None] * nodes
    radius = np.sqrt(u[..., None] ** 2 + z[..., None] ** 2 + s**2)
    return half * np.sum(weights * atmosphere.emissivity(radius, density_factor), axis=-1)


def render_map(
    atmosphere: Atmosphere,
    horizontal_axis_kpc: np.ndarray,
    z_axis_kpc: np.ndarray,
    cavities: Sequence[Spheroid] = (),
    *,
    view_deg: float = 0.0,
) -> SyntheticMap:
    """Project the atmosphere with cavities through the production box."""

    horizontal = np.asarray(horizontal_axis_kpc, dtype=float)
    vertical = np.asarray(z_axis_kpc, dtype=float)
    u, z = np.meshgrid(horizontal, vertical)
    lower, upper = _box_chord(u, view_deg)
    inside = upper > lower
    brightness = np.zeros(u.shape)
    rows = max(1, int(2.0e7 // (horizontal.size * ATMOSPHERE_SAMPLES)))
    for start in range(0, vertical.size, rows):
        block = slice(start, start + rows)
        brightness[block] = _segment_integral(
            atmosphere, u[block], z[block], lower[block], upper[block], 1.0, ATMOSPHERE_SAMPLES
        )
    brightness[~inside] = 0.0
    path_lengths: dict[str, np.ndarray] = {}
    volumes: dict[str, float] = {}
    for cavity in cavities:
        if abs(cavity.center_z_kpc) + cavity.semiaxis_along_jet_kpc + cavity.rim_width_kpc > BOX_HALF_HEIGHT_KPC:
            raise ValueError("cavity extends beyond the z boundary")
        if cavity.semiaxis_across_jet_kpc + cavity.rim_width_kpc > BOX_HALF_WIDTH_KPC:
            raise ValueError("cavity extends beyond the x-y boundary")
        if cavity.side in volumes:
            raise ValueError("at most one cavity per jet side")
        chord = cavity.half_chord(u, z)
        hit = chord > 0.0
        if np.any(hit):
            delta = _segment_integral(
                atmosphere, u[hit], z[hit], -chord[hit], chord[hit],
                cavity.density_factor, CHORD_SAMPLES,
            ) - _segment_integral(
                atmosphere, u[hit], z[hit], -chord[hit], chord[hit], 1.0, CHORD_SAMPLES,
            )
            brightness[hit] += delta
        if cavity.rim_width_kpc > 0.0:
            outer = cavity.half_chord(u, z, cavity.rim_width_kpc)
            shell = outer > chord
            if np.any(shell):
                excess = 2.0 * (
                    _segment_integral(
                        atmosphere, u[shell], z[shell], chord[shell], outer[shell],
                        cavity.rim_density_factor, CHORD_SAMPLES,
                    )
                    - _segment_integral(
                        atmosphere, u[shell], z[shell], chord[shell], outer[shell],
                        1.0, CHORD_SAMPLES,
                    )
                )
                brightness[shell] += excess
        path_lengths[cavity.side] = 2.0 * chord
        volumes[cavity.side] = cavity.volume_kpc3
    if not np.all(np.isfinite(brightness)) or np.any(brightness < 0.0):
        raise ValueError("synthetic brightness must be finite and non-negative")
    return SyntheticMap(brightness, horizontal, vertical, path_lengths, volumes, float(view_deg))


def bipolar_pair(
    *,
    semiaxis_along_jet_kpc: float,
    semiaxis_across_jet_kpc: float,
    center_z_kpc: float | None = None,
    density_factor: float = 0.01,
    rim_width_kpc: float = 0.0,
    rim_density_factor: float = 1.0,
) -> tuple[Spheroid, Spheroid]:
    """Two mirror-image cavities; by default each touches the nucleus."""

    center = semiaxis_along_jet_kpc if center_z_kpc is None else center_z_kpc
    return tuple(
        Spheroid(
            sign * center,
            semiaxis_along_jet_kpc,
            semiaxis_across_jet_kpc,
            density_factor,
            rim_width_kpc,
            rim_density_factor,
        )
        for sign in (-1.0, 1.0)
    )  # type: ignore[return-value]
