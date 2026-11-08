"""Pydantic request/response schemas for the FastAPI surface."""
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    thread_id: str | None = None
    log_file: str | None = Field(default=None, description="Path to a flight-log CSV for maintenance/anomaly runs")
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class ApproveRequest(BaseModel):
    approval_id: str = Field(min_length=1)
    approved: bool
    decided_by: str = Field(default="operator", max_length=120)


class ApprovalOut(BaseModel):
    id: str
    thread_id: str
    created_at: str | None
    action: str
    summary: str
    decision: str
    decided_by: str | None
    run_id: str | None


class HealthOut(BaseModel):
    status: str
    version: str
    app_env: str
    llm_available: bool
    embedding_provider: str
    vector_backend: str
    vector_store_docs: int | None
    langsmith_tracing: bool


class LogsOut(BaseModel):
    tickets: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    runs: list[dict[str, Any]]
    flight_logs: list[str]
