"""Shared human-readable formatting for internal enums and tool evidence.

One source of truth for the Streamlit UI, agent answers and PDF reports, so a
raw `TAKEOFF_AUTHORIZATION` or `{"motor": 3, ...}` never leaks to a user.
"""
from __future__ import annotations

FRIENDLY = {
    "TAKEOFF_AUTHORIZATION": "Takeoff authorization",
    "RPA_ARM": "RPA arming",
    "TAKEOFF": "Takeoff",
    "ARM": "Arming",
    "INSPECT": "Inspection required",
    "HOLD": "Hold — do not launch",
    "GROUND": "Grounded",
    "GROUNDED": "Grounded",
    "MONITOR": "Restricted operations",
    "PASS": "No anomalies",
    "NONE": "None",
    "TRIAGE": "Triage",
    "MISSION_PLANNING": "Mission planning",
    "MAINTENANCE": "Maintenance",
    "REGULATION": "Regulation compliance",
    "ANOMALY": "Anomaly detection",
    "SAFETY_SUPERVISOR": "Safety supervisor",
    "HUMAN_APPROVAL": "Human approval",
    "FINALIZE": "Finalize",
    "FLIGHT_LOG_ANALYSIS": "Flight log analysis",
    "COMPLETED": "Completed",
    "AWAITING_APPROVAL": "Awaiting approval",
    "APPROVAL_REQUIRED": "Approval required",
    "PAUSED": "Paused",
    "ERROR": "Error",
    "PENDING": "Pending",
    "APPROVED": "Approved",
    "REJECTED": "Rejected",
    "OPEN": "Open",
    "CLOSED": "Closed",
    "MOTOR_CURRENT_IMBALANCE": "Motor current imbalance",
    "VIBRATION_EXCESSIVE": "Excessive vibration",
    "BATTERY_VOLTAGE_SAG": "Battery voltage sag",
    "MOTOR_TEMP": "Motor overheat",
    "MOTOR_OVERHEAT": "Motor overheat",
    "VOLTAGE_LOW": "Low pack voltage",
}

ACRONYMS = {"RPA", "UAS", "VTOL", "FAA", "EASA", "DGCA", "NOTAM", "METAR", "TAF",
            "HITL", "PDF", "ID", "ESC", "IMU", "RMS", "IR"}

EVIDENCE_LABELS = {
    "motor": "Motor", "imbalance_pct": "Peak imbalance", "sustained_s": "Sustained",
    "max_ms2": "Peak vibration", "rms_ms2": "RMS vibration", "seconds_over": "Above limit",
    "baseline_v": "Fresh baseline", "min_v": "Minimum", "sag_v": "Sag",
    "max_temp_c": "Peak temperature", "avg_temp_c": "Average temperature",
    "max_c": "Peak temperature", "current_a": "Current", "voltage_v": "Voltage",
}

EVIDENCE_UNITS = {
    "imbalance_pct": "%", "sustained_s": " s", "max_ms2": " m/s²", "rms_ms2": " m/s²",
    "seconds_over": " s", "baseline_v": " V", "min_v": " V", "sag_v": " V",
    "max_temp_c": " °C", "avg_temp_c": " °C", "max_c": " °C",
    "current_a": " A", "voltage_v": " V",
}

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def friendly(value, default: str = "—") -> str:
    """`TAKEOFF_AUTHORIZATION` -> `Takeoff authorization`."""
    s = str(value or "").strip()
    if not s:
        return default
    if s in FRIENDLY:
        return FRIENDLY[s]
    if s.upper() in FRIENDLY:
        return FRIENDLY[s.upper()]
    words = s.replace("_", " ").replace("-", " ").split()
    return " ".join(w.upper() if w.upper() in ACRONYMS else w.capitalize() for w in words)


def format_pair(key: str, value) -> str:
    """`('sag_v', 6.62)` -> `Sag: 6.6 V`; arrays become a peak or range."""
    label = EVIDENCE_LABELS.get(key, friendly(key))
    unit = EVIDENCE_UNITS.get(key, "")
    if isinstance(value, (list, tuple)):
        numbers = [v for v in value if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not numbers:
            body = ", ".join(str(v) for v in value[:3])
        elif len(numbers) == 1:
            body = f"{numbers[0]:.1f}{unit}"
        elif key.endswith("_pct"):
            peak = max(numbers, key=abs)
            body = f"{'+' if peak > 0 else ''}{peak:.1f}{unit}"
        else:
            body = f"{min(numbers):.1f}–{max(numbers):.1f}{unit}"
    elif isinstance(value, float):
        body = f"{value:.1f}{unit}"
    elif isinstance(value, int):
        body = f"{value}{unit}"
    else:
        body = str(value)
    return f"{label}: {body}"


def format_evidence(ev: dict | None, limit: int = 6) -> str:
    """Format a tool evidence dict as a readable phrase, never raw JSON."""
    if not isinstance(ev, dict) or not ev:
        return ""
    return " · ".join(format_pair(k, v) for k, v in list(ev.items())[:limit])


def format_timestamp(value, with_year: bool = True) -> str:
    """`2026-11-22T10:20:00+00:00` -> `22 Nov 2026 · 10:20 UTC`."""
    from datetime import datetime, timezone

    if value is None or value == "":
        return "—"
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    day = f"{dt.day} {MONTHS[dt.month - 1]}"
    if with_year:
        day += f" {dt.year}"
    return f"{day} · {dt.hour:02d}:{dt.minute:02d} UTC"


def ticket_headline(title) -> tuple[str, str, int | None]:
    """Split `Flight log review — verdict Grounded (score 85/100)` for display."""
    import re

    raw = str(title or "").strip()
    match = re.match(
        r"^(.*?)\s*(?:—|–|-)\s*verdict\s+(.+?)\s*\(\s*score\s+(\d+)\s*/\s*100\s*\)\s*$",
        raw, re.I,
    )
    if not match:
        return (raw or "Maintenance ticket"), "", None
    return (match.group(1).strip() or "Flight log anomaly review",
            match.group(2).strip(), int(match.group(3)))
