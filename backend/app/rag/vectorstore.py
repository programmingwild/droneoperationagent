"""Vector store backends.

- pinecone : Pinecone serverless index (production). Created automatically if missing.
- local    : JSON-file store + cosine similarity via numpy (offline dev/tests; zero external deps).

`VECTOR_BACKEND=auto` selects Pinecone when PINECONE_API_KEY is set, else local.
"""
import json
import time
from pathlib import Path

import numpy as np

from ..config import get_settings
from .embeddings import cosine, embedding_dimension


class LocalVectorStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.records: list[dict] = []
        if self.path.exists():
            try:
                self.records = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.records = []

    def upsert(self, chunks: list[dict]) -> None:
        by_id = {r["id"]: r for r in self.records}
        for c in chunks:
            by_id[c["id"]] = c
        self.records = list(by_id.values())
        self._flush()

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records), encoding="utf-8")

    def query(self, vector: list[float], top_k: int, filter_: dict | None = None) -> list[dict]:
        scored = []
        for r in self.records:
            md = r.get("metadata", {})
            if filter_:
                if any(md.get(k) != v for k, v in filter_.items()):
                    continue
            scored.append((cosine(vector, r["vector"]), r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {**r, "score": float(s)}
            for s, r in scored[:top_k]
        ]

    def count(self) -> int:
        return len(self.records)


class PineconeVectorStore:
    def __init__(self):
        settings = get_settings()
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=settings.pinecone_api_key)
        existing = [i["name"] for i in pc.list_indexes()]
        if settings.pinecone_index not in existing:
            pc.create_index(
                name=settings.pinecone_index,
                dimension=embedding_dimension(),
                metric="cosine",
                spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
            )
            # wait for readiness
            for _ in range(30):
                status = pc.describe_index(settings.pinecone_index).status
                if status.get("ready") if isinstance(status, dict) else getattr(status, "ready", False):
                    break
                time.sleep(2)
        self.index = pc.Index(settings.pinecone_index)

    def upsert(self, chunks: list[dict]) -> None:
        vectors = [
            {
                "id": c["id"],
                "values": c["vector"],
                "metadata": {**c.get("metadata", {}), "text": c["text"][:1800]},
            }
            for c in chunks
        ]
        for i in range(0, len(vectors), 100):
            self.index.upsert(vectors=vectors[i:i + 100])

    def query(self, vector: list[float], top_k: int, filter_: dict | None = None) -> list[dict]:
        resp = self.index.query(
            vector=vector, top_k=top_k, include_metadata=True,
            filter={k: {"$eq": v} for k, v in (filter_ or {}).items()} or None,
        )
        out = []
        for m in resp.get("matches", []):
            md = dict(m.get("metadata", {}))
            text = md.pop("text", "")
            out.append({
                "id": m.get("id"),
                "text": text,
                "metadata": md,
                "score": float(m.get("score", 0.0)),
            })
        return out

    def count(self) -> int:
        stats = self.index.describe_index_stats()
        return int(stats.get("total_vector_count", 0))


def get_vector_store():
    settings = get_settings()
    backend = settings.vector_backend
    if backend == "auto":
        backend = "pinecone" if settings.pinecone_api_key else "local"
    if backend == "pinecone":
        if not settings.pinecone_api_key:
            raise RuntimeError("VECTOR_BACKEND=pinecone but PINECONE_API_KEY is not set")
        return PineconeVectorStore()
    return LocalVectorStore(settings.local_vector_store_path)
