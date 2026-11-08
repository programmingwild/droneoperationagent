"""Shared fixtures. Environment is configured BEFORE any app module import."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_tmp = Path(tempfile.mkdtemp(prefix="droneops-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["LLM_PROVIDER"] = "local"  # force offline/hermetic; ignore any .env key
os.environ["OPENAI_API_KEY"] = ""
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["VECTOR_BACKEND"] = "local"
os.environ["LOCAL_VECTOR_STORE_PATH"] = str(_tmp / "vector_store.json")
os.environ["FLIGHT_LOGS_DIR"] = str(ROOT / "data" / "sample_logs")
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["RAG_CONFIDENCE_THRESHOLD"] = "0.30"

import pytest  # noqa: E402

from backend.app.rag.ingest import ingest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ingest_corpus():
    ingest(reset=True)
    yield


@pytest.fixture()
def sample_log_path() -> Path:
    return ROOT / "data" / "sample_logs" / "flight_log_sample.csv"
