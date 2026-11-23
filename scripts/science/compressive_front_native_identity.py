#!/usr/bin/env python3
"""Replay both original G-HI identity gates and record any node-local mount-number difference."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
import os
import h5py
import numpy as np
from pathlib import Path

import build_q032_source_emission as source


def audit(previous, output, axes_path=None):
    contract_path=previous/'input_contract.json'
    expected='f2239f3ea557bb08be97beb128ae0f7898aaa744c3d32e51d17dfaae05e519e4'
    source.checked_compact({'path':str(contract_path),'sha256':expected})
    contract=json.loads(contract_path.read_text());binding=contract['native_input_receipt']
    source.checked_compact(binding);receipt=json.loads(Path(binding['path']).read_text())
    proof=receipt['native_preflight']['inherited_lineage']['receipt'];source.checked_compact(proof)
    lineage=json.loads(Path(proof['path']).read_text())
    if (lineage['schema_version']!=1 or lineage['status']!='passed'
            or lineage['lineage']!='accepted failed-run parent build/source plus validated 10 Myr home continuation'
            or [r['output_index'] for r in lineage['snapshots']['analysis_chain']]!=list(range(51))):
        raise ValueError('original source or history failed')
    paths={key:Path(r['path']) for key,r in receipt['inputs'].items()}
    inventory={}
    for role,epoch,idx in (('current_h5','current',20),('initial_h5','initial',0)):
        archived=receipt['inputs'][role];chain=lineage['snapshots']['analysis_chain'][idx]
        now=source.budget._stat_identity(paths[role])
        diff=[k for k,v in now.items() if archived.get(k)!=v or chain.get(k)!=v]
        matches=all(chain[k]==receipt[epoch][k] for k in ('time_code','timestep'))
        if set(diff)-{'device'} or not matches:raise ValueError(f'native identity differs: {role}, {diff}')
        inventory[role]=dict(archive_device=archived['device'],chain_device=chain['device'],worker_device=now['device'],
                              differing_stat_keys=diff,matching_timestep=matches,sha256=archived['sha256'])
    source.budget.bind_inputs(paths,Path(binding['path']))
    try:
        source.bind_inherited_lineage(receipt)
        historical='pass'
    except ValueError as exc:
        if 'differs from inherited lineage:' not in str(exc) or not any(r['differing_stat_keys'] for r in inventory.values()):raise
        historical='rejected by original device equality on this mount'
    result=dict(pbs_job=os.environ.get('PBS_JOBID'),checked_utc=datetime.now(timezone.utc).isoformat(),
                worker_hostname=os.uname().nodename,original_budget_gate='pass',original_inherited_lineage_gate=historical,
                native=inventory,native_receipt_sha256=binding['sha256'],lineage_certificate_sha256=proof['sha256'],
                source_sha256={Path(p).name:source.budget._sha256(Path(p)) for p in (source.__file__,source.budget.__file__)})
    if axes_path is not None:
        geometry={}
        for role,epoch in (('current_h5','current'),('initial_h5','initial')):
            with h5py.File(paths[role],'r') as native:
                _,_,shape=source.budget._single_timestep(native,receipt[epoch]['timestep'],context=epoch)
                grid=source.read_grid(native,shape,grid_file=paths['grid_file'])
                for axis in ('x','y','z','x_edges','y_edges','z_edges'):
                    values=np.asarray(getattr(grid,axis),dtype='<f8')
                    if epoch=='current':
                        geometry[axis]=values
                    elif not np.array_equal(geometry[axis],values):
                        raise ValueError(f'native grids differ on {axis}')
        np.savez_compressed(axes_path,**geometry)
        result['native_axes_npz_sha256']=source.budget._sha256(axes_path)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--previous',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--axes',type=Path)
    args=parser.parse_args();audit(args.previous,args.output,args.axes)
