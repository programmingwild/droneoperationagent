"""Drone Ops Agent — Streamlit chat UI.

Run:  streamlit run frontend/streamlit_app.py
Shows: streaming agent trace, citations, ticket table, and a HITL "pending approval" banner.
"""
import json
import os

import httpx
import streamlit as st

API = os.environ.get("DRONEOPS_API", "http://127.0.0.1:8000")

st.set_page_config(page_title="Drone Ops Agent", page_icon="🛸", layout="wide")

# ------------------------------------------------------------------ helpers

def api_get(path: str, timeout: float = 10.0):
    try:
        r = httpx.get(f"{API}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"_error": str(exc)}


def api_post(path: str, payload: dict, timeout: float = 120.0):
    try:
        r = httpx.post(f"{API}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"_error": str(exc)}


def stream_chat(query: str, log_file: str | None = None):
    """Yield parsed SSE events from POST /chat."""
    payload = {"query": query}
    if log_file:
        payload["log_file"] = log_file
    with httpx.stream("POST", f"{API}/chat", json=payload, timeout=300.0) as resp:
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            try:
                yield json.loads(line[6:])
            except json.JSONDecodeError:
                continue


def approval_banner(pending: dict):
    st.error(f"🛡️ PENDING HUMAN APPROVAL — {pending.get('action')}  (approval `{pending.get('id')}`)")
    st.markdown(pending.get("summary", ""))
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        if st.button("✅ Approve", type="primary", use_container_width=True):
            res = api_post("/approve", {"approval_id": pending["id"], "approved": True,
                                        "decided_by": "streamlit-operator"})
            st.session_state.setdefault("messages", []).append(
                ("assistant", res.get("answer", json.dumps(res))))
            st.session_state.pop("pending_approval", None)
            st.rerun()
    with c2:
        if st.button("❌ Reject", use_container_width=True):
            res = api_post("/approve", {"approval_id": pending["id"], "approved": False,
                                        "decided_by": "streamlit-operator"})
            st.session_state.setdefault("messages", []).append(
                ("assistant", res.get("answer", json.dumps(res))))
            st.session_state.pop("pending_approval", None)
            st.rerun()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.title("🛸 Drone Ops Agent")
    st.caption("Multi-agent RAG for UAS fleet maintenance & mission readiness")
    health = api_get("/health")
    if "_error" in health:
        st.warning(f"API unreachable at {API}\n\n`{health['_error']}`")
    else:
        st.success("API online")
        st.json(health, expanded=False)
    st.divider()
    st.markdown("**Try**")
    st.code("Is flying over people legal under part 107?\n"
            "Analyze the last flight log\n"
            "Can I fly the VX-6 on a 20-min inspection mission?")

if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------------------------------------------ tabs
tab_chat, tab_tickets, tab_approvals, tab_logs = st.tabs(["💬 Chat", "🔧 Tickets", "🛡️ Approvals", "📄 Flight logs"])

with tab_chat:
    if st.session_state.get("pending_approval"):
        approval_banner(st.session_state.pending_approval)

    for role, text in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(text)

    prompt = st.chat_input("Ask about legality, maintenance, missions…")
    if prompt:
        st.session_state.messages.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        node_steps: list[str] = []
        with st.chat_message("assistant"):
            status = st.status("Agent working…", expanded=True)
            final_answer, citations, trace = "", [], []
            for event in stream_chat(prompt):
                etype = event.get("type")
                if etype == "node":
                    node = event.get("node")
                    node_steps.append(node)
                    status.write(f"▸ {node}")
                elif etype == "approval_required":
                    st.session_state.pending_approval = {
                        "id": event.get("approval_id"),
                        "action": event.get("action"),
                        "summary": event.get("summary"),
                    }
                    final_answer = ("🛡️ This flight requires your explicit approval before any "
                                    "takeoff/arm authorization. See the banner above.")
                    trace = node_steps
                elif etype == "final":
                    final_answer = event.get("answer", "")
                    citations = event.get("citations", [])
                    trace = event.get("trace", node_steps)
                elif etype == "error":
                    final_answer = (f"⚠️ Agent error: {event.get('error')}\n\n"
                                    f"{event.get('safe_default', 'Do not launch.')}")
            status.update(label="Agent finished", state="complete")
            st.markdown(final_answer)
            if citations:
                with st.expander("📚 Citations"):
                    for i, c in enumerate(citations, 1):
                        loc = f"p.{c['page']}" if c.get("page") else c.get("section")
                        st.write(f"[{i}] {c['source']} — {loc} (score {c.get('score', 0):.3f})")
            with st.expander("🔍 Agent trace"):
                for line in trace:
                    st.write(f"- {line}")

        st.session_state.messages.append(("assistant", final_answer))
        if st.session_state.get("pending_approval"):
            st.rerun()

with tab_tickets:
    st.subheader("Maintenance tickets")
    data = api_get("/logs?limit=25")
    tickets = data.get("tickets", [])
    if not tickets:
        st.info("No tickets yet — run a log analysis from the Flight logs tab.")
    for t in tickets:
        sev = t.get("severity", "?")
        with st.expander(f"`{t['id']}` · {sev} · {t['title']}"):
            st.json(t)
            if st.button(f"📄 Export PDF — {t['id']}", key=f"pdf-{t['id']}"):
                try:
                    r = httpx.post(f"{API}/report/{t['id']}", timeout=30.0)
                    if r.status_code == 200:
                        st.download_button("Download PDF", r.content,
                                           file_name=f"{t['id']}.pdf", mime="application/pdf")
                    else:
                        st.error(f"export failed: {r.text}")
                except Exception as exc:
                    st.error(str(exc))

with tab_approvals:
    st.subheader("Pending human approvals")
    pending = api_get("/approvals/pending")
    if isinstance(pending, list) and pending:
        for p in pending:
            st.warning(f"`{p['id']}` · {p['action']} · thread `{p['thread_id']}`")
            st.caption(p["summary"])
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve", key=f"ap-{p['id']}"):
                api_post("/approve", {"approval_id": p["id"], "approved": True,
                                      "decided_by": "streamlit-operator"})
                st.rerun()
            if c2.button("❌ Reject", key=f"rj-{p['id']}"):
                api_post("/approve", {"approval_id": p["id"], "approved": False,
                                      "decided_by": "streamlit-operator"})
                st.rerun()
    else:
        st.success("No approvals pending.")

with tab_logs:
    st.subheader("Available flight logs")
    data = api_get("/logs?limit=25")
    logs = data.get("flight_logs", [])
    for name in logs:
        c1, c2 = st.columns([3, 1])
        c1.write(f"`{name}`")
        if c2.button("Analyze", key=f"log-{name}"):
            api_path = f"data/sample_logs/{name}"
            st.session_state.messages.append(
                ("user", f"Analyze flight log {name} (open a ticket if anything looks off)"))
            st.info(f"Queued maintenance analysis for {name}. Ask in Chat or re-open to see the ticket.")
    if not logs:
        st.info("Drop CSV flight logs into data/sample_logs/ to enable analysis.")
