from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_fluid_snapshot_science.pbs")


def test_wrapper_runs_all_retained_snapshots_with_locked_science_contract() -> None:
    text = WRAPPER.read_text()
    assert "#PBS -l walltime=48:00:00" in text
    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=64gb" in text
    assert "expected_indices = [0, 10, 20, 30, 40, 50]" in text
    assert "indices != expected_indices" in text
    assert 'metadata.get("snapshot_count") != 6' in text
    assert "--case G-LO" in text
    assert "--jet-power-one-sided-erg-s 1e43" in text
    assert "--jet-active-myr 50" in text
    assert "--tube-radius-kpc 2" in text
    assert "--velocity-floor-code 1e-4" in text
    assert "--disturbance-fraction 0.05" in text
    assert "--remove-geometry-cache-on-success" in text
    assert 'ENERGY_MODULE="$STAGE_ROOT/snapshot_energy.py"' in text
    assert 'SHOCK_MODULE="$STAGE_ROOT/snapshot_shocks.py"' in text


def test_wrapper_preserves_boundary_uncertainty_and_compact_archive() -> None:
    text = WRAPPER.read_text()
    assert 'row["boundary_status"] != "unmeasured_from_retained_snapshots"' in text
    assert 'row["residual_interpretation"] != "not_promoted_to_cocoon_boundary_unresolved"' in text
    assert "find . -type f ! -path './cache/*'" in text
    assert "tar -czf" in text
    assert "data.*" not in text
    assert "particles.*" not in text


def test_wrapper_is_no_overwrite_but_supports_explicit_resume() -> None:
    text = WRAPPER.read_text()
    assert 'RESUME="${RESUME:-0}"' in text
    assert "refusing to overwrite analysis root" in text
    assert "set -- --resume" in text
    assert '"$@"' in text
    assert "resume_args" not in text
    assert "sha256sum --check" in text
