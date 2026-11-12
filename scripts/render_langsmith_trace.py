"""Render a real LangSmith trace (fetched read-only via the API) into an HTML snapshot.

Usage: python scripts/render_langsmith_trace.py <trace_id>
Writes: docs/langsmith_trace.html
"""
import html
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from langsmith import Client  # noqa: E402

TRACE_ID = sys.argv[1] if len(sys.argv) > 1 else None
if not TRACE_ID:
    raise SystemExit("usage: render_langsmith_trace.py <trace_id>")

client = Client(api_url=os.environ.get("LANGSMITH_ENDPOINT") or None,
                api_key=os.environ.get("LANGSMITH_API_KEY"))
project = os.environ.get("LANGSMITH_PROJECT", "droneops")

runs = list(client.list_runs(trace_id=TRACE_ID, limit=100))
if not runs:
    raise SystemExit(f"no runs found for trace {TRACE_ID}")

by_id = {r.id: r for r in runs}
children: dict = {}
for r in runs:
    children.setdefault(str(r.parent_run_id) if r.parent_run_id else None, []).append(r)
for v in children.values():
    v.sort(key=lambda x: x.start_time or datetime.min)

root = next((r for r in runs if not r.parent_run_id), runs[0])


def dur_ms(r):
    if not r.end_time or not r.start_time:
        return None
    return (r.end_time - r.start_time).total_seconds() * 1000


def fmt_ms(ms):
    if ms is None:
        return "—"
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.2f} s"


def status_chip(r):
    st = (r.status or "unknown").lower()
    color = {"success": "#16a34a", "error": "#dc2626", "running": "#2563eb"}.get(st, "#6b7280")
    return f'<span class="chip" style="background:{color}">{html.escape(st)}</span>'


def rows(node, depth=0):
    out = []
    d = dur_ms(node)
    icon = {"chain": "🔗", "llm": "🤖", "tool": "🛠", "retriever": "📚"}.get(node.run_type, "•")
    cls = "row error" if (node.status or "").lower() == "error" else "row"
    out.append(
        f'<div class="{cls}" style="padding-left:{14 + depth * 26}px">'
        f'<span class="icon">{icon}</span>'
        f'<span class="name">{html.escape(node.name)}</span>'
        f'<span class="type">{html.escape(node.run_type)}</span>'
        f'{status_chip(node)}'
        f'<span class="dur">{fmt_ms(d)}</span></div>'
    )
    for c in children.get(str(node.id), []):
        out.extend(rows(c, depth + 1))
    return out


def pretty(v, limit=1400):
    if v is None:
        return "—"
    try:
        s = json.dumps(v, indent=2, ensure_ascii=False, default=str)
    except Exception:
        s = str(v)
    if len(s) > limit:
        s = s[:limit] + "\n… (truncated)"
    return html.escape(s)


root_dur = dur_ms(root)
started = root.start_time.isoformat() if root.start_time else ""
trace_rows = "\n".join(rows(root))
total_spans = len(runs)
errors = sum(1 for r in runs if (r.status or "").lower() == "error")

page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>LangSmith trace — {html.escape(project)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; background:#f7f7f8; color:#18181b; }}
  .top {{ background:#fff; border-bottom:1px solid #e4e4e7; padding:14px 16px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
  .logo {{ width:30px; height:30px; border-radius:8px; background:#7c3aed; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; }}
  .title {{ font-size:16px; font-weight:700; }}
  .sub {{ color:#71717a; font-size:11.5px; margin-top:2px; word-break:break-all; }}
  .badge {{ margin-left:auto; background:#f4f4f5; border:1px solid #e4e4e7; border-radius:999px; padding:5px 12px; font-size:11.5px; color:#52525b; }}
  .wrap {{ display:flex; flex-direction:column; gap:14px; padding:16px; }}
  @media (min-width: 1000px) {{ .wrap {{ display:grid; grid-template-columns: 1.15fr .85fr; gap:18px; padding:20px 26px 26px; }} }}
  .card {{ background:#fff; border:1px solid #e4e4e7; border-radius:12px; overflow:hidden; }}
  .card h3 {{ margin:0; padding:13px 16px; font-size:13px; letter-spacing:.02em; text-transform:uppercase; color:#71717a; border-bottom:1px solid #f0f0f1; }}
  .tree {{ padding:6px 0 10px; }}
  .row {{ display:flex; align-items:center; gap:7px; padding:8px 10px 8px 10px; border-bottom:1px solid #f7f7f8; font-size:12.5px; flex-wrap:wrap; }}
  .row:hover {{ background:#fafafa; }}
  .row.error {{ background:#fef2f2; }}
  .icon {{ width:16px; text-align:center; }}
  .name {{ font-weight:600; }}
  .type {{ color:#a1a1aa; font-size:10.5px; border:1px solid #e4e4e7; border-radius:6px; padding:1px 5px; }}
  .chip {{ margin-left:auto; color:#fff; font-size:10px; font-weight:700; padding:2px 7px; border-radius:999px; text-transform:uppercase; letter-spacing:.03em; }}
  .dur {{ width:58px; text-align:right; color:#52525b; font-variant-numeric:tabular-nums; font-size:11px; }}
  .meta {{ display:grid; grid-template-columns:1fr 1fr; gap:10px 12px; padding:12px; font-size:11.5px; }}
  .meta div span {{ display:block; color:#a1a1aa; font-size:10px; text-transform:uppercase; letter-spacing:.05em; margin-bottom:2px; }}
  .code {{ margin:0 12px 12px; background:#0b1020; color:#d6e2ff; border-radius:9px; padding:10px 12px; font-family: ui-monospace, Consolas, monospace; font-size:10.5px; line-height:1.5; white-space:pre-wrap; overflow:hidden; }}
  .foot {{ padding:0 16px 18px; color:#a1a1aa; font-size:11px; }}
</style></head>
<body>
  <div class="top">
    <div class="logo">L</div>
    <div>
      <div class="title">LangSmith · Trace view</div>
      <div class="sub">project <b>{html.escape(project)}</b> · trace <b>{html.escape(TRACE_ID)}</b></div>
    </div>
    <div class="badge">{total_spans} spans · {errors} errors · {fmt_ms(root_dur)}</div>
  </div>
  <div class="wrap">
    <div class="card">
      <h3>Run tree</h3>
      <div class="tree">{trace_rows}</div>
    </div>
    <div class="card">
      <h3>Root run · {html.escape(root.name)}</h3>
      <div class="meta">
        <div><span>Run ID</span>{html.escape(str(root.id))}</div>
        <div><span>Started</span>{html.escape(started)}</div>
        <div><span>Status</span>{status_chip(root)}</div>
        <div><span>Duration</span>{fmt_ms(root_dur)}</div>
      </div>
      <h3 style="border-top:1px solid #f0f0f1">Inputs</h3>
      <pre class="code">{pretty(root.inputs, 900)}</pre>
      <h3>Outputs</h3>
      <pre class="code">{pretty(root.outputs, 900)}</pre>
    </div>
  </div>
  <div class="foot">Fetched read-only from the LangSmith API ({html.escape(os.environ.get("LANGSMITH_ENDPOINT", ""))}) for project {html.escape(project)}. Rendered snapshot of a real trace — not a mock.</div>
</body></html>"""

out = ROOT / "docs" / "langsmith_trace.html"
out.write_text(page, encoding="utf-8")
print("wrote", out, "spans", total_spans, "errors", errors)
