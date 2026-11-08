"""LLM provider abstraction.

Production: OpenAI via langchain-openai (set OPENAI_API_KEY).
Offline fallback: deterministic extractive composer (NOT a generative model) — clearly labelled in
outputs as degraded, grounding answers only in retrieved chunks. No fabricated content.
"""
import logging
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)


def llm_available() -> bool:
    settings = get_settings()
    if settings.llm_provider == "local":
        return False
    return bool(settings.openai_api_key)


def get_chat_model():
    settings = get_settings()
    if not llm_available():
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        timeout=30,
        max_retries=2,
    )


def chat(system: str, user: str) -> str:
    model = get_chat_model()
    if model is None:
        raise RuntimeError("LLM_UNAVAILABLE")
    resp = model.invoke([("system", system), ("human", user)])
    return resp.content if isinstance(resp.content, str) else str(resp.content)


def grounded_answer(query: str, context: str, citations: list[dict]) -> str:
    """Answer strictly from retrieved context. Falls back to labelled extractive mode offline."""
    system = (
        "You are Drone Ops Agent, a UAS fleet maintenance and mission-readiness expert. "
        "Answer ONLY using the numbered context passages. Cite them as [n]. "
        "If the context does not contain the answer, say so plainly and refuse to guess. "
        "Never invent regulation section numbers, limits, or procedures."
    )
    user = f"Question: {query}\n\nContext:\n{context}\n\nAnswer with [n] citations."
    if llm_available():
        return chat(system, user)
    # Offline extractive fallback — quotes the top evidence instead of generating.
    excerpts = []
    for block in context.split("\n\n["):
        block = block if block.startswith("[") else "[" + block
        excerpts.append(block.strip())
    top = "\n".join(excerpts[:2])
    return (
        "[OFFLINE MODE — no OPENAI_API_KEY configured: extractive answer from retrieved passages, "
        "not a generated response]\n\n"
        f"Most relevant evidence for your question:\n\n{top}\n\n"
        "Set OPENAI_API_KEY to enable full generative answers with citations."
    )


def triage_with_llm(query: str) -> dict[str, Any] | None:
    model = get_chat_model()
    if model is None:
        return None
    from pydantic import BaseModel, Field
    from typing import Literal

    class TriageResult(BaseModel):
        classification: Literal["mission_planning", "maintenance", "regulation", "anomaly"]
        confidence: float = Field(ge=0.0, le=1.0)
        reason: str

    try:
        structured = model.with_structured_output(TriageResult)
        result = structured.invoke([
            ("system",
             "Classify the UAS operator query into exactly one route: "
             "mission_planning (flight planning, range, payload, go/no-go), "
             "maintenance (logs, tickets, wear, faults), "
             "regulation (legality, FAA/EASA/DGCA, airspace, approvals to fly), "
             "anomaly (unexpected telemetry, suspected fault, incident triage)."),
            ("human", query),
        ])
        return result.model_dump()
    except Exception as exc:  # provider or schema failure -> caller falls back to keywords
        logger.warning("triage_llm_failed", extra={"error": str(exc)})
        return None
