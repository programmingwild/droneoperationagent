"""Capture an authenticated LangSmith UI screenshot with headless Edge via CDP.

The LangSmith web app requires an interactive login. This script reuses the
session that already exists in the user's browser: the caller passes a JSON file
containing the `sb-auth-auth-token` localStorage value (a Supabase session).
The token is never written into the repo.

Usage:
    python scripts/capture_langsmith_ui.py <session_json> <url> <out.png> [--height N]

Requires Microsoft Edge (or Chrome) at the default Windows path.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9333


def _http(path: str, method: str = "GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


async def _cdp(ws, msg_id, method, params=None):
    await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=60)
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


async def capture(session_value: str, url: str, out: Path, height: int, width: int = 1440, post_js: str = "") -> None:
    profile = Path(tempfile.mkdtemp(prefix="ls-capture-"))
    proc = subprocess.Popen(
        [
            EDGE,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(60):
            try:
                _http("/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("Edge CDP did not start")

        target = _http("/json/new?about:blank", method="PUT")
        ws_url = target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
            i = 0

            async def cmd(method, params=None):
                nonlocal i
                i += 1
                return await _cdp(ws, i, method, params)

            await cmd("Page.enable")
            await cmd("Runtime.enable")
            await cmd("Network.enable")

            # Land on the origin first so localStorage is writable.
            await cmd("Page.navigate", {"url": "https://smith.langchain.com/"})
            await asyncio.sleep(4)
            await cmd(
                "Runtime.evaluate",
                {
                    "expression": (
                        "localStorage.setItem('sb-auth-auth-token', "
                        + json.dumps(session_value)
                        + "); localStorage.setItem('ls:auth:hasSignedIn','true'); 'ok'"
                    )
                },
            )

            await cmd("Page.navigate", {"url": url})
            await asyncio.sleep(12)
            if post_js:
                await cmd("Runtime.evaluate", {"expression": post_js})
                await asyncio.sleep(4)

            shot = await cmd(
                "Page.captureScreenshot",
                {"format": "png", "captureBeyondViewport": False},
            )
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(__import__("base64").b64decode(shot["data"]))
            title = await cmd("Runtime.evaluate", {"expression": "document.title", "returnByValue": True})
            print("wrote", out, "| title:", title.get("result", {}).get("value"))
    finally:
        proc.terminate()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("usage: capture_langsmith_ui.py <session_json> <url> <out.png> [--height N]")
    session_file, url, out_file = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    height = 1100
    width = 1440
    post_js = ""
    if "--height" in sys.argv:
        height = int(sys.argv[sys.argv.index("--height") + 1])
    if "--width" in sys.argv:
        width = int(sys.argv[sys.argv.index("--width") + 1])
    if "--js" in sys.argv:
        post_js = sys.argv[sys.argv.index("--js") + 1]
    session = Path(session_file).read_text(encoding="utf-8").strip()
    asyncio.run(capture(session, url, out_file, height, width, post_js))
