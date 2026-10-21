#!/usr/bin/env python3
"""Check saved low-power axial profiles and C-LO radial energy sums."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs/science/assets"
ARCHIVE = ASSETS / "four_case_fluid_snapshot_census_2026-08-25/remote_logs/four_case_fluid_snapshot_census_2026-08-25.tar.gz"
SHELLS = ASSETS / "cluster_background_and_age_validity_2026-08-26/review_products/C-LO/shell_energy_diagnostic.csv"
NATIVE = ASSETS / "q029_binary_native_refresh_2026-09-06/remote_analysis/C-LO/native_energy_selected_age.csv"
OUTPUT = ASSETS / "nojet_stability_followup_2026-10-21/outer_motion_and_central_gravity.json"
C_KM_S = 299792.458
INJECTION_ERG = 2e43 * 50 * 3.15576e13


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    sources = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in (ARCHIVE, SHELLS, NATIVE)}
    if sources[str(ARCHIVE.relative_to(ROOT))] != "b4dfb65a9231a53caec776f435ab819ce0b67c61fa9fd7f4aa866a5d7d83ece6":
        raise ValueError("Census archive differs from the accepted source")
    result = {
        "scope": "Saved compact products only; no raw HDF5 reread or remote job",
        "injected_bipolar_energy_50myr_erg": INJECTION_ERG,
        "sources_sha256": sources,
        "outer_motion_measure": "max_z abs(unweighted tube-mean vz), |z| > 100 kpc, tube radius 2 kpc; not a 3D maximum speed",
        "outer_axial_profiles": {},
    }
    with tarfile.open(ARCHIVE) as archive:
        for case in ("C-LO", "G-LO"):
            member = f"./{case}/per_snapshot/snapshot_0050_axial_profile.csv"
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError(f"Missing profile: {member}")
            rows = list(csv.DictReader(io.TextIOWrapper(handle)))
            if len(rows) != 1014 or any(not math.isclose(float(r["actual_time_myr"]), 50, abs_tol=1e-7) for r in rows):
                raise ValueError(f"Unexpected profile shape or age: {case}")
            for row in rows:
                if any(not math.isfinite(float(row[k])) for k in ("z_kpc", "vz_code", "baseline_vz_code")):
                    raise ValueError(f"Non-finite velocity or coordinate: {case}")
                if any(not math.isfinite(float(row[k])) or float(row[k]) <= 0
                       for k in ("rho_code", "pressure_code", "baseline_rho_code", "baseline_pressure_code")):
                    raise ValueError(f"Non-positive density or pressure: {case}")
            outer = [r for r in rows if abs(float(r["z_kpc"])) > 100]
            peak = max(abs(float(r["vz_code"])) for r in outer)
            maxima = [r for r in outer if math.isclose(abs(float(r["vz_code"])), peak, rel_tol=1e-12, abs_tol=0)]

            def sample(row: dict[str, str]) -> dict:
                return {
                    "z_kpc": float(row["z_kpc"]),
                    "tube_mean_vz_km_s": float(row["vz_code"]) * C_KM_S,
                    "tube_mean_density_ratio": float(row["rho_code"]) / float(row["baseline_rho_code"]),
                    "tube_mean_pressure_ratio": float(row["pressure_code"]) / float(row["baseline_pressure_code"]),
                }

            result["outer_axial_profiles"][case] = {
                "archive_member": member,
                "outer_profile_row_count": len(outer),
                "max_abs_tube_mean_vz_km_s": peak * C_KM_S,
                "max_abs_initial_tube_mean_vz_km_s": max(abs(float(r["baseline_vz_code"])) for r in outer) * C_KM_S,
                "maxima": [sample(r) for r in maxima],
                "representative_samples": [sample(min(outer, key=lambda r: abs(float(r["z_kpc"]) - z)))
                                           for z in (-249, -200, -150, -101, 101, 150, 200, 249)],
            }
    shells = [r for r in read_csv(SHELLS) if r["case"] == "C-LO" and int(r["snapshot_index"]) == 50]
    if [float(r["radius_min_kpc"]) for r in shells] != [0, 50, 100, 150, 200]:
        raise ValueError("Unexpected radial shell coverage")
    if [r["radius_max_kpc"] for r in shells] != ["50.0", "100.0", "150.0", "200.0", ""]:
        raise ValueError("Unexpected upper shell boundaries")
    if any(not math.isclose(float(r["injected_energy_erg"]), INJECTION_ERG, rel_tol=1e-12) for r in shells):
        raise ValueError("Shell injection normalization differs")
    native = [r for r in read_csv(NATIVE) if int(r["snapshot_index"]) == 50
              and r["side"] == "bipolar_total" and r["partition_method"] == "binary_threshold_1e-3"]
    if len(native) != 1:
        raise ValueError("Missing unique native reference")
    components = ("thermal", "kinetic", "gravitational")
    checks = {}
    for component in components:
        delta = math.fsum(float(r[f"{component}_delta_erg"]) for r in shells)
        reference = float(native[0][f"retained_{component}_delta_erg"])
        error = abs(delta - reference) / INJECTION_ERG
        if not math.isfinite(error) or error > 1e-8:
            raise ValueError(f"Radial/native disagreement: {component}")
        checks[f"{component}_difference_over_injection"] = error
    regions = {}
    for label, subset in (("inside_50_kpc", shells[:1]), ("inside_100_kpc", shells[:2]),
                          ("outside_100_kpc", shells[2:]), ("whole_grid", shells)):
        values = {f"delta_{c}_erg": math.fsum(float(r[f"{c}_delta_erg"]) for r in subset) for c in components}
        values["delta_total_erg"] = math.fsum(values.values())
        values.update({k.replace("_erg", "_over_injected"): v / INJECTION_ERG for k, v in list(values.items())})
        regions[label] = values
    result["C-LO_radial_energy_changes"] = regions
    result["C-LO_fraction_net_gravity_change_outside_100_kpc"] = regions["outside_100_kpc"]["delta_gravitational_erg"] / regions["whole_grid"]["delta_gravitational_erg"]
    result["radial_vs_native_checks"] = checks
    result["missing"] = ["G-LO central-100-kpc gravitational change", "10/30/80-kpc enclosed changes",
                         "full-3D outer-region maximum speeds and positions", "no-jet integrated energy drift"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
