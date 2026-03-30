"""Application dependency container and singleton wiring."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import BACKEND_ROOT, get_settings
from app.graph import PlannerGraphDeps, build_planner_graph
from app.memory.history_store import HistoryStore
from app.memory.long_term import LongTermMemory
from app.memory.profile_store import ProfileStore
from app.memory.short_term import SessionStore
from app.memory.summarizer import PreferenceSummarizer
from app.services.planner_service import PlannerService
from app.services.request_parser import RequestParser
from app.services.session_service import SessionService
from app.tools.budget_tool import BudgetTool
from app.tools.food_tool import FoodTool
from app.tools.hotel_tool import HotelTool
from app.tools.map_tool import MapTool
from app.tools.memory_tool import MemoryTool
from app.tools.weather_tool import WeatherTool


@dataclass
class ServiceContainer:
    session_service: SessionService
    planner_service: PlannerService
    memory_tool: MemoryTool
    summarizer: PreferenceSummarizer


def _resolve_path(path_str: str) -> str:
    path = Path(path_str)
    if path.is_absolute():
        return str(path)
    return str(BACKEND_ROOT / path)


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    settings = get_settings()

    profile_store = ProfileStore(db_path=_resolve_path(settings.profile_db))
    history_store = HistoryStore(db_path=_resolve_path(settings.trips_db))
    long_term_memory = LongTermMemory(profile_store=profile_store, history_store=history_store)
    memory_tool = MemoryTool(memory=long_term_memory)

    session_store = SessionStore(db_path=_resolve_path(settings.session_db))
    session_service = SessionService(store=session_store)

    parser = RequestParser()
    summarizer = PreferenceSummarizer()

    graph_deps = PlannerGraphDeps(
        map_tool=MapTool(),
        weather_tool=WeatherTool(),
        hotel_tool=HotelTool(),
        food_tool=FoodTool(),
        budget_tool=BudgetTool(),
        memory_tool=memory_tool,
        parser=parser,
        summarizer=summarizer,
        checkpoint_db=_resolve_path(settings.checkpoint_db),
        checkpointer_mode=settings.checkpointer_mode,
    )
    graph_app = build_planner_graph(graph_deps)

    planner_service = PlannerService(graph_app=graph_app, session_store=session_store)

    return ServiceContainer(
        session_service=session_service,
        planner_service=planner_service,
        memory_tool=memory_tool,
        summarizer=summarizer,
    )
