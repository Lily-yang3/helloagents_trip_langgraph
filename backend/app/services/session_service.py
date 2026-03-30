"""Session lifecycle service."""

from __future__ import annotations

import uuid

from app.memory.short_term import SessionRecord, SessionStore


class SessionService:
    def __init__(self, store: SessionStore) -> None:
        self.store = store

    @staticmethod
    def new_user_id() -> str:
        return f"user_{uuid.uuid4().hex[:10]}"

    def create_session(self, user_id: str) -> SessionRecord:
        return self.store.create_session(user_id=user_id)

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self.store.get_session(session_id=session_id)

    def validate_session_owner(self, session_id: str, user_id: str) -> SessionRecord:
        session = self.get_session(session_id=session_id)
        if session is None:
            raise ValueError("session_id 不存在，请先创建会话")
        if session.user_id != user_id:
            raise ValueError("user_id 与 session_id 不匹配")
        return session

    def touch_session(self, session_id: str) -> None:
        self.store.touch_session(session_id=session_id)
