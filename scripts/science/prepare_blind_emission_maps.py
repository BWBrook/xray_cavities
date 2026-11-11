"""Prepare source-bound sealed native maps for the frozen refit diagnostic."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import h5py
import numpy as np

import build_q032_source_emission as emission
import run_background_refit_blind as blind


BUDGET = emission.budget
NATIVE = emission.native
FREQUENCY_HZ = 2.417990504024e17
REDSHIFT = .05
AXIS_POLICY = 'renderer_auto_nx_horizontal_bins'
RUNTIME_HASHES = {
    'xraise_py': '4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5',
    'apec_table': 'e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3',
    'gaunt_lut': '64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747',
}
SEMANTICS = {'compiled_geometry_eos_units', 'historically_bound_configuration_and_atmosphere',
             'initialization_gamma', 'runtime_case_power_speed_duration'}
DETECTOR_FIELDS = (*blind.AXES,
                   *(f'brightness_current_{convention}_whole' for convention in emission.CONVENTIONS),
                   *(f'deficit_{convention}_A_v{cut}' for convention in emission.CONVENTIONS for cut in emission.CUTS))


def validate_specification(contract, config):
    case, index, kind = contract.get('case'), contract.get('snapshot_index'), contract.get('kind')
    if contract.get('schema_version') != 1:
        raise ValueError('invalid adapter contract schema')
    if any((case, index, angle, kind) not in blind.expected_units(config) for angle in emission.VIEWS):
        raise ValueError('case/index is outside the frozen science/null cohort')
    if (contract.get('frequency_hz') != FREQUENCY_HZ or contract.get('redshift') != REDSHIFT
            or contract.get('sky_axis_policy') != AXIS_POLICY):
        raise ValueError('frequency, redshift or sky-axis convention differs from development')
    if contract.get('views_side_on_azimuth_deg') != list(emission.VIEWS):
        raise ValueError('all three declared side-on azimuths are required')
    runtime = contract.get('inputs', {})
    if set(runtime) != set(RUNTIME_HASHES) or any(runtime[name].get('sha256') != pin for name, pin in RUNTIME_HASHES.items()):
        raise ValueError('emissivity runtime differs from frozen development identities')


def validate_native_receipt(receipt, case, index):
    if (receipt.get('schema_version') != 1 or receipt.get('status') != 'bound_spherical_budget_inputs'
            or receipt.get('case') != case or receipt.get('snapshot_index') != index):
        raise ValueError('native input receipt does not bind this actual case/index')
    roles = set(receipt.get('inputs', {}))
    if roles not in ({'current_h5', 'initial_h5', 'environment'},
                     {'current_h5', 'initial_h5', 'environment', 'grid_file'}):
        raise ValueError('native input receipt roles differ')
    checks = receipt.get('native_preflight', {}).get('semantic_checks', {})
    if not SEMANTICS <= set(checks) or any(checks[name] != 'passed' for name in SEMANTICS):
        raise ValueError('native case semantic preflight has not passed')
    if case == 'G-HI' and (index >= 48 or checks.get('inherited_parent_source_restart_and_chain') != 'passed'):
        raise ValueError('G-HI requires accepted retained-chain semantics')
    if abs(float(receipt['initial']['time_code']) / BUDGET.CODE_TIME_PER_MYR) > 1e-6:
        raise ValueError('initial input is not the actual zero-age reference')
    if abs(float(receipt['current']['time_code']) / BUDGET.CODE_TIME_PER_MYR - index) > .05:
        raise ValueError('current input age differs from the declared snapshot')


def bind_lineage(receipt):
    index = receipt['snapshot_index']
    if receipt['case'] != 'G-HI' or index >= 48:
        raise ValueError('inherited lineage is only valid for retained G-HI indices')
    record = receipt['native_preflight']['inherited_lineage']['receipt']
    identity = emission.checked_compact(record)
    accepted = blind.read_json(identity['path'])
    if (accepted.get('schema_version') != 1 or accepted.get('status') != 'passed'
            or accepted.get('lineage') != 'accepted failed-run parent build/source plus validated 10 Myr home continuation'):
        raise ValueError('G-HI lineage is not accepted')
    chain = accepted.get('snapshots', {}).get('analysis_chain', [])
    if [row.get('output_index') for row in chain] != list(range(51)):
        raise ValueError('G-HI lineage analysis chain is incomplete')
    for role, epoch, selected in [('initial_h5', 'initial', 0), ('current_h5', 'current', index)]:
        bound = receipt['inputs'][role]
        actual = BUDGET._stat_identity(Path(bound['path']))
        if (any(chain[selected].get(key) != value or bound.get(key) != value for key, value in actual.items())
                or any(chain[selected].get(key) != receipt[epoch].get(key) for key in ('timestep', 'time_code'))):
            raise ValueError('G-HI native identity/time differs from accepted lineage')
    BUDGET._stable([identity])
    return identity


def validate_receipt_contract(receipt, contract):
    case, index = receipt['case'], receipt['snapshot_index']
    if contract.get('schema_version') != 1 or contract.get('case') != case:
        raise ValueError('native receipt was relabelled against another case contract')
    last = 47 if case == 'G-HI' else 50
    chain = contract.get('snapshots', [])
    if [row.get('index') for row in chain] != list(range(last + 1)):
        raise ValueError('native case contract chain is incomplete')
    for role, selected in [('initial_h5', 0), ('current_h5', index)]:
        if receipt['inputs'][role]['path'] != chain[selected]['path']:
            raise ValueError('native receipt snapshot escapes its case contract')
    for role in ('environment', 'grid_file'):
        if role in receipt['inputs'] and any(receipt['inputs'][role].get(key) != contract['files'][role].get(key)
                                           for key in ('path', 'sha256')):
            raise ValueError('native atmosphere/grid differs from case contract')


def make_views(grid):
    views = {}
    for angle in emission.VIEWS:
        horizontal = (grid.x if angle == 0 else NATIVE.renderer.projected_axis(
            grid.x, grid.y, view_angle_deg=angle, projected_u_bins=len(grid.x))[0])
        shape = (len(grid.z), len(horizontal))
        empty = {method: {'mask': np.zeros(shape, dtype=bool)} for method in emission.METHODS}
        views[angle] = emission.make_view(grid, angle, horizontal, np.zeros(shape), empty)
    return views


def integrate_maps(current, initial, grid, emissivity):
    views = make_views(grid)
    discarded_filling, diagnostics = emission.integrate_native(current, initial, grid, views, emissivity)
    if any(row['volume_kpc3_denominator'] != 0 for row in discarded_filling):
        raise ValueError('placeholder reconstruction selected native cells')
    sealed, projection = {}, {}
    for angle, view in views.items():
        maps = {'horizontal_axis_kpc': view.horizontal, 'horizontal_edges_kpc': view.u_edges,
                'z_axis_kpc': grid.z, 'z_edges_kpc': grid.z_edges,
                'path_C_kpc': view.maps['path_C_kpc']}
        checks = {}
        for name in view.native_integrals:
            checks[name] = emission.closure(
                name, float(np.sum(view.maps[name] * np.outer(grid.dz, np.diff(view.u_edges)))),
                view.covered_integrals[name], view.covered_absolute_integrals[name])
        for convention in emission.CONVENTIONS:
            maps[f'brightness_current_{convention}_whole'] = view.maps[f'brightness_current_{convention}_whole']
            for cut in emission.CUTS:
                maps[f'deficit_{convention}_A_v{cut}'] = (view.maps[f'brightness_initial_{convention}_A_v{cut}']
                                                        - view.maps[f'brightness_current_{convention}_A_v{cut}'])
        projection[str(angle)] = {'geometry': view.geometry_report, 'integral_closure': checks,
                                 'native_integrals': view.native_integrals,
                                 'covered_integrals': view.covered_integrals,
                                 'uncovered_integrals': {name: view.native_integrals[name] - view.covered_integrals[name]
                                                        for name in view.native_integrals}}
        sealed[angle] = maps
    return sealed, diagnostics, projection


def qualification_holds(receipt, diagnostics, projection):
    holds = list(receipt['native_preflight']['scientific_qualification'].get('holds', []))
    holds += ['observer_comparators_are_diagnostic_not_promoted',
              'moving_ambient_does_not_identify_shocks_or_causal_jet_origin',
              'native_filling_not_measured_for_any_observer_mask',
              'initial_reference_is_not_an_evolved_nojet_counterfactual',
              'retained_image_compatibility_not_remeasured_by_this_adapter']
    if diagnostics['tracer_outside_unit_interval_count']:
        holds.append('stored_tracer_outside_unit_interval')
    if any(diagnostics['native_component_boundary_cell_counts']['C'].values()):
        holds.append('cocoon_contacts_native_domain_boundary')
    if any(any(faces.values()) for region, faces in diagnostics['native_component_boundary_cell_counts'].items() if region != 'C'):
        holds.append('moving_ambient_contacts_native_domain_boundary')
    if any(record['geometry']['projection_coverage_hold'] for record in projection.values()):
        holds.append('retained_sky_grid_does_not_cover_every_native_cell')
    if any(row['any_out_of_table'] or row['raw_nonfinite'] or any(
            row[f'{convention}_{flag}'] for convention in emission.CONVENTIONS for flag in ('nonfinite', 'negative'))
           for row in diagnostics['correction_domain'].values()):
        holds.append('emissivity_correction_domain_or_sign')
    return list(dict.fromkeys(holds))


def publish_maps(output, case, index, kind, maps):
    units = []
    for angle, fields in maps.items():
        if set(fields) != set(DETECTOR_FIELDS) | {'path_C_kpc'}:
            raise ValueError('unexpected detector/truth map fields')
        name = f'{case}_{index:04d}_{angle}deg'
        np.savez_compressed(Path(output) / f'{name}.npz', **{field: fields[field] for field in DETECTOR_FIELDS})
        target = fields['path_C_kpc'] if kind == 'science' else np.zeros_like(fields['path_C_kpc'])
        np.savez_compressed(Path(output) / f'{name}.truth.npz', **{axis: fields[axis] for axis in blind.AXES}, path_C_kpc=target)
        units.append({'unit_id': name, 'case': case, 'snapshot_index': index, 'view_deg': angle, 'kind': kind,
                      'maps_filename': f'{name}.npz', 'truth_filename': f'{name}.truth.npz'})
    return units


def run(contract_path, contract_sha256, output):
    if Path(output).exists():
        raise ValueError('refusing to overwrite sealed maps')
    contract_identity = emission.checked_compact({'path': str(Path(contract_path).absolute()), 'sha256': contract_sha256})
    contract = blind.read_json(contract_path)
    config_identity = emission.checked_compact(contract['protocol_config'])
    config = blind.load_config(config_identity['path'])
    validate_specification(contract, config)
    receipt_identity = emission.checked_compact(contract['native_input_receipt'])
    receipt = blind.read_json(receipt_identity['path'])
    case, index, kind = contract['case'], contract['snapshot_index'], contract['kind']
    validate_native_receipt(receipt, case, index)
    paths = {role: Path(record['path']) for role, record in receipt['inputs'].items()}
    native_ids, _, _, _ = BUDGET.bind_inputs(paths, Path(receipt_identity['path']))
    preflight_contract = emission.checked_compact(receipt['native_preflight']['contract'])
    native_contract = blind.read_json(preflight_contract['path'])
    validate_receipt_contract(receipt, native_contract)
    lineage = bind_lineage(receipt) if case == 'G-HI' else None
    runtime = {name: emission.checked_compact(record) for name, record in contract['inputs'].items()}
    source_paths = [Path(__file__), Path(blind.__file__), Path(emission.__file__), Path(NATIVE.__file__),
                    Path(BUDGET.__file__), Path(emission.ladder.__file__), Path(emission.ladder.seed_grow_module.__file__),
                    Path(emission.ladder.recovery.__file__), Path(emission.ladder.legacy_builder.__file__),
                    Path(NATIVE.renderer.__file__), Path(NATIVE.pluto.__file__), Path(NATIVE.snapshot_energy.__file__),
                    Path(__file__).with_name('measure_q031_fluxes.py'), Path(__file__).with_name('select_common_age_hdf5.py')]
    sources = {path.name: {**BUDGET._stat_identity(path), 'sha256': BUDGET._sha256(path)} for path in source_paths}
    identities = [contract_identity, config_identity, receipt_identity, preflight_contract, *native_ids,
                  *runtime.values(), *sources.values(), *([lineage] if lineage else [])]
    BUDGET._stable(identities)
    current_path, initial_path = paths['current_h5'], paths['initial_h5']
    BUDGET._validate_snapshot_index(current_path, index)
    BUDGET._validate_snapshot_index(initial_path, 0)
    with h5py.File(current_path, 'r') as current_file, h5py.File(initial_path, 'r') as initial_file:
        current_name, time_code, shape = BUDGET._single_timestep(current_file, receipt['current']['timestep'], context=f'{case}/{index}')
        initial_name, initial_time, initial_shape = BUDGET._single_timestep(initial_file, receipt['initial']['timestep'], context=f'{case}/initial')
        if (shape != initial_shape or list(shape) != native_contract['shape_nz_ny_nx']
                or not math.isclose(time_code, receipt['current']['time_code'], rel_tol=0, abs_tol=1e-10)
                or not math.isclose(initial_time, receipt['initial']['time_code'], rel_tol=0, abs_tol=1e-10)):
            raise ValueError('native shape/time differs from bound receipt')
        grid_file = paths.get('grid_file')
        grid = emission.read_grid(current_file, shape, grid_file=grid_file)
        initial_grid = emission.read_grid(initial_file, shape, grid_file=grid_file)
        BUDGET._validate_grid(grid, initial_grid)
        xraise = NATIVE.renderer.load_module(Path(runtime['xraise_py']['path']))
        tables = NATIVE.load_tables(Path(runtime['apec_table']['path']), Path(runtime['gaunt_lut']['path']))
        def emissivity(rho, pressure):
            values, temperature, flags = NATIVE.cell_emissivity(
                xraise=xraise, tables=tables, rho_code=rho[None, :, :], pressure_code=pressure[None, :, :],
                frequency_hz=FREQUENCY_HZ, redshift=REDSHIFT)
            return {name: value[0] for name, value in values.items()}, temperature[0], {name: value[0] for name, value in flags.items()}
        maps, diagnostics, projection = integrate_maps(current_file[current_name]['vars'], initial_file[initial_name]['vars'], grid, emissivity)
    BUDGET._stable(identities)
    Path(output).mkdir(parents=True)
    units = publish_maps(output, case, index, kind, maps)
    files = {path.name: {'sha256': BUDGET._sha256(path), 'size_bytes': path.stat().st_size}
             for path in sorted(Path(output).iterdir()) if path.is_file()}
    result = {'schema_version': 1, 'case': case, 'snapshot_index': index, 'kind': kind,
              'execution_status': 'sealed_native_emission_maps_prepared_no_observer_scoring',
              'actual_time_myr': time_code / BUDGET.CODE_TIME_PER_MYR,
              'frequency_hz': FREQUENCY_HZ, 'redshift': REDSHIFT, 'sky_axis_policy': AXIS_POLICY,
              'scientific_qualification': {'qualified': False, 'holds': qualification_holds(receipt, diagnostics, projection)},
              'native_filling_measured': False, 'observer_statistics_computed': False,
              'placeholder_filling_rows_discarded': True,
              'initial_null_target': 'explicitly no evolved cavity; empty target does not assert zero native nozzle tracer',
              'provenance': {'contract': contract_identity, 'protocol_config': config_identity,
                             'native_input_receipt': receipt_identity, 'native_inputs': native_ids,
                             'native_preflight_contract': preflight_contract,
                             'inherited_lineage_receipt': lineage, 'runtime': runtime, 'analysis_sources': sources},
              'diagnostics': diagnostics, 'projection': projection, 'units': units, 'files': files,
              'software': {'numpy': np.__version__, 'h5py': h5py.__version__}}
    BUDGET._stable(identities)
    BUDGET._atomic_publish(Path(output) / 'completion.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.contract, args.contract_sha256, args.output_dir)
    print(json.dumps({'execution_status': result['execution_status'], 'case': result['case'],
                      'snapshot_index': result['snapshot_index'], 'observer_statistics_computed': False}))


if __name__ == '__main__':
    main()
