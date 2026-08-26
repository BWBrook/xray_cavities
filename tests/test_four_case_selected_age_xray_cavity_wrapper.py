from pathlib import Path


WRAPPER = Path("scripts/kunanyi/four_case_selected_age_xray_cavity.pbs")


def test_wrapper_runs_all_cases_ages_and_views_in_parallel() -> None:
    text = WRAPPER.read_text()
    assert "#PBS -l select=1:ncpus=4:mpiprocs=1:mem=128gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    assert "for index in (10, 20, 30, 40, 50):" in text
    assert "for view in 0 45 90" in text
    assert "run_case C-HI" in text
    assert "run_case C-LO" in text
    assert "run_case G-HI" in text
    assert "run_case G-LO" in text
    assert 'pids+=("$!")' in text


def test_wrapper_places_analysis_on_home_not_full_scratch() -> None:
    text = WRAPPER.read_text()
    assert "/u/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables" in text
    assert "/scratch/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables" not in text


def test_wrapper_uses_canonical_roots_and_correct_g_hi_hdf5_split() -> None:
    text = WRAPPER.read_text()
    assert "2026-08-17-c-hi-full-history-rerun" in text
    assert "2026-08-17-c-lo-full-history-rerun" in text
    assert "2026-08-20-g-hi-full-history-production" in text
    assert "2026-08-21-g-hi-full-history-home-continuation" in text
    assert "2026-08-23-g-lo-matched-full-history-production" in text
    assert "index <= 10" in text
    assert 'shape != (1014, 960, 960)' in text


def test_wrapper_archives_compact_products_only() -> None:
    text = WRAPPER.read_text()
    assert "find . -path '*/compact/*' -type f" in text
    archive_section = text.split("find . -path '*/compact/*'", 1)[-1]
    assert "data.*.h5" not in archive_section
    assert "xraise_grid_0deg" not in archive_section
    assert 'tar -tzf "$ARCHIVE"' in text


def test_wrapper_can_isolate_one_failed_case_without_recomputing_others() -> None:
    text = WRAPPER.read_text()
    assert 'readonly CASE_ONLY="${CASE_ONLY:-ALL}"' in text
    assert 'C-HI|C-LO|G-HI|G-LO) cases=("$CASE_ONLY")' in text
    assert 'for case_id in "${cases[@]}"' in text
    assert 'python - "$ANALYSIS_ROOT" "${cases[@]}"' in text
    assert 'case_age_views={15 * len(cases)}' in text
