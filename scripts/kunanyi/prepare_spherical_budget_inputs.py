#!/usr/bin/env python3
"""Validate a reviewed native-case contract and bind exact spherical inputs.

The contract is a reviewed input, never generated from live filenames by this
program. Historical hash witnesses establish config/atmosphere identity;
current source and binary hashes establish stability, not historical linkage.
"""
from __future__ import annotations

import argparse
import hashlib
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


def inherited_lineage(contract: dict, files: dict, sources: dict) -> tuple[dict, dict, dict]:
    record = contract.get('inherited_lineage')
    if not isinstance(record, dict):
        raise ValueError('G-HI requires a reviewed inherited lineage receipt')
    identity = checked_file(record)
    receipt = json.loads(Path(identity['path']).read_text())
    budget._stable([identity])
    if (receipt.get('schema_version') != 1 or receipt.get('status') != 'passed'
        or receipt.get('lineage') != 'accepted failed-run parent build/source plus validated 10 Myr home continuation'):
        raise ValueError('invalid or non-passing G-HI lineage receipt')
    parent = Path(receipt['parent_problem'])
    continuation = Path(receipt['continuation_problem'])
    source = Path(contract['source_root'])
    if (not parent.is_absolute() or not continuation.is_absolute() or parent.resolve() == continuation.resolve()
        or Path(contract['problem_root']).resolve() != continuation.resolve()
        or source.resolve() != (parent/'src').resolve()
        or Path(receipt['problem_source_dir']).resolve() != source.resolve()):
        raise ValueError('G-HI lineage parent/continuation/source roots disagree')
    if (continuation/'src').exists() or (continuation/'src').is_symlink():
        raise ValueError('G-HI continuation must explicitly inherit its parent source')
    source_hashes = {str(Path(value['resolved_path']).relative_to(source.resolve())): value['sha256']
                     for value in sources.values()}
    source_digest = hashlib.sha256(json.dumps(source_hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if (source_hashes != receipt.get('source_hashes') or len(source_hashes) != receipt.get('source_file_count')
        or source_digest != receipt.get('source_manifest_sha256')):
        raise ValueError('G-HI source inventory differs from its lineage receipt')
    dependencies = {}
    binary_paths = [parent/'src/pluto', parent/'pluto', continuation/'pluto']
    if receipt.get('binary_paths') != [str(p) for p in binary_paths]:
        raise ValueError('G-HI lineage binary paths do not bind the inherited build')
    for ordinal, path in enumerate(binary_paths):
        dependencies[f'lineage_binary_{ordinal}'] = checked_file({'path': str(path), 'sha256': receipt['binary_sha256']})
    if files['binary']['sha256'] != receipt['binary_sha256']:
        raise ValueError('G-HI contract binary differs from its lineage receipt')
    dependencies['lineage_build_config'] = checked_file({
        'path': str(parent/'src/pluto.ini'), 'sha256': receipt['build_pluto_ini_sha256']})
    rendered = receipt.get('rendered_inputs', {})
    names = {'case_manifest.json', 'definitions_overrides.json', 'environment.ini',
             'pluto.ini', 'tabulated_cosmo_002031.csv'}
    if set(rendered) != names:
        raise ValueError('G-HI lineage rendered-input inventory is incomplete')
    for name, entry in rendered.items():
        for segment, root in [('parent', parent), ('continuation', continuation)]:
            if Path(entry[f'{segment}_path']) != root/name:
                raise ValueError('G-HI lineage rendered input escapes its run')
            dependencies[f'lineage_{segment}_{name}'] = checked_file({
                'path': entry[f'{segment}_path'], 'sha256': entry['sha256']})
    for role, name in [('runtime_config', 'pluto.ini'), ('environment_config', 'environment.ini'),
                       ('environment', 'tabulated_cosmo_002031.csv')]:
        if files[role]['sha256'] != rendered[name]['sha256']:
            raise ValueError('G-HI contract configuration differs from its lineage receipt')
    for segment, root in [('parent', parent), ('continuation', continuation)]:
        dependencies[f'lineage_{segment}_grid'] = checked_file({
            'path': str(root/'outputs/grid.out'), 'sha256': receipt['grid_out'][segment]})
    evidence = receipt.get('historical_evidence', {})
    required = {'parent_run_log', 'parent_source_revisions', 'continuation_run_log', 'staging_manifest',
                'restart_report', 'canonical_sequence_report', 'endpoint_report', 'source_revisions', 'done_marker'}
    if set(evidence) != required:
        raise ValueError('G-HI lineage historical evidence inventory is incomplete')
    for name, entry in evidence.items():
        dependencies[f'lineage_evidence_{name}'] = checked_file(entry)
    log = contract['evidence'][contract['production_log']]
    if (Path(log['path']).resolve() != Path(evidence['continuation_run_log']['path']).resolve()
        or log['sha256'] != evidence['continuation_run_log']['sha256']):
        raise ValueError('G-HI production log differs from its lineage receipt')
    restart = receipt.get('restart', {})
    restart_names = {'fluid_catalogue': 'dbl.h5.out', 'fluid_hdf5': 'data.0002.dbl.h5',
                     'particle_restart': 'particles.1000.dbl', 'restart_out': 'restart.out'}
    identities = restart.get('input_identity', {})
    hashes = restart.get('verified_sha256', {})
    if (restart.get('fluid_hdf5_rehashed') is not True or set(identities) != set(restart_names)
        or set(hashes) != set(restart_names)
        or restart.get('report', {}).get('input_sha256') != hashes
        or restart.get('report', {}).get('status') != 'ok'):
        raise ValueError('G-HI restart lacks verified hash-time identities')
    for name, filename in restart_names.items():
        path = parent/'outputs'/filename
        expected = identities[name]
        if (restart['accepted_parent_restart_paths'].get(name) != str(path)
            or expected.get('path') != str(path) or budget._stat_identity(path) != expected):
            raise ValueError(f'G-HI restart identity changed: {name}')
        dependencies[f'lineage_restart_{name}'] = expected
    for name in ('fluid_hdf5', 'particle_restart'):
        link = continuation/'outputs'/restart_names[name]
        if (restart['continuation_inherited_links'].get(name) != str(link) or not link.is_symlink()
            or link.resolve() != (parent/'outputs'/restart_names[name]).resolve()):
            raise ValueError(f'G-HI inherited restart link changed: {name}')
        dependencies[f'lineage_restart_link_{name}'] = budget._stat_identity(link)
    snapshots = receipt.get('snapshots', {})
    analysis = snapshots.get('analysis_chain', [])
    accepted = snapshots.get('accepted_chain', [])
    if ([r.get('output_index') for r in analysis] != list(range(51))
        or [r.get('output_index') for r in accepted] != list(range(51))):
        raise ValueError('G-HI lineage canonical chain is incomplete')
    for label, chain, transition in [('analysis', analysis, 10), ('accepted', accepted, 11)]:
        for index, entry in enumerate(chain):
            root = parent if index < transition else continuation
            path = root/'outputs'/f'data.{index:04d}.flt.h5'
            expected = {key: entry.get(key) for key in budget._stat_identity(path)}
            if entry.get('path') != str(path) or budget._stat_identity(path) != expected:
                raise ValueError(f'G-HI lineage snapshot identity changed: {label} {index}')
    anchor = continuation/'outputs/data.0010.flt.h5'
    if not anchor.is_symlink() or anchor.resolve() != (parent/'outputs/data.0010.flt.h5').resolve():
        raise ValueError('G-HI float restart anchor is not the accepted inherited symlink')
    budget._stable([identity, *dependencies.values()])
    return {'receipt': identity, 'limitations': receipt['limitations']}, dependencies, {
        entry['output_index']: entry for entry in analysis}


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
    if case != 'G-HI' and 'inherited_lineage' in contract:
        raise ValueError('inherited lineage is restricted to G-HI')
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
    lineage = None
    lineage_chain = {}
    if case == 'G-HI':
        lineage, dependencies, lineage_chain = inherited_lineage(contract, files, sources)
        evidence['inherited_lineage_receipt'] = lineage['receipt']
        files.update(dependencies)
    role_locations = {'runtime_config': 'pluto.ini', 'environment_config': 'environment.ini',
                      'environment': atmosphere, 'compiled_config': 'src/definitions.h',
                      'initialization_source': 'src/init.c', 'binary': 'pluto', 'grid_file': 'outputs/grid.out'}
    for role, relative in role_locations.items():
        expected_path = source_root/Path(relative).name if case == 'G-HI' and relative.startswith('src/') else problem/relative
        if role in files and Path(files[role]['resolved_path']) != expected_path.resolve():
            raise ValueError(f'native role escapes its historical problem tree: {role}')
    if case != 'G-HI' and source_root.resolve() != (problem/'src').resolve():
        raise ValueError('source root escapes the historical problem tree')
    chain = []
    specifications = contract.get('snapshots', [])
    last = 47 if case == 'G-HI' else 50
    if [row['index'] for row in specifications] != list(range(last + 1)):
        raise ValueError(f'contract must explicitly bind the full 0..{last} native chain')
    for row in specifications:
        source = Path(row['path'])
        if not source.is_absolute() or source.name != f"data.{row['index']:04d}.flt.h5":
            raise ValueError('snapshot path/index mismatch')
        inherited = lineage_chain.get(row['index'])
        if case == 'G-HI':
            if str(source) != inherited['path']:
                raise ValueError('snapshot differs from the inherited canonical chain')
        elif source.parent.resolve() != (problem/'outputs').resolve() or source.resolve().parent != (problem/'outputs').resolve():
            raise ValueError('snapshot escapes its historically bound output tree')
        before = budget._stat_identity(source)
        if inherited and before != {key: inherited.get(key) for key in before}:
            raise ValueError('snapshot differs from its inherited lineage identity')
        inspected = inspect_file(source, output_index=row['index'])
        if len(inspected) != 1:
            raise ValueError('snapshot has an ambiguous timestep')
        snap = inspected[0]
        if abs(snap.actual_time_myr-row['index']) > 0.05 or list(snap.shape) != contract['shape_nz_ny_nx']:
            raise ValueError('native cadence or grid shape mismatch')
        if inherited and (snap.timestep != inherited.get('timestep') or snap.time_code != inherited.get('time_code')
                          or list(snap.shape) != inherited.get('shape')):
            raise ValueError('native snapshot metadata differs from inherited lineage')
        budget._stable([before])
        chain.append({'index': row['index'], 'path': str(source), 'timestep': snap.timestep,
                      'time_code': snap.time_code, 'metadata': before})
    if abs(chain[0]['time_code']/budget.CODE_TIME_PER_MYR) > 1e-6:
        raise ValueError('baseline is not actual t=0')
    if not all(b['time_code'] > a['time_code'] for a,b in zip(chain,chain[1:])):
        raise ValueError('native times are not strictly increasing')
    budget._stable([contract_identity, *evidence.values(), *files.values(), *sources.values(),
                    *(row['metadata'] for row in chain)])
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
    if lineage is not None:
        report['inherited_lineage'] = lineage
        report['semantic_checks']['inherited_parent_source_restart_and_chain'] = 'passed'
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
    if 'inherited_lineage' in report:
        payload['native_preflight']['inherited_lineage'] = report['inherited_lineage']
    budget._atomic_publish(output, payload)
    return payload


def validate_existing_receipt(report: dict, index: int, receipt: dict) -> None:
    if report['case'] == 'G-HI' and index >= 48:
        raise ValueError('G-HI snapshots 48-50 are scientifically excluded')
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
    if receipt.get('native_preflight', {}).get('inherited_lineage') != report.get('inherited_lineage'):
        raise ValueError('existing receipt differs from inherited lineage binding')
    for name, metadata in expected.items():
        record = receipt['inputs'][name]
        for key, value in metadata.items():
            if key != 'role' and record.get(key) != value:
                raise ValueError(f'existing receipt differs from historically bound input: {name}:{key}')
    for role, snapshot in [('current', current), ('initial', initial)]:
        if receipt.get(role) != {key: snapshot[key] for key in ('timestep', 'time_code')}:
            raise ValueError(f'existing receipt timestep differs: {role}')
    budget._stable(list(receipt['inputs'].values()))
    budget._stable([report['contract'], *report['historical_evidence'].values(),
                    *files.values(), *report['source_files'].values()])


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
