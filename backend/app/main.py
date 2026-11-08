"""Drone Ops Agent — FastAPI application.

Endpoints:
  POST /chat      — run the agent graph; Server-Sent Events stream of stage + final payload
  POST /approve   — human-in-the-loop decision; resumes an interrupted run
  GET  /approvals/pending — pending HITL approvals
  GET  /logs      — tickets, approvals, recent runs, available flight-log CSVs
  GET  /tickets/{ticket_id}
  POST /report/{ticket_id} — export ticket as PDF (application/pdf)
  GET  /health    — liveness + backend/provider status
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from . import __version__
from .agents.graph import get_graph
from .config import get_settings
from .db import Approval, RunAudit, get_session
from .logging_conf import configure_logging, log_extra
from .schemas import ApproveRequest, ApprovalOut, ChatRequest, HealthOut, LogsOut
from .telemetry import init_tracing
from .tools.report import export_ticket_pdf
from .tools.ticket import get_ticket, list_tickets

settings = get_settings()
configure_logging(settings.log_level)
TRACING_ON = init_tracing()

app = FastAPI(title="Drone Ops Agent", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_session():
    with get_session() as session:
        yield session


def _jsonable(obj):
    return json.loads(json.dumps(obj, default=str))


def _slim(obj):
    """Recursively strip bulky embedding vectors from streamed payloads."""
    if isinstance(obj, dict):
        return {k: _slim(v) for k, v in obj.items() if k != "vector"}
    if isinstance(obj, list):
        return [_slim(v) for v in obj]
    return obj


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(_jsonable(payload))}\n\n"


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


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    from .agents import llm as llm_mod
    from .rag.vectorstore import get_vector_store

    doc_count = None
    try:
        doc_count = get_vector_store().count()
    except Exception:
        pass
    embedding_provider = settings.embedding_provider
    if embedding_provider == "auto":
        embedding_provider = "openai" if settings.openai_api_key else "local"
    vector_backend = settings.vector_backend
    if vector_backend == "auto":
        vector_backend = "pinecone" if settings.pinecone_api_key else "local"
    return HealthOut(
        status="ok",
        version=__version__,
        app_env=settings.app_env,
        llm_available=llm_mod.llm_available(),
        embedding_provider=embedding_provider,
        vector_backend=vector_backend,
        vector_store_docs=doc_count,
        langsmith_tracing=TRACING_ON,
    )


@app.post("/chat")
async def chat(req: ChatRequest):
    graph = get_graph()
    thread_id = req.thread_id or f"t-{uuid.uuid4().hex[:12]}"
    run_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "run_id": run_id,
        "thread_id": thread_id,
        "query": req.query,
        "log_file": req.log_file,
        "lat": req.lat,
        "lon": req.lon,
        "trace": [f"run started ({run_id[:8]})"],
        "errors": [],
        "tool_results": {},
    }

    def event_stream():
        import logging
        logger = logging.getLogger(__name__)
        logger.info("chat_run_started", extra=log_extra(run_id=run_id, thread_id=thread_id))
        yield _sse({"type": "run_started", "run_id": run_id, "thread_id": thread_id})
        try:
            for update in graph.stream(initial, config, stream_mode="updates"):
                for node, delta in update.items():
                    if node == "__interrupt__":
                        continue  # pause handled via get_state() below
                    yield _sse({"type": "node", "node": node, "delta": _slim(delta)})
            snapshot = graph.get_state(config)
            if snapshot.next:  # paused at interrupt_before=["human_approval"]
                pending = None
                for row in _pending_approvals():
                    if row["thread_id"] == thread_id:
                        pending = row
                        break
                yield _sse({
                    "type": "approval_required",
                    "thread_id": thread_id,
                    "approval_id": pending["id"] if pending else None,
                    "action": pending["action"] if pending else None,
                    "summary": pending["summary"] if pending else None,
                    "message": "Human-in-the-loop approval required before any authorization. "
                               "Use POST /approve or the Streamlit banner.",
                })
            else:
                yield _sse({"type": "final", **(snapshot.values.get("final") or {})})
        except Exception as exc:  # keep the stream alive; report the failure
            logger.exception("chat_run_failed", extra=log_extra(run_id=run_id))
            yield _sse({"type": "error", "error": str(exc),
                        "safe_default": "Do not launch. Resolve the error and retry."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _pending_approvals(session: Session | None = None) -> list[dict]:
    def _query(sess: Session):
        rows = (sess.query(Approval)
                .filter(Approval.decision == "PENDING")
                .order_by(Approval.created_at.asc()).all())
        return [_approval_dict(r) for r in rows]

    if session is not None:
        return _query(session)
    with get_session() as sess:
        return _query(sess)


@app.get("/approvals/pending", response_model=list[ApprovalOut])
def approvals_pending():
    return _pending_approvals()


@app.post("/approve")
def approve(req: ApproveRequest, session: Session = Depends(db_session)):
    row = session.get(Approval, req.approval_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"approval {req.approval_id} not found")
    if row.decision != "PENDING":
        raise HTTPException(status_code=409, detail=f"approval already decided: {row.decision}")

    graph = get_graph()
    config = {"configurable": {"thread_id": row.thread_id}}
    decision = "APPROVED" if req.approved else "REJECTED"
    try:
        graph.update_state(config, {"approval_decision": decision, "decided_by": req.decided_by})
        result = graph.invoke(None, config)
    except Exception as exc:
        row.decision = "REJECTED"  # fail safe: never leave a dangling authorization
        row.decided_by = f"system-fail-safe ({exc})"
        row.resolved_at = datetime.now(timezone.utc)
        session.commit()
        raise HTTPException(status_code=500, detail=f"resume failed; approval failed safe to REJECTED: {exc}")

    final = result.get("final", {})
    return {
        "approval_id": row.id,
        "decision": decision,
        "thread_id": row.thread_id,
        "answer": final.get("answer"),
        "recommended_action": final.get("recommended_action"),
        "trace": final.get("trace"),
    }


@app.get("/logs", response_model=LogsOut)
def logs(limit: int = 25):
    tickets = list_tickets(limit=limit)
    with get_session() as session:
        approvals = [_approval_dict(r) for r in
                     session.query(Approval).order_by(Approval.created_at.desc()).limit(limit).all()]
        runs = [
            {"id": r.id, "started_at": r.started_at.isoformat() if r.started_at else None,
             "query": r.query, "classification": r.classification, "status": r.status}
            for r in session.query(RunAudit).order_by(RunAudit.started_at.desc()).limit(limit).all()
        ]
    flight_logs = sorted(p.name for p in Path(settings.flight_logs_dir).glob("*.csv"))
    return LogsOut(tickets=tickets, approvals=approvals, runs=runs, flight_logs=flight_logs)


@app.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str):
    t = get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="ticket not found")
    return t


@app.post("/report/{ticket_id}")
def report(ticket_id: str):
    try:
        path = export_ticket_pdf(ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return FileResponse(path, media_type="application/pdf", filename=path.name)
