from pathlib import Path


WRAPPER = Path("scripts/kunanyi/selected_age_particle_radio.pbs")
SCRIPT = Path("scripts/science/g_lo_snapshot_radio.py")


def test_wrapper_runs_one_complete_case_surface_with_case_isolation() -> None:
    text = WRAPPER.read_text()
    assert "#PBS -l select=1:ncpus=16:mpiprocs=1:mem=128gb" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'readonly CASE="${CASE:?Set CASE to C-HI, C-LO, G-HI, or G-LO}"' in text
    assert 'ANALYSIS_ROOT}.work' in text
    assert 'for index in range(5001)' in text
    assert '--particle-paths-json "$PARTICLE_PATHS"' in text
    assert '--case "$CASE"' in text
    assert "primary_rows=50 view_rows=150" in text


def test_wrapper_places_transient_cache_on_home_not_full_scratch() -> None:
    text = WRAPPER.read_text()
    assert "/u/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables" in text
    assert "/scratch/bwbrook/xray_cavities_analysis/2026-08-26-four-case-selected-age-observables" not in text


def test_wrapper_fails_fast_on_complete_staged_radio_dependency_surface() -> None:
    text = WRAPPER.read_text()
    assert 'plutokore/src/plutokore/radio/praise.py' in text
    assert 'plutokore/src/plutokore/radio/praise2.py' in text
    assert 'plutokore/src/plutokore/radio/raytracing.py' in text
    assert 'from plutokore.radio import praise, raytracing' in text
    assert text.index("radio_dependency_import_validation=passed") < text.index(
        'python "$HISTORY_HELPER" extract'
    )


def test_wrapper_binds_canonical_case_roots_and_g_hi_split() -> None:
    text = WRAPPER.read_text()
    assert "2026-08-17-c-hi-full-history-rerun" in text
    assert "2026-08-17-c-lo-full-history-rerun" in text
    assert "2026-08-20-g-hi-full-history-production" in text
    assert "2026-08-21-g-hi-full-history-home-continuation" in text
    assert "2026-08-23-g-lo-matched-full-history-production" in text
    assert "index <= 1000" in text


def test_wrapper_archives_compact_outputs_but_not_history_cache() -> None:
    text = WRAPPER.read_text()
    assert "radio_luminosity_timeseries.csv" in text
    assert "radio_view_luminosity.csv" in text
    assert "history_cache_manifest.json" in text
    archive_section = text.split("printf '%s\\n'", 1)[-1]
    assert "history_cache.h5" not in archive_section
    assert 'tar -tzf "$ARCHIVE"' in text


def test_radio_script_uses_explicit_particle_manifest_and_dynamic_case() -> None:
    text = SCRIPT.read_text()
    assert 'parser.add_argument("--case"' in text
    assert 'parser.add_argument("--particle-paths-json"' in text
    assert '"case": case' in text
    assert "particle-path manifest must contain outputs 0..5000" in text
