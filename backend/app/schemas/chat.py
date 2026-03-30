"""Chat/session API schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .trip import TripPlan


class CreateSessionRequest(BaseModel):
    user_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    success: bool = True
    session_id: str
    thread_id: str
    user_id: str


class ChatMessageRequest(BaseModel):
    session_id: str
    user_id: str
    message: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    assistant_message: str
    structured_plan: Optional[TripPlan] = None
    need_clarification: bool
    session_id: str
    thread_id: str
