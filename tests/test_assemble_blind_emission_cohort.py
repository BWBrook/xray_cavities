from pathlib import Path
import json
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/science'))
import assemble_blind_emission_cohort as cohort


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/background_refit_blind_2026-11-11.json'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def record(path):
    return {'path': str(path.absolute()), 'sha256': cohort.blind.digest(path)}


@pytest.fixture
def inventory(tmp_path):
    config = cohort.blind.load_config(CONFIG)
    config_pin = cohort.blind.digest(CONFIG)
    source_keys = sorted({(case, index, kind) for case, index, _, kind in cohort.blind.expected_units(config)})
    entries = []
    for case, index, kind in source_keys:
        root = tmp_path / f'{case}_{index:04d}'
        root.mkdir()
        axes = {'horizontal_axis_kpc': np.array([-.5, .5]), 'horizontal_edges_kpc': np.array([-1., 0., 1.]),
                'z_axis_kpc': np.array([-.5, .5]), 'z_edges_kpc': np.array([-1., 0., 1.])}
        fields = {field: np.zeros((2, 2)) for field in cohort.producer.DETECTOR_FIELDS if field not in axes}
        fields.update(axes)
        fields['path_C_kpc'] = np.ones((2, 2))
        units = cohort.producer.publish_maps(root, case, index, kind,
                                            {angle: fields for angle in config['azimuths_deg']})
        native_path = root / 'native.json'
        write_json(native_path, {'schema_version': 1, 'status': 'bound_spherical_budget_inputs',
                   'case': case, 'snapshot_index': index,
                   'native_preflight': {'scientific_qualification': {'holds': ['upstream_scientific_hold']}}})
        native_record = record(native_path)
        sources = {Path(path).name: {'sha256': pin} for path, pin in config['source_sha256'].items()}
        sources['run_background_refit_blind.py'] = {'sha256': config['runner_sha256']}
        sources['prepare_blind_emission_maps.py'] = {'sha256': cohort.blind.digest(cohort.producer.__file__)}
        receipt = {'schema_version': 1, 'case': case, 'snapshot_index': index, 'kind': kind,
                   'execution_status': 'sealed_native_emission_maps_prepared_no_observer_scoring',
                   'native_filling_measured': False, 'observer_statistics_computed': False,
                   'placeholder_filling_rows_discarded': True,
                   'frequency_hz': cohort.producer.FREQUENCY_HZ, 'redshift': cohort.producer.REDSHIFT,
                   'sky_axis_policy': cohort.producer.AXIS_POLICY,
                   'provenance': {'protocol_config': {'sha256': config_pin}, 'analysis_sources': sources,
                       'runtime': {name: {'sha256': pin} for name, pin in cohort.producer.RUNTIME_HASHES.items()},
                       'native_input_receipt': native_record},
                   'scientific_qualification': {'qualified': False, 'holds': ['upstream_scientific_hold', 'diagnostic_only']},
                   'units': units,
                   'files': {path.name: {'sha256': cohort.blind.digest(path), 'size_bytes': path.stat().st_size}
                             for path in root.glob('*.npz')}}
        producer_path = root / 'completion.json'
        write_json(producer_path, receipt)
        entries.append({'producer_receipt': record(producer_path), 'native_input_receipt': native_record})
    path = tmp_path / 'inventory.json'
    write_json(path, {'schema': 1, 'producers': entries})
    return path


def assemble(inventory, output):
    return cohort.assemble(CONFIG, cohort.blind.digest(CONFIG), inventory, output)


def change_receipt(inventory, change):
    data = cohort.blind.read_json(inventory)
    entry = data['producers'][0]
    path = Path(entry['producer_receipt']['path'])
    receipt = cohort.blind.read_json(path)
    change(receipt, path.parent)
    write_json(path, receipt)
    entry['producer_receipt'] = record(path)
    write_json(inventory, data)


def test_complete_frozen_cohort_binds_66_maps_and_truth_units_without_reading_truth(inventory, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('assembly must not load any numeric array')
    monkeypatch.setattr(np, 'load', forbidden)
    result = assemble(inventory, tmp_path / 'assembled')
    assert result['producer_count'] == 22
    assert result['map_units'] == result['truth_units'] == 66
    assert result['payload_count'] == 132
    assert result['truth_arrays_read'] is False and result['scoring_truth_released'] is False
    maps = cohort.blind.read_json(tmp_path / 'assembled/maps_manifest.json')
    truth = cohort.blind.read_json(tmp_path / 'assembled/scoring_truth_manifest.json')
    assert {unit['unit_id'] for unit in maps['units']} == {unit['unit_id'] for unit in truth['units']}
    assert all('truth' not in unit for unit in maps['units'])
    assert all('maps' not in unit for unit in truth['units'])
    for unit in truth['units']:
        receipt = cohort.blind.read_json(unit['provenance']['producer_receipt']['path'])
        assert unit['truth']['sha256'] == receipt['files'][Path(unit['truth']['path']).name]['sha256']
        assert unit['qualification_holds'] == ['upstream_scientific_hold', 'diagnostic_only']


@pytest.mark.parametrize('mutation', ['missing_producer', 'duplicate_producer', 'missing_view', 'duplicate_view'])
def test_incomplete_or_duplicate_cases_and_azimuths_are_rejected(inventory, tmp_path, mutation):
    if mutation in ('missing_producer', 'duplicate_producer'):
        data = cohort.blind.read_json(inventory)
        data['producers'] = (data['producers'][:-1] if mutation == 'missing_producer'
                             else data['producers'] + [data['producers'][0]])
        write_json(inventory, data)
    elif mutation == 'missing_view':
        change_receipt(inventory, lambda receipt, root: receipt['units'].pop())
    else:
        change_receipt(inventory, lambda receipt, root: receipt['units'].__setitem__(1, dict(receipt['units'][0])))
    with pytest.raises(ValueError, match='cohort|duplicate producer|three frozen azimuths'):
        assemble(inventory, tmp_path / 'bad')


def test_unsafe_payload_paths_are_rejected(inventory, tmp_path):
    change_receipt(inventory, lambda receipt, root: receipt['units'][0].__setitem__('truth_filename', '../escape.npz'))
    with pytest.raises(ValueError, match='unsafe producer payload'):
        assemble(inventory, tmp_path / 'bad')


def test_truth_payload_hash_must_match_producer_files(inventory, tmp_path):
    data = cohort.blind.read_json(inventory)
    producer_path = Path(data['producers'][0]['producer_receipt']['path'])
    receipt = cohort.blind.read_json(producer_path)
    path = producer_path.parent / receipt['units'][0]['truth_filename']
    path.write_bytes(path.read_bytes() + b'substituted truth')
    with pytest.raises(ValueError, match='hash differs'):
        assemble(inventory, tmp_path / 'bad')


def test_detector_payload_must_not_contain_truth_even_with_updated_hashes(inventory, tmp_path):
    def insert_truth(receipt, root):
        path = root / receipt['units'][0]['maps_filename']
        with np.load(path, allow_pickle=False) as old:
            fields = {name: old[name] for name in old.files}
        fields['path_C_kpc'] = np.ones((2, 2))
        np.savez_compressed(path, **fields)
        receipt['files'][path.name] = {'sha256': cohort.blind.digest(path), 'size_bytes': path.stat().st_size}
    change_receipt(inventory, insert_truth)
    with pytest.raises(ValueError, match='NPZ array inventory differs'):
        assemble(inventory, tmp_path / 'bad')


@pytest.mark.parametrize('mutation', ['native_substitution', 'omitted_hold', 'changed_source', 'changed_config'])
def test_native_source_config_and_qualification_links_are_enforced(inventory, tmp_path, mutation):
    if mutation == 'native_substitution':
        data = cohort.blind.read_json(inventory)
        data['producers'][0]['native_input_receipt'] = data['producers'][1]['native_input_receipt']
        write_json(inventory, data)
    elif mutation == 'omitted_hold':
        change_receipt(inventory, lambda receipt, root: receipt['scientific_qualification'].__setitem__('holds', ['diagnostic_only']))
    elif mutation == 'changed_source':
        change_receipt(inventory, lambda receipt, root: receipt['provenance']['analysis_sources']['prepare_blind_emission_maps.py'].__setitem__('sha256', '0' * 64))
    else:
        change_receipt(inventory, lambda receipt, root: receipt['provenance']['protocol_config'].__setitem__('sha256', '0' * 64))
    with pytest.raises(ValueError, match='native receipt|qualification holds|scientific source|frozen config'):
        assemble(inventory, tmp_path / 'bad')
