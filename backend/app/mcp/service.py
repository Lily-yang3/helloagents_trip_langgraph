"""In-process MCP-style service for tool registration and async execution."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List

from pydantic import BaseModel

from app.mcp.models import MCPToolCall, MCPToolDescriptor, MCPToolResult
from app.tools.food_tool import FoodTool
from app.tools.hotel_tool import HotelTool
from app.tools.map_tool import MapTool
from app.tools.weather_tool import WeatherTool

ToolHandler = Callable[..., Any]


def _serialize_payload(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_serialize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_payload(item) for key, item in value.items()}
    return value


@dataclass
class MCPToolRegistration:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_key: str
    handler: ToolHandler
    tags: List[str] = field(default_factory=list)

    def descriptor(self) -> MCPToolDescriptor:
        return MCPToolDescriptor(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            output_key=self.output_key,
            tags=list(self.tags),
        )


class GlobalMCPService:
    """Registry that mimics MCP tool discovery and execution."""

    def __init__(self, tools: Iterable[MCPToolRegistration] | None = None) -> None:
        self._tools: Dict[str, MCPToolRegistration] = {}
        self._available_tools: List[MCPToolDescriptor] = []
        self._started = False
        for item in tools or []:
            self.register_tool(item)

    @property
    def started(self) -> bool:
        return self._started

    def register_tool(self, tool: MCPToolRegistration) -> None:
        self._tools[tool.name] = tool
        if self._started:
            self._available_tools = [item.descriptor() for item in self._tools.values()]

    def start(self) -> List[MCPToolDescriptor]:
        self._available_tools = [item.descriptor() for item in self._tools.values()]
        self._started = True
        return self.list_tools()

    def list_tools(self) -> List[MCPToolDescriptor]:
        if not self._started:
            return self.start()
        return list(self._available_tools)

    async def call_tool(self, name: str, arguments: Dict[str, Any] | None = None) -> MCPToolResult:
        arguments = dict(arguments or {})
        registration = self._tools.get(name)
        if registration is None:
            return MCPToolResult(
                tool_name=name,
                output_key="unknown",
                arguments=arguments,
                status="error",
                error=f"Tool not found: {name}",
            )

        started_at = time.perf_counter()
        try:
            payload = await self._invoke_handler(registration.handler, arguments)
            return MCPToolResult(
                tool_name=registration.name,
                output_key=registration.output_key,
                arguments=arguments,
                status="ok",
                payload=_serialize_payload(payload),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )
        except Exception as exc:  # pragma: no cover
            return MCPToolResult(
                tool_name=registration.name,
                output_key=registration.output_key,
                arguments=arguments,
                status="error",
                error=str(exc),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
            )

    async def call_tools(self, tool_calls: Iterable[MCPToolCall]) -> List[MCPToolResult]:
        calls = list(tool_calls)
        if not calls:
            return []
        return list(await asyncio.gather(*(self.call_tool(call.name, call.arguments) for call in calls)))

    @staticmethod
    async def _invoke_handler(handler: ToolHandler, arguments: Dict[str, Any]) -> Any:
        if inspect.iscoroutinefunction(handler):
            return await handler(**arguments)

        result = await asyncio.to_thread(handler, **arguments)
        if inspect.isawaitable(result):
            return await result
        return result


NULLABLE_INTEGER_SCHEMA = {
    "anyOf": [
        {"type": "integer"},
        {"type": "null"},
    ]
}


def build_builtin_mcp_tools(
    map_tool: MapTool,
    weather_tool: WeatherTool,
    hotel_tool: HotelTool,
    food_tool: FoodTool,
) -> List[MCPToolRegistration]:
    return [
        MCPToolRegistration(
            name="trip.search_attractions",
            description="Search POIs and attraction candidates for the requested city and interests.",
            input_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["city"],
            },
            output_key="attractions",
            handler=map_tool.search_attractions,
            tags=["travel", "poi", "external", "readonly"],
        ),
        MCPToolRegistration(
            name="trip.get_weather",
            description="Fetch weather forecasts for the target city and travel dates.",
            input_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "days": {"type": "integer", "minimum": 1, "maximum": 15},
                    "start_date": {"type": "string"},
                },
                "required": ["city", "days"],
            },
            output_key="weather",
            handler=weather_tool.get_weather,
            tags=["travel", "weather", "external", "readonly"],
        ),
        MCPToolRegistration(
            name="trip.recommend_hotels",
            description="Recommend hotels based on city and expected daily budget range.",
            input_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "budget_min": NULLABLE_INTEGER_SCHEMA,
                    "budget_max": NULLABLE_INTEGER_SCHEMA,
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["city"],
            },
            output_key="hotels",
            handler=hotel_tool.recommend_hotels,
            tags=["travel", "hotel", "pricing", "readonly"],
        ),
        MCPToolRegistration(
            name="trip.recommend_daily_meals",
            description="Generate daily meal suggestions from city and traveler preferences.",
            input_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "preferences": {"type": "array", "items": {"type": "string"}},
                    "days": {"type": "integer", "minimum": 1, "maximum": 15},
                },
                "required": ["city", "days"],
            },
            output_key="daily_meals",
            handler=food_tool.recommend_daily_meals,
            tags=["travel", "food", "readonly"],
        ),
    ]
