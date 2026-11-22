// Served by FastAPI: use same origin. Vite dev (:5173): point at the API.
const DEFAULT_API = window.location.port === '5173' ? 'http://127.0.0.1:8000' : window.location.origin
const BASE = (import.meta.env.VITE_API_URL || DEFAULT_API).replace(/\/$/, '')

async function json(path, options) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  health: () => json('/health'),
  logs: (limit = 25) => json(`/logs?limit=${limit}`),
  pending: () => json('/approvals/pending'),
  ticket: id => json(`/tickets/${encodeURIComponent(id)}`),

  async decide(id, approved) {
    return json('/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_id: id, approved, decided_by: 'web-operator' }),
    })
  },

  async report(id) {
    const res = await fetch(`${BASE}/report/${encodeURIComponent(id)}`, { method: 'POST' })
    if (!res.ok) throw new Error('Report export failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${id}.pdf`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
  },

  async *chat({ query, logFile, history, lat, lon }) {
    const res = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, log_file: logFile || null, history: history || [], lat, lon }),
    })
    if (!res.ok || !res.body) throw new Error(`Chat failed (${res.status})`)
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const frames = buffer.split('\n\n')
      buffer = frames.pop() || ''
      for (const frame of frames) {
        const line = frame.split('\n').find(l => l.startsWith('data: '))
        if (!line) continue
        try { yield JSON.parse(line.slice(6)) } catch { /* ignore malformed frame */ }
      }
    }
  },
}
