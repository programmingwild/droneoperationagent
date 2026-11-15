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
/* ================= Liquid Glass — premium mission-control design system ================= */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&family=Space+Grotesk:wght@500;700&display=swap');

:root {
  --glass: rgba(17, 27, 46, 0.55);
  --glass-strong: rgba(22, 34, 57, 0.72);
  --glass-soft: rgba(17, 27, 46, 0.38);
  --stroke: rgba(154, 203, 255, 0.14);
  --stroke-hi: rgba(154, 203, 255, 0.30);
  --accent: #22d3ee;
  --hi: #eef6ff;
  --mid: #a9c5e6;
  --mono: 'JetBrains Mono', ui-monospace, Consolas, monospace;
}

.block-container { padding-top: 4.35rem; max-width: 1200px; }

.stApp {
  background:
    radial-gradient(1000px 620px at 88% -12%, rgba(59,130,246,.30), transparent 62%),
    radial-gradient(820px 520px at -12% 8%, rgba(34,211,238,.20), transparent 58%),
    radial-gradient(760px 720px at 55% 115%, rgba(139,92,246,.22), transparent 62%),
    #070d1b;
  color: var(--hi);
  font-family: 'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif;
}

/* ---------- sidebar: frosted edge panel ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(12,19,35,.86), rgba(9,14,26,.80)) !important;
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  border-right: 1px solid var(--stroke);
}
[data-testid="stSidebar"] hr { border-color: var(--stroke); }
[data-testid="stSidebar"] .brand .logo { filter: drop-shadow(0 0 16px rgba(34,211,238,.55)); }
[data-testid="stSidebar"] .brand .name {
  font-family: 'Space Grotesk', 'Inter', sans-serif;
  background: linear-gradient(95deg,#f2fbff 0%, #67e8f9 45%, #3b82f6 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
[data-testid="stSidebar"] .brand .sub { color: var(--mid); }
[data-testid="stSidebar"] .stButton > button {
  background: rgba(34,211,238,.07) !important;
  border: 1px solid rgba(154,203,255,.18) !important;
  color: #cfeaff !important; border-radius: 12px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(34,211,238,.14) !important;
  border-color: rgba(34,211,238,.55) !important;
  box-shadow: 0 0 22px rgba(34,211,238,.30);
  transform: translateY(-1px);
}

/* ---------- buttons ---------- */
.stButton > button {
  border-radius: 12px !important;
  background: rgba(34,211,238,.09) !important;
  color: #bfeaff !important;
  border: 1px solid rgba(154,203,255,.22) !important;
  font-weight: 600 !important;
  transition: all .18s ease !important;
}
.stButton > button:hover {
  border-color: rgba(34,211,238,.55) !important;
  box-shadow: 0 6px 26px rgba(34,211,238,.28);
  transform: translateY(-1px);
}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #22d3ee 0%, #38bdf8 45%, #3b82f6 100%) !important;
  color: #041424 !important; border: none !important; font-weight: 800 !important;
  box-shadow: 0 10px 32px rgba(34,211,238,.38) !important;
}
.stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
  box-shadow: 0 12px 36px rgba(59,130,246,.45) !important;
}

/* ---------- hero ---------- */
.hero {
  position: relative; overflow: hidden;
  background: linear-gradient(155deg, rgba(24,38,64,.78), rgba(12,20,37,.80));
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  border: 1px solid var(--stroke-hi);
  border-radius: 22px; padding: 2.1rem 2.3rem;
  box-shadow: 0 30px 70px rgba(2,8,23,.55), inset 0 1px 0 rgba(255,255,255,.10);
}
.hero::after {
  content:""; position:absolute; width:520px; height:520px; right:-170px; top:-230px;
  background: radial-gradient(circle, rgba(34,211,238,.28), transparent 65%);
  pointer-events:none;
}
.hero::before {
  content:""; position:absolute; width:340px; height:340px; left:-120px; bottom:-190px;
  background: radial-gradient(circle, rgba(139,92,246,.25), transparent 65%);
  pointer-events:none;
}
.kicker {
  position: relative; font-family: var(--mono); font-size:.62rem; letter-spacing:.22em;
  text-transform: uppercase; color:#22d3ee; margin-bottom:.4rem;
}
.hero h1 {
  position: relative; font-family: 'Space Grotesk', 'Inter', sans-serif;
  font-size: 2.15rem; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 .35rem 0;
  background: linear-gradient(95deg,#f2fbff 0%, #7dd3fc 35%, #38bdf8 60%, #818cf8 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { position: relative; color: #b8d6f0; margin: 0; max-width: 46rem; line-height: 1.55; }
.hero .badge-row { margin-top: .95rem; position: relative; }
.tag {
  display: inline-block; padding: .22rem .7rem; border-radius: 999px;
  font-size: .65rem; letter-spacing: .10em; text-transform: uppercase; font-weight: 700;
  border: 1px solid rgba(103,232,249,.38); color: #7ff0ff;
  background: rgba(34,211,238,.08); margin-right: .4rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 0 18px rgba(34,211,238,.12);
}

/* ---------- glass pills ---------- */
.pill { display:inline-block; padding:.16rem .6rem; border-radius:8px; font-size:.7rem; font-weight:800;
        color:#fff; letter-spacing:.04em; font-family:var(--mono); }
.pill-high   { background: linear-gradient(135deg,#ef4444,#b91c1c); box-shadow: 0 0 14px rgba(239,68,68,.40); }
.pill-medium { background: linear-gradient(135deg,#f59e0b,#b45309); box-shadow: 0 0 14px rgba(245,158,11,.40); }
.pill-low    { background: linear-gradient(135deg,#22c55e,#15803d); box-shadow: 0 0 14px rgba(34,197,94,.40); }
.pill-info   { background: linear-gradient(135deg,#3b82f6,#1d4ed8); box-shadow: 0 0 14px rgba(59,130,246,.40); }
.pill-open   { background: rgba(71,85,105,.85); border:1px solid rgba(154,203,255,.25); }
.pill-ground { background:#7f1d1d; }
.pill-inspect{ background:#1d4ed8; }

/* ---------- citation cards ---------- */
.cite-card {
  border: 1px solid var(--stroke); border-left: 3px solid var(--accent);
  border-radius: 12px; padding: .55rem .75rem; margin: .4rem 0;
  background: var(--glass-soft); backdrop-filter: blur(10px);
  font-size: .85rem; box-shadow: inset 0 1px 0 rgba(255,255,255,.06);
}
.cite-card b { color: #7ff0ff; font-family: var(--mono); font-size: .78rem; }

/* ---------- sidebar brand ---------- */
.brand { display: flex; align-items: center; gap: .6rem; }
.brand .logo { font-size: 1.9rem; }
.brand .name { font-weight: 800; font-size: 1.12rem; letter-spacing: .02em; }
.brand .sub  { color: var(--mid); font-size: .72rem; }

/* ---------- HITL banner: high-urgency glass alert ---------- */
.hitl {
  border: 1px solid rgba(248,113,113,.55);
  background: linear-gradient(160deg, rgba(69,10,10,.82), rgba(43,15,18,.82));
  backdrop-filter: blur(14px);
  border-radius: 16px; padding: .8rem 1rem; margin-bottom: .6rem; color: #ffe4e4;
  box-shadow: 0 0 0 1px rgba(248,113,113,.15), 0 16px 48px rgba(239,68,68,.18);
}
.hitl h4 { margin: 0 0 .3rem 0; color: #fca5a5; letter-spacing: .06em;
           text-transform: uppercase; font-size: .78rem; }
.hitl code { background: #3b1216; color: #fda4a4; border: 1px solid rgba(248,113,113,.4);
             border-radius: 6px; padding: .1rem .35rem; font-size: .82rem; font-family: var(--mono); }
.hitl b { color: #fecaca; }

/* ---------- verdict banner ---------- */
.verdict { border-radius: 16px; padding: .75rem 1.05rem; margin: .35rem 0 .6rem 0; color: #fff;
           backdrop-filter: blur(12px);
           box-shadow: 0 18px 46px rgba(2,8,23,.5), inset 0 1px 0 rgba(255,255,255,.22); }
.verdict h3 { margin: 0; font-size: 1.05rem; font-family: 'Space Grotesk', 'Inter', sans-serif; }
.verdict small { opacity: .92; font-size: .78rem; font-family: var(--mono); }
.v-ground  { background: linear-gradient(135deg, rgba(127,29,29,.85), rgba(220,38,38,.75));
             border: 1px solid rgba(252,165,165,.5); }
.v-monitor { background: linear-gradient(135deg, rgba(120,53,15,.85), rgba(217,119,6,.75));
             border: 1px solid rgba(252,211,77,.5); }
.v-pass    { background: linear-gradient(135deg, rgba(20,83,45,.85), rgba(22,163,74,.75));
             border: 1px solid rgba(134,239,172,.5); }

/* ---------- stat tiles ---------- */
.tiles { display: flex; gap: .5rem; flex-wrap: wrap; margin: .4rem 0 .6rem; }
.tile { flex: 1 1 110px; background: var(--glass-soft); border: 1px solid var(--stroke);
        border-radius: 14px; padding: .5rem .6rem; text-align: center;
        backdrop-filter: blur(10px); box-shadow: inset 0 1px 0 rgba(255,255,255,.07); }
.tile .k { color: #8fb4d8; font-size: .6rem; text-transform: uppercase; letter-spacing: .07em; }
.tile .v { color: #eef6ff; font-size: 1.02rem; font-weight: 800; font-family: 'Space Grotesk', 'Inter', sans-serif; }

/* ---------- finding cards ---------- */
.finding { display: flex; gap: .6rem; align-items: flex-start; border: 1px solid var(--stroke);
           border-left: 4px solid #64748b; border-radius: 14px; padding: .55rem .75rem;
           margin: .35rem 0; background: var(--glass-soft); backdrop-filter: blur(10px);
           box-shadow: inset 0 1px 0 rgba(255,255,255,.05); }
.f-high   { border-left-color: #ef4444; box-shadow: inset 0 0 28px rgba(239,68,68,.09); }
.f-medium { border-left-color: #f59e0b; }
.f-low    { border-left-color: #eab308; }
.finding .icon { font-size: 1.1rem; line-height: 1.25; }
.finding .type { font-weight: 700; color: #f3f8ff; font-size: .82rem;
                 font-family: var(--mono); letter-spacing: .02em; }
.finding .desc { color: #a9c5e6; font-size: .8rem; line-height: 1.45; }
.finding .mono { font-family: var(--mono); color: #67e8f9; font-size: .7rem;
                 background: rgba(34,211,238,.07); border: 1px solid rgba(34,211,238,.18);
                 border-radius: 6px; padding: .12rem .35rem; display: inline-block; margin-top: .25rem; }

/* ---------- actions checklist ---------- */
.actions { border: 1px dashed rgba(103,232,249,.4); border-radius: 14px; padding: .55rem .85rem;
           background: rgba(34,211,238,.06); margin: .4rem 0; backdrop-filter: blur(8px); }
.actions b { color: #67e8f9; }
.actions ol { margin: .2rem 0 .1rem 1.1rem; padding: 0; }
.actions li { color: #c4dcf5; font-size: .82rem; margin: .15rem 0; line-height: 1.45; }

.rawhint { color: #64748b; font-size: .72rem; }

/* ---------- native widgets: glass treatment ---------- */
[data-testid="stMetric"] {
  background: var(--glass-soft); border: 1px solid var(--stroke); border-radius: 14px;
  padding: .55rem .75rem; backdrop-filter: blur(10px);
}
[data-testid="stMetricValue"] { font-family: 'Space Grotesk', 'Inter', sans-serif; color: #eef6ff; }
[data-testid="stTabs"] [role="tablist"] { gap: .2rem; border-bottom: 1px solid var(--stroke); }
[data-testid="stTabs"] [role="tab"] { color: #cfe3f7 !important; -webkit-text-fill-color: #cfe3f7 !important;
                                      opacity: 1 !important; border-radius: 10px 10px 0 0; font-weight: 600; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: #7ff0ff !important; -webkit-text-fill-color: #7ff0ff !important;
}
[data-testid="stExpander"] {
  border: 1px solid var(--stroke) !important; border-radius: 14px !important;
  background: var(--glass-soft) !important; backdrop-filter: blur(10px);
}
[data-testid="stChatMessage"] {
  background: rgba(15,24,42,.55) !important; border: 1px solid var(--stroke);
  border-radius: 18px !important; backdrop-filter: blur(10px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.05);
}
[data-testid="stChatInput"] {
  border: 1px solid var(--stroke-hi) !important; border-radius: 16px;
  background: rgba(13,21,38,.72); backdrop-filter: blur(12px);
}
[data-testid="stChatInput"] textarea { background: transparent !important; color: #eef6ff !important; }
[data-testid="stAlert"] { border-radius: 14px !important; border: 1px solid var(--stroke); backdrop-filter: blur(8px); }
code, pre { font-family: var(--mono) !important; }

/* ---------- scrollbars & focus ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: rgba(154,203,255,.18); border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: rgba(154,203,255,.32); }
:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; border-radius: 4px; }
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
            '<div class="hero"><div class="kicker">Mission Control · VX-6 Fleet</div><h1>🛸 Drone Ops Agent</h1>'
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
