"""SQLite-backed trip history store."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.schemas.trip import TripHistoryItem, TripPlan


class HistoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trip_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    assistant_message TEXT NOT NULL,
                    structured_plan_json TEXT
                )
                """
            )
            conn.commit()

    def add_history(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        assistant_message: str,
        structured_plan: Optional[TripPlan],
    ) -> TripHistoryItem:
        item_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        plan_json = structured_plan.model_dump_json() if structured_plan else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trip_history (
                    id, user_id, session_id, thread_id, created_at, assistant_message, structured_plan_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, user_id, session_id, thread_id, created_at, assistant_message, plan_json),
            )
            conn.commit()

        return TripHistoryItem(
            id=item_id,
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            created_at=created_at,
            assistant_message=assistant_message,
            structured_plan=structured_plan,
        )

    def list_by_user(self, user_id: str, limit: int = 20) -> List[TripHistoryItem]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, session_id, thread_id, created_at, assistant_message, structured_plan_json
                FROM trip_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        items: List[TripHistoryItem] = []
        for row in rows:
            plan = None
            if row["structured_plan_json"]:
                plan = TripPlan.model_validate(json.loads(row["structured_plan_json"]))
            items.append(
                TripHistoryItem(
                    id=row["id"],
                    user_id=row["user_id"],
                    session_id=row["session_id"],
                    thread_id=row["thread_id"],
                    created_at=row["created_at"],
                    assistant_message=row["assistant_message"],
                    structured_plan=plan,
                )
            )
        return items
