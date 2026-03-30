"""Schemas for MCP-style tool registration and execution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_key: str
    tags: List[str] = Field(default_factory=list)


class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    tool_name: str
    output_key: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    status: str
    payload: Any = None
    error: Optional[str] = None
    duration_ms: int = 0


class MCPExecutionReport(BaseModel):
    available_tools: List[MCPToolDescriptor] = Field(default_factory=list)
    tool_calls: List[MCPToolCall] = Field(default_factory=list)
    results: List[MCPToolResult] = Field(default_factory=list)
