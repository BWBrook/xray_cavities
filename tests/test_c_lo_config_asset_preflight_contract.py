from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs")


def test_c_lo_preflight_contract_is_read_only_and_bounded() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert "#PBS -N c_lo_preflight" in text
    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=4gb" in text
    assert "#PBS -l walltime=00:10:00" in text
    assert "qsub" not in lower
    assert "mpiexec" not in lower
    assert "setup-problem" not in lower
    assert "xraise_grid_smoke.py" not in lower
    assert "praise" not in lower


def test_c_lo_preflight_contract_targets_cluster_low_power_case() -> None:
    text = WRAPPER.read_text()

    assert 'EXPECTED_CASE_ID="${EXPECTED_CASE_ID:-C-LO}"' in text
    assert 'EXPECTED_JET_PWR="${EXPECTED_JET_PWR:-1e+43}"' in text
    assert 'EXPECTED_JET_SPD="${EXPECTED_JET_SPD:-0.1}"' in text
    assert "tabulated_cosmo_002003.csv" in text
    assert 'EXPECTED_ENV_ROWS="${EXPECTED_ENV_ROWS:-4000}"' in text


def test_c_lo_preflight_contract_validates_rendered_config_and_asset() -> None:
    text = WRAPPER.read_text()

    for required in (
        "pluto.ini",
        "environment.ini",
        "case_manifest.json",
        "run_definition.json",
        "render_validation.json",
        "definitions_overrides.json",
    ):
        assert f'require_file "$CONFIG_DIR/{required}"' in text
    assert 'require_file "$ENV_ASSET"' in text
    assert "ENV_ASSET_SHA256=" in text
    assert "environment row-count mismatch" in text
