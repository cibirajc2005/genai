from app.services.document_intelligence import build_profile, get_profile


def test_document_intelligence_extracts_only_present_facts():
    profile = build_profile("test-intelligence", "HR Policy. Employees must submit reports by 2026.", "HR Policy", "HR")
    assert profile["document_type"] == "Policy"
    assert "2026" in profile["important_dates"]
    assert get_profile("test-intelligence") is not None
