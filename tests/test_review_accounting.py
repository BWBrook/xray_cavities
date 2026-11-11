from __future__ import annotations

import json
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/kunanyi'))
sys.path.insert(0, str(ROOT/'scripts/science'))
import run_review_accounting as runner
import summarize_q031_source_accounting as source_accounting
from test_spherical_budget_inputs import _contract


def _write(path, data):
    path.write_text(json.dumps(data))
    return {'path':str(path.absolute()),'sha256':runner.inputs.budget._sha256(path)}


def _request(tmp_path, *, case='C-LO', indices=(20,)):
    path,contract = _contract(tmp_path/'native')
    contract['case'] = case
    files = contract['files']
    runtime = Path(files['runtime_config']['path'])
    runtime.write_text(runtime.read_text().replace('JET_PWR 1e+45', 'JET_PWR 1e+43'))
    if case.startswith('G-'):
        original = Path(files['environment']['path'])
        renamed = original.with_name('tabulated_cosmo_002031.csv')
        original.rename(renamed)
        files['environment']['path'] = str(renamed)
        config = Path(files['environment_config']['path'])
        config.write_text(config.read_text().replace('002003','002031'))
    environment = Path(files['environment']['path'])
    values = np.loadtxt(environment)
    values[-1,0] *= 1000.
    np.savetxt(environment,values)
    for row in contract['snapshots']:
        if row['index'] not in {0,*indices}:
            continue
        with h5py.File(row['path'],'a') as handle:
            for group in ('cell_coords','node_coords'):
                for axis in 'XYZ':
                    handle[f'{group}/{axis}'][...] *= 100.
    for record in files.values():
        record['sha256'] = runner.inputs.budget._sha256(Path(record['path']))
    witness = Path(contract['evidence']['hashes']['path'])
    witness.write_text('\n'.join(f"{files[role]['sha256']}  {files[role]['path']}" for role in runner.inputs.HISTORICAL_ROLES))
    log = Path(contract['evidence']['production']['path'])
    log.write_text(log.read_text().replace('CASE_ID=C-HI',f'CASE_ID={case}'))
    for record in contract['evidence'].values():
        record['sha256'] = runner.inputs.budget._sha256(Path(record['path']))
    contract_record = _write(path,contract)
    _,report = runner.inputs.validate_contract(path,contract_record['sha256'])
    selected = []
    for index in indices:
        receipt_path = tmp_path/f'input_{index}.json'
        runner.inputs.prepare_receipt(report,index,receipt_path)
        receipt_identity = runner.inputs.stable_hash(receipt_path)
        completed = {'schema_version':1,'status':'snapshot_measurement_completed','case':case,
            'snapshot_index':index,'contract_sha256':contract_record['sha256'],
            'input_receipt':receipt_identity}
        done_record = _write(tmp_path/f'previous_{index}.json',completed)
        selected.append({'index':index,'contract':contract_record,
            'input_receipt':receipt_identity,'previous_completion':done_record})
    request = {'schema':1,'case':case,'snapshots':selected}
    request_path = tmp_path/'request.json'
    identity = _write(request_path,request)
    return request_path,identity['sha256'],request,contract


def _revise_completion(request_path, request, update):
    row=request['snapshots'][0]
    done_path=Path(row['previous_completion']['path'])
    completed=json.loads(done_path.read_text())
    update(completed)
    row['previous_completion']=_write(done_path,completed)
    return _write(request_path,request)['sha256']


@pytest.mark.parametrize('indices,case', [((1,1),'C-HI'),((1,0),'C-HI'),((-1,),'C-HI'),((51,),'C-HI'),((48,),'G-HI')])
def test_request_rejects_duplicate_unsorted_and_excluded_indices(tmp_path,indices,case):
    request={'schema':1,'case':case,'snapshots':[{'index':index} for index in indices]}
    path=tmp_path/'request.json';identity=_write(path,request)
    with pytest.raises(ValueError,match='envelope'):
        runner.validate_request(path,identity['sha256'])


def test_pinned_request_hash_is_required_before_any_contract_access(tmp_path):
    path=tmp_path/'request.json';_write(path,{'schema':1,'case':'C-LO','snapshots':[{'index':20}]})
    with pytest.raises(ValueError,match='hash mismatch'):
        runner.validate_request(path,'0'*64)


@pytest.mark.parametrize('change',('status','schema','contract','receipt_sha','receipt_path','receipt_size'))
def test_prior_completion_must_be_completed_and_bind_exact_receipt(tmp_path,change):
    path,_,request,_=_request(tmp_path)
    def update(done):
        if change=='status':done['status']='failed'
        elif change=='schema':done['schema_version']=2
        elif change=='contract':done['contract_sha256']='0'*64
        elif change=='receipt_sha':done['input_receipt']['sha256']='0'*64
        elif change=='receipt_path':done['input_receipt']['path']=str(tmp_path/'other_receipt.json')
        else:done['input_receipt']['size_bytes']+=1
    digest=_revise_completion(path,request,update)
    with pytest.raises(ValueError,match='prior completion'):
        runner.validate_request(path,digest)


def test_changed_receipt_cannot_rebind_another_snapshot(tmp_path):
    path,_,request,_=_request(tmp_path)
    row=request['snapshots'][0];receipt_path=Path(row['input_receipt']['path'])
    receipt=json.loads(receipt_path.read_text());receipt['snapshot_index']=21
    row['input_receipt']=_write(receipt_path,receipt)
    digest=_revise_completion(path,request,lambda done:done.update(input_receipt=runner.inputs.stable_hash(receipt_path)))
    with pytest.raises(ValueError,match='existing receipt differs'):
        runner.validate_request(path,digest)


@pytest.mark.parametrize('change',('source','native'))
def test_changed_bound_source_or_input_fails_preflight(tmp_path,change):
    path,digest,_,contract=_request(tmp_path)
    target=Path(contract['files']['initialization_source']['path']) if change=='source' else Path(contract['snapshots'][20]['path'])
    with target.open('ab') as handle:handle.write(b'changed')
    with pytest.raises(ValueError,match='hash mismatch|historically bound input'):
        runner.validate_request(path,digest)


def test_serial_fixed_extraction_uses_exact_selected_case_ages_and_no_overwrite(tmp_path,monkeypatch):
    path,digest,_,_=_request(tmp_path,indices=(20,21))
    actual=runner.fixed.extract_snapshot;calls=[]
    def observe(**kwargs):
        calls.append((kwargs['case'],kwargs['snapshot_index'],kwargs['inset_kpc'],kwargs['potential_zero_shift_cm2_s2']))
        return actual(**kwargs)
    monkeypatch.setattr(runner.fixed,'extract_snapshot',observe)
    output=tmp_path/'result';result=runner.run(path,digest,'fixed',output)
    assert calls==[('C-LO',20,50.,1.e15),('C-LO',21,50.,1.e15)]
    assert result['indices']==[20,21]
    assert result['scientifically_qualified'] is False
    assert len(result['products'])==2
    for index in (20,21):
        payload=json.loads((output/f'snapshot_{index:04d}.json').read_text())
        assert payload['regions']['fixed_inset_box']['partitions']['all']['cell_count']==27
        assert payload['actual_time_myr']==pytest.approx(index)
        assert payload['provenance']['mode']=='bound_input_receipt'
    with pytest.raises(ValueError,match='overwrite'):
        runner.run(path,digest,'fixed',output)
    assert len(calls)==2


@pytest.mark.parametrize('change',('source','native','request','receipt'))
def test_mutation_during_extraction_prevents_request_completion(tmp_path,monkeypatch,change):
    path,digest,request,contract=_request(tmp_path)
    dummy_source=tmp_path/'runner_source.py';dummy_source.write_text('synthetic source identity\n')
    monkeypatch.setattr(runner,'__file__',str(dummy_source))
    actual=runner.fixed.extract_snapshot
    target={'source':dummy_source,'native':Path(contract['snapshots'][20]['path']),
            'request':path,'receipt':Path(request['snapshots'][0]['input_receipt']['path'])}[change]
    def mutate(**kwargs):
        result=actual(**kwargs)
        with target.open('ab') as handle:handle.write(b' ')
        return result
    monkeypatch.setattr(runner.fixed,'extract_snapshot',mutate)
    output=tmp_path/'result'
    with pytest.raises(ValueError,match='mutated'):
        runner.run(path,digest,'fixed',output)
    assert (output/'snapshot_0020.json').exists()
    assert not (output/'completion.json').exists()


def test_flux_smoke_passes_only_bound_glo_zero_and_one_to_existing_flux_route(tmp_path,monkeypatch):
    path,digest,_,contract=_request(tmp_path,case='G-LO',indices=(0,1))
    calls=[]
    def measure(**kwargs):
        calls.append(kwargs)
        assert kwargs['case']=='G-LO'
        links=sorted(kwargs['outputs_dirs'][0].iterdir())
        assert [p.name for p in links]==['data.0000.flt.h5','data.0001.flt.h5']
        assert all(p.is_symlink() and p.resolve()==Path(contract['snapshots'][index]['path']) for index,p in enumerate(links))
        assert kwargs['problem_source_dir']==Path(contract['source_root'])
        assert kwargs['environment_path'].name=='tabulated_cosmo_002031.csv'
        kwargs['output_dir'].mkdir()
        (kwargs['output_dir']/'provenance.json').write_text('{}')
        return {}
    def summarize(input_dir,output_dir):
        assert input_dir.name=='flux';output_dir.mkdir()
        (output_dir/'receipt.json').write_text('{"status":"synthetic"}')
    monkeypatch.setattr(runner.flux,'run_analysis',measure)
    monkeypatch.setattr(source_accounting,'run',summarize)
    output=tmp_path/'result';result=runner.run(path,digest,'flux',output)
    assert len(calls)==1 and result['indices']==[0,1]
    assert (output/'source_accounting/receipt.json').exists()
    assert result['scientifically_qualified'] is False
