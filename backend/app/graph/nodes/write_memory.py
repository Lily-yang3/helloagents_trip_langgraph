"""Graph node: write stable preference patch and trip history to long-term memory."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.schemas.trip import TripPlan
from app.tools.memory_tool import MemoryTool


def make_write_memory_node(memory_tool: MemoryTool) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        user_id = str(state.get("user_id") or "guest")
        session_id = str(state.get("session_id") or "")
        thread_id = str(state.get("thread_id") or "")
        assistant_message = str(state.get("assistant_message") or "")

        patch = dict(state.get("memory_patch") or {})
        if patch:
            profile = memory_tool.update_profile(user_id=user_id, patch=patch)
            profile_payload = profile.model_dump()
        else:
            profile = memory_tool.load_profile(user_id=user_id)
            profile_payload = profile.model_dump()

        structured_plan = None
        if state.get("structured_plan"):
            structured_plan = TripPlan.model_validate(state.get("structured_plan"))

        memory_tool.write_trip_history(
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            assistant_message=assistant_message,
            structured_plan=structured_plan,
        )

        messages = list(state.get("messages") or [])
        if assistant_message:
            messages.append({"role": "assistant", "content": assistant_message})

        return {
            "memory_profile": profile_payload,
            "messages": messages,
        }

    return node
