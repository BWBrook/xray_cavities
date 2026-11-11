"""Bind the complete sealed refit cohort into separate prediction/truth manifests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import prepare_blind_emission_maps as producer
import run_background_refit_blind as blind


def checked_record(record):
    path = Path(record['path'])
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise ValueError('bound files must have absolute regular nonsymlink paths')
    pin = record.get('sha256')
    before = producer.BUDGET._stat_identity(path)
    if (not isinstance(pin, str) or not producer.BUDGET.SHA256_PATTERN.fullmatch(pin)
            or blind.digest(path) != pin or producer.BUDGET._stat_identity(path) != before):
        raise ValueError('bound file hash differs or file changed while hashing')
    return {**before, 'sha256': pin}


def safe_name(name):
    if not isinstance(name, str) or not name or Path(name).name != name or name in ('.', '..'):
        raise ValueError('unsafe producer payload filename')
    return name


def payload(root, name, record, expected_arrays):
    path = root / safe_name(name)
    if path.resolve().parent != root.resolve():
        raise ValueError('producer payload escapes its directory')
    identity = checked_record({'path': str(path), 'sha256': record['sha256']})
    if identity['size_bytes'] != record['size_bytes']:
        raise ValueError('producer payload size differs')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if (len(names) != len(set(names)) or set(names) != {f'{field}.npy' for field in expected_arrays}):
        raise ValueError('detector/truth NPZ array inventory differs')
    producer.BUDGET._stable([identity])
    return identity


def bind_producer_metadata(record, native, config, config_sha256):
    case, index = record.get('case'), record.get('snapshot_index')
    if (record.get('schema_version') != 1 or type(index) is not int
            or record.get('execution_status') != 'sealed_native_emission_maps_prepared_no_observer_scoring'
            or record.get('native_filling_measured') is not False
            or record.get('observer_statistics_computed') is not False
            or record.get('placeholder_filling_rows_discarded') is not True):
        raise ValueError('producer is not an unscored sealed-map receipt')
    if (native.get('schema_version') != 1 or native.get('status') != 'bound_spherical_budget_inputs'
            or native.get('case') != case or native.get('snapshot_index') != index):
        raise ValueError('native receipt case/index differs from producer')
    if (record.get('frequency_hz') != producer.FREQUENCY_HZ or record.get('redshift') != producer.REDSHIFT
            or record.get('sky_axis_policy') != producer.AXIS_POLICY):
        raise ValueError('producer emission settings differ from frozen development')
    provenance = record['provenance']
    if provenance['protocol_config']['sha256'] != config_sha256:
        raise ValueError('producer was not run with this frozen config')
    sources = provenance['analysis_sources']
    expected_sources = {Path(path).name: pin for path, pin in config['source_sha256'].items()}
    expected_sources['run_background_refit_blind.py'] = config['runner_sha256']
    expected_sources['prepare_blind_emission_maps.py'] = blind.digest(producer.__file__)
    if any(sources.get(name, {}).get('sha256') != pin for name, pin in expected_sources.items()):
        raise ValueError('producer scientific source differs from frozen source')
    if (set(provenance['runtime']) != set(producer.RUNTIME_HASHES)
            or any(provenance['runtime'][name]['sha256'] != pin for name, pin in producer.RUNTIME_HASHES.items())):
        raise ValueError('producer runtime differs from development')
    qualification = record['scientific_qualification']
    holds = qualification.get('holds')
    if (qualification.get('qualified') is not False or not isinstance(holds, list)
            or any(not isinstance(hold, str) or not hold for hold in holds)
            or len(holds) != len(set(holds))
            or not set(native['native_preflight']['scientific_qualification']['holds']) <= set(holds)):
        raise ValueError('producer qualification holds are invalid or omit native holds')


def assemble(config_path, config_sha256, inventory_path, output):
    if Path(output).exists():
        raise ValueError('refusing to overwrite cohort manifests')
    config_identity = checked_record({'path': str(Path(config_path).absolute()), 'sha256': config_sha256})
    config = blind.load_config(config_path)
    inventory_identity = checked_record({'path': str(Path(inventory_path).absolute()),
                                         'sha256': blind.digest(inventory_path)})
    inventory = blind.read_json(inventory_path)
    if inventory.get('schema') != 1:
        raise ValueError('invalid producer inventory schema')
    expected = blind.expected_units(config)
    expected_producers = {(case, index, kind) for case, index, _, kind in expected}
    seen_producers, seen_payloads = set(), set()
    identities = [config_identity, inventory_identity]
    map_units, truth_units = [], []
    for entry in inventory['producers']:
        receipt_identity = checked_record(entry['producer_receipt'])
        native_identity = checked_record(entry['native_input_receipt'])
        identities.extend((receipt_identity, native_identity))
        record = blind.read_json(receipt_identity['path'])
        native = blind.read_json(native_identity['path'])
        bind_producer_metadata(record, native, config, config_sha256)
        if record['provenance']['native_input_receipt']['sha256'] != native_identity['sha256']:
            raise ValueError('native receipt hash differs from producer chain')
        source_key = (record['case'], record['snapshot_index'], record.get('kind'))
        if source_key not in expected_producers or source_key in seen_producers:
            raise ValueError('unexpected or duplicate producer case/index')
        seen_producers.add(source_key)
        units = record['units']
        if (len(units) != len(config['azimuths_deg'])
                or {unit.get('view_deg') for unit in units} != set(config['azimuths_deg'])):
            raise ValueError('producer must bind exactly the three frozen azimuths')
        names = []
        root = Path(receipt_identity['path']).parent
        for unit in units:
            if (unit.get('case'), unit.get('snapshot_index'), unit.get('kind')) != source_key:
                raise ValueError('unit metadata substitutes another producer case/index')
            key = blind.unit_key(unit)
            if key not in expected or type(unit['view_deg']) is not int:
                raise ValueError('unit is outside frozen cohort')
            identifier = safe_name(unit['unit_id'])
            map_name, truth_name = safe_name(unit['maps_filename']), safe_name(unit['truth_filename'])
            if (identifier != f'{unit["case"]}_{unit["snapshot_index"]:04d}_{unit["view_deg"]}deg'
                    or map_name != identifier + '.npz' or truth_name != identifier + '.truth.npz'):
                raise ValueError('unit filename/case/index association differs')
            for name in (map_name, truth_name):
                if (root / name).resolve() in seen_payloads:
                    raise ValueError('payload reused across units')
                seen_payloads.add((root / name).resolve())
                names.append(name)
            maps = payload(root, map_name, record['files'][map_name], producer.DETECTOR_FIELDS)
            truth = payload(root, truth_name, record['files'][truth_name], (*blind.AXES, 'path_C_kpc'))
            identities.extend((maps, truth))
            provenance = {'native_input_receipt': {name: native_identity[name] for name in ('path', 'sha256')},
                          'producer_receipt': {name: receipt_identity[name] for name in ('path', 'sha256')}}
            common = {name: unit[name] for name in ('unit_id', 'case', 'snapshot_index', 'view_deg', 'kind')}
            common.update({'provenance': provenance, 'qualification_holds': record['scientific_qualification']['holds']})
            map_units.append({**common, 'maps': {name: maps[name] for name in ('path', 'sha256')}})
            truth_units.append({**common, 'truth': {name: truth[name] for name in ('path', 'sha256')}})
        if set(record['files']) != set(names):
            raise ValueError('producer payload inventory differs from declared units')
    if seen_producers != expected_producers:
        raise ValueError('producer inventory omits frozen cohort cases/ages/nulls')
    blind.validate_units(config, map_units)
    blind.validate_units(config, truth_units)
    producer.BUDGET._stable(identities)
    Path(output).mkdir(parents=True)
    map_path, truth_path = Path(output) / 'maps_manifest.json', Path(output) / 'scoring_truth_manifest.json'
    config_record = {name: config_identity[name] for name in ('path', 'sha256')}
    blind.write_json(map_path, {'schema': 1, 'protocol_config': config_record, 'units': map_units})
    blind.write_json(truth_path, {'schema': 1, 'protocol_config': config_record, 'units': truth_units})
    result = {'schema': 1, 'status': 'complete_cohort_hash_bound_scoring_truth_sealed',
              'config_sha256': config_sha256, 'inventory_sha256': inventory_identity['sha256'],
              'assembler_sha256': blind.digest(__file__), 'producer_source_sha256': blind.digest(producer.__file__),
              'producer_count': len(seen_producers), 'map_units': len(map_units), 'truth_units': len(truth_units),
              'payload_count': len(seen_payloads), 'truth_arrays_read': False, 'scores_read_or_computed': False,
              'scoring_truth_released': False,
              'release_condition': 'Record and independently verify sealed prediction receipt and payload hashes before releasing scoring_truth_manifest.json.',
              'files': {path.name: {'sha256': blind.digest(path), 'size_bytes': path.stat().st_size}
                        for path in (map_path, truth_path)}}
    producer.BUDGET._stable(identities)
    blind.write_json(Path(output) / 'assembly_receipt.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.config, args.config_sha256, args.inventory, args.output_dir)
    print(json.dumps({name: result[name] for name in ('status', 'producer_count', 'map_units', 'truth_units', 'scoring_truth_released')}))


if __name__ == '__main__':
    main()
