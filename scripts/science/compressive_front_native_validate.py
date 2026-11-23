#!/usr/bin/env python3
"""Run the amended compression contract on the same physical axes as G-HI/20."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from compressive_front_native import ARMS, GAMMA, classify_block, classify_slabs, select_components
from independent_bow_shock import parse_pluto_grid, rh_jump_ratios
from validate_independent_bow_shock import (Atmosphere, GROUP_ATMOSPHERE, _background_on_feature_plane,
                                          _geometry, local_patch, unit)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class StoredGrid:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    x_edges: np.ndarray
    y_edges: np.ndarray
    z_edges: np.ndarray

    @property
    def shape(self):
        return self.z.size, self.y.size, self.x.size

    def subgrid(self, z, y, x):
        axes = tuple((getattr(self,n)[sl], getattr(self,n+'_edges')[sl.start:sl.stop+1])
                     for n,sl in zip(('x','y','z'),(x,y,z)))
        return StoredGrid(*(a[0] for a in axes), *(a[1] for a in axes))


def coords(grid):
    return (grid.z,grid.y,grid.x),tuple(np.diff(getattr(grid,n+'_edges')) for n in ('z','y','x'))


def synthetic(grid, atmosphere, direction, kind):
    direction = unit(direction)
    _,s,h = _geometry(grid,direction,.23)
    d,p = _background_on_feature_plane(grid,atmosphere,s,direction)
    a = np.sqrt(GAMMA*p/d)
    if kind.startswith('shock'):
        m = float(kind.split('_')[1]); jp,jd,_ = rh_jump_ratios(m)
        pd = np.where(s>=0,jp,1.); dd = np.where(s>=0,jd,1.)
        speed = np.where(s>=0,m*a/jd,m*a)
    else:
        width = 3.0 if kind=='broad_wave' else 1.0
        phase = np.tanh(s/(width*h))
        sign = -1.0 if kind=='rarefaction' else 1.0
        pd = np.exp(.15*phase)
        dd = pd**(1/GAMMA)
        speed = -sign*.15/GAMMA*a*phase
        if kind.startswith('contact'):
            pd = np.ones_like(p); dd = np.where(s>=0,int(kind.split('_')[1]),1.)
            if 'converging' not in kind:
                speed = np.zeros_like(p)
        if kind=='static':
            zz,yy,xx = np.meshgrid(grid.z,grid.y,grid.x,indexing='ij')
            d,p = atmosphere.at_radius(np.sqrt(xx*xx+yy*yy+zz*zz))
            dd,pd,speed = 1.,1.,np.zeros_like(p)
    fields = dict(rho=d*dd,prs=p*pd,**{f'vx{i+1}':speed*axis for i,axis in enumerate(direction)})
    return fields,dict(rho=d,prs=p),s/h


def sphere_check(grid):
    z,y,x = np.meshgrid(grid.z,grid.y,grid.x,indexing='ij',sparse=True)
    r = np.sqrt(x*x+y*y+z*z)
    radius = .64*min(grid.x[-1],grid.y[-1],grid.z[-1])
    width = float(min(np.median(np.diff(getattr(grid,n+'_edges'))) for n in ('x','y','z')))
    step = (1-np.tanh((r-radius)/width))/2
    # A radial velocity jump provides local convergence where the swept-up flow slows outward.
    v = 1.2*step/r
    now = dict(prs=1+1.5*step,rho=1+.8*step,vx1=v*x,vx2=v*y,vx3=v*z)
    zero = dict(prs=np.ones_like(r),rho=np.ones_like(r))
    bits,h = classify_block(now,zero,*coords(grid))
    tiled = np.empty_like(bits); widths = {s: np.empty_like(h[s]) for s in (1,2)}
    classify_slabs(now,zero,grid,tiled,widths,7)
    # The two outer derivative planes on physical faces are outside the analysis domain.
    same = bool(np.array_equal(bits,tiled) and all(np.array_equal(h[s][bits!=0],widths[s][bits!=0]) for s in (1,2)))
    labels,n = ndimage.label((bits&1)!=0,ndimage.generate_binary_structure(3,3))
    regions = select_components(labels,n,grid,h[1]); winner = regions.winners[0]
    mask = (labels==winner) if winner else np.zeros_like(bits,dtype=bool)
    extents = [float(np.max(np.abs(a+0*r)[mask],initial=0)) for a in (x,y,z)]
    # On a cardinal symmetry axis a spherical layer should reach both sides and both lateral directions.
    axial_lateral = all(abs(axis-radius) < 4*width for axis in extents)
    return dict(tiled_exact=same,radius_kpc=radius,normal_scale_kpc=width,selected_xyz_extent_kpc=extents,
                winners=regions.winners,passed=bool(same and winner and winner==regions.winners[1] and axial_lateral))


def validate(grid_path, atmospheric_path, out, native_axes=None):
    if native_axes is None:
        grid = parse_pluto_grid(grid_path)
    else:
        with np.load(native_axes, allow_pickle=False) as arrays:
            grid = StoredGrid(**{n: arrays[n] for n in StoredGrid.__dataclass_fields__})
        for n in ('x','y','z'):
            c = getattr(grid,n); e = getattr(grid,n+'_edges')
            if e.shape!=(c.size+1,) or not (np.all(np.diff(c)>0) and np.all(c>e[:-1]) and np.all(c<e[1:])):
                raise ValueError(f'malformed G-HI native coordinates on {n}')
    atmosphere = Atmosphere.read(atmospheric_path)
    if grid.shape!=(1014,960,960):
        raise ValueError('validation requires the G-HI production axes')
    rows=[]
    kinds=('shock_1.1','shock_1.5','shock_3','sound','broad_wave','contact_10','contact_100','contact_100_converging','rarefaction','static')
    for loc,target in [('central',(0.,0.,0.)),('stretched',(45.,-25.,70.))]:
        patch=local_patch(grid,target,cells=31)
        for orientation,normal in [('axial',(0,0,1)),('lateral',(1,0,0)),('diagonal',(1,1,0)),('oblique',(1,-2,3))]:
            for kind in kinds:
                now,initial,dist=synthetic(patch,atmosphere,normal,kind)
                bits,_=classify_block(now,initial,*coords(patch),radial=False)
                for bit,arm in enumerate(ARMS):
                    hit=(bits & (1<<bit))!=0
                    # Exclude patch tangential samples whose upstream/downstream reference is absent.
                    close=float(np.min(np.abs(dist[hit]))) if np.any(hit) else None
                    p95=float(np.percentile(np.abs(dist[hit]),95)) if np.any(hit) else None
                    if kind in ('shock_1.1','broad_wave'):
                        criterion='sensitivity'; passed=None
                    elif kind.startswith('shock') or kind=='sound':
                        criterion='positive'; passed=close is not None and close<=2.
                    else:
                        criterion='negative'; passed=not bool(np.any(hit))
                    rows.append(dict(placement=loc,orientation=orientation,kind=kind,arm=arm,criterion=criterion,
                                     cells=int(hit.sum()),nearest_widths=close,p95_widths=p95,passed=passed))
    sphere=sphere_check(local_patch(grid,(0.,0.,0.),cells=65))
    result=dict(passed=all(row['passed'] is not False for row in rows) and sphere['passed'],sphere=sphere,
                exact_grid_file_sha256=digest(grid_path),environment_sha256=digest(atmospheric_path),
                axis_edge_sha256={n:hashlib.sha256(np.asarray(getattr(grid,n+'_edges'),dtype='<f8').tobytes()).hexdigest() for n in ('x','y','z')},
                required_rows=sum(row['criterion']!='sensitivity' for row in rows),sensitivity_rows=sum(row['criterion']=='sensitivity' for row in rows),
                failures=[row for row in rows if row['passed'] is False])
    if native_axes is not None:
        result['native_axes_npz_sha256'] = digest(native_axes)
        text_grid = parse_pluto_grid(grid_path)
        result['source_representation_difference'] = {}
        result['axis_center_sha256'] = {}
        for n in ('x','y','z'):
            c,e = getattr(grid,n),getattr(grid,n+'_edges')
            tc,te = getattr(text_grid,n),getattr(text_grid,n+'_edges')
            width = np.diff(te)
            ew = np.minimum(np.r_[width[0],width],np.r_[width,width[-1]])
            result['source_representation_difference'][n] = dict(
                max_center_abs_kpc=float(np.max(np.abs(c-tc))),max_edge_abs_kpc=float(np.max(np.abs(e-te))),
                max_center_local_width=float(np.max(np.abs(c-tc)/width)),max_edge_local_width=float(np.max(np.abs(e-te)/ew)))
            result['axis_center_sha256'][n] = hashlib.sha256(np.asarray(c,dtype='<f8').tobytes()).hexdigest()
    out.mkdir(parents=True,exist_ok=True)
    with (out/'synthetic_validation.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    (out/'synthetic_validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--grid',type=Path,required=True)
    ap.add_argument('--native-axes',type=Path);ap.add_argument('--atmosphere',type=Path,default=GROUP_ATMOSPHERE);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();result=validate(a.grid,a.atmosphere,a.output,a.native_axes);print(json.dumps(result));raise SystemExit(int(not result['passed']))
