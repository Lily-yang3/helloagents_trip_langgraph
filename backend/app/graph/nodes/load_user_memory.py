"""Graph node: load long-term user memory profile."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.tools.memory_tool import MemoryTool


def make_load_user_memory_node(memory_tool: MemoryTool) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        user_id = str(state.get("user_id") or "guest")
        profile = memory_tool.load_profile(user_id)

        return {
            "memory_profile": profile.model_dump(),
            "messages": list(state.get("messages") or []),
        }

    return node
