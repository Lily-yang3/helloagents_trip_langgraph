"""Planner service that executes the LangGraph workflow."""

from __future__ import annotations

from typing import Any

from app.memory.short_term import SessionStore
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.schemas.trip import TripPlan


class PlannerService:
    def __init__(self, graph_app: Any, session_store: SessionStore) -> None:
        self.graph_app = graph_app
        self.session_store = session_store

    def process_message(self, request: ChatMessageRequest) -> ChatMessageResponse:
        session = self.session_store.get_session(request.session_id)
        if session is None:
            raise ValueError("session_id 不存在，请先调用 /api/chat/session")
        if session.user_id != request.user_id:
            raise ValueError("session_id 与 user_id 不匹配")

        state_input = {
            "user_id": request.user_id,
            "session_id": session.session_id,
            "thread_id": session.thread_id,
            "user_message": request.message,
        }

        graph_output = self.graph_app.invoke(
            state_input,
            config={"configurable": {"thread_id": session.thread_id}},
        )

        self.session_store.touch_session(session.session_id)

        structured_plan = None
        if graph_output.get("structured_plan"):
            structured_plan = TripPlan.model_validate(graph_output["structured_plan"])

        return ChatMessageResponse(
            assistant_message=str(graph_output.get("assistant_message") or ""),
            structured_plan=structured_plan,
            need_clarification=bool(graph_output.get("need_clarification")),
            session_id=session.session_id,
            thread_id=session.thread_id,
        )
