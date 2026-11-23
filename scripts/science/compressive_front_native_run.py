#!/usr/bin/env python3
"""Bind G-HI/20, extract independent native layers, and project their fixed-cell emission."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

import h5py
import numpy as np
from scipy import ndimage

import build_q032_source_emission as emission
from compressive_front_native import ARMS, classify_slabs, local_masks, select_components
from measure_q031_fluxes import read_grid


PRODUCER_SHA = '4ca1a4f445ae1d65d6a7aa7619ccea7745d545266656875ddfb469487affd31e'
CONTRACT_SHA = 'f2239f3ea557bb08be97beb128ae0f7898aaa744c3d32e51d17dfaae05e519e4'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def digest(path):
    with Path(path).open('rb') as f:
        data=hashlib.sha256()
        for buf in iter(lambda:f.read(8*1024**2),b''):
            data.update(buf)
        return data.hexdigest()


def verify(path, expected):
    path=Path(path)
    before=emission.budget._stat_identity(path)
    if digest(path)!=expected or before!=emission.budget._stat_identity(path):
        raise ValueError(f'file identity changed: {path.name}')
    return before


def bind(previous):
    cp=previous/'input_contract.json';rp=previous/'G-HI_0020'/'completion.json'
    verify(cp,CONTRACT_SHA);verify(rp,PRODUCER_SHA)
    c,old=load_json(cp),load_json(rp)
    if (old['case'],old['snapshot_index'],old['execution_status'])!=('G-HI',20,'completed_GHI20_source_emission_diagnostic'):
        raise ValueError('wrong prior producer')
    receipt=c['native_input_receipt'];verify(receipt['path'],receipt['sha256']);source=load_json(receipt['path'])
    if (source['case'],source['snapshot_index'],source['status'])!=('G-HI',20,'bound_spherical_budget_inputs'):
        raise ValueError('wrong or incomplete native lineage')
    lineage=source['native_preflight']['inherited_lineage']['receipt'];verify(lineage['path'],lineage['sha256'])
    proof=load_json(lineage['path']);chain=proof['snapshots']['analysis_chain']
    if (proof['status']!='passed' or [r['output_index'] for r in chain]!=list(range(51)) or
        source['native_preflight']['semantic_checks']['inherited_parent_source_restart_and_chain']!='passed'):
        raise ValueError('unbound native lineage')
    stable=[]
    for role,r in source['inputs'].items():
        now=verify(r['path'],r['sha256']);stable.append(now)
        for k in ('size_bytes','mtime_ns','ctime_ns','resolved_path','inode'):
            if r[k]!=now[k]:raise ValueError(f'native source identity differs: {role} {k}')
        if role in ('current_h5','initial_h5'):
            idx,epoch=(20,'current') if role=='current_h5' else (0,'initial')
            for k in ('size_bytes','mtime_ns','ctime_ns','resolved_path','inode'):
                if chain[idx][k]!=now[k]:raise ValueError(f'native source ancestry differs: {role} {k}')
            for k in ('time_code','timestep'):
                if source[epoch][k]!=chain[idx][k]:raise ValueError('native timestep ancestry differs')
    for name,r in old['provenance']['analysis_sources'].items():
        stable.append(verify(Path(emission.__file__).parent/name,r['sha256']))
    for r in c['inputs'].values():stable.append(verify(r['path'],r['sha256']))
    for angle,view in c['views'].items():
        for key in ('horizontal','vertical','metadata'):
            r=view[key];stable.append(verify(r['path'],r['sha256']))
        name=f'G-HI_0020_{angle}deg.npz';stable.append(verify(previous/'G-HI_0020'/name,old['files'][name]['sha256']))
    return c,source,old,stable


def native_grid(current,initial,source,validation):
    gpath=Path(source['inputs']['grid_file']['path'])
    for h5,epoch in ((current,'current'),(initial,'initial')):
        name,t,shape=emission.budget._single_timestep(h5,source[epoch]['timestep'],context=epoch)
        if shape!=(1014,960,960) or not math.isclose(t,source[epoch]['time_code'],rel_tol=0,abs_tol=1e-10):
            raise ValueError('snapshot geometry or time differs from production')
        grid=read_grid(h5,shape,grid_file=gpath)
        for n in ('x','y','z'):
            sha=hashlib.sha256(np.asarray(getattr(grid,n+'_edges'),dtype='<f8').tobytes()).hexdigest()
            if sha!=validation['axis_edge_sha256'][n]:raise ValueError('native and validation axes differ')
    return grid


def build_views(c,grid,previous):
    views={}
    for angle_key,rec in c['views'].items():
        angle=int(angle_key)
        u=np.loadtxt(rec['horizontal']['path']); z=np.loadtxt(rec['vertical']['path'])
        edges,operator,covered,geometry=emission.build_projection(grid,angle,u)
        axes=dict(horizontal_axis_kpc=u,horizontal_edges_kpc=edges,z_axis_kpc=grid.z,z_edges_kpc=grid.z_edges)
        name=f'G-HI_0020_{angle}deg.npz'
        with np.load(previous/'G-HI_0020'/name) as before:
            if any(not np.array_equal(before[n],v) for n,v in axes.items()):raise ValueError(f'original sky axes differ at {angle}')
        if not np.allclose(grid.z,z,rtol=emission.native.TEXT_RTOL,atol=1e-10):raise ValueError('native z mismatch')
        views[angle]=SimpleNamespace(operator=operator,axes=axes,maps={},geometry=geometry,covered=covered)
    return views


def stack_views(views,grid,iz,fields):
    for view in views.values():
        for name,field in fields.items():
            if name not in view.maps:
                view.maps[name]=np.zeros((len(grid.z),len(view.axes['horizontal_axis_kpc'])))
            view.maps[name][iz]=emission.project_scalar(view,field,grid)


def mem(temp,tag,shape,dtype):
    return np.memmap(temp/tag,mode='w+',dtype=dtype,shape=shape)


def layers_from_cells(grid,now,zero,temp,views,out,slab):
    shape=now['rho'].shape
    bits=mem(temp,'candidate.u1',shape,'u1'); hn={s:mem(temp,f'width_{s}.f4',shape,'f4') for s in (1,2)}
    classify_slabs(now,zero,grid,bits,hn,slab)
    label=mem(temp,'label.i4',shape,'i4'); layers=mem(temp,'layers.u1',shape,'u1'); structures={}
    for bit,(arm,params) in enumerate(ARMS.items()):
        print(f'COMPONENTS {arm} {stamp()}',flush=True)
        count=ndimage.label((bits & (1<<bit))!=0,structure=ndimage.generate_binary_structure(3,3),output=label)
        regions=select_components(label,count,grid,hn[params[3]])
        structures[arm]=dict(summary=regions.summary,qualifying_or_boundary=regions.records)
        for iz,z in enumerate(grid.z):
            main,other,boundary=local_masks(label[iz],regions,z>=0)
            if bit==0:
                layers[iz]=main.astype('u1') | (other.astype('u1')<<4) | (boundary.astype('u1')<<5)
            else:layers[iz] |= main.astype('u1')<<bit
    write_json(out/'components.json',structures)
    for iz in range(shape[0]):
        m=layers[iz]
        primary=(m&1)!=0
        fields={('front_path_kpc' if bit==0 else f'front_path_{arm}_kpc'):((m&(1<<bit))!=0).astype(float) for bit,arm in enumerate(ARMS)}
        fields.update(other_path_kpc=((m&16)!=0).astype(float),boundary_path_kpc=((m&32)!=0).astype(float),
                      front_resolution_kpc=primary*hn[1][iz].astype(float))
        stack_views(views,grid,iz,fields)
    for view in views.values():
        w=view.maps['front_resolution_kpc'];p=view.maps['front_path_kpc'];np.divide(w,p,out=w,where=p>0)
    return layers,structures


def project_emission(grid,now,zero,layers,views,c):
    native=emission.native
    xraise=native.renderer.load_module(Path(c['inputs']['xraise_py']['path']))
    tables=native.load_tables(Path(c['inputs']['apec_table']['path']),Path(c['inputs']['gaunt_lut']['path']))
    for iz in range(len(grid.z)):
        tracer=now['tr1'][iz].astype(float)
        if not np.isfinite(tracer).all():raise ValueError('nonfinite native tracer')
        cocoon=tracer>1e-3; front=((layers[iz]&1)!=0) & ~cocoon; rest=~(front|cocoon)
        fields={}
        for state,primitives in (('current',now),('initial',zero)):
            rho,prs=(np.asarray(primitives[n][iz:iz+1],dtype=float) for n in ('rho','prs'))
            vals,_,_=native.cell_emissivity(xraise=xraise,tables=tables,rho_code=rho,pressure_code=prs,
                    frequency_hz=c['frequency_hz'],redshift=c['redshift'])
            intensity=vals['retained_linear'][0]*emission.BRIGHTNESS_FACTOR
            for region,mask in (('front',front),('rest',rest),('lobe',cocoon)):
                fields[f'{region}_{state}_brightness']=intensity*mask
        stack_views(views,grid,iz,fields)
        if iz%64==0:print(f'EMISSIVITY {iz}/{len(grid.z)} {stamp()}',flush=True)


def run(previous,validation_file,scratch,out,slab):
    start=stamp();validation=load_json(validation_file)
    if not validation['passed'] or validation['required_rows']!=256:raise ValueError('synthetic contract failed')
    c,source,old,stable=bind(previous)
    print(f'INPUTS_BOUND {stamp()}',flush=True)
    out.mkdir(exist_ok=False,parents=True)
    with h5py.File(source['inputs']['current_h5']['path'],'r') as current,h5py.File(source['inputs']['initial_h5']['path'],'r') as initial:
        grid=native_grid(current,initial,source,validation);views=build_views(c,grid,previous)
        now=current[source['current']['timestep']]['vars'];zero=initial[source['initial']['timestep']]['vars']
        common=dict(case='G-HI',snapshot_index=20,actual_time_myr=source['current']['time_code']/emission.budget.CODE_TIME_PER_MYR,
                    source_contract_sha256=CONTRACT_SHA,source_producer_sha256=PRODUCER_SHA,
                    native_inputs_sha256={k:v['sha256'] for k,v in source['inputs'].items()},
                    selection_contract_sha256=digest(Path(__file__).with_name('ghi20_compressive_front_contract_2026-11-23.md')),
                    implementation_sha256={p.name:digest(p) for p in (Path(__file__),Path(__file__).with_name('compressive_front_native.py'))},
                    validation_sha256=digest(validation_file),started_utc=start,pbs_job_id=__import__('os').environ.get('PBS_JOBID'))
        with TemporaryDirectory(dir=scratch,prefix='ghi20-layers-') as tmp:
            layers,struct=layers_from_cells(grid,now,zero,Path(tmp),views,out,slab)
            geometry=out/'geometry';geometry.mkdir();geo_files={}
            for angle,v in views.items():
                p=geometry/f'G-HI_0020_{angle}deg.npz';np.savez_compressed(p,**v.axes,**v.maps)
                geo_files[p.name]=dict(size_bytes=p.stat().st_size,sha256=digest(p))
            write_json(geometry/'completion.json',dict(**common,files=geo_files,components_sha256=digest(out/'components.json'),
                completed_utc=stamp(),product='native geometry ready for provisional overlay; attribution pending'))
            print(f'GEOMETRY_COMPLETE {stamp()}',flush=True)
            project_emission(grid,now,zero,layers,views,c)
    emission.budget._stable(stable)
    files={};checks={}
    for angle,v in views.items():
        name=f'G-HI_0020_{angle}deg.npz';p=out/name;checks[str(angle)]={}
        with np.load(previous/'G-HI_0020'/name) as retained:
            for state in ('current','initial'):
                parts=sum(v.maps[f'{r}_{state}_brightness'] for r in ('lobe','front','rest'))
                for region,computed in (('whole',parts),('C',v.maps[f'lobe_{state}_brightness'])):
                    reference=retained[f'brightness_{state}_retained_linear_{region}']
                    checks[str(angle)][f'{state}_{region}']=emission.closure(f'{angle}_{state}_{region}',computed,reference)
        np.savez_compressed(p,**v.axes,**v.maps);files[name]=dict(sha256=digest(p),size_bytes=p.stat().st_size)
    write_json(out/'completion.json',dict(**common,completed_utc=stamp(),files=files,closure_against_previous=checks,
                components_sha256=digest(out/'components.json'),producer_qualification=old['scientific_qualification'],
                projection_geometry={str(a):v.geometry for a,v in views.items()}, component_summaries={k:v['summary'] for k,v in struct.items()}))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','validation','scratch','output'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--slab',type=int,default=8);a=ap.parse_args();run(a.previous,a.validation,a.scratch,a.output,a.slab)
