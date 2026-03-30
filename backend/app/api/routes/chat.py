"""Chat/session APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_service_container
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    CreateSessionRequest,
    CreateSessionResponse,
)
from app.services.dependencies import ServiceContainer

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/session", response_model=CreateSessionResponse)
def create_session(
    request: CreateSessionRequest,
    container: ServiceContainer = Depends(get_service_container),
) -> CreateSessionResponse:
    user_id = request.user_id or container.session_service.new_user_id()
    session = container.session_service.create_session(user_id=user_id)
    return CreateSessionResponse(
        success=True,
        user_id=user_id,
        session_id=session.session_id,
        thread_id=session.thread_id,
    )


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(
    request: ChatMessageRequest,
    container: ServiceContainer = Depends(get_service_container),
) -> ChatMessageResponse:
    try:
        return container.planner_service.process_message(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"处理消息失败: {exc}") from exc
