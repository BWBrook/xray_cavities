import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/science"))
import check_aperture_flux_cadence as cadence


def test_triangle_on_irregular_cadence_and_symmetric_radius_mean():
    times = [0., .015, .04, .07, .19, .3, .52, .61, .84, .995, 1.]
    states = []
    for i, t in zip(cadence.INDICES, times, strict=True):
        triangle = t/.3 if t <= .3 else (1-t)/.7
        surface = {}
        for name in cadence.APERTURES:
            for epoch, amplitude in ((10,4.), (11,-2.)):
                baseline = -3. if name == "R300" else 1.
                surface[f"{name}_at_{epoch}"] = {"centred_flux": {r:baseline+amplitude*triangle for r in cadence.RATES}}
        states.append({"index":i, "age_myr":t, "surfaces":surface})
    result = cadence.integrate(states)
    for name, base in (("R100",1.), ("R300",-3.)):
        for epoch, average_perturbation in ((10,2.), (11,-1.)):
            r = result["fixed"][f"{name}_at_{epoch}"]["total_energy_outward_erg"]
            assert r["annual"] == pytest.approx(base*cadence.SECONDS_PER_MYR)
            assert r["subinterval_trapezoids"] == pytest.approx((base+average_perturbation)*cadence.SECONDS_PER_MYR, abs=0.02)
        r = result["mean_of_two_fixed_surfaces"][name]["total_energy_outward_erg"]
        assert r["refined_minus_annual"] == pytest.approx(.5*cadence.SECONDS_PER_MYR)
    with pytest.raises(ValueError, match="nine interior"):
        cadence.integrate(states[:3]+states[4:])


def test_compact_identity_and_production_previous_next_comparison():
    assets = ROOT / "docs/science/assets"
    frozen = cadence.registration(assets / "aperture_transport_2026-11-26")
    compact = assets / "low_power_entropy_result_2026-11-23/compact_inputs.zip"
    records = cadence.read_restart(compact, frozen)
    assert all(b["step"] > a["step"] for a,b in zip(records,records[1:]))
    for epoch, measured_row in zip(cadence.ENDPOINTS, (records[0],records[-1]), strict=True):
        snap = frozen["snapshots"][epoch]
        identity = {"case":"C-LO", "index":epoch,"actual_age_myr":snap["age_myr"], "registration_sha256":cadence.REGISTRATION_SHA,
                    "native_sha256":snap["native_sha256"], "fixed_sha256":snap["fixed_sha256"]}
        check = {"age_myr":measured_row["age_myr"], "surfaces":{}}
        production = {"identity":identity, "measurement":{"apertures":{}}}
        for name in cadence.APERTURES:
            production["measurement"]["apertures"][name] = {"surfaces":{}}
            for radius_epoch in cadence.ENDPOINTS:
                spec = frozen["snapshots"][radius_epoch]["apertures"][name]
                role = ("current" if epoch==radius_epoch else ("next" if epoch==10 else "previous"))
                value = spec["raw_radius_kpc"] * 1.e12
                rates = {r:value for r in cadence.RATES}
                geometry = {"cell_count":spec["cell_count"], "volume_kpc3":spec["volume_kpc3"],"radius_kpc":spec["raw_radius_kpc"]}
                check["surfaces"][f"{name}_at_{radius_epoch}"] = {**geometry,"face_count":17,"area_kpc2":2.,
                        "centred_flux":dict(rates),"sum_absolute_face_contributions":{r:2*abs(value) for r in cadence.plane.RATES}}
                production["measurement"]["apertures"][name]["surfaces"][role] = {
                    **geometry, "geometry":{"total":{"face_count":17,"area_kpc2":2.}},
                    "flux":{"centered_primitives":{"total":dict(rates)}}}
        result=cadence.compare_endpoint(frozen,epoch,check,production)
        assert len(result)==28 and max(r["scaled_absolute_difference"] for r in result)==0
        primary = production["measurement"]["apertures"]["R100"]["surfaces"]["current"]
        primary["flux"]["centered_primitives"]["total"][cadence.RATES[-1]] *= 1.01
        with pytest.raises(ValueError, match="endpoint mismatch"):
            cadence.compare_endpoint(frozen,epoch,check,production)
