"""Bind and seal a completed image cohort while holding its scoring resources closed."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

SCIENCE = Path(__file__).resolve().parents[1] / 'science'
sys.path.insert(0, str(SCIENCE))
import assemble_blind_emission_cohort as assembler
import run_background_refit_blind as blind


def file_record(path):
    return {'path': str(path.absolute()), 'sha256': blind.digest(path)}


def attest_predictions(config_path, manifest_path, prediction_dir):
    """Check opaque prediction bytes, registered labels and input commitments."""
    config = blind.load_config(config_path)
    manifest = blind.read_json(manifest_path)
    blind.validate_units(config, manifest['units'])
    inputs = {unit['unit_id']: unit for unit in manifest['units']}
    receipt_path = prediction_dir / 'prediction_receipt.json'
    receipt = blind.read_json(receipt_path)
    if (receipt['status'] != 'predictions_sealed_before_scoring' or receipt['scoring_truth_read'] is not False
            or receipt['config_sha256'] != blind.digest(config_path)
            or receipt['input_manifest_sha256'] != blind.digest(manifest_path)
            or receipt['runner_sha256'] != config['runner_sha256']):
        raise ValueError('prediction receipt does not bind this source, config and complete manifest')
    blind.validate_units(config, receipt['units'])
    expected_files = {receipt_path.name}
    sealed = []
    labels = blind.expected_labels(config)
    for unit in receipt['units']:
        source = inputs[unit['unit_id']]
        name = unit['unit_id'] + '.npz'
        if (blind.unit_key(source) != blind.unit_key(unit) or unit['predictions'] != name
                or unit['input_sha256'] != source['maps']['sha256'] or unit['provenance'] != source['provenance']
                or unit['qualification_holds'] != source['qualification_holds']):
            raise ValueError('prediction case, source, qualification or provenance changed')
        blind.validate_labels(config, unit['labels'])
        path = prediction_dir / name
        if path.is_symlink() or not path.is_file() or blind.digest(path) != unit['prediction_sha256']:
            raise ValueError(f'prediction bytes changed for {name}')
        expected_files.add(name)
        sealed.append({'unit_id': unit['unit_id'], 'case': unit['case'], 'snapshot_index': unit['snapshot_index'],
                       'view_deg': unit['view_deg'], 'kind': unit['kind'], 'file': name, 'size_bytes': path.stat().st_size,
                       'prediction_sha256': unit['prediction_sha256'], 'maps_sha256': unit['input_sha256'],
                       'source_receipt_sha256': source['provenance']['native_input_receipt']['sha256'],
                       'producer_receipt_sha256': source['provenance']['producer_receipt']['sha256']})
    if {path.name for path in prediction_dir.iterdir()} != expected_files:
        raise ValueError('unexpected or missing file in sealed directory')
    counts = Counter(row['kind'] for row in sealed)
    return {'utc_after_validation': datetime.now(timezone.utc).isoformat(),
            'protocol_config_sha256': blind.digest(config_path), 'frozen_runner_sha256': config['runner_sha256'],
            'maps_manifest_sha256': blind.digest(manifest_path), 'prediction_receipt_sha256': blind.digest(receipt_path),
            'science_views': counts['science'], 'initial_null_views': counts['initial_null'],
            'labels_per_view': len(labels), 'prediction_masks': len(labels) * len(sealed),
            'label_definitions': labels, 'units': sealed}


def seal(stage, config_path, slots_path, destination):
    """Close the scoring manifest and raster permissions before predicting on image inputs."""
    if destination.exists():
        raise ValueError('choose a new seal directory for every attempt')
    slots = blind.read_json(slots_path)
    config = blind.load_config(config_path)
    expected = {(case, index, kind) for case, index, _, kind in blind.expected_units(config)}
    selected = [(row['case'], row['snapshot_index'], row['kind']) for row in slots]
    if len(selected) != len(set(selected)) or set(selected) != expected:
        raise ValueError('producer slots differ from frozen units')
    entries = []
    truth_files = []
    for row in slots:
        case, index = row['case'], row['snapshot_index']
        native = row['native_input_receipt']
        completion = stage / 'products' / f'{case}_{index:04d}' / 'completion.json'
        producer = blind.read_json(completion)
        if producer['provenance']['contract']['sha256'] != row['contract']['sha256']:
            raise ValueError('producer contract differs from staged slot')
        entries.append({'producer_receipt': file_record(completion), 'native_input_receipt': native})
        truth_files.extend(completion.parent / unit['truth_filename'] for unit in producer['units'])
    destination.mkdir(mode=0o700, parents=True)
    inventory = destination / 'producer_inventory.json'
    blind.write_json(inventory, {'schema': 1, 'producers': entries})
    manifests = destination / 'manifests'
    result = assembler.assemble(config_path, blind.digest(config_path), inventory, manifests)
    if (result['scoring_truth_released'] is not False or result['truth_arrays_read'] is not False
            or result['producer_count'] != len(slots) or result['truth_units'] != len(truth_files)):
        raise ValueError('incomplete cohort or unexpected assembly exposure')
    truth_files.append(manifests / 'scoring_truth_manifest.json')
    for path in truth_files:
        path.chmod(0)
    protected_utc = datetime.now(timezone.utc).isoformat()
    predictions = destination / 'predictions'
    blind.predict(config_path, manifests / 'maps_manifest.json', predictions)
    audit = attest_predictions(config_path, manifests / 'maps_manifest.json', predictions)
    if any(path.stat().st_mode & 0o777 for path in truth_files):
        raise ValueError('a scoring file was readable during sealing')
    for path in predictions.iterdir():
        path.chmod(0o400)
    predictions.chmod(0o500)
    audit.update(status='full_cohort_sealed_awaiting_independent_custody_review',
                 scoring_truth_released=False, scoring_truth_arrays_evaluated=False,
                 producer_count=result['producer_count'], truth_files_protected=len(truth_files),
                 protected_before_prediction_utc=protected_utc, assembler_sha256=result['assembler_sha256'],
                 producer_source_sha256=result['producer_source_sha256'],
                 producer_inventory_sha256=blind.digest(inventory), assembly_receipt_sha256=blind.digest(manifests/'assembly_receipt.json'),
                 scoring_manifest_commitment_sha256=result['files']['scoring_truth_manifest.json']['sha256'])
    out = destination / 'seal.json'
    blind.write_json(out, audit)
    out.chmod(0o400)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--slots', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    audit = seal(args.stage.resolve(), args.config.resolve(), args.slots.resolve(), args.output_dir.resolve())
    print(audit['status'], audit['science_views'], audit['initial_null_views'], audit['prediction_receipt_sha256'])
