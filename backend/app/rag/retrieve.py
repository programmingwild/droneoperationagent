"""Retrieval with citations and confidence scoring.

Hybrid ranking: candidates are fetched by cosine similarity, then re-ordered by a
blend of cosine score and lexical term overlap (64/36). The cosine score is kept as
`Citation.score` and drives the confidence gate, so grounding/refusal behaviour is
unchanged; only the *order* of candidates improves.
"""
import re
from pydantic import BaseModel

from ..config import get_settings
from .embeddings import embed_query
from .vectorstore import get_vector_store

_STOPWORDS = frozenset(
    "a an the of to in on at for with and or is are be by it its as from that this "
    "what which when where why how their there here you your our we they he she not no "
    "do does did can could should would shall may might will about into over under "
    "between during before after above below out up down off".split()
)


def _terms(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(t) > 2 and t not in _STOPWORDS
    }


def _lexical_overlap(query_terms: set[str], doc_text: str) -> float:
    if not query_terms:
        return 0.0
    doc_terms = _terms(doc_text)
    if not doc_terms:
        return 0.0
    return len(query_terms & doc_terms) / len(query_terms)


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
    # Overfetch, then re-order with lexical signal; keep cosine for scoring/gating.
    fetch_k = max(top_k * 4, 16)
    hits = store.query(vec, top_k=fetch_k, filter_=filter_ or None)
    query_terms = _terms(query)
    for h in hits:
        h["_hybrid"] = 0.64 * h["score"] + 0.36 * _lexical_overlap(query_terms, h.get("text", ""))
    hits.sort(key=lambda h: h["_hybrid"], reverse=True)
    hits = hits[:top_k]

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
