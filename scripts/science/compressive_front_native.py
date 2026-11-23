#!/usr/bin/env python3
"""Outward compressive layers in physical coordinates on a stretched Cartesian grid."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


ARMS = {'primary': (.045, .025, .015, 1), 'loose': (.020, .010, .0075, 1),
        'tight': (.080, .040, .030, 1), 'wide': (.045, .025, .015, 2)}
GAMMA = 5 / 3


def derivative(values, axis, centers, step):
    """Three-point unequal-spacing derivative, evaluating only cells with both neighbours."""
    result = np.zeros_like(values)
    arr = np.moveaxis(values, axis, 0)
    left = (centers[step:-step] - centers[:-2*step])[:, None, None]
    right = (centers[2*step:] - centers[step:-step])[:, None, None]
    target = np.moveaxis(result, axis, 0)
    target[step:-step] = (((arr[step:-step] - arr[:-2*step]) * (right / left)
                            + (arr[2*step:] - arr[step:-step]) * (left / right)) / (left + right))
    return result


def classify_block(now, initial, coords, widths, *, radial=True):
    """Return bit mask and physical widths for both stencils on a z-y-x block with ≥2 halo cells."""
    for fields, names in ((now, ('rho', 'prs', 'vx1', 'vx2', 'vx3')), (initial, ('rho', 'prs'))):
        for name in names:
            if not np.isfinite(fields[name]).all() or (name in ('rho', 'prs') and np.min(fields[name]) <= 0):
                raise ValueError(f'invalid native {name}')
    pressure = np.log(now['prs'] / initial['prs'])
    density = np.log(now['rho'] / initial['rho'])
    sound = np.sqrt(GAMMA * now['prs'] / now['rho'])
    axes = (coords[0][:, None, None], coords[1][None, :, None], coords[2][None, None, :])
    span = (widths[0][:, None, None], widths[1][None, :, None], widths[2][None, None, :])
    nonnozzle = sum(a*a for a in axes) > .75**2 if radial else True
    bits = np.zeros(pressure.shape, dtype='u1')
    for step in (1, 2):
        gradients = [derivative(pressure, k, c, step) for k,c in enumerate(coords)]
        length = np.sqrt(sum(g*g for g in gradients))
        normal = [np.divide(g, length, out=g, where=length>0) for g in gradients]
        inv_h = np.sqrt(sum((n/s)**2 for n,s in zip(normal,span)))
        h = np.divide(1., inv_h, out=np.zeros_like(inv_h), where=inv_h>0)
        if step == 1:
            primary_h = h.astype('f4')
        compression_p = 2*h*length
        compression_rho = 2*h*sum(n*derivative(density, k, c, step) for k,(n,c) in enumerate(zip(normal,coords)))
        convergence = -2*h*sum(derivative(now[f'vx{3-k}'], k, c, step) for k,c in enumerate(coords))/sound
        outward = (sum(n*a for n,a in zip(normal,axes)) < 0) & nonnozzle if radial else True
        for bit, (p_cut,d_cut,v_cut,arm_step) in enumerate(ARMS.values()):
            if arm_step == step:
                good = (compression_p>p_cut) & (compression_rho>d_cut) & (convergence>v_cut) & outward
                bits |= np.left_shift(good.astype('u1'),bit)
    for axis in range(3):
        ends = np.moveaxis(bits, axis, 0)
        ends[:2] = 0
        ends[-2:] = 0
    return bits,{1: primary_h, 2: h.astype('f4')}


def classify_slabs(current, initial, grid, bits, h_normal, slab):
    shape = bits.shape
    coords = (grid.z,grid.y,grid.x)
    widths = tuple(np.diff(edges) for edges in (grid.z_edges,grid.y_edges,grid.x_edges))
    for start in range(0,shape[0],slab):
        end = min(start+slab,shape[0])
        lo,hi = max(0,start-2),min(shape[0],end+2)
        cut = slice(lo,hi)
        now = {n: np.asarray(current[n][cut], dtype='f8') for n in ('rho','prs','vx1','vx2','vx3')}
        zero = {n: np.asarray(initial[n][cut], dtype='f8') for n in ('rho','prs')}
        masks,h = classify_block(now,zero,(grid.z[cut],*coords[1:]),(widths[0][cut],*widths[1:]))
        keep = slice(start-lo,end-lo)
        bits[start:end] = masks[keep]
        for step in (1, 2):
            h_normal[step][start:end] = h[step][keep]
        if start % (slab*8) == 0:
            print(f'CELL_LAYER {start}/{shape[0]}', flush=True)


@dataclass
class Components:
    winners: tuple[int, int]
    eligible: np.ndarray
    boundary: np.ndarray
    records: list
    summary: dict


def select_components(labels, count, grid, h_normal):
    shape = labels.shape
    extents = ndimage.find_objects(labels, max_label=count) if count else []
    boundary = np.zeros(count+1, dtype=bool)
    for axis in range(3):
        planes = np.moveaxis(labels,axis,0)
        for edge in (2,-3):
            boundary[np.unique(planes[edge])] = True
    boundary[0] = False
    area = np.zeros((2,count+1),float)
    cells = np.zeros(count+1,'i8')
    dx,dy,dz = (np.diff(getattr(grid,f'{name}_edges')) for name in ('x','y','z'))
    faces = dy[:, None]*dx[None,:]
    for iz,z in enumerate(grid.z):
        y,x = np.nonzero(labels[iz])
        ids = labels[iz,y,x]
        if not len(ids):
            continue
        length = h_normal[iz,y,x].astype(float)
        if np.any(length<=0) or not np.isfinite(length).all():
            raise ValueError('nonpositive local width for component ranking')
        cells += np.bincount(ids,minlength=count+1)
        area[int(z>=0)] += np.bincount(ids,weights=faces[y,x]*dz[iz]/length,minlength=count+1)
    eligible = np.zeros(count+1,dtype=bool)
    records = []
    for cid,slices in enumerate(extents,start=1):
        if slices is None:
            continue
        bounds = [[float(edge[s.start]),float(edge[s.stop])] for s,edge in
                  zip(slices,(grid.z_edges,grid.y_edges,grid.x_edges))]
        spans = [high-low for low,high in bounds]
        eligible[cid] = not boundary[cid] and cells[cid]>=32 and sum(s>=2.0 for s in spans)>=2
        if eligible[cid] or (boundary[cid] and cells[cid]>=32):
            records.append(dict(component=cid,cell_count=int(cells[cid]),boundary=bool(boundary[cid]),
                                bounds_zyx_kpc=bounds,area_negative_positive_kpc2=area[:,cid].tolist()))
    winners = []
    for side in (0,1):
        weights = np.where(eligible,area[side],0.)
        winner = int(np.argmax(weights)) if weights.max(initial=0)>0 else 0
        winners.append(winner)
    summary = dict(components=count,candidate_cells=int(cells.sum()),qualifying_components=int(eligible.sum()),
                   boundary_components=int(boundary.sum()),boundary_cells=int(cells[boundary].sum()),
                   unqualified_detached_cells=int(cells[~(eligible|boundary)].sum()),
                   winners_negative_positive=winners,ranking_width='primary local normal; wide arm uses its own width')
    return Components(tuple(winners),eligible,boundary,records,summary)


def local_masks(labels, comp, positive):
    picked = comp.winners[int(positive)]
    main = labels==picked if picked else np.zeros(labels.shape,dtype=bool)
    return main, comp.eligible[labels] & ~main, comp.boundary[labels]
