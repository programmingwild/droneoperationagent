"""Regression tests for the SSE payload sanitizer in the FastAPI layer.

The /chat stream must never leak raw embedding vectors to clients.
"""
from backend.app.main import _slim


def test_slim_strips_top_level_vector():
    assert _slim({"a": 1, "vector": [0.1, 0.2]}) == {"a": 1}


def test_slim_strips_nested_vectors():
    payload = {
        "type": "node",
        "delta": {
            "retrieved": [
                {"id": "x", "vector": [1.0] * 384, "metadata": {"source": "m.md"}},
                {"id": "y", "vector": [2.0] * 384, "metadata": {"source": "p.pdf"}},
            ],
            "trace": ["t1"],
        },
    }
    slimmed = _slim(payload)
    assert all("vector" not in chunk for chunk in slimmed["delta"]["retrieved"])
    assert slimmed["delta"]["trace"] == ["t1"]


def test_slim_handles_lists_and_scalars():
    assert _slim([{"vector": [1]}, "keep", 3]) == [{}, "keep", 3]
    assert _slim("plain") == "plain"
    assert _slim(None) is None
