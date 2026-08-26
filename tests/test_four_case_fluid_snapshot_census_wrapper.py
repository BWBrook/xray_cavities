from pathlib import Path


WRAPPER = Path("scripts/kunanyi/four_case_fluid_snapshot_census.pbs")


def test_wrapper_locks_matched_four_case_science_contract() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N four_fluid" in text
    assert "#PBS -l select=1:ncpus=4:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    assert '("C-HI", [args[0]], args[1])' in text
    assert '("C-LO", [args[2]], args[3])' in text
    assert '("G-HI", [args[4], args[5]], args[6])' in text
    assert '("G-LO", [args[7]], args[8])' in text
    assert "indices != list(range(51))" in text
    assert 'run_case C-HI 1e45' in text
    assert 'run_case C-LO 1e43' in text
    assert 'run_case G-HI 1e45' in text
    assert 'run_case G-LO 1e43' in text


def test_wrapper_runs_cases_concurrently_and_validates_science_boundaries() -> None:
    text = WRAPPER.read_text()

    assert text.count('pids+=("$!")') == 4
    assert 'if wait "${pids[$index]}"' in text
    assert "len(energy) != 51 * 4 * 3" in text
    assert "len(shocks) != 51 * 3 * 2" in text
    assert 'row["boundary_status"] != "unmeasured_from_retained_snapshots"' in text
    assert 'row["residual_interpretation"] != "not_promoted_to_cocoon_boundary_unresolved"' in text
    assert "powers != {expected_power}" in text
    assert 'metadata.get("snapshot_count") != 51' in text
    assert "four_case_validation=passed cases=4 snapshots=204" in text


def test_wrapper_is_no_overwrite_compact_and_has_no_follow_on_work() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert "refusing to overwrite Goal 062 surface" in text
    assert "sha256sum --check" in text
    assert "find . -type f ! -path '*/cache/*'" in text
    assert "tar -czf" in text
    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "rm -rf" not in lower
