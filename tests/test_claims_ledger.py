import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts/claims/check_claims.py")
check_claims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_claims)


def test_ledger_and_citations_are_consistent():
    assert check_claims.check(ROOT) == []


@pytest.fixture
def manuscript(tmp_path):
    for directory in ("claims", "settings", "text"):
        (tmp_path / directory).mkdir()
    claims = [
        {"id": "NAT-01", "status": "supported"},
        {"id": "NAT-03", "status": "provisional", "test": "Check the shock mask."},
        {"id": "OBS-02", "status": "withdrawn"},
    ]
    for claim in claims:
        claim.update(statement="Fixture", evidence=[])
    (tmp_path / "claims/claims.yaml").write_text(yaml.safe_dump({"claims": claims}))
    profiles = {
        "draft": {"manuscript_sources": ["../text/article.md"]},
        "submission": {"manuscript_sources": ["../text/article.md", "../text/captions.md"]},
    }
    (tmp_path / "settings/build.yaml").write_text(yaml.safe_dump({"profiles": profiles}))
    brief = {"brief": {"manuscript_sources": ["../text/brief.md"]}}
    (tmp_path / "settings/native_energy_brief.yaml").write_text(yaml.safe_dump({"profiles": brief}))
    (tmp_path / "AGENT_GUIDE.md").write_text("Earlier method. <!-- claims: OBS-02 -->\n")
    (tmp_path / "text/brief.md").write_text("Draft result. <!-- claims: NAT-03 -->\n")
    (tmp_path / "text/article.md").write_text("Measured enthalpy. <!-- claims: NAT-01 -->\n")
    (tmp_path / "figures").symlink_to(ROOT / "manuscript/figures", target_is_directory=True)
    return tmp_path


def test_submission_checks_its_caption_sources_and_preserves_guide_and_brief_policy(manuscript):
    path = manuscript / "text/captions.md"
    figure = "![Regional energy](../figures/q029_native_energetics.png){#fig-main-1}\n\n"
    path.write_text(figure + "<!-- claims: NAT-03 -->\n")
    assert check_claims.check(manuscript) == []
    assert check_claims.check(manuscript, strict=True) == [
        "text/captions.md: cites NAT-03, which is provisional"
    ]
    path.write_text(figure + "<!-- claims: NAT-01 -->\n")
    assert check_claims.check(manuscript, strict=True) == []


def test_uncited_or_withdrawn_detector_figure_cannot_reenter_the_article(manuscript):
    path = manuscript / "text/captions.md"
    retired = "![Former X-ray recovery](../figures/q029_observer_recovery.png){#fig-main-2}"
    path.write_text(retired + "\n\nAn unrelated claim. <!-- claims: NAT-01 -->\n")
    errors = check_claims.check(manuscript, strict=True)
    assert len(errors) == 1 and "q029_observer_recovery.png needs" in errors[0]
    path.write_text(retired + "\n\n<!-- claims:   -->\n")
    assert check_claims.check(manuscript, strict=True) == ["text/captions.md: empty claim citation"]
    path.write_text(retired + "\n\n<!-- claims: OBS-02 -->\n")
    assert check_claims.check(manuscript) == ["text/captions.md: cites OBS-02, which is withdrawn"]
    path.write_text(f"<!--\n{retired}\n-->\n")
    assert check_claims.check(manuscript, strict=True) == []
