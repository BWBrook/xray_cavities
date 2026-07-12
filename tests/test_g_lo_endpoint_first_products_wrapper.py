from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_endpoint_first_products.pbs")


def test_targets_validated_g_lo_endpoint():
    text = WRAPPER.read_text()
    assert "#PBS -N g_lo_xprod" in text
    assert "2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles" in text
    assert "data.0050.flt.h5" in text
    assert "Timestep_50" in text
    assert "data.0010.dbl.h5" in text
    assert "particles.5000.dbl" in text
    assert "15330.06968940" in text


def test_generates_all_refined_views_and_three_case_comparison():
    text = WRAPPER.read_text()
    assert '"0|0deg|direct_y_axis_sum"' in text
    assert '"45|45deg|edge_overlap_uniform_cell_projection"' in text
    assert '"90|90deg|edge_overlap_uniform_cell_projection"' in text
    assert "edge_overlap_uniform_cell_projection" in text
    assert "g_lo_endpoint_projection_metrics.csv" in text
    assert "three_case_endpoint_comparison.csv" in text
    assert "c_hi_refined_trio_context.csv" in text
    assert "c_lo_endpoint_projection_metrics.csv" in text
    assert 'case_order = ("C-HI", "C-LO", "G-LO")' in text


def test_is_postprocessing_only_with_stable_archive():
    text = WRAPPER.read_text().lower()
    assert "#pbs -l select=1:ncpus=1:mpiprocs=1:mem=96gb" in text
    assert "#pbs -l walltime=04:00:00" in text
    assert "xraise_grid_smoke.py" in text
    assert "qsub" not in text
    assert "mpiexec" not in text
    assert "pluto " not in text
    assert "praise" not in text
    assert "--files-from" in text
    assert "archive_manifest.tsv" in text
    assert "archive_checksums.sha256" in text


def test_fails_closed_on_endpoint_and_projection_support():
    text = WRAPPER.read_text()
    assert "DONE" in text
    assert "FAILED" in text
    assert "rho" in text and "prs" in text and "tr1" in text
    assert "EMPTY_COLUMN_FRACTION_MAX" in text
    assert "projection_empty_columns.csv" in text
    assert "duplicate projection metric columns" in text
