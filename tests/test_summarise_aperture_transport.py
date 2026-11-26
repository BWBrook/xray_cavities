import csv
from contextlib import ExitStack
import gzip
import json
import math
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import summarise_aperture_transport as summary


def stocks(amount, is_sweep=False):
    # Each amount is a signed perturbation in a discrete shell.
    factors = {"mass_g": 1, "thermal_erg": 3, "kinetic_erg": -1, "gravitational_erg": 2, "total_energy_erg": 4}
    return {keys[int(is_sweep)]: amount*factors[k] for k, keys in summary.STOCK.items()}


def rates(mass):
    numbers = (mass, 3*mass, 2*mass, mass, -2*mass, 6*mass, 4*mass)
    return dict(zip(summary.RATES.values(), numbers, strict=True))


def mocked_surface(reg, net, box):
    domain_faces = int(not reg["geometrically_complete_in_domain_box"])
    def patch(n):
        return {"face_count": n, "area_kpc2": n*1.75}
    assert domain_faces or box == 0
    geom = {"internal": patch(6), "domain": patch(domain_faces), "total": patch(6+domain_faces)}
    faces = {name: patch(domain_faces if i == 0 else 0) for i, name in enumerate(summary.BOX_FACES)}
    flux = {}
    for method, inside in zip(summary.METHODS, (net-box, -1.5*(net-box)), strict=True):
        flux[method] = {"internal": rates(inside), "domain": rates(box), "total": rates(inside+box)}
    return dict(radius_kpc=reg["raw_radius_kpc"], cell_count=reg["cell_count"], volume_kpc3=reg["volume_kpc3"],
                domain_contact=bool(domain_faces), sphere_fully_inside_domain=reg["geometrically_complete_in_domain_box"],
                geometry=geom, box_faces=faces, flux=flux)


@pytest.mark.parametrize("reverse", [False, True], ids=["expanding", "shrinking"])
def test_four_samples_and_signed_stock_balance(reverse):
    # States contain cumulative masses (1, 3, 6) and (2, 6, 7) inside the three nested radii.
    start, end = (3, 7) if not reverse else (7, 3)
    sw0, sw1 = (3, 1) if not reverse else (-1, -3)
    sign = -1 if reverse else 1
    m = summary.stock_motion(stocks(start), stocks(end), stocks(sw0, True), stocks(sw1, True), summary.Audit())
    assert m["mass_g"] == dict(change=4*sign, sweep_at_start=sw0, sweep_at_end=sw1, symmetric_sweep=2*sign,
                               symmetric_fixed_change=2*sign, old_fixed_change=end-start-sw1, new_fixed_change=end-start-sw0)
    reg = {"raw_radius_kpc": 5, "cell_count": 10, "volume_kpc3": 10, "geometrically_complete_in_domain_box": False}
    samples = [mocked_surface(reg, n, box) for n, box in zip((2, -1, 4, 9), (0.5, -1., 1.5, 2.))]
    source = {"delivered_gas_erg": 32., "injector_potential_erg": 1., "maintained_stock_change_erg": 3.,
              "archived_grid_residual_erg": -2.}
    for rule, mass_out in (("symmetric_fixed", 7.), ("old_fixed", 6.), ("new_fixed", 8.), ("moving_endpoints", 11.)):
        integrated = summary.integrate_flux(samples, summary.METHODS[0], rule, 2.)
        outward = integrated["total"]
        assert outward["mass_outward_g"] == mass_out
        assert outward["thermal_advective_outward_erg"] == 3*mass_out
        assert outward["pressure_work_outward_erg"] == 2*mass_out
        assert outward["gravitational_outward_erg"] == -2*mass_out
        donor = summary.integrate_flux(samples, summary.METHODS[1], rule, 2.)
        assert donor["domain"] == integrated["domain"]
        assert donor["total"] != outward
        for k, v in outward.items():
            assert integrated["internal"][k] + integrated["domain"][k] == v
        result = summary.balance(m, integrated, source, rule)
        sweep = {"old_fixed": sw1, "new_fixed": sw0}.get(rule, 2*sign)
        residual = 4*(end-start-sweep+mass_out)-32-1-3
        assert result["aperture_residual_erg"] == residual
        assert result["aperture_minus_grid_residual_erg"] == residual+2
        assert result["mass_change_minus_membership_plus_outward_g"] == end-start-sweep+mass_out
        if not reverse and rule == "symmetric_fixed":
            assert result["aperture_residual_erg"] == 0


def mock_endpoint(case, i, source, stage):
    """Manufactured fluxes and sweeps only; production metadata exercise the public replay joins."""
    snapshots = source["snapshots"]
    snap = snapshots[i]
    roles = {k: j for k, j in (("previous", i-1), ("current", i), ("next", i+1)) if 0 <= j < len(snapshots)}
    apertures = {}
    for name in summary.APERTURES:
        windows = {role: snapshots[j]["apertures"][name] for role, j in roles.items()}
        surfaces = {role: mocked_surface(r, (i-2)*r["raw_radius_kpc"], 0 if r["geometrically_complete_in_domain_box"] else i)
                    for role, r in windows.items()}
        sweeps = {}
        for left, right in (("previous", "current"), ("current", "next")):
            if left not in windows or right not in windows:
                continue
            a, b = windows[left], windows[right]
            dcells = b["cell_count"]-a["cell_count"]
            sweeps[f"{left}_to_{right}"] = dict(cell_count_delta=dcells, volume_delta_kpc3=b["volume_kpc3"]-a["volume_kpc3"],
                                                **stocks(dcells*i, True))
        apertures[name] = {"surfaces": surfaces, "sweeps": sweeps}
    return {"identity": dict(case=case, index=i, actual_age_myr=snap["age_myr"], stage_sha256=stage,
                             registration_sha256=summary.PINS["registration"], initial_sha256=snapshots[0]["native_sha256"],
                             native_sha256=snap["native_sha256"], fixed_sha256=snap["fixed_sha256"]),
            "measurement": dict(apertures=apertures, internal_face_methods=list(summary.METHODS), domain_face_method=summary.FACE)}


def test_native_identity_cohort_and_units(tmp_path):
    source = json.loads(summary.REGISTRATION.read_bytes())["cases"]["G-HI"]
    stage = "a"*64
    data = mock_endpoint("G-HI", 1, source, stage)
    args = ("G-HI", 1, source, summary.PINS["registration"], stage, summary.Audit())
    summary.validate_endpoint(data, *args)
    data["identity"]["stage_sha256"] = "b"*64
    with pytest.raises(ValueError, match="identity or stage"):
        summary.validate_endpoint(data, *args)
    data["identity"]["stage_sha256"] = stage
    sample = data["measurement"]["apertures"]["R100"]["surfaces"]["current"]
    rates_ = sample["flux"][summary.METHODS[0]]["total"]
    rates_["mass_flux_outward_g_myr"] = rates_.pop("mass_flux_outward_g_s")
    with pytest.raises(ValueError, match="units"):
        summary.validate_endpoint(data, *args)
    with ExitStack() as stack:
        with pytest.raises(ValueError, match="Wrong endpoint cohort"):
            summary.endpoint_inventory(tmp_path, {"G-HI": 1}, stack)
        with ZipFile(tmp_path/"endpoints_G-HI.zip", "w") as archive:
            archive.writestr("G-HI/snapshot_0000.json", "{}")
        with pytest.raises(ValueError, match="ZIP member"):
            summary.endpoint_inventory(tmp_path, {"G-HI": 1}, stack)


def test_four_case_public_replay_on_manufactured_endpoints(tmp_path):
    stage = "d"*64
    cases = json.loads(summary.REGISTRATION.read_bytes())["cases"]
    bundles = tmp_path/"endpoints"
    bundles.mkdir()
    for case, source in cases.items():
        with ZipFile(bundles/f"endpoints_{case}.zip", "w", compression=ZIP_DEFLATED) as archive:
            for i in range(len(source["snapshots"])):
                path = ("" if case == "C-HI" else case+"/") + f"snapshot_{i:04d}.json"
                archive.writestr(path, json.dumps(mock_endpoint(case, i, source, stage)))
    output = tmp_path/"result"
    report = summary.run(bundles, output, stage_sha256=stage)
    assert (report["snapshots"], report["intervals"], report["stage_provenance"]) == (201, 197, "supplied digest")
    assert report["products"]["geometry.csv.gz"]["rows"] == 402
    assert sum(report["products"][f"transport_{c}.csv.gz"]["rows"] for c in cases) == 197*2*2*4*3
    assert report["numerical_checks"]["whole grid review"]["checks"] == 197
    rows = list(csv.DictReader((output/"primary_balances.csv").open()))
    ghi = [r for r in rows if r["case"] == "G-HI" and r["aperture"] == "R100"]
    assert len(rows) == 394 and len(ghi) == 47
    end = ghi[-1]
    assert (end["end_geometry_complete"], end["end_domain_contact"], end["end_cocoon_contacts_domain"]) == ("False", "True", "True")
    assert end["start_cocoon_contacts_domain"] == "False"
    assert float(end["cumulative_stock_change_erg"]) == pytest.approx(cases["G-HI"]["snapshots"][-1]["apertures"]["R100"]["stock"]["total_delta_erg"])
    total = math.fsum(float(r["aperture_residual_erg"]) for r in ghi)
    supplied = math.fsum(float(r["delivered_gas_erg"]) for r in ghi)
    assert float(end["cumulative_aperture_residual_over_delivered_gas"]) == total/supplied
    raw = gzip.decompress((output/"stock_motion.csv.gz").read_bytes())
    assert report["products"]["stock_motion.csv.gz"]["expanded_csv_sha256"] == summary.digest(raw)
    with pytest.raises(ValueError, match="identity or stage"):
        summary.run(bundles, tmp_path/"bad", stage_sha256="a"*64)
    assert not (tmp_path/"bad").exists()
