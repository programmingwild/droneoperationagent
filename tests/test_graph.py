"""Graph transition tests with a fresh MemorySaver per test. LLM is NOT called (no key in test env)."""
import uuid

import pytest
from langgraph.checkpoint.memory import MemorySaver

from backend.app.agents.graph import build_graph


def _run(graph, query, log_file=None, thread=None):
    thread_id = thread or f"test-{uuid.uuid4().hex[:8]}"
    cfg = {"configurable": {"thread_id": thread_id}}
    state = {"run_id": uuid.uuid4().hex, "thread_id": thread_id, "query": query,
             "log_file": log_file, "trace": ["test run"], "errors": [], "tool_results": {}}
    for update in graph.stream(state, cfg, stream_mode="updates"):
        pass
    return cfg, graph.get_state(cfg)


@pytest.fixture()
def graph():
    return build_graph(MemorySaver())


def test_triage_regulation_route_answers_with_citations(graph):
    cfg, snap = _run(graph, "Is flying over people legal under part 107 in the US?")
    assert snap.values["classification"] == "regulation"
    assert snap.values["requires_approval"] is False
    final = snap.values.get("final") or {}
    assert final.get("citations"), "regulation answer must carry citations"
    assert final.get("answer")


def test_maintenance_route_writes_ticket(graph, sample_log_path):
    cfg, snap = _run(graph, "Analyze the last flight log and open a ticket if anything looks off",
                     log_file=str(sample_log_path))
    assert snap.values["classification"] == "maintenance"
    ticket = snap.values.get("tool_results", {}).get("ticket")
    assert ticket and ticket["id"].startswith("MT-")
    analysis = snap.values["tool_results"]["log_analysis"]
    assert analysis["verdict"] == "GROUND"
    assert snap.values["recommended_action"] == "INSPECT"


def test_mission_flow_interrupts_for_hitl_then_resume_approve(graph):
    cfg, snap = _run(graph, "Can I fly the VX-6 for a battery inspection mission?")
    assert snap.values["requires_approval"] is True
    assert snap.next == ("human_approval",)
    approval_id = snap.values["approval_id"]
    assert approval_id and approval_id.startswith("AP-")

    graph.update_state(cfg, {"approval_decision": "APPROVED", "decided_by": "test-pilot"})
    result = graph.invoke(None, cfg)
    final = result["final"]
    assert "TAKEOFF AUTHORIZED" in final["answer"]
    assert final["recommended_action"] == "TAKEOFF"
    assert final["requires_approval"] is False


def test_mission_flow_resume_reject_holds(graph):
    cfg, snap = _run(graph, "Can I fly the VX-6 for a battery inspection mission?")
    assert snap.next == ("human_approval",)
    graph.update_state(cfg, {"approval_decision": "REJECTED", "decided_by": "safety-officer"})
    result = graph.invoke(None, cfg)
    final = result["final"]
    assert "NOT AUTHORIZED" in final["answer"]
    assert final["recommended_action"] == "HOLD"


def test_no_takeoff_output_without_approval(graph):
    cfg, snap = _run(graph, "Can I fly the VX-6 for a battery inspection mission?")
    answer = snap.values.get("answer") or ""
    assert "TAKEOFF AUTHORIZED" not in answer  # never emitted before HITL
