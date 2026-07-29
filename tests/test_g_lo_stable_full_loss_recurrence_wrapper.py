from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT = Path(
    "scripts/kunanyi/g_lo_stable_full_loss_recurrence_gate.pbs"
)


def test_wrapper_is_syntax_valid_and_binds_immutable_inputs() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    text = SCRIPT.read_text()
    assert "g_lo_flloss" in text
    assert "select=1:ncpus=1:mpiprocs=1:mem=64gb" in text
    assert "walltime=12:00:00" in text
    assert (
        "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30"
        in text
    )
    assert (
        "35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df"
        in text
    )
    assert (
        "b20c8e0bf134b58f16d1c662de6872b0dc1f7586937feeb7f501d434faf3038b"
        in text
    )
    assert "e80252cf35ff5a06166240e2867d3d485aaf6956" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "sha256sum --check" in text


def test_wrapper_archives_before_scientific_exit_and_has_no_production() -> None:
    text = SCRIPT.read_text()
    assert text.index('mv "$archive_tmp" "$ARCHIVE"') < text.index(
        'if [[ "$scientific_decision" != "PASS" ]]'
    )
    assert "evidence_archived=1" in text
    assert "exit 3" in text
    assert "full_loss_gate_summary.json" in text
    lowered = text.lower()
    assert "qsub" not in lowered
    assert "mpirun" not in lowered
    assert "raytrace" not in lowered
    assert "pluto" not in lowered.replace("plutokore", "")


def test_wrapper_has_atomic_run_lock_and_no_overwrite_guards() -> None:
    text = SCRIPT.read_text()
    assert (
        'RUN_LOCK="${RUN_LOCK:-$STAGE_ROOT/'
        '.g_lo_stable_full_loss_recurrence_gate.lock}"'
    ) in text
    assert 'if ! mkdir "$RUN_LOCK"; then' in text
    assert "another stable full-loss diagnostic owns the stage lock" in text
    assert 'trap release_run_lock EXIT' in text
    assert "refusing to overwrite stable full-loss output" in text


def test_wrapper_declares_compact_deterministic_output_contract() -> None:
    text = SCRIPT.read_text()
    for name in (
        "full_loss_panel_selection.csv",
        "full_loss_interval_summary.csv",
        "full_loss_gamma_summary.csv",
        "full_loss_emissivity_summary.csv",
        "full_loss_gate_summary.csv",
        "full_loss_gate_summary.json",
        "full_loss_interval_traces.csv.gz",
        "full_loss_gamma_traces.csv.gz",
    ):
        assert name in text
    assert "--files-from" in text
