from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_praise_last_shock_comparison.pbs")


def test_wrapper_is_single_node_postprocessing_only():
    text = WRAPPER.read_text()
    assert "#PBS -N g_lo_lstcmp" in text
    assert "select=1:ncpus=16:mpiprocs=1:mem=96gb" in text
    assert "walltime=24:00:00" in text
    assert "g_lo_history.h5" in text
    assert "qsub" not in text
    assert "mpiexec" not in text
    assert "pluto -" not in text.lower()


def test_wrapper_binds_exact_method_inputs_and_pinned_source():
    text = WRAPPER.read_text()
    for value in (
        "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30",
        "35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df",
        "5fa466a1db5450921cd4b95785c0b949a499fd4457cc62da18333061dee8ebeb",
        "e80252cf35ff5a06166240e2867d3d485aaf6956",
        "stable_method_value_selection.csv",
        "stable_method_value_particle_comparison.csv",
    ):
        assert value in text
    assert "--commit-proof" in text


def test_wrapper_requires_established_kunanyi_import_shims():
    text = WRAPPER.read_text()
    for shim in ("contextlib2.py", "hdf5plugin.py", "yt.py"):
        assert f'"$PYTHON_COMPAT/{shim}"' in text


def test_wrapper_archives_pass_or_hold_evidence_without_live_root_race():
    text = WRAPPER.read_text()
    assert "archive_file_list_payload.sh" in text
    assert 'bash "$ARCHIVE_HELPER"' in text
    assert 'cp -a "$ANALYSIS_ROOT/." "$ARCHIVE_PAYLOAD/"' in text
    assert 'diagnostic_rc=$?' in text
    assert '[[ "$diagnostic_rc" =~ ^(0|3)$ ]]' in text
    assert "goal056_science_gate=HOLD" in text
    assert "goal056_science_gate=PASS" in text
    assert 'tar -czf "$ARCHIVE" -C "$ANALYSIS_ROOT"' not in text
