import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKES = ROOT / "docs/science/assets/paired_nojet_boundary_experiment_2026-11-01/original_smokes/smoke"
spec = importlib.util.spec_from_file_location("compare", ROOT / "scripts/science/compare_paired_boundary_prediction.py")
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


def test_smoke_contrasts_reproduce_recorded_values_and_sign_convention():
    cluster = compare.contrasts(SMOKES, "cluster_002003")[-1]
    group = compare.contrasts(SMOKES, "group_002031")[-1]
    assert cluster["contrast_mass_g"] == pytest.approx(1.628e39, rel=1e-3)
    assert cluster["contrast_h_erg"] == pytest.approx(1.137e55, rel=1e-3)
    assert group["contrast_h_erg"] == pytest.approx(1.348e53, rel=1e-3)
    for row in (cluster, group):
        assert row["transport_explains_mass"] == pytest.approx(1.0, abs=1e-4)
        assert row["transport_explains_h"] == pytest.approx(0.9998, abs=2e-4)
        assert 1.25 < row["mass_over_t2_prediction"] < 1.4


def test_incomplete_runs_are_never_given_a_verdict():
    rows = compare.contrasts(SMOKES, "cluster_002003")
    assert compare.verdict("cluster_002003", rows)["verdict"] == "incomplete"
