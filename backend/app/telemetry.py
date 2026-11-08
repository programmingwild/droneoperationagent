"""LangSmith tracing — env-gated (LANGSMITH_TRACING=true + LANGSMITH_API_KEY)."""
import os

from .config import get_settings


def init_tracing() -> bool:
    settings = get_settings()
    if not (settings.langsmith_tracing and settings.langsmith_api_key):
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    return True
