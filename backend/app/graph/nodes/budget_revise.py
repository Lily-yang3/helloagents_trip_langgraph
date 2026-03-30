"""Graph node: revise plan when budget exceeds limit."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.schemas.trip import ParsedTripRequest, TripPlan
from app.tools.budget_tool import BudgetTool


def make_budget_revise_node(budget_tool: BudgetTool) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        plan = TripPlan.model_validate(state.get("personalized_plan") or state.get("raw_plan") or {})
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})

        # If user did not provide budget, no revision is required.
        if parsed.total_budget is None:
            over_budget, budget = budget_tool.check_over_budget(plan=plan, total_budget=None)
            plan.budget = budget
            return {
                "personalized_plan": plan.model_dump(),
                "budget": budget.model_dump(),
                "over_budget": over_budget,
                "budget_revision_round": int(state.get("budget_revision_round", 0)),
            }

        revised = budget_tool.revise_plan_under_budget(plan, total_budget=parsed.total_budget)
        over_budget, budget = budget_tool.check_over_budget(revised, total_budget=parsed.total_budget)
        revised.budget = budget

        explanations = list(state.get("personalization_explanation") or [])
        explanations.append("预算超限时已优先降低酒店、餐饮和次要收费景点成本，并尽量保留核心兴趣点。")

        return {
            "personalized_plan": revised.model_dump(),
            "budget": budget.model_dump(),
            "over_budget": over_budget,
            "budget_revision_round": int(state.get("budget_revision_round", 0)) + 1,
            "personalization_explanation": explanations,
        }

    return node
