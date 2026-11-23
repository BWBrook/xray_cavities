import importlib.util
import json
import stat
from pathlib import Path

import numpy as np
import pytest

from test_assemble_blind_emission_cohort import CONFIG, inventory

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('seal_predictions', ROOT / 'scripts/kunanyi/seal_blind_emission_predictions.py')
sealer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sealer)


def test_scoring_files_are_closed_before_predict_and_receipt_is_content_bound(inventory, tmp_path, monkeypatch):
    stage = tmp_path / 'stage'
    stage.mkdir()
    (stage / 'products').symlink_to(tmp_path, target_is_directory=True)
    slots = []
    truth_paths = []
    for entry in sealer.blind.read_json(inventory)['producers']:
        path = Path(entry['producer_receipt']['path'])
        receipt = sealer.blind.read_json(path)
        receipt['provenance']['contract'] = {'sha256': 'a' * 64}
        sealer.blind.write_json(path, receipt)
        slots.append({**{k: receipt[k] for k in ('case', 'snapshot_index', 'kind')},
                      'contract': receipt['provenance']['contract'], 'native_input_receipt': entry['native_input_receipt']})
        truth_paths.extend(path.parent / u['truth_filename'] for u in receipt['units'])
    slots_path = stage / 'slots.json'
    sealer.blind.write_json(slots_path, slots)
    out = stage / 'seal'
    truth_paths.append(out / 'manifests/scoring_truth_manifest.json')
    config = sealer.blind.load_config(CONFIG)

    def empty_masks(image, horizontal, z):
        assert len(truth_paths) == 67
        assert all(stat.S_IMODE(f.stat().st_mode) == 0 for f in truth_paths)
        return {method: np.zeros(image.shape, dtype=bool) for method in config['methods']}

    monkeypatch.setattr(sealer.blind, 'observer_masks', empty_masks)
    result = sealer.seal(stage, CONFIG, slots_path, out)
    assert (result['science_views'], result['initial_null_views'], result['prediction_masks']) == (54, 12, 1056)
    assert result['scoring_truth_released'] is False
    assert 'native.json' not in json.dumps(result)
    assert (out / 'seal.json').stat().st_mode & 0o222 == 0
    assert (out / 'predictions/prediction_receipt.json').stat().st_mode & 0o222 == 0
    with pytest.raises(ValueError, match='new seal directory'):
        sealer.seal(stage, CONFIG, slots_path, out)
    # Let the temporary-fixture cleanup remove the sealed prediction directory.
    (out / 'predictions').chmod(0o700)
