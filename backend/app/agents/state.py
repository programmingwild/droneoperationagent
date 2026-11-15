"""Typed graph state (LangGraph)."""
from typing import Any, Literal, TypedDict

Classification = Literal["mission_planning", "maintenance", "regulation", "anomaly"]


class AgentState(TypedDict, total=False):
    # run context
    run_id: str
    thread_id: str
    query: str
    log_file: str | None
    lat: float | None
    lon: float | None
    history: list[dict[str, str]]  # prior user/assistant turns of this conversation

    # triage
    classification: Classification
    classification_conf: float

    # retrieval + tool outputs
    retrieved: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    retrieval_confident: bool
    tool_results: dict[str, Any]

    # answer construction
    answer: str
    recommended_action: str | None  # TAKEOFF | ARM | HOLD | INSPECT | LAND | NONE

    # HITL
    requires_approval: bool
    approval_id: str | None
    approval_action: str | None
    approval_summary: str | None
    approval_decision: str | None  # APPROVED | REJECTED (injected on resume)
    decided_by: str | None

    # observability
    trace: list[str]
    errors: list[str]

    # final payload
    final: dict[str, Any]
