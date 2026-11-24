import csv
import importlib.util
from pathlib import Path
import shutil
import stat
import sys
import tarfile

import numpy as np
import pytest

from test_assemble_blind_emission_cohort import CONFIG, ROOT, inventory
from test_seal_blind_emission_predictions import sealer

spec = importlib.util.spec_from_file_location('original_release', ROOT / 'scripts/kunanyi/release_blind_emission_scores.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
blind = sealer.blind


@pytest.fixture
def sealed(inventory, tmp_path, monkeypatch):
    stage = tmp_path / 'stage'
    stage.mkdir()
    (stage / 'products').symlink_to(tmp_path, target_is_directory=True)
    slots = []
    for entry in blind.read_json(inventory)['producers']:
        location = Path(entry['producer_receipt']['path'])
        data = blind.read_json(location)
        data['provenance']['contract'] = {'sha256': 'a' * 64}
        blind.write_json(location, data)
        slots.append({**{k: data[k] for k in ('case', 'snapshot_index', 'kind')},
                      'contract': data['provenance']['contract'], 'native_input_receipt': entry['native_input_receipt']})
    blind.write_json(stage / 'slots.json', slots)
    methods = blind.load_config(CONFIG)['methods']
    monkeypatch.setattr(blind, 'observer_masks',
                        lambda image, horizontal, z: {m: np.zeros_like(image, dtype=bool) for m in methods})
    directory = stage / 'seal'
    public = sealer.seal(stage, CONFIG, stage / 'slots.json', directory)
    originals = [tmp_path / f"{u['case']}_{u['snapshot_index']:04d}" / (u['unit_id'] + '.truth.npz')
                 for u in public['units']]
    originals.append(directory / 'manifests/scoring_truth_manifest.json')
    monkeypatch.setattr(release.review, 'SEAL', blind.digest(directory / 'seal.json'))
    monkeypatch.setattr(release.review, 'COMMITMENT', public['scoring_manifest_commitment_sha256'])
    yield directory, originals
    (directory / 'predictions').chmod(0o700)


def test_frozen_score_and_pre_release_independent_reader_agree(sealed, tmp_path, monkeypatch):
    directory, originals = sealed
    output = tmp_path / 'published'
    receipt = release.release(blind, CONFIG, directory, output)
    assert (receipt['archive_member_count'], receipt['scoring_files_reclosed']) == (67, 67)
    assert (receipt['scoring_rasters_verified'], receipt['prediction_files_verified']) == (66, 66)
    assert all(stat.S_IMODE(f.stat().st_mode) == 0 for f in originals)
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / 'scores').stat().st_mode) == 0o700
    assert all(stat.S_IMODE(f.stat().st_mode) == 0o400 for f in output.rglob('*') if f.is_file())
    assert blind.digest(output / 'scoring_evidence.tar') == receipt['archive_sha256']
    restored = tmp_path / 'restored'
    with tarfile.open(output / 'scoring_evidence.tar') as archive:
        names = {member.name for member in archive if member.isfile() and member.mode == 0o400}
        assert names == {'scoring_truth_manifest.json', *('truth/' + f.name for f in originals[:-1])}
        archive.extractall(restored, filter='data')

    # Rebuild only the independently published pieces of the prediction archive.
    extract = tmp_path / 'prediction_archive'
    producers = extract / 'producer_receipts'
    producers.mkdir(parents=True)
    shutil.copyfile(directory / 'seal.json', extract / 'seal.json')
    (extract / 'predictions').symlink_to(directory / 'predictions', target_is_directory=True)
    manifest = restored / 'scoring_truth_manifest.json'
    for unit in blind.read_json(manifest)['units']:
        filename = f"{unit['case']}_{unit['snapshot_index']:04d}.json"
        shutil.copyfile(unit['provenance']['producer_receipt']['path'], producers / filename)
    independent = tmp_path / 'independent'
    monkeypatch.setattr(release.review, 'PUBLIC', extract)
    monkeypatch.setattr(sys, 'argv', ['rescore', '--extract', str(extract), '--scoring-manifest', str(manifest),
                        '--truth-dir', str(restored / 'truth'), '--source', str(ROOT), '--output', str(independent)])
    release.review.main()
    with (output / 'scores/scores.csv').open() as first, (independent / 'scores.csv').open() as second:
        official = [{k: v for k, v in row.items() if k != 'qualification_holds'} for row in csv.DictReader(first)]
        comparison = list(csv.DictReader(second))
    assert len(official) == len(comparison) == 2112
    assert official == comparison


@pytest.mark.parametrize('bad', ['last_raster', 'last_prediction', 'manifest', 'scorer_interrupted'])
def test_failed_release_preserves_originals_and_publishes_nothing(bad, sealed, tmp_path, monkeypatch):
    directory, originals = sealed
    output = tmp_path / 'failed'
    def no_load(*args, **kwargs):
        pytest.fail('numerical array accessed before the final digest check')
    monkeypatch.setattr(np, 'load', no_load)
    if bad == 'scorer_interrupted':
        def interrupted(*args):
            assert all(stat.S_IMODE(f.stat().st_mode) == 0o400 for f in originals[:-1])
            assert stat.S_IMODE(originals[-1].stat().st_mode) == 0
            raise KeyboardInterrupt
        monkeypatch.setattr(blind, 'score', interrupted)
        error, message = KeyboardInterrupt, None
    else:
        paths = {'last_raster': originals[-2], 'manifest': originals[-1],
                 'last_prediction': directory / 'predictions' / blind.read_json(directory / 'seal.json')['units'][-1]['file']}
        target = paths[bad]
        mode = stat.S_IMODE(target.stat().st_mode)
        target.chmod(0o600)
        with target.open('r+b') as handle:
            handle.seek(-1, 2)
            last = handle.read(1)
            handle.seek(-1, 2)
            handle.write(bytes([last[0] ^ 1]))
        target.chmod(mode)
        monkeypatch.setattr(blind, 'score', lambda *args: pytest.fail('scorer invoked before every digest passed'))
        error = ValueError
        message = {'last_raster': 'archived bytes differ', 'last_prediction': 'sealed prediction differs',
                   'manifest': 'scoring manifest differs'}[bad]
    with pytest.raises(error, match=message):
        release.release(blind, CONFIG, directory, output)
    assert not output.exists()
    assert all(stat.S_IMODE(f.stat().st_mode) == 0 for f in originals)
