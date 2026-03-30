"""FastAPI dependency helpers."""

from __future__ import annotations

from app.services.dependencies import ServiceContainer, get_container


def get_service_container() -> ServiceContainer:
    return get_container()
