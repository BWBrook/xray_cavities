#!/usr/bin/env python3
"""Verify sealed native geometry and tabulate the competing 3-D components."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def summarize(archive, output):
    geometry = archive/'geometry'
    receipt = json.loads((geometry/'completion.json').read_text())
    components_path = archive/'components.json'
    if digest(components_path) != receipt['components_sha256']:
        raise ValueError('component receipt mismatch')
    profiles = json.loads(components_path.read_text())
    if set(profiles) != {'primary','loose','tight','wide'}:
        raise ValueError('component inventory is incomplete')
    output.mkdir(exist_ok=True, parents=True)
    (output/'components.json.gz').write_bytes(gzip.compress(components_path.read_bytes(),mtime=0))
    (output/'geometry_receipt.json').write_bytes((geometry/'completion.json').read_bytes())
    selections = []
    for arm,record in profiles.items():
        meta = record['summary']
        regions = {row['component']:row for row in record['qualifying_or_boundary'] if not row['boundary']}
        for side,name in enumerate(('negative_z','positive_z')):
            chosen = meta['winners_negative_positive'][side]
            ranked = sorted(regions.values(), key=lambda row:(-row['area_negative_positive_kpc2'][side],row['component']))
            weights = [r['area_negative_positive_kpc2'][side] for r in ranked]
            if chosen != (ranked[0]['component'] if sum(weights)>0 else 0):
                raise ValueError('published component rank disagrees with area weights')
            row = dict(arm=arm,side=name,candidate_cells=meta['candidate_cells'],component_count=meta['components'],
                       qualifying_components=meta['qualifying_components'],boundary_components=meta['boundary_components'],
                       selected_component=chosen)
            if chosen:
                winner = regions[chosen]
                row.update(selected_cells_entire_component=winner['cell_count'],selected_area_weight_kpc2=weights[0],
                           selected_area_weight_fraction=weights[0]/sum(weights))
                for axis, (low,high) in zip('zyx',winner['bounds_zyx_kpc']):
                    row[f'extent_{axis}_min_kpc'] = low; row[f'extent_{axis}_max_kpc'] = high
            selections.append(row)
    write_csv(output/'native_selected_components.csv',selections)
    views = []
    for angle in (0,45,90):
        name = f'G-HI_0020_{angle}deg.npz'; path = geometry/name
        if digest(path)!=receipt['files'][name]['sha256'] or path.stat().st_size!=receipt['files'][name]['size_bytes']:
            raise ValueError(f'projection digest mismatch at {angle}')
        with np.load(path, allow_pickle=False) as data:
            area = np.outer(np.diff(data['z_edges_kpc']),np.diff(data['horizontal_edges_kpc']))
            for arm in ('primary','loose','tight','wide','other','boundary'):
                key = {'primary':'front_path_kpc','other':'other_path_kpc','boundary':'boundary_path_kpc'}.get(arm,f'front_path_{arm}_kpc')
                length = data[key]
                if not np.isfinite(length).all() or np.min(length)<0: raise ValueError('invalid native path')
                row = dict(view_deg=angle,selection=arm,projected_volume_kpc3=float(np.sum(area*length)),
                           projected_area_kpc2=float(np.sum(area[length>0])),pixels_with_support=int(np.count_nonzero(length)),
                           max_los_path_kpc=float(np.max(length)),mean_native_width_weighted_by_volume_kpc=None)
                if arm=='primary' and row['projected_volume_kpc3']>0:
                    if not np.array_equal(length>0,data['front_resolution_kpc']>0): raise ValueError('unmatched resolution support')
                    row['mean_native_width_weighted_by_volume_kpc']=float(np.sum(area*length*data['front_resolution_kpc'])/row['projected_volume_kpc3'])
                views.append(row)
    write_csv(output/'native_projection_totals.csv',views)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();summarize(args.archive,args.output)
