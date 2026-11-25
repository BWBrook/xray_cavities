import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import project_ghi20_midplane_slabs as pilot


def test_native_slab_intersections_and_default_domain():
    widths, records = pilot.slab_widths([-50, -25, -4, 14, 50])
    expected = {"full": [25, 21, 18, 36], "slab30": [5, 21, 18, 16], "slab10": [0, 6, 14, 0]}
    for key, lengths in expected.items():
        np.testing.assert_array_equal(widths[key], lengths)
        assert records[key]["integrated_width_kpc"] == sum(lengths)
    assert [c["index_y"] for c in records["slab10"]["partial_cells"]] == [1, 2]
    assert [c["index_y"] for c in records["slab30"]["partial_cells"]] == [0, 3]
    aligned, saved = pilot.slab_widths([-30, -10, 0, 10, 30])
    assert saved["slab10"]["partial_cells"] == []
    np.testing.assert_array_equal(aligned["slab30"], aligned["full"])
    with pytest.raises(ValueError, match="outside"):
        pilot.slab_widths([-25, 0, 40])
    with pytest.raises(ValueError, match="Invalid"):
        pilot.slab_widths([-50, 10, 0, 50])


def test_two_epochs_binary_tracer_and_partial_volume_on_rectilinear_hdf5(tmp_path):
    xe, ye, ze = (np.array(a, dtype=float) for a in ([-9, -3, 2, 12], [-50, -25, -4, 14, 50], [-9, 0, 20]))
    mids = [(e[1:] + e[:-1]) / 2 for e in (xe, ye, ze)]
    grid = pilot.emission.Grid(*mids, np.diff(xe), np.diff(ye), np.diff(ze), xe, ye, ze, "synthetic edges")
    z, y, x = np.indices((2, 4, 3))
    rho, prs = 1.0 + 100 * z + 10 * y + x, 3.0 + 2 * x + y
    rho0, prs0 = 7.0 + 5 * z + 2 * y + x, np.ones(z.shape)
    tr = np.zeros(z.shape)
    tr[0, 0, 0], tr[0, 1, 1], tr[0, 2, 1], tr[1, 3, 2] = .4, .002, .9, 1.
    tr[1, 0, 2], tr[1, 2, 0] = .001, .0005
    factor = 4.0

    def signed_emissivity(density, pressure):
        values = density - 3 * pressure
        return values, {"negative": values < 0}

    with h5py.File(tmp_path / "synthetic.h5", "w") as file:
        cur, initial = file.create_group("now"), file.create_group("initial")
        for g, fields in ((cur, {"rho": rho, "prs": prs, "tr1": tr}),
                          (initial, {"rho": rho0, "prs": prs0, "tr1": np.ones(z.shape)})):
            for key, values in fields.items():
                g[key] = values
        maps, counts = pilot.project(cur, initial, grid, signed_emissivity, factor)

    assert counts["tracer_boundary_face_cells"] == {
        "x_min": 1, "x_max": 1, "y_min": 1, "y_max": 1, "z_min": 3, "z_max": 1}
    for depth, span in {"full": [25, 21, 18, 36], "slab30": [5, 21, 18, 16], "slab10": [0, 6, 14, 0]}.items():
        expected = {key: np.zeros((2, 3)) for key in pilot.FULL_REFERENCE}
        native_volume = [0., 0.]
        for i, j, k in np.ndindex(tr.shape):
            current_flux = (rho[i, j, k] - 3 * prs[i, j, k]) * factor * span[j]
            initial_flux = (rho0[i, j, k] - 3 * prs0[i, j, k]) * factor * span[j]
            expected["current"][i, k] += current_flux
            expected["initial"][i, k] += initial_flux
            if (i, j, k) in ((0, 0, 0), (0, 1, 1), (0, 2, 1), (1, 3, 2)):
                expected["tracer_path"][i, k] += span[j]
                expected["current_lobe"][i, k] += current_flux
                expected["initial_on_current_lobe"][i, k] += initial_flux
                native_volume[i] += span[j] * (xe[k+1] - xe[k]) * (ze[i+1] - ze[i])
        for field, values in expected.items():
            np.testing.assert_array_equal(maps[f"{field}_{depth}"], values)
        assert counts["native_tracer_volume_kpc3"][depth] == {
            "negative_z": native_volume[0], "positive_z": native_volume[1], "both": sum(native_volume)}
        negative = (rho < 3 * prs) & (np.asarray(span)[None, :, None] > 0)
        assert counts["emissivity_cell_counts"][depth]["current"]["negative"] == negative.sum()
