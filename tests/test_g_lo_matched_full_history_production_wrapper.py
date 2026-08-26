from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


WRAPPER = Path("scripts/kunanyi/g_lo_matched_full_history_production.pbs")
RENDERER = Path("scripts/science/render_three_case_configs.py")


def load_renderer():
    name = "render_four_case_configs_for_goal061"
    spec = importlib.util.spec_from_file_location(name, RENDERER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_g_lo_rendered_contract_is_matched_to_the_factorial() -> None:
    renderer = load_renderer()
    case = renderer.CASES["G-LO"]
    assert case.environment == "group"
    assert case.jet_power_erg_s == 1.0e43
    assert case.jet_speed_c == 0.1

    rendered = renderer.render_pluto_ini(
        case,
        "particles",
        "stewart_stretched_250",
        renderer.DEFAULT_DURATION_MYR,
        renderer.DEFAULT_SNAPSHOT_INTERVAL_MYR,
        renderer.DEFAULT_DBL_H5_INTERVAL_MYR,
        renderer.DEFAULT_PARTICLE_INTERVAL_MYR,
        32.0,
    )
    assert "tstop            15330.06968940" in rendered
    assert "dbl.h5           1533.00696894  -1" in rendered
    assert "flt.h5           306.60139379  -1" in rendered
    assert "particles_dbl       3.06601394  -1" in rendered
    assert "JET_PWR                     1e+43" in rendered
    assert "JET_SPD                     0.1" in rendered


def test_wrapper_targets_home_at_proven_production_scale() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_lo_hist2" in text
    assert "#PBS -l select=64:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'readonly CASE_ID="G-LO"' in text
    assert 'readonly CASE_VARIANT="particles"' in text
    assert 'readonly RUN_ROOT="/u/bwbrook/xray_cavities_runs/' in text
    assert 'readonly PLUTO_MAXTIME_HOURS="47.5"' in text
    assert 'readonly RESTART_POLICY="fresh"' in text
    assert 'case "$RUN_ROOT" in' in text
    assert "/u/bwbrook/*" in text
    assert "home_write_fsync_probe=passed" in text
    assert "bs=1M count=16 conv=fsync" in text


def test_wrapper_fails_closed_without_follow_on_work() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert 'if [ -e "$WORK_ROOT" ]; then' in text
    assert "no-overwrite gate failed" in text
    assert 'readonly ALLOW_DONE_RERUN="0"' in text
    assert 'readonly FORCE_REBUILD="0"' in text
    assert 'readonly WATCHDOG_TIMEOUT_SECONDS="5400"' in text
    assert "run_with_progress_watchdog.sh" in text
    assert 'exec bash "$BASE_SCRIPT"' in text
    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "three_case_lifecycle_compaction" not in lower
    assert "rm -rf" not in lower
