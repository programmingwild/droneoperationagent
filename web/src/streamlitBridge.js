// Bridge the React SPA's fetch() calls to the Streamlit component host.
// Streamlit Cloud has no separate HTTP API, so requests are forwarded as
// component values to the Python script, which runs the same FastAPI handlers
// in-process and sends the result back through component args.
import { Streamlit } from 'streamlit-component-lib'

const nativeFetch = window.fetch.bind(window)
const pending = new Map()
const queue = []
let counter = 0
let inFlight = false

function endpoint(path) {
  if (path === '/health') return ['health', {}]
  if (path.startsWith('/logs')) {
    const limit = Number(new URLSearchParams(path.split('?')[1] || '').get('limit') || 40)
    return ['logs', { limit }]
  }
  if (path.startsWith('/approvals/pending')) return ['pending', {}]
  if (path.startsWith('/approve')) return ['approve', {}]
  if (path.startsWith('/chat')) return ['chat', {}]
  const report = path.match(/^\/report\/(.+)$/)
  if (report) return ['report', { id: decodeURIComponent(report[1]) }]
  if (path.startsWith('/tickets/')) return ['ticket', { id: decodeURIComponent(path.slice(9)) }]
  return [null, null]
}

function responseFor(item, data) {
  if (item.kind === 'chat') {
    return new Response(data, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
  }
  if (item.kind === 'report') {
    const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0))
    return new Response(bytes, { status: 200, headers: { 'Content-Type': 'application/pdf' } })
  }
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function failure(message) {
  return new Response(JSON.stringify({ detail: message }), {
    status: /not found/i.test(message) ? 404 : 500,
    headers: { 'Content-Type': 'application/json' },
  })
}

function dispatchNext() {
  if (inFlight || !queue.length) return
  inFlight = true
  const item = queue.shift()
  pending.set(item.id, item)
  Streamlit.setComponentValue({ id: item.id, kind: item.kind, payload: item.payload })
}

function fitFrame() {
  const height = window.parent?.innerHeight || window.innerHeight
  Streamlit.setFrameHeight(Math.max(560, height))
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, event => {
  fitFrame()
  const answer = event.detail?.args?.response
  if (!answer || !pending.has(answer.id)) return
  const item = pending.get(answer.id)
  pending.delete(answer.id)
  item.resolve(answer.ok ? responseFor(item, answer.data) : failure(answer.error))
  inFlight = false
  dispatchNext()
})

window.fetch = async (input, options = {}) => {
  const url = String(input)
  const absolute = url.startsWith('http') ? new URL(url) : new URL(url, window.location.origin)
  if (absolute.origin !== window.location.origin) return nativeFetch(input, options)
  const [kind, params] = endpoint(absolute.pathname + absolute.search)
  if (!kind) return nativeFetch(input, options)

  let payload = params
  if (options.body) {
    try { payload = { ...params, ...JSON.parse(options.body) } } catch { /* non-JSON body */ }
  }
  const id = `nw-${++counter}`
  return new Promise(resolve => {
    queue.push({ id, kind, payload, resolve })
    dispatchNext()
  })
}

Streamlit.setComponentReady()
fitFrame()
window.addEventListener('resize', fitFrame)
setTimeout(fitFrame, 200)
setTimeout(fitFrame, 1000)
