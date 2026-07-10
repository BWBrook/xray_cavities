from __future__ import annotations

import re
import subprocess
from pathlib import Path


TEMPLATE = Path("scripts/kunanyi/jet_setup_production_template.pbs")


def test_watchdog_is_opt_in_and_default_run_still_invokes_mpirun_directly() -> None:
    text = TEMPLATE.read_text()

    assert 'PROGRESS_WATCHDOG_SCRIPT="${PROGRESS_WATCHDOG_SCRIPT:-}"' in text
    assert (
        'PROGRESS_WATCHDOG_TIMEOUT_SECONDS="${PROGRESS_WATCHDOG_TIMEOUT_SECONDS:-0}"'
        in text
    )
    assert (
        'PROGRESS_WATCHDOG_POLL_SECONDS="${PROGRESS_WATCHDOG_POLL_SECONDS:-60}"'
        in text
    )
    assert (
        'PROGRESS_WATCHDOG_TERM_GRACE_SECONDS="${PROGRESS_WATCHDOG_TERM_GRACE_SECONDS:-120}"'
        in text
    )
    assert 'PROGRESS_WATCHDOG_STATUS_LOG="${PROGRESS_WATCHDOG_STATUS_LOG:-' in text
    assert 'PROGRESS_WATCHDOG_TRIGGER_FILE="${PROGRESS_WATCHDOG_TRIGGER_FILE:-' in text

    run_start = text.index('set +e\n(\n  cd "$PROBLEM"')
    watchdog_branch = text[run_start : text.index("MPI_EXIT_CODE=$?", run_start)]
    direct_mpirun = (
        'mpirun "${MPI_LAUNCH_ARGS[@]}" ./pluto "${RUN_ARGS[@]}" '
        '> "outputs/logs/pluto_${PBS_JOBID:-manual}.log" 2>&1'
    )
    assert 'bash "$PROGRESS_WATCHDOG_SCRIPT"' in watchdog_branch
    assert "else" in watchdog_branch
    assert direct_mpirun in watchdog_branch
    assert watchdog_branch.index('bash "$PROGRESS_WATCHDOG_SCRIPT"') < watchdog_branch.index(
        "else"
    )
    assert watchdog_branch.index("else") < watchdog_branch.index(direct_mpirun)


def test_enabled_watchdog_is_fail_closed_and_wraps_the_same_mpi_command() -> None:
    text = TEMPLATE.read_text()

    assert (
        'require_nonnegative_integer "PROGRESS_WATCHDOG_TIMEOUT_SECONDS" '
        '"$PROGRESS_WATCHDOG_TIMEOUT_SECONDS"'
    ) in text
    assert 'require_file "$PROGRESS_WATCHDOG_SCRIPT"' in text
    assert (
        'require_positive_integer "PROGRESS_WATCHDOG_POLL_SECONDS" '
        '"$PROGRESS_WATCHDOG_POLL_SECONDS"'
    ) in text
    assert (
        'require_nonnegative_integer "PROGRESS_WATCHDOG_TERM_GRACE_SECONDS" '
        '"$PROGRESS_WATCHDOG_TERM_GRACE_SECONDS"'
    ) in text

    for option, variable in (
        ("--timeout-seconds", "PROGRESS_WATCHDOG_TIMEOUT_SECONDS"),
        ("--poll-seconds", "PROGRESS_WATCHDOG_POLL_SECONDS"),
        ("--term-grace-seconds", "PROGRESS_WATCHDOG_TERM_GRACE_SECONDS"),
        ("--status-log", "PROGRESS_WATCHDOG_STATUS_LOG"),
        ("--trigger-file", "PROGRESS_WATCHDOG_TRIGGER_FILE"),
    ):
        assert f'{option} "${variable}"' in text
    assert '--progress-dir "outputs"' in text
    assert '--command-log "outputs/logs/pluto_${PBS_JOBID:-manual}.log"' in text
    assert '-- mpirun "${MPI_LAUNCH_ARGS[@]}" ./pluto "${RUN_ARGS[@]}"' in text


def test_watchdog_timeout_has_a_distinct_failure_reason() -> None:
    text = TEMPLATE.read_text()

    assert 'if [ "$MPI_EXIT_CODE" -eq 124 ] &&' in text
    assert '[ "$PROGRESS_WATCHDOG_TIMEOUT_SECONDS" -gt 0 ] &&' in text
    assert '[ -f "$PROGRESS_WATCHDOG_TRIGGER_FILE" ]; then' in text
    assert 'FAILURE_REASON="no_progress_watchdog_timeout"' in text
    assert "classify_mpi_failure" in text


def test_explicit_h5_restart_is_validated_and_precedes_auto_discovery() -> None:
    text = TEMPLATE.read_text()

    assert 'H5_RESTART_INDEX="${H5_RESTART_INDEX:-}"' in text
    explicit_start = text.index('if [ -n "$H5_RESTART_INDEX" ]; then')
    auto_start = text.index('elif [ "$RESTART_POLICY" = "auto" ]; then', explicit_start)
    explicit_block = text[explicit_start:auto_start]

    assert 'case "$H5_RESTART_INDEX" in' in explicit_block
    assert '*[!0-9]*' in explicit_block
    assert "H5_RESTART_INDEX must be a nonnegative integer" in explicit_block
    assert 'H5_RESTART_INDEX=$((10#$H5_RESTART_INDEX))' in explicit_block
    assert (
        'H5_RESTART_PATH=$(printf "%s/outputs/data.%04d.dbl.h5" '
        '"$PROBLEM" "$H5_RESTART_INDEX")'
    ) in explicit_block
    assert 'require_file "$H5_RESTART_PATH"' in explicit_block
    assert 'validate_h5_restart_catalogue "${PROBLEM}/outputs/dbl.h5.out"' in explicit_block
    assert '"$H5_RESTART_INDEX"' in explicit_block
    assert '{found=1}' not in explicit_block
    assert '"${PROBLEM}/outputs/dbl.h5.out"' in explicit_block
    assert explicit_block.count('RUN_ARGS+=(-h5restart "$H5_RESTART_INDEX")') == 1
    assert 'RUN_KIND="h5_restart_${H5_RESTART_INDEX}"' in explicit_block
    assert "latest_restart_output" not in explicit_block


def _catalogue_validator_function() -> str:
    text = TEMPLATE.read_text()
    match = re.search(
        r"validate_h5_restart_catalogue\(\) \{\n.*?\n\}",
        text,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group(0)


def _run_catalogue_validator(tmp_path: Path, rows: str, index: int = 2) -> subprocess.CompletedProcess[str]:
    catalogue = tmp_path / "dbl.h5.out"
    catalogue.write_text(rows)
    script = tmp_path / "validate.sh"
    script.write_text(
        "#!/bin/bash\nset -u\n"
        + _catalogue_validator_function()
        + f'\nvalidate_h5_restart_catalogue "{catalogue}" "{index}"\n'
    )
    return subprocess.run(["bash", str(script)], text=True, capture_output=True, check=False)


def test_h5_restart_catalogue_validator_executes_for_one_numeric_match(tmp_path: Path) -> None:
    result = _run_catalogue_validator(
        tmp_path,
        "0 0.0 0.1 1\n1 1.0 0.1 2\n2 2.0 0.1 3\n",
    )

    assert result.returncode == 0, result.stderr


def test_h5_restart_catalogue_validator_rejects_duplicate_and_malformed_matches(
    tmp_path: Path,
) -> None:
    duplicate = _run_catalogue_validator(tmp_path, "2 2.0 0.1 3\n2 2.0 0.1 3\n")
    malformed = _run_catalogue_validator(tmp_path, "2bad 2.0 0.1 3\n")

    assert duplicate.returncode != 0
    assert malformed.returncode != 0


def test_empty_h5_restart_keeps_existing_auto_restart_contract() -> None:
    text = TEMPLATE.read_text()

    explicit_start = text.index('if [ -n "$H5_RESTART_INDEX" ]; then')
    auto_start = text.index('elif [ "$RESTART_POLICY" = "auto" ]; then', explicit_start)
    restart_end = text.index('echo "RUN_KIND=${RUN_KIND}"', auto_start)
    auto_block = text[auto_start:restart_end]

    assert "LATEST_RESTART=$(latest_restart_output || true)" in auto_block
    assert 'RUN_ARGS+=(-h5restart "$LATEST_OUTPUT")' in auto_block
    assert 'RUN_KIND="h5_restart_${LATEST_OUTPUT}"' in auto_block
    assert 'RUN_ARGS+=(-restart "$LATEST_OUTPUT")' in auto_block
    assert 'RUN_ARGS+=(-frestart "$LATEST_OUTPUT")' in auto_block


def test_intel_mpi_signal_propagation_override_is_inherited_unchanged() -> None:
    text = TEMPLATE.read_text()

    assert "unset I_MPI_JOB_SIGNAL_PROPAGATION" not in text
    assert "-genv I_MPI_JOB_SIGNAL_PROPAGATION" not in text
