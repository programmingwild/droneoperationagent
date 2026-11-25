import React from 'react'
import { ChevronRight, Menu, Search, ShieldAlert } from 'lucide-react'
import { Clock, MOD_KEY, StatusDot } from './ui'

const LABELS = {
  chat: 'Mission control',
  tickets: 'Maintenance tickets',
  approvals: 'Authorizations',
  logs: 'Flight logs',
  runs: 'Run audit',
}

export default function TopBar({ nav, health, pendingCount, onOpenSidebar, onOpenPalette, onOpenApprovals }) {
  const nominal = health?.llm_available
  return (
    <header className="topbar">
      <button className="icon-btn mobile-only" onClick={onOpenSidebar} aria-label="Open navigation">
        <Menu size={18} />
      </button>

      <div className="crumb">
        <span className="crumb-root">FLIGHT DECK</span>
        <ChevronRight size={12} className="crumb-sep" />
        <b>{LABELS[nav] || LABELS.chat}</b>
      </div>

      <div className="topbar-center">
        <span className="topbar-signal">
          <StatusDot tone={nominal ? 'green' : health ? 'amber' : 'muted'} pulse={!!nominal} />
          {health ? (nominal ? 'SYS NOMINAL' : 'OFFLINE MODE') : 'CONNECTING'}
        </span>
      </div>

      <div className="topbar-right">
        {pendingCount > 0 && (
          <button className="topbar-alert" onClick={onOpenApprovals} aria-label={`${pendingCount} approvals pending`}>
            <ShieldAlert size={14} />
            <span className="topbar-alert-text">{pendingCount} approval{pendingCount > 1 ? 's' : ''} pending</span>
          </button>
        )}
        <Clock />
        <button className="cmdk-trigger" onClick={onOpenPalette} aria-label="Open command palette">
          <Search size={14} />
          <span className="cmdk-label">Command</span>
          <kbd>{MOD_KEY} K</kbd>
        </button>
        <span className="topbar-live"><span className="live-dot" /> LIVE</span>
      </div>
    </header>
  )
}
