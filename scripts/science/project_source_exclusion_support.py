#!/usr/bin/env python3
"""Project all-gas speed and thermodynamic changes on the original X-ray sky grids."""

import argparse
import hashlib
import io
import json
import math
import os
import tarfile
import tempfile
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np

import prepare_blind_emission_maps as adapter

emission = adapter.emission
budget = emission.budget
ANGLES = emission.VIEWS
AXES = adapter.blind.AXES
FIELDS = ('tracer_footprint', 'speed_ge_30', 'speed_ge_100', 'speed_ge_300',
          'pressure_changed', 'density_changed', 'boundary_thermo_changed')
FACES = ('x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max')
SEAL_SHA = '5e917a299e83c5693e01f2c8dbf787213aa99e322aac77ebf5ad11d48a4244ce'
EXPOSED_SHA = '4ca1a4f445ae1d65d6a7aa7619ccea7745d545266656875ddfb469487affd31e'
RELEASE_SHA = 'db4f9586c2fce9f74140bd31362bcb5ea11ec13d1771eb21d130906727cd3c3a'


def json_at(path):
    return json.loads(Path(path).read_text())


def checked(path, digest):
    return emission.checked_compact({'path': str(Path(path).absolute()), 'sha256': digest})


def make_plan(seal_path, inventory_path, exposed_path, release_path):
    seal_id = checked(seal_path, SEAL_SHA)
    seal = json_at(seal_path)
    inventory_id = checked(inventory_path, seal['producer_inventory_sha256'])
    exposed_id = checked(exposed_path, EXPOSED_SHA)
    archive_id = checked(release_path, RELEASE_SHA)
    entries = [{'case': 'G-HI', 'snapshot_index': 20, 'kind': 'development',
                'producer': exposed_id, 'source_sha256': json_at(exposed_path)['provenance']['native_input_receipt']['sha256']}]
    inventory = {r['producer_receipt']['sha256']: r for r in json_at(inventory_path)['producers']}
    grouped = {}
    for unit in seal['units']:
        key = (unit['case'], unit['snapshot_index'], unit['kind'])
        grouped.setdefault(key, []).append(unit)
    if len(grouped) != 22 or len(inventory) != 22 or len(seal['units']) != 66:
        raise ValueError('incomplete sealed cohort')
    for (case, index, kind), units in sorted(grouped.items()):
        if ({u['view_deg'] for u in units} != set(ANGLES) or len(units) != 3
                or len({(u['producer_receipt_sha256'], u['source_receipt_sha256']) for u in units}) != 1):
            raise ValueError('inconsistent views or native bindings in seal')
        producer = inventory[units[0]['producer_receipt_sha256']]
        expected = units[0]['source_receipt_sha256']
        if producer['native_input_receipt']['sha256'] != expected:
            raise ValueError('inventory native binding differs from seal')
        checked(producer['producer_receipt']['path'], producer['producer_receipt']['sha256'])
        entries.append({'case': case, 'snapshot_index': index, 'kind': kind,
                        'producer': producer['producer_receipt'], 'source_sha256': expected})
    return {'seal': seal_id, 'inventory': inventory_id, 'archive': archive_id, 'slots': entries}


def bind_native(entry):
    prod_id = checked(entry['producer']['path'], entry['producer']['sha256'])
    prod = json_at(prod_id['path'])
    case, index, kind = entry['case'], entry['snapshot_index'], entry['kind']
    if ((prod['case'], prod['snapshot_index']) != (case, index)
            or prod.get('kind', 'development') != kind
            or (kind == 'development' and prod_id['sha256'] != EXPOSED_SHA)):
        raise ValueError('producer case, snapshot or scope differs')
    provenance = prod['provenance']
    source_id = checked(provenance['native_input_receipt']['path'], entry['source_sha256'])
    if source_id['sha256'] != provenance['native_input_receipt']['sha256']:
        raise ValueError('producer and seal disagree on native source')
    source = json_at(source_id['path'])
    adapter.validate_native_receipt(source, case, index)
    contract_id = emission.checked_compact(source['native_preflight']['contract'])
    contract = json_at(contract_id['path'])
    adapter.validate_receipt_contract(source, contract)
    paths = {name: Path(record['path']) for name, record in source['inputs'].items()}
    native_ids, _, _, _ = budget.bind_inputs(paths, Path(source_id['path']))
    for name, idx in (('current_h5', index), ('initial_h5', 0)):
        budget._validate_snapshot_index(paths[name], idx)
    stable = [prod_id, source_id, contract_id, *native_ids]
    if case == 'G-HI':
        rec = emission.checked_compact(source['native_preflight']['inherited_lineage']['receipt'])
        lineage = json_at(rec['path'])
        chain = lineage['snapshots']['analysis_chain']
        if (lineage['status'] != 'passed' or [row['output_index'] for row in chain] != list(range(51))
                or lineage['lineage'] != 'accepted failed-run parent build/source plus validated 10 Myr home continuation'):
            raise ValueError('incomplete G-HI ancestry')
        for role, epoch, idx in (('current_h5', 'current', index), ('initial_h5', 'initial', 0)):
            file_binding = source['inputs'][role]
            for k in ('path', 'resolved_path', 'size_bytes', 'inode', 'mtime_ns', 'ctime_ns'):
                if chain[idx][k] != file_binding[k]:
                    raise ValueError(f'G-HI lineage differs at {role} {k}')
            if any(chain[idx][k] != source[epoch][k] for k in ('timestep', 'time_code')):
                raise ValueError('G-HI lineage timestep differs')
        stable.append(rec)
    for filename in ('build_q032_source_emission.py', 'build_q031_native_emission.py',
                     'measure_q031_fluxes.py', 'xraise_grid_smoke.py'):
        stable.append(checked(Path(__file__).with_name(filename), provenance['analysis_sources'][filename]['sha256']))
    return prod, source, contract, native_ids, stable


def read_reference(entry, prod, archive, angle):
    uid = f"{entry['case']}_{entry['snapshot_index']:04d}_{angle}deg"
    if entry['kind'] == 'development':
        filename = uid + '.npz'
        path = Path(entry['producer']['path']).parent / filename
        record = checked(path, prod['files'][filename]['sha256'])
        source = path
    else:
        filename = uid + '.truth.npz'
        member = archive.getmember('truth/' + filename)
        payload = archive.extractfile(member).read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != prod['files'][filename]['sha256'] or len(payload) != prod['files'][filename]['size_bytes']:
            raise ValueError(f'private truth copy differs from bound producer at {uid}')
        record = {'member': member.name, 'sha256': digest, 'size_bytes': len(payload)}
        source = io.BytesIO(payload)
    with np.load(source, allow_pickle=False) as data:
        return {key: data[key] for key in (*AXES, 'path_C_kpc')}, record


def make_view(grid, angle, reference, kind):
    horizontal = reference['horizontal_axis_kpc']
    edges, operator, covered, geometry = emission.build_projection(grid, angle, horizontal)
    expected = {'horizontal_edges_kpc': edges, 'z_axis_kpc': grid.z, 'z_edges_kpc': grid.z_edges}
    if any(not np.array_equal(value, reference[name]) for name, value in expected.items()):
        raise ValueError(f'original horizontal edges or native vertical axes differ at {angle} deg')
    if kind != 'development':
        horizontal_native = (grid.x if angle == 0 else emission.native.renderer.projected_axis(
            grid.x, grid.y, view_angle_deg=angle, projected_u_bins=len(grid.x))[0])
        if not np.array_equal(horizontal_native, horizontal):
            raise ValueError(f'DET-05 horizontal axis differs from production at {angle} deg')
    target = reference['path_C_kpc']
    shape = len(grid.z), len(horizontal)
    if target.shape != shape or not np.isfinite(target).all() or np.any(target < 0):
        raise ValueError(f'invalid bound tracer path at {angle} deg')
    if kind == 'initial_null' and np.any(target):
        raise ValueError('initial scoring target is not empty')
    return SimpleNamespace(operator=operator, covered=covered, geometry=geometry,
                           axes={k: reference[k] for k in AXES}, target=target,
                           maps={f: np.zeros(shape, bool) for f in FIELDS}, covered_tracer=0.,
                           projected_tracer=0., max_depth_difference=0.)


def cell_fields(now, initial, iz, nz):
    if any(not np.isfinite(x).all() for x in (*now.values(), *initial.values())):
        raise ValueError('non-finite native primitive')
    for key in ('rho', 'prs'):
        if np.any(now[key] <= 0) or np.any(initial[key] <= 0):
            raise ValueError('nonpositive density or pressure')
    speed = np.sqrt(sum(now[f'vx{i}'] ** 2 for i in (1, 2, 3))) * budget.UNIT_VELOCITY_CMS / 1e5
    fields = {'tracer_footprint': now['tr1'] > 1.e-3,
              **{f'speed_ge_{cut}': speed >= cut for cut in emission.CUTS},
              'pressure_changed': np.abs(now['prs'] / initial['prs'] - 1.) >= .01,
              'density_changed': np.abs(now['rho'] / initial['rho'] - 1.) >= .01}
    changed = fields['pressure_changed'] | fields['density_changed']
    if iz not in (0, nz - 1):
        changed[1:-1, 1:-1] = False
    fields['boundary_thermo_changed'] = changed
    return fields


def integrate(current, initial, grid, views, kind):
    nz = len(grid.z)
    area = np.outer(grid.dy, grid.dx)
    boundary = {field: dict.fromkeys(FACES, 0) for field in FIELDS}
    counts = dict.fromkeys(FIELDS, 0)
    native_tracer = 0.
    for iz, dz in enumerate(grid.dz):
        now = {k: np.asarray(current[k][iz], dtype=np.float64) for k in ('rho', 'prs', 'tr1', 'vx1', 'vx2', 'vx3')}
        zero = {k: np.asarray(initial[k][iz], dtype=np.float64) for k in ('rho', 'prs')}
        cells = cell_fields(now, zero, iz, nz)
        native_tracer += float((area[cells['tracer_footprint']] * dz).sum())
        for field, selected in cells.items():
            n = int(np.count_nonzero(selected))
            counts[field] += n
            faces = boundary[field]
            if n:
                for key, side in zip(FACES[:4], (selected[:, 0], selected[:, -1], selected[0], selected[-1])):
                    faces[key] += int(np.count_nonzero(side))
                if iz == 0:
                    faces['z_min'] += n
                if iz == nz - 1:
                    faces['z_max'] += n
            elif field != 'tracer_footprint':
                continue
            scalar = selected.astype(np.float64) if n else None
            for view in views.values():
                path = (emission.project_scalar(view, scalar, grid) if n
                        else np.zeros(len(view.axes['horizontal_axis_kpc'])))
                view.maps[field][iz] = path > 0.
                if field == 'tracer_footprint':
                    view.covered_tracer += float(np.sum(view.covered[selected] * dz))
                    view.projected_tracer += float(np.sum(path * np.diff(view.axes['horizontal_edges_kpc'])) * dz)
                    if kind != 'initial_null':
                        if not np.array_equal(path > 0., view.target[iz] > 0.):
                            raise ValueError(f'physical tracer footprint differs on row {iz}')
                        difference = float(np.abs(path - view.target[iz]).max())
                        view.max_depth_difference = max(view.max_depth_difference, difference)
                        if not np.allclose(path, view.target[iz], atol=1e-12, rtol=1e-12):
                            raise ValueError(f'physical tracer depths differ on row {iz}')
    return counts, boundary, native_tracer


def run(plan_path, slot, root):
    plan = json_at(plan_path)
    entry = plan['slots'][slot]
    case, index, kind = entry['case'], entry['snapshot_index'], entry['kind']
    identity = f'{case}_{index:04d}'
    root.mkdir(parents=True, exist_ok=True)
    final = root / identity
    if final.exists():
        raise FileExistsError(f'already published: {identity}')
    prod, source, contract, native_ids, stable = bind_native(entry)
    paths = {i['role']: i['path'] for i in native_ids}
    with ExitStack() as stack:
        archive = None
        if kind != 'development':
            archive_id = checked(plan['archive']['path'], RELEASE_SHA)
            stable.append(archive_id)
            archive = stack.enter_context(tarfile.open(archive_id['path'], 'r:'))
        handles, grids, times = {}, {}, {}
        for role in ('current', 'initial'):
            h5 = stack.enter_context(h5py.File(paths[role + '_h5'], 'r'))
            name, time, shape = budget._single_timestep(h5, source[role]['timestep'], context=role)
            if (list(shape) != contract['shape_nz_ny_nx'] or
                    not math.isclose(time, source[role]['time_code'], abs_tol=1e-10, rel_tol=0)):
                raise ValueError(f'native HDF5 time or shape differs: {role}')
            handles[role], times[role] = h5[name]['vars'], time
            grids[role] = emission.read_grid(h5, shape, grid_file=Path(paths['grid_file']) if 'grid_file' in paths else None)
        grid = grids['current']
        budget._validate_grid(grid, grids['initial'])
        views, references = {}, {}
        for angle in ANGLES:
            ref, record = read_reference(entry, prod, archive, angle)
            views[angle] = make_view(grid, angle, ref, kind)
            references[angle] = record
            if kind == 'development':
                stable.append(record)
        counts, faces, native_tracer = integrate(handles['current'], handles['initial'], grid, views, kind)
    budget._stable(stable)
    if faces['tracer_footprint'] != prod['diagnostics']['native_component_boundary_cell_counts']['C']:
        raise ValueError('native tracer boundary counts differ from original')
    if counts['tracer_footprint'] == 0:
        raise ValueError('physical tracer unexpectedly absent')
    reports = {}
    with tempfile.TemporaryDirectory(dir=root, prefix=f'.{identity}-') as tmp:
        publish = Path(tmp) / identity
        publish.mkdir(mode=0o700)
        files = {}
        for angle, view in views.items():
            old = prod['projection'][str(angle)]
            native_old = old.get('native_integrals', old.get('native_volume_integrals'))['path_C_kpc']
            covered_old = old.get('covered_integrals', old.get('covered_volume_integrals'))['path_C_kpc']
            if (not math.isclose(native_old, native_tracer, rel_tol=2.e-12) or
                    any(not math.isclose(covered_old, x, rel_tol=2.e-12) for x in
                        (view.covered_tracer, view.projected_tracer))):
                raise ValueError(f'native or integrated tracer path disagrees with producer at {angle}')
            if np.any(view.maps['speed_ge_300'] & ~view.maps['speed_ge_100']) or np.any(view.maps['speed_ge_100'] & ~view.maps['speed_ge_30']):
                raise ValueError('speed masks are not nested')
            if np.any(view.maps['boundary_thermo_changed'] & ~(view.maps['pressure_changed'] | view.maps['density_changed'])):
                raise ValueError('boundary-only field exceeds all-cell counterpart')
            file = publish / f'{identity}_{angle}deg.npz'
            np.savez_compressed(file, **view.axes, **view.maps)
            files[file.name] = {'sha256': budget._sha256(file), 'size_bytes': file.stat().st_size}
            reports[angle] = {**view.geometry, 'reference': references[angle],
                              'old_tracer_native_kpc3': native_old, 'native_tracer_kpc3': native_tracer,
                              'old_tracer_covered_kpc3': covered_old, 'covered_tracer_kpc3': view.covered_tracer,
                              'projected_tracer_kpc3': view.projected_tracer,
                              'tracer_footprint_checked_against_reference': kind != 'initial_null',
                              'physical_tracer_vs_reference_depth_max_abs_kpc': view.max_depth_difference if kind != 'initial_null' else None,
                              'footprint_pixels': {key: int(np.count_nonzero(val)) for key, val in view.maps.items()}}
        receipt = {'schema_version': 1, 'case': case, 'snapshot_index': index, 'kind': kind,
                   'time_myr': times['current'] / budget.CODE_TIME_PER_MYR, 'native_shape_nz_ny_nx': list(shape),
                   'producer_sha256': entry['producer']['sha256'], 'native_receipt_sha256': entry['source_sha256'],
                   'native_inputs': {i['role']: i for i in native_ids}, 'boundary_face_counts': faces,
                   'native_selected_cell_counts': counts, 'projection': reports, 'files': files,
                   'source_code_sha256': budget._sha256(Path(__file__)), 'pbs_job_id': os.environ.get('PBS_JOBID'),
                   'definition': 'Any strictly positive native path. Speed is the three-component norm for all gas. Thermodynamic masks require absolute fractional change >= 0.01 at the same cell from initial conditions. The boundary mask contains only changed cells on a native face.'}
        (publish / 'completion.json').write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n')
        publish.rename(final)
    return final


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan')
    for name in ('seal', 'inventory', 'exposed', 'release', 'out'):
        plan.add_argument('--' + name, type=Path, required=True)
    run_command = commands.add_parser('run')
    run_command.add_argument('--plan', required=True, type=Path)
    run_command.add_argument('--slot', type=int, required=True)
    run_command.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    if args.command == 'plan':
        result = make_plan(args.seal, args.inventory, args.exposed, args.release)
        with args.out.open('x') as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    else:
        print(run(args.plan, args.slot, args.output_dir), flush=True)


if __name__ == '__main__':
    main()
