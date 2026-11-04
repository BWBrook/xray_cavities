#!/usr/bin/env python3
"""Run one independently qualified native case with serial bounded-memory I/O."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from prepare_spherical_budget_inputs import budget, stable_hash, validate_contract, prepare_receipt, validate_existing_receipt


def run_case(contract_path: Path, contract_sha256: str, output_dir: Path,
             indices: list[int] | None = None, safe_buffer_kpc: float = 40.) -> dict:
    contract, preflight = validate_contract(contract_path, contract_sha256)
    available = [row['index'] for row in preflight['chain']]
    selected = available if indices is None else indices
    if not selected or len(selected) != len(set(selected)) or not set(selected).issubset(available):
        raise ValueError('requested indices must be unique members of the accepted chain')
    output_dir.mkdir(parents=True, exist_ok=True)
    if (output_dir/'completion.json').exists():
        raise ValueError('case request already completed; refusing duplicate execution')
    lock = output_dir/'run.lock'
    lock.mkdir()
    cache = {}
    products = []
    extractor_identity = stable_hash(Path(budget.__file__))
    science = Path(budget.__file__).parent
    source_paths = [Path(__file__), Path(__file__).with_name('prepare_spherical_budget_inputs.py')]
    source_paths += [science/name for name in ('extract_spherical_energy_budget.py',
        'measure_q031_fluxes.py', 'pluto_h5_level3_ambient_extract.py',
        'select_common_age_hdf5.py', 'snapshot_energy.py')]
    analysis_sources = {path.name: stable_hash(path) for path in source_paths}
    source_hashes = {name: record['sha256'] for name, record in analysis_sources.items()}
    try:
        preflight_path = output_dir/'native_preflight.json'
        if preflight_path.exists():
            old = json.loads(preflight_path.read_text())
            if old != preflight:
                raise ValueError('existing preflight differs; use a new output directory')
        else:
            budget._atomic_publish(preflight_path, preflight)
        for index in selected:
            print(f'SNAPSHOT_START {preflight["case"]} {index}', flush=True)
            name = f'snapshot_{index:04d}'
            result_path = output_dir/f'{name}.json'
            receipt_path = output_dir/'inputs'/f'{name}.json'
            done_path = output_dir/f'{name}.complete.json'
            if done_path.exists():
                done = json.loads(done_path.read_text())
                if (done.get('contract_sha256') != contract_sha256 or done.get('snapshot_index') != index
                    or done.get('case') != preflight['case'] or done.get('safe_buffer_kpc') != safe_buffer_kpc
                    or done.get('extractor_sha256') != extractor_identity['sha256']
                    or done.get('analysis_source_sha256') != source_hashes):
                    raise ValueError(f'completed snapshot has a different analysis identity: {index}')
                for key, path in [('output', result_path), ('input_receipt', receipt_path)]:
                    if stable_hash(path)['sha256'] != done[key]['sha256']:
                        raise ValueError(f'completed product changed: {path}')
                old_receipt = json.loads(receipt_path.read_text())
                validate_existing_receipt(preflight, index, old_receipt)
                products.append(done)
                print(f'SNAPSHOT_REUSED {preflight["case"]} {index}', flush=True)
                continue
            if result_path.exists():
                raise ValueError(f'unreceipted existing result requires review: {result_path}')
            if receipt_path.exists():
                receipt = json.loads(receipt_path.read_text())
                validate_existing_receipt(preflight, index, receipt)
                cache.update({value['path']: value for value in receipt['inputs'].values()})
            else:
                receipt = prepare_receipt(preflight, index, receipt_path, cache)
            inputs = receipt['inputs']
            print(f'SNAPSHOT_INPUTS_BOUND {preflight["case"]} {index}', flush=True)
            budget.extract_snapshot(case=preflight['case'], snapshot_index=index,
                current_h5=Path(inputs['current_h5']['path']), initial_h5=Path(inputs['initial_h5']['path']),
                environment_path=Path(inputs['environment']['path']), input_receipt=receipt_path,
                grid_file=Path(inputs['grid_file']['path']) if 'grid_file' in inputs else None,
                safe_buffer_kpc=safe_buffer_kpc, output=result_path)
            budget._stable([*analysis_sources.values(), preflight['contract'],
                            *preflight['files'].values(), *preflight['source_files'].values(),
                            *preflight['historical_evidence'].values()])
            done = {'schema_version': 1, 'status': 'snapshot_measurement_completed',
                    'case': preflight['case'], 'snapshot_index': index,
                    'contract_sha256': contract_sha256, 'safe_buffer_kpc': safe_buffer_kpc,
                    'extractor_sha256': extractor_identity['sha256'],
                    'analysis_source_sha256': source_hashes,
                    'output': stable_hash(result_path), 'input_receipt': stable_hash(receipt_path)}
            budget._atomic_publish(done_path, done)
            products.append(done)
            print(f'SNAPSHOT_COMPLETED {preflight["case"]} {index}', flush=True)
        completion = {'schema_version': 1, 'status': 'requested_native_measurements_completed',
                      'case': preflight['case'], 'contract_sha256': contract_sha256,
                      'scientifically_retained_indices': available, 'requested_indices': selected,
                      'completed_indices': [row['snapshot_index'] for row in products], 'products': products,
                      'scientific_qualification': preflight['scientific_qualification']}
        budget._atomic_publish(output_dir/'completion.json', completion)
        return completion
    finally:
        lock.rmdir()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--indices', help='Comma-separated indices; omit for the entire retained chain')
    parser.add_argument('--safe-buffer-kpc', type=float, default=40.)
    args = parser.parse_args()
    indices = [int(value) for value in args.indices.split(',')] if args.indices else None
    run_case(args.contract, args.contract_sha256, args.output_dir, indices, args.safe_buffer_kpc)


if __name__ == '__main__':
    main()
