from pathlib import Path
import re


SCRIPT = Path("scripts/kunanyi/three_case_lifecycle_compaction.pbs")
LEDGER_SHA256 = "df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92"
CONFIRMATION_TOKEN = (
    "BARRY_APPROVED_GOAL047_"
    f"{LEDGER_SHA256}_DELETE_EXACT_296_ROWS_6845659111424_ALLOCATED_BYTES"
)


def wrapper_text() -> str:
    return SCRIPT.read_text()


def test_pbs_resource_and_stage_contract_is_exact() -> None:
    text = wrapper_text()
    assert "#PBS -N tri_compact_r1" in text
    assert "#PBS -q normal" in text
    assert "#PBS -l select=1:ncpus=8:mpiprocs=1:mem=64gb" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert "#PBS -m ae" in text
    assert (
        "/u/bwbrook/codex_kunanyi/"
        "goal047_three_case_lifecycle_compaction_retry1/"
        "three_case_lifecycle_compaction_retry1.out"
    ) in text
    assert (
        "/u/bwbrook/codex_kunanyi/"
        "goal047_three_case_lifecycle_compaction_retry1/"
        "three_case_lifecycle_compaction_retry1.err"
    ) in text
    assert (
        'readonly STAGE_DIR="/u/bwbrook/codex_kunanyi/'
        'goal047_three_case_lifecycle_compaction_retry1"'
    ) in text
    assert (
        'readonly EVIDENCE_ROOT="/scratch/bwbrook/xray_cavities_analysis/'
        '2026-07-24-three-case-lifecycle-compaction-execution-retry1"'
    ) in text


def test_retry_namespace_cannot_clobber_attempt1_evidence() -> None:
    text = wrapper_text()
    attempt1_stage = (
        'readonly STAGE_DIR="/u/bwbrook/codex_kunanyi/'
        'goal047_three_case_lifecycle_compaction"'
    )
    attempt1_evidence = (
        'readonly EVIDENCE_ROOT="/scratch/bwbrook/xray_cavities_analysis/'
        '2026-07-24-three-case-lifecycle-compaction-execution"'
    )
    assert attempt1_stage not in text
    assert attempt1_evidence not in text
    assert "three_case_lifecycle_compaction_retry1_2026-07-24.tar.gz" in text
    assert (
        'readonly STAGE_TRANSCRIPT="$STAGE_DIR/'
        'three_case_lifecycle_compaction_transcript.jsonl"'
    ) in text


def test_exact_approval_constants_and_inputs_are_frozen() -> None:
    text = wrapper_text()
    assert f'readonly EXPECTED_LEDGER_SHA256="{LEDGER_SHA256}"' in text
    assert f'readonly CONFIRMATION_TOKEN="{CONFIRMATION_TOKEN}"' in text
    assert 'readonly EXPECTED_DELETE_ROWS="296"' in text
    assert 'readonly EXPECTED_HDF5_ROWS="148"' in text
    assert 'readonly EXPECTED_XMF_ROWS="148"' in text
    assert 'readonly EXPECTED_ALLOCATED_BYTES="6845659111424"' in text
    assert 'readonly APPROVAL_RECEIPT="$STAGE_DIR/approval_receipt.json"' in text
    assert (
        'readonly PACKET_MANIFEST="$PACKET_DIR/local_asset_manifest.sha256"'
        in text
    )
    assert (
        'readonly COMPLETED_EVIDENCE_MANIFEST="$STAGE_DIR/'
        'goal046_completed_evidence_manifest.sha256"'
    ) in text
    assert 'sha256sum -c "$PACKET_MANIFEST"' in text
    assert 'sha256sum -c "$COMPLETED_EVIDENCE_MANIFEST"' in text
    assert "approval_status" in text
    assert "approved_payload_ledger_sha256" in text
    assert "staged_symlink_gate=passed symlink_count=0" in text
    assert "staged input tree contains symlinks" in text
    assert "followlinks=False" in text


def test_execute_cli_delegates_all_irreversible_mechanics() -> None:
    text = wrapper_text()
    assert 'nofile_limit="$(ulimit -n)"' in text
    assert '[ "$nofile_limit" -lt 1024 ]' in text
    assert 'echo "open_file_limit=$nofile_limit"' in text
    assert "import h5py" in text
    assert 'print(f"h5py_version={h5py.__version__}")' in text
    invocation = text[text.index('"$PYTHON" "$EXECUTOR" \\') :]
    for expected in (
        "--mode execute",
        '--packet-dir "$PACKET_DIR"',
        '--approved-ledger "$APPROVED_LEDGER"',
        '--expected-ledger-sha256 "$EXPECTED_LEDGER_SHA256"',
        '--confirmation-token "$CONFIRMATION_TOKEN"',
        '--approval-receipt "$APPROVAL_RECEIPT"',
        '--completed-evidence-dir "$COMPLETED_EVIDENCE_DIR"',
        '--evidence-root "$EVIDENCE_ROOT"',
        '--stage-transcript "$STAGE_TRANSCRIPT"',
        '--pbs-job-id "$PBS_JOBID"',
        '--lock-path "$EXECUTION_LOCK"',
        '--status-json "$EXECUTION_STATUS"',
        '--compact-evidence-file-list "$COMPACT_EVIDENCE_FILE_LIST"',
        "--max-workers 8",
    ):
        assert expected in invocation
    assert 'readonly EXECUTOR="$STAGE_DIR/execute_three_case_lifecycle_compaction.py"' in text
    assert '"$PYTHON" -m py_compile "$EXECUTOR"' in text
    assert "DELETION_COMPLETE_POSTCHECK_GREEN" in text


def test_shell_contains_no_destructive_or_submission_primitive() -> None:
    text = wrapper_text()
    forbidden_commands = (
        r"^\s*rm(?:dir)?\b",
        r"^\s*unlink\b",
        r"^\s*find\b",
        r"^\s*qsub\b",
    )
    for pattern in forbidden_commands:
        assert re.search(pattern, text, flags=re.MULTILINE) is None
    assert "-delete" not in text
    assert "rm -rf" not in text
    assert "cp -r" not in text
    assert "cp -a" not in text
    assert "glob(" not in text
    assert "rglob(" not in text


def test_outputs_use_no_clobber_reservations_and_hard_link_publish() -> None:
    text = wrapper_text()
    assert 'readonly WRAPPER_FAILURE_STATUS="$STAGE_DIR/wrapper_failure_status.json"' in text
    assert "WRAPPER_FAILED_CLOSED" in text
    assert "record_wrapper_exit" in text
    assert "trap 'record_wrapper_exit" in text
    assert "set -o noclobber" in text
    assert 'for output in "$EVIDENCE_ROOT" "$ARCHIVE"' in text
    assert '"$ARCHIVE_RESERVATION" "$ARCHIVE_PAYLOAD" "$ARCHIVE_PAYLOAD_TMP"' in text
    assert '"$STAGE_TRANSCRIPT" "$EXECUTION_LOCK" "$EXECUTION_STATUS"; do' in text
    assert 'if [ -e "$output" ] || [ -L "$output" ]; then' in text
    assert 'mkdir "$EVIDENCE_ROOT"' in text
    assert 'mkdir "$ARCHIVE_RESERVATION"' in text
    assert "os.link(source, destination)" in text
    assert "refusing to overwrite published archive" in text


def test_archive_is_explicit_compact_evidence_only() -> None:
    text = wrapper_text()
    assert "compact_evidence_file_list.txt" in text
    assert "archive_content_file_list.txt" in text
    assert "archive_file_list.txt" in text
    assert "archive_checksums.sha256" in text
    assert "archive_manifest.tsv" in text
    assert "--files-from" in text
    assert 'tar -tzf "$ARCHIVE_TMP"' in text
    assert 'tar -tzf "$ARCHIVE"' in text
    assert "raw HDF5/data/particle payload forbidden" in text
    assert '".h5", ".xmf", ".dbl", ".flt", ".tar", ".tar.gz"' in text
    assert "non-compact evidence exceeds 64 MiB" in text
    assert "source.is_symlink()" in text
    assert 'destination = payload / "executor_evidence" / relative' in text
    assert (
        'transcript_destination = payload / "stage_provenance" / '
        '"three_case_lifecycle_compaction_transcript.jsonl"'
    ) in text
    assert 'test -s "$STAGE_TRANSCRIPT"' in text
    assert 'sha256sum "$STAGE_TRANSCRIPT"' in text


def test_wrapper_prints_completion_markers_and_archive_sha() -> None:
    text = wrapper_text()
    assert 'echo "GOAL047_EXECUTOR_STATUS=$status"' in text
    assert 'echo "GOAL047_COMPACTION_COMPLETE=1"' in text
    assert 'sha256sum "$ARCHIVE"' in text
    assert 'echo "finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"' in text
