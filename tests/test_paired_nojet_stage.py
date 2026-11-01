from pathlib import Path
import importlib.util

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paired_stage", ROOT / "scripts/kunanyi/build_paired_nojet_stage.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def template():
    return """[Grid]
X1-grid 1 -200 400 u 200
X2-grid 1 -200 400 u 200
X3-grid 1 -250 500 u 250
[Time]
tstop 15330.06968940
first_dt 3.06601394
[Boundary]
X1-beg reflective
X1-end reflective
X2-beg reflective
X2-end reflective
X3-beg reflective
X3-end reflective
[Static Grid Output]
analysis -1.0 -1
log 10
dbl.h5 3066.01393788 -1
"""


@pytest.mark.parametrize("smoke", [False, True])
def test_boundary_treatment_is_the_only_within_pair_difference(smoke):
    reflective = stage.render_ini(template(), "reflective", smoke).splitlines()
    outflow = stage.render_ini(template(), "outflow", smoke).splitlines()
    changed = [(a, b) for a, b in zip(reflective, outflow) if a != b]
    assert len(reflective) == len(outflow)
    assert len(changed) == 6
    assert {a.split()[0] for a, _ in changed} == {f"X{axis}-{side}" for axis in (1, 2, 3) for side in ("beg", "end")}
    assert all(a.split()[1] == "reflective" and b.split()[1] == "outflow" for a, b in changed)
    assert "analysis         -1.0  1" in reflective


def test_missing_or_duplicate_setting_cannot_silently_change_experiment():
    with pytest.raises(ValueError, match="exactly one"):
        stage.replace_setting("", "tstop", "1")
    with pytest.raises(ValueError, match="exactly one"):
        stage.replace_setting("tstop 1\ntstop 2\n", "tstop", "3")
    with pytest.raises(ValueError):
        stage.render_ini(template(), "periodic", False)


def test_smoke_changes_duration_and_cadence_without_changing_grid():
    normal = stage.render_ini(template(), "outflow", False)
    smoke = stage.render_ini(template(), "outflow", True)
    changed = [a.split()[0] for a, b in zip(normal.splitlines(), smoke.splitlines()) if a != b]
    assert changed == ["tstop", "dbl.h5"]
    assert f"{0.25 * stage.CODE_TIME_PER_MYR:.12f}" in smoke
