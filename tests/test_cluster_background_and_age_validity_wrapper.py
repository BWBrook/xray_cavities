from pathlib import Path


WRAPPER = Path("scripts/kunanyi/cluster_background_and_age_validity.pbs")


def test_wrapper_locks_small_paired_cluster_diagnostic() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N cl_bgdiag" in text
    assert "#PBS -l select=1:ncpus=2:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=04:00:00" in text
    assert "indices=(0 5 10 15 20 30 40 50)" in text
    assert "--case C-HI" in text and "--case C-LO" in text
    assert "--jet-power-one-sided-erg-s 1e45" in text
    assert "--jet-power-one-sided-erg-s 1e43" in text
    assert text.count("&\n") == 2


def test_wrapper_validates_against_goal062_and_is_no_overwrite() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert "GOAL062_ROOT" in text
    assert "reference_relative_error" in text
    assert "len(reconstruction_errors) != len(expected_indices) - 1" in text
    assert "max_error > 1.0e-8" in text
    assert "cluster_background_validation=passed cases=2 snapshots=16 shell_rows=80" in text
    assert "refusing to overwrite Goal 063 surface" in text
    assert "sha256sum --check" in text
    assert "tar -czf" in text
    assert "qsub" not in lower
    assert "rm -rf" not in lower
