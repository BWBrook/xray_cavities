from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


WRAPPER = Path("scripts/kunanyi/g_hi_full_history_production.pbs")
RENDERER = Path("scripts/science/render_three_case_configs.py")


def load_renderer():
    name = "render_four_case_configs_for_goal060"
    spec = importlib.util.spec_from_file_location(name, RENDERER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_g_hi_case_and_rendered_contract() -> None:
    renderer = load_renderer()
    assert [case.case_id for case in renderer.selected_cases(None)] == [
        "C-HI",
        "C-LO",
        "G-LO",
        "G-HI",
    ]
    case = renderer.CASES["G-HI"]
    assert case.environment == "group"
    assert case.jet_power_erg_s == 1.0e45
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
    assert "JET_PWR                     1e+45" in rendered
    assert "JET_SPD                     0.1" in rendered


def test_wrapper_pins_fresh_history_complete_production() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_hi_hist" in text
    assert "#PBS -l select=64:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'readonly CASE_ID="G-HI"' in text
    assert 'readonly CASE_VARIANT="particles"' in text
    assert "rendered_g_hi_config/G-HI/particles" in text
    assert "2026-08-20-g-hi-full-history-production" in text
    assert 'readonly PLUTO_MAXTIME_HOURS="47.5"' in text
    assert 'readonly RESTART_POLICY="fresh"' in text
    assert 'readonly ALLOW_DONE_RERUN="0"' in text


def test_wrapper_fails_closed_and_has_no_follow_on_work() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert 'if [ -e "$WORK_ROOT" ]; then' in text
    assert "no-overwrite gate failed" in text
    assert 'readonly WATCHDOG_TIMEOUT_SECONDS="5400"' in text
    assert "run_with_progress_watchdog.sh" in text
    assert 'readonly I_MPI_JOB_SIGNAL_PROPAGATION="1"' in text
    assert 'exec bash "$BASE_SCRIPT"' in text
    assert "qsub" not in lower
    assert "force-fresh" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "compact" not in lower
