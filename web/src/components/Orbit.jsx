import React, { useRef } from 'react'
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'framer-motion'

const TICKS = Array.from({ length: 60 }, (_, i) => {
  const angle = (i * 6) * Math.PI / 180
  const long = i % 5 === 0
  const inner = long ? 176 : 182
  const outer = 188
  return {
    x1: 210 + inner * Math.cos(angle),
    y1: 210 + inner * Math.sin(angle),
    x2: 210 + outer * Math.cos(angle),
    y2: 210 + outer * Math.sin(angle),
    long,
  }
})

function DroneGlyph({ size = 56 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="5" cy="5" r="2.1" />
      <circle cx="19" cy="5" r="2.1" />
      <circle cx="5" cy="19" r="2.1" />
      <circle cx="19" cy="19" r="2.1" />
      <path d="M6.45 6.45l3.15 3.15m8-3.15l-3.15 3.15m-8 8l3.15-3.15m8 3.15l-3.15-3.15" />
      <rect x="9" y="9" width="6" height="6" rx="1.6" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    </svg>
  )
}

function Chip({ className, label, value }) {
  return (
    <div className={`orbit-chip ${className}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  )
}

export default function Orbit({ health }) {
  const ref = useRef(null)
  const reduceMotion = useReducedMotion()
  const mx = useMotionValue(0)
  const my = useMotionValue(0)
  const springX = useSpring(mx, { stiffness: 110, damping: 18, mass: 0.6 })
  const springY = useSpring(my, { stiffness: 110, damping: 18, mass: 0.6 })
  const rotateY = useTransform(springX, [-0.5, 0.5], [-6, 6])
  const rotateX = useTransform(springY, [-0.5, 0.5], [5, -5])

  const handleMove = e => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    mx.set((e.clientX - rect.left) / rect.width - 0.5)
    my.set((e.clientY - rect.top) / rect.height - 0.5)
  }

  const reset = () => { mx.set(0); my.set(0) }

  const docs = health?.vector_store_docs ?? '—'
  const model = health ? (health.llm_available ? 'Groq online' : 'Offline') : 'Connecting'

  return (
    <motion.div
      ref={ref}
      className="orbit"
      aria-hidden="true"
      onPointerMove={reduceMotion ? undefined : handleMove}
      onPointerLeave={reduceMotion ? undefined : reset}
      style={reduceMotion ? undefined : { rotateX, rotateY, transformPerspective: 1100 }}
    >
      <div className="orbit-halo" />
      <div className="orbit-radar" />

      <svg className="orbit-svg" viewBox="0 0 420 420">
        <circle className="ring ring-outer" cx="210" cy="210" r="197" />
        <circle className="ring ring-mid" cx="210" cy="210" r="166" />
        <circle className="ring ring-inner" cx="210" cy="210" r="122" />
        <circle className="ring ring-dash" cx="210" cy="210" r="198" />

        {TICKS.map((t, i) => (
          <line key={i} className={t.long ? 'tick tick-long' : 'tick'}
            x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} />
        ))}

        <line className="crosshair" x1="210" y1="10" x2="210" y2="48" />
        <line className="crosshair" x1="210" y1="372" x2="210" y2="410" />
        <line className="crosshair" x1="10" y1="210" x2="48" y2="210" />
        <line className="crosshair" x1="372" y1="210" x2="410" y2="210" />

        <g className="orbit-satellite">
          <circle cx="210" cy="13" r="3.2" />
        </g>
        <g className="orbit-satellite orbit-satellite-alt">
          <circle cx="210" cy="407" r="2" />
        </g>

        <path className="orbit-arc" d="M 210 42 A 168 168 0 0 1 378 210" />
        <path className="orbit-arc orbit-arc-faint" d="M 210 378 A 168 168 0 0 1 42 210" />
      </svg>

      <div className="orbit-core">
        <DroneGlyph size={54} />
        <span className="orbit-core-kicker">SYSTEMS</span>
        <b>Nominal</b>
      </div>

      <Chip className="chip-1" label="INDEX" value={`${docs} docs`} />
      <Chip className="chip-2" label="INFERENCE" value={model} />
      <Chip className="chip-3" label="SAFETY" value="HITL enforced" />
      <Chip className="chip-4" label="AGENT MESH" value="5 nodes" />
    </motion.div>
  )
}
