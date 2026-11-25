"""Drone Ops Agent — public entry point.

Streamlit Cloud runs this file, so it hosts the React SPA ("NIGHTWATCH") as a
custom component and serves every API request through the in-process agent.
The legacy Streamlit UI is preserved in ``frontend/legacy_app.py``.
"""
import asyncio
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st
import streamlit.components.v1 as components

from backend.app import main as api
from backend.app.db import get_session
from backend.app.schemas import ApproveRequest, ChatRequest
from frontend.spa_component import nightwatch_spa

# Every visitor to the old Streamlit link is sent to the production deployment.
# Add ?legacy=1 to the URL to keep the embedded demo reachable for internal QA.
RENDER_URL = "https://drone-ops-agent-2c27.onrender.com/"


def _redirect_page() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet" />
<style>
  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; background: #050607; }
  body {
    display: grid; place-items: center; padding: 24px;
    color: #F2F4EA; font-family: 'Google Sans', system-ui, sans-serif;
    background: radial-gradient(ellipse at 50% 30%, rgba(216,255,62,.07), transparent 62%), #050607;
  }
  .card {
    width: min(520px, 100%); padding: 34px 32px;
    border: 1px solid rgba(216,255,62,.26); border-radius: 16px;
    background: rgba(13,16,13,.85);
    box-shadow: 0 30px 90px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.04);
  }
  .eyebrow {
    font-family: 'Fira Code', monospace; font-size: .58rem; letter-spacing: .2em;
    text-transform: uppercase; color: #D8FF3E; display: flex; align-items: center; gap: 9px;
  }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: #D8FF3E; box-shadow: 0 0 12px #D8FF3E; }
  h1 { font-size: clamp(2.1rem, 6vw, 3rem); line-height: 1.05; letter-spacing: -.055em; margin: 20px 0 14px; }
  h1 em { font-style: normal; color: #D8FF3E; }
  p { color: #a9b4a5; line-height: 1.65; font-size: .95rem; margin: 0 0 24px; }
  .btn {
    display: inline-flex; align-items: center; gap: 10px; min-height: 46px;
    padding: 0 18px; border-radius: 9px; text-decoration: none;
    background: #D8FF3E; color: #0a0c04; font-weight: 700; font-size: .9rem;
  }
  .btn span { font-size: 1.1rem; }
  .url {
    margin-top: 20px; font-family: 'Fira Code', monospace; font-size: .62rem;
    color: #7d887a; overflow-wrap: anywhere;
  }
  .count { margin-top: 10px; font-family: 'Fira Code', monospace; font-size: .56rem; color: #5f6b5e; }
</style>
</head>
<body>
  <div class="card">
    <div class="eyebrow"><span class="dot"></span> DRONE OPS / MOVED</div>
    <h1>New home,<br><em>same mission.</em></h1>
    <p>This demo has moved to its production deployment. The new app will open in a new tab automatically — or use the button below.</p>
    <a class="btn" href="__URL__" target="_blank" rel="noopener">Open the new app <span>→</span></a>
    <div class="url">__URL__</div>
    <div class="count">OPENING NEW TAB AUTOMATICALLY · 3s</div>
  </div>
<script>
  // Streamlit Cloud sandboxes its iframe without top-navigation permission,
  // so a same-tab redirect is impossible. A form submission to a new tab is
  // the reliable automatic equivalent; the button is the manual fallback.
  setTimeout(function () {
    try {
      var form = document.createElement('form');
      form.action = "__URL__";
      form.method = "GET";
      form.target = "_blank";
      document.body.appendChild(form);
      form.submit();
    } catch (e) {
      window.open("__URL__", "_blank", "noopener");
    }
  }, 3000);
</script>
</body>
</html>
""".replace("__URL__", RENDER_URL)


def _ensure_index():
    """Streamlit Cloud has ephemeral disk: build the corpus index once per boot."""
    from backend.app.config import get_settings

    settings = get_settings()
    backend = settings.vector_backend
    if backend == "auto":
        backend = "pinecone" if settings.pinecone_api_key else "local"
    if backend != "local" or (ROOT / "data" / "vector_store.json").exists():
        return
    from backend.app.rag.ingest import ingest

    ingest(reset=True)


st.set_page_config(page_title="Drone Ops Agent", layout="wide", initial_sidebar_state="collapsed")

# Remove Streamlit chrome: the SPA owns the entire viewport.
st.markdown(
    """
    <style>
      header, footer, #MainMenu, .stDeployButton {visibility: hidden !important;}
      #stStatusWidget, [data-testid="stStatusWidget"], .stStatusWidget {display: none !important;}
      html, body, .stApp {overflow: hidden !important;}
      .block-container {padding: 0 !important; max-width: none !important;}
      .stApp {background: #050607 !important;}
      div[data-testid="stIFrame"] iframe {display: block; width: 100% !important; height: 100vh !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Recruiters and other visitors land here first: ask them to use the new app,
# then send them there. `?legacy=1` keeps the embedded demo reachable for QA.
if st.query_params.get("legacy") != "1":
    components.html(_redirect_page(), height=680)
    st.stop()

_ensure_index()


def _health():
    return api.health().model_dump()


def _logs(payload):
    return api.logs(limit=int(payload.get("limit") or 40)).model_dump()


def _chat(payload):
    # Reuse the exact FastAPI SSE stream so behaviour cannot drift.
    response = asyncio.run(api.chat(ChatRequest(**payload)))

    async def collect():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))
        return "".join(chunks)

    return asyncio.run(collect())


def _approve(payload):
    with get_session() as session:
        return api.approve(ApproveRequest(**payload), session)


def _report(payload):
    ticket_id = str(payload.get("id") or "")
    response = api.report(ticket_id)
    return base64.b64encode(Path(response.path).read_bytes()).decode("ascii")


HANDLERS = {
    "health": lambda payload: _health(),
    "logs": _logs,
    "pending": lambda payload: api.approvals_pending(),
    "ticket": lambda payload: api.ticket_detail(str(payload.get("id") or "")),
    "approve": _approve,
    "chat": _chat,
    "report": _report,
}


def handle(request):
    kind = request.get("kind")
    handler = HANDLERS.get(kind)
    if handler is None:
        raise ValueError(f"unknown request: {kind}")
    return handler(request.get("payload") or {})


# The component calls back with one request per Streamlit rerun. Responses are
# stored in session state and handed back through component args.
value = nightwatch_spa(response=st.session_state.get("spa_response"))
if isinstance(value, dict) and value.get("id") and value["id"] != st.session_state.get("spa_request_id"):
    request_id = value["id"]
    st.session_state["spa_request_id"] = request_id
    try:
        data = handle(value)
        st.session_state["spa_response"] = {"id": request_id, "ok": True, "data": data}
    except Exception as exc:  # surfaced in the UI as a failed request
        st.session_state["spa_response"] = {"id": request_id, "ok": False, "error": str(exc)}
    st.rerun()
