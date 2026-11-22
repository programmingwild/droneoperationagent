import React, { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from './api'
import Sidebar from './components/Sidebar'
import ChatView from './components/Chat'
import ApprovalModal from './components/ApprovalModal'
import { Toasts } from './components/ui'
import { TicketsView, ApprovalsView, LogsView, RunsView } from './components/Views'

let seq = 0
const uid = () => `m-${Date.now()}-${seq++}`

export default function App() {
  const [nav, setNav] = useState('chat')
  const [messages, setMessages] = useState([])
  const [pendingApproval, setPendingApproval] = useState(null)
  const [health, setHealth] = useState(null)
  const [logsData, setLogsData] = useState({ tickets: [], runs: [], flight_logs: [] })
  const [busy, setBusy] = useState(false)
  const [steps, setSteps] = useState([])
  const [toasts, setToasts] = useState([])
  const [mobileNav, setMobileNav] = useState(false)
  const threadRef = useRef(null)

  const toast = useCallback((text, tone = 'info') => {
    const id = uid()
    setToasts(t => [...t, { id, text, tone }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4200)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [h, l, p] = await Promise.all([api.health(), api.logs(40), api.pending()])
      setHealth(h)
      setLogsData(l)
      setPendingApproval(p?.[0] || null)
    } catch (e) {
      toast(`API unreachable — start FastAPI on port 8000 (${e.message})`, 'danger')
    }
  }, [toast])

  useEffect(() => { refresh() }, [refresh])

  const newChat = () => {
    setMessages([]); setSteps([]); setPendingApproval(null); threadRef.current = null
    setNav('chat'); setMobileNav(false)
  }

  const patchLast = (fn) => setMessages(ms => {
    if (!ms.length) return ms
    const copy = [...ms]
    copy[copy.length - 1] = { ...copy[copy.length - 1], ...fn(copy[copy.length - 1]) }
    return copy
  })

  const send = async (query, logFile) => {
    if (busy) return
    setBusy(true); setSteps([]); setNav('chat')
    setMessages(ms => [...ms, { id: uid(), role: 'user', text: query, ts: Date.now() }])
    setMessages(ms => [...ms, { id: uid(), role: 'assistant', text: '', citations: [], trace: [], panel: null, streaming: true }])

    const history = messages.filter(m => m.text).slice(-12).map(m => ({ role: m.role, content: m.text }))
    try {
      for await (const ev of api.chat({ query, logFile, history })) {
        if (ev.type === 'run_started') {
          threadRef.current = ev.thread_id
        } else if (ev.type === 'node') {
          setSteps(s => [...s, ev.node])
        } else if (ev.type === 'approval_required') {
          setPendingApproval({ id: ev.approval_id, action: ev.action, summary: ev.summary, thread_id: ev.thread_id })
          patchLast(() => ({ text: 'This flight requires your explicit approval before any takeoff/arm authorization. Use the approval panel to decide.', streaming: false }))
        } else if (ev.type === 'final') {
          patchLast(() => ({
            text: ev.answer || '', citations: ev.citations || [], trace: ev.trace || [],
            panel: ev.tool_results?.log_analysis ? { ...ev.tool_results.log_analysis, ticket: ev.tool_results.ticket } : null,
            streaming: false,
          }))
        } else if (ev.type === 'error') {
          patchLast(() => ({ text: `Agent error: ${ev.error}\n\n${ev.safe_default || 'Do not launch. Resolve the error and retry.'}`, streaming: false }))
          toast('Agent error — fail-safe response shown', 'danger')
        }
      }
    } catch (e) {
      patchLast(() => ({ text: `Could not reach the API: ${e.message}`, streaming: false }))
      toast('API request failed', 'danger')
    } finally {
      setBusy(false); setSteps([])
      refresh()
    }
  }

  const decide = async (id, approved) => {
    if (!id) { toast('No approval ID available — refresh and retry', 'danger'); return }
    setBusy(true)
    try {
      const res = await api.decide(id, approved)
      setMessages(ms => [...ms, { id: uid(), role: 'assistant', text: res.answer || `Authorization ${approved ? 'approved' : 'rejected'}.` }])
      setPendingApproval(null)
      toast(`Authorization ${approved ? 'approved' : 'rejected'}`)
      refresh()
    } catch (e) {
      toast(`Decision failed: ${e.message}`, 'danger')
    } finally { setBusy(false) }
  }

  const report = async id => {
    try { await api.report(id); toast('PDF report downloaded') }
    catch (e) { toast(`Export failed: ${e.message}`, 'danger') }
  }

  const regenerate = index => {
    const msgs = messages.slice(0, index)
    const lastUser = [...msgs].reverse().find(m => m.role === 'user')
    setMessages(msgs)
    if (lastUser) setTimeout(() => send(lastUser.text, null), 30)
  }

  const view = () => {
    switch (nav) {
      case 'tickets': return <TicketsView tickets={logsData.tickets} onReport={report} />
      case 'approvals': return <ApprovalsView pending={pendingApproval ? [pendingApproval] : []} onDecide={decide} busy={busy} />
      case 'logs': return <LogsView logs={logsData.flight_logs} onAnalyze={send} />
      case 'runs': return <RunsView runs={logsData.runs} />
      default: return <ChatView messages={messages} busy={busy} steps={steps} onSend={send} onReport={report}
        onRegenerate={regenerate} pendingApproval={pendingApproval} flightLogs={logsData.flight_logs}
        onOpenSidebar={() => setMobileNav(true)} />
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient" aria-hidden="true"><span /><span /><span /></div>
      <Sidebar nav={nav} setNav={setNav} onNewChat={newChat}
        onQuick={q => send(q, null)} health={health}
        pendingCount={pendingApproval ? 1 : 0}
        mobileOpen={mobileNav} onCloseMobile={() => setMobileNav(false)} />
      <main className="main">
        <AnimatePresence mode="wait">
          <motion.div key={nav} className="view" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}>
            {view()}
          </motion.div>
        </AnimatePresence>
      </main>
      <ApprovalModal pending={pendingApproval} onDecide={decide} busy={busy} />
      <Toasts items={toasts} />
    </div>
  )
}
