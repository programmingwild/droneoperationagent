"""Retrieval evaluation harness (offline-safe; LLM-as-judge runs live when GROQ_API_KEY is set).

Run from repo root:  python -m backend.app.evals.run_eval
Writes:              evals/results.json
"""
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from ..config import REPO_ROOT, get_settings
from ..rag.retrieve import format_context, retrieve

DATASET = Path(__file__).with_name("eval_dataset.json")
RESULTS = REPO_ROOT / "evals" / "results.json"


def _judge_context(question: str, context: str) -> str | None:
    """Ask Groq whether the retrieved context suffices to answer. None when offline/unavailable."""
    try:
        from ..agents.llm import chat
        answer = chat(
            "You are a strict evaluation judge. Reply with exactly one word: SUFFICIENT or INSUFFICIENT.",
            f"Question: {question}\n\nRetrieved context:\n{context}\n\n"
            "Does the context contain enough information to answer the question?",
        ).strip().upper()
        if "INSUFFICIENT" in answer:
            return "INSUFFICIENT"
        if "SUFFICIENT" in answer:
            return "SUFFICIENT"
        return None
    except Exception:
        return None


def run_eval(k: int = 4) -> dict:
    settings = get_settings()
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    rows = []
    hits_at_1 = hits_at_k = confident = 0

    for item in dataset:
        retr = retrieve(
            item["question"], top_k=k,
            regulation=item.get("regulation"),
        )
        sources = [c.source for c in retr.citations]
        judge = _judge_context(item["question"], format_context(retr))
        hit1 = bool(sources) and sources[0] in item["expected_sources"]
        hitk = any(s in item["expected_sources"] for s in sources)
        hits_at_1 += hit1
        hits_at_k += hitk
        confident += retr.confident
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "expected_sources": item["expected_sources"],
            "retrieved": [{"source": c.source, "section": c.section, "score": c.score} for c in retr.citations],
            "hit_at_1": hit1,
            "hit_at_k": hitk,
            "top_score": retr.top_score,
            "confident": retr.confident,
            "judge": judge,
        })

    n = len(dataset)
    judges = [r.get("judge") for r in rows if r.get("judge")]
    judge_result: dict | str
    if judges:
        sufficient = sum(1 for j in judges if j == "SUFFICIENT")
        judge_result = {
            "status": "ran",
            "provider": "groq",
            "n": len(judges),
            "sufficient": sufficient,
            "insufficient": len(judges) - sufficient,
            "sufficient_rate": round(sufficient / len(judges), 3),
        }
    else:
        judge_result = "skipped (offline)"
    result = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "embedding_provider": settings.embedding_provider,
            "vector_backend": settings.vector_backend,
            "top_k": k,
            "confidence_threshold": settings.rag_confidence_threshold,
        },
        "n_questions": n,
        "hit_at_1": round(hits_at_1 / n, 3),
        "hit_at_k": round(hits_at_k / n, 3),
        "confident_rate": round(confident / n, 3),
        "mean_top_score": round(statistics.mean(r["top_score"] for r in rows), 4),
        "per_question": rows,
        "llm_judge": judge_result,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    summary = run_eval()
    for key, value in summary.items():
        if key != "per_question":
            print(f"{key}: {value}")
    misses = [r for r in summary["per_question"] if not r["hit_at_k"]]
    if misses:
        print("\nMisses:")
        for r in misses:
            print(f"  {r['id']}: expected {r['expected_sources']}, got {[c['source'] for c in r['retrieved']]}")
