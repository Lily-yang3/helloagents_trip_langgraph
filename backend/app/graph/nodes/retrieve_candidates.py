"""Graph node: retrieve candidates via MCP-managed async tool calls."""

from __future__ import annotations

import asyncio
from typing import Callable

from app.graph.state import PlannerState
from app.schemas.trip import ParsedTripRequest
from app.schemas.user import UserProfile
from app.services.mcp_agent import MCPTravelAgent


def make_retrieve_candidates_node(
    retrieval_agent: MCPTravelAgent,
) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        parsed = ParsedTripRequest.model_validate(state.get("parsed_request") or {})
        profile = UserProfile.model_validate(
            state.get("memory_profile") or {"user_id": str(state.get("user_id") or "guest")}
        )
        retrieval = asyncio.run(retrieval_agent.retrieve_candidates(parsed_request=parsed, profile=profile))

        return {
            "mcp_available_tools": retrieval["available_tools"],
            "tool_calls": retrieval["tool_calls"],
            "tool_results": retrieval["tool_results"],
            "candidates": retrieval["candidates"],
        }

    return node
