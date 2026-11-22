import React from 'react'
import { motion } from 'framer-motion'
import { MessageSquare, Ticket, ShieldCheck, FileText, Activity, Plus, Cpu, Database, Radio, Sparkles } from 'lucide-react'
import { QUICK_PROMPTS } from '../quick'

const NAV = [
  { key: 'chat', label: 'Chat', icon: MessageSquare },
  { key: 'tickets', label: 'Tickets', icon: Ticket },
  { key: 'approvals', label: 'Approvals', icon: ShieldCheck },
  { key: 'logs', label: 'Flight logs', icon: FileText },
  { key: 'runs', label: 'Runs', icon: Activity },
]

export default function Sidebar({ nav, setNav, onNewChat, onQuick, health, pendingCount, mobileOpen, onCloseMobile }) {
  const llm = health?.llm_available ? 'Groq online' : 'OFFLINE fallback'
  const docs = health?.vector_store_docs ?? '—'

  return (
    <>
      {mobileOpen && <div className="sidebar-scrim" onClick={onCloseMobile} />}
      <motion.aside
        className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.45, ease: [0.2, 0.8, 0.2, 1] }}
      >
        <div className="brand">
          <div className="brand-mark">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
              <path d="M6.4 6.4l3.2 3.2m8-3.2-3.2 3.2m-8 8 3.2-3.2m8 3.2-3.2-3.2" /><rect x="9" y="9" width="6" height="6" rx="1.5" />
            </svg>
          </div>
          <div className="brand-text">
            <div className="brand-name">Drone Ops Agent</div>
            <div className="brand-sub">MULTI-AGENT · UAS READINESS</div>
          </div>
        </div>

        <motion.button className="btn btn-primary sidebar-new" onClick={onNewChat} whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
          <Plus size={16} /> New mission
        </motion.button>

        <div className="nav-label">Workspace</div>
        <nav className="nav-list">
          {NAV.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              className={`nav-item ${nav === key ? 'nav-active' : ''}`}
              onClick={() => { setNav(key); onCloseMobile() }}
            >
              {nav === key && <motion.span layoutId="nav-active" className="nav-active-bg" transition={{ type: 'spring', stiffness: 420, damping: 34 }} />}
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {key === 'approvals' && pendingCount > 0 && <span className="nav-badge">{pendingCount}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-divider" />

        <div className="nav-label">System</div>
        <div className="system-card">
          <div className="sys-row"><Cpu size={14} /><span>LLM</span><b className={health?.llm_available ? 'ok' : 'warn'}>{llm}</b></div>
          <div className="sys-row"><Database size={14} /><span>Index</span><b>{docs} docs</b></div>
          <div className="sys-row"><Radio size={14} /><span>HITL</span><b className="ok">enforced</b></div>
        </div>

        <div className="sidebar-divider" />
        <div className="nav-label">Quick prompts</div>
        <div className="quick-list">
          {QUICK_PROMPTS.map(q => (
            <button key={q.label} className="quick-item" title={q.query}
              onClick={() => { onQuick(q.query); onCloseMobile() }}>
              <Sparkles size={13} /> {q.label}
            </button>
          ))}
        </div>

        <div className="sidebar-foot">
          <span className="foot-sig">Decision support only · not flight-certified</span>
        </div>
      </motion.aside>
    </>
  )
}
