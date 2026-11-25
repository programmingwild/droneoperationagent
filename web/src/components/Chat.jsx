import React, { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  AlertTriangle, ArrowUp, ArrowUpRight, BookOpen, Check, ChevronDown, Copy,
  FileDown, FileText, GitBranch, Loader2, Zap, XCircle,
} from 'lucide-react'
import { friendly, formatEvidence, severityClass, sourceLabel, stripSources, humanizeCitations, cleanSection } from '../format'
import { QUICK_PROMPTS } from '../quick'
import { SeverityPill } from './ui'
import Orbit from './Orbit'

const VERDICT = {
  GROUND: { label: 'Grounded — do not fly', icon: XCircle, tone: 'ground' },
  MONITOR: { label: 'Monitor — restricted operations', icon: AlertTriangle, tone: 'monitor' },
  PASS: { label: 'Pass — no anomalies', icon: Check, tone: 'pass' },
}

const rise = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.2, 0.8, 0.2, 1] } },
}

export function EmptyState({ onSend, health }) {
  const docs = health?.vector_store_docs ?? '—'
  const model = health ? (health.llm_available ? 'Groq online' : 'Offline fallback') : 'Connecting'

  return (
    <div className="hero">
      <div className="hero-grid">
        <div className="hero-copy">
          <div className="hero-eyebrow">
            <span className="live-dot" />
            LIVE MISSION CONTROL
            <span className="hero-eyebrow-sep">/</span>
            {health?.llm_available ? 'SYS NOMINAL' : 'SYS CHECK'}
          </div>

          <h1 className="hero-title">
            <span>Fly with</span>
            <span className="hero-accent">certainty<span className="hero-dot">.</span></span>
          </h1>

          <p className="hero-sub">
            Airspace, airworthiness, flight logs. Every answer is grounded in your documents and
            cited — and nothing takes off without your approval.
          </p>

          <div className="hero-meta">
            <span className="hero-meta-item"><b>{docs}</b> docs indexed</span>
            <span className="hero-meta-item"><b>{model}</b></span>
            <span className="hero-meta-item"><b>HITL</b> enforced</span>
          </div>
        </div>

        <Orbit health={health} />
      </div>

      <div className="protocol-head">
        <span><span className="protocol-dot" /> ISSUE A QUERY</span>
        <span className="protocol-count">04 PROTOCOLS AVAILABLE</span>
      </div>

      <div className="suggest-grid">
        {QUICK_PROMPTS.map(s => (
          <button key={s.label} className="suggest-card" onClick={() => onSend(s.query)}
            aria-label={`${s.label} — ${s.hint}`}>
            <span className="suggest-index">{s.code}</span>
            <span className="suggest-icon"><s.icon size={17} strokeWidth={1.7} /></span>
            <span className="suggest-copy"><b>{s.label}</b><small>{s.hint}</small></span>
            <ArrowUpRight size={17} className="suggest-arrow" />
          </button>
        ))}
      </div>

      <div className="hero-foot">
        <span>GROUNDED</span>
        <span>CITED</span>
        <span>HUMAN-APPROVED</span>
        <span className="hero-foot-end">DRONE OPS / NIGHTWATCH</span>
      </div>
    </div>
  )
}

export function FlightPanel({ data, onReport }) {
  if (!data) return null
  const verdict = VERDICT[String(data.verdict || '').toUpperCase()] || { label: data.verdict || 'Unknown', icon: AlertTriangle, tone: 'monitor' }
  const Icon = verdict.icon
  const anomalies = data.anomalies || []
  const high = anomalies.filter(a => ['HIGH', 'CRITICAL'].includes(String(a.severity || '').toUpperCase())).length
  const score = Number.isFinite(Number(data.anomaly_score)) ? Math.max(0, Math.min(100, Math.round(Number(data.anomaly_score)))) : null
  const tiles = [
    ['Anomaly score', score == null ? '—' : `${score}/100`],
    ['Findings', `${anomalies.length} (${high} high)`],
    ['Vibration max', `${(data.max_vibration_ms2 ?? 0).toFixed(1)} m/s²`],
    ['Voltage sag', `${(data.voltage_sag_v ?? 0).toFixed(1)} V`],
    ['Motor temp max', `${(data.motor_temp_max_c ?? 0).toFixed(0)} °C`],
  ]

  return (
    <motion.div className="panel-stack" initial="hidden" animate="show"
      variants={{ show: { transition: { staggerChildren: 0.06 } } }}>
      <motion.div className={`verdict verdict-${verdict.tone}`} variants={rise}>
        <div className="verdict-icon"><Icon size={20} strokeWidth={1.8} /></div>
        <div className="verdict-main">
          <div className="verdict-kicker">FLIGHT LOG ANALYSIS</div>
          <div className="verdict-label">{verdict.label}</div>
          <div className="verdict-sub">{data.rows ?? '?'} rows · {(data.duration_s ?? 0).toFixed(1)}s · ticket {data.ticket?.id || 'not opened'}</div>
        </div>
        <div className={`gauge gauge-${verdict.tone}`} style={{ '--pct': `${score ?? 0}%` }}>
          <div className="gauge-inner">
            <b>{score ?? '—'}</b>
            <span>ANOMALY</span>
          </div>
        </div>
      </motion.div>

      <motion.div className="tile-grid" variants={rise}>
        {tiles.map(([k, v]) => (
          <div className="tile" key={k}><span className="tile-k">{k}</span><span className="tile-v">{v}</span></div>
        ))}
      </motion.div>

      {anomalies.length > 0 && (
        <motion.div className="findings-head" variants={rise}>
          <span>FINDINGS</span>
          <span>{String(anomalies.length).padStart(2, '0')} DETECTED</span>
        </motion.div>
      )}

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
            <div className="ticket-id">TICKET {data.ticket.id} <SeverityPill value={data.ticket.severity} /></div>
            <p>Aircraft grounded pending inspection. Technician sign-off required before next flight.</p>
          </div>
          <button className="btn btn-ghost" onClick={() => onReport(data.ticket.id)}>
            <FileDown size={15} /> Export PDF
          </button>
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
      <motion.div className="msg-user" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}>
        <span className="msg-user-meta">OPERATOR</span>
        <div className="bubble-user">{m.text}</div>
      </motion.div>
    )
  }

  const answerText = humanizeCitations(stripSources(m.text))

  const copy = () => navigator.clipboard?.writeText(answerText).then(() => {
    setCopied(true); setTimeout(() => setCopied(false), 1600)
  }).catch(() => {})

  return (
    <motion.div className="msg-assistant" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}>
      <div className="msg-head">
        <span className="avatar-mini">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
            <circle cx="5" cy="5" r="1.7" /><circle cx="19" cy="5" r="1.7" />
            <circle cx="5" cy="19" r="1.7" /><circle cx="19" cy="19" r="1.7" />
            <rect x="9" y="9" width="6" height="6" rx="1.5" />
          </svg>
        </span>
        <span className="msg-name">DRONE OPS AGENT</span>
        {m.streaming && <span className="msg-tag msg-tag-live"><Loader2 size={10} className="spin" /> THINKING</span>}
        {!m.streaming && m.text && <span className="msg-tag">GROUNDED</span>}
      </div>

      {m.panel && <FlightPanel data={m.panel} onReport={onReport} />}

      <div className="answer">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{answerText}</ReactMarkdown>
      </div>

      {m.citations?.length > 0 && (
        <div className="citations">
          <button className="disclosure" onClick={e => {
            const next = !showCites
            setShowCites(next)
            if (next) setTimeout(() => {
              e.currentTarget.closest('.msg-assistant')?.querySelector('.cite-list')
                ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
            }, 320)
          }} aria-expanded={showCites}>
            <BookOpen size={14} /> Sources ({m.citations.length})
            <ChevronDown size={14} className={showCites ? 'rot' : ''} />
          </button>
          <AnimatePresence>
            {showCites && (
              <motion.div className="cite-list" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
                {m.citations.map((c, i) => {
                  const score = Number(c.score || 0)
                  const rel = Math.round(Math.min(1, score) * 100)
                  const match = score >= 0.6 ? 'Strong match' : score >= 0.4 ? 'Good match' : 'Related passage'
                  const section = cleanSection(c.section)
                  const label = sourceLabel(c.source)
                  const title = section || label || 'Document passage'
                  return (
                    <div className="cite-card" key={i} style={{ '--rel': `${rel}%` }}>
                      <div className="cite-card-top">
                        <b>[{i + 1}] {title}</b>
                        <span className="cite-rel">{match}</span>
                      </div>
                      <div className="cite-meta">
                        {section && label && <span className="cite-source">{label}</span>}
                        {c.page && <span>p.{c.page}</span>}
                        {!section && <span>Document passage</span>}
                      </div>
                      <div className="cite-bar"><i /></div>
                    </div>
                  )
                })}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {m.trace?.length > 0 && (
        <div className="trace-row">
          <span className="trace-label"><GitBranch size={12} /> TRACE</span>
          {m.trace.map((s, i) => <span key={i} className="trace-chip">{friendly(s)}</span>)}
        </div>
      )}

      {!m.streaming && (
        <div className="msg-actions">
          <button onClick={copy} aria-label="Copy answer">
            {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}
          </button>
          <button onClick={() => onRegenerate(index)}><Zap size={13} /> Regenerate</button>
        </div>
      )}
    </motion.div>
  )
}

export function QuickBar({ onSend, disabled }) {
  const [open, setOpen] = useState(true)
  if (!open) {
    return (
      <div className="quickbar quickbar-collapsed">
        <button className="quickbar-reopen" onClick={() => setOpen(true)}>
          <Zap size={13} /> Protocols
        </button>
      </div>
    )
  }
  return (
    <div className="quickbar">
      <span className="quickbar-label"><Zap size={11} /> PROTOCOLS</span>
      <div className="quickbar-items">
        {QUICK_PROMPTS.map(q => (
          <button key={q.label} className="quick-chip" onClick={() => onSend(q.query)}
            disabled={disabled} title={q.query}>
            <q.icon size={13} strokeWidth={1.8} />
            <span>{q.label}</span>
          </button>
        ))}
      </div>
      <button className="quickbar-hide" onClick={() => setOpen(false)} title="Hide protocols" aria-label="Hide protocols">
        <ChevronDown size={14} />
      </button>
    </div>
  )
}

export default function ChatView({
  messages, busy, steps, onSend, onReport, onRegenerate, flightLogs, health,
}) {
  const [text, setText] = useState('')
  const [logFile, setLogFile] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const bottomRef = useRef(null)
  const scrollRef = useRef(null)
  const taRef = useRef(null)

  useEffect(() => {
    if (messages.length === 0 && !busy) {
      scrollRef.current?.scrollTo({ top: 0, behavior: 'auto' })
      return
    }
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy, steps])

  useEffect(() => {
    if (!busy) { setElapsed(0); return }
    const started = Date.now()
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => clearInterval(id)
  }, [busy])

  const submit = (value) => {
    const q = (value ?? text).trim()
    if (!q || busy) return
    onSend(q, logFile || null)
    setText('')
    if (taRef.current) taRef.current.style.height = 'auto'
  }

  return (
    <div className="chat-view">
      {(messages.length > 0 || busy) && <QuickBar onSend={submit} disabled={busy} />}

      <div className="chat-scroll" ref={scrollRef}>
        <div className={`chat-inner ${messages.length === 0 && !busy ? 'chat-inner-empty' : ''}`}>
          {messages.length === 0 && !busy
            ? <EmptyState onSend={submit} health={health} />
            : (
              <AnimatePresence initial={false}>
                {messages.map((m, i) => (
                  <Message key={m.id || i} m={m} index={i} onReport={onReport} onRegenerate={onRegenerate} />
                ))}
              </AnimatePresence>
            )}

          {busy && (
            <motion.div className="thinking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} role="status" aria-live="polite">
              <div className="thinking-head">
                <span className="eq" aria-hidden="true"><i /><i /><i /><i /></span>
                <span>Agent mesh working</span>
                <span className="thinking-time">{elapsed}s</span>
              </div>
              <div className="step-list">
                {steps.length === 0 && <div className="step"><span className="step-dot" />Establishing agent mesh…</div>}
                {steps.map((s, i) => (
                  <motion.div key={`${s}-${i}`} className="step" initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}>
                    <span className="step-dot" />{friendly(s)}
                  </motion.div>
                ))}
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
              <label className="log-select">
                <FileText size={13} />
                <select value={logFile} onChange={e => setLogFile(e.target.value)} aria-label="Attach a flight log">
                  <option value="">Attach telemetry</option>
                  {flightLogs.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </label>
              {logFile && <span className="attach-live"><span className="live-dot" /> attached</span>}
            </div>
          )}

          <div className="composer">
            <span className="composer-prefix" aria-hidden="true">›</span>
            <textarea
              ref={taRef}
              rows={1}
              value={text}
              placeholder="Ask about airspace or a flight log…"
              aria-label="Message the Drone Ops Agent"
              onChange={e => {
                setText(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
              }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
            />
            <motion.button className="send-btn" onClick={() => submit()} disabled={!text.trim() || busy}
              whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.94 }} aria-label="Send message">
              {busy ? <Loader2 size={17} className="spin" /> : <ArrowUp size={18} strokeWidth={2.3} />}
            </motion.button>
          </div>

          <div className="composer-foot">
            <span>ENTER TO SEND · SHIFT+ENTER FOR A NEW LINE</span>
            <span className="composer-foot-end">RAG · CITED · HUMAN-APPROVED</span>
          </div>
        </div>
      </div>
    </div>
  )
}
