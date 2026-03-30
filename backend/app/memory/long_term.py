"""Facade for long-term memory operations."""

from __future__ import annotations

from typing import Any, Dict, List

from app.memory.history_store import HistoryStore
from app.memory.profile_store import ProfileStore
from app.schemas.trip import TripHistoryItem, TripPlan
from app.schemas.user import UserProfile


class LongTermMemory:
    def __init__(self, profile_store: ProfileStore, history_store: HistoryStore) -> None:
        self.profile_store = profile_store
        self.history_store = history_store

    def get_profile(self, user_id: str) -> UserProfile:
        return self.profile_store.get_profile(user_id)

    def update_profile(self, user_id: str, patch: Dict[str, Any]) -> UserProfile:
        return self.profile_store.merge_patch(user_id=user_id, patch=patch)

    def add_trip_history(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        assistant_message: str,
        structured_plan: TripPlan | None,
    ) -> TripHistoryItem:
        return self.history_store.add_history(
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            assistant_message=assistant_message,
            structured_plan=structured_plan,
        )

    def list_history(self, user_id: str, limit: int = 20) -> List[TripHistoryItem]:
        return self.history_store.list_by_user(user_id=user_id, limit=limit)
