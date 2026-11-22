import React, { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, X, FileDown, FileText, Ticket as TicketIcon, ShieldCheck, Activity, ChevronDown, Clock } from 'lucide-react'
import { friendly, formatEvidence, severityClass } from '../format'
import { EmptyRow, SectionHead, SeverityPill, StatusDot } from './ui'

const rise = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

export function TicketsView({ tickets, onReport, onRefresh }) {
  if (!tickets?.length) return <><SectionHead eyebrow="MAINTENANCE" title="Tickets" hint="Flight-log anomalies become trackable maintenance tickets." /><EmptyRow icon={TicketIcon} title="No tickets yet" hint="Analyze a flight log from the Chat view to create one." /></>
  const open = tickets.filter(t => String(t.status).toUpperCase() === 'OPEN').length
  const high = tickets.filter(t => ['HIGH', 'CRITICAL'].includes(String(t.severity).toUpperCase())).length
  return (
    <>
      <SectionHead eyebrow="MAINTENANCE" title="Tickets" hint="Findings, evidence and sign-off status across the fleet."
        right={<div className="stat-row"><div className="stat"><b>{open}</b><span>Open</span></div><div className="stat"><b>{high}</b><span>High severity</span></div><div className="stat"><b>{tickets.length}</b><span>Total</span></div></div>} />
      <div className="view-list">
        {tickets.map((t, i) => <TicketCard key={t.id} t={t} i={i} onReport={onReport} />)}
      </div>
    </>
  )
}

function TicketCard({ t, i, onReport }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.div className="list-card" initial="hidden" animate="show" variants={rise} transition={{ delay: Math.min(i * 0.04, 0.3) }}>
      <button className="list-card-head" onClick={() => setOpen(!open)}>
        <span className={`card-accent accent-${severityClass(t.severity)}`} />
        <span className="list-card-main"><b className="mono">{t.id}</b><span>{t.title}</span></span>
        <SeverityPill value={t.severity} />
        <span className="status-chip"><StatusDot tone={String(t.status).toUpperCase() === 'OPEN' ? 'amber' : 'green'} /> {friendly(t.status)}</span>
        <ChevronDown size={16} className={open ? 'rot' : ''} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div className="list-card-body" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
            {(t.findings || []).map((f, j) => (
              <div className="finding compact" key={j}>
                <div className="finding-top"><span className={`sev-dot sev-${severityClass(f.severity)}`} /><b>{friendly(f.type, 'Finding')}</b><SeverityPill value={f.severity} /></div>
                <p>{f.description}</p>
                {f.evidence && <code className="evidence">{formatEvidence(f.evidence)}</code>}
              </div>
            ))}
            <div className="card-foot">
              <span className="mono muted">Created {t.created_at}</span>
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
      <SectionHead eyebrow="SAFETY CONTROL" title="Pending approvals" hint="Authorization-shaped actions pause here. Nothing launches without a recorded human decision." />
      {!pending?.length ? (
        <EmptyRow icon={ShieldCheck} title="No approvals pending" hint="Authorization requests will appear here for your decision." />
      ) : (
        <div className="view-list">
          {pending.map((p, i) => (
            <motion.div key={p.id} className="list-card approval-card" initial="hidden" animate="show" variants={rise} transition={{ delay: i * 0.05 }}>
              <div className="approval-head"><ShieldCheck size={18} /><div><b>{friendly(p.action, 'Authorization')}</b><span className="mono muted"> {p.id} · thread {p.thread_id}</span></div></div>
              <p className="approval-summary">{p.summary || 'No summary provided.'}</p>
              <div className="approval-actions">
                <button className="btn btn-danger" disabled={busy} onClick={() => onDecide(p.id, false)}><X size={15} /> Reject</button>
                <button className="btn btn-primary" disabled={busy} onClick={() => onDecide(p.id, true)}><Check size={15} /> Approve</button>
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
      <SectionHead eyebrow="TELEMETRY" title="Flight logs" hint="Telemetry CSVs eligible for deterministic anomaly analysis." />
      {!logs?.length ? <EmptyRow icon={FileText} title="No flight logs found" hint="Drop CSV logs into data/sample_logs/." /> : (
        <div className="view-list">
          {logs.map((f, i) => (
            <motion.div key={f} className="list-card row-card" initial="hidden" animate="show" variants={rise} transition={{ delay: i * 0.04 }}>
              <span className="row-icon"><FileText size={17} /></span>
              <span className="list-card-main"><b className="mono">{f}</b><span>Telemetry CSV · eligible for anomaly analysis</span></span>
              <button className="btn btn-ghost" onClick={() => onAnalyze(`Analyze flight log ${f} and open a maintenance ticket if needed`)}>Analyze →</button>
            </motion.div>
          ))}
        </div>
      )}
    </>
  )
}

const STATUS_TONE = { completed: 'green', awaiting_approval: 'amber', approval_required: 'amber', paused: 'amber', error: 'red' }

export function RunsView({ runs }) {
  return (
    <>
      <SectionHead eyebrow="AUDIT" title="Agent runs" hint="Every /chat invocation, with classification and outcome." />
      {!runs?.length ? <EmptyRow icon={Activity} title="No runs recorded yet" hint="Ask the agent something to see the audit trail." /> : (
        <div className="view-list">
          {runs.map((r, i) => (
            <motion.div key={r.id || i} className="list-card row-card" initial="hidden" animate="show" variants={rise} transition={{ delay: Math.min(i * 0.04, 0.3) }}>
              <span className="row-icon"><Activity size={17} /></span>
              <span className="list-card-main"><b>{r.query}</b><span className="mono muted"><Clock size={11} /> {r.started_at} · run {String(r.id).slice(0, 12)}</span></span>
              <span className="status-chip"><StatusDot tone={STATUS_TONE[String(r.status).toLowerCase()] || 'muted'} /> {friendly(r.status)}</span>
              <span className="pill pill-info">{friendly(r.classification)}</span>
            </motion.div>
          ))}
        </div>
      )}
    </>
  )
}
