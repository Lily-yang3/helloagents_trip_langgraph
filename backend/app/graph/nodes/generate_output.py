"""Graph node: produce assistant message and structured output."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.schemas.trip import Budget, TripPlan


def make_generate_output_node() -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        source = state.get("personalized_plan") or state.get("raw_plan") or {}
        plan = TripPlan.model_validate(source)
        explanations = list(state.get("personalization_explanation") or [])

        if state.get("budget"):
            plan.budget = Budget.model_validate(state.get("budget"))

        day_count = len(plan.days)
        budget_total = plan.budget.total if plan.budget else 0

        message = f"已生成 {plan.city} {day_count} 天个性化行程，预计总预算约 {budget_total} 元。"
        if explanations:
            message += " 个性化依据：" + "；".join(explanations[:2])
        if state.get("over_budget"):
            message += " 当前方案仍略超预算，你可以继续让我压缩成本或调整偏好。"

        return {
            "assistant_message": message,
            "structured_plan": plan.model_dump(),
            "need_clarification": False,
        }

    return node
