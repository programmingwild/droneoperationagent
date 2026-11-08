"""Retrieval with citations and confidence scoring."""
from pydantic import BaseModel

from ..config import get_settings
from .embeddings import embed_query
from .vectorstore import get_vector_store


class Citation(BaseModel):
    source: str
    section: str
    page: int | None = None
    score: float


class RetrievalResult(BaseModel):
    chunks: list[dict]
    citations: list[Citation]
    top_score: float
    confident: bool


def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    doc_type: str | None = None,
    regulation: str | None = None,
) -> RetrievalResult:
    settings = get_settings()
    top_k = top_k or settings.rag_top_k
    filter_ = {k: v for k, v in (("doc_type", doc_type), ("regulation", regulation)) if v}
    store = get_vector_store()
    vec = embed_query(query)
    hits = store.query(vec, top_k=top_k, filter_=filter_ or None)

    citations = [
        Citation(
            source=h["metadata"].get("source", "?"),
            section=h["metadata"].get("section", "?"),
            page=h["metadata"].get("page"),
            score=round(h["score"], 4),
        )
        for h in hits
    ]
    top_score = max((h["score"] for h in hits), default=0.0)
    confident = top_score >= settings.rag_confidence_threshold
    return RetrievalResult(chunks=hits, citations=citations, top_score=top_score, confident=confident)


def format_context(result: RetrievalResult) -> str:
    lines = []
    for i, h in enumerate(result.chunks, 1):
        md = h.get("metadata", {})
        loc = f"p.{md.get('page')}" if md.get("page") else md.get("section", "?")
        lines.append(f"[{i}] (source={md.get('source')}, section={loc})\n{h.get('text', '')}")
    return "\n\n".join(lines)
