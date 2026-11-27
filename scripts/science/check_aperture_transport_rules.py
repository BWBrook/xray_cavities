"""Review of the aperture-transport accounts (BND-17) from Codex's receipts.

This is accounting on the published endpoint receipts and stock tables, not
a second flux measurement. For each annual interval the receipts hold the
outward flux at both ends on the earlier radius a and the later radius b,
and the stored energy change between the two radii at both ends. That is
enough to write two ordinary fixed-volume balances per interval:

    earlier radius:  [S1(a) - S0(a)] + dt/2 [F0(a) + F1(a)] - delivery
    later radius:    [S1(b) - S0(b)] + dt/2 [F0(b) + F1(b)] - delivery

The registered rule is their mean. Here each is closed on its own and its
residual is compared with the whole-grid residual of the same interval. The
script also totals the flux on each snapshot's own surface, splits the
transport into the C-LO shell by component, and replays the jump counts of
the candidate fronts (NAT-03). exterior.csv compares the energy stored
between each aperture and the fixed inset box (an independent stock) with
the net left outside by each transport account, at ages where the sphere
lies inside that box. With --slab-archive (the retained turn-34
projections) it also places each axial front against the farthest
tracer-bearing gas on sightlines through the jet axis.

Tables go to docs/science/assets/aperture_transport_review_2026-11-27.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'docs/science/assets'
TRANSPORT = ASSETS / 'aperture_transport_2026-11-26'
PARTITION = ASSETS / 'four_case_energy_partition_2026-11-26'
SHOCKS = ASSETS / 'four_case_shock_partition_2026-11-26'
OUT = ASSETS / 'aperture_transport_review_2026-11-27'
CASES = ('C-HI', 'C-LO', 'G-HI', 'G-LO')
APERTURES = ('R100', 'R300')
MYR = 3.15576e13
BOX_HALF_WIDTH_KPC = 149.72422790527344
PARTS = {'thermal_advective': 'thermal_advective_flux_outward_erg_s', 'pressure_work': 'pressure_work_outward_erg_s',
         'kinetic': 'kinetic_flux_outward_erg_s', 'gravitational': 'gravitational_flux_outward_erg_s',
         'total': 'total_energy_flux_outward_erg_s', 'mass': 'mass_flux_outward_g_s'}
STOCKS = {'thermal': 'thermal_erg', 'kinetic': 'kinetic_erg', 'gravitational': 'gravitational_erg', 'total': 'total_energy_erg', 'mass': 'mass_g'}
COLUMNS = {'thermal': 'thermal_delta_erg', 'kinetic': 'kinetic_delta_erg', 'gravitational': 'gravitational_delta_erg',
           'total': 'total_delta_erg', 'mass': 'mass_delta_g'}


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def load(case):
    with zipfile.ZipFile(TRANSPORT / f'endpoints_{case}.zip') as archive:
        records = [json.loads(archive.read(name)) for name in sorted(archive.namelist())]
    return {record['identity']['index']: record for record in records}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slab-archive', type=Path, help='private_archive/turn34_four_case_slabs')
    parser.add_argument('--pilot-projection', type=Path, help='G-HI/20 projections.npz from the slab pilot')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    stock = {(r['case'], int(r['snapshot_index']), r['aperture']): r for r in read(PARTITION / 'sphere_components.csv') if r['region'] == 'all'}
    published = {(r['case'], int(r['end_index']), r['aperture']): r for r in read(TRANSPORT / 'tables/primary_balances.csv')
                 if (r['face_method'], r['integration_rule']) == ('centered_primitives', 'symmetric_fixed')}
    box = {(r['case'], int(r['snapshot_index'])): r for r in read(PARTITION / 'box_components.csv')
           if (r['aperture'], r['region']) == ('fixed_inset_box', 'all')}
    rules, shell, calibration, exterior = [], [], [], []

    for case in CASES:
        records = load(case)
        last = max(records)
        totals = {aperture: {} for aperture in APERTURES}
        for aperture in APERTURES:
            run = {key: 0. for key in (
                'delivery', 'source', 'grid_residual', 'earlier_stock', 'later_stock',
                *(f'{rule}_{part}' for rule in ('earlier', 'later', 'own_surface') for part in PARTS),
                *(f'{half}_{part}' for half in ('ahead_at_start', 'behind_at_end') for part in STOCKS))}
            complete = True
            for index in range(1, last + 1):
                theirs = published[case, index, aperture]
                before, after = (records[i]['measurement']['apertures'][aperture] for i in (index - 1, index))
                dt = (records[index]['identity']['actual_age_myr'] - records[index - 1]['identity']['actual_age_myr']) * MYR
                flux = lambda record, which, part: record['surfaces'][which]['flux']['centered_primitives']['total'][PARTS[part]]
                ahead, behind = before['sweeps']['current_to_next'], after['sweeps']['previous_to_current']
                level = lambda i, part: float(stock[case, i, aperture][COLUMNS[part]])
                complete &= all(after['surfaces'][w]['sphere_fully_inside_domain'] for w in ('previous', 'current')) and \
                    before['surfaces']['next']['sphere_fully_inside_domain']
                delivery = float(theirs['delivered_gas_erg'])
                source = delivery + float(theirs['injector_potential_erg']) + float(theirs['maintained_stock_change_erg'])
                run['delivery'] += delivery
                run['source'] += source
                run['grid_residual'] += float(theirs['archived_grid_residual_erg'])
                run['earlier_stock'] += level(index, 'total') - behind['total_energy_erg'] - level(index - 1, 'total')
                run['later_stock'] += level(index, 'total') - level(index - 1, 'total') - ahead['total_energy_erg']
                for part in PARTS:
                    run[f'earlier_{part}'] += dt / 2 * (flux(before, 'current', part) + flux(after, 'previous', part))
                    run[f'later_{part}'] += dt / 2 * (flux(before, 'next', part) + flux(after, 'current', part))
                    run[f'own_surface_{part}'] += dt / 2 * (flux(before, 'current', part) + flux(after, 'current', part))
                for part, key in STOCKS.items():
                    run[f'ahead_at_start_{part}'] += ahead[key]
                    run[f'behind_at_end_{part}'] += behind[key]
                membership = (run['ahead_at_start_total'] + run['behind_at_end_total']) / 2
                transport = (run['earlier_total'] + run['later_total']) / 2
                residual = level(index, 'total') - membership + transport - run['source']
                calibration.append({
                    'case': case, 'end_index': index, 'aperture': aperture,
                    'stock': np.isclose(level(index, 'total'), float(theirs['cumulative_stock_change_erg']), rtol=1e-9),
                    'membership': np.isclose(membership, float(theirs['cumulative_membership_correction_erg']), rtol=1e-9),
                    'transport': np.isclose(transport, float(theirs['cumulative_total_energy_outward_erg']), rtol=1e-9),
                    'residual': np.isclose(residual, float(theirs['cumulative_aperture_residual_erg']), rtol=1e-7,
                                           atol=1e-9 * run['delivery'])})
                d = run['delivery']
                state = {'complete': complete, 'age': records[index]['identity']['actual_age_myr'],
                         'radius': after['surfaces']['current']['radius_kpc'], **run,
                         'specific_thermal': flux(after, 'current', 'thermal_advective') / flux(after, 'current', 'mass') if flux(after, 'current', 'mass') else float('nan'),
                         **{f'stock_{part}': level(index, part) for part in COLUMNS}}
                totals[aperture][index] = state
                if complete and state['radius'] < BOX_HALF_WIDTH_KPC:
                    outside = float(box[case, index]['total_delta_erg']) - level(index, 'total')
                    exterior.append({
                        'case': case, 'end_index': index, 'actual_age_myr': state['age'], 'aperture': aperture, 'radius_kpc': state['radius'],
                        'stored_between_aperture_and_inset_box_over_delivery': outside / d,
                        **{f'{part}_between_aperture_and_inset_box_over_delivery': (float(box[case, index][COLUMNS[part]]) - level(index, part)) / d
                           for part in ('thermal', 'kinetic', 'gravitational')},
                        'later_radius_outward_minus_stored_ahead_over_delivery': (run['later_total'] - run['ahead_at_start_total']) / d,
                        'registered_outward_minus_membership_over_delivery': (transport - membership) / d,
                        'registered_outward_over_delivery': transport / d})
                rules.append({
                    'case': case, 'end_index': index, 'actual_age_myr': state['age'], 'aperture': aperture,
                    'radius_kpc': state['radius'], 'spheres_complete_so_far': complete, 'delivered_gas_erg': d,
                    'stored_over_delivery': level(index, 'total') / d,
                    'grid_residual_over_delivery': run['grid_residual'] / d,
                    'earlier_radius_outward_over_delivery': run['earlier_total'] / d,
                    'earlier_radius_residual_over_delivery': (run['earlier_stock'] + run['earlier_total'] - run['source']) / d,
                    'later_radius_outward_over_delivery': run['later_total'] / d,
                    'later_radius_residual_over_delivery': (run['later_stock'] + run['later_total'] - run['source']) / d,
                    'registered_mean_outward_over_delivery': transport / d,
                    'registered_mean_residual_over_delivery': residual / d,
                    'own_surface_outward_over_delivery': run['own_surface_total'] / d,
                    'stored_ahead_of_surface_at_start_over_delivery': run['ahead_at_start_total'] / d,
                    'stored_between_radii_at_end_over_delivery': run['behind_at_end_total'] / d,
                    'mass_residual_times_surface_potential_over_delivery': '' if not flux(after, 'current', 'mass') else
                        float(theirs['cumulative_mass_change_minus_membership_plus_outward_g']) - float(theirs['cumulative_delivered_mass_g'])})
                row = rules[-1]
                if row['mass_residual_times_surface_potential_over_delivery'] != '':
                    potential = flux(after, 'current', 'gravitational') / flux(after, 'current', 'mass')
                    row['surface_potential_erg_per_g'] = potential
                    row['mass_residual_times_surface_potential_over_delivery'] *= potential / d
                else:
                    row['surface_potential_erg_per_g'] = ''

        for index in range(1, last + 1):
            inner, outer = totals['R300'][index], totals['R100'][index]
            d = inner['delivery']
            net = lambda rule, part='total': (inner[f'{rule}_{part}'] - outer[f'{rule}_{part}'])
            closure = lambda rule: ((outer[f'{rule}_stock'] + outer[f'{rule}_total']) - (inner[f'{rule}_stock'] + inner[f'{rule}_total'])) / d
            mean = lambda part='total': (net('earlier', part) + net('later', part)) / 2
            moved = lambda half, part='total': outer[f'{half}_{part}'] - inner[f'{half}_{part}']
            residual = lambda a, rule: (a[f'{rule}_stock'] + a[f'{rule}_total'] - a['source']) / d
            shell.append({
                'case': case, 'end_index': index, 'actual_age_myr': inner['age'], 'R300_kpc': inner['radius'], 'R100_kpc': outer['radius'],
                'both_complete_so_far': inner['complete'] and outer['complete'],
                'shell_stock_over_delivery': (outer['stock_total'] - inner['stock_total']) / d,
                **{f'shell_{part}_over_delivery': (outer[f'stock_{part}'] - inner[f'stock_{part}']) / d for part in ('thermal', 'kinetic', 'gravitational')},
                'shell_mass_change_g': outer['stock_mass'] - inner['stock_mass'],
                'shell_thermal_gain_per_mass_gain_erg_per_g': (outer['stock_thermal'] - inner['stock_thermal']) / (outer['stock_mass'] - inner['stock_mass'])
                    if outer['stock_mass'] != inner['stock_mass'] else float('nan'),
                'specific_thermal_energy_at_R300_erg_per_g': inner['specific_thermal'], 'specific_thermal_energy_at_R100_erg_per_g': outer['specific_thermal'],
                'net_into_shell_earlier_radii': net('earlier') / d, 'net_into_shell_later_radii': net('later') / d,
                'net_into_shell_registered_mean': mean() / d, 'net_into_shell_own_surfaces': net('own_surface') / d,
                **{f'net_into_shell_{part}': mean(part) / d for part in ('thermal_advective', 'pressure_work', 'kinetic', 'gravitational')},
                'net_mass_into_shell_g': mean('mass'),
                'membership_registered_mean': (moved('ahead_at_start') + moved('behind_at_end')) / 2 / d,
                'membership_start_half': moved('ahead_at_start') / 2 / d, 'membership_end_half': moved('behind_at_end') / 2 / d,
                'closure_earlier_radii': closure('earlier'), 'closure_later_radii': closure('later'),
                'R300_residual_earlier': residual(inner, 'earlier'), 'R300_residual_later': residual(inner, 'later'),
                'R100_residual_earlier': residual(outer, 'earlier'), 'R100_residual_later': residual(outer, 'later'),
                'earlier_minus_later_outward_R300': (inner['earlier_total'] - inner['later_total']) / d,
                'earlier_minus_later_outward_R100': (outer['earlier_total'] - outer['later_total']) / d})

    fronts = []
    selected = {}
    for row in read(SHOCKS / 'downstream_components.csv'):
        if float(row['threshold_factor']) == 1 and row['status'].startswith('quantitative') and row['side'].endswith('_z'):
            selected.setdefault((row['case'], int(row['snapshot_index'])), set()).add(row['side'])
    axial = {(r['case'], int(r['snapshot_index']), r['side']): r for r in read(SHOCKS / 'axial_evidence.csv')}
    number = lambda value: float(value) if value not in ('', 'nan') else float('nan')
    for (case, index), sides in sorted(selected.items()):
        if len(sides) < 2:
            continue
        for side in sorted(sides):
            r = axial[case, index, side]
            pressure, density = number(r['pressure_jump_ratio']), number(r['density_jump_ratio'])
            fronts.append({
                'case': case, 'snapshot_index': index, 'side': side, 'pressure_jump_ratio': pressure, 'density_jump_ratio': density,
                'compressive_in_both': bool(pressure > 1 and density > 1 and r['both_jump_machs_defined'] == 'True'),
                'mach_from_pressure_jump': number(r['mach_rh_pressure']), 'mach_from_density_jump': number(r['mach_rh_density']),
                'mach_from_propagation': number(r['signed_radial_mach']),
                'pressure_ratio_expected_at_propagation_mach': (5 * number(r['signed_radial_mach']) ** 2 - 1) / 4,
                'shock_distance_kpc': number(r['shock_distance_kpc'])})
            projection = args.slab_archive and args.slab_archive / f'native/{case}_{index:04d}/projections.npz'
            if (case, index) == ('G-HI', 20) and args.pilot_projection:
                projection = args.pilot_projection
            if projection and projection.exists():
                with np.load(projection, allow_pickle=False) as data:
                    z, edges, x, path = data['z_axis_kpc'], data['z_edges_kpc'], data['horizontal_axis_kpc'], data['tracer_path_full']
                centre = int(np.argmin(np.abs(x)))
                half = (z < 0) if side == 'negative_z' else (z > 0)
                occupied = half & (path[:, centre - 1:centre + 2] > 0).any(axis=1)
                tip = float(np.abs(z[occupied]).max())
                cell = float(np.abs(np.diff(edges))[np.argmin(np.where(half, np.abs(np.abs(z) - fronts[-1]['shock_distance_kpc']), np.inf))])
                fronts[-1].update({'tracer_tip_on_axis_sightlines_kpc': tip, 'front_minus_tip_kpc': fronts[-1]['shock_distance_kpc'] - tip,
                                   'front_minus_tip_cells': (fronts[-1]['shock_distance_kpc'] - tip) / cell})
            else:
                fronts[-1].update({'tracer_tip_on_axis_sightlines_kpc': '', 'front_minus_tip_kpc': '', 'front_minus_tip_cells': ''})

    for name, table in (('rules.csv', rules), ('shell.csv', shell), ('fronts.csv', fronts), ('exterior.csv', exterior)):
        write(name, table)
    digest = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
    checks = {key: int(sum(bool(r[key]) for r in calibration)) for key in ('stock', 'membership', 'transport', 'residual')}
    bilateral = sorted({(r['case'], r['snapshot_index']) for r in fronts})
    both = [key for key in bilateral if all(r['compressive_in_both'] for r in fronts if (r['case'], r['snapshot_index']) == key)]
    (OUT / 'summary.json').write_text(json.dumps({
        'cumulative_rows_compared_with_primary_balances': len(calibration), 'rows_agreeing': checks,
        'bilateral_selections': len(bilateral), 'with_compressive_pressure_and_density_jumps_on_both_sides': [list(k) for k in both],
        'inputs': {str(p.relative_to(ROOT)): digest(p) for p in (
            *(TRANSPORT / f'endpoints_{c}.zip' for c in CASES), TRANSPORT / 'tables/primary_balances.csv',
            PARTITION / 'sphere_components.csv', SHOCKS / 'axial_evidence.csv', SHOCKS / 'downstream_components.csv')},
        'tables': {name: digest(OUT / name) for name in ('rules.csv', 'shell.csv', 'fronts.csv', 'exterior.csv')}}, indent=2) + '\n')
    print(len(calibration), checks, len(bilateral), both)


if __name__ == '__main__':
    main()
