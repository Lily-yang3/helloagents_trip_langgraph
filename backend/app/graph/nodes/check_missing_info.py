"""Graph node: detect missing mandatory fields for planning."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.schemas.trip import ParsedTripRequest
from app.services.request_parser import RequestParser


def make_check_missing_info_node(parser: RequestParser) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})
        missing_fields = parser.identify_missing_fields(parsed)

        return {
            "missing_fields": missing_fields,
            "need_clarification": bool(missing_fields),
        }

    return node
