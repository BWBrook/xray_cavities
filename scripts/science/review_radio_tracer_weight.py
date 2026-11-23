"""Independent refit of the two spectra in the radio tracer-weight check (RAD-01).

Reads only the public five-frequency spectra. Refits the injection index and
the continuous-injection break with a separate grid search over the same
delta-kernel shape, then asks how sharply five in-band points locate a break
that lies above the band. It does not rerun the per-particle substitution.

Run: uv run --no-project --with pandas python scripts/science/review_radio_tracer_weight.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs/science/assets"
SPECTRA = ASSETS / "radio_tracer_weight_check_2026-11-23/spectra.csv"
BINS = ASSETS / "radio_tracer_weight_check_2026-11-23/particle_age_bins.csv"
OUT = ASSETS / "radio_tracer_weight_review_2026-11-23"


def shape(nu, alpha, nu_break):
    p = 2 * alpha + 1
    x = np.sqrt(nu / nu_break)
    return nu ** (-p / 2) * np.where(x < 1, 1 - (1 - np.minimum(x, 1)) ** (p - 1), 1.0)


def rms(nu, lum, alpha, nu_break):
    r = np.log(lum) - np.log(shape(nu, alpha, nu_break))
    return float(np.sqrt(np.mean((r - r.mean()) ** 2)))


def main():
    spectra = pd.read_csv(SPECTRA)
    grid = np.exp(np.linspace(np.log(1e-4), np.log(1e5), 400001))
    result = {}
    for arm, g in spectra.groupby("arm"):
        lossless = g[g.loss_model == "lossless"].sort_values("frequency_ghz")
        full = g[g.loss_model == "full_loss"].sort_values("frequency_ghz")
        nu, lum = full.frequency_ghz.values, full.luminosity_w_hz.values
        alpha = -np.polyfit(np.log(lossless.frequency_ghz), np.log(lossless.luminosity_w_hz), 1)[0]
        score = np.array([rms(nu, lum, alpha, b) for b in grid[::40]])
        coarse = grid[::40]
        k = score.argmin()
        fine = np.exp(np.linspace(np.log(coarse[k - 1]), np.log(coarse[k + 1]), 20001))
        fine_score = np.array([rms(nu, lum, alpha, b) for b in fine])
        best = fine[fine_score.argmin()]
        within = coarse[score <= 2 * fine_score.min()]
        local = lambda a, b: float(np.log(lum[a] / lum[b]) / np.log(nu[b] / nu[a]))
        result[arm] = dict(
            alpha_injection=float(alpha), fitted_break_ghz=float(best), log_rms_at_best=float(fine_score.min()),
            break_range_with_rms_within_twice_best_ghz=[float(within.min()), float(within.max())],
            log_rms_at_15_ghz=rms(nu, lum, alpha, 15.0), log_rms_with_no_break=rms(nu, lum, alpha, 1e5),
            index_1p4_to_15=local(2, 4), index_4p5_to_15=local(3, 4), index_0p15_to_1p4=local(0, 2),
            full_loss_over_lossless=[float(v) for v in lum / lossless.luminosity_w_hz.values])
    result["unit_over_weighted_full_loss"] = [
        float(v) for v in spectra[(spectra.arm == "unit_tracer") & (spectra.loss_model == "full_loss")].luminosity_w_hz.values
        / spectra[(spectra.arm == "weighted") & (spectra.loss_model == "full_loss")].luminosity_w_hz.values]
    bins = pd.read_csv(BINS)
    sums = bins.groupby("clock")[[c for c in bins.columns if "fraction" in c]].sum()
    result["age_bin_fraction_sums"] = {clock: row.round(6).to_dict() for clock, row in sums.iterrows()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "refit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
