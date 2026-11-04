from __future__ import annotations

import json
import hashlib
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/kunanyi'))
sys.path.insert(0, str(Path(__file__).parent))
import prepare_spherical_budget_inputs as preflight
import run_spherical_budget_case as runner
from test_spherical_energy_budget import _write_h5, _base_state, _write_environment


def _contract(tmp_path):
    tmp_path.mkdir(exist_ok=True)
    problem = tmp_path/'problem'
    (problem/'src').mkdir(parents=True)
    (problem/'outputs').mkdir()
    definitions = problem/'src/definitions.h'
    definitions.write_text('\n'.join(f'#define {key} {value}' for key,value in {
        'PHYSICS':'HD', 'DIMENSIONS':'3', 'GEOMETRY':'CARTESIAN', 'BODY_FORCE':'VECTOR',
        'EOS':'IDEAL', 'NTRACER':'1', 'MU_NORM':'0.60364',
        'UNIT_DENSITY':'((CONST_amu)*MU_NORM)', 'UNIT_LENGTH':'((CONST_pc)*1e3)',
        'UNIT_VELOCITY':'CONST_c'}.items()))
    init = problem/'src/init.c'; init.write_text('void Init() { g_gamma = 5.0/3.0; }')
    runtime = problem/'pluto.ini'
    runtime.write_text('[Parameters]\n'+'\n'.join(f'{k} {v}' for k,v in {
        'JET_PWR':1e45,'JET_SPD':.1,'JET_INJECTION_HEIGHT':.75,'JET_INITIAL_RADIUS':.1,
        'JET_X1O':0,'JET_X2O':0,'JET_X3O':0,'JET_ROTATION_ANGLE':0,
        'JET_START_TIME':0,'JET_END_TIME':50,'JET_ACTIVE_TIME':50,'JET_EPISODES':1}.items()))
    env = problem/'tabulated_cosmo_002003.csv'; _write_environment(env)
    env_config = problem/'environment.ini'; env_config.write_text('[Tabulated Environment]\nTabulatedData tabulated_cosmo_002003.csv\n')
    binary = problem/'pluto'; binary.write_bytes(b'fixture-not-native-binary')
    files = {'runtime_config':runtime, 'environment_config':env_config, 'environment':env,
             'compiled_config':definitions, 'initialization_source':init, 'binary':binary}
    records = {key:{'path':str(path), 'sha256':preflight.budget._sha256(path)} for key,path in files.items()}
    witness = tmp_path/'historic_hashes.txt'
    witness.write_text('\n'.join(f"{records[key]['sha256']}  {files[key]}" for key in preflight.HISTORICAL_ROLES))
    for key in preflight.HISTORICAL_ROLES:records[key]['historical_hash_witness']='hashes'
    log = tmp_path/'production.out'; log.write_text(f'CASE_ID=C-HI\nWORKDIR={tmp_path}\n')
    evidence = {key:{'path':str(path),'sha256':preflight.budget._sha256(path)}
                for key,path in {'hashes':witness, 'production':log}.items()}
    snapshots = []
    for index in range(51):
        path=problem/'outputs'/f'data.{index:04d}.flt.h5'
        _write_h5(path,_base_state(),timestep=f'Timestep_{index}',time_code=index*preflight.budget.CODE_TIME_PER_MYR)
        snapshots.append({'index':index,'path':str(path)})
    contract = {'schema_version':1, 'case':'C-HI','files':records,'evidence':evidence,
                'source_files':{key:records[key] for key in ('compiled_config','initialization_source')},
                'source_root':str(problem/'src'), 'problem_root':str(problem),
                'production_log':'production','historical_workdir':str(tmp_path),
                'shape_nz_ny_nx':[5,5,5], 'snapshots':snapshots}
    path=tmp_path/'contract.json'; path.write_text(json.dumps(contract))
    return path,contract


def _validate(path, contract=None):
    if contract is not None:path.write_text(json.dumps(contract))
    return preflight.validate_contract(path,preflight.budget._sha256(path))


def test_contract_and_receipt_preserve_provenance_holds(tmp_path):
    path,_=_contract(tmp_path)
    _,report=_validate(path)
    receipt=preflight.prepare_receipt(report,1,tmp_path/'receipt.json')
    assert receipt['case']=='C-HI'
    assert receipt['native_preflight']['scientific_qualification']['qualified'] is False
    assert receipt['inputs']['current_h5']['sha256']==preflight.budget._sha256(tmp_path/'problem/outputs/data.0001.flt.h5')
    with pytest.raises(ValueError,match='overwrite'):
        preflight.prepare_receipt(report,1,tmp_path/'receipt.json')


@pytest.mark.parametrize('change,match',[
    ('wrong_case','parameter mismatch'),('gamma','gamma'),('units','definition'),
    ('history','historical evidence'),('missing_evidence','historical evidence'),
    ('bad_time','cadence'),('missing_index','full 0..50'),('wrong_log','production log'),
])
def test_rejects_material_identity_failures(tmp_path,change,match):
    path,contract=_contract(tmp_path)
    if change=='wrong_case':contract['case']='C-LO'
    elif change in ('gamma','units'):
        role='initialization_source' if change=='gamma' else 'compiled_config'
        p=Path(contract['files'][role]['path'])
        p.write_text(p.read_text().replace('5.0/3.0','1.4').replace('CONST_c','1e5'))
        contract['files'][role]['sha256']=preflight.budget._sha256(p)
    elif change=='history':
        p=Path(contract['evidence']['hashes']['path']);p.write_text('no historical hashes here')
        contract['evidence']['hashes']['sha256']=preflight.budget._sha256(p)
    elif change=='missing_evidence':contract['evidence']={}
    elif change=='bad_time':
        p=tmp_path/'problem/outputs/data.0001.flt.h5';_write_h5(p,_base_state(),timestep='Timestep_1',time_code=0.)
    elif change=='missing_index':contract['snapshots'].pop(3)
    elif change=='wrong_log':contract['historical_workdir']='/other/run'
    with pytest.raises(ValueError,match=match):_validate(path,contract)


def test_pinned_contract_and_live_input_mutation_are_rejected(tmp_path):
    path,contract=_contract(tmp_path)
    with pytest.raises(ValueError,match='hash mismatch'):
        preflight.validate_contract(path,'0'*64)
    _,report=_validate(path)
    target=tmp_path/'problem/outputs/data.0001.flt.h5'
    with target.open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='mutated'):
        preflight.prepare_receipt(report,1,tmp_path/'receipt.json')


def test_receipt_hash_cache_reads_baseline_once(tmp_path,monkeypatch):
    path,_=_contract(tmp_path);_,report=_validate(path)
    actual=preflight.stable_hash;reads=[]
    def counted(path):
        reads.append(path.name);return actual(path)
    monkeypatch.setattr(preflight,'stable_hash',counted)
    cache={}
    for index in (0,1,2):preflight.prepare_receipt(report,index,tmp_path/f'input_{index}.json',cache)
    assert reads.count('data.0000.flt.h5')==1
    assert reads.count('tabulated_cosmo_002003.csv')==1


def test_single_case_smoke_completion_and_duplicate_refusal(tmp_path):
    path,_=_contract(tmp_path)
    result=runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1],0.)
    assert result['scientifically_retained_indices']==list(range(51))
    assert result['requested_indices']==[1] and result['completed_indices']==[1]
    output=json.loads((tmp_path/'results/snapshot_0001.json').read_text())
    assert output['execution_status']=='completed_spherical_energy_budget_measurement'
    assert output['thresholds']['100']['measurement_status']=='unavailable_no_cells_meet_speed_threshold'
    with pytest.raises(ValueError,match='duplicate execution'):
        runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1],0.)


def test_resume_checks_completed_hashes_and_skips_the_first_snapshot(tmp_path,monkeypatch):
    path,_=_contract(tmp_path)
    actual=runner.budget.extract_snapshot
    calls=[]
    def interrupt(**kwargs):
        calls.append(kwargs['snapshot_index'])
        if kwargs['snapshot_index']==2:raise RuntimeError('simulated interruption')
        return actual(**kwargs)
    monkeypatch.setattr(runner.budget,'extract_snapshot',interrupt)
    with pytest.raises(RuntimeError,match='interruption'):
        runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1,2],0.)
    assert not (tmp_path/'results/run.lock').exists()
    assert not (tmp_path/'results/completion.json').exists()
    assert (tmp_path/'results/snapshot_0001.complete.json').exists()
    monkeypatch.setattr(runner.budget,'extract_snapshot',actual)
    completed=runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1,2],0.)
    assert completed['completed_indices']==[1,2]


def test_resume_rejects_changed_product(tmp_path,monkeypatch):
    path,_=_contract(tmp_path)
    actual=runner.budget.extract_snapshot
    def interrupt(**kwargs):
        if kwargs['snapshot_index']==2:raise RuntimeError('simulated interruption')
        return actual(**kwargs)
    monkeypatch.setattr(runner.budget,'extract_snapshot',interrupt)
    with pytest.raises(RuntimeError):
        runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1,2],0.)
    (tmp_path/'results/snapshot_0001.json').write_text('{}')
    monkeypatch.setattr(runner.budget,'extract_snapshot',actual)
    with pytest.raises(ValueError,match='completed product changed'):
        runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1,2],0.)


def test_unreviewed_extra_source_and_binary_change_rejected(tmp_path):
    path,_=_contract(tmp_path)
    extra=tmp_path/'problem/src/new.c';extra.write_text('void extra() {}')
    with pytest.raises(ValueError,match='source inventory'):_validate(path)
    extra.unlink()
    (tmp_path/'problem/pluto').write_bytes(b'different executable')
    with pytest.raises(ValueError,match='contract hash mismatch'):_validate(path)


def test_same_shape_other_run_cannot_replace_snapshot(tmp_path):
    path,contract=_contract(tmp_path)
    foreign=tmp_path/'unrelated_outputs';foreign.mkdir()
    source=foreign/'data.0001.flt.h5'
    _write_h5(source,_base_state(),timestep='Timestep_1',time_code=preflight.budget.CODE_TIME_PER_MYR)
    contract['snapshots'][1]['path']=str(source)
    with pytest.raises(ValueError,match='historically bound output tree'):_validate(path,contract)


@pytest.mark.parametrize('completed',[False,True])
def test_resume_cannot_substitute_receipt_input_from_another_run(tmp_path,monkeypatch,completed):
    path,_=_contract(tmp_path)
    actual=runner.budget.extract_snapshot
    def interrupt(**kwargs):
        if kwargs['snapshot_index']==(2 if completed else 1):raise RuntimeError('interrupted')
        return actual(**kwargs)
    monkeypatch.setattr(runner.budget,'extract_snapshot',interrupt)
    with pytest.raises(RuntimeError):
        runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1,2],0.)
    foreign=tmp_path/'unrelated_outputs';foreign.mkdir()
    source=foreign/'data.0001.flt.h5'
    _write_h5(source,_base_state(),timestep='Timestep_1',time_code=preflight.budget.CODE_TIME_PER_MYR)
    receipt_path=tmp_path/'results/inputs/snapshot_0001.json'
    receipt=json.loads(receipt_path.read_text());receipt['inputs']['current_h5']=preflight.stable_hash(source)
    receipt_path.write_text(json.dumps(receipt))
    if completed:
        done_path=tmp_path/'results/snapshot_0001.complete.json'
        done=json.loads(done_path.read_text());done['input_receipt']=preflight.stable_hash(receipt_path)
        done_path.write_text(json.dumps(done))
    monkeypatch.setattr(runner.budget,'extract_snapshot',actual)
    with pytest.raises(ValueError,match='historically bound input'):
        runner.run_case(path,preflight.budget._sha256(path),tmp_path/'results',[1,2],0.)


def _inherited_contract(tmp_path):
    path, contract = _contract(tmp_path)
    parent = tmp_path/'problem'
    late = tmp_path/'continuation/problem'
    (late/'outputs').mkdir(parents=True)
    old_environment = parent/'tabulated_cosmo_002003.csv'
    environment = parent/'tabulated_cosmo_002031.csv'
    old_environment.rename(environment)
    (parent/'environment.ini').write_text('TabulatedData tabulated_cosmo_002031.csv\n')
    (parent/'src/pluto').write_bytes((parent/'pluto').read_bytes())
    (parent/'src/pluto.ini').write_bytes((parent/'pluto.ini').read_bytes())
    names = ['pluto.ini', 'environment.ini', environment.name, 'case_manifest.json', 'definitions_overrides.json']
    for name in names:
        if not (parent/name).exists():
            (parent/name).write_text('{}')
        shutil.copyfile(parent/name, late/name)
    shutil.copyfile(parent/'pluto', late/'pluto')
    for root in (parent, late):
        (root/'outputs/grid.out').write_text('synthetic retained geometry\n')
    for index in range(10, 51):
        current = late/'outputs'/f'data.{index:04d}.flt.h5'
        if index == 10:
            current.symlink_to(parent/'outputs'/current.name)
        else:
            shutil.copyfile(parent/'outputs'/current.name, current)
    contract.update(case='G-HI', problem_root=str(late), historical_workdir=str(late.parent))
    for role, name in [('runtime_config', 'pluto.ini'), ('environment_config', 'environment.ini'),
                       ('environment', environment.name), ('binary', 'pluto')]:
        contract['files'][role].update(path=str(late/name), sha256=preflight.budget._sha256(late/name))
    witness = Path(contract['evidence']['hashes']['path'])
    witness.write_text('\n'.join(contract['files'][key]['sha256'] for key in preflight.HISTORICAL_ROLES))
    contract['evidence']['hashes']['sha256'] = preflight.budget._sha256(witness)
    log = Path(contract['evidence']['production']['path'])
    log.write_text(f'CASE_ID=G-HI\nWORKDIR={late.parent}\n')
    contract['evidence']['production']['sha256'] = preflight.budget._sha256(log)
    source_hashes = {str(Path(value['path']).relative_to(parent/'src')): value['sha256']
                     for value in contract['source_files'].values()}
    historical = {name: contract['evidence']['hashes'] for name in (
        'parent_run_log', 'parent_source_revisions', 'staging_manifest', 'restart_report',
        'canonical_sequence_report', 'endpoint_report', 'source_revisions', 'done_marker')}
    historical['continuation_run_log'] = contract['evidence']['production']
    restart_names = {'fluid_catalogue': 'dbl.h5.out', 'fluid_hdf5': 'data.0002.dbl.h5',
                     'particle_restart': 'particles.1000.dbl', 'restart_out': 'restart.out'}
    restart_paths = {}
    for name, filename in restart_names.items():
        source = parent/'outputs'/filename
        source.write_bytes(f'{name} restart fixture'.encode())
        restart_paths[name] = source
    for name in ('fluid_hdf5', 'particle_restart'):
        (late/'outputs'/restart_names[name]).symlink_to(restart_paths[name])
    restart_hashes = {name: preflight.budget._sha256(source) for name, source in restart_paths.items()}
    def chain(transition):
        values = []
        for index in range(51):
            source = (parent if index < transition else late)/'outputs'/f'data.{index:04d}.flt.h5'
            snap = preflight.inspect_file(source, output_index=index)[0]
            values.append({**preflight.budget._stat_identity(source), 'output_index': index,
                           'timestep': snap.timestep, 'time_code': snap.time_code,
                           'time_myr': snap.actual_time_myr, 'shape': list(snap.shape)})
        return values
    receipt = {
        'schema_version': 1, 'status': 'passed',
        'lineage': 'accepted failed-run parent build/source plus validated 10 Myr home continuation',
        'parent_problem': str(parent), 'continuation_problem': str(late),
        'problem_source_dir': str(parent/'src'), 'source_hashes': source_hashes,
        'source_file_count': len(source_hashes),
        'source_manifest_sha256': hashlib.sha256(json.dumps(source_hashes,sort_keys=True,separators=(',', ':')).encode()).hexdigest(),
        'binary_paths': [str(p) for p in (parent/'src/pluto', parent/'pluto', late/'pluto')],
        'binary_sha256': preflight.budget._sha256(parent/'pluto'),
        'build_pluto_ini_sha256': preflight.budget._sha256(parent/'src/pluto.ini'),
        'rendered_inputs': {name: {'parent_path':str(parent/name), 'continuation_path':str(late/name),
                                  'sha256':preflight.budget._sha256(parent/name)} for name in names},
        'grid_out': {name:preflight.budget._sha256(root/'outputs/grid.out')
                     for name,root in [('parent',parent),('continuation',late)]},
        'historical_evidence': historical,
        'restart': {'report': {'status':'ok','input_sha256':restart_hashes},
                    'verified_sha256':restart_hashes, 'fluid_hdf5_rehashed':True,
                    'accepted_parent_restart_paths': {name:str(source) for name,source in restart_paths.items()},
                    'continuation_inherited_links': {name:str(late/'outputs'/restart_names[name])
                                                     for name in ('fluid_hdf5','particle_restart')},
                    'input_identity': {name:preflight.budget._stat_identity(source) for name,source in restart_paths.items()}},
        'snapshots': {'analysis_chain':chain(10), 'accepted_chain':chain(11)},
        'limitations': {'historical_source_tree_hash_manifest_available':False},
    }
    lineage_path = tmp_path/'lineage.json'
    lineage_path.write_text(json.dumps(receipt))
    contract['inherited_lineage'] = {'path':str(lineage_path), 'sha256':preflight.budget._sha256(lineage_path)}
    contract['snapshots'] = [{'index':r['output_index'],'path':r['path']} for r in receipt['snapshots']['analysis_chain'][:48]]
    path.write_text(json.dumps(contract))
    return path, contract, receipt


def test_inherited_lineage_binds_parent_zero_and_continuation_without_restart_rehash(tmp_path, monkeypatch):
    path, contract, lineage = _inherited_contract(tmp_path)
    original = preflight.budget._sha256
    restart_paths = set(lineage['restart']['accepted_parent_restart_paths'].values())
    def no_restart_hash(source):
        assert str(source) not in restart_paths, 'verified restart must not be rehashed'
        return original(source)
    monkeypatch.setattr(preflight.budget, '_sha256', no_restart_hash)
    _, report = _validate(path)
    assert [row['index'] for row in report['chain']] == list(range(48))
    assert report['chain'][0]['path'].startswith(lineage['parent_problem'])
    assert report['chain'][10]['path'].startswith(lineage['continuation_problem'])
    receipt = preflight.prepare_receipt(report, 47, tmp_path/'input.json')
    assert receipt['native_preflight']['inherited_lineage']['receipt']['sha256'] == contract['inherited_lineage']['sha256']
    preflight.validate_existing_receipt(report, 47, receipt)
    with pytest.raises(ValueError, match='scientifically excluded'):
        preflight.prepare_receipt(report, 48, tmp_path/'excluded.json')
    changed = Path(lineage['restart']['accepted_parent_restart_paths']['fluid_hdf5'])
    changed.write_bytes(b'changed after preflight')
    with pytest.raises(ValueError, match='mutated'):
        preflight.validate_existing_receipt(report, 47, receipt)


def test_inherited_case_executes_with_retained_indices_only(tmp_path):
    path, _, _ = _inherited_contract(tmp_path)
    result = runner.run_case(path, preflight.budget._sha256(path), tmp_path/'results', [10], 0.)
    assert result['scientifically_retained_indices'] == list(range(48))
    assert result['completed_indices'] == [10]
    receipt = json.loads((tmp_path/'results/inputs/snapshot_0010.json').read_text())
    assert receipt['inputs']['initial_h5']['path'] == str(tmp_path/'problem/outputs/data.0000.flt.h5')
    assert receipt['inputs']['current_h5']['path'] == str(tmp_path/'continuation/problem/outputs/data.0010.flt.h5')
    assert receipt['native_preflight']['inherited_lineage']['limitations']['historical_source_tree_hash_manifest_available'] is False


@pytest.mark.parametrize('change,match', [
    ('receipt_hash','hash mismatch'), ('receipt_status','non-passing'), ('source','source inventory differs'),
    ('restart','restart identity changed'), ('missing_identity','hash-time identities'),
    ('skipped_hash','hash-time identities'), ('chain','canonical chain'), ('case','restricted to G-HI'),
    ('metadata','metadata differs'), ('excluded','full 0..47'), ('missing_receipt','reviewed inherited'),
])
def test_inherited_lineage_rejects_substitution(tmp_path, change, match):
    path, contract, receipt = _inherited_contract(tmp_path)
    if change == 'receipt_hash':
        contract['inherited_lineage']['sha256'] = '0'*64
    elif change == 'receipt_status': receipt['status'] = 'pending'
    elif change == 'source': receipt['source_hashes']['init.c'] = '0'*64
    elif change == 'restart':
        Path(receipt['restart']['accepted_parent_restart_paths']['fluid_hdf5']).write_bytes(b'changed')
    elif change == 'missing_identity': del receipt['restart']['input_identity']
    elif change == 'skipped_hash': receipt['restart']['fluid_hdf5_rehashed'] = False
    elif change == 'chain': contract['snapshots'][20]['path'] = contract['snapshots'][20]['path'].replace('/continuation', '')
    elif change == 'case': contract['case'] = 'C-HI'
    elif change == 'metadata': receipt['snapshots']['analysis_chain'][20]['time_code'] += 1
    elif change == 'excluded': contract['snapshots'].append({'index':48,'path':receipt['snapshots']['analysis_chain'][48]['path']})
    elif change == 'missing_receipt': del contract['inherited_lineage']
    if change != 'receipt_hash' and 'inherited_lineage' in contract:
        p = Path(contract['inherited_lineage']['path']); p.write_text(json.dumps(receipt))
        contract['inherited_lineage']['sha256'] = preflight.budget._sha256(p)
    with pytest.raises(ValueError, match=match):
        _validate(path, contract)
