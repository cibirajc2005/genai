from app.services.agents.planner import create_plan


def test_plan_is_safe_and_bounded():
    plan = create_plan()
    assert len(plan) <= 8
    assert plan[0].name == "Identify relevant documents"
    assert all("reasoning" not in step.name.lower() for step in plan)
