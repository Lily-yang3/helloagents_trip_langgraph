"""Agent wrapper that binds LLM-planned tool calls to the MCP service."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.llm_client import LLMClient
from app.mcp.models import MCPExecutionReport, MCPToolCall, MCPToolDescriptor
from app.mcp.service import GlobalMCPService
from app.schemas.trip import ParsedTripRequest
from app.schemas.user import UserProfile


class MCPTravelAgent:
    """Tool-aware retrieval agent powered by a global MCP registry."""

    def __init__(self, mcp_service: GlobalMCPService, llm_client: LLMClient) -> None:
        self.mcp_service = mcp_service
        self.llm_client = llm_client

    async def retrieve_candidates(self, parsed_request: ParsedTripRequest, profile: UserProfile) -> Dict[str, Any]:
        available_tools = self.mcp_service.list_tools()
        planned_calls = self.llm_client.plan_tool_calls(
            request_context=self._build_request_context(parsed_request, profile),
            tools=available_tools,
        )
        tool_calls = self._ensure_required_calls(planned_calls, parsed_request, profile, available_tools)
        tool_results = await self.mcp_service.call_tools(tool_calls)

        report = MCPExecutionReport(
            available_tools=available_tools,
            tool_calls=tool_calls,
            results=tool_results,
        )

        return {
            "available_tools": [item.model_dump() for item in report.available_tools],
            "tool_calls": [item.model_dump() for item in report.tool_calls],
            "tool_results": [item.model_dump() for item in report.results],
            "candidates": self._aggregate_candidates(report.results),
        }

    def _build_request_context(self, parsed_request: ParsedTripRequest, profile: UserProfile) -> Dict[str, Any]:
        hotel_budget_min, hotel_budget_max = self._resolve_hotel_budget(parsed_request, profile)
        return {
            "intent": "retrieve travel planning candidates",
            "request": parsed_request.model_dump(),
            "user_profile": profile.model_dump(),
            "derived_constraints": {
                "city": parsed_request.city or "北京",
                "travel_days": parsed_request.travel_days or 3,
                "preferences": self._merge_preferences(parsed_request, profile),
                "hotel_budget_min": hotel_budget_min,
                "hotel_budget_max": hotel_budget_max,
                "start_date": parsed_request.start_date,
            },
        }

    def _ensure_required_calls(
        self,
        planned_calls: Sequence[MCPToolCall],
        parsed_request: ParsedTripRequest,
        profile: UserProfile,
        tools: Sequence[MCPToolDescriptor],
    ) -> List[MCPToolCall]:
        tool_by_output = {tool.output_key: tool.name for tool in tools}
        enriched_calls: List[MCPToolCall] = []
        seen_outputs: set[str] = set()

        for item in planned_calls:
            output_key = self._output_key_for_name(item.name, tools)
            if not output_key or output_key in seen_outputs:
                continue
            enriched_calls.append(
                MCPToolCall(
                    name=item.name,
                    arguments=self._enrich_arguments(item.name, dict(item.arguments), parsed_request, profile),
                )
            )
            seen_outputs.add(output_key)

        for fallback in self._fallback_tool_calls(parsed_request, profile, tool_by_output):
            output_key = self._output_key_for_name(fallback.name, tools)
            if output_key and output_key not in seen_outputs:
                enriched_calls.append(fallback)
                seen_outputs.add(output_key)

        return enriched_calls

    def _fallback_tool_calls(
        self,
        parsed_request: ParsedTripRequest,
        profile: UserProfile,
        tool_by_output: Dict[str, str],
    ) -> List[MCPToolCall]:
        city = parsed_request.city or "北京"
        days = parsed_request.travel_days or 3
        preferences = self._merge_preferences(parsed_request, profile)
        hotel_budget_min, hotel_budget_max = self._resolve_hotel_budget(parsed_request, profile)

        return [
            MCPToolCall(
                name=tool_by_output["attractions"],
                arguments={
                    "city": city,
                    "preferences": preferences,
                    "limit": max(days * 4, 8),
                },
            ),
            MCPToolCall(
                name=tool_by_output["weather"],
                arguments={
                    "city": city,
                    "days": days,
                    "start_date": parsed_request.start_date,
                },
            ),
            MCPToolCall(
                name=tool_by_output["hotels"],
                arguments={
                    "city": city,
                    "budget_min": hotel_budget_min,
                    "budget_max": hotel_budget_max,
                    "limit": max(3, min(6, days + 1)),
                },
            ),
            MCPToolCall(
                name=tool_by_output["daily_meals"],
                arguments={
                    "city": city,
                    "preferences": preferences,
                    "days": days,
                },
            ),
        ]

    def _enrich_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        parsed_request: ParsedTripRequest,
        profile: UserProfile,
    ) -> Dict[str, Any]:
        city = parsed_request.city or "北京"
        days = parsed_request.travel_days or 3
        preferences = self._merge_preferences(parsed_request, profile)
        hotel_budget_min, hotel_budget_max = self._resolve_hotel_budget(parsed_request, profile)

        if tool_name == "trip.search_attractions":
            arguments.setdefault("city", city)
            arguments.setdefault("preferences", preferences)
            arguments.setdefault("limit", max(days * 4, 8))
        elif tool_name == "trip.get_weather":
            arguments.setdefault("city", city)
            arguments.setdefault("days", days)
            arguments.setdefault("start_date", parsed_request.start_date)
        elif tool_name == "trip.recommend_hotels":
            arguments.setdefault("city", city)
            arguments.setdefault("budget_min", hotel_budget_min)
            arguments.setdefault("budget_max", hotel_budget_max)
            arguments.setdefault("limit", max(3, min(6, days + 1)))
        elif tool_name == "trip.recommend_daily_meals":
            arguments.setdefault("city", city)
            arguments.setdefault("preferences", preferences)
            arguments.setdefault("days", days)

        return arguments

    @staticmethod
    def _output_key_for_name(name: str, tools: Sequence[MCPToolDescriptor]) -> str:
        for item in tools:
            if item.name == name:
                return item.output_key
        return ""

    @staticmethod
    def _aggregate_candidates(results: Sequence[Any]) -> Dict[str, Any]:
        candidates: Dict[str, Any] = {
            "attractions": [],
            "weather": [],
            "hotels": [],
            "daily_meals": [],
        }
        for item in results:
            if item.status != "ok" or item.output_key not in candidates:
                continue
            candidates[item.output_key] = item.payload or []
        return candidates

    @staticmethod
    def _merge_preferences(parsed_request: ParsedTripRequest, profile: UserProfile) -> List[str]:
        return list(
            dict.fromkeys([*(parsed_request.preferences or []), *(profile.attraction_preference or [])])
        )

    @staticmethod
    def _resolve_hotel_budget(parsed_request: ParsedTripRequest, profile: UserProfile) -> tuple[int | None, int | None]:
        hotel_budget_min = profile.hotel_budget_min
        hotel_budget_max = profile.hotel_budget_max
        if parsed_request.total_budget and (hotel_budget_min is None or hotel_budget_max is None):
            days = max(parsed_request.travel_days or 1, 1)
            per_day = max(parsed_request.total_budget // days, 200)
            hotel_budget_min = int(per_day * 0.35)
            hotel_budget_max = int(per_day * 0.55)
        return hotel_budget_min, hotel_budget_max
