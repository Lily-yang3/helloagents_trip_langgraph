"""Graph node: parse latest user message into structured request fields."""

from __future__ import annotations

from typing import Callable

from app.graph.state import PlannerState
from app.memory.summarizer import PreferenceSummarizer
from app.services.request_parser import RequestParser


def make_parse_user_request_node(
    parser: RequestParser,
    summarizer: PreferenceSummarizer,
) -> Callable[[PlannerState], dict]:
    def node(state: PlannerState) -> dict:
        user_message = str(state.get("user_message") or "").strip()
        previous_request = dict(state.get("parsed_request") or {})

        parsed = parser.parse(user_message, previous=previous_request)
        memory_patch = summarizer.from_request(parsed, raw_text=user_message)

        messages = list(state.get("messages") or [])
        if user_message:
            messages.append({"role": "user", "content": user_message})

        return {
            "messages": messages,
            "parsed_request": parsed.model_dump(),
            "memory_patch": memory_patch,
        }

    return node
