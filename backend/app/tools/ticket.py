"""Ticket writer — persists maintenance tickets to SQLite/Postgres via SQLAlchemy."""
import json
from datetime import datetime, timezone

from ..db import Ticket, get_session
from ..tools.flight_logs import LogAnalysis

SEVERITY_BY_VERDICT = {"GROUND": "HIGH", "MONITOR": "MEDIUM", "PASS": "LOW"}


def create_ticket(
    title: str,
    severity: str,
    findings: list[dict],
    recommended_action: str,
    log_file: str | None = None,
    source: str = "flight_log_analysis",
) -> dict:
    severity = severity.upper()
    if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        severity = "MEDIUM"
    with get_session() as session:
        ticket = Ticket(
            title=title[:300],
            severity=severity,
            status="OPEN",
            source=source,
            findings_json=json.dumps(findings, default=str),
            log_file=log_file,
            recommended_action=recommended_action,
        )
        session.add(ticket)
        session.commit()
        return get_ticket(ticket.id)


def create_ticket_from_analysis(analysis: LogAnalysis, log_file: str | None = None) -> dict:
    anomalies = [a.to_dict() for a in analysis.anomalies]
    severity = SEVERITY_BY_VERDICT.get(analysis.verdict, "MEDIUM")
    if any(a["severity"] == "CRITICAL" for a in anomalies):
        severity = "CRITICAL"
    title = f"Flight log anomaly review — verdict {analysis.verdict} (score {analysis.anomaly_score}/100)"
    action = (
        "Aircraft GROUNDED pending inspection of flagged systems before next flight."
        if analysis.verdict == "GROUND"
        else "Inspect flagged systems within 5 flights; monitor trend."
    )
    return create_ticket(title, severity, anomalies, action, log_file=log_file)


def get_ticket(ticket_id: str) -> dict | None:
    with get_session() as session:
        t = session.get(Ticket, ticket_id)
        if not t:
            return None
        return _to_dict(t)


def list_tickets(limit: int = 50, status: str | None = None) -> list[dict]:
    with get_session() as session:
        q = session.query(Ticket).order_by(Ticket.created_at.desc())
        if status:
            q = q.filter(Ticket.status == status.upper())
        return [_to_dict(t) for t in q.limit(limit).all()]


def _to_dict(t: Ticket) -> dict:
    created = t.created_at
    if isinstance(created, datetime) and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return {
        "id": t.id,
        "created_at": created.isoformat() if created else None,
        "title": t.title,
        "severity": t.severity,
        "status": t.status,
        "source": t.source,
        "findings": json.loads(t.findings_json or "[]"),
        "log_file": t.log_file,
        "recommended_action": t.recommended_action,
    }
