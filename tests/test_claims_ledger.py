import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts/claims/check_claims.py")
check_claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_claims)


def test_ledger_and_citations_are_consistent():
    assert check_claims.check(ROOT) == []
