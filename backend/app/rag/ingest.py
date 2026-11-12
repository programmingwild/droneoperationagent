"""Ingestion: markdown + PDF -> chunks -> embeddings -> vector store.

Usage:
  python -m backend.app.rag.ingest            # ingest everything under data/docs
  python -m backend.app.rag.ingest --reset    # clear local store first
"""
import argparse
import json
from pathlib import Path

from ..config import REPO_ROOT, get_settings
from .chunking import chunks_from_markdown, chunks_from_pdf_pages
from .embeddings import embed_texts
from .vectorstore import get_vector_store

DOCS_DIR = REPO_ROOT / "data" / "docs"
MANIFEST = DOCS_DIR / "manifest.json"


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def collect_chunks() -> list[dict]:
    manifest = _load_manifest()
    chunks: list[dict] = []

    for md_path in sorted(DOCS_DIR.glob("*.md")):
        meta = manifest.get(md_path.name, {})
        text = md_path.read_text(encoding="utf-8")
        cs = chunks_from_markdown(
            text,
            source=md_path.name,
            doc_type=meta.get("doc_type", "manual"),
            regulation=meta.get("regulation"),
        )
        chunks.extend(cs)

    pdf_dir = DOCS_DIR / "pdf"
    if pdf_dir.exists():
        from pypdf import PdfReader

        for pdf_path in sorted(pdf_dir.glob("*.pdf")):
            meta = manifest.get(pdf_path.name, {})
            reader = PdfReader(str(pdf_path))
            pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
            cs = chunks_from_pdf_pages(
                pages,
                source=pdf_path.name,
                doc_type=meta.get("doc_type", "manual"),
                regulation=meta.get("regulation"),
            )
            chunks.extend(cs)

    return chunks


def ingest(reset: bool = False) -> dict:
    settings = get_settings()
    store = get_vector_store()
    if reset and hasattr(store, "_flush"):
        store.records = []
        store._flush()

    chunks = collect_chunks()
    if not chunks:
        return {"ingested": 0, "backend": settings.vector_backend}

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts, fit_local=True)
    records = []
    for c, vec in zip(chunks, vectors):
        records.append({
            "id": c.id,
            "text": c.text,
            "vector": vec,
            "metadata": {
                "source": c.source,
                "doc_type": c.doc_type,
                "regulation": c.regulation,
                "section": c.section,
                "page": c.page,
                "chunk_index": c.chunk_index,
            },
        })
    store.upsert(records)
    return {"ingested": len(records), "backend": settings.vector_backend,
            "sources": sorted({c.source for c in chunks})}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    result = ingest(reset=args.reset)
    print(json.dumps(result, indent=2))
