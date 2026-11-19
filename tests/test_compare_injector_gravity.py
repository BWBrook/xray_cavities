from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts/science"))
import compare_injector_gravity as exact
from measure_outer_tracer_gravity import measure_snapshot
from measure_q031_fluxes import Grid, ControlBox
from snapshot_energy import load_environment


def test_sphere_and_padded_work_match_independent_cell_sum_and_native_reduction(tmp_path):
    edges = np.linspace(-1.5,1.5,7)
    centres = (edges[1:]+edges[:-1])/2
    widths = np.diff(edges)
    grid = Grid(centres,centres,centres,widths,widths,widths,edges,edges,edges)
    z,y,x = np.meshgrid(centres,centres,centres,indexing="ij")
    rho = 2.+z
    flow = np.sign(z)
    fields = dict(rho=rho,vx1=flow*x,vx2=flow*y,vx3=flow*z,tr1=np.zeros_like(z))
    arrays = {**fields,**{d:centres for d in "xyz"},**{d+"_edges":edges for d in "xyz"}}
    path = tmp_path/"gravity.csv"
    radii_kpc = np.arange(5.)
    a = -2.e-9*radii_kpc
    np.savetxt(path,np.column_stack((radii_kpc*exact.SOLVER_LENGTH_CM,*[np.ones(5)]*3,a,a)))
    env = load_environment(path)
    n, usphere, wsphere, wpadded = exact.patch_terms(arrays,env,np.column_stack((radii_kpc,a)),.75)
    assert n == 8
    inside, orbit_inward, orbit_outward = [], [], []
    for k,j,i in np.ndindex(z.shape):
        coord = [x[k,j,i],y[k,j,i],z[k,j,i]]
        r = np.linalg.norm(coord)
        side = np.sign(coord[2])
        m = rho[k,j,i]*.5**3*exact.MASS_UNIT
        w = -2.e-9*m*exact.UNIT_VELOCITY_CMS*side*r*r
        if r <= .75:
            inside.append(m*float(env.potential_at_radius(np.array(r*exact.UNIT_LENGTH_CM))))
        elif side < 0.:
            orbit_inward.append(w)
        else:
            orbit_outward.append(w)
    assert usphere == pytest.approx(sum(inside))
    boxes = {4:ControlBox(0,5,0,5,0,5,1,4,1,4,1,4,8,4)}
    saved = measure_snapshot(fields,grid,boxes,path,slab_depth=2)
    assert wpadded == pytest.approx([saved["gravity"]["inside_p4"][k] for k in exact.WORK_FIELDS])
    outside = [saved["gravity"]["whole_grid"][k]-w for k,w in zip(exact.WORK_FIELDS,wsphere,strict=True)]
    assert outside == pytest.approx([sum(orbit_inward),sum(orbit_outward),sum(orbit_inward+orbit_outward)])


def test_two_surface_signs_and_missing_direct_work():
    # An equal mass of 2 crosses both surfaces outward at potentials 7 and 3.
    # A 3-erg storage increase outside the source gives 11 erg of negative work.
    parts = (8.,5.,2.*7.,2.*3.,20.,-.1)
    balanced = exact.compare_interval(*parts,direct=-11./20.)
    assert balanced["potential_continuity_work_over_label"] == pytest.approx(-.55)
    assert balanced["direct_minus_continuity_work_over_label"] == pytest.approx(0.)
    offset = exact.compare_interval(*parts,direct=-.5)
    assert offset["direct_minus_continuity_work_over_label"] == pytest.approx(.05)
    assert offset["hydro_balance_minus_direct_work_over_label"] == pytest.approx(-.15)
    pending = exact.compare_interval(*parts,direct=None)
    assert pending["potential_continuity_work_over_label"] == pytest.approx(-.55)
    assert pending["direct_minus_continuity_work_over_label"] is None
