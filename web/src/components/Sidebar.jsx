import React from 'react'
import { motion } from 'framer-motion'
import {
  Activity, Command, FileText, MessageSquare, ShieldCheck, Ticket,
} from 'lucide-react'

const NAV = [
  { key: 'chat', label: 'Mission control', icon: MessageSquare },
  { key: 'tickets', label: 'Tickets', icon: Ticket },
  { key: 'approvals', label: 'Approvals', icon: ShieldCheck },
  { key: 'logs', label: 'Flight logs', icon: FileText },
  { key: 'runs', label: 'Runs', icon: Activity },
]

export default function Sidebar({
  nav, setNav, mobileOpen, onCloseMobile, onOpenPalette, pendingCount,
}) {
  return (
    <>
      {mobileOpen && <div className="sidebar-scrim" onClick={onCloseMobile} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`} aria-label="Primary navigation">
        <button className="rail-brand" onClick={() => { setNav('chat'); onCloseMobile() }}
          aria-label="Mission control">
          <span className="rail-brand-mark">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"
              strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" />
              <circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
              <path d="M6.4 6.4l3.2 3.2m8-3.2-3.2 3.2m-8 8 3.2-3.2m8 3.2-3.2-3.2" />
              <rect x="9" y="9" width="6" height="6" rx="1.5" />
            </svg>
          </span>
          <span className="rail-brand-text">
            <b>Drone Ops<span>.</span></b>
            <small>AUTONOMOUS FLIGHT DECK</small>
          </span>
        </button>

        <nav className="nav-list" aria-label="Workspace">
          {NAV.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`nav-item ${nav === key ? 'nav-active' : ''}`}
              onClick={() => { setNav(key); onCloseMobile() }}
              aria-label={label}
              aria-current={nav === key ? 'page' : undefined}
            >
              {nav === key && (
                <motion.span layoutId="nav-active" className="nav-active-bg"
                  transition={{ type: 'spring', stiffness: 420, damping: 34 }} />
              )}
              <Icon size={18} strokeWidth={1.7} />
              <span className="nav-text">{label}</span>
              {key === 'approvals' && pendingCount > 0 && (
                <span className="nav-badge">{pendingCount}</span>
              )}
              {nav === key && <span className="nav-caret">›</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-spacer" />

        <button className="rail-btn" onClick={onOpenPalette} aria-label="Command palette">
          <Command size={16} strokeWidth={1.7} />
          <span className="nav-text">Command palette</span>
        </button>
      </aside>
    </>
  )
}
