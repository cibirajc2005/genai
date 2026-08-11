from app.services.document_intelligence import build_profile, get_profile
from unittest.mock import patch


def test_document_intelligence_extracts_only_present_facts():
    profile = build_profile("test-intelligence", "HR Policy. Employees must submit reports by 2026.", "HR Policy", "HR")
    assert profile["document_type"] == "Policy"
    assert "2026" in profile["important_dates"]
    assert get_profile("test-intelligence") is not None


def test_intelligence_still_returns_when_optional_table_is_missing():
    with patch("app.services.document_intelligence.connection", side_effect=RuntimeError("missing table")):
        profile = build_profile("d", "Policy staff must submit a report by 2027.", "Policy")
    assert profile["document_type"] == "Policy"
    assert profile["important_dates"] == ["2027"]
