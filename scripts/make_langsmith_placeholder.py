"""Generate an honest placeholder for docs/langsmith_trace.png (replace with a real trace)."""
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    raise SystemExit(f"Pillow required: {e}")

out = Path(__file__).resolve().parents[1] / "docs" / "langsmith_trace.png"
img = Image.new("RGB", (1200, 700), color=(245, 247, 250))
d = ImageDraw.Draw(img)
d.rectangle([40, 40, 1160, 660], outline=(180, 0, 0), width=4)
try:
    font = ImageFont.truetype("arial.ttf", 34)
    font2 = ImageFont.truetype("arial.ttf", 23)
except Exception:
    font = font2 = ImageFont.load_default()

d.text((70, 80), "LangSmith Trace Screenshot — PLACEHOLDER (replace with a real trace)", fill=(180, 0, 0), font=font)
lines = [
    "1) .env: LANGSMITH_TRACING=true, LANGSMITH_API_KEY=<rotated key>,",
    "    LANGSMITH_PROJECT=droneops, LANGSMITH_ENDPOINT=https://aws.api.smith.langchain.com",
    "2) Restart API; run a traced query (POST /chat or Streamlit).",
    "3) Open LangSmith (project 'droneops') → capture the run/graph trace.",
    "4) Replace this file with the real screenshot: docs/langsmith_trace.png",
    "",
    "Expected trace: triage → specialist → safety_supervisor → (human_approval) → finalize,",
    "including tool calls (retrieval, battery/log/airspace) and citations.",
]
y = 165
for line in lines:
    d.text((70, y), line, fill=(30, 30, 30), font=font2)
    y += 42
out.parent.mkdir(parents=True, exist_ok=True)
img.save(out)
print("wrote", out)
