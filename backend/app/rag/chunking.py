"""Recursive character text splitter with overlap + section/page awareness.

Chunk records: {id, text, source, doc_type, regulation, section, page, chunk_index}
"""
import hashlib
import re
from dataclasses import dataclass, field

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    text: str
    source: str
    doc_type: str
    regulation: str | None
    section: str
    page: int | None
    chunk_index: int
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        key = f"{self.source}|{self.page}|{self.chunk_index}|{self.text[:80]}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _split_recursive(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    sep = separators[0]
    rest = separators[1:]
    if sep == "":
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    parts = text.split(sep)
    pieces: list[str] = []
    buf = ""
    for part in parts:
        candidate = part if not buf else buf + sep + part
        if len(candidate) <= chunk_size:
            buf = candidate
        else:
            if buf:
                pieces.append(buf)
            if len(part) > chunk_size:
                pieces.extend(_split_recursive(part, rest, chunk_size))
                buf = ""
            else:
                buf = part
    if buf:
        pieces.append(buf)
    return pieces


def split_text(text: str, chunk_size: int = 900, chunk_overlap: int = 150) -> list[str]:
    pieces = _split_recursive(text, DEFAULT_SEPARATORS, chunk_size)
    if not pieces:
        return []
    merged: list[str] = []
    buf = ""
    for piece in pieces:
        if not buf:
            buf = piece
            continue
        if len(buf) + len(piece) + 1 <= chunk_size:
            buf += "\n" + piece
        else:
            merged.append(buf)
            tail = buf[-chunk_overlap:] if chunk_overlap > 0 else ""
            candidate = (tail + "\n" + piece) if (tail and len(tail) + len(piece) + 1 <= chunk_size) else piece
            buf = candidate
    if buf:
        merged.append(buf)
    return merged


def chunks_from_markdown(
    text: str,
    *,
    source: str,
    doc_type: str,
    regulation: str | None,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    # Strip simple front-matter if present
    fm_end = text.find("\n---", 4)
    if text.startswith("---") and fm_end != -1:
        text = text[fm_end + 4:].lstrip()

    # Split into sections by markdown headings; chunks never cross section boundaries.
    heading_matches = list(HEADING_RE.finditer(text))
    sections: list[tuple[str, str]] = []  # (heading, body)
    if heading_matches:
        if heading_matches[0].start() > 0:
            preamble = text[:heading_matches[0].start()].strip()
            if preamble:
                sections.append(("front matter", preamble))
        for i, m in enumerate(heading_matches):
            body_start = m.end()
            body_end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(text)
            body = (m.group(0) + "\n" + text[body_start:body_end]).strip()
            sections.append((m.group(2).strip(), body))
    else:
        sections.append(("front matter", text))

    chunks: list[Chunk] = []
    idx = 0
    for heading, body in sections:
        for piece in split_text(body, chunk_size, chunk_overlap):
            if not piece.strip():
                continue
            chunks.append(Chunk(
                text=piece.strip(),
                source=source,
                doc_type=doc_type,
                regulation=regulation,
                section=heading,
                page=None,
                chunk_index=idx,
            ))
            idx += 1
    return chunks


def chunks_from_pdf_pages(
    pages: list[tuple[int, str]],
    *,
    source: str,
    doc_type: str,
    regulation: str | None,
    chunk_size: int = 900,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for page_no, page_text in pages:
        for piece in split_text(page_text, chunk_size, chunk_overlap):
            if not piece.strip():
                continue
            chunks.append(Chunk(
                text=piece.strip(),
                source=source,
                doc_type=doc_type,
                regulation=regulation,
                section=f"page {page_no}",
                page=page_no,
                chunk_index=idx,
            ))
            idx += 1
    return chunks
