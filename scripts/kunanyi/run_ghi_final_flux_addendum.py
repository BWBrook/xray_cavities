"""Qualify one G-HI index-47 endpoint without altering the failed R2 stage."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import socket
import stat
import sys
import tarfile


ORIGINAL_JOB = '879905'
ORIGINAL_REQUEST_SHA256 = '790c151d2021f25f4174010ee7636730f5c5b1061109cd51b376d1b90aa4335a'
ORIGINAL_STAGE_SHA256 = '52fedf9d9bc088db3c3692dc33c5a6127e0fd5c5a97ac7dda4ce9c85a8a35b81'
ORIGINAL_SIGNATURE = '25f93a5c2cc3e55fc8055849d566b5ef4c2ee1be1aca8af7cd63c6cf9b325e84'
CAPTURE_SHA256 = '7ddf50b4018b983b427d9feb62bccfae884c8cc6a5983ff8d90718689931e2a7'
ANALYSIS = 'results/flux_G-HI_full'
IMPLEMENTATION_NAMES = ('measure_q031_fluxes.py', 'snapshot_energy.py',
    'pluto_h5_level3_ambient_extract.py', 'select_common_age_hdf5.py')
def require(condition, message):
    if not condition:
        raise ValueError(message)


def stat_identity(path):
    path = Path(path).absolute()
    value = path.stat()
    require(stat.S_ISREG(value.st_mode), f'file is not regular: {path}')
    return {'path': str(path), 'resolved_path': str(path.resolve()), 'device': value.st_dev,
        'inode': value.st_ino, 'size_bytes': value.st_size, 'mtime_ns': value.st_mtime_ns,
        'ctime_ns': value.st_ctime_ns}


def checked_hash(path, expected_sha=None):
    before = stat_identity(path)
    with Path(path).open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    require(stat_identity(path) == before, f'file changed while hashing: {path}')
    require(expected_sha is None or digest == expected_sha, f'file hash mismatch: {path}')
    return {**before, 'sha256': digest}


def unchanged(records, *, rehash):
    for record in records:
        require(stat_identity(record['path']) == {k: v for k, v in record.items() if k != 'sha256'},
            f'file identity changed: {record["path"]}')
        if rehash:
            checked_hash(Path(record['path']), record['sha256'])


def verify_original_stage(stage):
    manifest = stage/'stage_checksums.sha256'
    records = [checked_hash(manifest, ORIGINAL_STAGE_SHA256)]
    names = set()
    for line in manifest.read_text().splitlines():
        sha, name = line.split(None, 1)
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts and name not in names,
            'invalid or duplicate original stage manifest path')
        require(not (stage/path).is_symlink(), 'original stage member is not regular')
        names.add(name)
        records.append(checked_hash(stage/path, sha))
    require(len(names) == 37, 'unexpected original stage manifest inventory')
    return records


def original_modules(stage):
    sys.dont_write_bytecode = True
    roots = [stage/'scripts/kunanyi', stage/'scripts/science']
    names = ('run_review_accounting', 'prepare_spherical_budget_inputs',
        'extract_fixed_box_energy_budget', 'extract_spherical_energy_budget',
        'measure_q031_fluxes', 'snapshot_energy', 'pluto_h5_level3_ambient_extract',
        'select_common_age_hdf5')
    for name in names:
        if name in sys.modules:
            require(Path(sys.modules[name].__file__).resolve() in [r/(name+'.py') for r in roots],
                f'project import already resolves outside original stage: {name}')
    sys.path[:0] = [str(r) for r in roots]
    runner = importlib.import_module('run_review_accounting')
    for name in names:
        module = sys.modules.get(name)
        require(module is not None and Path(module.__file__).resolve() in [r/(name+'.py') for r in roots],
            f'project import resolves outside original stage: {name}')
    return runner, runner.inputs, runner.flux


def validate_context(context):
    require(context.get('status') == 'derived_partial_checkpoint_reduction'
        and context.get('original_request_status') == 'failed_at_index_47'
        and context.get('original_native_run_completed') is False
        and context.get('final_native_and_source_stability_checks_executed') is False
        and context.get('case') == 'G-HI' and context.get('kept_indices') == list(range(47))
        and context.get('excluded_failed_index') == 47, 'invalid archived partial context')
    payload = context['original_full_signature_payload']
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(context.get('original_full_analysis_signature') == ORIGINAL_SIGNATURE == digest,
        'archived original analysis signature mismatch')
    require(payload.get('method_version') == 1 and payload.get('case') == 'G-HI'
        and [s['output_index'] for s in payload.get('snapshots', [])] == list(range(48)),
        'archived original method or index envelope differs')
    expected = {f'{ANALYSIS}/flux/checkpoints/{i:04d}-{i:04d}.json' for i in range(47)}
    require(set(context.get('checkpoint_sha256', {})) == expected, 'archived prefix is not exactly indices0-46')
    return payload


def archived_files(archive, context):
    wanted = {'stage/requests/G-HI_full.json', 'stage/source_revision.json',
        'stage/submissions/flux_G-HI_full.json', 'stage/flux_G-HI_full.out',
        'stage/'+ANALYSIS+'/request_binding.json'}
    wanted.update('stage/'+name for name in context['checkpoint_sha256'])
    with tarfile.open(archive) as handle:
        members = handle.getmembers()
        require(len(members) == 238 and len({m.name for m in members}) == 238,
            'original capture member inventory differs')
        require(all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                    for m in members), 'original capture has unsafe or nonregular members')
        return {name: handle.extractfile(name).read() for name in sorted(wanted)}


def validate_prefix(stage, context, archived, metadata):
    records, inventory = [], []
    for i in range(47):
        name = f'{ANALYSIS}/flux/checkpoints/{i:04d}-{i:04d}.json'
        data = archived['stage/'+name]
        expected = context['checkpoint_sha256'][name]
        require(hashlib.sha256(data).hexdigest() == expected, 'archived checkpoint hash differs from context')
        live = checked_hash(stage/name, expected)
        require(live['size_bytes'] == len(data), 'live and archived checkpoint sizes differ')
        checkpoint = json.loads(data)
        require(checkpoint['analysis_signature'] == ORIGINAL_SIGNATURE and checkpoint['snapshot'] == metadata[i],
            f'archived checkpoint metadata/signature mismatch: {i}')
        records.append(live)
        inventory.append({'index': i, 'filename': Path(name).name, 'size_bytes': len(data), 'sha256': expected})
    return records, inventory


def site_identity(stage, expected_host):
    host = socket.gethostname().split('.')[0]
    require(expected_host and host == expected_host,
        f'addendum requires pinned compatible compute host {expected_host}; observed {host}')
    roots = {}
    for name, path in [('stage', stage), ('bound_snapshots', stage/ANALYSIS/'bound_snapshots')]:
        value = path.stat()
        roots[name] = {'resolved_path': str(path.resolve()), 'device': value.st_dev, 'inode': value.st_ino}
    return {'hostname': host, 'python': sys.version, 'roots': roots}


def native_context(stage, bindings, flux):
    require([row[0]['index'] for row in bindings] == list(range(48)), 'fresh request does not cover exactly0-47')
    specification, preflight = bindings[0][1:3]
    files = preflight['files']
    source_root = Path(specification['source_root'])
    flux.parse_source_definitions(source_root/'definitions_usr.h')
    flux.parse_core_definitions(source_root/'definitions.h')
    flux.validate_absent_nonadvective_overrides(source_root/'definitions.h')
    flux.validate_stationary_source(source_root/'pluto_usr.h')
    flux.validate_source_implementation(source_root/'jet.c', source_root/'init.c')
    parameters = flux.parse_pluto_parameters(Path(files['runtime_config']['path']))
    snapshots = flux.canonical_snapshot_chain([stage/ANALYSIS/'bound_snapshots'])
    require([s.output_index for s in snapshots] == list(range(48)), 'live bound snapshot chain differs')
    metadata = [flux._snapshot_metadata(s) for s in snapshots]
    environment = flux.load_environment(Path(files['environment']['path']))
    grid_path = Path(files['grid_file']['path'])
    with flux.h5py.File(snapshots[0].input_h5, 'r') as base, flux.h5py.File(snapshots[47].input_h5, 'r') as target:
        grid = flux.read_grid(base, snapshots[0].shape, grid_file=grid_path)
        flux.read_and_validate_axes(base=base, final=target, nz=snapshots[47].shape[0],
            ny=snapshots[47].shape[1], nx=snapshots[47].shape[2])
        final_grid = flux.read_grid(target, snapshots[47].shape, grid_file=grid_path)
        require(all(flux.np.array_equal(getattr(grid, axis), getattr(final_grid, axis))
                    for axis in ('x_edges', 'y_edges', 'z_edges')), 'final native node geometry differs')
    boxes = {padding: flux.derive_control_box(grid, injection_height_kpc=parameters['JET_INJECTION_HEIGHT'],
        centre_kpc=(-parameters['JET_X1O'], -parameters['JET_X2O'], -parameters['JET_X3O']),
        padding_cells=padding) for padding in (1, 2, 4)}
    payload = {'method_version': flux.METHOD_VERSION, 'case': 'G-HI', 'snapshots': metadata,
        'environment_path': str(Path(files['environment']['path']).resolve()), 'environment_sha256': files['environment']['sha256'],
        'pluto_ini_path': str(Path(files['runtime_config']['path']).resolve()), 'pluto_ini_sha256': files['runtime_config']['sha256'],
        'problem_source_dir': str(source_root.resolve()),
        'grid_geometry': {'edge_source': grid.edge_source, 'grid_file': str(grid_path),
            'grid_file_sha256': files['grid_file']['sha256'],
            'max_cell_center_edge_midpoint_residual_kpc': grid.max_center_edge_residual_kpc},
        'problem_source_hashes': {name: item['sha256'] for name, item in preflight['source_files'].items()},
        'analysis_implementation_hashes': {name: flux.sha256_file(stage/'scripts/science'/name) for name in IMPLEMENTATION_NAMES},
        'shell_layers': [1, 2, 4, 8], 'control_padding_cells': [1, 2, 4],
        'control_boxes': {str(p): box.__dict__ for p, box in boxes.items()}, 'canonical_overlap_audit': []}
    return payload, parameters, snapshots[47], grid, environment, boxes


def validate_source_inventory(root, expected):
    observed = {str(path.relative_to(root)) for path in root.rglob('*')
        if path.is_file() and path.suffix in ('.c', '.h')}
    require(observed == set(expected), 'original C/header source inventory changed')


def validate_endpoint(endpoint, expected_metadata, *, flux, time_myr):
    require(endpoint.get('schema_version') == 1 and endpoint.get('status') == 'measured_ghi_final_snapshot_addendum'
        and endpoint.get('method_version') == 1 and endpoint.get('case') == 'G-HI'
        and endpoint.get('snapshot') == expected_metadata
        and endpoint.get('scientific_qualification', {}).get('qualified') is False,
        'endpoint case/index/input metadata or status differs')
    for row in [*endpoint['flux_rows'], *endpoint['storage_rows']]:
        require(row['snapshot_index'] == 47 and row['timestep'] == expected_metadata['timestep']
            and row['actual_time_code'] == expected_metadata['time_code'] and row['actual_time_myr'] == time_myr
            and row['input_h5'] == expected_metadata['path'],
            'endpoint row does not bind the original index47 input')
    faces = (*flux.FACE_NAMES, 'closed_surface_total')
    expected = {('domain_boundary', 'outer_active_cell', face) for face in faces}
    expected.update((f'nozzle_control_p{p}', method, face) for p in (1, 2, 4)
        for method in ('centered_primitives', 'donor_cell_primitives')
        for face in faces)
    diagnostic = endpoint['linear_diagnostics']
    require(diagnostic['native_primitives_valid'] is True
        and [r['face'] for r in diagnostic['faces']] == list(flux.FACE_NAMES),
        'endpoint native primitive gate or six-face diagnostic inventory differs')
    invalid_faces = []
    for face in diagnostic['faces']:
        require(face['active']['valid'] is True and face['inner']['valid'] is True,
            'endpoint native boundary primitive is invalid')
        valid = face['linear']['valid']
        require(type(valid) is bool and valid == face['original_linear_gate_passed']
            and valid == (face['linear']['invalid_cell_count'] == 0),
            'endpoint independent/original linear diagnostic differs')
        if not valid:
            invalid_faces.append(face['face'])
    require(diagnostic['invalid_faces'] == invalid_faces
        and diagnostic['all_faces_linear_valid'] is (not invalid_faces)
        and diagnostic['linear_invalid_cell_count_sum_over_faces'] == sum(
            face['linear']['invalid_cell_count'] for face in diagnostic['faces']),
        'endpoint aggregate linear diagnostic differs')
    availability = {'domain_boundary': {
        'outer_active_cell': {'available': True, 'reason': 'original_native_gate_passed'},
        'linear_to_boundary_face': {'available': not invalid_faces,
            'reason': 'invalid_linear_primitive_faces' if invalid_faces else 'all_six_faces_valid',
            'invalid_faces': invalid_faces}}}
    for padding in (1, 2, 4):
        availability[f'nozzle_control_p{padding}'] = {method: {
            'available': True, 'reason': 'original_native_gate_passed'} for method in flux.CONTROL_RECONSTRUCTIONS}
    require(endpoint['surface_availability'] == availability, 'endpoint availability disagrees with diagnostic')
    if not invalid_faces:
        expected.update(('domain_boundary', 'linear_to_boundary_face', face) for face in faces)
    observed = [(r['surface'], r['reconstruction'], r['face']) for r in endpoint['flux_rows']]
    require(len(observed) == len(expected) and set(observed) == expected, 'endpoint flux branch inventory differs')
    storage_expected = {(geometry, region) for geometry in ('exact_fv_nodes', 'legacy_midpoint_centres')
        for region in ('whole_grid', 'nozzle_control_p1', 'nozzle_control_p2', 'nozzle_control_p4',
            'boundary_layer_1', 'boundary_layer_2', 'boundary_layer_4', 'boundary_layer_8')}
    storage = [(r['volume_geometry'], r['region']) for r in endpoint['storage_rows']]
    require(len(storage) == len(storage_expected) and set(storage) == storage_expected,
        'endpoint storage inventory differs')
    for rows, fields in ((endpoint['flux_rows'], flux.FLUX_FIELDS), (endpoint['storage_rows'], flux.STORAGE_FIELDS)):
        require(all(isinstance(row[field], (int, float)) and math.isfinite(row[field])
            for row in rows for field in fields), 'endpoint contains a nonfinite physical measurement')
    json.dumps(endpoint, allow_nan=False)


def validate_parameters(parameters, context):
    expected = context['pluto_parameters']
    require(set(expected) == {'JET_PWR', 'JET_START_TIME', 'JET_ACTIVE_TIME'}
        and {key: parameters.get(key) for key in expected} == expected,
        'fresh original labelled runtime parameters differ')


def run(args):
    stage, output = args.original_stage.resolve(), args.output_dir.resolve()
    require(not output.exists() and not output.is_relative_to(stage), 'output must be new and outside original stage')
    site = site_identity(stage, args.expected_host)
    pinned = verify_original_stage(stage)
    archive_identity = checked_hash(args.prefix_capture, CAPTURE_SHA256)
    context_identity = checked_hash(args.partial_context, args.partial_context_sha256)
    endpoint_identity = checked_hash(args.endpoint_module, args.endpoint_module_sha256)
    runner_identity = checked_hash(Path(__file__))
    context = json.loads(args.partial_context.read_text())
    archived_payload = validate_context(context)
    archived = archived_files(args.prefix_capture, context)
    dynamic_names = ['requests/G-HI_full.json', 'source_revision.json', 'submissions/flux_G-HI_full.json',
        'flux_G-HI_full.out', ANALYSIS+'/request_binding.json']
    for name in dynamic_names:
        expected = hashlib.sha256(archived['stage/'+name]).hexdigest()
        pinned.append(checked_hash(stage/name, expected))
    original_bound = json.loads(archived['stage/'+ANALYSIS+'/request_binding.json'])
    require(hashlib.sha256(archived['stage/'+ANALYSIS+'/request_binding.json']).hexdigest() == context['request_binding_sha256']
        and hashlib.sha256(archived['stage/flux_G-HI_full.out']).hexdigest() == context['failure_log_sha256'],
        'archived failed request or failure-log binding differs')
    submission = json.loads(archived['stage/submissions/flux_G-HI_full.json'])
    require(submission['job_id'].split('.')[0] == ORIGINAL_JOB and submission['analysis'] == 'flux_G-HI_full'
        and submission['stage_manifest_sha256'] == ORIGINAL_STAGE_SHA256, 'wrong original job or stage')
    original, inputs, flux = original_modules(stage)
    request, request_identity, bindings = original.validate_request(stage/'requests/G-HI_full.json', ORIGINAL_REQUEST_SHA256)
    require(request == original_bound['request'] and original_bound['mode'] == 'flux', 'original full request differs')
    for row, _, preflight, *_ in bindings:
        require(preflight == original_bound['preflights'][str(row['index'])], 'fresh original preflight differs from archived binding')
    payload, parameters, snapshot, grid, environment, boxes = native_context(stage, bindings, flux)
    require(payload == archived_payload and flux._signature(payload) == ORIGINAL_SIGNATURE,
        'fresh original method/config/input signature differs')
    source_root = Path(payload['problem_source_dir'])
    validate_source_inventory(source_root, payload['problem_source_hashes'])
    validate_parameters(parameters, context)
    prefix_records, prefix_inventory = validate_prefix(stage, context, archived, payload['snapshots'])
    source_config_records = {}
    for _, _, preflight, *_ in bindings:
        for record in [*preflight['source_files'].values(), *(preflight['files'][role]
                for role in (*inputs.REQUIRED_FILES, 'grid_file'))]:
            previous = source_config_records.setdefault(record['path'], record)
            require(previous == record, 'source/config path has conflicting original identities')
    source_config = {path: checked_hash(Path(path), record['sha256'])
        for path, record in sorted(source_config_records.items())}
    native = {}
    for i in (46, 47):
        record = bindings[i][3]['inputs']['current_h5']
        before = inputs.budget._stat_identity(Path(record['path']))
        require(before['device'] == payload['snapshots'][i]['device'] == 46, 'native input is not on the original compatible filesystem')
        native[str(i)] = {'before': before, 'historical_payload_sha256': record['sha256'], 'fresh_payload_rehashed': False}
    spec = importlib.util.spec_from_file_location('ghi_final_flux_measurement', args.endpoint_module)
    require(spec is not None and spec.loader is not None, 'cannot load pinned endpoint implementation')
    endpoint_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = endpoint_module
    spec.loader.exec_module(endpoint_module)
    endpoint = endpoint_module.measure_final_snapshot(snapshot, grid=grid, environment=environment,
        boxes=boxes, shell_layers=(1, 2, 4, 8))
    validate_endpoint(endpoint, payload['snapshots'][47], flux=flux, time_myr=snapshot.actual_time_myr)
    for row, _, preflight, receipt, receipt_identity, done_identity in bindings:
        inputs.validate_existing_receipt(preflight, row['index'], receipt)
        inputs.budget._stable([receipt_identity, done_identity])
    for i in (46, 47):
        after = inputs.budget._stat_identity(Path(bindings[i][3]['inputs']['current_h5']['path']))
        require(after == native[str(i)]['before'], f'index{i} native identity changed during endpoint measurement')
        native[str(i)]['after'] = after
    unchanged([*pinned, *prefix_records, *source_config.values(), archive_identity,
        context_identity, endpoint_identity, runner_identity], rehash=True)
    validate_source_inventory(source_root, payload['problem_source_hashes'])
    require(site_identity(stage, args.expected_host) == site, 'compute site identities changed')
    output.mkdir(parents=True, exist_ok=False)
    flux._atomic_json(output/'endpoint.json', endpoint)
    endpoint_product = checked_hash(output/'endpoint.json')
    receipt = {'schema_version': 1, 'status': 'qualified_ghi_index47_addendum', 'case': 'G-HI',
        'snapshot_index': 47, 'execution_qualified': True, 'scientifically_qualified': False,
        'original_request': {'job_id': submission['job_id'], 'status': 'failed_original_request',
            'request_sha256': ORIGINAL_REQUEST_SHA256, 'stage_manifest_sha256': ORIGINAL_STAGE_SHA256,
            'analysis_signature': ORIGINAL_SIGNATURE}, 'endpoint_product': endpoint_product,
        'prefix': {'capture_sha256': CAPTURE_SHA256, 'partial_context_sha256': context_identity['sha256'],
            'inventory_sha256': flux._signature({'checkpoints': prefix_inventory}),
            'count': 47, 'indices': list(range(47)), 'checkpoints': prefix_inventory,
            'original_index46_sha256': prefix_inventory[46]['sha256']},
        'sources': {'original_analysis_implementation_hashes': payload['analysis_implementation_hashes'],
            'original_stage_files': pinned, 'source_config': list(source_config.values()),
            'endpoint_module': endpoint_identity, 'runner': runner_identity},
        'native_inputs': native, 'site': site,
        'stability': {'source_config_before_after': True, 'native_metadata_before_after': True,
            'original_prefix_before_after': True, 'archived_prefix_before_after': True,
            'index46_checkpoint_hash_before_after': True, 'site_before_after': True},
        'limits': ['Separate index47 addendum; original job879905 remains failed.',
            'Index46/47 native payloads were not freshly rehashed; original receipt hashes and fresh stat identities bind inputs. Original contract validation retains historical dependency hashing.',
            'No solver-step delivery, source localisation or historical executable-to-source attestation is established.']}
    flux._atomic_json(output/'qualification.json', receipt)
    print('G_HI_INDEX47_ADDENDUM_QUALIFIED', endpoint_product['sha256'], flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-stage', type=Path, required=True)
    parser.add_argument('--expected-host', required=True, help='compatible compute host pinned in the private launcher')
    parser.add_argument('--prefix-capture', type=Path, required=True)
    parser.add_argument('--partial-context', type=Path, required=True)
    parser.add_argument('--partial-context-sha256', required=True)
    parser.add_argument('--endpoint-module', type=Path, required=True)
    parser.add_argument('--endpoint-module-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
