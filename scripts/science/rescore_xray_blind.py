"""Independent rescoring of the sealed 54-view X-ray predictions.

Committed before the scoring files were released. It refuses to open a
scoring raster unless the released manifest hashes to the value published
in commit 35c0879 and every raster hashes to the value in its archived
producer receipt. Side metrics come from the frozen side_score at c352554.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'docs/science/assets/xray_prediction_seal_2026-11-23'
COMMITMENT = '7ad2cc4b8d46209931aded1ec206e884963fdf7cc30d024d044fa458f8ed170a'
SEAL = '5e917a299e83c5693e01f2c8dbf787213aa99e322aac77ebf5ad11d48a4244ce'
RUNNER, CONFIG = 'scripts/science/run_background_refit_blind.py', 'configs/background_refit_blind_2026-11-11.json'
AXES = ('horizontal_axis_kpc', 'horizontal_edges_kpc', 'z_axis_kpc', 'z_edges_kpc')


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', type=Path, required=True, help='extracted prediction archive')
    parser.add_argument('--scoring-manifest', type=Path, required=True)
    parser.add_argument('--truth-dir', type=Path, required=True, help='directory of <unit>.truth.npz')
    parser.add_argument('--source', type=Path, required=True, help='checkout of c352554')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import numpy as np

    if sha(PUBLIC / 'seal.json') != SEAL or sha(args.extract / 'seal.json') != SEAL:
        raise ValueError('seal differs from the announced hash')
    if sha(args.scoring_manifest) != COMMITMENT:
        raise ValueError('released scoring manifest differs from the pre-prediction commitment')
    seal = json.loads((PUBLIC / 'seal.json').read_text())
    released = {unit['unit_id']: unit for unit in json.loads(args.scoring_manifest.read_text())['units']}
    if set(released) != {unit['unit_id'] for unit in seal['units']}:
        raise ValueError('scoring manifest and seal list different units')
    for unit in seal['units']:
        tag = f'{unit["case"]}_{unit["snapshot_index"]:04d}'
        producer = json.loads((args.extract / 'producer_receipts' / f'{tag}.json').read_text())
        truth = args.truth_dir / f'{unit["unit_id"]}.truth.npz'
        expected = producer['files'][truth.name]['sha256']
        if (sha(args.extract / 'producer_receipts' / f'{tag}.json') != unit['producer_receipt_sha256']
                or sha(truth) != expected or released[unit['unit_id']]['truth']['sha256'] != expected
                or sha(args.extract / 'predictions' / unit['file']) != unit['prediction_sha256']):
            raise ValueError(f'{unit["unit_id"]}: scoring raster or prediction differs from its commitment')

    sys.path.insert(0, str(args.source / 'scripts/science'))
    spec = importlib.util.spec_from_file_location('frozen_blind', args.source / RUNNER)
    blind = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(blind)
    config = blind.load_config(args.source / CONFIG)
    rows = []
    for unit in seal['units']:
        with np.load(args.truth_dir / f'{unit["unit_id"]}.truth.npz', allow_pickle=False) as target, \
                np.load(args.extract / 'predictions' / unit['file'], allow_pickle=False) as masks:
            axes = {name: masks[name] for name in AXES}
            if any(not np.array_equal(axes[name], target[name]) for name in AXES):
                raise ValueError(f'{unit["unit_id"]}: scoring grid differs from the sealed prediction')
            path = np.asarray(target['path_C_kpc'], dtype=float)
            if not np.all(np.isfinite(path)) or np.any(path < 0):
                raise ValueError(f'{unit["unit_id"]}: invalid tracer path')
            for label in seal['label_definitions']:
                for side in blind.emission.ladder.SIDES:
                    metrics = blind.side_score(masks[label['key']].astype(bool), path > 0, axes, side,
                                               unit['kind'], config['criteria'])
                    rows.append({'unit_id': unit['unit_id'], 'case': unit['case'],
                                 'snapshot_index': unit['snapshot_index'], 'view_deg': unit['view_deg'],
                                 'kind': unit['kind'], **label,
                                 'primary': label['correction'] == 'retained_linear'
                                 and label['velocity_cut_km_s'] in (0, 100), **metrics})
    args.output.mkdir(parents=True)
    with (args.output / 'scores.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    groups = []
    for mode in blind.MODES:
        for method in config['methods']:
            chosen = [row for row in rows if row['primary'] and row['mode'] == mode and row['method'] == method]
            if len(chosen) != 2 * len(seal['units']):
                raise ValueError('primary side count differs from the frozen cohort')
            science = [row for row in chosen if row['kind'] == 'science']
            null = [row for row in chosen if row['kind'] == 'initial_null']
            groups.append({'mode': mode, 'method': method, 'science_sides': len(science),
                           'science_sides_failed': sum(not row['generalization_criterion_passed'] for row in science),
                           'null_sides': len(null),
                           'null_sides_failed': sum(not row['generalization_criterion_passed'] for row in null),
                           'all_primary_sides_pass': all(row['generalization_criterion_passed'] for row in chosen)})
    report = {'scoring_manifest_sha256': COMMITMENT, 'seal_sha256': SEAL, 'groups': groups,
              'scores_sha256': sha(args.output / 'scores.csv')}
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
