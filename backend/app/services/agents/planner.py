from app.schemas.agents import ResearchStep


def create_plan(include_risk: bool = True) -> list[ResearchStep]:
    names = ["Identify relevant documents", "Search evidence", "Analyze findings"]
    if include_risk:
        names.append("Assess risks")
    names += ["Verify citations", "Critique answer", "Generate final answer"]
    return [ResearchStep(order=i + 1, name=name) for i, name in enumerate(names)]
