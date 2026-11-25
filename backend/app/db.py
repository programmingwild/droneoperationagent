"""SQLAlchemy models: maintenance tickets, HITL approvals, run audit log.

Defaults to SQLite at data/droneops.db; set DATABASE_URL=postgresql+psycopg2://... for Postgres.
"""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True, default=lambda: f"MT-{uuid.uuid4().hex[:8].upper()}")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    title = Column(String(300), nullable=False)
    severity = Column(String(20), nullable=False)  # CRITICAL | HIGH | MEDIUM | LOW
    status = Column(String(20), nullable=False, default="OPEN")
    source = Column(String(50), nullable=False, default="flight_log_analysis")
    findings_json = Column(Text, nullable=False, default="[]")
    log_file = Column(String(500), nullable=True)
    recommended_action = Column(Text, nullable=True)

    def findings(self) -> list[dict]:
        return json.loads(self.findings_json or "[]")


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(String, primary_key=True, default=lambda: f"AP-{uuid.uuid4().hex[:8].upper()}")
    thread_id = Column(String(120), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    action = Column(String(80), nullable=False)  # e.g. TAKEOFF_AUTHORIZATION / RPA_ARM
    summary = Column(Text, nullable=False)
    decision = Column(String(20), nullable=False, default="PENDING")  # PENDING | APPROVED | REJECTED
    decided_by = Column(String(120), nullable=True)
    run_id = Column(String(120), nullable=True)


class RunAudit(Base):
    __tablename__ = "run_audit"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    started_at = Column(DateTime(timezone=True), default=_utcnow)
    query = Column(Text, nullable=False)
    classification = Column(String(40), nullable=True)
    answer = Column(Text, nullable=True)
    citations_json = Column(Text, nullable=False, default="[]")
    requires_approval = Column(String(1), nullable=False, default="0")
    status = Column(String(30), nullable=False, default="completed")


_engine = None
_Session = None


def normalize_database_url(url: str) -> str:
    """Render/Heroku provide `postgres://`; SQLAlchemy needs a driver scheme."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    return url


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = normalize_database_url(get_settings().database_url)
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        Base.metadata.create_all(_engine)
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session():
    get_engine()
    return _Session()


def reset_engine() -> None:
    """Used by tests to pick up a fresh DATABASE_URL."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine, _Session = None, None
