from pathlib import Path
import json
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/science'))
import run_background_refit_blind as blind


def axes():
    edges = np.array([-200., -100., 0., 100., 200.])
    centres = (edges[:-1] + edges[1:]) / 2
    return dict(zip(blind.AXES, (centres, edges, centres, edges)))


def config(tmp_path):
    value = {'schema': 1, 'runner_sha256': blind.digest(blind.__file__), 'source_sha256': {},
             'heldout_indices': {'C-HI': [10]}, 'null_cases': ['C-HI'], 'azimuths_deg': [0],
             'correction_policies': ['retained_linear'], 'velocity_cuts_km_s': [100],
             'methods': list(blind.emission.METHODS),
             'criteria': {'minimum_completeness': .75, 'minimum_purity': .95}}
    path = tmp_path / 'config.json'
    blind.write_json(path, value)
    return path, value


def test_freeze_rejects_source_mutation_and_wrong_runner(tmp_path):
    path, value = config(tmp_path)
    value['source_sha256'] = {'scripts/science/build_q032_source_emission.py': '0' * 64}
    blind.write_json(path, value)
    with pytest.raises(ValueError, match='frozen source'):
        blind.load_config(path)
    value['source_sha256'] = {}
    value['runner_sha256'] = '0' * 64
    blind.write_json(path, value)
    with pytest.raises(ValueError, match='frozen runner'):
        blind.load_config(path)


def test_manifest_requires_all_units_once_and_excludes_development_case(tmp_path):
    _, value = config(tmp_path)
    units = [{'case': 'C-HI', 'snapshot_index': index, 'view_deg': 0,
              'kind': kind, 'unit_id': str(index)} for index, kind in [(10, 'science'), (0, 'initial_null')]]
    blind.validate_units(value, units)
    with pytest.raises(ValueError, match='exactly once'):
        blind.validate_units(value, units + [units[0]])
    units[0] = {**units[0], 'case': 'G-HI', 'snapshot_index': 20}
    with pytest.raises(ValueError, match='exactly once'):
        blind.validate_units(value, units)


def test_per_side_scoring_keeps_nondetections_and_all_truth_in_denominator():
    a = axes()
    truth = np.zeros((4, 4), dtype=bool)
    truth[0, 0] = truth[1, 1] = truth[2, 2] = True
    found = np.zeros_like(truth)
    found[1, 1] = True
    criteria = {'minimum_completeness': .75, 'minimum_purity': .95}
    low = blind.side_score(found, truth, a, 'negative_z', 'science', criteria)
    high = blind.side_score(found, truth, a, 'positive_z', 'science', criteria)
    assert low['completeness'] == .5
    assert low['purity'] == 1
    assert low['truth_fraction_inside_candidate_aperture'] == .5
    assert not low['generalization_criterion_passed']
    assert high['nondetection'] and high['completeness'] == 0 and high['purity'] is None
    assert not high['generalization_criterion_passed']


def test_null_detections_fail_and_nonnull_target_is_not_a_null():
    mask = np.zeros((4, 4), dtype=bool)
    criteria = {'minimum_completeness': .75, 'minimum_purity': .95}
    assert blind.side_score(mask, mask, axes(), 'negative_z', 'initial_null', criteria)['generalization_criterion_passed']
    mask[1, 1] = True
    assert not blind.side_score(mask, np.zeros_like(mask), axes(), 'negative_z', 'initial_null', criteria)['generalization_criterion_passed']
    with pytest.raises(ValueError, match='nonzero tracer truth'):
        blind.side_score(mask, mask, axes(), 'negative_z', 'initial_null', criteria)


def test_two_phase_prediction_does_not_read_truth_and_detects_tampering(tmp_path, monkeypatch):
    config_path, _ = config(tmp_path)
    units, truths = [], []
    for index, kind in [(10, 'science'), (0, 'initial_null')]:
        path = tmp_path / f'maps{index}.npz'
        image = np.ones((4, 4))
        replacement = np.zeros_like(image)
        if index:
            image[1, 1] = .9
            replacement[1, 1] = -.2
        np.savez(path, **axes(), brightness_current_retained_linear_whole=image,
                 deficit_retained_linear_A_v100=replacement,
                 path_C_kpc=np.array({'reading this object requires forbidden pickle'}, dtype=object))
        base = {'case': 'C-HI', 'snapshot_index': index, 'view_deg': 0,
                'kind': kind, 'unit_id': str(index), 'qualification_holds': ['synthetic_diagnostic_only']}
        native = tmp_path / f'native{index}.json'
        producer = tmp_path / f'producer{index}.json'
        blind.write_json(native, {'case': 'C-HI', 'snapshot_index': index})
        native_record = {'path': str(native), 'sha256': blind.digest(native)}
        blind.write_json(producer, {'case': 'C-HI', 'snapshot_index': index,
                                   'provenance': {'native_input_receipt': native_record},
                                   'scientific_qualification': {'qualified': False, 'holds': base['qualification_holds']},
                                   'files': {path.name: {'sha256': blind.digest(path)}}})
        base['provenance'] = {'native_input_receipt': native_record,
                              'producer_receipt': {'path': str(producer), 'sha256': blind.digest(producer)}}
        units.append({**base, 'maps': {'path': str(path), 'sha256': blind.digest(path)}})
        truth_path = tmp_path / f'truth{index}.npz'
        truth = np.zeros_like(image)
        if index:
            truth[1, 1] = 1
        np.savez(truth_path, **axes(), path_C_kpc=truth)
        truths.append({**base, 'truth': {'path': str(truth_path), 'sha256': blind.digest(truth_path)}})
    manifest, truth_manifest = tmp_path / 'manifest.json', tmp_path / 'truth_manifest.json'
    blind.write_json(manifest, {'units': units})
    blind.write_json(truth_manifest, {'units': truths})
    seen = []
    def detector(image, h, z):
        seen.append(image.copy())
        return {method: image < .8 for method in blind.emission.METHODS}
    monkeypatch.setattr(blind, 'observer_masks', detector)
    predictions = tmp_path / 'predictions'
    receipt = blind.predict(config_path, manifest, predictions)
    assert receipt['scoring_truth_read'] is False
    assert not seen[0][1, 1] < .8 and seen[1][1, 1] < .8
    result = blind.score(config_path, predictions, truth_manifest, tmp_path / 'scores')
    assert result['detector_adopted'] is False
    assert all(group['failed_sides'] > 0 for group in result['groups'])
    assert all(group['primary_side_count'] == 4 for group in result['groups'])
    assert 'synthetic_diagnostic_only' in (tmp_path / 'scores/scores.csv').read_text()
    receipt_path = predictions / 'prediction_receipt.json'
    saved_receipt = receipt_path.read_text()
    for broken in ([], receipt['units'][0]['labels'][:-1], receipt['units'][0]['labels'] + [receipt['units'][0]['labels'][0]]):
        receipt['units'][0]['labels'] = broken
        blind.write_json(receipt_path, receipt)
        with pytest.raises(ValueError, match='prediction labels'):
            blind.score(config_path, predictions, truth_manifest, tmp_path / 'incomplete_score')
    receipt_path.write_text(saved_receipt)
    truth_records = blind.read_json(truth_manifest)
    truth_records['units'][0]['qualification_holds'] = []
    blind.write_json(truth_manifest, truth_records)
    with pytest.raises(ValueError, match='qualification holds'):
        blind.score(config_path, predictions, truth_manifest, tmp_path / 'different_holds')
    blind.write_json(truth_manifest, {'units': truths})
    prediction_file = predictions / '10.npz'
    prediction_file.write_bytes(prediction_file.read_bytes() + b'tampered')
    with pytest.raises(ValueError, match='changed after sealing'):
        blind.score(config_path, predictions, truth_manifest, tmp_path / 'scores_after_tamper')
