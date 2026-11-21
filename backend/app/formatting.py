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
    "motor": "Motor", "imbalance_pct": "Imbalance", "sustained_s": "Sustained",
    "max_ms2": "Peak", "rms_ms2": "RMS", "seconds_over": "Above limit",
    "baseline_v": "Fresh baseline", "min_v": "Minimum", "sag_v": "Sag",
    "max_temp_c": "Peak temperature", "avg_temp_c": "Average temperature",
    "current_a": "Current", "voltage_v": "Voltage",
}

EVIDENCE_UNITS = {
    "imbalance_pct": "%", "sustained_s": " s", "max_ms2": " m/s²", "rms_ms2": " m/s²",
    "seconds_over": " s", "baseline_v": " V", "min_v": " V", "sag_v": " V",
    "max_temp_c": " °C", "avg_temp_c": " °C", "current_a": " A", "voltage_v": " V",
}


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
    """`('sag_v', 6.62)` -> `Sag: 6.6 V`."""
    label = EVIDENCE_LABELS.get(key, friendly(key))
    unit = EVIDENCE_UNITS.get(key, "")
    if isinstance(value, (list, tuple)):
        body = ", ".join(f"{v:.1f}{unit}" if isinstance(v, (int, float)) else str(v)
                         for v in value)
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
