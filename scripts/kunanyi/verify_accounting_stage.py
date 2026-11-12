"""Run accounting checks using only the packaged project modules and fixtures."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile


STAGED_FILES = (
    'scripts/kunanyi/run_review_accounting.py',
    'scripts/kunanyi/prepare_spherical_budget_inputs.py',
    'scripts/kunanyi/run_spherical_budget_case.py',
    'scripts/science/extract_fixed_box_energy_budget.py',
    'scripts/science/extract_spherical_energy_budget.py',
    'scripts/science/measure_q031_fluxes.py',
    'scripts/science/summarize_q031_source_accounting.py',
    'scripts/science/pluto_h5_level3_ambient_extract.py',
    'scripts/science/select_common_age_hdf5.py',
    'scripts/science/snapshot_energy.py',
    'tests/test_fixed_box_energy_budget.py',
    'tests/test_review_accounting.py',
    'tests/test_q031_source_accounting.py',
    'tests/test_spherical_energy_budget.py',
    'tests/test_spherical_budget_inputs.py',
    'tests/test_q031_fluxes.py',
)
TARGET_TESTS = (
    'tests/test_fixed_box_energy_budget.py',
    'tests/test_review_accounting.py',
    'tests/test_q031_source_accounting.py',
)


def verify(stage: Path, basetemp: Path) -> None:
    stage = stage.resolve()
    for name in STAGED_FILES:
        path = stage/name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'missing or nonregular packaged dependency: {name}')
    code = '''
from pathlib import Path
import importlib.util
import json
import sys
stage = Path(sys.argv[1]).resolve()
files, targets = json.loads(sys.argv[2]), json.loads(sys.argv[3])
sys.path[:0] = [str(stage/name) for name in ('scripts/science', 'scripts/kunanyi', 'tests')]
for name in files:
    path = stage/name
    spec = importlib.util.find_spec(path.stem)
    if spec is None or Path(spec.origin).resolve() != path:
        raise RuntimeError('packaged module resolves outside stage: '+name)
import pytest
raise SystemExit(pytest.main(['-q', '-c', '/dev/null', '--rootdir', str(stage),
    '--confcutdir', str(stage), '-p', 'no:cacheprovider', '--basetemp', sys.argv[4], *targets]))
'''
    import json
    subprocess.run([sys.executable, '-I', '-B', '-c', code, str(stage),
                    json.dumps(STAGED_FILES), json.dumps(TARGET_TESTS), str(basetemp)],
                   cwd=stage, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', type=Path)
    parser.add_argument('--basetemp', type=Path)
    args = parser.parse_args()
    if args.basetemp is None:
        with tempfile.TemporaryDirectory(prefix='accounting_stage_') as scratch:
            verify(args.stage, Path(scratch)/'pytest')
    else:
        verify(args.stage, args.basetemp)


if __name__ == '__main__':
    main()
