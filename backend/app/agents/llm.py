"""LLM provider abstraction.

Production: OpenAI or Groq via langchain-openai (Groq exposes an OpenAI-compatible API).
Offline fallback: deterministic extractive composer (NOT a generative model) — clearly labelled in
outputs as degraded, grounding answers only in retrieved chunks. No fabricated content.
"""
import logging
from typing import Any

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


def resolve_provider(settings: Settings | None = None) -> str:
    """Resolve the effective chat provider: openai | groq | local."""
    s = settings or get_settings()
    provider = (s.llm_provider or "auto").lower().strip()
    if provider in {"openai", "groq", "local"}:
        return provider
    # auto: prefer OpenAI (if credited), then Groq, then offline
    if s.openai_api_key:
        return "openai"
    if s.groq_api_key:
        return "groq"
    return "local"


def llm_available() -> bool:
    s = get_settings()
    provider = resolve_provider(s)
    if provider == "openai":
        return bool(s.openai_api_key)
    if provider == "groq":
        return bool(s.groq_api_key)
    return False


def get_chat_model():
    s = get_settings()
    if not llm_available():
        return None
    from langchain_openai import ChatOpenAI

    if resolve_provider(s) == "groq":
        return ChatOpenAI(
            model=s.groq_model,
            api_key=s.groq_api_key,
            base_url=s.groq_base_url,
            temperature=0,
            timeout=30,
            max_retries=2,
        )
    return ChatOpenAI(
        model=s.openai_model,
        api_key=s.openai_api_key,
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
        "[OFFLINE MODE — no LLM API key configured: extractive answer from retrieved passages, "
        "not a generated response]\n\n"
        f"Most relevant evidence for your question:\n\n{top}\n\n"
        "Set OPENAI_API_KEY or GROQ_API_KEY to enable full generative answers with citations."
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
