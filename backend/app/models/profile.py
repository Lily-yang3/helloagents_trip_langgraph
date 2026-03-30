"""Profile patch model for long-term memory updates."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProfilePatch(BaseModel):
    travel_style: Optional[str] = None
    hotel_budget_min: Optional[int] = None
    hotel_budget_max: Optional[int] = None
    food_preference: List[str] = Field(default_factory=list)
    attraction_preference: List[str] = Field(default_factory=list)
    transport_preference: Optional[str] = None
    pace_preference: Optional[str] = None
    avoid_tags: List[str] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
