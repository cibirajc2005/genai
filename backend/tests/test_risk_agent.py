from app.services.agents.risk_agent import analyze_risks


def test_risk_is_grounded_and_has_discrete_severity():
    rows = [{"document_id":"d", "text":"Employees must notify management before the deadline."}]
    risks = analyze_risks(rows)
    assert risks and risks[0].severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert risks[0].evidence
