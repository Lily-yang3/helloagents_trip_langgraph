"""Memory tool facade for graph nodes."""

from __future__ import annotations

from typing import Any, Dict, List

from app.memory.long_term import LongTermMemory
from app.schemas.trip import TripHistoryItem, TripPlan
from app.schemas.user import UserProfile


class MemoryTool:
    def __init__(self, memory: LongTermMemory) -> None:
        self.memory = memory

    def load_profile(self, user_id: str) -> UserProfile:
        return self.memory.get_profile(user_id)

    def update_profile(self, user_id: str, patch: Dict[str, Any]) -> UserProfile:
        return self.memory.update_profile(user_id=user_id, patch=patch)

    def write_trip_history(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        assistant_message: str,
        structured_plan: TripPlan | None,
    ) -> TripHistoryItem:
        return self.memory.add_trip_history(
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            assistant_message=assistant_message,
            structured_plan=structured_plan,
        )

    def list_history(self, user_id: str, limit: int = 20) -> List[TripHistoryItem]:
        return self.memory.list_history(user_id=user_id, limit=limit)
