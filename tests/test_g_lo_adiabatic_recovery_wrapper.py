from __future__ import annotations

import subprocess
from pathlib import Path


SCRIPT = Path("scripts/kunanyi/g_lo_adiabatic_recovery_diagnostic.pbs")


def test_wrapper_is_syntax_testable_and_binds_immutable_inputs() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    text = SCRIPT.read_text()
    assert "g_lo_adrec" in text
    assert "sha256sum --check" in text
    assert "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30" in text
    assert "35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df" in text
    assert "b20c8e0bf134b58f16d1c662de6872b0dc1f7586937feeb7f501d434faf3038b" in text
    assert "pressure_method_selection.csv" in text
    assert "pressure_method_nonfinite_emissivity_records.csv" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "e80252cf35ff5a06166240e2867d3d485aaf6956" in text
    assert "plutokore_commit.txt" in text
    assert "goal049_g_lo_adiabatic_recovery_index_repair_v2" in text
    assert "2026-07-28-g-lo-adiabatic-recovery-index-repair-v2" in text


def test_wrapper_archives_before_scientific_fail_and_has_no_production() -> None:
    text = SCRIPT.read_text()
    assert text.index('mv "$archive_tmp" "$ARCHIVE"') < text.index('if [[ "$scientific_decision" != "PASS" ]]')
    assert "evidence_archived=1" in text
    assert "exit 3" in text
    assert "diagnostic_rc" in text
    assert "adiabatic_recovery_infrastructure=FAIL" in text
    lowered = text.lower()
    assert "qsub" not in lowered
    assert "mpirun" not in lowered
    assert "raytrace" not in lowered


def test_wrapper_claims_an_atomic_single_run_lock() -> None:
    text = SCRIPT.read_text()
    assert 'RUN_LOCK="${RUN_LOCK:-$STAGE_ROOT/.g_lo_adiabatic_recovery_run.lock}"' in text
    assert 'if ! mkdir "$RUN_LOCK"; then' in text
    assert "another adiabatic-recovery diagnostic already owns the stage lock" in text
    assert 'trap release_run_lock EXIT' in text
