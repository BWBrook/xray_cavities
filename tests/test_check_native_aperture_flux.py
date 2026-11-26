import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import check_native_aperture_flux as check


def geometry():
    edges = [np.array(a, dtype=float) for a in ((-9, -5, -2, -.5, 1.5, 3, 6, 9),
                                                  (-10, -6, -3, -1, 1, 2, 4, 8),
                                                  (-12, -5, -2.5, -.75, 1.25, 2.5, 5, 12))]
    centres = [(e[:-1] + e[1:]) / 2 for e in edges]
    return centres, edges


def primitives(x, y, z):
    return (2 + x/30, 3 + y/40 + z/60, .012 + x/1000, -.009 + y/800, .005 - z/1300)


def test_affine_stretched_single_cell_and_constant_potential_shift():
    centres, edges = geometry()
    z, y, x = np.meshgrid(*centres[::-1], indexing="ij")
    fields = dict(zip(check.FIELDS, primitives(x, y, z), strict=True))
    radius = .7
    phi = lambda r: r*23
    a = check.scan(fields, centres, edges, {"one": radius}, phi)["one"]
    assert (a["cell_count"], a["volume_kpc3"], a["face_count"], a["area_kpc2"]) == (1, 8, 6, 24)
    mid = [.5, 0, .25]
    expected = np.zeros(5)
    for axis in range(3):
        for sign in (-1, 1):
            position = mid.copy()
            position[axis] += sign
            rho_code, p_code, *v_code = primitives(*position)
            v = np.array(v_code) * check.UNIT_VELOCITY_CMS
            rho = rho_code * check.UNIT_DENSITY_CGS
            pressure = p_code * check.UNIT_DENSITY_CGS * check.UNIT_VELOCITY_CMS**2
            volume_rate = 4 * check.UNIT_LENGTH_CM**2 * v[axis] * sign
            mass_rate = rho * volume_rate
            expected += [mass_rate, pressure*volume_rate/(check.GAMMA_GAS-1), pressure*volume_rate,
                         mass_rate*np.dot(v,v)/2, mass_rate*phi(np.linalg.norm(position)*check.UNIT_LENGTH_CM)]
    np.testing.assert_allclose([a["centred_flux"][k] for k in check.RATES], expected, rtol=3e-14)
    radii = {"inner": radius, "outer": 3.0}
    zero = check.scan(fields, centres, edges, radii, lambda r: r*0)
    shift = 2.7e13
    shifted = check.scan(fields, centres, edges, radii, lambda r: r*0+shift)
    for name, r in radii.items():
        inside = np.sqrt(x*x + y*y + z*z) <= r
        count = sum(np.count_nonzero(np.diff(np.pad(inside, 1), axis=i)) for i in (0,1,2))
        assert shifted[name]["face_count"] == count
        assert shifted[name]["cell_count"] == np.count_nonzero(inside)
        f = shifted[name]["centred_flux"]
        assert zero[name]["centred_flux"][check.RATES[-1]] == 0
        assert f[check.RATES[-1]] == pytest.approx(shift * f[check.RATES[0]], rel=2e-14)


def test_staged_hdf5_replay_and_source_identity(tmp_path):
    centres, edges = geometry()
    z, y, x = np.meshgrid(*centres[::-1], indexing="ij")
    directory = tmp_path / "requests/C-LO"
    directory.mkdir(parents=True)
    native = tmp_path / "data.0030.flt.h5"
    with h5py.File(native, "w") as f:
        for key, arrays in (("cell_coords", centres), ("node_coords", edges)):
            for label, arr in zip("XYZ", arrays, strict=True):
                f[f"{key}/{label}"] = arr
        group = f.create_group("Timestep_30")
        group.attrs["Time"] = 19.5
        for key, field in zip(check.FIELDS, primitives(x,y,z), strict=True):
            group[f"vars/{key}"] = field.astype("f4")
    np.savez(directory / "axes.npz", **dict(zip(["x","y","z","x_edges","y_edges","z_edges"], centres+edges, strict=True)))
    np.savetxt(directory / "atmosphere.csv", [[0,1,1,0,1e-8,1e-8],[1e24,1,1,0,1e-8,1e-8]])
    native_sha = check.sha(native)
    rec = {"index":30, "fixed_receipt_sha256":"fixed", "native":{"sha256":native_sha,"resolved_path":str(native)},
           "time_code":19.5, "timestep":"Timestep_30"}
    request = directory / "request.json"
    request.write_text(json.dumps({"history":[None]*30+[rec]}))
    volumes = np.diff(edges[2])[:,None,None] * np.diff(edges[1])[None,:,None] * np.diff(edges[0])[None,None,:]
    apertures = {}
    for name, radius in (("R100",3.0),("R300",.7)):
        mask = np.sqrt(x*x + y*y + z*z) <= radius
        apertures[name] = {"geometrically_complete_in_domain_box":True, "raw_radius_kpc":radius,
                           "cell_count":int(mask.sum()), "volume_kpc3":float(volumes[mask].sum())}
    frozen = {"input_request_sha256": check.sha(request),
              "static_sha256":{k:check.sha(directory/k) for k in ("axes.npz","atmosphere.csv")},
              "snapshots":[None]*30 + [{"index":30,"age_myr":30.,"fixed_sha256":"fixed","native_sha256":native_sha,
                                        "apertures":apertures}]}
    (tmp_path/"registration.json").write_text(json.dumps({"cases":{"C-LO":frozen}}))
    result = check.run(tmp_path)
    assert result["native_sha256"] == native_sha
    assert result["apertures"]["R300"]["face_count"] == 6
    with h5py.File(native, "r+") as f:
        f["Timestep_30/vars/vx3"][0,0,0] = 1
    with pytest.raises(ValueError, match="native file"):
        check.run(tmp_path)
