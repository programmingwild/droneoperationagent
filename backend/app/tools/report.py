"""PDF report exporter for maintenance tickets (reportlab)."""
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from ..config import get_settings
from .ticket import get_ticket


def export_ticket_pdf(ticket_id: str, out_path: str | Path | None = None) -> Path:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"ticket not found: {ticket_id}")

    reports_dir = get_settings().data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = Path(out_path) if out_path else reports_dir / f"{ticket_id}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    story = [
        Paragraph("Drone Ops Agent — Maintenance Ticket Report", styles["Title"]),
        Spacer(1, 4 * mm),
        Paragraph(f"Ticket <b>{ticket['id']}</b> — {ticket['title']}", styles["Heading2"]),
        Spacer(1, 2 * mm),
    ]

    meta = Table(
        [["Severity", ticket["severity"]],
         ["Status", ticket["status"]],
         ["Source", ticket["source"]],
         ["Created", ticket["created_at"] or "—"],
         ["Log file", ticket["log_file"] or "—"]],
        colWidths=[35 * mm, 125 * mm],
    )
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
    ]))
    story += [meta, Spacer(1, 4 * mm),
              Paragraph("Findings", styles["Heading3"])]

    findings = ticket["findings"]
    if not findings:
        story.append(Paragraph("No findings recorded.", styles["Normal"]))
    else:
        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "?")
            typ = f.get("type", "FINDING")
            desc = f.get("description", "")
            story.append(Paragraph(f"<b>{i}. [{sev}] {typ}</b><br/>{desc}", styles["Normal"]))
            ev = f.get("evidence")
            if ev:
                story.append(Paragraph(f"<font size=8>Evidence: {json.dumps(ev, default=str)}</font>", styles["Normal"]))
            story.append(Spacer(1, 2 * mm))

    story += [Spacer(1, 2 * mm),
              Paragraph("Recommended action", styles["Heading3"]),
              Paragraph(ticket["recommended_action"] or "—", styles["Normal"])]
    doc.build(story)
    return out
