"""Run reviewed existing-output accounting against pinned prior native receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import prepare_spherical_budget_inputs as inputs
import extract_fixed_box_energy_budget as fixed
import measure_q031_fluxes as flux


def read_bound(record):
    path = Path(record['path'])
    identity = inputs.checked_file(record)
    data = json.loads(path.read_text())
    inputs.budget._stable([identity])
    return data, identity


def validate_request(path, expected_sha):
    request, identity = read_bound({'path': str(Path(path).absolute()), 'sha256': expected_sha})
    case = request.get('case')
    selected = request.get('snapshots', [])
    indices = [row['index'] for row in selected]
    if (request.get('schema') != 1 or case not in inputs.budget.CASES or not indices
            or indices != sorted(set(indices)) or min(indices) < 0
            or max(indices) > (47 if case == 'G-HI' else 50)):
        raise ValueError('invalid request schema/case/retained index envelope')
    preflights, bindings = {}, []
    for row in selected:
        contract = row['contract']
        key = (contract['path'], contract['sha256'])
        if key not in preflights:
            preflights[key] = inputs.validate_contract(Path(key[0]), key[1])
        specification, preflight = preflights[key]
        if preflight['case'] != case:
            raise ValueError('request case differs from native contract')
        receipt, receipt_identity = read_bound(row['input_receipt'])
        done, done_identity = read_bound(row['previous_completion'])
        previous_input = done.get('input_receipt', {})
        if (done.get('schema_version') != 1
                or done.get('status') != 'snapshot_measurement_completed'
                or done.get('case') != case or done.get('snapshot_index') != row['index']
                or done.get('contract_sha256') != key[1]
                or any(previous_input.get(field) != receipt_identity[field]
                       for field in ('path', 'size_bytes', 'sha256'))):
            raise ValueError('prior completion does not bind requested input receipt')
        inputs.validate_existing_receipt(preflight, row['index'], receipt)
        bindings.append((row, specification, preflight, receipt, receipt_identity, done_identity))
    return request, identity, bindings


def run(request_path, expected_sha, mode, output_dir):
    if output_dir.exists():
        raise ValueError('refusing to overwrite accounting request output')
    request, request_identity, bindings = validate_request(request_path, expected_sha)
    output_dir.mkdir(parents=True)
    sources = [Path(__file__), Path(inputs.__file__)]
    sources += [Path(fixed.__file__).parent/name for name in fixed.SOURCE_FILES]
    if mode == 'flux':
        sources.append(Path(fixed.__file__).parent/'summarize_q031_source_accounting.py')
    source_identities = [inputs.stable_hash(path) for path in sources]
    inputs.budget._atomic_publish(output_dir/'request_binding.json', {
        'request': request, 'request_identity': request_identity,
        'source_files': source_identities,
        'preflights': {str(row['index']): preflight for row, _, preflight, *_ in bindings},
        'mode': mode, 'native_payloads_rehashed': False,
        'holds': ['snapshot reconstruction is not solver-step flux/source instrumentation',
                  'coarse controls do not certify production boundary quietness']})
    products = []
    if mode == 'fixed':
        for row, _, _, receipt, *_ in bindings:
            native = receipt['inputs']
            target = output_dir/f"snapshot_{row['index']:04d}.json"
            print('FIXED_SNAPSHOT_START', request['case'], row['index'], flush=True)
            fixed.extract_snapshot(case=request['case'], snapshot_index=row['index'],
                current_h5=Path(native['current_h5']['path']),
                initial_h5=Path(native['initial_h5']['path']),
                environment_path=Path(native['environment']['path']),
                grid_file=Path(native['grid_file']['path']) if 'grid_file' in native else None,
                input_receipt=Path(row['input_receipt']['path']),
                inset_kpc=50., potential_zero_shift_cm2_s2=1.e15, output=target)
            products.append(inputs.stable_hash(target))
            print('FIXED_SNAPSHOT_COMPLETED', request['case'], row['index'], flush=True)
    elif mode == 'flux':
        if bindings[0][0]['index'] != 0 or len(bindings) < 2:
            raise ValueError('flux series requires initial snapshot and at least one later age')
        native_dir = output_dir/'bound_snapshots'
        native_dir.mkdir()
        for row, _, _, receipt, *_ in bindings:
            path = Path(receipt['inputs']['current_h5']['path'])
            (native_dir/path.name).symlink_to(path)
        contract = bindings[0][1]
        files = contract['files']
        flux.run_analysis(case=request['case'], outputs_dirs=[native_dir],
            environment_path=Path(files['environment']['path']),
            pluto_ini=Path(files['runtime_config']['path']),
            problem_source_dir=Path(contract['source_root']),
            grid_file=Path(files['grid_file']['path']) if 'grid_file' in files else None,
            output_dir=output_dir/'flux')
        sys.path.insert(0, str(Path(fixed.__file__).parent))
        import summarize_q031_source_accounting as source_accounting
        source_accounting.run(output_dir/'flux', output_dir/'source_accounting')
        products = [inputs.stable_hash(path) for path in sorted(output_dir.rglob('*'))
                    if path.is_file() and path.suffix in ('.csv', '.json')]
    else:
        raise ValueError('mode must be fixed or flux')
    for row, _, preflight, receipt, receipt_identity, done_identity in bindings:
        inputs.validate_existing_receipt(preflight, row['index'], receipt)
        inputs.budget._stable([receipt_identity, done_identity])
    inputs.budget._stable([request_identity, *source_identities])
    result = {'schema': 1, 'execution_status': 'completed_review_accounting_request',
              'case': request['case'], 'mode': mode,
              'indices': [row['index'] for row, *_ in bindings],
              'request_sha256': expected_sha, 'products': products,
              'scientifically_qualified': False}
    inputs.budget._atomic_publish(output_dir/'completion.json', result)
    print('REVIEW_ACCOUNTING_COMPLETED', request['case'], mode, flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--mode', choices=('fixed', 'flux'), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    run(args.request, args.request_sha256, args.mode, args.output_dir)


if __name__ == '__main__':
    main()
