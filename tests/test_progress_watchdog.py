from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHDOG = REPO_ROOT / "scripts/kunanyi/run_with_progress_watchdog.sh"


def watchdog_command(
    tmp_path: Path,
    command: list[str],
    *,
    timeout_seconds: int,
    poll_seconds: int = 1,
    term_grace_seconds: int = 1,
) -> tuple[list[str], dict[str, Path]]:
    paths = {
        "progress": tmp_path / "outputs",
        "command_log": tmp_path / "logs/pluto.log",
        "status_log": tmp_path / "logs/watchdog.tsv",
        "trigger_file": tmp_path / "markers/watchdog.triggered",
    }
    paths["progress"].mkdir(parents=True)
    argv = [
        "bash",
        str(WATCHDOG),
        "--timeout-seconds",
        str(timeout_seconds),
        "--poll-seconds",
        str(poll_seconds),
        "--term-grace-seconds",
        str(term_grace_seconds),
        "--progress-dir",
        str(paths["progress"]),
        "--command-log",
        str(paths["command_log"]),
        "--status-log",
        str(paths["status_log"]),
        "--trigger-file",
        str(paths["trigger_file"]),
        "--",
        *command,
    ]
    return argv, paths


def status_events(path: Path) -> list[str]:
    lines = path.read_text().splitlines()
    assert lines[0] == (
        "timestamp_utc\tevent\tchild_pid\tno_progress_seconds\texit_code\tsignature"
    )
    return [line.split("\t")[1] for line in lines[1:]]


def test_successful_command_keeps_running_while_pluto_artifacts_progress(
    tmp_path: Path,
) -> None:
    producer = tmp_path / "produce_progress.sh"
    producer.write_text(
        """#!/bin/bash
set -eu
progress_dir=$1
for index in 0 1 2 3; do
  printf '%s catalogue-row\n' "$index" >> "$progress_dir/dbl.h5.out"
  printf '%s float-catalogue-row\n' "$index" >> "$progress_dir/flt.h5.out"
  printf '%s restart-row\n' "$index" >> "$progress_dir/restart.out"
  particle=$(printf '%s/particles.%04d.dbl' "$progress_dir" "$index")
  dbl_hdf5=$(printf '%s/data.%04d.dbl.h5' "$progress_dir" "$index")
  flt_hdf5=$(printf '%s/data.%04d.flt.h5' "$progress_dir" "$index")
  printf 'particle-%s\n' "$index" > "$particle"
  printf 'dbl-hdf5-%s\n' "$index" > "$dbl_hdf5"
  printf 'flt-hdf5-%s\n' "$index" > "$flt_hdf5"
  printf 'step=%s\n' "$index"
  sleep 0.7
done
"""
    )
    argv, paths = watchdog_command(
        tmp_path,
        ["bash", str(producer), str(tmp_path / "outputs")],
        timeout_seconds=2,
    )

    result = subprocess.run(argv, text=True, capture_output=True, timeout=10)

    assert result.returncode == 0, result.stderr
    assert "step=3" in paths["command_log"].read_text()
    assert not paths["trigger_file"].exists()
    events = status_events(paths["status_log"])
    assert events[0] == "started"
    assert "progress" in events
    assert events[-1] == "command_exit"
    status_text = paths["status_log"].read_text()
    assert "log_size=" not in status_text
    assert "particle=particles." in status_text
    assert "hdf5=count=" in status_text
    assert "metadata_cksum=" in status_text
    assert "dbl_h5_out=dbl.h5.out" in status_text
    assert "flt_h5_out=flt.h5.out" in status_text
    assert "restart_out=restart.out" in status_text


def test_command_log_growth_does_not_count_as_scientific_progress(
    tmp_path: Path,
) -> None:
    chatty_command = (
        "for index in $(seq 1 30); do "
        "printf 'heartbeat=%s\\n' \"$index\"; "
        "sleep 0.1; "
        "done"
    )
    argv, paths = watchdog_command(
        tmp_path,
        ["bash", "-c", chatty_command],
        timeout_seconds=1,
        term_grace_seconds=1,
    )

    result = subprocess.run(argv, text=True, capture_output=True, timeout=10)

    assert result.returncode == 124, result.stderr
    assert paths["command_log"].read_text().count("heartbeat=") > 1
    assert "reason=no_progress_watchdog_timeout" in paths["trigger_file"].read_text()
    assert "log_size=" not in paths["status_log"].read_text()


def test_static_command_times_out_terminates_launcher_and_escalates(
    tmp_path: Path,
) -> None:
    child_pid_file = tmp_path / "child.pid"
    static_command = (
        "trap '' TERM; "
        'printf "%s\\n" "$$" > "$1"; '
        "printf 'launcher-ready\\n'; "
        "while :; do sleep 10; done"
    )
    argv, paths = watchdog_command(
        tmp_path,
        ["bash", "-c", static_command, "bash", str(child_pid_file)],
        timeout_seconds=1,
        term_grace_seconds=1,
    )

    result = subprocess.run(argv, text=True, capture_output=True, timeout=10)

    assert result.returncode == 124, result.stderr
    child_pid = int(child_pid_file.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)
    trigger = paths["trigger_file"].read_text()
    assert "reason=no_progress_watchdog_timeout" in trigger
    assert "timeout_seconds=1" in trigger
    events = status_events(paths["status_log"])
    assert "timeout" in events
    assert "trigger_written" in events
    assert "term_sent" in events
    assert "kill_group_sent" in events
    assert events[-1] == "watchdog_exit"
    assert events.index("timeout") < events.index("trigger_written")
    assert events.index("trigger_written") < events.index("term_sent")
    assert not list(paths["trigger_file"].parent.glob("*.tmp.*"))


def test_timeout_kills_the_entire_launcher_process_group(tmp_path: Path) -> None:
    launcher_pid_file = tmp_path / "launcher.pid"
    descendant_pid_file = tmp_path / "descendant.pid"
    launcher = tmp_path / "launcher.sh"
    launcher.write_text(
        """#!/bin/bash
set -eu
launcher_pid_file=$1
descendant_pid_file=$2
printf '%s\n' "$$" > "$launcher_pid_file"
bash -c 'trap "" TERM; printf "%s\\n" "$$" > "$1"; while :; do sleep 10; done' bash "$descendant_pid_file" &
trap '' TERM
wait
"""
    )
    argv, paths = watchdog_command(
        tmp_path,
        ["bash", str(launcher), str(launcher_pid_file), str(descendant_pid_file)],
        timeout_seconds=1,
        term_grace_seconds=1,
    )

    result = subprocess.run(argv, text=True, capture_output=True, timeout=10)

    assert result.returncode == 124, result.stderr
    assert launcher_pid_file.exists()
    assert descendant_pid_file.exists()
    for pid_file in (launcher_pid_file, descendant_pid_file):
        pid = int(pid_file.read_text())
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            pytest.fail(f"watchdog left process {pid} alive")
    assert "kill_group_sent" in status_events(paths["status_log"])


def test_ordinary_nonzero_exit_is_preserved(tmp_path: Path) -> None:
    argv, paths = watchdog_command(
        tmp_path,
        ["bash", "-c", "printf 'ordinary-failure\\n'; exit 23"],
        timeout_seconds=3,
    )

    result = subprocess.run(argv, text=True, capture_output=True, timeout=10)

    assert result.returncode == 23, result.stderr
    assert paths["command_log"].read_text() == "ordinary-failure\n"
    assert not paths["trigger_file"].exists()
    assert status_events(paths["status_log"])[-1] == "command_exit"
    assert "\t23\t" in paths["status_log"].read_text()


@pytest.mark.parametrize(
    ("forwarded_signal", "expected_exit"),
    [(signal.SIGTERM, 143), (signal.SIGINT, 130)],
)
def test_term_and_int_are_forwarded_to_the_child_launcher(
    tmp_path: Path,
    forwarded_signal: signal.Signals,
    expected_exit: int,
) -> None:
    child_pid_file = tmp_path / "forwarded-child.pid"
    signal_file = tmp_path / "forwarded.signal"
    child_command = """
signal_file=$1
pid_file=$2
trap 'printf "TERM\\n" > "$signal_file"; exit 143' TERM
trap 'printf "INT\\n" > "$signal_file"; exit 130' INT
printf '%s\\n' "$$" > "$pid_file"
while :; do sleep 0.1; done
"""
    argv, paths = watchdog_command(
        tmp_path,
        [
            "bash",
            "-c",
            child_command,
            "bash",
            str(signal_file),
            str(child_pid_file),
        ],
        timeout_seconds=10,
    )
    process = subprocess.Popen(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    child_pid: int | None = None
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not child_pid_file.exists():
            if process.poll() is not None:
                break
            time.sleep(0.05)
        assert child_pid_file.exists(), process.communicate(timeout=1)
        child_pid = int(child_pid_file.read_text())

        os.kill(process.pid, forwarded_signal)
        assert process.wait(timeout=5) == expected_exit

        expected_name = "TERM" if forwarded_signal == signal.SIGTERM else "INT"
        assert signal_file.read_text() == f"{expected_name}\n"
        assert "signal_forwarded" in status_events(paths["status_log"])
        assert not paths["trigger_file"].exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=3)
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
