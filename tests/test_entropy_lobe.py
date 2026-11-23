import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import extract_spherical_energy_budget as reference
import reduce_entropy_lobes as comparison
from measure_entropy_lobe import CUTS, scan_lobe, storage_in_sphere
from measure_q031_fluxes import Grid


def test_promoted_tracer_cuts_and_cropped_r100_match_native_budget():
    edges = np.array([-5., -3., -1.5, -0.5, 0.5, 1.5, 3., 5.])
    centres = (edges[:-1] + edges[1:]) / 2
    widths = np.diff(edges)
    grid = Grid(*(centres,) * 3, *(widths,) * 3, *(edges,) * 3)
    shape = (7, 7, 7)
    cells = np.indices(shape)
    start = {k: np.full(shape, value, dtype="<f4") for k, value in
             (("rho", 1.), ("prs", 1.), ("vx1", 1e-4), ("vx2", 0.), ("vx3", 0.), ("tr1", 0.))}
    now = {k: v.copy() for k, v in start.items()}
    now["rho"] += (cells[0] + cells[1]) * 0.05
    now["prs"] += cells[2] * 0.1
    now["tr1"][3, 3, 1:6] = [*CUTS, .02, 0.0009]
    # Each velocity component is below 100 km/s, but their vector length exceeds it.
    now["vx1"][4, 4, 4] = now["vx2"][4, 4, 4] = 80e5 / reference.UNIT_VELOCITY_CMS
    probe = scan_lobe(now, grid, True)
    assert [r["cells"] for r in probe["lobes"]] == [4, 2, 1]
    vol = widths[:, None, None] * widths[None, :, None] * widths[None, None, :]
    for row, cut in zip(probe["lobes"], CUTS, strict=True):
        mask = now["tr1"].astype(float) > cut
        assert row["volume_kpc3"] == vol[mask].sum()
        assert row["enthalpy_2p5pv_erg"] == pytest.approx(
            2.5 * (vol[mask] * now["prs"][mask]).sum() * reference.UNIT_ENERGY_ERG, rel=1e-14)
    discovery = reference.discover_apertures(now, grid, safe_buffer_kpc=0)
    assert probe["r100_radius_kpc"] == discovery["thresholds"][100]["raw_radius_kpc"]
    assert probe["r100_defining_cell_zyx"] == [4, 4, 4]
    environment = SimpleNamespace(potential_at_radius=lambda r: r * 1e-8)
    historical = reference.integrate_budgets(current=now, initial=start, grid=grid, environment=environment,
                                              discovery=discovery, injected_energy_erg=1e55, safe_buffer_kpc=0)
    original = historical[100]["sphere_budget"]
    measured = storage_in_sphere(now, start, grid, environment, probe["r100_radius_kpc"])
    assert measured["cells"] == original["cell_count"]
    assert measured["complete_sphere"]
    for name in ("thermal", "kinetic", "gravitational", "total"):
        key = f"{name}_delta_erg"
        assert measured[key] == pytest.approx(original["delta_erg"][key], rel=1e-14)


def test_paired_lobe_readout_reproduces_from_archived_worker_results(tmp_path):
    comparison.reduce(comparison.OUTPUT / "snapshot_readout.json", tmp_path)
    for name in ("native_lobes.csv", "r100_storage.csv", "paired_effects.csv", "verification.json"):
        assert (tmp_path/name).read_bytes() == (comparison.OUTPUT/name).read_bytes()
    primary = [r for r in comparison.records(tmp_path/"paired_effects.csv") if r["tracer_cut"] == "0.001"]
    matched = [r for r in primary if r["timing"] == "off_interpolated_to_on"]
    assert len(matched) == 2
    assert all(float(r["off_saved_low_myr"]) < float(r["on_age_myr"]) < float(r["off_saved_high_myr"]) for r in matched)
    assert all(r["off_age_myr"] == r["on_age_myr"] for r in matched)
    assert all(r["off_age_myr"] == r["on_age_myr"] == "12.0" for r in primary if r["nominal_myr"] == "12")
