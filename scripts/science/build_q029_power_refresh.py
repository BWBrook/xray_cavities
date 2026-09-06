#!/usr/bin/env python3
"""Join accepted X-ray enthalpies to unchanged, geometry-verified cavity clocks."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from build_four_case_cavity_age_method_comparison import (
    AGE_METHODS, SECONDS_PER_MYR, build_cavity_powers, build_method_summary,
)

ASSETS = Path('docs/science/assets')
Q029 = ASSETS / 'q029_binary_native_refresh_2026-09-06'
OLD = ASSETS / 'four_case_scientific_synthesis_2026-08-26'


def read(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def key(row, side=False):
    return (row['case'], int(row['snapshot_index']), row['view'], *((row['side'],) if side else ()))


def indexed(rows, side=False):
    out = {key(r, side): r for r in rows}
    if len(out) != len(rows):
        raise ValueError('duplicate cavity rows')
    return out


def close(a, b, label):
    a, b = float(a), float(b)
    if not math.isfinite(a) or not math.isfinite(b) or not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError(f'{label}: {a} differs from {b}')


def refreshed_geometry(old, observer):
    obs = indexed(observer, True)
    previous = indexed(old, True)
    if set(obs) != set(previous):
        raise ValueError('observer/clock geometry keys differ')
    output = []
    for k, row in previous.items():
        x = obs[k]
        for a, b in [('volume_kpc3','volume_kpc3'), ('projected_cavity_radius_kpc','centroid_radius_kpc'), ('actual_time_myr','actual_time_myr')]:
            close(row[a], x[b], f'{k}/{a}')
        output.append(dict(row, pV_erg=float(x['enthalpy_erg']) / 2.5,
                           pressure_dyn_cm2=x['pressure_dyn_cm2'],
                           pressure_role='xray_deprojected_ellipsoid_volume_average'))
    return output


def add_factorization(powers, matched):
    match = indexed(matched)
    for row in powers:
        m = match[key(row)]
        scale = 1.0 if row['cavity_energy_model'] == '2.5pV' else 1.6
        close(row['cavity_energy_erg'], float(m['observer_enthalpy_erg'])*scale, 'accepted total enthalpy')
        close(float(row['known_bipolar_power_erg_s'])*float(row['actual_time_myr'])*SECONDS_PER_MYR,
              m['injected_energy_erg'], 'injection and true clock')
        row['pressure_role'] = 'xray_deprojected_ellipsoid_volume_average'
        row['clock_atmosphere_role'] = 'retained_initial_atmosphere_for_sound_buoyant_refill'
        row['effective_bipolar_age_myr'] = ''
        row['clock_factor'] = ''
        row['factorization_relative_error'] = ''
        row['physical_proxy_factor'] = scale*float(m['native_lobe_enthalpy_erg'])/float(m['injected_energy_erg'])
        row['measurement_factor'] = float(m['ratio_to_native_lobe_enthalpy'])
        if row['inferred_cavity_power_erg_s'] != '':
            t_eff = float(row['cavity_energy_erg'])/float(row['inferred_cavity_power_erg_s'])/SECONDS_PER_MYR
            row['effective_bipolar_age_myr'] = t_eff
            row['clock_factor'] = float(row['actual_time_myr'])/t_eff
            fact = row['physical_proxy_factor']*row['measurement_factor']*row['clock_factor']
            direct = float(row['inferred_to_known_power_ratio'])
            close(fact, direct, 'three-factor power identity')
            row['factorization_relative_error'] = abs(fact/direct-1)
    return powers


def write(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def build(output):
    join=Q029/'accepted_refresh/primary_join'
    sources=[OLD/'xray_cavity_age_geometry.csv', OLD/'age_method_comparison.csv',
             join/'xray_cavity_enthalpy_selected_age.csv',join/'matched_native_xray_energetics.csv']
    geometry,ages,observer,matched=map(read,sources)
    observer=[r for r in observer if r['volume_depth_assumption']=='geometric_depth' and r['pressure_method']=='ellipsoid_volume_average' and r['energy_model']=='2.5pV']
    matched=[r for r in matched if r['volume_depth_assumption']=='geometric_depth' and r['pressure_method']=='ellipsoid_volume_average' and r['energy_model']=='2.5pV']
    if len(observer)!=74 or len(matched)!=37 or len(ages)!=37*7:
        raise ValueError('accepted observer/age coverage drift')
    if {(*key(a),a['age_method']) for a in ages} != {(*key(m),method) for m in matched for method in AGE_METHODS}:
        raise ValueError('age methods not aligned to accepted observer keys')
    updated=refreshed_geometry(geometry,observer)
    powers=add_factorization(build_cavity_powers(updated,ages),matched)
    summary=build_method_summary(ages,powers)
    output.mkdir(parents=True,exist_ok=False)
    write(output/'cavity_power_method_comparison.csv',powers)
    write(output/'age_power_method_summary.csv',summary)
    metadata={'status':'accepted_xray_enthalpies_with_geometry_verified_retained_clocks',
              'geometry_side_rows_verified':74,'valid_observer_views':37,'age_rows':len(ages),'power_rows':len(powers),
              'observer_change_from_old_power_tables':'replace tracer-shell pressure proxy with accepted X-ray-deprojected pressure',
              'clock_convention':'unchanged side ages; side-based power=sum(H_side/t_side); common true/spectral age otherwise',
              'effective_age_definition':'H_total / sum(H_side/t_side) for side clocks; common age otherwise',
              'age_summary_definition':'arithmetic mean of side ages, distinct from effective age in power factorization',
              'max_factorization_relative_error':max(r['factorization_relative_error'] for r in powers if r['factorization_relative_error']!=''),
              'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (output/'power_refresh_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-root',type=Path,default=Q029/'power_refresh')
    build(p.parse_args().output_root)
