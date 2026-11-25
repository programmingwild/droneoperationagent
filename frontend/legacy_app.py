"""Drone Ops Agent — ChatGPT-style mission-control UI.

Run:  streamlit run frontend/streamlit_app.py
Talks to the FastAPI agent at $DRONEOPS_API (default http://127.0.0.1:8000).
"""
import html as _html
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
import streamlit as st
import streamlit.components.v1 as components

API = os.environ.get("DRONEOPS_API", "http://127.0.0.1:8000")

# Inline SVG icons for raw-HTML regions. One family (outline, 1.8 stroke,
# currentColor) so icons inherit the theme and never render as font emojis.
_ICON_PATHS = {
    "drone": ('<circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/>'
              '<circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>'
              '<path d="M6.4 6.4l3.2 3.2m8-3.2-3.2 3.2m-8 8 3.2-3.2m8 3.2-3.2-3.2"/>'
              '<rect x="9" y="9" width="6" height="6" rx="1.5"/>'),
    "check-circle": ('<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/>'
                     '<path d="m9 11 3 3L22 4"/>'),
    "alert-triangle": ('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
                       '<path d="M12 9v4m0 4h.01"/>'),
    "x-circle": ('<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6m0-6 6 6"/>'),
    "copy": ('<rect x="9" y="9" width="13" height="13" rx="2"/>'
             '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
}


def _ico(name: str, size: int = 18, cls: str = "") -> str:
    """Return an inline outline SVG that inherits the current text color."""
    return (f'<span class="ico {cls}" aria-hidden="true" style="width:{size}px;height:{size}px">'
            f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round">{_ICON_PATHS.get(name, _ICON_PATHS["drone"])}</svg></span>')


# One source of truth for readable labels: UI, agent answers and PDF reports.
from backend.app.formatting import (  # noqa: E402
    friendly as _friendly,
    format_pair as _fmt_evidence,
)

# Embedded mode: the whole agent runs in-process (Streamlit Community Cloud, single-process).
# See frontend/embedded_api.py. The helpers below delegate to it when this is set.
EMBEDDED = os.environ.get("EMBEDDED_API", "").strip().lower() in {"1", "true", "yes", "on"}


st.set_page_config(page_title="Drone Ops Agent", page_icon="assets/drone.svg", layout="wide",
                   initial_sidebar_state="expanded")

# ------------------------------------------------------------------ theme CSS
st.markdown("""
<style>
/* ================= Liquid Glass — mission-control design system ================ */
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --glass: rgba(17, 27, 46, 0.55);
  --glass-strong: rgba(22, 34, 57, 0.72);
  --glass-soft: rgba(17, 27, 46, 0.38);
  --stroke: rgba(154, 203, 255, 0.20);
  --stroke-hi: rgba(154, 203, 255, 0.36);
  --accent: #22d3ee;
  --hi: #f2f7ff;
  --mid: #a9c5e6;
  --muted: #93b4d6;   /* >= 7:1 on every surface */
  --faint: #9fb3cc;   /* >= 7:1 on every surface */
  --sans: 'Fira Sans', -apple-system, 'Segoe UI', system-ui, sans-serif;
  --mono: 'Fira Code', ui-monospace, Consolas, monospace;
}

/* No horizontal scroll; keyboard focus never hidden behind sticky UI. */
html, body { overflow-x: clip; scroll-padding-top: 4.35rem; scroll-padding-bottom: 5rem; }

.block-container { padding-top: 4.35rem; padding-bottom: 1.5rem; max-width: 1100px; }

.stApp {
  background:
    radial-gradient(1000px 620px at 88% -12%, rgba(59,130,246,.30), transparent 62%),
    radial-gradient(820px 520px at -12% 8%, rgba(34,211,238,.20), transparent 58%),
    radial-gradient(760px 720px at 55% 115%, rgba(139,92,246,.22), transparent 62%),
    #070d1b;
  color: var(--hi);
  font-family: var(--sans);
}

/* ---------- sidebar: frosted left rail ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(12,19,35,.88), rgba(9,14,26,.82)) !important;
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  border-right: 1px solid var(--stroke);
}
[data-testid="stSidebar"] hr { border-color: var(--stroke); margin: .55rem 0; }
[data-testid="stSidebar"] .brand .logo { filter: drop-shadow(0 0 14px rgba(34,211,238,.6)); font-size:1.55rem; }
[data-testid="stSidebar"] .brand .name {
  font-family: var(--sans); font-weight: 800; font-size: 1.02rem;
  letter-spacing: .03em;
  background: linear-gradient(95deg,#f2fbff 0%, #67e8f9 45%, #3b82f6 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
[data-testid="stSidebar"] .brand .sub { color: var(--mid); font-size: .68rem; }
[data-testid="stSidebar"] .nav-label {
  font-family: var(--mono); font-size:.62rem; letter-spacing:.18em; text-transform: uppercase;
  color:var(--muted); margin:.35rem 0 .1rem .1rem;
}
[data-testid="stSidebar"] .stButton > button {
  justify-content: flex-start; text-align: left;
  background: transparent !important; border: 1px solid transparent !important;
  color: #cfe3f7 !important; border-radius: 12px !important; font-weight: 500 !important;
  padding: .32rem .6rem !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(34,211,238,.10) !important; border-color: rgba(154,203,255,.15) !important;
  transform: none; box-shadow: none;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: linear-gradient(135deg, rgba(34,211,238,.22), rgba(59,130,246,.22)) !important;
  border: 1px solid rgba(34,211,238,.45) !important; color: #a5f3fc !important;
  box-shadow: 0 0 18px rgba(34,211,238,.22), inset 0 1px 0 rgba(255,255,255,.09) !important;
}

/* ---------- buttons (main area) ---------- */
.stButton > button {
  border-radius: 12px !important;
  background: rgba(34,211,238,.09) !important;
  color: #bfeaff !important; border: 1px solid rgba(154,203,255,.22) !important;
  font-weight: 600 !important; transition: all .18s ease !important;
}
.stButton > button:hover {
  border-color: rgba(34,211,238,.55) !important;
  box-shadow: 0 6px 26px rgba(34,211,238,.28); transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #22d3ee 0%, #38bdf8 45%, #3b82f6 100%) !important;
  color: #041424 !important; border: none !important; font-weight: 800 !important;
  box-shadow: 0 10px 32px rgba(34,211,238,.38) !important;
}

/* ---------- ChatGPT-style conversation column ---------- */
.chat-col { max-width: 872px; margin: 0 auto; }

.umsg { display: flex; justify-content: flex-end; margin: .55rem 0; }
.umsg > div {
  background: linear-gradient(135deg, rgba(34,211,238,.16), rgba(59,130,246,.24));
  border: 1px solid rgba(103,232,249,.32);
  padding: .55rem .95rem; border-radius: 18px 18px 4px 18px;
  max-width: 78%; color: var(--hi); line-height: 1.55;
  box-shadow: 0 4px 18px rgba(2,8,23,.35), inset 0 1px 0 rgba(255,255,255,.07);
}
.amsg-meta { display:flex; align-items:center; gap:.45rem; margin:.6rem 0 .15rem; }
.amsg-avatar {
  width: 26px; height: 26px; border-radius: 999px; display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg,#164e63,#0e7490); border: 1px solid rgba(103,232,249,.4);
  font-size: .82rem; box-shadow: 0 0 14px rgba(34,211,238,.3);
}
.amsg-name { font-family: var(--mono); font-size: .68rem; letter-spacing:.08em; color:#7dd3fc; text-transform: uppercase; }
.amsg-body { border: 1px solid transparent; border-radius: 4px 18px 18px 18px; padding: .05rem .2rem .35rem; }

.msg-actions { display: flex; gap: .35rem; margin: .15rem 0 .5rem; opacity: .85; }
.msg-actions button { font-size: .72rem; }

/* typing cursor */
.cursor::after { content: "▌"; color:#22d3ee; animation: blink 1.1s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }

/* empty state */
.empty-wrap { max-width: 760px; margin: 8vh auto 0; text-align: center; }
.empty-glyph { font-size: 3.2rem; filter: drop-shadow(0 0 30px rgba(34,211,238,.55)); }
.empty-title {
  font-family: var(--sans); font-size: 1.65rem; font-weight: 700;
  letter-spacing: -.02em; margin: .5rem 0 .2rem;
  background: linear-gradient(95deg,#f2fbff 0%, #7dd3fc 35%, #38bdf8 60%, #818cf8 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.empty-sub { color: var(--mid); margin-bottom: 1.3rem; }

/* suggestion cards */
.suggest { text-align: left !important; min-height: 96px; }

/* generic pills */
.pill { display:inline-block; padding:.16rem .6rem; border-radius:8px; font-size:.7rem; font-weight:800;
        color:#fff; letter-spacing:.04em; font-family:var(--mono); }
.pill-high   { background: linear-gradient(135deg,#ef4444,#b91c1c); box-shadow: 0 0 14px rgba(239,68,68,.40); }
.pill-medium { background: linear-gradient(135deg,#f59e0b,#b45309); box-shadow: 0 0 14px rgba(245,158,11,.40); }
.pill-low    { background: linear-gradient(135deg,#22c55e,#15803d); box-shadow: 0 0 14px rgba(34,197,94,.40); }
.pill-info   { background: linear-gradient(135deg,#3b82f6,#1d4ed8); box-shadow: 0 0 14px rgba(59,130,246,.40); }
.pill-open   { background: rgba(71,85,105,.85); border:1px solid rgba(154,203,255,.25); }

/* citation cards */
.cite-card { border:1px solid var(--stroke); border-left:3px solid var(--accent);
             border-radius:12px; padding:.55rem .75rem; margin:.4rem 0;
             background: var(--glass-soft); backdrop-filter: blur(10px); font-size:.84rem;
             box-shadow: inset 0 1px 0 rgba(255,255,255,.06); }
.cite-card b { color: #7ff0ff; font-family: var(--mono); font-size:.78rem; }

/* HITL banner */
.hitl { border:1px solid rgba(248,113,113,.55);
        background: linear-gradient(160deg, rgba(69,10,10,.82), rgba(43,15,18,.82));
        backdrop-filter: blur(14px); border-radius:16px; padding:.8rem 1rem; margin-bottom:.6rem;
        color:#ffe4e4; box-shadow: 0 0 0 1px rgba(248,113,113,.15), 0 16px 48px rgba(239,68,68,.18); }
.hitl h4 { margin:0 0 .3rem 0; color:#fca5a5; letter-spacing:.04em; font-size:.86rem; font-weight:700; }
.hitl code { background:#3b1216; color:#fda4a4; border:1px solid rgba(248,113,113,.4);
             border-radius:6px; padding:.1rem .35rem; font-size:.82rem; font-family: var(--mono); }
.hitl b { color: #fecaca; }

/* verdict panel */
.verdict { border-radius:16px; padding:.75rem 1.05rem; margin:.35rem 0 .6rem 0; color:#fff;
           backdrop-filter: blur(12px);
           box-shadow: 0 18px 46px rgba(2,8,23,.5), inset 0 1px 0 rgba(255,255,255,.22); }
.verdict h3 { margin:0; font-size:1.05rem; font-family:var(--sans); }
.verdict small { opacity:.92; font-size:.78rem; font-family: var(--mono); }
.v-ground  { background: linear-gradient(135deg, rgba(127,29,29,.85), rgba(220,38,38,.75)); border:1px solid rgba(252,165,165,.5); }
.v-monitor { background: linear-gradient(135deg, rgba(120,53,15,.85), rgba(217,119,6,.75)); border:1px solid rgba(252,211,77,.5); }
.v-pass    { background: linear-gradient(135deg, rgba(20,83,45,.85), rgba(22,163,74,.75)); border:1px solid rgba(134,239,172,.5); }

.tiles { display:flex; gap:.5rem; flex-wrap:wrap; margin:.4rem 0 .6rem; }
.tile { flex:1 1 110px; background: var(--glass-soft); border:1px solid var(--stroke);
        border-radius:14px; padding:.5rem .6rem; text-align:center; backdrop-filter: blur(10px);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.07); }
.tile .k { color:#8fb4d8; font-size:.6rem; text-transform:uppercase; letter-spacing:.07em; }
.tile .v { color:#eef6ff; font-size:1.02rem; font-weight:800; font-family:var(--sans); }

.finding { display:flex; gap:.6rem; align-items:flex-start; border:1px solid var(--stroke);
           border-left:4px solid #64748b; border-radius:14px; padding:.55rem .75rem;
           margin:.35rem 0; background: var(--glass-soft); backdrop-filter: blur(10px);
           box-shadow: inset 0 1px 0 rgba(255,255,255,.05); }
.f-high   { border-left-color:#ef4444; box-shadow: inset 0 0 28px rgba(239,68,68,.09); }
.f-medium { border-left-color:#f59e0b; }
.f-low    { border-left-color:#eab308; }
.finding .icon { font-size:1.1rem; line-height:1.25; }
.finding .type { font-weight:700; color:#f3f8ff; font-size:.82rem; font-family: var(--mono); letter-spacing:.02em; }
.finding .desc { color:#a9c5e6; font-size:.8rem; line-height:1.45; }
.finding .mono { font-family: var(--mono); color:#67e8f9; font-size:.7rem;
                 background: rgba(34,211,238,.07); border:1px solid rgba(34,211,238,.18);
                 border-radius:6px; padding:.12rem .35rem; display:inline-block; margin-top:.25rem; }

.actions { border:1px dashed rgba(103,232,249,.4); border-radius:14px; padding:.55rem .85rem;
           background: rgba(34,211,238,.06); margin:.4rem 0; backdrop-filter: blur(8px); }
.actions b { color:#67e8f9; }
.actions li { color:#c4dcf5; font-size:.82rem; margin:.15rem 0; line-height:1.45; }
.rawhint { color:var(--faint); font-size:.76rem; }

/* ---------- native widgets: glass ---------- */
[data-testid="stMetric"] { background: var(--glass-soft); border:1px solid var(--stroke);
  border-radius:14px; padding:.55rem .75rem; backdrop-filter: blur(10px); }
[data-testid="stMetricValue"] { font-family:var(--sans); color:#eef6ff; }
[data-testid="stExpander"] { border:1px solid var(--stroke) !important; border-radius:14px !important;
  background: var(--glass-soft) !important; backdrop-filter: blur(10px); }
[data-testid="stChatInput"] { border:1px solid var(--stroke-hi) !important; border-radius:16px;
  background: rgba(13,21,38,.72); backdrop-filter: blur(12px); }
[data-testid="stChatInput"] textarea { background: transparent !important; color:#eef6ff !important; }
[data-testid="stAlert"] { border-radius:14px !important; border:1px solid var(--stroke); backdrop-filter: blur(8px); }
[data-testid="stPopover"], [data-testid="stPopoverBody"] { border-radius:14px !important; }
code, pre { font-family: var(--mono) !important; }

/* ---------- scrollbars & focus ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: rgba(154,203,255,.18); border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: rgba(154,203,255,.32); }
:focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; border-radius: 4px; }

/* ---------- vector icons & status dots (no emoji as structural icons) ---------- */
.ico { display:inline-flex; align-items:center; justify-content:center; vertical-align:-.18em; flex:0 0 auto; }
.ico svg { display:block; }
.sev-dot { display:inline-block; width:9px; height:9px; border-radius:999px; flex:0 0 auto;
           box-shadow:0 0 0 3px rgba(255,255,255,.06); }
.sev-high   { background:#f87171; box-shadow:0 0 10px rgba(248,113,113,.6); }
.sev-medium { background:#fbbf24; box-shadow:0 0 10px rgba(251,191,36,.5); }
.sev-low    { background:#a3e635; }
.sev-none   { background:#64748b; }

/* Pressed feedback — stable, no layout shift. Disabled states read as disabled. */
.stButton > button:active { transform: translateY(0) scale(.985) !important; }
.stButton > button:disabled { opacity:.45 !important; cursor:not-allowed !important; }
.stApp { scroll-padding-bottom: 5rem; }

/* ================= responsive / interaction polish ================= */
/* Soft lift on the elements people actually touch — makes the UI feel alive. */
.umsg > div, .cite-card, .tile, .finding, .verdict, .hitl, .suggest {
  transition: transform .2s cubic-bezier(.2,.8,.2,1), box-shadow .2s ease, border-color .2s ease !important;
}
.umsg > div:hover { transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(2,8,23,.55), inset 0 1px 0 rgba(255,255,255,.1); }
.cite-card:hover, .finding:hover { transform: translateX(3px); border-color: rgba(103,232,249,.4); }
.tile:hover { transform: translateY(-2px); border-color: rgba(154,203,255,.28); }

/* Compact top bar — shown only on small screens where the sidebar is hidden. */
.mtop { display: none; }
.mtop-status { color:#7dd3fc; font-family: var(--mono); font-size:.64rem; letter-spacing:.08em; }

@media (max-width: 1100px) {
  .block-container { max-width: 100%; padding-left: 1.1rem; padding-right: 1.1rem; }
}

@media (max-width: 860px) {
  .block-container { padding-top: 3.4rem; padding-left: .9rem; padding-right: .9rem; }
  .chat-col { max-width: 100%; }
  .empty-wrap { margin-top: 4vh; }
  .empty-title { font-size: 1.4rem; }
  .empty-glyph { font-size: 2.6rem; }
  .suggest { min-height: 80px; }
  .umsg > div { max-width: 88%; }
  .tiles { gap: .35rem; }
  .tile { flex: 1 1 30%; padding: .45rem .45rem; }
  .tile .v { font-size: .92rem; }
  .finding { padding: .45rem .6rem; }
  [data-testid="stChatInput"] { position: sticky; bottom: .5rem; z-index: 5; }
  /* Touch targets >= 44px on small screens. */
  .stButton > button, [data-testid="stSidebar"] .stButton > button { min-height: 44px !important; }
  [data-testid="stSidebar"] .stButton > button { padding: .55rem .7rem !important; }
  .msg-actions button { min-height: 44px; min-width: 44px; padding: .5rem .8rem; }
}

@media (max-width: 560px) {
  .block-container { padding-top: 3rem; padding-left: .6rem; padding-right: .6rem; }
  .empty-title { font-size: 1.2rem; }
  .empty-sub { font-size: .85rem; }
  .empty-glyph { font-size: 2.1rem; }
  .suggest { min-height: 64px; font-size: .76rem; }
  .tiles { display: grid; grid-template-columns: repeat(2, 1fr); }
  .tile { flex: none; }
  .tile .v { font-size: .88rem; }
  .umsg > div { max-width: 92%; padding: .5rem .75rem; }
  .hitl { padding: .6rem .7rem; }
  .verdict { padding: .6rem .8rem; }
  .verdict h3 { font-size: .92rem; }
  .mtop {
    display: flex; align-items: center; justify-content: space-between;
    padding: .5rem .75rem; margin-bottom: .7rem;
    background: var(--glass); border: 1px solid var(--stroke); border-radius: 12px;
    backdrop-filter: blur(12px);
  }
  .mtop b { font-family: var(--sans); letter-spacing: .02em; }
}

/* Respect reduced-motion preferences. */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
}
</style>
""", unsafe_allow_html=True)

# Rendered at the top of the main column; CSS keeps it hidden on desktop.
st.markdown(
    f'<div class="mtop"><b>{_ico("drone", 16)} Drone Ops Agent</b>'
    '<span class="mtop-status">DECISION SUPPORT</span></div>',
    unsafe_allow_html=True)

# v3 visual system lives in its own stylesheet; loaded last so it wins.
_CSS_V3 = Path(__file__).parent / "styles" / "v3.css"
if _CSS_V3.exists():
    st.markdown(f"<style>{_CSS_V3.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ------------------------------------------------------------------ helpers

def _ensure_index():
    """Embedded mode only: the corpus index lives on ephemeral disk; build once per boot."""
    if (ROOT / "data" / "vector_store.json").exists():
        return
    from backend.app.rag.ingest import ingest
    ingest(reset=True)


if EMBEDDED:
    _ensure_index()


def api_get(path: str, timeout: float = 10.0):
    if not EMBEDDED:
        try:
            r = httpx.get(f"{API}{path}", timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            return {"_error": str(exc)}
    from embedded_api import api_get as _embedded_get
    return _embedded_get(path, timeout)


def api_post(path: str, payload: dict, timeout: float = 120.0):
    if not EMBEDDED:
        try:
            r = httpx.post(f"{API}{path}", json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            return {"_error": str(exc)}
    from embedded_api import api_post as _embedded_post
    return _embedded_post(path, payload, timeout)


def api_download(path: str):
    """(status_code, content_bytes, filename) — uniform for HTTP and embedded mode."""
    if not EMBEDDED:
        try:
            r = httpx.post(f"{API}{path}", timeout=30.0)
            return r.status_code, r.content, f"{path.rsplit('/', 1)[-1]}.pdf"
        except Exception as exc:
            return 500, str(exc).encode("utf-8"), f"{path.rsplit('/', 1)[-1]}.txt"
    from embedded_api import api_download as _embedded_download
    return _embedded_download(path)


def _history_payload(messages: list[dict], limit: int = 12) -> list[dict]:
    hist = [{"role": m["role"], "content": m["text"]} for m in messages
            if m.get("text")][-limit:]
    return hist


def stream_chat(query: str, log_file: str | None = None):
    """Yield parsed SSE events from POST /chat (includes session history for memory)."""
    if not EMBEDDED:
        payload = {"query": query, "history": _history_payload(st.session_state.messages)}
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
    else:
        from embedded_api import stream_chat as _embedded_stream

        yield from _embedded_stream(query, log_file, _history_payload(st.session_state.messages))


def severity_pill(sev: str) -> str:
    sev = (sev or "?").upper()
    cls = {"HIGH": "pill-high", "MEDIUM": "pill-medium", "LOW": "pill-low"}.get(sev, "pill-info")
    return f'<span class="pill {cls}">{sev}</span>'


def copy_to_clipboard(text: str, label: str = "Copy"):
    safe = json.dumps(text[:4000])
    html = f"""
    <button id="c" style="cursor:pointer;display:inline-flex;align-items:center;gap:.35rem;border:1px solid rgba(154,203,255,.22);background:rgba(34,211,238,.07);color:#bfeaff;border-radius:9px;padding:.35rem .7rem;font-size:.76rem;font-family:'Fira Sans',sans-serif;font-weight:600;min-height:32px">{_ico("copy", 13)} {label}</button>
    <script>
      const b = document.getElementById('c');
      const orig = b.innerHTML;
      b.addEventListener('click', async () => {{
        try {{ await navigator.clipboard.writeText({safe}); b.textContent = 'Copied'; }}
        catch (e) {{ b.textContent = 'Select + Ctrl+C'; }}
        setTimeout(() => {{ b.innerHTML = orig; }}, 1600);
      }});
    </script>"""
    components.html(html, height=40)


_VERA = {
    "GROUND": ("x-circle", "GROUNDED — DO NOT FLY", "v-ground"),
    "MONITOR": ("alert-triangle", "MONITOR — RESTRICTED OPERATIONS", "v-monitor"),
    "PASS": ("check-circle", "PASS — NO ANOMALIES", "v-pass"),
}


def render_flight_panel(la: dict, ticket: dict | None):
    verdict = str(la.get("verdict", "")).upper()
    icon, label, cls = _VERA.get(verdict, ("alert-triangle", verdict or "UNKNOWN", "v-monitor"))
    st.markdown(
        f'<div class="verdict {cls}"><h3>{_ico(icon, 20)} {label}</h3>'
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
        dot = {"HIGH": "sev-high", "CRITICAL": "sev-high", "MEDIUM": "sev-medium",
               "LOW": "sev-low"}.get(sev, "sev-none")
        ev = a.get("evidence") or {}
        ev_txt = " · ".join(_fmt_evidence(k, v) for k, v in list(ev.items())[:6])
        st.markdown(
            f'<div class="finding {cls}"><div class="icon"><span class="sev-dot {dot}"></span></div><div>'
            f'<div class="type">{_html.escape(_friendly(a.get("type"), "Finding"))}</div>'
            f'<div class="desc">{_html.escape(str(a.get("description", "")))}</div>'
            + (f'<div class="mono">{_html.escape(ev_txt)}</div>' if ev_txt else "")
            + "</div></div>",
            unsafe_allow_html=True)

    if ticket:
        t_id = ticket.get("id", "?")
        t_sev = (ticket.get("severity") or "?").upper()
        st.markdown(
            f'<div class="actions"><b>Ticket {t_id}</b> · severity <b>{_html.escape(_friendly(t_sev))}</b>'
            f' · status {_html.escape(_friendly(ticket.get("status")))}<br/>'
            "Aircraft is <b>grounded pending inspection</b>. Technician sign-off required before next flight.</div>",
            unsafe_allow_html=True)
        if st.button("Export report (PDF)", key=f"panel-pdf-{t_id}"):
            code, content, fname = api_download(f"/report/{t_id}")
            if code == 200:
                st.download_button("Download PDF", content,
                                   file_name=fname, mime="application/pdf",
                                   key=f"panel-dl-{t_id}")
            else:
                st.error(content.decode("utf-8", "ignore"))


def _decide_approval(pending: dict, approved: bool):
    """Record the HITL decision, append the resumed answer, and close the dialog."""
    res = api_post("/approve", {"approval_id": pending["id"], "approved": approved,
                                "decided_by": "streamlit-operator"})
    decision = "APPROVED" if approved else "REJECTED"
    if "_error" in res:
        answer = f"Approval failed safe: {res['_error']}"
    else:
        answer = res.get("answer") or f"Authorization {_friendly(decision).lower()}."
    st.session_state.messages.append({"role": "assistant", "text": answer})
    st.session_state.pop("pending_approval", None)
    st.rerun()


@st.dialog("Human approval required")
def approval_dialog(pending: dict):
    """Modal popup: an authorization request must never hide above the fold."""
    st.markdown(
        f'<div class="hitl">{_ico("alert-triangle", 20)} <b>Human approval required</b><br/>'
        f'Action: <b>{_html.escape(_friendly(pending.get("action"), "authorization"))}</b> · '
        f'approval <code>{_html.escape(str(pending.get("id") or ""))}</code></div>',
        unsafe_allow_html=True)
    st.caption("Nothing launches until you decide — this is a safety control, not a suggestion.")
    with st.container(border=True):
        st.markdown(pending.get("summary") or "No summary provided.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Approve", type="primary", use_container_width=True, key="dlg-approve"):
            _decide_approval(pending, True)
    with c2:
        if st.button("Reject", use_container_width=True, key="dlg-reject"):
            _decide_approval(pending, False)


def _append_assistant_turn(answer: str, panel: dict | None = None, citations: list | None = None,
                           trace: list | None = None):
    st.session_state.messages.append({
        "role": "assistant", "text": answer, "panel": panel,
        "citations": citations or [], "trace": trace or [],
    })


def render_message(m: dict, index: int):
    if m["role"] == "user":
        st.markdown(f'<div class="umsg"><div>{_html.escape(m["text"])}</div></div>',
                    unsafe_allow_html=True)
        return

    st.markdown(f'<div class="amsg-meta"><div class="amsg-avatar">{_ico("drone", 15)}</div>'
                '<div class="amsg-name">Drone Ops Agent</div></div>', unsafe_allow_html=True)
    panel = m.get("panel")
    if panel:
        render_flight_panel(panel.get("log_analysis", {}), panel.get("ticket"))
    st.markdown(m.get("text", ""))
    if m.get("citations"):
        with st.expander(f"Sources ({len(m['citations'])})"):
            for i, c in enumerate(m["citations"], 1):
                loc = f"p.{c['page']}" if c.get("page") else (c.get("section") or "")
                st.markdown(
                    f'<div class="cite-card"><b>[{i}] {c.get("source")}</b><br>{loc}<br>relevance {c.get("score", 0):.3f}</div>',
                    unsafe_allow_html=True)
    if m.get("trace"):
        with st.expander("Agent trace"):
            st.markdown(" → ".join(f"{_friendly(s)}" for s in m["trace"]))

    c1, c2, _ = st.columns([1.4, 1.4, 8])
    with c1:
        copy_to_clipboard(m.get("text", ""))
    with c2:
        if st.button("Regenerate", key=f"regen-{index}"):
            # re-ask the previous user message, dropping this assistant reply
            msgs = st.session_state.messages
            for j in range(index - 1, -1, -1):
                if msgs[j]["role"] == "user":
                    st.session_state.messages = msgs[:j]
                    st.session_state.queued_prompt = msgs[j]["text"]
                    st.rerun()
                    break


def handle_query(prompt: str, show_user: bool = True):
    """Stream one agent turn and render it; append to session messages."""
    if show_user:
        st.session_state.messages.append({"role": "user", "text": prompt})
        st.markdown(f'<div class="umsg"><div>{_html.escape(prompt)}</div></div>',
                    unsafe_allow_html=True)

    st.markdown(f'<div class="amsg-meta"><div class="amsg-avatar">{_ico("drone", 15)}</div>'
                '<div class="amsg-name">Drone Ops Agent</div></div>',
                unsafe_allow_html=True)
    status = st.status("Drone Ops Agent is thinking…", expanded=True)
    final_answer, citations, trace, tool_results = "", [], [], {}
    steps: list[str] = []
    for event in stream_chat(prompt):
        etype = event.get("type")
        if etype == "node":
            steps.append(event.get("node"))
            status.write(f"▸ {_friendly(event.get('node'))} ▌")
        elif etype == "approval_required":
            st.session_state.pending_approval = {
                "id": event.get("approval_id"),
                "action": event.get("action"),
                "summary": event.get("summary"),
            }
            final_answer = ("This flight requires your explicit approval "
                            "before any takeoff/arm authorization. See the approval panel.")
            trace = steps
        elif etype == "final":
            final_answer = event.get("answer", "")
            citations = event.get("citations", [])
            trace = event.get("trace", steps)
            tool_results = event.get("tool_results") or {}
        elif etype == "error":
            final_answer = (f"Agent error: {event.get('error')}\n\n"
                            f"{event.get('safe_default', 'Do not launch.')}")
    status.update(label="Done", state="complete")

    panel = {"log_analysis": tool_results.get("log_analysis"),
             "ticket": tool_results.get("ticket")} if tool_results.get("log_analysis") else None
    if panel:
        render_flight_panel(panel["log_analysis"], panel.get("ticket"))
        with st.expander("Raw agent answer"):
            st.markdown(final_answer)
    else:
        st.markdown(final_answer)

    _append_assistant_turn(final_answer, panel, citations, trace)


# ------------------------------------------------------------------ sidebar
health = api_get("/health")
api_ok = "_error" not in health
true_pending = api_get("/approvals/pending") if api_ok else []
pending_n = len(true_pending) if isinstance(true_pending, list) else 0

NAV = [
    ("Chat", "chat"),
    ("Tickets", "tickets"),
    ("Approvals", "approvals"),
    ("Flight logs", "logs"),
    ("Runs", "runs"),
]
if "nav" not in st.session_state:
    st.session_state.nav = "chat"
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown(f'<div class="brand"><div class="logo">{_ico("drone", 22)}</div><div>'
                '<div class="name">Drone Ops Agent</div>'
                '<div class="sub">Multi-agent RAG · UAS fleet readiness</div>'
                "</div></div>", unsafe_allow_html=True)

    if st.button("New chat", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("pending_approval", None)
        st.session_state.pop("queued_prompt", None)
        st.session_state.nav = "chat"
        st.rerun()

    st.markdown('<div class="nav-label">Workspace</div>', unsafe_allow_html=True)
    for label, key in NAV:
        badge = ""
        if key == "approvals" and pending_n:
            badge = f"  ·  {pending_n}"
        btn_type = "primary" if st.session_state.nav == key else "secondary"
        if st.button(f"{label}{badge}", key=f"nav-{key}",
                     use_container_width=True, type=btn_type):
            st.session_state.nav = key
            st.rerun()

    st.divider()
    st.markdown('<div class="nav-label">System</div>', unsafe_allow_html=True)
    if not api_ok:
        st.warning(f"API unreachable at {API}")
    else:
        llm = "Groq (online)" if health.get("llm_available") else "OFFLINE fallback"
        st.markdown(f"LLM &nbsp;**{llm}**", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("Vector docs", health.get("vector_store_docs", "—"))
        c2.metric("Embeddings", str(health.get("embedding_provider", "local")))
        tracing = "on" if health.get("langsmith_tracing") else "off"
        st.caption(f"app {health.get('app_env', '?')} · v{health.get('version', '?')} · tracing {tracing}")
    st.divider()

    st.markdown('<div class="nav-label">Quick prompts</div>', unsafe_allow_html=True)
    for label, q in [
        ("Part 107 over-people rule", "Is flying over people legal under Part 107?"),
        ("Analyze last flight log", "Analyze the last flight log and open a maintenance ticket if needed"),
        ("VX-6 20-min inspection", "Can I fly the VX-6 on a 20-min inspection mission at 120m and what are the risks?"),
        ("DGCA yellow-zone rules", "What is required to fly a drone in a yellow zone in India?"),
    ]:
        if st.button(label, use_container_width=True, key=f"qp-{label}"):
            st.session_state.queued_prompt = q
            st.session_state.nav = "chat"
            st.rerun()

    st.divider()
    with st.expander("About"):
        st.markdown(
            "Answers grounded in the bundled corpus (**FAA Part 107 · EASA Open Category · DGCA Drone Rules · "
            "VX-6 manual · maintenance checklist · UAV paper**) with `[n]` citations. Anything shaped like "
            "takeoff/arm authorization pauses for explicit human approval. **Decision support only — "
            "never an autonomous authorizer.**")

# ================================================================== CHAT
if st.session_state.nav == "chat":
    # Always-visible quick prompts — no sidebar scrolling required.
    st.markdown('<div class="qbar-label">QUICK PROMPTS</div>', unsafe_allow_html=True)
    qbar = st.columns(4)
    for qi, (qlabel, qtext) in enumerate([
        ("Part 107 legality", "Is flying over people legal under Part 107?"),
        ("Analyze flight log", "Analyze the last flight log and open a maintenance ticket if needed"),
        ("Plan a mission", "Can I fly the VX-6 on a 20-min inspection mission at 120m and what are the risks?"),
        ("DGCA yellow zone", "What is required to fly a drone in a yellow zone in India?"),
    ]):
        with qbar[qi]:
            if st.button(qlabel, key=f"qbar-{qi}", use_container_width=True, help=qtext):
                st.session_state.queued_prompt = qtext
                st.rerun()
    st.markdown('<div class="qbar-div"></div>', unsafe_allow_html=True)

    if not st.session_state.messages:
        docs = health.get("vector_store_docs", "—")
        llm_state = "Groq online" if health.get("llm_available") else "Offline mode"
        st.markdown(
            f'<div class="hero">'
            '<div class="hero-eyebrow"><span class="live-dot"></span> UAV fleet intelligence · decision support</div>'
            f'<div class="hero-glyph">{_ico("drone", 38)}</div>'
            '<div class="hero-title">How can I help<br/>with your fleet today?</div>'
            '<div class="hero-sub">Grounded answers, cited sources, and human-approved '
            'authorizations — in one mission-control workspace.</div>'
            '<div class="hero-meta">'
            f'<span>{_html.escape(str(docs))} documents indexed</span>'
            f'<span>{llm_state}</span>'
            '<span>Human approval enforced</span></div></div>',
            unsafe_allow_html=True)
        cols = st.columns(2)
        suggestions = [
            ("Legality check", "Is flying over people legal under Part 107?"),
            ("Analyze the flight log", "Analyze the last flight log and open a maintenance ticket if needed"),
            ("Plan a mission", "Can I fly the VX-6 on a 20-min inspection mission at 120m?"),
            ("DGCA rules", "What is required to fly a drone in a yellow zone in India?"),
        ]
        for i, (title, q) in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(f"{title}", key=f"sugg-{i}", use_container_width=True,
                             help=q):
                    st.session_state.queued_prompt = q
                    st.rerun()

    else:
        for i, m in enumerate(st.session_state.messages):
            render_message(m, i)
            # inline edit for user turns
            if m["role"] == "user":
                if st.session_state.get("editing") == i:
                    edited = st.text_area("Edit prompt", value=m["text"], key=f"edit-{i}", height=90)
                    c1, c2, _ = st.columns([1, 1, 6])
                    if c1.button("Send", key=f"send-{i}", type="primary"):
                        st.session_state.messages = st.session_state.messages[:i]
                        st.session_state.queued_prompt = edited
                        st.session_state.pop("editing", None)
                        st.rerun()
                    if c2.button("Cancel", key=f"cancel-{i}"):
                        st.session_state.pop("editing", None)
                        st.rerun()
                else:
                    if st.button("Edit", key=f"edit-btn-{i}", help="Edit and resend"):
                        st.session_state.editing = i
                        st.rerun()

    queued = st.session_state.pop("queued_prompt", None)
    chat_input = st.chat_input("Ask about legality, maintenance, missions…")
    prompt = queued or chat_input
    if prompt:
        st.session_state.pop("editing", None)
        handle_query(prompt)
        if st.session_state.get("pending_approval"):
            st.rerun()

# ================================================================== TICKETS
elif st.session_state.nav == "tickets":
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
        st.info("No tickets yet — analyze a flight log from the Flight logs section.")
    for t in tickets:
        with st.container(border=True):
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
            if st.button("Export PDF", key=f"pdf-{t.get('id')}"):
                code, content, fname = api_download(f"/report/{t.get('id')}")
                if code == 200:
                    st.download_button("Download PDF", content,
                                       file_name=fname,
                                       mime="application/pdf", key=f"dl-{t.get('id')}")
                else:
                    st.error(content.decode("utf-8", "ignore"))

# ================================================================== APPROVALS
elif st.session_state.nav == "approvals":
    st.subheader("Pending human approvals")
    st.caption("Authorization-shaped actions (takeoff/arm) always pause here. Nothing launches without a decision.")
    pending = api_get("/approvals/pending")
    if not isinstance(pending, list):
        pending = []
    if pending:
        for p in pending:
            st.markdown(
                '<div class="hitl"><h4>'
                f'{_html.escape(_friendly(p.get("action"), "Authorization"))} required</h4>'
                f'Approval <code>{_html.escape(str(p.get("id") or ""))}</code> · '
                f'thread <code>{_html.escape(str(p.get("thread_id") or ""))}</code>'
                "</div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(p.get("summary", ""))
                c1, c2, _ = st.columns([1, 1, 4])
                if c1.button("Approve", key=f"ap-{p['id']}", type="primary"):
                    api_post("/approve", {"approval_id": p["id"], "approved": True,
                                          "decided_by": "streamlit-operator"})
                    st.rerun()
                if c2.button("Reject", key=f"rj-{p['id']}"):
                    api_post("/approve", {"approval_id": p["id"], "approved": False,
                                          "decided_by": "streamlit-operator"})
                    st.rerun()
    else:
        st.success("No approvals pending.")

# ================================================================== FLIGHT LOGS
elif st.session_state.nav == "logs":
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
            if c2.button("Analyze", key=f"log-{name}", use_container_width=True):
                st.session_state.queued_prompt = (
                    f"Analyze flight log {name} and open a maintenance ticket if needed")
                st.session_state.nav = "chat"
                st.rerun()

# ================================================================== RUNS
elif st.session_state.nav == "runs":
    st.subheader("Recent agent runs")
    st.caption("Audit trail of /chat invocations recorded by the API.")
    data = api_get("/logs?limit=25")
    runs = data.get("runs", []) if isinstance(data, dict) else []
    if not runs:
        st.info("No runs recorded yet.")
    for r in runs:
        status_ = (r.get("status") or "?").lower()
        dot = ("sev-low" if status_ == "completed" else
               "sev-high" if status_ in {"approval_required", "paused", "awaiting_approval"} else "sev-medium")
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(
                f'<div style="display:flex;align-items:center;gap:.55rem">'
                f'<span class="sev-dot {dot}"></span><b>{_html.escape(str(r.get("query", "")))}</b></div>',
                unsafe_allow_html=True)
            c1.caption(f"{r.get('started_at', '')} · run `{r.get('id', '')[:12]}`")
            c2.markdown(f'<span class="pill pill-info">{_html.escape(_friendly(r.get("classification")))}</span>',
                        unsafe_allow_html=True)

# ============================================================ HITL MODAL (popup)
# Rendered last so the authorization decision is always centred on screen,
# never scrolled above the conversation under a sticky header.
if st.session_state.get("pending_approval"):
    approval_dialog(st.session_state.pending_approval)
