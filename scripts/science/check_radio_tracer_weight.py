"""Reweight the original per-particle G-HI/20 radio emissivities in the production ray trace."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from astropy import units as u
from scipy.stats import spearmanr

from scripts.science import g_lo_snapshot_radio as radio
from scripts.science.snapshot_inference import fit_continuous_injection_spectrum, fit_injection_index


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
PRODUCTION = ASSETS / "four_case_selected_age_observables_2026-08-26/completed_radio_pair_1/G-HI"
BREAKS = ASSETS / "four_case_boundary_spectral_field_review_2026-08-28/spectral_break_frequencies.csv"
LEGACY = ASSETS / "q029_binary_native_refresh_2026-09-06/power_refresh/age_power_method_summary.csv"
AGES = [(0, 1), (1, 5), (5, 10), (10, 20)]
FREQ = radio.FREQUENCIES_GHZ


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def compare(source, particles, output):
    from plutokore.radio import praise, raytracing

    modules = {p.name: digest(p) for p in (Path(praise.__file__), Path(raytracing.__file__),
               Path(praise.__file__).with_name("praise2.py"))}
    if (modules["praise2.py"] != radio.EXPECTED_PRAISE2_SOURCE_SHA256
            or modules["raytracing.py"] != "597bf9241fee0eabc1f57a9715a338ee588157787dd2ad1edd939e7c17426f38"
            or modules["praise.py"] != "ce4b17cf40ecefabbbd4ef4330b75fb63c39d40c2ef1a05a6e5ac87131145bf4"):
        raise ValueError("The radio module hashes differ from the G-HI production archive")
    with np.load(source) as compressed:
        data = dict(compressed)
    fields = ("tracer", "tinj", "pressure", "density")
    parsed = radio.parse_particle_file(particles, fields=(*fields, "x1", "x2", "x3", "vx1", "vx2", "vx3"),
                                       vector_components={"last_shock_time": 2})
    aligned = radio.align_particle_ids(parsed.ids, data["ids"])
    for field in (*fields, "last_shock_time"):
        np.testing.assert_array_equal(parsed.fields[field][aligned], data[field])
    n = len(aligned)
    if particles.name != "particles.2000.dbl" or n != 78918 or parsed.header.time != data["times"]:
        raise ValueError("The geometry differs from the production G-HI/20 radio source")
    tracer = data["tracer"]
    if not np.all(np.isfinite(tracer) & (tracer > 0)):
        raise ValueError("A zero or invalid tracer requires rerunning the emissivity model for those particles")
    coords = np.column_stack([parsed.fields[k][aligned] for k in ("x1", "x2", "x3")])
    velocities = np.column_stack([parsed.fields[k][aligned] for k in ("vx1", "vx2", "vx3")])
    unit_myr = (radio.TIME_UNIT_S * u.s).to_value(u.Myr)
    age = {key:(data["times"] - data[key]) * unit_myr for key in ("tinj", "last_shock_time")}
    emit = data["full_loss"][:, 0] > 0
    labels, _ = radio._component_labels_from_original_z(coords)
    channels = {}
    cohorts = []
    correlation = {}
    for clock, years in age.items():
        correlation[clock] = float(spearmanr(years[emit], tracer[emit]).statistic)
        if not np.all((years >= 0) & (years < 20)):
            raise ValueError("The fixed age bins leave some particles out")
        for lo, hi in AGES:
            group = (years >= lo) & (years < hi) & emit
            cohorts.append(dict(clock=clock, lower_myr=lo, upper_myr=hi, emitting_particles=int(group.sum()),
                                median_tracer=float(np.median(tracer[group]))))
    for arm in ("weighted", "unit_tracer"):
        for model in ("lossless", "full_loss"):
            luminosity_density = data[model] if arm == "weighted" else data[model] / tracer[:,None]
            for i, nu in enumerate(FREQ):
                channels[(arm, model, nu)] = luminosity_density[:,i]
            if model == "full_loss":
                for c in cohorts:
                    years = age[c["clock"]]
                    belongs = (years >= c["lower_myr"]) & (years < c["upper_myr"])
                    for i in (0, 4):
                        channels[(arm, c["clock"], c["lower_myr"], FREQ[i])] = luminosity_density[:,i] * belongs
    map_cube, _ = radio._raytrace_component_cropped(
        coords=coords, velocity=velocities, emissivity=np.column_stack(list(channels.values())) * radio.EMISSIVITY_UNIT,
        labels=labels, view_deg=45, delta_r=radio.RAY_STEP_KPC, pixel_size=radio.PIXEL_SIZE_KPC,
        support_bound=radio.derive_support_bound(coords, multiplier=2), kd_jobs=1,
    )
    lum = dict(zip(channels, radio.luminosity_from_map(map_cube.to_value(radio.INTENSITY_UNIT),
                                                        pixel_size_kpc=radio.PIXEL_SIZE_KPC), strict=True))
    with (PRODUCTION/"radio_view_luminosity.csv").open() as f:
        baseline = {(r["loss_model"], float(r["frequency_ghz"])):float(r["luminosity_w_hz"]) for r in csv.DictReader(f)
                    if r["snapshot_index"] == "20" and r["view"] == "45deg"}
    errors = [abs(lum["weighted",model,nu]/reference - 1) for (model,nu), reference in baseline.items()]
    if len(baseline) != 10 or max(errors) > 1e-8:
        raise ValueError(f"Weighted luminosities do not reproduce the original view: {max(errors)}")
    spectra, fits = [], {}
    for arm in ("weighted", "unit_tracer"):
        values = {}
        for model in ("lossless", "full_loss"):
            values[model] = np.array([lum[arm,model,nu] for nu in FREQ])
            spectra += [dict(arm=arm, loss_model=model, frequency_ghz=nu, luminosity_w_hz=value)
                        for nu, value in zip(FREQ, values[model], strict=True)]
        alpha = fit_injection_index(FREQ, values["lossless"])
        fits[arm] = fit_continuous_injection_spectrum(FREQ, values["full_loss"], alpha_injection=alpha).as_dict()
        fits[arm]["slope_1p4_to_15_ghz"] = -np.log(values["full_loss"][-1]/values["full_loss"][2])/np.log(15/1.4)
        for clock in age:
            for nu in (FREQ[0], FREQ[-1]):
                counts = sum(lum[arm,clock,lo,nu] for lo,_ in AGES)
                np.testing.assert_allclose(counts, lum[arm,"full_loss",nu], rtol=1e-12, atol=0)
        for c in cohorts:
            for nu in (FREQ[0], FREQ[-1]):
                c[f"{arm}_fraction_{nu:g}GHz"] = lum[arm,c["clock"],c["lower_myr"],nu] / lum[arm,"full_loss",nu]
    with BREAKS.open() as f:
        valid = [r for r in csv.DictReader(f) if not (r["case"]=="G-HI" and r["snapshot_index"]=="50")]
    [original] = [r for r in valid if r["case"]=="G-HI" and r["snapshot_index"]=="20" and r["view"]=="45deg"]
    np.testing.assert_allclose(fits["weighted"]["fitted_break_ghz"], float(original["fitted_break_ghz"]), rtol=5e-7)
    if fits["weighted"]["break_status"] != original["break_status"]:
        raise ValueError("The weighted spectrum has the wrong censoring decision")
    with LEGACY.open() as f:
        old_detector = [r for r in csv.DictReader(f) if r["cavity_energy_model"] == "2.5pV"
                        and r["age_method"] == "spectral_age_mean_pressure"]
    receipt = dict(case="G-HI", view_deg=45, snapshot_index=20, particle_output=2000,
                   particle_age_myr=float(data["times"] * unit_myr), source_modules_sha256=modules,
                   input_slice_sha256=digest(source), native_particle_sha256=digest(particles),
                   reference_sha256={p.name:digest(p) for p in (PRODUCTION/"radio_view_luminosity.csv",
                                     PRODUCTION/"g_lo_snapshot_radio_metadata.json", BREAKS, LEGACY)},
                   native_file_particles=len(parsed.ids), active_radio_particles=n,
                   min_tracer=float(tracer.min()), max_tracer=float(tracer.max()), nonpositive_tracer=int(sum(tracer<=0)),
                   low_frequency_emitting_particles=int(emit.sum()),
                   particles_without_positive_last_shock_time=int(sum(data["last_shock_time"]<=0)),
                   legacy_selected_cavity_views=sum(int(r["total_cavity_rows"]) for r in old_detector),
                   legacy_spectral_age_upper_limits=sum(int(r["spectral_age_upper_limit_rows"]) for r in old_detector),
                   weighted_luminosity_max_relative_error=max(errors), original_fitted_break_ghz=float(original["fitted_break_ghz"]),
                   above_band_views=sum(r["break_status"]=="break_above_observed_band" for r in valid),
                   total_views=len(valid), emitting_particles_age_tracer_spearman=correlation, fits=fits)
    output.mkdir(parents=True, exist_ok=True)
    (output/"result.json").write_text(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n")
    write_csv(output/"spectra.csv", spectra)
    write_csv(output/"particle_age_bins.csv", cohorts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_slice", type=Path)
    parser.add_argument("particles", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    compare(args.source_slice, args.particles, args.output)
