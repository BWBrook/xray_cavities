from pathlib import Path
import copy
import json
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/science'))
import prepare_blind_emission_maps as adapter


def grid():
    edges = np.linspace(-4, 4, 9)
    centres = (edges[:-1] + edges[1:]) / 2
    widths = np.diff(edges)
    return adapter.emission.Grid(centres, centres, centres, widths, widths, widths,
                                 edges, edges, edges, 'synthetic_exact_edges')


def primitives():
    return {'rho': np.ones((8, 8, 8)), 'prs': np.ones((8, 8, 8)),
            'vx1': np.zeros((8, 8, 8)), 'vx2': np.zeros((8, 8, 8)),
            'vx3': np.zeros((8, 8, 8)), 'tr1': np.zeros((8, 8, 8))}


def emissivity(rho, pressure):
    values = {key: rho ** 2 for convention in adapter.emission.CONVENTIONS
              for key in (convention, convention + '_before')}
    return values, np.ones_like(rho), {'any': np.zeros_like(rho, dtype=bool),
                                      'raw_nonfinite': np.zeros_like(rho, dtype=bool)}


def native_receipt(case='C-LO', index=20):
    return {'schema_version': 1, 'status': 'bound_spherical_budget_inputs',
            'case': case, 'snapshot_index': index,
            'inputs': {name: {} for name in ('initial_h5', 'current_h5', 'environment')},
            'initial': {'time_code': 0, 'timestep': 'Timestep_0'},
            'current': {'time_code': index * adapter.BUDGET.CODE_TIME_PER_MYR, 'timestep': 'Timestep_1'},
            'native_preflight': {'semantic_checks': {name: 'passed' for name in adapter.SEMANTICS},
                                 'scientific_qualification': {'qualified': False, 'holds': ['upstream_hold']}}}


def test_placeholder_masks_do_not_change_emission_paths_or_signed_replacement():
    g = grid()
    current, initial = primitives(), primitives()
    current['tr1'][:, :, :4] = .5
    current['rho'][:, :, :4] = .1
    current['rho'][:, :, 4:] = 2
    current['vx1'][:, :, 4:] = 200e5 / adapter.BUDGET.UNIT_VELOCITY_CMS
    maps, diagnostics, projection = adapter.integrate_maps(current, initial, g, emissivity)
    reference = adapter.make_views(g)
    for view in reference.values():
        for observer in view.observers.values():
            observer['mask'][:] = True
    filling, _ = adapter.emission.integrate_native(current, initial, g, reference, emissivity)
    assert any(row['volume_kpc3_denominator'] > 0 for row in filling)
    for angle, fields in maps.items():
        view = reference[angle]
        np.testing.assert_allclose(fields['path_C_kpc'], view.maps['path_C_kpc'])
        for convention in adapter.emission.CONVENTIONS:
            np.testing.assert_allclose(fields[f'brightness_current_{convention}_whole'],
                                       view.maps[f'brightness_current_{convention}_whole'])
            for cut in adapter.emission.CUTS:
                np.testing.assert_allclose(fields[f'deficit_{convention}_A_v{cut}'],
                    view.maps[f'brightness_initial_{convention}_A_v{cut}'] - view.maps[f'brightness_current_{convention}_A_v{cut}'])
        assert np.any(fields['deficit_retained_linear_A_v100'] < 0)
        assert np.all(fields['deficit_retained_linear_A_v300'] == 0)
        assert not any('mask' in key or 'filling' in key for key in fields)
        assert projection[str(angle)]['geometry']['operator']
    assert diagnostics['tracer_outside_unit_interval_count'] == 0


def test_initial_same_cell_maps_have_zero_replacement_even_with_nozzle_tracer():
    now = primitives()
    now['tr1'][:, 3:5, 3:5] = 1
    now['vx1'][:, 3:5, 3:5] = 200e5 / adapter.BUDGET.UNIT_VELOCITY_CMS
    maps, _, _ = adapter.integrate_maps(now, now, grid(), emissivity)
    for fields in maps.values():
        assert np.any(fields['path_C_kpc'] > 0)
        assert all(np.all(value == 0) for key, value in fields.items() if key.startswith('deficit_'))


def test_serialization_keeps_projected_truth_out_of_detector_inputs(tmp_path):
    current = primitives()
    current['tr1'][:, :, :4] = .5
    maps, _, _ = adapter.integrate_maps(current, primitives(), grid(), emissivity)
    for kind, index in [('science', 20), ('initial_null', 0)]:
        directory = tmp_path / kind
        directory.mkdir()
        units = adapter.publish_maps(directory, 'C-LO', index, kind, maps)
        for unit in units:
            with np.load(directory / unit['maps_filename'], allow_pickle=False) as detector:
                assert set(detector.files) == set(adapter.DETECTOR_FIELDS)
                assert 'path_C_kpc' not in detector.files
                assert not any('tracer' in key for key in detector.files)
            with np.load(directory / unit['truth_filename'], allow_pickle=False) as truth:
                assert set(truth.files) == set(adapter.blind.AXES) | {'path_C_kpc'}
                assert bool(np.any(truth['path_C_kpc'])) == (kind == 'science')


def test_specification_rejects_development_excluded_epochs_and_runtime_drift():
    config = {'heldout_indices': {'C-LO': [20], 'G-HI': [10, 30, 40]},
              'azimuths_deg': [0, 45, 90], 'null_cases': ['C-LO', 'G-HI']}
    spec = {'schema_version': 1, 'case': 'C-LO', 'snapshot_index': 20, 'kind': 'science',
            'frequency_hz': adapter.FREQUENCY_HZ, 'redshift': adapter.REDSHIFT,
            'sky_axis_policy': adapter.AXIS_POLICY, 'views_side_on_azimuth_deg': [0, 45, 90],
            'inputs': {key: {'sha256': digest} for key, digest in adapter.RUNTIME_HASHES.items()}}
    adapter.validate_specification(spec, config)
    for index in (20, 48, 50):
        with pytest.raises(ValueError, match='outside the frozen'):
            adapter.validate_specification({**spec, 'case': 'G-HI', 'snapshot_index': index}, config)
    changed = copy.deepcopy(spec)
    changed['inputs']['apec_table']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='runtime differs'):
        adapter.validate_specification(changed, config)
    with pytest.raises(ValueError, match='convention differs'):
        adapter.validate_specification({**spec, 'redshift': .1}, config)


def test_native_receipt_requires_case_epoch_and_semantic_preflight():
    receipt = native_receipt()
    adapter.validate_native_receipt(receipt, 'C-LO', 20)
    with pytest.raises(ValueError, match='actual case/index'):
        adapter.validate_native_receipt(receipt, 'C-HI', 20)
    receipt['native_preflight']['semantic_checks']['initialization_gamma'] = 'not_checked'
    with pytest.raises(ValueError, match='semantic preflight'):
        adapter.validate_native_receipt(receipt, 'C-LO', 20)
    receipt = native_receipt('G-HI', 30)
    with pytest.raises(ValueError, match='retained-chain'):
        adapter.validate_native_receipt(receipt, 'G-HI', 30)


def test_arbitrary_retained_ghi_epoch_stays_bound_to_accepted_lineage(tmp_path):
    receipt = native_receipt('G-HI', 30)
    receipt['native_preflight']['semantic_checks']['inherited_parent_source_restart_and_chain'] = 'passed'
    chain = [{'output_index': index} for index in range(51)]
    for role, epoch, index in [('initial_h5', 'initial', 0), ('current_h5', 'current', 30)]:
        path = tmp_path / f'data.{index:04d}.flt.h5'
        path.write_bytes(b'synthetic lineage identity fixture')
        identity = adapter.BUDGET._stat_identity(path)
        receipt['inputs'][role] = identity
        chain[index] |= {**identity, **receipt[epoch]}
    lineage_path = tmp_path / 'lineage.json'
    lineage_path.write_text(json.dumps({'schema_version': 1, 'status': 'passed',
        'lineage': 'accepted failed-run parent build/source plus validated 10 Myr home continuation',
        'snapshots': {'analysis_chain': chain}}))
    receipt['native_preflight']['inherited_lineage'] = {'receipt': {
        'path': str(lineage_path), 'sha256': adapter.BUDGET._sha256(lineage_path)}}
    assert adapter.bind_lineage(receipt)['sha256'] == adapter.BUDGET._sha256(lineage_path)
    receipt['current']['time_code'] += 1
    with pytest.raises(ValueError, match='identity/time differs'):
        adapter.bind_lineage(receipt)


def test_native_case_contract_rejects_relabelling_and_snapshot_substitution():
    receipt = native_receipt()
    snapshots = [{'index': index, 'path': f'/synthetic/C-LO/data.{index:04d}.flt.h5'} for index in range(51)]
    receipt['inputs']['initial_h5'] = {'path': snapshots[0]['path']}
    receipt['inputs']['current_h5'] = {'path': snapshots[20]['path']}
    receipt['inputs']['environment'] = {'path': '/synthetic/environment.csv', 'sha256': '1' * 64}
    case_contract = {'schema_version': 1, 'case': 'C-LO', 'snapshots': snapshots,
                     'files': {'environment': dict(receipt['inputs']['environment'])}}
    adapter.validate_receipt_contract(receipt, case_contract)
    with pytest.raises(ValueError, match='relabelled'):
        adapter.validate_receipt_contract(receipt, {**case_contract, 'case': 'C-HI'})
    receipt['inputs']['current_h5']['path'] = '/synthetic/another-case/data.0020.flt.h5'
    with pytest.raises(ValueError, match='escapes its case contract'):
        adapter.validate_receipt_contract(receipt, case_contract)


def test_qualification_holds_preserve_upstream_flags():
    now = primitives()
    now['tr1'][:, :, :4] = .5
    _, diagnostics, projection = adapter.integrate_maps(now, primitives(), grid(), emissivity)
    holds = adapter.qualification_holds(native_receipt(), diagnostics, projection)
    assert 'upstream_hold' in holds
    assert 'native_filling_not_measured_for_any_observer_mask' in holds
    assert 'cocoon_contacts_native_domain_boundary' in holds
    assert 'initial_reference_is_not_an_evolved_nojet_counterfactual' in holds
