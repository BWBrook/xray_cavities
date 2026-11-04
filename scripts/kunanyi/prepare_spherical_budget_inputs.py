#!/usr/bin/env python3
"""Validate a reviewed native-case contract and bind exact spherical inputs.

The contract is a reviewed input, never generated from live filenames by this
program. Historical hash witnesses establish config/atmosphere identity;
current source and binary hashes establish stability, not historical linkage.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

SCIENCE = Path(__file__).resolve().parents[1] / 'science'
sys.path.insert(0, str(SCIENCE))
import extract_spherical_energy_budget as budget
from measure_q031_fluxes import parse_pluto_parameters
from select_common_age_hdf5 import inspect_file

REQUIRED_FILES = {'runtime_config', 'environment_config', 'environment',
                  'compiled_config', 'initialization_source', 'binary'}
HISTORICAL_ROLES = {'runtime_config', 'environment_config', 'environment'}


def stable_hash(path: Path) -> dict:
    before = budget._stat_identity(path)
    digest = budget._sha256(path)
    if budget._stat_identity(path) != before:
        raise ValueError(f'file changed while hashing: {path}')
    return {**before, 'sha256': digest}


def checked_file(record: dict) -> dict:
    path = Path(record['path'])
    if not path.is_absolute():
        raise ValueError(f'contract path must be absolute: {path}')
    identity = stable_hash(path)
    if identity['sha256'] != record.get('sha256'):
        raise ValueError(f'contract hash mismatch: {path}')
    return identity


def _defines(path: Path) -> dict[str, str]:
    text = re.sub(r'/\*.*?\*/', '', path.read_text(), flags=re.S)
    values = {}
    for line in text.splitlines():
        match = re.match(r'\s*#define\s+(\w+)\s+(.+)', line.split('//')[0])
        if match:
            key, value = match.groups()
            normalized = re.sub(r'[\s()]', '', value)
            if key in values and values[key] != normalized:
                raise ValueError(f'conflicting compiled definition: {key}')
            values[key] = normalized
    return values


def validate_contract(path: Path, expected_sha256: str) -> tuple[dict, dict]:
    contract_identity = checked_file({'path': str(path.absolute()), 'sha256': expected_sha256})
    contract = json.loads(path.read_text())
    budget._stable([contract_identity])
    case = contract.get('case')
    if contract.get('schema_version') != 1 or case not in budget.CASES:
        raise ValueError('invalid native case contract schema or case')
    evidence = {key: checked_file(value) for key, value in contract.get('evidence', {}).items()}
    if not evidence:
        raise ValueError('historical evidence is required')
    records = contract.get('files', {})
    if not REQUIRED_FILES.issubset(records):
        raise ValueError(f'missing native identity roles: {sorted(REQUIRED_FILES-set(records))}')
    files = {key: checked_file(value) for key, value in records.items()}
    for role in HISTORICAL_ROLES:
        witness = records[role].get('historical_hash_witness')
        if witness not in evidence:
            raise ValueError(f'missing historical hash witness: {role}')
        tokens = Path(evidence[witness]['path']).read_text().split()
        if files[role]['sha256'] not in tokens:
            raise ValueError(f'historical evidence does not contain exact hash: {role}')
    source_records = contract.get('source_files', {})
    if not source_records:
        raise ValueError('frozen source-file inventory is required')
    sources = {name: checked_file(record) for name, record in source_records.items()}
    source_root = Path(contract['source_root'])
    observed_sources = {str(p.resolve()) for p in source_root.rglob('*')
                        if p.is_file() and p.suffix in ('.c', '.h')}
    if not source_root.is_absolute() or not observed_sources or observed_sources != {
            value['resolved_path'] for value in sources.values()}:
        raise ValueError('source inventory differs from the reviewed C/header inventory')
    for role in ('compiled_config', 'initialization_source'):
        if not any(value['resolved_path'] == files[role]['resolved_path'] and
                   value['sha256'] == files[role]['sha256'] for value in sources.values()):
            raise ValueError(f'{role} is not in the frozen source inventory')
    params = parse_pluto_parameters(Path(files['runtime_config']['path']))
    expected_power = budget.CASE_BIPOLAR_POWER_ERG_S[case] / 2.0
    expected = {'JET_PWR': expected_power, 'JET_SPD': 0.1, 'JET_START_TIME': 0.,
                'JET_END_TIME': 50., 'JET_ACTIVE_TIME': 50., 'JET_EPISODES': 1.}
    for key, value in expected.items():
        if not math.isclose(params[key], value, rel_tol=1e-12, abs_tol=0.):
            raise ValueError(f'case physical parameter mismatch: {key}')
    defs = _defines(Path(files['compiled_config']['path']))
    required_defs = {'PHYSICS': 'HD', 'DIMENSIONS': '3', 'GEOMETRY': 'CARTESIAN',
                     'BODY_FORCE': 'VECTOR', 'EOS': 'IDEAL', 'NTRACER': '1',
                     'UNIT_DENSITY': 'CONST_amu*MU_NORM', 'UNIT_LENGTH': 'CONST_pc*1e3',
                     'UNIT_VELOCITY': 'CONST_c', 'MU_NORM': '0.60364'}
    for key, value in required_defs.items():
        if defs.get(key) != value:
            raise ValueError(f'unsupported compiled physical definition: {key}')
    init_text = re.sub(r'/\*.*?\*/|//[^\n]*', '', Path(files['initialization_source']['path']).read_text(), flags=re.S)
    gammas = re.findall(r'\bg_gamma\s*=\s*([^;]+);', init_text)
    if not gammas or any(re.sub(r'\s', '', value) != '5.0/3.0' for value in gammas):
        raise ValueError('initialization source does not establish gamma=5/3')
    atmosphere = 'tabulated_cosmo_002003.csv' if case.startswith('C-') else 'tabulated_cosmo_002031.csv'
    env_config = Path(files['environment_config']['path']).read_text()
    tables = re.findall(r'^\s*TabulatedData\s+(\S+)', env_config, flags=re.M)
    if tables != [atmosphere] or Path(files['environment']['path']).name != atmosphere:
        raise ValueError('case atmosphere binding mismatch')
    budget.load_environment(Path(files['environment']['path']))
    log_id = contract.get('production_log')
    if log_id not in evidence:
        raise ValueError('accepted production log is required')
    production_log = Path(evidence[log_id]['path']).read_text()
    for line in (f'CASE_ID={case}', f"WORKDIR={contract['historical_workdir']}"):
        if line not in production_log.splitlines():
            raise ValueError(f'production log does not bind {line}')
    historical_problem = Path(contract['historical_workdir'])/'problem'
    problem = Path(contract['problem_root'])
    if not problem.is_absolute() or not historical_problem.is_dir() or historical_problem.resolve() != problem.resolve():
        raise ValueError('live problem root is not the historical run or its exact resolved migration target')
    role_locations = {'runtime_config': 'pluto.ini', 'environment_config': 'environment.ini',
                      'environment': atmosphere, 'compiled_config': 'src/definitions.h',
                      'initialization_source': 'src/init.c', 'binary': 'pluto', 'grid_file': 'outputs/grid.out'}
    for role, relative in role_locations.items():
        if role in files and Path(files[role]['resolved_path']) != (problem/relative).resolve():
            raise ValueError(f'native role escapes its historical problem tree: {role}')
    if source_root.resolve() != (problem/'src').resolve():
        raise ValueError('source root escapes the historical problem tree')
    if case == 'G-HI':
        raise ValueError('G-HI inherited-source/restart qualification must be integrated before execution')
    chain = []
    specifications = contract.get('snapshots', [])
    if [row['index'] for row in specifications] != list(range(51)):
        raise ValueError('contract must explicitly bind the full 0..50 native chain')
    for row in specifications:
        source = Path(row['path'])
        if not source.is_absolute() or source.name != f"data.{row['index']:04d}.flt.h5":
            raise ValueError('snapshot path/index mismatch')
        if source.parent.resolve() != (problem/'outputs').resolve() or source.resolve().parent != (problem/'outputs').resolve():
            raise ValueError('snapshot escapes its historically bound output tree')
        before = budget._stat_identity(source)
        inspected = inspect_file(source, output_index=row['index'])
        if len(inspected) != 1:
            raise ValueError('snapshot has an ambiguous timestep')
        snap = inspected[0]
        if abs(snap.actual_time_myr-row['index']) > 0.05 or list(snap.shape) != contract['shape_nz_ny_nx']:
            raise ValueError('native cadence or grid shape mismatch')
        budget._stable([before])
        chain.append({'index': row['index'], 'path': str(source), 'timestep': snap.timestep,
                      'time_code': snap.time_code, 'metadata': before})
    if abs(chain[0]['time_code']/budget.CODE_TIME_PER_MYR) > 1e-6:
        raise ValueError('baseline is not actual t=0')
    if not all(b['time_code'] > a['time_code'] for a,b in zip(chain,chain[1:])):
        raise ValueError('native times are not strictly increasing')
    budget._stable([contract_identity, *evidence.values(), *files.values(), *sources.values()])
    report = {'schema_version': 1, 'status': 'native_measurement_preflight_passed', 'case': case,
              'contract': contract_identity, 'historical_evidence': evidence, 'files': files,
              'source_files': sources, 'chain': chain,
              'semantic_checks': {'runtime_case_power_speed_duration': 'passed',
                                  'compiled_geometry_eos_units': 'passed',
                                  'initialization_gamma': 'passed',
                                  'historically_bound_configuration_and_atmosphere': 'passed'},
              'scientific_qualification': {'qualified': False, 'holds': [
                  'historical_executable_to_source_build_linkage_not_established_by_this_preflight',
                  'native_geometry_tracer_and_boundary_holds_require_result_review']}}
    return contract, report


def prepare_receipt(report: dict, index: int, output: Path, cache: dict | None = None) -> dict:
    if report.get('status') != 'native_measurement_preflight_passed':
        raise ValueError('native preflight did not pass')
    case = report['case']
    if case == 'G-HI' and index >= 48:
        raise ValueError('G-HI snapshots 48-50 are scientifically excluded')
    if output.exists():
        raise ValueError(f'refusing to overwrite input receipt: {output}')
    selected = {row['index']: row for row in report['chain']}
    if index not in selected:
        raise ValueError('requested snapshot absent from accepted chain')
    current, initial = selected[index], selected[0]
    files = report['files']
    paths = {'current_h5': Path(current['path']), 'initial_h5': Path(initial['path']),
             'environment': Path(files['environment']['path'])}
    if 'grid_file' in files:
        paths['grid_file'] = Path(files['grid_file']['path'])
    cache = {} if cache is None else cache
    records = {}
    for role, path in paths.items():
        key = str(path)
        if key not in cache:
            cache[key] = stable_hash(path)
        budget._stable([cache[key]])
        records[role] = cache[key]
    budget._stable([current['metadata'], initial['metadata'], report['contract'],
                    *report['historical_evidence'].values(), *files.values(), *report['source_files'].values()])
    payload = {'schema_version': 1, 'status': 'bound_spherical_budget_inputs', 'case': case,
               'snapshot_index': index, 'inputs': records,
               'current': {key: current[key] for key in ('timestep', 'time_code')},
               'initial': {key: initial[key] for key in ('timestep', 'time_code')},
               'native_preflight': {key: report[key] for key in ('contract', 'semantic_checks', 'scientific_qualification')}}
    budget._atomic_publish(output, payload)
    return payload


def validate_existing_receipt(report: dict, index: int, receipt: dict) -> None:
    selected = {row['index']: row for row in report['chain']}
    current, initial = selected[index], selected[0]
    files = report['files']
    expected = {'current_h5': current['metadata'], 'initial_h5': initial['metadata'],
                'environment': files['environment']}
    if 'grid_file' in files:
        expected['grid_file'] = files['grid_file']
    if (receipt.get('status') != 'bound_spherical_budget_inputs' or receipt.get('case') != report['case']
        or receipt.get('snapshot_index') != index or set(receipt.get('inputs', {})) != set(expected)
        or receipt.get('native_preflight', {}).get('contract', {}).get('sha256') != report['contract']['sha256']):
        raise ValueError('existing receipt differs from requested case/index/roles/contract')
    for name, metadata in expected.items():
        record = receipt['inputs'][name]
        for key, value in metadata.items():
            if key != 'role' and record.get(key) != value:
                raise ValueError(f'existing receipt differs from historically bound input: {name}:{key}')
    for role, snapshot in [('current', current), ('initial', initial)]:
        if receipt.get(role) != {key: snapshot[key] for key in ('timestep', 'time_code')}:
            raise ValueError(f'existing receipt timestep differs: {role}')
    budget._stable(list(receipt['inputs'].values()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    _, report = validate_contract(args.contract, args.contract_sha256)
    budget._atomic_publish(args.output, report)


if __name__ == '__main__':
    main()
