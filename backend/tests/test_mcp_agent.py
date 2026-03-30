"""Tests for the MCP-style tool registry and retrieval agent."""

from __future__ import annotations

import pytest

from app.schemas.trip import ParsedTripRequest
from app.schemas.user import UserProfile


@pytest.mark.asyncio
async def test_mcp_service_lists_and_executes_tools(isolated_runtime):
    container = isolated_runtime

    tools = container.mcp_service.list_tools()
    tool_names = {item.name for item in tools}
    assert "trip.search_attractions" in tool_names
    assert "trip.get_weather" in tool_names
    assert "trip.recommend_hotels" in tool_names
    assert "trip.recommend_daily_meals" in tool_names

    result = await container.mcp_service.call_tool(
        "trip.search_attractions",
        {"city": "杭州", "preferences": ["美食"], "limit": 4},
    )

    assert result.status == "ok"
    assert result.output_key == "attractions"
    assert result.payload


@pytest.mark.asyncio
async def test_mcp_agent_returns_standardized_candidates(isolated_runtime):
    container = isolated_runtime

    parsed = ParsedTripRequest(
        city="杭州",
        start_date="2026-05-01",
        travel_days=2,
        total_budget=2400,
        preferences=["美食", "文化"],
    )
    profile = UserProfile(user_id="agent_user", attraction_preference=["历史"])

    payload = await container.mcp_agent.retrieve_candidates(parsed_request=parsed, profile=profile)

    assert payload["available_tools"]
    assert payload["tool_calls"]
    assert payload["tool_results"]
    assert payload["candidates"]["attractions"]
    assert payload["candidates"]["weather"]
    assert payload["candidates"]["hotels"]
    assert payload["candidates"]["daily_meals"]
