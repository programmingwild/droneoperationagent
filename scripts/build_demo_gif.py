"""Build docs/demo.gif from real UI captures + composed title cards (PIL).

Frames: title card -> maintenance verdict (real) -> live HITL banner (real) -> authorized (real)
        -> end card (architecture summary). Real captures are downscaled to a common width.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
W = 880
BG = (14, 17, 23)
ACCENT = (255, 75, 75)
WHITE = (240, 240, 240)
GRAY = (150, 158, 171)
GREEN = (46, 204, 113)

FONT_PATHS = [
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def font(size: int, bold: bool = False):
    candidates = [FONT_PATHS[0] if bold else FONT_PATHS[1], FONT_PATHS[2], FONT_PATHS[3]]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def card(lines: list[tuple[str, int, tuple, bool]], footer: str | None = None) -> Image.Image:
    """Compose a title card. lines = [(text, size, color, bold)]."""
    img = Image.new("RGB", (W, 500), BG)
    draw = ImageDraw.Draw(img)
    # accent bar
    draw.rectangle([0, 0, W, 6], fill=ACCENT)
    y = 110
    for text, size, color, bold in lines:
        f = font(size, bold)
        draw.text((60, y), text, font=f, fill=color)
        y += int(size * 1.5)
    if footer:
        draw.text((60, 440), footer, font=font(17), fill=GRAY)
    return img


def real_frame(src: Path, caption: str) -> Image.Image:
    if not src.exists():
        # placeholder-free: skip frame entirely if capture missing
        return None
    shot = Image.open(src).convert("RGB")
    scale = W / shot.width
    shot = shot.resize((W, int(shot.height * scale)))
    bar = Image.new("RGB", (W, 56), BG)
    draw = ImageDraw.Draw(bar)
    draw.rectangle([0, 0, 6, 56], fill=ACCENT)
    draw.text((22, 16), caption, font=font(19, bold=True), fill=WHITE)
    frame = Image.new("RGB", (W, shot.height + 56), BG)
    frame.paste(bar, (0, 0))
    frame.paste(shot, (0, 56))
    return frame


def main() -> None:
    temp = Path(r"C:/Users/Janardhanan/AppData/Local/Temp")
    # locate the browser captures from this session by globbing known temp dirs
    def find(name: str) -> Path | None:
        hits = sorted(ROOT.glob(f"docs/**/{name}"), key=lambda p: p.stat().st_mtime)
        return hits[-1] if hits else None

    captures = {
        "maintenance": Path(r"C:\Users\JANARD~1\AppData\Local\Temp\opencode-browser-OR1TOb\0\screenshot.jpeg"),
        "banner": Path(r"C:\Users\JANARD~1\AppData\Local\Temp\opencode-browser-X0UJLH\0\screenshot.jpeg"),
        "authorized": Path(r"C:\Users\JANARD~1\AppData\Local\Temp\opencode-browser-RZkIg9\0\screenshot.jpeg"),
    }

    frames = [
        card([
            ("DRONE OPS AGENT", 56, WHITE, True),
            ("Multi-agent RAG for UAS fleet", 30, GRAY, False),
            ("maintenance & mission readiness", 30, GRAY, False),
            ("LangGraph · FastAPI · Streamlit · Pinecone", 19, ACCENT, True),
        ], footer="Human-in-the-loop takeoff authorization — never without approval"),
        real_frame(captures["maintenance"], "1 · Maintenance agent: log → GROUND verdict + ticket"),
        real_frame(captures["banner"], "2 · Mission agent: estimate GO → HITL interrupt → red banner"),
        real_frame(captures["authorized"], "3 · Human approves → TAKEOFF AUTHORIZED is emitted"),
        card([
            ("PRODUCTION-GRADE BASICS", 40, WHITE, True),
            ("Citations or refusal · retrieval confidence gate", 22, GRAY, False),
            ("25 pytest tests (graph + tools) · eval: hit@1 = 0.90", 22, GRAY, False),
            ("docker compose up — api + streamlit + postgres", 22, GRAY, False),
        ], footer="Not legal advice. Always verify with your aviation authority."),
    ]
    frames = [f for f in frames if f is not None]
    if len(frames) < 2:
        print("warning: no real captures found; embedding cards only")

    max_h = max(f.height for f in frames)
    normalized = []
    for f in frames:
        if f.height != max_h:
            padded = Image.new("RGB", (W, max_h), BG)
            padded.paste(f, (0, (max_h - f.height) // 2))
            f = padded
        normalized.append(f)

    out = DOCS / "demo.gif"
    normalized[0].save(
        out, save_all=True, append_images=normalized[1:],
        duration=[3500, 4200, 4200, 4200, 3500][: len(normalized)], loop=0, optimize=True,
    )
    print("wrote", out, out.stat().st_size // 1024, "KB", f"({len(normalized)} frames)")


if __name__ == "__main__":
    main()
