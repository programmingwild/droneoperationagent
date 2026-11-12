"""CI-only: generate a traced smoke run against a live LangSmith project.

No-ops cleanly (exit 0, writes nothing) when LANGSMITH_API_KEY is absent, so forks
and unconfigured runs stay green. Writes docs/langsmith_trace.html (uploaded as a
CI artifact) — never commit that file from CI.

Usage:  python scripts/ci_trace_snapshot.py
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    if not os.environ.get("LANGSMITH_API_KEY"):
        print("LANGSMITH_API_KEY not set — skipping trace snapshot "
              "(add the LANGSMITH_API_KEY secret to a droneops-ci project to enable).")
        return 0

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "droneops-ci")
    os.environ.setdefault("LLM_PROVIDER", "groq" if os.environ.get("GROQ_API_KEY") else "local")

    from langgraph.checkpoint.memory import MemorySaver

    from backend.app.agents.graph import build_graph

    graph = build_graph(checkpointer=MemorySaver())
    graph.invoke(
        {
            "run_id": "ci-snapshot",
            "thread_id": "ci-snapshot",
            "query": "What does Part 107 say about maximum altitude?",
            "log_file": None,
            "lat": None,
            "lon": None,
            "trace": ["ci snapshot"],
        },
        config={"configurable": {"thread_id": "ci-snapshot"}},
    )
    time.sleep(12)  # let LangSmith ingest the spans

    from langsmith import Client

    client = Client(
        api_url=os.environ.get("LANGSMITH_ENDPOINT") or None,
        api_key=os.environ["LANGSMITH_API_KEY"],
    )
    project = os.environ["LANGSMITH_PROJECT"]
    runs = list(client.list_runs(project_name=project, limit=1))
    if not runs:
        print(f"No runs ingested into project {project!r} yet; nothing to render.")
        return 0
    trace_id = str(runs[0].trace_id)
    print("snapshot trace:", trace_id)
    subprocess.check_call([sys.executable, "scripts/render_langsmith_trace.py", trace_id])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
