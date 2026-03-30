"""Trip history APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_service_container
from app.schemas.trip import TripHistoryResponse
from app.services.dependencies import ServiceContainer

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/history/{user_id}", response_model=TripHistoryResponse)
def list_history(
    user_id: str,
    container: ServiceContainer = Depends(get_service_container),
) -> TripHistoryResponse:
    items = container.memory_tool.list_history(user_id=user_id, limit=30)
    return TripHistoryResponse(success=True, user_id=user_id, items=items)
