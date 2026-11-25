import React from 'react'
import { motion } from 'framer-motion'
import {
  Activity, Command, Cpu, Database, FileText, MessageSquare, Plus,
  Radio, ShieldCheck, Ticket,
} from 'lucide-react'
import { MOD_KEY, StatusDot } from './ui'

const NAV = [
  { key: 'chat', label: 'Mission control', icon: MessageSquare },
  { key: 'tickets', label: 'Tickets', icon: Ticket },
  { key: 'approvals', label: 'Approvals', icon: ShieldCheck },
  { key: 'logs', label: 'Flight logs', icon: FileText },
  { key: 'runs', label: 'Runs', icon: Activity },
]

export default function Sidebar({
  nav, setNav, onNewChat, health, pendingCount, mobileOpen, onCloseMobile, onOpenPalette,
}) {
  const llm = health?.llm_available ? 'Groq' : health ? 'Offline' : '—'
  const docs = health?.vector_store_docs ?? '—'

  return (
    <>
      {mobileOpen && <div className="sidebar-scrim" onClick={onCloseMobile} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">
            <svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor"
              strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" />
              <circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
              <path d="M6.4 6.4l3.2 3.2m8-3.2-3.2 3.2m-8 8 3.2-3.2m8 3.2-3.2-3.2" />
              <rect x="9" y="9" width="6" height="6" rx="1.5" />
            </svg>
          </div>
          <div className="brand-text">
            <div className="brand-name">Drone Ops<span>.</span></div>
            <div className="brand-sub">AUTONOMOUS FLIGHT DECK</div>
          </div>
          <span className="brand-ver">2.0</span>
        </div>

        <motion.button className="new-mission" onClick={onNewChat} whileTap={{ scale: 0.985 }}>
          <span className="new-mission-icon"><Plus size={14} strokeWidth={2.6} /></span>
          <span>New mission</span>
        </motion.button>

        <div className="nav-label">Workspace</div>
        <nav className="nav-list" aria-label="Workspace">
          {NAV.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`nav-item ${nav === key ? 'nav-active' : ''}`}
              onClick={() => { setNav(key); onCloseMobile() }}
              aria-current={nav === key ? 'page' : undefined}
            >
              {nav === key && (
                <motion.span layoutId="nav-active" className="nav-active-bg"
                  transition={{ type: 'spring', stiffness: 420, damping: 34 }} />
              )}
              <Icon size={17} strokeWidth={1.7} />
              <span>{label}</span>
              {key === 'approvals' && pendingCount > 0 && <span className="nav-badge">{pendingCount}</span>}
              {nav === key && <span className="nav-caret">›</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-divider" />

        <div className="nav-label">System</div>
        <div className="system-card">
          <div className="system-card-head">
            <span>LIVE READOUT</span>
            <span className="system-state">
              <StatusDot tone={health?.llm_available ? 'green' : 'amber'} pulse={!!health?.llm_available} />
              {health?.llm_available ? 'NOMINAL' : health ? 'DEGRADED' : 'SYNCING'}
            </span>
          </div>
          <div className="sys-row"><Cpu size={13} /><span>Inference</span><b className={health?.llm_available ? 'ok' : 'warn'}>{llm}</b></div>
          <div className="sys-row"><Database size={13} /><span>Document index</span><b>{docs}</b></div>
          <div className="sys-row"><Radio size={13} /><span>Safety gate</span><b className="ok">Enforced</b></div>
          <div className="sys-row"><Activity size={13} /><span>Agent mesh</span><b>5 nodes</b></div>
        </div>

        <div className="sidebar-spacer" />

        <button className="palette-trigger" onClick={onOpenPalette}>
          <Command size={14} />
          <span>Command palette</span>
          <kbd>{MOD_KEY} K</kbd>
        </button>

        <div className="sidebar-foot">
          <span>DECISION SUPPORT ONLY</span>
          <span>NOT FLIGHT CERTIFIED</span>
        </div>
      </aside>
    </>
  )
}
