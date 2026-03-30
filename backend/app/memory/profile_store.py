"""SQLite-backed user profile store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from app.schemas.user import UserProfile


class ProfileStore:
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
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_profile(self, user_id: str) -> UserProfile:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_json FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return UserProfile(user_id=user_id)
        return UserProfile.model_validate(json.loads(row["profile_json"]))

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        profile.last_updated = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (user_id, profile_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_json=excluded.profile_json,
                    updated_at=excluded.updated_at
                """,
                (profile.user_id, profile.model_dump_json(), profile.last_updated),
            )
            conn.commit()
        return profile

    def merge_patch(self, user_id: str, patch: Dict[str, Any]) -> UserProfile:
        profile = self.get_profile(user_id)
        data = profile.model_dump()

        for key, value in patch.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                current = data.get(key) or []
                if not isinstance(current, list):
                    current = []
                merged = list(dict.fromkeys([*current, *value]))
                data[key] = merged
            elif isinstance(value, dict):
                current = data.get(key) or {}
                if not isinstance(current, dict):
                    current = {}
                current.update(value)
                data[key] = current
            else:
                data[key] = value

        merged_profile = UserProfile.model_validate(data)
        return self.upsert_profile(merged_profile)
