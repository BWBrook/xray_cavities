#!/usr/bin/env python3
"""G-HI/20 source/external emission and reconstructed-cavity filling diagnostic.

Current binary tracer membership and full speed define disjoint C/A/E masks.
Every initial reference uses those same current cells. Outputs remain diagnostic;
neither the velocity cuts nor the retained observer comparators are promoted.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Callable

import h5py
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.sparse import csr_matrix

import build_q031_native_emission as native
import extract_spherical_energy_budget as budget
from measure_q031_fluxes import Grid, read_grid
import xray_cavity_method_ladder as ladder

VIEWS = (0, 45, 90)
CUTS = (30, 100, 300)
METHODS = (ladder.SEED_GROW, 'deficit_threshold_observer_radial_0.05')
SIDES = ('negative_z', 'positive_z', 'bipolar_total')
CONVENTIONS = native.CONVENTIONS
REGIONS = ('C', *(name for cut in CUTS for name in (f'A_v{cut}', f'E_v{cut}')))
MASS_FACTOR = native.MASS_FACTOR
PRESSURE_VOLUME_FACTOR = budget.UNIT_ENERGY_ERG
BRIGHTNESS_FACTOR = native.BRIGHTNESS_VOLUME_FACTOR


def partition_masks(tracer: np.ndarray, velocities: tuple[np.ndarray, ...], cut: float) -> dict[str, np.ndarray]:
    tracer = np.asarray(tracer, dtype=np.float64)
    speed = np.sqrt(sum(np.asarray(v, dtype=np.float64)**2 for v in velocities)) * budget.UNIT_VELOCITY_CMS / 1e5
    if len(velocities) != 3 or not np.all(np.isfinite(tracer)) or not np.all(np.isfinite(speed)):
        raise ValueError('partition requires finite tracer and all three velocity components')
    cocoon = tracer > 1e-3
    moving = ~cocoon & (speed >= cut)
    return {'C': cocoon, 'A': moving, 'E': ~cocoon & ~moving}


def signed_ratio(numerator: float, denominator: float, scale: float) -> dict[str, Any]:
    if not all(math.isfinite(v) for v in (numerator, denominator, scale)) or scale < 0:
        raise ValueError('ratio inputs must be finite, with a nonnegative reference scale')
    near_zero = abs(denominator) <= 1e-12 * max(scale, np.finfo(float).tiny)
    return {'numerator': numerator, 'denominator': denominator,
            'ratio': None if near_zero else numerator / denominator,
            'near_zero_denominator': near_zero,
            'denominator_to_reference_scale': abs(denominator)/scale if scale else None}


def revolution_membership(mask_row: np.ndarray, u_edges: np.ndarray,
                          radius: np.ndarray, solid: str) -> np.ndarray:
    if solid not in ('W+', 'W-'):
        raise ValueError('solid must be W+ or W-')
    signed_radius = radius if solid == 'W+' else -radius
    indices = np.searchsorted(u_edges, signed_radius, side='right') - 1
    valid = (indices >= 0) & (indices < len(mask_row))
    selected = np.zeros(radius.shape, dtype=bool)
    selected[valid] = np.asarray(mask_row, dtype=bool)[indices[valid]]
    return selected


def closure(label: str, actual: np.ndarray | float, expected: np.ndarray | float,
            reference_scale: np.ndarray | float | None = None) -> dict[str, float]:
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError(f'{label}: incompatible or non-finite closure inputs')
    scale = max(float(np.max(np.abs(a), initial=0)), float(np.max(np.abs(b), initial=0)),
                float(np.max(np.abs(reference_scale), initial=0)) if reference_scale is not None else 0.,
                np.finfo(float).tiny)
    error = float(np.max(np.abs(a-b), initial=0))
    if error > 4e-11 * scale:
        raise ValueError(f'{label}: closure failed, error={error}, scale={scale}')
    return {'max_abs_error': error, 'error_to_scale': error/scale}


def checked_compact(record: dict) -> dict:
    path = Path(record['path'])
    if not path.is_absolute():
        raise ValueError('identity paths must be absolute')
    before = budget._stat_identity(path)
    digest = budget._sha256(path)
    if digest != record.get('sha256') or before != budget._stat_identity(path):
        raise ValueError(f'identity mismatch or mutation: {path}')
    return {**before, 'sha256': digest}


def bind_inherited_lineage(receipt: dict) -> dict:
    preflight = receipt.get('native_preflight', {})
    lineage = preflight.get('inherited_lineage', {})
    record = lineage.get('receipt')
    if (not isinstance(record, dict) or not {'path', 'sha256'} <= record.keys()
        or preflight.get('semantic_checks', {}).get('inherited_parent_source_restart_and_chain') != 'passed'):
        raise ValueError('G-HI emission requires a verified inherited-lineage binding')
    identity = checked_compact(record)
    accepted = json.loads(Path(identity['path']).read_text())
    if (accepted.get('schema_version') != 1 or accepted.get('status') != 'passed'
        or accepted.get('lineage') != 'accepted failed-run parent build/source plus validated 10 Myr home continuation'):
        raise ValueError('G-HI inherited-lineage receipt is not accepted')
    chain = accepted.get('snapshots', {}).get('analysis_chain', [])
    if [row.get('output_index') for row in chain] != list(range(51)):
        raise ValueError('G-HI inherited-lineage analysis chain is incomplete')
    for role, epoch, index in [('initial_h5', 'initial', 0), ('current_h5', 'current', 20)]:
        bound = receipt['inputs'][role]
        actual = budget._stat_identity(Path(bound['path']))
        if (any(chain[index].get(key) != value or bound.get(key) != value for key, value in actual.items())
            or any(chain[index].get(key) != receipt[epoch].get(key) for key in ('timestep', 'time_code'))):
            raise ValueError(f'G-HI emission snapshot differs from inherited lineage: {role}')
    budget._stable([identity])
    return identity


def unpack_mask(npz: Any, key: str, shape: tuple[int, int]) -> np.ndarray:
    if key not in npz:
        raise ValueError(f'missing retained mask: {key}')
    packed = np.asarray(npz[key])
    if packed.dtype != np.uint8 or packed.ndim != 1 or packed.size != math.ceil(math.prod(shape)/8):
        raise ValueError('invalid packed retained mask')
    return np.unpackbits(packed, count=math.prod(shape)).reshape(shape).astype(bool)


def original_observers(image: np.ndarray, horizontal: np.ndarray, z: np.ndarray) -> dict:
    seed = ladder.seed_grow_module.recover_hemisphere_seed_grow(image, horizontal, z)
    radial = ladder.observer_radial_background(image, horizontal, z)
    threshold = ladder.deficit_threshold(image, horizontal, z, background=radial,
                                        background_label='observer_radial', threshold=.05)
    return {
        METHODS[0]: {'mask': seed.observer_mask, 'background': seed.background,
                     'condition_number': seed.background_diagnostics.condition_number,
                     'support_threshold': seed.support_threshold},
        METHODS[1]: {'mask': threshold.mask, 'background': radial,
                     'condition_number': None, 'support_threshold': .05},
    }


def detect_fixed(image: np.ndarray, horizontal: np.ndarray, z: np.ndarray,
                 method: str, original: dict) -> np.ndarray:
    if method == METHODS[1]:
        return ladder.deficit_threshold(image, horizontal, z, background=original['background'],
                                        background_label='fixed_original_radial', threshold=.05).mask
    if method != METHODS[0]:
        raise ValueError('unsupported observer comparator')
    deficit = ladder.recovery.compute_fractional_deficit(image, original['background'])
    _, candidate = ladder._rois(horizontal, z)
    support = max(ladder.seed_grow_module.robust_outer_annulus_threshold(deficit, horizontal, z),
                  ladder.seed_grow_module.NUMERICAL_SUPPORT_EPS_MULTIPLIER*np.finfo(float).eps*original['condition_number'])
    hemispheres = ladder._hemispheres(z, image.shape)
    return np.logical_or.reduce([
        ladder.seed_grow_module._recover_hemisphere(side, deficit, candidate, hemispheres[side],
                                                    support, horizontal, z).mask
        for side in ladder.SIDES])


@dataclass
class View:
    angle: int
    horizontal: np.ndarray
    u_edges: np.ndarray
    retained_image: np.ndarray
    observers: dict
    operator: csr_matrix | None
    covered_area_xy: np.ndarray
    maps: dict[str, np.ndarray]
    native_integrals: dict[str, float]
    covered_integrals: dict[str, float]
    covered_absolute_integrals: dict[str, float]
    geometry_report: dict
    tracer_projection_indices: tuple[np.ndarray, np.ndarray] | None
    correction_contributions: dict


def build_projection(grid: Grid, angle: int, horizontal: np.ndarray) -> tuple[np.ndarray, csr_matrix | None, np.ndarray, dict]:
    if angle not in VIEWS:
        raise ValueError('only the three declared side-on azimuths are supported')
    horizontal = np.asarray(horizontal, dtype=float)
    if horizontal.ndim != 1 or horizontal.size < 2 or not np.all(np.diff(horizontal) > 0):
        raise ValueError('projected axis must be finite and strictly increasing')
    if angle == 0:
        if horizontal.shape != grid.x.shape or not np.allclose(horizontal, grid.x, rtol=native.TEXT_RTOL, atol=1e-10):
            raise ValueError('zero-degree sky axis differs from native X')
        edges = grid.x_edges.copy()
        operator = None
        covered = np.outer(grid.dy, grid.dx)
    else:
        edges = native.renderer.centres_to_edges(horizontal)
        cell, bins, weights = native.renderer.projected_overlap_contributions(
            x_edges=grid.x_edges, y_edges_chunk=grid.y_edges, u_edges=edges, view_angle_deg=angle)
        operator = csr_matrix((weights, (cell, bins)), shape=(len(grid.x)*len(grid.y), len(horizontal)))
        covered = np.asarray(operator.dot(np.diff(edges))).reshape(len(grid.y), len(grid.x))
    whole = np.outer(grid.dy, grid.dx)
    if np.any(covered < -1e-12*whole) or np.any(covered > whole*(1+1e-10)):
        raise ValueError('projected coverage is outside native cell area')
    report = {'operator': 'direct_y_exact_native_widths' if angle == 0 else 'edge_overlap_uniform_cell_projection',
              'native_edges': grid.edge_source,
              'centre_reconstructed_x_edge_max_difference_kpc': float(np.max(np.abs(native.renderer.centres_to_edges(grid.x)-grid.x_edges))),
              'centre_reconstructed_y_edge_max_difference_kpc': float(np.max(np.abs(native.renderer.centres_to_edges(grid.y)-grid.y_edges))),
              'native_xy_area_kpc2': float(whole.sum()), 'projected_covered_xy_area_kpc2': float(covered.sum()),
              'uncovered_native_xy_area_fraction': float(max(0., (whole.sum()-covered.sum())/whole.sum())),
              'projection_coverage_hold': bool(np.any(whole-covered > 1e-10*whole)),
              'native_edge_and_retained_sky_grid_policy': 'exact source edges; retained horizontal bins; explicit outer coverage loss'}
    return edges, operator, covered, report


def project_scalar(view: View, values: np.ndarray, grid: Grid) -> np.ndarray:
    if values.shape != (len(grid.y), len(grid.x)):
        raise ValueError('projection slab shape mismatch')
    if view.operator is None:
        return np.sum(values*grid.dy[:, None], axis=0)
    return np.asarray(view.operator.T.dot(values.ravel())).ravel()


def make_view(grid: Grid, angle: int, horizontal: np.ndarray, image: np.ndarray, observers: dict) -> View:
    edges, operator, covered, geometry = build_projection(grid, angle, horizontal)
    shape = (len(grid.z), len(horizontal))
    if image.shape != shape:
        raise ValueError('retained image/native sky shape mismatch')
    names = [f'path_{region}_kpc' for region in (*REGIONS, 'whole')]
    names += [f'brightness_{state}_{convention}_{region}' for state in ('current','initial')
              for convention in CONVENTIONS for region in (*REGIONS,'whole')]
    maps = {name: np.zeros(shape) for name in names}
    maps['tracer_max'] = np.full(shape, -np.inf)
    coo = operator.tocoo() if operator is not None else None
    indices = (coo.row, coo.col) if coo is not None else None
    contributions = {(method, side, state, convention, region, domain): np.zeros(2)
                     for method in observers for side in SIDES for state in ('current', 'initial')
                     for convention in CONVENTIONS for region in (*REGIONS, 'whole')
                     for domain in ('out_of_table', 'retained_negative')}
    return View(angle, horizontal, edges, image, observers, operator, covered, maps,
                {name: 0. for name in names}, {name: 0. for name in names},
                {name: 0. for name in names}, geometry, indices, contributions)


def observer_projection_weights(view: View, mask_row: np.ndarray, grid: Grid, iz: int) -> np.ndarray:
    pixel_widths = np.asarray(mask_row, dtype=float)*np.diff(view.u_edges)
    if view.operator is None:
        return grid.dy[:, None]*pixel_widths[None, :]*grid.dz[iz]
    return np.asarray(view.operator.dot(pixel_widths)).reshape(len(grid.y), len(grid.x))*grid.dz[iz]


def accumulate_corrections(view: View, iz: int, grid: Grid, masks: dict,
                           emission: dict, domains: dict) -> None:
    side = 'negative_z' if grid.z[iz] < 0 else 'positive_z' if grid.z[iz] > 0 else None
    sides = ('bipolar_total', side) if side is not None else ('bipolar_total',)
    weights = {method: observer_projection_weights(view, observer['mask'][iz], grid, iz)
               for method, observer in view.observers.items()}
    for state, fields in emission.items():
        for convention in CONVENTIONS:
            values = fields[convention]*BRIGHTNESS_FACTOR
            for domain, selected in domains[state].items():
                for method, weight in weights.items():
                    weighted = np.where(selected, values*weight, 0.)
                    for region in (*REGIONS, 'whole'):
                        piece = weighted if region == 'whole' else weighted[masks[region]]
                        contribution = np.array([np.sum(piece), np.sum(np.abs(piece))])
                        for hemisphere in sides:
                            view.correction_contributions[method, hemisphere, state, convention, region, domain] += contribution


def _fill_add(target: dict, selected: np.ndarray, cocoon: np.ndarray,
              rho: np.ndarray, pressure: np.ndarray, volume: np.ndarray) -> None:
    for kind, values, factor in [('volume_kpc3', np.ones_like(rho), 1.),
                                 ('mass_g', rho, MASS_FACTOR),
                                 ('pressure_integral_erg', pressure, PRESSURE_VOLUME_FACTOR)]:
        target[f'{kind}_denominator'] += float(np.sum((values*volume)[selected]))*factor
        target[f'{kind}_numerator'] += float(np.sum((values*volume)[selected & cocoon]))*factor


def integrate_native(current: h5py.Group, initial: h5py.Group, grid: Grid, views: dict[int, View],
                     emissivity: Callable[[np.ndarray, np.ndarray], tuple[dict, np.ndarray, dict]]) -> tuple[list[dict], dict]:
    radius = np.hypot(grid.y[:, None], grid.x[None, :])
    area_xy = np.outer(grid.dy, grid.dx)
    filling = {(angle, method, solid, side): {f'{kind}_{part}': 0. for kind in
               ('volume_kpc3','mass_g','pressure_integral_erg') for part in ('numerator','denominator')}
               for angle in views for method in METHODS for solid in ('W+','W-') for side in SIDES}
    correction = {state: {key: 0 for key in ('cells','any_out_of_table','raw_nonfinite',
                   *(f'{convention}_{flag}' for convention in CONVENTIONS for flag in ('nonfinite','negative')))}
                  for state in ('current','initial')}
    diagnostics = {'tracer_outside_unit_interval_count': 0, 'tracer_min': math.inf, 'tracer_max': -math.inf,
                   'native_component_boundary_cell_counts': {region: {face: 0 for face in
                       ('x_min','x_max','y_min','y_max','z_min','z_max')} for region in ('C', *(f'A_v{cut}' for cut in CUTS))},
                   'moving_ambient_is_not_causal_source_identification': True,
                   'speed_histogram_edges_km_s': [0., 1., 10., 30., 100., 300., 1000., None],
                   'disturbed_ambient_cell_count_by_speed': [0]*7,
                   'disturbed_ambient_volume_kpc3_by_speed': [0.]*7,
                   'disturbance_definition': 'current tracer-negative; abs(rho/rho0-1)>=0.01 OR abs(p/p0-1)>=0.01',
                   'correction_domain': correction}
    for iz, z in enumerate(grid.z):
        now = {name: np.asarray(current[name][iz,:,:],dtype=np.float64) for name in ('rho','prs','vx1','vx2','vx3','tr1')}
        zero = {name: np.asarray(initial[name][iz,:,:],dtype=np.float64) for name in ('rho','prs')}
        if any(not np.all(np.isfinite(value)) for value in [*now.values(), *zero.values()]):
            raise ValueError(f'non-finite native primitive at z={iz}')
        if any(np.any(state[name] <= 0) for state in (now,zero) for name in ('rho','prs')):
            raise ValueError(f'nonpositive native density/pressure at z={iz}')
        diagnostics['tracer_outside_unit_interval_count'] += int(np.count_nonzero((now['tr1']<0)|(now['tr1']>1)))
        diagnostics['tracer_min'] = min(diagnostics['tracer_min'], float(now['tr1'].min()))
        diagnostics['tracer_max'] = max(diagnostics['tracer_max'], float(now['tr1'].max()))
        partitions = {cut: partition_masks(now['tr1'], tuple(now[f'vx{i}'] for i in (1,2,3)), cut) for cut in CUTS}
        masks = {'C': partitions[30]['C'], **{f'{region}_v{cut}': partitions[cut][region] for cut in CUTS for region in ('A','E')}}
        for region, counts_by_face in diagnostics['native_component_boundary_cell_counts'].items():
            selected = masks[region]
            for face, edge in [('x_min',selected[:,0]),('x_max',selected[:,-1]),
                               ('y_min',selected[0]),('y_max',selected[-1])]:
                counts_by_face[face] += int(np.count_nonzero(edge))
            if iz == 0: counts_by_face['z_min'] += int(np.count_nonzero(selected))
            if iz == len(grid.z)-1: counts_by_face['z_max'] += int(np.count_nonzero(selected))
        speed = np.sqrt(sum(now[f'vx{i}']**2 for i in (1,2,3)))*budget.UNIT_VELOCITY_CMS/1e5
        disturbed = ~masks['C'] & ((np.abs(now['rho']/zero['rho']-1)>=.01)|(np.abs(now['prs']/zero['prs']-1)>=.01))
        volume = area_xy*grid.dz[iz]
        edges = [0.,1.,10.,30.,100.,300.,1000.,np.inf]
        counts = np.histogram(speed[disturbed], edges)[0]
        volumes = np.histogram(speed[disturbed], edges, weights=volume[disturbed])[0]
        diagnostics['disturbed_ambient_cell_count_by_speed'] = (np.asarray(diagnostics['disturbed_ambient_cell_count_by_speed'])+counts).tolist()
        diagnostics['disturbed_ambient_volume_kpc3_by_speed'] = (np.asarray(diagnostics['disturbed_ambient_volume_kpc3_by_speed'])+volumes).tolist()
        emission, domains = {}, {}
        for state, primitives in [('current',now),('initial',zero)]:
            values, _, flags = emissivity(primitives['rho'],primitives['prs'])
            emission[state] = values
            domains[state] = {'out_of_table': flags['any'],
                              'retained_negative': np.isfinite(values['retained_linear_before']) & (values['retained_linear_before'] < 0)}
            correction[state]['cells'] += now['rho'].size
            correction[state]['any_out_of_table'] += int(np.count_nonzero(flags['any']))
            correction[state]['raw_nonfinite'] += int(np.count_nonzero(flags['raw_nonfinite']))
            for convention in CONVENTIONS:
                before = values[f'{convention}_before']
                correction[state][f'{convention}_nonfinite'] += int(np.count_nonzero(~np.isfinite(before)))
                correction[state][f'{convention}_negative'] += int(np.count_nonzero(before<0))
        for angle, view in views.items():
            accumulate_corrections(view, iz, grid, masks, emission, domains)
            for region in (*REGIONS,'whole'):
                mask = np.ones_like(masks['C']) if region=='whole' else masks[region]
                fields = {f'path_{region}_kpc': (mask.astype(float),1.)}
                fields.update({f'brightness_{state}_{convention}_{region}': (emission[state][convention]*mask,BRIGHTNESS_FACTOR)
                               for state in ('current','initial') for convention in CONVENTIONS})
                for name,(values,scale) in fields.items():
                    view.maps[name][iz] = project_scalar(view,values,grid)*scale
                    view.native_integrals[name] += float(np.sum(values*volume))*scale
                    view.covered_integrals[name] += float(np.sum(values*view.covered_area_xy))*grid.dz[iz]*scale
                    view.covered_absolute_integrals[name] += float(np.sum(np.abs(values)*view.covered_area_xy))*grid.dz[iz]*scale
            if view.operator is None:
                view.maps['tracer_max'][iz] = np.max(now['tr1'],axis=0)
            else:
                cells, bins = view.tracer_projection_indices
                np.maximum.at(view.maps['tracer_max'][iz], bins, now['tr1'].ravel()[cells])
            for method, observer in view.observers.items():
                for solid in ('W+','W-'):
                    selected = revolution_membership(observer['mask'][iz],view.u_edges,radius,solid)
                    for side in SIDES:
                        if side=='bipolar_total' or (side=='negative_z' and z<0) or (side=='positive_z' and z>0):
                            _fill_add(filling[angle,method,solid,side],selected,masks['C'],now['rho'],now['prs'],volume)
        if iz % 32 == 0:
            print(f'GHI20_EMISSION_SLAB {iz}/{len(grid.z)}',flush=True)
    rows=[]
    for (angle,method,solid,side), values in filling.items():
        view=views[angle]; mask=view.observers[method]['mask'].copy()
        if side=='negative_z':mask[grid.z>=0]=False
        if side=='positive_z':mask[grid.z<=0]=False
        moments=native.exact_abs_u_moments(mask,view.u_edges,grid.z_edges)
        geometric=moments['positive_u_revolution_kpc3' if solid=='W+' else 'negative_u_revolution_kpc3']
        selected_bins=np.any(mask,axis=0)
        radii=np.maximum(view.u_edges[1:],0) if solid=='W+' else np.maximum(-view.u_edges[:-1],0)
        on_side=(view.u_edges[1:]>0) if solid=='W+' else (view.u_edges[:-1]<0)
        radius_max=float(np.max(radii[selected_bins&on_side],initial=0))
        domain_radius=min(abs(grid.x_edges[0]),abs(grid.x_edges[-1]),abs(grid.y_edges[0]),abs(grid.y_edges[-1]))
        radial_truncation=radius_max>domain_radius
        axial_truncation=bool(np.any(mask[[0,-1]][:,on_side]))
        row={'view_deg':angle,'method':method,'solid':solid,'hemisphere':side,**values,
             'geometric_revolution_volume_kpc3':geometric,
             'native_minus_geometric_volume_kpc3':values['volume_kpc3_denominator']-geometric,
             'radial_domain_truncation':radial_truncation,
             'axial_domain_truncation':axial_truncation,
             'domain_truncation':radial_truncation or axial_truncation,
             'domain_truncation_basis':'radius exceeds native inscribed circle or selected signed-solid z bins contact a native end face',
             'native_cell_denominator_used':True,
             'nondetection':not bool(np.any(selected_bins & on_side)),
             'filling_domain':'native full cells whose centres lie in the retained-mask revolution solid'}
        for kind in ('volume_kpc3','mass_g','pressure_integral_erg'):
            row[f'{kind}_share']=values[f'{kind}_numerator']/values[f'{kind}_denominator'] if values[f'{kind}_denominator'] else None
        rows.append(row)
    for angle in views:
        for method in METHODS:
            for side in SIDES:
                pair=[row for row in rows if row['view_deg']==angle and row['method']==method and row['hemisphere']==side and row['solid'] in ('W+','W-')]
                pooled={key:pair[0][key] for key in pair[0]}
                pooled['solid']='pooled_Wplus_Wminus'
                for kind in ('volume_kpc3','mass_g','pressure_integral_erg'):
                    for part in ('numerator','denominator'):
                        pooled[f'{kind}_{part}']=sum(row[f'{kind}_{part}'] for row in pair)
                    denominator=pooled[f'{kind}_denominator']
                    pooled[f'{kind}_share']=pooled[f'{kind}_numerator']/denominator if denominator else None
                for key in ('geometric_revolution_volume_kpc3','native_minus_geometric_volume_kpc3'):
                    pooled[key]=sum(row[key] for row in pair)
                for flag in ('domain_truncation','radial_domain_truncation','axial_domain_truncation'):
                    pooled[flag]=any(row[flag] for row in pair)
                pooled['nondetection']=all(row['nondetection'] for row in pair)
                pooled['filling_domain']='pooled sums of two reconstructed solids; overlap counted once in each solid, not a union'
                rows.append(pooled)
    return rows, diagnostics


def _side_mask(shape: tuple[int, int], z: np.ndarray, side: str) -> np.ndarray:
    selected = np.ones(shape,dtype=bool)
    if side=='negative_z':selected[z>=0]=False
    elif side=='positive_z':selected[z<=0]=False
    elif side!='bipolar_total':raise ValueError('unknown hemisphere')
    return selected


def finish_views(views: dict[int, View], grid: Grid) -> tuple[list[dict], list[dict], list[dict], dict]:
    attribution, recoveries, paths, reports = [], [], [], {}
    for angle, view in views.items():
        area = np.outer(grid.dz,np.diff(view.u_edges))
        checks = {}
        for name in view.native_integrals:
            checks[name] = closure(f'{angle}:{name}:covered integral',float(np.sum(view.maps[name]*area)),
                                   view.covered_integrals[name],view.covered_absolute_integrals[name])
        for cut in CUTS:
            regions=('C',f'A_v{cut}',f'E_v{cut}')
            checks[f'path_partition_v{cut}']=closure('path partition',sum(view.maps[f'path_{r}_kpc'] for r in regions),view.maps['path_whole_kpc'])
            for convention in CONVENTIONS:
                for state in ('current','initial'):
                    checks[f'{state}_{convention}_v{cut}']=closure('brightness partition',
                        sum(view.maps[f'brightness_{state}_{convention}_{r}'] for r in regions),
                        view.maps[f'brightness_{state}_{convention}_whole'],
                        sum(np.abs(view.maps[f'brightness_{state}_{convention}_{r}']) for r in regions))
        for convention in CONVENTIONS:
            for region in (*REGIONS,'whole'):
                view.maps[f'deficit_{convention}_{region}']=(view.maps[f'brightness_initial_{convention}_{region}']-
                                                            view.maps[f'brightness_current_{convention}_{region}'])
            for cut in CUTS:
                regions=('C',f'A_v{cut}',f'E_v{cut}')
                checks[f'deficit_{convention}_v{cut}']=closure('signed deficit partition',
                    sum(view.maps[f'deficit_{convention}_{r}'] for r in regions),view.maps[f'deficit_{convention}_whole'],
                    sum(np.abs(view.maps[f'brightness_{state}_{convention}_{r}']) for state in ('current','initial') for r in regions))
        total=view.maps['brightness_current_retained_linear_whole']
        difference=total-view.retained_image
        compatibility_scale=max(float(np.max(np.abs(total))),float(np.max(np.abs(view.retained_image))),np.finfo(float).tiny)
        maximum_relative=float(np.max(np.abs(difference)))/compatibility_scale
        reports[str(angle)]={'closure':checks, 'projection_geometry':view.geometry_report,
            'retained_map_max_abs_difference':float(np.max(np.abs(difference))),
            'retained_map_difference_to_peak':maximum_relative,
            'retained_map_compatibility_hold':maximum_relative>native.TEXT_RTOL,
            'retained_comparison_scope':'same axes and fixed retained masks; exact native edges can change projected totals',
            'native_volume_integrals':view.native_integrals,'covered_volume_integrals':view.covered_integrals,
            'covered_absolute_emissivity_integrals':view.covered_absolute_integrals,
            'uncovered_integrals':{key:view.native_integrals[key]-view.covered_integrals[key] for key in view.native_integrals}}
        truth=view.maps['path_C_kpc']>0
        if 'retained_tracer_mask' in view.maps:
            reports[str(angle)]['retained_tracer_disagreement_pixels'] = int(np.count_nonzero(truth != view.maps['retained_tracer_mask']))
        for convention in CONVENTIONS:
            image=view.maps[f'brightness_current_{convention}_whole']
            initial=view.maps[f'brightness_initial_{convention}_whole']
            baseline_refit=original_observers(image,view.horizontal,grid.z)
            for cut in CUTS:
                moving_deficit=view.maps[f'deficit_{convention}_A_v{cut}']
                replacement=image+moving_deficit
                view.maps[f'ambient_replaced_{convention}_v{cut}']=replacement
                refit=original_observers(replacement,view.horizontal,grid.z)
                for method, original in view.observers.items():
                    background=original['background'];observed_deficit=background-image
                    fixed_mask=detect_fixed(replacement,view.horizontal,grid.z,method,original)
                    current_fixed=detect_fixed(image,view.horizontal,grid.z,method,original)
                    modes={'retained_original':original['mask'], 'exact_projection_fixed':current_fixed,
                           'exact_projection_refit':baseline_refit[method]['mask'],
                           'ambient_replaced_fixed':fixed_mask,'ambient_replaced_refit':refit[method]['mask']}
                    finite=np.isfinite(background)
                    checks[f'observer_identity_{convention}_v{cut}_{method}']=closure('observer deficit identity',
                        observed_deficit[finite],
                        (view.maps[f'deficit_{convention}_C']+view.maps[f'deficit_{convention}_A_v{cut}']+
                         view.maps[f'deficit_{convention}_E_v{cut}']+background-initial)[finite],
                        (np.abs(background)+np.abs(image)+np.abs(initial))[finite])
                    for mode, detection in modes.items():
                        view.maps[f'mask_{convention}_v{cut}_{method}_{mode}']=detection
                        for side in SIDES:
                            half=_side_mask(image.shape,grid.z,side);selected=detection&half;tracer=truth&half
                            intersection=float(area[selected&tracer].sum());found=float(area[selected].sum());true=float(area[tracer].sum())
                            moments=native.exact_abs_u_moments(selected,view.u_edges,grid.z_edges)
                            recoveries.append({'view_deg':angle,'correction':convention,'velocity_cut_km_s':cut,
                                'method':method,'comparison':mode,'hemisphere':side,'recovered_area_kpc2':found,
                                'tracer_area_kpc2':true,'intersection_area_kpc2':intersection,
                                'tracer_completeness':intersection/true if true else None,
                                'tracer_purity':intersection/found if found else None,
                                'symmetrized_revolution_volume_kpc3':moments['symmetrized_revolution_kpc3'],
                                'pixel_centre_revolution_volume_kpc3':moments['centre_approximation_symmetrized_kpc3'],
                                'nondetection':not bool(np.any(selected)),
                                'aperture_contact':bool(ladder.touches_aperture(selected,view.horizontal,grid.z)),
                                'native_filling_measured_for_this_mask':mode=='retained_original'})
                    for side in SIDES:
                        selected=original['mask']&_side_mask(image.shape,grid.z,side)
                        if np.any(selected&~finite):raise ValueError('retained cavity extends outside its finite observer background')
                        weights=area[selected]
                        integrate=lambda field: float(np.sum(field[selected]*weights))
                        pieces={region:integrate(view.maps[f'deficit_{convention}_{region}']) for region in ('C',f'A_v{cut}',f'E_v{cut}')}
                        background_term=integrate(background-initial);denominator=integrate(observed_deficit)
                        scale=integrate(np.abs(background)+np.abs(image))
                        ratio=signed_ratio(pieces['C'],denominator,scale)
                        cocoon_brightness=integrate(view.maps[f'brightness_current_{convention}_C'])
                        total_brightness=integrate(image)
                        positive=all(np.all(view.maps[f'brightness_current_{convention}_{region}'][selected]>=0)
                                     for region in ('C',f'A_v{cut}',f'E_v{cut}'))
                        attribution.append({'view_deg':angle,'correction':convention,'velocity_cut_km_s':cut,
                            'method':method,'hemisphere':side,'observed_mask_pixel_count':int(selected.sum()),
                            'cocoon_deficit_integral':pieces['C'],'moving_ambient_deficit_integral':pieces[f'A_v{cut}'],
                            'external_deficit_integral':pieces[f'E_v{cut}'],'background_difference_integral':background_term,
                            'observed_deficit_integral':denominator,
                            'retained_original_deficit_integral':integrate(background-view.retained_image),
                            'deficit_attribution_ratio':ratio['ratio'],'near_zero_denominator':ratio['near_zero_denominator'],
                            'denominator_reference_scale':scale,'deficit_cancellation_ratio':abs(denominator)/integrate(np.abs(observed_deficit)) if integrate(np.abs(observed_deficit)) else None,
                            'cocoon_brightness_integral':cocoon_brightness,'whole_brightness_integral':total_brightness,
                            'cocoon_brightness_share':cocoon_brightness/total_brightness if positive and total_brightness>0 else None,
                            'brightness_positivity_pass':positive,
                            'emission_domain':'fixed retained observed mask; full projected line of sight',
                            'integral_units':'mJy sr^-1 kpc^2; not detector counts'})
        for method, original in view.observers.items():
            for side in SIDES:
                half=_side_mask(total.shape,grid.z,side);tracer=truth&half
                rows=np.any(tracer,axis=1);extent=float(np.max(np.abs(grid.z[rows]),initial=0))
                tip=np.broadcast_to(np.abs(grid.z[:,None])>=.8*extent,tracer.shape)&tracer if extent else np.zeros_like(tracer)
                rim=tracer&~binary_erosion(tracer)
                missing=tracer&~original['mask']
                regions={'all_tracer':tracer,'missed_tracer':missing,'missed_tip':missing&tip,
                         'missed_rim':missing&rim,'missed_interior':missing&~rim&~tip}
                background=original['background'];deficit=background-total
                fields={'cocoon_path_kpc':view.maps['path_C_kpc'],
                        'cocoon_path_fraction':np.divide(view.maps['path_C_kpc'],view.maps['path_whole_kpc'],out=np.zeros_like(total),where=view.maps['path_whole_kpc']>0),
                        'initial_brightness':view.maps['brightness_initial_retained_linear_whole'],
                        'observed_fractional_deficit':np.divide(deficit,background,out=np.full_like(total,np.nan),where=background>0)}
                bins={'cocoon_path_kpc':[-np.inf,0,.1,1,3,10,30,100,300,np.inf],
                      'cocoon_path_fraction':[-np.inf,0,.001,.01,.03,.1,.3,1.,np.inf],
                      'initial_brightness':[-np.inf,*np.logspace(-15,15,31),np.inf],
                      'observed_fractional_deficit':[-np.inf,-1,-.3,-.1,-.05,0,.05,.1,.3,1,np.inf]}
                for region,selected in regions.items():
                    for field,values in fields.items():
                        valid=selected&np.isfinite(values)
                        counts,_=np.histogram(values[valid],bins[field]);areas,_=np.histogram(values[valid],bins[field],weights=area[valid])
                        for i,(count,area_sum) in enumerate(zip(counts,areas)):
                            paths.append({'view_deg':angle,'method':method,'hemisphere':side,'region':region,'field':field,
                                          'bin_low':float(bins[field][i]),'bin_high':float(bins[field][i+1]),
                                          'pixel_count':int(count),'area_kpc2':float(area_sum),
                                          'nonfinite_selected_pixels':int(np.count_nonzero(selected&~np.isfinite(values)))})
    return attribution,recoveries,paths,reports


def correction_rows(views: dict[int, View], attribution: list[dict]) -> list[dict]:
    rows = []
    for reference in attribution:
        view = views[reference['view_deg']]
        cut = reference['velocity_cut_km_s']
        components = {'C': 'cocoon_deficit_integral', f'A_v{cut}': 'moving_ambient_deficit_integral',
                      f'E_v{cut}': 'external_deficit_integral', 'whole': 'initial_minus_current_brightness_integral'}
        for region, component in components.items():
            for domain in ('out_of_table', 'retained_negative'):
                for state in ('current', 'initial'):
                    signed, absolute = view.correction_contributions[
                        reference['method'], reference['hemisphere'], state, reference['correction'], region, domain]
                    deficit = float(signed)*(1 if state == 'initial' else -1)
                    ratio = signed_ratio(deficit, reference['observed_deficit_integral'], reference['denominator_reference_scale'])
                    rows.append({key: reference[key] for key in
                                 ('view_deg', 'method', 'hemisphere', 'correction', 'velocity_cut_km_s')} | {
                        'region': region, 'state': state, 'correction_domain': domain,
                        'signed_brightness_integral': float(signed), 'absolute_brightness_integral': float(absolute),
                        'signed_deficit_contribution': deficit, 'attribution_component': component,
                        'component_signed_deficit_integral': reference[component] if region != 'whole' else
                            sum(reference[name] for name in components.values() if name in reference),
                        'observed_deficit_integral': reference['observed_deficit_integral'],
                        'signed_contribution_to_observed_deficit_ratio': ratio['ratio'],
                        'near_zero_observed_deficit': ratio['near_zero_denominator'],
                        'domains_overlap': True,
                        'emission_domain': 'fixed retained observed mask; full projected line of sight',
                        'absolute_integral_definition': 'absolute native emissivity before line-of-sight cancellation',
                        'integral_units': 'mJy sr^-1 kpc^2; not detector counts'})
    return rows


def load_inputs(contract_path: Path, contract_sha256: str) -> tuple[dict, dict, list[dict], dict]:
    contract_identity=checked_compact({'path':str(contract_path.absolute()),'sha256':contract_sha256})
    contract=json.loads(contract_path.read_text())
    if contract.get('schema_version')!=1 or contract.get('case')!='G-HI' or contract.get('snapshot_index')!=20:
        raise ValueError('this diagnostic contract is fixed to G-HI snapshot20')
    if set(contract.get('views',{}))!={'0','45','90'}:
        raise ValueError('contract must bind all three declared azimuths')
    if not math.isclose(float(contract['frequency_hz']),native.renderer.DEFAULT_FREQ_HZ,rel_tol=1e-12):
        raise ValueError('this diagnostic is fixed to the retained 1-keV frequency')
    if not math.isfinite(float(contract['redshift'])) or float(contract['redshift'])<0:
        raise ValueError('invalid redshift')
    native_receipt_identity=checked_compact(contract['native_input_receipt'])
    receipt=json.loads(Path(native_receipt_identity['path']).read_text())
    if (receipt.get('schema_version')!=1 or receipt.get('status')!='bound_spherical_budget_inputs'
        or receipt.get('case')!='G-HI' or receipt.get('snapshot_index')!=20):
        raise ValueError('native input receipt does not bind G-HI20')
    native_paths={role:Path(record['path']) for role,record in receipt['inputs'].items()}
    if set(native_paths) not in ({'current_h5','initial_h5','environment'}, {'current_h5','initial_h5','environment','grid_file'}):
        raise ValueError('native receipt roles differ from the accepted input contract')
    native_ids,_,_,_=budget.bind_inputs(native_paths,Path(native_receipt_identity['path']))
    lineage_identity=bind_inherited_lineage(receipt)
    compact={name:checked_compact(contract['inputs'][name]) for name in ('xraise_py','apec_table','gaunt_lut')}
    for angle, records in contract['views'].items():
        if set(records)!={'image','horizontal','vertical','metadata','masks'}:
            raise ValueError('each view requires exact image, axes, metadata and mask identities')
        compact.update({f'view{angle}_{role}':checked_compact(record) for role,record in records.items()})
    sources=[Path(__file__),Path(native.__file__),Path(budget.__file__),Path(ladder.__file__),
             Path(ladder.seed_grow_module.__file__),Path(ladder.recovery.__file__),Path(ladder.legacy_builder.__file__),
             Path(native.renderer.__file__),Path(native.pluto.__file__),Path(native.snapshot_energy.__file__),
             Path(__file__).with_name('measure_q031_fluxes.py'),Path(__file__).with_name('select_common_age_hdf5.py')]
    source_ids={path.name:{**budget._stat_identity(path),'sha256':budget._sha256(path)} for path in sources}
    identities=[contract_identity,native_receipt_identity,lineage_identity,*native_ids,*compact.values(),*source_ids.values()]
    budget._stable(identities)
    provenance={'contract':contract_identity,'native_input_receipt':native_receipt_identity,
                'inherited_lineage_receipt':lineage_identity,
                'native_inputs':native_ids,'compact_inputs':compact,'analysis_sources':source_ids,
                'native_semantic_qualification':receipt.get('native_preflight',{}),
                'native_identity_scope':'exact externally bound receipt; historical source/continuation acceptance is external to this diagnostic'}
    return contract,receipt,identities,provenance


def load_views(contract: dict, receipt: dict, grid: Grid, shape: tuple[int,int,int]) -> dict[int,View]:
    views={}
    for angle in VIEWS:
        records=contract['views'][str(angle)]
        image=np.loadtxt(records['image']['path']);horizontal=np.loadtxt(records['horizontal']['path']);z=np.loadtxt(records['vertical']['path'])
        if image.shape!=(shape[0],horizontal.size) or not np.all(np.isfinite(image)):
            raise ValueError('retained map has invalid shape or non-finite values')
        if z.shape!=grid.z.shape or not np.allclose(z,grid.z,rtol=native.TEXT_RTOL,atol=1e-10):
            raise ValueError('retained vertical axis differs from native Z')
        metadata=json.loads(Path(records['metadata']['path']).read_text())
        for key, role in [('xraise_source','xraise_py'),('apec_table','apec_table'),('gaunt_lut','gaunt_lut')]:
            historical = Path(metadata.get(key, ''))
            if not historical.is_absolute() or historical.resolve() != Path(contract['inputs'][role]['path']).resolve():
                raise ValueError(f'retained-map emissivity input mismatch: {key}')
        if (Path(metadata['input_h5']).resolve()!=Path(receipt['inputs']['current_h5']['resolved_path'])
            or metadata.get('timestep')!=receipt['current']['timestep']
            or metadata.get('grid_shape_nz_ny_nx')!=list(shape)):
            raise ValueError('retained-map native identity mismatch')
        for key,expected in [('time_code',receipt['current']['time_code']),('frequency_hz',contract['frequency_hz']),('redshift',contract['redshift'])]:
            if not math.isclose(float(metadata.get(key,math.nan)),float(expected),rel_tol=2e-14,abs_tol=1e-10):
                raise ValueError(f'retained-map {key} mismatch')
        projection=metadata.get('projection',{})
        if (projection.get('view_angle_deg')!=angle or projection.get('sky_horizontal_bins')!=horizontal.size
            or projection.get('projected_accumulation')!=native.renderer.resolve_projection_method(angle,'auto')):
            raise ValueError('retained-map projection metadata mismatch')
        if angle:
            expected_h,_=native.renderer.projected_axis(grid.x,grid.y,view_angle_deg=angle,projected_u_bins=horizontal.size)
            if not np.allclose(horizontal,expected_h,rtol=native.TEXT_RTOL,atol=1e-10):
                raise ValueError('retained projected axis differs from the declared historical operator')
        observers=original_observers(image,horizontal,z)
        with np.load(records['masks']['path'],allow_pickle=False) as packed:
            if tuple(packed['shape'])!=image.shape or not np.array_equal(packed['horizontal_axis_kpc'],horizontal) or not np.array_equal(packed['z_axis_kpc'],z):
                raise ValueError('retained-mask axes/shape do not match its image')
            for method,observer in observers.items():
                saved=np.logical_or.reduce([unpack_mask(packed,f'{method}__{side}',image.shape) for side in ladder.SIDES])
                if not np.array_equal(saved,observer['mask']):
                    raise ValueError(f'regenerated observer mask differs from retained mask: {angle}:{method}')
                if not np.array_equal(detect_fixed(image,horizontal,z,method,observer),saved):
                    raise ValueError('fixed-background detector does not reproduce the original protocol')
            retained_tracer=unpack_mask(packed,'tracer',image.shape)
        view=make_view(grid,angle,horizontal,image,observers)
        view.maps['retained_tracer_mask']=retained_tracer
        view.maps['retained_image']=image
        for method,observer in observers.items():
            view.maps[f'original_background_{method}']=observer['background']
            view.maps[f'original_mask_{method}']=observer['mask']
        views[angle]=view
    return views


def run(contract_path: Path, contract_sha256: str, output_dir: Path) -> dict:
    if output_dir.exists():raise ValueError('refusing to overwrite an emission result directory')
    contract,receipt,identities,provenance=load_inputs(contract_path,contract_sha256)
    inputs=receipt['inputs'];current_path=Path(inputs['current_h5']['path']);initial_path=Path(inputs['initial_h5']['path'])
    grid_file=Path(inputs['grid_file']['path']) if 'grid_file' in inputs else None
    budget._validate_snapshot_index(current_path,20);budget._validate_snapshot_index(initial_path,0)
    with h5py.File(current_path,'r') as current_file,h5py.File(initial_path,'r') as initial_file:
        current_name,time_code,shape=budget._single_timestep(current_file,receipt['current']['timestep'],context='G-HI20 current')
        initial_name,t0,shape0=budget._single_timestep(initial_file,receipt['initial']['timestep'],context='G-HI20 initial')
        if shape!=shape0 or abs(t0/budget.CODE_TIME_PER_MYR)>1e-6 or abs(time_code/budget.CODE_TIME_PER_MYR-20)>.05:
            raise ValueError('native initial/current shape or time mismatch')
        for actual,expected in [(time_code,receipt['current']['time_code']),(t0,receipt['initial']['time_code'])]:
            if not math.isclose(actual,float(expected),rel_tol=0,abs_tol=1e-10):raise ValueError('native time differs from exact receipt')
        grid=read_grid(current_file,shape,grid_file=grid_file)
        initial_grid=read_grid(initial_file,shape,grid_file=grid_file)
        budget._validate_grid(grid,initial_grid)
        views=load_views(contract,receipt,grid,shape)
        xraise=native.renderer.load_module(Path(contract['inputs']['xraise_py']['path']))
        tables=native.load_tables(Path(contract['inputs']['apec_table']['path']),Path(contract['inputs']['gaunt_lut']['path']))
        def emission(rho,pressure):
            values,temperature,flags = native.cell_emissivity(xraise=xraise,tables=tables,rho_code=rho[None,:,:],pressure_code=pressure[None,:,:],
                                                             frequency_hz=contract['frequency_hz'],redshift=contract['redshift'])
            return {k:v[0] for k,v in values.items()},temperature[0],{k:v[0] for k,v in flags.items()}
        output_dir.mkdir(parents=True)
        filling,diagnostics=integrate_native(current_file[current_name]['vars'],initial_file[initial_name]['vars'],grid,views,emission)
    budget._stable(identities)
    attribution,recoveries,paths,projection=finish_views(views,grid)
    budget._stable(identities)
    for angle,view in views.items():
        np.savez_compressed(output_dir/f'G-HI_0020_{angle}deg.npz',horizontal_axis_kpc=view.horizontal,
                            horizontal_edges_kpc=view.u_edges,z_axis_kpc=grid.z,z_edges_kpc=grid.z_edges,**view.maps)
    for name,rows in [('filling',filling),('deficit_attribution',attribution),('observer_comparisons',recoveries),
                      ('path_histograms',paths),('correction_contributions',correction_rows(views, attribution))]:
        native.write_rows(output_dir/f'{name}.csv',rows)
    budget._stable(identities)
    files={path.name:{'size_bytes':path.stat().st_size,'sha256':budget._sha256(path)} for path in sorted(output_dir.iterdir()) if path.is_file()}
    holds=['native_source_and_continuation_semantics_require_external_review','observer_comparators_are_diagnostic_not_promoted',
           'velocity_cuts_do_not_identify_shock_or_causal_jet_origin','native_revolution_solids_use_full_cell_centre_membership']
    if diagnostics['tracer_outside_unit_interval_count']:holds.append('stored_tracer_outside_unit_interval')
    if any(diagnostics['native_component_boundary_cell_counts']['C'].values()):holds.append('cocoon_contacts_native_domain_boundary')
    if any(any(faces.values()) for region,faces in diagnostics['native_component_boundary_cell_counts'].items() if region != 'C'):
        holds.append('moving_ambient_contacts_native_domain_boundary')
    if any(value.get('retained_tracer_disagreement_pixels',0) for value in projection.values()):holds.append('exact_projection_tracer_mask_differs_from_retained_mask')
    if any(row['domain_truncation'] for row in filling):holds.append('reconstructed_solid_domain_truncation')
    if any(value['projection_geometry']['projection_coverage_hold'] for value in projection.values()):holds.append('retained_sky_grid_does_not_cover_every_native_cell')
    if any(value['retained_map_compatibility_hold'] for value in projection.values()):holds.append('exact_edge_maps_differ_from_retained_maps')
    if any(row['any_out_of_table'] or row['raw_nonfinite'] or any(row[f'{convention}_{flag}'] for convention in CONVENTIONS for flag in ('nonfinite','negative')) for row in diagnostics['correction_domain'].values()):holds.append('emissivity_correction_domain_or_sign')
    result={'schema_version':1,'execution_status':'completed_GHI20_source_emission_diagnostic',
            'case':'G-HI','snapshot_index':20,'actual_time_myr':time_code/budget.CODE_TIME_PER_MYR,
            'views_side_on_azimuth_deg':list(VIEWS),'speed_cuts_km_s':list(CUTS),
            'scientific_qualification':{'qualified':False,'holds':holds},'diagnostics':diagnostics,
            'projection':projection,'provenance':provenance,'files':files,
            'software':{'numpy':np.__version__,'h5py':h5py.__version__},
            'interpretation':{'components':'C=current tr1>1e-3; A=non-C with full speed>=cut; E=complement',
                'initial_reference':'same current component masks applied to actual initial emissivity',
                'source_component':'C+A; moving ambient is not proof of jet origin',
                'filling':'native full-cell numerators/denominators in separate W+ and W- reconstructions; pooled sums, not union',
                'deficit_attribution':'signed cocoon deficit / observed deficit; unbounded and undefined near zero',
                'counterfactual':'replace A emissivity by same-cell initial value; no hydrodynamic rerun',
                'counterfactual_filling':'projected recovery only; new masks have no reused native filling',
                'projection':'actual native edges with retained sky bins; uncovered native integrals explicit',
                'rendering':'NPZ contains component/reference/deficit/path maps and observer outlines; plot rendering is separate'}}
    budget._atomic_publish(output_dir/'completion.json',result)
    return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--contract-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    run(args.contract,args.contract_sha256,args.output_dir)


if __name__=='__main__':
    main()
