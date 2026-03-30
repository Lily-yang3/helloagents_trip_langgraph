"""LangGraph state definition for personalized trip planning."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from app.schemas.trip import CandidateData, ParsedTripRequest, TripPlan
from app.schemas.user import UserProfile


class PlannerState(TypedDict, total=False):
    user_id: str
    session_id: str
    thread_id: str

    user_message: str
    messages: List[Dict[str, str]]

    parsed_request: Dict[str, Any]
    missing_fields: List[str]
    clarification_question: str
    need_clarification: bool

    memory_profile: Dict[str, Any]
    memory_patch: Dict[str, Any]

    mcp_available_tools: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    candidates: Dict[str, Any]
    raw_plan: Dict[str, Any]
    personalized_plan: Dict[str, Any]

    budget: Dict[str, Any]
    over_budget: bool
    budget_revision_round: int

    assistant_message: str
    structured_plan: Optional[Dict[str, Any]]
    personalization_explanation: List[str]
