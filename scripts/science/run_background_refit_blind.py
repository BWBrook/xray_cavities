"""Freeze predictions before opening truth for the background-refit diagnostic."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

import build_q032_source_emission as emission


ROOT = Path(__file__).resolve().parents[2]
MODES = ('observer_refit', 'ambient_replaced_refit')
AXES = ('horizontal_axis_kpc', 'horizontal_edges_kpc', 'z_axis_kpc', 'z_edges_kpc')


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def bind(record):
    path = Path(record['path'])
    if not path.is_absolute() or not path.is_file() or digest(path) != record['sha256']:
        raise ValueError('missing, nonabsolute or changed bound input')
    return path


def load_config(path):
    config = read_json(path)
    if config['schema'] != 1 or config['runner_sha256'] != digest(__file__):
        raise ValueError('protocol schema or frozen runner differs')
    for name, expected in config['source_sha256'].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f'frozen source differs: {name}')
    return config


def expected_units(config):
    return {(case, index, angle, 'science')
            for case, indices in config['heldout_indices'].items()
            for index in indices for angle in config['azimuths_deg']} | {
                (case, 0, angle, 'initial_null') for case in config['null_cases']
                for angle in config['azimuths_deg']}


def unit_key(unit):
    return (unit['case'], unit['snapshot_index'], unit['view_deg'], unit['kind'])


def validate_units(config, units):
    keys = [unit_key(unit) for unit in units]
    if len(keys) != len(set(keys)) or set(keys) != expected_units(config):
        raise ValueError('manifest must contain each frozen science and null unit exactly once')
    identifiers = [unit['unit_id'] for unit in units]
    if (len(identifiers) != len(set(identifiers))
            or any(not name or Path(name).name != name or name in ('.', '..') for name in identifiers)):
        raise ValueError('unsafe or duplicate unit identifier')


def expected_labels(config):
    labels = []
    for convention in config['correction_policies']:
        for mode in MODES:
            for cut in ([0] if mode == 'observer_refit' else config['velocity_cuts_km_s']):
                for method in config['methods']:
                    labels.append({'key': f'{mode}__{method}__{convention}__v{cut}',
                                   'mode': mode, 'method': method, 'correction': convention,
                                   'velocity_cut_km_s': cut,
                                   'truth_assisted_input': mode != 'observer_refit'})
    return labels


def validate_labels(config, labels):
    expected = expected_labels(config)
    if (len(labels) != len(expected) or len({row['key'] for row in labels}) != len(labels)
            or {row['key']: row for row in labels} != {row['key']: row for row in expected}):
        raise ValueError('missing, duplicate or changed frozen prediction labels')


def bind_provenance(unit):
    provenance = unit['provenance']
    if set(provenance) != {'native_input_receipt', 'producer_receipt'}:
        raise ValueError('native and producer provenance must both be bound')
    native = read_json(bind(provenance['native_input_receipt']))
    producer = read_json(bind(provenance['producer_receipt']))
    if any(record.get('case') != unit['case'] or record.get('snapshot_index') != unit['snapshot_index']
           for record in (native, producer)):
        raise ValueError('source-native provenance unit differs')
    if producer['provenance']['native_input_receipt']['sha256'] != provenance['native_input_receipt']['sha256']:
        raise ValueError('producer/native receipt chain differs')
    if producer['scientific_qualification']['holds'] != unit['qualification_holds']:
        raise ValueError('producer qualification holds differ from manifest')
    if 'maps' in unit:
        record = producer['files'][Path(unit['maps']['path']).name]
        if record['sha256'] != unit['maps']['sha256']:
            raise ValueError('map differs from bound producer receipt')
    return provenance


def validate_axes(axes, shape):
    h, he, z, ze = (np.asarray(axes[name], dtype=float) for name in AXES)
    for centres, edges in ((h, he), (z, ze)):
        if (centres.ndim != 1 or centres.size < 2 or edges.shape != (centres.size + 1,)
                or not np.all(np.isfinite(centres)) or not np.all(np.isfinite(edges))
                or not np.all(np.diff(centres) > 0) or not np.all(np.diff(edges) > 0)
                or not np.all((centres > edges[:-1]) & (centres < edges[1:]))):
            raise ValueError('invalid exact image axes')
    if shape != (z.size, h.size):
        raise ValueError('image/axes shape differs')
    return h, he, z, ze


def observer_masks(image, horizontal, z):
    image = np.asarray(image, dtype=float)
    if image.shape != (z.size, horizontal.size) or not np.all(np.isfinite(image)):
        raise ValueError('invalid observer image')
    return {method: result['mask'] for method, result in
            emission.original_observers(image, horizontal, z).items()}


def predict(config_path, manifest_path, output):
    config = load_config(config_path)
    manifest = read_json(manifest_path)
    units = manifest['units']
    validate_units(config, units)
    if Path(output).exists():
        raise ValueError('refusing to overwrite predictions')
    Path(output).mkdir(parents=True)
    records = []
    for unit in units:
        provenance = bind_provenance(unit)
        path = bind(unit['maps'])
        before = digest(path)
        with np.load(path, allow_pickle=False) as maps:
            axes = {name: maps[name] for name in AXES}
            primary = maps['brightness_current_retained_linear_whole']
            h, _, z, _ = validate_axes(axes, primary.shape)
            masks, labels = {}, []
            for convention in config['correction_policies']:
                image = maps[f'brightness_current_{convention}_whole']
                for mode in MODES:
                    cuts = [0] if mode == 'observer_refit' else config['velocity_cuts_km_s']
                    for cut in cuts:
                        selected_image = image if mode == 'observer_refit' else (
                            image + maps[f'deficit_{convention}_A_v{cut}'])
                        for method, mask in observer_masks(selected_image, h, z).items():
                            key = f'{mode}__{method}__{convention}__v{cut}'
                            masks[key] = mask
                            labels.append({'key': key, 'mode': mode, 'method': method,
                                           'correction': convention, 'velocity_cut_km_s': cut,
                                           'truth_assisted_input': mode != 'observer_refit'})
        if digest(path) != before:
            raise ValueError('maps changed during prediction')
        destination = Path(output) / f'{unit["unit_id"]}.npz'
        np.savez_compressed(destination, **axes, **masks)
        records.append({**{name: unit[name] for name in ('unit_id', 'case', 'snapshot_index', 'view_deg', 'kind')},
                        'input_sha256': before, 'predictions': destination.name,
                        'prediction_sha256': digest(destination), 'labels': labels,
                        'provenance': provenance, 'qualification_holds': unit['qualification_holds']})
    receipt = {'schema': 1, 'status': 'predictions_sealed_before_scoring',
               'config_sha256': digest(config_path), 'input_manifest_sha256': digest(manifest_path),
               'runner_sha256': digest(__file__), 'units': records,
               'scoring_truth_read': False, 'detector_adopted': False}
    write_json(Path(output) / 'prediction_receipt.json', receipt)
    return receipt


def side_score(mask, truth, axes, side, kind, criteria):
    h, he, z, ze = validate_axes(axes, mask.shape)
    if truth.shape != mask.shape or truth.dtype != bool:
        raise ValueError('truth must be a Boolean mask on the prediction grid')
    half = np.broadcast_to((z < 0 if side == 'negative_z' else z > 0)[:, None], mask.shape)
    selected, target = mask & half, truth & half
    area = np.outer(np.diff(ze), np.diff(he))
    found, true, intersection = (float(area[region].sum()) for region in (selected, target, selected & target))
    completeness = intersection / true if true else None
    purity = intersection / found if found else None
    contact = emission.ladder.touches_aperture(selected, h, z)
    if kind == 'initial_null' and true:
        raise ValueError('declared initial null has nonzero tracer truth')
    passed = (found == 0) if kind == 'initial_null' else (
        true > 0 and found > 0 and completeness >= criteria['minimum_completeness']
        and purity >= criteria['minimum_purity'] and not contact)
    _, candidate = emission.ladder._rois(h, z)
    truth_in_aperture = float(area[target & candidate].sum()) / true if true else None
    volume = emission.native.exact_abs_u_moments(selected, he, ze)['symmetrized_revolution_kpc3']
    return {'hemisphere': side, 'recovered_area_kpc2': found, 'truth_area_kpc2': true,
            'intersection_area_kpc2': intersection, 'completeness': completeness,
            'purity': purity, 'nondetection': found == 0, 'aperture_contact': contact,
            'truth_fraction_inside_candidate_aperture': truth_in_aperture,
            'revolution_volume_kpc3': volume, 'generalization_criterion_passed': bool(passed)}


def score(config_path, predictions, truth_manifest_path, output):
    config = load_config(config_path)
    receipt = read_json(Path(predictions) / 'prediction_receipt.json')
    if (receipt['config_sha256'] != digest(config_path) or receipt['runner_sha256'] != digest(__file__)
            or receipt['status'] != 'predictions_sealed_before_scoring' or receipt['scoring_truth_read']):
        raise ValueError('prediction freeze differs')
    validate_units(config, receipt['units'])
    truth_units = read_json(truth_manifest_path)['units']
    validate_units(config, truth_units)
    lookup = {unit['unit_id']: unit for unit in truth_units}
    if set(lookup) != {unit['unit_id'] for unit in receipt['units']}:
        raise ValueError('truth/prediction identifiers differ')
    for unit in receipt['units']:
        validate_labels(config, unit['labels'])
        prediction_path = Path(predictions) / unit['predictions']
        if digest(prediction_path) != unit['prediction_sha256']:
            raise ValueError('prediction changed after sealing')
        with np.load(prediction_path, allow_pickle=False) as masks:
            if set(masks.files) != set(AXES) | {row['key'] for row in unit['labels']}:
                raise ValueError('prediction mask inventory differs from frozen labels')
    if Path(output).exists():
        raise ValueError('refusing to overwrite scores')
    rows = []
    for unit in receipt['units']:
        truth_unit = lookup[unit['unit_id']]
        if unit_key(unit) != unit_key(truth_unit):
            raise ValueError('truth metadata substitution')
        bind_provenance(truth_unit)
        if (unit['qualification_holds'] != truth_unit['qualification_holds']
                or any(unit['provenance'][role]['sha256'] != truth_unit['provenance'][role]['sha256']
                       for role in unit['provenance'])):
            raise ValueError('truth/prediction provenance or qualification holds differ')
        truth_path = bind(truth_unit['truth'])
        prediction_path = Path(predictions) / unit['predictions']
        if digest(prediction_path) != unit['prediction_sha256']:
            raise ValueError('prediction changed after sealing')
        with np.load(truth_path, allow_pickle=False) as truth_file, np.load(prediction_path, allow_pickle=False) as masks:
            axes = {name: masks[name] for name in AXES}
            if any(not np.array_equal(axes[name], truth_file[name]) for name in AXES):
                raise ValueError('truth grid differs from sealed prediction')
            truth = np.asarray(truth_file['path_C_kpc'], dtype=float)
            if not np.all(np.isfinite(truth)) or np.any(truth < 0):
                raise ValueError('invalid tracer path truth')
            truth = truth > 0
            for label in unit['labels']:
                for side in emission.ladder.SIDES:
                    metrics = side_score(masks[label['key']].astype(bool), truth, axes, side, unit['kind'], config['criteria'])
                    primary = (label['correction'] == 'retained_linear'
                               and label['velocity_cut_km_s'] in (0, 100))
                    rows.append({**{name: unit[name] for name in ('unit_id', 'case', 'snapshot_index', 'view_deg', 'kind')},
                                 **label, 'primary': primary,
                                 'qualification_holds': json.dumps(unit['qualification_holds']), **metrics})
        bind(truth_unit['truth'])
    Path(output).mkdir(parents=True)
    with (Path(output) / 'scores.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    groups = []
    for mode in MODES:
        for method in emission.METHODS:
            selected = [row for row in rows if row['primary'] and row['mode'] == mode and row['method'] == method]
            if len(selected) != 2 * len(receipt['units']) or not selected:
                raise ValueError('primary side count differs from complete frozen cohort')
            groups.append({'mode': mode, 'method': method, 'primary_side_count': len(selected),
                           'failed_sides': sum(not row['generalization_criterion_passed'] for row in selected),
                           'all_primary_sides_pass': all(row['generalization_criterion_passed'] for row in selected),
                           'truth_assisted_input': mode != 'observer_refit'})
    report = {'status': 'frozen_diagnostic_evaluated', 'config_sha256': digest(config_path),
              'prediction_receipt_sha256': digest(Path(predictions) / 'prediction_receipt.json'),
              'truth_manifest_sha256': digest(truth_manifest_path), 'groups': groups,
              'scores_sha256': digest(Path(output) / 'scores.csv'), 'detector_adopted': False,
              'limits': 'Passing the truth-assisted arm cannot validate an observer-only detector.'}
    write_json(Path(output) / 'evaluation_receipt.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    predict_parser = sub.add_parser('predict')
    predict_parser.add_argument('--config', type=Path, required=True)
    predict_parser.add_argument('--manifest', type=Path, required=True)
    predict_parser.add_argument('--output-dir', type=Path, required=True)
    score_parser = sub.add_parser('score')
    score_parser.add_argument('--config', type=Path, required=True)
    score_parser.add_argument('--predictions', type=Path, required=True)
    score_parser.add_argument('--truth-manifest', type=Path, required=True)
    score_parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = (predict(args.config, args.manifest, args.output_dir) if args.command == 'predict'
              else score(args.config, args.predictions, args.truth_manifest, args.output_dir))
    print(json.dumps({'status': result['status'], 'detector_adopted': False}))


if __name__ == '__main__':
    main()
