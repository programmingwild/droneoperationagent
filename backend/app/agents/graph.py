"""LangGraph assembly: triage → specialist → safety → (HITL) → finalize.

HITL uses interrupt_before=["human_approval"]: the graph pauses with the approval request persisted.
An operator approves/rejects via POST /approve, which updates state and resumes the run.
"""
import logging
import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..config import get_settings
from . import nodes
from .state import AgentState

logger = logging.getLogger(__name__)

_ROUTES = {
    "mission_planning": "mission_planning",
    "maintenance": "maintenance",
    "regulation": "regulation",
    "anomaly": "anomaly",
}


def _route_triage(state: AgentState) -> str:
    return _ROUTES.get(state.get("classification", "regulation"), "regulation")


def _route_after_safety(state: AgentState) -> str:
    return "human_approval" if state.get("requires_approval") else "finalize"


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("triage", nodes.triage_node)
    graph.add_node("mission_planning", nodes.mission_planning_node)
    graph.add_node("maintenance", nodes.maintenance_node)
    graph.add_node("regulation", nodes.regulation_node)
    graph.add_node("anomaly", nodes.anomaly_node)
    graph.add_node("safety_supervisor", nodes.safety_supervisor_node)
    graph.add_node("human_approval", nodes.human_approval_node)
    graph.add_node("finalize", nodes.finalize_node)

    graph.add_edge(START, "triage")
    graph.add_conditional_edges("triage", _route_triage, _ROUTES)
    for specialist in _ROUTES.values():
        graph.add_edge(specialist, "safety_supervisor")
    graph.add_conditional_edges(
        "safety_supervisor", _route_after_safety,
        {"human_approval": "human_approval", "finalize": "finalize"},
    )
    graph.add_edge("human_approval", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(
        checkpointer=checkpointer or default_checkpointer(),
        interrupt_before=["human_approval"],
    )


def default_checkpointer():
    settings = get_settings()
    dsn = settings.database_url
    # Production: durable Postgres checkpointer (same database as the audit trail).
    if dsn.startswith(("postgresql://", "postgres://", "postgresql+psycopg2://")):
        try:
            import psycopg
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg.rows import dict_row

            saver = PostgresSaver(
                psycopg.connect(dsn.replace("+psycopg2", ""), autocommit=True, row_factory=dict_row)
            )
            saver.setup()
            return saver
        except Exception as exc:
            logger.warning("postgres_checkpointer_unavailable_fallback_sqlite",
                           extra={"error": str(exc)[:200]})
    # Dev/test: SQLite file checkpointer.
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        path = Path(settings.data_dir / "checkpoints.sqlite")
        conn = sqlite3.connect(str(path), check_same_thread=False)
        saver = SqliteSaver(conn)
        if hasattr(saver, "setup"):
            try:
                saver.setup()
            except Exception:
                pass  # already initialised
        return saver
    except Exception as exc:
        logger.warning("sqlite_checkpointer_unavailable_fallback_memory", extra={"error": str(exc)})
        return MemorySaver()


_compiled = None


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
