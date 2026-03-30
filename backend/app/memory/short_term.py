"""Session registry and LangGraph checkpointer factory."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except Exception:  # pragma: no cover
    SqliteSaver = None


@dataclass
class SessionRecord:
    session_id: str
    thread_id: str
    user_id: str
    created_at: str
    updated_at: str


class SessionStore:
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
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_session(self, user_id: str) -> SessionRecord:
        session_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, thread_id, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, thread_id, user_id, now, now),
            )
            conn.commit()
        return SessionRecord(
            session_id=session_id,
            thread_id=thread_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id, thread_id, user_id, created_at, updated_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return SessionRecord(
            session_id=row["session_id"],
            thread_id=row["thread_id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def touch_session(self, session_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
            conn.commit()


def build_checkpointer(checkpoint_db: str, mode: str = "memory"):
    """Build checkpointer.

    mode=memory: deterministic default for local/dev stability.
    mode=sqlite: persistent checkpointing via sqlite saver (best effort).
    """
    if (mode or "").lower() == "sqlite" and SqliteSaver is not None:
        try:
            saver_or_cm = SqliteSaver.from_conn_string(checkpoint_db)
            # langgraph-checkpoint-sqlite v3 returns a context manager.
            if hasattr(saver_or_cm, "__enter__") and hasattr(saver_or_cm, "__exit__"):
                saver = saver_or_cm.__enter__()
                # Keep a reference so GC does not close the context unexpectedly.
                setattr(saver, "_managed_context", saver_or_cm)
                return saver
            return saver_or_cm
        except Exception as exc:  # pragma: no cover
            print(f"[checkpointer-warning] sqlite checkpointer unavailable: {exc}")
    return MemorySaver()
