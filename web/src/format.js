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
  max_ms2: 'Peak', rms_ms2: 'RMS', seconds_over: 'Above limit',
  baseline_v: 'Fresh baseline', min_v: 'Minimum', sag_v: 'Sag',
  max_temp_c: 'Peak temperature', avg_temp_c: 'Average temperature',
  current_a: 'Current', voltage_v: 'Voltage',
}
const UNITS = {
  imbalance_pct: '%', sustained_s: ' s', max_ms2: ' m/s²', rms_ms2: ' m/s²',
  seconds_over: ' s', baseline_v: ' V', min_v: ' V', sag_v: ' V',
  max_temp_c: ' °C', avg_temp_c: ' °C', current_a: ' A', voltage_v: ' V',
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
  if (Array.isArray(value)) return value.map(v => typeof v === 'number' ? `${v.toFixed(1)}${unit}` : String(v)).join(', ')
  if (typeof value === 'number') return Number.isInteger(value) ? `${value}${unit}` : `${value.toFixed(1)}${unit}`
  return String(value)
}

export function formatEvidence(ev) {
  if (!ev || typeof ev !== 'object') return ''
  return Object.entries(ev).slice(0, 6)
    .map(([k, v]) => `${LABELS[k] || friendly(k)}: ${fmtValue(k, v)}`)
    .join(' · ')
}

export const severityClass = sev => String(sev || '').toLowerCase().replace('critical', 'high')
