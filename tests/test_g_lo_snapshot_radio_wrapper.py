from pathlib import Path


WRAPPER = Path(__file__).parents[1] / "scripts" / "kunanyi" / "g_lo_snapshot_radio.pbs"


def test_wrapper_runs_full_radio_surface_with_causal_fluid_binding() -> None:
    text = WRAPPER.read_text()
    assert "#PBS -l select=1:ncpus=16:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert '--fluid-manifest "$FLUID_ROOT/snapshot_manifest.csv"' in text
    assert '--praise2-commit-proof "$PRAISE2_COMMIT_PROOF"' in text
    assert "particles.0999.dbl" in text
    assert "particles.5000.dbl" in text
    assert "future particle state entered" in text


def test_wrapper_archives_compact_outputs_not_work_cache() -> None:
    text = WRAPPER.read_text()
    assert "find . -type f ! -path './.work/*'" in text
    assert "radio_luminosity_timeseries.csv" in text
    assert "radio_view_luminosity.csv" in text
    assert "tar -tzf" in text
