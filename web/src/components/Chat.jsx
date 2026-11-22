import React, { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowUp, BookOpen, Check, ChevronDown, Copy, FileDown, FileText, GitBranch, Menu,
  Scale, Search, ShieldAlert, Wrench, Zap, Radar, Loader2, AlertTriangle, XCircle,
} from 'lucide-react'
import { friendly, formatEvidence, severityClass } from '../format'
import { SeverityPill } from './ui'

const SUGGESTIONS = [
  { icon: Scale, title: 'Legality check', hint: 'Part 107 over-people rule', query: 'Is flying over people legal under Part 107?' },
  { icon: Wrench, title: 'Analyze flight log', hint: 'Find anomalies, open a ticket', query: 'Analyze the last flight log and open a maintenance ticket if needed' },
  { icon: Radar, title: 'Plan a mission', hint: 'VX-6 endurance & risk', query: 'Can I fly the VX-6 on a 20-min inspection mission at 120m and what are the risks?' },
  { icon: Search, title: 'DGCA rules', hint: 'Yellow-zone requirements', query: 'What is required to fly a drone in a yellow zone in India?' },
]

const VERDICT = {
  GROUND: { label: 'GROUNDED — DO NOT FLY', icon: XCircle, tone: 'ground' },
  MONITOR: { label: 'MONITOR — RESTRICTED OPERATIONS', icon: AlertTriangle, tone: 'monitor' },
  PASS: { label: 'PASS — NO ANOMALIES', icon: Check, tone: 'pass' },
}

export function EmptyState({ onSend }) {
  return (
    <motion.div className="hero" initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.08 } } }}>
      <motion.div className="hero-eyebrow" variants={rise}>
        <span className="live-dot" /> UAV FLEET INTELLIGENCE · DECISION SUPPORT
      </motion.div>
      <motion.div className="hero-glyph" variants={rise}>
        <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
          <path d="M6.4 6.4l3.2 3.2m8-3.2-3.2 3.2m-8 8 3.2-3.2m8 3.2-3.2-3.2" /><rect x="9" y="9" width="6" height="6" rx="1.5" />
        </svg>
      </motion.div>
      <motion.h1 className="hero-title" variants={rise}>How can I help<br />with your fleet today?</motion.h1>
      <motion.p className="hero-sub" variants={rise}>
        Grounded answers, cited sources, and human-approved authorizations — in one mission-control workspace.
      </motion.p>
      <motion.div className="suggest-grid" variants={rise}>
        {SUGGESTIONS.map((s, i) => (
          <motion.button key={s.title} className="suggest-card" onClick={() => onSend(s.query)}
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18 + i * 0.07, type: 'spring', stiffness: 260, damping: 24 }}
            whileHover={{ y: -4 }} whileTap={{ scale: 0.98 }}>
            <span className="suggest-icon"><s.icon size={18} strokeWidth={1.7} /></span>
            <span className="suggest-copy"><b>{s.title}</b><small>{s.hint}</small></span>
            <ArrowUp size={14} className="suggest-arrow" />
          </motion.button>
        ))}
      </motion.div>
    </motion.div>
  )
}

const rise = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.2, 0.8, 0.2, 1] } } }

export function FlightPanel({ data, onReport }) {
  if (!data) return null
  const verdict = VERDICT[String(data.verdict || '').toUpperCase()] || { label: data.verdict || 'UNKNOWN', icon: AlertTriangle, tone: 'monitor' }
  const Icon = verdict.icon
  const anomalies = data.anomalies || []
  const high = anomalies.filter(a => ['HIGH', 'CRITICAL'].includes(String(a.severity || '').toUpperCase())).length
  const tiles = [
    ['Anomaly score', `${data.anomaly_score ?? '—'}/100`],
    ['Findings', `${anomalies.length} (${high} high)`],
    ['Vibration max', `${(data.max_vibration_ms2 ?? 0).toFixed(1)} m/s²`],
    ['Voltage sag', `${(data.voltage_sag_v ?? 0).toFixed(1)} V`],
    ['Motor temp max', `${(data.motor_temp_max_c ?? 0).toFixed(0)} °C`],
  ]

  return (
    <motion.div className="panel-stack" initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.06 } } }}>
      <motion.div className={`verdict verdict-${verdict.tone}`} variants={rise}>
        <div className="verdict-icon"><Icon size={22} strokeWidth={1.8} /></div>
        <div>
          <div className="verdict-label">{verdict.label}</div>
          <div className="verdict-sub">{data.rows ?? '?'} rows · {(data.duration_s ?? 0).toFixed(1)}s · anomaly score {data.anomaly_score ?? '—'}/100</div>
        </div>
      </motion.div>
      <motion.div className="tile-grid" variants={rise}>
        {tiles.map(([k, v]) => <div className="tile" key={k}><span className="tile-k">{k}</span><span className="tile-v">{v}</span></div>)}
      </motion.div>
      {anomalies.map((a, i) => (
        <motion.div key={i} className={`finding finding-${severityClass(a.severity)}`} variants={rise}>
          <div className="finding-top">
            <span className={`sev-dot sev-${severityClass(a.severity)}`} />
            <b>{friendly(a.type, 'Finding')}</b>
            <SeverityPill value={a.severity} />
          </div>
          <p>{a.description}</p>
          {a.evidence && <code className="evidence">{formatEvidence(a.evidence)}</code>}
        </motion.div>
      ))}
      {data.ticket && (
        <motion.div className="ticket-strip" variants={rise}>
          <div>
            <div className="ticket-id">Ticket {data.ticket.id} <SeverityPill value={data.ticket.severity} /></div>
            <p>Aircraft grounded pending inspection. Technician sign-off required before next flight.</p>
          </div>
          <button className="btn btn-ghost" onClick={() => onReport(data.ticket.id)}><FileDown size={15} /> Export PDF</button>
        </motion.div>
      )}
    </motion.div>
  )
}

function Message({ m, onReport, onRegenerate, index }) {
  const [showCites, setShowCites] = useState(false)
  const [copied, setCopied] = useState(false)
  if (m.role === 'user') {
    return (
      <motion.div className="msg-user" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="bubble-user">{m.text}</div>
      </motion.div>
    )
  }
  const copy = () => navigator.clipboard?.writeText(m.text || '').then(() => {
    setCopied(true); setTimeout(() => setCopied(false), 1600)
  }).catch(() => {})
  return (
    <motion.div className="msg-assistant" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <div className="msg-head"><span className="avatar-mini">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="5" cy="5" r="1.7" /><circle cx="19" cy="5" r="1.7" /><circle cx="5" cy="19" r="1.7" /><circle cx="19" cy="19" r="1.7" /><rect x="9" y="9" width="6" height="6" rx="1.5" /></svg>
      </span><span className="msg-name">Drone Ops Agent</span></div>
      {m.panel && <FlightPanel data={m.panel} onReport={onReport} />}
      <div className="answer"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text || ''}</ReactMarkdown></div>
      {m.citations?.length > 0 && (
        <div className="citations">
          <button className="disclosure" onClick={() => setShowCites(!showCites)}>
            <BookOpen size={14} /> Sources ({m.citations.length})
            <ChevronDown size={14} className={showCites ? 'rot' : ''} />
          </button>
          <AnimatePresence>
            {showCites && (
              <motion.div className="cite-list" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
                {m.citations.map((c, i) => (
                  <div className="cite-card" key={i}>
                    <b>[{i + 1}] {c.source}</b>
                    <span>{c.page ? `p.${c.page}` : c.section || ''} · relevance {Number(c.score || 0).toFixed(3)}</span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
      {m.trace?.length > 0 && (
        <div className="trace-row"><GitBranch size={13} />{m.trace.map((s, i) => <span key={i} className="trace-chip">{friendly(s)}</span>)}</div>
      )}
      <div className="msg-actions">
        <button onClick={copy}>{copied ? <Check size={13} /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}</button>
        <button onClick={() => onRegenerate(index)}><Zap size={13} /> Regenerate</button>
      </div>
    </motion.div>
  )
}

export default function ChatView({ messages, busy, steps, onSend, onReport, onRegenerate, pendingApproval, flightLogs, onOpenSidebar }) {
  const [text, setText] = useState('')
  const [logFile, setLogFile] = useState('')
  const bottomRef = useRef(null)
  const taRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy, steps])

  const submit = (value) => {
    const q = (value ?? text).trim()
    if (!q || busy) return
    onSend(q, logFile || null)
    setText('')
    if (taRef.current) taRef.current.style.height = 'auto'
  }

  return (
    <div className="chat-view">
      <div className="chat-topbar">
        <button className="icon-btn mobile-only" onClick={onOpenSidebar}><Menu size={18} /></button>
        <div className="crumb"><span>Workspace</span><span className="crumb-sep">/</span><b>Mission control</b></div>
        <div className="topbar-right">
          {pendingApproval && <span className="topbar-alert"><ShieldAlert size={13} /> Approval pending</span>}
          <span className="topbar-live"><span className="live-dot" /> LIVE</span>
        </div>
      </div>

      <div className="chat-scroll">
        <div className="chat-inner">
          {messages.length === 0 && !busy ? <EmptyState onSend={submit} /> : (
            <AnimatePresence initial={false}>
              {messages.map((m, i) => <Message key={m.id || i} m={m} index={i} onReport={onReport} onRegenerate={onRegenerate} />)}
            </AnimatePresence>
          )}
          {busy && (
            <motion.div className="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="thinking-head"><Loader2 size={15} className="spin" /> Drone Ops Agent is working…</div>
              <div className="step-list">
                {steps.map((s, i) => <motion.div key={`${s}-${i}`} className="step" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}><span className="step-bar" />{friendly(s)}</motion.div>)}
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="composer-wrap">
        <div className="composer-inner">
          {flightLogs?.length > 0 && (
            <div className="composer-tools">
              <label className="log-select"><FileText size={13} />
                <select value={logFile} onChange={e => setLogFile(e.target.value)}>
                  <option value="">No log attached</option>
                  {flightLogs.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </label>
            </div>
          )}
          <div className="composer">
            <textarea ref={taRef} rows={1} value={text} placeholder="Ask about legality, maintenance, missions…"
              onChange={e => { setText(e.target.value); e.target.style.height = 'auto'; e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px` }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }} />
            <motion.button className="send-btn" onClick={() => submit()} disabled={!text.trim() || busy}
              whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.94 }}>
              <ArrowUp size={18} strokeWidth={2.2} />
            </motion.button>
          </div>
          <div className="composer-hint">Enter to send · Shift+Enter for a new line · grounded answers with citations</div>
        </div>
      </div>
    </div>
  )
}
