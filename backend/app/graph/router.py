"""Routing helpers for conditional LangGraph edges."""

from __future__ import annotations

from app.graph.state import PlannerState


def route_missing_info(state: PlannerState) -> str:
    if state.get("need_clarification"):
        return "ask_clarification"
    return "retrieve_candidates"


def route_budget(state: PlannerState) -> str:
    over_budget = bool(state.get("over_budget"))
    revision_round = int(state.get("budget_revision_round", 0))
    if over_budget and revision_round < 2:
        return "budget_revise"
    return "generate_output"
