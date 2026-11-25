import React, { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Activity, ArrowUpRight, Check, ChevronDown, Clock, FileDown, FileText,
  ShieldCheck, Ticket as TicketIcon, X,
} from 'lucide-react'
import { friendly, formatEvidence, formatTimestamp, plainPreview, severityClass, ticketHeadline } from '../format'
import { EmptyRow, SectionHead, SeverityPill, StatusDot } from './ui'

const rise = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

export function TicketsView({ tickets, onReport }) {
  if (!tickets?.length) {
    return (
      <>
        <SectionHead index="01" eyebrow="MAINTENANCE" title="Tickets" hint="Flight-log anomalies become trackable maintenance tickets." />
        <EmptyRow icon={TicketIcon} title="No tickets yet" hint="Analyze a flight log from Mission control to open one." />
      </>
    )
  }

  const open = tickets.filter(t => String(t.status).toUpperCase() === 'OPEN').length
  const high = tickets.filter(t => ['HIGH', 'CRITICAL'].includes(String(t.severity).toUpperCase())).length

  return (
    <>
      <SectionHead index="01" eyebrow="MAINTENANCE" title="Tickets"
        hint="Findings, evidence and sign-off status across the fleet."
        right={(
          <div className="stat-row">
            <div className="stat"><b>{open}</b><span>Open</span></div>
            <div className="stat"><b>{high}</b><span>High severity</span></div>
            <div className="stat"><b>{tickets.length}</b><span>Total</span></div>
          </div>
        )} />
      <div className="view-list">
        {tickets.map((t, i) => <TicketCard key={t.id} t={t} i={i} onReport={onReport} />)}
      </div>
    </>
  )
}

function TicketCard({ t, i, onReport }) {
  const [open, setOpen] = useState(false)
  const isOpen = String(t.status).toUpperCase() === 'OPEN'
  const head = ticketHeadline(t.title)
  const tone = /ground/i.test(head.verdict) ? 'ground'
    : /monitor/i.test(head.verdict) ? 'monitor'
      : /pass/i.test(head.verdict) ? 'pass' : 'neutral'
  return (
    <motion.div className="list-card" initial="hidden" animate="show" variants={rise}
      transition={{ delay: Math.min(i * 0.04, 0.3) }}>
      <button className="list-card-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className={`card-accent accent-${severityClass(t.severity)}`} />
        <span className="list-card-main">
          <b className="mono">{t.id}</b>
          <span className="ticket-line">
            <span className="ticket-title">{head.title}</span>
            {head.verdict && (
              <span className={`verdict-chip tone-${tone}`}>
                {head.verdict}
                {head.score != null && <i>{head.score}/100</i>}
              </span>
            )}
          </span>
        </span>
        <SeverityPill value={t.severity} />
        <span className="status-chip">
          <StatusDot tone={isOpen ? 'amber' : 'green'} pulse={isOpen} /> {friendly(t.status)}
        </span>
        <ChevronDown size={16} className={open ? 'rot' : 'card-chev'} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div className="list-card-body" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
            {(t.findings || []).map((f, j) => (
              <div className="finding compact" key={j}>
                <div className="finding-top">
                  <span className={`sev-dot sev-${severityClass(f.severity)}`} />
                  <b>{friendly(f.type, 'Finding')}</b>
                  <SeverityPill value={f.severity} />
                </div>
                <p>{f.description}</p>
                {f.evidence && <code className="evidence">{formatEvidence(f.evidence)}</code>}
              </div>
            ))}
            <div className="card-foot">
              <span className="mono muted">Created {formatTimestamp(t.created_at)}</span>
              <button className="btn btn-ghost" onClick={() => onReport(t.id)}><FileDown size={14} /> Export PDF</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function ApprovalsView({ pending, onDecide, busy }) {
  return (
    <>
      <SectionHead index="02" eyebrow="SAFETY CONTROL" title="Authorizations"
        hint="Authorization-shaped actions pause here. Nothing launches without a recorded human decision."
        right={pending?.length ? <div className="queue-pill"><span className="live-dot" /> {pending.length} awaiting decision</div> : null} />

      {!pending?.length ? (
        <div className="approval-clear">
          <div className="clear-visual" aria-hidden="true">
            <span className="clear-ring clear-ring-outer" />
            <span className="clear-ring clear-ring-inner" />
            <span className="clear-core"><ShieldCheck size={34} strokeWidth={1.4} /></span>
          </div>
          <div className="clear-copy">
            <h2>No authorizations waiting</h2>
            <p>Any authorization-shaped action pauses at the safety supervisor and lands here for a recorded human decision.</p>
          </div>
          <div className="clear-protocols">
            <span><StatusDot tone="green" /> Safety supervisor armed</span>
            <span><StatusDot tone="amber" /> Auto-approval disabled</span>
            <span><StatusDot tone="green" /> Audit trail recording</span>
          </div>
        </div>
      ) : (
        <div className="view-list">
          {pending.map((p, i) => (
            <motion.div key={p.id} className="list-card approval-card" initial="hidden" animate="show" variants={rise}
              transition={{ delay: i * 0.05 }}>
              <div className="approval-head">
                <span className="approval-icon"><ShieldCheck size={18} /></span>
                <div>
                  <b>{friendly(p.action, 'Authorization')}</b>
                  <span className="mono muted"> {p.id} · thread {p.thread_id}</span>
                </div>
                <span className="approval-flag">HUMAN DECISION</span>
              </div>
              <p className="approval-summary">{plainPreview(p.summary, 240) || 'No summary provided.'}</p>
              <div className="approval-actions">
                <button className="btn btn-danger" disabled={busy} onClick={() => onDecide(p.id, false)}>
                  <X size={15} /> Reject
                </button>
                <button className="btn btn-primary" disabled={busy} onClick={() => onDecide(p.id, true)}>
                  <Check size={15} /> Approve authorization
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </>
  )
}

export function LogsView({ logs, onAnalyze }) {
  return (
    <>
      <SectionHead index="03" eyebrow="TELEMETRY" title="Flight logs"
        hint="Telemetry CSVs eligible for deterministic anomaly analysis." />
      {!logs?.length ? (
        <EmptyRow icon={FileText} title="No flight logs found" hint="Drop CSV logs into data/sample_logs/." />
      ) : (
        <div className="view-list">
          {logs.map((f, i) => (
            <motion.div key={f} className="list-card row-card" initial="hidden" animate="show" variants={rise}
              transition={{ delay: i * 0.04 }}>
              <span className="row-icon"><FileText size={17} /></span>
              <span className="list-card-main">
                <b className="mono">{f}</b>
                <span>Telemetry CSV · anomaly-ready</span>
              </span>
              <span className="row-signal" aria-hidden="true">
                {Array.from({ length: 14 }, (_, j) => (
                  <i key={j} style={{ height: `${18 + ((i * 17 + j * 23) % 74)}%` }} />
                ))}
              </span>
              <button className="btn btn-ghost" onClick={() => onAnalyze(`Analyze flight log ${f} and open a maintenance ticket if needed`)}>
                Analyze <ArrowUpRight size={14} />
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </>
  )
}

const STATUS_TONE = {
  completed: 'green', awaiting_approval: 'amber', approval_required: 'amber',
  paused: 'amber', error: 'red',
}

export function RunsView({ runs }) {
  return (
    <>
      <SectionHead index="04" eyebrow="AUDIT" title="Run log"
        hint="Every /chat invocation, with classification and outcome." />
      {!runs?.length ? (
        <EmptyRow icon={Activity} title="No runs recorded yet" hint="Ask the agent something to see the audit trail." />
      ) : (
        <div className="view-list">
          {runs.map((r, i) => (
            <motion.div key={r.id || i} className="list-card row-card run-row" initial="hidden" animate="show"
              variants={rise} transition={{ delay: Math.min(i * 0.035, 0.28) }}>
              <span className="row-icon"><Activity size={16} /></span>
              <span className="list-card-main">
                <b>{r.query}</b>
                <span className="mono muted"><Clock size={11} /> {formatTimestamp(r.started_at, { year: false })} · run {String(r.id).slice(0, 12)}</span>
              </span>
              <span className="pill pill-info">{friendly(r.classification)}</span>
              <span className="status-chip">
                <StatusDot tone={STATUS_TONE[String(r.status).toLowerCase()] || 'muted'} />
                {friendly(r.status)}
              </span>
            </motion.div>
          ))}
        </div>
      )}
    </>
  )
}
