from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/science'))
import project_source_exclusion_support as project


def native_grid():
    edges = np.array([-4., -1., 0., 1., 4.])
    mid = (edges[1:] + edges[:-1]) / 2
    width = np.diff(edges)
    return project.emission.Grid(mid, mid, mid, width, width, width, edges, edges, edges, 'synthetic_exact_edges')


def sample():
    grid = native_grid()
    dims = (len(grid.z), len(grid.y), len(grid.x))
    state = {key: np.zeros(dims) for key in ('tr1', 'vx1', 'vx2', 'vx3')}
    zero = {key: np.ones(dims) for key in ('prs', 'rho')}
    state.update({key: arr.copy() for key, arr in zero.items()})
    state['tr1'][1, 1, 1] = .75
    state['tr1'][2, 1, 2] = .001
    unit = 1e5 / project.budget.UNIT_VELOCITY_CMS
    for k in ('vx1', 'vx2', 'vx3'):
        state[k][1, 1, 1] = 200 * unit
    state['vx2'][2, 2, 2] = 101 * unit
    state['rho'][1, 1, 1] = 1.1
    state['prs'][2, 0, 0] = 1.1
    return grid, state, zero


@pytest.mark.parametrize('kind', ['science', 'initial_null'])
def test_original_tracer_and_all_speed_paths_on_stretched_sky_axes(kind):
    grid, state, zero = sample()
    old = project.adapter.make_views(grid)
    views = {}
    for angle, previous in old.items():
        depth = np.stack([project.emission.project_scalar(previous, (z > .001).astype(float), grid) for z in state['tr1']])
        ref = {'z_axis_kpc': grid.z, 'z_edges_kpc': grid.z_edges, 'horizontal_axis_kpc': previous.horizontal,
               'horizontal_edges_kpc': previous.u_edges,
               'path_C_kpc': np.zeros_like(depth) if kind == 'initial_null' else depth}
        views[angle] = project.make_view(grid, angle, ref, kind)
    counts, faces, volume = project.integrate(state, zero, grid, views, kind)
    assert counts['speed_ge_100'] == 2 and counts['speed_ge_300'] == 1
    assert counts['tracer_footprint'] == 1 and volume == 1.
    assert faces['boundary_thermo_changed'] == dict(x_min=1, y_min=1, z_min=0, x_max=0, y_max=0, z_max=0)
    for angle, view in views.items():
        assert np.array_equal(view.maps['speed_ge_300'], view.maps['tracer_footprint'])
        assert np.array_equal(view.maps['speed_ge_30'], view.maps['speed_ge_100'])
        assert np.array_equal(view.maps['pressure_changed'], view.maps['boundary_thermo_changed'])
        assert view.maps['density_changed'].any() and view.covered_tracer == pytest.approx(view.projected_tracer)
    assert views[0].maps['speed_ge_100'][2, 2] and not views[0].maps['tracer_footprint'][2, 2]
    assert views[0].maps['tracer_footprint'][1, 1]


def test_shifted_reference_edges_rejected_at_same_shape():
    grid, state, zero = sample()
    ref = dict(horizontal_axis_kpc=grid.x, horizontal_edges_kpc=grid.x_edges + .1, z_axis_kpc=grid.z,
               z_edges_kpc=grid.z_edges, path_C_kpc=np.zeros((4, 4)))
    with pytest.raises(ValueError, match='edges'):
        project.make_view(grid, 0, ref, 'science')
