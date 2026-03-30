"""User profile and feedback schemas."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    travel_style: Optional[str] = None
    hotel_budget_min: Optional[int] = None
    hotel_budget_max: Optional[int] = None
    food_preference: List[str] = Field(default_factory=list)
    attraction_preference: List[str] = Field(default_factory=list)
    transport_preference: Optional[str] = None
    pace_preference: Optional[str] = None
    avoid_tags: List[str] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    last_updated: Optional[str] = None


class FeedbackRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    thread_id: Optional[str] = None
    feedback_text: str
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    success: bool
    message: str
    profile: UserProfile
