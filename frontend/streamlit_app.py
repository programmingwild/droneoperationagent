"""Drone Ops Agent — Streamlit mission-control UI.

Run:  streamlit run frontend/streamlit_app.py
Talks to the FastAPI agent at $DRONEOPS_API (default http://127.0.0.1:8000).
"""
import json
import os

import httpx
import streamlit as st

API = os.environ.get("DRONEOPS_API", "http://127.0.0.1:8000")

st.set_page_config(page_title="Drone Ops Agent", page_icon="🛸", layout="wide")

# ------------------------------------------------------------------ theme CSS
st.markdown("""
<style>
.block-container { padding-top: 1.6rem; }

/* hero */
.hero {
  background: linear-gradient(135deg, #0b2239 0%, #10344f 55%, #0f4c5c 100%);
  border-radius: 18px; padding: 2.2rem 2.4rem; color: #eaf4ff;
  border: 1px solid rgba(125, 211, 252, .25);
}
.hero h1 { font-size: 2.1rem; margin: 0 0 .35rem 0; color: #f0f9ff; }
.hero p  { color: #bfe3ff; margin: 0; max-width: 46rem; }
.hero .badge-row { margin-top: .9rem; }
.tag {
  display: inline-block; padding: .18rem .65rem; border-radius: 999px;
  font-size: .72rem; letter-spacing: .08em; text-transform: uppercase;
  border: 1px solid rgba(255,255,255,.35); color: #dff3ff; margin-right: .4rem;
}

/* generic pills */
.pill { display: inline-block; padding: .1rem .55rem; border-radius: 8px;
        font-size: .75rem; font-weight: 700; color: #fff; }
.pill-high  { background: #dc2626; }
.pill-medium{ background: #d97706; }
.pill-low   { background: #16a34a; }
.pill-info  { background: #2563eb; }
.pill-open  { background: #475569; }
.pill-ground{ background: #7f1d1d; }
.pill-inspect { background: #1d4ed8; }

/* citation cards */
.cite-card {
  border: 1px solid #dbe5ef; border-left: 4px solid #0ea5e9;
  border-radius: 10px; padding: .55rem .75rem; margin: .35rem 0;
  background: #f8fbff; font-size: .85rem;
}
.cite-card b { color: #075985; }

/* sidebar brand */
.brand { display: flex; align-items: center; gap: .6rem; }
.brand .logo { font-size: 1.9rem; }
.brand .name { font-weight: 800; font-size: 1.15rem; letter-spacing: .02em; }
.brand .sub  { color: #64748b; font-size: .72rem; }

/* pending approval banner — dark maroon alert, explicit colors for the dark theme */
.hitl {
  border: 2px solid #ef4444; background: #2b0f12; border-radius: 12px;
  padding: .8rem 1rem; margin-bottom: .6rem; color: #fde2e2;
}
.hitl h4 { margin: 0 0 .3rem 0; color: #fca5a5; letter-spacing:.02em; }
.hitl code {
  background: #3b1216; color: #fda4a4; border: 1px solid #7f1d1d;
  border-radius: 6px; padding: .1rem .35rem; font-size:.82rem;
}
.hitl b { color: #fecaca; }

/* verdict banner (flight analysis) */
.verdict { border-radius: 12px; padding: .7rem 1rem; margin: .3rem 0 .6rem 0; color:#fff; }
.verdict h3 { margin: 0; font-size: 1.05rem; }
.verdict small { opacity: .85; font-size: .78rem; }
.v-ground  { background: linear-gradient(135deg,#7f1d1d,#dc2626); border:1px solid #fca5a5; }
.v-monitor { background: linear-gradient(135deg,#78350f,#d97706); border:1px solid #fcd34d; }
.v-pass    { background: linear-gradient(135deg,#14532d,#16a34a); border:1px solid #86efac; }

/* stat tiles */
.tiles { display:flex; gap:.5rem; flex-wrap:wrap; margin:.4rem 0 .6rem; }
.tile { flex:1 1 120px; background:#0f1c30; border:1px solid #1e3a5f; border-radius:10px; padding:.45rem .6rem; text-align:center; }
.tile .k { color:#7aa5d0; font-size:.65rem; text-transform:uppercase; letter-spacing:.06em; }
.tile .v { color:#f0f7ff; font-size:1.05rem; font-weight:800; }

/* finding cards */
.finding { display:flex; gap:.6rem; align-items:flex-start; border:1px solid #1e3a5f;
           border-left:5px solid #64748b; border-radius:10px; padding:.5rem .7rem; margin:.35rem 0;
           background:#0f1c30; }
.f-high { border-left-color:#ef4444; }
.f-medium { border-left-color:#f59e0b; }
.f-low { border-left-color:#eab308; }
.finding .icon { font-size:1.1rem; line-height:1.2; }
.finding .type { font-weight:700; color:#f3f8ff; font-size:.85rem; }
.finding .desc { color:#a8c0dd; font-size:.8rem; }
.finding .mono { font-family:ui-monospace,Consolas,monospace; color:#67e8f9; font-size:.72rem; }

/* actions checklist */
.actions { border:1px dashed #155e75; border-radius:10px; padding:.5rem .8rem; background:rgba(34,211,238,.06); margin:.4rem 0; }
.actions b { color:#67e8f9; }
.actions ol { margin:.2rem 0 .1rem 1.1rem; padding:0; }
.actions li { color:#c4dcf5; font-size:.82rem; margin:.15rem 0; }

/* raw answer expander */
.rawhint { color:#64748b; font-size:.72rem; }
</style>
""", unsafe_allow_html=True)

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


def severity_pill(sev: str) -> str:
    sev = (sev or "?").upper()
    cls = {"HIGH": "pill-high", "MEDIUM": "pill-medium", "LOW": "pill-low"}.get(sev, "pill-info")
    return f'<span class="pill {cls}">{sev}</span>'


def render_query(prompt: str):
    """Render a user message and stream the agent's SSE response into the current container."""
    st.session_state.messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        status = st.status("Agent working…", expanded=True)
        final_answer, citations, trace = "", [], []
        tool_results: dict = {}
        steps: list[str] = []
        for event in stream_chat(prompt):
            etype = event.get("type")
            if etype == "node":
                node = event.get("node")
                steps.append(node)
                status.write(f"▸ {node}")
            elif etype == "approval_required":
                st.session_state.pending_approval = {
                    "id": event.get("approval_id"),
                    "action": event.get("action"),
                    "summary": event.get("summary"),
                }
                final_answer = ("🛡️ This flight requires your explicit approval before any "
                                "takeoff/arm authorization. See the banner above.")
                trace = steps
            elif etype == "final":
                final_answer = event.get("answer", "")
                citations = event.get("citations", [])
                trace = event.get("trace", steps)
                tool_results = event.get("tool_results") or {}
            elif etype == "error":
                final_answer = (f"⚠️ Agent error: {event.get('error')}\n\n"
                                f"{event.get('safe_default', 'Do not launch.')}")
        status.update(label="Agent finished", state="complete")
        la = tool_results.get("log_analysis") if tool_results else None
        if la:
            render_flight_panel(la, (tool_results or {}).get("ticket"))
            with st.expander("📄 Raw agent answer"):
                st.markdown(final_answer)
        else:
            st.markdown(final_answer)
        if citations:
            with st.expander(f"📚 Sources ({len(citations)})", expanded=False):
                for i, c in enumerate(citations, 1):
                    loc = f"p.{c['page']}" if c.get("page") else (c.get("section") or "")
                    st.markdown(
                        f'<div class="cite-card"><b>[{i}] {c.get("source")}</b>'
                        f'<br>{loc}<br>relevance {c.get("score", 0):.3f}</div>',
                        unsafe_allow_html=True)
        if trace:
            with st.expander("🔍 Agent trace"):
                st.markdown(" → ".join(f"`{s}`" for s in trace))
    st.session_state.messages.append(("assistant", final_answer))
    return final_answer


_VERA = {
    "GROUND": ("🚫", "GROUNDED — DO NOT FLY", "v-ground"),
    "MONITOR": ("⚠️", "MONITOR — RESTRICTED OPERATIONS", "v-monitor"),
    "PASS": ("✅", "PASS — NO ANOMALIES", "v-pass"),
}


def render_flight_panel(la: dict, ticket: dict | None):
    verdict = str(la.get("verdict", "")).upper()
    icon, label, cls = _VERA.get(verdict, ("❓", verdict or "UNKNOWN", "v-monitor"))
    st.markdown(
        f'<div class="verdict {cls}"><h3>{icon} {label}</h3>'
        f'<small>{la.get("rows", "?")} rows · {la.get("duration_s", 0):.1f}s · '
        f'anomaly score {la.get("anomaly_score", "?")}/100</small></div>',
        unsafe_allow_html=True)

    anoms = la.get("anomalies", [])
    hi = sum(1 for a in anoms if (a.get("severity") or "").upper() in {"HIGH", "CRITICAL"})
    st.markdown(
        '<div class="tiles">'
        f'<div class="tile"><div class="k">Anomaly score</div><div class="v">{la.get("anomaly_score", "—")}/100</div></div>'
        f'<div class="tile"><div class="k">Findings</div><div class="v">{len(anoms)} ({hi} high)</div></div>'
        f'<div class="tile"><div class="k">Vib max</div><div class="v">{la.get("max_vibration_ms2", 0):.1f} m/s²</div></div>'
        f'<div class="tile"><div class="k">Sag</div><div class="v">{la.get("voltage_sag_v", 0):.1f} V</div></div>'
        f'<div class="tile"><div class="k">Temp max</div><div class="v">{la.get("motor_temp_max_c", 0):.0f} °C</div></div>'
        "</div>",
        unsafe_allow_html=True)

    for a in anoms:
        sev = (a.get("severity") or "").upper()
        cls = {"HIGH": "f-high", "CRITICAL": "f-high", "MEDIUM": "f-medium", "LOW": "f-low"}.get(sev, "")
        ico = {"HIGH": "🔴", "CRITICAL": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get(sev, "⚪")
        ev = a.get("evidence") or {}
        ev_txt = " · ".join(f"{k}={v}" for k, v in list(ev.items())[:5])
        st.markdown(
            f'<div class="finding {cls}"><div class="icon">{ico}</div><div>'
            f'<div class="type">[{sev}] {a.get("type", "")}</div>'
            f'<div class="desc">{a.get("description", "")}</div>'
            + (f'<div class="mono">{ev_txt}</div>' if ev_txt else "")
            + "</div></div>",
            unsafe_allow_html=True)

    if ticket:
        t_id = ticket.get("id", "?")
        t_sev = (ticket.get("severity") or "?").upper()
        st.markdown(
            f'<div class="actions"><b>Ticket {t_id}</b> · severity <b>{t_sev}</b> · status {ticket.get("status")}<br/>'
            "Aircraft is <b>grounded pending inspection</b>. Technician sign-off required before next flight.</div>",
            unsafe_allow_html=True)
        if st.button("📄 Export maintenance report (PDF)", key=f"panel-pdf-{t_id}"):
            try:
                r = httpx.post(f"{API}/report/{t_id}", timeout=30.0)
                if r.status_code == 200:
                    st.download_button("Download PDF", r.content,
                                       file_name=f"{t_id}.pdf", mime="application/pdf",
                                       key=f"panel-dl-{t_id}")
                else:
                    st.error(f"export failed: {r.text}")
            except Exception as exc:
                st.error(str(exc))


def approval_banner(pending: dict):
    st.markdown(
        '<div class="hitl"><h4>🛡️ PENDING HUMAN APPROVAL</h4>'
        f'Action: <b>{pending.get("action")}</b> · approval <code>{pending.get("id")}</code>'
        "</div>",
        unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(pending.get("summary", ""))
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                res = api_post("/approve", {"approval_id": pending["id"], "approved": True,
                                            "decided_by": "streamlit-operator"})
                st.session_state.messages.append(("assistant", res.get("answer", json.dumps(res))))
                st.session_state.pop("pending_approval", None)
                st.rerun()
        with c2:
            if st.button("❌ Reject", use_container_width=True):
                res = api_post("/approve", {"approval_id": pending["id"], "approved": False,
                                            "decided_by": "streamlit-operator"})
                st.session_state.messages.append(("assistant", res.get("answer", json.dumps(res))))
                st.session_state.pop("pending_approval", None)
                st.rerun()


# ------------------------------------------------------------------ sidebar
health = api_get("/health")
api_ok = "_error" not in health

with st.sidebar:
    st.markdown('<div class="brand"><div class="logo">🛸</div><div>'
                '<div class="name">Drone Ops Agent</div>'
                '<div class="sub">Multi-agent RAG · UAS fleet &amp; mission readiness</div>'
                "</div></div>", unsafe_allow_html=True)
    st.divider()

    st.markdown("**System status**")
    if not api_ok:
        st.warning(f"API unreachable at `{API}`")
    else:
        llm = "🟢 Groq" if health.get("llm_available") else "🟡 OFFLINE"
        tracing = "🟢 on" if health.get("langsmith_tracing") else "⚪ off"
        st.markdown(f"LLM &nbsp;&nbsp;**{llm}**", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("Vector docs", health.get("vector_store_docs", "—"))
        c2.metric("Embeddings", str(health.get("embedding_provider", "local")))
        st.caption(f"app {health.get('app_env', '?')} · v{health.get('version', '?')} · tracing {tracing}")

    true_pending = api_get("/approvals/pending") if api_ok else []
    pending_n = len(true_pending) if isinstance(true_pending, list) else 0
    if pending_n:
        st.error(f"🛡️ {pending_n} approval(s) pending")
    st.divider()

    st.markdown("**Quick prompts**")
    for label, q in [
        ("⚖️ Part 107 over-people rule", "Is flying over people legal under Part 107?"),
        ("🔧 Analyze last flight log", "Analyze the last flight log and open a maintenance ticket if needed"),
        ("✈️ VX-6 20-min inspection mission", "Can I fly the VX-6 on a 20-min inspection mission at 120m and what are the risks?"),
        ("🛰️ DGCA yellow-zone rules", "What is required to fly a drone in a yellow zone in India?"),
    ]:
        if st.button(label, use_container_width=True, key=f"qp-{label}"):
            st.session_state.queued_prompt = q
            st.rerun()
    st.divider()
    with st.expander("About"):
        st.markdown(
            "Answers are grounded in the bundled corpus (**FAA Part 107 · EASA · DGCA · VX-6 manual · "
            "maintenance checklist**) with `[n]` citations. TAKEOFF/arm authorizations always require "
            "explicit human approval. Decision-support only — **not certified for flight operations**.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------------------------------------------ tabs
tab_chat, tab_tickets, tab_approvals, tab_logs, tab_runs = st.tabs(
    ["Chat", "Tickets", "Approvals", "Flight logs", "Runs"])

# ================================================================== CHAT
with tab_chat:
    if st.session_state.get("pending_approval"):
        approval_banner(st.session_state.pending_approval)

    if not st.session_state.messages:
        st.markdown(
            '<div class="hero"><h1>🛸 Drone Ops Agent</h1>'
            "<p>Ask about regulations, maintenance, missions, or anomalies — answers are "
            "retrieval-grounded with citations, and anything authorization-shaped pauses for "
            "your explicit approval.</p>"
            '<div class="badge-row">'
            '<span class="tag">RAG + citations</span>'
            '<span class="tag">Human-in-the-loop</span>'
            '<span class="tag">Groq · prod LLM</span>'
            '<span class="tag">Refusal when unsure</span>'
            "</div></div>",
            unsafe_allow_html=True)
        st.caption("Or click a quick prompt in the sidebar to get started.")

    for role, text in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(text)

    # process a queued quick-prompt, if any
    queued = st.session_state.pop("queued_prompt", None)
    chat_input = st.chat_input("Ask about legality, maintenance, missions…")
    prompt = queued or chat_input

    if prompt:
        render_query(prompt)
        if st.session_state.get("pending_approval"):
            st.rerun()

# ================================================================== TICKETS
with tab_tickets:
    st.subheader("Maintenance tickets")
    data = api_get("/logs?limit=25")
    if "_error" in data:
        st.warning(f"Could not load {API}/logs — {data['_error']}")
        tickets = []
    else:
        tickets = data.get("tickets", [])
    if tickets:
        open_n = sum(1 for t in tickets if (t.get("status") or "").upper() == "OPEN")
        high_n = sum(1 for t in tickets if (t.get("severity") or "").upper() in {"HIGH", "CRITICAL"})
        c1, c2, c3 = st.columns(3)
        c1.metric("Open", open_n)
        c2.metric("High severity", high_n)
        c3.metric("Total", len(tickets))
    if not tickets:
        st.info("No tickets yet — analyze a flight log from the **📄 Flight logs** tab to open one.")
    for t in tickets:
        header = st.container(border=True)
        with header:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**`{t.get('id')}`**  \n{t.get('title', '')}")
            c2.markdown(severity_pill(t.get("severity", "?")), unsafe_allow_html=True)
            c3.markdown(f'<span class="pill pill-open">{(t.get("status") or "?").upper()}</span>',
                        unsafe_allow_html=True)
            with st.expander("Findings & evidence"):
                for f_ in t.get("findings", []):
                    st.markdown(f"**{f_.get('type')}** — {severity_pill(f_.get('severity', '?'))}",
                                unsafe_allow_html=True)
                    st.markdown(f_.get("description", ""))
                    if f_.get("evidence"):
                        st.json(f_["evidence"], expanded=False)
            if st.button(f"📄 Export PDF", key=f"pdf-{t.get('id')}"):
                try:
                    r = httpx.post(f"{API}/report/{t.get('id')}", timeout=30.0)
                    if r.status_code == 200:
                        st.download_button("Download PDF", r.content,
                                           file_name=f"{t.get('id')}.pdf", mime="application/pdf",
                                           key=f"dl-{t.get('id')}")
                    else:
                        st.error(f"export failed: {r.text}")
                except Exception as exc:
                    st.error(str(exc))

# ================================================================== APPROVALS
with tab_approvals:
    st.subheader("Pending human approvals")
    st.caption("Authorization-shaped actions (takeoff/arm) always pause here. Nothing launches without a decision.")
    pending = api_get("/approvals/pending")
    if not isinstance(pending, list):
        pending = []
    if pending:
        for p in pending:
            st.markdown(
                '<div class="hitl"><h4>🛡️ TAKEOFF / ARM AUTHORIZATION REQUIRED</h4>'
                f"Approval <code>{p.get('id')}</code> · thread <code>{p.get('thread_id')}</code>"
                "</div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(p.get("summary", ""))
                c1, c2, _ = st.columns([1, 1, 4])
                if c1.button("✅ Approve", key=f"ap-{p['id']}", type="primary"):
                    api_post("/approve", {"approval_id": p["id"], "approved": True,
                                          "decided_by": "streamlit-operator"})
                    st.rerun()
                if c2.button("❌ Reject", key=f"rj-{p['id']}"):
                    api_post("/approve", {"approval_id": p["id"], "approved": False,
                                          "decided_by": "streamlit-operator"})
                    st.rerun()
    else:
        st.success("No approvals pending.")

# ================================================================== FLIGHT LOGS
with tab_logs:
    st.subheader("Flight logs")
    data = api_get("/logs?limit=25")
    logs = data.get("flight_logs", []) if isinstance(data, dict) else []
    if not logs:
        st.info("Drop CSV flight logs into `data/sample_logs/` to enable analysis.")
    for name in logs:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**`{name}`**")
            c1.caption("Telemetry CSV · eligible for maintenance analysis")
            if c2.button("🔍 Analyze", key=f"log-{name}", use_container_width=True):
                render_query(f"Analyze flight log {name} and open a maintenance ticket if needed")
                st.rerun()

# ================================================================== RUNS
with tab_runs:
    st.subheader("Recent agent runs")
    st.caption("Audit trail of /chat invocations recorded by the API.")
    data = api_get("/logs?limit=25")
    runs = data.get("runs", []) if isinstance(data, dict) else []
    if not runs:
        st.info("No runs recorded yet.")
    for r in runs:
        status = (r.get("status") or "?").lower()
        icon = "✅" if status == "completed" else ("🛡️" if status in {"approval_required", "paused"} else "⚠️")
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"{icon} **{r.get('query', '')}**")
            c1.caption(f"{r.get('started_at', '')} · run `{r.get('id', '')[:12]}`")
            c2.markdown(f'<span class="pill pill-info">{r.get("classification") or "?"}</span>',
                        unsafe_allow_html=True)
