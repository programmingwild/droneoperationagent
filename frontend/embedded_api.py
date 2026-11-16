"""Embedded (in-process) API shim for Streamlit Community Cloud.

Activated with the EMBEDDED_API=1 environment variable (e.g. in the Cloud's
secrets panel). Mirrors the FastAPI surface (`/health`, `/logs`,
`/approvals/pending`, `/approve`, `/report/{id}`, `/chat` SSE) so the Streamlit
UI runs exactly as before — but every call goes straight into this process:
no uvicorn, no Postgres. State lives in SQLite (`data/droneops.db`, gitignored),
so it resets on every redeploy/restart. That is the trade the Cloud makes for
not running containers.

NOT for production HITL flows where approvals must survive restarts.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings  # noqa: E402
from backend.app.db import Approval, RunAudit, get_session  # noqa: E402
from backend.app.tools.report import export_ticket_pdf  # noqa: E402
from backend.app.tools.ticket import list_tickets  # noqa: E402


def _slim(obj):
    if isinstance(obj, dict):
        return {k: _slim(v) for k, v in obj.items() if k != "vector"}
    if isinstance(obj, list):
        return [_slim(v) for v in obj]
    return obj


def _jsonable(obj):
    return json.loads(json.dumps(obj, default=str))


def _approval_dict(a: Approval) -> dict:
    created = a.created_at
    if created and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return {
        "id": a.id,
        "thread_id": a.thread_id,
        "created_at": created.isoformat() if created else None,
        "action": a.action,
        "summary": a.summary,
        "decision": a.decision,
        "decided_by": a.decided_by,
        "run_id": a.run_id,
    }


def _runs(limit: int) -> list[dict]:
    with get_session() as session:
        rows = session.query(RunAudit).order_by(RunAudit.started_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "query": r.query,
                "classification": r.classification,
                "status": r.status,
            }
            for r in rows
        ]


# ------------------------------------------------------------------ GET
def api_get(path: str, timeout: float = 10.0):
    settings = get_settings()
    try:
        if path == "/health":
            from backend.app.agents import llm as llm_mod
            from backend.app.rag.vectorstore import get_vector_store

            try:
                doc_count = get_vector_store().count()
            except Exception:
                doc_count = None
            return {
                "status": "ok",
                "version": "embedded",
                "app_env": settings.app_env,
                "llm_available": llm_mod.llm_available(),
                "embedding_provider": "local",
                "vector_backend": settings.vector_backend,
                "vector_store_docs": doc_count,
                "langsmith_tracing": os.environ.get("LANGSMITH_TRACING", "").lower() == "true",
            }
        if path.startswith("/logs"):
            from urllib.parse import parse_qs, urlparse

            try:
                limit = int(parse_qs(urlparse(path).query).get("limit", ["25"])[0])
            except Exception:
                limit = 25
            tickets = list_tickets(limit=limit)
            with get_session() as session:
                approvals = [
                    _approval_dict(r)
                    for r in session.query(Approval)
                    .order_by(Approval.created_at.desc())
                    .limit(limit)
                    .all()
                ]
            flight_logs = sorted(p.name for p in Path(settings.flight_logs_dir).glob("*.csv"))
            return {
                "tickets": tickets,
                "approvals": approvals,
                "runs": _runs(limit),
                "flight_logs": flight_logs,
            }
        if path == "/approvals/pending":
            with get_session() as session:
                rows = (
                    session.query(Approval)
                    .filter(Approval.decision == "PENDING")
                    .order_by(Approval.created_at.asc())
                    .all()
                )
                return [_approval_dict(r) for r in rows]
        return {"_error": f"unknown path {path}"}
    except Exception as exc:
        return {"_error": str(exc)}


# ------------------------------------------------------------------ POST
def api_post(path: str, payload: dict, timeout: float = 120.0):
    try:
        if path == "/approve":
            from backend.app.agents.graph import get_graph

            approval_id = payload.get("approval_id")
            approved = bool(payload.get("approved"))
            with get_session() as session:
                row = session.get(Approval, approval_id)
                if row is None:
                    return {"_error": f"approval {approval_id} not found"}
                if row.decision != "PENDING":
                    return {"_error": f"approval already decided: {row.decision}"}
                thread_id = row.thread_id
                graph = get_graph()
                config = {"configurable": {"thread_id": thread_id}}
                decision = "APPROVED" if approved else "REJECTED"
                try:
                    graph.update_state(config, {"approval_decision": decision,
                                                "decided_by": payload.get("decided_by", "operator")})
                    result = graph.invoke(None, config)
                except Exception as exc:
                    row.decision = "REJECTED"  # fail safe: never leave a dangling authorization
                    row.decided_by = f"system-fail-safe ({exc})"
                    row.resolved_at = datetime.now(timezone.utc)
                    session.commit()
                    return {"_error": f"resume failed; approval failed safe to REJECTED: {exc}"}
                final = result.get("final", {})
                row.decision = decision
                row.decided_by = payload.get("decided_by", "operator")
                row.resolved_at = datetime.now(timezone.utc)
                session.commit()
                return {
                    "approval_id": row.id,
                    "decision": decision,
                    "thread_id": thread_id,
                    "answer": final.get("answer"),
                    "recommended_action": final.get("recommended_action"),
                    "trace": final.get("trace"),
                }
        return {"_error": f"unknown path {path}"}
    except Exception as exc:
        return {"_error": str(exc)}


def api_download(path: str):
    """Mirrors Streamlit's export flow: returns (status_code, content_bytes, filename)."""
    ticket_id = path.rsplit("/", 1)[-1]
    try:
        pdf_path = Path(export_ticket_pdf(ticket_id))
        return 200, pdf_path.read_bytes(), pdf_path.name
    except Exception as exc:
        return 500, str(exc).encode("utf-8"), f"{ticket_id}.txt"


# ------------------------------------------------------------------ chat SSE
def stream_chat(query: str, log_file: str | None = None, history: list[dict] | None = None):
    """Yields the same event dicts as the /chat SSE stream, in-process."""
    from backend.app.agents.graph import get_graph

    graph = get_graph()
    thread_id = f"t-{uuid.uuid4().hex[:12]}"
    run_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "run_id": run_id,
        "thread_id": thread_id,
        "query": query,
        "log_file": log_file,
        "lat": None,
        "lon": None,
        "history": history or [],
        "trace": [f"run started ({run_id[:8]})"],
        "errors": [],
        "tool_results": {},
    }

    yield {"type": "run_started", "run_id": run_id, "thread_id": thread_id}
    try:
        for update in graph.stream(initial, config, stream_mode="updates"):
            for node, delta in update.items():
                if node == "__interrupt__":
                    continue
                yield {"type": "node", "node": node, "delta": _slim(delta)}

        snapshot = graph.get_state(config)
        if snapshot.next:
            # graph paused at interrupt_before=["human_approval"]
            pending = None
            with get_session() as session:
                row = (
                    session.query(Approval)
                    .filter(Approval.decision == "PENDING", Approval.thread_id == thread_id)
                    .first()
                )
                if row:
                    pending = _approval_dict(row)
            yield {
                "type": "approval_required",
                "thread_id": thread_id,
                "approval_id": (pending or {}).get("id"),
                "action": (pending or {}).get("action"),
                "summary": (pending or {}).get("summary"),
                "message": "Human-in-the-loop approval required before any authorization.",
            }
        else:
            yield {"type": "final", **(snapshot.values.get("final") or {})}
    except Exception as exc:
        yield {"type": "error", "error": str(exc),
               "safe_default": "Do not launch. Resolve the error and retry."}
