from pathlib import Path

from collab.directory import SyntheticExpertDirectory
from collab.models import ClinicalNeed


def test_utrecht_is_top_match_for_conversion_resectability() -> None:
    directory = SyntheticExpertDirectory()

    result = directory.find_matches(ClinicalNeed())

    assert result.matches[0].centre.id == "utrecht-crc"
    assert result.matches[0].score > result.matches[1].score
    assert any("synthetic directory" in limitation for limitation in result.limitations)
    assert result.matches[0].conditions
    reasons = {reason.label: reason for reason in result.matches[0].reasons}
    assert reasons["Clinical fit"].status == "match"
    assert "conversion" in reasons["Clinical fit"].detail
    assert reasons["Synthetic availability"].detail.startswith("Demonstration")


def test_directory_can_load_from_explicit_fixture() -> None:
    fixture = Path(__file__).parents[1] / "src" / "collab" / "fixtures" / "expert_centres.json"

    directory = SyntheticExpertDirectory(fixture)

    assert directory.get_centre("utrecht-crc") is not None
    assert directory.get_centre("missing") is None
