"""Embedding providers.

- openai : OpenAI embeddings (text-embedding-3-small, 1536 dims) — production path.
- local  : sentence-transformers all-MiniLM-L6-v2 (384 dims) when installed — real semantic
           embeddings, fully offline — else TF-IDF char/word fallback (data/local_embedder.pkl)
           fitted at ingest time. Lexical TF-IDF is the last resort and is clearly documented.
"""
import pickle
from pathlib import Path

import numpy as np

from ..config import REPO_ROOT, get_settings

LOCAL_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_ST_DIM = 384
LOCAL_EMBEDDER_PATH = REPO_ROOT / "data" / "local_embedder.pkl"
LOCAL_DIM = 30_000
_st_model = None


def _use_openai() -> bool:
    settings = get_settings()
    if settings.embedding_provider == "local":
        return False
    if settings.embedding_provider == "openai":
        return True
    return bool(settings.openai_api_key)


def _st_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except Exception:
        return False


def local_backend() -> str:
    return "sentence-transformers" if _st_available() else "tfidf"


def embedding_dimension() -> int:
    if _use_openai():
        return 1536
    return _ST_DIM if _st_available() else LOCAL_DIM


def _st_embed(texts: list[str]) -> list[list[float]]:
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer

        _st_model = SentenceTransformer(LOCAL_ST_MODEL)
    vecs = _st_model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [list(map(float, v)) for v in vecs]


def fit_local_tfidf(texts: list[str]) -> list[list[float]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), stop_words="english",
                                 max_features=LOCAL_DIM, sublinear_tf=True)
    matrix = normalize(vectorizer.fit_transform(texts))
    LOCAL_EMBEDDER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_EMBEDDER_PATH.open("wb") as f:
        pickle.dump(vectorizer, f)
    return matrix.toarray().astype(np.float32).tolist()


def _tfidf_embed(texts: list[str], fit: bool = False) -> list[list[float]]:
    from sklearn.preprocessing import normalize

    if fit:
        return fit_local_tfidf(texts)
    if not LOCAL_EMBEDDER_PATH.exists():
        raise RuntimeError(
            f"Local TF-IDF embedder not fitted at {LOCAL_EMBEDDER_PATH}. "
            "Run: python -m backend.app.rag.ingest --reset"
        )
    with LOCAL_EMBEDDER_PATH.open("rb") as f:
        vectorizer = pickle.load(f)
    return normalize(vectorizer.transform(texts)).toarray().astype(np.float32).tolist()


def _local_embed(texts: list[str], fit: bool = False) -> list[list[float]]:
    if _st_available():
        return _st_embed(texts)
    if fit and not LOCAL_EMBEDDER_PATH.exists():
        return _tfidf_embed(texts, fit=True)
    return _tfidf_embed(texts, fit=False) if not fit else fit_local_tfidf(texts)


def embed_texts(texts: list[str], *, fit_local: bool = False) -> list[list[float]]:
    if _use_openai():
        from langchain_openai import OpenAIEmbeddings

        settings = get_settings()
        embedder = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
        return [list(map(float, v)) for v in embedder.embed_documents(texts)]
    return _local_embed(texts, fit=fit_local)


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))
