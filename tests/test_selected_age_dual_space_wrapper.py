from pathlib import Path


WRAPPER = Path("scripts/kunanyi/four_case_selected_age_dual_space_energetics.pbs")
REPAIR_WRAPPER = Path("scripts/kunanyi/four_case_selected_age_pressure_repair.pbs")


def wrapper_text() -> str:
    return WRAPPER.read_text()


def test_wrapper_runs_full_selected_age_surface_but_excludes_g_hi_50() -> None:
    text = wrapper_text()

    assert "run_case C-HI" in text and "10 20 30 40 50" in text
    assert "run_case C-LO" in text and "10 20 30 40 50" in text
    assert 'run_case G-HI 1e45 "$G_HI_EARLY_OUTPUTS" "$G_HI_LATE_OUTPUTS" 10 20 30 40' in text
    assert 'run_case G-LO 1e43 "$G_LO_OUTPUTS" "" 10 20 30 40 50' in text
    assert "case_age_views=57" in text


def test_wrapper_uses_home_analysis_storage_and_two_case_memory_safe_waves() -> None:
    text = wrapper_text()

    assert "#PBS -l select=1:ncpus=2:mpiprocs=1:mem=128gb" in text
    assert "/u/bwbrook/xray_cavities_analysis/2026-08-31-selected-age-dual-space-energetics" in text
    assert "run_pair C-HI C-LO" in text
    assert "run_pair G-HI G-LO" in text


def test_wrapper_archives_only_compact_products_and_logs() -> None:
    text = wrapper_text()

    assert "find . -path '*/compact/*' -type f" in text
    assert "find ./logs -type f" in text
    assert "tar -czf" in text and "--files-from" in text
    assert "find . -type f -print" not in text


def test_wrapper_enforces_xray_only_pressure_provenance() -> None:
    text = wrapper_text()

    assert "pressure_deprojection_inputs" not in text
    assert "tracer_loaded_or_used" in text
    assert "tracer independence gate failed" in text
    assert "xray_pressure_deprojection.py" in text


def test_pressure_repair_reuses_maps_without_repeating_projection_or_hdf5_work() -> None:
    text = REPAIR_WRAPPER.read_text()

    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=16gb" in text
    assert "2026-08-31-selected-age-dual-space-energetics" in text
    assert "build_selected_age_xray_pressure.py" in text
    assert "xraise_grid_smoke.py" not in text
    assert ".flt.h5" not in text
    assert "deprojection_regularization" in text
    assert "maximum_residual > 0.01" in text
    assert "maximum_interpolated > 2" in text


def test_pressure_repair_has_stable_no_overwrite_archive_contract() -> None:
    text = REPAIR_WRAPPER.read_text()

    assert "refusing to overwrite pressure-repair surface" in text
    assert "sha256sum --check" in text
    assert "tar -czf" in text and "--files-from" in text
    assert "case_age_views={view_count}" in text
