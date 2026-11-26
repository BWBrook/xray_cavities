import itertools
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import check_aperture_mass_budget as mass


def test_public_patches_and_temporally_constant_maintained_density():
    rates = mass.public_rates(json.loads(mass.checked(mass.VERIFICATION, mass.PINS["injector_verification"])))
    stocks = mass.csv_rows(mass.checked(mass.MAINTAINED, mass.MAINTAINED_SHA))
    assert len(stocks) == len(rates) == 201
    for c, last in mass.CASES.items():
        rows = [r for r in stocks if r["case"] == c]
        assert [int(r["snapshot_index"]) for r in rows] == list(range(last + 1))
        assert len({r["selected_native_rho_sha256"] for r in rows}) == 1
        assert len({r["maintained_mass_g"] for r in rows}) == 1
        assert all(int(r["maintained_cell_count"]) == 14328 for r in rows)
        assert all(r["patch_sha256"] == rates[c, i]["patch_sha256"] for i, r in enumerate(rows))


def test_signed_balance_and_cancellation_over_two_intervals():
    label = 4e43 / (.1*mass.UNIT_VELOCITY_CMS)**2 * mass.SECONDS
    sources = {("C-LO", i): {"age_myr": float(i), "cap": 2., "stationary": stationary, "net": 2.+stationary,
                             "maintained_mass_g": stored*label}
               for i, (stationary, stored) in enumerate(((-1., 4.), (-1., 4.5), (-5., 4.25)))}
    rows = []
    for aperture, method, rule in itertools.product(mass.APERTURES, mass.METHODS, mass.WEIGHTS):
        cumulative = {}
        for i, (change, motion, outward, injected) in enumerate(((3.5, .5, -1.5, 1.), (1.5, 1.25, -1., -1.)), 1):
            row = dict(case="C-LO", start_index=i-1, end_index=i, start_age_myr=float(i-1), end_age_myr=float(i),
                       aperture=aperture, face_method=method, integration_rule=rule, end_geometry_complete=True,
                       end_cocoon_contacts_domain=False, mass_change_minus_membership_plus_outward_g=(change-motion+outward)*label)
            for k, v in zip((*mass.TERMS[:4], "labelled_mass_g"), (change, motion, outward, injected, 1.), strict=True):
                row[k] = v*label
                cumulative[k] = cumulative.get(k, 0.) + row[k]
                row[f"cumulative_{k}"] = cumulative[k]
            rows.append(row)
    output = mass.case_balances("C-LO", 2, rows, sources)
    assert len(output) == 32
    primary = [r for r in output if r["aperture"] == "R100" and r["face_method"] == mass.METHODS[0]
               and r["integration_rule"] == "symmetric_fixed"]
    assert primary[0]["mass_residual_over_label"] == pytest.approx(0., abs=1e-14)
    assert primary[1]["mass_residual_over_label"] == pytest.approx(.5)
    assert primary[1]["mass_residual_over_signed_delivery"] == pytest.approx(-.5)
    assert primary[1]["cumulative_mass_residual_over_signed_delivery"] is None
    assert primary[1]["cumulative_mass_residual_over_label"] == pytest.approx(.25)
    assert primary[1]["cumulative_mass_residual_over_abs_aperture_and_injector_sectors"] == pytest.approx(.5/10.5)
    with pytest.raises(ValueError, match="Incomplete cumulative mass history"):
        mass.case_balances("C-LO", 2, rows[1:], sources)
