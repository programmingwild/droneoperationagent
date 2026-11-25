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

from backend.app import main as api
from backend.app.db import get_session
from backend.app.schemas import ApproveRequest, ChatRequest
from frontend.spa_component import nightwatch_spa

st.set_page_config(page_title="Drone Ops Agent", layout="wide", initial_sidebar_state="collapsed")

# Remove Streamlit chrome: the SPA owns the entire viewport.
st.markdown(
    """
    <style>
      header, footer, #MainMenu, .stDeployButton {visibility: hidden !important;}
      .block-container {padding: 0 !important; max-width: none !important;}
      .stApp {background: #050607 !important;}
      div[data-testid="stIFrame"] iframe {display: block; width: 100% !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


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
