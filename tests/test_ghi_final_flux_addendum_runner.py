from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[1]/'scripts/kunanyi/run_ghi_final_flux_addendum.py'
SPEC = importlib.util.spec_from_file_location('ghi_addendum_runner_test', SOURCE)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prefix_fixture(tmp_path):
    metadata = [{'output_index': i, 'path': f'/native/{i}'} for i in range(48)]
    context, archived = {'checkpoint_sha256': {}}, {}
    for i in range(47):
        name = f'{runner.ANALYSIS}/flux/checkpoints/{i:04d}-{i:04d}.json'
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps({'analysis_signature': runner.ORIGINAL_SIGNATURE, 'snapshot': metadata[i]}).encode()
        path.write_bytes(raw)
        context['checkpoint_sha256'][name] = sha(raw)
        archived['stage/'+name] = raw
    return context, archived, metadata


def endpoint_fixture(valid=True):
    flux = SimpleNamespace(FACE_NAMES=('x_negative', 'x_positive', 'y_negative', 'y_positive', 'z_negative', 'z_positive'),
        CONTROL_RECONSTRUCTIONS=('centered_primitives', 'donor_cell_primitives'),
        FLUX_FIELDS=('mass_flux_outward_g_s', 'total_energy_flux_outward_erg_s'),
        STORAGE_FIELDS=('mass_g', 'total_energy_erg'))
    metadata = {'output_index': 47, 'timestep': 'Timestep_47', 'time_code': 47., 'path': '/native/47'}
    prefix = {'snapshot_index': 47, 'timestep': 'Timestep_47', 'actual_time_code': 47.,
        'actual_time_myr': 47., 'input_h5': '/native/47'}
    faces = [*flux.FACE_NAMES, 'closed_surface_total']
    branches = [('domain_boundary', 'outer_active_cell')]
    if valid:
        branches.append(('domain_boundary', 'linear_to_boundary_face'))
    branches.extend((f'nozzle_control_p{p}', m) for p in (1, 2, 4) for m in flux.CONTROL_RECONSTRUCTIONS)
    availability = {'domain_boundary': {'outer_active_cell': {'available': True, 'reason': 'original_native_gate_passed'},
        'linear_to_boundary_face': {'available': valid, 'reason': 'all_six_faces_valid' if valid else 'invalid_linear_primitive_faces',
            'invalid_faces': [] if valid else ['x_negative']}}}
    availability.update({f'nozzle_control_p{p}': {m: {'available': True, 'reason': 'original_native_gate_passed'}
        for m in flux.CONTROL_RECONSTRUCTIONS} for p in (1, 2, 4)})
    diagnostics = [{'face': face, 'active': {'valid': True}, 'inner': {'valid': True},
        'linear': {'valid': valid or face != 'x_negative', 'invalid_cell_count': int(not valid and face == 'x_negative')},
        'original_linear_gate_passed': valid or face != 'x_negative'} for face in flux.FACE_NAMES]
    endpoint = {'schema_version': 1, 'method_version': 1, 'status': 'measured_ghi_final_snapshot_addendum', 'case': 'G-HI',
        'snapshot': metadata, 'scientific_qualification': {'qualified': False}, 'surface_availability': availability,
        'flux_rows': [{**prefix, 'surface': s, 'reconstruction': m, 'face': f,
            'mass_flux_outward_g_s': 1., 'total_energy_flux_outward_erg_s': 2.} for s, m in branches for f in faces],
        'storage_rows': [{**prefix, 'volume_geometry': g, 'region': r, 'mass_g': 1., 'total_energy_erg': 2.}
            for g in ('exact_fv_nodes', 'legacy_midpoint_centres') for r in ('whole_grid', 'nozzle_control_p1',
                'nozzle_control_p2', 'nozzle_control_p4', 'boundary_layer_1', 'boundary_layer_2', 'boundary_layer_4', 'boundary_layer_8')],
        'linear_diagnostics': {'native_primitives_valid': True, 'all_faces_linear_valid': valid,
            'invalid_faces': [] if valid else ['x_negative'], 'linear_invalid_cell_count_sum_over_faces': int(not valid),
            'faces': diagnostics}}
    return endpoint, metadata, flux


def test_hash_and_stat_change_fail_closed(tmp_path):
    path = tmp_path/'source'
    path.write_bytes(b'original')
    identity = runner.checked_hash(path, sha(b'original'))
    runner.unchanged([identity], rehash=True)
    path.write_bytes(b'modified')
    with pytest.raises(ValueError, match='identity changed'):
        runner.unchanged([identity], rehash=True)
    with pytest.raises(ValueError, match='hash mismatch'):
        runner.checked_hash(path, sha(b'original'))


def test_original_stage_source_pin(tmp_path, monkeypatch):
    entries = []
    for i in range(37):
        path = tmp_path/f'{i}.py'
        path.write_bytes(str(i).encode())
        entries.append(f'{sha(path.read_bytes())}  {path.name}\n')
    manifest = tmp_path/'stage_checksums.sha256'
    manifest.write_text(''.join(entries))
    monkeypatch.setattr(runner, 'ORIGINAL_STAGE_SHA256', sha(manifest.read_bytes()))
    assert len(runner.verify_original_stage(tmp_path)) == 38
    (tmp_path/'0.py').write_bytes(b'changed producer')
    with pytest.raises(ValueError, match='hash mismatch'):
        runner.verify_original_stage(tmp_path)


def test_context_signature_and_index_envelope(monkeypatch):
    payload = {'method_version': 1, 'case': 'G-HI', 'snapshots': [{'output_index': i} for i in range(48)]}
    signature = sha(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode())
    monkeypatch.setattr(runner, 'ORIGINAL_SIGNATURE', signature)
    context = {'status': 'derived_partial_checkpoint_reduction', 'original_request_status': 'failed_at_index_47',
        'original_native_run_completed': False, 'final_native_and_source_stability_checks_executed': False,
        'case': 'G-HI', 'kept_indices': list(range(47)), 'excluded_failed_index': 47,
        'original_full_signature_payload': payload, 'original_full_analysis_signature': signature,
        'checkpoint_sha256': {f'{runner.ANALYSIS}/flux/checkpoints/{i:04d}-{i:04d}.json': 'test' for i in range(47)}}
    assert runner.validate_context(context) == payload
    changed = copy.deepcopy(context)
    changed['original_full_signature_payload']['method_version'] = 2
    with pytest.raises(ValueError, match='signature mismatch'):
        runner.validate_context(changed)
    context['kept_indices'].append(47)
    with pytest.raises(ValueError, match='partial context'):
        runner.validate_context(context)


def test_prefix_matches_archive_context_and_live_bytes(tmp_path):
    context, archived, metadata = prefix_fixture(tmp_path)
    identities, inventory = runner.validate_prefix(tmp_path, context, archived, metadata)
    assert len(identities) == len(inventory) == 47
    assert inventory[46]['filename'] == '0046-0046.json'
    (tmp_path/runner.ANALYSIS/'flux/checkpoints/0046-0046.json').write_bytes(b'substituted checkpoint')
    with pytest.raises(ValueError, match='hash mismatch'):
        runner.validate_prefix(tmp_path, context, archived, metadata)


def test_prefix_metadata_substitution_fails(tmp_path):
    context, archived, metadata = prefix_fixture(tmp_path)
    metadata[46]['path'] = '/another/native46'
    with pytest.raises(ValueError, match='metadata/signature mismatch'):
        runner.validate_prefix(tmp_path, context, archived, metadata)


def test_host_pin_and_wrong_module_origin_fail(tmp_path, monkeypatch):
    (tmp_path/runner.ANALYSIS/'bound_snapshots').mkdir(parents=True)
    monkeypatch.setattr(runner.socket, 'gethostname', lambda: 'fixture-node.example')
    assert runner.site_identity(tmp_path, 'fixture-node')['hostname'] == 'fixture-node'
    with pytest.raises(ValueError, match='pinned compatible compute host'):
        runner.site_identity(tmp_path, 'another-node')
    monkeypatch.setitem(sys.modules, 'run_review_accounting', SimpleNamespace(__file__='/wrong/producer.py'))
    with pytest.raises(ValueError, match='outside original stage'):
        runner.original_modules(tmp_path)


def test_output_symlink_into_original_stage_fails_before_native_work(tmp_path):
    stage = tmp_path/'stage'
    stage.mkdir()
    alias = tmp_path/'stage-alias'
    alias.symlink_to(stage, target_is_directory=True)
    with pytest.raises(ValueError, match='outside original stage'):
        runner.run(SimpleNamespace(original_stage=stage, output_dir=alias/'new-output'))


def test_label_parameters_allow_other_original_config_keys():
    context = {'pluto_parameters': {'JET_PWR': 1.e45, 'JET_START_TIME': 0., 'JET_ACTIVE_TIME': 50.}}
    live = {**context['pluto_parameters'], 'JET_INJECTION_HEIGHT': 1., 'JET_SPD': .1}
    runner.validate_parameters(live, context)
    live['JET_PWR'] *= 2
    with pytest.raises(ValueError, match='labelled runtime parameters'):
        runner.validate_parameters(live, context)


@pytest.mark.parametrize('valid', [True, False])
def test_endpoint_complete_available_branch_inventory(valid):
    endpoint, metadata, flux = endpoint_fixture(valid)
    runner.validate_endpoint(endpoint, metadata, flux=flux, time_myr=47.)


@pytest.mark.parametrize('mutation', ['storage_duplicate', 'invalid_linear_published', 'availability', 'nonfinite', 'wrong_index'])
def test_endpoint_rejects_inconsistent_or_invalid_product(mutation):
    endpoint, metadata, flux = endpoint_fixture(False)
    if mutation == 'storage_duplicate':
        endpoint['storage_rows'][-1] = copy.deepcopy(endpoint['storage_rows'][0])
    elif mutation == 'invalid_linear_published':
        endpoint['flux_rows'].append({**endpoint['flux_rows'][0], 'reconstruction': 'linear_to_boundary_face'})
    elif mutation == 'availability':
        endpoint['surface_availability']['domain_boundary']['linear_to_boundary_face']['available'] = True
    elif mutation == 'nonfinite':
        endpoint['flux_rows'][0]['total_energy_flux_outward_erg_s'] = float('nan')
    else:
        endpoint['flux_rows'][0]['snapshot_index'] = 48
    with pytest.raises(ValueError):
        runner.validate_endpoint(endpoint, metadata, flux=flux, time_myr=47.)


def test_added_c_source_is_detected(tmp_path):
    (tmp_path/'original.c').write_text('original')
    runner.validate_source_inventory(tmp_path, {'original.c': 'hash'})
    (tmp_path/'added.c').write_text('unreviewed')
    with pytest.raises(ValueError, match='source inventory changed'):
        runner.validate_source_inventory(tmp_path, {'original.c': 'hash'})
