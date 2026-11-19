from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import measure_outer_tracer_gravity as outer
from measure_q031_fluxes import Grid, ControlBox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/science/assets/outer_tracer_gravity_2026-11-19"))
import replay_compact as compact


def test_nonuniform_native_slabs_raw_faces_and_vector_work(tmp_path):
    nodes = [np.array(e, dtype=float) for e in ([-4,-3,-1,.5,2,5], [-3,-1,.5,4], [-4,-3,1,2,6])]
    axes = [(e[:-1] + e[1:])/2 for e in nodes]
    widths = [np.diff(e) for e in nodes]
    grid = Grid(*axes, *widths, *nodes)
    z, y, x = np.meshgrid(*axes[::-1], indexing="ij")
    velocity_sign = np.sign(z)
    rho = 2. + .1*x
    tracer = np.full_like(z, 2.e-4)
    tracer[2,1,2] = 1.
    tracer[0,0,0] = 0.
    boxes = {1: ControlBox(1,3,1,1,1,2,1,3,1,1,1,2,6,1)}
    profile = tmp_path / "gravity.dat"
    # A different fifth column detects reading the unused mass-based acceleration.
    np.savetxt(profile, [[0.,1.,1.,1.,9.,0.], [10.*outer.SOLVER_LENGTH_CM,1.,1.,1.,9.,-20.]])
    fields = dict(rho=rho, tr1=tracer, vx1=x*velocity_sign, vx2=y*velocity_sign, vx3=z*velocity_sign)
    with h5py.File(tmp_path / "slabs.h5", "w") as h5:
        variables = h5.create_group("Timestep_12/vars")
        for name, values in fields.items():
            variables[name] = values
        result = outer.measure_snapshot(variables, grid, boxes, profile, shell_kpc=1.3, slab_depth=2,
                                        labelled_power_erg_s=1.e45)
        lightweight = outer.measure_snapshot(variables, grid, boxes, None, shell_kpc=1.3, slab_depth=3, gravity=False)
    assert result["tracer"] == lightweight["tracer"]
    assert result["face_tracer"] == lightweight["face_tracer"]
    assert lightweight["gravity"] == {}
    assert result["tracer"]["min_margin_raw_positive_kpc"] == 0.
    assert result["tracer"]["min_margin_above_threshold_kpc"] == 2.
    volume = widths[2][:,None,None] * widths[1][None,:,None] * widths[0][None,None,:]
    geometric_shell = np.prod([e[-1]-e[0] for e in nodes]) - np.prod([e[-1]-e[0]-2*1.3 for e in nodes])
    # The untagged corner is wholly in the shell and the bright test cell is wholly interior.
    shell_effective = geometric_shell - volume[0,0,0]
    shell = result["tracer"]["boundary_shell"]
    assert shell["dilute_cell_volume_kpc3"] == pytest.approx(shell_effective)
    assert shell["raw_tagged_mass_g"] == pytest.approx(shell["dilute_tagged_mass_g"])
    assert result["tracer"]["whole_grid"]["raw_tagged_mass_g"] == pytest.approx(np.sum(rho*tracer*volume)*outer.MASS_UNIT)
    face = result["face_tracer"]["x_negative"]
    area = widths[2][:,None] * widths[1][None,:]
    flux = -rho[:,:,0]*tracer[:,:,0]*fields["vx1"][:,:,0]*area*outer.MASS_FLUX_UNIT
    assert face["tagged_inward_g_s"] == pytest.approx(flux[flux < 0].sum())
    assert face["tagged_outward_g_s"] == pytest.approx(flux[flux > 0].sum())
    assert face["tagged_net_outward_g_s"] == pytest.approx(flux.sum())
    assert face["raw_positive_area_kpc2"] == pytest.approx(area.sum() - area[0,0])
    assert face["raw_positive_cell_volume_kpc3"] == pytest.approx((area.sum() - area[0,0])*widths[0][0])
    expected = -2.*(x*x+y*y+z*z)*velocity_sign*rho*volume*outer.MASS_UNIT*outer.UNIT_VELOCITY_CMS
    inside = np.zeros(z.shape, dtype=bool)
    inside[1:3,1,1:4] = True
    for key, mask in (("whole_grid", np.ones_like(inside)), ("inside_p1", inside), ("outside_p1", ~inside)):
        work = result["gravity"][key]
        assert work["inward_motion_erg_s"] == pytest.approx(expected[mask & (z < 0)].sum())
        assert work["outward_motion_erg_s"] == pytest.approx(expected[mask & (z > 0)].sum())
        assert work["net_erg_s"] == pytest.approx(expected[mask].sum())
        assert work["net_over_labelled_power"] == pytest.approx(expected[mask].sum()/1.e45)


def test_subnormal_positive_support_and_empty_threshold():
    nodes = np.array([-2., 0., 2.])
    centres = np.array([-1., 1.])
    widths = np.diff(nodes)
    grid = Grid(centres, centres, centres, widths, widths, widths, nodes, nodes, nodes)
    shape = (2,2,2)
    fields = {key: np.zeros(shape, dtype=np.float32) for key in ("rho","tr1","vx1","vx2","vx3")}
    fields["rho"][:] = 1.
    fields["tr1"][0,0,0] = np.nextafter(np.float32(0), np.float32(1))
    result = outer.measure_snapshot(fields, grid, {}, None, gravity=False)
    assert result["tracer"]["min_margin_raw_positive_kpc"] == 0.
    assert result["tracer"]["min_margin_above_threshold_kpc"] is None
    assert result["tracer"]["boundary_shell"]["dilute_tagged_mass_g"] > 0.
    fields["tr1"][0,0,0] = -1.e-20
    with pytest.raises(ValueError, match="invalid raw density or tracer"):
        outer.measure_snapshot(fields, grid, {}, None, gravity=False)


def test_native_join_matches_regions_and_requires_both_annual_endpoints():
    def epoch(i, inward, outward):
        row = dict(age_myr=i,tagged_inward_g_s=-i,tagged_outward_g_s=0.,tagged_net_outward_g_s=-i)
        return row, {"outside_p4":dict(inward_motion_erg_s=inward,outward_motion_erg_s=outward,net_erg_s=inward+outward)}
    epochs = {("C-HI",0):epoch(0,0.,-2.), ("C-HI",1):epoch(1,2.,-4.),
              ("C-HI",3):epoch(3,2.,-4.), ("C-HI",4):epoch(4,2.,-4.)}
    intervals = [dict(case="C-HI",start_index=i,end_index=i+1,start_myr=i,end_myr=i+1,
                      labelled_energy_erg=4.*compact.SECONDS_PER_MYR,padding=4,nozzle_method="centered_primitives",
                      boundary_method="outer_active_cell",rule="trapezoid",inferred_gravity_work_over_label=-.2,
                      outside_total_residual_over_label=-.1) for i in range(4)]
    joined = compact.join_native_work(epochs,intervals)
    assert [r["end_index"] for r in joined] == [1,4]
    assert joined[0]["direct_net_work_over_label"] == pytest.approx(-.5)
    assert joined[0]["direct_minus_continuity_work_over_label"] == pytest.approx(-.3)
    assert joined[0]["hydro_balance_minus_direct_work_over_label"] == pytest.approx(.2)
    limits = {("C-HI",b,rule):dict(interval_signed_tracer_transport_lower_g=-5.*compact.SECONDS_PER_MYR,
                                    interval_signed_tracer_transport_upper_g=0) for b in (1,4) for rule in compact.RULES}
    fluxes = compact.join_native_mass(epochs,intervals,limits)
    assert len(fluxes) == 6
    assert fluxes[1]["cumulative_tagged_net_outward_over_label"] == fluxes[1]["tagged_net_outward_over_label"]
    assert fluxes[-1]["tagged_net_outward_over_label"] < 0
    assert fluxes[-1]["cumulative_tagged_net_outward_over_label"] is None
