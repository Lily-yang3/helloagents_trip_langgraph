"""LangGraph workflow assembly for personalized trip planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    make_ask_clarification_node,
    make_budget_check_node,
    make_budget_revise_node,
    make_build_candidate_plan_node,
    make_check_missing_info_node,
    make_generate_output_node,
    make_load_user_memory_node,
    make_parse_user_request_node,
    make_personalize_rerank_node,
    make_retrieve_candidates_node,
    make_write_memory_node,
)
from app.graph.router import route_budget, route_missing_info
from app.graph.state import PlannerState
from app.memory.short_term import build_checkpointer
from app.memory.summarizer import PreferenceSummarizer
from app.services.request_parser import RequestParser
from app.tools.budget_tool import BudgetTool
from app.tools.food_tool import FoodTool
from app.tools.hotel_tool import HotelTool
from app.tools.map_tool import MapTool
from app.tools.memory_tool import MemoryTool
from app.tools.weather_tool import WeatherTool


@dataclass
class PlannerGraphDeps:
    map_tool: MapTool
    weather_tool: WeatherTool
    hotel_tool: HotelTool
    food_tool: FoodTool
    budget_tool: BudgetTool
    memory_tool: MemoryTool
    parser: RequestParser
    summarizer: PreferenceSummarizer
    checkpoint_db: str
    checkpointer_mode: str = "memory"


def build_planner_graph(deps: PlannerGraphDeps) -> Any:
    """Build and compile planner graph with optional persistent checkpointer."""
    graph = StateGraph(PlannerState)

    graph.add_node("load_user_memory", make_load_user_memory_node(deps.memory_tool))
    graph.add_node("parse_user_request", make_parse_user_request_node(deps.parser, deps.summarizer))
    graph.add_node("check_missing_info", make_check_missing_info_node(deps.parser))
    graph.add_node("ask_clarification", make_ask_clarification_node(deps.parser))
    graph.add_node(
        "retrieve_candidates",
        make_retrieve_candidates_node(
            map_tool=deps.map_tool,
            weather_tool=deps.weather_tool,
            hotel_tool=deps.hotel_tool,
            food_tool=deps.food_tool,
        ),
    )
    graph.add_node("build_candidate_plan", make_build_candidate_plan_node())
    graph.add_node("personalize_rerank", make_personalize_rerank_node())
    graph.add_node("budget_check", make_budget_check_node(deps.budget_tool))
    graph.add_node("budget_revise", make_budget_revise_node(deps.budget_tool))
    graph.add_node("generate_output", make_generate_output_node())
    graph.add_node("write_memory", make_write_memory_node(deps.memory_tool))

    graph.add_edge(START, "load_user_memory")
    graph.add_edge("load_user_memory", "parse_user_request")
    graph.add_edge("parse_user_request", "check_missing_info")

    graph.add_conditional_edges(
        "check_missing_info",
        route_missing_info,
        {
            "ask_clarification": "ask_clarification",
            "retrieve_candidates": "retrieve_candidates",
        },
    )

    graph.add_edge("ask_clarification", END)

    graph.add_edge("retrieve_candidates", "build_candidate_plan")
    graph.add_edge("build_candidate_plan", "personalize_rerank")
    graph.add_edge("personalize_rerank", "budget_check")

    graph.add_conditional_edges(
        "budget_check",
        route_budget,
        {
            "budget_revise": "budget_revise",
            "generate_output": "generate_output",
        },
    )

    graph.add_edge("budget_revise", "budget_check")
    graph.add_edge("generate_output", "write_memory")
    graph.add_edge("write_memory", END)

    checkpointer = build_checkpointer(deps.checkpoint_db, mode=deps.checkpointer_mode)
    return graph.compile(checkpointer=checkpointer)
