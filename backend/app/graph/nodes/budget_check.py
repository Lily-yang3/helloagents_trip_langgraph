"""Graph node: calculate and validate budget."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.schemas.trip import ParsedTripRequest, TripPlan
from app.tools.budget_tool import BudgetTool


def make_budget_check_node(budget_tool: BudgetTool) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        source = state.get("personalized_plan") or state.get("raw_plan") or {}
        plan = TripPlan.model_validate(source)
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})

        over_budget, budget = budget_tool.check_over_budget(plan=plan, total_budget=parsed.total_budget)
        plan.budget = budget

        return {
            "personalized_plan": plan.model_dump(),
            "budget": budget.model_dump(),
            "over_budget": over_budget,
            "budget_revision_round": int(state.get("budget_revision_round", 0)),
        }

    return node
