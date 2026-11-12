from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/kunanyi'))
import verify_accounting_stage as stage_check


def payload(tmp_path):
    stage = tmp_path/'package'
    for name in stage_check.STAGED_FILES:
        target = stage/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return stage


def test_packaged_checks_pass_without_repository_import_paths(tmp_path, monkeypatch):
    stage = payload(tmp_path)
    monkeypatch.setenv('PYTHONPATH', str(ROOT/'scripts/kunanyi'))
    stage_check.verify(stage, tmp_path/'checks')


@pytest.mark.parametrize('kind', ('missing', 'external_symlink'))
def test_omitted_helper_cannot_be_supplied_by_owning_checkout(tmp_path, monkeypatch, kind):
    stage = payload(tmp_path)
    name = 'scripts/kunanyi/run_spherical_budget_case.py'
    target = stage/name
    target.unlink()
    if kind == 'external_symlink':
        target.symlink_to(ROOT/name)
    monkeypatch.setenv('PYTHONPATH', str(ROOT/'scripts/kunanyi'))
    with pytest.raises(ValueError, match='run_spherical_budget_case'):
        stage_check.verify(stage, tmp_path/'checks')
