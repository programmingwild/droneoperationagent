"""Provider resolution: OpenAI vs Groq vs offline fallback (no network)."""
from backend.app.agents.llm import resolve_provider
from backend.app.config import Settings


def _s(**kw) -> Settings:
    base = dict(openai_api_key=None, groq_api_key=None, llm_provider="auto")
    base.update(kw)
    return Settings(**base)


def test_explicit_local_always_offline():
    assert resolve_provider(_s(llm_provider="local", openai_api_key="x", groq_api_key="y")) == "local"


def test_explicit_groq():
    assert resolve_provider(_s(llm_provider="groq", groq_api_key="g")) == "groq"


def test_auto_prefers_openai_then_groq_then_local():
    assert resolve_provider(_s(openai_api_key="o", groq_api_key="g")) == "openai"
    assert resolve_provider(_s(groq_api_key="g")) == "groq"
    assert resolve_provider(_s()) == "local"


def test_unknown_provider_falls_back_to_auto_rules():
    assert resolve_provider(_s(llm_provider="bogus", groq_api_key="g")) == "groq"


def test_groq_defaults_are_openai_compatible():
    s = _s()
    assert s.groq_base_url.endswith("/openai/v1")
    assert s.groq_model
