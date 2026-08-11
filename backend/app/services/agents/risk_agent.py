import re
from app.schemas.agents import Risk

RISK_TERMS = {"penalty": "HIGH", "terminate": "HIGH", "must": "MEDIUM", "deadline": "MEDIUM", "liable": "HIGH", "prohibited": "HIGH", "may": "LOW"}


def analyze_risks(evidence: list[dict]) -> list[Risk]:
    risks: list[Risk] = []
    for item in evidence:
        lowered = item["text"].lower()
        match = next(((term, severity) for term, severity in RISK_TERMS.items() if term in lowered), None)
        if match:
            sentence = next((s.strip() for s in re.split(r"(?<=[.!?])\s+", item["text"]) if match[0] in s.lower()), item["text"][:240])
            risks.append(Risk(title=f"Potential {match[0]}-related obligation", severity=match[1],
                description="This passage may require management or compliance review.", evidence=sentence[:320],
                document_id=item["document_id"], recommendation="Have an authorized human reviewer assess this requirement."))
    return risks[:8]
