"""User profile and feedback APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_service_container
from app.schemas.user import FeedbackRequest, FeedbackResponse, UserProfile
from app.services.dependencies import ServiceContainer

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile/{user_id}", response_model=UserProfile)
def get_profile(
    user_id: str,
    container: ServiceContainer = Depends(get_service_container),
) -> UserProfile:
    return container.memory_tool.load_profile(user_id=user_id)


@router.post("/feedback", response_model=FeedbackResponse)
def write_feedback(
    request: FeedbackRequest,
    container: ServiceContainer = Depends(get_service_container),
) -> FeedbackResponse:
    try:
        patch = container.summarizer.from_feedback(
            feedback_text=request.feedback_text,
            rating=request.rating,
        )
        profile = container.memory_tool.update_profile(user_id=request.user_id, patch=patch)
        return FeedbackResponse(success=True, message="反馈已写入用户画像", profile=profile)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"写入反馈失败: {exc}") from exc
