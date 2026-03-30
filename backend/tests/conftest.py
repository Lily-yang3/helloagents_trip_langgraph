"""Test fixtures for backend services."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.dependencies import get_container


@pytest.fixture()
def isolated_runtime(tmp_path: Path):
    settings = get_settings()

    settings.data_dir = str(tmp_path)
    settings.checkpoint_db = str(tmp_path / "checkpoints.sqlite")
    settings.profile_db = str(tmp_path / "profiles.sqlite")
    settings.trips_db = str(tmp_path / "trips.sqlite")
    settings.session_db = str(tmp_path / "sessions.sqlite")
    settings.checkpointer_mode = "memory"
    settings.mock_mode = True
    settings.unsplash_access_key = ""
    settings.unsplash_secret_key = ""
    settings.ensure_data_dirs()

    get_container.cache_clear()
    container = get_container()
    yield container
    get_container.cache_clear()
