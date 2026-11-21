"""PDF report exporter for maintenance tickets (reportlab).

All user-facing text goes through the shared formatter, so the PDF reads exactly
like the UI — no raw enums or JSON evidence dumps.
"""
import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import get_settings
from ..formatting import FRIENDLY, format_evidence, friendly
from .ticket import get_ticket

NAVY = colors.HexColor("#0b1220")
CYAN = colors.HexColor("#22d3ee")
INK = colors.HexColor("#16243a")
MUTED = colors.HexColor("#5a6b82")
PALE = colors.HexColor("#f4f8fc")
SEVERITY_COLOR = {
    "CRITICAL": colors.HexColor("#b91c1c"),
    "HIGH": colors.HexColor("#dc2626"),
    "MEDIUM": colors.HexColor("#b45309"),
    "LOW": colors.HexColor("#15803d"),
}

HEAD = ParagraphStyle("head", fontName="Helvetica", fontSize=9, leading=13,
                      textColor=colors.white)
SECTION = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=12, leading=15,
                         textColor=NAVY, spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=14, textColor=INK)
FOOT = ParagraphStyle("foot", fontName="Helvetica", fontSize=7.5, leading=11,
                      textColor=MUTED, spaceBefore=12)


def export_ticket_pdf(ticket_id: str, out_path: str | Path | None = None) -> Path:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"ticket not found: {ticket_id}")

    reports_dir = get_settings().data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = Path(out_path) if out_path else reports_dir / f"{ticket_id}.pdf"

    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Maintenance ticket {ticket_id}",
                            author="Drone Ops Agent")
    width = doc.width
    story = []

    # ---- header band -------------------------------------------------------
    header_text = (
        '<font color="#67e8f9" size=7.5>UAV FLEET INTELLIGENCE · MAINTENANCE RECORD</font><br/>'
        '<font color="#ffffff" size=18><b>Maintenance Ticket Report</b></font><br/>'
        f'<font color="#a9c1dd" size=9>Ticket {html.escape(str(ticket["id"]))} &nbsp;·&nbsp; '
        f'{html.escape(str(ticket["title"]))}</font>'
    )
    header = Table([[Paragraph(header_text, HEAD)]], colWidths=[width])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    rule = Table([[""]], colWidths=[width], rowHeights=[1.4])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CYAN)]))
    story += [header, rule, Spacer(1, 5 * mm)]

    # ---- metadata ----------------------------------------------------------
    sev = friendly(ticket["severity"])
    sev_color = SEVERITY_COLOR.get(str(ticket["severity"]).upper(), INK)
    meta_rows = [
        ["Severity", f'<font color="#{sev_color.hexval()[2:]}"><b>{html.escape(sev)}</b></font>'],
        ["Status", friendly(ticket["status"])],
        ["Source", friendly(ticket["source"])],
        ["Created", str(ticket["created_at"] or "—")],
        ["Log file", str(ticket["log_file"] or "—")],
    ]
    meta = Table([[k, Paragraph(str(v), BODY)] for k, v in meta_rows],
                 colWidths=[32 * mm, width - 32 * mm])
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd8e6")),
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (0, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
    ]))
    story += [Paragraph("Findings", SECTION), meta, Spacer(1, 3 * mm)]

    # ---- findings ----------------------------------------------------------
    findings = ticket["findings"]
    if not findings:
        story.append(Paragraph("No findings recorded.", BODY))
    else:
        for i, f in enumerate(findings, 1):
            sev_label = friendly(f.get("severity"), "Unknown")
            bar = SEVERITY_COLOR.get(str(f.get("severity", "")).upper(), MUTED)
            typ = html.escape(friendly(f.get("type"), "Finding"))
            desc = html.escape(str(f.get("description", "")))
            body = (f'<b>{i}. {typ}</b> &nbsp; <font color="#{bar.hexval()[2:]}" size=8>'
                    f'<b>{html.escape(sev_label)}</b></font><br/>{desc}')
            evidence_text = format_evidence(f.get("evidence"))
            if evidence_text:
                body += f'<br/><font color="#5a6b82" size=7.8>{html.escape(evidence_text)}</font>'
            card = Table([[Paragraph(body, BODY)]], colWidths=[width])
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e2ee")),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]))
            story += [card, Spacer(1, 2 * mm)]

    # ---- action ------------------------------------------------------------
    action = str(ticket["recommended_action"] or "—")
    if action.upper() in FRIENDLY:
        action = friendly(action)
    action_card = Table([[Paragraph(html.escape(action), BODY)]], colWidths=[width])
    action_card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eefbfd")),
        ("LINEBEFORE", (0, 0), (0, -1), 3, CYAN),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#bfe9ef")),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    story += [Paragraph("Recommended action", SECTION), action_card]

    story.append(Paragraph(
        "Decision support only — not certified for flight operations. "
        "Verify all findings with a qualified technician before returning the aircraft to service.",
        FOOT))
    doc.build(story)
    return out
