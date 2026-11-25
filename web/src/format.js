// Human-readable labels shared across the React UI (mirrors backend/app/formatting.py).
const FRIENDLY = {
  TAKEOFF_AUTHORIZATION: 'Takeoff authorization', RPA_ARM: 'RPA arming',
  TAKEOFF: 'Takeoff', ARM: 'Arming', INSPECT: 'Inspection required',
  HOLD: 'Hold — do not launch', GROUND: 'Grounded', GROUNDED: 'Grounded',
  MONITOR: 'Restricted operations', PASS: 'No anomalies', NONE: 'None',
  TRIAGE: 'Triage', MISSION_PLANNING: 'Mission planning', MAINTENANCE: 'Maintenance',
  REGULATION: 'Regulation compliance', ANOMALY: 'Anomaly detection',
  SAFETY_SUPERVISOR: 'Safety supervisor', HUMAN_APPROVAL: 'Human approval',
  FINALIZE: 'Finalize', COMPLETED: 'Completed', AWAITING_APPROVAL: 'Awaiting approval',
  APPROVAL_REQUIRED: 'Approval required', PAUSED: 'Paused', ERROR: 'Error',
  PENDING: 'Pending', APPROVED: 'Approved', REJECTED: 'Rejected',
  OPEN: 'Open', CLOSED: 'Closed', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low', CRITICAL: 'Critical',
  MOTOR_CURRENT_IMBALANCE: 'Motor current imbalance', VIBRATION_EXCESSIVE: 'Excessive vibration',
  BATTERY_VOLTAGE_SAG: 'Battery voltage sag', MOTOR_TEMP: 'Motor overheat',
  MOTOR_OVERHEAT: 'Motor overheat', VOLTAGE_LOW: 'Low pack voltage',
  FLIGHT_LOG_ANALYSIS: 'Flight log analysis',
}
const ACRONYMS = new Set(['RPA', 'UAS', 'VTOL', 'FAA', 'EASA', 'DGCA', 'NOTAM', 'METAR', 'TAF', 'HITL', 'PDF', 'ID', 'ESC', 'IMU', 'RMS', 'IR'])
const LABELS = {
  motor: 'Motor', imbalance_pct: 'Imbalance', sustained_s: 'Sustained',
  max_ms2: 'Peak vibration', rms_ms2: 'RMS vibration', seconds_over: 'Above limit',
  baseline_v: 'Fresh baseline', min_v: 'Minimum', sag_v: 'Sag',
  max_temp_c: 'Peak temperature', avg_temp_c: 'Average temperature',
  max_c: 'Peak temperature', current_a: 'Current', voltage_v: 'Voltage',
}
const UNITS = {
  imbalance_pct: '%', sustained_s: ' s', max_ms2: ' m/s²', rms_ms2: ' m/s²',
  seconds_over: ' s', baseline_v: ' V', min_v: ' V', sag_v: ' V',
  max_temp_c: ' °C', avg_temp_c: ' °C', max_c: ' °C', current_a: ' A', voltage_v: ' V',
}

export function friendly(value, fallback = '—') {
  const s = String(value ?? '').trim()
  if (!s) return fallback
  if (FRIENDLY[s]) return FRIENDLY[s]
  if (FRIENDLY[s.toUpperCase()]) return FRIENDLY[s.toUpperCase()]
  return s.replace(/[_-]/g, ' ').split(/\s+/)
    .map(w => ACRONYMS.has(w.toUpperCase()) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

function fmtValue(key, value) {
  const unit = UNITS[key] || ''
  if (typeof value === 'number') return Number.isInteger(value) ? `${value}${unit}` : `${value.toFixed(1)}${unit}`
  return String(value)
}

// Evidence arrays are per-sample telemetry. Summarize them instead of dumping
// every reading: a peak for deviation series, a range for everything else.
function fmtSamples(key, values) {
  const nums = values.filter(v => typeof v === 'number' && Number.isFinite(v))
  if (!nums.length) return values.slice(0, 3).map(String).join(', ')
  if (nums.length === 1) return fmtValue(key, nums[0])
  const unit = UNITS[key] || ''
  if (key.endsWith('_pct')) {
    const peak = nums.reduce((a, b) => (Math.abs(b) > Math.abs(a) ? b : a))
    return `${peak > 0 ? '+' : ''}${peak.toFixed(1)}${unit}`
  }
  return `${Math.min(...nums).toFixed(1)}–${Math.max(...nums).toFixed(1)}${unit}`
}

function evidenceLabel(key, value) {
  const base = LABELS[key] || friendly(key)
  if (!Array.isArray(value) || value.length < 2) return base
  return key.endsWith('_pct') ? `Peak ${base.toLowerCase()}` : `${base} range`
}

export function formatEvidence(ev) {
  if (!ev || typeof ev !== 'object') return ''
  return Object.entries(ev)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .slice(0, 6)
    .map(([k, v]) => `${evidenceLabel(k, v)}: ${Array.isArray(v) ? fmtSamples(k, v) : fmtValue(k, v)}`)
    .join(' · ')
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function formatTimestamp(value, { year = true } = {}) {
  const raw = String(value || '').trim()
  // Backend audit rows are naive UTC; treat them as UTC rather than browser-local time.
  const d = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw) ? raw : `${raw}Z`)
  if (Number.isNaN(d.getTime())) return String(value || '')
  const pad = n => String(n).padStart(2, '0')
  const date = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}${year ? ` ${d.getUTCFullYear()}` : ''}`
  return `${date} · ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`
}

// "Flight log anomaly review — verdict Grounded (score 85/100)" reads like a
// backend log line. Split the useful parts so the UI can style them.
export function ticketHeadline(title) {
  const raw = String(title || '').trim()
  const m = raw.match(/^(.*?)\s*(?:—|–|-)\s*verdict\s+(.+?)\s*\(\s*score\s+(\d+)\s*\/\s*100\s*\)\s*$/i)
  if (!m) return { title: raw || 'Maintenance ticket', verdict: '', score: null }
  return {
    title: m[1].trim() || 'Flight log anomaly review',
    verdict: m[2].trim(),
    score: Number(m[3]),
  }
}

// Long markdown summaries belong in the approval modal; list rows get a
// readable plain-text preview.
export function plainPreview(text, max = 220) {
  const s = String(text || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_#>`~]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  if (s.length <= max) return s
  return `${s.slice(0, max).replace(/\s+\S*$/, '')}…`
}

export const severityClass = sev => String(sev || '').toLowerCase().replace('critical', 'high')

// `faa_part_107.md` -> `FAA Part 107`; keeps acronyms readable.
export function sourceLabel(source) {
  const base = String(source || '').split(/[\\/]/).pop().replace(/\.[a-z0-9]+$/i, '')
  return base.split(/[_\-\s]+/).filter(Boolean)
    .map(w => ACRONYMS.has(w.toUpperCase()) ? w.toUpperCase() : (/^\d+$/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ')
}

// The backend appends a plain-text Sources list for non-SPA clients; the React UI
// renders those as structured citation cards instead.
export function stripSources(text) {
  return String(text || '')
    .replace(/\n{2,}\*\*Sources\*\*\n[\s\S]*?(?=\n{2,}\*\*|$)/i, '')
    .trimEnd()
}

const SUPERSCRIPT = { 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' }

// RAG answers cite as 【2】; render that as a quiet superscript instead.
export function humanizeCitations(text) {
  return String(text || '').replace(/【(\d+)】/g, (_, n) =>
    n.split('').map(d => SUPERSCRIPT[d] || d).join(''))
}

// Drops ingestion-only qualifiers from document section titles.
export function cleanSection(section) {
  return String(section || '').replace(/\s*\(condensed for rag\)\s*/i, '').trim()
}
