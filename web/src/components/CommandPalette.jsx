import React, { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  Activity, CornerDownLeft, FileText, MessageSquare, Plus, RefreshCw,
  Search, ShieldCheck, Ticket,
} from 'lucide-react'
import { QUICK_PROMPTS } from '../quick'
import { MOD_KEY } from './ui'

const NAV_ITEMS = [
  { key: 'chat', label: 'Mission control', hint: 'Return to the agent', icon: MessageSquare, keywords: 'chat home agent' },
  { key: 'tickets', label: 'Maintenance tickets', hint: 'Findings and sign-off', icon: Ticket, keywords: 'maintenance findings work orders' },
  { key: 'approvals', label: 'Authorizations', hint: 'Human-in-the-loop queue', icon: ShieldCheck, keywords: 'approve reject hitl safety' },
  { key: 'logs', label: 'Flight logs', hint: 'Telemetry ready for analysis', icon: FileText, keywords: 'csv telemetry files' },
  { key: 'runs', label: 'Run audit', hint: 'Every agent invocation', icon: Activity, keywords: 'history audit traces' },
]

export default function CommandPalette({ open, onClose, nav, onNav, onNewChat, onSend, onRefresh }) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const inputRef = useRef(null)
  const itemRefs = useRef([])
  const reduceMotion = useReducedMotion()

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase()
    const match = item => !q || `${item.label} ${item.hint} ${item.keywords || ''}`.toLowerCase().includes(q)

    return [
      {
        label: 'Actions',
        items: [
          {
            id: 'new-mission', label: 'New mission', hint: 'Clear the deck and start over',
            icon: Plus, keywords: 'new chat reset clear', run: onNewChat,
          },
          {
            id: 'refresh', label: 'Refresh telemetry', hint: 'Reload health, tickets, logs and approvals',
            icon: RefreshCw, keywords: 'reload sync health data', run: onRefresh,
          },
        ].filter(match),
      },
      {
        label: 'Navigate',
        items: NAV_ITEMS
          .filter(item => item.key !== nav)
          .map(item => ({
            id: `nav-${item.key}`, label: item.label, hint: item.hint, icon: item.icon,
            keywords: item.keywords, run: () => onNav(item.key),
          }))
          .filter(match),
      },
      {
        label: 'Protocols',
        items: QUICK_PROMPTS.map(p => ({
          id: `prompt-${p.code}`, label: p.label, hint: p.hint, icon: p.icon,
          code: p.code, keywords: p.keywords, run: () => onSend(p.query),
        })).filter(match),
      },
    ].filter(group => group.items.length)
  }, [query, nav, onNav, onNewChat, onSend, onRefresh])

  const flat = useMemo(() => groups.flatMap(group => group.items), [groups])

  useEffect(() => {
    if (!open) return
    setQuery('')
    setActive(0)
    const id = setTimeout(() => inputRef.current?.focus(), 40)
    return () => clearTimeout(id)
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKey = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return
    setActive(0)
  }, [query, open])

  useEffect(() => {
    itemRefs.current[active]?.scrollIntoView({ block: 'nearest' })
  }, [active])

  const invoke = item => {
    if (!item) return
    onClose()
    // Let the overlay begin its exit before the next view paints.
    setTimeout(() => item.run(), 30)
  }

  const onKeyDown = e => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive(i => (flat.length ? (i + 1) % flat.length : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive(i => (flat.length ? (i - 1 + flat.length) % flat.length : 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      invoke(flat[active])
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    }
  }

  let cursor = -1
  const activeId = flat[active] ? `palette-item-${flat[active].id}` : undefined

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="palette-scrim"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.18 }}
          onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            className="palette"
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            initial={reduceMotion ? false : { opacity: 0, y: -14, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -8, scale: 0.99 }}
            transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 380, damping: 32 }}
          >
            <div className="palette-input-wrap">
              <Search size={17} className="palette-search-icon" />
              <input
                ref={inputRef}
                className="palette-input"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Search commands, views, protocols…"
                role="combobox"
                aria-expanded="true"
                aria-controls="palette-list"
                aria-activedescendant={activeId}
                aria-autocomplete="list"
                spellCheck="false"
              />
              <kbd className="palette-mod">{MOD_KEY} K</kbd>
            </div>

            <div className="palette-list" id="palette-list" role="listbox" aria-label="Commands">
              {groups.map(group => (
                <div className="palette-group" key={group.label}>
                  <div className="palette-group-label">{group.label}</div>
                  {group.items.map(item => {
                    cursor += 1
                    const index = cursor
                    const isActive = index === active
                    const Icon = item.icon
                    return (
                      <button
                        key={item.id}
                        ref={el => { itemRefs.current[index] = el }}
                        id={`palette-item-${item.id}`}
                        className={`palette-item ${isActive ? 'is-active' : ''}`}
                        role="option"
                        aria-selected={isActive}
                        onMouseMove={() => setActive(index)}
                        onClick={() => invoke(item)}
                        tabIndex={-1}
                      >
                        <span className="palette-item-icon"><Icon size={15} strokeWidth={1.8} /></span>
                        <span className="palette-item-copy"><b>{item.label}</b><small>{item.hint}</small></span>
                        {item.code && <span className="palette-code">{item.code}</span>}
                        {isActive && <CornerDownLeft size={13} className="palette-enter" />}
                      </button>
                    )
                  })}
                </div>
              ))}
              {flat.length === 0 && (
                <div className="palette-empty">
                  <span>NO MATCH</span>
                  <p>Try “regulation”, “log”, “ticket” or a view name.</p>
                </div>
              )}
            </div>

            <div className="palette-foot">
              <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
              <span><kbd>↵</kbd> select</span>
              <span><kbd>esc</kbd> close</span>
              <span className="palette-foot-end">DRONE OPS / COMMAND</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
