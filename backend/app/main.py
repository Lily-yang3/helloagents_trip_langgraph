"""FastAPI entrypoint for LangGraph personalized trip planner."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, trips, user
from app.core.config import get_settings, print_settings, validate_settings
from app.core.logging import setup_logging
from app.schemas.common import HealthResponse
from app.services.dependencies import get_container

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="LangGraph-based personalized trip planner with short/long-term memory",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(trips.router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    setup_logging(settings.log_level)
    validate_settings()
    print_settings()

    # Warm up singleton dependencies to surface config/runtime errors early.
    container = get_container()
    tool_names = ", ".join(item.name for item in container.mcp_service.list_tools())
    print(f"[mcp] started global tool service with {len(container.mcp_service.list_tools())} tools: {tool_names}")


@app.get("/", response_model=dict)
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy", service=settings.app_name, version=settings.app_version)
