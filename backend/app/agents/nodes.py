"""LangGraph node implementations: triage -> specialists -> safety -> HITL -> finalize."""
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from ..config import get_settings
from ..db import Approval, RunAudit, get_session
from ..rag.retrieve import format_context, retrieve
from ..tools.battery import BatteryInput, estimate_battery_range
from ..tools.flight_logs import parse_flight_log
from ..tools.notam import check_airspace
from ..tools.ticket import create_ticket_from_analysis
from .llm import grounded_answer, triage_with_llm
from .prompts import MISSION_SYSTEM, REGULATION_SYSTEM
from .state import AgentState

logger = logging.getLogger(__name__)

AUTHZ_KEYWORDS = ("TAKEOFF AUTHORIZED", "RPA ARMED", "CLEARED FOR TAKEOFF", "ARM AUTHORIZED")


# ---------------------------------------------------------------- helpers
def _trace(state: AgentState, msg: str) -> list[str]:
    return [*state.get("trace", []), f"{datetime.now(timezone.utc):%H:%M:%S} {msg}"]


def _history_block(state: AgentState, max_turns: int = 8, max_chars: int = 300) -> str:
    """Render prior turns as a compact transcript the model can reference."""
    hist = state.get("history") or []
    lines = []
    for turn in hist[-max_turns:]:
        role = str(turn.get("role", "user")).strip().lower()
        content = " ".join(str(turn.get("content", "")).split())
        if content:
            lines.append(f"{role}: {content[:max_chars]}")
    return "\n".join(lines)


def _err(state: AgentState, msg: str) -> list[str]:
    logger.error("agent_node_error", extra={"error": msg, "run_id": state.get("run_id")})
    return [*state.get("errors", []), msg]


def _safe_tool_failure(state: AgentState, tool: str, exc: Exception) -> AgentState:
    return {
        "answer": (
            f"Tool unavailable ({tool}): {exc}. No data could be verified — applying the safe "
            "default: do NOT launch or arm. Resolve the tool failure and re-run. If conditions "
            "are otherwise known safe, a human may still authorize launch through the approval flow."
        ),
        "recommended_action": "HOLD",
        "requires_approval": False,
        "retrieval_confident": False,
        "errors": _err(state, f"{tool}: {exc}"),
        "trace": _trace(state, f"tool failure in {tool} — safe default HOLD applied"),
    }


def _infer_regulation(query: str) -> str | None:
    q = query.lower()
    if any(k in q for k in ("dgca", "india", "digital sky", "npnt")):
        return "dgca_india"
    if any(k in q for k in ("easa", "europe", "open category", "a1/a2", "ce mark", "c0", "c1", "c2")):
        return "easa_open"
    if any(k in q for k in ("faa", "part 107", "107", "laanc", "usa", "united states", "f.a.a")):
        return "faa_part_107"
    return None


def _extract_battery_overrides(query: str) -> dict:
    q = query.lower()
    out: dict = {}
    m = re.search(r"(\d[\d,]*)\s*mah", q)
    if m:
        out["capacity_mah"] = int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg", q)
    if m:
        pass  # weight does not feed the current model beyond docs; kept for future thrust model
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:m/s|mps)\s*(?:headwind|wind)", q) or re.search(r"headwind[^\d]*(\d+(?:\.\d+)?)", q)
    if m:
        out["headwind_kmh"] = float(m.group(1)) * 3.6
    m = re.search(r"(\d+(?:\.\d+)?)\s*km/h", q)
    if m and "headwind" not in q[:m.start()][-12:]:
        out["cruise_speed_kmh"] = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*reserve", q)
    if m:
        out["reserve_fraction"] = min(0.9, max(0.0, float(m.group(1)) / 100.0))
    return out


def _format_citations(retr) -> list[dict]:
    return [
        {"source": c.source, "section": c.section, "page": c.page, "score": c.score}
        for c in retr.citations
    ]


# ---------------------------------------------------------------- triage
_KEYWORDS = {
    "mission_planning": ("range", "endurance", "mission", "payload", "battery", "how far", "plan a flight", "go no-go", "go/no-go"),
    "maintenance": ("ticket", "maintenance", "log", "motor", "bearing", "propeller", "esc", "vibration", "current draw", "checklist", "wear"),
    "regulation": ("legal", "legality", "regulation", "faa", "part 107", "easa", "dgca", "airspace", "notam", "laanc", "approval to fly", "authori"),
    "anomaly": ("anomal", "fault", "spike", "unexpected", "abnormal", "weird", "incident"),
}


def triage_node(state: AgentState) -> AgentState:
    query = state["query"]
    trace = _trace(state, "triage: classifying query")
    llm_result = triage_with_llm(query, _history_block(state))
    if llm_result:
        cls, conf = llm_result["classification"], float(llm_result["confidence"])
        trace = _trace({"trace": trace}, f"triage: llm route → {cls} ({conf:.2f})")
        return {"classification": cls, "classification_conf": conf, "trace": trace}
    q = query.lower()
    scores = {cls: sum(1 for k in kws if k in q) for cls, kws in _KEYWORDS.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best, conf = "regulation", 0.3  # safest default: legal/grounded path, will refuse if unsure
    else:
        conf = 0.6
    trace = _trace({"trace": trace}, f"triage: keyword route → {best} ({conf:.2f}) [offline]")
    return {"classification": best, "classification_conf": conf, "trace": trace}


# ---------------------------------------------------------------- specialists
def mission_planning_node(state: AgentState) -> AgentState:
    query = state["query"]
    trace = _trace(state, "mission_planning: estimating battery range")
    try:
        overrides = _extract_battery_overrides(query)
        est = estimate_battery_range(BatteryInput(**overrides))
    except Exception as exc:
        return _safe_tool_failure(state, "battery_estimator", exc)

    try:
        retr = retrieve(query, doc_type=None, regulation=None, top_k=4)
    except Exception as exc:
        return _safe_tool_failure(state, "rag_retrieve", exc)

    retr_note = "" if retr.confident else "\n⚠ Retrieval confidence below threshold — guidance unverified.\n"
    estimate_block = (
        f"**Battery-range estimate (physics model)**\n"
        f"- Nominal {est.nominal_voltage_v} V · full {est.full_voltage_v} V · loaded cutoff {est.cutoff_voltage_v} V\n"
        f"- Hover C-rate {est.hover_c_rate}C · full-throttle {est.full_throttle_c_rate}C\n"
        f"- Hover voltage sag {est.hover_voltage_sag_v} V (full-throttle {est.full_throttle_voltage_sag_v} V)\n"
        f"- Usable capacity {est.usable_capacity_ah} Ah (after {est.reserve_fraction:.0%} reserve) → "
        f"endurance ≈ {est.endurance_min} min, range ≈ {est.range_km} km at {est.groundspeed_kmh} km/h groundspeed\n"
        f"- Verdict: **{est.verdict}**"
    )
    if est.warnings:
        estimate_block += "\n- Warnings:\n" + "\n".join(f"  - {w}" for w in est.warnings)

    context = format_context(retr)
    body = grounded_answer(query, context, _format_citations(retr), _history_block(state)) if retr.chunks else \
        "No manual excerpts retrieved — rely on the physics estimate only."
    answer = f"{retr_note}{estimate_block}\n\n{body}"

    return {
        "answer": answer,
        "recommended_action": "TAKEOFF" if est.verdict == "GO" else "HOLD",
        "retrieved": retr.chunks,
        "citations": _format_citations(retr),
        "retrieval_confident": retr.confident,
        "tool_results": {**state.get("tool_results", {}), "battery_estimate": est.model_dump()},
        "trace": _trace({"trace": trace}, f"mission_planning: verdict {est.verdict}, {len(retr.citations)} citations"),
    }


def regulation_node(state: AgentState) -> AgentState:
    query = state["query"]
    trace = _trace(state, "regulation: retrieving rule passages")
    reg = _infer_regulation(query)
    try:
        retr = retrieve(query, regulation=reg, top_k=4)
    except Exception as exc:
        return _safe_tool_failure(state, "rag_retrieve", exc)

    if not retr.confident or not retr.citations:
        answer = (
            "I cannot give a reliable yes/no on legality — retrieval confidence is below the safety "
            "threshold or no citable passages were found. Safe guidance: treat the flight as NOT "
            "authorized until you verify airspace (LAANC/Digital Sky/national portal), altitude, "
            "VLOS and operator-certificate requirements with your aviation authority or a qualified "
            "remote pilot. I will not guess on a legal question."
        )
        return {
            "answer": answer,
            "recommended_action": "HOLD",
            "citations": [],
            "retrieved": retr.chunks,
            "retrieval_confident": False,
            "trace": _trace({"trace": trace}, "regulation: LOW CONFIDENCE — refused, safe guidance issued"),
        }

    context = format_context(retr)
    body = grounded_answer(query, context, _format_citations(retr), _history_block(state))
    cite_lines = "\n".join(
        f"- [{i + 1}] {c.source} — {c.section}{' p.' + str(c.page) if c.page else ''} (score {c.score})"
        for i, c in enumerate(retr.citations)
    )
    answer = f"{body}\n\n**Sources**\n{cite_lines}"

    # Optional live airspace check if coordinates supplied
    tool_results = dict(state.get("tool_results", {}))
    lat, lon = state.get("lat"), state.get("lon")
    if lat is not None and lon is not None:
        try:
            report = check_airspace(lat, lon)
            tool_results["airspace"] = report.model_dump()
            answer += f"\n\n**Airspace check ({report.status})** — {report.advisory}"
            trace = _trace({"trace": trace}, f"regulation: airspace proxy → {report.status}")
        except Exception as exc:
            tool_results["airspace"] = {"status": "error", "error": str(exc)}
            answer += "\n\n⚠ Live airspace check failed; treat conditions as unverified."

    return {
        "answer": answer,
        "recommended_action": "NONE",
        "retrieved": retr.chunks,
        "citations": _format_citations(retr),
        "retrieval_confident": True,
        "tool_results": tool_results,
        "trace": _trace({"trace": trace}, f"regulation: answered with {len(retr.citations)} citations ({reg or 'all corpus'})"),
    }


def _run_log_analysis(state: AgentState, log_path: str) -> AgentState:
    trace = _trace(state, f"maintenance: parsing {Path(log_path).name}")
    try:
        analysis = parse_flight_log(log_path)
        ticket = create_ticket_from_analysis(analysis, log_file=log_path)
    except Exception as exc:
        return _safe_tool_failure(state, "flight_log_analysis", exc)

    anomalies = analysis.anomalies
    verdict = (analysis.verdict or "").upper()
    verdict_line = {
        "GROUND": "🚫 **GROUNDED — do not fly**",
        "MONITOR": "⚠️ **MONITOR — restricted operations only**",
        "PASS": "✅ **PASS — no anomalies detected**",
    }.get(verdict, f"**{verdict}**")

    def _sev_icon(sev: str) -> str:
        return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}.get((sev or "").upper(), "⚪")

    sev_counts = {}
    for a in anomalies:
        sev_counts[(a.severity or "?").upper()] = sev_counts.get((a.severity or "?").upper(), 0) + 1
    findings_head = (
        f"**Findings ({len(anomalies)} — {', '.join(f'{v}x {k}' for k, v in sorted(sev_counts.items()))})**"
        if anomalies else "**Findings**\n- none"
    )
    anomaly_lines = "\n".join(
        f"- {_sev_icon(a.severity)} **{a.type}** — {a.description}" for a in anomalies
    )

    # Deterministic required-actions checklist, keyed off the actual finding types.
    _ACTIONS = {
        "MOTOR_CURRENT_IMBALANCE": "Motor current imbalance → inspect motor bearings/ESC and propeller condition on the flagged axis; run a 10-min hover check.",
        "VIBRATION_EXCESSIVE": "Excessive vibration → check prop balance, motor mounts and IMU dampers; verify with a short tethered hover.",
        "BATTERY_VOLTAGE_SAG": "Voltage sag → measure battery internal resistance, check connector/wiring, downsize payload or mission time.",
        "MOTOR_TEMP": "Motor overtemp → check cooling airflow and motor load; verify bench temps after 5-min hover.",
        "VOLTAGE_LOW": "Low voltage → swap to a fresh/charged pack and log IR before return to service.",
    }
    actions = []
    for a in anomalies:
        for key, action in _ACTIONS.items():
            if key in (a.type or "").upper() and action not in actions:
                actions.append(action)
    if not actions:
        actions.append("Review logged anomalies against the 50-hour / 100-flight checklist before next flight.")
    action_lines = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(actions))

    answer = (
        f"{verdict_line}\n"
        f"Flight-log analysis · **{analysis.rows} rows** over **{analysis.duration_s:.1f} s** · anomaly score **{analysis.anomaly_score}/100**\n\n"
        f"- Motor current imbalance (% of mean): {analysis.motor_current_imbalance_pct}\n"
        f"- Max vibration **{analysis.max_vibration_ms2} m/s²** (RMS {analysis.vibration_rms_ms2})\n"
        f"- Voltage min **{analysis.voltage_min_v} V** · sag **{analysis.voltage_sag_v} V**\n"
        f"- Max motor temp **{analysis.motor_temp_max_c} °C**\n\n"
        f"{findings_head}\n{anomaly_lines or '- none'}\n\n"
        f"**Ticket {ticket['id']}** · severity **{ticket['severity']}** · status {ticket['status']}\n\n"
        f"**Required before next flight**\n{action_lines}\n\n"
        f"{ticket['recommended_action']} Technician sign-off required to clear."
    )
    return {
        "answer": answer,
        "recommended_action": "INSPECT",
        "retrieval_confident": True,
        "tool_results": {**state.get("tool_results", {}),
                         "log_analysis": analysis.to_dict(), "ticket": ticket},
        "trace": _trace({"trace": trace}, f"maintenance: verdict {analysis.verdict}, ticket {ticket['id']}"),
    }


def maintenance_node(state: AgentState) -> AgentState:
    log_path = state.get("log_file")
    if not log_path:
        candidates = sorted(
            Path(get_settings().flight_logs_dir).glob("*.csv"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        log_path = str(candidates[0]) if candidates else None
    if not log_path:
        return {
            "answer": (
                "No flight log found. Provide a CSV flight log path (log_file) or place a CSV in "
                f"{get_settings().flight_logs_dir}. I cannot assess airworthiness without data."
            ),
            "recommended_action": "HOLD",
            "retrieval_confident": False,
            "trace": _trace(state, "maintenance: NO LOG FILE available"),
        }
    return _run_log_analysis(state, log_path)


def anomaly_node(state: AgentState) -> AgentState:
    result = _run_log_analysis(state, state.get("log_file")) if state.get("log_file") else maintenance_node(state)
    result["trace"] = [*(result.get("trace", [])), "anomaly: routed through maintenance pipeline"]
    return result


# ---------------------------------------------------------------- safety + HITL
def safety_supervisor_node(state: AgentState) -> AgentState:
    trace = _trace(state, "safety: evaluating authorization requirement")
    action = (state.get("recommended_action") or "NONE").upper()
    answer_u = (state.get("answer") or "").upper()
    requires = action in ("TAKEOFF", "ARM") or any(k in answer_u for k in AUTHZ_KEYWORDS)

    if requires:
        approval_action = "TAKEOFF_AUTHORIZATION" if action == "TAKEOFF" else "RPA_ARM"
        summary = (state.get("answer") or "")[:600]
        try:
            with get_session() as session:
                approval = Approval(
                    thread_id=state.get("thread_id", "unknown"),
                    action=approval_action,
                    summary=summary,
                    decision="PENDING",
                    run_id=state.get("run_id"),
                )
                session.add(approval)
                session.commit()
                session.refresh(approval)
                approval_id = approval.id
        except Exception as exc:
            # Fail-safe: authorization must never proceed without a durable approval record
            return {
                "answer": (state.get("answer", "") +
                           "\n\n⛔ Authorization BLOCKED: could not persist the approval record — "
                           "failing safe. Do NOT take off."),
                "recommended_action": "HOLD",
                "requires_approval": False,
                "errors": _err(state, f"approval_persist: {exc}"),
                "trace": _trace({"trace": trace}, "safety: approval persist FAILED — authorization blocked"),
            }
        return {
            "requires_approval": True,
            "approval_id": approval_id,
            "approval_action": approval_action,
            "approval_summary": summary,
            "trace": _trace({"trace": trace}, f"safety: HITL approval required ({approval_action}) → {approval_id}"),
        }

    return {
        "requires_approval": False,
        "trace": _trace({"trace": trace}, "safety: no authorization requested — proceeding"),
    }


def human_approval_node(state: AgentState) -> AgentState:
    trace = _trace(state, "hitl: human decision received")
    decision = (state.get("approval_decision") or "REJECTED").upper()
    decided_by = state.get("decided_by") or "unknown-operator"
    approval_id = state.get("approval_id")
    action = state.get("approval_action") or "AUTHORIZATION"

    try:
        with get_session() as session:
            row = session.get(Approval, approval_id) if approval_id else None
            if row:
                row.decision = decision
                row.decided_by = decided_by
                row.resolved_at = datetime.now(timezone.utc)
                session.commit()
    except Exception as exc:
        return _safe_tool_failure(state, "approval_resolve", exc)

    if decision == "APPROVED":
        verdict_word = "TAKEOFF AUTHORIZED" if action == "TAKEOFF_AUTHORIZATION" else "RPA ARMED"
        answer = (
            f"✅ **{verdict_word}** — human-in-the-loop approval {approval_id} granted by "
            f"{decided_by}. Authorization is limited to the reviewed flight proposal; all "
            "documented limits (400 ft AGL, VLOS, 20% reserve, weather/airspace verification) "
            "remain in force. Abort on any in-flight emergency cue (§107.21)."
        )
        recommended = "TAKEOFF" if action == "TAKEOFF_AUTHORIZATION" else "ARM"
    else:
        answer = (
            f"❌ **NOT AUTHORIZED** — human reviewer {decided_by} did not approve "
            f"({approval_id}). Aircraft remains on the ground / disarmed. Re-plan, fix the "
            "flagged deficiencies, and resubmit for approval."
        )
        recommended = "HOLD"

    return {
        "answer": answer,
        "recommended_action": recommended,
        "requires_approval": False,
        "trace": _trace({"trace": trace}, f"hitl: decision {decision} by {decided_by}"),
    }


def finalize_node(state: AgentState) -> AgentState:
    trace = _trace(state, "finalize: assembling response")
    citations = state.get("citations", [])
    final = {
        "run_id": state.get("run_id"),
        "thread_id": state.get("thread_id"),
        "answer": state.get("answer", ""),
        "classification": state.get("classification"),
        "recommended_action": state.get("recommended_action"),
        "requires_approval": bool(state.get("requires_approval")),
        "approval_id": state.get("approval_id"),
        "approval_action": state.get("approval_action"),
        "approval_summary": state.get("approval_summary"),
        "citations": citations,
        "retrieval_confident": state.get("retrieval_confident"),
        "tool_results": state.get("tool_results", {}),
        "errors": state.get("errors", []),
        "trace": trace,
    }
    try:
        with get_session() as session:
            session.add(RunAudit(
                query=state.get("query", ""),
                classification=state.get("classification"),
                answer=final["answer"][:4000],
                citations_json=json.dumps(citations, default=str),
                requires_approval="1" if final["requires_approval"] else "0",
                status="awaiting_approval" if final["requires_approval"] else "completed",
            ))
            session.commit()
    except Exception as exc:
        logger.warning("audit_write_failed", extra={"error": str(exc)})
    return {"final": final, "trace": trace}
