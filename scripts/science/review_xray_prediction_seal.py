"""Independent custody review of the sealed 54-view X-ray predictions.

chain  -- hash every archive member, bind the public seal, cohort, frozen
          sources and native inputs, and confirm the inputs carry no target.
replay -- rerun the frozen detector on the archived inputs and compare every
          sealed mask. The acceptance rule is fixed here before the first run:
          a mask is reproduced only if every pixel is equal. Differences are
          reported as counts of unequal pixels. Selected areas, images and
          scores are never computed or written.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'docs/science/assets/xray_prediction_seal_2026-11-23'
OUT = ROOT / 'docs/science/assets/xray_prediction_seal_review_2026-11-24'
CONFIG = 'configs/background_refit_blind_2026-11-11.json'
RUNNER = 'scripts/science/run_background_refit_blind.py'
FREEZE, ADAPTER, REGISTER = 'c352554', 'f1218f1', '1bc015c'
AXES = ('horizontal_axis_kpc', 'horizontal_edges_kpc', 'z_axis_kpc', 'z_edges_kpc')
CLASSES = {'contracts': 22, 'map_inputs': 66, 'native_receipts': 22, 'predictions': 66,
           'preflight_contracts': 4, 'prior_completions': 22, 'producer_receipts': 22}


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def git_sha(commit, path):
    blob = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'],
                          check=True, capture_output=True).stdout
    return hashlib.sha256(blob).hexdigest()


def local_imports(path):
    tree = ast.parse((ROOT / path).read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split('.')[0])
    return {f'scripts/science/{name}.py' for name in names
            if (ROOT / 'scripts/science' / f'{name}.py').is_file()}


def import_closure(path):
    seen, pending = set(), [path]
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(local_imports(current))
    return seen


def staged_meta(extract):
    staging = json.loads((extract / 'staging.json').read_text())
    return staging['frozen_protocol_commit'], staging['map_adapter_commit']


def expected_units(config):
    return {(case, index, angle, 'science') for case, indices in config['heldout_indices'].items()
            for index in indices for angle in config['azimuths_deg']} | {
                (case, 0, angle, 'initial_null') for case in config['null_cases']
                for angle in config['azimuths_deg']}


def expected_labels(config):
    keys = []
    for convention in config['correction_policies']:
        for mode in ('observer_refit', 'ambient_replaced_refit'):
            for cut in ([0] if mode == 'observer_refit' else config['velocity_cuts_km_s']):
                keys += [f'{mode}__{method}__{convention}__v{cut}' for method in config['methods']]
    return keys


def chain(tar, extract):
    checks, notes = {}, {}
    public = {name: json.loads((PUBLIC / name).read_text()) for name in
              ('seal.json', 'archive_verification.json', 'prediction_audit.json',
               'live_custody_witness.json', 'preparation.json')}
    receipt = json.loads((tar.parent / 'archive_receipt.json').read_text())
    config = json.loads((ROOT / CONFIG).read_text())
    seal = public['seal.json']

    checks['archive_bytes_and_sha256_match_public_record'] = (
        tar.stat().st_size == public['archive_verification.json']['archive_bytes']
        and sha(tar) == public['archive_verification.json']['archive_sha256'] == receipt['archive_sha256'])
    files = sorted(str(path.relative_to(extract)) for path in extract.rglob('*') if path.is_file())
    checks['all_232_members_rehash_to_creator_inventory'] = (
        files == sorted(receipt['members']) and len(files) == 232
        and all(sha(extract / name) == receipt['members'][name]['sha256'] for name in files))
    counts = {name: sum(member.startswith(name + '/') for member in files) for name in CLASSES}
    checks['member_classes'] = counts == CLASSES
    checks['no_scoring_member_names'] = not any(
        word in name.lower() for name in files for word in ('truth', 'scoring', 'path_c'))

    seal_hash = sha(extract / 'seal.json')
    checks['seal_matches_public_copy_and_announced_hash'] = (
        seal_hash == sha(PUBLIC / 'seal.json') == public['prediction_audit.json']['seal_sha256']
        == public['archive_verification.json']['seal_sha256'] == receipt['seal_sha256'])
    notes['seal_sha256'] = seal_hash
    checks['prediction_receipt_bound'] = (
        sha(extract / 'prediction_receipt.json') == seal['prediction_receipt_sha256']
        == public['prediction_audit.json']['prediction_receipt_sha256'])
    checks['maps_manifest_and_assembly_bound'] = (
        sha(extract / 'maps_manifest.json') == seal['maps_manifest_sha256']
        == public['live_custody_witness.json']['maps_manifest_sha256']
        and sha(extract / 'assembly_receipt.json') == seal['assembly_receipt_sha256']
        == public['live_custody_witness.json']['assembly_receipt_sha256'])
    assembly = json.loads((extract / 'assembly_receipt.json').read_text())
    commitment = assembly['files']['scoring_truth_manifest.json']['sha256']
    checks['scoring_manifest_commitment_consistent'] = (
        commitment == seal['scoring_manifest_commitment_sha256']
        == public['live_custody_witness.json']['opaque_scoring_manifest_commitment_sha256'])
    notes['scoring_manifest_commitment_sha256'] = commitment

    units = seal['units']
    checks['cohort_is_exactly_the_frozen_66_views'] = (
        len(units) == 66 and {(u['case'], u['snapshot_index'], u['view_deg'], u['kind']) for u in units}
        == expected_units(config) and not any(u['case'] == 'G-HI' and u['snapshot_index'] == 20 for u in units))
    labels = expected_labels(config)
    checks['sixteen_frozen_labels'] = [row['key'] for row in seal['label_definitions']] == labels and len(labels) == 16
    checks['every_sealed_prediction_and_input_hash_matches_archive'] = all(
        sha(extract / 'predictions' / u['file']) == u['prediction_sha256']
        and sha(extract / 'map_inputs' / u['file']) == u['maps_sha256'] for u in units)
    predicted = json.loads((extract / 'prediction_receipt.json').read_text())
    by_id = {u['unit_id']: u for u in predicted['units']}
    checks['prediction_receipt_units_agree_with_seal'] = (
        predicted['runner_sha256'] == seal['frozen_runner_sha256'] == config['runner_sha256']
        and predicted['config_sha256'] == seal['protocol_config_sha256']
        and all(by_id[u['unit_id']]['prediction_sha256'] == u['prediction_sha256']
                and by_id[u['unit_id']]['input_sha256'] == u['maps_sha256'] for u in units))

    map_keys = set(AXES) | {f'brightness_current_{c}_whole' for c in config['correction_policies']} | {
        f'deficit_{c}_A_v{v}' for c in config['correction_policies'] for v in config['velocity_cuts_km_s']}
    seen_map, seen_prediction = set(), set()
    for u in units:
        with zipfile.ZipFile(extract / 'map_inputs' / u['file']) as archive:
            seen_map.add(frozenset(name.removesuffix('.npy') for name in archive.namelist()))
        with zipfile.ZipFile(extract / 'predictions' / u['file']) as archive:
            seen_prediction.add(frozenset(name.removesuffix('.npy') for name in archive.namelist()))
    checks['detector_inputs_hold_only_axes_brightness_and_declared_components'] = seen_map == {frozenset(map_keys)}
    checks['predictions_hold_only_axes_and_sixteen_masks'] = seen_prediction == {frozenset(set(AXES) | set(labels))}

    frozen = {RUNNER: config['runner_sha256'], **config['source_sha256']}
    checks['frozen_sources_identical_at_freeze_commit_and_now'] = all(
        git_sha(FREEZE, path) == expected == sha(ROOT / path) for path, expected in frozen.items())
    config_hash = sha(ROOT / CONFIG)
    checks['config_identical_at_freeze_commit_archive_and_now'] = (
        git_sha(FREEZE, CONFIG) == config_hash == sha(extract / 'config.json')
        == seal['protocol_config_sha256'] == public['preparation.json']['frozen_config_sha256'])
    staged = json.loads((extract / 'staging.json').read_text())['sources']
    closure = import_closure(RUNNER)
    checks['all_modules_the_detector_can_import_identical_at_freeze_in_stage_and_now'] = all(
        git_sha(FREEZE, path) == staged.get(path) == sha(ROOT / path) for path in closure)
    notes['detector_import_closure'] = len(closure)
    notes['imported_modules_outside_the_protocol_hash_list'] = sorted(closure - set(frozen))
    adapter = {'scripts/science/prepare_blind_emission_maps.py': seal['producer_source_sha256'],
               'scripts/science/assemble_blind_emission_cohort.py': seal['assembler_sha256']}
    checks['map_producer_and_assembler_identical_at_adapter_commit_in_stage_and_seal'] = all(
        git_sha(ADAPTER, path) == staged[path] == expected for path, expected in adapter.items())
    wrapper = 'scripts/kunanyi/seal_blind_emission_predictions.py'
    checks['custody_wrapper_identical_at_register_commit_and_in_stage'] = (
        git_sha(REGISTER, wrapper) == staged[wrapper] == public['preparation.json']['custody_wrapper_sha256'])
    checks['stage_records_freeze_and_adapter_commits'] = (
        staged_meta(extract) == (FREEZE, ADAPTER))

    register = PUBLIC / 'native_inputs.csv'
    register_hash = sha(register)
    checks['native_register_unchanged_since_pre_production_commit'] = (
        git_sha(REGISTER, str(register.relative_to(ROOT))) == register_hash
        == public['prediction_audit.json']['precommitted_native_inputs_sha256']
        == public['preparation.json']['native_input_csv_sha256'])
    rows = list(csv.DictReader(register.open()))
    slots = {(row['case'], row['snapshot_index']): row for row in json.loads((extract / 'slots.json').read_text())}
    native_ok, truth_bound = len(rows) == 22, 0
    initial = {row['case']: row['current_h5_sha256'] for row in rows if row['snapshot_index'] == '0'}
    for row in rows:
        tag = f'{row["case"]}_{int(row["snapshot_index"]):04d}'
        native = json.loads((extract / 'native_receipts' / f'{tag}.json').read_text())
        producer = json.loads((extract / 'producer_receipts' / f'{tag}.json').read_text())
        inputs = native['inputs']
        native_ok &= (
            sha(extract / 'contracts' / f'{tag}.json') == row['producer_contract_sha256']
            and sha(extract / 'native_receipts' / f'{tag}.json') == row['native_input_receipt_sha256']
            and sha(extract / 'preflight_contracts' / f'{row["case"]}.json') == row['native_preflight_contract_sha256']
            and sha(extract / 'prior_completions' / f'{tag}.json') == row['previous_native_completion_sha256']
            and inputs['current_h5']['sha256'] == row['current_h5_sha256']
            and inputs['initial_h5']['sha256'] == row['initial_h5_sha256'] == initial[row['case']]
            and inputs['environment']['sha256'] == row['atmosphere_sha256']
            and inputs['grid_file']['sha256'] == row['grid_file_sha256']
            and native['case'] == producer['case'] == row['case']
            and native['snapshot_index'] == producer['snapshot_index'] == int(row['snapshot_index'])
            and producer['provenance']['native_input_receipt']['sha256'] == row['native_input_receipt_sha256']
            and producer['kind'] == row['kind']
            and abs(producer['actual_time_myr'] - float(row['actual_age_myr'])) < 1e-9)
        producer_hash = sha(extract / 'producer_receipts' / f'{tag}.json')
        for u in (u for u in units if (u['case'], u['snapshot_index']) == (row['case'], int(row['snapshot_index']))):
            native_ok &= (u['source_receipt_sha256'] == row['native_input_receipt_sha256']
                          and u['producer_receipt_sha256'] == producer_hash
                          and producer['files'][u['file']]['sha256'] == u['maps_sha256'])
            truth_bound += u['file'].replace('.npz', '.truth.npz') in producer['files']
        native_ok &= slots[(row['case'], int(row['snapshot_index']))]['contract']['sha256'] == row['producer_contract_sha256']
    checks['all_22_native_bindings_agree_from_register_to_sealed_unit'] = bool(native_ok)
    checks['producer_receipts_commit_all_66_scoring_raster_hashes'] = truth_bound == 66
    notes['distinct_native_snapshot_hashes'] = len({row['current_h5_sha256'] for row in rows})

    result = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks, 'notes': notes}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'chain.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def replay(extract, source, start, stop):
    import numpy as np
    sys.path.insert(0, str(source / 'scripts/science'))
    spec = importlib.util.spec_from_file_location('frozen_blind', source / RUNNER)
    blind = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(blind)
    config = blind.load_config(source / CONFIG)
    local = [module for module in sys.modules.values()
             if (ROOT / 'scripts/science' / f'{module.__name__}.py').is_file()]
    if not local or any(source.resolve() not in Path(module.__file__).resolve().parents for module in local):
        raise ValueError('a detector module was not loaded from the freeze checkout')
    seal = json.loads((PUBLIC / 'seal.json').read_text())
    rows = []
    for unit in seal['units'][start:stop]:
        with np.load(extract / 'map_inputs' / unit['file'], allow_pickle=False) as maps, \
                np.load(extract / 'predictions' / unit['file'], allow_pickle=False) as sealed:
            axes = {name: maps[name] for name in AXES}
            h, _, z, _ = blind.validate_axes(axes, maps['brightness_current_retained_linear_whole'].shape)
            axes_equal = all(np.array_equal(axes[name], sealed[name]) for name in AXES)
            for convention in config['correction_policies']:
                image = maps[f'brightness_current_{convention}_whole']
                for mode in blind.MODES:
                    for cut in ([0] if mode == 'observer_refit' else config['velocity_cuts_km_s']):
                        selected = image if mode == 'observer_refit' else image + maps[f'deficit_{convention}_A_v{cut}']
                        for method, mask in blind.observer_masks(selected, h, z).items():
                            key = f'{mode}__{method}__{convention}__v{cut}'
                            stored = sealed[key]
                            same_layout = stored.shape == mask.shape and stored.dtype == mask.dtype
                            rows.append({'unit_id': unit['unit_id'], 'label': key, 'axes_equal': axes_equal,
                                         'same_shape_and_dtype': same_layout, 'pixels': int(mask.size),
                                         'unequal_pixels': int(np.count_nonzero(stored != mask)) if same_layout else -1})
        print(unit['unit_id'], sum(row['unequal_pixels'] != 0 for row in rows[-16:]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / ('replay.csv' if (start, stop) == (0, 66) else f'replay_{start:02d}_{stop:02d}.csv')
    with destination.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    import scipy
    summary = {'acceptance_rule': 'every pixel equal; fixed in the script before the first run',
               'units': len({row['unit_id'] for row in rows}), 'masks': len(rows),
               'masks_reproduced_exactly': sum(row['unequal_pixels'] == 0 and row['axes_equal'] for row in rows),
               'pixels_compared': sum(row['pixels'] for row in rows),
               'unequal_pixels': sum(max(row['unequal_pixels'], 0) for row in rows),
               'source': f'git archive of {FREEZE}', 'python': sys.version.split()[0],
               'numpy': np.__version__, 'scipy': scipy.__version__,
               'selected_areas_or_scores_computed': False}
    if (start, stop) == (0, 66):
        (OUT / 'replay_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    one = sub.add_parser('chain')
    one.add_argument('--tar', type=Path, required=True)
    one.add_argument('--extract', type=Path, required=True)
    two = sub.add_parser('replay')
    two.add_argument('--extract', type=Path, required=True)
    two.add_argument('--source', type=Path, required=True, help='checkout of the freeze commit')
    two.add_argument('--start', type=int, default=0)
    two.add_argument('--stop', type=int, default=66)
    args = parser.parse_args()
    if args.command == 'chain':
        sys.exit(0 if chain(args.tar, args.extract)['status'] == 'passed' else 1)
    replay(args.extract, args.source, args.start, args.stop)
