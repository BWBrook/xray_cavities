#!/usr/bin/env python3
"""Derive independent localization and background-stability decisions from bound measurements."""

import argparse
import hashlib
import json
from pathlib import Path

ENERGY_COMPONENTS = ('thermal_erg', 'kinetic_erg', 'gravitational_erg', 'total_energy_erg')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(raw):
    tolerance = raw['absolute_energy_tolerance_erg']
    if not 0 < tolerance < float('inf'):
        raise ValueError('invalid absolute tolerance')
    rows = []
    for item in raw['regions']:
        components = {kind: {key: item[kind][key] for key in ENERGY_COMPONENTS}
                      for kind in ('contrast_cell_l1', 'reflective_delta_cell_l1', 'outflow_delta_cell_l1')}
        for values in components.values():
            if any(not isinstance(v, (int, float)) or not 0 <= v < float('inf') for v in values.values()):
                raise ValueError('non-finite or negative absolute component')
        paired = all(v <= tolerance for v in components['contrast_cell_l1'].values())
        stable = all(v <= tolerance for kind, values in components.items()
                     if kind != 'contrast_cell_l1' for v in values.values())
        rows.append({'buffer_kpc': item['buffer_kpc'], 'cell_count': item['cell_count'],
                     'paired_localization_pass': paired, 'background_stability_pass': stable,
                     'combined_pass': paired and stable, 'component_l1_erg': components,
                     'signed_contrast': item['contrast']})
    if [r['buffer_kpc'] for r in rows] != sorted(set(r['buffer_kpc'] for r in rows)):
        raise ValueError('widths must be unique and increasing')
    first = lambda name: next((r['buffer_kpc'] for r in rows if r[name]), None)
    return {'case': raw['case'], 'time_myr': raw['time_myr'], 'absolute_energy_tolerance_erg': tolerance,
            'smallest_paired_localization_width_kpc': first('paired_localization_pass'),
            'smallest_background_stability_width_kpc': first('background_stability_pass'),
            'smallest_combined_passing_width_kpc': first('combined_pass'),
            'adopted_coarse_width_at_50_myr_kpc': first('combined_pass') if abs(raw['time_myr'] - 50) <= 1e-8 else None,
            'supersedes': 'r1 adopted width used paired contrast only; raw measured quantities unchanged',
            'criterion': 'all four component L1 values <=0.01 S(t), for paired contrast and each twin drift',
            'production_certification': False, 'regions': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', type=Path)
    parser.add_argument('mode', choices=('smoke', 'full'))
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.stage / ('results_' + args.mode)
    completion = root / 'completion.json'
    receipt = json.loads(completion.read_text())
    manifest = args.stage / 'stage_checksums.sha256'
    if receipt['status'] != 'complete' or receipt['mode'] != args.mode:
        raise ValueError('incomplete measurement receipt')
    if sha256(manifest) != receipt['stage_manifest_sha256']:
        raise ValueError('stage manifest mismatch')
    for name, expected in receipt['files'].items():
        if Path(name).name != name or sha256(root / name) != expected:
            raise ValueError('measurement hash mismatch: ' + name)
    for line in manifest.read_text().splitlines():
        expected, name = line.split('  ', 1)
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or sha256(args.stage / relative) != expected:
            raise ValueError('stage source hash mismatch: ' + name)
    summaries = [summarize(json.loads((root / (case + '.json')).read_text()))
                 for case in ('cluster_002003', 'group_002031')]
    payload = {'status': 'complete_decision_overlay', 'mode': args.mode,
               'source_completion_sha256': sha256(completion),
               'source_stage_manifest_sha256': sha256(manifest),
               'source_measurements': receipt['files'],
               'decision_script_sha256': sha256(Path(__file__)), 'cases': summaries}
    encoded = json.dumps(payload, indent=2, allow_nan=False) + '\n'
    with args.output.open('x') as handle:
        handle.write(encoded)


if __name__ == '__main__':
    main()
